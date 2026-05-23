import os
import sys
import json
import argparse
import requests
import psycopg2
import yaml


# ---------------------------------------------------------------------------
# Hardcoded post-fetch filters per Omie endpoint call
# ---------------------------------------------------------------------------
FILTERS = {
    "ListarProdutos": lambda record: record.get("descricao_familia") == "Acabado",
}


def check_env_vars():
    missing = [v for v in ("OMIE_APP_KEY", "OMIE_APP_SECRET", "DATABASE_URL") if not os.environ.get(v)]
    if missing:
        print(
            f"Error: the following required environment variables are not set: {', '.join(missing)}\n"
            "Please export them before running this script:\n"
            + "\n".join(f"  export {v}=<value>" for v in missing),
            file=sys.stderr,
        )
        sys.exit(1)


def load_config(config_path: str) -> list[dict]:
    """Load and validate the sync config YAML file."""
    if not os.path.exists(config_path):
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    syncs = config.get("syncs")
    if not syncs or not isinstance(syncs, list):
        print("Error: config file must contain a non-empty 'syncs' list.", file=sys.stderr)
        sys.exit(1)

    for i, entry in enumerate(syncs):
        for field in ("table", "pk", "call", "url"):
            if not entry.get(field):
                print(f"Error: sync entry #{i + 1} is missing required field '{field}'.", file=sys.stderr)
                sys.exit(1)

    return syncs


def fetch_all_pages(call: str, url: str) -> list[dict]:
    """Fetch all pages from an Omie endpoint, handling pagination transparently."""
    app_key = os.environ["OMIE_APP_KEY"]
    app_secret = os.environ["OMIE_APP_SECRET"]
    headers = {"Content-type": "application/json"}

    records = []
    page = 1
    total_pages = None
    pages_fetched = 0

    while True:
        body = {
            "call": call,
            "app_key": app_key,
            "app_secret": app_secret,
            "param": [{"pagina": page, "registros_por_pagina": 50}],
        }

        response = requests.post(url, headers=headers, json=body)

        if response.status_code != 200:
            raise RuntimeError(f"Omie API returned HTTP {response.status_code}: {response.text}")

        data = response.json()

        if "faultCode" in data:
            raise RuntimeError(f"Omie API fault: [{data['faultCode']}] {data.get('faultString', '')}")

        if total_pages is None:
            total_pages = data.get("total_de_paginas", 1)

        page_records = []
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0:
                page_records = value
                break

        records.extend(page_records)
        pages_fetched += 1

        if page >= total_pages:
            break
        page += 1

    print(f"    Pages fetched:    {pages_fetched}", flush=True)
    return records


def apply_filter(call: str, records: list[dict]) -> list[dict]:
    """Apply hardcoded per-endpoint filter if one exists."""
    filter_fn = FILTERS.get(call)
    if filter_fn:
        return [r for r in records if filter_fn(r)]
    return records


def get_table_columns(conn, table: str) -> list[str]:
    """Return the list of column names for the target table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        rows = cur.fetchall()
    if not rows:
        raise RuntimeError(f"Table '{table}' does not exist in the database.")
    return [row[0] for row in rows]


def sync_table(entry: dict, conn) -> dict:
    """
    Upsert all records from one Omie endpoint into the target table,
    then delete rows no longer present in the API response.
    Raises RuntimeError on any failure — caller handles stop-on-error.
    """
    call  = entry["call"]
    url   = entry["url"]
    table = entry["table"]
    pk    = entry["pk"]

    records = fetch_all_pages(call, url)
    print(f"    Records from API: {len(records)}")

    records = apply_filter(call, records)
    print(f"    After filter:     {len(records)}")

    table_columns = get_table_columns(conn, table)
    api_pks = set()
    inserted = updated = deleted = unchanged = skipped_columns = 0

    with conn.cursor() as cur:
        for record in records:
            valid_keys = [k for k in record.keys() if k in table_columns]
            ignored    = [k for k in record.keys() if k not in table_columns]
            if ignored:
                skipped_columns += len(ignored)

            row_data = {k: record[k] for k in valid_keys}

            for k, v in row_data.items():
                if isinstance(v, (dict, list)):
                    row_data[k] = json.dumps(v, ensure_ascii=False)

            pk_value = row_data.get(pk)
            if pk_value is None:
                continue

            api_pks.add(pk_value)

            cur.execute(f"SELECT * FROM {table} WHERE {pk} = %s", (pk_value,))
            existing = cur.fetchone()

            if existing is None:
                cols         = ", ".join(row_data.keys())
                placeholders = ", ".join(["%s"] * len(row_data))
                cur.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                    list(row_data.values()),
                )
                inserted += 1
            else:
                col_names    = [desc[0] for desc in cur.description]
                existing_dict = dict(zip(col_names, existing))
                changed = {
                    k: v for k, v in row_data.items()
                    if str(existing_dict.get(k)) != str(v)
                }
                changed.pop(pk, None)

                if changed:
                    set_clause = ", ".join(f"{k} = %s" for k in changed)
                    cur.execute(
                        f"UPDATE {table} SET {set_clause} WHERE {pk} = %s",
                        list(changed.values()) + [pk_value],
                    )
                    updated += 1
                else:
                    unchanged += 1

        cur.execute(f"SELECT {pk} FROM {table}")
        db_pks        = {row[0] for row in cur.fetchall()}
        pks_to_delete = db_pks - api_pks

        for pk_value in pks_to_delete:
            cur.execute(f"DELETE FROM {table} WHERE {pk} = %s", (pk_value,))
            deleted += 1

    conn.commit()

    return {
        "inserted": inserted,
        "updated": updated,
        "deleted": deleted,
        "unchanged": unchanged,
        "skipped_columns": skipped_columns,
    }


def main():
    parser = argparse.ArgumentParser(description="Sync all Omie ERP endpoints defined in omie-sync.yaml into Postgres.")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "..", "omie-sync.yaml"),
        help="Path to omie-sync.yaml (default: ../omie-sync.yaml relative to this script)",
    )
    args = parser.parse_args()

    check_env_vars()

    syncs = load_config(args.config)
    print(f"Loaded {len(syncs)} sync job(s) from {args.config}\n")

    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        for i, entry in enumerate(syncs, 1):
            print(f"[{i}/{len(syncs)}] {entry['call']} → {entry['table']} (pk: {entry['pk']})")
            try:
                summary = sync_table(entry, conn)
            except RuntimeError as e:
                # Rollback current transaction and stop immediately
                conn.rollback()
                print(f"\n✖ Sync failed for '{entry['table']}': {e}", file=sys.stderr)
                print("Stopping. No further sync jobs will run.", file=sys.stderr)
                sys.exit(1)

            print(f"    ✔ Inserted:         {summary['inserted']}")
            print(f"    ✔ Updated:          {summary['updated']}")
            print(f"    ✔ Deleted:          {summary['deleted']}")
            print(f"    ✔ Unchanged:        {summary['unchanged']}")
            if summary["skipped_columns"]:
                print(f"    ⚠ Skipped columns:  {summary['skipped_columns']} (not in table)")
            print()

    finally:
        conn.close()

    print(f"✔ All {len(syncs)} sync job(s) completed successfully.")


if __name__ == "__main__":
    main()

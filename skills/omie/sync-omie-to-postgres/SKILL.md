---
name: sync-omie-to-postgres
description: >
  Sync data from Omie ERP API endpoints into existing PostgreSQL tables, handling
  pagination, upsert (update changed columns only), and deletion of records no longer
  present in Omie. Use this skill ONLY when the user wants to pull live Omie data into
  Postgres tables that already exist. Triggers include: "sync Omie data", "update my
  Postgres table from Omie", "pull latest Omie records into the database", "refresh Omie
  data", "add a new table to the sync", or any request to keep Postgres tables in sync
  with Omie endpoints.

  DO NOT use this skill to create new tables (use infer-postgres-schema for that), for
  non-Omie data sources, or for one-off queries against the database.
---

# sync-omie-to-postgres

Pull all records from Omie ERP API endpoints into existing PostgreSQL tables.
All sync jobs are declared in `omie-sync.yaml` — no user input is needed at runtime,
making this safe to run as a cron job.

Handles pagination transparently, upserts only changed columns, and deletes rows
whose primary keys are no longer returned by the API.

This skill is scoped exclusively to **Omie ERP API data** and **existing Postgres tables**.

---

## Prerequisites

Before running any step, verify the following are in place. If anything is missing, stop
and tell the user what's needed.

| Requirement | How to check | How to fix |
|---|---|---|
| `OMIE_APP_KEY` env var set | `[[ -n "${OMIE_APP_KEY}" ]] && echo "✅ Set"` | - |
| `OMIE_APP_SECRET` env var set | `[[ -n "${OMIE_APP_SECRET}" ]] && echo "✅ Set"` | - |
| `DATABASE_URL` env var set | `[[ -n "${DATABASE_URL}" ]] && echo "✅ Set"` | - |
| All target tables exist in Postgres | `\dt` in psql | Run the `infer-postgres-schema` skill first |
| `requests`, `psycopg2`, `pyyaml` available | `python -c "import requests, psycopg2, yaml"` | `pip install requests psycopg2-binary pyyaml` |

---

## Config file: `omie-sync.yaml`

All sync jobs are declared in `omie-sync.yaml`, located at the root of the
`sync-omie-to-postgres/` folder. The script reads this file automatically —
no flags or user input needed at runtime.

### Structure

```yaml
syncs:
  - table: omie_produtos       # target Postgres table (must already exist)
    pk: codigo_produto         # primary key column in that table
    call: ListarProdutos       # Omie API call name
    url: https://app.omie.com.br/api/v1/geral/produtos/
```

### Adding a new sync job

When the user wants to add a new table to the sync, update `omie-sync.yaml` by appending
a new entry — no changes to the script are needed:

```yaml
  - table: omie_clientes
    pk: codigo_cliente_omie
    call: ListarClientes
    url: https://app.omie.com.br/api/v1/geral/clientes/
```

---

## Running the sync

```bash
python scripts/sync-omie-table.py
```

The script resolves `omie-sync.yaml` relative to its own location automatically.
To use a different config path:

```bash
python scripts/sync-omie-table.py --config /path/to/omie-sync.yaml
```

### Cron job example

```cron
0 3 * * * cd /path/to/skills/omie/sync-omie-to-postgres && python scripts/sync-omie-table.py >> logs/sync.log 2>&1
```

---

## Filtering rules (hardcoded per endpoint)

Some Omie endpoints require post-fetch filtering. These are hardcoded in the script and
applied automatically — they do not need to be declared in `omie-sync.yaml`.

| Endpoint call | Filter applied |
|---|---|
| `ListarProdutos` | Keep only records where `descricao_familia == "Acabado"` |
| *(all others)* | No filter — all returned records are synced |

---

## Behaviour on failure

If any sync job fails, the script rolls back that job's transaction, prints the error,
and exits immediately with code 1. No further jobs in the config will run.

---

## Error handling

| Situation | Action |
|---|---|
| `OMIE_APP_KEY` or `OMIE_APP_SECRET` not set | Print prerequisite instructions and exit 1 |
| `omie-sync.yaml` not found or malformed | Print config error and exit 1 |
| Omie API returns non-200 | Raise error, rollback, stop |
| Omie returns `faultCode` / `faultString` | Raise error with fault message, rollback, stop |
| Target table does not exist | Raise error, rollback, stop — tell user to run `infer-postgres-schema` first |
| Column in API response not in table | Warn the user; skip that column and continue |
| `DATABASE_URL` not set or wrong | Print prerequisite instructions and exit 1 |

---

## Example output

```
Loaded 2 sync job(s) from omie-sync.yaml

[1/2] ListarProdutos → omie_produtos (pk: codigo_produto)
    Pages fetched:    12
    Records from API: 348
    After filter:     201
    ✔ Inserted:         12
    ✔ Updated:          41
    ✔ Deleted:          3
    ✔ Unchanged:        145

[2/2] ListarClientes → omie_clientes (pk: codigo_cliente_omie)
    Pages fetched:    4
    Records from API: 98
    After filter:     98
    ✔ Inserted:         0
    ✔ Updated:          5
    ✔ Deleted:          1
    ✔ Unchanged:        92

✔ All 2 sync job(s) completed successfully.
```

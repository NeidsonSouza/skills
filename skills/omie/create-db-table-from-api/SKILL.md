---
name: infer-postgres-schema
description: >
  Infer a PostgreSQL table schema from Omie ERP API data and create the table immediately.
  Use this skill ONLY when the user wants to map data coming from the Omie ERP API into a
  PostgreSQL table. Triggers include: running a script that calls the Omie API to inspect
  fields, generating a CREATE TABLE statement from Omie API output, inferring PostgreSQL
  column types from an Omie API response sample, or setting up a database table to store
  Omie ERP data. Trigger this skill when `scripts/get-table-fields.py` is used with an Omie
  API command, or when the user says things like "create a table for Omie products/clients/
  orders", "map this Omie data to Postgres", or "I want to store Omie data in the database".

  DO NOT use this skill for generic PostgreSQL table creation unrelated to Omie ERP, for
  other APIs or data sources, or for general database schema design tasks.
---

# infer-postgres-schema (Omie ERP → PostgreSQL)

Infer PostgreSQL column types from the output of `scripts/get-table-fields.py` when querying
the **Omie ERP API**, ask the user minimal schema questions, and immediately run `CREATE TABLE`
— then display the table spec straight from the database.

This skill is scoped exclusively to **Omie ERP API data**. If the user wants to create a
PostgreSQL table from a non-Omie source, do not use this skill — handle it as a general task.

---

## Prerequisites

Before running any step, verify the following are in place. If anything is missing, stop and
tell the user what's needed.

| Requirement | How to check |
|---|---|
| `OMIE_APP_KEY` env var set | `[[ -n "${OMIE_APP_KEY}" ]] && echo "✅ Set"` |
| `OMIE_APP_SECRET` env var set | `[[ -n "${OMIE_APP_SECRET}" ]] && echo "✅ Set"` |
| `DATABASE_URL` env var set | `[[ -n "${DATABASE_URL}" ]] && echo "✅ Set"` |
| `requests` library available | `python -c "import requests"` |

> The script will exit with a clear error message if `OMIE_APP_KEY` or `OMIE_APP_SECRET` are
> missing. `DATABASE_URL` is checked later, before the `CREATE TABLE` step.

---

## Step-by-step workflow

### 1. Confirm the data source is Omie

Before proceeding, confirm the bash command or context involves the Omie ERP API
(e.g. calls to `app.omie.com.br/api/v1/...`). If the user has not made this clear, ask:

> "Is this data coming from the Omie ERP API?"

If the answer is no, stop and handle the request as a general task outside this skill.

### 2. Collect the user's bash command

Ask the user for the bash command they want to run (the `-i` input to the script). Example:

> "Please provide the Omie API bash command you want to pass to the script."

The user's response is the raw shell command string. Write it to a temp file:

```bash
cat > /tmp/input_command.sh << 'EOF'
<user's bash command here>
EOF
```

### 3. Run the script

```bash
python scripts/get-table-fields.py -i /tmp/input_command.sh
```

Capture the full stdout. The output will be a Python dict literal (one example Omie record)
that represents all fields that must become columns in the new table.

### 4. Parse the output and infer PostgreSQL types

Parse every key-value pair in the output dict and map it to a PostgreSQL type using the rules below.

#### Type inference rules

| Python value pattern | PostgreSQL type |
|---|---|
| `int` or `float` (e.g. `0`, `0.25`) | `NUMERIC` (use `INTEGER` if always whole) |
| `str` that is always short/fixed (e.g. `'N'`, `'S'`, `'UN'`) | `VARCHAR(50)` |
| `str` that may be long or free text | `TEXT` |
| `str` that looks like a date `DD/MM/YYYY` | `DATE` |
| `str` that looks like a time `HH:MM:SS` | `TIME` |
| Nested `dict` (e.g. `{'dAlt': ..., 'dInc': ...}`) | `JSONB` |
| Nested `list` | `JSONB` |
| `bool` or `'N'`/`'S'` flag strings | `VARCHAR(1)` |

> **Important:** Any field whose value is a nested dict or list **must** be typed as `JSONB`,
> regardless of its contents.

Build a preliminary column list like:
```
column_name   | inferred_type | example_value
```

### 5. Ask about the primary key

Present the column list to the user and ask:

> "Which field should be the **primary key**? (e.g. `codigo_produto`)"

Wait for the user's answer before proceeding.

### 6. Ask about foreign keys

Ask once:

> "Should any field be a **foreign key** referencing an existing table?
> If yes, tell me the field name, the target table, and the target column
> (e.g. `codigo_familia → familias(id)`). If none, just say 'none'."

Wait for the user's answer.

### 7. Build the CREATE TABLE statement

Construct the full SQL using the inferred types, the chosen primary key, and any foreign key
constraints. Follow these conventions:

- Table name: ask the user if not already provided, or derive it from the Omie entity name
  in snake_case (e.g. `omie_produtos`, `omie_clientes`).
- Use `NOT NULL` only for the primary key column.
- Place `PRIMARY KEY` inline on its column definition.
- Place `REFERENCES` inline on any FK column.
- Keep column order identical to the original Omie dict key order.

Example shape:

```sql
CREATE TABLE omie_produtos (
    codigo_produto      BIGINT PRIMARY KEY,
    codigo              VARCHAR(50),
    descricao           TEXT,
    inativo             VARCHAR(1),
    valor_unitario      NUMERIC,
    info                JSONB,
    recomendacoes_fiscais JSONB,
    codigo_familia      BIGINT REFERENCES familias(id),
    ...
);
```

### 8. Execute immediately

Run the SQL against the PostgreSQL database:

```bash
psql "$DATABASE_URL" -c "<the CREATE TABLE statement>"
```

If `DATABASE_URL` is not set, ask the user for the connection string before running.

Do **not** ask for confirmation — execute right away after collecting PK/FK answers.

### 9. Show the table spec from the database

After successful creation, query the database to show the actual table definition as recorded:

```sql
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = '<table_name>'
ORDER BY ordinal_position;
```

Display the result as a formatted table to the user. Also show any constraints:

```sql
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = '<table_name>'::regclass;
```

### 10. Delete the files that will not be used in future

Delete `/tmp/input_command.sh` and any other junk file created in in this process.

---

## Error handling

| Situation | Action |
|---|---|
| Data source is not Omie ERP | Stop; do not use this skill — handle as a general task |
| `OMIE_APP_KEY` or `OMIE_APP_SECRET` not set | Show the prerequisite instructions and stop |
| Script exits with non-zero code | Show stderr to user and stop |
| Output is not a parseable dict | Ask user to check the script and try again |
| `psql` / DB connection fails | Ask for correct `DATABASE_URL` |
| Table already exists | Show the error; ask if user wants to `DROP` first or rename |

---

## Example interaction summary

```
User:  "Run the script with: curl -s https://app.omie.com.br/api/v1/geral/produtos/ ..."
Agent: confirms Omie API → writes command → runs get-table-fields.py → parses output
Agent: "Here are the inferred columns: [...]. Which field is the primary key?"
User:  "codigo_produto"
Agent: "Any foreign keys? (field → table(column))"
User:  "codigo_familia → familias(id)"
Agent: runs CREATE TABLE immediately
Agent: shows information_schema result from the live DB
```

---
name: get-client-data
description: >
  Retrieve basic registration data for all clients from the Omie ERP system.
  Use this skill when the agent needs any of the following client fields:
  `cnpj_cpf`, `codigo_cliente`, `nome_fantasia`, or `razao_social`.
  Triggers include: "get client data", "list clients", "fetch client registration",
  "I need the client's CNPJ/CPF", or any request that requires identifying a client
  by name or code before performing a downstream operation.

  DO NOT use this skill for order data, product data, or any non-client entity,
  even if the request indirectly involves a client.
---

# get-client-data

Runs `scripts/list_client_data.py` to retrieve the full list of clients from the
Omie ERP system and returns their basic registration fields in JSON Lines format.

This skill takes no parameters and always returns the complete client list.

---

## Prerequisites

Before running any step, verify the following are in place. If anything is missing,
stop and tell the user what's needed.

| Requirement          | How to check                                      |
|----------------------|---------------------------------------------------|
| `OMIE_APP_KEY` set   | `[[ -n "${OMIE_APP_KEY}" ]] && echo "✅ Set"`     |
| `OMIE_APP_SECRET` set| `[[ -n "${OMIE_APP_SECRET}" ]] && echo "✅ Set"`  |

---

## Step-by-step workflow

### 1. Run the script

```bash
python scripts/list_client_data.py
```

Capture the full stdout. The output is a stream of JSON objects (one per line), each
representing one client record.

### 2. Parse the output

Each line of output is a JSON object with the following fields:

| Field                        | Type     | Description                        |
|------------------------------|----------|------------------------------------|
| `cnpj_cpf`                   | `string` | Client tax ID (CNPJ or CPF)        |
| `codigo_cliente`             | `number` | Omie's internal client ID          |
| `codigo_cliente_integracao`  | `string` | External integration code (may be empty) |
| `nome_fantasia`              | `string` | Trade name                         |
| `razao_social`               | `string` | Legal company name                 |

Example record:

```json
{
  "cnpj_cpf": "15.470.976/0001-03",
  "codigo_cliente": 6216003967,
  "codigo_cliente_integracao": "",
  "nome_fantasia": "CONSTRUALTO",
  "razao_social": "JR MATERIAIS DE CONSTRUCAO LTDA"
}
```

### 3. Use the data

Pass the relevant fields to the downstream step that triggered this skill
(e.g. use `codigo_cliente` to look up orders, or `cnpj_cpf` to match a billing record).

---

## Error handling

| Situation                              | Action                                              |
|----------------------------------------|-----------------------------------------------------|
| `OMIE_APP_KEY` or `OMIE_APP_SECRET` not set | Show prerequisite instructions and stop        |
| Script exits with non-zero code        | Show stderr to the user and stop                    |
| Output is empty                        | Inform the user that no clients were returned; ask them to verify API credentials and filters |
| Output is not valid JSON Lines         | Ask the user to check the script and try again      |

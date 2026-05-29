---
name: get-parcelas
description: >
  Retrieve basic registration data for payment terms (parcelas) from the Omie ERP system.
  Use this skill when the agent needs any of the following fields: `codigo_parcela`, `cDescricao`, or `nParcelas`.
  Triggers include: "list parcelas", "get parcela data", "payment terms", "installment codes", 
  or any request that requires the parcela code for creating a pedido.

  DO NOT use this skill for other Omie entities (clients, products, orders),
  for generic database queries, or for non-Omie data sources.
---

# get-parcelas

Runs `scripts/list_parcela_data.py` to retrieve the full list of payment terms (parcelas) 
from the Omie ERP system and returns their basic registration fields in JSON Lines format.

This skill takes no parameters and always returns the complete list of parcelas.

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
python scripts/list_parcela_data.py
```

Capture the full stdout. The output is a stream of JSON objects (one per line), each
representing one parcela record.

### 2. Parse the output

Each line of output is a JSON object with the following fields:

| Field            | Type     | Description                                      |
|------------------|----------|--------------------------------------------------|
| `cDescricao`     | `string` | Description of the payment term                  |
| `codigo_parcela` | `string` | Parcel code (cCodigo) — Used when creating pedidos |
| `nParcelas`      | `number` | Number of installments                           |

Example record:

```json
{
  "cDescricao": "A Vista",
  "codigo_parcela": "000",
  "nParcelas": 1
}
```

### 3. Use the data

Pass the relevant fields to the downstream step (e.g. use `codigo_parcela` when creating a new pedido).

---

## Error handling

| Situation                              | Action                                              |
|----------------------------------------|-----------------------------------------------------|
| `OMIE_APP_KEY` or `OMIE_APP_SECRET` not set | Show prerequisite instructions and stop        |
| Script exits with non-zero code        | Show stderr to the user and stop                    |
| Output is empty                        | Inform the user that no parcelas were returned; ask them to verify API credentials |
| Output is not valid JSON Lines         | Ask the user to check the script and try again      |
```

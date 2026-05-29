---
name: get-parcelas
description: >
  Retrieve basic registration data for parcelas from the Omie ERP API.
  Use this skill when the agent needs to list parcelas and access fields such as
  `codigo_parcela`. Triggers include: "list parcelas", "get parcela data",
  "retrieve parcelas from Omie", or any task that requires running
  `scripts/list_parcela_data.py` to fetch parcela records.

  DO NOT use this skill for other Omie entities (clients, products, orders),
  for generic database queries, or for non-Omie data sources.
---

# get-parcelas (Omie ERP → Parcela List)

Retrieve basic registration data for parcelas by running `scripts/list_parcela_data.py`
against the **Omie ERP API**. This skill takes no input parameters and returns the full
list of parcelas in JSON Lines format.

This skill is scoped exclusively to **Omie ERP parcela data**. For other entities, use
the appropriate skill.

---

## Prerequisites

Before running any step, verify the following are in place. If anything is missing, stop and
tell the user what's needed.

| Requirement | How to check |
|---|---|
| `OMIE_APP_KEY` env var set | `[[ -n "${OMIE_APP_KEY}" ]] && echo "✅ Set"` |
| `OMIE_APP_SECRET` env var set | `[[ -n "${OMIE_APP_SECRET}" ]] && echo "✅ Set"` |
| `requests` library available | `python -c "import requests"` |

---

## Step-by-step workflow

### 1. Confirm the context is Omie parcelas

Confirm the task involves fetching parcela data from the Omie ERP API. If unclear, ask:

> "Are you trying to retrieve parcela data from the Omie ERP API?"

If the answer is no, stop and handle the request as a general task outside this skill.

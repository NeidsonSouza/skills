---
name: create-order-omie
description: "Use this skill whenever the user wants to create a sales order (pedido de venda) in the Omie ERP. The agent must collect client information, resolve the correct client code, generate an integration order code, collect product list with quantities, resolve product codes and CFOPs, then run the creation script. Triggers: user mentions creating an order, pedido, or sending products to a client in Omie."
---

# Create Order in Omie ERP

## Overview

This skill guides the agent to create a sales order (`pedido de venda`) in Omie via script. The agent must collect and resolve all required values before running the final creation script.

The final script call will be:
```bash
python scripts/create_order.py \
  --codigo_cliente <value> \
  --codigo_pedido_integracao <value> \
  --products '[{"cfop": "...", "codigo_produto": "...", "quantidade": ...}, ...]'
```

---

## Step 1 — Identify the Client (`codigo_cliente`)

### 1.1 Collect client identifier from the user
Accept any of the following, from text, image, or PDF attachment:
- CNPJ
- CPF
- Nome Fantasia
- Razão Social

Be flexible: the user may provide this in a message, in an attached document, or in an image. Extract the identifier intelligently from whatever format is given.

**CNPJ filtering — seller vs. client:**
Documents (images, PDFs) may contain more than one CNPJ — typically the seller's and the client's. Always normalize CNPJs before comparing: strip all non-numeric characters (`.`, `/`, `-`) and ensure the result has exactly 14 digits.

The seller's CNPJ is **05950308000100** (Kipanus Industria e Comercio LTDA). If a document contains multiple CNPJs, discard any that match the seller's and use the remaining one as the client identifier. If after filtering no CNPJ remains, fall back to nome_fantasia or razão_social found in the document, or ask the user.

### 1.2 Run client lookup
```bash
python scripts/list_clients.py
```
This script returns all clients registered in the system.

### 1.3 Find the best match
- Compare the user-provided identifier against the returned client list.
- Rank by similarity (CNPJ/CPF exact match takes priority; otherwise fuzzy match on nome_fantasia / razao_social).

### 1.4 Confirm with the user (conditional)
- **If certainty ≥ 90%:** use the matched client directly, no confirmation needed. Inform the user which client was selected.
- **If certainty < 90%:** present the top match(es) to the user and ask for confirmation before proceeding.

### 1.5 Save `codigo_cliente`
Once confirmed or auto-matched, store the `codigo_cliente` value for the final script.

---

## Step 2 — Get Order Integration Code (`codigo_pedido_integracao`)

Run the following script to get the next available integration code:
```bash
python scripts/get_codigo_pedido_integracao.py
```
Store the output as `codigo_pedido_integracao`.

---

## Step 3 — Collect Products

The user may provide products in any format: plain text, a list, an image, or a PDF. Be flexible and extract all product entries intelligently. Each entry from the user should include:
- **Product description** (required — used to look up `codigo_produto` and determine `cfop`)
- **Quantidade** (required — numeric quantity)
- **Price** (optional — collect if provided, used for total double-check at the end)

If any required field is ambiguous or missing for a product, ask the user before proceeding.

---

## Step 4 — Resolve Each Product (`codigo_produto` and `cfop`)

For each product collected in Step 3, do the following:

### 4.1 Run product lookup
```bash
python scripts/list_products.py
```
This returns the full product catalog with codes and descriptions.

### 4.2 Find the best match
Match the user's product description against the catalog descriptions.

### 4.3 Confirm with the user (conditional)
- **If certainty ≥ 90%:** use the matched product directly. Inform the user which product was matched.
- **If certainty < 90%:** present the top match(es) and ask for confirmation.

### 4.4 Save `codigo_produto`
Use the `codigo_produto` from the matched catalog entry.

### 4.5 Determine `cfop`
Inspect the **product description returned by the API** (not the user's input):
- Set `cfop = "5.102"` if the description contains any of the words: `SACO`, `TAPETE`, `VARAL`, `ESTAMPADO` (case-insensitive).
- Set `cfop = "5.101"` in all other cases.

---

## Step 5 — Review and Confirm Order

Before running the creation script, present a summary to the user:

```
Cliente: <nome> (codigo_cliente: <value>)
Pedido integração: <codigo_pedido_integracao>

Produtos:
1. <product name> | Qtd: <quantidade> | CFOP: <cfop> | Código: <codigo_produto> [| Preço unit.: R$ <price>]
2. ...

[Total estimado: R$ <total> (if prices were provided)]
```

Ask the user to confirm before proceeding.

---

## Step 6 — Create the Order

Once the user confirms, run:
```bash
python scripts/create_order.py \
  --codigo_cliente <value> \
  --codigo_pedido_integracao <value> \
  --products '[{"cfop": "...", "codigo_produto": "...", "quantidade": ...}, ...]'
```

Report the result to the user. If the script returns an error, inform the user clearly and suggest corrective action.

---

## Error Handling & Edge Cases

- **Client not found:** inform the user no match was found and ask them to provide more details.
- **Product not found:** inform the user and ask for clarification or an alternative description.
- **Multiple strong matches:** always present options and let the user decide rather than guessing.
- **Missing quantity:** always ask — never assume a quantity.
- **Partial input (e.g., only some products provided):** ask if the list is complete before proceeding to Step 5.
- **Price mismatch at total check:** flag the discrepancy to the user before creating the order.

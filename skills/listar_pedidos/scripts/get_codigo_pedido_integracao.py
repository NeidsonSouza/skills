import json
import requests
import os

APP_KEY = os.getenv("OMIE_APP_KEY")
APP_SECRET = os.getenv("OMIE_APP_SECRET")
PAGE_SIZE = 100
URL = "https://app.omie.com.br/api/v1/produtos/pedido/"
CALL = "ListarPedidos"


def fetch_page(page: int) -> dict:
    payload = {
        "call": CALL,
        "param": [
            {
                "pagina": page,
                "registros_por_pagina": PAGE_SIZE,
                "apenas_importado_api": "N",
            }
        ],
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
    }
    response = requests.post(URL, json=payload)
    response.raise_for_status()
    return response.json()


def main():
    # Step 1: fetch first page just to learn the total
    first = fetch_page(1)
    total_pages = first.get("total_de_paginas", 1)

    # Step 2: walk backwards from the last page
    for page in range(total_pages, 0, -1):
        data = fetch_page(page) if page != 1 else first
        items = data.get("pedido_venda_produto", [])

        # Walk backwards within the page too
        for item in reversed(items):
            code = item.get("cabecalho", {}).get("codigo_pedido_integracao", "")
            if code:
                try:
                    next_code = int(code) + 1
                    print(next_code)
                except ValueError:
                    # Non-integer code — just report it as-is
                    print(f"Last used: {code!r} (not an integer, can't auto-increment)")
                return

    print(1)


if __name__ == "__main__":
    main()

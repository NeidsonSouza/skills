import json
import requests
import os

APP_KEY = os.getenv("OMIE_APP_KEY")
APP_SECRET = os.getenv("OMIE_APP_SECRET")
PAGE_SIZE = 100
URL = "https://app.omie.com.br/api/v1/geral/clientes/"
CALL = "ListarClientesResumido"


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
    page = 1
    total_pages = 1

    while page <= total_pages:
        data = fetch_page(page)

        total_pages = data.get("total_de_paginas", 1)
        items = data.get("clientes_cadastro_resumido", [])

        for item in items:
            print(json.dumps(item, ensure_ascii=False))

        page += 1


if __name__ == "__main__":
    main()

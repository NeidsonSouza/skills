import argparse
import json
import os
import sys

import requests


OMIE_API_URL = "https://app.omie.com.br/api/v1/produtos/pedidovenda/"

APP_KEY = os.environ.get("OMIE_APP_KEY", "#APP_KEY#")
APP_SECRET = os.environ.get("OMIE_APP_SECRET", "#APP_SECRET#")


def create_order(codigo_cliente: int, codigo_pedido_integracao: int, products: list[dict]) -> dict:
    payload = {
        "call": "AdicionarPedido",
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
        "param": [
            {
                "codigo_parcela": "T54",
                "codigo_pedido_integracao": codigo_pedido_integracao,
                "codigo_cliente": codigo_cliente,
                "codigo_categoria": "1.04.94",
                "codigo_conta_corrente": 5887041986,
                "codVend": 0,
                "enviar_email": "S",
                "itens": products,
            }
        ],
    }

    response = requests.post(
        OMIE_API_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
    )

    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a sales order on Omie.")
    parser.add_argument("--codigo_cliente", type=int, required=True, help="Client code")
    parser.add_argument("--codigo_pedido_integracao", type=int, required=True, help="Integration order code")
    parser.add_argument(
        "--products",
        type=str,
        required=True,
        help='JSON array of products, e.g. \'[{"cfop": "5.101", "codigo_produto": 123, "quantidade": 1}]\'',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        products = json.loads(args.products)
    except json.JSONDecodeError as e:
        print(f"Error: --products is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(products, list) or not products:
        print("Error: --products must be a non-empty JSON array.", file=sys.stderr)
        sys.exit(1)

    result = create_order(
        codigo_cliente=args.codigo_cliente,
        codigo_pedido_integracao=args.codigo_pedido_integracao,
        products=products,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

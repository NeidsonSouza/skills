import os
import re
import json
import requests
import argparse


def load_curl_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def parse_curl(raw: str) -> tuple[str, dict]:
    """Extract URL and JSON body from a curl command string."""
    # Remove line continuations and collapse into one line
    single_line = raw.replace("\\\n", " ").strip()

    # Extract URL (first argument after 'curl ...')
    url_match = re.search(r"curl\s+(?:-s\s+)?(['\"]?)(\S+)\1", single_line)
    if not url_match:
        raise ValueError("Could not find URL in curl command.")
    url = url_match.group(2)

    # Extract -d / --data body
    data_match = re.search(r"-d\s+'([^']+)'", single_line)
    if not data_match:
        data_match = re.search(r'-d\s+"([^"]+)"', single_line)
    if not data_match:
        raise ValueError("Could not find -d payload in curl command.")

    raw_body = data_match.group(1)

    # Replace placeholders with env vars
    app_key = os.environ["OMIE_APP_KEY"]
    app_secret = os.environ["OMIE_APP_SECRET"]
    raw_body = raw_body.replace("#APP_KEY#", app_key)
    raw_body = raw_body.replace("#APP_SECRET#", app_secret)

    body = json.loads(raw_body)
    return url, body


def make_request(url: str, body: dict) -> dict:
    headers = {"Content-type": "application/json"}
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    return response.json()


def extract_first_item(data: dict) -> dict | list | None:
    """
    Find the first list value in the response that contains actual records
    and return its first element. Falls back to the full response if none found.
    """
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 0:
            return value[0]
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", required=True)
    args = parser.parse_args()

    input_file = args.i

    raw_curl = load_curl_file(input_file)
    url, body = parse_curl(raw_curl)

    response_data = make_request(url, body)
    first_item = extract_first_item(response_data)

    print(first_item)


if __name__ == "__main__":
    main()

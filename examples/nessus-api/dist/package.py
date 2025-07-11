import requests
from datetime import datetime, timezone
import urllib3
import argparse
import json
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def process_request_data(workflow_id):
    file_path = Path(f'/tmp/is/{workflow_id}.json')

    if not file_path.exists():
        raise FileNotFoundError(f'File {file_path} not found')

    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
            
            url = config.get('url')
            access_key = config.get('accessKey')
            secret_key = config.get('secretKey')

            if not all([url, access_key, secret_key]):
                raise ValueError(f"O JSON deve conter as chaves: 'url', 'accessKey' e 'secretKey', {config}")

            return {
                'url': url,
                'access_key': access_key,
                'secret_key': secret_key
            }

    except Exception as e:
        raise RuntimeError(f"Erro ao processar o arquivo JSON: {e}")


def consultar_vulnerabilidades(url, access_key, secret_key):
    headers = {
        "Accept": "*/*",
        "X-ApiKeys": f"accessKey={access_key};secretKey={secret_key}"
    }

    print(f"Requisitando: {url}")
    response = requests.get(url, headers=headers, verify=False)

    if response.status_code != 200:
        raise RuntimeError(f"Erro na requisição principal: {response.status_code} - {response.text}")

    data = response.json()
    hosts = data.get("hosts", [])
    scan_date = datetime.now(timezone.utc)
    host_ids = [host.get("host_id") for host in hosts]

    severity_map = {0: "None", 1: "Low", 2: "Medium", 3: "High", 4: "Critical"}

    for host_id in host_ids:
        print(f"\n Buscando dados do host {host_id}...")
        host_url = f"{url}/hosts/{host_id}"
        host_response = requests.get(host_url, headers=headers, verify=False)

        if host_response.status_code == 200:
            host_data = host_response.json()
            vulnerabilities = host_data.get("vulnerabilities", [])

            for vuln in vulnerabilities:
            
                severity = vuln.get("severity", 0)
                print(f"  - {vuln['plugin_name']} | Gravidade: {severity_map.get(severity, 'Desconhecida')} | Plugin ID: {vuln['plugin_id']}")
        else:
            print(f"Erro ao buscar dados do host {host_id}: {host_response.status_code}")


def main(workflow_id, project_name):
    try:
        config = process_request_data(workflow_id)
        consultar_vulnerabilidades(config['url'], config['access_key'], config['secret_key'])

    except Exception as e:
        print(f"[ERRO FATAL] {e}")
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow_id', type=str, required=True)
    parser.add_argument('--project_name', type=str, required=True)
    args, _ = parser.parse_known_args()

    main(args.workflow_id, args.project_name)

import argparse
import json
from pathlib import Path
from infinitestack import scicrop_api
from infinitestack import collect


def process_response_data(lat, lon):
    return scicrop_api.get_weather_data(lat, lon)


def process_request_data():
    file_path = Path(f'/tmp/is/{workflow_id}.json')

    if not file_path.exists():
        print(f'File {file_path} file found')
        exit(1)
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            lat = float(data["lat"])
            lon = float(data["lon"])
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Invalid input format: {e}")
        print("Expected format: '{\"lat\": value, \"lon\": value}'")
        exit(1)

    return lat, lon


def build_request(lat, lon):
    with open("descriptor.json", "r") as file:
        package_json = json.load(file)

    json_response = process_response_data(lat, lon)
    print('Response = ', json_response)
    request_data = []
    for data in package_json["output"][0]["tables"]:
        table_name = data["table_name"]
        column_array = data["columns"]

        row = {}
        for col in column_array:
            print("col name", col["name"])
            name = col["name"]
            row[name] = json_response["data"].get(name)

        request_data.append({"table_name": table_name, "fields": [row]})

    print("Request = ", json.dumps(request_data, indent=2))


def get_database_id_from_package(project_name):
    bridge = collect.Bridge(project_name)
    return bridge.get_database_ids_from_package("scicrop-api")


def main(workflow_id, project_name):
    bridge = collect.Bridge(project_name)
    project_id = bridge.project_id
    database_ids = get_database_id_from_package(project_name)

    lat, lon = process_request_data()
    build_request(lat, lon)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow_id', type=str, required=True)
    parser.add_argument('--project_name', type=str, required=True)
    args, _ = parser.parse_known_args()

    workflow_id = args.workflow_id
    project_name = args.project_name

    main(workflow_id, project_name)

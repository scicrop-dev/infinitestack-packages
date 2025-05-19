import argparse
import json
from pathlib import Path
from infinitestack import scicrop_api
from infinitestack import orm
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
    with open(
            "/opt/infinitestack/etc/commons/packages/98e1e23e-e56a-413f-be8c-363db66fc2fb/descriptor.json",
            "r") as file:
        package_json = json.load(file)

    json_response = process_response_data(lat, lon)
    tables_list = []

    for data in package_json["output"][0]["tables"]:
        table_name = data["table_name"]
        column_array = data["columns"]

        row = {}
        for col in column_array:
            name = col["name"]
            row[name] = json_response["data"].get(name)

        tables_list.append({"table_name": table_name, "fields": [row]})

    request_data = {"tables": tables_list}
    return request_data


def save_database(lat, lon, database_name, project_name):
    my_orm = orm.Orm(database_name)
    my_orm.set_project(project_name)
    my_orm.insert_data_json(build_request(lat, lon))


def get_database_id_from_package(project_name):
    bridge = collect.Bridge(project_name)
    return bridge.get_database_ids_from_package("scicrop-api")


def main(workflow_id, project_name):
    bridge = collect.Bridge(project_name)
    project_id = bridge.project_id
    database_ids = get_database_id_from_package(project_name)

    lat, lon = process_request_data()
    request = build_request(lat, lon)
    #TODO: get the database name from the id
    save_database(lat, lon, ..., project_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow_id', type=str, required=True)
    parser.add_argument('--project_name', type=str, required=True)
    args, _ = parser.parse_known_args()

    workflow_id = args.workflow_id
    project_name = args.project_name

    main(workflow_id, project_name)

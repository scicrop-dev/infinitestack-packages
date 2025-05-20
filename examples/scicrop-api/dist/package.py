import argparse
import json
from pathlib import Path
from infinitestack import scicrop_api
from infinitestack import orm
from infinitestack import collect
from infinitestack import package_wrapper


def process_response_data(lat, lon):
    return scicrop_api.get_weather_data(lat, lon)


def process_request_data(workflow_id):
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

    json_response = process_response_data(lat, lon)
    request = package_wrapper.build_request("scicrop-api", json_response)
    print(f"request {request}")
    return request


def save_database(lat, lon, database_names, project_name):
    for database in database_names:
        my_orm = orm.Orm(database)
        my_orm.set_project(project_name)
        my_orm.insert_data_json(build_request(lat, lon))


def get_database_names_from_package():
    return package_wrapper.get_database_names_from_package("scicrop-api")


def main(workflow_id, project_name):
    database_names = get_database_names_from_package()
    lat, lon = process_request_data(workflow_id)
    save_database(lat, lon, database_names, project_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow_id', type=str, required=True)
    parser.add_argument('--project_name', type=str, required=True)
    args, _ = parser.parse_known_args()

    workflow_id = args.workflow_id
    project_name = args.project_name

    main(workflow_id, project_name)

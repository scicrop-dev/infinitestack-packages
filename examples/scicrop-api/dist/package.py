import argparse
import json
from pathlib import Path
from infinitestack.scicrop_api import SciCropClient
from infinitestack import orm
from infinitestack import package_wrapper


def process_response_data(data):
    client = SciCropClient()
    return client.call_endpoint("weather-current", data)


def process_request_data(workflow_id):
    file_path = Path(f'/tmp/is/{workflow_id}.json')

    if not file_path.exists():
        print(f'File {file_path} not found')
        exit(1)

    try:
        with open(file_path, 'r') as f:
            geojson = json.load(f)
            features = geojson.get('features', [])

            if not features:
                raise ValueError("No features found in GeoJSON")

            data_list = []
            for feature in features:
                coords = feature.get('geometry', {}).get('coordinates', [])
                if len(coords) != 2:
                    raise ValueError(
                        f"Invalid coordinates in feature: {feature}")

                lon, lat = coords
                data_list.append({'lat': str(lat), 'lon': str(lon)})

            return data_list

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Invalid input format: {e}")
        print(
            "Expected GeoJSON format with features containing Point coordinates"
        )
        exit(1)


def build_request(data):
    json_response = process_response_data(data)
    request = package_wrapper.build_requests("scicrop-api", json_response)
    return request


def save_database(data_list, database_names, project_name):
    for database in database_names:
        my_orm = orm.Orm(database)
        my_orm.set_project(project_name)

        for data in data_list:
            print(
                f"Processing data for lat: {data['lat']}, lon: {data['lon']}")
            request = build_request(data)
            my_orm.insert_data_json(request)


def get_database_names_from_package():
    return package_wrapper.get_database_names_from_package("scicrop-api")


def main(workflow_id, project_name):
    database_names = get_database_names_from_package()
    data_list = process_request_data(workflow_id)
    save_database(data_list, database_names, project_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow_id', type=str, required=True)
    parser.add_argument('--project_name', type=str, required=True)
    args, _ = parser.parse_known_args()

    workflow_id = args.workflow_id
    project_name = args.project_name

    main(workflow_id, project_name)

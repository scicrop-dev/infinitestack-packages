import sys
import argparse
import json
from pathlib import Path
from infinitestack import scicrop_api
from infinitestack import collect


def process_data(lat, lon):
    print("LIVE", scicrop_api.get_weather_data(lat, lon))
    # print("FORECAST", scicrop_api.get_weather_forecast(lat, lon))


def get_database_id_from_package(project_name):
    bridge = collect.Bridge(project_name)
    database_ids = bridge.get_database_ids_from_package("scicrop-api")
    print("database_id's = ", database_ids)
    return database_ids


def main(workflow_id, project_name):
    bridge = collect.Bridge(project_name)
    project_id = bridge.project_id

    database_ids = get_database_id_from_package(project_name)

    file_path = Path(f'/tmp/is/{workflow_id}.json')

    if not file_path.exists():
        print('File not found')
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

    print(f"Parsed lat: {lat}, lon: {lon}")
    process_data(lat, lon)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workflow_id', type=str, required=True)
    parser.add_argument('--project_name', type=str, required=True)
    args, _ = parser.parse_known_args()

    workflow_id = args.workflow_id
    project_name = args.project_name

    main(workflow_id, project_name)

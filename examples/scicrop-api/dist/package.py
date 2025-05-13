import sys
from infinitestack import scicrop_api


def process_data(args):
    lat, long = args[0], args[1]
    print("LIVE ", scicrop_api.get_weather_data(lat, long))
    print("FORECAST ", scicrop_api.get_weather_forecast(lat, long))


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python package.py arg1 arg2 ...")
        sys.exit(1)

    print(f"Received {len(args)} arguments:")
    for i, arg in enumerate(args, start=1):
        print(f"Argument {i}: {arg}")

    process_data(args)


if __name__ == "__main__":
    main()

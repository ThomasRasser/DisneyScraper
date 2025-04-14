import argparse
import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from utils.cache_decorator import file_cache_wrapper_url_fetch, remove_cache_for_url
from utils.constants import (
    DISNEYLAND_LAT,
    DISNEYLAND_LON,
    WEATHER_API_KEY_ENV,
    WEATHER_DATA_PATH,
    WEATHER_URL_HISTORY,
    WEATHER_URL_ONE_CALL,
    clean_path,
)
from utils.save_load import load_json_data, save_json_data

load_dotenv()


# region OpenWeatherMap Functions
@file_cache_wrapper_url_fetch
def fetch_historical_weather_data(
    url: str,
    lat: float,
    lon: float,
    timestamp: int,
) -> dict | None:
    """
    Fetch historical weather data from OpenWeatherMap.
    :param url: URL to use for caching purposes.
    :param lat: Latitude of the location.
    :param lon: Longitude of the location.
    :param timestamp: UNIX timestamp for the time of interest.
    :return: JSON response from the API or None on error.
    """
    print("Fetching historical weather data from OpenWeatherMap...")

    weather_url = WEATHER_URL_ONE_CALL + "?"
    if "lat" not in url:
        weather_url += f"lat={lat}"
    if "lon" not in url:
        weather_url += f"&lon={lon}"
    if "dt" not in url:
        weather_url += f"&dt={timestamp}"
    if "units" not in url:
        weather_url += "&units=metric"
    if "lang" not in url:
        weather_url += "&lang=en"
    if "appid" not in url:
        weather_url += f"&appid={os.getenv(WEATHER_API_KEY_ENV)}"

    print(f"Fetching data from: {weather_url}")
    response = requests.get(weather_url)
    try:
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None


# region OpenWeatherMap Historical City API Functions
@file_cache_wrapper_url_fetch
def fetch_historical_city_weather_data(
    url: str,
    lat: float,
    lon: float,
    start: int,
    end: int | None = None,
    cnt: int | None = None,
) -> dict | None:
    """
    Fetch historical weather data for a city from OpenWeatherMap.
    :param url: URL to use for caching purposes.
    :param lat: Latitude of the location.
    :param lon: Longitude of the location.
    :param start: Start date (UNIX timestamp).
    :param end: End date (UNIX timestamp), optional.
    :param cnt: Count of hourly timestamps, optional.
    :return: JSON response from the API or None on error.
    """
    print("Fetching historical city weather data from OpenWeatherMap...")

    weather_url = "https://history.openweathermap.org/data/2.5/history/city?"
    if "lat" not in url:
        weather_url += f"lat={lat}"
    if "lon" not in url:
        weather_url += f"&lon={lon}"
    if "type" not in url:
        weather_url += "&type=hour"
    if "start" not in url:
        weather_url += f"&start={start}"
    if end and "end" not in url:
        weather_url += f"&end={end}"
    elif cnt and "cnt" not in url:
        weather_url += f"&cnt={cnt}"
    if "appid" not in url:
        weather_url += f"&appid={os.getenv(WEATHER_API_KEY_ENV)}"

    print(f"Fetching data from: {weather_url}")
    response = requests.get(weather_url)
    try:
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None


# endregion


# region Main
def main():
    """
    Main function to fetch and save historical weather data from OpenWeatherMap.
    """
    parser = argparse.ArgumentParser(description="Fetch and save historical weather data.")
    parser.add_argument("--fetch", action="store_true", help="Fetch weather data.")
    parser.add_argument("--hist", action="store_true", help="Fetch weather data.")
    parser.add_argument("--clean", action="store_true", help="Clear cached and saved data.")
    args = parser.parse_args()

    if not args.fetch and not args.clean and not args.hist:
        print("No arguments passed. Use --fetch, --hist or --clean")
        return

    try:
        today_noon = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday_noon = today_noon - timedelta(days=1)
        timestamp = int(yesterday_noon.timestamp())
        cache_url = f"{WEATHER_URL_ONE_CALL}{DISNEYLAND_LAT}{DISNEYLAND_LON}{timestamp}"

        if args.clean:
            if os.path.exists(WEATHER_DATA_PATH):
                os.remove(WEATHER_DATA_PATH)
                print(f"Removed file: {clean_path(WEATHER_DATA_PATH)}")
            remove_cache_for_url(cache_url)
            print(f"Removed cache for query: {cache_url}")

        if args.fetch:
            data = fetch_historical_weather_data(
                url=cache_url, lat=DISNEYLAND_LAT, lon=DISNEYLAND_LON, timestamp=timestamp
            )
            if data:
                save_json_data(data, WEATHER_DATA_PATH)

        if args.hist:
            data = fetch_historical_city_weather_data(
                url=cache_url,
                lat=DISNEYLAND_LAT,
                lon=DISNEYLAND_LON,
                start=int(yesterday_noon.timestamp()),
            )
            if data:
                save_json_data(data, WEATHER_DATA_PATH)

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

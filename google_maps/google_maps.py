import argparse
import os
import sys

import googlemaps
import requests
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.cache_decorator import file_cache_wrapper_url_fetch, remove_cache_for_url
from utils.constants import (
    FINAL_COMBINED_ATTRACTIONS_PATH,
    GM_API_KEY_ENV,
    GM_ATTRACTIONS_PATH,
    GM_GEOCODE_URL,
)
from utils.save_load import load_json_data, save_json_data

load_dotenv()
gmaps = googlemaps.Client(key=os.getenv(GM_API_KEY_ENV))


# region Google Maps API
@file_cache_wrapper_url_fetch
def fetch_long_and_lat_by_place_name(url: str) -> dict | None:
    """
    Fetches the latitude and longitude of a place using Google Maps API.
    :param url: The name of the place to search for.
    :return: A dictionary containing the latitude and longitude of the place.
    """
    print(f"Fetching data from Google Maps API for {url}...")

    place_name = url  # url is used to use the same cache decorator as the other functions
    geocode_result = gmaps.geocode(place_name)
    if geocode_result:
        location = geocode_result[0]["geometry"]["location"]
        print(f"Latitude: {location['lat']}, Longitude: {location['lng']}")
        return {
            "place_name": place_name,
            "latitude": location["lat"],
            "longitude": location["lng"],
        }
    else:
        print("No results found.")
        return None


# endregion


# region Main
def main():
    """
    Main function to fetch and save Disneyland Paris data from Google Maps.
    """
    parser = argparse.ArgumentParser(description="Fetch and parse Disneyland Paris attraction data.")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing parsed data and cached files before running."
    )
    args = parser.parse_args()

    final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)

    first_name = final_attractions[0]["name"]

    PLACE_NAME_PREFIX = "Disneyland Paris, "
    url = PLACE_NAME_PREFIX + first_name

    if args.clean:
        remove_cache_for_url(url)

    data = fetch_long_and_lat_by_place_name(url)
    save_json_data(data, GM_ATTRACTIONS_PATH)
    print(data)


if __name__ == "__main__":
    main()
# endregion

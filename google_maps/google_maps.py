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


def create_all_files_and_merge(clean: bool = False) -> None:
    """
    Does the scraping and creates all files necessary for the final combined data.
    and merges them into the combined data file.

    Expected that the `FINAL_COMBINED_ATTRACTIONS` file exists
    and has been populated with the scraped data.

    :clean: If True, dont use cached data.
    """
    assert os.path.exists(FINAL_COMBINED_ATTRACTIONS_PATH), f"File not found: {FINAL_COMBINED_ATTRACTIONS_PATH}"

    final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)

    if clean:
        os.remove(GM_ATTRACTIONS_PATH)
        print(f"Removed existing file: {GM_ATTRACTIONS_PATH}")
        remove_cache_for_url(GM_GEOCODE_URL)
        print(f"Removed cache for URL: {GM_GEOCODE_URL}")

    PLACE_NAME_PREFIX = "Disneyland Paris, "
    google_attractions = []
    for attraction in final_attractions:
        if "name" in attraction:
            if attraction["name"] == "Pirates' Beach":
                # Special case for Pirates' Beach
                # This is a workaround for the fact that the name is not found in Google Maps
                # but the attraction is still there under the name "La Plage des Pirates"
                name = PLACE_NAME_PREFIX + "La Plage des Pirates"
            else:
                name = PLACE_NAME_PREFIX + attraction["name"]

            gm_data = fetch_long_and_lat_by_place_name(name)
            if gm_data:
                attraction["gm_lat"] = gm_data["latitude"]
                attraction["gm_lon"] = gm_data["longitude"]
                google_attractions.append(gm_data)

        else:
            print("No name found in attraction data: ", attraction)

    save_json_data(google_attractions, GM_ATTRACTIONS_PATH)
    save_json_data(final_attractions, FINAL_COMBINED_ATTRACTIONS_PATH)


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

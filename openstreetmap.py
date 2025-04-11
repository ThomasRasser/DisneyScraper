import argparse
import json
import os
from pathlib import Path

import requests

from cache_decorator import file_cache_wrapper_url_fetch, remove_cache_for_url

# region Constants
OSM_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
DATA = {"data": '[out:json][timeout:60];area["name"="Disneyland Paris"]->.a;(way(area.a););(._;>;);out body;'}
DISNEY_NODES_PATH = "data/disneyland_paris_nodes.json"
# endregion


# region Open StreetMap Functions
@file_cache_wrapper_url_fetch
def fetch_osm_data(url: str, osm_url: str = OSM_URL, headers: dict = HEADERS, data: dict = DATA) -> dict:
    """
    Fetch data from OpenStreetMap for Disneyland Paris.
    :param url: URL to fetch data from. (used for caching)
    :param osm_url: OpenStreetMap API URL.
    :param headers: Headers for the request.
    :param data: Data to send in the request.
    :param cache_dir: Directory to store cached files.
    :return: JSON response from the API.
    """
    print("Fetching data from OpenStreetMap...")

    response = requests.post(osm_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return None


def save_disneyland_data(data, output_file):
    """
    Save the fetched data to a JSON file.
    :param data: Data to save.
    :param output_file: Path to the output file.
    """
    print("Saving data to file...")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {output_file}")


# endregion


# region Main
def main():
    """
    Main function to fetch and save Disneyland Paris data from OpenStreetMap.
    """
    parser = argparse.ArgumentParser(description="Fetch and parse Disneyland Paris attraction data.")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing parsed data and cached files before running."
    )
    args = parser.parse_args()

    try:
        if args.clean and os.path.exists(DISNEY_NODES_PATH):
            os.remove(DISNEY_NODES_PATH)
            print(f"Removed existing file: {DISNEY_NODES_PATH}")
            remove_cache_for_url(OSM_URL, CACHE_DIR)
            print(f"Removed cache for URL: {OSM_URL}")

        # Fetch data from OpenStreetMap
        full_osm_url = f"{OSM_URL}?{DATA['data']}"
        data = fetch_osm_data(full_osm_url)
        if data:
            # Save the data to a JSON file
            save_disneyland_data(data, DISNEY_NODES_PATH)
        else:
            print("No data fetched.")
            return

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    # except Exception as e:
    #     print(f"An error occurred: {e}")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

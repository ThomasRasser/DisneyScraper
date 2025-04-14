import argparse
import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.cache_decorator import file_cache_wrapper_url_fetch, remove_cache_for_url
from utils.constants import (
    QT_DISNEY_STUDIO_DATA_PATH,
    QT_DISNEY_STUDIO_URL,
    QT_DISNEYLAND_DATA_PATH,
    QT_DISNEYLAND_URL,
    QT_HEADERS,
    clean_path,
)
from utils.save_load import save_json_data


# region Queue Times Functions
@file_cache_wrapper_url_fetch
def fetch_queue_times_data(url: str, headers: dict = QT_HEADERS) -> dict | None:
    """
    Fetch attraction data from Queue Times API.
    :param url: URL identifier for caching purposes
    :param api_url: The actual API endpoint to call
    :param headers: Headers for the request
    :return: JSON response from the API
    """
    print("Fetching data from Queue Times")

    response = requests.get(url, headers=headers)
    try:
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: {response.status_code}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def get_rides_dict(qt_response: dict) -> dict:
    """
    Extract rides information from the Queue Times API response.
    :param qt_response: The response from the Queue Times API
    :return: A dictionary containing rides information
    """
    lands = qt_response.get("lands", [])
    rides = {}

    for land in lands:
        rides_list = land.get("rides", [])
        for ride in rides_list:
            ride_id = ride.get("id")
            ride_name = ride.get("name")
            wait_time = ride.get("wait_time")
            is_open = ride.get("is_open")
            last_updated = ride.get("last_updated")

            rides[ride_name] = {
                "id": ride_id,
                "wait_time": wait_time,
                "is_open": is_open,
                "last_updated": last_updated,
                "land": land.get("name"),
            }

    return rides


# endregion


# Main
def main():
    """
    Main function to fetch and save Disneyland attraction data from Queue Times API.
    """
    parser = argparse.ArgumentParser(description="Fetch and parse Disneyland attraction data from Queue Times API.")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing parsed data and cached files before running."
    )
    args = parser.parse_args()

    try:
        # Clean existing files and caches if requested
        if args.clean:
            # Remove existing output files
            if QT_DISNEYLAND_DATA_PATH.exists():
                os.remove(QT_DISNEYLAND_DATA_PATH)
                print(f"Removed existing file: {clean_path(QT_DISNEYLAND_DATA_PATH)}")

            if QT_DISNEY_STUDIO_DATA_PATH.exists():
                os.remove(QT_DISNEY_STUDIO_DATA_PATH)
                print(f"Removed existing file: {clean_path(QT_DISNEY_STUDIO_DATA_PATH)}")

            # Remove caches
            remove_cache_for_url(QT_DISNEYLAND_URL)
            remove_cache_for_url(QT_DISNEY_STUDIO_URL)
            print("Removed all Queue Times API caches")

        disneyland_data = fetch_queue_times_data(QT_DISNEYLAND_URL)
        save_json_data(disneyland_data, QT_DISNEYLAND_DATA_PATH)

        disney_studio_data = fetch_queue_times_data(QT_DISNEY_STUDIO_URL)
        save_json_data(disney_studio_data, QT_DISNEY_STUDIO_DATA_PATH)

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    # except Exception as e:
    #     print(f"Error: {str(e)}")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

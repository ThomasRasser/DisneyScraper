import argparse
import os
import sys

import requests

from utils.utils import levenstein_distance_case_insensitive, matching_words_count

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.cache_decorator import file_cache_wrapper_url_fetch, remove_cache_for_url
from utils.constants import (
    FINAL_COMBINED_ATTRACTIONS_PATH,
    QT_DISNEY_STUDIO_DATA_PATH,
    QT_DISNEY_STUDIO_URL,
    QT_DISNEYLAND_DATA_PATH,
    QT_DISNEYLAND_URL,
    QT_HEADERS,
    clean_path,
)
from utils.save_load import load_json_data, save_json_data


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


def add_qt_to_final_ride_combination(qt_rides: dict, final_attractions: list) -> None:
    """
    Find the overlap between Queue Times rides and scraped Disneyland attractions.
    Use scraped attractions as ground truth -> if a ride is not found in the scraped data,
    it is not a ride and can be ignored.
    :param qt_rides: Dictionary of rides from Queue Times.
    :param attractions: List of attractions from Disneyland.
    :return: List of overlapping rides.
    """
    print("Finding overlap between Queue Times and Disneyland attractions")

    overlapping_ride_names = []
    not_overlapping_ride_names = []

    scrape_attraction_names = set()
    for attraction in final_attractions:
        if "name" in attraction:
            scrape_attraction_names.add(attraction["name"])

    qt_attraction_names = set(qt_rides.keys())

    for final_attraction in final_attractions:
        if final_attraction["name"] in qt_attraction_names:
            final_attraction["qt_id"] = qt_rides[final_attraction["name"]]["id"]
            final_attraction["qt_name"] = final_attraction["name"]
            overlapping_ride_names.append(final_attraction["name"])
        else:
            not_overlapping_ride_names.append(final_attraction["name"])

    print(f"Found {len(overlapping_ride_names)} overlapping rides.")
    print(f"Found {len(not_overlapping_ride_names)} not overlapping rides.")
    print(f"Not overlapping rides: {not_overlapping_ride_names}")
    print("--------------------")

    # Try to find the best match for the not overlapping rides
    # via levenstein distance
    for not_overlapping_scrape_name in not_overlapping_ride_names:
        best_match = None
        best_distance = float("inf")
        for qt_name in qt_attraction_names:
            distance = levenstein_distance_case_insensitive(not_overlapping_scrape_name, qt_name)
            if distance < best_distance:
                best_match = qt_name
                best_distance = distance

        if best_match:
            print(f"Best match for '{not_overlapping_scrape_name}' is '{best_match}' with distance {best_distance}.")
            if best_distance < 3:
                final_attraction = next(
                    (a for a in final_attractions if a["name"] == not_overlapping_scrape_name), None
                )
                if final_attraction:
                    final_attraction["qt_id"] = qt_rides[best_match]["id"]
                    final_attraction["qt_name"] = best_match
                    print(f"Added '{best_match}' to final attractions.")

                overlapping_ride_names.append(best_match)
                not_overlapping_ride_names.remove(not_overlapping_scrape_name)
                print(f"Added '{best_match}' to overlapping rides.")
    print("--------------------")

    # Try to find the best match for the not overlapping rides
    # via matching words count
    for not_overlapping_scrape_name in not_overlapping_ride_names:
        best_match = None
        best_count = 0
        for qt_name in qt_attraction_names:
            count = matching_words_count(not_overlapping_scrape_name, qt_name)
            if count > best_count:
                best_match = qt_name
                best_count = count

        if best_match:
            print(f"Best match for '{not_overlapping_scrape_name}' is '{best_match}' with {best_count} words.")
        else:
            print(f"No match found for '{not_overlapping_scrape_name}'.")

    # NOTE:
    # We dont have queue times data for the attractions:
    # - 'La Galerie de la Belle au Bois Dormant'
    # - 'Liberty Arcade'.
    # - 'Discovery Arcade'.
    # - 'Horse-Drawn Streetcars'.
    # - 'Sleeping Beauty Castle'.
    # But as far as I can tell, they are not rides, so we can ignore them.

    # Save the combined data
    save_json_data(final_attractions, FINAL_COMBINED_ATTRACTIONS_PATH)


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

    # Merge the data
    add_qt_to_final_ride_combination(
        get_rides_dict(disneyland_data),
        final_attractions,
    )


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

import argparse
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from google_maps.google_maps import fetch_long_and_lat_by_place_name
from queue_times.queue_times import get_rides_dict
from utils.constants import (
    COMBINED_ATTRACTION_DATA_PATH,
    COMBINED_ATTRACTIONS_QT_PATH,
    COMBINED_DINING_DATA_PATH,
    FINAL_COMBINED_ATTRACTIONS_PATH,
    FINAL_COMBINED_DINING_PATH,
    OSM_ATTRACTION_DISTANCES_PATH,
    PARSED_ATTRACTIONS_PATH,
    QT_DISNEY_STUDIO_DATA_PATH,
    QT_DISNEYLAND_DATA_PATH,
    QT_RIDES_DICT_PATH,
    clean_path,
)
from utils.save_load import (
    load_json_data,
    load_json_data_cached,
    load_osm_data,
    save_json_data,
)
from utils.utils import (
    levenstein_distance_case_insensitive,
    matching_words_count,
)


def combine_scraped_disneyland_and_google_maps_data(final_attractions: list) -> None:
    """
    Combine the scraped Disneyland attractions data with Google Maps data.
    :param final_attractions: List of attractions from Disneyland.
    :return: List of combined attractions data.
    """
    print("Combining scraped Disneyland attractions with Google Maps data")

    PLACE_NAME_PREFIX = "Disneyland Paris, "
    for attraction in final_attractions:
        if "name" in attraction:
            name = PLACE_NAME_PREFIX + attraction["name"]
            if "presented" in name:
                name = name.split("presented")[0].strip()

            gm_data = fetch_long_and_lat_by_place_name(name)
            if gm_data:
                attraction["gm_lat"] = gm_data["latitude"]
                attraction["gm_lon"] = gm_data["longitude"]

    save_json_data(final_attractions, FINAL_COMBINED_ATTRACTIONS_PATH)


def combine_scraped_disneyland_and_osm_data(final_attractions: list) -> None:
    """
    Combine the scraped Disneyland attractions data with OSM data.
    :param final_attractions: List of attractions from Disneyland.
    :return: List of combined attractions data.
    """
    print("Combining scraped Disneyland attractions with OSM data")

    osm_data = load_json_data(OSM_ATTRACTION_DISTANCES_PATH)

    for attraction in final_attractions:
        if "name" in attraction:
            name = attraction["name"]
            osm_data_entry = next((entry for entry in osm_data if entry["name"] == name), None)
            if osm_data_entry:
                attraction["osm_lat"] = osm_data_entry["gm_lat"]
                attraction["osm_lon"] = osm_data_entry["gm_lon"]
                attraction["osm_node_id"] = osm_data_entry["closest_node"]["id"]
            else:
                print(f"No OSM data found for {name}")

    save_json_data(final_attractions, FINAL_COMBINED_ATTRACTIONS_PATH)


def generate_combined_ride_data_from_scraping(scraped_attractions: list, overwrite: bool = False) -> None:
    """
    Generate combined ride data from scraping.
    :param attractions: List of attractions from Disneyland.
    :return: List of combined ride data.
    """
    # Rides must contain:
    # - scrape_name
    # - scrape_duration
    # - scrape_description
    # - scrape_max_height_cm
    # - scrape_min_height_cm
    # - scrape_min_age
    # - scrape_accessibility_tags
    # - scrape_keywords
    # - scrape_detail_url
    # - scrape_image_url

    # - osm_tags
    # - osm_node_id
    # - osm_lat
    # - osm_lon

    # - gm_lat
    # - gm_lon

    # - qt_id
    # - qt_name
    # - qt_is_open

    print("Generating combined ride data from scraping")

    if os.path.exists(FINAL_COMBINED_ATTRACTIONS_PATH) and not overwrite:
        print(f"Combined ride data already exists at {clean_path(FINAL_COMBINED_ATTRACTIONS_PATH)}.")
        return

    combined_ride_data = []
    for attraction in scraped_attractions:
        ride_data = {}
        # Scraped data
        ride_data["name"] = attraction.get("title", "")
        ride_data["is_open"] = False  # Will be updated via Queue Times API
        ride_data["duration"] = None  # Must be updated via scraping
        ride_data["description"] = ""  # Must be updated via scraping
        ride_data["max_height_cm"] = None  # Must be updated via scraping
        min_height = attraction.get("min_height_cm", None)
        ride_data["min_height_cm"] = int(float((min_height))) if min_height is not None else None

        ride_data["min_age"] = None  # Must be updated via scraping
        ride_data["accessibility_tags"] = []  # Must be updated via scraping
        ride_data["keywords"] = attraction.get("keywords", [])
        ride_data["detail_url"] = attraction.get("link", None)
        ride_data["image_url"] = attraction.get("image", None)
        # OSM data
        ride_data["osm_tags"] = attraction.get("osm_tags", [])
        ride_data["osm_node_id"] = attraction.get("osm_id", None)
        ride_data["osm_lat"] = attraction.get("lat", None)
        ride_data["osm_lon"] = attraction.get("lon", None)
        # Google Maps data
        ride_data["gm_lat"] = attraction.get("gm_lat", None)
        ride_data["gm_lon"] = attraction.get("gm_lon", None)
        # Queue Times data
        ride_data["qt_id"] = attraction.get("qt_id", None)
        ride_data["qt_name"] = attraction.get("qt_name", None)

        # Add ride data to combined data
        combined_ride_data.append(ride_data)

    save_json_data(combined_ride_data, FINAL_COMBINED_ATTRACTIONS_PATH)
    print(f"Combined ride data saved to {clean_path(FINAL_COMBINED_ATTRACTIONS_PATH)}.")


# region Main
def main():
    """
    Main function to fetch and parse attraction data from Disneyland Paris.
    """

    parser = argparse.ArgumentParser(description="Combine Disneyland Paris attraction data with OSM data.")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing parsed data and cached files before running."
    )
    parser.add_argument("--osm", action="store_true", help="Combine attractions with OSM data.")
    parser.add_argument("--qt", action="store_true", help="Combine attractions with Queue Times data.")
    parser.add_argument("--gm", action="store_true", help="Combine attractions with Google Maps data.")
    parser.add_argument("--gen", action="store_true", help="Generate combined ride data from scraping.")
    args = parser.parse_args()

    try:
        if args.clean and args.gen:
            if os.path.exists(FINAL_COMBINED_ATTRACTIONS_PATH):
                os.remove(FINAL_COMBINED_ATTRACTIONS_PATH)
                print(f"Removed existing file: {clean_path(FINAL_COMBINED_ATTRACTIONS_PATH)}")

        if args.gen:
            scraped_attraction_data = load_json_data(PARSED_ATTRACTIONS_PATH)
            if not scraped_attraction_data:
                print(f"No data found in {clean_path(PARSED_ATTRACTIONS_PATH)}.")
                return

            generate_combined_ride_data_from_scraping(scraped_attraction_data, overwrite=args.clean)

        # ==============================================

        if args.clean and args.qt:
            if os.path.exists(COMBINED_ATTRACTIONS_QT_PATH):
                os.remove(COMBINED_ATTRACTIONS_QT_PATH)

        if args.qt:
            final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)
            qt_disney_land_data = load_json_data(QT_DISNEYLAND_DATA_PATH)
            qt_disney_studio_data = load_json_data(QT_DISNEY_STUDIO_DATA_PATH)

            qt_land_rides = get_rides_dict(qt_disney_land_data)
            qt_studio_rides = get_rides_dict(qt_disney_studio_data)

            qt_rides = {**qt_land_rides, **qt_studio_rides}
            print(f"Loaded {len(qt_rides)} rides from Queue Times data.")
            save_json_data(qt_rides, QT_RIDES_DICT_PATH)

            add_qt_to_final_ride_combination(qt_rides, final_attractions)

        # ==============================================

        if args.gm:
            final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)
            combine_scraped_disneyland_and_google_maps_data(final_attractions)

        # ==============================================

        if args.osm:
            final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)
            combine_scraped_disneyland_and_osm_data(final_attractions)

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    # except Exception as e:
    #     print(f"An error occurred: {e}")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

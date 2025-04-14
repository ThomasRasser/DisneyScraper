import argparse
import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.cache_decorator import (
    file_cache_wrapper_url_fetch,
    remove_cache_for_url,
)
from utils.constants import (
    FINAL_COMBINED_ATTRACTIONS_PATH,
    FINAL_COMBINED_DINING_PATH,
    GM_ATTRACTIONS_PATH,
    OSM_ATTRACTION_DISTANCES_PATH,
    OSM_DATA,
    OSM_DISNEY_NODES_PATH,
    OSM_HEADERS,
    OSM_URL,
    clean_path,
)
from utils.save_load import (
    load_json_data,
    load_osm_data,
    save_json_data,
)
from utils.utils import calculate_coordinate_distance_cm


# region Open StreetMap Functions
@file_cache_wrapper_url_fetch
def fetch_osm_data(url: str, osm_url: str = OSM_URL, headers: dict = OSM_HEADERS, data: dict = OSM_DATA) -> dict | None:
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
        osm_data = response.json()
        osm_nodes = osm_data.get("elements", [])
        return osm_nodes
    else:
        print(f"Error fetching data: {response.status_code}")
        return None


def find_closest_node(latitude: float, longitude: float, nodes: list) -> dict | None:
    """
    Find the closest node to the given latitude and longitude.
    :param latitude: Latitude of the point.
    :param longitude: Longitude of the point.
    :param nodes: List of nodes to search.
    :return: The closest node to the given coordinates.
    """
    closest_node = None
    min_distance = float("inf")

    for node in nodes:
        if "lat" not in node or "lon" not in node:
            continue

        node_lat = node["lat"]
        node_lon = node["lon"]
        distance = calculate_coordinate_distance_cm(latitude, longitude, node_lat, node_lon)
        if distance < min_distance:
            min_distance = distance
            closest_node = node

    return closest_node


def create_all_files_and_merge(clean: bool = False) -> None:
    """
    Does the scraping and creates all files necessary for the final combined data.
    and merges them into the combined data file.

    Expected that the `FINAL_COMBINED_ATTRACTIONS` file exists
    and has been populated with the scraped data.

    :clean: If True, dont use cached data.
    """
    assert os.path.exists(FINAL_COMBINED_ATTRACTIONS_PATH), f"File not found: {FINAL_COMBINED_ATTRACTIONS_PATH}"

    # Fetch osm data
    full_osm_url = f"{OSM_URL}?{OSM_DATA['data']}"
    if clean:
        if os.path.exists(OSM_DISNEY_NODES_PATH):
            os.remove(OSM_DISNEY_NODES_PATH)
        print(f"Removed existing file: {clean_path(OSM_DISNEY_NODES_PATH)}")

        remove_cache_for_url(full_osm_url)
        print(f"Removed cache for URL: {OSM_URL}")

    osm_data = fetch_osm_data(full_osm_url)
    osm_nodes = osm_data.get("elements", [])
    save_json_data(osm_data, OSM_DISNEY_NODES_PATH)

    # The data can only be merged, once the google maps data is available
    print("Merging data OSM data based on Google Maps data...")
    changes = 0
    final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)
    for attraction in final_attractions:
        latitude = attraction.get("gm_lat", None)
        longitude = attraction.get("gm_lon", None)
        if latitude is None or longitude is None:
            print("No latitude or longitude found in attraction data: ", attraction)
            continue

        closest_node = find_closest_node(latitude, longitude, osm_nodes)
        if closest_node is None:
            print(f"No closest node found for {attraction['name']}.")
            continue

        attraction["osm_node_id"] = closest_node.get("id", None)
        attraction["osm_lat"] = closest_node.get("lat", None)
        attraction["osm_lon"] = closest_node.get("lon", None)
        changes += 1

    # Save the merged data
    if changes == 0:
        print("No changes made to the attractions data.")
        return

    save_json_data(final_attractions, FINAL_COMBINED_ATTRACTIONS_PATH)


# endregion


# region Main
def main():
    """
    Main function to fetch and save Disneyland Paris data from OpenStreetMap.
    """
    parser = argparse.ArgumentParser(description="Fetch and parse Disneyland Paris attraction data.")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing parsed data and cached files before running.",
    )
    parser.add_argument(
        "--close",
        action="store_true",
        help="Find the closest node to the given coordinates.",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch data from OpenStreetMap.",
    )
    args = parser.parse_args()

    try:
        if args.fetch:
            create_all_files_and_merge(clean=args.clean)
            print("Disneyland Paris data scraping completed successfully.")

        if args.close:
            osm_nodes = load_osm_data()
            final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)

            attraction_distances = []

            for attraction in final_attractions:
                latitude = attraction["gm_lat"]
                longitude = attraction["gm_lon"]

                closest_node = find_closest_node(latitude, longitude, osm_nodes)
                distance_in_cm = calculate_coordinate_distance_cm(
                    latitude, longitude, closest_node["lat"], closest_node["lon"]
                )
                attraction_distances.append(
                    {
                        "name": attraction["name"],
                        "closest_node": closest_node,
                        "distance_in_cm": distance_in_cm,
                        "gm_lat": latitude,
                        "gm_lon": longitude,
                    }
                )

            attraction_distances.sort(key=lambda x: x["distance_in_cm"], reverse=True)
            print("10 worst attractions:")
            for attraction in attraction_distances[:10]:
                print(f"{attraction['name']}: {attraction['distance_in_cm']} cm")

            save_json_data(
                attraction_distances,
                OSM_ATTRACTION_DISTANCES_PATH,
            )

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

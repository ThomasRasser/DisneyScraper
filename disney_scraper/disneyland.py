import argparse
import json
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disney_scraper.parser import (
    parse_disneyland_attraction_details,
    parse_disneyland_attraction_lists,
    parse_disneyland_dining_lists,
)
from utils.cache_decorator import remove_complete_cache
from utils.constants import (
    DISNEY_ATTRACTIONS_URL,
    DISNEY_DINING_URL,
    FINAL_COMBINED_ATTRACTIONS_PATH,
    PARSED_ATTRACTIONS_DETAIL_PATH,
    PARSED_ATTRACTIONS_PATH,
    PARSED_DINING_PATH,
    clean_path,
)
from utils.save_load import load_json_data, save_json_data
from utils.scraper import extract_human_text_from_html, get_html_multiple_cached, get_html_single_cached


# region Scraping Functions
def scrape_disneyland_attraction_lists() -> list:
    """
    Scrape Disneyland Paris attraction data and save it to a JSON file.
    :return: List of parsed attractions.
    """
    print("Starting Disneyland Paris attraction data scraping...")

    # Fetch the HTML content
    html_content = get_html_single_cached(DISNEY_ATTRACTIONS_URL)
    if not html_content:
        print("Failed to fetch HTML content.")
        return []
    print("Fetched HTML content.")

    # Parse the HTML content and extract attraction data
    attractions = parse_disneyland_attraction_lists(html_content)

    # Save the data to a JSON file
    save_json_data(attractions, PARSED_ATTRACTIONS_PATH)

    return attractions


def scrape_disneyland_dining_lists() -> list:
    """
    Scrape Disneyland Paris dining data and save it to a JSON file.
    :return: List of parsed dining options.
    """
    print("Starting Disneyland Paris dining data scraping...")

    # Fetch the HTML content
    html_content = get_html_single_cached(DISNEY_DINING_URL)
    if not html_content:
        print("Failed to fetch HTML content.")
        return []
    print("Fetched HTML content.")

    # Parse the HTML content and extract dining data
    dining = parse_disneyland_dining_lists(html_content)

    # Save the data to a JSON file
    save_json_data(dining, PARSED_DINING_PATH)

    return dining


def fetch_disneyland_attractions_details(attractions: list[dict]) -> list:
    """
    Fetch detailed information about Disneyland Paris attractions,
    by visiting each attraction's page.
    :return: List of detailed attractions.
    """
    print("Starting Disneyland Paris attraction details scraping...")

    # Fetch details for each attraction
    attraction_detail_urls = [attraction["link"] for attraction in attractions]
    attraction_detail_names = [attraction["title"] for attraction in attractions]
    attractions_detailed_dict = get_html_multiple_cached(attraction_detail_urls)
    attractions_detailed_html = attractions_detailed_dict.values()

    # Parse the HTML content by extracting the human-readable text
    attractions_detailed_lst = []
    for name, url, html in zip(attraction_detail_names, attraction_detail_urls, attractions_detailed_html):
        if html:
            text = extract_human_text_from_html(html)
            new_attraction = {
                "name": name,
                "url": url,
                "text": text,
            }
            attractions_detailed_lst.append(new_attraction)
        else:
            print(f"Failed to fetch HTML content for {url}")

    # Save the detailed data to a JSON file
    save_json_data(attractions_detailed_lst, PARSED_ATTRACTIONS_DETAIL_PATH)

    return attractions_detailed_lst


# endregion


# region Merging Functions
def generate_final_ride_data_file_from_scraping(scraped_attractions: list, overwrite: bool = False) -> None:
    """
    Generate combined ride data from scraping.
    :param attractions: List of attractions from Disneyland.
    :return: List of combined ride data.
    """
    # Rides must contain:
    # - name (most likely the same as in the scrape_name)

    # - scrape_name
    # - scrape_duration
    # - scrape_description
    # - scrape_max_height_cm
    # - scrape_min_height_cm
    # - scrape_accessibility_tags
    # - scrape_services_tags: [str],
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
        # Basic data
        ride_data["name"] = attraction.get("title", "")
        if ride_data["name"] and ", presented by" in ride_data["name"]:
            ride_data["name"] = ride_data["name"].split(", presented by")[0].strip()
        # Scraped data
        ride_data["scrape_name"] = attraction.get("title", "")
        ride_data["scrape_description"] = ""  # Must be updated via scraping
        ride_data["scrape_max_height_cm"] = None  # Must be updated via scraping
        min_height = attraction.get("min_height_cm", None)
        ride_data["scrape_min_height_cm"] = int(float((min_height))) if min_height is not None else None
        ride_data["scrape_min_age"] = None  # Must be updated via scraping
        ride_data["scrape_accessibility_tags"] = []  # Must be updated via scraping
        ride_data["scrape_services_tags"] = []  # Must be updated via scraping
        ride_data["scrape_keywords"] = attraction.get("keywords", [])
        ride_data["scrape_detail_url"] = attraction.get("link", None)
        ride_data["scrape_image_url"] = attraction.get("image", None)
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
        ride_data["qt_is_open"] = False  # Will be updated live and is therefore not needed here
        # Touruing Plans data
        ride_data["tp_duration"] = None  # Must be updated via scraping

        # Add ride data to combined data
        combined_ride_data.append(ride_data)

    save_json_data(combined_ride_data, FINAL_COMBINED_ATTRACTIONS_PATH)
    print(f"Combined ride data saved to {clean_path(FINAL_COMBINED_ATTRACTIONS_PATH)}.")


def create_all_files_and_merge(clean: bool = False) -> None:
    """
    Does the scraping and creates all files necessary for the final combined data.
    and merges them into the combined data file.

    Since the scraped data from the website is the ground truth,
    the initial FINAL_COMBINED_ATTRACTIONS file will be created here.

    all following create_all_files_and_merge in different files,
    are building upon this file: FINAL_COMBINED_ATTRACTIONS_PATH
    """
    if clean and os.path.exists(PARSED_ATTRACTIONS_PATH):
        os.remove(PARSED_ATTRACTIONS_PATH)
        print(f"Removed existing file: {PARSED_ATTRACTIONS_PATH}")
        remove_complete_cache()

    # Scrape and parse data
    scraped_attractions = scrape_disneyland_attraction_lists()
    scraped_dining = scrape_disneyland_dining_lists()

    # Merge data
    print("Merging data...")

    if clean or not os.path.exists(FINAL_COMBINED_ATTRACTIONS_PATH):
        print("Creating initial combined attractions file...")
        generate_final_ride_data_file_from_scraping(scraped_attractions, overwrite=True)

    if not clean and os.path.exists(FINAL_COMBINED_ATTRACTIONS_PATH):
        print(f"Final combined attractions file already exists: {clean_path(FINAL_COMBINED_ATTRACTIONS_PATH)}")
        print("Overwrite? (y/n): ", end="")
        choice = input().strip().lower()
        if choice == "y":
            print("Removing existing file...")
            os.remove(FINAL_COMBINED_ATTRACTIONS_PATH)

            print("Creating initial combined attractions file...")
            generate_final_ride_data_file_from_scraping(scraped_attractions, overwrite=True)
        else:
            print("Keeping existing file.")

    # Fetch detailed information about attractions
    attractions_detailed = fetch_disneyland_attractions_details(scraped_attractions)
    if not attractions_detailed:
        print("Failed to fetch detailed attraction data.")
        return
    print("Fetched detailed attraction data.")


# endregion


# region Main
def main():
    """
    Main function to fetch and parse attraction data from Disneyland Paris.
    """

    parser = argparse.ArgumentParser(description="Fetch and parse Disneyland Paris attraction data.")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing parsed data and cached files before running."
    )
    args = parser.parse_args()

    try:
        create_all_files_and_merge(clean=args.clean)

        print("Disneyland Paris data scraping completed successfully.")

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

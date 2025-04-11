import argparse
import json
import os
import sys
import time

from cache_decorator import remove_cache
from parser import parse_disneyland_attraction_details, parse_disneyland_attraction_lists, parse_disneyland_dining_lists
from scraper import get_html_multiple_cached, get_html_single_cached

# region  Constants
THOMAS_RASSER_URL = "https://rasser.derthomas.at/Autohaus/index.html"
DISNEY_ATTRACTIONS_URL = "https://www.disneylandparis.com/en-gb/attractions/"
PARSED_ATTRACTIONS_PATH = "data/parsed_attractions.json"
DISNEY_DINING_URL = "https://www.disneylandparis.com/en-gb/dining/"
PARSED_DINING_PATH = "data/parsed_dining.json"
# endregion


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
        return
    print("Fetched HTML content.")

    # Parse the HTML content and extract attraction data
    attractions = parse_disneyland_attraction_lists(html_content)

    # Save the data to a JSON file
    os.makedirs(os.path.dirname(PARSED_ATTRACTIONS_PATH), exist_ok=True)
    with open(PARSED_ATTRACTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(attractions, f, ensure_ascii=False, indent=4)
    print(f"Parsed data saved to {PARSED_ATTRACTIONS_PATH}.")

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
        return
    print("Fetched HTML content.")

    # Parse the HTML content and extract dining data
    dining = parse_disneyland_dining_lists(html_content)

    # Save the data to a JSON file
    os.makedirs(os.path.dirname(PARSED_DINING_PATH), exist_ok=True)
    with open(PARSED_DINING_PATH, "w", encoding="utf-8") as f:
        json.dump(dining, f, ensure_ascii=False, indent=4)
    print(f"Parsed data saved to {PARSED_DINING_PATH}.")

    return dining


def scrape_disneyland_attractions_details() -> list:
    """
    Scrape detailed information about Disneyland Paris attractions,
    by visiting each attraction's page.
    :return: List of detailed attractions.
    """
    print("Starting Disneyland Paris attraction details scraping...")

    # Load the parsed attractions data
    if not os.path.exists(PARSED_ATTRACTIONS_PATH):
        print(f"Parsed attractions file not found: {PARSED_ATTRACTIONS_PATH}")
        return []

    with open(PARSED_ATTRACTIONS_PATH, "r", encoding="utf-8") as f:
        attractions = json.load(f)

    # Fetch details for each attraction
    attraction_urls = [attraction["link"] for attraction in attractions]
    attractions_detailed_dict = get_html_multiple_cached(attraction_urls)

    # Parse attractions
    attractions_detailed_lst = []
    for attraction_url in attraction_urls:
        if attraction_url in attractions_detailed_dict:
            parsed_attraction = parse_disneyland_attraction_details(attractions_detailed_dict[attraction_url])
            attractions_detailed_lst.append(parsed_attraction)
        else:
            print(f"Failed to fetch details for {attraction_url}")

    # Save the detailed data to a JSON file
    detailed_attractions_path = PARSED_ATTRACTIONS_PATH.replace(".json", "_details.json")
    with open(detailed_attractions_path, "w", encoding="utf-8") as f:
        json.dump(attractions_detailed_lst, f, ensure_ascii=False, indent=4)
    print(f"Detailed data saved to {detailed_attractions_path}.")


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
        if args.clean and os.path.exists(PARSED_ATTRACTIONS_PATH):
            os.remove(PARSED_ATTRACTIONS_PATH)
            print(f"Removed existing file: {PARSED_ATTRACTIONS_PATH}")
            remove_cache()

        scrape_disneyland_attraction_lists()
        scrape_disneyland_dining_lists()
        # scrape_disneyland_attractions_details()

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

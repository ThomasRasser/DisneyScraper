import argparse
import json
import os
import sys
import time

from cache_decorator import remove_cache
from parser import parse_disneyland_attraction_lists
from scraper import BrowserPool, get_html_multiple, get_html_single, get_html_single_cached

# region  Constants
THOMAS_RASSER_URL = "https://rasser.derthomas.at/Autohaus/index.html"
DISNEY_ATTRACTIONS_URL = "https://www.disneylandparis.com/en-gb/attractions/"
PARSED_ATTRACTIONS_PATH = "data/parsed_attractions.json"
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

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

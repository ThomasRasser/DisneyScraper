import os
import sys

from disney_scraper.disneyland import create_all_files_and_merge as merge_scrape
from disney_scraper.open_api import create_all_files_and_merge as merge_open_api
from google_maps.google_maps import create_all_files_and_merge as merge_google_maps
from osm.openstreetmap import create_all_files_and_merge as merge_osm
from queue_times.queue_times import create_all_files_and_merge as merge_queue


def main():
    """
    Main function to fetch and parse attraction data from Disneyland Paris.
    """
    print("Starting data scraping and merging...")

    merge_scrape(clean=False)
    # merge_open_api(clean=False)

    merge_google_maps(clean=False)
    merge_osm(clean=False)

    merge_queue(clean=False)

    print("Data scraping and merging completed.")


if __name__ == "__main__":
    main()

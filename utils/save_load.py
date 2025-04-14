import json
import os
from functools import lru_cache

from utils.constants import (
    OSM_DISNEY_NODES_PATH,
    clean_path,
)

# region Loading data


def load_json_data(file_path: str) -> dict:
    """
    Load JSON data from a file.
    :param file_path: Path to the JSON file.
    :return: Parsed JSON data.
    """
    print(f"Loading JSON data from {clean_path(file_path)}")

    if not os.path.exists(file_path):
        print(f"File not found: {clean_path(file_path)}")
        return {}

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


@lru_cache(maxsize=128)
def load_json_data_cached(file_path: str) -> dict:
    return load_json_data(file_path)


def load_osm_data() -> list:
    """
    Load the OpenStreetMap data from the JSON file.
    :return: OSM data as a list of elements.
    """
    print(f"Loading OSM data from {clean_path(OSM_DISNEY_NODES_PATH)}")
    osm_data = load_json_data_cached(OSM_DISNEY_NODES_PATH)

    if not osm_data:
        print("No elements found in OSM data.")
        return []

    if "elements" in osm_data:
        osm_data = osm_data["elements"]
    else:
        print("No elements found in OSM data.")
        return []

    return osm_data


# endregion


# region Saving data
def save_json_data(data, output_file: str) -> None:
    """
    Save the data to a JSON file.
    :param data: Data to save.
    :param output_file: Path to the output file.
    """
    if not data:
        print(f"Nothing to save for {clean_path(output_file)}")
        return

    print(f"Saving data to {clean_path(output_file)}")

    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data saved to {clean_path(output_file)}")


# endregion

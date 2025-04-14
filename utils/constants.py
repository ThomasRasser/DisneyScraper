from pathlib import Path

# Root Directory
ROOT_DIR = "/home/thomas/desktop/tu/10_Semester/7_Advanced_Software_Engineering_ASE/2_Webscraper/1_Disney_Scraper"

# Scrapgin Disneyland Paris
THOMAS_RASSER_URL = "https://rasser.derthomas.at/Autohaus/index.html"
DISNEY_ATTRACTIONS_URL = "https://www.disneylandparis.com/en-gb/attractions/"
PARSED_ATTRACTIONS_PATH = Path(ROOT_DIR) / "data" / "parsed_attractions.json"
DISNEY_DINING_URL = "https://www.disneylandparis.com/en-gb/dining/"
PARSED_DINING_PATH = Path(ROOT_DIR) / "data" / "parsed_dining.json"

# OpenStreetMap (OSM)
OSM_URL = "https://overpass-api.de/api/interpreter"
OSM_HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}
OSM_DATA = {"data": '[out:json][timeout:60];area["name"="Disneyland Paris"]->.a;(way(area.a););(._;>;);out body;'}
DISNEY_NODES_PATH = Path(ROOT_DIR) / "data" / "osm_disneyland_paris_nodes.json"
OSM_ATTRACTION_DISTANCES_PATH = Path(ROOT_DIR) / "data" / "osm_disneyland_paris_attraction_distances.json"

# Queue Times (QT)
QT_DISNEY_STUDIO_URL = "https://queue-times.com/parks/28/queue_times.json"
QT_DISNEYLAND_URL = "https://queue-times.com/parks/4/queue_times.json"
QT_HEADERS = {"Content-Type": "application/json"}
QT_DISNEYLAND_DATA_PATH = Path(ROOT_DIR) / "data" / "queue_times_disneyland.json"
QT_DISNEY_STUDIO_DATA_PATH = Path(ROOT_DIR) / "data" / "queue_times_disney_studio.json"

# Combined Data
COMBINED_ATTRACTION_DATA_PATH = Path(ROOT_DIR) / "data" / "combined_attractions_data.json"
COMBINED_DINING_DATA_PATH = Path(ROOT_DIR) / "data" / "combined_dining_data.json"

COMBINED_ATTRACTIONS_QT_PATH = Path(ROOT_DIR) / "data" / "combined_attractions_qt.json"
COMBINED_ATTRACTIONS_OSM_PATH = Path(ROOT_DIR) / "data" / "combined_attractions_osm.json"

QT_RIDES_DICT_PATH = Path(ROOT_DIR) / "data" / "qt_rides_dict.json"

FINAL_COMBINED_ATTRACTIONS_PATH = Path(ROOT_DIR) / "data" / "final_combined_attractions.json"
FINAL_COMBINED_DINING_PATH = Path(ROOT_DIR) / "data" / "final_combined_dining.json"

# Nodes
NODE_ISLAND_PATH = Path(ROOT_DIR) / "data" / "node_islands.json"
BIGGEST_ISLAND_PATH = Path(ROOT_DIR) / "data" / "biggest_island.json"
NODE_ISLAND_IMG_PATH = Path(ROOT_DIR) / "data" / "node_islands_split.png"
NODE_ISLAND_IMG_PATH_TSP = Path(ROOT_DIR) / "data" / "node_islands_split_tsp.png"

# Cache Directory
CACHE_DIR = Path(ROOT_DIR) / "cache"

# Google Maps API (GM)
GM_API_KEY_ENV = "GOOGLE_MAPS_API_KEY"  # Environment variable
GM_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GM_ATTRACTIONS_PATH = Path(ROOT_DIR) / "data" / "gm_disneyland_paris_attractions.json"

# Weather
WEATHER_API_KEY_ENV = "OPEN_WEATHER_API_KEY"  # Environment variable
WEATHER_URL_ONE_CALL = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
WEATHER_URL_HISTORY = "https://history.openweathermap.org/data/2.5/history"
WEATHER_DATA_PATH = Path(ROOT_DIR) / "data" / "weather_data.json"
DISNEYLAND_LAT = 48.86717
DISNEYLAND_LON = 2.78347

# OpenAPI
OPEN_API_KEY_ENV = "OPEN_API_KEY"  # Environment variable
OPEN_API_URL = "https://api.openai.com/v1/chat/completions"
OPEN_API_MODEL = "gpt-3.5-turbo"
OPEN_API_RESPONSE_PATH = Path(ROOT_DIR) / "data" / "open_api_response.json"


# Path functions
def clean_path(path: str | Path) -> str:
    """
    Clean the path by removing the root directory.
    :param path: The path to clean.
    """
    path = Path(path)
    path_parts = path.parts
    root_dir_parts = Path(ROOT_DIR).parts
    relative_path_parts = path_parts[len(root_dir_parts) :]
    relative_path = Path(*relative_path_parts)
    return str(relative_path)


def print_path(path: str | Path) -> None:
    """
    Print the path to the console, but without the root directory.
    :param path: The path to print.
    """
    path = clean_path(path)
    print(path)

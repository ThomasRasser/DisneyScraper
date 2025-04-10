import hashlib
import json
import os
import sys
import time
from functools import lru_cache

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# region  Constants
DISNEY_ATTRACTIONS_URL = "https://www.disneylandparis.com/en-gb/attractions/"
PARSED_ATTRACTIONS_PATH = "data/parsed_attractions.json"
CACHE_DIR = "cache"
# endregion


# region Decorators
def file_cache_wrapper(func):
    def wrapper(url, cache_dir=CACHE_DIR, max_age_hours=1):
        """
        Decorator to cache the HTML content of a URL using a file-based cache.
        :param func: The function to wrap.
        :param url: The URL to fetch.
        :param cache_dir: The directory to store cached files.
        :param max_age_days: The maximum age of the cache in days.
        :return: The HTML content as a string.
        """
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # Create a filename based on the URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(cache_dir, f"{url_hash}.json")

        # Check if cache file exists and is less than a day old
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                try:
                    cached_data = json.load(f)
                    timestamp = cached_data.get("timestamp", 0)
                    current_time = time.time()

                    # Check if cache is still valid (less than max_age_days old)
                    if current_time - timestamp < max_age_hours * 60 * 60:  # Convert hours to seconds
                        print(f"Using cached content for {url}")
                        return cached_data.get("html")
                except json.JSONDecodeError:
                    # If the JSON is corrupted, ignore the cache
                    pass

        # Cache miss or expired, call the original function
        html_content = func(url)

        # Save the result to cache if it's not None
        if html_content is not None:
            cache_data = {"timestamp": time.time(), "html": html_content}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)

        return html_content

    return wrapper


# endregion


# region Utility Functions
def get_soup(html_content):
    return BeautifulSoup(html_content, "html.parser")


# endregion

# region Scraping


@lru_cache(maxsize=128)
@file_cache_wrapper
def get_html_single(url: str, wait_selector: str = "body", timeout: int = 10) -> str | None:
    print(f"Fetching {url}...")

    options = Options()
    options.add_argument("--headless=new")  # More stealthy headless mode
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            });
            """
            },
        )
        driver.get(url)
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)))
        time.sleep(1)  # Slight delay for dynamic content to load
        return driver.page_source
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
    finally:
        driver.quit()


def parse_attraction_lists(html: str) -> list[dict]:
    """
    Parses the HTML content and extracts attraction data.
    :param html: The HTML content as a string.
    :return: A list of dictionaries containing attraction data.
    """
    print("Parsing HTML content...")

    soup = get_soup(html)

    # Attraction lists have the class `card-list`
    # Usually there is one list for open and one for closed attractions
    attraction_lists = soup.find_all("div", class_="card-list")
    if not attraction_lists:
        print("No attraction lists found.")
        return []

    # Example attraction item
    """
    <div class="m-button-card m-card" title="Learn more about &quot;it's a small world&quot;">
        <article>
            <ahref="https://www.disneylandparis.com/en-gb/attractions/disneyland-park/its-a-small-world-app/" class="card-content">
                <div class="card-image">
                    <span class=" lazy-load-image-background  lazy-load-image-loaded"
                        style="color: transparent; display: inline-block; height: auto; width: 100%;">
                            <img height="90px" alt width="100%"
                            src="https://media.disneylandparis.com/d4th/en-gb/images/n016335_2_2028jan27_world_it-a-small-world-attraction_16-9_tcm752-256994.jpg?w=180">
                    </span>
                </div>
                <div class="card-text">
                    <div class="card-description full-description">
                        <h2>
                            "it's a small world"
                        </h2>
                        <div class="activity-info">
                            Height: Any Height
                        </div>
                        <div class="activity-info">
                            Fun For Little Ones, Disney Premier Access, Disney Premier Access One, Disney Premier Access Ultimate
                        </div>
                        <div class="activity-info">
                            Disneyland Park, Fantasyland
                        </div>
                    </div>
                </div>
            </a>
        </article>
    </div>
    """

    # Extract and clean-up the attraction data
    attractions = []
    for attraction_list in attraction_lists:
        for attraction in attraction_list.find_all("div", class_="m-button-card m-card"):
            try:
                new_attraction = {}

                new_attraction["title"] = attraction.get("title", "")
                if new_attraction["title"]:
                    new_attraction["title"] = new_attraction["title"].replace("Learn more about ", "").strip()

                a_tag = attraction.find("a")
                new_attraction["link"] = a_tag.get("href", "") if a_tag else ""

                img_tag = attraction.find("img")
                new_attraction["image"] = img_tag.get("src", "") if img_tag else ""

                h2_tag = attraction.find("h2")
                new_attraction["description"] = h2_tag.text.strip() if h2_tag and h2_tag.text else ""

                info_tags = attraction.find_all("div", class_="activity-info")
                new_attraction["min_height_cm"] = info_tags[0].text.strip() if len(info_tags) > 0 else ""
                if new_attraction["min_height_cm"]:
                    new_attraction["min_height_cm"] = new_attraction["min_height_cm"].replace("Height: ", "").strip()
                    if new_attraction["min_height_cm"] == "Any Height":
                        new_attraction["min_height_cm"] = "0"
                    if "cm" in new_attraction["min_height_cm"]:
                        new_attraction["min_height_cm"] = new_attraction["min_height_cm"].replace("cm", "").strip()
                    if "m" in new_attraction["min_height_cm"]:
                        new_attraction["min_height_cm"] = str(
                            float(new_attraction["min_height_cm"].replace("m", "").strip()) * 100
                        )

                new_attraction["keywords"] = info_tags[1].text.strip() if len(info_tags) > 1 else ""
                new_attraction["location"] = info_tags[2].text.strip() if len(info_tags) > 2 else ""

                attractions.append(new_attraction)
                print(f"Found attraction: {new_attraction['title']}")
            except (AttributeError, IndexError) as e:
                print(f"Error parsing attraction data: {e}")

    return attractions


# endregion


# region Main
def main():
    """
    Main function to fetch and parse attraction data from Disneyland Paris.
    """

    try:
        # Fetch the HTML content
        html_content = get_html_single(DISNEY_ATTRACTIONS_URL)

        # Check if HTML content was fetched successfully
        if not html_content:
            print("Failed to fetch HTML content.")
            sys.exit(1)

        # Parse the HTML content and extract attraction data
        attractions = parse_attraction_lists(html_content)

        # Save the data to a JSON file
        if not os.path.exists(PARSED_ATTRACTIONS_PATH):
            os.makedirs(os.path.dirname(PARSED_ATTRACTIONS_PATH), exist_ok=True)

        with open(PARSED_ATTRACTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(attractions, f, ensure_ascii=False, indent=4)

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Cleaning up...")


if __name__ == "__main__":
    main()
# endregion

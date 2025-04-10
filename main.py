import argparse
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

from cache_decorator import file_cache_wrapper, remove_cache

# region  Constants
DISNEY_ATTRACTIONS_URL = "https://www.disneylandparis.com/en-gb/attractions/"
PARSED_ATTRACTIONS_PATH = "data/parsed_attractions.json"
# endregion


# region Scraping - List
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

    soup = BeautifulSoup(html, "html.parser")

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

    parser = argparse.ArgumentParser(description="Fetch and parse Disneyland Paris attraction data.")
    parser.add_argument(
        "--clean", action="store_true", help="Remove existing parsed data and cached files before running."
    )
    args = parser.parse_args()

    try:
        if args.clean and os.path.exists(PARSED_ATTRACTIONS_PATH):
            os.remove(PARSED_ATTRACTIONS_PATH)
            print(f"Removed existing file: {PARSED_ATTRACTIONS_PATH}")

        if args.clean and os.path.exists("cache"):
            remove_cache()
            print("Removed existing cache files.")

        # Fetch the HTML content
        html_content = get_html_single(DISNEY_ATTRACTIONS_URL)

        # Check if HTML content was fetched successfully
        if not html_content:
            print("Failed to fetch HTML content.")
            sys.exit(1)

        # Parse the HTML content and extract attraction data
        attractions = parse_attraction_lists(html_content)

        # Save the data to a JSON file
        os.makedirs(os.path.dirname(PARSED_ATTRACTIONS_PATH), exist_ok=True)
        with open(PARSED_ATTRACTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(attractions, f, ensure_ascii=False, indent=4)

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Script finished.")


if __name__ == "__main__":
    main()
# endregion

import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_decorator import remove_complete_cache
from utils.constants import (
    OPEN_API_KEY_ENV,
    OPEN_API_MODEL,
    OPEN_API_RESPONSE_PATH,
    OPEN_API_URL,
    clean_path,
)
from utils.save_load import load_json_data, save_json_data
from utils.scraper import (
    extract_human_text_from_html,
    get_html_multiple,
    get_html_single,
    get_html_single_cached,
)


def fetch_chatgpt_response(prompt: str, model: str = OPEN_API_MODEL) -> dict | None:
    """
    Fetch response from ChatGPT API.
    :param prompt: User input prompt.
    :param model: Model to use (e.g., gpt-3.5-turbo, gpt-4).
    :return: JSON response or None on error.
    """
    print("Fetching response from ChatGPT...")

    headers = {"Authorization": f"Bearer {os.getenv(OPEN_API_KEY_ENV)}", "Content-Type": "application/json"}

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(OPEN_API_URL, headers=headers, json=data)
    try:
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching data: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error parsing response: {e}")
        return None


def main():
    URL = "https://www.disneylandparis.com/en-gb/attractions/walt-disney-studios-park/flight-force/"

    html = get_html_single_cached(URL)
    if not html:
        print("Failed to fetch HTML content.")
        return

    text = extract_human_text_from_html(html)

    prompt = f"""
    You are a JSON generator. Your task is to generate a JSON object based on the following text:
    {text}
    The JSON object should contain the following fields:
    "name": ""
    "duration": null,
    "description": "",
    "max_height_cm": null,
    "min_height_cm": 120,
    "min_age": null,
    "accessibility_tags": [],
    """

    response = fetch_chatgpt_response(prompt)
    if not response:
        print("Failed to fetch ChatGPT response.")
        return

    save_json_data(response, OPEN_API_RESPONSE_PATH)


if __name__ == "__main__":
    main()

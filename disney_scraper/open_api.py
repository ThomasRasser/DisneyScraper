import argparse
import json
import os
import sys

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cache_decorator import file_cache_wrapper_url_fetch
from utils.constants import (
    FINAL_COMBINED_ATTRACTIONS_PATH,
    FINAL_COMBINED_DINING_PATH,
    OPEN_API_KEY_ENV,
    OPEN_API_MODEL,
    OPEN_API_RESPONSE_PATH,
    OPEN_API_URL,
    PARSED_ATTRACTIONS_DETAIL_PATH,
    clean_path,
)
from utils.save_load import (
    load_json_data,
    save_json_data,
)
from utils.scraper import (
    extract_human_text_from_html,
    get_html_multiple_cached,
    get_html_single_cached,
)

# region Scraping Functions


def fetch_chatgpt_response(url: str, model: str = OPEN_API_MODEL) -> dict | None:
    """
    Fetch response from ChatGPT API.
    :param url: User input prompt. (called url for consistency with the cache decorator)
    :param model: Model to use (e.g., gpt-3.5-turbo, gpt-4).
    :return: JSON response or None on error.
    """
    print("Fetching response from ChatGPT...")
    prompt = url

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


def generate_attraction_json_parse_prompt(text: str) -> dict:
    """
    Generate a prompt for ChatGPT to parse the raw text data,
    scraped from the Disneyland Paris website, into a structured JSON format.
    :param accessibility_keywords: List of keywords for accessibility tags, already defined.
    :return: Formatted prompt string.
    """

    prompt = f"""
    You are a JSON generator. Your task is to generate a VALID JSON object,
    which can be read by a python3 script using `json.loads()`.

    The information is based on the following text:
    ----------------------
    {text}
    ----------------------
    The JSON object should contain the following fields:
    - name: str
    - description: str,
    - accessibility_tags: [str],
    - services_tags: [str],

    Regarding height, if the attractions mentions "Any Height" or "No Height Restriction",
    please set the value of min_height_cm to 0 and max_height_cm to 300.

    Services Tags are all the keywords that are related to services and bonus features, provided by the Disneyland,
    for example regarding fast pass, single rider, photo pass, ...

    Accessibility Tags are all the keywords that are related to accessibility,
    for example regarding wheelchair access, pregnancy, guide dogs, ...
    """

    prompt += """
    If the information is not available in the text, please set the value to `null`.

    IT IS ESSENTIAL THAT THE JSON OBJECT IS VALID.
    Please return the JSON object in a valid format.
    """

    return prompt


def generate_fix_json_prompt(json_data_raw: str, error: str = None) -> str:
    """
    Generate a prompt for ChatGPT to fix the JSON data.
    :param json_data: JSON data to be fixed.
    :return: Formatted prompt string.
    """
    prompt = f"""
    You are a JSON fixer. Your task is to fix the following JSON object, which is not valid JSON.
    After you are finished, it should be valid JSON, which can be read by a python3 script using:
    `json.loads(response_dict_raw)`

    The JSON object is:
    ----------------------
    {json_data_raw}
    ----------------------
    """

    if error:
        prompt += f"""
        The error message is:
        ----------------------
        {error}
        ----------------------
        """

    prompt += """
    Please return the fixed JSON object in a valid format.
    """

    return prompt


def get_gpt_response_content(response: dict) -> str:
    """
    Get the content from the ChatGPT response.
    :param response: JSON response from ChatGPT.
    :return: Content string.
    """
    try:
        return response.get("choices")[0].get("message").get("content")
    except (KeyError, IndexError) as e:
        print(f"🟥 Error fetching content from response: {e}")
        print(f"Response: {response}")


def parse_gpt_json_response(response_content: str) -> dict:
    """
    Parse the JSON response from ChatGPT.
    :param response: JSON response from ChatGPT.
    :return: Parsed JSON object.
    """
    try:
        return json.loads(response_content)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"🟥 Error parsing JSON response: {e}")
        print(f"Response: {response_content}")
        raise e


def parse_gpt_json_response_with_fix(response_content: str) -> dict:
    """
    Parse the JSON response from ChatGPT and fix it if necessary.
    :param response: JSON response from ChatGPT.
    :return: Parsed JSON object.
    """
    try:
        return json.loads(response_content)
    except json.JSONDecodeError as e:
        fixed_prompt = generate_fix_json_prompt(response_content, error=str(e))
        fixed_response = fetch_chatgpt_response(fixed_prompt)
        if fixed_response:
            return parse_gpt_json_response(fixed_response)
        else:
            print("🟥 Failed to parse JSON, even after fix")
            return {}


def parse_disney_attractions_details(scraped_attractions_detail_text: list[dict]) -> dict:
    """
    Parse the Disneyland Paris attractions details from the JSON file
    and generate a structured JSON object.
    :return: Parsed attractions details.
    """
    parsed_attractions_dict = {}
    for attraction in scraped_attractions_detail_text:
        name = attraction["name"]
        text = attraction["text"]

        prompt = generate_attraction_json_parse_prompt(text)

        response = fetch_chatgpt_response(prompt)
        if not response:
            print(f"🟥 Failed to fetch response for {name}.")

        response_content = get_gpt_response_content(response)
        parsed_data = parse_gpt_json_response_with_fix(response_content)

        if parsed_data:
            parsed_attractions_dict[name] = parsed_data

    return parsed_attractions_dict


# endregion


def create_all_files_and_merge(clean: bool = False) -> None:
    """
    Does the scraping and creates all files necessary for the final combined data.
    and merges them into the combined data file.

    Expected that the `FINAL_COMBINED_ATTRACTIONS` file exists
    and has been populated with the scraped data.

    :clean: If True, dont use cached data.
    """

    assert os.path.exists(FINAL_COMBINED_ATTRACTIONS_PATH), f"File not found: {FINAL_COMBINED_ATTRACTIONS_PATH}"

    final_attractions = load_json_data(FINAL_COMBINED_ATTRACTIONS_PATH)
    scraped_attractions_detail_text = load_json_data(PARSED_ATTRACTIONS_DETAIL_PATH)
    scraped_dining = load_json_data(FINAL_COMBINED_DINING_PATH)

    # Merge the gpt data into final combined rides data
    gpt_scraped_data_dict = parse_disney_attractions_details(scraped_attractions_detail_text)

    for attraction in final_attractions:
        name = attraction["scrape_name"]
        if name in gpt_scraped_data_dict:
            gpt_entry = gpt_scraped_data_dict[name]
            attraction["scrape_description"] = gpt_entry.get("description", "")
            attraction["scrape_accessibility_tags"] = gpt_entry.get("accessibility_tags", [])
            attraction["scrape_services_tags"] = gpt_entry.get("services_tags", [])
        else:
            print(f"🟨 Attraction {name} not found in GPT scraped data.")

    # Save the merged data
    save_json_data(final_attractions, FINAL_COMBINED_ATTRACTIONS_PATH)


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

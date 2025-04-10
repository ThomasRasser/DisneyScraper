import hashlib
import json
import os
import time

CACHE_DIR = "cache"


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


def remove_cache(cache_dir=CACHE_DIR):
    """
    Remove all cached files in the specified directory.
    :param cache_dir: The directory to remove cached files from.
    """
    if os.path.exists(cache_dir):
        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Removed cache file: {file_path}")
            except Exception as e:
                print(f"Error removing cache file {file_path}: {e}")

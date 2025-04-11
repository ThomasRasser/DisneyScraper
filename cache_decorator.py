import hashlib
import json
import os
import time

CACHE_DIR = "cache"


def file_cache_wrapper_url_fetch(func):
    def wrapper(*args, cache_dir=CACHE_DIR, max_age_hours=1, **kwargs):
        """
        Decorator to cache the HTML content of a URL using a file-based cache.
        Assumes the first positional arg or 'url' kwarg is the URL.
        :param func: The function to wrap.
        :param cache_dir: Directory to store cached files.
        :param max_age_hours: Maximum age of the cache in hours.
        :return: The HTML content of the URL.
        """
        url = kwargs.get("url") if "url" in kwargs else args[0]

        cache_file = _get_cache_file_path(url, cache_dir)

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


def remove_complete_cache(cache_dir=CACHE_DIR):
    """
    Remove all cached files in the specified directory.
    :param cache_dir: The directory to remove cached files from.
    """
    if not os.path.exists(cache_dir):
        print(f"Cache directory does not exist: {cache_dir}")
        return
    if not os.path.isdir(cache_dir):
        print(f"Cache path is not a directory: {cache_dir}")
        return
    if not os.access(cache_dir, os.W_OK):
        print(f"Cache directory is not writable: {cache_dir}")
        return

    for filename in os.listdir(cache_dir):
        file_path = os.path.join(cache_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Removed cache file: {file_path}")
        except Exception as e:
            print(f"Error removing cache file {file_path}: {e}")


def remove_cache_for_url(url, cache_dir=CACHE_DIR):
    """
    Remove the cache for a specific URL.
    :param url: The URL to remove the cache for.
    :param cache_dir: The directory to remove cached files from.
    """
    cache_file = _get_cache_file_path(url, cache_dir)

    if not os.path.exists(cache_file):
        print(f"No cache file found for {url}: {cache_file}")
        return
    if not os.path.isfile(cache_file):
        print(f"Cache file is not a file for {url}: {cache_file}")
        return
    if not os.access(cache_file, os.W_OK):
        print(f"Cache file is not writable for {url}: {cache_file}")
        return

    try:
        os.remove(cache_file)
        print(f"Removed cache file for {url}: {cache_file}")
    except Exception as e:
        print(f"Error removing cache file {cache_file}: {e}")


def _get_cache_file_path(url, cache_dir=CACHE_DIR):
    """
    Get the cache file path for a specific URL.
    :param url: The URL to get the cache file path for.
    :param cache_dir: The directory to store cached files.
    :return: The cache file path.
    """
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    url_hash = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(cache_dir, f"{url_hash}.json")

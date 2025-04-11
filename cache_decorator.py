import hashlib
import json
import os
import time

CACHE_DIR = "cache"


def file_cache_wrapper(func):
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

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(cache_dir, f"{url_hash}.json")

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                try:
                    cached_data = json.load(f)
                    timestamp = cached_data.get("timestamp", 0)
                    if time.time() - timestamp < max_age_hours * 3600:
                        print(f"Using cached content for {url}")
                        return cached_data.get("html")
                except json.JSONDecodeError:
                    pass

        html_content = func(*args, **kwargs)

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

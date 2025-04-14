import concurrent.futures
import queue
import time
from functools import lru_cache
from pathlib import Path
from threading import Lock

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from utils.cache_decorator import file_cache_wrapper_url_fetch


class BrowserPool:
    def __init__(self, pool_size=5):
        self.pool_size = pool_size
        self.available_browsers = queue.Queue(pool_size)
        self.lock = Lock()
        self.initialized = False

    def initialize(self):
        if self.initialized:
            return

        with self.lock:
            if not self.initialized:
                for _ in range(self.pool_size):
                    self.available_browsers.put(self._create_browser())
                self.initialized = True

    def _create_browser(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

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
        return driver

    def get_browser(self):
        if not self.initialized:
            self.initialize()
        return self.available_browsers.get()

    def return_browser(self, browser):
        try:
            self.available_browsers.put(browser, block=False)
        except queue.Full:
            browser.quit()


# Create a global browser pool
browser_pool = BrowserPool(pool_size=5)


def scroll_and_wait_for_images(browser, timeout=10, pause=0.75, max_scrolls=50):
    for _ in range(max_scrolls):
        browser.execute_script("window.scrollBy(0, window.innerHeight);")
        time.sleep(pause)
        browser.execute_script("window.scrollBy(0, -100);")  # Trigger loading for some buggy lazy-loaders
        time.sleep(0.2)

    WebDriverWait(browser, timeout).until(
        lambda d: d.execute_script("""
        return Array.from(document.images).every(
            img => img.complete && img.naturalWidth > 0
        )
    """)
    )


@lru_cache(maxsize=128)
@file_cache_wrapper_url_fetch
def get_html_single_cached(url: str, wait_selector: str = "body", timeout: int = 10) -> str | None:
    return get_html_single(url, wait_selector, timeout)


def get_html_single(url: str, wait_selector: str = "body", timeout: int = 10) -> str | None:
    print(f"Fetching {url}...")
    browser = None

    try:
        browser = browser_pool.get_browser()
        browser.get(url)

        WebDriverWait(browser, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)))

        scroll_and_wait_for_images(browser, timeout)

        return browser.page_source
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        if browser:
            try:
                browser.quit()
            except:
                pass
        return None
    finally:
        if browser:
            browser_pool.return_browser(browser)


def get_html_multiple_cached(urls: list, wait_selector: str = "body", timeout: int = 10, max_workers: int = 5) -> dict:
    return get_html_multiple(urls, wait_selector, timeout, max_workers, get_html_single_cached)


def get_html_multiple(
    urls: list, wait_selector: str = "body", timeout: int = 10, max_workers: int = 5, scrape_function=get_html_single
) -> dict:
    """
    Fetch HTML from multiple URLs concurrently using the browser pool
    :params urls: List of URLs to fetch
    :params wait_selector: CSS selector to wait for
    :params timeout: Maximum time to wait for the selector
    :params max_workers: Maximum number of concurrent workers
    :returns: Dictionary mapping URLs to their HTML content
    """
    results = {}

    # Initialize the browser pool if not already done
    browser_pool.initialize()

    # Use a smaller number of workers than the pool size to avoid exhaustion
    max_workers = min(max_workers, browser_pool.pool_size)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scrape_function, url, wait_selector, timeout): url for url in urls}

        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                html = future.result()
                results[url] = html
            except Exception as e:
                print(f"Exception processing {url}: {e}")
                results[url] = None

    return results


def extract_human_text_from_html(html: str, selector: str = "main") -> str:
    """
    Extract human-readable text from HTML using a given selector.
    Defaults to extracting from the <main> tag.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    main_element = soup.select_one(selector)
    if not main_element:
        return soup.get_text(separator="\n", strip=True)

    return main_element.get_text(separator="\n", strip=True)

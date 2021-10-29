import os
import time
import signal
import requests
import io
import hashlib
import pathlib

from PIL import Image
from selenium import webdriver
from glob import glob



# Credit:
# https://stackoverflow.com/a/22348885
class timeout:
    def __init__(self, seconds=1, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def fetch_image_urls(
    query: str,
    max_links_to_fetch: int,
    wd: webdriver,
    sleep_between_interactions: int = 1,
):
    def scroll_to_end(wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(sleep_between_interactions)

    # build the google query
    search_url = "https://www.google.com/search?safe=off&site=&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"

    # load the page
    wd.get(search_url.format(q=query))

    image_urls = set()
    image_count = 0
    results_start = 0
    while image_count < max_links_to_fetch:
        scroll_to_end(wd)

        # get all image thumbnail results
        thumbnail_results = wd.find_elements_by_css_selector("img.Q4LuWd")
        number_results = len(thumbnail_results)

        print(
            f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}"
        )

        for img in thumbnail_results[results_start:number_results]:
            # try to click every thumbnail such that we can get the real image behind it
            try:
                img.click()
                time.sleep(sleep_between_interactions)
            except Exception:
                continue

            # extract image urls
            actual_images = wd.find_elements_by_css_selector("img.n3VNCb")
            for actual_image in actual_images:
                if actual_image.get_attribute(
                    "src"
                ) and "http" in actual_image.get_attribute("src"):
                    image_urls.add(actual_image.get_attribute("src"))

            image_count = len(image_urls)

            if len(image_urls) >= max_links_to_fetch:
                print(f"Found: {len(image_urls)} image links, done!")
                break
        else:
            print("Found:", len(image_urls), "image links, looking for more ...")
            time.sleep(SLEEP_BEFORE_MORE)

            not_what_you_want_button = ""
            try:
                not_what_you_want_button = wd.find_element_by_css_selector(".r0zKGf")
            except:
                pass

            # If there are no more images return.
            if not_what_you_want_button:
                print("No more images available.")
                return image_urls

            load_more_button = wd.find_element_by_css_selector(".mye4qd")
            if load_more_button and not not_what_you_want_button:
                wd.execute_script("document.querySelector('.mye4qd').click();")

        # move the result startpoint further down
        results_start = len(thumbnail_results)

    return image_urls


def persist_image(folder_path: str, url: str):
    try:
        print("Getting image")
        with timeout(GET_IMAGE_TIMEOUT):
            image_content = requests.get(url).content

    except Exception as e:
        print(f"ERROR - Could not download {url} - {e}")

    try:
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert("RGB")
        file_path = os.path.join(
            folder_path, hashlib.sha1(image_content).hexdigest()[:10] + ".jpg"
        )
        with open(file_path, "wb") as f:
            image.save(f, "JPEG", quality=85)
        print(f"SUCCESS - saved {url} - as {file_path}")
    except Exception as e:
        print(f"ERROR - Could not save {url} - {e}")


def search_and_download(search_term: str, target_path="./images", number_images=5):
    target_folder = os.path.join(target_path, "_".join(search_term.lower().split(" ")))

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    with webdriver.Chrome(executable_path=DRIVER_PATH) as wd:
        res = fetch_image_urls(
            search_term,
            number_images,
            wd=wd,
            sleep_between_interactions=SLEEP_BETWEEN_INTERACTIONS,
        )

        if res is not None:
            for elem in res:
                persist_image(target_folder, elem)
        else:
            print(f"Failed to return links for term: {search_term}")

##############
# Parameters
##############

number_of_images = 10
GET_IMAGE_TIMEOUT = 2
SLEEP_BETWEEN_INTERACTIONS = 0.1
SLEEP_BEFORE_MORE = 5

output_path_root = "."

# Get terms already recorded.
# dirs = glob(output_path + "*")
# dirs = [dir.split("/")[-1].replace("_", " ") for dir in dirs]

search_terms = [
    'emergency vehicle on road',
    'police car on road',
    'police bike on road',
    'police motorcycle on road',
    'ambulance on road',
    'fire truck on road',
    'fire engine on road',
    'police car on road night',
    'police bike on road night',
    'police motorcycle on road night',
    'ambulance on road night',
    'fire truck on road night',
    'fire engine on road night',
]

# Exclude terms already stored.
# search_terms = [term for term in search_terms if term not in dirs]

##########
# Scrap
##########
DRIVER_PATH = './chromedriver'
for term in search_terms:
    search_and_download(term, output_path_root, number_of_images)

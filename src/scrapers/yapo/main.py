from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
import time
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.models import Car
import re
import requests
from scrapers.utils import (
    normalize_fuel_type,
    normalize_transmission,
    load_env,
    post_car,
    save_to_json,
)


config = load_env()

DEFAULT_URL = "https://public-api.yapo.cl"
BASE_URL = "https://public-api.yapo.cl/autos-usados/region-metropolitana"
N_PAGES = int(config["YP_N_PAGES"])
BACKEND_URL = str(config["BACKEND_URL"])


# Convert a dictionary of data extracted from Yapo to a json following the Car model format
def convert_yapo_data_to_json(
    car_dict: dict,
):
    d = car_dict
    fuel_type = normalize_fuel_type(d["Combustible"])
    transmission_type = normalize_transmission(d["Transmisión"])
    try:
        car = Car(
            brand=d["Marca"],
            model=d["Modelo"],
            year=int(d["Año"]),
            km=re.sub(r"[']", "", d["Kilómetros"]),
            version="",
            transmission=transmission_type,
            priceActual=int(re.sub(r"[\$\.]", "", d["Precio"].split()[0])),
            priceOriginal=int(re.sub(r"[\$\.]", "", d["Precio"].split()[0])),
            location=d["Localización"],
            fuelType=fuel_type,
            postUrl=DEFAULT_URL + d["post_url"],
            imgUrl=d["img_url"],
            dataSource="yapo",
            publishedAt=datetime.strptime(d["Publicado"], "%d/%m/%Y").isoformat() + "Z",
            scrapedAt=datetime.now().isoformat() + "Z",
        )
        return car.model_dump()
    except KeyError or requests.exceptions.RequestException:
        return None


# Explore the main page of used cars to get (post_url, img_url) pairs to be explored
def get_links(n_pages: int, retries: int = 3):
    car_listing_links = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            # proxy= {},
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="es-ES",
            permissions=[],
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": "https://www.google.com/",
            },
        )
        page = context.new_page()
        for attempt in range(retries):
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded")
                print(f"Connecting to {BASE_URL}")
                break
            except PlaywrightTimeoutError:
                print(f"Attempt {attempt}/{retries} to connect to the URL failed")
                continue
            except Exception as e:
                raise Exception(f"(get_links) Error -> in attempt {attempt}) : {e}")
        time.sleep(2)
        print(f"Loading pages ({n_pages}) in total")
        for page_number in range(1, n_pages + 1):
            print(f"Loading page {page_number}")
            try:
                page_url = f"{BASE_URL}.{page_number}"
                page.goto(page_url, timeout=10000, wait_until="domcontentloaded")
                car_listing_class = "d3-ad-tile d3-ads-grid__item d3-ad-tile--fullwidth d3-ad-tile--bordered d3-ad-tile--feat d3-ad-tile--feat-plat"
                car_list_locator = page.locator(f'div[class="{car_listing_class}"]')
                links_locator = car_list_locator.locator(
                    'a[href^="/autos-usados/"]:not([class])'
                )

                page.wait_for_load_state("domcontentloaded")
                links_list = links_locator.evaluate_all(  # links_list is of type (post_url , img_url)
                    """els => els.map(el => {
                        const href = el.getAttribute('href');
                        const img = el.querySelector('img');
                        const imgSrc = img?.getAttribute('src') || img?.getAttribute('data-src');
                        return [href, imgSrc];
                        })"""
                )
                print(f"Retrieved {len(links_list)} links from page {page_number}")
                for url in links_list:
                    car_listing_links.append(tuple(url))
                time.sleep(0.5)
            except Exception:
                print(f"Error loading/processing page {page_number}")
                continue
        browser.close()
        return car_listing_links


# Scrape all publications while posting to db
def scrape_and_post(
    links_list: list[tuple[str]],
    retries: int = 3,
):
    print("Scraping publications details")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            # proxy= {}
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            permissions=[],
        )
        page = context.new_page()
        print(f"Connecting to {BASE_URL}")
        for attempt in range(retries):
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded")
                break
            except PlaywrightTimeoutError:
                print(f"Attempt {attempt}/{retries} to connect to the URL failed")
                continue
            except Exception as e:
                raise Exception(
                    f"Error (scrape_and_post) -> in attempt {attempt}) : {e}"
                )
        time.sleep(2)
        car_list = list()
        print(f"Loading publications ({len(links_list)} in total)")
        count = 1
        for post_url, img_url in links_list:
            input()
            try:
                attr_dict = dict()
                attr_dict["post_url"] = post_url
                attr_dict["img_url"] = img_url
                page.goto(
                    DEFAULT_URL + post_url, timeout=10000, wait_until="domcontentloaded"
                )
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                car_data = soup.find_all("div", "d3-container d3-property__insight")
                car_desc = soup.find_all("div", "d3-property-details__detail-label")
                # car data
                keys = ["Marca", "Modelo", "Precio", "Año", "Kilómetros", "Combustible"]
                for e in car_data:
                    dat = e.get_text().split()
                    result = {}
                    i = 0
                    # cases where locations has two words "Localización: Las Condes"
                    while i < len(dat):
                        key = dat[i]
                        if key in keys:
                            i += 1
                            value_parts = []
                            while i < len(dat) and dat[i] not in keys:
                                value_parts.append(dat[i])
                                i += 1
                            result[key] = " ".join(value_parts)
                        else:
                            i += 1
                    attr_dict.update(result)

                # aditional car data in post description
                labels = ["Publicado", "Localización", "Transmisión"]
                for e in car_desc:
                    e = e.get_text().split()
                    if e[0] in labels and len(e) > 1:
                        attr_dict[e[0]] = " ".join(e[1 : len(e)])
                car = convert_yapo_data_to_json(attr_dict)
                post_car(car, count, len(links_list), backend_url=BACKEND_URL)
                car_list.append(car)
                count += 1
                time.sleep(1)
            except Exception as e:
                print(e)
                continue
        browser.close()
        print(f"Sent {count} publications in total")
        return car_list


def main():
    try:
        print("Amount of pages to scrape: ", N_PAGES)
        start = time.time()
        links_list = get_links(N_PAGES)
        end = time.time()
        print("Time to get links of publications (per page): ", (end - start) / N_PAGES)

        if links_list:
            start = time.time()
            car_list = scrape_and_post(links_list)
            end = time.time()
        else:
            print("Error: url list returned empty")
            exit(1)

        print(
            "Time of scraping (per page): ",
            (end - start) / N_PAGES,
        )
        save_to_json(car_list)

    except Exception as e:
        print(" ->", e)


if __name__ == "__main__":
    main()

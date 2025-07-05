import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from scrapers.models import Car
from scrapers.utils import (
    load_env,
    normalize_fuel_type,
    normalize_transmission,
    save_to_json,
    post_car,
)

config = load_env()

DEVELOPMENT_MODE = False
HEADLESS_MODE = True
BACKEND_URL = str(config["BACKEND_URL"])
N_PAGES = int(config["KVK_N_PAGES"])  # optional, 0 if you want ot get all kavak pages
PROXY_USER = str(config["PROXY_USER"])
PROXY_PASS = str(config["PROXY_PASS"])


def post_cars_to_api(cars_data: list[Car], backend_url) -> None:
    for i, car in enumerate(cars_data, start=1):
        car = car.model_dump()
        try:
            post_car(car, i, len(cars_data), backend_url)
        except Exception as e:
            print(f"[{i}/{len(cars_data)}] Exception publishing car: {e}")
            continue


def parse_price(price_text: str) -> int | None:
    found_digits = re.findall(r"\d[\d.]*", price_text)
    if found_digits:
        return int(found_digits[0].replace(".", ""))
    return None


def extract_cars_from_dom(page) -> list[Car]:
    extracted_cars = []

    cars_container = page.query_selector(".results_results__container__tcF4_")
    if not cars_container:
        print("No se encontró el contenedor principal de autos")
        return []

    car_cards = cars_container.query_selector_all(
        "a[class*='card-product_cardProduct__']"
    )
    print(f"Encontradas {len(car_cards)} tarjetas de autos")

    current_timestamp = datetime.now().isoformat()

    for car_card in car_cards:
        try:
            href = car_card.get_attribute("href")
            data_testid = car_card.get_attribute("data-testid")
            car_url = None
            if href:
                if not href.startswith(("http://", "https://")):
                    href = f"https://www.kavak.com{href}"
                car_id = None
                if data_testid and data_testid.startswith("card-product-"):
                    car_id = data_testid.replace("card-product-", "")
                if car_id:
                    sep = "&" if "?" in href else "?"
                    car_url = f"{href}{sep}id={car_id}"
                else:
                    car_url = href

            image_element = car_card.query_selector("img")
            car_image_url = (
                image_element.get_attribute("src") if image_element else None
            )

            title_element = car_card.query_selector(
                "h3[class*='card-product_cardProduct__title__']"
            )
            if not title_element:
                title_element = car_card.query_selector("h3")

            title_text = title_element.inner_text() if title_element else "Desconocido"
            brand_model_parts = (
                title_text.split("•") if "•" in title_text else [title_text, ""]
            )
            car_brand = brand_model_parts[0].strip()
            car_model = (
                brand_model_parts[1].strip() if len(brand_model_parts) > 1 else ""
            )

            details_element = car_card.query_selector(
                "p[class*='card-product_cardProduct__subtitle__']"
            )
            if not details_element:
                details_element = car_card.query_selector("p:not([class*='location'])")

            details_text = details_element.inner_text() if details_element else ""
            details_parts = details_text.split("•") if "•" in details_text else []

            car_year_str = "0"
            car_km_str = "0"
            car_version = ""
            car_transmission = ""

            if len(details_parts) >= 4:
                car_year_str = details_parts[0].strip()
                car_km_str = details_parts[1].strip()
                car_version = details_parts[2].strip()
                car_transmission = details_parts[3].strip()

            try:
                car_year = int(car_year_str)
            except ValueError:
                car_year = 0

            try:
                car_km = int(
                    car_km_str.lower().replace("km", "").replace(".", "").strip()
                )
            except ValueError:
                car_km = 0

            price_element = car_card.query_selector(
                "div[class*='amount_uki-amount__']"
            ) or car_card.query_selector("span[class*='amount_uki-amount__']")
            current_price = (
                parse_price(price_element.inner_text()) if price_element else 0
            )

            original_price_element = car_card.query_selector(
                "span[class*='card-product_cardProduct__price__']"
            )
            original_price = (
                parse_price(original_price_element.inner_text())
                if original_price_element
                else None
            )

            if original_price is None:
                price_section_elements = car_card.query_selector_all(
                    "span[class*='card-product_cardProduct__priceSection__']"
                )
                for price_section in price_section_elements:
                    if "precio" in price_section.inner_text().lower():
                        next_element = price_section.evaluate_handle(
                            "el => el.nextElementSibling"
                        )
                        if next_element:
                            price_text = next_element.inner_text()
                            original_price = parse_price(price_text)
                            break

            location_element = car_card.query_selector(
                "span[class*='card-product_cardProduct__footerInfo__']"
            )
            car_location = (
                location_element.inner_text().strip()
                if location_element
                else "Desconocido"
            )

            normalized_transmission = normalize_transmission(car_transmission)
            normalized_fuel = normalize_fuel_type(None)

            car_data = Car(
                brand=car_brand,
                model=car_model,
                year=car_year,
                km=car_km,
                version=car_version,
                transmission=normalized_transmission,
                priceActual=current_price,
                priceOriginal=original_price,
                location=car_location,
                fuelType=normalized_fuel,
                postUrl=car_url,
                imgUrl=car_image_url,
                dataSource="kavak",
                publishedAt=None,
                scrapedAt=current_timestamp,
            )
            extracted_cars.append(car_data)
            print(
                f"Car extracted: {car_brand} {car_model} ({car_year}) - Price: ${current_price:,} - URL: {car_url}"
            )

        except Exception as error:
            print(f"Error al parsear un auto: {error}")
            import traceback

            traceback.print_exc()

    return extracted_cars


# Get number of pages available to scrape
def get_number_of_pages(page) -> int:
    try:
        page.wait_for_selector(".results_results__pagination__yZaD_", timeout=100000)
        pagination_element = page.query_selector(".results_results__pagination__yZaD_")

        if pagination_element:
            page_links = pagination_element.query_selector_all("a")
            page_numbers = []

            for link in page_links:
                link_text = link.inner_text().strip()
                if link_text.isdigit():
                    page_numbers.append(int(link_text))

            if page_numbers:
                return max(page_numbers)
    except Exception as error:
        print("Error getting the total number of pages:", error)
        page.screenshot(path="error_get_total_pages.png")

    return 1


# Try to load the main page and then return the browser instance
def load_main_page(playwright, proxy_settings, max_retries=3):
    for attempt_number in range(1, max_retries + 1):
        print(f"\n[Attempt {attempt_number}/{max_retries}] using proxy...")
        try:
            browser_instance = playwright.chromium.launch(
                headless=HEADLESS_MODE,
                proxy=proxy_settings,
                args=["--ignore-certificate-errors"],
            )
            browser_page = browser_instance.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "es-ES,es;q=0.9",
                    "Referer": "https://www.google.com/",
                },
                viewport={"width": 1280, "height": 800},
            )

            browser_page.goto("https://www.kavak.com/cl/usados", timeout=100000)
            browser_page.mouse.wheel(0, 1000)
            time.sleep(2)

            page_content = browser_page.content().lower()

            if "request could not be satisfied" in page_content:
                print("Request blocked, retrying...")
                browser_page.screenshot(path=f"bloqueo_intento_{attempt_number}.png")
                browser_instance.close()
                continue

            return browser_page, browser_instance

        except Exception as error:
            print(f"Error loading page (attempt {attempt_number}):", error)

    raise RuntimeError("The site could not be accessed after multiple attempts.")


# Function for testing purposes
def pause_for_inspection(
    page, message="Scraper paused. Press Enter in the console to continue..."
):
    if DEVELOPMENT_MODE:
        print(message)
        input()


def main():
    collected_cars = []

    proxy_config = {
        "server": "http://brd.superproxy.io:33335",
        "username": PROXY_USER,
        "password": PROXY_PASS,
    }

    with sync_playwright() as playwright:
        try:
            if N_PAGES < 0:
                raise Exception("Invalid number of pages")
            browser_page, browser = load_main_page(playwright, proxy_config)
            total_page_count = get_number_of_pages(browser_page)
            print(f"Detected {total_page_count} pages")
            print(
                f"Number of pages to scrape: {N_PAGES if (N_PAGES > 0) else total_page_count}"
            )

            pause_for_inspection(
                browser_page,
                "First page loaded. Inspect the content and press Enter to continue....",
            )
        except Exception as error:
            print("Error:", error)
            return

        # Explore pages one by one
        for page_number in range(N_PAGES or total_page_count):
            try:
                print(f"Scraping page {page_number}...")
                page_url = f"https://www.kavak.com/cl/usados?page={page_number}"
                browser_page.goto(page_url, timeout=120000)

                content_selector = ".results_results__container__tcF4_"
                browser_page.wait_for_selector(content_selector, timeout=100000)

                card_selector = "a[class*='card-product_cardProduct__']"
                browser_page.wait_for_selector(card_selector, timeout=10000)

                pause_for_inspection(
                    browser_page,
                    f"Page {page_number} loaded. Inspect the contents and press Enter to continue...",
                )

                page_cars = extract_cars_from_dom(browser_page)
                post_cars_to_api(page_cars, BACKEND_URL)
                collected_cars.extend(page_cars)
                print(f"{len(page_cars)} cars were extracted from page {page_number}")

            except Exception as error:
                print(f"Error processing page {page_number}:", error)
                browser_page.screenshot(path=f"error_page_{page_number}.png")

        pause_for_inspection(
            browser_page,
            "Scraping completed. Press Enter to close the browser...",
        )
        browser.close()

    # for car in collected_cars:
    #     print(f"{car.brand} {car.model} - {car.priceActual:,} CLP - URL: {car.postUrl}")

    save_to_json(collected_cars, filename="kavak.json")


if __name__ == "__main__":
    main()

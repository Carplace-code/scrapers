import re
import json
import time
import random
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from scrapers.models import Car
import requests


DEVELOPMENT_MODE = False
HEADLESS_MODE = True

def post_cars_to_api(cars_data: list[Car], api_url: str, method: str = "POST") -> None:
    for i, car in enumerate(cars_data, start=1):
        payload = car.model_dump()
        # Cambia fuelType a "other" si es None
        if payload.get("fuelType") is None:
            payload["fuelType"] = "other"
        try:
            if method.upper() == "POST":
                response = requests.post(api_url, json=payload, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(api_url, json=payload, timeout=10)
            else:
                print(f"[{i}/{len(cars_data)}] Método HTTP no soportado: {method}")
                continue

            if response.status_code in (200, 201):
                print(f"[{i}/{len(cars_data)}] Auto publicado correctamente: {car.brand} {car.model}")
            else:
                print(f"[{i}/{len(cars_data)}] Error {response.status_code} al publicar ({method} {api_url}): {response.text}")
        except Exception as e:
            print(f"[{i}/{len(cars_data)}] Excepción al publicar el auto: {e}")

def parse_price(price_text: str) -> int | None:
    found_digits = re.findall(r"\d[\d.]*", price_text)
    if found_digits:
        return int(found_digits[0].replace(".", ""))
    return None

def save_to_json(cars_data: list[Car], filename: str = "autos.json") -> None:
    json_data = [car.model_dump() for car in cars_data]
    Path(filename).write_text(
        json.dumps(json_data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nSe guardaron {len(cars_data)} autos en {filename}")

# Enums para normalización
class FuelTypeEnum:
    GAS = "gas"
    DIESEL = "diesel"
    ELECTRICITY = "electricity"
    HYBRID = "hybrid"
    OTHER = "other"

class TransmissionTypeEnum:
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    OTHER = "other"

def normalize_fuel_type(raw_fuel: str | None) -> str | None:
    if not raw_fuel:
        return None
    raw = raw_fuel.lower()
    if "bencina" in raw or "gasolina" in raw or "gas" in raw:
        return FuelTypeEnum.GAS
    if "diesel" in raw:
        return FuelTypeEnum.DIESEL
    if "eléctrico" in raw or "electric" in raw:
        return FuelTypeEnum.ELECTRICITY
    if "híbrido" in raw or "hybrid" in raw:
        return FuelTypeEnum.HYBRID
    return FuelTypeEnum.OTHER

def normalize_transmission(raw_trans: str | None) -> str:
    if not raw_trans:
        return TransmissionTypeEnum.OTHER
    raw = raw_trans.lower()
    if "automático" in raw or "automatic" in raw:
        return TransmissionTypeEnum.AUTOMATIC
    if "manual" in raw:
        return TransmissionTypeEnum.MANUAL
    return TransmissionTypeEnum.OTHER

def extract_cars_from_dom(page) -> list[Car]:
    extracted_cars = []
    
    cars_container = page.query_selector(".results_results__container__tcF4_")
    if not cars_container:
        print("No se encontró el contenedor principal de autos")
        return []
    
    car_cards = cars_container.query_selector_all("a[class*='card-product_cardProduct__']")
    print(f"Encontradas {len(car_cards)} tarjetas de autos")
    
    current_timestamp = datetime.now().isoformat()
    
    for car_card in car_cards:
        try:
            href = car_card.get_attribute("href")
            data_testid = car_card.get_attribute("data-testid")
            car_url = None
            if href:
                if not href.startswith(('http://', 'https://')):
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
            car_image_url = image_element.get_attribute("src") if image_element else None
            
            title_element = car_card.query_selector("h3[class*='card-product_cardProduct__title__']")
            if not title_element:
                title_element = car_card.query_selector("h3")
            
            title_text = title_element.inner_text() if title_element else "Desconocido"
            brand_model_parts = title_text.split("•") if "•" in title_text else [title_text, ""]
            car_brand = brand_model_parts[0].strip()
            car_model = brand_model_parts[1].strip() if len(brand_model_parts) > 1 else ""
            
            details_element = car_card.query_selector("p[class*='card-product_cardProduct__subtitle__']")
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
                car_km = int(car_km_str.lower().replace("km", "").replace(".", "").strip())
            except ValueError:
                car_km = 0
                
            price_element = car_card.query_selector("div[class*='amount_uki-amount__']") or car_card.query_selector("span[class*='amount_uki-amount__']")
            current_price = parse_price(price_element.inner_text()) if price_element else 0
            
            original_price_element = car_card.query_selector("span[class*='card-product_cardProduct__price__']")
            original_price = parse_price(original_price_element.inner_text()) if original_price_element else None
            
            if original_price is None:
                price_section_elements = car_card.query_selector_all("span[class*='card-product_cardProduct__priceSection__']")
                for price_section in price_section_elements:
                    if "precio" in price_section.inner_text().lower():
                        next_element = price_section.evaluate_handle("el => el.nextElementSibling")
                        if next_element:
                            price_text = next_element.inner_text()
                            original_price = parse_price(price_text)
                            break
            
            location_element = car_card.query_selector("span[class*='card-product_cardProduct__footerInfo__']")
            car_location = location_element.inner_text().strip() if location_element else "Desconocido"
            
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
                scrapedAt=current_timestamp
            )
            extracted_cars.append(car_data)
            print(f"Auto extraído: {car_brand} {car_model} ({car_year}) - Precio: ${current_price:,} - URL: {car_url}")

        except Exception as error:
            print(f"Error al parsear un auto: {error}")
            import traceback
            traceback.print_exc()
    
    return extracted_cars

def get_total_pages(page) -> int:
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
        print("Error al obtener el número total de páginas:", error)
        page.screenshot(path="error_get_total_pages.png")

    return 1

def robust_scraper_attempt(playwright, proxy_settings, max_retries=3):
    for attempt_number in range(1, max_retries + 1):
        print(f"\n[Intento {attempt_number}/{max_retries}] usando proxy...")
        try:
            browser_instance = playwright.chromium.launch(
                headless=HEADLESS_MODE,
                proxy=proxy_settings,
                args=["--ignore-certificate-errors"]
            )
            browser_page = browser_instance.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "es-ES,es;q=0.9",
                    "Referer": "https://www.google.com/"
                },
                viewport={"width": 1280, "height": 800}
            )

            browser_page.goto("https://www.kavak.com/cl/usados", timeout=100000)
            browser_page.mouse.wheel(0, 1000)
            time.sleep(2)

            page_content = browser_page.content().lower()

            if "request could not be satisfied" in page_content:
                print("Página bloqueada, reintentando...")
                browser_page.screenshot(path=f"bloqueo_intento_{attempt_number}.png")
                browser_instance.close()
                continue

            return browser_page, browser_instance

        except Exception as error:
            print(f"Error al cargar la página (intento {attempt_number}):", error)

    raise RuntimeError("No se pudo acceder al sitio tras múltiples intentos.")

def pause_for_inspection(page, message="Scraper pausado. Presiona Enter en la consola para continuar..."):
    if DEVELOPMENT_MODE:
        print(message)
        input()

def main():
    collected_cars = []
    session_id = random.randint(1000, 9999)
    
    proxy_config = {
        "server": "http://brd.superproxy.io:33335",
        "username": f"brd-customer-hl_59fd91ff-zone-residential_proxy1-session-{session_id}",
        "password": "fmj7cpmf7i9p"
    }

    with sync_playwright() as playwright:
        try:
            browser_page, browser = robust_scraper_attempt(playwright, proxy_config)
            total_page_count = get_total_pages(browser_page)
            print(f"Total de páginas detectadas: {total_page_count}")
            
            pause_for_inspection(browser_page, "Primera página cargada. Inspecciona el contenido y presiona Enter para continuar...")
        except Exception as error:
            print("Error crítico:", error)
            return

        for page_number in range(1):  # Cambiar por `range(total_page_count)` si deseas scrapear todas
            try:
                print(f"Scrapeando página {page_number}...")
                page_url = f"https://www.kavak.com/cl/usados?page={page_number}"
                browser_page.goto(page_url, timeout=120000)
                
                content_selector = ".results_results__container__tcF4_"
                browser_page.wait_for_selector(content_selector, timeout=100000)
                
                card_selector = "a[class*='card-product_cardProduct__']"
                browser_page.wait_for_selector(card_selector, timeout=10000)
                
                pause_for_inspection(browser_page, f"Página {page_number} cargada. Inspecciona el contenido y presiona Enter para continuar...")
                
                page_cars = extract_cars_from_dom(browser_page)
                collected_cars.extend(page_cars)
                print(f"Se extrajeron {len(page_cars)} autos de la página {page_number}")

            except Exception as error:
                print(f"Error al procesar la página {page_number}:", error)
                browser_page.screenshot(path=f"error_page_{page_number}.png")
                
        pause_for_inspection(browser_page, "Scraping completado. Presiona Enter para cerrar el navegador...")
        browser.close()

    for car in collected_cars:
        print(f"{car.brand} {car.model} - {car.priceActual:,} CLP - URL: {car.postUrl}")

    save_to_json(collected_cars)

    API_URL = "https://carplace-git-schema-changes-carplaces-projects.vercel.app/api/cars"
    post_cars_to_api(collected_cars, API_URL, method="POST")

if __name__ == "__main__":
    main()

import re
import json
import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright
from kavak_scraper.models import Car

# -------------------- Utilidades --------------------

def parse_price(text: str) -> int | None:
    digits = re.findall(r"\d[\d.]*", text)
    if digits:
        return int(digits[0].replace(".", ""))
    return None

def save_to_json(cars: list[Car], filename: str = "autos.json") -> None:
    data = [car.model_dump() for car in cars]
    Path(filename).write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nSe guardaron {len(cars)} autos en {filename}")

# -------------------- Scraping --------------------

def get_total_pages(page) -> int:
    try:
        page.wait_for_selector(".results_results__pagination__yZaD_", timeout=100000)
        pagination = page.query_selector(".results_results__pagination__yZaD_")

        if pagination:
            page_links = pagination.query_selector_all("a")
            numbers = []

            for link in page_links:
                text = link.inner_text().strip()
                if text.isdigit():
                    numbers.append(int(text))

            if numbers:
                return max(numbers)
    except Exception as e:
        print("Error al obtener el número total de páginas:", e)
        page.screenshot(path="error_get_total_pages.png")

    return 1  # Valor por defecto si falla

def extract_cars_from_text(text: str) -> list[Car]:
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    blocks = []

    current_block = []
    for line in lines:
        if line.count("•") == 1:
            if current_block:
                blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    valid_blocks = [b for b in blocks if len(b) >= 5]
    parsed_cars = []

    for block in valid_blocks:
        try:
            brand, model = [x.strip() for x in block[0].split("•")]

            year_line = block[1]
            year_str, km_str, version, transmission = [x.strip() for x in year_line.split("•")]

            year = int(year_str)
            km = int(km_str.lower().replace("km", "").replace(".", "").strip())

            price_lines = []
            for i, line in enumerate(block):
                if "$" in line and re.search(r"\d", line):
                    price_lines.append(line)
                elif line.strip() == "$" and i + 1 < len(block):
                    next_line = block[i + 1]
                    if re.search(r"\d", next_line):
                        price_lines.append(next_line)

            price_actual = parse_price(price_lines[0]) if price_lines else 0
            price_original = parse_price(price_lines[1]) if len(price_lines) > 1 else None
            print(block)

            location = next(
                (
                    line for line in reversed(block)
                    if not any(x in line for x in [
                        "$", "Bono Financiando", "Nuevo ingreso",
                        "Precio", "¡Promoción!", "Reservado", "Precio Imbatible"
                    ])
                ),
                "Desconocido"
            )

            car = Car(
                brand=brand,
                model=model,
                year=year,
                km=km,
                version=version,
                transmission=transmission,
                price_actual=price_actual,
                price_original=price_original,
                location=location,
            )
            parsed_cars.append(car)

        except Exception as e:
            print("Error al parsear un auto:", e)
            print(block)

    return parsed_cars

# -------------------- Manejo de bloqueo --------------------

def robust_scraper_attempt(p, proxy_config, max_retries=3):
    for attempt in range(1, max_retries + 1):
        print(f"\n[Intento {attempt}/{max_retries}] usando proxy...")
        try:
            browser = p.chromium.launch(
                headless=True,
                proxy=proxy_config,
                args=["--ignore-certificate-errors"]
            )
            page = browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "es-ES,es;q=0.9",
                    "Referer": "https://www.google.com/"
                },
                viewport={"width": 1280, "height": 800}
            )

            page.goto("https://www.kavak.com/cl/usados", timeout=100000)
            page.mouse.wheel(0, 1000)
            time.sleep(2)

            content = page.content().lower()

            if "request could not be satisfied" in content:
                print("Página bloqueada, reintentando...")
                page.screenshot(path=f"bloqueo_intento_{attempt}.png")
                browser.close()
                continue

            return page, browser

        except Exception as e:
            print(f"Error al cargar la página (intento {attempt}):", e)

    raise RuntimeError("No se pudo acceder al sitio tras múltiples intentos.")

# -------------------- Ejecución principal --------------------

def main():
    all_cars = []

    session_id = random.randint(1000, 9999)
    proxy_config = {
        "server": "http://brd.superproxy.io:22225",
        "username": f"brd-customer-hl_1bde1bb4-zone-residential_proxy1-session-{session_id}",
        "password": "www0ye7kbgs9"
    }

    with sync_playwright() as p:
        try:
            page, browser = robust_scraper_attempt(p, proxy_config)

            total_pages = get_total_pages(page)
            print(f"Total de páginas detectadas: {total_pages}")
        except Exception as e:
            print("Error crítico:", e)
            return

        for page_num in range(1):  # Cambiar por `range(total_pages)` si deseas scrapear todas
            try:
                print(f"Scrapeando página {page_num}...")
                url = f"https://www.kavak.com/cl/usados?page={page_num}"
                page.goto(url, timeout=120000)
                content_selector = ".results_results__container__tcF4_"
                page.wait_for_selector(content_selector, timeout=100000)

                element = page.query_selector(content_selector)
                if element:
                    raw_text = element.inner_text()
                    cars = extract_cars_from_text(raw_text)
                    all_cars.extend(cars)
                else:
                    print(f"No se encontró el contenedor de autos en la página {page_num}.")
                    page.screenshot(path=f"missing_container_page_{page_num}.png")

            except Exception as e:
                print(f"Error al procesar la página {page_num}:", e)
                page.screenshot(path=f"error_page_{page_num}.png")

        browser.close()

    for car in all_cars:
        print(f"{car.brand} {car.model} - {car.price_actual:,} CLP")

    save_to_json(all_cars)

if __name__ == "__main__":
    main()

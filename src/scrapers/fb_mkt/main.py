# fb_crawler ussing session cookies from another browser
from playwright.sync_api import sync_playwright
from dotenv import dotenv_values
from bs4 import BeautifulSoup
import os
import time
import json
import re
# from scrapers.fb_mkt.utils import get_year_brand_model

# Cargar el .env si existe
env_config = {}
if os.path.exists(".env"):
    env_config = dotenv_values(".env")

# Mezclar variables, dando prioridad a las del entorno
config = {**env_config, **os.environ}


def crawl_facebook_marketplace():
    elements = []
    # link original:
    # https://www.facebook.com/marketplace/santiagocl/carros

    initial_url = "https://www.facebook.com/marketplace/"
    min_price = int(
        config["FB_MIN_PRICE"]
    )  # mejor usar un precio minimo para descartar publicaciones raras
    n_scrolls = int(config["FB_N_SCROLLS"])
    wait_between_scrolls = int(config["FB_T_SCROLL"])

    c_user = config["FB_C_USER"]
    xs = config["FB_XS"]
    cookie1 = {
        "name": "c_user",
        "value": c_user,
        "domain": ".facebook.com",
        "path": "/",
    }
    cookie2 = {"name": "xs", "value": xs, "domain": ".facebook.com", "path": "/"}

    # Initialize the session using Playwright.
    with sync_playwright() as p:
        # Open a new browser page.
        browser = p.chromium.launch(
            headless=False,
            # proxy={}
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            permissions=[],
        )
        # Add sesion cookies
        context.add_cookies([cookie1, cookie2])
        page = context.new_page()
        # Navigate to the URL.
        page.goto(initial_url)
        # Wait for the page to load.
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        print("Cargando marketplace")

        # Go to marketplace url and search params
        vehicule_button = page.locator("span", has_text="Vehículos" or "Vehicules")
        vehicule_button.first.click()
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        price_input = page.locator(
            'input[placeholder="Mín."][aria-label="Intervalo mínimo"]'
        )
        price_input.fill(str(min_price))
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        print("Empezando extracción de datos...")
        # Start data extraction
        name_class = "x78zum5.xdt5ytf"
        locator = page.locator(f'div.{name_class}[data-virtualized="false"]')

        # Infinite scroll to the bottom of the page until the loop breaks.
        for _ in range(n_scrolls):
            divs = locator.evaluate_all("els => els.map(el => el.outerHTML)")
            for div in divs:
                elements.append(div)
            page.keyboard.press("End")
            time.sleep(wait_between_scrolls)

        return elements


def save_to_json(data, output_file):
    img_class = (
        "x15mokao x1ga7v0g x16uus16 xbiv7yw xt7dq6l xl1xv1r x6ikm8r x10wlt62 xh8yej3"
    )
    title_class = "x1lliihq x6ikm8r x10wlt62 x1n2onr6"
    price_class = "x193iq5w xeuugli x13faqbe x1vvkbs x1xmvt09 x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x xudqn12 x676frb x1lkfr7t x1lbecb7 x1s688f xzsf02u"
    url_class = "x1i10hfl xjbqb8w x1ejq31n x18oe1m7 x1sy0etr xstzfhl x972fbf x10w94by x1qhh985 x14e42zd x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x14z9mp xat24cr x1lziwak xexx8yu xyri2b x18d9i69 x1c1uobl x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g xkrqix3 x1sur9pj x1s688f x1lku1pv"
    location_class = "x1lliihq x6ikm8r x10wlt62 x1n2onr6 xlyipyv xuxw1ft x1j85h84"
    parsed = dict()
    i = 0
    for d in data:
        try:
            d = re.sub(r"&nbsp;|\xa0|\\|", "", d)
            d = re.sub(r"class=/", "class=", d)
            soup = BeautifulSoup(d, "html.parser")
            image = soup.find("img", class_=img_class)["src"]
            # Get the item title from span.
            title = soup.find("span", title_class).text.strip()
            # Get the item price.
            price = soup.find("span", price_class).text.strip()
            # Get the item URL.
            post_url = soup.find("a", class_=url_class)["href"]
            # Get the item location.
            location_km = soup.find_all("span", location_class)
            location = location_km[0].text.strip()
            km = ""

            if len(location_km) >= 2:
                km = location_km[1].text.strip()

            parsed[i] = {
                "title": title,
                "image": image,
                "price": price,
                "post_url": post_url,
                "location": location,
                "km": km,
            }

            # print(get_year_brand_model(title))
            # print(price_format(price))
            # print(km_format(km))

        except Exception as e:
            print(e)
            # print("error en elemento número: ", i) # generalmente publicaciones sin precio/titulo
            pass
        finally:
            i += 1

    # print("Cantidad de elementos extraidos: ", len(parsed))

    visited = set()
    llaves = list(parsed.keys())
    for val in llaves:  # post processing
        try:
            url = parsed[val]["post_url"]
            if url in visited:
                del parsed[val]
            else:
                visited.add(url)

        except Exception as e:
            print(e)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    with open(
        os.path.join(current_dir, output_file), "w", encoding="utf-8"
    ) as f:  # ojo las tildes y chr especiales
        json.dump(parsed, f, indent=2)

    print("Cantidad total de vehiculos (sin repetidos): ", len(parsed))


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    start = time.time()
    elements = crawl_facebook_marketplace()
    with open(os.path.join(current_dir, "elements.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(elements))
    end = time.time()
    print("Tiempo total de scrapeo: ", end - start)

    # with open(os.path.join(current_dir, "elements.json"), "r", encoding="utf-8") as f:
    #     elements = json.load(f)
    save_to_json(
        elements, "cars.json"
    )  # TO DO: implementar una forma de conectar a la db


if __name__ == "__main__":
    main()

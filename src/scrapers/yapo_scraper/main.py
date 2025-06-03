from playwright.sync_api import sync_playwright
import os
import time
import json
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.models import Car
import re


# obtener los pares de (post_url, img_url) para irlos explorando despues
def scrape_yapo(base_url: str, pages: int):
    car_listing_links = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True
            # , proxy= {}
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
        page.goto(base_url)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        for page_number in range(1, pages + 1):
            print(f"Cargando pagina {page_number}")
            try:
                myUrl = f"{base_url}.{page_number}"
                page.goto(myUrl)
                car_listing_class = "d3-ad-tile d3-ads-grid__item d3-ad-tile--fullwidth d3-ad-tile--bordered d3-ad-tile--feat d3-ad-tile--feat-plat"
                car_list_locator = page.locator(f'div[class="{car_listing_class}"]')
                links_locator = car_list_locator.locator(
                    'a[href^="/autos-usados/"]:not([class])'
                )

                page.wait_for_load_state("domcontentloaded")
                links_list = links_locator.evaluate_all(  # links es una lista de listas (url , img_url)
                    """els => els.map(el => {
                        const href = el.getAttribute('href');
                        const img = el.querySelector('img');
                        const imgSrc = img?.getAttribute('src') || img?.getAttribute('data-src');
                        return [href, imgSrc];
                        })"""
                )
                for url in links_list:
                    car_listing_links.append(tuple(url))

                time.sleep(1)
            except Exception:
                continue
        browser.close()
        return car_listing_links


# ir a todas las publicaciones de a una para obtener todos los detalles
def get_details(base_url: str, links_list: list[tuple[str]]):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            # proxy= {}
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            permissions=[],
        )
        page = context.new_page()
        page.goto(base_url)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(1)
        dict_list = list()
        for link in links_list:
            try:
                attr_dict = dict()
                page.goto(base_url + link[0])
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                car_data = soup.find_all("div", "d3-container d3-property__insight")
                car_desc = soup.find_all("div", "d3-property-details__detail-label")

                # datos del auto
                keys = "Marca Modelo Precio Año Kilómetros Combustible".split(" ")
                for e in car_data:
                    dat = e.get_text().split()
                    result = {}
                    i = 0
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

                # datos adicionales en la descripción del auto
                labels = ["Publicado", "Localización", "Transmisión"]
                for e in car_desc:
                    e = e.get_text().split()
                    if e[0] in labels and len(e) > 1:
                        attr_dict[e[0]] = " ".join(e[1 : len(e)])
                dict_list.append(attr_dict)
                time.sleep(1)
            except Exception as e:
                continue
        browser.close()
        return dict_list


def save_to_json(
    car_dict_list: list[dict],
    links_list: list[tuple[str]],
    default_url: str,
    output_path,
):
    parsed_cars = list()
    for i in range(len(car_dict_list)):
        d = car_dict_list[i]
        post_url = links_list[i][0]
        img_url = links_list[i][1]
        try:
            car = Car(
                brand=d["Marca"],
                model=d["Modelo"],
                year=int(d["Año"]),
                km=re.sub(r"[']", "", d["Kilómetros"]),
                version="",
                transmission=d["Transmisión"],
                price_actual=int(re.sub(r"[\$\.]", "", d["Precio"].split()[0])),
                price_original=-1,
                location=d["Localización"],
                fuel_type=d["Combustible"],
                post_url=default_url + post_url,
                img_url=img_url,
                data_source="yapo",
                published_at=datetime.strptime(d["Publicado"], "%d/%m/%Y").strftime(
                    "%d/%m/%Y"
                ),
                scraped_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            parsed_cars.append(car.model_dump())
        except KeyError:  # llave no encontrada
            continue
    with open(os.path.join(current_dir, output_path), "w", encoding="utf-8") as f:
        f.write(json.dumps(parsed_cars))
    print(f"Se guardaron {len(parsed_cars)} en {output_path}")


if __name__ == "__main__":
    try:
        base_url = "https://public-api.yapo.cl/autos-usados/region-metropolitana"
        default_url = "https://public-api.yapo.cl"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        n_pages = 1
        i1 = time.time()
        links_list = scrape_yapo(base_url, n_pages)
        i2 = time.time()
        print("numero de paginas: ", n_pages)
        print("tiempo de scrapeo por pagina: ", (i2 - i1) / n_pages)
        with open(
            os.path.join(current_dir, "link_list.json"), "w", encoding="utf-8"
        ) as f:
            f.write(json.dumps(links_list))

        i1 = time.time()
        car_dict_list = get_details(default_url, links_list)
        i2 = time.time()
        print(
            "tiempo de obtener detalles publicaciones por pagina: ", (i2 - i1) / n_pages
        )
        with open(
            os.path.join(current_dir, "car_dict_list.json"), "w", encoding="utf-8"
        ) as f:
            f.write(json.dumps(car_dict_list))
        save_to_json(car_dict_list, links_list, default_url, "autos.json")

    except Exception as e:
        print(e)

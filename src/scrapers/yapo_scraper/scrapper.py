#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from schema import CarSchema
from pydantic import ValidationError
from bs4 import BeautifulSoup as soup
import pandas as pd
import time

def init_browser():
    options = Options()
    #options.add_argument('--headless')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument(f'--user-data-dir={tempfile.gettempdir()}/chrome-user-data')
    return webdriver.Chrome(options=options)

def scrape_yapo(browser, pages=5):
    car_info_list = []
    base_url = 'https://www.yapo.cl/autos-usados/region-metropolitana'
    default_url = 'https://www.yapo.cl'
    count = 0

    for page_number in range(1, pages + 1):
        try:
            # -------------------------------------------------
            myUrl = f'{base_url}.{page_number}'
            browser.get(myUrl)
            print(f"Scraping page {page_number}...")

            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#currentlistings"))
            )

            pageSoup = soup(browser.page_source, 'html.parser')
            car_list = pageSoup.select('#currentlistings > div.d3-ads-grid.d3-ads-grid--category-list')
            if not car_list:
                raise ValueError(f"Car list container not found on page {page_number}")
            # -------------------------------------------------
            for car in car_list[0].find_all('div', class_='d3-ad-tile'):
                try:
                    count += 1
                    """print("-----------------------------------------------\n")
                    print(f"-----------------{count}-----------------------\n")
                    print("-----------------------------------------------\n")"""
                    # -------------------------------------------------
                    relative_link = car.find('a', class_='d3-ad-tile__description')['href']
                    car_link = default_url + relative_link

                    short_description = car.find('div',
                                                 class_='d3-ad-tile__short-description').text.strip() if car.find(
                        'div', class_='d3-ad-tile__short-description') else 'N/A'
                    car_title = car.find('span', class_='d3-ad-tile__title').text.strip() if car.find('span',
                                                                                                      class_='d3-ad-tile__title') else 'N/A'
                    price = car.find('div', class_='d3-ad-tile__price').text.strip() if car.find('div',
                                                                                                 class_='d3-ad-tile__price') else 'N/A'
                    details = car.find('ul', class_='d3-ad-tile__details')
                    year = details.find('li', class_='d3-ad-tile__details-item').text.strip() if details else 'N/A'
                    mileage_items = details.find_all('li', class_='d3-ad-tile__details-item')
                    mileage = mileage_items[3].text.strip() if len(mileage_items) > 3 else 'N/A'

                    location = car.find('div', class_='d3-ad-tile__location').text.strip() if car.find('div',                                                                             class_='d3-ad-tile__location') else 'N/A'
                    # -------------------------------------------------
                    needs_description = False
                    needs_images = False

                    if short_description.endswith('...'):
                        needs_description = True

                    # TODO: Fix implementation
                    images_container = car.find('div', class_='d3-ad-tile__cover')
                    if not images_container.find('div', class_='d3-photos-carousel'):
                        needs_images = True

                    if needs_description: #or needs_images:
                        # -------------------------------------------------
                        print(f"Entrando al detalle de {car_link} para extraer info adicional...")

                        browser.get(car_link)
                        time.sleep(2)
                        # -------------------------------------------------
                        if needs_description:
                            try:
                                full_description_element = browser.find_element(By.CSS_SELECTOR,
                                                                                'div.d3-property-about__text')
                                full_description = full_description_element.text.strip()
                                #print("Descripción completa extraída.")
                                #print(full_description)
                            except Exception as e:
                                full_description = 'N/A'
                                print(f"Error extrayendo descripción completa: {e}")
                        else:
                            full_description = short_description

                        # -------------------------------------------------
                        if needs_images:
                            #TODO: Fix implementation
                            try:
                                images_elements = browser.find_elements(By.CSS_SELECTOR,
                                                                        'div.d3-property_hero-carousel img')
                                image_urls = [img.get_attribute('src') for img in images_elements if
                                              img.get_attribute('src')]
                                print(f"{len(image_urls)} imágenes extraídas.")
                            except Exception as e:
                                image_urls = []
                                print(f"Error extrayendo imágenes: {e}")
                        else:
                            image_urls = []

                    else:
                        full_description = short_description
                        image_urls = []

                    # ---------------------------------------------

                    car_data = {
                        "Link": car_link,
                        "Descripcion": full_description,
                        "Marca_y_Modelo": car_title,
                        "Precio": price,
                        "Año": year,
                        "Kilometraje": mileage,
                        "Ubicacion": location
                    }

                    validated_car = CarSchema(**car_data)
                    car_info_list.append(validated_car)

                except ValidationError as e:
                    print(f"Error de validación en {car_link}: {e}")
                    continue

                except Exception as e:
                    print(f"Error general en el scraping pagina {page_number}, auto {car_link}: {e}")
                    continue

            print(f"Page {page_number} scraped successfully")

        except Exception as e:
            print(f"Error during scraping page {page_number}: {e}")
            continue

    print('Total cars scraped:', count)
    return car_info_list

def save_data(car_info_list, output_path='./output/car_data.csv'):
    car_info = pd.DataFrame(car_info_list)
    car_info.to_csv(output_path, index=False)
    print(f"Data saved to {output_path}")
    print(car_info)

if __name__ == "__main__":
    try:
        browser = init_browser()
        print("WebDriver initialized successfully")

        car_info_list = scrape_yapo(browser, pages=5)
        save_data(car_info_list)

    except Exception as e:
        print(f"Fatal error: {e}")

    finally:
        browser.quit()
        print("Browser closed")

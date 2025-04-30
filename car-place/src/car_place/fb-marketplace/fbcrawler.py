# fb_crawler ussing session cookies from another browser 
from random import randint
from playwright.sync_api import sync_playwright
from reader import save_to_json
import os
import sys
import time
import json

def crawl_facebook_marketplace(session_file_path):
  elements = []
  # link original:
  # https://www.facebook.com/marketplace/santiagocl/carros

  
  initial_url = "https://www.facebook.com/marketplace/"
  min_price = 100000 # mejor usar un precio minimo para descartar publicaciones raras
  n_scrolls = 10
  wait_between_scrolls = 6

  with open(session_file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
  c_user = lines[0].split("=")[1].strip("\n")
  xs = lines[1].split("=")[1].strip("\n")
  cookie1 = {'name':'c_user', 'value': c_user, 'domain': '.facebook.com', 'path': "/"}
  cookie2 = {'name':'xs', 'value': xs, 'domain': '.facebook.com', 'path': "/"}

  # Initialize the session using Playwright.
  with sync_playwright() as p:
    # Open a new browser page.
    browser = p.chromium.launch(headless=False 
                                # , proxy= { por si queremos usar proxy

                                # }
                                )
    context = browser.new_context()    
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
    vehicule_button = page.locator("span", has_text="Vehículos" or "Vehicules").first.click()
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)
    price_input = page.locator('input[placeholder="Mín."][aria-label="Intervalo mínimo"]').fill(str(min_price))
    page.keyboard.press('Enter')
    page.wait_for_load_state("domcontentloaded")
    time.sleep(10)

    print("Empezando extracción de datos...")
    # Start data extraction
    name_class = "x78zum5.xdt5ytf"
    locator = page.locator(f'div.{name_class}[data-virtualized="false"]')
    
    # Infinite scroll to the bottom of the page until the loop breaks.
    for _ in range(n_scrolls):
      divs = locator.evaluate_all("els => els.map(el => el.outerHTML)")
      for div in divs:
        elements.append(div)
      page.keyboard.press('End')
      time.sleep(wait_between_scrolls)

    return elements
  
if __name__ == "__main__":
  current_dir = os.path.dirname(os.path.abspath(__file__))
  start = time.time()
  elements = crawl_facebook_marketplace(os.path.join(current_dir, 'fb_sessions.txt'))
  with open(os.path.join(current_dir, "elements.json"), 'w', encoding='utf-8') as f:
    f.write(json.dumps(elements))
  end = time.time()
  print("Tiempo total de scrapeo: ", end - start)
  save_to_json(elements, "cars.json")
  sys.exit(0)
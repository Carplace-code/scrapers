import json
from bs4 import BeautifulSoup
from pprint import pprint
import re
import os

def save_to_json(data, output_file):
  img_class = 'x168nmei x13lgxp2 x5pf9jr xo71vjh xt7dq6l xl1xv1r x6ikm8r x10wlt62 xh8yej3'
  title_class = 'x1lliihq x6ikm8r x10wlt62 x1n2onr6'
  price_class = 'x193iq5w xeuugli x13faqbe x1vvkbs x10flsy6 x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x x1tu3fi x3x7a5m x1lkfr7t x1lbecb7 x1s688f xzsf02u'
  url_class = 'x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g xkrqix3 x1sur9pj x1s688f x1lku1pv'
  location_class = 'x1lliihq x6ikm8r x10wlt62 x1n2onr6 xlyipyv xuxw1ft'

  parsed = dict()
  i = 0
  for d in data:
    try: 
      d = re.sub(r'&nbsp;|\xa0', '', d)
      d = re.sub(r'class=/', 'class=', d)
      soup = BeautifulSoup(d, 'html.parser')
      image = soup.find('img', class_=img_class)['src']
      # Get the item title from span.
      title = soup.find('span', title_class).text.strip()
      # Get the item price.
      price = soup.find('span', price_class).text.strip() # ver que pasa cuando dice gratis
      # Get the item URL.
      post_url = soup.find('a', class_= url_class)['href']
      # Get the item location.
      location_km = soup.find_all('span', location_class)
      location = location_km[0].text.strip()
      km = ''

      if len(location_km) >= 2:
        km = location_km[1].text.strip()
      
      parsed[i] = {
        'title': title,
        'image': image,
        'price': price,
        'post_url': post_url,
        'location': location,
        'km': km
      }
      
    except Exception as e:
      # print(e)
      # print("error en elemento número: ", i) # generalmente publicaciones sin precio/titulo
      pass
    finally:
      i += 1

  # print("Cantidad de elementos extraidos: ", len(parsed))

  visited = set()
  k = 0
  llaves = list(parsed.keys())
  for val in llaves: # post processing
    try:
      url = parsed[val]["post_url"]
      if url in visited:
        del parsed[val]
      else:
        visited.add(url)

    except Exception as e:
      print(e)

  current_dir = os.path.dirname(os.path.abspath(__file__))
  with open(os.path.join(current_dir, output_file), 'w', encoding='utf-8') as f: # ojo las tildes y chr especiales
    json.dump(parsed, f, indent = 2)

  print("Cantidad total de vehiculos (sin repetidos): ", len(parsed))

if __name__ == "__main__":
  
  save_to_json([], "cars.json")

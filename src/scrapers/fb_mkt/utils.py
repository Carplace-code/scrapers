import re


def km_format(km_string: str):
    try:
        km = ""
        km_list = km_string.split(" ")
        km = km_list[0]

        if km[-1] == "k":
            km = re.sub(r"k", "", km)
        else:
            return None
        km = int(km)
        if km_list[1] == "km":
            return km * 1000
        elif km_list[1] == "millas":
            return km * 1609.34
        else:
            return None
    except ValueError or Exception:
        return None


# obtener datos desde el título (solo contando en casos donde es posible)
def get_year_brand_model(title_string: str):
    try:
        title_list = title_string.split(" ")
        year = int(title_list[0])
        brand = title_list[1]
        model = " ".join(title_list[2:])
        return year, brand, model
    except Exception:
        return None


def price_format(price_string: str):
    try:
        price = int(re.sub(r"\.|\$", "", price_string))
        return price
    except ValueError:
        return None

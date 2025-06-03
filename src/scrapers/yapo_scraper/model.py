from pydantic import BaseModel


class Car(BaseModel):
    brand: str
    model: str
    year: int
    km: int
    version: str | None
    transmission: str | None
    price_actual: int
    price_original: int | None
    location: str
    fuel_type: str | None
    post_url: str
    img_url: str | None
    data_source: str
    published_at: str | None
    scraped_at: str | None


# datetime.now()
# kavak original model
# car = Car(
#             brand=brand,
#             model=model,
#             year=year,
#             km=km,
#             version=version,
#             transmission=transmission,
#             price_actual=price_actual,
#             price_original=price_original,
#             location=location,
#         )

# kavak model
# class Car(BaseModel):
#     brand: str
#     model: str
#     year: int
#     km: int
#     version: str
#     transmission: str
#     price_actual: int
#     price_original: int | None
#     location: str
#     post_url: str
#     img_url: str | None

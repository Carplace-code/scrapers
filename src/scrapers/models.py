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

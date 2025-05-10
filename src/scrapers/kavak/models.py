# src/kavak_scraper/models.py
from pydantic import BaseModel


class Car(BaseModel):
    brand: str
    model: str
    year: int
    km: int
    version: str
    transmission: str
    price_actual: int
    price_original: int | None
    location: str

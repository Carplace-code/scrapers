from pydantic import BaseModel


class Car(BaseModel):
    brand: str
    model: str
    year: int
    km: int
    version: str | None
    transmission: str | None
    priceActual: int
    priceOriginal: int | None
    location: str
    fuelType: str | None
    postUrl: str
    imgUrl: str | None
    dataSource: str
    publishedAt: str | None
    scrapedAt: str | None


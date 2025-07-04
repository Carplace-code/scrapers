from dotenv import dotenv_values
import os
from scrapers.models import Car
from pathlib import Path
import json
import requests


def load_env():
    env_config = {}
    if os.path.exists(".env"):
        env_config = dotenv_values(".env")
    config = {**env_config, **os.environ}
    return config


# Enums para normalización
class FuelTypeEnum:
    GAS = "gas"
    DIESEL = "diesel"
    ELECTRICITY = "electricity"
    HYBRID = "hybrid"
    OTHER = "other"


class TransmissionTypeEnum:
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    OTHER = "other"


def normalize_fuel_type(raw_fuel: str | None) -> str | None:
    if not raw_fuel:
        return FuelTypeEnum.OTHER
    raw = raw_fuel.lower()
    if "bencina" in raw or "gasolina" in raw or "gas" in raw:
        return FuelTypeEnum.GAS
    if "diesel" in raw:
        return FuelTypeEnum.DIESEL
    if "eléctrico" in raw or "electric" in raw:
        return FuelTypeEnum.ELECTRICITY
    if "híbrido" in raw or "hybrid" in raw:
        return FuelTypeEnum.HYBRID
    return FuelTypeEnum.OTHER


def normalize_transmission(raw_trans: str | None) -> str:
    if not raw_trans:
        return TransmissionTypeEnum.OTHER
    raw = raw_trans.lower()
    if "automático" in raw or "automatic" in raw or "automática" in raw:
        return TransmissionTypeEnum.AUTOMATIC
    if "manual" in raw:
        return TransmissionTypeEnum.MANUAL
    return TransmissionTypeEnum.OTHER


def save_to_json(cars_data: list[Car], filename: str = "cars.json") -> None:
    json_data = [car.model_dump() for car in cars_data]
    Path(filename).write_text(
        json.dumps(json_data, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSuccesfully saved {len(cars_data)} cars in {filename}")


def post_car(car: Car, backend_url):
    try:
        if car:
            response = requests.post(backend_url, json=car, timeout=10)
            # print(f"Status Code: {response.status_code}")
            # print(f"Response Text: {response.text}")
            if response.status_code in (200, 201):
                print(f"Auto publicado correctamente: {car.brand} {car.model}")
            else:
                print(f"Error {response.status_code} al publicar : {response.text}")
            return response
        else:
            return None
    except requests.exceptions.RequestException:
        raise requests.exceptions.RequestException()
    except Exception as e:
        raise Exception(f"Error (post_car): {e}")

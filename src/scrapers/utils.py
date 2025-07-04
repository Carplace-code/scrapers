from dotenv import dotenv_values
import os


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
        return None
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

from pydantic import BaseModel, HttpUrl
from typing import Optional

class CarSchema(BaseModel):
    Link: HttpUrl
    Descripcion: str
    Marca_y_Modelo: str
    Precio: str
    Año: str
    Kilometraje: str
    Ubicacion: str

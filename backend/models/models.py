from pydantic import BaseModel
from typing import Optional

class Location(BaseModel):
    id: str
    locationName: str
    latitude: float
    longitude: float

class CreateLocationModel(BaseModel):
    locationName: str
    latitude: float
    longitude: float
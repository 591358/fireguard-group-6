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

class UpdateLocationModel(BaseModel):
    locationName: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    

class User(BaseModel):
    id: str
    userName: str
    password: str

class CreateUserModel(BaseModel):
    userName: str
    password: str

class UpdateUserModel(BaseModel):
    userName: str
    password: str
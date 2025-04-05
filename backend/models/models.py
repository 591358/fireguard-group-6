from pydantic import BaseModel
from typing import List, Optional

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
    username: str
    email: str
    roles: List[str]

class CreateUser(BaseModel):
    username: str
    password: str
    email:  str

class TokenData(BaseModel):
    username: str
    roles: List[str]
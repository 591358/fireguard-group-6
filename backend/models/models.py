from datetime import datetime
from typing import List, Optional

from mongomock import ObjectId
from pydantic import BaseModel, Field


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
    _id: ObjectId
    username: str
    email: str
    roles: List[str] = Field(default_factory=list)
    keycloak_user_id: str


class CreateUser(BaseModel):
    username: str
    password: str
    email: str


class UpdateUser(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

    class Config:
        extra = "forbid"


class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    password: Optional[str] = None

    class Config:
        extra = "forbid"


class TokenData(BaseModel):
    username: str
    roles: List[str]


class FireRisk(BaseModel):
    locationName: str
    time: datetime
    risk_value: float

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

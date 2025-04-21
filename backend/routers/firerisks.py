import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection

from backend.models.models import Location
from backend.mongo import get_fire_risk_collection, get_location_collection, serialize_document
from backend.services.fire_risk_service import FireRiskService
from dynamic_frcm.src.frcm.datamodel.model import Location as FrcmLocation


def convert_backend_location_to_frcm(backend_location: Location) -> FrcmLocation:
    return FrcmLocation(latitude=backend_location.latitude, longitude=backend_location.longitude)


def convert_frcm_location_to_backend(frcm_location: FrcmLocation, id: str, locationName: str) -> Location:
    return Location(id=id, locationName=locationName, latitude=frcm_location.latitude, longitude=frcm_location.longitude)


location_fields_map = {
    "id": "_id",
    "locationName": "locationName",
    "latitude": "latitude",
    "longitude": "longitude",
}

fire_risk_fields = {"id": "_id", "location": "location", "firerisk": "firerisk"}
firerisk_router = APIRouter(prefix="/firerisks", tags=["Fire Risk"])

logger = logging.getLogger(__name__)


async def find_fire_risk(location_name: str, time: datetime, fire_risk_collection: AsyncIOMotorCollection):
    doc = await fire_risk_collection.find_one({"locationName": location_name, "time": time})
    return serialize_document(doc, fire_risk_fields) if doc else None


async def get_location_by_name(
    location_name: str,
    location_collection: AsyncIOMotorCollection,
) -> Optional[Location]:
    doc = await location_collection.find_one({"locationName": location_name})
    doc = serialize_document(doc, location_fields_map)
    return Location(**doc) if doc else None


async def calculate_fire_risk_prediction(location: Location, start_time: Optional[str], end_time: Optional[str]):
    """
    Calculates fire risk prediction for a given location based on current or historical weather data.

    Args:
        location (Location): The location for which fire risk is predicted.
        start_time (Optional[str]): The start time for the prediction period. If not provided,
                                    the current weather is used.
        end_time (Optional[str]): The end time for the prediction period. If not provided,
                                  the current weather is used.

    Returns:
        WeatherData: The weather data and calculated fire risk for the location.

    Notes:
        - If both `start_time` and `end_time` are provided, the risk is calculated for the specified period.
        - If either `start_time` or `end_time` is missing, the current weather is used for prediction.
    """

    fire_risk_service = FireRiskService()
    backend_location = convert_backend_location_to_frcm(location)

    if start_time and end_time:
        weather_data = fire_risk_service.compute_fire_risk_period(backend_location, start_time, end_time)
    else:
        weather_data = fire_risk_service.compute_fire_risk_now(backend_location)
    return weather_data


@firerisk_router.get("/")
async def predict(
    location_name: str,
    time: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    fire_risk_collection: AsyncIOMotorCollection = Depends(get_fire_risk_collection),
    location_collection: AsyncIOMotorCollection = Depends(get_location_collection),
):
    try:
        time_now = datetime.datetime.fromisoformat(time) if time else datetime.datetime.now()
    except ValueError:
        logger.error(f"Invalid time format: {time}")
        raise HTTPException(status_code=400, detail="Invalid time format. Please use ISO format.")

    fire_risk = await find_fire_risk(location_name, time_now, fire_risk_collection)

    if fire_risk:
        logger.info(f"Fire risk found for location: {location_name}")
        return fire_risk

    location = await get_location_by_name(location_name, location_collection)
    if not location:
        logger.error(f"Location not found: {location_name}")
        raise HTTPException(status_code=404, detail="Location not found")

    fire_risk = await calculate_fire_risk_prediction(location, start_time, end_time)
    return fire_risk

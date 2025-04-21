from fastapi import APIRouter, Depends, HTTPException
from mongomock import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from backend.auth import has_role
from backend.models.models import CreateLocationModel, Location, UpdateLocationModel
from backend.mongo import get_location_collection, serialize_document

location_fields_map = {
    "id": "_id",
    "locationName": "locationName",
    "latitude": "latitude",
    "longitude": "longitude",
}
locations_router = APIRouter(prefix="/locations", tags=["Locations"])


@locations_router.post(
    "/",
    response_model=Location,
    dependencies=[Depends(has_role("User"))],
)
async def create_location(
    location: CreateLocationModel,
    collection: AsyncIOMotorCollection = Depends(get_location_collection),
):
    body = location.model_dump()
    result = await collection.insert_one(body)
    created_location = await collection.find_one({"_id": result.inserted_id})
    if not created_location:
        raise HTTPException(status_code=500, detail="Failed to retrieve inserted document")

    return serialize_document(created_location, location_fields_map)


@locations_router.get(
    "/{location_id}",
    dependencies=[Depends(has_role("User"))],
)
async def get_location_by_id(
    location_id: str,
    collection: AsyncIOMotorCollection = Depends(get_location_collection),
):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")

    result = await collection.find_one({"_id": object_id})
    if not result:
        raise HTTPException(status_code=404, detail="Location not found")

    return serialize_document(result, location_fields_map)


@locations_router.get(
    "/",
    response_model=list[Location],
    dependencies=[Depends(has_role("User"))],
)
async def get_locations(
    collection: AsyncIOMotorCollection = Depends(get_location_collection),
):
    raw_docs = await collection.find().to_list(length=None)
    return [serialize_document(doc, location_fields_map) for doc in raw_docs]


@locations_router.put(
    "/{location_id}",
    response_model=Location,
    dependencies=[Depends(has_role("User"))],
)
async def update_location(
    location_id: str,
    data: UpdateLocationModel,
    collection: AsyncIOMotorCollection = Depends(get_location_collection),
):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    result = await collection.update_one(
        {"_id": object_id},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Location not found")

    updated_location = await collection.find_one({"_id": object_id})
    return serialize_document(updated_location, location_fields_map)

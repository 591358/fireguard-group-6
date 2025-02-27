import os
from typing import Union
from fastapi import FastAPI, HTTPException
from mongo import location_collection
from models.models import Location, CreateLocationModel
from fastapi import FastAPI, Request
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def serialize_document(doc):
    return {
        "id": str(doc["_id"]),
        "locationName": doc["locationName"],
        "latitude": doc["latitude"],
        "longitude": doc["longitude"],
    }

app = FastAPI()


app = FastAPI()

@app.post("/locations")
async def create_location(location: CreateLocationModel):
    body = location.model_dump()
    result = location_collection.insert_one(body)
    created_location = location_collection.find_one({"_id": result.inserted_id})
    if not created_location:
        raise HTTPException(status_code=500, detail="Failed to retrieve inserted document")
    
    return serialize_document(created_location)

@app.get("/location/{location_id}")
async def get_location_by_id(location_id: str):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")
    result = location_collection.find_one(({"_id":object_id}))
    if not result:
        raise HTTPException(status_code=500, detail="Could not retrieve document")
    
    return serialize_document(result)

@app.get("/locations", response_model=list[Location])
async def get_locations():
    documents = location_collection.find()
    return [serialize_document(doc) for doc in documents]
    

@app.get("/")
def read_root():
    return "test"


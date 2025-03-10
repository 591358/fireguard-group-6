import os
from typing import Union
from fastapi import Depends, FastAPI, HTTPException
from backend.keyCloakUtils import check_role, decode_jwt
from backend.mongo import location_collection
from backend.models.models import Location, CreateLocationModel, UpdateLocationModel
from pymongo.collection import Collection
from fastapi import FastAPI, Request
from fastapi_keycloak_middleware import KeycloakConfiguration, setup_keycloak_middleware, CheckPermissions,AuthorizationMethod
from bson import ObjectId
from dotenv import load_dotenv
import logging


app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


keycloak_config = KeycloakConfiguration(
    url=os.getenv("KEYCLOAK_URL"),
    realm=os.getenv("REALM_NAME"),
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
)

setup_keycloak_middleware(
     app,
     keycloak_configuration=keycloak_config,
 )

def serialize_document(doc):
    return {
        "id": str(doc["_id"]),
        "locationName": doc["locationName"],
        "latitude": doc["latitude"],
        "longitude": doc["longitude"],
    }

def get_location_collection() -> Collection:
    return location_collection


@app.get("/user")
async def user_route(request: Request):
    user = await check_role(request, ["protected"])
    return {"message": f"Hello {user['preferred_username']}, you are a user"}

@app.get("/admin")
async def user_route(request: Request):
    user = await check_role(request, ["admin"])
    return {"message": f"Hello {user['preferred_username']}, you are an admin"}


@app.post("/locations", response_model=Location)
async def create_location(location: CreateLocationModel, collection: Collection = Depends(get_location_collection)):
    body = location.model_dump()
    result = collection.insert_one(body)
    created_location = collection.find_one({"_id": result.inserted_id})
    if not created_location:
        raise HTTPException(status_code=500, detail="Failed to retrieve inserted document")
    
    return serialize_document(created_location)

@app.get("/location/{location_id}")
async def get_location_by_id(location_id: str, collection: Collection = Depends(get_location_collection)):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")
    result = collection.find_one(({"_id": object_id}))
    if not result:
        raise HTTPException(status_code=500, detail="Could not retrieve document")
    
    return serialize_document(result)

@app.get("/locations", response_model=list[Location])
async def get_locations(collection: Collection = Depends(get_location_collection)):
    documents = collection.find()
    return [serialize_document(doc) for doc in documents]
    
@app.put("/location/{location_id}", response_model=Location)
async def update_location(location_id: str, data: UpdateLocationModel, collection: Collection = Depends(get_location_collection)):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    data = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    
    if not data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")
    
    result = collection.update_one({"_id": object_id}, {"$set": data})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Location not found")
    
    updated_location = collection.find_one({"_id": object_id})
    return serialize_document(updated_location)
    
    

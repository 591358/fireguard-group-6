import logging
import os
import sys

sys.path.append("/app/dynamic_frcm/src")
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from mongomock import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from backend.app import app
from backend.auth import has_role, validate_token
from backend.models.models import CreateLocationModel, Location, TokenData, UpdateLocationModel
from backend.mongo import get_location_collection, serialize_document

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
load_dotenv()
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
REALM_NAME = os.getenv("REALM_NAME")
CLIENT_ID = os.getenv("CLIENT_ID")
TESTING = os.getenv("TESTING") == "True"

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
    auto_error=False,
)
if not TESTING:

    async def get_current_user(token: str = Depends(oauth2_scheme)):
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return await validate_token(token)

else:

    async def get_current_user(token: str = Depends(oauth2_scheme)):
        return TokenData(username="test_user", roles=["Admin", "User"])


location_fields_map = {
    "id": "_id",
    "locationName": "locationName",
    "latitude": "latitude",
    "longitude": "longitude",
}


@app.get("/public")
async def public_endpoint():
    return {"message": "This is a public endpoint accessible to everyone."}


@app.get("/protected")
async def protected_endpoint(current_user: TokenData = Depends(get_current_user)):
    return {
        "message": f"Hello {current_user.username}, you are authenticated!",
        "roles": current_user.roles,
    }


@app.post("/locations", response_model=Location, dependencies=[Depends(has_role("User"))])
async def create_location(location: CreateLocationModel, collection: AsyncIOMotorCollection = Depends(get_location_collection)):
    body = location.model_dump()
    result = await collection.insert_one(body)
    created_location = await collection.find_one({"_id": result.inserted_id})
    if not created_location:
        raise HTTPException(status_code=500, detail="Failed to retrieve inserted document")

    return serialize_document(created_location, location_fields_map)


@app.get("/location/{location_id}", dependencies=[Depends(has_role("User"))])
async def get_location_by_id(location_id: str, collection: AsyncIOMotorCollection = Depends(get_location_collection)):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")
    result = await collection.find_one(({"_id": object_id}))
    if not result:
        raise HTTPException(status_code=500, detail="Could not retrieve document")

    return serialize_document(result, location_fields_map)


@app.get("/locations", response_model=list[Location], dependencies=[Depends(has_role("User"))])
async def get_locations(collection: AsyncIOMotorCollection = Depends(get_location_collection)):
    documents = await collection.find()
    return [serialize_document(doc, location_fields_map) async for doc in documents]


@app.put("/location/{location_id}", response_model=Location, dependencies=[Depends(has_role("User"))])
async def update_location(location_id: str, data: UpdateLocationModel, collection: AsyncIOMotorCollection = Depends(get_location_collection)):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    data = {k: v for k, v in data.model_dump(exclude_unset=True).items()}

    if not data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    result = await collection.update_one({"_id": object_id}, {"$set": data})

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Location not found")

    updated_location = await collection.find_one({"_id": object_id})
    return serialize_document(updated_location, location_fields_map)

import os
from fastapi import Depends, FastAPI, HTTPException
from backend.keyCloakUtils import check_role
from backend.mongo import location_collection,user_collection
from backend.models.models import Location, CreateLocationModel, UpdateLocationModel, User,CreateUserModel
from pymongo.collection import Collection
from fastapi import FastAPI, Request
from fastapi_keycloak_middleware import KeycloakConfiguration, setup_keycloak_middleware
from bson import ObjectId
from dotenv import load_dotenv
import logging


app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


if os.getenv("TESTING") != "True":
    keycloak_config = KeycloakConfiguration(
        url=os.getenv("KEYCLOAK_URL"),
        realm=os.getenv("REALM_NAME"),
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        exclude_patterns=["/users"]  # explicitly exclude this endpoint from auth

    )
    setup_keycloak_middleware(app, keycloak_configuration=keycloak_config)

user_fields_map = {
    "id": "_id",
    "userName": "userName",
    "password": "password",
}

location_fields_map = {
    "id": "_id",
    "locationName": "locationName",
    "latitude": "latitude",
    "longitude": "longitude",
}
def serialize_document(doc, fields_map):
    """
    Generic function to serialize MongoDB document.
    
    Args:
        doc (dict): The MongoDB document to serialize.
        fields_map (dict): A mapping of the field names to be serialized for the document.
    
    Returns:
        dict: The serialized document with the specified fields.
    """
    serialized_doc = {}
    for field, field_name in fields_map.items():
        serialized_doc[field] = str(doc.get(field_name)) if doc.get(field_name) else None
    return serialized_doc


def get_location_collection() -> Collection:
    return location_collection

def get_user_collection() -> Collection:
    return user_collection

@app.get("/users", response_model=list[User])
async def get_users(collection: Collection = Depends(get_user_collection)):
    documents = collection.find()
    return [serialize_document(doc, user_fields_map) for doc in documents]


@app.delete("/user/{user_id}", response_model=dict)
async def delete_user(user_id: str, collection: Collection = Depends(get_user_collection)):
    try:
        object_id = ObjectId(user_id)
    except Exception as e:
        logger.error(f"Error converting user_id to ObjectId: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid id format")
    res = collection.delete_one({"_id": object_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"detail": "User deleted successfully"}


@app.post("/users", response_model=User)
async def create_user(user: CreateUserModel, collection: Collection = Depends(get_user_collection)):
    body = user.model_dump()
    result = collection.insert_one(body)
    created_user = collection.find_one({"_id": result.inserted_id})
    if not created_user:
        raise HTTPException(status_code=500, detail="Failed to retrieve inserted document")
    return serialize_document(created_user, user_fields_map)

# @app.get("/user")
# async def user_route(request: Request):
#     user = await check_role(request, ["protected"])
#     return {"message": f"Hello {user['preferred_username']}, you are a user"}

# @app.get("/admin")
# async def user_route(request: Request):
#     user = await check_role(request, ["admin"])
#     return {"message": f"Hello {user['preferred_username']}, you are an admin"}


@app.post("/locations", response_model=Location)
async def create_location(location: CreateLocationModel, collection: Collection = Depends(get_location_collection)):
    body = location.model_dump()
    result = collection.insert_one(body)
    created_location = collection.find_one({"_id": result.inserted_id})
    if not created_location:
        raise HTTPException(status_code=500, detail="Failed to retrieve inserted document")
    
    return serialize_document(created_location,location_fields_map)

@app.get("/location/{location_id}")
async def get_location_by_id(location_id: str, collection: Collection = Depends(get_location_collection)):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")
    result = collection.find_one(({"_id": object_id}))
    if not result:
        raise HTTPException(status_code=500, detail="Could not retrieve document")
    
    return serialize_document(result, location_fields_map)

@app.get("/locations", response_model=list[Location])
async def get_locations(collection: Collection = Depends(get_location_collection)):
    documents = collection.find()
    return [serialize_document(doc, location_fields_map) for doc in documents]
    
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
    return serialize_document(updated_location, location_fields_map)
    
    

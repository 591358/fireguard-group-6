import os
from typing import Collection, List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from mongomock import ObjectId
from backend.mongo import get_location_collection, get_user_collection, location_collection, user_collection
from backend.auth import get_admin_token, has_role, validate_token
from backend.create_user import (assign_role_to_user, create_new_user,
                                 create_user_in_db)
from backend.models.models import (CreateLocationModel, CreateUser, Location,
                                   TokenData, UpdateLocationModel, User)
from backend.mongo import (serialize_document)

load_dotenv()
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
REALM_NAME = os.getenv("REALM_NAME")
CLIENT_ID = os.getenv("CLIENT_ID")
TESTING = os.getenv("TESTING") == "True"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
    auto_error=False
)
app = FastAPI()
if not TESTING:
    async def get_current_user(token: str = Depends(oauth2_scheme)):
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return await validate_token(token)
else:
    async def get_current_user(token: str = Depends(oauth2_scheme)): 
        return TokenData(username="test_user", roles=["Admin", "User"])


@app.get("/public")
async def public_endpoint():
    return {"message": "This is a public endpoint accessible to everyone."}

@app.get("/protected")
async def protected_endpoint(current_user: TokenData = Depends(get_current_user)):
    return {
        "message": f"Hello {current_user.username}, you are authenticated!",
        "roles": current_user.roles,
    }

@app.post("/create_user/")
async def create_user_endpoint(user: CreateUser):
    access_token = await get_admin_token()
    created_user = await create_new_user(user, access_token)
    if "id" not in created_user:
        raise HTTPException(status_code=400, detail="User ID not found in Keycloak response")
    stored_user = await create_user_in_db(user)
    await assign_role_to_user(created_user["id"], "User", access_token)
    return {"message": "User created and role assigned", "user": created_user, "stored in db": stored_user}

@app.get("/users", response_model=List[User], dependencies=[Depends(has_role("Admin"))])
async def get_all_users(collection: Collection = Depends(get_user_collection)):
    return collection.find()


@app.post("/locations", response_model=Location, dependencies=[Depends(has_role("User"))])
async def create_location(location: CreateLocationModel, collection: Collection = Depends(get_location_collection)):
    body = location.model_dump()
    result = collection.insert_one(body)
    created_location = collection.find_one({"_id": result.inserted_id})
    if not created_location:
        raise HTTPException(status_code=500, detail="Failed to retrieve inserted document")
    
    return serialize_document(created_location)

@app.get("/location/{location_id}", dependencies=[Depends(has_role("User"))])
async def get_location_by_id(location_id: str, collection: Collection = Depends(get_location_collection)):
    try:
        object_id = ObjectId(location_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")
    result = collection.find_one(({"_id": object_id}))
    if not result:
        raise HTTPException(status_code=500, detail="Could not retrieve document")
    
    return serialize_document(result)

@app.get("/locations", response_model=list[Location], dependencies=[Depends(has_role("User"))])
async def get_locations(collection: Collection = Depends(get_location_collection)):
    documents = collection.find()
    return [serialize_document(doc) for doc in documents]
    
@app.put("/location/{location_id}", response_model=Location, dependencies=[Depends(has_role("User"))])
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
    
    

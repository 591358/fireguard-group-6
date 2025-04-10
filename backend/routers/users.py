import os
from typing import Collection, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from mongomock import ObjectId

from backend.auth import delete_user_from_keycloak, get_admin_token, get_current_user, has_role
from backend.create_user import assign_role_to_user, create_new_user, create_user_in_db
from backend.models.models import CreateUser, UpdateUser, User
from backend.mongo import get_user_collection, serialize_document

user_fields_map = {"_id": "_id", "username": "username", "email": "email", "roles": "roles", "keycloak_user_id": "keycloak_user_id"}
users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get(
    "/{user_id}",
    response_model=User,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_role("Admin"))],
    summary="Get user by ID",
    response_description="Returns a single user with the provided ID",
)
async def get_user(user_id: str, collection: Collection = Depends(get_user_collection)):
    """
    Retrieve a single user by their MongoDB `_id`.

    - **user_id**: MongoDB ObjectId (as string)
    - Requires Admin role
    """
    try:
        object_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")

    result = collection.find_one({"_id": object_id})
    if not result:
        raise HTTPException(status_code=500, detail="Could not retrieve document")

    return serialize_document(result, user_fields_map)


@users_router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a new user", response_description="Returns the newly created user data")
async def create_user_endpoint(user: CreateUser):
    """
    Creates a new user in Keycloak and stores them in MongoDB.

    - Ensures default "User" role exists (creates it if missing)
    - Assigns the "User" role to the created user
    - Stores the user in MongoDB
    """
    access_token = await get_admin_token()
    if not access_token:
        raise HTTPException(status_code=500, detail="Failed to obtain admin token")

    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm_name = os.getenv("REALM_NAME")
    role_name = "User"

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        role_check_url = f"{keycloak_url}/admin/realms/{realm_name}/roles/{role_name}"
        role_response = await client.get(role_check_url, headers=headers)

        if role_response.status_code == 404:
            create_role_url = f"{keycloak_url}/admin/realms/{realm_name}/roles"
            create_role_payload = {"name": role_name}
            create_role_response = await client.post(create_role_url, json=create_role_payload, headers=headers)
            if create_role_response.status_code not in [201, 204]:
                raise HTTPException(status_code=500, detail=f"Failed to create role '{role_name}'")

    created_user = await create_new_user(user, access_token)
    created_user["id"] = str(created_user["id"])

    if "id" not in created_user:
        raise HTTPException(status_code=400, detail="User ID not found in Keycloak response")

    stored_user = await create_user_in_db(user, created_user["id"])

    try:
        await assign_role_to_user(created_user["id"], role_name, access_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign role '{role_name}': {str(e)}")

    return {
        "message": "User created, role assigned, and user stored in database",
        "user": created_user,
        "stored_in_db": serialize_document(stored_user, user_fields_map),
    }


@users_router.get(
    "/",
    response_model=List[User],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_role("Admin"))],
    summary="List all users",
    response_description="Returns a list of all users in the system",
)
async def get_all_users(collection: Collection = Depends(get_user_collection)):
    """
    Retrieve a list of all users stored in MongoDB.

    - Requires Admin role
    """
    users = collection.find()
    return [serialize_document(doc, user_fields_map) for doc in users]


@users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_role("Admin"))],
    summary="Delete user by ID",
    response_description="Deletes a user from both MongoDB and Keycloak",
)
async def delete_user(user_id: str, collection: Collection = Depends(get_user_collection)):
    """
    Deletes a user from both MongoDB and Keycloak using the MongoDB `_id`.

    - **user_id**: MongoDB ObjectId (as string)
    - Requires Admin role
    """
    try:
        obj_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    user = collection.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found in database.")

    keycloak_user_id = user.get("keycloak_user_id")
    if not keycloak_user_id:
        raise HTTPException(status_code=500, detail="User is missing Keycloak ID.")

    response = await delete_user_from_keycloak(keycloak_user_id)
    if "error" in response:
        raise HTTPException(status_code=response.get("status_code", 500), detail=response.get("detail", "Unknown error during Keycloak deletion"))

    result = collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete user from database.")

    return {"message": f"User {user_id} deleted successfully from both Keycloak and MongoDB."}


@users_router.put(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Update current user's profile",
    response_description="Updates the profile of the currently authenticated user",
)
async def update_my_user(user_update: UpdateUser, collection: Collection = Depends(get_user_collection), current_user=Depends(get_current_user)):
    """
    Update the profile of the currently authenticated user.

    - Accepts partial updates
    - Uses `username` from auth context to find the user in MongoDB
    """
    if not user_update:
        raise HTTPException(status_code=400, detail="No update data provided")

    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")

    user = collection.find_one({"username": current_user.username})
    if not user:
        raise HTTPException(status_code=404, detail="Authenticated user not found")

    result = collection.update_one({"_id": user["_id"]}, {"$set": update_data})
    if result.modified_count == 0:
        return {"Message": "No changes made."}

    return {"Message": "User profile successfully updated"}

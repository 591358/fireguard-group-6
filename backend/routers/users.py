import os
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from mongomock import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from backend.auth import delete_user_from_keycloak, get_admin_token, get_current_user, has_role
from backend.create_user import assign_role_to_user, create_new_user, create_user_in_db
from backend.models.models import CreateUser, UpdateUser, User
from backend.mongo import get_user_collection, serialize_document

user_fields_map = {
    "_id": "_id",
    "username": "username",
    "email": "email",
    "roles": "roles",
    "keycloak_user_id": "keycloak_user_id",
}
users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get(
    "/{user_id}",
    response_model=User,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_role("Admin"))],
    summary="Get user by ID",
    response_description="Returns a single user with the provided ID",
)
async def get_user(
    user_id: str,
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
):
    """
    Retrieve a single user by their MongoDB `_id`.
    - **user_id**: MongoDB ObjectId (as string)
    - Requires Admin role
    """
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")

    result = await collection.find_one({"_id": object_id})
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return serialize_document(result, user_fields_map, default_list_fields=["roles"])


@users_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    response_description="Returns the newly created user data",
)
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
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # ensure the "User" role exists
    async with httpx.AsyncClient() as client:
        role_check_url = f"{keycloak_url}/admin/realms/{realm_name}/roles/{role_name}"
        role_response = await client.get(role_check_url, headers=headers)
        if role_response.status_code == 404:
            create_role_url = f"{keycloak_url}/admin/realms/{realm_name}/roles"
            create_role_payload = {"name": role_name}
            create_role_resp = await client.post(create_role_url, json=create_role_payload, headers=headers)
            if create_role_resp.status_code not in (201, 204):
                raise HTTPException(status_code=500, detail=f"Failed to create role '{role_name}'")

    # create in Keycloak
    created_user = await create_new_user(user, access_token)
    if "id" not in created_user:
        raise HTTPException(status_code=400, detail="User ID not in Keycloak response")
    created_user["id"] = str(created_user["id"])

    # store in MongoDB
    stored_user = await create_user_in_db(user, created_user["id"])

    # assign User role
    try:
        await assign_role_to_user(created_user["id"], role_name, access_token)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assign role '{role_name}': {e}",
        )

    return {
        "message": "User created, role assigned, and user stored in database",
        "user": created_user,
        "stored_in_db": serialize_document(stored_user, user_fields_map, default_list_fields=["roles"]),
    }


@users_router.get(
    "/",
    response_model=List[User],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_role("Admin"))],
    summary="List all users",
    response_description="Returns a list of all users in the system",
)
async def get_all_users(
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
):
    """
    Retrieve a list of all users stored in MongoDB.
    - Requires Admin role
    """
    raw_users = await collection.find().to_list(length=None)
    return [serialize_document(u, user_fields_map, default_list_fields=["roles"]) for u in raw_users]


@users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_role("Admin"))],
    summary="Delete user by ID",
    response_description="Deletes a user from both MongoDB and Keycloak",
)
async def delete_user(
    user_id: str,
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
):
    """
    Deletes a user from both MongoDB and Keycloak.
    - **user_id**: MongoDB ObjectId (as string)
    - Requires Admin role
    """
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    user = await collection.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    keycloak_user_id = user.get("keycloak_user_id")
    if not keycloak_user_id:
        raise HTTPException(status_code=500, detail="User is missing Keycloak ID")

    resp = await delete_user_from_keycloak(keycloak_user_id)
    if "error" in resp:
        raise HTTPException(
            status_code=resp.get("status_code", 500),
            detail=resp.get("detail", "Error deleting in Keycloak"),
        )

    result = await collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete user from database")

    return {"message": f"User {user_id} deleted successfully"}


@users_router.put(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Update current user's profile",
    response_description="Updates the profile of the currently authenticated user",
)
async def update_my_user(
    user_update: UpdateUser,
    collection: AsyncIOMotorCollection = Depends(get_user_collection),
    current_user=Depends(get_current_user),
):
    """
    Partially updates the profile of the currently authenticated user.
    - Uses username from auth context to find the user in MongoDB.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    user = await collection.find_one({"username": current_user.username})
    if not user:
        raise HTTPException(status_code=404, detail="Authenticated user not found")

    result = await collection.update_one({"_id": user["_id"]}, {"$set": update_data})
    if result.modified_count == 0:
        return {"message": "No changes made"}

    return {"message": "User profile successfully updated"}

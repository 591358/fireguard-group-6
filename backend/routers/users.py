from typing import Collection, List

from fastapi import APIRouter, Depends, HTTPException
from mongomock import ObjectId

from backend.auth import delete_user_from_keycloak, get_admin_token, get_current_user, has_role
from backend.create_user import assign_role_to_user, create_new_user, create_user_in_db
from backend.models.models import CreateUser, UpdateUser, User
from backend.mongo import get_user_collection, serialize_document

user_fields_map = {"_id": "_id", "username": "username", "email": "email", "roles": "roles", "keycloak_user_id": "keycloak_user_id"}
users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/{user_id}", dependencies=[Depends(has_role("Admin"))], summary="Get user by provided id")
async def get_user(user_id: str, collection: Collection = Depends(get_user_collection)):
    try:
        object_id = ObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid id format")
    result = collection.find_one(({"_id": object_id}))
    if not result:
        raise HTTPException(status_code=500, detail="Could not retrieve document")

    return serialize_document(result, user_fields_map)


@users_router.post("/", summary="Create a new user")
async def create_user_endpoint(user: CreateUser):
    access_token = await get_admin_token()
    created_user = await create_new_user(user, access_token)
    created_user["id"] = str(created_user["id"])
    if "id" not in created_user:
        raise HTTPException(status_code=400, detail="User ID not found in Keycloak response")
    stored_user = await create_user_in_db(user, created_user["id"])
    try:
        await assign_role_to_user(created_user["id"], "User", access_token)  # noqa: F821
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign role: {str(e)}")

    return {
        "message": "User created and role assigned",
        "user": created_user,
        "stored in db": serialize_document(stored_user, user_fields_map),
    }


@users_router.get("/", response_model=List[User], dependencies=[Depends(has_role("Admin"))], summary="Get all users")
async def get_all_users(collection: Collection = Depends(get_user_collection)):
    users = collection.find()
    return [serialize_document(doc, user_fields_map) for doc in users]


@users_router.delete("/{user_id}", dependencies=[Depends(has_role("Admin"))], summary="Delete user by ID")
async def delete_user(user_id: str, collection: Collection = Depends(get_user_collection)):
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


@users_router.put("/me", summary="Update the authenticated user's profile")
async def update_my_user(user_update: UpdateUser, collection=Depends(get_user_collection), current_user=Depends(get_current_user)):
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

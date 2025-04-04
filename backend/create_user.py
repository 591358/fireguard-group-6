import os
from typing import Collection

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

from backend.models.models import CreateUser
from backend.mongo import user_collection

load_dotenv()
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
REALM_NAME = os.getenv("REALM_NAME")
CLIENT_ID = os.getenv("CLIENT_ID")


async def assign_role_to_user(user_id: str, role_name: str, access_token: str):
    async with httpx.AsyncClient() as client:
        roles_response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        roles_response.raise_for_status()
        roles = roles_response.json()

        role_id = next((role["id"] for role in roles if role["name"] == role_name), None)
        if not role_id:
            raise HTTPException(status_code=404, detail="Role not found")

        response = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/role-mappings/realm",
            headers={"Authorization": f"Bearer {access_token}"},
            json=[{"id": role_id, "name": role_name}],
        )
        response.raise_for_status()

async def create_user_in_db(user: CreateUser, collection: Collection = user_collection):
    """Stores the user in MongoDB after creation in Keycloak."""
    existing_user = collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    inserted_user = collection.insert_one(user.model_dump())
    stored_user = {"id": str(inserted_user.inserted_id), **user.model_dump()}
    return stored_user

async def create_new_user(user: CreateUser, access_token: str):
    async with httpx.AsyncClient() as client:
        check_user_response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"email": user.email}  
        )
        check_user_response.raise_for_status()

        existing_users = check_user_response.json()
        if existing_users:
            raise HTTPException(status_code=400, detail="User already exists")

        response = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "username": user.username,
                "email": user.email,
                "enabled": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": user.password,
                        "temporary": False,
                    }
                ],
            },
        )
        response.raise_for_status()

        user_response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"email": user.email}
        )
        user_response.raise_for_status()
        created_user = user_response.json()[0]
        return created_user 
    
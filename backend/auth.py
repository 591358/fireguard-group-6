import logging
import os
from datetime import datetime, timezone

import httpx
import requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwk, jwt

from backend.models.models import CreateUser, TokenData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL")
REALM_NAME = os.getenv("REALM_NAME")
CLIENT_ID = os.getenv("CLIENT_ID")
JWKS_URL = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/certs"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
    auto_error=False,
)


def get_token_url(url: str, realm_name: str):
    return f"{url}/realms/{realm_name}/protocol/openid-connect/token"


def get_application_header():
    return {"Content-Type": "application/x-www-form-urlencoded"}


def get_keycloak_info():
    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm_name = os.getenv("REALM_NAME")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    return keycloak_url, realm_name, client_id, client_secret


def get_user_token(username: str, password: str):
    url, realm_name, client_id, client_secret = get_keycloak_info()
    token_url = get_token_url(url, realm_name)
    data = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
    }
    headers = get_application_header()
    response = requests.post(token_url, data=data, headers=headers)

    if response.status_code == 200:
        token_data = response.json()
        return {"access_token": token_data["access_token"], "refresh_token": token_data["refresh_token"]}
    else:
        logger.error("Error: %s", {response.status_code})
        logger.info(response.text)
        return None


# TODO refactor this method, also the fetching of the keycloak info.
async def get_admin_token():
    url, _, _, _ = get_keycloak_info()
    token_url = get_token_url(url, "master")
    admin_id = os.getenv("ADMIN_CLIENT_ID")
    admin_sectet = os.getenv("ADMIN_CLIENT_SECRET")
    logger.info("AD: %s", admin_id)
    logger.info("ADS: %s", admin_sectet)
    data = {"grant_type": "client_credentials", "client_id": admin_id, "client_secret": admin_sectet}

    response = requests.post(token_url, data, get_application_header)
    if response.status_code == 200:
        logger.info("Access token %s", response.json()["access_token"])
        return response.json()["access_token"]
    else:
        logger.error("Failed to get admin token: %s", response.text)
        return None


def refresh_access_token(refresh_token: str):
    url, realm_name, client_id, client_secret = get_keycloak_info()
    token_url = get_token_url(url, realm_name)
    data = {"grant_type": "refresh_token", "client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token}
    headers = get_application_header()
    response = requests.post(token_url, data, headers)
    logger.info("Response: %s", response.json)
    if response.status_code == 200:
        token_data = response.json()
        return {"access_token": token_data["access_token"], "refresh_token": token_data["refresh_token"]}
    else:
        logger.error("Failed to refresh access token: %s", response.text)
        return None


def is_token_expired(token: str):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded.get("exp", 0)
        return datetime.now(timezone.utc).timestamp() > exp_timestamp
    except jwt.DecodeError:
        return True


async def create_user(user: CreateUser):
    [username, password, email] = user
    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm_name = os.getenv("REALM_NAME")

    admin_token = await get_admin_token()
    if not admin_token:
        logger.error("Failed to get admin token")
        return None

    user_url = f"{keycloak_url}/admin/realms/{realm_name}/users"

    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    data = {
        "username": username,
        "email": email,
        "enabled": True,
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }

    response = requests.post(user_url, json=data, headers=headers)
    if response.status_code == 201:
        logger.info("User created successfully")
        return {"message": "User created successfully"}
    elif response.status_code == 204:
        logger.info("User created with no content returned")
        return {"message": "User created successfully, no content returned"}
    else:
        logger.error("Failed to create user: %s", response.text)
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {"error": "Response is not JSON", "status_code": response.status_code}


async def validate_token(token: str) -> TokenData:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(JWKS_URL)
            response.raise_for_status()
            jwks = response.json()

        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token missing 'kid' header")

        key_data = next((key for key in jwks["keys"] if key["kid"] == kid), None)
        if not key_data:
            raise HTTPException(status_code=401, detail="Matching key not found in JWKS")

        public_key = jwk.construct(key_data).public_key()

        payload = jwt.decode(token, key=public_key, algorithms=["RS256"], options={"verify_aud": False})

        username = payload.get("preferred_username")
        roles = payload.get("realm_access", {}).get("roles", [])
        if not username or not roles:
            raise HTTPException(status_code=401, detail="Token missing required claims")

        return TokenData(username=username, roles=roles)

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await validate_token(token)


def has_role(required_role: str):
    def role_checker(token_data: TokenData = Depends(get_current_user)) -> TokenData:
        if required_role not in token_data.roles:
            raise HTTPException(status_code=403, detail="Not authorized")
        return token_data

    return role_checker


async def delete_user_from_keycloak(user_id: str):
    """
    Deletes a user from Keycloak using the Admin API.
    Parameters:
        user_id: ID of the user to be deleted.
    Returns:
        A response message indicating success or failure.
    """
    admin_token = await get_admin_token()
    if not admin_token:
        logger.error("Failed to get admin token")
        return {"error": "Failed to get admin token"}

    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm_name = os.getenv("REALM_NAME")
    delete_url = f"{keycloak_url}/admin/realms/{realm_name}/users/{user_id}"

    headers = {
        "Authorization": f"Bearer {admin_token}",
    }

    response = requests.delete(delete_url, headers=headers)

    if response.status_code == 204:
        logger.info(f"User {user_id} deleted successfully")
        return {"message": f"User {user_id} deleted successfully"}
    else:
        logger.error(f"Failed to delete user {user_id}: {response.status_code}, {response.text}")
        return {"error": f"Failed to delete user {user_id}", "status_code": response.status_code, "detail": response.text}

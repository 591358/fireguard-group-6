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

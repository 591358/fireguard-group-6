from fastapi import HTTPException, Request
from jose import jwt
import json
import base64
import logging
logger = logging.getLogger(__name__)
def decode_jwt(token: str):
    """ Decodes and prints JWT token for debugging """
    try:
        decoded = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
        logger.info(f"✅ Decoded JWT: {json.dumps(decoded, indent=2)}")
    except Exception as e:
        logger.error(f"❌ Error decoding JWT: {e}")


def decode_jwt(token: str):
    if not token:
        logger.error("JWT token is missing")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing token")
    try:
        parts = token.split(".")
        if len(parts) != 3:
            logger.error("Invalid JWT format")
            raise HTTPException(status_code=401, detail="Invalid JWT format")

        payload_data = base64.urlsafe_b64decode(parts[1] + "==")
        payload = json.loads(payload_data)
        logger.info(f"Decoded JWT Payload: {json.dumps(payload, indent=2)}")
        return payload
    except Exception as e:
        logger.error(f"Error decoding JWT: {e}")
        raise HTTPException(status_code=401, detail="Invalid JWT token")



async def get_current_user(request: Request):
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    if not token:
        logger.error("Authorization header missing or invalid")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing token")
    user = decode_jwt(token)
    if not user:
        logger.error("Decoded JWT returned None")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")
    return user

async def check_role(request: Request, required_roles: list):
    user = await get_current_user(request)
    user_roles = user.get("realm_access", {}).get("roles", [])
    if not user_roles:
        logger.error("No roles found in token")
        raise HTTPException(status_code=403, detail="Forbidden: No roles assigned")
    if not any(role in user_roles for role in required_roles):
        logger.error(f"User lacks required roles: {required_roles}")
        raise HTTPException(status_code=403, detail="Forbidden: Insufficient role")
    return user

import os
import logging
import requests
import dotenv
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
dotenv.load_dotenv()
def get_keycloak_info():
    keycloak_url = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")  # Default to keycloak if not set
    realm_name = os.getenv("REALM_NAME") 
    client_id = os.getenv("CLIENT_ID")  
    client_secret = os.getenv("CLIENT_SECRET")  
    return keycloak_url, realm_name, client_id, client_secret


#TODO: FIX .env not bein updated in docker
def get_user_token(username: str, password: str):
    url, realm_name, client_id, client_secret = get_keycloak_info()
    token_url = f"{url}/realms/{realm_name}/protocol/openid-connect/token"
    logger.info("TOKEN URL %s", token_url)
    logger.info("client_id %s", client_id)
    logger.info("client_secret %s", client_secret )
    data = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
    }
    headers = {
    "Content-Type": "application/x-www-form-urlencoded"
    }   

    response = requests.post(token_url, data=data, headers=headers)

    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        logger.error("Error: %s", {response.status_code})
        logger.info(response.text)
        return None

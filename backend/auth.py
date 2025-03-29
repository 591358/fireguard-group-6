import os
import logging
import requests
from dotenv import load_dotenv
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


def get_token_url(url: str, realm_name: str):
    return f"{url}/realms/{realm_name}/protocol/openid-connect/token"

def get_application_header():
    return  {"Content-Type": "application/x-www-form-urlencoded"}   

def get_keycloak_info():
    keycloak_url = os.getenv("KEYCLOAK_URL") 
    realm_name=os.getenv("REALM_NAME")
    client_id=os.getenv("CLIENT_ID")
    client_secret=os.getenv("CLIENT_SECRET")
    return keycloak_url, realm_name, client_id, client_secret

def get_user_token(username: str, password: str):
    url, realm_name, client_id, client_secret = get_keycloak_info()
    token_url =  get_token_url(url, realm_name)
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
        return token_data["access_token"]
    else:
        logger.error("Error: %s", {response.status_code})
        logger.info(response.text)
        return None


#TODO refactor this method, also the fetching of the keycloak info.
def get_admin_token():
    url, _, _, _= get_keycloak_info()
    token_url = get_token_url(url, "master")
    admin_id = os.getenv("ADMIN_CLIENT_ID")
    admin_sectet = os.getenv("ADMIN_CLIENT_SECRET")
    logger.info("AD: %s", admin_id)
    logger.info("ADS: %s", admin_sectet)
    data = {
        "grant_type": "client_credentials",
        "client_id":  admin_id,
        "client_secret": admin_sectet
    }
    
    response = requests.post(token_url, data, get_application_header)
    if response.status_code == 200:
        logger.info("Access token %s",response.json()["access_token"] )
        return response.json()["access_token"]
    else:
        logger.error("Failed to get admin token: %s", response.text)
        return None


def create_user(username: str, email: str, password: str):
    keycloak_url = os.getenv("KEYCLOAK_URL")
    realm_name = os.getenv("REALM_NAME")
    
    admin_token = get_admin_token()
    if not admin_token:
        logger.error("Failed to get admin token")
        return None

    user_url = f"{keycloak_url}/admin/realms/{realm_name}/users"
    
    headers = {
        "Authorization": f"Bearer {admin_token}", 
        "Content-Type": "application/json"
    }

    data = {
        "username": username,
        "email": email,
        "enabled": True,
        "credentials": [{
            "type": "password",
            "value": password,
            "temporary": False 
        }]
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

        
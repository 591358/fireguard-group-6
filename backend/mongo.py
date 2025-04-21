import os

from dotenv import load_dotenv
from mongomock import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.collection import Collection

# Loads the environment variables from the .env file
load_dotenv()
uri = os.getenv("MONGO_URI")


# Create a new client and connect to the server
client = AsyncIOMotorClient(uri)
db = client.Fireguard

location_collection: Collection = db["locations"]
user_collection: Collection = db["users"]
fire_risk_collection: Collection = db["firerisks"]


def serialize_objectid(obj):
    """Converts MongoDB ObjectId to string"""
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError(f"ObjectId of type {type(obj)} is not serializable")


def serialize_document(doc, fields_map):
    """
    Generic function to serialize MongoDB document.

    Args:
        doc (dict): The MongoDB document to serialize.
        fields_map (dict): A mapping of the field names to be serialized for the document.

    Returns:
        dict: The serialized document with the specified fields.
    """
    serialized_doc = {}
    for field, field_name in fields_map.items():
        if field_name == "_id":
            serialized_doc["id"] = str(doc.get(field_name))
        else:
            serialized_doc[field] = doc.get(field_name)
    list_fields = ["roles"]
    for list_field in list_fields:
        if list_field not in serialized_doc or serialized_doc[list_field] is None:
            serialized_doc[list_field] = []
    return serialized_doc


def get_location_collection() -> Collection:
    return location_collection


def get_user_collection() -> Collection:
    return user_collection


def get_fire_risk_collection() -> Collection:
    return fire_risk_collection

import asyncio
import os
from mongomock import ObjectId
from pymongo.mongo_client import MongoClient
from pymongo.collection import Collection
from dotenv import load_dotenv


# Loads the environment variables from the .env file
load_dotenv()
uri = os.getenv("MONGO_URI")


# Create a new client and connect to the server
client = MongoClient(uri)
db = client.Fireguard

location_collection: Collection = db["locations"]
user_collection: Collection = db["users"]


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
    return serialized_doc


def get_location_collection() -> Collection:
    return location_collection

def get_user_collection() -> Collection:
    return user_collection

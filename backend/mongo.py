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
    
def serialize_document(doc):
    return {
        "id": str(doc["_id"]),
        "locationName": doc["locationName"],
        "latitude": doc["latitude"],
        "longitude": doc["longitude"],
    }

def get_location_collection() -> Collection:
    return location_collection

def get_user_collection() -> Collection:
    return user_collection

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


def serialize_document(
    doc: dict,
    fields_map: dict,
    default_list_fields: list[str] | None = None,
) -> dict:
    """
    Generic function to serialize a MongoDB document.

    Args:
      • doc: the raw MongoDB document
      • fields_map: mapping { output_field_name: document_field_name }
      • default_list_fields: optional list of fields to ensure exist as lists

    Returns:
      A dict with only the fields in `fields_map`, plus any default_list_fields
      initialized to [] if missing.
    """
    serialized: dict = {}

    # copy just the mapped fields
    for out_field, doc_field in fields_map.items():
        if doc_field == "_id":
            # convert ObjectId -> str
            serialized[out_field] = str(doc.get(doc_field))
        else:
            serialized[out_field] = doc.get(doc_field)

    # inject any default-list fields (e.g. Roles) if requested
    if default_list_fields:
        for lf in default_list_fields:
            serialized.setdefault(lf, [])

    return serialized


def get_location_collection() -> Collection:
    return location_collection


def get_user_collection() -> Collection:
    return user_collection


def get_fire_risk_collection() -> Collection:
    return fire_risk_collection

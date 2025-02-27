import os
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
import os

from backend.auth import get_current_user
from backend.mongo import get_location_collection

os.environ["TESTING"] = "True"
import logging

import mongomock
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.main import app
from backend.models.models import TokenData
import logging

logger = logging.getLogger(__name__)

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_current_user():
    return TokenData(
        username="testUser",
        roles=["User"]
    )

import logging

logger = logging.getLogger(__name__)

@pytest.fixture
def client(mock_current_user):
    mock_client = mongomock.MongoClient()
    mock_db = mock_client.db
    mock_collection = mock_db.location_collection
    
    test_locations = [
        {"_id": mongomock.ObjectId(), "locationName": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"_id": mongomock.ObjectId(), "locationName": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
    ]
    mock_collection.insert_many(test_locations)

    print("Overriding dependencies for testing...")
    
    app.dependency_overrides[get_location_collection] = lambda: mock_collection
    app.dependency_overrides[get_current_user] = lambda: mock_current_user 
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()




def test_get_locations(client):
    response = client.get("/locations")
    assert response.status_code == 200
    assert len(response.json()) == 2

    expected_data = [
        {"locationName": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"locationName": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
    ]

    for i, loc in enumerate(expected_data):
        assert response.json()[i]["locationName"] == loc["locationName"]
        assert response.json()[i]["latitude"] == loc["latitude"]
        assert response.json()[i]["longitude"] == loc["longitude"]

def test_insert_location(client):
    mock_collection = app.dependency_overrides[get_location_collection]()

    payLoad = {
        "locationName": "Oslo",
        "latitude": 25.0,
        "longitude": 50.0
    }
    response = client.post("/locations", json=payLoad)
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 200, response.text
    data = response.json()
    
    assert data["locationName"] == payLoad["locationName"]
    assert data["latitude"] == payLoad["latitude"]
    assert data["longitude"] == payLoad["longitude"]
    assert "id" in data
    inserted_doc = mock_collection.find_one({"_id": mongomock.ObjectId(data["id"])})
    assert inserted_doc is not None
    assert inserted_doc["locationName"] == payLoad["locationName"]
    assert inserted_doc["latitude"] == payLoad["latitude"]
    assert inserted_doc["longitude"] == payLoad["longitude"]


def test_get_location_by_id(client):
    mock_collection = app.dependency_overrides[get_location_collection]()
    payLoad = {
        "_id": mongomock.ObjectId(),
        "locationName": "Berlin",
        "latitude": 43.0,
        "longitude": 33.3
    }
    
    mock_collection.insert_one(payLoad)
    location_id = str(payLoad["_id"])
    
    response = client.get(f"/location/{location_id}")
    
    if response.status_code != 200:
        logger.error("Failed to fetch location: %s", response.json())
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == location_id
    assert data["locationName"] == payLoad["locationName"]
    assert data["latitude"] == payLoad["latitude"]
    assert data["longitude"] == payLoad["longitude"]
    
    
def test_location_put(client):
    mock_collection = app.dependency_overrides[get_location_collection]()
    test_location = {
        "_id": mongomock.ObjectId(),
        "locationName": "Bergen",
        "latitude": 60,
        "longitude": 5,
    }
    location_id = str(test_location["_id"])
    mock_collection.insert_one(test_location)
    
    update_payload = {
        "locationName": "Oslo",
        "latitude": 58
    }
    response = client.put(f"/location/{location_id}", json=update_payload)
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert data["id"] == location_id
    assert data["locationName"] == update_payload["locationName"]
    assert data["latitude"] == update_payload["latitude"]
    assert data["longitude"] == test_location["longitude"]
    
    updated_doc = mock_collection.find_one({"_id": mongomock.ObjectId(location_id)})
    assert updated_doc is not None
    assert updated_doc["locationName"] == update_payload["locationName"]
    assert updated_doc["latitude"] == updated_doc["latitude"]
    assert updated_doc["longitude"] == test_location["longitude"]
    
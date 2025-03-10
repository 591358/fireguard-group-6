import pytest
import mongomock
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.main import app, get_location_collection
import logging
import os


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Use mongomock to create a fake MongoDB instance
@pytest.fixture
def client():
    mock_client = mongomock.MongoClient()
    mock_db = mock_client.db
    mock_collection = mock_db.location_collection  # Mocked collection
    # Insert test data into mock collection
    test_locations = [
        {"_id": mongomock.ObjectId(), "locationName": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"_id": mongomock.ObjectId(), "locationName": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
    ]
    mock_collection.insert_many(test_locations)
    # Override FastAPI dependency to return the mock collection
    app.dependency_overrides[get_location_collection] = lambda: mock_collection
    yield TestClient(app)
    # Clear overrides after test
    app.dependency_overrides.clear()


def get_test_token():
    """Fetches Keycloak access token from GitHub Actions environment"""
    return os.getenv("ACCESS_TOKEN")

def test_get_locations(client):
    headers = {"Authorization": f"Bearer {get_test_token()}"}
    response = client.get("/locations", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    expected_data = [
        {"locationName": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"locationName": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
    ]
    for i, loc in enumerate(expected_data):
        assert data[i]["locationName"] == loc["locationName"]
        assert data[i]["latitude"] == loc["latitude"]
        assert data[i]["longitude"] == loc["longitude"]

def test_insert_location(client):
    mock_collection = app.dependency_overrides[get_location_collection]()

    payLoad = {
        "locationName": "Oslo",
        "latitude": 25.0,
        "longitude": 50.0
    }
    response = client.post("/locations", json=payLoad)
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
    
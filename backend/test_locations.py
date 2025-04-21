import os

from backend.auth import get_current_user
from backend.mongo import get_location_collection

os.environ["TESTING"] = "True"
import logging

import mongomock
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.models import TokenData

logger = logging.getLogger(__name__)

load_dotenv()
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FakeAsyncCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    async def to_list(self, length=None):
        return list(self.cursor)

    async def __aiter__(self):
        for item in self.cursor:
            yield item


class FakeAsyncCollection:
    def __init__(self, collection):
        self.collection = collection

    def find(self, *args, **kwargs):
        return FakeAsyncCursor(self.collection.find(*args, **kwargs))

    async def find_one(self, *args, **kwargs):
        return self.collection.find_one(*args, **kwargs)

    async def insert_one(self, *args, **kwargs):
        return self.collection.insert_one(*args, **kwargs)

    async def insert_many(self, *args, **kwargs):
        return self.collection.insert_many(*args, **kwargs)

    async def update_one(self, *args, **kwargs):
        return self.collection.update_one(*args, **kwargs)

    async def delete_one(self, *args, **kwargs):
        return self.collection.delete_one(*args, **kwargs)


@pytest.fixture
def mock_current_user():
    return TokenData(username="testUser", roles=["User"])


logger = logging.getLogger(__name__)


@pytest.fixture
def client(mock_current_user):
    mock_client = mongomock.MongoClient()
    mock_db = mock_client.db
    mock_collection = FakeAsyncCollection(mock_db.location_collection)

    test_locations = [
        {"_id": mongomock.ObjectId(), "locationName": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"_id": mongomock.ObjectId(), "locationName": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
    ]
    mock_db.location_collection.insert_many(test_locations)

    print("Overriding dependencies for testing...")

    app.dependency_overrides[get_location_collection] = lambda: mock_collection
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    yield TestClient(app)

    app.dependency_overrides.clear()


def test_get_locations(client):
    response = client.get("/locations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    expected = [
        {"locationName": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"locationName": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
    ]

    for loc, expected_loc in zip(data, expected):
        assert loc["locationName"] == expected_loc["locationName"]
        assert loc["latitude"] == expected_loc["latitude"]
        assert loc["longitude"] == expected_loc["longitude"]


def test_insert_location(client):
    mock_collection = app.dependency_overrides[get_location_collection]()
    payload = {"locationName": "Oslo", "latitude": 25.0, "longitude": 50.0}

    response = client.post("/locations", json=payload)
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["locationName"] == payload["locationName"]
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]
    assert "id" in data

    inserted_doc = mock_collection.collection.find_one({"_id": mongomock.ObjectId(data["id"])})
    assert inserted_doc is not None
    assert inserted_doc["locationName"] == payload["locationName"]
    assert inserted_doc["latitude"] == payload["latitude"]
    assert inserted_doc["longitude"] == payload["longitude"]


def test_get_location_by_id(client):
    mock_collection = app.dependency_overrides[get_location_collection]()
    payload = {"_id": mongomock.ObjectId(), "locationName": "Berlin", "latitude": 43.0, "longitude": 33.3}

    mock_collection.collection.insert_one(payload)
    location_id = str(payload["_id"])

    response = client.get(f"/locations/{location_id}")

    if response.status_code != 200:
        logger.error("Failed to fetch location: %s", response.json())

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == location_id
    assert data["locationName"] == payload["locationName"]
    assert data["latitude"] == payload["latitude"]
    assert data["longitude"] == payload["longitude"]


def test_location_put(client):
    mock_collection = app.dependency_overrides[get_location_collection]()
    test_location = {
        "_id": mongomock.ObjectId(),
        "locationName": "Bergen",
        "latitude": 60,
        "longitude": 5,
    }
    location_id = str(test_location["_id"])
    mock_collection.collection.insert_one(test_location)

    update_payload = {"locationName": "Oslo", "latitude": 58}

    response = client.put(f"/locations/{location_id}", json=update_payload)

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["id"] == location_id
    assert data["locationName"] == update_payload["locationName"]
    assert data["latitude"] == update_payload["latitude"]
    assert data["longitude"] == test_location["longitude"]

    updated_doc = mock_collection.collection.find_one({"_id": mongomock.ObjectId(location_id)})
    assert updated_doc is not None
    assert updated_doc["locationName"] == update_payload["locationName"]
    assert updated_doc["latitude"] == update_payload["latitude"]
    assert updated_doc["longitude"] == test_location["longitude"]

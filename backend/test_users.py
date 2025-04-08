import logging
import os

os.environ["TESTING"] = "True"

from unittest.mock import patch

import mongomock
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from backend.app import app
from backend.auth import get_current_user
from backend.models.models import TokenData
from backend.mongo import get_user_collection

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_db():
    mock_client = mongomock.MongoClient()
    mock_db = mock_client.db
    mock_collection = mock_db.user_collection

    test_users = [
        {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "Test User",
            "email": "testuser@example.com",
            "password": "testpassword",
            "roles": ["Admin"],
            "keycloak_user_id": "507f1f77bcf86cd799439011",
        },
        {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "username": "Another User",
            "email": "anotheruser@example.com",
            "password": "testpassword2",
            "roles": ["User"],
            "keycloak_user_id": "507f1f77bcf86cd799439012",
        },
    ]

    mock_collection.insert_many(test_users)
    logger.debug(f"Inserted test users: {test_users}")

    yield mock_collection


@pytest.fixture
def mock_get_admin_token():
    with patch("backend.auth.get_admin_token") as mock_token:
        mock_token.return_value = "mocked-access-token"
        yield mock_token


@pytest.fixture
def mock_requests_delete():
    with patch("requests.delete") as mock_delete:
        mock_delete.return_value.status_code = 204
        mock_delete.return_value.json.return_value = {}
        yield mock_delete


@pytest.fixture
def mock_current_user():
    return TokenData(username="test_user", roles=["Admin"])


@pytest.fixture
def client(mock_db, mock_current_user):
    app.dependency_overrides[get_user_collection] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_user(client):
    user_id = "507f1f77bcf86cd799439011"
    logger.debug(f"Sending GET request to fetch user with ID: {user_id}")
    response = client.get(f"/users/{user_id}")

    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response body: {response.text}")

    assert response.status_code == 200, response.text
    data = response.json()

    assert "username" in data
    assert data["username"] == "Test User"
    assert data["email"] == "testuser@example.com"
    assert "roles" in data
    assert "keycloak_user_id" in data
    assert data["roles"] == ["Admin"]


def test_get_all_users(client):
    logger.debug("Testing fetching all users...")
    response = client.get("/users/")

    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response body: {response.text}")

    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data) == 2
    assert any(user["username"] == "Test User" for user in data)
    assert any(user["username"] == "Another User" for user in data)

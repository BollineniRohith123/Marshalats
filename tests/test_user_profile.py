import pytest
from fastapi.testclient import TestClient
from backend.server import app
import pymongo
from datetime import date

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """
    Fixture to clean up the database before and after tests.
    """
    # Clean up before tests
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    for collection_name in db.list_collection_names():
        db[collection_name].drop()

    yield

    # Clean up after tests
    for collection_name in db.list_collection_names():
        db[collection_name].drop()
    mongo_client.close()

def test_register_user_with_dob_and_gender():
    """Test registering a new user with date_of_birth and gender."""
    with TestClient(app) as client:
        user_data = {
            "email": "testuser@example.com",
            "phone": "+1234567890",
            "full_name": "Test User",
            "role": "student",
            "password": "password123",
            "date_of_birth": "1995-05-15",
            "gender": "female"
        }

        # Register user
        register_response = client.post("/api/auth/register", json=user_data)
        assert register_response.status_code == 200
        assert "user_id" in register_response.json()
        user_id = register_response.json()["user_id"]

        # Login to get token
        login_response = client.post("/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Get user profile
        profile_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert profile_response.status_code == 200
        profile_data = profile_response.json()

        # Verify new fields
        assert profile_data["date_of_birth"] == "1995-05-15"
        assert profile_data["gender"] == "female"

def test_update_user_profile_with_dob_and_gender():
    """Test updating a user's profile with date_of_birth and gender."""
    with TestClient(app) as client:
        # 1. Create a user first
        user_data = {
            "email": "updateuser@example.com",
            "phone": "+1234567891",
            "full_name": "Update User",
            "role": "student",
            "password": "password123"
        }
        register_response = client.post("/api/auth/register", json=user_data)
        assert register_response.status_code == 200

        # 2. Login to get token
        login_response = client.post("/api/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 3. Update the profile
        update_data = {
            "full_name": "Updated User Name",
            "date_of_birth": "2000-01-01",
            "gender": "other"
        }
        update_response = client.put("/api/auth/profile", json=update_data, headers={"Authorization": f"Bearer {token}"})
        assert update_response.status_code == 200
        assert update_response.json()["message"] == "Profile updated successfully"

        # 4. Get the profile again to verify the update
        profile_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert profile_response.status_code == 200
        profile_data = profile_response.json()

        # Verify updated fields
        assert profile_data["full_name"] == "Updated User Name"
        assert profile_data["date_of_birth"] == "2000-01-01"
        assert profile_data["gender"] == "other"

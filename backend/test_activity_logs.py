import pytest
from fastapi.testclient import TestClient
from backend.server import app
import pymongo

# It's better to have a central conftest.py for fixtures, but for now, we'll redefine.
@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Fixture to clean up the database before and after tests."""
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    # List of all collections to be managed by tests
    collections_to_clean = [
        "users", "branches", "courses", "enrollments", "payments",
        "attendance", "qr_sessions", "products", "product_purchases",
        "complaints", "coach_ratings", "session_bookings", "transfer_requests",
        "events", "activity_logs"
    ]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    # Cleanup after tests
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_token(client, role="student", branch_id=None, email_suffix=""):
    """Helper function to get a token for a given role."""
    user_map = {
        "super_admin": {
            "email": f"admin{email_suffix}@edumanage.com",
            "password": "AdminPass123!",
            "full_name": "Super Administrator",
            "phone": f"+919876543210{email_suffix}",
            "role": "super_admin"
        },
        "student": {
            "email": f"student{email_suffix}@edumanage.com",
            "password": "Student123!",
            "full_name": "Test Student",
            "phone": f"+919876543212{email_suffix}",
            "role": "student"
        }
    }
    user_data = user_map[role]
    if branch_id:
        user_data["branch_id"] = user_data

    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    assert login_response.status_code == 200, f"Failed to get token for {role}"
    return login_response.json()["access_token"]

def test_activity_log_on_login_and_user_creation():
    """Test if activity logs are created on key events."""
    with TestClient(app) as client:
        # 1. Test login log
        student_email = "logstudent@edumanage.com"
        student_pass = "Student123!"
        student_data = {
            "email": student_email,
            "password": student_pass,
            "full_name": "Log Student",
            "phone": "+919876543299",
            "role": "student"
        }
        client.post("/api/auth/register", json=student_data)
        client.post("/api/auth/login", json={"email": student_email, "password": student_pass})

        # Check the database for the activity log
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.activity_logs.find_one({"action": "login_success"})
        mongo_client.close()

        assert log is not None
        assert log["details"]["email"] == student_email
        assert log["status"] == "success"

        # 2. Test user creation log (by admin)
        admin_token = get_token(client, "super_admin", email_suffix="_logtest")
        new_user_data = {
            "email": "newuserlog@edumanage.com",
            "password": "NewUser123!",
            "full_name": "New Log User",
            "phone": "+919876543298",
            "role": "student"
        }
        client.post("/api/users", json=new_user_data, headers={"Authorization": f"Bearer {admin_token}"})

        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.activity_logs.find_one({"action": "admin_create_user"})
        mongo_client.close()

        assert log is not None
        assert log["details"]["created_user_email"] == new_user_data["email"]

def test_get_activity_logs_security_and_content():
    """Test the activity logs endpoint for security and functionality."""
    with TestClient(app) as client:
        # Setup: One admin, one student. Student logs in.
        admin_token = get_token(client, "super_admin", email_suffix="_getlog")
        student_token = get_token(client, "student", email_suffix="_getlog")

        # 1. Test: Non-admin cannot access the endpoint
        fail_response = client.get("/api/admin/activity-logs", headers={"Authorization": f"Bearer {student_token}"})
        assert fail_response.status_code == 403

        # 2. Test: Super admin can access the endpoint and sees logs
        success_response = client.get("/api/admin/activity-logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert success_response.status_code == 200

        logs_data = success_response.json()
        assert "logs" in logs_data
        assert "total" in logs_data
        # There should be logs for registration and login of both users
        assert logs_data["total"] >= 4

        # 3. Test filtering by action
        filtered_response = client.get("/api/admin/activity-logs?action=login_success", headers={"Authorization": f"Bearer {admin_token}"})
        assert filtered_response.status_code == 200
        filtered_logs = filtered_response.json()["logs"]
        # Both admin and student logged in successfully
        assert len(filtered_logs) == 2
        for log in filtered_logs:
            assert log["action"] == "login_success"

import pytest
from fastapi.testclient import TestClient
from backend.server import app
import pymongo

# Re-using the fixture and helper from the other test file.
@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Fixture to clean up the database before and after tests."""
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = [
        "users", "branches", "activity_logs"
    ]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_token_and_id(client, role="student", branch_id=None, email_suffix=""):
    """Helper function to get a token and user ID for a given role."""
    user_map = {
        "super_admin": {"email": f"admin{email_suffix}@edumanage.com", "password": "AdminPass123!", "full_name": "Super Admin", "phone": f"10{email_suffix}", "role": "super_admin"},
        "coach_admin": {"email": f"coach_admin{email_suffix}@edumanage.com", "password": "CoachAdminPass123!", "full_name": "Coach Admin", "phone": f"11{email_suffix}", "role": "coach_admin"},
        "student": {"email": f"student{email_suffix}@edumanage.com", "password": "Student123!", "full_name": "Test Student", "phone": f"12{email_suffix}", "role": "student"}
    }
    user_data = user_map[role]
    if branch_id:
        user_data["branch_id"] = branch_id

    # A setup admin is needed to create other users.
    # To avoid re-creating it every time, we check for its existence.
    setup_admin_data = {"email": "admin_setup@edumanage.com", "password": "AdminPass123!", "full_name": "Setup Admin", "phone": "10_setup", "role": "super_admin"}
    login_response = client.post("/api/auth/login", json={"email": setup_admin_data["email"], "password": setup_admin_data["password"]})
    if login_response.status_code != 200:
        client.post("/api/auth/register", json=setup_admin_data)
        login_response = client.post("/api/auth/login", json={"email": setup_admin_data["email"], "password": setup_admin_data["password"]})

    admin_token = login_response.json()["access_token"]

    # Create the desired user
    create_response = client.post("/api/users", json=user_data, headers={"Authorization": f"Bearer {admin_token}"})

    # Login as the new user to get their token and ID
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    token = login_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me_response.json()["id"]

    return token, user_id

def get_token(client, role="student", branch_id=None, email_suffix=""):
    # A simplified get_token for when we don't need the ID right away
    token, _ = get_token_and_id(client, role, branch_id, email_suffix)
    return token

def test_force_password_reset_by_super_admin():
    """Super Admin can reset a student's password."""
    with TestClient(app) as client:
        admin_token, _ = get_token_and_id(client, "super_admin", email_suffix="_sa")
        _, student_id = get_token_and_id(client, "student", email_suffix="_s1")

        response = client.post(f"/api/users/{student_id}/force-password-reset", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert "Password for user" in response.json()["message"]

        # Also check if an activity log was created
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.activity_logs.find_one({"action": "admin_force_password_reset"})
        mongo_client.close()
        assert log is not None
        assert log["details"]["reset_user_id"] == student_id

def test_force_password_reset_by_coach_admin():
    """Coach Admin can reset password for a student in their branch, but not others."""
    with TestClient(app) as client:
        # Setup: Super Admin, 2 branches, 1 Coach Admin in branch1, 2 students
        super_admin_token = get_token(client, "super_admin", email_suffix="_cas")

        branch1_res = client.post("/api/branches", json={"name": "B1", "address": "1", "city": "c", "state": "s", "pincode": "p", "phone": "p", "email": "e1@c.com"}, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch1_id = branch1_res.json()["branch_id"]

        branch2_res = client.post("/api/branches", json={"name": "B2", "address": "2", "city": "c", "state": "s", "pincode": "p", "phone": "p", "email": "e2@c.com"}, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch2_id = branch2_res.json()["branch_id"]

        coach_admin_token, _ = get_token_and_id(client, "coach_admin", branch_id=branch1_id, email_suffix="_ca1")
        _, student1_id = get_token_and_id(client, "student", branch_id=branch1_id, email_suffix="_s1")
        _, student2_id = get_token_and_id(client, "student", branch_id=branch2_id, email_suffix="_s2")

        # 1. Success: Coach Admin resets password for student in same branch
        response_success = client.post(f"/api/users/{student1_id}/force-password-reset", headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert response_success.status_code == 200

        # 2. Failure: Coach Admin tries to reset password for student in other branch
        response_fail_branch = client.post(f"/api/users/{student2_id}/force-password-reset", headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert response_fail_branch.status_code == 403

        # 3. Failure: Coach Admin tries to reset password for a Super Admin
        _, super_admin_id_target = get_token_and_id(client, "super_admin", email_suffix="_sa2")
        response_fail_admin = client.post(f"/api/users/{super_admin_id_target}/force-password-reset", headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert response_fail_admin.status_code == 403

def test_force_password_reset_security():
    """Test security aspects of the force password reset endpoint."""
    with TestClient(app) as client:
        student1_token, _ = get_token_and_id(client, "student", email_suffix="_s1sec")
        _, student2_id = get_token_and_id(client, "student", email_suffix="_s2sec")

        # Failure: Student cannot reset another student's password
        response = client.post(f"/api/users/{student2_id}/force-password-reset", headers={"Authorization": f"Bearer {student1_token}"})
        assert response.status_code == 403

def test_force_password_reset_user_not_found():
    """Test force password reset for a non-existent user."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin", email_suffix="_404")

        response = client.post("/api/users/non-existent-user-id/force-password-reset", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 404

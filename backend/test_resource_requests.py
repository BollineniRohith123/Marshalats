import pytest
from fastapi.testclient import TestClient
from backend.server import app

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "resource_requests", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_token_and_id(client, role="coach_admin", branch_id=None, suffix=""):
    # Simplified helper
    user_map = {
        "super_admin": {"email": f"admin{suffix}@edumanage.com", "password": "AdminPass123!", "full_name": "Super Admin", "phone": f"130{suffix}", "role": "super_admin"},
        "coach_admin": {"email": f"ca{suffix}@edumanage.com", "password": "CAPass123!", "full_name": "Coach Admin", "phone": f"131{suffix}", "role": "coach_admin"},
    }
    user_data = user_map[role]
    if branch_id:
        user_data["branch_id"] = branch_id

    # Super admin creates the user
    # To avoid creating the setup admin every time, we try to log in first.
    sa_login_res = client.post("/api/auth/login", json={"email": "admin_res@edumanage.com", "password": "AdminPass123!"})
    if sa_login_res.status_code != 200:
        client.post("/api/auth/register", json={"email": "admin_res@edumanage.com", "password": "AdminPass123!", "full_name": "Resource Admin", "phone": "132", "role": "super_admin"})
        sa_login_res = client.post("/api/auth/login", json={"email": "admin_res@edumanage.com", "password": "AdminPass123!"})
    sa_token = sa_login_res.json()["access_token"]

    # Use the logged-in super admin to create the requested user
    create_res = client.post("/api/users", json=user_data, headers={"Authorization": f"Bearer {sa_token}"})

    # Login as the new user
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    token = login_response.json()["access_token"]
    user_id = login_response.json()["user"]["id"]
    return token, user_id

def test_resource_request_flow():
    """Test the full lifecycle of a resource request."""
    with TestClient(app) as client:
        # Setup
        super_admin_token, _ = get_token_and_id(client, "super_admin", suffix="_res_sa")
        branch_res = client.post("/api/branches", json={"name":"B_Res","address":"a","city":"c","state":"s","pincode":"p","email":"b_res@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch_id = branch_res.json()["branch_id"]
        coach_admin_token, _ = get_token_and_id(client, "coach_admin", branch_id=branch_id, suffix="_res_ca")

        # 1. Coach Admin creates a resource request
        request_data = {"resource_type": "maintenance", "description": "Leaky faucet in the restroom."}
        res_create = client.post("/api/requests/resource", json=request_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_create.status_code == 201
        request_id = res_create.json()["id"]

        # 2. Super Admin sees the pending request
        res_get = client.get("/api/requests/resource?status=pending", headers={"Authorization": f"Bearer {super_admin_token}"})
        assert len(res_get.json()["requests"]) == 1
        assert res_get.json()["requests"][0]["id"] == request_id

        # 3. Super Admin approves the request
        res_approve = client.put(f"/api/requests/resource/{request_id}", json={"status": "approved"}, headers={"Authorization": f"Bearer {super_admin_token}"})
        assert res_approve.status_code == 200
        assert res_approve.json()["request"]["status"] == "approved"

import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import date, timedelta

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Fixture to clean up the database before and after tests."""
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "holidays", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_token_and_id(client, role="student", branch_id=None, email_suffix=""):
    user_map = {
        "super_admin": {"email": f"admin{email_suffix}@edumanage.com", "password": "AdminPass123!", "full_name": "Super Admin", "phone": f"30{email_suffix}", "role": "super_admin"},
        "coach_admin": {"email": f"coach_admin{email_suffix}@edumanage.com", "password": "CoachAdminPass123!", "full_name": "Coach Admin", "phone": f"31{email_suffix}", "role": "coach_admin"},
        "student": {"email": f"student{email_suffix}@edumanage.com", "password": "Student123!", "full_name": "Test Student", "phone": f"32{email_suffix}", "role": "student"}
    }
    user_data = user_map[role]
    if branch_id:
        user_data["branch_id"] = branch_id

    reg_response = client.post("/api/auth/register", json=user_data)

    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    token = login_response.json()["access_token"]

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me_response.json()["id"]
    return token, user_id

def create_branch(client, admin_token, name):
    email_name = name.replace(" ", "")
    branch_data = {"name": name, "address": "a", "city": "c", "state": "s", "pincode": "p", "phone": "p", "email": f"{email_name}@e.com"}
    response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    return response.json()["branch_id"]

def test_holiday_management():
    """Test CRUD operations for branch holidays."""
    with TestClient(app) as client:
        admin_token, _ = get_token_and_id(client, "super_admin", email_suffix="_h_sa")
        branch1_id = create_branch(client, admin_token, "Branch1")
        branch2_id = create_branch(client, admin_token, "Branch2")
        coach_admin_token, _ = get_token_and_id(client, "coach_admin", branch_id=branch1_id, email_suffix="_h_ca")

        holiday_data = {"date": (date.today() + timedelta(days=30)).isoformat(), "description": "Annual Day"}

        # 1. Super Admin can add a holiday to any branch
        res_sa_add = client.post(f"/api/branches/{branch2_id}/holidays", json=holiday_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_sa_add.status_code == 201
        holiday_id = res_sa_add.json()["id"]

        # 2. Coach Admin can add a holiday to their own branch
        res_ca_add = client.post(f"/api/branches/{branch1_id}/holidays", json=holiday_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_ca_add.status_code == 201

        # 3. Coach Admin cannot add a holiday to another branch
        res_ca_add_fail = client.post(f"/api/branches/{branch2_id}/holidays", json=holiday_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_ca_add_fail.status_code == 403

        # 4. Anyone can get the list of holidays
        res_get = client.get(f"/api/branches/{branch2_id}/holidays", headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_get.status_code == 200
        assert len(res_get.json()["holidays"]) == 1

        # 5. Coach Admin can delete a holiday from their own branch
        res_ca_del = client.delete(f"/api/branches/{branch1_id}/holidays/{res_ca_add.json()['id']}", headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_ca_del.status_code == 204

        # 6. Super Admin can delete any holiday
        res_sa_del = client.delete(f"/api/branches/{branch2_id}/holidays/{holiday_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_sa_del.status_code == 204

def test_coach_admin_branch_update():
    """Test a Coach Admin's ability to update their own branch."""
    with TestClient(app) as client:
        admin_token, _ = get_token_and_id(client, "super_admin", email_suffix="_bu_sa")
        branch1_id = create_branch(client, admin_token, "UpdateBranch1")
        branch2_id = create_branch(client, admin_token, "UpdateBranch2")
        coach_admin_token, _ = get_token_and_id(client, "coach_admin", branch_id=branch1_id, email_suffix="_bu_ca")

        update_data = {"phone": "123-456-7890", "address": "New Address"}
        restricted_update = {"is_active": False}

        # 1. Success: Coach Admin updates their own branch
        res_success = client.put(f"/api/branches/{branch1_id}", json=update_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_success.status_code == 200

        # 2. Failure: Coach Admin tries to update another branch
        res_fail_branch = client.put(f"/api/branches/{branch2_id}", json=update_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_fail_branch.status_code == 403

        # 3. Failure: Coach Admin tries to update a restricted field
        res_fail_field = client.put(f"/api/branches/{branch1_id}", json=restricted_update, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert res_fail_field.status_code == 403

def test_delete_branch_success():
    """Test that a Super Admin can delete a branch with no dependencies."""
    with TestClient(app) as client:
        admin_token, _ = get_token_and_id(client, "super_admin", email_suffix="_del_b_sa")
        branch_id = create_branch(client, admin_token, "Deletable Branch")

        # Delete the branch
        res_delete = client.delete(f"/api/branches/{branch_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_delete.status_code == 204

        # Verify it's gone
        res_get = client.get(f"/api/branches/{branch_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_get.status_code == 404

def test_delete_branch_with_users_fails():
    """Test that deleting a branch with associated users fails."""
    with TestClient(app) as client:
        admin_token, _ = get_token_and_id(client, "super_admin", email_suffix="_del_b_fail_sa")
        branch_id = create_branch(client, admin_token, "Non-Deletable Branch")

        # Create a user in the branch, which is a dependency
        get_token_and_id(client, "student", branch_id=branch_id, email_suffix="_del_b_stud")

        # Attempt to delete the branch
        res_delete = client.delete(f"/api/branches/{branch_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_delete.status_code == 400
        assert "Cannot delete branch with associated users" in res_delete.json()["detail"]

def test_branch_report_export():
    """Test exporting a branch report to CSV."""
    with TestClient(app) as client:
        admin_token, _ = get_token_and_id(client, "super_admin", email_suffix="_brexp_sa")
        branch_id = create_branch(client, admin_token, "Export Branch")

        # Setup some data in the branch
        get_token_and_id(client, "student", branch_id=branch_id, email_suffix="_brexp_s1")

        # Call the export endpoint
        response = client.get(f"/api/reports/branch/{branch_id}/export", headers={"Authorization": f"Bearer {admin_token}"})

        # Verify headers and content
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment; filename=" in response.headers["content-disposition"]
        assert "Total Students,1" in response.content.decode("utf-8")

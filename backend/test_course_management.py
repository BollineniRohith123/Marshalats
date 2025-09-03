import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "courses", "enrollments", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client, suffix=""):
    email = f"admin_course{suffix}@edumanage.com"
    user_data = {"email": email, "password": "AdminPass123!", "full_name": f"Course Admin{suffix}", "phone": f"120{suffix}", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": email, "password": user_data["password"]})
    return login_response.json()["access_token"]

def create_course(client, admin_token, name="Test Course"):
    course_data = {"name": name, "description": "d", "duration_months": 1, "base_fee": 1}
    res = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    return res.json()["course_id"]

def test_delete_course_success():
    """Test that a Super Admin can delete a course with no enrollments."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        course_id = create_course(client, admin_token)

        # Delete the course
        res_delete = client.delete(f"/api/courses/{course_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_delete.status_code == 204

        # Verify it's gone
        res_get = client.get("/api/courses", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(res_get.json()["courses"]) == 0

def test_delete_course_with_enrollment_fails():
    """Test that deleting a course with enrollments fails."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_enroll")

        # Setup: Create course, user, and enrollment
        course_id = create_course(client, admin_token)

        branch_res = client.post("/api/branches", json={"name":"B_Del","address":"a","city":"c","state":"s","pincode":"p","email":"b_del@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]

        student_data = {"email": "s_del@e.com", "password": "p", "full_name": "s", "phone": "121", "role": "student", "branch_id": branch_id}
        user_res = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {admin_token}"})
        student_id = user_res.json()["user_id"]

        enrollment_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100}
        client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})

        # Attempt to delete the course
        res_delete = client.delete(f"/api/courses/{course_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_delete.status_code == 400
        assert "Cannot delete course with existing enrollments" in res_delete.json()["detail"]

def test_course_attendance_policy():
    """Test setting and retrieving an attendance policy for a course."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_policy")

        # Create a course with an attendance policy
        policy = {"min_percentage": 80, "max_absences": 10}
        course_data = {"name": "Policy Course", "description": "d", "duration_months": 1, "base_fee": 1, "attendance_policy": policy}
        res_create = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_create.status_code == 200
        course_id = res_create.json()["course_id"]

        # Retrieve the course and verify the policy
        res_get = client.get(f"/api/courses", headers={"Authorization": f"Bearer {admin_token}"})
        course = res_get.json()["courses"][0]
        assert course["id"] == course_id
        assert course["attendance_policy"]["min_percentage"] == 80

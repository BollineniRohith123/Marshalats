import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "courses", "enrollments", "course_change_requests", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_token_and_id(client, role="student", branch_id=None, email_suffix=""):
    # Simplified helper
    user_map = {
        "super_admin": {"email": f"admin{email_suffix}@edumanage.com", "password": "AdminPass123!", "full_name": "Super Admin", "phone": f"40{email_suffix}", "role": "super_admin"},
        "student": {"email": f"student{email_suffix}@edumanage.com", "password": "Student123!", "full_name": "Test Student", "phone": f"41{email_suffix}", "role": "student"},
    }
    user_data = user_map[role]
    if branch_id:
        user_data["branch_id"] = branch_id

    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    token = login_response.json()["access_token"]
    user_id = login_response.json()["user"]["id"]
    return token, user_id

def create_branch(client, admin_token, name):
    email_name = name.replace(" ", "")
    branch_data = {"name": name, "address": "a", "city": "c", "state": "s", "pincode": "p", "phone": "p", "email": f"{email_name}@e.com"}
    response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    return response.json()["branch_id"]

def create_course(client, admin_token, name):
    course_data = {"name": name, "description": "d", "duration_months": 1, "base_fee": 100}
    response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
    return response.json()["course_id"]

def enroll_student(client, admin_token, student_id, course_id, branch_id):
    enrollment_data = {
        "student_id": student_id,
        "course_id": course_id,
        "branch_id": branch_id,
        "start_date": datetime.now().isoformat(),
        "fee_amount": 100.0
    }
    response = client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})
    return response.json()["enrollment_id"]

def test_course_change_request_flow():
    """Test the full lifecycle of a student course change request."""
    with TestClient(app) as client:
        # 1. Setup
        admin_token, _ = get_token_and_id(client, "super_admin", email_suffix="_ccr")
        branch_id = create_branch(client, admin_token, "CCR Branch")
        course1_id = create_course(client, admin_token, "Course One")
        course2_id = create_course(client, admin_token, "Course Two")
        student_token, student_id = get_token_and_id(client, "student", branch_id=branch_id, email_suffix="_ccr")
        enrollment1_id = enroll_student(client, admin_token, student_id, course1_id, branch_id)

        # 2. Student requests a course change
        request_data = {
            "current_enrollment_id": enrollment1_id,
            "new_course_id": course2_id,
            "reason": "Switching to a different discipline."
        }
        res_create = client.post("/api/requests/course-change", json=request_data, headers={"Authorization": f"Bearer {student_token}"})
        assert res_create.status_code == 201
        request_id = res_create.json()["id"]

        # 3. Admin sees the pending request
        res_get = client.get("/api/requests/course-change?status=pending", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(res_get.json()["requests"]) == 1
        assert res_get.json()["requests"][0]["id"] == request_id

        # 4. Admin approves the request
        res_approve = client.put(f"/api/requests/course-change/{request_id}", json={"status": "approved"}, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_approve.status_code == 200

        # 5. Verify old enrollment is inactive
        res_enrollments = client.get(f"/api/enrollments?student_id={student_id}", headers={"Authorization": f"Bearer {admin_token}"})
        enrollments = res_enrollments.json()["enrollments"]
        old_enrollment = next((e for e in enrollments if e["id"] == enrollment1_id), None)
        assert old_enrollment is not None
        assert old_enrollment["is_active"] is False

        # 6. Verify new enrollment exists and is active
        new_enrollment = next((e for e in enrollments if e["course_id"] == course2_id), None)
        assert new_enrollment is not None
        assert new_enrollment["is_active"] is True

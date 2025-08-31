import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "courses", "enrollments", "attendance", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client):
    user_data = {"email": "admin_bio@edumanage.com", "password": "AdminPass123!", "full_name": "Bio Admin", "phone": "50", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    return login_response.json()["access_token"]

def setup_student_for_attendance(client, admin_token, biometric_id, email="bio_student@e.com", phone="51"):
    # Create branch, course, and student with a biometric ID
    branch_res = client.post("/api/branches", json={"name":"B","address":"a","city":"c","state":"s","pincode":"p","email":"b@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
    branch_id = branch_res.json()["branch_id"]
    course_res = client.post("/api/courses", json={"name":"C","description":"d","duration_months":1,"base_fee":1}, headers={"Authorization": f"Bearer {admin_token}"})
    course_id = course_res.json()["course_id"]

    student_data = {"email": email, "password": "p", "full_name": "Bio Student", "phone": phone, "role": "student", "branch_id": branch_id, "biometric_id": biometric_id}
    user_res = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {admin_token}"})
    student_id = user_res.json()["user_id"]

    # Enroll the student
    enrollment_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100}
    client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})

def test_biometric_attendance_success():
    """Test successful attendance marking via biometric endpoint."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        biometric_id = "fingerprint_123"
        setup_student_for_attendance(client, admin_token, biometric_id)

        attendance_payload = {
            "device_id": "Device001",
            "biometric_id": biometric_id,
            "timestamp": datetime.now().isoformat()
        }

        response = client.post("/api/attendance/biometric", json=attendance_payload)
        assert response.status_code == 200
        assert response.json()["message"] == "Attendance marked successfully"

        # Verify that a second attempt on the same day returns the correct message
        response_again = client.post("/api/attendance/biometric", json=attendance_payload)
        assert response_again.status_code == 200
        assert response_again.json()["message"] == "Attendance already marked for today."

def test_biometric_attendance_failures():
    """Test failure scenarios for the biometric attendance endpoint."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        setup_student_for_attendance(client, admin_token, "fingerprint_456", email="bio_student2@e.com", phone="52")

        # 1. Failure: Biometric ID not found
        payload_not_found = {
            "device_id": "Device001",
            "biometric_id": "non_existent_id",
            "timestamp": datetime.now().isoformat()
        }
        response_not_found = client.post("/api/attendance/biometric", json=payload_not_found)
        assert response_not_found.status_code == 404

        # 2. Failure: Student has no active enrollment (setup a new student without one)
        no_enroll_student = {"email": "no_enroll@e.com", "password": "p", "full_name": "No Enroll", "phone": "53", "role": "student", "biometric_id": "no_enroll_bio_id"}
        client.post("/api/users", json=no_enroll_student, headers={"Authorization": f"Bearer {admin_token}"})

        payload_no_enroll = {
            "device_id": "Device001",
            "biometric_id": "no_enroll_bio_id",
            "timestamp": datetime.now().isoformat()
        }
        response_no_enroll = client.post("/api/attendance/biometric", json=payload_no_enroll)
        assert response_no_enroll.status_code == 400

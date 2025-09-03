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
    user_data = {"email": "admin_anomaly@edumanage.com", "password": "AdminPass123!", "full_name": "Anomaly Admin", "phone": "140", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    return login_response.json()["access_token"]

def setup_student_with_attendance(client, admin_token, email, phone, attendance_pattern):
    branch_res = client.post("/api/branches", json={"name":"B_Anom","address":"a","city":"c","state":"s","pincode":"p","email":f"b_{phone}@e.com","phone":f"ph{phone}"}, headers={"Authorization": f"Bearer {admin_token}"})
    branch_id = branch_res.json()["branch_id"]
    course_res = client.post("/api/courses", json={"name":"C_Anom","description":"d","duration_months":1,"base_fee":1}, headers={"Authorization": f"Bearer {admin_token}"})
    course_id = course_res.json()["course_id"]

    student_data = {"email": email, "password": "p", "full_name": "Anomaly Student", "phone": phone, "role": "student", "branch_id": branch_id}
    user_res = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {admin_token}"})
    student_id = user_res.json()["user_id"]

    enrollment_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100}
    client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})

    for i, is_present in enumerate(attendance_pattern):
        att_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "attendance_date": datetime(2025, 1, i + 1).isoformat(), "method": "manual", "is_present": is_present}
        client.post("/api/attendance/manual", json=att_data, headers={"Authorization": f"Bearer {admin_token}"})

    return student_id

def test_get_attendance_anomalies():
    """Test the endpoint for finding attendance anomalies."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)

        # Student 1: Has 3 consecutive absences at the end
        s1_pattern = [True, True, False, False, False]
        s1_id = setup_student_with_attendance(client, admin_token, "s1_anom@e.com", "141", s1_pattern)

        # Student 2: Has absences, but not 3 consecutively at the end
        s2_pattern = [False, False, True, False, True]
        s2_id = setup_student_with_attendance(client, admin_token, "s2_anom@e.com", "142", s2_pattern)

        # Student 3: Has only 2 records (should not be an anomaly)
        s3_pattern = [False, False]
        s3_id = setup_student_with_attendance(client, admin_token, "s3_anom@e.com", "143", s3_pattern)

        # Call the anomalies endpoint
        response = client.get("/api/attendance/anomalies", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200

        anomalies = response.json()["anomalies"]
        assert len(anomalies) == 1
        assert anomalies[0]["student_id"] == s1_id

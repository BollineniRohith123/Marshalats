import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "courses", "enrollments", "attendance", "notification_templates", "notification_logs", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client):
    user_data = {"email": "admin_att_rem@edumanage.com", "password": "AdminPass123!", "full_name": "Att Rem Admin", "phone": "150", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    return login_response.json()["access_token"]

def setup_student_with_low_attendance(client, admin_token):
    # Create branch and course with a strict policy
    policy = {"min_percentage": 80}
    branch_res = client.post("/api/branches", json={"name":"B_AttRem","address":"a","city":"c","state":"s","pincode":"p","email":"b_attrem@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
    branch_id = branch_res.json()["branch_id"]
    course_res = client.post("/api/courses", json={"name":"C_AttRem","description":"d","duration_months":1,"base_fee":1, "attendance_policy": policy}, headers={"Authorization": f"Bearer {admin_token}"})
    course_id = course_res.json()["course_id"]

    # Create student and enroll
    student_data = {"email": "low_att@e.com", "password": "p", "full_name": "Low Attender", "phone": "151", "role": "student", "branch_id": branch_id}
    user_res = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {admin_token}"})
    student_id = user_res.json()["user_id"]
    enrollment_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100}
    client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})

    # Mark attendance such that percentage is below 80% (e.g., 2 present, 3 absent = 40%)
    attendance_pattern = [True, True, False, False, False]
    for i, is_present in enumerate(attendance_pattern):
        att_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "attendance_date": datetime(2025, 2, i + 1).isoformat(), "method": "manual", "is_present": is_present}
        client.post("/api/attendance/manual", json=att_data, headers={"Authorization": f"Bearer {admin_token}"})

    # Create the required notification template
    template_data = {"name": "low_attendance_warning", "type": "sms", "body": "Hi {{student_name}}, your attendance for {{course_name}} is low ({{attendance_percentage}})."}
    client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})

def test_send_low_attendance_reminders():
    """Test the endpoint for sending low attendance reminders."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        setup_student_with_low_attendance(client, admin_token)

        # Call the reminder endpoint
        response = client.post("/api/reminders/attendance", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert response.json()["message"] == "Sent 1 low attendance warnings."

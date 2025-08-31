import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "courses", "enrollments", "complaints", "notification_templates", "notification_logs", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client, suffix=""):
    email = f"admin_notify_enh{suffix}@edumanage.com"
    user_data = {"email": email, "password": "AdminPass123!", "full_name": f"Notify Admin{suffix}", "phone": f"100{suffix}", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": email, "password": user_data["password"]})
    return login_response.json()["access_token"]

def create_user_and_get_token(client, admin_token, suffix, branch_id):
    email = f"student{suffix}@notify.com"
    user_data = {"email": email, "password": "p", "full_name": f"Student {suffix}", "phone": f"101{suffix}", "role": "student", "branch_id": branch_id}
    user_res = client.post("/api/users", json=user_data, headers={"Authorization": f"Bearer {admin_token}"})
    user_id = user_res.json()["user_id"]
    token = client.post("/api/auth/login", json={"email": email, "password": "p"}).json()["access_token"]
    return token, user_id

def test_complaint_status_update_notification():
    """Test that a student is notified when their complaint status changes."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)

        # Setup: Create a branch, student, complaint, and template
        branch_res = client.post("/api/branches", json={"name":"B_Notify","address":"a","city":"c","state":"s","pincode":"p","email":"b_notify@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]
        student_token, student_id = create_user_and_get_token(client, admin_token, "_complaint", branch_id)

        template_data = {"name": "complaint_status_update", "type": "whatsapp", "body": "Your complaint '{{subject}}' is now {{status}}."}
        client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})

        complaint_data = {"subject": "Test Complaint", "description": "d", "category": "c"}
        complaint_id = client.post("/api/complaints", json=complaint_data, headers={"Authorization": f"Bearer {student_token}"}).json()["complaint_id"]

        # Update the complaint status
        client.put(f"/api/complaints/{complaint_id}", json={"status": "resolved"}, headers={"Authorization": f"Bearer {admin_token}"})

        # Verify a notification log was created
        import pymongo
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.notification_logs.find_one({"user_id": student_id})
        mongo_client.close()

        assert log is not None
        assert "resolved" in log["content"]
        assert "Test Complaint" in log["content"]

def test_class_reminder_notification():
    """Test sending class reminders to enrolled students."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_reminder")

        # Setup: branch, course, 2 students enrolled, 1 not enrolled, and a template
        branch_res = client.post("/api/branches", json={"name":"B_Rem","address":"a","city":"c","state":"s","pincode":"p","email":"b_rem@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]
        course_res = client.post("/api/courses", json={"name":"Rem Course","description":"d","duration_months":1,"base_fee":1}, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_res.json()["course_id"]

        _, s1_id = create_user_and_get_token(client, admin_token, "_s1", branch_id)
        _, s2_id = create_user_and_get_token(client, admin_token, "_s2", branch_id)

        enroll_data1 = {"student_id":s1_id, "course_id":course_id, "branch_id":branch_id, "start_date":datetime.now().isoformat(), "fee_amount":100}
        client.post("/api/enrollments", json=enroll_data1, headers={"Authorization": f"Bearer {admin_token}"})
        enroll_data2 = {"student_id":s2_id, "course_id":course_id, "branch_id":branch_id, "start_date":datetime.now().isoformat(), "fee_amount":100}
        client.post("/api/enrollments", json=enroll_data2, headers={"Authorization": f"Bearer {admin_token}"})

        template_data = {"name": "class_reminder", "type": "sms", "body": "Hi {{student_name}}, friendly reminder for your {{course_name}} class tomorrow!"}
        client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})

        # Send reminders
        reminder_data = {"course_id": course_id, "branch_id": branch_id}
        res = client.post("/api/reminders/class", json=reminder_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert "Sent 2 class reminders" in res.json()["message"]

        # Verify logs
        import pymongo
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log_count = db.notification_logs.count_documents({})
        mongo_client.close()
        assert log_count == 2

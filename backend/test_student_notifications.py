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

def create_user_and_get_token(client, admin_token, suffix, branch_id, role="student"):
    email = f"user{suffix}@{role.replace('_', '-')}.notify.com"
    user_data = {"email": email, "password": "p", "full_name": f"User {suffix}", "phone": f"101{suffix}", "role": role}
    if branch_id:
        user_data["branch_id"] = branch_id

    user_res = client.post("/api/users", json=user_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert user_res.status_code == 200, f"Failed to create user {email}. Response: {user_res.json()}"
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

def test_coach_admin_notified_on_profile_update():
    """Test that a Coach Admin is notified when a user in their branch is updated."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_prof_upd")

        # Setup
        branch_res = client.post("/api/branches", json={"name":"B_Notify_Upd","address":"a","city":"c","state":"s","pincode":"p","email":"b_notify_upd@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]

        _, coach_admin_id = create_user_and_get_token(client, admin_token, "_ca_upd", branch_id, role="coach_admin")
        _, student_id = create_user_and_get_token(client, admin_token, "_student_upd", branch_id)

        template_data = {"name": "profile_update_alert", "type": "sms", "body": "Profile for {{updated_user_name}} was updated by {{admin_name}}."}
        client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})

        # Super Admin updates the student's profile
        update_data = {"full_name": "Updated Student Name"}
        client.put(f"/api/users/{student_id}", json=update_data, headers={"Authorization": f"Bearer {admin_token}"})

        # Verify a notification log was created for the Coach Admin
        import pymongo
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.notification_logs.find_one({"user_id": coach_admin_id})
        mongo_client.close()

        assert log is not None
        assert "Updated Student Name" in log["content"]

def test_course_completion_notification():
    """Test that a student is notified when their enrollment is marked as complete."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_comp")

        # Setup
        branch_res = client.post("/api/branches", json={"name":"B_Comp","address":"a","city":"c","state":"s","pincode":"p","email":"b_comp@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]

        _, student_id = create_user_and_get_token(client, admin_token, "_comp_s1", branch_id)

        course_res = client.post("/api/courses", json={"name":"Comp Course","description":"d","duration_months":1,"base_fee":1}, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_res.json()["course_id"]

        enroll_data = {"student_id":student_id, "course_id":course_id, "branch_id":branch_id, "start_date":datetime.now().isoformat(), "fee_amount":100}
        enrollment_id = client.post("/api/enrollments", json=enroll_data, headers={"Authorization": f"Bearer {admin_token}"}).json()["enrollment_id"]

        template_data = {"name": "course_completion", "type": "sms", "body": "Congratulations {{student_name}} on completing {{course_name}}!"}
        client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})

        # Mark enrollment as inactive (complete)
        client.put(f"/api/enrollments/{enrollment_id}", json={"is_active": False}, headers={"Authorization": f"Bearer {admin_token}"})

        # Verify notification log
        import pymongo
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.notification_logs.find_one({"user_id": student_id})
        mongo_client.close()

        assert log is not None
        assert "Congratulations" in log["content"]

def test_get_my_notification_history():
    """Test that a student can retrieve their notification history."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_hist")

        # Setup
        branch_res = client.post("/api/branches", json={"name":"B_Hist","address":"a","city":"c","state":"s","pincode":"p","email":"b_hist@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]
        student_token, student_id = create_user_and_get_token(client, admin_token, "_hist_s1", branch_id)

        # Create a notification for the student
        template_data = {"name": "hist_test", "type": "sms", "body": "History test"}
        template_id = client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"}).json()["id"]
        trigger_data = {"user_id": student_id, "template_id": template_id, "context": {}}
        client.post("/api/notifications/trigger", json=trigger_data, headers={"Authorization": f"Bearer {admin_token}"})

        # Get notification history as the student
        res = client.get("/api/notifications/my-history", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["logs"][0]["content"] == "History test"

def test_get_me_with_manager_info():
    """Test that the /me endpoint returns branch and manager details."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_mgr")

        # Create a manager (Coach Admin)
        manager_res = client.post("/api/users", json={"email":"mgr@e.com", "password":"p", "full_name":"Test Manager", "phone":"170", "role":"coach_admin"}, headers={"Authorization": f"Bearer {admin_token}"})
        manager_id = manager_res.json()["user_id"]

        # Create a branch and assign the manager
        branch_res = client.post("/api/branches", json={"name":"Managed Branch","address":"a","city":"c","state":"s","pincode":"p","email":"managed@e.com","phone":"ph", "manager_id": manager_id}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]

        # Assign the manager to the branch
        client.put(f"/api/users/{manager_id}", json={"branch_id": branch_id}, headers={"Authorization": f"Bearer {admin_token}"})

        # Create a student in that branch
        student_token, _ = create_user_and_get_token(client, admin_token, "_stud_mgr", branch_id)

        # Call /me as the student
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200

        user_info = res.json()
        assert "branch_details" in user_info
        assert user_info["branch_details"]["name"] == "Managed Branch"
        assert user_info["branch_details"]["manager_name"] == "Test Manager"

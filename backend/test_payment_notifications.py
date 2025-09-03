import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "payments", "notification_templates", "notification_logs", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def setup_test_data(client):
    # Create Super Admin to create other users
    admin_data = {"email": "admin_pay_notif@e.com", "password": "p", "full_name": "Admin", "phone": "160", "role": "super_admin"}
    client.post("/api/auth/register", json=admin_data)
    admin_token = client.post("/api/auth/login", json={"email": admin_data["email"], "password": "p"}).json()["access_token"]

    # Create Branch
    branch_res = client.post("/api/branches", json={"name":"B_PayNotif","address":"a","city":"c","state":"s","pincode":"p","email":"b_paynotif@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
    branch_id = branch_res.json()["branch_id"]

    # Create Coach Admin for the branch
    ca_data = {"email": "ca_pay_notif@e.com", "password": "p", "full_name": "CA Pay Notif", "phone": "161", "role": "coach_admin", "branch_id": branch_id}
    ca_res = client.post("/api/users", json=ca_data, headers={"Authorization": f"Bearer {admin_token}"})
    coach_admin_id = ca_res.json()["user_id"]

    # Create Student in the branch
    student_data = {"email": "s_pay_notif@e.com", "password": "p", "full_name": "Student Pay Notif", "phone": "162", "role": "student", "branch_id": branch_id}
    s_res = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {admin_token}"})
    student_id = s_res.json()["user_id"]
    student_token = client.post("/api/auth/login", json={"email": student_data["email"], "password": "p"}).json()["access_token"]

    # Create an OVERDUE payment for the student
    payment_data = {"id":"p1","student_id":student_id,"enrollment_id":"e1","amount":100,"payment_type":"course_fee","payment_method":"cash","due_date":datetime(2024,1,10).isoformat(),"payment_status":"overdue"}
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    db.payments.insert_one(payment_data)
    mongo_client.close()

    # Create notification template
    template_data = {"name": "payment_default_alert", "type": "whatsapp", "body": "Access for student {{student_name}} has been restricted due to overdue payments."}
    client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})

    return student_token, coach_admin_id


def test_coach_admin_notified_on_payment_default():
    """Test that a Coach Admin is notified when a student's access is restricted."""
    with TestClient(app) as client:
        student_token, coach_admin_id = setup_test_data(client)

        # Attempt to access a protected endpoint as the student
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})

        # Verify student access is denied
        assert response.status_code == 403
        assert "Access restricted" in response.json()["detail"]

        # Verify a notification log was created for the Coach Admin
        import pymongo
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.notification_logs.find_one({"user_id": coach_admin_id})
        mongo_client.close()

        assert log is not None
        assert "Student Pay Notif" in log["content"]

import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "courses", "enrollments", "payments", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client):
    user_data = {"email": "admin_remind@edumanage.com", "password": "AdminPass123!", "full_name": "Reminder Admin", "phone": "70", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    return login_response.json()["access_token"]

def setup_payment_data(client, admin_token):
    branch_res = client.post("/api/branches", json={"name":"B","address":"a","city":"c","state":"s","pincode":"p","email":"b_rem@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
    branch_id = branch_res.json()["branch_id"]
    course_res = client.post("/api/courses", json={"name":"C","description":"d","duration_months":1,"base_fee":1}, headers={"Authorization": f"Bearer {admin_token}"})
    course_id = course_res.json()["course_id"]

    # Student 1 with a pending payment
    s1_data = {"email": "s1_rem@e.com", "password": "p", "full_name": "s1", "phone": "71", "role": "student", "branch_id": branch_id}
    user_res = client.post("/api/users", json=s1_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert user_res.status_code == 200, "Failed to create student 1"
    s1_id = user_res.json()["user_id"]
    e1_data = {"student_id": s1_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100}
    enroll_res = client.post("/api/enrollments", json=e1_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert enroll_res.status_code == 200, "Failed to enroll student 1"

    # Student 2 with a paid payment (should not get a reminder)
    s2_data = {"email": "s2_rem@e.com", "password": "p", "full_name": "s2", "phone": "72", "role": "student", "branch_id": branch_id}
    user_res2 = client.post("/api/users", json=s2_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert user_res2.status_code == 200, "Failed to create student 2"
    s2_id = user_res2.json()["user_id"]
    e2_data = {"student_id": s2_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100}
    e2_res = client.post("/api/enrollments", json=e2_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert e2_res.status_code == 200, "Failed to enroll student 2"
    e2_id = e2_res.json()["enrollment_id"]

    payments_res = client.get(f"/api/payments?enrollment_id={e2_id}", headers={"Authorization":f"Bearer {admin_token}"})
    assert payments_res.status_code == 200, "Failed to get payments for student 2"
    payment = payments_res.json()["payments"][0]

    update_res = client.put(f"/api/payments/{payment['id']}", json={"payment_status": "paid", "transaction_id": "T1"}, headers={"Authorization":f"Bearer {admin_token}"})
    assert update_res.status_code == 200, "Failed to update payment for student 2"


def test_send_payment_reminders():
    """Test the endpoint for sending payment reminders."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        setup_payment_data(client, admin_token)

        response = client.post("/api/payments/send-reminders", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        # Student 1 has 2 pending payments (admission and course fee)
        # Student 2 has 1 pending payment (the other was paid)
        assert response.json()["message"] == "Successfully sent 3 payment reminders."

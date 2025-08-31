import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime
import csv
import io

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
    user_data = {"email": "admin_export@edumanage.com", "password": "AdminPass123!", "full_name": "Export Admin", "phone": "60", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    return login_response.json()["access_token"]

def setup_attendance_data(client, admin_token):
    # Create branch, course, student, and enroll
    branch_res = client.post("/api/branches", json={"name":"B","address":"a","city":"c","state":"s","pincode":"p","email":"b_exp@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
    branch_id = branch_res.json()["branch_id"]
    course_res = client.post("/api/courses", json={"name":"C","description":"d","duration_months":1,"base_fee":1}, headers={"Authorization": f"Bearer {admin_token}"})
    course_id = course_res.json()["course_id"]
    student_data = {"email": "export_student@e.com", "password": "p", "full_name": "Export Student", "phone": "61", "role": "student", "branch_id": branch_id}
    user_res = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {admin_token}"})
    student_id = user_res.json()["user_id"]
    enrollment_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100}
    client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})

    # Create two attendance records
    att1 = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "attendance_date": datetime(2025, 1, 5).isoformat(), "method": "manual"}
    att2 = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "attendance_date": datetime(2025, 1, 6).isoformat(), "method": "manual"}
    client.post("/api/attendance/manual", json=att1, headers={"Authorization": f"Bearer {admin_token}"})
    client.post("/api/attendance/manual", json=att2, headers={"Authorization": f"Bearer {admin_token}"})
    return student_id

def test_attendance_export():
    """Test exporting attendance records to a CSV file."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        student_id = setup_attendance_data(client, admin_token)

        # Call the export endpoint
        response = client.get(f"/api/attendance/reports/export?student_id={student_id}", headers={"Authorization": f"Bearer {admin_token}"})

        # Verify headers
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment; filename=" in response.headers["content-disposition"]

        # Verify CSV content
        csv_content = response.content.decode("utf-8")
        reader = csv.reader(io.StringIO(csv_content))

        rows = list(reader)
        # 1 header row + 2 data rows
        assert len(rows) == 3

        # Check header
        assert rows[0] == ["attendance_id", "student_id", "course_id", "branch_id", "attendance_date", "check_in_time", "method", "is_present", "notes"]

        # Check data (just check the student_id in the data rows)
        assert rows[1][1] == student_id
        assert rows[2][1] == student_id

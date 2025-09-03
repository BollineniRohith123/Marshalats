import pytest
from fastapi.testclient import TestClient
from backend.server import app
from datetime import datetime, timedelta

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "payments", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client):
    user_data = {"email": "admin_fin@edumanage.com", "password": "AdminPass123!", "full_name": "Finance Admin", "phone": "80", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    return login_response.json()["access_token"]

def setup_finance_data(client, admin_token):
    # Manually insert payments to control dates precisely
    p1_data = {"id":"p1","student_id":"s1","enrollment_id":"e1","amount":100,"payment_type":"course_fee","payment_method":"cash","due_date":datetime(2025,1,10),"payment_status":"paid","payment_date":datetime(2025,1,5)}
    p2_data = {"id":"p2","student_id":"s2","enrollment_id":"e2","amount":200,"payment_type":"course_fee","payment_method":"cash","due_date":datetime(2025,2,10),"payment_status":"paid","payment_date":datetime(2025,2,5)}
    p3_data = {"id":"p3","student_id":"s3","enrollment_id":"e3","amount":50,"payment_type":"course_fee","payment_method":"cash","due_date":datetime(2025,1,15),"payment_status":"pending"}
    p4_data = {"id":"p4","student_id":"s4","enrollment_id":"e4","amount":75,"payment_type":"course_fee","payment_method":"cash","due_date":datetime(2025,2,15),"payment_status":"pending"}

    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    db.payments.insert_many([p1_data, p2_data, p3_data, p4_data])
    mongo_client.close()


def test_financial_report_with_date_range():
    """Test the financial report endpoint with a date range."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        setup_finance_data(client, admin_token)

        # 1. Test report for January
        start_date = datetime(2025, 1, 1).isoformat()
        end_date = datetime(2025, 1, 31).isoformat()
        response_jan = client.get(f"/api/reports/financial?start_date={start_date}&end_date={end_date}", headers={"Authorization": f"Bearer {admin_token}"})

        assert response_jan.status_code == 200
        report_jan = response_jan.json()
        assert report_jan["total_collected"] == 100 # p1
        assert report_jan["outstanding_dues"] == 50 # p3

        # 2. Test report for February
        start_date = datetime(2025, 2, 1).isoformat()
        end_date = datetime(2025, 2, 28).isoformat()
        response_feb = client.get(f"/api/reports/financial?start_date={start_date}&end_date={end_date}", headers={"Authorization": f"Bearer {admin_token}"})

        assert response_feb.status_code == 200
        report_feb = response_feb.json()
        assert report_feb["total_collected"] == 200 # p2
        assert report_feb["outstanding_dues"] == 75 # p4

        # 3. Test report with no date range (should include everything)
        response_all = client.get("/api/reports/financial", headers={"Authorization": f"Bearer {admin_token}"})
        assert response_all.status_code == 200
        report_all = response_all.json()
        assert report_all["total_collected"] == 300 # p1 + p2
        assert report_all["outstanding_dues"] == 125 # p3 + p4

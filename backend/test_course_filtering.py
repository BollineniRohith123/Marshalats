import pytest
from fastapi.testclient import TestClient
from backend.server import app
import pymongo

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Fixture to clean up the database before and after tests."""
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "courses", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client):
    """Helper to get a super admin token."""
    user_data = {"email": "admin_filter@edumanage.com", "password": "AdminPass123!", "full_name": "Filter Admin", "phone": "20", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    return login_response.json()["access_token"]

def test_course_filtering():
    """Test filtering courses by category and level."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)

        # Create a variety of courses
        courses_data = [
            {"name": "Karate Basics", "description": "d", "duration_months": 1, "base_fee": 1, "category": "Martial Arts", "level": "Beginner"},
            {"name": "Advanced Karate", "description": "d", "duration_months": 1, "base_fee": 1, "category": "Martial Arts", "level": "Advanced"},
            {"name": "Yoga for Beginners", "description": "d", "duration_months": 1, "base_fee": 1, "category": "Fitness", "level": "Beginner"},
            {"name": "Zumba", "description": "d", "duration_months": 1, "base_fee": 1, "category": "Fitness", "level": "Intermediate"},
            {"name": "Salsa Dance", "description": "d", "duration_months": 1, "base_fee": 1, "category": "Dance", "level": "Beginner"},
        ]
        for course in courses_data:
            response = client.post("/api/courses", json=course, headers={"Authorization": f"Bearer {admin_token}"})
            assert response.status_code == 200

        # 1. Test no filters - should return all 5 courses
        response_all = client.get("/api/courses", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(response_all.json()["courses"]) == 5

        # 2. Test filter by category "Martial Arts" - should return 2 courses
        response_cat = client.get("/api/courses?category=Martial%20Arts", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(response_cat.json()["courses"]) == 2

        # 3. Test filter by level "Beginner" - should return 3 courses
        response_level = client.get("/api/courses?level=Beginner", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(response_level.json()["courses"]) == 3

        # 4. Test filter by category "Fitness" and level "Beginner" - should return 1 course
        response_both = client.get("/api/courses?category=Fitness&level=Beginner", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(response_both.json()["courses"]) == 1
        assert response_both.json()["courses"][0]["name"] == "Yoga for Beginners"

        # 5. Test filter with no results
        response_none = client.get("/api/courses?category=Sports", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(response_none.json()["courses"]) == 0

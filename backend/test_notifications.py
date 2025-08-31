import pytest
from fastapi.testclient import TestClient
from backend.server import app

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "notification_templates", "notification_logs", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client, suffix=""):
    email = f"admin_notify{suffix}@edumanage.com"
    user_data = {"email": email, "password": "AdminPass123!", "full_name": f"Notify Admin{suffix}", "phone": f"90{suffix}", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": email, "password": user_data["password"]})
    return login_response.json()["access_token"]

def create_user(client, admin_token, suffix, branch_id=None):
    email = f"user{suffix}@notify.com"
    user_data = {"email": email, "password": "p", "full_name": f"User {suffix}", "phone": f"91{suffix}", "role": "student"}
    if branch_id:
        user_data["branch_id"] = branch_id
    res = client.post("/api/users", json=user_data, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200, f"Failed to create user {email}"
    return res.json()["user_id"]

def test_notification_template_crud():
    """Test CRUD operations for notification templates."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)

        # 1. Create
        template_data = {"name": "Test Template", "type": "sms", "body": "Hello {{name}}"}
        res_create = client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_create.status_code == 201
        template = res_create.json()
        template_id = template["id"]
        assert template["name"] == "Test Template"

        # 2. Get All
        res_get_all = client.get("/api/notifications/templates", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(res_get_all.json()["templates"]) == 1

        # 3. Update
        update_data = {"name": "Updated Template", "type": "whatsapp", "body": "Hi {{name}}!"}
        res_update = client.put(f"/api/notifications/templates/{template_id}", json=update_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_update.status_code == 200

        # 4. Get One to verify update
        res_get_one = client.get(f"/api/notifications/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_get_one.json()["name"] == "Updated Template"
        assert res_get_one.json()["type"] == "whatsapp"

        # 5. Delete
        res_delete = client.delete(f"/api/notifications/templates/{template_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_delete.status_code == 204

def test_trigger_and_broadcast_notifications():
    """Test triggering a single notification and broadcasting."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_trig")

        # Setup branch, users, and a template
        branch_res = client.post("/api/branches", json={"name":"B_Notify","address":"a","city":"c","state":"s","pincode":"p","email":"b_notify@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]

        user1_id = create_user(client, admin_token, "_u1", branch_id=branch_id)
        user2_id = create_user(client, admin_token, "_u2", branch_id=branch_id)
        user3_id = create_user(client, admin_token, "_u3") # No branch

        template_data = {"name": "Event Alert", "type": "whatsapp", "body": "Event: {{event_name}}"}
        template_id = client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"}).json()["id"]

        # 1. Trigger a single notification
        trigger_data = {"user_id": user1_id, "template_id": template_id, "context": {"event_name": "Annual Day"}}
        res_trigger = client.post("/api/notifications/trigger", json=trigger_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_trigger.status_code == 200

        # 2. Broadcast to a specific branch
        broadcast_data = {"branch_id": branch_id, "template_id": template_id, "context": {"event_name": "Branch Meetup"}}
        res_broadcast = client.post("/api/notifications/broadcast", json=broadcast_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res_broadcast.status_code == 200
        assert "Attempted to notify 2 users" in res_broadcast.json()["message"]

        # 3. Verify notification logs
        import pymongo
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        logs = list(db.notification_logs.find())
        mongo_client.close()

        # 1 trigger + 2 broadcast = 3 logs
        assert len(logs) == 3

        # Check the triggered notification content
        triggered_log = next((log for log in logs if log["user_id"] == user1_id and "Annual Day" in log["content"]), None)
        assert triggered_log is not None

def test_get_notification_logs():
    """Test retrieving and filtering notification logs."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_log_test")

        # Setup: Create a user and a template
        user_id = create_user(client, admin_token, "_log_user")
        template_data = {"name": "Log Test Template", "type": "sms", "body": "Test"}
        template_id = client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"}).json()["id"]

        # Trigger a notification to create a log
        trigger_data = {"user_id": user_id, "template_id": template_id, "context": {}}
        client.post("/api/notifications/trigger", json=trigger_data, headers={"Authorization": f"Bearer {admin_token}"})

        # 1. Get all logs
        res_all = client.get("/api/notifications/logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_all.status_code == 200
        assert res_all.json()["total"] == 1
        assert res_all.json()["logs"][0]["user_id"] == user_id

        # 2. Filter by user_id
        res_filtered = client.get(f"/api/notifications/logs?user_id={user_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_filtered.status_code == 200
        assert res_filtered.json()["total"] == 1

        # 3. Filter by a different user_id (should be empty)
        res_empty = client.get("/api/notifications/logs?user_id=some_other_id", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_empty.status_code == 200
        assert res_empty.json()["total"] == 0

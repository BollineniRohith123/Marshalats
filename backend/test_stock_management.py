import pytest
from fastapi.testclient import TestClient
from backend.server import app

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    collections_to_clean = ["users", "branches", "products", "notification_templates", "notification_logs", "activity_logs"]
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    yield
    for collection_name in collections_to_clean:
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
    mongo_client.close()

def get_admin_token(client, suffix=""):
    email = f"admin_stock{suffix}@edumanage.com"
    user_data = {"email": email, "password": "AdminPass123!", "full_name": f"Stock Admin{suffix}", "phone": f"110{suffix}", "role": "super_admin"}
    client.post("/api/auth/register", json=user_data)
    login_response = client.post("/api/auth/login", json={"email": email, "password": user_data["password"]})
    return login_response.json()["access_token"]

def create_product_with_stock(client, admin_token, branch_id, initial_stock, threshold):
    product_data = {
        "name": "Test Gloves", "description": "d", "category": "c", "price": 100,
        "branch_availability": {branch_id: initial_stock},
        "stock_alert_threshold": threshold
    }
    res = client.post("/api/products", json=product_data, headers={"Authorization": f"Bearer {admin_token}"})
    return res.json()["product_id"]

def test_product_restocking():
    """Test the product restocking endpoint."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client)
        branch_res = client.post("/api/branches", json={"name":"B_Stock","address":"a","city":"c","state":"s","pincode":"p","email":"b_stock@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]
        product_id = create_product_with_stock(client, admin_token, branch_id, 10, 5)

        # Restock the product
        restock_data = {"branch_id": branch_id, "quantity": 15}
        res = client.post(f"/api/products/{product_id}/restock", json=restock_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200

        # Verify the new stock level
        res_product = client.get("/api/products", headers={"Authorization": f"Bearer {admin_token}"})
        product = res_product.json()["products"][0]
        assert product["branch_availability"][branch_id] == 25 # 10 + 15

def test_low_stock_alert():
    """Test that a low stock alert is triggered when stock drops below the threshold."""
    with TestClient(app) as client:
        admin_token = get_admin_token(client, suffix="_alert")

        # Setup: branch, product, template, and a user to make a purchase
        branch_res = client.post("/api/branches", json={"name":"B_Alert","address":"a","city":"c","state":"s","pincode":"p","email":"b_alert@e.com","phone":"ph"}, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_res.json()["branch_id"]

        user_data = {"email":"purchaser@e.com", "password":"p", "full_name":"p", "phone":"111", "role":"student", "branch_id":branch_id}
        user_res = client.post("/api/users", json=user_data, headers={"Authorization":f"Bearer {admin_token}"})
        student_id = user_res.json()["user_id"]

        template_data = {"name": "low_stock_alert", "type": "sms", "body": "Low stock for {{product_name}} at branch {{branch_id}}. Current stock: {{stock_level}}"}
        client.post("/api/notifications/templates", json=template_data, headers={"Authorization": f"Bearer {admin_token}"})

        product_id = create_product_with_stock(client, admin_token, branch_id, initial_stock=12, threshold=10)

        # Make a purchase that brings the stock to 9 (below the threshold of 10)
        purchase_data = {"student_id": student_id, "product_id": product_id, "branch_id": branch_id, "quantity": 3, "payment_method": "cash"}
        res = client.post("/api/products/purchase", json=purchase_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200

        # Verify that a notification log was created for the admin
        import pymongo
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        log = db.notification_logs.find_one({"content": {"$regex": "Low stock"}})
        mongo_client.close()

        assert log is not None
        assert "Current stock: 9" in log["content"]

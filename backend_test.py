import pytest
from fastapi.testclient import TestClient
from backend.server import app, db
import pymongo
from datetime import datetime

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """
    Fixture to clean up the database before and after tests.
    """
    # Clean up before tests
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    db = mongo_client["student_management_db"]
    for collection_name in db.list_collection_names():
        db[collection_name].drop()

    yield

    # Clean up after tests
    for collection_name in db.list_collection_names():
        db[collection_name].drop()
    mongo_client.close()

def get_token(client, role="student", branch_id=None):
    """Helper function to get a token for a given role."""
    test_users = {
        "super_admin": {
            "email": "admin@edumanage.com",
            "password": "AdminPass123!",
            "full_name": "Super Administrator",
            "phone": "+919876543210",
            "role": "super_admin"
        },
        "student": {
            "email": "student@edumanage.com",
            "password": "Student123!",
            "full_name": "Test Student",
            "phone": "+919876543212",
            "role": "student"
        }
    }
    user_data = test_users[role]
    if branch_id:
        user_data["branch_id"] = branch_id

    # Register user
    client.post("/api/auth/register", json=user_data)

    # Login to get token
    login_response = client.post("/api/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })

    return login_response.json()["access_token"]

def test_get_courses_empty():
    """Test GET /courses when there are no courses."""
    with TestClient(app) as client:
        token = get_token(client, "super_admin")
        response = client.get("/api/courses", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json() == {"courses": []}

def test_course_management():
    """Test creating and then getting a course."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")
        
        # Create a course
        course_data = {
            "name": "Karate Beginner Course",
            "description": "Basic karate training for beginners",
            "duration_months": 6,
            "base_fee": 5000.0,
            "branch_pricing": {},
            "schedule": {
                "days": ["monday", "wednesday", "friday"],
                "time": "18:00-19:00"
            }
        }
        create_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert create_response.status_code == 200

        # Get courses
        get_response = client.get("/api/courses", headers={"Authorization": f"Bearer {admin_token}"})
        assert get_response.status_code == 200

        courses = get_response.json()["courses"]
        assert len(courses) == 1
        assert courses[0]["name"] == "Karate Beginner Course"

def test_complaint_submission():
    """Test submitting a complaint."""
    with TestClient(app) as client:
        # First, create a branch
        admin_token = get_token(client, "super_admin")
        branch_data = {
            "name": "Test Branch for Complaints",
            "address": "123 Complaint Street",
            "city": "Testville",
            "state": "TS",
            "pincode": "12345",
            "phone": "+1234567890",
            "email": "complaints@test.com"
        }
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert branch_response.status_code == 200
        branch_id = branch_response.json()["branch_id"]

        # Create a student with that branch_id
        student_token = get_token(client, "student", branch_id=branch_id)
        
        # Submit a complaint
        complaint_data = {
            "subject": "Facility Issue",
            "description": "The training hall needs better ventilation.",
            "category": "facilities",
            "priority": "medium"
        }
        complaint_response = client.post("/api/complaints", json=complaint_data, headers={"Authorization": f"Bearer {student_token}"})
        assert complaint_response.status_code == 200
        assert "complaint_id" in complaint_response.json()

def test_product_management():
    """Test creating, updating, and then getting a product."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")
        
        # Create a product
        product_data = {
            "name": "Karate Uniform",
            "description": "White karate gi with belt",
            "category": "uniform",
            "price": 1500.0
        }
        create_response = client.post("/api/products", json=product_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert create_response.status_code == 200
        product_id = create_response.json()["product_id"]
        
        # Update the product
        update_data = {"price": 1600.0, "description": "High-quality white karate gi with belt"}
        update_response = client.put(f"/api/products/{product_id}", json=update_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert update_response.status_code == 200

        # Get the product again to verify the update
        get_response = client.get("/api/products", headers={"Authorization": f"Bearer {admin_token}"})
        assert get_response.status_code == 200
        
        products = get_response.json()["products"]
        assert len(products) == 1
        assert products[0]["name"] == "Karate Uniform"
        assert products[0]["price"] == 1600.0
        assert products[0]["description"] == "High-quality white karate gi with belt"

def test_student_enrollment():
    """Test enrolling a student in a course."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")

        # Create branch
        branch_data = {"name": "Test Branch", "address": "123 Test St", "city": "Testville", "state": "TS", "pincode": "12345", "phone": "+1234567890", "email": "test@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]

        # Create course
        course_data = {"name": "Test Course", "description": "A test course", "duration_months": 1, "base_fee": 100}
        course_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_response.json()["course_id"]

        # Create student
        student_user_data = {
            "email": "enrollstudent@edumanage.com",
            "password": "Student123!",
            "full_name": "Enroll Student",
            "phone": "+919876543213",
            "role": "student",
            "branch_id": branch_id
        }
        reg_response = client.post("/api/auth/register", json=student_user_data)
        student_id = reg_response.json()["user_id"]

        # Enroll student
        enrollment_data = {
            "student_id": student_id,
            "course_id": course_id,
            "branch_id": branch_id,
            "start_date": datetime.now().isoformat(),
            "fee_amount": 100.0
        }
        enrollment_response = client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert enrollment_response.status_code == 200
        assert "enrollment_id" in enrollment_response.json()

def test_session_booking():
    """Test booking a session."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")

        # Create branch
        branch_data = {"name": "Test Branch", "address": "123 Test St", "city": "Testville", "state": "TS", "pincode": "12345", "phone": "+1234567890", "email": "test@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]

        # Create course
        course_data = {"name": "Test Course", "description": "A test course", "duration_months": 1, "base_fee": 100}
        course_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_response.json()["course_id"]

        # Create student
        student_token = get_token(client, "student", branch_id=branch_id)

        # Create coach
        coach_data = {
            "email": "coach@edumanage.com",
            "password": "Coach123!",
            "full_name": "Test Coach",
            "phone": "+919876543214",
            "role": "coach",
            "branch_id": branch_id
        }
        coach_response = client.post("/api/users", json=coach_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert coach_response.status_code == 200
        coach_id = coach_response.json()["user_id"]

        # Book session
        booking_data = {
            "course_id": course_id,
            "branch_id": branch_id,
            "coach_id": coach_id,
            "session_date": datetime.now().isoformat(),
            "duration_minutes": 60
        }
        booking_response = client.post("/api/sessions/book", json=booking_data, headers={"Authorization": f"Bearer {student_token}"})
        assert booking_response.status_code == 200
        assert "booking_id" in booking_response.json()

def test_payment_processing():
    """Test processing a payment."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")

        # Create branch, course, and student
        branch_data = {"name": "Test Branch", "address": "123 Test St", "city": "Testville", "state": "TS", "pincode": "12345", "phone": "+1234567890", "email": "test@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]
        course_data = {"name": "Test Course", "description": "A test course", "duration_months": 1, "base_fee": 100}
        course_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_response.json()["course_id"]
        student_user_data = {"email": "paymentstudent@edumanage.com", "password": "Student123!", "full_name": "Payment Student", "phone": "+919876543215", "role": "student", "branch_id": branch_id}
        reg_response = client.post("/api/auth/register", json=student_user_data)
        student_id = reg_response.json()["user_id"]
        enrollment_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100.0}
        enrollment_response = client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})
        enrollment_id = enrollment_response.json()["enrollment_id"]

        # Process payment
        payment_data = {
            "student_id": student_id,
            "enrollment_id": enrollment_id,
            "amount": 100.0,
            "payment_type": "course_fee",
            "payment_method": "cash",
            "due_date": datetime.now().isoformat()
        }
        payment_response = client.post("/api/payments", json=payment_data, headers={"Authorization": f"Bearer {admin_token}"})
        assert payment_response.status_code == 200
        assert "payment_id" in payment_response.json()

def test_qr_code_scanning():
    """Test scanning a QR code for attendance."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")

        # Create branch, course, and student
        branch_data = {"name": "Test Branch", "address": "123 Test St", "city": "Testville", "state": "TS", "pincode": "12345", "phone": "+1234567890", "email": "test@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]
        course_data = {"name": "Test Course", "description": "A test course", "duration_months": 1, "base_fee": 100}
        course_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_response.json()["course_id"]
        
        # Create and enroll student
        student_user_data = {"email": "qrstudent@edumanage.com", "password": "Student123!", "full_name": "QR Student", "phone": "+919876543216", "role": "student", "branch_id": branch_id}
        reg_response = client.post("/api/auth/register", json=student_user_data)
        student_id = reg_response.json()["user_id"]
        enrollment_data = {"student_id": student_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100.0}
        client.post("/api/enrollments", json=enrollment_data, headers={"Authorization": f"Bearer {admin_token}"})
        
        # Login as the new student to get their token
        login_response = client.post("/api/auth/login", json={
            "email": student_user_data["email"],
            "password": student_user_data["password"]
        })
        student_token = login_response.json()["access_token"]

        # Generate QR code
        qr_response = client.post(f"/api/attendance/generate-qr?course_id={course_id}&branch_id={branch_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert qr_response.status_code == 200
        qr_code_id = qr_response.json()["qr_code_id"]

        # The qr_code to be scanned is not returned by the generate-qr endpoint in this implementation.
        # The test needs to find it from the database.
        
        # To do this, I need to query the database.
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        db = mongo_client["student_management_db"]
        qr_session = db.qr_sessions.find_one({"id": qr_code_id})
        mongo_client.close()
        
        assert qr_session is not None
        qr_code_to_scan = qr_session["qr_code"]

        # Scan with the correct code
        scan_response = client.post(f"/api/attendance/scan-qr?qr_code={qr_code_to_scan}", headers={"Authorization": f"Bearer {student_token}"})
        assert scan_response.status_code == 200
        assert "attendance_id" in scan_response.json()

def test_view_purchase_history():
    """Test viewing purchase history."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")

        # Create branch, product, and student
        branch_data = {"name": "Test Branch", "address": "123 Test St", "city": "Testville", "state": "TS", "pincode": "12345", "phone": "+1234567890", "email": "test@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]
        product_data = {"name": "Test Product", "description": "A test product", "category": "test", "price": 10.0, "branch_availability": {branch_id: 10}}
        product_response = client.post("/api/products", json=product_data, headers={"Authorization": f"Bearer {admin_token}"})
        product_id = product_response.json()["product_id"]
        student_user_data = {"email": "purchasestudent@edumanage.com", "password": "Student123!", "full_name": "Purchase Student", "phone": "+919876543217", "role": "student", "branch_id": branch_id}
        reg_response = client.post("/api/auth/register", json=student_user_data)
        student_id = reg_response.json()["user_id"]

        # Login as the new student to get their token
        login_response = client.post("/api/auth/login", json={
            "email": student_user_data["email"],
            "password": student_user_data["password"]
        })
        student_token = login_response.json()["access_token"]

        # Record a purchase
        purchase_data = {"student_id": student_id, "product_id": product_id, "branch_id": branch_id, "quantity": 1, "payment_method": "cash"}
        client.post("/api/products/purchase", json=purchase_data, headers={"Authorization": f"Bearer {student_token}"})

        # Get purchase history as student
        student_history_response = client.get("/api/products/purchases", headers={"Authorization": f"Bearer {student_token}"})
        assert student_history_response.status_code == 200
        student_purchases = student_history_response.json()["purchases"]
        assert len(student_purchases) == 1
        assert student_purchases[0]["product_id"] == product_id

        # Get purchase history as admin
        admin_history_response = client.get(f"/api/products/purchases?student_id={student_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_history_response.status_code == 200
        admin_purchases = admin_history_response.json()["purchases"]
        assert len(admin_purchases) == 1
        assert admin_purchases[0]["product_id"] == product_id

def test_password_reset():
    """Test the password reset flow."""
    with TestClient(app) as client:
        # Create a user
        user_email = "resetstudent@edumanage.com"
        user_pass = "Student123!"
        user_data = {
            "email": user_email,
            "password": user_pass,
            "full_name": "Reset Student",
            "phone": "+919876543218",
            "role": "student"
        }
        client.post("/api/auth/register", json=user_data)

        # 1. Forgot Password
        forgot_response = client.post("/api/auth/forgot-password", json={"email": user_email})
        assert forgot_response.status_code == 200
        reset_token = forgot_response.json()["reset_token"]

        # 2. Reset Password
        new_password = "NewPassword123!"
        reset_response = client.post("/api/auth/reset-password", json={"token": reset_token, "new_password": new_password})
        assert reset_response.status_code == 200

        # 3. Login with new password
        login_response = client.post("/api/auth/login", json={"email": user_email, "password": new_password})
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

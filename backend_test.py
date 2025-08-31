import pytest
from fastapi.testclient import TestClient
from backend.server import app, db
import pymongo
from datetime import datetime

@pytest.fixture(scope="function", autouse=True)
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

def test_coach_admin_user_creation():
    """Test user creation by a Coach Admin."""
    with TestClient(app) as client:
        # Setup: Create Super Admin, a branch, and a Coach Admin for that branch
        super_admin_token = get_token(client, "super_admin")
        branch_data = {"name": "Coach Admin Branch", "address": "456 Admin Ave", "city": "Coachville", "state": "CS", "pincode": "67890", "phone": "+16543218765", "email": "coachadmin@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch_id = branch_response.json()["branch_id"]
        
        coach_admin_email = "coachadmin@edumanage.com"
        coach_admin_pass = "CoachAdmin123!"
        coach_admin_data = {"email": coach_admin_email, "password": coach_admin_pass, "full_name": "Branch Coach Admin", "phone": "+919876543220", "role": "coach_admin", "branch_id": branch_id}
        client.post("/api/users", json=coach_admin_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        
        # Login as Coach Admin
        coach_admin_login_response = client.post("/api/auth/login", json={"email": coach_admin_email, "password": coach_admin_pass})
        coach_admin_token = coach_admin_login_response.json()["access_token"]

        # 1. Test: Successfully create a student in the same branch
        student_data = {"email": "studentbycoach@edumanage.com", "password": "NewStudent123!", "full_name": "Student by Coach", "phone": "+919876543221", "role": "student", "branch_id": branch_id}
        success_response = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert success_response.status_code == 200
        assert "user_id" in success_response.json()

        # 2. Test: Fail to create a user in a different branch
        other_branch_data = {"name": "Other Branch", "address": "789 Other St", "city": "Otherville", "state": "OS", "pincode": "54321", "phone": "+19876543210", "email": "other@test.com"}
        other_branch_response = client.post("/api/branches", json=other_branch_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        other_branch_id = other_branch_response.json()["branch_id"]
        
        student_other_branch_data = {"email": "otherbranchstudent@edumanage.com", "password": "NewStudent123!", "full_name": "Other Branch Student", "phone": "+919876543222", "role": "student", "branch_id": other_branch_id}
        fail_branch_response = client.post("/api/users", json=student_other_branch_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert fail_branch_response.status_code == 403

        # 3. Test: Fail to create another admin
        new_admin_data = {"email": "newadminbycoach@edumanage.com", "password": "NewAdmin123!", "full_name": "New Admin by Coach", "phone": "+919876543223", "role": "coach_admin", "branch_id": branch_id}
        fail_admin_response = client.post("/api/users", json=new_admin_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert fail_admin_response.status_code == 403

def test_coach_admin_student_update():
    """Test student profile update by a Coach Admin."""
    with TestClient(app) as client:
        # Setup: Create Super Admin, two branches, a Coach Admin, and two students
        super_admin_token = get_token(client, "super_admin")
        branch1_data = {"name": "Branch One", "address": "1 Admin Ave", "city": "Coachville", "state": "CS", "pincode": "67890", "phone": "+16543218765", "email": "branch1@test.com"}
        branch1_response = client.post("/api/branches", json=branch1_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch1_id = branch1_response.json()["branch_id"]
        
        branch2_data = {"name": "Branch Two", "address": "2 Other St", "city": "Otherville", "state": "OS", "pincode": "54321", "phone": "+19876543210", "email": "branch2@test.com"}
        branch2_response = client.post("/api/branches", json=branch2_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch2_id = branch2_response.json()["branch_id"]

        coach_admin_email = "coachadmin2@edumanage.com"
        coach_admin_pass = "CoachAdmin123!"
        coach_admin_data = {"email": coach_admin_email, "password": coach_admin_pass, "full_name": "Branch Coach Admin 2", "phone": "+919876543230", "role": "coach_admin", "branch_id": branch1_id}
        client.post("/api/users", json=coach_admin_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        
        student1_data = {"email": "student1@edumanage.com", "password": "Student123!", "full_name": "Student One", "phone": "+919876543231", "role": "student", "branch_id": branch1_id}
        student1_response = client.post("/api/users", json=student1_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        student1_id = student1_response.json()["user_id"]
        
        student2_data = {"email": "student2@edumanage.com", "password": "Student123!", "full_name": "Student Two", "phone": "+919876543232", "role": "student", "branch_id": branch2_id}
        student2_response = client.post("/api/users", json=student2_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        student2_id = student2_response.json()["user_id"]

        # Login as Coach Admin
        coach_admin_login_response = client.post("/api/auth/login", json={"email": coach_admin_email, "password": coach_admin_pass})
        coach_admin_token = coach_admin_login_response.json()["access_token"]

        # 1. Test: Successfully update a student in the same branch
        update_data = {"full_name": "Student One Updated"}
        success_response = client.put(f"/api/users/{student1_id}", json=update_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert success_response.status_code == 200

        # 2. Test: Fail to update a student in a different branch
        fail_branch_response = client.put(f"/api/users/{student2_id}", json=update_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert fail_branch_response.status_code == 403

        # 3. Test: Fail to update a super admin's profile
        me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {super_admin_token}"})
        super_admin_id = me_response.json()["id"]
        fail_admin_response = client.put(f"/api/users/{super_admin_id}", json=update_data, headers={"Authorization": f"Bearer {coach_admin_token}"})
        assert fail_admin_response.status_code == 403

def test_financial_report():
    """Test the financial report endpoint."""
    with TestClient(app) as client:
        admin_token = get_token(client, "super_admin")

        # Setup: Create a branch and a course
        branch_data = {"name": "Finance Branch", "address": "123 Finance St", "city": "Financeville", "state": "FS", "pincode": "54321", "phone": "+1234567891", "email": "finance@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]
        course_data = {"name": "Finance Course", "description": "A test course", "duration_months": 1, "base_fee": 1000.0}
        course_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_response.json()["course_id"]

        # Enrollment 1: Student pays course fee, admission fee is pending
        s1_data = {"email": "s1.finance@test.com", "password": "p", "full_name": "s1", "phone": "1", "role": "student", "branch_id": branch_id}
        s1_id = client.post("/api/auth/register", json=s1_data).json()["user_id"]
        e1_data = {"student_id": s1_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 1000.0, "admission_fee": 500.0}
        e1_id = client.post("/api/enrollments", json=e1_data, headers={"Authorization": f"Bearer {admin_token}"}).json()["enrollment_id"]

        payments = client.get(f"/api/payments?enrollment_id={e1_id}", headers={"Authorization": f"Bearer {admin_token}"}).json()["payments"]
        course_fee_payment = next(p for p in payments if p["payment_type"] == "course_fee")
        client.put(f"/api/payments/{course_fee_payment['id']}", json={"payment_status": "paid", "transaction_id": "T1"}, headers={"Authorization": f"Bearer {admin_token}"})

        # Enrollment 2: All fees pending
        s2_data = {"email": "s2.finance@test.com", "password": "p", "full_name": "s2", "phone": "2", "role": "student", "branch_id": branch_id}
        s2_id = client.post("/api/auth/register", json=s2_data).json()["user_id"]
        client.post("/api/enrollments", json={"student_id": s2_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 1000.0, "admission_fee": 500.0}, headers={"Authorization": f"Bearer {admin_token}"})

        # Get financial report
        report_response = client.get("/api/reports/financial", headers={"Authorization": f"Bearer {admin_token}"})
        assert report_response.status_code == 200
        report = report_response.json()

        assert report["total_collected"] == 1000.0
        assert report["outstanding_dues"] == 2000.0

def test_branch_report():
    """Test the branch-specific report endpoint."""
    with TestClient(app) as client:
        # Setup
        super_admin_token = get_token(client, "super_admin")
        branch1_data = {"name": "Reporting Branch 1", "address": "1 Report St", "city": "Reportville", "state": "RS", "pincode": "11122", "phone": "+1112223333", "email": "report1@test.com"}
        b1_res = client.post("/api/branches", json=branch1_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch1_id = b1_res.json()["branch_id"]

        course_data = {"name": "Reporting Course", "description": "A test course", "duration_months": 1, "base_fee": 100}
        c_res = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        course_id = c_res.json()["course_id"]

        s1_data = {"email": "s1.report@test.com", "password": "p", "full_name": "s1", "phone": "1", "role": "student", "branch_id": branch1_id}
        s1_id = client.post("/api/auth/register", json=s1_data).json()["user_id"]
        client.post("/api/enrollments", json={"student_id": s1_id, "course_id": course_id, "branch_id": branch1_id, "start_date": datetime.now().isoformat(), "fee_amount": 100.0}, headers={"Authorization": f"Bearer {super_admin_token}"})

        # 1. Test: Super admin can get the report
        report1_res = client.get(f"/api/reports/branch/{branch1_id}", headers={"Authorization": f"Bearer {super_admin_token}"})
        assert report1_res.status_code == 200
        report1 = report1_res.json()
        assert report1["total_students"] == 1
        assert report1["active_enrollments"] == 1

        # 2. Test: Coach admin for the branch can get the report
        ca1_email = "ca1.report@test.com"
        ca1_pass = "p"
        ca1_data = {"email": ca1_email, "password": ca1_pass, "full_name": "CA1", "phone": "ca1", "role": "coach_admin", "branch_id": branch1_id}
        client.post("/api/users", json=ca1_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        ca1_token = client.post("/api/auth/login", json={"email": ca1_email, "password": ca1_pass}).json()["access_token"]

        ca1_report_res = client.get(f"/api/reports/branch/{branch1_id}", headers={"Authorization": f"Bearer {ca1_token}"})
        assert ca1_report_res.status_code == 200

        # 3. Test: Coach admin for another branch cannot get the report
        branch2_data = {"name": "Reporting Branch 2", "address": "2 Report St", "city": "Reportville", "state": "RS", "pincode": "33344", "phone": "+4445556666", "email": "report2@test.com"}
        b2_res = client.post("/api/branches", json=branch2_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch2_id = b2_res.json()["branch_id"]

        ca2_email = "ca2.report@test.com"
        ca2_pass = "p"
        ca2_data = {"email": ca2_email, "password": ca2_pass, "full_name": "CA2", "phone": "ca2", "role": "coach_admin", "branch_id": branch2_id}
        client.post("/api/users", json=ca2_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        ca2_token = client.post("/api/auth/login", json={"email": ca2_email, "password": ca2_pass}).json()["access_token"]

        ca2_report_res = client.get(f"/api/reports/branch/{branch1_id}", headers={"Authorization": f"Bearer {ca2_token}"})
        assert ca2_report_res.status_code == 403

def test_student_transfer_request():
    """Test the student transfer request flow."""
    with TestClient(app) as client:
        # Setup: Create Super Admin, two branches, and a student in branch 1
        super_admin_token = get_token(client, "super_admin")
        branch1_data = {"name": "Branch One", "address": "1 Transfer Ave", "city": "Transferville", "state": "TS", "pincode": "11111", "phone": "+1111111111", "email": "branch1@transfer.com"}
        branch1_response = client.post("/api/branches", json=branch1_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch1_id = branch1_response.json()["branch_id"]
        
        branch2_data = {"name": "Branch Two", "address": "2 Transfer Ave", "city": "Transferville", "state": "TS", "pincode": "22222", "phone": "+2222222222", "email": "branch2@transfer.com"}
        branch2_response = client.post("/api/branches", json=branch2_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        branch2_id = branch2_response.json()["branch_id"]

        student_email = "transferstudent@edumanage.com"
        student_pass = "Student123!"
        student_data = {"email": student_email, "password": student_pass, "full_name": "Transfer Student", "phone": "+919876543240", "role": "student", "branch_id": branch1_id}
        student_response = client.post("/api/users", json=student_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        student_id = student_response.json()["user_id"]

        # Login as student
        student_login_response = client.post("/api/auth/login", json={"email": student_email, "password": student_pass})
        student_token = student_login_response.json()["access_token"]

        # 1. Student creates a transfer request
        request_data = {"new_branch_id": branch2_id, "reason": "Moving to a new area."}
        create_request_response = client.post("/api/requests/transfer", json=request_data, headers={"Authorization": f"Bearer {student_token}"})
        assert create_request_response.status_code == 201
        request_id = create_request_response.json()["id"]

        # 2. Admin gets the list of pending requests
        get_requests_response = client.get("/api/requests/transfer?status=pending", headers={"Authorization": f"Bearer {super_admin_token}"})
        assert get_requests_response.status_code == 200
        requests = get_requests_response.json()["requests"]
        assert len(requests) == 1
        assert requests[0]["id"] == request_id

        # 3. Admin approves the request
        update_data = {"status": "approved"}
        approve_response = client.put(f"/api/requests/transfer/{request_id}", json=update_data, headers={"Authorization": f"Bearer {super_admin_token}"})
        assert approve_response.status_code == 200

        # 4. Verify the student's branch has been updated
        me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
        updated_student_data = me_response.json()
        assert updated_student_data["branch_id"] == branch2_id

def test_course_stats():
    """Test the course statistics endpoint."""
    with TestClient(app) as client:
        # Setup
        admin_token = get_token(client, "super_admin")
        branch_data = {"name": "Stats Branch", "address": "123 Stats St", "city": "Statsville", "state": "SS", "pincode": "55555", "phone": "+5555555555", "email": "stats@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]

        course_data = {"name": "Stats Course", "description": "A test course", "duration_months": 1, "base_fee": 100}
        course_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_response.json()["course_id"]

        # Enroll two students
        s1_data = {"email": "s1.stats@test.com", "password": "p", "full_name": "s1", "phone": "1", "role": "student", "branch_id": branch_id}
        s1_id = client.post("/api/auth/register", json=s1_data).json()["user_id"]
        client.post("/api/enrollments", json={"student_id": s1_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100.0}, headers={"Authorization": f"Bearer {admin_token}"})

        s2_data = {"email": "s2.stats@test.com", "password": "p", "full_name": "s2", "phone": "2", "role": "student", "branch_id": branch_id}
        s2_id = client.post("/api/auth/register", json=s2_data).json()["user_id"]
        client.post("/api/enrollments", json={"student_id": s2_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100.0}, headers={"Authorization": f"Bearer {admin_token}"})

        # Get course stats
        stats_response = client.get(f"/api/courses/{course_id}/stats", headers={"Authorization": f"Bearer {admin_token}"})
        assert stats_response.status_code == 200
        stats = stats_response.json()

        assert stats["active_enrollments"] == 2

def test_overdue_payment_restriction():
    """Test access restriction for students with overdue payments."""
    with TestClient(app) as client:
        # Setup
        admin_token = get_token(client, "super_admin")
        branch_data = {"name": "Restriction Branch", "address": "123 Restriction St", "city": "Restrictionville", "state": "RS", "pincode": "66666", "phone": "+6666666666", "email": "restriction@test.com"}
        branch_response = client.post("/api/branches", json=branch_data, headers={"Authorization": f"Bearer {admin_token}"})
        branch_id = branch_response.json()["branch_id"]

        course_data = {"name": "Restriction Course", "description": "A test course", "duration_months": 1, "base_fee": 100}
        course_response = client.post("/api/courses", json=course_data, headers={"Authorization": f"Bearer {admin_token}"})
        course_id = course_response.json()["course_id"]

        student_email = "overdue.student@test.com"
        student_pass = "password"
        s1_data = {"email": student_email, "password": student_pass, "full_name": "Overdue Student", "phone": "3", "role": "student", "branch_id": branch_id}
        s1_id = client.post("/api/auth/register", json=s1_data).json()["user_id"]
        e1_data = {"student_id": s1_id, "course_id": course_id, "branch_id": branch_id, "start_date": datetime.now().isoformat(), "fee_amount": 100.0}
        e1_id = client.post("/api/enrollments", json=e1_data, headers={"Authorization": f"Bearer {admin_token}"}).json()["enrollment_id"]

        # Find the pending payment and mark it as overdue
        payments = client.get(f"/api/payments?enrollment_id={e1_id}", headers={"Authorization": f"Bearer {admin_token}"}).json()["payments"]
        payment_to_update = payments[0]
        client.put(f"/api/payments/{payment_to_update['id']}", json={"payment_status": "overdue"}, headers={"Authorization": f"Bearer {admin_token}"})

        # Login as the student
        student_token = client.post("/api/auth/login", json={"email": student_email, "password": student_pass}).json()["access_token"]

        # 1. Test: Access is restricted
        me_response_fail = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
        assert me_response_fail.status_code == 403

        # 2. Test: Pay the overdue bill and regain access
        client.put(f"/api/payments/{payment_to_update['id']}", json={"payment_status": "paid", "transaction_id": "T-OVERDUE"}, headers={"Authorization": f"Bearer {admin_token}"})
        me_response_success = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
        assert me_response_success.status_code == 200

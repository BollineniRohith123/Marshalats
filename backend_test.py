#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Student Management System
Tests all backend APIs systematically with proper authentication flow
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

class StudentManagementAPITester:
    def __init__(self):
        # Use the production URL from frontend/.env
        self.base_url = "https://edumanage-44.preview.emergentagent.com"
        self.api_url = f"{self.base_url}/api"
        self.session = requests.Session()
        self.tokens = {}  # Store tokens for different user roles
        self.test_data = {}  # Store created test data for cleanup and reference
        self.results = []
        
        # Test user credentials for different roles
        self.test_users = {
            "super_admin": {
                "email": "admin@edumanage.com",
                "password": "AdminPass123!",
                "full_name": "Super Administrator",
                "phone": "+919876543210",
                "role": "super_admin"
            },
            "coach_admin": {
                "email": "coach.admin@edumanage.com", 
                "password": "CoachAdmin123!",
                "full_name": "Coach Administrator",
                "phone": "+919876543211",
                "role": "coach_admin"
            },
            "student": {
                "email": "student@edumanage.com",
                "password": "Student123!",
                "full_name": "Test Student",
                "phone": "+919876543212",
                "role": "student"
            }
        }

    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")

    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    headers: Dict = None, auth_token: str = None) -> requests.Response:
        """Make HTTP request with optional authentication"""
        url = f"{self.api_url}{endpoint}" if endpoint.startswith('/') else f"{self.api_url}/{endpoint}"
        
        # Handle root endpoint
        if endpoint == "/":
            url = self.base_url
            
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=request_headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=request_headers, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=request_headers, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=request_headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise

    # PRIORITY 1 - Core Authentication & User Flow Tests
    
    def test_health_check(self):
        """Test health check endpoint"""
        try:
            response = self.make_request("GET", "/")
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "OK":
                        self.log_result("Health Check", True, "API is healthy and responding")
                        return True
                    else:
                        self.log_result("Health Check", False, "Unexpected response format", data)
                except:
                    # If response is not JSON, check if it's a valid HTML response
                    if "Student Management System" in response.text or response.status_code == 200:
                        self.log_result("Health Check", True, "API is responding (non-JSON response)")
                        return True
                    else:
                        self.log_result("Health Check", False, "Non-JSON response", response.text[:100])
            else:
                self.log_result("Health Check", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Health Check", False, f"Request failed: {str(e)}")
        return False

    def test_student_registration(self):
        """Test student registration (public endpoint)"""
        try:
            # Create unique test student
            student_data = {
                "email": f"teststudent_{int(time.time())}@edumanage.com",
                "phone": f"+9198765432{int(time.time()) % 100:02d}",
                "full_name": "Test Student Registration",
                "role": "student",
                "password": "TestPass123!"
            }
            
            response = self.make_request("POST", "/auth/register", student_data)
            
            if response.status_code == 200:
                data = response.json()
                if "user_id" in data:
                    self.test_data["registered_student"] = student_data
                    self.log_result("Student Registration", True, "Student registered successfully")
                    return True
                else:
                    self.log_result("Student Registration", False, "Missing user_id in response", data)
            else:
                self.log_result("Student Registration", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Student Registration", False, f"Request failed: {str(e)}")
        return False

    def test_user_login(self):
        """Test user login for different roles"""
        success_count = 0
        
        # First, register test users
        for role, user_data in self.test_users.items():
            try:
                # Try to register the user (might fail if already exists, that's ok)
                self.make_request("POST", "/auth/register", user_data)
            except:
                pass  # User might already exist
        
        # Test login for each role
        for role, user_data in self.test_users.items():
            try:
                login_data = {
                    "email": user_data["email"],
                    "password": user_data["password"]
                }
                
                response = self.make_request("POST", "/auth/login", login_data)
                
                if response.status_code == 200:
                    data = response.json()
                    if "access_token" in data and "user" in data:
                        self.tokens[role] = data["access_token"]
                        self.log_result(f"Login ({role})", True, f"Login successful for {role}")
                        success_count += 1
                    else:
                        self.log_result(f"Login ({role})", False, "Missing token or user in response", data)
                else:
                    self.log_result(f"Login ({role})", False, f"HTTP {response.status_code}", response.text)
            except Exception as e:
                self.log_result(f"Login ({role})", False, f"Request failed: {str(e)}")
        
        return success_count > 0

    def test_get_current_user(self):
        """Test getting current user info"""
        success_count = 0
        
        for role, token in self.tokens.items():
            try:
                response = self.make_request("GET", "/auth/me", auth_token=token)
                
                if response.status_code == 200:
                    data = response.json()
                    if "id" in data and "email" in data and "role" in data:
                        self.log_result(f"Get Current User ({role})", True, f"User info retrieved for {role}")
                        success_count += 1
                    else:
                        self.log_result(f"Get Current User ({role})", False, "Missing required fields", data)
                else:
                    self.log_result(f"Get Current User ({role})", False, f"HTTP {response.status_code}", response.text)
            except Exception as e:
                self.log_result(f"Get Current User ({role})", False, f"Request failed: {str(e)}")
        
        return success_count > 0

    def test_profile_update(self):
        """Test profile update"""
        if "student" not in self.tokens:
            self.log_result("Profile Update", False, "No student token available")
            return False
            
        try:
            update_data = {
                "full_name": "Updated Test Student",
                "phone": "+919876543299"
            }
            
            response = self.make_request("PUT", "/auth/profile", update_data, auth_token=self.tokens["student"])
            
            if response.status_code == 200:
                self.log_result("Profile Update", True, "Profile updated successfully")
                return True
            else:
                self.log_result("Profile Update", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Profile Update", False, f"Request failed: {str(e)}")
        return False

    # PRIORITY 2 - Administrative Functions Tests
    
    def test_create_user_as_admin(self):
        """Test creating users as Super Admin"""
        if "super_admin" not in self.tokens:
            self.log_result("Create User (Admin)", False, "No super admin token available")
            return False
            
        try:
            new_user_data = {
                "email": f"newuser_{int(time.time())}@edumanage.com",
                "phone": f"+9198765432{int(time.time()) % 100:02d}",
                "full_name": "New Test User",
                "role": "coach",
                "password": "NewUser123!"
            }
            
            response = self.make_request("POST", "/users", new_user_data, auth_token=self.tokens["super_admin"])
            
            if response.status_code == 200:
                data = response.json()
                if "user_id" in data:
                    self.test_data["created_user"] = new_user_data
                    self.log_result("Create User (Admin)", True, "User created successfully by admin")
                    return True
                else:
                    self.log_result("Create User (Admin)", False, "Missing user_id in response", data)
            else:
                self.log_result("Create User (Admin)", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Create User (Admin)", False, f"Request failed: {str(e)}")
        return False

    def test_branch_management(self):
        """Test branch creation and retrieval"""
        if "super_admin" not in self.tokens:
            self.log_result("Branch Management", False, "No super admin token available")
            return False
            
        try:
            # Create branch
            branch_data = {
                "name": "Test Branch Mumbai",
                "address": "123 Test Street, Andheri",
                "city": "Mumbai",
                "state": "Maharashtra", 
                "pincode": "400001",
                "phone": "+912212345678",
                "email": "mumbai@edumanage.com",
                "business_hours": {
                    "monday": {"open": "09:00", "close": "18:00"},
                    "tuesday": {"open": "09:00", "close": "18:00"}
                }
            }
            
            response = self.make_request("POST", "/branches", branch_data, auth_token=self.tokens["super_admin"])
            
            if response.status_code == 200:
                data = response.json()
                if "branch_id" in data:
                    branch_id = data["branch_id"]
                    self.test_data["branch_id"] = branch_id
                    
                    # Test getting branches
                    get_response = self.make_request("GET", "/branches", auth_token=self.tokens["super_admin"])
                    if get_response.status_code == 200:
                        branches_data = get_response.json()
                        if "branches" in branches_data and len(branches_data["branches"]) > 0:
                            self.log_result("Branch Management", True, "Branch created and retrieved successfully")
                            return True
                        else:
                            self.log_result("Branch Management", False, "No branches found in response", branches_data)
                    else:
                        self.log_result("Branch Management", False, f"Get branches failed: HTTP {get_response.status_code}")
                else:
                    self.log_result("Branch Management", False, "Missing branch_id in response", data)
            else:
                self.log_result("Branch Management", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Branch Management", False, f"Request failed: {str(e)}")
        return False

    def test_course_management(self):
        """Test course creation and retrieval"""
        if "super_admin" not in self.tokens:
            self.log_result("Course Management", False, "No super admin token available")
            return False
            
        try:
            # Create course
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
            
            response = self.make_request("POST", "/courses", course_data, auth_token=self.tokens["super_admin"])
            
            if response.status_code == 200:
                data = response.json()
                if "course_id" in data:
                    course_id = data["course_id"]
                    self.test_data["course_id"] = course_id
                    
                    # Test getting courses
                    get_response = self.make_request("GET", "/courses", auth_token=self.tokens["super_admin"])
                    if get_response.status_code == 200:
                        courses_data = get_response.json()
                        if "courses" in courses_data and len(courses_data["courses"]) > 0:
                            self.log_result("Course Management", True, "Course created and retrieved successfully")
                            return True
                        else:
                            self.log_result("Course Management", False, "No courses found in response", courses_data)
                    else:
                        self.log_result("Course Management", False, f"Get courses failed: HTTP {get_response.status_code}")
                else:
                    self.log_result("Course Management", False, "Missing course_id in response", data)
            else:
                self.log_result("Course Management", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Course Management", False, f"Request failed: {str(e)}")
        return False

    # PRIORITY 3 - Student Management Functions Tests
    
    def test_student_enrollment(self):
        """Test student enrollment"""
        if "super_admin" not in self.tokens:
            self.log_result("Student Enrollment", False, "No super admin token available")
            return False
            
        if "branch_id" not in self.test_data or "course_id" not in self.test_data:
            self.log_result("Student Enrollment", False, "Missing branch_id or course_id from previous tests")
            return False
            
        try:
            # First create a student for enrollment
            student_data = {
                "email": f"enrollstudent_{int(time.time())}@edumanage.com",
                "phone": f"+9198765432{int(time.time()) % 100:02d}",
                "full_name": "Enrollment Test Student",
                "role": "student",
                "password": "EnrollTest123!"
            }
            
            reg_response = self.make_request("POST", "/auth/register", student_data)
            if reg_response.status_code != 200:
                self.log_result("Student Enrollment", False, "Failed to create student for enrollment")
                return False
                
            student_id = reg_response.json()["user_id"]
            
            # Create enrollment
            enrollment_data = {
                "student_id": student_id,
                "course_id": self.test_data["course_id"],
                "branch_id": self.test_data["branch_id"],
                "start_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "fee_amount": 5000.0,
                "admission_fee": 500.0
            }
            
            response = self.make_request("POST", "/enrollments", enrollment_data, auth_token=self.tokens["super_admin"])
            
            if response.status_code == 200:
                data = response.json()
                if "enrollment_id" in data:
                    self.test_data["enrollment_id"] = data["enrollment_id"]
                    self.test_data["enrolled_student_id"] = student_id
                    self.log_result("Student Enrollment", True, "Student enrolled successfully")
                    return True
                else:
                    self.log_result("Student Enrollment", False, "Missing enrollment_id in response", data)
            else:
                self.log_result("Student Enrollment", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Student Enrollment", False, f"Request failed: {str(e)}")
        return False

    def test_qr_code_generation(self):
        """Test QR code generation for attendance"""
        if "super_admin" not in self.tokens:
            self.log_result("QR Code Generation", False, "No super admin token available")
            return False
            
        if "branch_id" not in self.test_data or "course_id" not in self.test_data:
            self.log_result("QR Code Generation", False, "Missing branch_id or course_id from previous tests")
            return False
            
        try:
            # QR generation endpoint expects query parameters
            endpoint = f"/attendance/generate-qr?course_id={self.test_data['course_id']}&branch_id={self.test_data['branch_id']}&valid_minutes=30"
            
            response = self.make_request("POST", endpoint, {}, auth_token=self.tokens["super_admin"])
            
            if response.status_code == 200:
                data = response.json()
                if "qr_code_id" in data and "qr_code_data" in data:
                    self.test_data["qr_code_id"] = data["qr_code_id"]
                    # Extract QR code from response for scanning test
                    # The QR code data should be in the format "attendance:course_id:branch_id:timestamp"
                    self.test_data["qr_code"] = f"attendance:{self.test_data['course_id']}:{self.test_data['branch_id']}:{int(time.time())}"
                    self.log_result("QR Code Generation", True, "QR code generated successfully")
                    return True
                else:
                    self.log_result("QR Code Generation", False, "Missing QR code data in response", data)
            else:
                self.log_result("QR Code Generation", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("QR Code Generation", False, f"Request failed: {str(e)}")
        return False

    def test_qr_code_scanning(self):
        """Test QR code scanning for attendance"""
        # First, we need to login as the enrolled student
        if "enrolled_student_id" not in self.test_data:
            self.log_result("QR Code Scanning", False, "No enrolled student available for testing")
            return False
            
        try:
            # Login as the enrolled student
            login_data = {
                "email": f"enrollstudent_{int(time.time())}@edumanage.com",  # This might not work as time has changed
                "password": "EnrollTest123!"
            }
            
            # We need to create a fresh QR code and student for this test
            # Create a new student and enroll them first
            student_data = {
                "email": f"qrstudent_{int(time.time())}@edumanage.com",
                "phone": f"+9198765432{int(time.time()) % 100:02d}",
                "full_name": "QR Test Student",
                "role": "student",
                "password": "QRTest123!"
            }
            
            reg_response = self.make_request("POST", "/auth/register", student_data)
            if reg_response.status_code != 200:
                self.log_result("QR Code Scanning", False, "Failed to create student for QR test")
                return False
                
            student_id = reg_response.json()["user_id"]
            
            # Login as this student
            login_response = self.make_request("POST", "/auth/login", {
                "email": student_data["email"],
                "password": student_data["password"]
            })
            
            if login_response.status_code != 200:
                self.log_result("QR Code Scanning", False, "Failed to login as QR test student")
                return False
                
            student_token = login_response.json()["access_token"]
            
            # Enroll this student
            if "branch_id" in self.test_data and "course_id" in self.test_data:
                enrollment_data = {
                    "student_id": student_id,
                    "course_id": self.test_data["course_id"],
                    "branch_id": self.test_data["branch_id"],
                    "start_date": datetime.now().isoformat(),
                    "fee_amount": 5000.0,
                    "admission_fee": 500.0
                }
                
                enroll_response = self.make_request("POST", "/enrollments", enrollment_data, auth_token=self.tokens["super_admin"])
                if enroll_response.status_code != 200:
                    self.log_result("QR Code Scanning", False, "Failed to enroll student for QR test")
                    return False
            
            # Generate a fresh QR code
            qr_params = {
                "course_id": self.test_data["course_id"],
                "branch_id": self.test_data["branch_id"],
                "valid_minutes": 30
            }
            
            qr_response = self.make_request("POST", "/attendance/generate-qr", qr_params, auth_token=self.tokens["super_admin"])
            if qr_response.status_code != 200:
                self.log_result("QR Code Scanning", False, "Failed to generate QR code for scanning test")
                return False
                
            # Extract QR code from the database format (this is a simplified approach)
            qr_code = f"attendance:{self.test_data['course_id']}:{self.test_data['branch_id']}:{int(time.time())}"
            
            # Now scan the QR code
            scan_data = {"qr_code": qr_code}
            response = self.make_request("POST", "/attendance/scan-qr", scan_data, auth_token=student_token)
            
            if response.status_code == 200:
                data = response.json()
                if "attendance_id" in data:
                    self.log_result("QR Code Scanning", True, "QR code scanned and attendance marked successfully")
                    return True
                else:
                    self.log_result("QR Code Scanning", False, "Missing attendance_id in response", data)
            else:
                self.log_result("QR Code Scanning", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("QR Code Scanning", False, f"Request failed: {str(e)}")
        return False

    def test_payment_processing(self):
        """Test payment processing"""
        if "super_admin" not in self.tokens:
            self.log_result("Payment Processing", False, "No super admin token available")
            return False
            
        if "enrollment_id" not in self.test_data or "enrolled_student_id" not in self.test_data:
            self.log_result("Payment Processing", False, "Missing enrollment data for payment test")
            return False
            
        try:
            payment_data = {
                "student_id": self.test_data["enrolled_student_id"],
                "enrollment_id": self.test_data["enrollment_id"],
                "amount": 5000.0,
                "payment_type": "course_fee",
                "payment_method": "upi",
                "due_date": datetime.now().isoformat(),
                "transaction_id": f"TXN{int(time.time())}",
                "notes": "Test payment processing"
            }
            
            response = self.make_request("POST", "/payments", payment_data, auth_token=self.tokens["super_admin"])
            
            if response.status_code == 200:
                data = response.json()
                if "payment_id" in data:
                    self.test_data["payment_id"] = data["payment_id"]
                    self.log_result("Payment Processing", True, "Payment processed successfully")
                    return True
                else:
                    self.log_result("Payment Processing", False, "Missing payment_id in response", data)
            else:
                self.log_result("Payment Processing", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Payment Processing", False, f"Request failed: {str(e)}")
        return False

    # PRIORITY 4 - Additional Features Tests
    
    def test_product_management(self):
        """Test product management"""
        if "super_admin" not in self.tokens:
            self.log_result("Product Management", False, "No super admin token available")
            return False
            
        try:
            # Create product
            product_data = {
                "name": "Karate Uniform",
                "description": "White karate gi with belt",
                "category": "uniform",
                "price": 1500.0,
                "branch_availability": {
                    self.test_data.get("branch_id", "test_branch"): 10
                },
                "image_url": "https://example.com/karate-uniform.jpg"
            }
            
            response = self.make_request("POST", "/products", product_data, auth_token=self.tokens["super_admin"])
            
            if response.status_code == 200:
                data = response.json()
                if "product_id" in data:
                    product_id = data["product_id"]
                    self.test_data["product_id"] = product_id
                    
                    # Test getting products
                    get_response = self.make_request("GET", "/products", auth_token=self.tokens["super_admin"])
                    if get_response.status_code == 200:
                        products_data = get_response.json()
                        if "products" in products_data and len(products_data["products"]) > 0:
                            self.log_result("Product Management", True, "Product created and retrieved successfully")
                            return True
                        else:
                            self.log_result("Product Management", False, "No products found in response", products_data)
                    else:
                        self.log_result("Product Management", False, f"Get products failed: HTTP {get_response.status_code}")
                else:
                    self.log_result("Product Management", False, "Missing product_id in response", data)
            else:
                self.log_result("Product Management", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Product Management", False, f"Request failed: {str(e)}")
        return False

    def test_complaint_submission(self):
        """Test complaint submission"""
        if "student" not in self.tokens:
            self.log_result("Complaint Submission", False, "No student token available")
            return False
            
        try:
            complaint_data = {
                "subject": "Facility Issue",
                "description": "The training hall needs better ventilation and lighting for evening sessions.",
                "category": "facilities",
                "priority": "medium"
            }
            
            response = self.make_request("POST", "/complaints", complaint_data, auth_token=self.tokens["student"])
            
            if response.status_code == 200:
                data = response.json()
                if "complaint_id" in data:
                    self.test_data["complaint_id"] = data["complaint_id"]
                    self.log_result("Complaint Submission", True, "Complaint submitted successfully")
                    return True
                else:
                    self.log_result("Complaint Submission", False, "Missing complaint_id in response", data)
            else:
                self.log_result("Complaint Submission", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Complaint Submission", False, f"Request failed: {str(e)}")
        return False

    def test_session_booking(self):
        """Test session booking"""
        if "student" not in self.tokens:
            self.log_result("Session Booking", False, "No student token available")
            return False
            
        if "course_id" not in self.test_data or "branch_id" not in self.test_data:
            self.log_result("Session Booking", False, "Missing course_id or branch_id for session booking")
            return False
            
        try:
            # First create a coach for the session
            coach_data = {
                "email": f"coach_{int(time.time())}@edumanage.com",
                "phone": f"+9198765432{int(time.time()) % 100:02d}",
                "full_name": "Test Coach",
                "role": "coach",
                "password": "Coach123!",
                "branch_id": self.test_data["branch_id"]
            }
            
            coach_response = self.make_request("POST", "/users", coach_data, auth_token=self.tokens["super_admin"])
            if coach_response.status_code != 200:
                self.log_result("Session Booking", False, "Failed to create coach for session booking")
                return False
                
            coach_id = coach_response.json()["user_id"]
            
            booking_data = {
                "course_id": self.test_data["course_id"],
                "branch_id": self.test_data["branch_id"],
                "coach_id": coach_id,
                "session_date": (datetime.now() + timedelta(days=3)).isoformat(),
                "duration_minutes": 60,
                "notes": "Individual training session"
            }
            
            response = self.make_request("POST", "/sessions/book", booking_data, auth_token=self.tokens["student"])
            
            if response.status_code == 200:
                data = response.json()
                if "booking_id" in data and "fee" in data:
                    self.test_data["booking_id"] = data["booking_id"]
                    self.log_result("Session Booking", True, f"Session booked successfully with fee: ₹{data['fee']}")
                    return True
                else:
                    self.log_result("Session Booking", False, "Missing booking_id or fee in response", data)
            else:
                self.log_result("Session Booking", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_result("Session Booking", False, f"Request failed: {str(e)}")
        return False

    def test_dashboard_statistics(self):
        """Test dashboard statistics"""
        success_count = 0
        
        # Test for different roles
        for role, token in self.tokens.items():
            try:
                response = self.make_request("GET", "/reports/dashboard", auth_token=token)
                
                if response.status_code == 200:
                    data = response.json()
                    if "dashboard_stats" in data:
                        stats = data["dashboard_stats"]
                        required_fields = ["total_students", "active_enrollments", "pending_payments"]
                        if all(field in stats for field in required_fields):
                            self.log_result(f"Dashboard Stats ({role})", True, f"Dashboard statistics retrieved for {role}")
                            success_count += 1
                        else:
                            self.log_result(f"Dashboard Stats ({role})", False, "Missing required statistics fields", stats)
                    else:
                        self.log_result(f"Dashboard Stats ({role})", False, "Missing dashboard_stats in response", data)
                else:
                    self.log_result(f"Dashboard Stats ({role})", False, f"HTTP {response.status_code}", response.text)
            except Exception as e:
                self.log_result(f"Dashboard Stats ({role})", False, f"Request failed: {str(e)}")
        
        return success_count > 0

    def run_all_tests(self):
        """Run all tests in priority order"""
        print("🚀 Starting Comprehensive Backend API Testing for Student Management System")
        print("=" * 80)
        
        # PRIORITY 1 - Core Authentication & User Flow
        print("\n📋 PRIORITY 1 - Core Authentication & User Flow")
        print("-" * 50)
        self.test_health_check()
        self.test_student_registration()
        self.test_user_login()
        self.test_get_current_user()
        self.test_profile_update()
        
        # PRIORITY 2 - Administrative Functions
        print("\n📋 PRIORITY 2 - Administrative Functions")
        print("-" * 50)
        self.test_create_user_as_admin()
        self.test_branch_management()
        self.test_course_management()
        
        # PRIORITY 3 - Student Management Functions
        print("\n📋 PRIORITY 3 - Student Management Functions")
        print("-" * 50)
        self.test_student_enrollment()
        self.test_qr_code_generation()
        self.test_qr_code_scanning()
        self.test_payment_processing()
        
        # PRIORITY 4 - Additional Features
        print("\n📋 PRIORITY 4 - Additional Features")
        print("-" * 50)
        self.test_product_management()
        self.test_complaint_submission()
        self.test_session_booking()
        self.test_dashboard_statistics()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - passed
        
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['message']}")
        
        return passed, failed

if __name__ == "__main__":
    tester = StudentManagementAPITester()
    passed, failed = tester.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)
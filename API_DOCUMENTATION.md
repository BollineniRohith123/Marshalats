# Student Management System API Documentation

## Overview
This is a comprehensive Student Management System API built with FastAPI, supporting role-based access for Super Admin, Staff (Coach Admin), Coaches, and Students.

## Base URL
```
Production: https://edumanage-44.preview.dev.com/api
Development: http://localhost:8001/api
```

## Authentication
The API uses JWT (JSON Web Token) for authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## User Roles
- **Super Admin**: Full system access, manages branches, courses, users
- **Coach Admin**: Branch-level management, student enrollment, course scheduling
- **Coach**: Limited access to assigned courses and students
- **Student**: Personal profile, course enrollment, attendance, payments

---

# API Endpoints

## 1. Authentication & User Management

### POST /api/auth/register
**Description**: Register a new student (public endpoint). Upon successful registration, an SMS containing login credentials will be sent to the registered phone number.
**Access**: Public
**Request Body**:
```json
{
  "email": "student@example.com",
  "phone": "+1234567890",
  "full_name": "John Doe",
  "role": "student",
  "branch_id": "branch-uuid",
  "password": "optional-password"
}
```
**Response**:
```json
{
  "message": "User registered successfully",
  "user_id": "user-uuid"
}
```

### POST /api/auth/login
**Description**: User login
**Access**: Public
**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response**:
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "role": "student",
    "full_name": "John Doe"
  }
}
```

### GET /api/auth/me
**Description**: Get current user information
**Access**: Authenticated users
**Response**:
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "phone": "+1234567890",
  "full_name": "John Doe",
  "role": "student",
  "branch_id": "branch-uuid",
  "biometric_id": "fingerprint_123",
  "is_active": true,
  "created_at": "2025-01-07T12:00:00Z"
}
```

### PUT /api/auth/profile
**Description**: Update user profile
**Access**: Authenticated users
**Request Body**:
```json
{
  "email": "newemail@example.com",
  "phone": "+0987654321",
  "full_name": "Jane Doe",
  "biometric_id": "fingerprint_456"
}
```

### POST /api/auth/forgot-password
**Description**: Initiate password reset. If an account with the provided email exists, a password reset token will be sent via SMS.
**Access**: Public
**Request Body**:
```json
{
  "email": "user@example.com"
}
```
**Response**:
```json
{
  "message": "If an account with that email exists, a password reset link has been sent."
}
```

### POST /api/auth/reset-password
**Description**: Reset password with a valid token
**Access**: Public
**Request Body**:
```json
{
  "token": "your_reset_token_here",
  "new_password": "YourNewPassword123!"
}
```
**Response**:
```json
{
  "message": "Password has been reset successfully."
}
```

---

## 2. User Management

### POST /api/users
**Description**: Create new user. Coach Admins can only create users for their own branch and cannot create other admin users (Super Admin or Coach Admin roles).
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "email": "newuser@example.com",
  "phone": "+1234567890",
  "full_name": "New User",
  "role": "coach_admin",
  "branch_id": "branch-uuid"
}
```
**Response**:
```json
{
  "message": "User created successfully",
  "user_id": "user-uuid"
}
```

### GET /api/users
**Description**: Get users with filtering
**Access**: Super Admin, Coach Admin
**Query Parameters**:
- `role`: Filter by user role
- `branch_id`: Filter by branch
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 50)

**Response**:
```json
{
  "users": [
    {
      "id": "user-uuid",
      "email": "user@example.com",
      "full_name": "User Name",
      "role": "student",
      "is_active": true
    }
  ],
  "total": 1
}
```

### PUT /api/users/{user_id}
**Description**: Update user. Coach Admins can only update students in their own branch.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "email": "newemail@example.com",
  "phone": "+0987654321",
  "full_name": "Jane Doe",
  "biometric_id": "fingerprint_456",
  "is_active": true
}
```
**Response**:
```json
{
  "message": "User updated successfully"
}
```

### DELETE /api/users/{user_id}
**Description**: Deactivate user
**Access**: Super Admin
**Response**:
```json
{
  "message": "User deactivated successfully"
}
```

### POST /api/users/{user_id}/force-password-reset
**Description**: Force a password reset for a user. A new temporary password will be generated and sent to the user via SMS and WhatsApp.
**Access**: Super Admin, Coach Admin
**Details**:
- Super Admins can reset the password for any user.
- Coach Admins can only reset passwords for Students and Coaches within their own branch.
**Response**:
```json
{
  "message": "Password for user [User's Full Name] has been reset and sent to them."
}
```

---

## 3. Branch Management

### POST /api/branches
**Description**: Create new branch
**Access**: Super Admin
**Request Body**:
```json
{
  "name": "Downtown Branch",
  "address": "123 Main St",
  "city": "Springfield",
  "state": "IL",
  "pincode": "62701",
  "phone": "+1234567890",
  "email": "downtown@example.com",
  "manager_id": "manager-uuid",
  "business_hours": {
    "monday": {"open": "09:00", "close": "18:00"},
    "tuesday": {"open": "09:00", "close": "18:00"}
  }
}
```
**Response**:
```json
{
  "message": "Branch created successfully",
  "branch_id": "branch-uuid"
}
```

### GET /api/branches
**Description**: Get all branches
**Access**: All authenticated users
**Query Parameters**:
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 50)
**Response**:
```json
{
  "branches": [
    {
      "id": "branch-uuid",
      "name": "Downtown Branch",
      "address": "123 Main St",
      "city": "Springfield",
      "state": "IL",
      "pincode": "62701",
      "phone": "+1234567890",
      "email": "downtown@example.com",
      "manager_id": "manager-uuid",
      "is_active": true,
      "business_hours": {},
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### GET /api/branches/{branch_id}
**Description**: Get branch by ID
**Access**: All authenticated users
**Response**:
```json
{
  "id": "branch-uuid",
  "name": "Downtown Branch",
  "address": "123 Main St",
  "city": "Springfield",
  "state": "IL",
  "pincode": "62701",
  "phone": "+1234567890",
  "email": "downtown@example.com",
  "manager_id": "manager-uuid",
  "is_active": true,
  "business_hours": {},
  "created_at": "2025-01-07T12:00:00Z",
  "updated_at": "2025-01-07T12:00:00Z"
}
```

### PUT /api/branches/{branch_id}
**Description**: Update branch.
**Access**: Super Admin, Coach Admin (own branch only)
**Details**: Coach Admins can only update certain fields (e.g., name, address, phone) and cannot update the manager or active status.
**Request Body**:
```json
{
  "name": "Updated Branch Name",
  "address": "456 New St",
  "phone": "+0987654321"
}
```
**Response**:
```json
{
  "message": "Branch updated successfully"
}
```

### POST /api/branches/{branch_id}/holidays
**Description**: Create a new holiday for a branch.
**Access**: Super Admin, Coach Admin (own branch only)
**Request Body**:
```json
{
  "date": "2025-12-25",
  "description": "Christmas Day"
}
```
**Response**:
```json
{
  "id": "holiday-uuid",
  "branch_id": "branch-uuid",
  "date": "2025-12-25",
  "description": "Christmas Day",
  "created_at": "2025-01-07T12:00:00Z"
}
```

### GET /api/branches/{branch_id}/holidays
**Description**: Get all holidays for a specific branch.
**Access**: All authenticated users
**Response**:
```json
{
  "holidays": [
    {
      "id": "holiday-uuid",
      "branch_id": "branch-uuid",
      "date": "2025-12-25",
      "description": "Christmas Day",
      "created_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### DELETE /api/branches/{branch_id}/holidays/{holiday_id}
**Description**: Delete a holiday for a branch.
**Access**: Super Admin, Coach Admin (own branch only)
**Response**: (No content) `204 No Content`

---

## 4. Course Management

### POST /api/courses
**Description**: Create new course
**Access**: Super Admin
**Request Body**:
```json
{
  "name": "Martial Arts Basics",
  "description": "Introduction to martial arts",
  "category": "Martial Arts",
  "level": "Beginner",
  "duration_months": 6,
  "base_fee": 1000.0,
  "branch_pricing": {
    "branch-uuid-1": 1200.0,
    "branch-uuid-2": 1100.0
  },
  "coach_id": "coach-uuid",
  "schedule": {
    "days": ["monday", "wednesday", "friday"],
    "time": "18:00-19:00"
  }
}
```
**Response**:
```json
{
  "message": "Course created successfully",
  "course_id": "course-uuid"
}
```

### GET /api/courses
**Description**: Get courses
**Access**: All authenticated users
**Query Parameters**:
- `branch_id`: Filter by branch (only courses available at this branch)
- `category`: Filter by course category (e.g., `Martial Arts`)
- `level`: Filter by course level (e.g., `Beginner`)
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 50)
**Response**:
```json
{
  "courses": [
    {
      "id": "course-uuid",
      "name": "Martial Arts Basics",
      "description": "Introduction to martial arts",
      "category": "Martial Arts",
      "level": "Beginner",
      "duration_months": 6,
      "base_fee": 1000.0,
      "branch_pricing": {},
      "coach_id": "coach-uuid",
      "schedule": {},
      "is_active": true,
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### PUT /api/courses/{course_id}
**Description**: Update course
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "name": "Advanced Martial Arts",
  "base_fee": 1500.0
}
```
**Response**:
```json
{
  "message": "Course updated successfully"
}
```

### GET /api/courses/{course_id}/stats
**Description**: Get statistics for a specific course.
**Access**: Super Admin, Coach Admin
**Response**:
```json
{
  "course_details": {
    "id": "course-uuid",
    "name": "Martial Arts Basics",
    "description": "Introduction to martial arts",
    "category": "Martial Arts",
    "level": "Beginner",
    "duration_months": 6,
    "base_fee": 1000.0,
    "branch_pricing": {},
    "coach_id": "coach-uuid",
    "schedule": {},
    "is_active": true,
    "created_at": "2025-01-07T12:00:00Z",
    "updated_at": "2025-01-07T12:00:00Z"
  },
  "active_enrollments": 120
}
```

---

## 5. Student Enrollment & Management

### POST /api/enrollments
**Description**: Create student enrollment. This will also create initial pending payment records (admission fee and course fee) and send a WhatsApp confirmation to the student.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "student_id": "student-uuid",
  "course_id": "course-uuid",
  "branch_id": "branch-uuid",
  "start_date": "2025-02-01T00:00:00Z",
  "fee_amount": 1200.0,
  "admission_fee": 500.0
}
```
**Response**:
```json
{
  "message": "Enrollment created successfully",
  "enrollment_id": "enrollment-uuid"
}
```

### GET /api/enrollments
**Description**: Get enrollments with filtering
**Access**: Based on role (Super Admin, Coach Admin can see all/their branch's enrollments; Student can only see their own)
**Query Parameters**:
- `student_id`: Filter by student
- `course_id`: Filter by course
- `branch_id`: Filter by branch
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 50)
**Response**:
```json
{
  "enrollments": [
    {
      "id": "enrollment-uuid",
      "student_id": "student-uuid",
      "course_id": "course-uuid",
      "branch_id": "branch-uuid",
      "enrollment_date": "2025-01-07T12:00:00Z",
      "start_date": "2025-02-01T00:00:00Z",
      "end_date": "2025-08-01T00:00:00Z",
      "fee_amount": 1200.0,
      "admission_fee": 500.0,
      "payment_status": "pending",
      "next_due_date": "2025-03-01T00:00:00Z",
      "is_active": true,
      "created_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### GET /api/students/{student_id}/courses
**Description**: Get student's enrolled courses
**Access**: Student (own data), Admins
**Response**:
```json
{
  "enrolled_courses": [
    {
      "enrollment": {
        "id": "enrollment-uuid",
        "student_id": "student-uuid",
        "course_id": "course-uuid",
        "branch_id": "branch-uuid",
        "enrollment_date": "2025-01-07T12:00:00Z",
        "start_date": "2025-02-01T00:00:00Z",
        "end_date": "2025-08-01T00:00:00Z",
        "fee_amount": 1200.0,
        "admission_fee": 500.0,
        "payment_status": "pending",
        "next_due_date": "2025-03-01T00:00:00Z",
        "is_active": true,
        "created_at": "2025-01-07T12:00:00Z"
      },
      "course": {
        "id": "course-uuid",
        "name": "Martial Arts Basics",
        "description": "Introduction to martial arts",
        "category": "Martial Arts",
        "level": "Beginner",
        "duration_months": 6,
        "base_fee": 1000.0,
        "branch_pricing": {},
        "coach_id": "coach-uuid",
        "schedule": {},
        "is_active": true,
        "created_at": "2025-01-07T12:00:00Z",
        "updated_at": "2025-01-07T12:00:00Z"
      }
    }
  ]
}
```

### POST /api/students/enroll
**Description**: Allow a student to enroll themselves in a course. This will also create initial pending payment records (admission fee and course fee) and send a WhatsApp confirmation to the student.
**Access**: Student
**Request Body**:
```json
{
  "course_id": "course-uuid",
  "branch_id": "branch-uuid",
  "start_date": "2025-02-01T00:00:00Z"
}
```
**Response**:
```json
{
  "message": "Enrollment created successfully",
  "enrollment_id": "enrollment-uuid"
}
```

---

## 6. Attendance System

### POST /api/attendance/generate-qr
**Description**: Generate QR code for attendance
**Access**: Super Admin, Coach Admin, Coach
**Request Body**:
```json
{
  "course_id": "course-uuid",
  "branch_id": "branch-uuid",
  "valid_minutes": 30
}
```
**Response**:
```json
{
  "qr_code_id": "qr-session-uuid",
  "qr_code_data": "base64_encoded_qr_image",
  "valid_until": "2025-01-07T12:30:00Z",
  "course_name": "Martial Arts Basics"
}
```

### POST /api/attendance/scan-qr
**Description**: Mark attendance via QR code scan
**Access**: Students
**Request Body**:
```json
{
  "qr_code": "attendance:course-id:branch-id:timestamp"
}
```
**Response**:
```json
{
  "message": "Attendance marked successfully",
  "attendance_id": "attendance-uuid"
}
```

### POST /api/attendance/biometric
**Description**: Record attendance from a (mock) biometric device. This endpoint would typically be called by the hardware.
**Access**: Public (in a real scenario, this would likely be secured with an API key)
**Request Body**:
```json
{
  "device_id": "Device001",
  "biometric_id": "fingerprint_123",
  "timestamp": "2025-01-08T09:05:00Z"
}
```
**Response**:
```json
{
  "message": "Attendance marked successfully",
  "attendance_id": "attendance-uuid"
}
```

### POST /api/attendance/manual
**Description**: Manually mark attendance
**Access**: Super Admin, Coach Admin, Coach
**Request Body**:
```json
{
  "student_id": "student-uuid",
  "course_id": "course-uuid",
  "branch_id": "branch-uuid",
  "attendance_date": "2025-01-07T10:00:00Z",
  "method": "manual",
  "notes": "Late arrival"
}
```
**Response**:
```json
{
  "message": "Attendance marked successfully",
  "attendance_id": "attendance-uuid"
}
```

### GET /api/attendance/reports
**Description**: Get attendance reports
**Access**: Based on role (Super Admin, Coach Admin, Coach can see all/their branch's reports; Student can only see their own)
**Query Parameters**:
- `student_id`: Filter by student
- `course_id`: Filter by course
- `branch_id`: Filter by branch
- `start_date`: Filter by date range
- `end_date`: Filter by date range
**Response**:
```json
{
  "attendance_records": [
    {
      "id": "attendance-uuid",
      "student_id": "student-uuid",
      "course_id": "course-uuid",
      "branch_id": "branch-uuid",
      "attendance_date": "2025-01-07T10:00:00Z",
      "check_in_time": "2025-01-07T10:00:00Z",
      "check_out_time": null,
      "method": "manual",
      "qr_code_used": null,
      "marked_by": "user-uuid",
      "is_present": true,
      "notes": "Late arrival",
      "created_at": "2025-01-07T10:00:00Z"
    }
  ]
}
```

### GET /api/attendance/reports/export
**Description**: Export attendance reports as a CSV file. Accepts the same filters as the Get Attendance Reports endpoint.
**Access**: Based on role
**Query Parameters**:
- `student_id`: Filter by student
- `course_id`: Filter by course
- `branch_id`: Filter by branch
- `start_date`: Filter by date range
- `end_date`: Filter by date range
**Response**:
A downloadable CSV file with the attendance records.

---

## 7. Payment & Subscription Management

### POST /api/payments
**Description**: Process payment. This will update enrollment payment status if the payment clears it and send a WhatsApp confirmation to the student.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "student_id": "student-uuid",
  "enrollment_id": "enrollment-uuid",
  "amount": 1200.0,
  "payment_type": "course_fee",
  "payment_method": "cash",
  "due_date": "2025-02-01T00:00:00Z",
  "transaction_id": "TXN123456789",
  "notes": "Monthly fee payment"
}
```
**Response**:
```json
{
  "message": "Payment processed successfully",
  "payment_id": "payment-uuid"
}
```

### PUT /api/payments/{payment_id}
**Description**: Update a payment's status.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "payment_status": "paid"
}
```
**Response**:
```json
{
  "message": "Payment updated successfully"
}
```

### POST /api/payments/{payment_id}/proof
**Description**: Submit proof of payment for an offline transaction.
**Access**: Student
**Request Body**:
```json
{
  "proof": "url_to_image_of_receipt"
}
```
**Response**:
```json
{
  "message": "Payment proof submitted successfully."
}
```

### GET /api/payments
**Description**: Get payments with filtering
**Access**: Based on role (Super Admin, Coach Admin can see all/their branch's payments; Student can only see their own)
**Query Parameters**:
- `student_id`: Filter by student
- `enrollment_id`: Filter by enrollment
- `payment_status`: Filter by status (pending, paid, overdue, cancelled)
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 50)
**Response**:
```json
{
  "payments": [
    {
      "id": "payment-uuid",
      "student_id": "student-uuid",
      "enrollment_id": "enrollment-uuid",
      "amount": 1200.0,
      "payment_type": "course_fee",
      "payment_method": "cash",
      "payment_status": "pending",
      "transaction_id": null,
      "payment_date": null,
      "due_date": "2025-02-01T00:00:00Z",
      "notes": "Monthly fee payment",
      "payment_proof": null,
      "created_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### GET /api/payments/dues
**Description**: Get outstanding dues
**Access**: Based on role (Super Admin, Coach Admin can see all/their branch's dues; Student can only see their own)
**Response**:
```json
{
  "outstanding_dues": {
    "student-uuid": {
      "total_amount": 1200.0,
      "payments": [
        {
          "id": "payment-uuid",
          "student_id": "student-uuid",
          "enrollment_id": "enrollment-uuid",
          "amount": 1200.0,
          "payment_type": "course_fee",
          "payment_method": "cash",
          "payment_status": "pending",
          "transaction_id": null,
          "payment_date": null,
          "due_date": "2025-02-01T00:00:00Z",
          "notes": "Monthly fee payment",
          "payment_proof": null,
          "created_at": "2025-01-07T12:00:00Z"
        }
      ]
    }
  }
}
```

### POST /api/payments/send-reminders
**Description**: Triggers sending of payment reminders for all pending and overdue payments via SMS and WhatsApp.
**Access**: Super Admin, Coach Admin
**Response**:
```json
{
  "message": "Successfully sent [X] payment reminders."
}
```

### POST /api/students/payments
**Description**: Allow a student to process a payment for their enrollment. This will send a WhatsApp confirmation to the student.
**Access**: Student
**Request Body**:
```json
{
  "enrollment_id": "enrollment-uuid",
  "amount": 1200.0,
  "payment_method": "online",
  "transaction_id": "TXN123456789",
  "notes": "Online payment for course fee"
}
```
**Response**:
```json
{
  "message": "Payment processed successfully",
  "payment_id": "payment-uuid"
}
```

---

## 8. Products/Accessories Management

### POST /api/products
**Description**: Create product
**Access**: Super Admin
**Request Body**:
```json
{
  "name": "Training Gloves",
  "description": "Professional training gloves",
  "category": "gloves",
  "price": 250.0,
  "branch_availability": {
    "branch-uuid-1": 50
  },
  "stock_alert_threshold": 10,
  "image_url": "https://example.com/gloves.jpg"
}
```
**Response**:
```json
{
  "message": "Product created successfully",
  "product_id": "product-uuid"
}
```

### GET /api/products
**Description**: Get products catalog
**Access**: All authenticated users
**Query Parameters**:
- `branch_id`: Filter by branch availability
- `category`: Filter by category
**Response**:
```json
{
  "products": [
    {
      "id": "product-uuid",
      "name": "Training Gloves",
      "description": "Professional training gloves",
      "category": "gloves",
      "price": 250.0,
      "branch_availability": {
        "branch-uuid-1": 50
      },
      "stock_alert_threshold": 10,
      "image_url": "https://example.com/gloves.jpg",
      "is_active": true,
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### PUT /api/products/{product_id}
**Description**: Update product details.
**Access**: Super Admin
**Request Body**:
```json
{
  "name": "Updated Training Gloves",
  "price": 275.0
}
```
**Response**:
```json
{
  "message": "Product updated successfully"
}
```

### POST /api/products/{product_id}/restock
**Description**: Add stock for a product at a specific branch.
**Access**: Super Admin, Coach Admin (own branch only)
**Request Body**:
```json
{
  "branch_id": "branch-uuid-1",
  "quantity": 50
}
```
**Response**:
```json
{
  "message": "Successfully added 50 units to product Training Gloves at branch branch-uuid-1."
}
```

### GET /api/products/purchases
**Description**: Get product purchases with filtering. Students can only view their own purchases.
**Access**: All authenticated users
**Query Parameters**:
- `student_id`: Filter by student (Admin only)
- `branch_id`: Filter by branch (Admin only)
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 50)
**Response**:
```json
{
  "purchases": [
    {
      "id": "purchase-uuid",
      "student_id": "student-uuid",
      "product_id": "product-uuid",
      "branch_id": "branch-uuid",
      "quantity": 2,
      "unit_price": 250.0,
      "total_amount": 500.0,
      "payment_method": "cash",
      "purchase_date": "2025-01-07T12:00:00Z",
      "created_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### POST /api/products/purchase
**Description**: Record offline product purchase. This may trigger a low-stock alert notification to admins.
**Access**: All authenticated users
**Request Body**:
```json
{
  "student_id": "student-uuid",
  "product_id": "product-uuid",
  "branch_id": "branch-uuid",
  "quantity": 2,
  "payment_method": "cash"
}
```
**Response**:
```json
{
  "message": "Purchase recorded successfully",
  "purchase_id": "purchase-uuid",
  "total_amount": 500.0
}
```

### POST /api/students/products/purchase
**Description**: Allow a student to purchase a product online. This may trigger a low-stock alert notification to admins and will create a payment record. A WhatsApp confirmation will be sent to the student.
**Access**: Student
**Request Body**:
```json
{
  "product_id": "product-uuid",
  "quantity": 1,
  "payment_method": "online"
}
```
**Response**:
```json
{
  "message": "Product purchased successfully",
  "purchase_id": "purchase-uuid",
  "total_amount": 250.0
}
```

---

## 9. Complaints & Feedback System

### POST /api/complaints
**Description**: Submit complaint (Students only). This will notify relevant admins via WhatsApp.
**Access**: Students
**Request Body**:
```json
{
  "subject": "Inappropriate behavior",
  "description": "Detailed description of the issue",
  "category": "coach_behavior",
  "coach_id": "coach-uuid",
  "priority": "high"
}
```
**Response**:
```json
{
  "message": "Complaint submitted successfully",
  "complaint_id": "complaint-uuid"
}
```

### GET /api/complaints
**Description**: Get complaints
**Access**: Based on role (Super Admin, Coach Admin can see all/their branch's complaints; Student can only see their own)
**Query Parameters**:
- `status`: Filter by status (open, in_progress, resolved, closed)
- `category`: Filter by category
**Response**:
```json
{
  "complaints": [
    {
      "id": "complaint-uuid",
      "student_id": "student-uuid",
      "branch_id": "branch-uuid",
      "subject": "Inappropriate behavior",
      "description": "Detailed description of the issue",
      "category": "coach_behavior",
      "coach_id": "coach-uuid",
      "status": "open",
      "priority": "high",
      "assigned_to": null,
      "resolution": null,
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### PUT /api/complaints/{complaint_id}
**Description**: Update complaint status. This will trigger a notification to the student who filed the complaint.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "status": "resolved",
  "assigned_to": "admin-uuid",
  "resolution": "Issue has been resolved through counseling"
}
```
**Response**:
```json
{
  "message": "Complaint updated successfully"
}
```

### POST /api/feedback/coaches
**Description**: Rate and review coach
**Access**: Students
**Request Body**:
```json
{
  "coach_id": "coach-uuid",
  "rating": 4,
  "review": "Great instructor, very patient"
}
```
**Response**:
```json
{
  "message": "Rating submitted successfully",
  "rating_id": "rating-uuid"
}
```

### GET /api/coaches/{coach_id}/ratings
**Description**: Get all ratings for a specific coach.
**Access**: All authenticated users
**Response**:
```json
{
  "ratings": [
    {
      "id": "rating-uuid",
      "student_id": "student-uuid",
      "coach_id": "coach-uuid",
      "branch_id": "branch-uuid",
      "rating": 4,
      "review": "Great instructor, very patient",
      "created_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

---

## 10. Session Booking System

### POST /api/sessions/book
**Description**: Book individual session (₹250 flat rate). This will also create a pending payment record for the session fee.
**Access**: Students
**Request Body**:
```json
{
  "course_id": "course-uuid",
  "branch_id": "branch-uuid",
  "coach_id": "coach-uuid",
  "session_date": "2025-01-15T16:00:00Z",
  "duration_minutes": 60,
  "notes": "Focus on basic techniques"
}
```
**Response**:
```json
{
  "message": "Session booked successfully",
  "booking_id": "booking-uuid",
  "fee": 250.0
}
```

### GET /api/sessions/my-bookings
**Description**: Get student's session bookings
**Access**: Students
**Response**:
```json
{
  "bookings": [
    {
      "id": "booking-uuid",
      "student_id": "student-uuid",
      "course_id": "course-uuid",
      "branch_id": "branch-uuid",
      "coach_id": "coach-uuid",
      "session_date": "2025-01-15T16:00:00Z",
      "duration_minutes": 60,
      "fee": 250.0,
      "status": "scheduled",
      "payment_status": "pending",
      "notes": "Focus on basic techniques",
      "created_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

---

## 11. Student Requests

### Student Transfer Requests

### POST /api/requests/transfer
**Description**: Create a new transfer request.
**Access**: Student
**Request Body**:
```json
{
  "new_branch_id": "new-branch-uuid",
  "reason": "Moving to a new city."
}
```
**Response**:
```json
{
  "id": "transfer-request-uuid",
  "student_id": "student-uuid",
  "current_branch_id": "current-branch-uuid",
  "new_branch_id": "new-branch-uuid",
  "reason": "Moving to a new city.",
  "status": "pending",
  "created_at": "2025-01-07T12:00:00Z",
  "updated_at": "2025-01-07T12:00:00Z"
}
```

### GET /api/requests/transfer
**Description**: Get a list of transfer requests.
**Access**: Super Admin, Coach Admin (can only see requests for their own branch)
**Query Parameters**:
- `status`: Filter by status (pending, approved, rejected)
**Response**:
```json
{
  "requests": [
    {
      "id": "transfer-request-uuid",
      "student_id": "student-uuid",
      "current_branch_id": "current-branch-uuid",
      "new_branch_id": "new-branch-uuid",
      "reason": "Moving to a new city.",
      "status": "pending",
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### PUT /api/requests/transfer/{request_id}
**Description**: Update a transfer request (approve/reject). On approval, the student's branch will be updated.
**Access**: Super Admin, Coach Admin (can only manage requests for their own branch)
**Request Body**:
```json
{
  "status": "approved"
}
```
**Response**:
```json
{
  "message": "Transfer request updated successfully.",
  "request": {
    "id": "transfer-request-uuid",
    "student_id": "student-uuid",
    "current_branch_id": "current-branch-uuid",
    "new_branch_id": "new-branch-uuid",
    "reason": "Moving to a new city.",
    "status": "approved",
    "created_at": "2025-01-07T12:00:00Z",
    "updated_at": "2025-01-07T12:00:00Z"
  }
}
```

### Student Course Change Requests

### POST /api/requests/course-change
**Description**: Allows a student to request a change to a different course.
**Access**: Student
**Request Body**:
```json
{
  "current_enrollment_id": "enrollment-uuid-old",
  "new_course_id": "course-uuid-new",
  "reason": "I would like to switch to the advanced course."
}
```
**Response**:
```json
{
  "id": "course-change-request-uuid",
  "student_id": "student-uuid",
  "branch_id": "branch-uuid",
  "current_enrollment_id": "enrollment-uuid-old",
  "new_course_id": "course-uuid-new",
  "reason": "I would like to switch to the advanced course.",
  "status": "pending",
  "created_at": "2025-01-07T12:00:00Z",
  "updated_at": "2025-01-07T12:00:00Z"
}
```

### GET /api/requests/course-change
**Description**: Get a list of course change requests.
**Access**: Super Admin, Coach Admin (can only see requests for their own branch)
**Query Parameters**:
- `status`: Filter by status (pending, approved, rejected)
**Response**:
```json
{
  "requests": [
    {
      "id": "course-change-request-uuid",
      "student_id": "student-uuid",
      "branch_id": "branch-uuid",
      "current_enrollment_id": "enrollment-uuid-old",
      "new_course_id": "course-uuid-new",
      "reason": "I would like to switch to the advanced course.",
      "status": "pending",
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### PUT /api/requests/course-change/{request_id}
**Description**: Update a course change request (approve/reject). On approval, the student's old enrollment is deactivated and a new one is created for the new course.
**Access**: Super Admin, Coach Admin (can only manage requests for their own branch)
**Request Body**:
```json
{
  "status": "approved"
}
```
**Response**:
```json
{
  "message": "Course change request updated successfully.",
  "request": {
    "id": "course-change-request-uuid",
    "student_id": "student-uuid",
    "branch_id": "branch-uuid",
    "current_enrollment_id": "enrollment-uuid-old",
    "new_course_id": "course-uuid-new",
    "reason": "I would like to switch to the advanced course.",
    "status": "approved",
    "created_at": "2025-01-07T12:00:00Z",
    "updated_at": "2025-01-07T12:00:00Z"
  }
}
```

---

## 12. Reporting & Analytics

### GET /api/reports/dashboard
**Description**: Get dashboard statistics
**Access**: Based on role (Super Admin can filter by branch; Coach Admin sees their branch's stats; Coach/Student see limited relevant stats)
**Query Parameters**:
- `branch_id`: Filter by branch (for Super Admin)
**Response**:
```json
{
  "dashboard_stats": {
    "total_students": 150,
    "active_enrollments": 120,
    "pending_payments": 25,
    "overdue_payments": 8,
    "today_attendance": 45
  }
}
```

### GET /api/reports/financial
**Description**: Get a financial report summary.
**Access**: Super Admin
**Query Parameters**:
- `start_date`: Filter by date range (ISO 8601 format)
- `end_date`: Filter by date range (ISO 8601 format)
**Response**:
```json
{
  "total_collected": 100000.0,
  "outstanding_dues": 15000.0,
  "report_generated_at": "2025-01-07T12:00:00Z",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-01-31T23:59:59Z"
}
```

### GET /api/reports/branch/{branch_id}
**Description**: Get a detailed report for a specific branch.
**Access**: Super Admin, Coach Admin (can only access reports for their own branch)
**Response**:
```json
{
  "branch_details": {
    "id": "branch-uuid",
    "name": "Downtown Branch",
    "address": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "pincode": "62701",
    "phone": "+1234567890",
    "email": "downtown@example.com",
    "manager_id": "manager-uuid",
    "is_active": true,
    "business_hours": {},
    "created_at": "2025-01-07T12:00:00Z",
    "updated_at": "2025-01-07T12:00:00Z"
  },
  "total_students": 150,
  "active_enrollments": 120,
  "payments_summary": [
    {
      "_id": "paid",
      "total_amount": 80000.0,
      "count": 100
    },
    {
      "_id": "pending",
      "total_amount": 20000.0,
      "count": 20
    }
  ],
  "report_generated_at": "2025-01-07T12:00:00Z"
}
```

---

## 13. Branch Event Management

### POST /api/events
**Description**: Create a new branch event.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "title": "Annual Martial Arts Tournament",
  "description": "Join us for our annual tournament!",
  "start_time": "2025-03-10T09:00:00Z",
  "end_time": "2025-03-10T17:00:00Z"
}
```
**Response**:
```json
{
  "id": "event-uuid",
  "branch_id": "branch-uuid",
  "title": "Annual Martial Arts Tournament",
  "description": "Join us for our annual tournament!",
  "start_time": "2025-03-10T09:00:00Z",
  "end_time": "2025-03-10T17:00:00Z",
  "created_by": "user-uuid",
  "created_at": "2025-01-07T12:00:00Z"
}
```

### GET /api/events
**Description**: Get events for a specific branch.
**Access**: All authenticated users
**Query Parameters**:
- `branch_id`: The ID of the branch to get events for.
**Response**:
```json
{
  "events": [
    {
      "id": "event-uuid",
      "branch_id": "branch-uuid",
      "title": "Annual Martial Arts Tournament",
      "description": "Join us for our annual tournament!",
      "start_time": "2025-03-10T09:00:00Z",
      "end_time": "2025-03-10T17:00:00Z",
      "created_by": "user-uuid",
      "created_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### PUT /api/events/{event_id}
**Description**: Update a branch event.
**Access**: Super Admin, Coach Admin (can only manage events for their own branch)
**Request Body**:
```json
{
  "title": "Updated Tournament Name",
  "description": "New description for the tournament",
  "start_time": "2025-03-10T09:00:00Z",
  "end_time": "2025-03-10T18:00:00Z"
}
```
**Response**:
```json
{
  "message": "Event updated successfully"
}
```

### DELETE /api/events/{event_id}
**Description**: Delete a branch event.
**Access**: Super Admin, Coach Admin (can only manage events for their own branch)
**Response**: (No content) `204 No Content`

---

## 14. Admin & Auditing

### GET /api/admin/activity-logs
**Description**: Get user activity logs (Super Admin only)
**Access**: Super Admin
**Query Parameters**:
- `user_id`: Filter by user ID
- `action`: Filter by action type (e.g., `login_success`, `admin_create_user`)
- `start_date`: Filter by date range (ISO 8601 format)
- `end_date`: Filter by date range (ISO 8601 format)
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 100)
**Response**:
```json
{
  "logs": [
    {
      "id": "log-uuid",
      "user_id": "user-uuid",
      "user_name": "John Doe",
      "action": "login_success",
      "details": {
        "email": "john.doe@example.com"
      },
      "status": "success",
      "ip_address": "127.0.0.1",
      "timestamp": "2025-01-08T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

## 15. Notification Management

### POST /api/notifications/templates
**Description**: Create a new notification template.
**Access**: Super Admin
**Request Body**:
```json
{
  "name": "Payment Reminder",
  "type": "whatsapp",
  "subject": "Payment Due",
  "body": "Hi {{student_name}}, a friendly reminder that your payment of {{amount}} is due on {{due_date}}."
}
```
**Response**:
```json
{
  "id": "template-uuid",
  "name": "Payment Reminder",
  "type": "whatsapp",
  "subject": "Payment Due",
  "body": "Hi {{student_name}}, a friendly reminder that your payment of {{amount}} is due on {{due_date}}.",
  "is_active": true,
  "created_at": "2025-01-07T12:00:00Z",
  "updated_at": "2025-01-07T12:00:00Z"
}
```

### GET /api/notifications/templates
**Description**: Get all notification templates.
**Access**: Super Admin
**Response**:
```json
{
  "templates": [
    {
      "id": "template-uuid",
      "name": "Payment Reminder",
      "type": "whatsapp",
      "subject": "Payment Due",
      "body": "Hi {{student_name}}, a friendly reminder that your payment of {{amount}} is due on {{due_date}}.",
      "is_active": true,
      "created_at": "2025-01-07T12:00:00Z",
      "updated_at": "2025-01-07T12:00:00Z"
    }
  ]
}
```

### GET /api/notifications/templates/{template_id}
**Description**: Get a single notification template by ID.
**Access**: Super Admin
**Response**:
```json
{
  "id": "template-uuid",
  "name": "Payment Reminder",
  "type": "whatsapp",
  "subject": "Payment Due",
  "body": "Hi {{student_name}}, a friendly reminder that your payment of {{amount}} is due on {{due_date}}.",
  "is_active": true,
  "created_at": "2025-01-07T12:00:00Z",
  "updated_at": "2025-01-07T12:00:00Z"
}
```

### PUT /api/notifications/templates/{template_id}
**Description**: Update a notification template.
**Access**: Super Admin
**Request Body**: (Same as create)
```json
{
  "name": "Updated Payment Reminder",
  "type": "whatsapp",
  "subject": "Updated Payment Due",
  "body": "Hi {{student_name}}, your payment of {{amount}} is now due on {{due_date}}. Please pay soon."
}
```
**Response**:
```json
{
  "message": "Template updated successfully"
}
```

### DELETE /api/notifications/templates/{template_id}
**Description**: Delete a notification template.
**Access**: Super Admin
**Response**: (No content) `204 No Content`

### POST /api/notifications/trigger
**Description**: Trigger a notification for a specific user using a template.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "user_id": "user-uuid",
  "template_id": "template-uuid",
  "context": {
    "student_name": "John Doe",
    "amount": "₹1200",
    "due_date": "2025-02-01"
  }
}
```
**Response**:
```json
{
  "message": "Notification sent successfully."
}
```

### POST /api/notifications/broadcast
**Description**: Broadcast a notification to all users, or all users in a specific branch. This can be used for branch-wide announcements. Coach Admins can only broadcast to their own branch.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "branch_id": "branch-uuid",
  "template_id": "template-uuid",
  "context": {
    "event_name": "Holiday Closure"
  }
}
```
**Response**:
```json
{
  "message": "Broadcast sent. Attempted to notify [X] users, successfully sent to [Y]."
}
```

### GET /api/notifications/logs
**Description**: Get a log of all notifications that have been sent.
**Access**: Super Admin, Coach Admin (can only see logs for users in their branch)
**Query Parameters**:
- `user_id`: Filter by user ID
- `template_id`: Filter by template ID
- `status`: Filter by status (e.g., `sent`, `failed`)
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 100)
**Response**:
```json
{
  "logs": [
    {
      "id": "log-uuid",
      "user_id": "user-uuid",
      "template_id": "template-uuid",
      "type": "whatsapp",
      "status": "sent",
      "content": "Hi John Doe, a friendly reminder...",
      "created_at": "2025-01-09T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## 16. Reminders

### POST /api/reminders/class
**Description**: Triggers class reminders for all students enrolled in a specific course/branch. In a real-world application, this would be called by a scheduled job (e.g., daily).
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "course_id": "course-uuid",
  "branch_id": "branch-uuid"
}
```
**Response**:
```json
{
  "message": "Sent [X] class reminders for course '[Course Name]'."
}
```

---

## Response Codes

- `200`: Success
- `201`: Created
- `204`: No Content (for successful deletions)
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

## Error Response Format
```json
{
  "detail": "Error message description"
}
```

---

## Integration Points for Later Implementation

### 1. Firebase SMS Integration
- **Purpose**: Send login credentials and payment reminders
- **Endpoints**: Will be integrated into user creation and payment processing
- **Required**: Firebase Service Account JSON, Project ID, Web API Key

### 2. zaptra.in WhatsApp Integration
- **Purpose**: Send course notifications, payment reminders, complaint alerts
- **Endpoints**: Will be integrated into enrollment, payment, and complaint systems
- **Required**: zaptra.in API key/token, API endpoint URL

### 3. Biometric Integration
- **Purpose**: Alternative attendance marking method
- **Endpoints**: `/api/attendance/biometric` (to be implemented)
- **Required**: Biometric device API specifications

---

## Sample Usage Flows

### Student Registration & Enrollment Flow
1. `POST /api/auth/register` - Register student
2. `POST /api/auth/login` - Login
3. `GET /api/courses` - Browse available courses
4. Admin: `POST /api/enrollments` - Enroll student in course
5. `POST /api/payments` - Process admission fee and course fee

### Daily Attendance Flow
1. Coach: `POST /api/attendance/generate-qr` - Generate QR for class
2. Student: `POST /api/attendance/scan-qr` - Scan QR to mark attendance
3. Coach: `GET /api/attendance/reports` - View attendance

### Payment Management Flow
1. `GET /api/payments/dues` - Check outstanding dues
2. `POST /api/payments` - Record payment
3. Auto-send WhatsApp confirmation (when integrated)

### Complaint Handling Flow
1. Student: `POST /api/complaints` - Submit complaint
2. Auto-notify admins via WhatsApp (when integrated)
3. Admin: `PUT /api/complaints/{id}` - Update complaint status
4. Student: `GET /api/complaints` - Check complaint status

This API provides a comprehensive foundation for the Student Management System with proper authentication, authorization, and business logic. The external integrations (Firebase SMS, zaptra.in WhatsApp) can be easily added to the existing notification functions.
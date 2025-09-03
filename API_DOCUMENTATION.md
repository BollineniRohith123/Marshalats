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
**Description**: Register a new student (public endpoint)
**Access**: Public
**Request Body**:
```json
{
  "email": "student@example.com",
  "phone": "+1234567890",
  "full_name": "John Doe",
  "dob": "1995-05-15",
  "gender": "Male",
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
**Description**: Get current user information. **Note:** If a student has an overdue payment, this endpoint (and any other requiring authentication) will return a 403 Forbidden error, and a notification will be sent to the branch's Coach Admin.
**Access**: Authenticated users
**Response**:
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "phone": "+1234567890",
  "full_name": "John Doe",
  "dob": "1995-05-15T00:00:00",
  "gender": "Male",
  "role": "student",
  "branch_id": "branch-uuid",
  "biometric_id": "fingerprint_123",
  "is_active": true,
  "created_at": "2025-01-07T12:00:00Z",
  "branch_details": {
    "id": "branch-uuid",
    "name": "Downtown Branch",
    "manager_name": "Jane Smith"
  }
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
  "dob": "1995-05-16",
  "gender": "Female",
  "biometric_id": "fingerprint_456"
}
```

### POST /api/auth/forgot-password
**Description**: Initiate password reset
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
**Description**: Create new user
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "email": "newuser@example.com",
  "phone": "+1234567890",
  "full_name": "New User",
  "dob": "1990-01-01",
  "gender": "Male",
  "role": "coach_admin",
  "branch_id": "branch-uuid"
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
**Description**: Update user. Coach Admins can only update students in their own branch. **This will notify the branch's Coach Admin.**
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "full_name": "Updated Name",
  "dob": "1991-02-03",
  "gender": "Non-binary"
}
```

### DELETE /api/users/{user_id}
**Description**: Deactivate user
**Access**: Super Admin

### POST /api/users/{user_id}/force-password-reset
**Description**: Force a password reset for a user. A new temporary password will be generated and sent to the user.
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

### GET /api/branches
**Description**: Get all branches
**Access**: All authenticated users

### GET /api/branches/{branch_id}
**Description**: Get branch by ID
**Access**: All authenticated users

### PUT /api/branches/{branch_id}
**Description**: Update branch.
**Access**: Super Admin, Coach Admin (own branch only)
**Details**: Coach Admins can only update certain fields (e.g., name, address, phone) and cannot update the manager or active status.

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

### GET /api/branches/{branch_id}/holidays
**Description**: Get all holidays for a specific branch.
**Access**: All authenticated users

### DELETE /api/branches/{branch_id}/holidays/{holiday_id}
**Description**: Delete a holiday for a branch.
**Access**: Super Admin, Coach Admin (own branch only)

### DELETE /api/branches/{branch_id}
**Description**: Permanently delete a branch. This action will fail if the branch has any associated users.
**Access**: Super Admin

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

### GET /api/courses
**Description**: Get courses
**Access**: All authenticated users
**Query Parameters**:
- `branch_id`: Filter by branch
- `category`: Filter by course category (e.g., `Martial Arts`)
- `level`: Filter by course level (e.g., `Beginner`)

### PUT /api/courses/{course_id}
**Description**: Update course
**Access**: Super Admin, Coach Admin

### DELETE /api/courses/{course_id}
**Description**: Permanently delete a course. This action will fail if the course has any student enrollments (past or present).
**Access**: Super Admin

---

## 5. Student Enrollment & Management

### POST /api/enrollments
**Description**: Create student enrollment
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

### GET /api/enrollments
**Description**: Get enrollments with filtering
**Access**: Based on role
**Query Parameters**:
- `student_id`: Filter by student
- `course_id`: Filter by course
- `branch_id`: Filter by branch

### PUT /api/enrollments/{enrollment_id}
**Description**: Update an enrollment's status (e.g., to mark as inactive/complete). **This will trigger a course completion notification if the enrollment is deactivated.**
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "is_active": false,
  "payment_status": "paid"
}
```

### GET /api/students/{student_id}/courses
**Description**: Get student's enrolled courses
**Access**: Student (own data), Admins

### POST /api/students/enroll
**Description**: Allow a student to enroll themselves in a course.
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

### GET /api/attendance/reports
**Description**: Get attendance reports
**Access**: Based on role
**Query Parameters**:
- `student_id`: Filter by student
- `course_id`: Filter by course
- `branch_id`: Filter by branch
- `start_date`: Filter by date range
- `end_date`: Filter by date range

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

### GET /api/attendance/anomalies
**Description**: Identifies attendance anomalies, defined as students with 3 or more consecutive absences in any course.
**Access**: Super Admin, Coach Admin (can only see anomalies for their branch)
**Query Parameters**:
- `branch_id`: Filter anomalies by a specific branch (Super Admin only).
**Response**:
```json
{
  "anomalies": [
    {
      "student_name": "John Doe",
      "student_id": "student-uuid",
      "course_name": "Advanced Karate",
      "course_id": "course-uuid",
      "details": "3 or more consecutive absences detected."
    }
  ]
}
```

---

## 7. Payment & Subscription Management

### POST /api/payments
**Description**: Process payment
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

### GET /api/payments
**Description**: Get payments with filtering
**Access**: Based on role
**Query Parameters**:
- `student_id`: Filter by student
- `enrollment_id`: Filter by enrollment
- `payment_status`: Filter by status (pending, paid, overdue, cancelled)

### GET /api/payments/dues
**Description**: Get outstanding dues
**Access**: Based on role

### POST /api/payments/send-reminders
**Description**: Triggers sending of payment reminders for all pending and overdue payments.
**Access**: Super Admin, Coach Admin
**Response**:
```json
{
  "message": "Successfully sent [X] payment reminders."
}
```

### POST /api/students/payments
**Description**: Allow a student to process a payment for their enrollment.
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
  "attendance_policy": {
    "min_percentage": 80
  },
  "stock_alert_threshold": 10,
  "image_url": "https://example.com/gloves.jpg"
}
```

### GET /api/products
**Description**: Get products catalog
**Access**: All authenticated users
**Query Parameters**:
- `branch_id`: Filter by branch availability
- `category`: Filter by category

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

### POST /api/products/purchase
**Description**: Record offline product purchase. **This may trigger a low-stock alert notification to admins.**
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

### GET /api/products/purchases
**Description**: Get product purchases with filtering. Students can only view their own purchases.
**Access**: All authenticated users
**Query Parameters**:
- `student_id`: Filter by student (Admin only)
- `branch_id`: Filter by branch (Admin only)

### POST /api/students/products/purchase
**Description**: Allow a student to purchase a product online. **This may trigger a low-stock alert notification to admins.**
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
**Description**: Submit complaint (Students only)
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

### GET /api/complaints
**Description**: Get complaints
**Access**: Based on role
**Query Parameters**:
- `status`: Filter by status (open, in_progress, resolved, closed)
- `category`: Filter by category

### PUT /api/complaints/{complaint_id}
**Description**: Update complaint status. **This will trigger a notification to the student who filed the complaint.**
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "status": "resolved",
  "assigned_to": "admin-uuid",
  "resolution": "Issue has been resolved through counseling"
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

---

## 10. Session Booking System

### POST /api/sessions/book
**Description**: Book individual session (₹250 flat rate)
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

### GET /api/sessions/my-bookings
**Description**: Get student's session bookings
**Access**: Students

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

### GET /api/requests/transfer
**Description**: Get a list of transfer requests.
**Access**: Super Admin, Coach Admin
**Query Parameters**:
- `status`: Filter by status (pending, approved, rejected)

### PUT /api/requests/transfer/{request_id}
**Description**: Update a transfer request (approve/reject).
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "status": "approved"
}
```

### Resource Requests

### POST /api/requests/resource
**Description**: Allows a Coach Admin to request resources (e.g., staff, maintenance) for their branch.
**Access**: Coach Admin
**Request Body**:
```json
{
  "resource_type": "maintenance",
  "description": "The air conditioning unit in the main hall is not working."
}
```

### GET /api/requests/resource
**Description**: Get a list of resource requests.
**Access**: Super Admin, Coach Admin (own branch only)
**Query Parameters**:
- `status`: Filter by status (pending, approved, rejected, fulfilled)

### PUT /api/requests/resource/{request_id}
**Description**: Update a resource request.
**Access**: Super Admin
**Request Body**:
```json
{
  "status": "approved"
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

### GET /api/requests/course-change
**Description**: Get a list of course change requests.
**Access**: Super Admin, Coach Admin
**Query Parameters**:
- `status`: Filter by status (pending, approved, rejected)

### PUT /api/requests/course-change/{request_id}
**Description**: Update a course change request (approve/reject). On approval, the student's old enrollment is deactivated and a new one is created for the new course.
**Access**: Super Admin, Coach Admin
**Request Body**:
```json
{
  "status": "approved"
}
```

---

## 12. Reporting & Analytics

### GET /api/reports/dashboard
**Description**: Get dashboard statistics
**Access**: Based on role
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

### GET /api/reports/branch/{branch_id}
**Description**: Get a detailed report for a specific branch.
**Access**: Super Admin, Coach Admin

### GET /api/reports/branch/{branch_id}/export
**Description**: Export a detailed report for a specific branch as a CSV file.
**Access**: Super Admin, Coach Admin

### GET /api/reports/accessory-sales
**Description**: Get a sales report for accessories, grouped by product.
**Access**: Super Admin, Coach Admin (can only see sales for their branch)
**Query Parameters**:
- `branch_id`: Filter by a specific branch.
- `product_id`: Filter for a specific product.
- `start_date`: Filter by date range (ISO 8601 format).
- `end_date`: Filter by date range (ISO 8601 format).
**Response**:
```json
{
  "report": [
    {
      "product_id": "product-uuid-1",
      "product_name": "Training Gloves",
      "total_quantity_sold": 15,
      "total_revenue": 3750.0
    }
  ]
}
```

### GET /api/courses/{course_id}/stats
**Description**: Get statistics for a specific course.
**Access**: Super Admin, Coach Admin

---

## 13. Branch Event Management

### POST /api/events
**Description**: Create a new branch event.
**Access**: Super Admin, Coach Admin

### GET /api/events
**Description**: Get events for a specific branch.
**Access**: All authenticated users

### PUT /api/events/{event_id}
**Description**: Update a branch event.
**Access**: Super Admin, Coach Admin

### DELETE /api/events/{event_id}
**Description**: Delete a branch event.
**Access**: Super Admin, Coach Admin

---

## 14. Payment Proof

### POST /api/payments/{payment_id}/proof
**Description**: Submit proof of payment for an offline transaction.
**Access**: Student



## Response Codes

- `200`: Success
- `201`: Created
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

## 15. Admin & Auditing

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

## 16. Notification Management

### POST /api/notifications/templates
**Description**: Create a new notification template.
**Access**: Super Admin
**Request Body**:
```json
{
  "name": "Payment Reminder",
  "type": "whatsapp",
  "body": "Hi {{student_name}}, a friendly reminder that your payment of {{amount}} is due on {{due_date}}."
}
```

### GET /api/notifications/templates
**Description**: Get all notification templates.
**Access**: Super Admin

### PUT /api/notifications/templates/{template_id}
**Description**: Update a notification template.
**Access**: Super Admin
**Request Body**: (Same as create)

### DELETE /api/notifications/templates/{template_id}
**Description**: Delete a notification template.
**Access**: Super Admin

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

### POST /api/notifications/broadcast
**Description**: Broadcast a notification to all users, or all users in a specific branch. **This can be used for branch-wide announcements.**
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

### GET /api/notifications/my-history
**Description**: Get the current student's notification history.
**Access**: Student
**Query Parameters**:
- `skip`: Skip records (pagination)
- `limit`: Limit records (default: 50)
**Response**: A paginated list of `NotificationLog` objects.

---

## 17. Reminders

### POST /api/reminders/class
**Description**: Triggers class reminders for all students enrolled in a specific course. In a real-world application, this would be called by a scheduled job (e.g., daily).
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

### POST /api/reminders/attendance
**Description**: Triggers low attendance warnings for all students whose attendance percentage has fallen below their course's policy threshold.
**Access**: Super Admin, Coach Admin
**Response**:
```json
{
  "message": "Sent [Y] low attendance warnings."
}
```

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
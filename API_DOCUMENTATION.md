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
  "full_name": "Jane Doe"
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
**Description**: Update user. Coach Admins can only update students in their own branch.
**Access**: Super Admin, Coach Admin

### DELETE /api/users/{user_id}
**Description**: Deactivate user
**Access**: Super Admin

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
**Description**: Update branch
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

### PUT /api/courses/{course_id}
**Description**: Update course
**Access**: Super Admin, Coach Admin

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
    "branch-uuid-1": 50,
    "branch-uuid-2": 30
  },
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

### POST /api/products/purchase
**Description**: Record offline product purchase
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
**Description**: Allow a student to purchase a product online.
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
**Description**: Update complaint status
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

## 11. Student Transfer Requests

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

### GET /api/reports/branch/{branch_id}
**Description**: Get a detailed report for a specific branch.
**Access**: Super Admin, Coach Admin

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
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
import uuid
import hashlib
import jwt
from passlib.context import CryptContext
import qrcode
import io
import base64
from enum import Enum
import secrets
import re
from bson import ObjectId

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
db = None

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get('DB_NAME', 'student_management_db')]
    print("Database connection opened.")
    yield
    client.close()
    print("Database connection closed.")

# Create FastAPI app
app = FastAPI(title="Student Management System", version="1.0.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('SECRET_KEY', 'student_management_secret_key_2025')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Enums
class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    COACH_ADMIN = "coach_admin" 
    COACH = "coach"
    STUDENT = "student"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class AttendanceMethod(str, Enum):
    QR_CODE = "qr_code"
    BIOMETRIC = "biometric"
    MANUAL = "manual"

class ComplaintStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class SessionStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

# Base Models
class BaseUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    phone: str
    full_name: str
    role: UserRole
    branch_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    full_name: str
    role: UserRole
    branch_id: Optional[str] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    branch_id: Optional[str] = None
    is_active: Optional[bool] = None

class Branch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    city: str
    state: str
    pincode: str
    phone: str
    email: EmailStr
    manager_id: Optional[str] = None
    is_active: bool = True
    business_hours: Dict[str, Dict[str, str]] = {}  # {"monday": {"open": "09:00", "close": "18:00"}}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BranchCreate(BaseModel):
    name: str
    address: str
    city: str
    state: str
    pincode: str
    phone: str
    email: EmailStr
    manager_id: Optional[str] = None
    business_hours: Optional[Dict[str, Dict[str, str]]] = {}

class BranchUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    manager_id: Optional[str] = None
    business_hours: Optional[Dict[str, Dict[str, str]]] = None
    is_active: Optional[bool] = None

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    duration_months: int
    base_fee: float
    branch_pricing: Dict[str, float] = {}  # {"branch_id": price}
    coach_id: Optional[str] = None
    schedule: Dict[str, Any] = {}  # Flexible schedule structure
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CourseCreate(BaseModel):
    name: str
    description: str
    duration_months: int
    base_fee: float
    branch_pricing: Optional[Dict[str, float]] = {}
    coach_id: Optional[str] = None
    schedule: Optional[Dict[str, Any]] = {}

class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_months: Optional[int] = None
    base_fee: Optional[float] = None
    branch_pricing: Optional[Dict[str, float]] = None
    coach_id: Optional[str] = None
    schedule: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class Enrollment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    course_id: str
    branch_id: str
    enrollment_date: datetime = Field(default_factory=datetime.utcnow)
    start_date: datetime
    end_date: datetime
    fee_amount: float
    admission_fee: float = 500.0  # Non-refundable admission fee
    payment_status: PaymentStatus = PaymentStatus.PENDING
    next_due_date: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EnrollmentCreate(BaseModel):
    student_id: str
    course_id: str
    branch_id: str
    start_date: datetime
    fee_amount: float
    admission_fee: float = 500.0

class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    enrollment_id: str
    amount: float
    payment_type: str  # "course_fee", "admission_fee", "session_fee", "accessory"
    payment_method: str  # "online", "cash", "upi", "card"
    payment_status: PaymentStatus
    transaction_id: Optional[str] = None
    payment_date: Optional[datetime] = None
    due_date: datetime
    notes: Optional[str] = None
    payment_proof: Optional[str] = None  # URL or reference to the proof
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentProof(BaseModel):
    proof: str

class PaymentCreate(BaseModel):
    student_id: str
    enrollment_id: str
    amount: float
    payment_type: str
    payment_method: str
    due_date: datetime
    transaction_id: Optional[str] = None
    notes: Optional[str] = None

class Attendance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    course_id: str
    branch_id: str
    attendance_date: datetime
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    method: AttendanceMethod
    qr_code_used: Optional[str] = None
    marked_by: Optional[str] = None  # User ID who marked attendance
    is_present: bool = True
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AttendanceCreate(BaseModel):
    student_id: str
    course_id: str
    branch_id: str
    attendance_date: datetime
    method: AttendanceMethod
    qr_code_used: Optional[str] = None
    notes: Optional[str] = None

class QRCodeSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    branch_id: str
    course_id: str
    qr_code: str
    qr_code_data: str  # Base64 encoded QR image
    generated_by: str  # User ID
    valid_until: datetime
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str  # "uniform", "gloves", "belt", "accessories"
    price: float
    branch_availability: Dict[str, int] = {}  # {"branch_id": stock_count}
    image_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    description: str
    category: str
    price: float
    branch_availability: Optional[Dict[str, int]] = {}
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    branch_availability: Optional[Dict[str, int]] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class ProductPurchase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    product_id: str
    branch_id: str
    quantity: int
    unit_price: float
    total_amount: float
    payment_method: str
    purchase_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductPurchaseCreate(BaseModel):
    student_id: str
    product_id: str
    branch_id: str
    quantity: int
    payment_method: str

class Complaint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    branch_id: str
    subject: str
    description: str
    category: str  # "coach_behavior", "facilities", "safety", "other"
    coach_id: Optional[str] = None  # If complaint is about specific coach
    status: ComplaintStatus = ComplaintStatus.OPEN
    priority: str = "medium"  # "low", "medium", "high", "urgent"
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ComplaintCreate(BaseModel):
    subject: str
    description: str
    category: str
    coach_id: Optional[str] = None
    priority: str = "medium"

class ComplaintUpdate(BaseModel):
    status: Optional[ComplaintStatus] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    priority: Optional[str] = None

class CoachRating(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    coach_id: str
    branch_id: str
    rating: int  # 1-5
    review: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CoachRatingCreate(BaseModel):
    coach_id: str
    rating: int
    review: Optional[str] = None

class SessionBooking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    course_id: str
    branch_id: str
    coach_id: str
    session_date: datetime
    duration_minutes: int = 60
    fee: float = 250.0  # Flat rate
    status: SessionStatus = SessionStatus.SCHEDULED
    payment_status: PaymentStatus = PaymentStatus.PENDING
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SessionBookingCreate(BaseModel):
    course_id: str
    branch_id: str
    coach_id: str
    session_date: datetime
    duration_minutes: int = 60
    notes: Optional[str] = None

# Authentication utilities
def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key == "_id":
                continue  # Skip MongoDB _id field
            elif isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = serialize_doc(value)
            elif isinstance(value, list):
                result[key] = serialize_doc(value)
            else:
                result[key] = value
        return result
    return doc

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return serialize_doc(user)

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")

    # Restrict access for students with overdue payments
    if current_user["role"] == UserRole.STUDENT:
        overdue_payment = await db.payments.find_one({
            "student_id": current_user["id"],
            "payment_status": PaymentStatus.OVERDUE.value
        })
        if overdue_payment:
            raise HTTPException(status_code=403, detail="Access restricted due to overdue payments.")

    return current_user

def require_role(allowed_roles: List[UserRole]):
    async def role_checker(current_user: dict = Depends(get_current_active_user)):
        if current_user["role"] not in [role.value for role in allowed_roles]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

# QR Code utilities
def generate_qr_code(data: str) -> str:
    """Generate QR code and return base64 encoded image"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return base64.b64encode(img_buffer.getvalue()).decode()

# Notification utilities (Mock implementations - to be replaced with real integrations)
async def send_sms(phone: str, message: str) -> bool:
    """Mock SMS sending - to be replaced with Firebase integration"""
    logging.info(f"Mock SMS sent to {phone}: {message}")
    return True

async def send_whatsapp(phone: str, message: str) -> bool:
    """Mock WhatsApp sending - to be replaced with zaptra.in integration"""
    logging.info(f"Mock WhatsApp sent to {phone}: {message}")
    return True

# AUTHENTICATION ENDPOINTS
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    """Register a new student (public endpoint)"""
    # Check if user exists
    existing_user = await db.users.find_one({
        "$or": [{"email": user_data.email}, {"phone": user_data.phone}]
    })
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email or phone already exists")
    
    # Generate password if not provided
    if not user_data.password:
        user_data.password = secrets.token_urlsafe(8)
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user = BaseUser(**user_data.dict())
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    
    result = await db.users.insert_one(user_dict)
    
    # Send credentials via SMS (mock)
    await send_sms(user.phone, f"Your account created. Email: {user.email}, Password: {user_data.password}")
    
    return {"message": "User registered successfully", "user_id": user.id}

@api_router.post("/auth/login")
async def login(user_credentials: UserLogin):
    """User login"""
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Account is deactivated")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return {"access_token": access_token, "token_type": "bearer", "user": {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "full_name": user["full_name"]
    }}

@api_router.post("/auth/forgot-password")
async def forgot_password(forgot_password_data: ForgotPassword):
    """Initiate password reset process"""
    user = await db.users.find_one({"email": forgot_password_data.email})
    if not user:
        # Don't reveal that the user does not exist
        return {"message": "If an account with that email exists, a password reset link has been sent."}

    # Generate a short-lived token for password reset
    reset_token = create_access_token(
        data={"sub": user["id"], "scope": "password_reset"},
        expires_delta=timedelta(minutes=15)
    )

    # In a real application, you would email this token to the user
    # For this example, we'll just log it.
    logging.info(f"Password reset token for {user['email']}: {reset_token}")

    await send_sms(user["phone"], f"Your password reset token is: {reset_token}")

    response = {"message": "If an account with that email exists, a password reset link has been sent."}
    if os.environ.get("TESTING") == "True":
        response["reset_token"] = reset_token
    return response

@api_router.post("/auth/reset-password")
async def reset_password(reset_password_data: ResetPassword):
    """Reset password using a token"""
    try:
        payload = jwt.decode(
            reset_password_data.token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        if payload.get("scope") != "password_reset":
            raise HTTPException(status_code=401, detail="Invalid token scope")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    new_hashed_password = hash_password(reset_password_data.new_password)
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"password": new_hashed_password, "updated_at": datetime.utcnow()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Password has been reset successfully."}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user information"""
    user_info = current_user.copy()
    user_info.pop("password", None)
    return user_info

@api_router.put("/auth/profile")
async def update_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Update user profile"""
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": update_data}
    )
    return {"message": "Profile updated successfully"}

# USER MANAGEMENT ENDPOINTS (Super Admin only)
@api_router.post("/users")
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Create new user (Super Admin or Coach Admin)"""
    # If a coach admin is creating a user, they must be in the same branch
    if current_user["role"] == UserRole.COACH_ADMIN:
        if not current_user.get("branch_id") or user_data.branch_id != current_user["branch_id"]:
            raise HTTPException(status_code=403, detail="Coach Admins can only create users for their own branch.")
        # Coach admins cannot create other admins
        if user_data.role in [UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]:
            raise HTTPException(status_code=403, detail="Coach Admins cannot create other admin users.")

    # Check if user exists
    existing_user = await db.users.find_one({
        "$or": [{"email": user_data.email}, {"phone": user_data.phone}]
    })
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Generate password if not provided
    if not user_data.password:
        user_data.password = secrets.token_urlsafe(8)
    
    hashed_password = hash_password(user_data.password)
    user = BaseUser(**user_data.dict())
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    
    await db.users.insert_one(user_dict)
    
    # Send credentials
    await send_sms(user.phone, f"Account created. Email: {user.email}, Password: {user_data.password}")
    
    return {"message": "User created successfully", "user_id": user.id}

@api_router.get("/users")
async def get_users(
    role: Optional[UserRole] = None,
    branch_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Get users with filtering"""
    filter_query = {}
    if role:
        filter_query["role"] = role.value
    if branch_id:
        filter_query["branch_id"] = branch_id
    
    users = await db.users.find(filter_query).skip(skip).limit(limit).to_list(length=limit)
    for user in users:
        user.pop("password", None)
    
    return {"users": serialize_doc(users), "total": len(users)}

@api_router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Update user (Super Admin or Coach Admin)"""
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user["role"] == UserRole.COACH_ADMIN:
        # Coach Admins can only update students in their own branch
        if target_user["role"] != UserRole.STUDENT.value:
            raise HTTPException(status_code=403, detail="Coach Admins can only update student profiles.")
        if target_user.get("branch_id") != current_user.get("branch_id"):
            raise HTTPException(status_code=403, detail="Coach Admins can only update students in their own branch.")

    update_data = {k: v for k, v in user_update.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        # This case should be rare due to the check above, but it's good practice
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User updated successfully"}

# TRANSFER REQUESTS
class TransferRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TransferRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    current_branch_id: str
    new_branch_id: str
    reason: str
    status: TransferRequestStatus = TransferRequestStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TransferRequestCreate(BaseModel):
    new_branch_id: str
    reason: str

class TransferRequestUpdate(BaseModel):
    status: TransferRequestStatus

@api_router.post("/requests/transfer", status_code=status.HTTP_201_CREATED)
async def create_transfer_request(
    request_data: TransferRequestCreate,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Create a new transfer request."""
    if not current_user.get("branch_id"):
        raise HTTPException(status_code=400, detail="User is not currently assigned to a branch.")

    transfer_request = TransferRequest(
        student_id=current_user["id"],
        current_branch_id=current_user["branch_id"],
        **request_data.dict()
    )
    await db.transfer_requests.insert_one(transfer_request.dict())
    return transfer_request

@api_router.get("/requests/transfer")
async def get_transfer_requests(
    status: Optional[TransferRequestStatus] = None,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Get a list of transfer requests."""
    filter_query = {}
    if status:
        filter_query["status"] = status.value

    if current_user["role"] == UserRole.COACH_ADMIN:
        # Coach admins can only see requests for their branch
        filter_query["current_branch_id"] = current_user.get("branch_id")

    requests = await db.transfer_requests.find(filter_query).to_list(1000)
    return {"requests": serialize_doc(requests)}

@api_router.put("/requests/transfer/{request_id}")
async def update_transfer_request(
    request_id: str,
    update_data: TransferRequestUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Update a transfer request (approve/reject)."""
    transfer_request = await db.transfer_requests.find_one({"id": request_id})
    if not transfer_request:
        raise HTTPException(status_code=404, detail="Transfer request not found")

    if current_user["role"] == UserRole.COACH_ADMIN:
        if transfer_request["current_branch_id"] != current_user.get("branch_id"):
            raise HTTPException(status_code=403, detail="You can only manage requests for your own branch.")

    updated_request = await db.transfer_requests.find_one_and_update(
        {"id": request_id},
        {"$set": {"status": update_data.status, "updated_at": datetime.utcnow()}},
        return_document=True
    )

    # If approved, update the student's branch
    if update_data.status == TransferRequestStatus.APPROVED:
        await db.users.update_one(
            {"id": transfer_request["student_id"]},
            {"$set": {"branch_id": transfer_request["new_branch_id"]}}
        )

    return {"message": "Transfer request updated successfully.", "request": serialize_doc(updated_request)}

# BRANCH EVENT MANAGEMENT
class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    branch_id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EventCreate(BaseModel):
    title: str
    description: str
    start_time: datetime
    end_time: datetime

@api_router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Create a new branch event."""
    if not current_user.get("branch_id"):
        raise HTTPException(status_code=400, detail="User is not assigned to a branch.")

    event = Event(
        **event_data.dict(),
        branch_id=current_user["branch_id"],
        created_by=current_user["id"]
    )
    await db.events.insert_one(event.dict())
    return event

@api_router.get("/events")
async def get_events(
    branch_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get events for a specific branch."""
    events = await db.events.find({"branch_id": branch_id}).to_list(1000)
    return {"events": serialize_doc(events)}

@api_router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    event_data: EventCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Update a branch event."""
    event = await db.events.find_one({"id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["branch_id"] != current_user.get("branch_id"):
        raise HTTPException(status_code=403, detail="You can only manage events for your own branch.")

    await db.events.update_one(
        {"id": event_id},
        {"$set": event_data.dict()}
    )
    return {"message": "Event updated successfully"}

@api_router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Delete a branch event."""
    event = await db.events.find_one({"id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["branch_id"] != current_user.get("branch_id"):
        raise HTTPException(status_code=403, detail="You can only manage events for your own branch.")

    await db.events.delete_one({"id": event_id})
    return


@api_router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Deactivate user (Super Admin only)"""
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deactivated successfully"}

# BRANCH MANAGEMENT ENDPOINTS
@api_router.post("/branches")
async def create_branch(
    branch_data: BranchCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Create new branch"""
    branch = Branch(**branch_data.dict())
    await db.branches.insert_one(branch.dict())
    return {"message": "Branch created successfully", "branch_id": branch.id}

@api_router.get("/branches")
async def get_branches(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all branches"""
    branches = await db.branches.find({"is_active": True}).skip(skip).limit(limit).to_list(length=limit)
    return {"branches": serialize_doc(branches)}

@api_router.get("/branches/{branch_id}")
async def get_branch(
    branch_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get branch by ID"""
    branch = await db.branches.find_one({"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return serialize_doc(branch)

@api_router.put("/branches/{branch_id}")
async def update_branch(
    branch_id: str,
    branch_update: BranchUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Update branch"""
    update_data = {k: v for k, v in branch_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.branches.update_one(
        {"id": branch_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    return {"message": "Branch updated successfully"}

# COURSE MANAGEMENT ENDPOINTS
@api_router.post("/courses")
async def create_course(
    course_data: CourseCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Create new course"""
    course = Course(**course_data.dict())
    await db.courses.insert_one(course.dict())
    return {"message": "Course created successfully", "course_id": course.id}

@api_router.get("/courses")
async def get_courses(
    branch_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """Get courses"""
    filter_query = {"is_active": True}
    
    courses = await db.courses.find(filter_query).skip(skip).limit(limit).to_list(length=limit)
    
    # Filter by branch pricing if branch_id provided
    if branch_id:
        courses = [c for c in courses if branch_id in c.get("branch_pricing", {})]
    
    return {"courses": serialize_doc(courses)}

@api_router.put("/courses/{course_id}")
async def update_course(
    course_id: str,
    course_update: CourseUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Update course"""
    update_data = {k: v for k, v in course_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"message": "Course updated successfully"}

@api_router.get("/courses/{course_id}/stats")
async def get_course_stats(
    course_id: str,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Get statistics for a specific course."""
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    active_enrollments = await db.enrollments.count_documents({"course_id": course_id, "is_active": True})

    stats = {
        "course_details": serialize_doc(course),
        "active_enrollments": active_enrollments
    }
    return stats

# STUDENT ENROLLMENT ENDPOINTS
@api_router.post("/enrollments")
async def create_enrollment(
    enrollment_data: EnrollmentCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Create student enrollment"""
    # Validate student, course, and branch exist
    student = await db.users.find_one({"id": enrollment_data.student_id, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    course = await db.courses.find_one({"id": enrollment_data.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    branch = await db.branches.find_one({"id": enrollment_data.branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Calculate end date
    end_date = enrollment_data.start_date + timedelta(days=course["duration_months"] * 30)
    
    enrollment = Enrollment(
        **enrollment_data.dict(),
        end_date=end_date,
        next_due_date=enrollment_data.start_date + timedelta(days=30)
    )
    
    await db.enrollments.insert_one(enrollment.dict())
    
    # Create initial payment records
    admission_payment = Payment(
        student_id=enrollment_data.student_id,
        enrollment_id=enrollment.id,
        amount=enrollment_data.admission_fee,
        payment_type="admission_fee",
        payment_method="pending",
        payment_status=PaymentStatus.PENDING,
        due_date=datetime.utcnow() + timedelta(days=7)
    )
    
    course_payment = Payment(
        student_id=enrollment_data.student_id,
        enrollment_id=enrollment.id,
        amount=enrollment_data.fee_amount,
        payment_type="course_fee",
        payment_method="pending", 
        payment_status=PaymentStatus.PENDING,
        due_date=enrollment_data.start_date
    )
    
    await db.payments.insert_many([admission_payment.dict(), course_payment.dict()])
    
    # Send enrollment confirmation
    await send_whatsapp(student["phone"], f"Welcome! You're enrolled in {course['name']}. Start date: {enrollment_data.start_date.date()}")
    
    return {"message": "Enrollment created successfully", "enrollment_id": enrollment.id}

@api_router.get("/enrollments")
async def get_enrollments(
    student_id: Optional[str] = None,
    course_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """Get enrollments with filtering"""
    filter_query = {}
    if student_id:
        filter_query["student_id"] = student_id
    if course_id:
        filter_query["course_id"] = course_id
    if branch_id:
        filter_query["branch_id"] = branch_id
    
    # Role-based filtering
    if current_user["role"] == "student":
        filter_query["student_id"] = current_user["id"]
    elif current_user["role"] == "coach_admin" and current_user.get("branch_id"):
        filter_query["branch_id"] = current_user["branch_id"]
    
    enrollments = await db.enrollments.find(filter_query).skip(skip).limit(limit).to_list(length=limit)
    return {"enrollments": serialize_doc(enrollments)}

@api_router.get("/students/{student_id}/courses")
async def get_student_courses(
    student_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get student's enrolled courses"""
    # Check permission
    if current_user["role"] == "student" and current_user["id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    enrollments = await db.enrollments.find({"student_id": student_id, "is_active": True}).to_list(length=100)
    
    # Enrich with course details
    course_ids = [e["course_id"] for e in enrollments]
    courses = await db.courses.find({"id": {"$in": course_ids}}).to_list(length=100)
    
    course_dict = {c["id"]: c for c in courses}
    
    result = []
    for enrollment in enrollments:
        course = course_dict.get(enrollment["course_id"])
        if course:
            result.append({
                "enrollment": enrollment,
                "course": course
            })
    
    return {"enrolled_courses": serialize_doc(result)}

class StudentEnrollmentCreate(BaseModel):
    course_id: str
    branch_id: str
    start_date: datetime
    # admission_fee and fee_amount will be derived from the course and branch pricing

@api_router.post("/students/enroll", status_code=status.HTTP_201_CREATED)
async def student_enroll_in_course(
    enrollment_data: StudentEnrollmentCreate,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Allow a student to enroll themselves in a course."""
    student_id = current_user["id"]

    # Validate student, course, and branch exist
    student = await db.users.find_one({"id": student_id, "role": "student"})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    course = await db.courses.find_one({"id": enrollment_data.course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    branch = await db.branches.find_one({"id": enrollment_data.branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Check if student is already enrolled in this course
    existing_enrollment = await db.enrollments.find_one({
        "student_id": student_id,
        "course_id": enrollment_data.course_id,
        "is_active": True
    })
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Student already enrolled in this course.")

    # Determine fee_amount based on branch pricing
    admission_fee = 500.0 # Fixed admission fee
    fee_amount = course["base_fee"]
    if enrollment_data.branch_id in course.get("branch_pricing", {}):
        fee_amount = course["branch_pricing"][enrollment_data.branch_id]

    # Calculate end date
    end_date = enrollment_data.start_date + timedelta(days=course["duration_months"] * 30)

    enrollment = Enrollment(
        student_id=student_id,
        course_id=enrollment_data.course_id,
        branch_id=enrollment_data.branch_id,
        start_date=enrollment_data.start_date,
        end_date=end_date,
        fee_amount=fee_amount,
        admission_fee=admission_fee,
        next_due_date=enrollment_data.start_date + timedelta(days=30)
    )

    await db.enrollments.insert_one(enrollment.dict())

    # Create initial payment records (pending)
    admission_payment = Payment(
        student_id=student_id,
        enrollment_id=enrollment.id,
        amount=admission_fee,
        payment_type="admission_fee",
        payment_method="pending",
        payment_status=PaymentStatus.PENDING,
        due_date=datetime.utcnow() + timedelta(days=7)
    )

    course_payment = Payment(
        student_id=student_id,
        enrollment_id=enrollment.id,
        amount=fee_amount,
        payment_type="course_fee",
        payment_method="pending",
        payment_status=PaymentStatus.PENDING,
        due_date=enrollment_data.start_date
    )

    await db.payments.insert_many([admission_payment.dict(), course_payment.dict()])

    # Send enrollment confirmation
    await send_whatsapp(student["phone"], f"Welcome! You're enrolled in {course['name']}. Start date: {enrollment_data.start_date.date()}")

    return {"message": "Enrollment created successfully", "enrollment_id": enrollment.id}

class StudentPaymentCreate(BaseModel):
    enrollment_id: str
    amount: float
    payment_method: str # e.g., "online", "upi", "card"
    transaction_id: Optional[str] = None
    notes: Optional[str] = None

@api_router.post("/students/payments", status_code=status.HTTP_201_CREATED)
async def student_process_payment(
    payment_data: StudentPaymentCreate,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Allow a student to process a payment for their enrollment."""
    student_id = current_user["id"]

    # Validate enrollment and payment
    enrollment = await db.enrollments.find_one({"id": payment_data.enrollment_id, "student_id": student_id})
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found or does not belong to you.")

    # Find the pending payment for this enrollment
    # This assumes there's a specific pending payment the student is trying to clear
    # In a real system, you might have a more complex payment reconciliation logic
    pending_payment = await db.payments.find_one({
        "enrollment_id": payment_data.enrollment_id,
        "student_id": student_id,
        "payment_status": PaymentStatus.PENDING.value,
        "amount": payment_data.amount # Ensure the amount matches
    })

    if not pending_payment:
        raise HTTPException(status_code=400, detail="No matching pending payment found for this enrollment and amount.")

    # Simulate payment gateway interaction (update payment status)
    update_data = {
        "payment_status": PaymentStatus.PAID,
        "payment_method": payment_data.payment_method,
        "transaction_id": payment_data.transaction_id,
        "payment_date": datetime.utcnow(),
        "notes": payment_data.notes,
        "updated_at": datetime.utcnow()
    }

    result = await db.payments.update_one(
        {"id": pending_payment["id"]},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update payment status.")

    # Update enrollment payment status if needed (e.g., if all payments are cleared)
    # This logic might need to be more sophisticated in a real app
    await db.enrollments.update_one(
        {"id": enrollment["id"]},
        {"$set": {"payment_status": PaymentStatus.PAID}} # Simplified: mark enrollment paid if this payment clears it
    )

    # Send payment confirmation
    await send_whatsapp(current_user["phone"], f"Payment of ₹{payment_data.amount} received for enrollment {payment_data.enrollment_id}. Thank you!")

    return {"message": "Payment processed successfully", "payment_id": pending_payment["id"]}

# ATTENDANCE SYSTEM ENDPOINTS
@api_router.post("/attendance/generate-qr")
async def generate_attendance_qr(
    course_id: str,
    branch_id: str,
    valid_minutes: int = 30,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH]))
):
    """Generate QR code for attendance"""
    # Validate course and branch
    course = await db.courses.find_one({"id": course_id})
    branch = await db.branches.find_one({"id": branch_id})
    
    if not course or not branch:
        raise HTTPException(status_code=404, detail="Course or branch not found")
    
    # Generate unique QR data
    qr_data = f"attendance:{course_id}:{branch_id}:{int(datetime.utcnow().timestamp())}"
    qr_code_image = generate_qr_code(qr_data)
    
    # Store QR session
    qr_session = QRCodeSession(
        branch_id=branch_id,
        course_id=course_id,
        qr_code=qr_data,
        qr_code_data=qr_code_image,
        generated_by=current_user["id"],
        valid_until=datetime.utcnow() + timedelta(minutes=valid_minutes)
    )
    
    await db.qr_sessions.insert_one(qr_session.dict())
    
    return {
        "qr_code_id": qr_session.id,
        "qr_code_data": qr_code_image,
        "valid_until": qr_session.valid_until,
        "course_name": course["name"]
    }

@api_router.post("/attendance/scan-qr")
async def scan_qr_attendance(
    qr_code: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Mark attendance via QR code scan"""
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can scan QR codes")
    
    # Find valid QR session
    qr_session = await db.qr_sessions.find_one({
        "qr_code": qr_code,
        "is_active": True,
        "valid_until": {"$gt": datetime.utcnow()}
    })
    
    if not qr_session:
        raise HTTPException(status_code=400, detail="Invalid or expired QR code")
    
    # Check if student is enrolled in this course
    enrollment = await db.enrollments.find_one({
        "student_id": current_user["id"],
        "course_id": qr_session["course_id"],
        "branch_id": qr_session["branch_id"],
        "is_active": True
    })
    
    if not enrollment:
        raise HTTPException(status_code=400, detail="You are not enrolled in this course")
    
    # Check if already marked attendance today
    today = datetime.utcnow().date()
    existing_attendance = await db.attendance.find_one({
        "student_id": current_user["id"],
        "course_id": qr_session["course_id"],
        "attendance_date": {
            "$gte": datetime.combine(today, datetime.min.time()),
            "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
        }
    })
    
    if existing_attendance:
        raise HTTPException(status_code=400, detail="Attendance already marked for today")
    
    # Create attendance record
    attendance = Attendance(
        student_id=current_user["id"],
        course_id=qr_session["course_id"],
        branch_id=qr_session["branch_id"],
        attendance_date=datetime.utcnow(),
        check_in_time=datetime.utcnow(),
        method=AttendanceMethod.QR_CODE,
        qr_code_used=qr_code
    )
    
    await db.attendance.insert_one(attendance.dict())
    
    return {"message": "Attendance marked successfully", "attendance_id": attendance.id}

@api_router.post("/attendance/manual")
async def manual_attendance(
    attendance_data: AttendanceCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN, UserRole.COACH]))
):
    """Manually mark attendance"""
    attendance = Attendance(
        **attendance_data.dict(),
        check_in_time=datetime.utcnow(),
        marked_by=current_user["id"]
    )
    
    await db.attendance.insert_one(attendance.dict())
    return {"message": "Attendance marked successfully", "attendance_id": attendance.id}

@api_router.get("/attendance/reports")
async def get_attendance_reports(
    student_id: Optional[str] = None,
    course_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get attendance reports"""
    filter_query = {}
    
    if student_id:
        filter_query["student_id"] = student_id
    if course_id:
        filter_query["course_id"] = course_id
    if branch_id:
        filter_query["branch_id"] = branch_id
    
    if start_date and end_date:
        filter_query["attendance_date"] = {"$gte": start_date, "$lte": end_date}
    
    # Role-based filtering
    if current_user["role"] == "student":
        filter_query["student_id"] = current_user["id"]
    elif current_user["role"] == "coach_admin" and current_user.get("branch_id"):
        filter_query["branch_id"] = current_user["branch_id"]
    
    attendance_records = await db.attendance.find(filter_query).to_list(length=1000)
    return {"attendance_records": serialize_doc(attendance_records)}

# PAYMENT MANAGEMENT ENDPOINTS
@api_router.post("/payments")
async def process_payment(
    payment_data: PaymentCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Process payment"""
    payment = Payment(
        **payment_data.dict(),
        payment_status=PaymentStatus.PAID if payment_data.transaction_id else PaymentStatus.PENDING,
        payment_date=datetime.utcnow() if payment_data.transaction_id else None
    )
    
    await db.payments.insert_one(payment.dict())
    
    # Update enrollment payment status if needed
    if payment.payment_status == PaymentStatus.PAID:
        enrollment = await db.enrollments.find_one({"id": payment.enrollment_id})
        if enrollment:
            # Calculate next due date
            next_due = datetime.utcnow() + timedelta(days=30)
            await db.enrollments.update_one(
                {"id": payment.enrollment_id},
                {"$set": {"payment_status": PaymentStatus.PAID, "next_due_date": next_due}}
            )
    
    # Send payment confirmation
    student = await db.users.find_one({"id": payment.student_id})
    if student:
        message = f"Payment received: ₹{payment.amount} for {payment.payment_type}. Thank you!"
        await send_whatsapp(student["phone"], message)
    
    return {"message": "Payment processed successfully", "payment_id": payment.id}

class PaymentUpdate(BaseModel):
    payment_status: PaymentStatus
    transaction_id: Optional[str] = None
    notes: Optional[str] = None

@api_router.put("/payments/{payment_id}")
async def update_payment(
    payment_id: str,
    payment_update: PaymentUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Update a payment's status."""
    update_data = payment_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    if payment_update.payment_status == PaymentStatus.PAID:
        update_data["payment_date"] = datetime.utcnow()

    result = await db.payments.update_one(
        {"id": payment_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"message": "Payment updated successfully"}

@api_router.post("/payments/{payment_id}/proof")
async def submit_payment_proof(
    payment_id: str,
    proof_data: PaymentProof,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Submit proof of payment for an offline transaction."""
    payment = await db.payments.find_one({"id": payment_id, "student_id": current_user["id"]})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found or you do not have permission to update it.")

    await db.payments.update_one(
        {"id": payment_id},
        {"$set": {"payment_proof": proof_data.proof, "updated_at": datetime.utcnow()}}
    )
    return {"message": "Payment proof submitted successfully."}

@api_router.get("/payments")
async def get_payments(
    student_id: Optional[str] = None,
    enrollment_id: Optional[str] = None,
    payment_status: Optional[PaymentStatus] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """Get payments with filtering"""
    filter_query = {}
    
    if student_id:
        filter_query["student_id"] = student_id
    if enrollment_id:
        filter_query["enrollment_id"] = enrollment_id
    if payment_status:
        filter_query["payment_status"] = payment_status.value
    
    # Role-based filtering
    if current_user["role"] == "student":
        filter_query["student_id"] = current_user["id"]
    
    payments = await db.payments.find(filter_query).skip(skip).limit(limit).to_list(length=limit)
    return {"payments": serialize_doc(payments)}

@api_router.get("/payments/dues")
async def get_outstanding_dues(
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get outstanding dues"""
    filter_query = {"payment_status": PaymentStatus.PENDING.value, "due_date": {"$lt": datetime.utcnow()}}
    
    if current_user["role"] == "student":
        filter_query["student_id"] = current_user["id"]
    
    overdue_payments = await db.payments.find(filter_query).to_list(length=1000)
    
    # Group by student
    dues_by_student = {}
    for payment in overdue_payments:
        student_id = payment["student_id"]
        if student_id not in dues_by_student:
            dues_by_student[student_id] = {"total_amount": 0, "payments": []}
        dues_by_student[student_id]["total_amount"] += payment["amount"]
        dues_by_student[student_id]["payments"].append(payment)
    
    return {"outstanding_dues": serialize_doc(dues_by_student)}

# PRODUCTS/ACCESSORIES MANAGEMENT
@api_router.post("/products")
async def create_product(
    product_data: ProductCreate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Create product"""
    product = Product(**product_data.dict())
    await db.products.insert_one(product.dict())
    return {"message": "Product created successfully", "product_id": product.id}

@api_router.get("/products")
async def get_products(
    branch_id: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get products catalog"""
    filter_query = {"is_active": True}
    
    if category:
        filter_query["category"] = category
    
    products = await db.products.find(filter_query).to_list(length=1000)
    
    # Filter by branch availability if specified
    if branch_id:
        products = [p for p in products if branch_id in p.get("branch_availability", {})]
    
    return {"products": serialize_doc(products)}

@api_router.put("/products/{product_id}")
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Update product details (Super Admin only)"""
    update_data = {k: v for k, v in product_update.dict(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")

    update_data["updated_at"] = datetime.utcnow()

    result = await db.products.update_one(
        {"id": product_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product updated successfully"}

@api_router.get("/products/purchases")
async def get_product_purchases(
    student_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """Get product purchases with filtering"""
    filter_query = {}
    if student_id:
        filter_query["student_id"] = student_id
    if branch_id:
        filter_query["branch_id"] = branch_id

    if current_user["role"] == UserRole.STUDENT:
        filter_query["student_id"] = current_user["id"]
    elif current_user["role"] == UserRole.COACH_ADMIN:
        filter_query["branch_id"] = current_user.get("branch_id")

    purchases = await db.product_purchases.find(filter_query).skip(skip).limit(limit).to_list(length=limit)
    return {"purchases": serialize_doc(purchases)}

@api_router.post("/products/purchase")
async def purchase_product(
    purchase_data: ProductPurchaseCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """Record offline product purchase"""
    # Validate product and stock
    product = await db.products.find_one({"id": purchase_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    branch_stock = product.get("branch_availability", {}).get(purchase_data.branch_id, 0)
    if branch_stock < purchase_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    # Create purchase record
    purchase = ProductPurchase(
        **purchase_data.dict(),
        unit_price=product["price"],
        total_amount=product["price"] * purchase_data.quantity
    )
    
    await db.product_purchases.insert_one(purchase.dict())
    
    # Update stock
    new_stock = branch_stock - purchase_data.quantity
    await db.products.update_one(
        {"id": purchase_data.product_id},
        {"$set": {f"branch_availability.{purchase_data.branch_id}": new_stock}}
    )
    
    return {"message": "Purchase recorded successfully", "purchase_id": purchase.id, "total_amount": purchase.total_amount}

class StudentProductPurchaseCreate(BaseModel):
    product_id: str
    quantity: int
    payment_method: str # e.g., "online", "upi", "card"

@api_router.post("/students/products/purchase", status_code=status.HTTP_201_CREATED)
async def student_purchase_product(
    purchase_data: StudentProductPurchaseCreate,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Allow a student to purchase a product online."""
    student_id = current_user["id"]
    branch_id = current_user.get("branch_id")

    if not branch_id:
        raise HTTPException(status_code=400, detail="Student is not assigned to a branch.")

    # Validate product and stock
    product = await db.products.find_one({"id": purchase_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    branch_stock = product.get("branch_availability", {}).get(branch_id, 0)
    if branch_stock < purchase_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock at your branch.")

    # Calculate total amount
    unit_price = product["price"]
    total_amount = unit_price * purchase_data.quantity

    # Create ProductPurchase record
    purchase = ProductPurchase(
        student_id=student_id,
        product_id=purchase_data.product_id,
        branch_id=branch_id,
        quantity=purchase_data.quantity,
        unit_price=unit_price,
        total_amount=total_amount,
        payment_method=purchase_data.payment_method,
        purchase_date=datetime.utcnow()
    )
    await db.product_purchases.insert_one(purchase.dict())

    # Update stock
    new_stock = branch_stock - purchase_data.quantity
    await db.products.update_one(
        {"id": purchase_data.product_id},
        {"$set": {f"branch_availability.{branch_id}": new_stock}}
    )

    # Create Payment record for the purchase
    payment = Payment(
        student_id=student_id,
        enrollment_id="", # No enrollment for product purchases
        amount=total_amount,
        payment_type="accessory_purchase",
        payment_method=purchase_data.payment_method,
        payment_status=PaymentStatus.PAID, # Assuming online payment is immediately paid
        transaction_id=str(uuid.uuid4()), # Generate a dummy transaction ID
        due_date=datetime.utcnow(),
        notes=f"Online purchase of {purchase_data.quantity} x {product['name']}"
    )
    await db.payments.insert_one(payment.dict())

    # Send confirmation
    await send_whatsapp(current_user["phone"], f"Thank you for your purchase of {purchase_data.quantity} x {product['name']} for ₹{total_amount}. Your order is confirmed!")

    return {"message": "Product purchased successfully", "purchase_id": purchase.id, "total_amount": total_amount}

# COMPLAINTS & FEEDBACK SYSTEM
@api_router.post("/complaints")
async def create_complaint(
    complaint_data: ComplaintCreate,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Submit complaint (Students only)"""
    complaint = Complaint(
        **complaint_data.dict(),
        student_id=current_user["id"],
        branch_id=current_user.get("branch_id") or ""
    )
    
    await db.complaints.insert_one(complaint.dict())
    
    # Notify admins
    admins = await db.users.find({"role": {"$in": ["super_admin", "coach_admin"]}}).to_list(length=100)
    for admin in admins:
        message = f"New complaint from {current_user['full_name']}: {complaint.subject}"
        await send_whatsapp(admin["phone"], message)
    
    return {"message": "Complaint submitted successfully", "complaint_id": complaint.id}

@api_router.get("/complaints")
async def get_complaints(
    status: Optional[ComplaintStatus] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get complaints"""
    filter_query = {}
    
    if status:
        filter_query["status"] = status.value
    if category:
        filter_query["category"] = category
    
    # Role-based filtering
    if current_user["role"] == "student":
        filter_query["student_id"] = current_user["id"]
    
    complaints = await db.complaints.find(filter_query).to_list(length=1000)
    return {"complaints": serialize_doc(complaints)}

@api_router.put("/complaints/{complaint_id}")
async def update_complaint(
    complaint_id: str,
    complaint_update: ComplaintUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Update complaint status"""
    update_data = {k: v for k, v in complaint_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.complaints.update_one(
        {"id": complaint_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    return {"message": "Complaint updated successfully"}

@api_router.post("/feedback/coaches")
async def rate_coach(
    rating_data: CoachRatingCreate,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Rate and review coach"""
    if rating_data.rating < 1 or rating_data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    rating = CoachRating(
        **rating_data.dict(),
        student_id=current_user["id"],
        branch_id=current_user.get("branch_id", "")
    )
    
    await db.coach_ratings.insert_one(rating.dict())
    return {"message": "Rating submitted successfully", "rating_id": rating.id}

@api_router.get("/coaches/{coach_id}/ratings")
async def get_coach_ratings(
    coach_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get all ratings for a specific coach."""
    ratings = await db.coach_ratings.find({"coach_id": coach_id}).to_list(1000)
    return {"ratings": serialize_doc(ratings)}

# SESSION BOOKING SYSTEM
@api_router.post("/sessions/book")
async def book_session(
    booking_data: SessionBookingCreate,
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Book individual session"""
    # Validate coach availability (simplified)
    existing_booking = await db.session_bookings.find_one({
        "coach_id": booking_data.coach_id,
        "session_date": booking_data.session_date,
        "status": {"$ne": SessionStatus.CANCELLED.value}
    })
    
    if existing_booking:
        raise HTTPException(status_code=400, detail="Coach not available at this time")
    
    booking = SessionBooking(
        **booking_data.dict(),
        student_id=current_user["id"]
    )
    
    await db.session_bookings.insert_one(booking.dict())
    
    # Create payment record
    payment = Payment(
        student_id=current_user["id"],
        enrollment_id="",  # No enrollment for individual sessions
        amount=booking.fee,
        payment_type="session_fee",
        payment_method="pending",
        payment_status=PaymentStatus.PENDING,
        due_date=booking.session_date
    )
    await db.payments.insert_one(payment.dict())
    
    return {"message": "Session booked successfully", "booking_id": booking.id, "fee": booking.fee}

@api_router.get("/sessions/my-bookings")
async def get_my_bookings(
    current_user: dict = Depends(require_role([UserRole.STUDENT]))
):
    """Get student's session bookings"""
    bookings = await db.session_bookings.find({"student_id": current_user["id"]}).to_list(length=1000)
    return {"bookings": serialize_doc(bookings)}

# REPORTING & ANALYTICS ENDPOINTS
@api_router.get("/reports/dashboard")
async def get_dashboard_stats(
    branch_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """Get dashboard statistics"""
    stats = {}
    
    # Filter by role and branch
    filter_query = {}
    if current_user["role"] == "coach_admin" and current_user.get("branch_id"):
        filter_query["branch_id"] = current_user["branch_id"]
    elif branch_id:
        filter_query["branch_id"] = branch_id
    
    # Total students
    student_count = await db.users.count_documents({"role": "student", "is_active": True})
    stats["total_students"] = student_count
    
    # Active enrollments
    enrollment_count = await db.enrollments.count_documents({**filter_query, "is_active": True})
    stats["active_enrollments"] = enrollment_count
    
    # Pending payments
    pending_payments = await db.payments.count_documents({"payment_status": PaymentStatus.PENDING.value})
    stats["pending_payments"] = pending_payments
    
    # Overdue payments
    overdue_count = await db.payments.count_documents({
        "payment_status": PaymentStatus.PENDING.value,
        "due_date": {"$lt": datetime.utcnow()}
    })
    stats["overdue_payments"] = overdue_count
    
    # Today's attendance
    today = datetime.utcnow().date()
    today_attendance = await db.attendance.count_documents({
        "attendance_date": {
            "$gte": datetime.combine(today, datetime.min.time()),
            "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
        }
    })
    stats["today_attendance"] = today_attendance
    
    return {"dashboard_stats": stats}

@api_router.get("/reports/financial")
async def get_financial_report(
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Get a financial report summary."""
    total_collected = await db.payments.aggregate([
        {"$match": {"payment_status": PaymentStatus.PAID.value}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)

    pending_payments_cursor = db.payments.find({"payment_status": PaymentStatus.PENDING.value})
    pending_payments = await pending_payments_cursor.to_list(length=1000)
    print("Pending payments being aggregated:", pending_payments)

    outstanding_dues = await db.payments.aggregate([
        {"$match": {"payment_status": PaymentStatus.PENDING.value}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]).to_list(1)

    report = {
        "total_collected": total_collected[0]["total"] if total_collected else 0,
        "outstanding_dues": outstanding_dues[0]["total"] if outstanding_dues else 0,
        "report_generated_at": datetime.utcnow()
    }
    return report

@api_router.get("/reports/branch/{branch_id}")
async def get_branch_report(
    branch_id: str,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN, UserRole.COACH_ADMIN]))
):
    """Get a detailed report for a specific branch."""
    if current_user["role"] == UserRole.COACH_ADMIN and current_user.get("branch_id") != branch_id:
        raise HTTPException(status_code=403, detail="You can only access reports for your own branch.")

    branch = await db.branches.find_one({"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Aggregate data for the report
    total_students = await db.users.count_documents({"role": "student", "branch_id": branch_id, "is_active": True})
    active_enrollments = await db.enrollments.count_documents({"branch_id": branch_id, "is_active": True})

    payments_summary = await db.payments.aggregate([
        {"$match": {"student_id": {"$in": [user["id"] for user in await db.users.find({"branch_id": branch_id}).to_list(1000)]}}},
        {"$group": {
            "_id": "$payment_status",
            "total_amount": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }}
    ]).to_list(1000)

    report = {
        "branch_details": serialize_doc(branch),
        "total_students": total_students,
        "active_enrollments": active_enrollments,
        "payments_summary": payments_summary,
        "report_generated_at": datetime.utcnow()
    }
    return report

# Add middleware and startup
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Include API routes
app.include_router(api_router)

# Health check endpoint
@app.get("/")
async def health_check():
    return {"status": "OK", "message": "Student Management System API", "version": "1.0.0"}

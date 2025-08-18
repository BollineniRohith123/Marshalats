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

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'student_management_db')]

# Create FastAPI app
app = FastAPI(title="Student Management System", version="1.0.0")
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
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_active", False):
        raise HTTPException(status_code=400, detail="Inactive user")
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
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Create new user (Super Admin only)"""
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
    
    return {"users": users, "total": len(users)}

@api_router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(require_role([UserRole.SUPER_ADMIN]))
):
    """Update user (Super Admin only)"""
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User updated successfully"}

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
    return {"branches": branches}

@api_router.get("/branches/{branch_id}")
async def get_branch(
    branch_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """Get branch by ID"""
    branch = await db.branches.find_one({"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch

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
    
    return {"courses": courses}

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

# Continue in next part due to length...
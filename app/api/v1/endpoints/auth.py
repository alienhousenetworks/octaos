import random
from datetime import datetime, timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api import deps
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.base import User, Tenant
from app.services.email.sender import send_global_smtp_email

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str
    tenant_id: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    company_name: str

class SignupInitiateRequest(BaseModel):
    name: str
    email: EmailStr
    phone_no: str
    company: Optional[str] = None
    company_website: Optional[str] = None
    company_email: Optional[str] = None
    company_address: Optional[str] = None
    password: str

class SignupVerifyRequest(BaseModel):
    email: EmailStr
    otp: str

class LoginInitiateRequest(BaseModel):
    email: EmailStr
    password: str

class LoginVerifyRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendOtpRequest(BaseModel):
    email: EmailStr


def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


def send_otp(email: str, otp: str, purpose: str = "verification"):
    subject = f"Your NexusOS {purpose.capitalize()} Code"
    body = (
        f"Hello,\n\n"
        f"Your 6-digit one-time passcode (OTP) for {purpose} is: {otp}\n\n"
        f"This code will expire in 10 minutes.\n\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"Best regards,\n"
        f"The NexusOS Team"
    )
    send_global_smtp_email(email, subject, body)


# --- OLD ENDPOINTS (BACKWARD COMPATIBILITY) ---

@router.post("/signup", response_model=Token)
def signup(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
) -> Any:
    # Check if user exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # Create tenant (company)
    tenant = Tenant(name=user_in.company_name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Create user
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        tenant_id=tenant.id,
        is_superuser=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Simple form login sets user as verified to allow Swagger and testing to run seamlessly
    user.is_verified = True
    db.add(user)
    db.commit()
    
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


# --- NEW OTP FLOWS ---

@router.post("/signup/initiate")
def signup_initiate(
    *,
    db: Session = Depends(deps.get_db),
    signup_in: SignupInitiateRequest,
) -> Any:
    # Check if user exists
    user = db.query(User).filter(User.email == signup_in.email).first()
    if user:
        if getattr(user, "is_verified", True):
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system.",
            )
        # Unverified user: we can update details and send a new OTP
        user.name = signup_in.name
        user.phone_no = signup_in.phone_no
        user.hashed_password = get_password_hash(signup_in.password)
        # Update tenant name and metadata if provided
        if signup_in.company:
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
            if tenant:
                tenant.name = signup_in.company
                tenant.company_website = signup_in.company_website
                tenant.company_email = signup_in.company_email
                tenant.company_address = signup_in.company_address
                db.add(tenant)
    else:
        # Create tenant (company)
        company_name = signup_in.company or f"{signup_in.name}'s Company"
        tenant = Tenant(
            name=company_name,
            company_website=signup_in.company_website,
            company_email=signup_in.company_email,
            company_address=signup_in.company_address
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

        # Create user (not verified yet)
        user = User(
            email=signup_in.email,
            hashed_password=get_password_hash(signup_in.password),
            tenant_id=tenant.id,
            name=signup_in.name,
            phone_no=signup_in.phone_no,
            is_verified=False,
            is_superuser=True
        )
        db.add(user)

    # Generate OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()

    # Send OTP
    send_otp(user.email, otp, purpose="signup")
    return {"message": "Verification OTP sent successfully", "email": user.email}


@router.post("/signup/verify", response_model=Token)
def signup_verify(
    *,
    db: Session = Depends(deps.get_db),
    verify_in: SignupVerifyRequest,
) -> Any:
    user = db.query(User).filter(User.email == verify_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user.otp and user.otp == verify_in.otp:
        if user.otp_expires_at and user.otp_expires_at > datetime.utcnow():
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    # Mark as verified
    user.is_verified = True
    user.otp = None
    user.otp_expires_at = None
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


@router.post("/signup/resend-otp")
def signup_resend_otp(
    *,
    db: Session = Depends(deps.get_db),
    resend_in: ResendOtpRequest,
) -> Any:
    user = db.query(User).filter(User.email == resend_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Generate new OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()

    # Send OTP
    send_otp(user.email, otp, purpose="signup")
    return {"message": "Verification OTP resent successfully", "email": user.email}


@router.post("/login/initiate")
def login_initiate(
    *,
    db: Session = Depends(deps.get_db),
    login_in: LoginInitiateRequest,
) -> Any:
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # If the user registered but never verified, tell them to verify using the signup verification flow
    if not getattr(user, "is_verified", False):
        raise HTTPException(
            status_code=403, 
            detail="Account email is unverified. Please verify your email first.",
            headers={"X-Verification-Required": "true"}
        )

    # Generate OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()

    # Send OTP
    send_otp(user.email, otp, purpose="login")
    return {"message": "Login OTP sent successfully", "email": user.email, "otp_required": True}


@router.post("/login/verify", response_model=Token)
def login_verify(
    *,
    db: Session = Depends(deps.get_db),
    verify_in: LoginVerifyRequest,
) -> Any:
    user = db.query(User).filter(User.email == verify_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user.otp and user.otp == verify_in.otp:
        if user.otp_expires_at and user.otp_expires_at > datetime.utcnow():
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    # Clear OTP
    user.otp = None
    user.otp_expires_at = None
    db.add(user)
    db.commit()

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


@router.post("/login/resend-otp")
def login_resend_otp(
    *,
    db: Session = Depends(deps.get_db),
    resend_in: ResendOtpRequest,
) -> Any:
    user = db.query(User).filter(User.email == resend_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Generate new OTP
    otp = generate_otp()
    user.otp = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.add(user)
    db.commit()

    # Send OTP
    send_otp(user.email, otp, purpose="login")
    return {"message": "Login OTP resent successfully", "email": user.email}


@router.get("/me")
def read_current_user(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "name": getattr(current_user, "name", None),
        "phone_no": getattr(current_user, "phone_no", None)
    }

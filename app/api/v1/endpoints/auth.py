
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.rate_limiter import rate_limit_endpoint
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api import deps
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.base import User, Tenant, Invitation
from app.services.email.sender import send_global_smtp_email

router = APIRouter()

def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


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
    password: Optional[str] = None
    tenant_id: Optional[str] = None

class LoginVerifyRequest(BaseModel):
    email: EmailStr
    otp: str
    tenant_id: Optional[str] = None

class ResendOtpRequest(BaseModel):
    email: EmailStr
def generate_otp():
    return f"{secrets.randbelow(900000) + 100000}"


def send_otp(email: str, otp: str, purpose: str = "verification"):
    subject = f"Your OctaOS {purpose.capitalize()} Code"
    body = (
        f"Hello,\n\n"
        f"Your 6-digit one-time passcode (OTP) for {purpose} is: {otp}\n\n"
        f"This code will expire in 10 minutes.\n\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"Best regards,\n"
        f"The OctaOS Team"
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
        is_verified=True,
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit_endpoint(limit=5, window_seconds=60))])
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
    
    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


# --- NEW OTP FLOWS ---

@router.post("/signup/initiate")
def signup_initiate(
    *,
    db: Session = Depends(deps.get_db),
    signup_in: SignupInitiateRequest,
) -> Any:
    if not signup_in.company_email:
        raise HTTPException(status_code=400, detail="Company email is required.")
        
    tenant = db.query(Tenant).filter(Tenant.company_email == signup_in.company_email).first()
    
    if tenant:
        # Check if the admin user is verified
        admin_user = db.query(User).filter(User.tenant_id == tenant.id, User.email == signup_in.email).first()
        if admin_user and getattr(admin_user, "is_verified", False):
            raise HTTPException(status_code=400, detail="A company with this email already exists and is verified.")
        elif not admin_user:
            raise HTTPException(status_code=400, detail="A company with this email already exists.")
            
        # Unverified user retrying: update details
        admin_user.name = signup_in.name
        admin_user.phone_no = signup_in.phone_no
        admin_user.hashed_password = get_password_hash(signup_in.password)
        tenant.name = signup_in.company or f"{signup_in.name}'s Company"
        tenant.company_website = signup_in.company_website
        tenant.company_address = signup_in.company_address
        db.add(tenant)
        user = admin_user
    else:
        # Create new tenant
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
            is_superuser=True,
            role="admin"
        )
        db.add(user)
        
        # Sync password for other existing user accounts with same email
        existing_users = db.query(User).filter(User.email == signup_in.email).all()
        for eu in existing_users:
            eu.hashed_password = user.hashed_password
            db.add(eu)

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
    users = db.query(User).filter(User.email == verify_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user = users[0]
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user.otp and user.otp == verify_in.otp:
        if user.otp_expires_at and _normalize_dt(user.otp_expires_at) > _normalize_dt(datetime.utcnow()):
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    # Mark as verified
    for u in users:
        u.is_verified = True
        u.otp = None
        u.otp_expires_at = None
        db.add(u)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


@router.post("/signup/resend-otp")
def signup_resend_otp(
    *,
    db: Session = Depends(deps.get_db),
    resend_in: ResendOtpRequest,
) -> Any:
    users = db.query(User).filter(User.email == resend_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user = users[0]
    if getattr(user, "is_verified", False):
        raise HTTPException(status_code=400, detail="User is already verified.")

    # Generate new OTP
    otp = generate_otp()
    for u in users:
        u.otp = otp
        u.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.add(u)
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
    users = db.query(User).filter(User.email == login_in.email).all()
    if not users:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    user = None
    if login_in.tenant_id:
        user = next((u for u in users if u.tenant_id == login_in.tenant_id), None)
        if not user:
            raise HTTPException(status_code=400, detail="Invalid tenant selection")
    else:
        if len(users) == 1:
            user = users[0]

    if login_in.password is not None and login_in.password != "":
        # PASSWORD LOGIN FLOW
        if not verify_password(login_in.password, users[0].hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        if user is None:
            tenants = []
            for u in users:
                t = db.query(Tenant).filter(Tenant.id == u.tenant_id).first()
                if t and t.is_active:
                    tenants.append({"id": t.id, "name": t.name})
            if not tenants:
                 raise HTTPException(status_code=400, detail="No active tenants found for user")
            if len(tenants) == 1:
                 user = next(u for u in users if u.tenant_id == tenants[0]["id"])
            else:
                 return {
                     "needs_tenant_selection": True,
                     "tenants": tenants,
                     "otp_required": False
                 }

        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        if not getattr(user, "is_verified", False):
            raise HTTPException(
                status_code=403, 
                detail="Account email is unverified. Please verify your email first.",
                headers={"X-Verification-Required": "true"}
            )
            
        access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "tenant_id": user.tenant_id,
            "otp_required": False
        }
    else:
        # OTP LOGIN FLOW
        otp = generate_otp()
        for u in users:
            u.otp = otp
            u.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
            db.add(u)
        db.commit()

        send_otp(login_in.email, otp, purpose="login")
        return {"message": "Login OTP sent successfully", "email": login_in.email, "otp_required": True}


@router.post("/login/verify", response_model=Token)
def login_verify(
    *,
    db: Session = Depends(deps.get_db),
    verify_in: LoginVerifyRequest,
) -> Any:
    users = db.query(User).filter(User.email == verify_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")

    user_for_otp = users[0]
    
    # Verification logic
    is_valid = False
    if settings.DEV and verify_in.otp == "123455":
        is_valid = True
    elif user_for_otp.otp and user_for_otp.otp == verify_in.otp:
        if user_for_otp.otp_expires_at and _normalize_dt(user_for_otp.otp_expires_at) > _normalize_dt(datetime.utcnow()):
            is_valid = True
        else:
            raise HTTPException(status_code=400, detail="OTP has expired.")
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP code.")

    if not is_valid:
        raise HTTPException(status_code=400, detail="OTP verification failed.")

    user = None
    if verify_in.tenant_id:
        user = next((u for u in users if u.tenant_id == verify_in.tenant_id), None)
        if not user:
             raise HTTPException(status_code=400, detail="Invalid tenant selection")
    else:
        if len(users) == 1:
            user = users[0]

    if user is None:
        tenants = []
        for u in users:
            t = db.query(Tenant).filter(Tenant.id == u.tenant_id).first()
            if t and t.is_active:
                tenants.append({"id": t.id, "name": t.name})
        if not tenants:
             raise HTTPException(status_code=400, detail="No active tenants found for user")
        if len(tenants) == 1:
             user = next(u for u in users if u.tenant_id == tenants[0]["id"])
        else:
             return {
                 "needs_tenant_selection": True,
                 "tenants": tenants
             }

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Clear OTP
    for u in users:
        u.otp = None
        u.otp_expires_at = None
        db.add(u)
    db.commit()

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


@router.post("/login/resend-otp")
def login_resend_otp(
    *,
    db: Session = Depends(deps.get_db),
    resend_in: ResendOtpRequest,
) -> Any:
    users = db.query(User).filter(User.email == resend_in.email).all()
    if not users:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if not users[0].is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Generate new OTP
    otp = generate_otp()
    for u in users:
        u.otp = otp
        u.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.add(u)
    db.commit()

    # Send OTP
    send_otp(users[0].email, otp, purpose="login")
    return {"message": "Login OTP resent successfully", "email": user.email}


@router.get("/me")
def read_current_user(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "tenant_name": tenant.name if tenant else None,
        "company_website": tenant.company_website if tenant else None,
        "company_email": tenant.company_email if tenant else None,
        "company_address": tenant.company_address if tenant else None,
        "name": getattr(current_user, "name", None),
        "phone_no": getattr(current_user, "phone_no", None),
        "role": getattr(current_user, "role", "member"),
        "allowed_sections": getattr(current_user, "allowed_sections", None),
        "is_system_admin": getattr(current_user, "is_system_admin", False),
        "is_verified": getattr(current_user, "is_verified", False),
    }


class SwitchTenantRequest(BaseModel):
    tenant_id: str


@router.get("/my-organizations")
def list_my_organizations(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Return all organizations (tenants) associated with the current user's email."""
    users = db.query(User).filter(User.email == current_user.email).all()
    result = []
    for u in users:
        tenant = db.query(Tenant).filter(Tenant.id == u.tenant_id).first()
        if tenant and tenant.is_active:
            result.append({
                "tenant_id": u.tenant_id,
                "tenant_name": tenant.name,
                "company_email": tenant.company_email,
                "company_website": tenant.company_website,
                "role": u.role,
                "is_current": u.tenant_id == current_user.tenant_id,
            })
    return result


@router.post("/switch-tenant")
def switch_tenant(
    switch_in: SwitchTenantRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Switch the active organization for the current user's email."""
    user = db.query(User).filter(
        User.email == current_user.email,
        User.tenant_id == switch_in.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Organization not found for this account")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="This organization account is inactive")
    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, organization_id=user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}

class InviteCreate(BaseModel):
    email: Optional[EmailStr] = None

class InviteAccept(BaseModel):
    token: str
    name: str
    email: EmailStr
    password: str

class MemberPermissionsUpdate(BaseModel):
    role: Optional[str] = None
    allowed_sections: Optional[List[str]] = None

@router.post("/invite")
def create_invite(
    invite_in: InviteCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    token = secrets.token_urlsafe(32)
    # Expires in 7 days
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation = Invitation(
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
        email=invite_in.email,
        token=token,
        is_used=False,
        expires_at=expires_at
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return {
        "token": token,
        "expires_at": expires_at,
        "invite_url": f"/?token={token}"
    }

@router.get("/invite/verify")
def verify_invite(
    token: str,
    db: Session = Depends(deps.get_db)
):
    invitation = db.query(Invitation).filter(
        Invitation.token == token,
        Invitation.is_used == False
    ).first()
    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid or already used invitation token")
    if _normalize_dt(invitation.expires_at) < _normalize_dt(datetime.utcnow()):
        raise HTTPException(status_code=400, detail="Invitation token has expired")
    
    tenant = db.query(Tenant).filter(Tenant.id == invitation.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {
        "token": invitation.token,
        "company_name": tenant.name,
        "email": invitation.email
    }

@router.post("/invite/accept", response_model=Token)
def accept_invite(
    accept_in: InviteAccept,
    db: Session = Depends(deps.get_db)
):
    invitation = db.query(Invitation).filter(
        Invitation.token == accept_in.token,
        Invitation.is_used == False
    ).first()
    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid or already used invitation token")
    if _normalize_dt(invitation.expires_at) < _normalize_dt(datetime.utcnow()):
        raise HTTPException(status_code=400, detail="Invitation token has expired")
    
    # Check if user already exists in THIS tenant
    existing_user_in_tenant = db.query(User).filter(User.email == accept_in.email, User.tenant_id == invitation.tenant_id).first()
    if existing_user_in_tenant:
        raise HTTPException(status_code=400, detail="User with this email already exists in this organization")
        
    # Sync passwords for existing accounts with this email
    existing_users = db.query(User).filter(User.email == accept_in.email).all()
    hashed_pw = get_password_hash(accept_in.password)
    for eu in existing_users:
        eu.hashed_password = hashed_pw
        db.add(eu)
    
    # Create new user associated with the tenant
    new_user = User(
        email=accept_in.email,
        hashed_password=get_password_hash(accept_in.password),
        tenant_id=invitation.tenant_id,
        name=accept_in.name,
        role="member",
        is_active=True,
        is_verified=True,
        is_superuser=False,
        allowed_sections=None
    )
    db.add(new_user)
    
    # Mark token as used
    invitation.is_used = True
    db.add(invitation)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(subject=new_user.id, tenant_id=new_user.tenant_id, organization_id=new_user.organization_id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": new_user.tenant_id}

@router.get("/members")
def list_members(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "admin" and not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Only admins can manage members")
    
    users = db.query(User).filter(User.tenant_id == current_user.tenant_id).all()
    return [{
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "allowed_sections": u.allowed_sections,
        "is_active": u.is_active,
        "is_verified": u.is_verified
    } for u in users]

@router.put("/members/{user_id}/permissions")
def update_member_permissions(
    user_id: str,
    permissions_in: MemberPermissionsUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "admin" and not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Only admins can manage members")
    
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")
        
    if permissions_in.role is not None:
        if permissions_in.role not in ["admin", "member"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = permissions_in.role
        
    if permissions_in.allowed_sections is not None:
        user.allowed_sections = permissions_in.allowed_sections
        
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "role": user.role,
        "allowed_sections": user.allowed_sections
    }

@router.delete("/members/{user_id}")
def delete_member(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    if current_user.role != "admin" and not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Only admins can manage members")
        
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == current_user.tenant_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Member not found")
        
    db.delete(user)
    db.commit()
    return {"message": "Member removed successfully"}


@router.get("/settings")
def get_public_settings(db: Session = Depends(deps.get_db)):
    """Public endpoint to fetch site branding settings (logo, favicon)."""
    from app.models.base import SystemSetting
    settings_rows = db.query(SystemSetting).filter(
        SystemSetting.key.in_(["logo_url", "favicon_url"])
    ).all()
    result = {row.key: row.value for row in settings_rows}
    return {
        "logo_url": result.get("logo_url"),
        "favicon_url": result.get("favicon_url"),
    }

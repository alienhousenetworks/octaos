from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions.rbac import Action, Resource, require_permission
from app.core.security.audit import record_audit
from app.core.security.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.tenancy.models import AuditLog, Tenant, User
from app.db import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=200)
    subdomain: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str
    subdomain: str | None = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    slug = payload.subdomain.strip().lower()
    if db.query(Tenant).filter(Tenant.subdomain == slug).first():
        raise HTTPException(status_code=400, detail="Subdomain already registered.")

    tenant = Tenant(name=payload.tenant_name.strip(), subdomain=slug)
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.email.strip().lower(),
        hashed_password=hash_password(payload.password),
        name=payload.name or payload.email.split("@")[0],
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    record_audit(
        db,
        tenant_id=tenant.id,
        user_id=user.id,
        action="register",
        resource="tenant",
        resource_id=tenant.id,
    )
    token = create_access_token(user.id, tenant.id, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role},
        "tenant": {"id": tenant.id, "name": tenant.name, "subdomain": tenant.subdomain},
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    q = db.query(User).filter(User.email == payload.email.strip().lower(), User.is_active.is_(True))
    if payload.subdomain:
        tenant = db.query(Tenant).filter(Tenant.subdomain == payload.subdomain.strip().lower()).first()
        if not tenant:
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        q = q.filter(User.tenant_id == tenant.id)

    user = q.first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token = create_access_token(user.id, user.tenant_id, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role, "tenant_id": user.tenant_id},
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "tenant_id": current_user.tenant_id,
    }


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = 50,
    current_user: User = Depends(require_permission(Resource.AUDIT_LOGS, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == current_user.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "action": r.action,
            "resource": r.resource,
            "resource_id": r.resource_id,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api import deps
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.base import User, Tenant

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str
    tenant_id: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    company_name: str

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
        is_superuser=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    # We embed the tenant_id in the sub (or a custom claim). Here we'll put the user.id in sub and tenant.id in a claim, but for simplicity let's just use user.id and we can fetch the user in deps.
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
    
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer", "tenant_id": user.tenant_id}


@router.get("/me")
def read_current_user(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id
    }


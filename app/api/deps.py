from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.base import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        token_data = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = db.query(User).filter(User.id == token_data).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Check if tenant is active
    if user.tenant and not user.tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant organization is suspended"
        )
        
    if not getattr(user, "is_verified", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unverified user. Please complete OTP verification.")
    return user

def get_current_tenant_id(current_user: User = Depends(get_current_user)) -> str:
    return current_user.tenant_id

def check_access(vertical: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_system_admin:
            return current_user
        if current_user.role == "admin":
            return current_user
        allowed = current_user.allowed_sections
        if allowed is None:
            return current_user
        if "all" in allowed:
            return current_user
        if vertical in allowed:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to section: {vertical}"
        )
    return dependency

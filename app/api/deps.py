from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.base import User, tenant_context, org_context

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

_API_KEY_WRITE_ROLES = {"admin", "super_admin", "standard_operator", "manager", "agent"}


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
        token_type = payload.get("type", "access")
        if token_type not in ("access", None):
            # Reject refresh tokens used as access tokens
            if token_type == "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        token_data = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        org_id = payload.get("organization_id")
    except JWTError:
        # 401 so clients can attempt refresh / re-login (was 403 which looked like RBAC)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials — session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == token_data).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    if user.tenant and not user.tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant organization is suspended",
        )

    if not getattr(user, "is_verified", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unverified user. Please complete OTP verification.",
        )

    # Bind request tenant context to authenticated user (ignore spoofed headers)
    if tenant_id and tenant_id != user.tenant_id and not getattr(user, "is_system_admin", False):
        raise HTTPException(status_code=403, detail="Token tenant mismatch")
    tenant_context.set(user.tenant_id)
    if org_id or user.organization_id:
        org_context.set(org_id or user.organization_id)

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def get_current_tenant_id(current_user: User = Depends(get_current_user)) -> str:
    return current_user.tenant_id


def _api_key_can_write(credential) -> bool:
    if (getattr(credential, "role", None) or "").lower() in _API_KEY_WRITE_ROLES:
        return True
    for grant in getattr(credential, "grants", None) or []:
        actions = {str(action).lower() for action in (grant.allowed_actions or [])}
        if actions.intersection({"invoke", "update", "create", "*"}):
            return True
    return False


def _user_for_api_key(db: Session, credential) -> User:
    user = None
    if credential.user_id:
        user = (
            db.query(User)
            .filter(User.id == credential.user_id, User.tenant_id == credential.tenant_id)
            .first()
        )
    if user is None or not user.is_active:
        user = (
            db.query(User)
            .filter(User.tenant_id == credential.tenant_id, User.is_active.is_(True))
            .order_by(User.is_superuser.desc(), User.id.asc())
            .first()
        )
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is not linked to an active workspace user.")
    if user.tenant and not user.tenant.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant organization is suspended")
    tenant_context.set(user.tenant_id)
    if user.organization_id:
        org_context.set(user.organization_id)
    return user


def get_current_user_or_api_key(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme_optional),
    x_octaos_key: Optional[str] = Header(None, alias="X-OctaOS-Key"),
) -> User:
    """Accept a dashboard JWT or an active OctaOS API key (octa_mcp_...)."""
    raw = (token or "").strip() or (x_octaos_key or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if raw.startswith("octa_mcp_"):
        from app.services.mcp.auth.credentials import authenticate_mcp_key

        credential = authenticate_mcp_key(db, raw)
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or deactivated API key.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = _user_for_api_key(db, credential)
        # Kept on the user for this request. A context var does not survive
        # every dependency boundary in the test client or under threaded workers.
        user._octaos_api_key_write = _api_key_can_write(credential)
        return user
    user = get_current_user(db=db, token=raw)
    user._octaos_api_key_write = None
    return user


def get_current_tenant_id_or_api_key(current_user: User = Depends(get_current_user_or_api_key)) -> str:
    return current_user.tenant_id


def require_api_key_write(current_user: User = Depends(get_current_user_or_api_key)) -> User:
    """Block read-only API keys from outreach and mail writes. Dashboard sessions pass.

    Depends on API-key resolution so the grant is set in this request before the check.
    """
    write = getattr(current_user, "_octaos_api_key_write", None)
    if write is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This API key is read-only. Outreach and mail need an operator or admin API key.",
        )
    return current_user


def check_access(vertical: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_system_admin:
            return current_user
        if current_user.role in ("admin", "organization_admin"):
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
            detail=f"Access denied to section: {vertical}",
        )

    return dependency


def require_metrics_token(authorization: Optional[str] = Header(None)) -> None:
    """Protect /metrics in non-dev environments when METRICS_TOKEN is set."""
    if settings.DEV and not settings.METRICS_TOKEN:
        return
    if not settings.METRICS_TOKEN:
        if settings.ENVIRONMENT in ("production", "staging"):
            raise HTTPException(status_code=403, detail="Metrics disabled")
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Metrics token required")
    token = authorization.split(" ", 1)[1]
    if token != settings.METRICS_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid metrics token")

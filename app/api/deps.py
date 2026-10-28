from typing import Generator, Optional, List, Any
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.base import User, tenant_context, org_context

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
    # 1. MCP API Key Authentication (octa_mcp_...)
    if token and token.startswith("octa_mcp_"):
        from app.services.mcp.auth.credentials import authenticate_mcp_key
        cred = authenticate_mcp_key(db, token)
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired MCP API key.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        tenant_context.set(cred.tenant_id)
        if cred.user_id:
            user = db.query(User).filter(User.id == cred.user_id).first()
            if user:
                setattr(user, "mcp_credential", cred)
                return user
        # Proxy User representation for external AI agent credential
        agent_user = User(
            id=f"agent_{cred.id}",
            tenant_id=cred.tenant_id,
            email=f"{cred.name.lower().replace(' ', '_')}@agent.octaos.internal",
            role=cred.role if cred.role in ("admin", "super_admin") else "member",
            is_active=True,
        )
        setattr(agent_user, "is_verified", True)
        setattr(agent_user, "allowed_sections", ["all"])
        setattr(agent_user, "mcp_credential", cred)
        return agent_user

    # 2. Standard User JWT Session Authentication
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


class AuthPrincipal:
    """Unified identity representation for human user sessions and external AI credentials."""
    def __init__(
        self,
        tenant_id: str,
        user: Optional[User] = None,
        credential: Any = None,
    ):
        self.tenant_id = tenant_id
        self.user = user
        self.credential = credential

    @property
    def is_agent(self) -> bool:
        return self.credential is not None

    @property
    def name(self) -> str:
        return self.actor_name

    @property
    def actor_name(self) -> str:
        if self.credential:
            return self.credential.name
        if self.user:
            return getattr(self.user, "name", None) or self.user.email
        return "Unknown"


    @property
    def connection_name(self) -> Optional[str]:
        if self.credential:
            return self.credential.name
        return None

    @property
    def key_name(self) -> str:
        if self.credential:
            return self.credential.name
        return "session"

    def has_scope(self, scope: str) -> bool:
        # Dashboard admin / system admin bypass
        if self.user and getattr(self.user, "is_system_admin", False):
            return True
        if self.user and getattr(self.user, "role", None) in ("admin", "organization_admin"):
            return True

        # External MCP / Agent Credential grants
        if self.credential:
            role = getattr(self.credential, "role", None)
            if role in ("admin", "super_admin"):
                return True
            if scope == "dashboard:activity:write" and role in ("standard_operator", "agent", "controller"):
                return True
            grants = getattr(self.credential, "grants", []) or []
            for g in grants:
                actions = getattr(g, "allowed_actions", []) or []
                model = getattr(g, "model_name", None) or ""
                if "*" in actions or scope in actions:
                    return True
                if model in ("activity_event", "activity", "dashboard", "*") and ("create" in actions or "write" in actions or "*" in actions):
                    return True
                # Map broad categories, e.g. "create" on lead -> "write:leads"
                if "write" in scope and ("create" in actions or "update" in actions):
                    return True
                if "read" in scope and ("read" in actions or "query" in actions):
                    return True
            return False

        return True


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    """
    Unified authentication dependency accepting either:
    1. Human dashboard session (Bearer JWT or user cookie)
    2. External controller API Key (Bearer octa_mcp_... or X-OctaOS-Key header or ?api_key=...)
    """
    auth_header = request.headers.get("Authorization") or ""
    raw_token = ""
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:].strip()
    elif request.headers.get("X-OctaOS-Key"):
        raw_token = request.headers.get("X-OctaOS-Key", "").strip()
    elif "api_key" in request.query_params:
        raw_token = request.query_params["api_key"].strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token, session JWT, or API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. MCP API Key Authentication (octa_mcp_...)
    if raw_token.startswith("octa_mcp_"):
        from app.services.mcp.auth.credentials import authenticate_mcp_key
        cred = authenticate_mcp_key(db, raw_token)
        if not cred:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired MCP API key.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        tenant_context.set(cred.tenant_id)
        user = None
        if cred.user_id:
            user = db.query(User).filter(User.id == cred.user_id).first()
        return AuthPrincipal(tenant_id=cred.tenant_id, user=user, credential=cred)

    # 2. User JWT Session Authentication
    try:
        payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        tenant_context.set(user.tenant_id)
        return AuthPrincipal(tenant_id=user.tenant_id, user=user, credential=None)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials — session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_scopes(required_scopes: List[str]):
    """Enforces fine-grained permission scopes on routes."""
    def dependency(
        principal: AuthPrincipal = Depends(get_current_principal),
    ) -> AuthPrincipal:
        for scope in required_scopes:
            if not principal.has_scope(scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission Denied: Missing required scope '{scope}'",
                )
        return principal
    return dependency

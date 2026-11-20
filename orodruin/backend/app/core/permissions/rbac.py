from enum import Enum
from typing import Dict, List

from fastapi import Depends, HTTPException, status

from app.core.security.auth import get_current_user
from app.core.tenancy.models import User


class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"


class Resource(str, Enum):
    INTELLIGENCE = "intelligence"
    LEADS = "leads"
    USERS = "users"
    TICKETS = "tickets"
    CAMPAIGNS = "campaigns"
    PUBLISH = "publish"
    SETTINGS = "settings"
    INTEGRATIONS = "integrations"
    AUDIT_LOGS = "audit_logs"
    BILLING = "billing"
    HR = "hr"
    FINANCE = "finance"
    VIDEOS = "videos"
    WORKFLOWS = "workflows"
    AGENTS = "agents"
    LEARNING = "learning"


ROLE_PERMISSIONS: Dict[str, Dict[str, List[str]]] = {
    "super_admin": {"*": ["*"]},
    "admin": {r.value: ["create", "read", "update", "delete", "execute"] for r in Resource},
    "manager": {
        "intelligence": ["create", "read", "update", "execute"],
        "leads": ["create", "read", "update", "delete", "execute"],
        "users": ["read"],
        "tickets": ["create", "read", "update", "execute"],
        "campaigns": ["create", "read", "update", "execute"],
        "publish": ["create", "read", "update", "execute"],
        "settings": ["read", "update"],
        "integrations": ["read", "update"],
        "audit_logs": ["read"],
        "billing": ["read"],
        "hr": ["create", "read", "update", "execute"],
        "finance": ["read", "create", "update"],
        "videos": ["create", "read", "update", "execute"],
        "workflows": ["create", "read", "update", "execute"],
        "agents": ["create", "read", "update", "execute"],
        "learning": ["read", "update", "execute"],
    },
    "agent": {
        "intelligence": ["create", "read", "execute"],
        "leads": ["create", "read", "update"],
        "users": ["read"],
        "tickets": ["create", "read", "update"],
        "campaigns": ["create", "read", "update"],
        "hr": ["read", "create", "update"],
        "videos": ["read", "create"],
        "workflows": ["read", "execute"],
        "agents": ["read", "execute"],
        "learning": ["read"],
    },
    "read_only": {r.value: ["read"] for r in Resource},
}


def has_permission(user: User, resource: Resource, action: Action) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    role = (getattr(user, "role", None) or "read_only").lower()
    perms = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["read_only"])
    if "*" in perms and ("*" in perms["*"] or action.value in perms["*"]):
        return True
    allowed = perms.get(resource.value, [])
    return "*" in allowed or action.value in allowed


def require_permission(resource: Resource, action: Action):
    def _dep(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied for {action.value} on {resource.value}.",
            )
        return current_user

    return _dep

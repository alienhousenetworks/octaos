from enum import Enum
from typing import List, Dict, Set, Any
from fastapi import Depends, HTTPException, status
from app.api import deps
from app.models.base import User

class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"

class Resource(str, Enum):
    LEADS = "leads"
    USERS = "users"
    TICKETS = "tickets"
    CAMPAIGNS = "campaigns"
    SETTINGS = "settings"
    INTEGRATIONS = "integrations"
    AUDIT_LOGS = "audit_logs"
    MEETINGS = "meetings"

# Role permissions registry mapping resource to list of allowed actions
ROLE_PERMISSIONS: Dict[str, Dict[str, List[str]]] = {
    "super_admin": {
        "*": ["*"]
    },
    "organization_admin": {
        "leads": ["create", "read", "update", "delete"],
        "users": ["create", "read", "update", "delete"],
        "tickets": ["create", "read", "update", "delete"],
        "campaigns": ["create", "read", "update", "delete"],
        "settings": ["create", "read", "update", "delete"],
        "integrations": ["create", "read", "update", "delete"],
        "meetings": ["create", "read", "update", "delete"],
        "audit_logs": ["read"]
    },
    "manager": {
        "leads": ["create", "read", "update"],
        "users": ["read"],
        "tickets": ["create", "read", "update"],
        "campaigns": ["create", "read", "update", "execute"],
        "meetings": ["create", "read", "update"],
        "audit_logs": ["read"]
    },
    "employee": {
        "leads": ["create", "read", "update"],
        "tickets": ["create", "read", "update"],
        "campaigns": ["read"],
        "meetings": ["create", "read"]
    },
    "read_only": {
        "leads": ["read"],
        "users": ["read"],
        "tickets": ["read"],
        "campaigns": ["read"],
        "meetings": ["read"]
    }
}

def has_permission(user_role: str, resource: str, action: str) -> bool:
    role = user_role.lower() if user_role else "employee"
    
    # Map legacy role names to standard standard ones
    if role in ["admin", "organization_admin"]:
        role = "organization_admin"
    elif role in ["member", "employee"]:
        role = "employee"
    elif role in ["superuser", "system_admin", "super_admin"]:
        role = "super_admin"

    permissions = ROLE_PERMISSIONS.get(role, {})
    
    # Check super admin wildcard
    if "*" in permissions and ("*" in permissions["*"] or action in permissions["*"]):
        return True
        
    if resource in permissions:
        allowed_actions = permissions[resource]
        return "*" in allowed_actions or action in allowed_actions
        
    return False

def require_permission(resource: Resource, action: Action):
    def dependency(current_user: User = Depends(deps.get_current_user)) -> User:
        if getattr(current_user, "is_system_admin", False) or getattr(current_user, "is_superuser", False):
            return current_user
            
        if not has_permission(current_user.role, resource.value, action.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: you do not have permission to {action.value} {resource.value}."
            )
        return current_user
    return dependency

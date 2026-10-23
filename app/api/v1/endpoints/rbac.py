"""
Django-Style RBAC API Endpoints.
Provides complete CRUD capabilities for Permissions, Groups, and User Role & Department assignments.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.models.base import User
from app.models.rbac import Group, Permission
from app.services.rbac_service import (
    ensure_system_permissions,
    ensure_tenant_default_groups,
    get_user_all_permissions,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = None


class UserRBACUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    is_staff: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_active: Optional[bool] = None
    group_ids: Optional[List[str]] = None
    user_permission_ids: Optional[List[str]] = None


class BulkActionRequest(BaseModel):
    user_ids: List[str]
    action: str  # delete, activate, deactivate, assign_group, remove_group
    group_id: Optional[str] = None


def _check_admin(current_user: User):
    """Enforce admin or superuser access to RBAC governance."""
    is_admin = (
        current_user.role == "admin"
        or getattr(current_user, "is_system_admin", False)
        or getattr(current_user, "is_superuser", False)
        or getattr(current_user, "is_staff", False)
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required to access RBAC governance.",
        )


# ─────────────────────────────────────────────────────────────
# 1. PERMISSIONS
# ─────────────────────────────────────────────────────────────

@router.get("/permissions")
def list_permissions(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """List all available system permissions, categorized by module/content_type."""
    _check_admin(current_user)
    # Ensure system catalog is seeded
    ensure_system_permissions(db)

    perms = db.query(Permission).order_by(Permission.content_type.asc(), Permission.name.asc()).all()

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    flat_list = []
    for p in perms:
        item = p.to_dict()
        flat_list.append(item)
        grouped.setdefault(p.content_type, []).append(item)

    return {
        "permissions": flat_list,
        "grouped": grouped,
        "total": len(flat_list),
    }


# ─────────────────────────────────────────────────────────────
# 2. GROUPS (ROLES)
# ─────────────────────────────────────────────────────────────

@router.get("/groups")
def list_groups(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """List all RBAC groups in the current tenant."""
    _check_admin(current_user)
    # Ensure standard default groups exist for the tenant
    ensure_tenant_default_groups(db, current_user.tenant_id)

    groups = (
        db.query(Group)
        .filter(Group.tenant_id == current_user.tenant_id)
        .order_by(Group.name.asc())
        .all()
    )
    return [g.to_dict() for g in groups]


@router.post("/groups")
def create_group(
    payload: GroupCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Create a new group in the tenant."""
    _check_admin(current_user)
    existing = (
        db.query(Group)
        .filter(Group.tenant_id == current_user.tenant_id, Group.name == payload.name.strip())
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"A group named '{payload.name}' already exists.")

    group = Group(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        description=payload.description or "",
    )

    if payload.permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(payload.permission_ids)).all()
        group.permissions.extend(perms)

    db.add(group)
    db.commit()
    db.refresh(group)
    return group.to_dict()


@router.get("/groups/{group_id}")
def get_group(
    group_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Retrieve detailed information for a single group."""
    _check_admin(current_user)
    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.tenant_id == current_user.tenant_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    res = group.to_dict()
    res["permissions"] = [p.to_dict() for p in group.permissions]
    res["members"] = [
        {
            "id": u.id,
            "name": u.name or u.email.split("@")[0].title(),
            "email": u.email,
            "department": getattr(u, "department", None) or "General",
        }
        for u in group.users
    ]
    return res


@router.put("/groups/{group_id}")
def update_group(
    group_id: str,
    payload: GroupUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Update group name, description, and permission assignments."""
    _check_admin(current_user)
    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.tenant_id == current_user.tenant_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if payload.name is not None:
        new_name = payload.name.strip()
        if new_name:
            dup = (
                db.query(Group)
                .filter(
                    Group.tenant_id == current_user.tenant_id,
                    Group.name == new_name,
                    Group.id != group_id,
                )
                .first()
            )
            if dup:
                raise HTTPException(status_code=400, detail=f"Another group named '{new_name}' already exists.")
            group.name = new_name

    if payload.description is not None:
        group.description = payload.description

    if payload.permission_ids is not None:
        perms = db.query(Permission).filter(Permission.id.in_(payload.permission_ids)).all()
        group.permissions = perms

    db.commit()
    db.refresh(group)
    return group.to_dict()


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a group from the tenant."""
    _check_admin(current_user)
    group = (
        db.query(Group)
        .filter(Group.id == group_id, Group.tenant_id == current_user.tenant_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    db.delete(group)
    db.commit()
    return {"message": f"Group '{group.name}' successfully deleted"}


# ─────────────────────────────────────────────────────────────
# 3. USERS RBAC MANAGEMENT
# ─────────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """List all users in the tenant with their assigned groups, roles, and status."""
    _check_admin(current_user)
    users = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id)
        .order_by(User.name.asc())
        .all()
    )

    results = []
    for u in users:
        group_list = [{"id": g.id, "name": g.name} for g in getattr(u, "groups", [])]
        results.append({
            "id": u.id,
            "name": u.name or u.email.split("@")[0].title(),
            "email": u.email,
            "phone_no": u.phone_no,
            "role": u.role,
            "department": getattr(u, "department", None) or "General",
            "is_staff": bool(getattr(u, "is_staff", False)),
            "is_superuser": bool(getattr(u, "is_superuser", False)),
            "is_active": bool(u.is_active),
            "is_verified": bool(getattr(u, "is_verified", False)),
            "groups": group_list,
            "groups_count": len(group_list),
            "permissions_count": len(get_user_all_permissions(db, u)),
        })

    return results


@router.get("/users/{user_id}")
def get_user_rbac(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get full RBAC profile for an individual user."""
    _check_admin(current_user)
    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    effective_perms = list(get_user_all_permissions(db, user))

    return {
        "id": user.id,
        "name": user.name or user.email.split("@")[0].title(),
        "email": user.email,
        "phone_no": user.phone_no,
        "role": user.role,
        "department": getattr(user, "department", None) or "",
        "is_staff": bool(getattr(user, "is_staff", False)),
        "is_superuser": bool(getattr(user, "is_superuser", False)),
        "is_active": bool(user.is_active),
        "group_ids": [g.id for g in getattr(user, "groups", [])],
        "groups": [{"id": g.id, "name": g.name} for g in getattr(user, "groups", [])],
        "user_permission_ids": [p.id for p in getattr(user, "user_permissions", [])],
        "effective_permissions": effective_perms,
        "effective_permissions_count": len(effective_perms),
    }


@router.put("/users/{user_id}")
def update_user_rbac(
    user_id: str,
    payload: UserRBACUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Update a user's RBAC profile, groups, direct permissions, and staff/superuser flags."""
    _check_admin(current_user)
    user = (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == current_user.tenant_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None:
        user.name = payload.name
    if payload.department is not None:
        user.department = payload.department
    if payload.role is not None:
        user.role = payload.role
    if payload.is_staff is not None:
        user.is_staff = payload.is_staff
    if payload.is_superuser is not None:
        # Prevent self-demotion or non-superusers granting superuser
        if not getattr(current_user, "is_superuser", False) and not getattr(current_user, "is_system_admin", False):
            if payload.is_superuser:
                raise HTTPException(status_code=403, detail="Only existing superusers can grant superuser status.")
        user.is_superuser = payload.is_superuser
    if payload.is_active is not None:
        if user_id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own user account.")
        user.is_active = payload.is_active

    if payload.group_ids is not None:
        groups = (
            db.query(Group)
            .filter(Group.id.in_(payload.group_ids), Group.tenant_id == current_user.tenant_id)
            .all()
        )
        user.groups = groups

    if payload.user_permission_ids is not None:
        perms = db.query(Permission).filter(Permission.id.in_(payload.user_permission_ids)).all()
        user.user_permissions = perms

    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "department": user.department,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "group_ids": [g.id for g in user.groups],
        "user_permission_ids": [p.id for p in user.user_permissions],
    }


@router.post("/users/bulk-action")
def bulk_user_action(
    payload: BulkActionRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Execute Django-style batch actions across multiple users."""
    _check_admin(current_user)
    if not payload.user_ids:
        raise HTTPException(status_code=400, detail="No users selected.")

    users = (
        db.query(User)
        .filter(User.id.in_(payload.user_ids), User.tenant_id == current_user.tenant_id)
        .all()
    )

    action = payload.action.lower()
    affected = 0

    if action == "delete":
        for u in users:
            if u.id != current_user.id:
                db.delete(u)
                affected += 1
    elif action == "activate":
        for u in users:
            u.is_active = True
            affected += 1
    elif action == "deactivate":
        for u in users:
            if u.id != current_user.id:
                u.is_active = False
                affected += 1
    elif action == "assign_group":
        if not payload.group_id:
            raise HTTPException(status_code=400, detail="Target group_id is required.")
        group = (
            db.query(Group)
            .filter(Group.id == payload.group_id, Group.tenant_id == current_user.tenant_id)
            .first()
        )
        if not group:
            raise HTTPException(status_code=404, detail="Target group not found.")
        for u in users:
            if group not in u.groups:
                u.groups.append(group)
                affected += 1
    elif action == "remove_group":
        if not payload.group_id:
            raise HTTPException(status_code=400, detail="Target group_id is required.")
        group = (
            db.query(Group)
            .filter(Group.id == payload.group_id, Group.tenant_id == current_user.tenant_id)
            .first()
        )
        if not group:
            raise HTTPException(status_code=404, detail="Target group not found.")
        for u in users:
            if group in u.groups:
                u.groups.remove(group)
                affected += 1
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported bulk action '{payload.action}'.")

    db.commit()
    return {"message": f"Successfully performed '{action}' on {affected} user(s).", "affected": affected}


@router.post("/seed-defaults")
def seed_defaults(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Seed standard system permissions and tenant default groups."""
    _check_admin(current_user)
    ensure_system_permissions(db)
    groups = ensure_tenant_default_groups(db, current_user.tenant_id)
    return {"message": "Standard permissions and default groups successfully verified/seeded.", "groups": [g.name for g in groups]}

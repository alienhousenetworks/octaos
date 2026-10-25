"""API endpoints for Section Rooms (HR, Marketing, Sales, Support)."""
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api import deps
from app.models.base import User
from app.models.rooms import SectionRoom
from app.models.verticals import Candidate, ContentPost, Ticket, Lead
from app.models.deal_room import DealRoom


router = APIRouter()

VALID_SECTIONS = {"hr", "marketing", "sales", "support"}


def _slugify(text: str) -> str:
    """Generate a clean URL slug from a name."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[\s_-]+", "-", clean)
    clean = clean.strip("-")
    return clean or "room"


def _generate_unique_slug(db: Session, tenant_id: str, section: str, base_slug: str, exclude_id: Optional[str] = None) -> str:
    """Ensure slug is unique within a tenant's section."""
    slug = base_slug
    counter = 1
    while True:
        query = db.query(SectionRoom).filter(
            SectionRoom.tenant_id == tenant_id,
            SectionRoom.section == section,
            SectionRoom.slug == slug,
        )
        if exclude_id:
            query = query.filter(SectionRoom.id != exclude_id)
        if not query.first():
            return slug
        counter += 1
        slug = f"{base_slug}-{counter}"


def _user_can_access_room(room: SectionRoom, user: Optional[User]) -> bool:
    """Verify if a user has access to a room."""
    if not user:
        return room.visibility == "public"
    if user.role == "admin" or user.is_superuser or getattr(user, "is_system_admin", False):
        return True
    if room.created_by_user_id == user.id:
        return True
    if room.visibility in ("internal_public", "public"):
        # Check section permissions if configured
        if user.allowed_sections and "all" not in user.allowed_sections:
            if room.section not in user.allowed_sections:
                return False
        return True
    # For private rooms, check explicit access list
    if room.access_list:
        for member in room.access_list:
            if isinstance(member, dict) and (member.get("user_id") == user.id or member.get("email") == user.email):
                return True
    return False


def _get_room_counts(db: Session, room: SectionRoom) -> Dict[str, int]:
    """Calculate items count for the room."""
    counts = {"total": 0, "active": 0}
    try:
        if room.section == "hr":
            total = db.query(Candidate).filter(
                Candidate.tenant_id == room.tenant_id,
                Candidate.room_id == room.id,
            ).count()
            active = db.query(Candidate).filter(
                Candidate.tenant_id == room.tenant_id,
                Candidate.room_id == room.id,
                Candidate.status.in_(["sourced", "screened", "interviewed", "offered"]),
            ).count()
            counts = {"total": total, "active": active}
        elif room.section == "marketing":
            total = db.query(ContentPost).filter(
                ContentPost.tenant_id == room.tenant_id,
                ContentPost.room_id == room.id,
            ).count()
            active = db.query(ContentPost).filter(
                ContentPost.tenant_id == room.tenant_id,
                ContentPost.room_id == room.id,
                ContentPost.status.in_(["draft", "scheduled"]),
            ).count()
            counts = {"total": total, "active": active}
        elif room.section == "sales":
            lead_room_filter = (Lead.room_id == room.id)
            deal_room_filter = (DealRoom.room_id == room.id)
            if room.slug == "default":
                lead_room_filter = or_(Lead.room_id == room.id, Lead.room_id.is_(None), Lead.room_id == "sales-default")
                deal_room_filter = or_(DealRoom.room_id == room.id, DealRoom.room_id.is_(None), DealRoom.room_id == "sales-default")
            leads_total = db.query(Lead).filter(
                Lead.tenant_id == room.tenant_id,
                lead_room_filter,
            ).count()
            deals_total = db.query(DealRoom).filter(
                DealRoom.tenant_id == room.tenant_id,
                deal_room_filter,
            ).count()
            total = leads_total + deals_total
            leads_active = db.query(Lead).filter(
                Lead.tenant_id == room.tenant_id,
                lead_room_filter,
                Lead.status.in_(["captured", "contacted", "in_discussion", "qualified", "ready", "contact_partial"]),
            ).count()
            deals_active = db.query(DealRoom).filter(
                DealRoom.tenant_id == room.tenant_id,
                deal_room_filter,
                DealRoom.stage.notin_(["won", "lost"]),
            ).count()
            counts = {"total": total, "active": leads_active + deals_active}
        elif room.section == "support":
            total = db.query(Ticket).filter(
                Ticket.tenant_id == room.tenant_id,
                Ticket.room_id == room.id,
            ).count()
            active = db.query(Ticket).filter(
                Ticket.tenant_id == room.tenant_id,
                Ticket.room_id == room.id,
                Ticket.status.in_(["open", "pending_human", "human_handling"]),
            ).count()
            counts = {"total": total, "active": active}
    except Exception:
        pass
    return counts


def _format_room_dict(db: Session, room: SectionRoom) -> Dict[str, Any]:
    creator_name = None
    creator_email = None
    if room.created_by_user:
        creator_name = room.created_by_user.name
        creator_email = room.created_by_user.email
    elif room.created_by_user_id:
        u = db.query(User).filter(User.id == room.created_by_user_id).first()
        if u:
            creator_name = u.name
            creator_email = u.email

    counts = _get_room_counts(db, room)
    return {
        "id": room.id,
        "tenant_id": room.tenant_id,
        "section": room.section,
        "name": room.name,
        "slug": room.slug,
        "description": room.description,
        "status": room.status,
        "visibility": room.visibility,
        "share_token": room.share_token,
        "access_list": room.access_list or [],
        "data": room.data or {},
        "created_by_user_id": room.created_by_user_id,
        "creator_name": creator_name,
        "creator_email": creator_email,
        "created_at": room.created_at.isoformat() if room.created_at else None,
        "updated_at": room.updated_at.isoformat() if room.updated_at else None,
        "counts": counts,
    }


# Schemas
class RoomCreate(BaseModel):
    section: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    visibility: str = "internal_public"  # internal_public | private | public
    data: Dict[str, Any] = {}
    access_list: List[Dict[str, Any]] = []


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class RoomAccessUpdate(BaseModel):
    visibility: Optional[str] = None  # internal_public | private | public
    access_list: Optional[List[Dict[str, Any]]] = None
    regenerate_share_token: Optional[bool] = False


@router.get("/staff")
def list_section_staff(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List staff members of the tenant for assigning room access."""
    users = db.query(User).filter(
        User.tenant_id == current_user.tenant_id,
        User.is_active == True,
    ).all()
    return [
        {
            "id": u.id,
            "name": u.name or u.email.split("@")[0],
            "email": u.email,
            "role": u.role,
        }
        for u in users
    ]


@router.get("/verify-slug")
def verify_slug(
    section: str = Query(..., pattern="^(hr|marketing|sales|support)$"),
    slug: str = Query(..., min_length=1),
    room_id: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> Any:
    """Verify if a slug is available in this section."""
    clean_slug = _slugify(slug)
    query = db.query(SectionRoom).filter(
        SectionRoom.tenant_id == tenant_id,
        SectionRoom.section == section,
        SectionRoom.slug == clean_slug,
    )
    if room_id:
        query = query.filter(SectionRoom.id != room_id)
    exists = query.first() is not None
    return {
        "slug": clean_slug,
        "available": not exists,
    }


@router.get("/")
def list_rooms(
    section: str = Query(..., pattern="^(hr|marketing|sales|support)$"),
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """List all rooms in a section accessible by the current user. Auto-seeds default room if empty."""
    tenant_id = current_user.tenant_id

    # Check if section has any rooms; if none, auto-seed a Default Room and backfill existing unassigned records
    existing_count = db.query(SectionRoom).filter(
        SectionRoom.tenant_id == tenant_id,
        SectionRoom.section == section,
    ).count()

    if existing_count == 0:
        default_room = SectionRoom(
            tenant_id=tenant_id,
            section=section,
            name=f"General {section.upper()}",
            slug="default",
            description=f"Primary default workspace folder for {section.upper()}.",
            status="active",
            visibility="internal_public",
            created_by_user_id=current_user.id,
            data={},
        )
        db.add(default_room)
        db.flush()

        # Backfill existing records that have no room_id
        if section == "hr":
            db.query(Candidate).filter(
                Candidate.tenant_id == tenant_id,
                Candidate.room_id.is_(None),
            ).update({"room_id": default_room.id}, synchronize_session=False)
        elif section == "marketing":
            db.query(ContentPost).filter(
                ContentPost.tenant_id == tenant_id,
                ContentPost.room_id.is_(None),
            ).update({"room_id": default_room.id}, synchronize_session=False)
        elif section == "sales":
            db.query(Lead).filter(
                Lead.tenant_id == tenant_id,
                Lead.room_id.is_(None),
            ).update({"room_id": default_room.id}, synchronize_session=False)
            db.query(DealRoom).filter(
                DealRoom.tenant_id == tenant_id,
                DealRoom.room_id.is_(None),
            ).update({"room_id": default_room.id}, synchronize_session=False)
        elif section == "support":
            db.query(Ticket).filter(
                Ticket.tenant_id == tenant_id,
                Ticket.room_id.is_(None),
            ).update({"room_id": default_room.id}, synchronize_session=False)

        db.commit()

    q = db.query(SectionRoom).filter(
        SectionRoom.tenant_id == tenant_id,
        SectionRoom.section == section,
    )

    if status and status != "all":
        q = q.filter(SectionRoom.status == status)

    if search:
        search_filter = f"%{search.strip()}%"
        q = q.filter(
            or_(
                SectionRoom.name.ilike(search_filter),
                SectionRoom.slug.ilike(search_filter),
                SectionRoom.description.ilike(search_filter),
            )
        )

    rooms = q.order_by(SectionRoom.created_at.desc()).all()

    # Filter by user access
    accessible_rooms = [
        _format_room_dict(db, r)
        for r in rooms
        if _user_can_access_room(r, current_user)
    ]
    return accessible_rooms


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Create a new section room with a unique slug and creator attribution."""
    section = payload.section.lower().strip()
    if section not in VALID_SECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid section: {payload.section}")

    base_slug = _slugify(payload.slug if payload.slug else payload.name)
    unique_slug = _generate_unique_slug(db, current_user.tenant_id, section, base_slug)

    share_token = secrets.token_urlsafe(16) if payload.visibility == "public" else None

    room = SectionRoom(
        tenant_id=current_user.tenant_id,
        section=section,
        name=payload.name.strip(),
        slug=unique_slug,
        description=payload.description.strip() if payload.description else None,
        status=payload.status,
        visibility=payload.visibility,
        share_token=share_token,
        access_list=payload.access_list or [],
        data=payload.data or {},
        created_by_user_id=current_user.id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return _format_room_dict(db, room)


@router.get("/{section}/{slug}")
def get_room_by_slug(
    section: str,
    slug: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Fetch room details by section and slug, enforcing access rules."""
    room = db.query(SectionRoom).filter(
        SectionRoom.tenant_id == current_user.tenant_id,
        SectionRoom.section == section.lower(),
        SectionRoom.slug == slug.lower(),
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not _user_can_access_room(room, current_user):
        raise HTTPException(status_code=403, detail="You do not have access to this room")

    return _format_room_dict(db, room)


@router.patch("/{room_id}")
def update_room(
    room_id: str,
    payload: RoomUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update room name, description, status, or data dictionary."""
    room = db.query(SectionRoom).filter(
        SectionRoom.id == room_id,
        SectionRoom.tenant_id == current_user.tenant_id,
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if not _user_can_access_room(room, current_user):
        raise HTTPException(status_code=403, detail="Not authorized to edit this room")

    if payload.name is not None:
        room.name = payload.name.strip()
    if payload.description is not None:
        room.description = payload.description.strip() if payload.description else None
    if payload.status is not None:
        room.status = payload.status
    if payload.data is not None:
        merged_data = dict(room.data or {})
        merged_data.update(payload.data)
        room.data = merged_data

    room.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(room)
    return _format_room_dict(db, room)


@router.put("/{room_id}/access")
def update_room_access(
    room_id: str,
    payload: RoomAccessUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update room visibility, staff access list, or regenerate public share link."""
    room = db.query(SectionRoom).filter(
        SectionRoom.id == room_id,
        SectionRoom.tenant_id == current_user.tenant_id,
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Only creator or admin can change access
    is_owner = room.created_by_user_id == current_user.id
    is_admin = current_user.role == "admin" or getattr(current_user, "is_system_admin", False)
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Only the room owner or admin can modify room access")

    if payload.visibility is not None:
        room.visibility = payload.visibility
        if payload.visibility == "public" and not room.share_token:
            room.share_token = secrets.token_urlsafe(16)
        elif payload.visibility != "public":
            room.share_token = None

    if payload.access_list is not None:
        room.access_list = payload.access_list

    if payload.regenerate_share_token and room.visibility == "public":
        room.share_token = secrets.token_urlsafe(16)

    room.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(room)
    return _format_room_dict(db, room)


@router.delete("/{room_id}")
def delete_room(
    room_id: str,
    permanent: bool = Query(False),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Archive or permanently delete a section room."""
    room = db.query(SectionRoom).filter(
        or_(SectionRoom.id == room_id, SectionRoom.slug == room_id.lower()),
        SectionRoom.tenant_id == current_user.tenant_id,
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    is_owner = room.created_by_user_id == current_user.id
    is_admin = current_user.role == "admin" or getattr(current_user, "is_system_admin", False)
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Only the room owner or admin can delete this room")

    if room.slug == "default":
        raise HTTPException(status_code=400, detail="Cannot delete the default room")

    if permanent:
        # Unlink foreign keys safely
        db.query(Candidate).filter(Candidate.room_id == room.id).update({"room_id": None})
        db.query(ContentPost).filter(ContentPost.room_id == room.id).update({"room_id": None})
        db.query(Lead).filter(Lead.room_id == room.id).update({"room_id": None})
        db.query(DealRoom).filter(DealRoom.room_id == room.id).update({"room_id": None})
        db.query(Ticket).filter(Ticket.room_id == room.id).update({"room_id": None})
        deleted_id = room.id
        db.delete(room)
        db.commit()
        return {"status": "deleted", "id": deleted_id}

    # Mark as archived
    room.status = "archived"
    room.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "archived", "id": room.id}


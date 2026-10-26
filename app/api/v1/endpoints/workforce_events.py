"""Authenticated API for the persistent workforce event stream."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.services.workforce_event_service import EventConflictError, WorkforceEventService

router = APIRouter()


class WorkforceEventCreate(BaseModel):
    event_key: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_.:-]+$")
    payload: dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = Field(default=None, max_length=200)


@router.post("", status_code=201)
def append_workforce_event(
    body: WorkforceEventCreate,
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_active_user),
):
    """Append a user-originated event; retries with the same key are idempotent."""
    try:
        event = WorkforceEventService(db, user.tenant_id).append(
            event_key=body.event_key,
            event_type=body.event_type,
            payload=body.payload,
            source="user",
            run_id=body.run_id,
            actor_user_id=user.id,
        )
    except EventConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "id": event.id,
        "event_key": event.event_key,
        "event_type": event.event_type,
        "source": event.source,
        "run_id": event.run_id,
        "payload": event.payload,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("")
def read_workforce_events(
    cursor: Optional[str] = Query(default=None, max_length=500),
    limit: int = Query(default=100, ge=1, le=200),
    event_type: Optional[str] = Query(default=None, max_length=120),
    run_id: Optional[str] = Query(default=None, max_length=200),
    db: Session = Depends(deps.get_db),
    user: User = Depends(deps.get_current_active_user),
):
    """Read durable events after a cursor; every query is scoped to the caller tenant."""
    try:
        return WorkforceEventService(db, user.tenant_id).read(
            cursor=cursor,
            limit=limit,
            event_type=event_type,
            run_id=run_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid event cursor") from exc

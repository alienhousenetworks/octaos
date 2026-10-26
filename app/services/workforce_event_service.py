"""Tenant-scoped append-only event log with cursor-based replay."""
from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.workforce_events import WorkforceEvent


MAX_EVENT_PAYLOAD_BYTES = 64 * 1024


class EventConflictError(ValueError):
    pass


def encode_cursor(created_at: datetime, event_id: str) -> str:
    raw = f"{created_at.isoformat()}|{event_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + ("=" * (-len(cursor) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        timestamp, event_id = decoded.split("|", 1)
        parsed = datetime.fromisoformat(timestamp)
        if not event_id:
            raise ValueError("empty event id")
        return parsed, event_id
    except Exception as exc:
        raise ValueError("Invalid event cursor") from exc


class WorkforceEventService:
    def __init__(self, db: Session, tenant_id: str):
        if not tenant_id:
            raise ValueError("tenant_id is required")
        self.db = db
        self.tenant_id = tenant_id

    def append(
        self,
        *,
        event_key: str,
        event_type: str,
        payload: dict[str, Any],
        source: str = "user",
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
    ) -> WorkforceEvent:
        if not event_key or len(event_key) > 200:
            raise ValueError("event_key must be between 1 and 200 characters")
        if not event_type or len(event_type) > 120:
            raise ValueError("event_type must be between 1 and 120 characters")
        if len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) > MAX_EVENT_PAYLOAD_BYTES:
            raise ValueError("Event payload exceeds 64 KiB")
        existing = (
            self.db.query(WorkforceEvent)
            .filter(
                WorkforceEvent.tenant_id == self.tenant_id,
                WorkforceEvent.event_key == event_key,
            )
            .first()
        )
        if existing:
            if existing.event_type != event_type or existing.payload != payload:
                raise EventConflictError("event_key was already used for a different event")
            return existing
        event = WorkforceEvent(
            tenant_id=self.tenant_id,
            event_key=event_key,
            event_type=event_type,
            source=source,
            run_id=run_id,
            agent_id=agent_id,
            actor_user_id=actor_user_id,
            payload=payload,
        )
        self.db.add(event)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            # Concurrent duplicate delivery: fetch the winning tenant-scoped row.
            existing = (
                self.db.query(WorkforceEvent)
                .filter(
                    WorkforceEvent.tenant_id == self.tenant_id,
                    WorkforceEvent.event_key == event_key,
                )
                .first()
            )
            if existing and existing.event_type == event_type and existing.payload == payload:
                return existing
            if existing:
                raise EventConflictError("event_key was already used for a different event")
            raise
        self.db.refresh(event)
        return event

    def read(
        self,
        *,
        cursor: Optional[str] = None,
        limit: int = 100,
        event_type: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        query = self.db.query(WorkforceEvent).filter(WorkforceEvent.tenant_id == self.tenant_id)
        if event_type:
            query = query.filter(WorkforceEvent.event_type == event_type)
        if run_id:
            query = query.filter(WorkforceEvent.run_id == run_id)
        if cursor:
            created_at, event_id = decode_cursor(cursor)
            query = query.filter(
                or_(
                    WorkforceEvent.created_at > created_at,
                    and_(
                        WorkforceEvent.created_at == created_at,
                        WorkforceEvent.id > event_id,
                    ),
                )
            )
        rows = (
            query.order_by(WorkforceEvent.created_at.asc(), WorkforceEvent.id.asc())
            .limit(max(1, min(limit, 200)) + 1)
            .all()
        )
        has_more = len(rows) > max(1, min(limit, 200))
        rows = rows[: max(1, min(limit, 200))]
        items = [
            {
                "id": row.id,
                "event_key": row.event_key,
                "event_type": row.event_type,
                "source": row.source,
                "run_id": row.run_id,
                "agent_id": row.agent_id,
                "actor_user_id": row.actor_user_id,
                "payload": row.payload or {},
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
        next_cursor = None
        if rows and rows[-1].created_at:
            next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id)
        return {"items": items, "next_cursor": next_cursor, "has_more": has_more}

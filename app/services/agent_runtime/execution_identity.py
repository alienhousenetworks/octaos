"""Tenant-scoped canonical execution identity registry.

Source runtimes retain their own records, but every run can register an alias to one
canonical execution ID. This is a correlation layer, not a replacement for durable
source records or their state machines.
"""
from __future__ import annotations

import uuid
from typing import Any, Mapping, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent_runtime import ExecutionIdentity


def register_execution_identity(
    db: Session,
    *,
    tenant_id: str,
    source_kind: str,
    source_id: str,
    canonical_execution_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> ExecutionIdentity:
    """Idempotently register a tenant-scoped source alias to a canonical run ID."""
    if not tenant_id or not source_kind.strip() or not source_id.strip():
        raise ValueError("tenant_id, source_kind and source_id are required")
    existing = db.query(ExecutionIdentity).filter(
        ExecutionIdentity.tenant_id == tenant_id,
        ExecutionIdentity.source_kind == source_kind,
        ExecutionIdentity.source_id == source_id,
    ).first()
    if existing:
        if canonical_execution_id and existing.canonical_execution_id != canonical_execution_id:
            raise ValueError("EXECUTION_IDENTITY_CONFLICT")
        if metadata:
            merged = dict(existing.metadata_json or {})
            merged.update(dict(metadata))
            existing.metadata_json = merged
            db.commit()
            db.refresh(existing)
        return existing

    canonical = canonical_execution_id or str(uuid.uuid4())
    identity = ExecutionIdentity(
        tenant_id=tenant_id,
        canonical_execution_id=canonical,
        source_kind=source_kind,
        source_id=source_id,
        metadata_json=dict(metadata or {}),
    )
    db.add(identity)
    try:
        db.commit()
        db.refresh(identity)
        return identity
    except IntegrityError:
        db.rollback()
        existing = db.query(ExecutionIdentity).filter(
            ExecutionIdentity.tenant_id == tenant_id,
            ExecutionIdentity.source_kind == source_kind,
            ExecutionIdentity.source_id == source_id,
        ).first()
        if existing and (not canonical_execution_id or existing.canonical_execution_id == canonical_execution_id):
            return existing
        raise ValueError("EXECUTION_IDENTITY_CONFLICT")

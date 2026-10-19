"""Policy-aware cache with tenant, identity, and query isolation."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.models.knowledge_connectors import ConnectorCacheEntry
from app.services.knowledge_connectors.contracts import ConnectorResult, ExecutionContext


class ConnectorCacheManager:
    """Manages policy-isolated cached query results."""

    @staticmethod
    def _compute_hashes(
        context: ExecutionContext,
        params: Dict[str, Any],
    ) -> tuple[str, str]:
        param_str = json.dumps(params, sort_keys=True)
        query_hash = hashlib.sha256(param_str.encode("utf-8")).hexdigest()
        identity_str = f"{context.tenant_id}:{context.acting_agent_id or 'anon'}:{context.department}"
        identity_hash = hashlib.sha256(identity_str.encode("utf-8")).hexdigest()
        return query_hash, identity_hash

    @classmethod
    def get(
        cls,
        db: Session,
        connector_id: str,
        context: ExecutionContext,
        params: Dict[str, Any],
    ) -> Optional[ConnectorResult]:
        query_hash, identity_hash = cls._compute_hashes(context, params)
        entry = db.query(ConnectorCacheEntry).filter(
            ConnectorCacheEntry.tenant_id == context.tenant_id,
            ConnectorCacheEntry.connector_id == connector_id,
            ConnectorCacheEntry.query_hash == query_hash,
            ConnectorCacheEntry.acting_identity_hash == identity_hash,
            ConnectorCacheEntry.expires_at > datetime.utcnow(),
        ).first()

        if not entry:
            return None

        try:
            cached_dict = entry.cached_envelope
            cached_result = ConnectorResult(**cached_dict)
            cached_result.status = "stale" if (entry.expires_at - datetime.utcnow()).total_seconds() < 30 else cached_result.status
            return cached_result
        except Exception:
            return None

    @classmethod
    def set(
        cls,
        db: Session,
        connector_id: str,
        context: ExecutionContext,
        params: Dict[str, Any],
        result: ConnectorResult,
        ttl_seconds: int = 300,
    ) -> None:
        if result.status not in ("success", "partial"):
            return  # Do not cache error, timeout, or denied results

        query_hash, identity_hash = cls._compute_hashes(context, params)
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        # Upsert cache entry
        existing = db.query(ConnectorCacheEntry).filter(
            ConnectorCacheEntry.tenant_id == context.tenant_id,
            ConnectorCacheEntry.connector_id == connector_id,
            ConnectorCacheEntry.query_hash == query_hash,
            ConnectorCacheEntry.acting_identity_hash == identity_hash,
        ).first()

        if existing:
            existing.cached_envelope = result.model_dump(mode="json")
            existing.expires_at = expires_at
        else:
            new_entry = ConnectorCacheEntry(
                tenant_id=context.tenant_id,
                connector_id=connector_id,
                query_hash=query_hash,
                acting_identity_hash=identity_hash,
                cached_envelope=result.model_dump(mode="json"),
                expires_at=expires_at,
            )
            db.add(new_entry)

        db.commit()

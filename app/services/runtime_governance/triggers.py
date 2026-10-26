"""Idempotent trigger-to-task dispatch using the durable task idempotency index."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Mapping

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,180}$")


def trigger_idempotency_key(trigger_id: str, delivery_id: str) -> str:
    """Build a bounded stable key without storing untrusted provider IDs verbatim."""
    if not _SAFE_ID.fullmatch(trigger_id or "") or not _SAFE_ID.fullmatch(delivery_id or ""):
        raise ValueError("Trigger and delivery IDs must be 1–180 safe identifier characters.")
    digest = hashlib.sha256(f"{trigger_id}:{delivery_id}".encode("utf-8")).hexdigest()
    return f"trigger:{digest}"


def dispatch_trigger_task(
    db: Any,
    *,
    tenant_id: str,
    created_by_id: str,
    trigger_id: str,
    delivery_id: str,
    title: str,
    goal: str,
    task_type: str,
    payload: Mapping[str, Any] | None = None,
    organization_id: str | None = None,
    autonomy_level: str = "supervised",
    risk_level: str = "standard",
) -> AutonomousTask:
    """Persist one task per trigger delivery; database uniqueness deduplicates retries.

    This creates a queued task only. A separate worker/dispatcher performs execution
    after tenant policy, connector status and approval requirements are evaluated.
    """
    # Keep identifier helpers importable without importing the application's full
    # model registry; dispatch loads DB-bound dependencies only when invoked.
    from app.models.autonomous_work import AutonomousTask
    from app.services.autonomous_runtime.engine import AutonomousRuntime

    received_at = datetime.now(timezone.utc).isoformat()
    safe_payload = dict(payload or {})
    # Recursively reject secrets so nested webhook objects cannot bypass the guard.
    forbidden = {"api_key", "access_token", "refresh_token", "password", "secret", "client_secret", "authorization", "cookie", "private_key"}
    def reject_secret_fields(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key).lower().replace("-", "_") in forbidden:
                    raise ValueError("Trigger payload contains a forbidden secret field.")
                reject_secret_fields(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                reject_secret_fields(child)
    reject_secret_fields(safe_payload)
    runtime = AutonomousRuntime(db)
    return runtime.create_task(
        tenant_id=tenant_id,
        organization_id=organization_id,
        created_by_id=created_by_id,
        title=title,
        goal=goal,
        autonomy_level=autonomy_level,
        risk_level=risk_level,
        context={
            "task_type": task_type,
            "trigger": {"trigger_id": trigger_id, "delivery_id_hash": hashlib.sha256(delivery_id.encode()).hexdigest(),
                        "received_at": received_at},
            "payload": safe_payload,
        },
        idempotency_key=trigger_idempotency_key(trigger_id, delivery_id),
    )

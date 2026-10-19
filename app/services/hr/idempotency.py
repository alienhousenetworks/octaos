import hashlib
import json
from typing import Any, Dict


def canonical_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def hr_idempotency_key(tenant_id: str, capability_id: str, subject_id: str, payload: Dict[str, Any]) -> str:
    """33-character key. Fits workflow_events.correlation_id String(64) and the outbox String(128)."""
    material = f"{tenant_id}|{capability_id}|{subject_id}|{canonical_json(payload)}"
    return "h" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]

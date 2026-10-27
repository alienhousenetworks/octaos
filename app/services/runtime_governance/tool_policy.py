"""Server-side policy checks for tool execution and signed webhook delivery.

High-risk approvals are bound to a canonical action fingerprint. A generic
"approved" flag is deliberately insufficient: the caller must present the same
fingerprint that was approved, covering the exact target and payload.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


HIGH_RISK_ACTION_PREFIXES = (
    "email.send", "email.delete", "crm.delete", "payment.", "billing.",
    "post.publish", "contract.sign", "user.delete", "browser.submit", "webhook_post",
)


@dataclass(frozen=True)
class ToolAuthorization:
    allowed: bool
    reason: str
    approval_required: bool = False


def action_fingerprint(
    *,
    tenant_id: str,
    run_id: str,
    bot_id: str,
    tool_name: str,
    target: str,
    payload: Mapping[str, Any],
    policy_version: str,
) -> str:
    """Return a stable digest binding an approval to one exact proposed action."""
    canonical = {
        "tenant_id": tenant_id,
        "run_id": run_id,
        "bot_id": bot_id,
        "tool_name": tool_name,
        "target": target,
        "payload": payload,
        "policy_version": policy_version,
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def authorize_tool_call(
    *,
    tenant_id: str,
    request_tenant_id: str,
    tool_name: str,
    granted_tools: Iterable[str],
    connection_active: bool,
    approval_status: str | None = None,
    action_binding: str | None = None,
    approved_action_binding: str | None = None,
) -> ToolAuthorization:
    """Authorize at execution time; UI-hidden tools are not a security control.

    High-risk actions require an approved, exact action fingerprint. This prevents
    a stale approval for one recipient/message/target being reused for another.
    """
    if not tenant_id or tenant_id != request_tenant_id:
        return ToolAuthorization(False, "TENANT_MISMATCH")
    if not connection_active:
        return ToolAuthorization(False, "CONNECTION_INACTIVE")
    grants = set(granted_tools)
    if tool_name not in grants and "*" not in grants:
        return ToolAuthorization(False, "TOOL_NOT_GRANTED")
    if approval_status == "rejected":
        return ToolAuthorization(False, "APPROVAL_REJECTED")
    high_risk = any(tool_name == prefix or tool_name.startswith(prefix) for prefix in HIGH_RISK_ACTION_PREFIXES)
    if high_risk:
        if approval_status != "approved":
            return ToolAuthorization(False, "APPROVAL_REQUIRED", approval_required=True)
        if not action_binding or not approved_action_binding:
            return ToolAuthorization(False, "APPROVAL_BINDING_REQUIRED", approval_required=True)
        if not hmac.compare_digest(action_binding, approved_action_binding):
            return ToolAuthorization(False, "APPROVAL_BINDING_MISMATCH", approval_required=True)
    return ToolAuthorization(True, "AUTHORIZED")


def verify_hmac_webhook(
    *,
    secret: str,
    timestamp: str,
    raw_body: bytes,
    signature: str,
    now: float | None = None,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify timestamped HMAC-SHA256 signatures and reject stale/replayed payloads.

    Caller must separately persist and deduplicate the provider event ID; a valid
    signature alone does not provide delivery idempotency.
    """
    if not secret or not timestamp or not signature or not isinstance(raw_body, bytes):
        return False
    if not timestamp.isascii() or not timestamp.isdecimal():
        return False
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    current = time.time() if now is None else now
    if abs(current - sent_at) > tolerance_seconds:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("ascii") + b"." + raw_body,
        hashlib.sha256,
    ).hexdigest()
    supplied = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, supplied)

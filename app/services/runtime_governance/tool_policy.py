"""Server-side policy checks for tool execution and signed webhook delivery."""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Iterable


HIGH_RISK_ACTION_PREFIXES = (
    "email.send", "email.delete", "crm.delete", "payment.", "billing.",
    "post.publish", "contract.sign", "user.delete", "browser.submit", "webhook_post",
)


@dataclass(frozen=True)
class ToolAuthorization:
    allowed: bool
    reason: str
    approval_required: bool = False


def authorize_tool_call(
    *,
    tenant_id: str,
    request_tenant_id: str,
    tool_name: str,
    granted_tools: Iterable[str],
    connection_active: bool,
    approval_status: str | None = None,
) -> ToolAuthorization:
    """Authorize at execution time; UI-hidden tools are not a security control."""
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
    if high_risk and approval_status != "approved":
        return ToolAuthorization(False, "APPROVAL_REQUIRED", approval_required=True)
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

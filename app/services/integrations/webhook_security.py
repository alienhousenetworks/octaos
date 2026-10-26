"""Shared HMAC verification for configurable OctaOS webhook ingress."""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional


def verify_timestamped_hmac(
    *,
    secret: str,
    timestamp: Optional[str],
    signature: Optional[str],
    body: bytes,
    now: Optional[float] = None,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify X-OctaOS-Timestamp and X-OctaOS-Signature.

    Signature format is sha256=<hex hmac>. The signed bytes are
    ASCII(timestamp) + b"." + raw request body. Callers should separately
    apply provider/event idempotency because a valid signature can be replayed
    within the accepted time window.
    """
    if not secret or not timestamp or not signature:
        return False

    try:
        timestamp_value = int(timestamp)
    except (TypeError, ValueError):
        return False

    current_time = time.time() if now is None else now
    if abs(current_time - timestamp_value) > tolerance_seconds:
        return False

    supplied = signature.strip()
    if supplied.startswith("sha256="):
        supplied = supplied[len("sha256="):]

    signed = timestamp.encode("ascii", errors="strict") + b"." + body
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied.lower())

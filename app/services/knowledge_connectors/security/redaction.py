"""Data redaction and credential masking utilities."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set

SENSITIVE_KEY_PATTERNS = {
    "password", "secret", "token", "api_key", "apikey", "authorization",
    "private_key", "ssn", "social_security", "credit_card", "card_number",
    "cvv", "bank_account", "account_number"
}


def mask_secret_string(val: str) -> str:
    """Masks all but the first 3 and last 4 characters of a secret."""
    if not val or len(val) <= 8:
        return "********"
    return f"{val[:3]}****{val[-4:]}"


def redact_dictionary(
    data: Any,
    denied_fields: List[str] | Set[str] | None = None,
    redact_sensitive_keys: bool = True,
) -> Any:
    """Recursively redacts denied fields and standard sensitive keys from dictionaries."""
    denied_set = set(k.lower() for k in (denied_fields or []))

    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if k_lower in denied_set:
                result[k] = "[REDACTED_BY_POLICY]"
            elif redact_sensitive_keys and any(p in k_lower for p in SENSITIVE_KEY_PATTERNS):
                result[k] = "[REDACTED_SENSITIVE]"
            else:
                result[k] = redact_dictionary(v, denied_fields, redact_sensitive_keys)
        return result
    elif isinstance(data, list):
        return [redact_dictionary(item, denied_fields, redact_sensitive_keys) for item in data]
    else:
        return data

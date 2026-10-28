"""Security helpers for outbound collaboration payloads and network destinations."""
from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any, Dict
from urllib.parse import urlsplit


class CollaborationSecurityError(ValueError):
    """An outbound collaboration request failed a security boundary."""


def validate_public_https_url(url: str) -> str:
    """Reject unsafe URL forms and hosts resolving to non-public IP addresses."""
    if not isinstance(url, str) or len(url) > 2048:
        raise CollaborationSecurityError("URL is missing or exceeds the allowed length.")
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() != "https":
        raise CollaborationSecurityError("Only HTTPS destinations are permitted.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise CollaborationSecurityError("URL must contain a hostname and no embedded credentials.")
    if parsed.port not in (None, 443):
        raise CollaborationSecurityError("Only the default HTTPS port is permitted.")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
        raise CollaborationSecurityError("Local destinations are not permitted.")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError) as exc:
            raise CollaborationSecurityError("Destination hostname could not be safely resolved.") from exc
    if not addresses or any(
        not (address.is_global and not address.is_private and not address.is_loopback
             and not address.is_link_local and not address.is_multicast and not address.is_reserved)
        for address in addresses
    ):
        raise CollaborationSecurityError("Private, loopback, link-local, or reserved destinations are not permitted.")
    return url.strip()


def validate_json_schema(payload: Any, schema: Dict[str, Any]) -> None:
    """Validate the full JSON Schema contract, including nested types and constraints."""
    if not isinstance(schema, dict):
        raise CollaborationSecurityError("Output schema must be a JSON object.")
    try:
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(payload),
            key=lambda error: list(map(str, error.absolute_path)),
        )
    except ImportError as exc:
        raise CollaborationSecurityError("JSON Schema validation dependency is unavailable.") from exc
    except Exception as exc:
        raise CollaborationSecurityError("Output schema is invalid.") from exc
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "$"
        raise CollaborationSecurityError(f"Output schema violation at {path}: {first.message[:300]}")


def bounded_json_size(value: Any, max_bytes: int = 1_000_000) -> None:
    """Bound response size before validation/storage."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CollaborationSecurityError("Result is not JSON serializable.") from exc
    if len(encoded) > max_bytes:
        raise CollaborationSecurityError("Result exceeds the 1 MB collaboration payload limit.")

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


def _validate_node(val: Any, sch: Dict[str, Any], path: str = "$") -> None:
    expected_type = sch.get("type")
    if expected_type:
        if expected_type == "object":
            if not isinstance(val, dict):
                raise CollaborationSecurityError(f"Output schema violation at {path}: expected object, got {type(val).__name__}")
        elif expected_type == "integer":
            if not isinstance(val, int) or isinstance(val, bool):
                raise CollaborationSecurityError(f"Output schema violation at {path}: expected integer, got {type(val).__name__}")
        elif expected_type == "number":
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise CollaborationSecurityError(f"Output schema violation at {path}: expected number, got {type(val).__name__}")
        elif expected_type == "string":
            if not isinstance(val, str):
                raise CollaborationSecurityError(f"Output schema violation at {path}: expected string, got {type(val).__name__}")
        elif expected_type == "boolean":
            if not isinstance(val, bool):
                raise CollaborationSecurityError(f"Output schema violation at {path}: expected boolean, got {type(val).__name__}")
        elif expected_type == "array":
            if not isinstance(val, list):
                raise CollaborationSecurityError(f"Output schema violation at {path}: expected array, got {type(val).__name__}")

    if isinstance(val, (int, float)) and not isinstance(val, bool):
        if "minimum" in sch and val < sch["minimum"]:
            raise CollaborationSecurityError(f"Output schema violation at {path}: {val} is less than minimum {sch['minimum']}")
        if "maximum" in sch and val > sch["maximum"]:
            raise CollaborationSecurityError(f"Output schema violation at {path}: {val} is greater than maximum {sch['maximum']}")

    if isinstance(val, dict):
        required = sch.get("required", [])
        for req_key in required:
            if req_key not in val:
                raise CollaborationSecurityError(f"Output schema violation at {path}: missing required property '{req_key}'")

        properties = sch.get("properties", {})
        for prop_name, prop_val in val.items():
            if prop_name in properties:
                _validate_node(prop_val, properties[prop_name], f"{path}.{prop_name}")
            elif sch.get("additionalProperties") is False:
                raise CollaborationSecurityError(f"Output schema violation at {path}: unexpected property '{prop_name}'")


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
        if errors:
            first = errors[0]
            path = ".".join(str(part) for part in first.absolute_path) or "$"
            raise CollaborationSecurityError(f"Output schema violation at {path}: {first.message[:300]}")
    except ImportError:
        # Fallback to standard library schema validator if jsonschema is not installed in the environment
        _validate_node(payload, schema, "$")
    except CollaborationSecurityError:
        raise
    except Exception as exc:
        raise CollaborationSecurityError("Output schema is invalid.") from exc


def bounded_json_size(value: Any, max_bytes: int = 1_000_000) -> None:
    """Bound response size before validation/storage."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CollaborationSecurityError("Result is not JSON serializable.") from exc
    if len(encoded) > max_bytes:
        raise CollaborationSecurityError("Result exceeds the 1 MB collaboration payload limit.")


class PublicPinnedResolver:
    """aiohttp resolver that validates and pins DNS answers for the actual socket.

    The connector receives numeric, prevalidated addresses from this resolver rather
    than resolving the hostname a second time in the networking stack. TLS still uses
    the original URL hostname for certificate/SNI verification.
    """

    async def resolve(self, host: str, port: int = 443, family: int = socket.AF_UNSPEC):
        import asyncio
        import aiohttp.abc

        hostname = host.rstrip(".").lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith((".localhost", ".local")):
            raise CollaborationSecurityError("Local destinations are not permitted.")
        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(
                hostname, port, family=family, type=socket.SOCK_STREAM,
            )
        except OSError as exc:
            raise CollaborationSecurityError("Destination hostname could not be safely resolved.") from exc
        if not infos:
            raise CollaborationSecurityError("Destination hostname returned no addresses.")
        resolved = []
        for af, socktype, proto, _canonname, sockaddr in infos:
            ip = ipaddress.ip_address(sockaddr[0])
            if not (ip.is_global and not ip.is_private and not ip.is_loopback and
                    not ip.is_link_local and not ip.is_multicast and not ip.is_reserved):
                raise CollaborationSecurityError("DNS resolved to a private or reserved address.")
            resolved.append({
                "hostname": hostname,
                "host": str(ip),
                "port": port,
                "family": af,
                "proto": proto,
                "flags": 0,
            })
        # De-duplicate resolver results while preserving their order.
        unique = []
        seen = set()
        for entry in resolved:
            key = (entry["host"], entry["family"])
            if key not in seen:
                unique.append(entry)
                seen.add(key)
        return unique

    async def close(self) -> None:
        return None

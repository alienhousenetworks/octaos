"""Layered URL, DNS, and IP validation for outbound network egress."""
from __future__ import annotations

import ipaddress
import socket
import urllib.parse
from typing import List, Tuple
from app.services.knowledge_connectors.errors import SSRFProtectionError


CLOUD_METADATA_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata",
    "instance-data",
    "100.100.100.100",  # Alibaba cloud metadata
}

DISALLOWED_TLDS = {
    "local",
    "internal",
    "corp",
    "home",
    "lan",
}


def is_ip_forbidden(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Returns True if IP address is private, loopback, link-local, multicast, or reserved."""
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        return True

    # Cloud metadata exact check
    if str(ip_obj) == "169.254.169.254":
        return True

    # IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1 or ::ffff:169.254.169.254)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        return is_ip_forbidden(ip_obj.ipv4_mapped)

    return False


def validate_and_resolve_destination(
    url_str: str,
    allow_http_for_testing: bool = False,
) -> Tuple[str, List[str], int]:
    """
    Validates URL scheme, hostname, and resolves IP addresses with strict SSRF defense.
    Returns (normalized_url, resolved_public_ips, port).
    Raises SSRFProtectionError on any violation.
    """
    if not url_str or not isinstance(url_str, str):
        raise SSRFProtectionError("URL must be a non-empty string.")

    parsed = urllib.parse.urlparse(url_str.strip())
    allowed_schemes = ("https", "http") if allow_http_for_testing else ("https",)

    if parsed.scheme.lower() not in allowed_schemes:
        raise SSRFProtectionError(
            f"Prohibited scheme '{parsed.scheme}'. Only HTTPS is permitted in production."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFProtectionError("Target URL does not contain a valid hostname.")

    hostname_lower = hostname.lower()

    # Block well-known internal/cloud metadata hostnames
    if hostname_lower in CLOUD_METADATA_HOSTS:
        raise SSRFProtectionError(f"Access to cloud metadata host '{hostname}' is strictly forbidden.")

    # Block internal TLDs
    if "." in hostname_lower:
        tld = hostname_lower.split(".")[-1]
        if tld in DISALLOWED_TLDS:
            raise SSRFProtectionError(f"Access to private TLD '.{tld}' is forbidden.")

    # Determine default port if unspecified
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    # Resolve all IPv4 and IPv6 addresses
    resolved_ips: List[str] = []
    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        for entry in addr_info:
            ip_str = entry[4][0]
            ip_obj = ipaddress.ip_address(ip_str)

            if is_ip_forbidden(ip_obj):
                raise SSRFProtectionError(
                    f"Access to forbidden/private IP address '{ip_str}' resolved from '{hostname}' is denied.",
                    ip=ip_str,
                    host=hostname,
                )
            if ip_str not in resolved_ips:
                resolved_ips.append(ip_str)

    except socket.gaierror as e:
        raise SSRFProtectionError(f"DNS resolution failure for host '{hostname}': {e}", host=hostname)

    if not resolved_ips:
        raise SSRFProtectionError(f"Host '{hostname}' resolved to 0 accessible IP addresses.", host=hostname)

    return url_str.strip(), resolved_ips, port

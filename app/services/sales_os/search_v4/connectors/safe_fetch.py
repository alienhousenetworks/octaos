"""SSRF-conscious HTTP retrieval for locally fetched public search results."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

from app.services.web_ingestion.firecrawl_client import validate_target_url

_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_ALLOWED_PORTS = {80, 443}


def validate_public_fetch_url(url: str) -> str:
    """Validate each locally fetched URL and require every DNS answer to be public."""
    safe_url = validate_target_url(url)
    parsed = urlparse(safe_url)
    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not allowed.")
    if parsed.port is not None and parsed.port not in _ALLOWED_PORTS:
        raise ValueError("Only standard public web ports 80 and 443 are allowed.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("The URL does not contain a valid host.")

    try:
        answers = socket.getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError("The public host could not be resolved safely.") from exc

    addresses = {answer[4][0] for answer in answers if answer and answer[4]}
    if not addresses:
        raise ValueError("The public host did not resolve to an address.")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address.split("%", 1)[0])
        except ValueError as exc:
            raise ValueError("The public host resolved to an invalid address.") from exc
        if not ip.is_global:
            raise ValueError("The URL resolves to a non-public network address.")
    return safe_url


async def safe_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str],
    max_redirects: int = 4,
) -> httpx.Response:
    """Fetch public pages while validating every redirect before following it."""
    current = validate_public_fetch_url(url)
    for redirect_count in range(max_redirects + 1):
        response = await client.get(current, headers=headers, follow_redirects=False)
        if response.status_code not in _REDIRECT_STATUSES:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        if redirect_count >= max_redirects:
            raise ValueError("The source exceeded the permitted redirect limit.")
        current = validate_public_fetch_url(urljoin(current, location))
    raise ValueError("The source exceeded the permitted redirect limit.")

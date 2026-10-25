"""Pinned, bounded source retrieval and deterministic quote verification."""
from __future__ import annotations

import asyncio
import http.client
import ipaddress
import re
import socket
import ssl
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from typing import Callable
from urllib.parse import urlsplit, quote as url_quote

MAX_SOURCE_BYTES = 1_500_000
MAX_QUOTE_CHARS = 700
ALLOWED_CONTENT_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}


@dataclass(frozen=True)
class SourceVerification:
    source_url: str
    retrieved_at: str
    content_sha256: str | None
    quote: str
    verified: bool
    reason: str
    matched_start: int | None = None
    matched_end: int | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return ip.is_global


def _validate_and_resolve(url: str, resolver: Callable):
    try:
        parsed = urlsplit(str(url or "").strip())
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"}:
            return None, [], "unsupported_scheme"
        if not parsed.hostname or parsed.username or parsed.password:
            return None, [], "invalid_host_or_credentials"
        if (scheme == "https" and parsed.port not in (None, 443)) or (scheme == "http" and parsed.port not in (None, 80)):
            return None, [], "non_standard_port_blocked"
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
            return None, [], "local_hostname_blocked"
        try:
            ipaddress.ip_address(host)
            addresses = [host]
        except ValueError:
            try:
                addresses = sorted({
                    row[4][0] for row in resolver(
                        host, parsed.port or (443 if scheme == "https" else 80),
                        type=socket.SOCK_STREAM,
                    )
                })
            except (OSError, socket.gaierror, TypeError):
                return None, [], "dns_resolution_failed"
        if not addresses:
            return None, [], "dns_resolution_empty"
        if not all(_is_public_ip(address) for address in addresses):
            return None, [], "non_public_address_blocked"
        return parsed, addresses, "url_validated"
    except (ValueError, UnicodeError):
        return None, [], "malformed_url"


def validate_public_source_url(url: str, resolver: Callable = socket.getaddrinfo) -> tuple[bool, str]:
    """Validate syntax and require every resolved address to be globally routable."""
    _parsed, _addresses, reason = _validate_and_resolve(url, resolver)
    return reason == "url_validated", reason


def normalize_source_text(raw: str) -> str:
    """Convert basic HTML to searchable text without interpreting page scripts."""
    text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1\s*>", " ", raw or "")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def verify_quote(source_url: str, source_text: str, quote: str) -> SourceVerification:
    retrieved = datetime.now(timezone.utc).isoformat()
    clean_quote = " ".join(str(quote or "").split()).strip()
    clean_text = " ".join(str(source_text or "").split()).strip()
    fingerprint = sha256(clean_text.encode("utf-8")).hexdigest() if clean_text else None
    if not clean_quote:
        return SourceVerification(source_url, retrieved, fingerprint, "", False, "quote_missing")
    if len(clean_quote) > MAX_QUOTE_CHARS:
        return SourceVerification(source_url, retrieved, fingerprint, clean_quote[:MAX_QUOTE_CHARS], False, "quote_too_long")
    start = clean_text.casefold().find(clean_quote.casefold())
    if start < 0:
        return SourceVerification(source_url, retrieved, fingerprint, clean_quote, False, "quote_not_found_in_source")
    return SourceVerification(source_url, retrieved, fingerprint, clean_quote, True, "exact_quote_match", start, start + len(clean_quote))


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, address: str, port: int, timeout: float):
        super().__init__(host=host, port=port, timeout=timeout)
        self._pinned_address = address

    def connect(self):
        self.sock = socket.create_connection((self._pinned_address, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, port: int, timeout: float):
        super().__init__(host=host, port=port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = address

    def connect(self):
        raw = socket.create_connection((self._pinned_address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def _fetch_pinned_source(parsed, host: str, address: str, port: int, target: str):
    """Connect to the prevalidated IP while preserving Host and TLS SNI/cert checks."""
    connection = (
        _PinnedHTTPSConnection(host, address, port, timeout=8.0)
        if parsed.scheme.lower() == "https"
        else _PinnedHTTPConnection(host, address, port, timeout=8.0)
    )
    try:
        connection.request(
            "GET", target,
            headers={
                "Host": host if port in (80, 443) else f"{host}:{port}",
                "User-Agent": "OctaOS-SalesEvidence/1.0",
                "Accept": "text/html,text/plain,application/xhtml+xml",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        body = response.read(MAX_SOURCE_BYTES + 1)
        headers = {
            "content-type": response.getheader("content-type", ""),
            "content-encoding": response.getheader("content-encoding", "identity").lower(),
            "charset": response.headers.get_content_charset() or "utf-8",
        }
        return response.status, headers, body
    finally:
        connection.close()


async def fetch_and_verify_source(
    url: str,
    quote: str,
    *,
    resolver: Callable = socket.getaddrinfo,
) -> SourceVerification:
    """Fetch a public source with DNS-pinned TCP, bounded bytes, and no redirects."""
    retrieved = datetime.now(timezone.utc).isoformat()
    clean_quote = str(quote or "")[:MAX_QUOTE_CHARS]
    parsed, addresses, reason = _validate_and_resolve(url, resolver)
    if reason != "url_validated" or parsed is None:
        return SourceVerification(url, retrieved, None, clean_quote, False, reason)
    if not str(quote or "").strip():
        return SourceVerification(url, retrieved, None, "", False, "quote_missing")

    host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    path = url_quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    if parsed.query:
        path += "?" + parsed.query
    try:
        status, headers, body = await asyncio.to_thread(
            _fetch_pinned_source, parsed, host, addresses[0], port, path
        )
        if status in {301, 302, 303, 307, 308}:
            return SourceVerification(url, retrieved, None, clean_quote, False, "redirect_not_followed")
        if status != 200:
            return SourceVerification(url, retrieved, None, clean_quote, False, f"http_status_{status}")
        content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            return SourceVerification(url, retrieved, None, clean_quote, False, "unsupported_content_type")
        if headers.get("content-encoding", "identity") not in {"", "identity"}:
            return SourceVerification(url, retrieved, None, clean_quote, False, "compressed_response_blocked")
        if len(body) > MAX_SOURCE_BYTES:
            return SourceVerification(url, retrieved, None, clean_quote, False, "source_too_large")
        page_text = normalize_source_text(body.decode(headers.get("charset") or "utf-8", errors="replace"))
        result = verify_quote(url, page_text, quote)
        return SourceVerification(
            source_url=result.source_url,
            retrieved_at=retrieved,
            content_sha256=result.content_sha256,
            quote=result.quote,
            verified=result.verified,
            reason=result.reason,
            matched_start=result.matched_start,
            matched_end=result.matched_end,
        )
    except (OSError, ssl.SSLError, http.client.HTTPException, UnicodeError, ValueError):
        return SourceVerification(url, retrieved, None, clean_quote, False, "source_fetch_failed")

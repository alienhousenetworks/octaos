"""Source retrieval and quote verification for evidence-backed sales claims.

The verifier is deterministic: an LLM may propose a claim, but only a quote
actually present in retrieved source text can pass. Fetching is bounded and
rejects non-public destinations, credentials, redirects, and oversized pages.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from typing import Callable
from urllib.parse import urlsplit

import httpx

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
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        or ip.is_reserved or ip.is_unspecified
    )


def validate_public_source_url(
    url: str,
    resolver: Callable = socket.getaddrinfo,
) -> tuple[bool, str]:
    """Validate URL syntax and resolve every address before any outbound fetch."""
    try:
        parsed = urlsplit(str(url or "").strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            return False, "unsupported_scheme"
        if not parsed.hostname or parsed.username or parsed.password:
            return False, "invalid_host_or_credentials"
        if parsed.port not in (None, 80, 443):
            return False, "non_standard_port_blocked"
        host = parsed.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
            return False, "local_hostname_blocked"
        try:
            ipaddress.ip_address(host)
            addresses = [host]
        except ValueError:
            try:
                addresses = sorted({row[4][0] for row in resolver(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)})
            except (OSError, socket.gaierror, TypeError):
                return False, "dns_resolution_failed"
        if not addresses:
            return False, "dns_resolution_empty"
        if not all(_is_public_ip(address) for address in addresses):
            return False, "non_public_address_blocked"
        return True, "url_validated"
    except (ValueError, UnicodeError):
        return False, "malformed_url"


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


async def fetch_and_verify_source(
    url: str,
    quote: str,
    *,
    client: httpx.AsyncClient | None = None,
    resolver: Callable = socket.getaddrinfo,
) -> SourceVerification:
    """Fetch a bounded public source page and verify the quote in its body.

    Redirects are deliberately not followed: every hop must be validated by the
    caller rather than letting an untrusted source redirect the worker.
    """
    valid, reason = validate_public_source_url(url, resolver=resolver)
    retrieved = datetime.now(timezone.utc).isoformat()
    if not valid:
        return SourceVerification(url, retrieved, None, str(quote or "")[:MAX_QUOTE_CHARS], False, reason)
    owns_client = client is None
    session = client or httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=4.0), follow_redirects=False, headers={"User-Agent": "OctaOS-SalesEvidence/1.0"})
    try:
        response = await session.get(url, follow_redirects=False)
        if response.is_redirect:
            return SourceVerification(url, retrieved, None, str(quote or "")[:MAX_QUOTE_CHARS], False, "redirect_not_followed")
        if response.status_code != 200:
            return SourceVerification(url, retrieved, None, str(quote or "")[:MAX_QUOTE_CHARS], False, f"http_status_{response.status_code}")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            return SourceVerification(url, retrieved, None, str(quote or "")[:MAX_QUOTE_CHARS], False, "unsupported_content_type")
        body = response.content
        if len(body) > MAX_SOURCE_BYTES:
            return SourceVerification(url, retrieved, None, str(quote or "")[:MAX_QUOTE_CHARS], False, "source_too_large")
        encoding = response.encoding or "utf-8"
        page_text = normalize_source_text(body.decode(encoding, errors="replace"))
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
    except (httpx.HTTPError, UnicodeError, ValueError):
        return SourceVerification(url, retrieved, None, str(quote or "")[:MAX_QUOTE_CHARS], False, "source_fetch_failed")
    finally:
        if owns_client:
            await session.aclose()

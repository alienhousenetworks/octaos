"""Canonical URLs and source-host checks. Dedup ignores tracking parameters."""
import re
from urllib.parse import parse_qsl, urlencode, urlparse

_DROP_PARAMS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}
_BOARD_HOSTS = (
    "news.google.com",
    "news.ycombinator.com",
    "reddit.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "duckduckgo.com",
    "google.com",
    "wikipedia.org",
    "youtube.com",
)


def host_of(url: str) -> str:
    hostname = (urlparse(url or "").hostname or "").lower()
    return hostname.removeprefix("www.")


def is_company_site(url: str) -> bool:
    host = host_of(url)
    if not host or "." not in host:
        return False
    return not host.endswith(_BOARD_HOSTS)


def canonical_url(url: str) -> str:
    raw = (url or "").strip()
    parsed = urlparse(raw)
    host = host_of(raw)
    if not host:
        return ""
    path = re.sub(r"/+$", "", parsed.path or "")
    kept = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        lowered = key.lower()
        if lowered in _DROP_PARAMS or lowered.startswith("utm_"):
            continue
        kept.append((lowered, value))
    query = urlencode(sorted(kept))
    base = f"{host}{path}"
    return f"{base}?{query}" if query else base


def dedupe_key(url: str) -> str:
    return canonical_url(url) or (url or "").strip().lower()

"""Canonical domain and email identity. Does not guess a domain from a company name."""
import re

_DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def canonical_domain(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = text.split("/")[0].split("?")[0].split("#")[0]
    if text.startswith("www."):
        text = text[4:]
    if "@" in text:
        text = text.split("@", 1)[1]
    text = text.strip(".")
    if not _DOMAIN_RE.match(text):
        return None
    return text


def domain_from_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return canonical_domain(email.split("@", 1)[1])

"""Reject invented sales contacts and keep email signatures on the sender."""
from __future__ import annotations

from typing import Iterable, Optional

INVENTED_EMAILS = {
    "lead@example.com",
    "none@example.com",
    "test@example.com",
    "user@example.com",
    "inbound@example.com",
}

INVENTED_NAMES = {
    "inbound lead",
    "interested prospect",
    "unknown",
    "unknown corp",
}


def is_invented_email(email: Optional[str]) -> bool:
    """True when the address is missing or one of the hard-coded placeholders."""
    if not email or "@" not in email:
        return True
    normalized = email.strip().lower()
    if normalized in INVENTED_EMAILS:
        return True
    local, _, domain = normalized.partition("@")
    if domain in {"example.com", "example.org", "example.net"} and local in {
        "lead", "none", "test", "user", "inbound", "contact",
    }:
        return True
    if domain == "whatsapp.com":
        return True
    return False


def is_invented_name(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in INVENTED_NAMES


def host_of(value: Optional[str]) -> Optional[str]:
    text = (value or "").strip().lower().rstrip(".")
    if not text:
        return None
    for token in text.replace("<", " ").replace(">", " ").split():
        candidate = token.strip(".,);")
        if "://" in candidate:
            candidate = candidate.split("://", 1)[1]
        candidate = candidate.split("/")[0].split("?")[0].split(":")[0]
        if candidate.startswith("www."):
            candidate = candidate[4:]
        if "." in candidate and " " not in candidate and "@" not in candidate:
            return candidate
    return None


def prospect_hosts(lead) -> list[str]:
    """Domains that belong to the prospect, not the sender."""
    hosts: list[str] = []
    email = getattr(lead, "email", None) or ""
    if "@" in email:
        hosts.append(email.split("@", 1)[1].lower())
    data = getattr(lead, "data", None) or {}
    if isinstance(data, dict):
        for key in ("website", "url", "domain"):
            host = host_of(str(data.get(key) or ""))
            if host:
                hosts.append(host)
        discovery = data.get("discovery") if isinstance(data.get("discovery"), dict) else {}
        host = host_of(str(discovery.get("evidence_url") or discovery.get("source_url") or ""))
        if host:
            hosts.append(host)
    return hosts


def correct_sender_signature(
    body: Optional[str],
    *,
    prospect_hosts: Iterable[str],
    sender_website: Optional[str],
) -> str:
    """Drop a closing line that is the prospect's own website.

    The sender website is appended only when the tenant profile has one.
    Existing wording above the signature is left as it is.
    """
    text = (body or "").strip()
    if not text:
        return ""
    blocked = {host_of(host) or host.strip().lower() for host in prospect_hosts}
    blocked.discard("")
    blocked.discard(None)
    sender_host = host_of(sender_website)
    if sender_host:
        blocked.discard(sender_host)

    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    removed_prospect_site = False
    if lines:
        last_host = host_of(lines[-1])
        if last_host and last_host in blocked:
            lines.pop()
            removed_prospect_site = True
            while lines and not lines[-1].strip():
                lines.pop()
    corrected = "\n".join(lines).strip()
    # Put the sender site back only when the prospect site was occupying that spot.
    if removed_prospect_site and sender_website and sender_host:
        corrected = f"{corrected}\n{sender_website.strip()}".strip()
    return corrected

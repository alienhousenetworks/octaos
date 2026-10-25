"""Evidence and authorization gates for Sales AI outbound actions.

These deterministic checks are deliberately conservative: missing evidence or
permission must remain a blocker rather than being inferred by an LLM.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

_PLACEHOLDER_NAMES = {
    "", "unknown", "unknown contact", "decision maker", "founder/owner",
    "prospect", "there", "n/a", "not available",
}


def has_real_contact_name(value: Any) -> bool:
    name = " ".join(str(value or "").split()).strip()
    return bool(name and name.casefold() not in _PLACEHOLDER_NAMES)


def assess_outreach_readiness(
    prospect: dict[str, Any],
    *,
    auto_send_enabled: bool,
    permission_state: str | None,
    suppressed: bool = False,
    human_approved: bool = False,
) -> dict[str, Any]:
    """Return an explainable send decision without attempting delivery."""
    contact = prospect.get("contact") if isinstance(prospect.get("contact"), dict) else {}
    blockers: list[str] = []

    if suppressed:
        blockers.append("suppressed")
    if not auto_send_enabled and not human_approved:
        blockers.append("automatic_sending_not_enabled")
    if (permission_state or "").strip().lower() != "granted":
        blockers.append("outbound_permission_not_granted")
    if not has_real_contact_name(contact.get("name")):
        blockers.append("contact_identity_unverified")
    if not (str(contact.get("email") or "").strip() or str(contact.get("phone") or "").strip()):
        blockers.append("no_contact_route")
    if str(prospect.get("contact_status") or "").upper() != "READY":
        blockers.append("contact_not_qualified_by_discovery")

    evidence_url = str(prospect.get("evidence_url") or "").strip()
    parsed_source = urlparse(evidence_url)
    evidence_url_valid = parsed_source.scheme in {"http", "https"} and bool(parsed_source.netloc)
    evidence_quote = str(prospect.get("evidence_quote") or "").strip()
    buying_signal = str(prospect.get("buying_signal") or "").strip()
    news = prospect.get("news") or []
    jobs = prospect.get("jobs") or []

    def has_sourced_signal(items: Any) -> bool:
        if not isinstance(items, list):
            return False
        for item in items:
            if not isinstance(item, dict):
                continue
            source_url = str(item.get("url") or item.get("source_url") or "").strip()
            claim_text = str(item.get("title") or item.get("summary") or item.get("description") or "").strip()
            parsed = urlparse(source_url)
            if claim_text and parsed.scheme in {"http", "https"} and parsed.netloc:
                return True
        return False

    if not evidence_url_valid:
        blockers.append("source_url_missing_or_invalid")
    # Generated pain-point guesses alone are not evidence for outbound claims.
    if not any((evidence_quote, buying_signal, has_sourced_signal(news), has_sourced_signal(jobs))):
        blockers.append("need_evidence_missing")

    return {
        "ready": not blockers,
        "status": "authorized" if not blockers else "blocked",
        "blockers": blockers,
        "evidence_url_present": evidence_url_valid,
        "contact_identity_present": has_real_contact_name(contact.get("name")),
    }



def assess_channel_authorization(
    settings: dict[str, Any] | None,
    channel: str,
    *,
    recipient_opt_in: bool = False,
    human_approved: bool = False,
) -> dict[str, Any]:
    """Final defense-in-depth gate used by dispatchers and cadence workers."""
    config = settings if isinstance(settings, dict) else {}
    normalized_channel = (channel or "email").strip().lower()
    blockers: list[str] = []
    if not bool(config.get("sales_ai_auto_send_enabled", False)) and not human_approved:
        blockers.append("automatic_sending_not_enabled")
    if str(config.get("outbound_permission_state") or "").strip().lower() != "granted":
        blockers.append("outbound_permission_not_granted")
    if normalized_channel == "whatsapp":
        if str(config.get("whatsapp_permission_state") or "").strip().lower() != "granted":
            blockers.append("whatsapp_permission_not_granted")
        if not recipient_opt_in:
            blockers.append("recipient_whatsapp_opt_in_missing")
    return {
        "ready": not blockers,
        "status": "authorized" if not blockers else "blocked",
        "channel": normalized_channel,
        "blockers": blockers,
    }

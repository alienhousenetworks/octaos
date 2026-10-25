"""Evidence and authorization gates for Sales AI outbound actions.

These deterministic checks are deliberately conservative: missing evidence or
permission must remain a blocker rather than being inferred by an LLM.
"""
from __future__ import annotations

from typing import Any

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
) -> dict[str, Any]:
    """Return an explainable send decision without attempting delivery."""
    contact = prospect.get("contact") if isinstance(prospect.get("contact"), dict) else {}
    blockers: list[str] = []

    if suppressed:
        blockers.append("suppressed")
    if not auto_send_enabled:
        blockers.append("automatic_sending_not_enabled")
    if (permission_state or "").strip().lower() != "granted":
        blockers.append("outbound_permission_not_granted")
    if not has_real_contact_name(contact.get("name")):
        blockers.append("contact_identity_unverified")
    if not (str(contact.get("email") or "").strip() or str(contact.get("phone") or "").strip()):
        blockers.append("no_contact_route")

    evidence_url = str(prospect.get("evidence_url") or "").strip()
    evidence_quote = str(prospect.get("evidence_quote") or "").strip()
    buying_signal = str(prospect.get("buying_signal") or "").strip()
    pain_points = prospect.get("pain_points") or []
    news = prospect.get("news") or []
    jobs = prospect.get("jobs") or []
    if not evidence_url:
        blockers.append("source_url_missing")
    if not any((evidence_quote, buying_signal, pain_points, news, jobs)):
        blockers.append("need_evidence_missing")

    return {
        "ready": not blockers,
        "status": "authorized" if not blockers else "blocked",
        "blockers": blockers,
        "evidence_url_present": bool(evidence_url),
        "contact_identity_present": has_real_contact_name(contact.get("name")),
    }

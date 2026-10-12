"""Tiers 0–6. Absence of evidence stays unknown unless a check can prove absence."""
import re
from typing import Any, Callable

ROLE_LOCAL_PARTS = {
    "info", "sales", "admin", "contact", "hello", "support", "office", "team",
    "enquiries", "enquiry", "noreply", "no-reply", "careers", "jobs",
}
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "yopmail.com", "trashmail.com", "guerrillamailblock.com",
}
BASIS_REQUIRED_JURISDICTIONS = {"EU", "EEA", "UK", "GB"}
NURTURE_SCORE = 60.0

TIER6_STATES = (
    "READY",
    "NEEDS_RESEARCH",
    "NEEDS_VERIFICATION",
    "NEEDS_APPROVAL",
    "NURTURE",
    "SUPPRESSED",
    "DO_NOT_CONTACT",
)


def _tier(tier: int, status: str, verifier: str, reason: str | None = None, score: float | None = None, **details: Any) -> dict:
    return {
        "tier": tier,
        "status": status,
        "verifier": verifier,
        "failure_reason": reason,
        "score": score,
        "details": details,
    }


def tier0_identity(
    *,
    canonical_domain: str | None,
    email: str | None,
    duplicate_email: bool = False,
    provider_ids: dict | None = None,
) -> dict:
    if duplicate_email:
        return _tier(0, "failed", "identity", "duplicate_contact", email=email)
    if not canonical_domain and not (provider_ids or {}):
        return _tier(0, "unknown", "identity", "identity_unresolved")
    return _tier(0, "passed", "identity", domain=canonical_domain)


def tier1_syntax(email: str | None, mx_lookup: Callable[[str], dict] | None = None) -> dict:
    if not email:
        return _tier(1, "unknown", "syntax", "email_absent")
    try:
        from email_validator import EmailNotValidError, validate_email
        validated = validate_email(email, check_deliverability=False)
        normalized = validated.normalized
    except Exception as exc:
        return _tier(1, "failed", "syntax", "invalid_syntax", error=str(exc)[:200])
    local, domain = normalized.split("@", 1)
    local_key = local.split("+", 1)[0].lower()
    if domain.lower() in DISPOSABLE_DOMAINS:
        return _tier(1, "failed", "syntax", "disposable_domain", email=normalized)
    flags = {"role_account": local_key in ROLE_LOCAL_PARTS}
    mx_status = "not_checked"
    if mx_lookup is not None:
        looked = mx_lookup(domain)
        mx_status = looked.get("status", "unknown")
        if mx_status == "absent":
            return _tier(1, "failed", "dns", "domain_nxdomain", email=normalized)
    return _tier(1, "passed", "syntax", email=normalized, mx_status=mx_status, **flags)


def tier2_deliverability(verifier_result: dict | None) -> dict:
    if not verifier_result:
        return _tier(2, "unknown", "deliverability", "no_verifier_configured")
    status = verifier_result.get("status")
    verifier = verifier_result.get("verifier") or "deliverability"
    details = {
        key: value
        for key, value in verifier_result.items()
        if key not in {"status", "verifier", "score", "reason"}
    }
    if status == "temporary_failure":
        return _tier(2, "unknown", verifier, "temporary_failure", **details)
    if status == "verified":
        return _tier(2, "passed", verifier, score=verifier_result.get("score"), **details)
    if status == "failed":
        return _tier(2, "failed", verifier, verifier_result.get("reason") or "undeliverable", **details)
    return _tier(2, "unknown", verifier, "verifier_inconclusive", **details)


def tier3_employment(*, has_current_role_evidence: bool | None) -> dict:
    if has_current_role_evidence is True:
        return _tier(3, "passed", "employment")
    if has_current_role_evidence is False:
        return _tier(3, "failed", "employment", "not_current_employee")
    return _tier(3, "unknown", "employment", "employment_unknown")


def tier4_compliance(
    *,
    suppressed: bool,
    suppression_reason: str | None = None,
    permission_state: str = "unknown",
    jurisdiction: str | None = None,
    legal_basis: str | None = None,
    channel: str = "email",
) -> dict:
    if suppressed:
        return _tier(4, "failed", "suppression", suppression_reason or "suppressed", channel=channel)
    jurisdiction_key = (jurisdiction or "").upper()
    if jurisdiction_key in BASIS_REQUIRED_JURISDICTIONS and not legal_basis:
        return _tier(4, "approval_required", "permission", "lawful_basis_missing", jurisdiction=jurisdiction_key, channel=channel)
    if permission_state == "denied":
        return _tier(4, "failed", "permission", "permission_denied", channel=channel)
    if permission_state == "approval_required":
        return _tier(4, "approval_required", "permission", "approval_required", channel=channel)
    if permission_state == "granted":
        return _tier(4, "passed", "permission", channel=channel, legal_basis=legal_basis)
    return _tier(4, "unknown", "permission", "permission_unknown", channel=channel)


def tier6_state(
    *,
    tiers: list[dict],
    score: float | None,
    suppressed: bool,
    suppression_reason: str | None = None,
) -> str:
    reason = (suppression_reason or "").lower()
    if suppressed and reason in {"manual_dnc", "complaint", "do_not_contact"}:
        return "DO_NOT_CONTACT"
    if suppressed or any(item["tier"] == 4 and item["status"] == "failed" and item["verifier"] == "suppression" for item in tiers):
        return "SUPPRESSED"
    if any(item["tier"] == 4 and item["status"] == "approval_required" for item in tiers):
        return "NEEDS_APPROVAL"
    if any(item["tier"] == 0 and item["status"] == "unknown" for item in tiers):
        return "NEEDS_RESEARCH"
    if any(item["tier"] in {1, 2} and item["status"] == "failed" for item in tiers):
        return "NEEDS_VERIFICATION"
    if any(item["tier"] == 2 and item["status"] == "unknown" for item in tiers):
        return "NEEDS_VERIFICATION"
    if any(item["tier"] == 3 and item["status"] != "passed" for item in tiers):
        return "NEEDS_RESEARCH"
    if any(item["tier"] == 4 and item["status"] != "passed" for item in tiers):
        return "NEEDS_APPROVAL"
    if score is None or score < NURTURE_SCORE:
        return "NURTURE"
    return "READY"


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_looks_present(email: str | None) -> bool:
    return bool(email and _EMAIL_RE.match(email))

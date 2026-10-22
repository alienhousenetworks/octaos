"""Grounded record copilot.

Answers use only values on the record. Missing numbers stay missing.
A stored score is reported as stored, not recalculated.
"""
from __future__ import annotations

from typing import Any

from app.services.sales_os.verticals.registry import get_pack, terminology_for

_REFUSAL_HINTS = (
    "approve the loan",
    "approved loan",
    "credit decision",
    "loan is approved",
    "kyc approved",
    "eligibility approved",
    "bind coverage",
    "policy is issued",
    "policy issued",
    "medical claim",
    "clinical efficacy",
    "prescribe",
    "guarantee the award",
    "improper influence",
    "hold unit without deposit",
    "hold without deposit",
    "mark unit held",
    "mark unit booked",
    "invent inventory",
)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _evidence(claim: str, source: str, observed_at: str | None = None) -> dict[str, Any]:
    return {
        "claim": claim,
        "source": source,
        "verification_status": "UNVERIFIED",
        "note": "Stored on the record. Not re-checked against an external source.",
        "observed_at": observed_at,
    }


def advise_record(record: dict[str, Any], pack_id: str | None, question: str) -> dict[str, Any]:
    pack = get_pack(pack_id) if pack_id else None
    terms = terminology_for(pack_id)
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    asked = (question or "").strip() or "What should we do next with this customer?"
    lowered = asked.lower()

    evidence: list[dict[str, Any]] = []
    unknowns: list[str] = []

    def cite(label: str, value: Any, source: str) -> str | None:
        text = _text(value)
        if text is None:
            unknowns.append(label)
            return None
        evidence.append(_evidence(f"{label}: {text}", source, _text(record.get("updated_at"))))
        return text

    name = cite(terms["contact"], record.get("name"), "lead.name")
    company = cite(terms["account"], record.get("company"), "lead.company")
    email = cite("Email", record.get("email") or record.get("company_email"), "lead.email")
    phone = cite("Phone", record.get("phone") or record.get("mobile_no"), "lead.phone")
    status = cite("Status", record.get("status"), "lead.status")
    source = cite("Source", record.get("source"), "lead.source")
    why = cite("Why this account", record.get("why") or data.get("why_now"), "lead.why")
    evidence_url = cite("Evidence URL", data.get("evidence_url") or record.get("evidence_url"), "lead.evidence_url")
    consent = _text(data.get("permission_state") or data.get("consent"))
    if consent:
        evidence.append(_evidence(f"Contact permission stored as {consent}", "lead.data.permission_state"))
    else:
        unknowns.append("Contact permission")

    sent_flag = data.get("sent_actual")
    if sent_flag is True:
        evidence.append(
            _evidence(
                "The record has sent_actual set. That is not a delivery receipt.",
                "lead.data.sent_actual",
            )
        )
    else:
        unknowns.append("Delivery receipt")

    breakdown = data.get("scoring_breakdown")
    score = record.get("score")
    if isinstance(breakdown, dict) and breakdown:
        readiness = {
            "label": "Stored score",
            "value": str(score) if isinstance(score, (int, float)) else None,
            "source": "lead.data.scoring_breakdown",
            "verification_status": "PARTIALLY_VERIFIED",
            "note": "A breakdown is stored. This copilot did not recalculate it.",
        }
        evidence.append(_evidence(f"Scoring breakdown keys: {', '.join(sorted(breakdown))}", "lead.data.scoring_breakdown"))
    elif isinstance(score, (int, float)) and score > 0:
        readiness = {
            "label": "Stored score",
            "value": str(score),
            "source": "lead.score",
            "verification_status": "UNVERIFIED",
            "note": "No scoring breakdown is stored with this number.",
        }
    else:
        readiness = {
            "label": "Not scored",
            "value": None,
            "source": "lead.score",
            "verification_status": "UNAVAILABLE",
            "note": "No usable score is stored. Missing is not zero.",
        }
        unknowns.append("Qualification score")

    deal_health = {
        "label": "Status",
        "value": status or None,
        "source": "lead.status",
        "verification_status": "UNVERIFIED" if status else "UNAVAILABLE",
        "note": "Stage label from the record. Not a predicted win probability.",
    }

    if pack:
        for question_text in pack["qualification"]:
            if question_text.lower() not in lowered and not _answered(question_text, record, data):
                unknowns.append(question_text)

    refused = _refused(pack, lowered)
    asks_missing_metric = any(
        phrase in lowered
        for phrase in ("attendance", "awaiting confirmation", "open rate", "revenue forecast")
    ) and not any(key in data for key in ("attendance", "open_rate", "forecast"))

    if refused:
        answer = refused
        recommendation = "Stop and hand this to the person authorized for that decision."
        actions: list[dict[str, Any]] = []
    elif asks_missing_metric:
        answer = "That figure is not stored on this record, so it cannot be used."
        recommendation = "Collect the figure from the system that measured it before acting on it."
        actions = []
    else:
        answer = _answer(asked, name, company, email, phone, status, why, evidence_url, terms)
        recommendation = _next_action(email, phone, status, why, consent, data)
        actions = _actions(email, data)
        if pack and pack.get("id") == "real_estate":
            actions = [
                {
                    "id": "find_matching_properties",
                    "label": "Match available properties",
                    "preview": f"Evaluate real-time available units against {name or 'buyer'}'s budget and configuration preferences.",
                    "executes": True,
                    "requires_confirmation": False,
                },
                {
                    "id": "schedule_site_visit",
                    "label": "Schedule site visit",
                    "preview": f"Book private property showing for {name or 'this inquiry'} at {company or 'selected project'}.",
                    "executes": True,
                    "requires_confirmation": True,
                },
                {
                    "id": "request_unit_hold",
                    "label": "Request unit hold",
                    "preview": "Initiate temporary unit reservation subject to authoritative inventory lock.",
                    "executes": True,
                    "requires_confirmation": True,
                },
                {
                    "id": "create_booking_application",
                    "label": "Create booking contract",
                    "preview": "Prepare binding booking application with price snapshot and milestone payment plan.",
                    "executes": True,
                    "requires_confirmation": True,
                },
                {
                    "id": "verify_financing",
                    "label": "Verify mortgage readiness",
                    "preview": "Review buyer pre-approval or financing qualification evidence.",
                    "executes": False,
                    "requires_confirmation": False,
                },
            ] + actions


    known = len(evidence)
    if refused or asks_missing_metric:
        confidence = "low"
    elif known >= 4 and (email or phone) and why:
        confidence = "high"
    elif known >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "record": {
            "id": record.get("id"),
            "name": name,
            "company": company,
            "status": status,
        },
        "pack": None
        if pack is None
        else {"id": pack["id"], "name": pack["name"], "version": pack["version"]},
        "terminology": terms,
        "question": asked,
        "answer": answer,
        "recommendation": recommendation,
        "confidence": confidence,
        "confidence_basis": f"{known} stored field(s) cited. Confidence is coverage of the record, not a win probability.",
        "readiness": readiness,
        "deal_health": deal_health,
        "evidence": evidence,
        "unknowns": _unique(unknowns),
        "actions": actions,
        "prohibited": list((pack or {}).get("ai_guidance", {}).get("prohibited") or []),
        "invented": False,
    }


def _answered(question_text: str, record: dict[str, Any], data: dict[str, Any]) -> bool:
    blob = " ".join(
        _text(part) or ""
        for part in (
            record.get("why"),
            record.get("need_of_what"),
            record.get("target_context"),
            data.get("why_now"),
            data.get("qualification_reason"),
        )
    ).lower()
    tokens = [word for word in question_text.lower().split() if len(word) > 4]
    return bool(tokens) and any(word in blob for word in tokens[:2])


def _refused(pack: dict[str, Any] | None, lowered: str) -> str | None:
    hints = list(_REFUSAL_HINTS)
    if pack:
        hints.extend(item.lower() for item in pack["ai_guidance"]["prohibited"])
    for hint in hints:
        if hint and hint in lowered:
            return (
                "This request is outside what Sales AI may decide. "
                "The record was not changed."
            )
    if ("hold" in lowered and "unit" in lowered) or "without deposit" in lowered:
        return (
            "This request is outside what Sales AI may decide. "
            "The record was not changed."
        )
    if "mark" in lowered and "sent" in lowered:
        return "A send is recorded only after the delivery service confirms it. This copilot will not mark it sent."
    return None


def _answer(
    asked: str,
    name: str | None,
    company: str | None,
    email: str | None,
    phone: str | None,
    status: str | None,
    why: str | None,
    evidence_url: str | None,
    terms: dict[str, str],
) -> str:
    who = name or f"This {terms['lead'].lower()}"
    where = f" at {company}" if company else ""
    parts = [f"{who}{where} is the open record."]
    if status:
        parts.append(f"Stored status is {status}.")
    if email:
        parts.append(f"Email on the record is {email}.")
    elif phone:
        parts.append(f"Phone on the record is {phone}.")
    else:
        parts.append("No email or phone is stored.")
    if why:
        parts.append(f"Stored context: {why}")
    if evidence_url:
        parts.append(f"A source URL is stored: {evidence_url}. It was not re-fetched.")
    if asked.lower().startswith("what should"):
        parts.append("The recommendation below uses only these stored fields.")
    return " ".join(parts)


def _next_action(
    email: str | None,
    phone: str | None,
    status: str | None,
    why: str | None,
    consent: str | None,
    data: dict[str, Any],
) -> str:
    if not email and not phone:
        return "Capture a real email, phone, or link that was copied from a source before outreach."
    if consent is None:
        return "Confirm contact permission before any external message. Permission is not stored."
    if not why:
        return "Add the business reason for this conversation before changing stage."
    draft = _text(data.get("draft_body"))
    if draft and data.get("sent_actual") is not True:
        return "A draft is stored. Review it before anyone sends it."
    if status in {"contacted", "meeting_scheduled"}:
        return "Review the timeline, then decide whether a meeting should be booked."
    return "Review the stored context and choose a next step. Stage was not changed."


def _actions(email: str | None, data: dict[str, Any]) -> list[dict[str, Any]]:
    draft = _text(data.get("draft_body"))
    actions = [
        {
            "id": "review_follow_up",
            "label": "Review follow-up",
            "preview": "Open the stored draft." if draft else "Ask the composer for a draft. Nothing is sent.",
            "executes": False,
            "requires_confirmation": True,
        },
        {
            "id": "prepare_proposal",
            "label": "Prepare proposal",
            "preview": "Open deal desk. No price is calculated from this panel.",
            "executes": False,
            "requires_confirmation": True,
        },
        {
            "id": "schedule_meeting",
            "label": "Schedule meeting",
            "preview": "Shows a confirmation step. The meeting service runs only after that confirmation."
            + ("" if email else " No email is stored, so booking may fail."),
            "executes": False,
            "requires_confirmation": True,
        },
    ]
    return actions


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered

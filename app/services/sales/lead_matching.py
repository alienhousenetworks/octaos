"""Match inbound senders to active sales leads."""
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.verticals import Lead

ACTIVE_SALES_STATUSES = frozenset(
    {"captured", "enriched", "contacted", "meeting_scheduled", "replied"}
)

EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def normalize_email(value: str) -> str:
    if not value:
        return ""
    match = EMAIL_RE.search(value.strip().lower())
    return match.group(0) if match else value.strip().lower()


def normalize_phone(value: str) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) > 10 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def find_lead_for_inbound(
    db: Session,
    tenant_id: str,
    channel: str,
    sender: str,
) -> Optional[Lead]:
    sender_email = normalize_email(sender) if channel == "email" else ""
    sender_phone = normalize_phone(sender) if channel == "whatsapp" else ""

    leads: List[Lead] = (
        db.query(Lead)
        .filter(Lead.tenant_id == tenant_id, Lead.status.in_(ACTIVE_SALES_STATUSES))
        .all()
    )

    for lead in leads:
        if channel == "email" and lead.email:
            if normalize_email(lead.email) == sender_email:
                return lead
        if channel == "whatsapp" and lead.phone:
            if normalize_phone(lead.phone) == sender_phone:
                return lead
        # Email channel but sender is phone-only lead record
        if channel == "email" and lead.phone and sender_phone:
            if normalize_phone(lead.phone) == sender_phone:
                return lead

    return None

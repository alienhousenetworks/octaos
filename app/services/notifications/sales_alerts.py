"""Telegram alerts and reminder helpers for the Sales pipeline."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from asgiref.sync import async_to_sync

from app.models.verticals import Lead
from app.services.notifications.telegram import send_telegram_notification


def default_meeting_start_utc() -> datetime:
    start = datetime.now(timezone.utc) + timedelta(days=1)
    return start.replace(hour=10, minute=0, second=0, microsecond=0)


def meeting_start_from_lead(lead: Lead) -> Optional[datetime]:
    raw = (lead.data or {}).get("meeting_starts_at")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def send_sales_telegram(db: Session, tenant_id: str, message: str) -> bool:
    return async_to_sync(send_telegram_notification)(
        db, tenant_id, message, parse_mode=None
    )


def format_meeting_booked_message(lead: Lead, meeting_time: str, meet_url: str) -> str:
    return (
        "Sales meeting booked\n"
        f"Lead: {lead.name} ({lead.company})\n"
        f"Email: {lead.email}\n"
        f"When: {meeting_time}\n"
        f"Link: {meet_url}"
    )


def format_meeting_reminder_1h(lead: Lead, meeting_time: str, meet_url: str) -> str:
    return (
        "Reminder: sales call in about 1 hour\n"
        f"Lead: {lead.name} ({lead.company})\n"
        f"When: {meeting_time}\n"
        f"Link: {meet_url or 'N/A'}"
    )


def format_meeting_reminder_tomorrow(lead: Lead, meeting_time: str, meet_url: str) -> str:
    return (
        "Reminder: sales meeting tomorrow\n"
        f"Lead: {lead.name} ({lead.company})\n"
        f"When: {meeting_time}\n"
        f"Link: {meet_url or 'N/A'}"
    )


def format_followup_reminder(lead: Lead) -> str:
    return (
        "Follow-up reminder\n"
        f"No meeting booked yet for {lead.name} ({lead.company}).\n"
        f"Outreach was sent 24+ hours ago — consider a follow-up email or call."
    )

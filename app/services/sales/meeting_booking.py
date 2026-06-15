"""Book sales meetings on Google Calendar (or placeholder) and notify Telegram."""
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential
from app.models.verticals import Lead
from app.models.teams import AgentMetric
from app.services.notifications.sales_alerts import (
    default_meeting_start_utc,
    format_meeting_booked_message,
    send_sales_telegram,
)


def create_google_calendar_event(
    creds_dict: dict, attendee_email: str, summary: str, description: str
) -> Tuple[Optional[str], Optional[datetime]]:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes"),
    )
    service = build("calendar", "v3", credentials=creds)
    start_time = datetime.now(timezone.utc) + timedelta(days=1)
    start_time = start_time.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time.isoformat().replace("+00:00", "Z")},
        "end": {"dateTime": end_time.isoformat().replace("+00:00", "Z")},
        "attendees": [{"email": attendee_email}],
        "conferenceData": {
            "createRequest": {
                "requestId": f"{random.randint(100000, 999999)}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    event_result = service.events().insert(
        calendarId="primary", body=event, conferenceDataVersion=1
    ).execute()
    return event_result.get("hangoutLink"), start_time


def book_meeting_for_lead(
    db: Session,
    tenant_id: str,
    lead: Lead,
    *,
    tool: str = "google_calendar",
    suggested_time: Optional[str] = None,
    log_activity: Optional[Callable[[str, str, str], None]] = None,
) -> bool:
    """Returns True if a meeting was booked."""
    if lead.status == "meeting_scheduled":
        return False

    calendar_cred = (
        db.query(APICredential)
        .filter_by(tenant_id=tenant_id, provider="google_calendar")
        .first()
    )
    if not calendar_cred or not calendar_cred.encrypted_key.strip():
        raise ValueError("No Google Calendar credentials found. Please connect Google Workspace under Platform Setup -> API Settings to schedule calendar events.")

    meeting_time = suggested_time or "Next business day at 10:00 AM UTC"
    meet_url = ""
    meeting_starts_at = default_meeting_start_utc()
    calendar_booked = False

    try:
        creds_dict = json.loads(decrypt_api_key(calendar_cred.encrypted_key))
        actual_meet_url, event_start = create_google_calendar_event(
            creds_dict,
            lead.email or f"{lead.phone}@placeholder.local",
            f"Meeting: {lead.company} / {lead.name}",
            f"Sales discussion with {lead.name}",
        )
        meet_url = actual_meet_url or f"https://meet.google.com/abc-{lead.id[:8]}"
        if event_start:
            meeting_starts_at = event_start
            meeting_time = event_start.strftime("%A %d %b %Y, %H:%M UTC")
        calendar_booked = True
    except Exception as exc:
        raise ValueError(f"Google Calendar API Error: {exc}. Please verify your Google Workspace connection.")

    lead.status = "meeting_scheduled"
    lead.data = {
        **(lead.data or {}),
        "meeting_time": meeting_time,
        "meeting_link": meet_url,
        "meeting_starts_at": meeting_starts_at.isoformat(),
        "calendar_booked": calendar_booked,
        "reminder_1h_sent": False,
        "reminder_24h_sent": False,
        "telegram_meeting_booked_sent": False,
    }

    booked_msg = format_meeting_booked_message(lead, meeting_time, meet_url)
    if send_sales_telegram(db, tenant_id, booked_msg):
        lead.data["telegram_meeting_booked_sent"] = True

    metric_roi = (
        db.query(AgentMetric)
        .filter_by(tenant_id=tenant_id, metric_name="revenue_impact")
        .first()
    )
    if not metric_roi:
        metric_roi = AgentMetric(tenant_id=tenant_id, metric_name="revenue_impact", value=0.0)
        db.add(metric_roi)
    metric_roi.value += 1500.0

    if log_activity:
        log_activity(
            "Meeting Booked",
            f"Meeting with {lead.name} ({lead.company}) for {meeting_time}. Meet: {meet_url}",
            "success",
        )
    db.commit()
    return True

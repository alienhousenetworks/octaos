"""Book sales meetings on Google Calendar (or placeholder) and notify Telegram."""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential
from app.models.verticals import Lead
from app.models.teams import AgentMetric
from app.services.notifications.sales_alerts import (
    format_meeting_booked_message,
    send_sales_telegram,
)


def create_google_calendar_event(
    creds_dict: dict,
    attendee_email: str,
    summary: str,
    description: str,
    start_time: datetime | None = None,
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
    if start_time is None:
        raise ValueError("An explicit prospect-agreed meeting time is required; no default slot will be invented.")
    if start_time.tzinfo is None:
        raise ValueError("Meeting time must include a timezone.")
    start_time = start_time.astimezone(timezone.utc)
    end_time = start_time + timedelta(hours=1)
    
    # Check calendar availability using freeBusy
    body = {
        "timeMin": start_time.isoformat().replace("+00:00", "Z"),
        "timeMax": end_time.isoformat().replace("+00:00", "Z"),
        "items": [{"id": "primary"}]
    }
    events_result = service.freebusy().query(body=body).execute()
    calendars = events_result.get("calendars", {})
    primary = calendars.get("primary", {})
    busy = primary.get("busy", [])
    if len(busy) > 0:
        raise ValueError("Calendar slot is not available. The primary calendar has conflicting events.")
        
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time.isoformat().replace("+00:00", "Z")},
        "end": {"dateTime": end_time.isoformat().replace("+00:00", "Z")},
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    if attendee_email:
        event["attendees"] = [{"email": attendee_email}]
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
    import re
    if not lead.email or not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", lead.email):
        raise ValueError(f"Invalid email address format for lead: '{lead.email}'")
        
    if lead.status == "meeting_scheduled":
        return False

    calendar_cred = (
        db.query(APICredential)
        .filter_by(tenant_id=tenant_id, provider="google_calendar")
        .first()
    )
    if not calendar_cred or not calendar_cred.encrypted_key.strip():
        raise ValueError("No Google Calendar credentials found. Please connect Google Workspace under Platform Setup -> API Settings to schedule calendar events.")

    if not suggested_time:
        raise ValueError("An explicit prospect-agreed meeting time is required before booking.")
    try:
        parsed_time = datetime.fromisoformat(str(suggested_time).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Meeting time must be an ISO-8601 timestamp with timezone, e.g. 2026-10-26T10:00:00+05:30.") from exc
    if parsed_time.tzinfo is None:
        raise ValueError("Meeting time must include a timezone.")
    meeting_starts_at = parsed_time.astimezone(timezone.utc)
    if meeting_starts_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError("Meeting time must be at least five minutes in the future.")

    meeting_time = meeting_starts_at.strftime("%A %d %b %Y, %H:%M UTC")
    meet_url = ""
    calendar_booked = False

    try:
        creds_dict = json.loads(decrypt_api_key(calendar_cred.encrypted_key))
        actual_meet_url, event_start = create_google_calendar_event(
            creds_dict,
            lead.email,
            f"Meeting: {lead.company} / {lead.name}",
            f"Sales discussion with {lead.name}",
            start_time=meeting_starts_at,
        )
        meet_url = actual_meet_url
        if event_start:
            meeting_starts_at = event_start
            meeting_time = event_start.strftime("%A %d %b %Y, %H:%M UTC")
        calendar_booked = True
    except Exception as exc:
        raise ValueError(f"Google Calendar API Error: {exc}. Please verify your Google Workspace connection.")

    lead.status = "meeting_scheduled"
    
    # Generate Pre-Meeting Brief for the Account Executive
    brief = {
        "account_name": lead.company or "Target Account",
        "prospect_name": lead.name,
        "prospect_email": lead.email,
        "pain_points": lead.target_context or (lead.data or {}).get("pain_points") or "Not recorded; confirm with the prospect.",
        "qualification_notes": lead.why or "No qualification rationale is recorded.",
        "meeting_time": meeting_time,
        "meeting_link": meet_url,
        "conversation_summary": f"Calendar event created for a sales discussion with {lead.name} at {lead.company}.",
        "recommended_agenda": [
            "1. Confirm the prospect's stated business priorities",
            "2. Validate the problem and desired outcome",
            "3. Discuss the relevant offering and evidence-backed fit",
            "4. Agree next steps and required stakeholders"
        ],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    lead.data = {
        **(lead.data or {}),
        "meeting_time": meeting_time,
        "meeting_link": meet_url,
        "meeting_starts_at": meeting_starts_at.isoformat(),
        "calendar_booked": calendar_booked,
        "reminder_1h_sent": False,
        "reminder_24h_sent": False,
        "telegram_meeting_booked_sent": False,
        "pre_meeting_brief": brief,
    }

    booked_msg = format_meeting_booked_message(lead, meeting_time, meet_url)
    if send_sales_telegram(db, tenant_id, booked_msg):
        lead.data["telegram_meeting_booked_sent"] = True

    meeting_metric = (
        db.query(AgentMetric)
        .filter_by(tenant_id=tenant_id, metric_name="meetings_booked")
        .first()
    )
    if not meeting_metric:
        meeting_metric = AgentMetric(tenant_id=tenant_id, metric_name="meetings_booked", value=0.0)
        db.add(meeting_metric)
    meeting_metric.value += 1.0

    if log_activity:
        log_activity(
            "Meeting Booked",
            f"Meeting with {lead.name} ({lead.company}) for {meeting_time}. Meet: {meet_url}",
            "success",
        )
    db.commit()
    return True

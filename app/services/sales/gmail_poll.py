"""Poll Gmail inbox for replies to sales outreach threads."""
import base64
import json
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential
from app.models.verticals import Lead
from app.services.sales.lead_matching import normalize_email


def _gmail_service(creds_dict: dict):
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
    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts") or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts") or []:
        text = _decode_body(part)
        if text:
            return text
    return ""


def _header(headers: List[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def poll_gmail_inbox_for_sales(db: Session, tenant_id: str) -> int:
    """
    Fetch recent inbox messages and queue sales inbound tasks for matching leads.
    Returns count of newly queued messages.
    """
    cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="gmail").first()
    if not cred or not cred.encrypted_key:
        return 0

    try:
        creds_dict = json.loads(decrypt_api_key(cred.encrypted_key))
        service = _gmail_service(creds_dict)
    except Exception as exc:
        print(f"Gmail poll init failed for {tenant_id}: {exc}")
        return 0

    # Threads we already know about from outbound
    leads = (
        db.query(Lead)
        .filter(
            Lead.tenant_id == tenant_id,
            Lead.status.in_(("contacted", "replied", "meeting_scheduled", "enriched")),
        )
        .all()
    )
    lead_emails = {normalize_email(l.email) for l in leads if l.email}
    if not lead_emails:
        return 0

    try:
        result = (
            service.users()
            .messages()
            .list(userId="me", q="in:inbox newer_than:7d", maxResults=40)
            .execute()
        )
    except Exception as exc:
        print(f"Gmail list failed for {tenant_id}: {exc}")
        return 0

    from app.core.celery_app import celery_app

    queued = 0
    for item in result.get("messages") or []:
        msg_id = item.get("id")
        if not msg_id:
            continue
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )
        except Exception:
            continue

        headers = msg.get("payload", {}).get("headers") or []
        from_hdr = _header(headers, "From")
        subject = _header(headers, "Subject")
        sender_email = normalize_email(from_hdr)
        if sender_email not in lead_emails:
            continue

        # Skip our own sent mail
        label_ids = msg.get("labelIds") or []
        if "SENT" in label_ids and "INBOX" not in label_ids:
            continue

        body = _decode_body(msg.get("payload") or {})
        if not body.strip():
            continue

        lead = next(
            (l for l in leads if l.email and normalize_email(l.email) == sender_email),
            None,
        )
        if not lead:
            continue

        processed = set((lead.data or {}).get("processed_inbound_ids") or [])
        if msg_id in processed:
            continue

        celery_app.send_task(
            "process_sales_inbound_task",
            args=[tenant_id, lead.id, "email", body, subject, msg_id],
        )
        queued += 1

    return queued

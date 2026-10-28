"""Unified Mailbox API: Inbound Webhooks, Universal Sending, and Hosted Connect Sessions.

Allows connecting ANY company mailbox (Google Workspace, Microsoft 365 / Outlook, IMAP)
so AI agents can read, sync, and reply to emails across providers.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.core.celery_app import celery_app
from app.services.webhook_security import check_and_store_idempotency
from app.models.base import User
from app.models.verticals import Lead
from app.services.email.universal_provider import (
    BaseUniversalMailboxAdapter,
    UnipileAdapter,
    EmailEngineAdapter,
    AurinkoAdapter,
    get_universal_mailbox_provider,
)
from app.services.sales.lead_matching import normalize_email
from app.services.sales.bounce_sentinel import BounceSentinel

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──

class ConnectSessionRequest(BaseModel):
    redirect_url: Optional[str] = Field(None, description="URL to return to after user connects mailbox")
    provider_type: Optional[str] = Field("MAIL", description="Connection type: MAIL, LINKEDIN, WHATSAPP, or auto")


class OutboundSendRequest(BaseModel):
    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, description="Email subject line")
    body: str = Field(..., min_length=1, description="Plaintext or HTML email body")
    thread_id: Optional[str] = Field(None, description="Thread ID to maintain email conversation threading")
    in_reply_to: Optional[str] = Field(None, description="Message-ID being replied to")


# ── Webhook Receiver ──

@router.post("/webhook/{tenant_id}")
async def receive_unified_email_webhook(
    tenant_id: str,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Receives real-time push webhook notifications from Unipile, EmailEngine,
    or other universal email sync engines.
    """
    raw_body = await request.body()
    headers_dict = {k.lower(): v for k, v in request.headers.items()}
    signature = (
        headers_dict.get("x-signature")
        or headers_dict.get("x-aurinko-signature")
        or headers_dict.get("x-unipile-signature")
        or headers_dict.get("x-hub-signature-256")
    )

    provider = get_universal_mailbox_provider(db, tenant_id)
    # If no tenant-specific provider resolved, instantiate a default parser
    if not provider:
        provider = UnipileAdapter(api_key="")

    # Verify signature if configured
    if not provider.verify_webhook(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature")

    parsed = provider.parse_inbound_webhook(raw_body, headers_dict)
    if not parsed:
        # Check if generic JSON fallback
        try:
            generic_data = json.loads(raw_body.decode("utf-8"))
            parsed = {
                "provider": "generic",
                "event": generic_data.get("event", "message"),
                "sender": generic_data.get("sender") or generic_data.get("from", ""),
                "recipient": generic_data.get("recipient") or generic_data.get("to", ""),
                "subject": generic_data.get("subject", ""),
                "body": generic_data.get("body") or generic_data.get("text", ""),
                "message_id": generic_data.get("message_id") or generic_data.get("id"),
                "thread_id": generic_data.get("thread_id"),
            }
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unparseable webhook payload")

    sender = parsed.get("sender", "").strip()
    subject = parsed.get("subject", "").strip()
    body = parsed.get("body", "").strip()
    external_id = str(parsed.get("message_id") or hashlib.sha256(raw_body).hexdigest())

    # Idempotency deduplication check
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    if not check_and_store_idempotency(
        db,
        tenant_id=tenant_id,
        provider=parsed.get("provider", "universal_email"),
        event_id=external_id,
        payload_hash=payload_hash,
    ):
        return {"status": "duplicate", "event_id": external_id}

    # 1. Check for NDR / Delivery Status Notification Bounces
    if BounceSentinel.is_bounce(sender, subject):
        bounced_email = BounceSentinel.extract_bounced_email(body)
        if bounced_email:
            BounceSentinel.record_bounce(db, tenant_id, bounced_email)
        return {"status": "bounce_recorded", "bounced_email": bounced_email}

    # 2. Check if sender matches an active Sales Lead
    sender_norm = normalize_email(sender)
    leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).all()
    matched_lead = next(
        (l for l in leads if l.email and normalize_email(l.email) == sender_norm),
        None,
    )

    if matched_lead:
        # Route to sales inbound reply processing pipeline
        try:
            celery_app.send_task(
                "process_sales_inbound_task",
                args=[tenant_id, matched_lead.id, "email", body, subject, external_id],
            )
            return {
                "status": "queued_for_sales",
                "lead_id": matched_lead.id,
                "lead_name": matched_lead.name,
                "external_id": external_id,
            }
        except Exception as exc:
            logger.warning(f"Failed to queue celery task; processing synchronously: {exc}")
            from app.services.sales.reply_handler import SalesReplyHandler
            handler = SalesReplyHandler(db, tenant_id)
            handler.register_inbound(
                matched_lead,
                channel="email",
                content=body,
                subject=subject,
                external_id=external_id,
            )
            db.commit()
            return {
                "status": "processed_sales_sync",
                "lead_id": matched_lead.id,
                "external_id": external_id,
            }

    # 3. Check if Support Ticket or Support Agent handles this message
    try:
        from app.services.agents.support import SupportAgent
        support_agent = SupportAgent(db, tenant_id)
        # Check if tenant has support enabled
        import asyncio
        from asgiref.sync import async_to_sync
        async_to_sync(support_agent.handle_incoming_message)(
            channel="email",
            sender=sender,
            content=body,
            subject=subject or None,
            external_id=external_id,
        )
        return {
            "status": "routed_to_support",
            "sender": sender,
            "external_id": external_id,
        }
    except Exception as exc:
        logger.info(f"Support routing skipped or handled: {exc}")

    return {
        "status": "received",
        "sender": sender,
        "external_id": external_id,
        "matched": False,
    }


# ── Universal Connect Session & Status ──

@router.post("/connect-session")
def create_connect_session(
    payload: ConnectSessionRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Generates a 1-click hosted onboarding URL (via Unipile or EmailEngine)
    allowing the user to connect their Google Workspace, Microsoft 365, or IMAP mailbox.
    """
    provider = get_universal_mailbox_provider(db, tenant_id)
    if not provider or not provider.is_configured():
        # Check if environment-level Unipile key is provided
        unipile_key = settings.__dict__.get("UNIPILE_API_KEY") or os.environ.get("UNIPILE_API_KEY")
        if unipile_key:
            provider = UnipileAdapter(api_key=unipile_key)

    if not provider or not provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Universal Mailbox engine is not configured. Add your Unipile or EmailEngine API key in Platform Setup -> API Settings.",
        )

    res = provider.create_connect_session(
        tenant_id=tenant_id,
        redirect_url=payload.redirect_url,
        provider_type=payload.provider_type,
    )
    if not res.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=res.get("error", "Failed to generate mailbox connect link"),
        )
    return res


@router.get("/status")
def get_universal_mailbox_status(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Returns current connection status and active provider for the tenant."""
    provider = get_universal_mailbox_provider(db, tenant_id)
    configured = bool(provider and provider.is_configured())

    accounts: List[Dict[str, Any]] = []
    if configured and hasattr(provider, "list_accounts"):
        try:
            accounts = provider.list_accounts()  # type: ignore
        except Exception:
            pass

    return {
        "configured": configured,
        "provider": provider.name if provider else None,
        "webhook_url": f"/api/v1/unified-mail/webhook/{tenant_id}",
        "connected_accounts_count": len(accounts),
        "accounts": [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "type": a.get("type") or a.get("provider_type"),
                "status": a.get("status") or "active",
            }
            for a in accounts
        ],
    }


@router.post("/send")
def send_outbound_email(
    payload: OutboundSendRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """
    Directly dispatches an email through the tenant's universal connected mailbox
    (Google Workspace, Microsoft 365, or IMAP/SMTP).
    """
    from app.services.email.sender import send_email_with_status

    result = send_email_with_status(
        db=db,
        tenant_id=tenant_id,
        to_email=payload.to_email,
        subject=payload.subject,
        body=payload.body,
        thread_id=payload.thread_id,
        in_reply_to=payload.in_reply_to,
    )
    if not result.get("sent"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("message", "Failed to send email through configured mailboxes"),
        )
    return result

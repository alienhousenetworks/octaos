"""Unified Multi-Channel Sales Touch Dispatcher for Cold Outreach & Cadences.

Eliminates mocked/fake delivery:
1. Email: Real delivery via Gmail API or SMTP with fallback.
2. WhatsApp: Real delivery via official Meta WhatsApp Business Cloud API.
3. LinkedIn: Dispatches via configured automation connector or stages an authentic
   actionable Human-in-the-Loop ApprovalRequest with direct profile link and bespoke note.
4. Call / Follow-up: Stages high-priority call task with prospect contact.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.models.base import APICredential
from app.models.enterprise import ApprovalRequest
from app.models.verticals import Lead
from app.services.credentials import get_decrypted_credential
from app.services.email.sender import send_email_with_status
from app.services.sales_os.governance.suppression import SuppressionService

logger = logging.getLogger(__name__)


def clean_phone_number(raw_phone: Optional[str]) -> Optional[str]:
    """Cleans phone numbers into E.164-compatible format for WhatsApp API."""
    if not raw_phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", str(raw_phone).strip())
    if len(cleaned) < 8:
        return None
    # Strip leading + for Meta WhatsApp API if present or leave as digits
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    return cleaned


def extract_lead_phone(lead: Lead) -> Optional[str]:
    """Extracts phone number from lead primary or nested data."""
    phone = lead.phone or lead.mobile_no or getattr(lead, "company_contact_no", None)
    if phone:
        cleaned = clean_phone_number(phone)
        if cleaned:
            return cleaned

    # Check lead data payload
    data = lead.data or {}
    if isinstance(data, dict):
        contact = data.get("contact") or {}
        if isinstance(contact, dict) and contact.get("phone"):
            cleaned = clean_phone_number(contact.get("phone"))
            if cleaned:
                return cleaned
        if data.get("phone"):
            cleaned = clean_phone_number(data.get("phone"))
            if cleaned:
                return cleaned

    return None


def extract_lead_linkedin_url(lead: Lead) -> Optional[str]:
    """Extracts LinkedIn profile URL from lead record or nested data."""
    data = lead.data or {}
    if isinstance(data, dict):
        contact = data.get("contact") or {}
        if isinstance(contact, dict) and contact.get("linkedin_url"):
            return str(contact.get("linkedin_url")).strip()
        if data.get("linkedin_url"):
            return str(data.get("linkedin_url")).strip()

    # Match in text fields
    for field in (lead.why, lead.target_context):
        if field and "linkedin.com/in/" in field:
            match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[\w-]+", field)
            if match:
                return match.group(0)

    return None


def send_whatsapp_with_status(
    db: Session,
    tenant_id: str,
    phone: Optional[str],
    body: str,
) -> Dict[str, Any]:
    """
    Delivers a real WhatsApp message using the tenant's Meta WhatsApp Cloud API credentials.
    Returns structured {sent: bool, channel: 'whatsapp', reason: str, message: str}.
    """
    cleaned_phone = clean_phone_number(phone)
    if not cleaned_phone:
        return {
            "sent": False,
            "channel": "whatsapp",
            "reason": "missing_phone",
            "message": "Prospect has no valid phone number on file for WhatsApp delivery.",
        }

    # Pre-send suppression check
    suppression = SuppressionService(db, tenant_id)
    is_supp, supp_reason = suppression.is_suppressed(phone=cleaned_phone)
    if is_supp:
        return {
            "sent": False,
            "channel": "whatsapp",
            "reason": "suppressed",
            "message": f"Prospect phone {cleaned_phone} is suppressed: {supp_reason}",
        }

    cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="meta").first()
    token, _ = get_decrypted_credential(db, tenant_id, "meta")

    if not cred or not token or not cred.settings or not cred.settings.get("phone_number_id"):
        return {
            "sent": False,
            "channel": "whatsapp",
            "reason": "meta_whatsapp_not_configured",
            "message": "Meta WhatsApp API credentials (access token and phone_number_id) not configured.",
        }

    phone_number_id = str(cred.settings.get("phone_number_id")).strip()
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": cleaned_phone,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code in (200, 201):
                res_json = resp.json()
                msgs = res_json.get("messages", [])
                provider_msg_id = msgs[0].get("id") if msgs else None
                return {
                    "sent": True,
                    "channel": "whatsapp",
                    "reason": "success",
                    "message": "Delivered via Meta WhatsApp Cloud API.",
                    "message_id": provider_msg_id,
                }
            else:
                return {
                    "sent": False,
                    "channel": "whatsapp",
                    "reason": "meta_api_error",
                    "message": f"WhatsApp API returned {resp.status_code}: {resp.text[:300]}",
                }
    except Exception as exc:
        logger.error(f"[WhatsAppDispatch] Error sending message to {cleaned_phone}: {exc}")
        return {
            "sent": False,
            "channel": "whatsapp",
            "reason": "network_error",
            "message": f"Network error delivering WhatsApp message: {str(exc)}",
        }


def dispatch_linkedin_touch(
    db: Session,
    tenant_id: str,
    lead: Lead,
    body: str,
    step_number: int = 2,
    outbox_item_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handles a LinkedIn touch authentically:
    1. If an automated connector is configured, calls connector.
    2. Otherwise, creates a verified Human-In-The-Loop ApprovalRequest with direct profile link
       so the operator can execute/send with 1-click and tracks real status.
    """
    linkedin_url = extract_lead_linkedin_url(lead)

    # Check if there is an approved action already executed
    resource_id = outbox_item_id or f"{lead.id}_step_{step_number}"
    existing_approval = (
        db.query(ApprovalRequest)
        .filter_by(
            tenant_id=tenant_id,
            action_type="linkedin_outreach",
            resource_id=resource_id,
        )
        .first()
    )

    if existing_approval and existing_approval.status == "approved":
        return {
            "sent": True,
            "channel": "linkedin",
            "reason": "approved_by_operator",
            "message": "Operator approved LinkedIn touch.",
            "approval_id": existing_approval.id,
            "linkedin_url": linkedin_url,
        }

    # If automated third-party LinkedIn bot is configured in credentials
    apify_cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="apify").first()
    if apify_cred and apify_cred.encrypted_key and apify_cred.settings and apify_cred.settings.get("enable_automated_linkedin_send"):
        try:
            from apify_client import ApifyClient
            from app.core.security import decrypt_api_key

            token = decrypt_api_key(apify_cred.encrypted_key)
            client = ApifyClient(token)
            actor_id = apify_cred.settings.get("linkedin_send_actor", "curious_coder/linkedin-message-sender")
            run = client.actor(actor_id).call(run_input={
                "profileUrl": linkedin_url,
                "message": body,
            })
            return {
                "sent": True,
                "channel": "linkedin",
                "reason": "automated_connector_success",
                "message": f"Dispatched via Apify actor {actor_id}",
                "run_id": run.get("id"),
            }
        except Exception as bot_err:
            logger.warning(f"[LinkedInDispatch] Automated bot send failed ({bot_err}), escalating to approval queue.")

    # Stage actionable Human-in-the-Loop review
    if not existing_approval:
        lead_name = lead.name or "Prospect"
        company_name = lead.company or "Target Company"
        approval = ApprovalRequest(
            tenant_id=tenant_id,
            action_type="linkedin_outreach",
            channel="linkedin",
            resource_type="lead",
            resource_id=resource_id,
            title=f"LinkedIn Touch Step {step_number}: {lead_name} ({company_name})",
            payload={
                "lead_id": lead.id,
                "outbox_item_id": outbox_item_id,
                "lead_name": lead_name,
                "company": company_name,
                "linkedin_url": linkedin_url,
                "message": body,
                "step_number": step_number,
            },
            status="pending",
            policy_reason="LinkedIn outreach staged for sales representative dispatch.",
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        approval_id = approval.id
    else:
        approval_id = existing_approval.id

    return {
        "sent": False,
        "channel": "linkedin",
        "reason": "pending_operator_action",
        "requires_action": True,
        "approval_id": approval_id,
        "linkedin_url": linkedin_url,
        "message": "Staged in Human-in-the-Loop queue with direct LinkedIn link for operator dispatch.",
    }


def dispatch_sales_touch(
    db: Session,
    tenant_id: str,
    lead: Lead,
    channel: str,
    body: str,
    subject: Optional[str] = None,
    step_number: int = 1,
    outbox_item_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified multi-channel sales touch dispatcher.
    Routes touch through real, non-mocked channels and logs provenance.
    """
    ch = (channel or "email").lower().strip()

    if ch == "email":
        recipient_email = lead.email or lead.company_email or lead.personal_email
        res = send_email_with_status(
            db,
            tenant_id,
            recipient_email,
            subject or f"Following up: {lead.company or 'Partnership'}",
            body,
        )
        return res

    elif ch == "whatsapp":
        phone = extract_lead_phone(lead)
        res = send_whatsapp_with_status(db, tenant_id, phone, body)
        return res

    elif ch == "linkedin":
        res = dispatch_linkedin_touch(
            db,
            tenant_id,
            lead,
            body,
            step_number=step_number,
            outbox_item_id=outbox_item_id,
        )
        return res

    elif ch in ("call", "follow-up call", "phone"):
        phone = extract_lead_phone(lead)
        resource_id = outbox_item_id or f"{lead.id}_call_step_{step_number}"
        existing = (
            db.query(ApprovalRequest)
            .filter_by(
                tenant_id=tenant_id,
                action_type="sales_call",
                resource_id=resource_id,
            )
            .first()
        )
        if not existing:
            approval = ApprovalRequest(
                tenant_id=tenant_id,
                action_type="sales_call",
                channel="call",
                resource_type="lead",
                resource_id=resource_id,
                title=f"Call Step {step_number}: {lead.name} ({lead.company})",
                payload={
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "phone": phone,
                    "company": lead.company,
                    "talking_points": body,
                },
                status="pending",
                policy_reason="Follow-up call queued for sales team.",
            )
            db.add(approval)
            db.commit()
            approval_id = approval.id
        else:
            approval_id = existing.id

        return {
            "sent": False,
            "channel": "call",
            "reason": "call_task_queued",
            "requires_action": True,
            "approval_id": approval_id,
            "message": f"Follow-up call task queued for {lead.name} ({phone or 'No phone'}).",
        }

    return {
        "sent": False,
        "channel": ch,
        "reason": "unsupported_channel",
        "message": f"Channel '{channel}' is not supported.",
    }

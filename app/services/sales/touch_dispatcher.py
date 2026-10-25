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
from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper
from app.services.sales_os.governance.suppression import SuppressionService
from app.services.sales_os.quality_gates import assess_channel_authorization

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
    human_approved: bool = False,
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

    approval_is_granted = bool(
        existing_approval and str(existing_approval.status or "").lower() == "approved"
    )

    # Automated LinkedIn dispatch requires the same explicit tenant authorization
    # as email/WhatsApp. Without it, retain the human approval queue below.
    apify_cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="apify").first()
    sales_credential = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="sales").first()
    sales_settings = (sales_credential.settings if sales_credential else {}) or {}
    linkedin_authorization = assess_channel_authorization(
        sales_settings, "linkedin", human_approved=human_approved
    )
    automated_linkedin_enabled = bool(
        apify_cred
        and apify_cred.encrypted_key
        and apify_cred.settings
        and apify_cred.settings.get("enable_automated_linkedin_send")
        and linkedin_authorization["ready"]
    )
    if approval_is_granted and not automated_linkedin_enabled:
        return {
            "sent": False,
            "channel": "linkedin",
            "reason": "approved_waiting_for_execution",
            "requires_action": True,
            "approval_id": existing_approval.id,
            "linkedin_url": linkedin_url,
            "message": "Approved, but no authorized automated connector execution receipt exists. Do not mark this touch as sent.",
        }

    if automated_linkedin_enabled:
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
        "reason": "approved_but_dispatch_failed" if approval_is_granted else "pending_operator_action",
        "requires_action": True,
        "approval_id": approval_id,
        "linkedin_url": linkedin_url,
        "message": (
            "Approval exists, but no successful provider execution receipt was recorded."
            if approval_is_granted
            else "Staged in Human-in-the-Loop queue with direct LinkedIn link for operator dispatch."
        ),
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
    human_approved: bool = False,
) -> Dict[str, Any]:
    """
    Unified multi-channel sales touch dispatcher.
    Routes touch through real, non-mocked channels and logs provenance.
    """
    ch = (channel or "email").lower().strip()

    # Central authorization is enforced here as well as in the V3 orchestrator,
    # so cadence/outbox callers cannot bypass the tenant's send policy.
    if ch in {"email", "whatsapp"}:
        sales_credential = db.query(APICredential).filter_by(
            tenant_id=tenant_id, provider="sales"
        ).first()
        settings = (sales_credential.settings if sales_credential else {}) or {}
        lead_data = lead.data if isinstance(getattr(lead, "data", None), dict) else {}
        contact_data = lead_data.get("contact") if isinstance(lead_data.get("contact"), dict) else {}
        opt_in_value = (
            contact_data.get("whatsapp_opt_in")
            if "whatsapp_opt_in" in contact_data
            else lead_data.get("whatsapp_opt_in")
        )
        opt_in_source = (
            contact_data.get("whatsapp_opt_in_source")
            if "whatsapp_opt_in_source" in contact_data
            else lead_data.get("whatsapp_opt_in_source")
        )
        opt_in_at = (
            contact_data.get("whatsapp_opt_in_at")
            if "whatsapp_opt_in_at" in contact_data
            else lead_data.get("whatsapp_opt_in_at")
        )
        recipient_opt_in = (
            ch == "whatsapp"
            and opt_in_value is True
            and bool(opt_in_source)
            and bool(opt_in_at)
        )
        from app.services.sales_os.quality_gates import assess_outreach_readiness

        evidence = lead_data.get("evidence") if isinstance(lead_data.get("evidence"), dict) else {}
        qualification = lead_data.get("qualification") if isinstance(lead_data.get("qualification"), dict) else {}
        contact_name = (
            contact_data.get("name")
            or lead_data.get("contact_name")
            or (lead.name if lead.name and lead.name.strip().casefold() != (lead.company or "").strip().casefold() else None)
        )
        recipient_email = lead.email or lead.company_email or lead.personal_email
        recipient_phone = extract_lead_phone(lead)
        prospect = {
            "contact_status": (
                lead_data.get("contact_status")
                or contact_data.get("contact_status")
                or qualification.get("contact_status")
            ),
            "evidence_url": lead_data.get("evidence_url") or evidence.get("url") or getattr(lead, "evidence_url", None),
            "evidence_quote": lead_data.get("evidence_quote") or evidence.get("quote"),
            "buying_signal": lead_data.get("buying_signal"),
            "news": lead_data.get("news") or [],
            "jobs": lead_data.get("jobs") or [],
            "contact": {
                "name": contact_name,
                "email": recipient_email,
                "phone": recipient_phone,
            },
        }
        readiness = assess_outreach_readiness(
            prospect,
            auto_send_enabled=bool(settings.get("sales_ai_auto_send_enabled", False)),
            permission_state=settings.get("outbound_permission_state"),
            suppressed=bool(lead_data.get("suppressed") or lead_data.get("do_not_contact")),
            human_approved=human_approved,
        )
        authorization = assess_channel_authorization(
            settings,
            ch,
            recipient_opt_in=recipient_opt_in,
            human_approved=human_approved,
        )
        blockers = list(dict.fromkeys(readiness["blockers"] + authorization["blockers"]))
        if blockers:
            return {
                "sent": False,
                "channel": ch,
                "reason": "outbound_authorization_blocked",
                "message": "Outbound dispatch blocked: " + ", ".join(blockers),
                "blockers": blockers,
                "readiness": readiness,
                "authorization": authorization,
            }

    # The outbox and the legacy cadence schedule both call this dispatcher.
    # Keep the final policy checks here as the last line of defense so direct
    # callers cannot bypass suppression or deliverability rules.
    recipient_email = None
    phone = None
    if ch == "email":
        recipient_email = lead.email or lead.company_email or lead.personal_email
        if not recipient_email:
            return {
                "sent": False,
                "channel": "email",
                "reason": "no_recipient",
                "message": "No email address available for this lead.",
            }
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", recipient_email):
            return {
                "sent": False,
                "channel": "email",
                "reason": "invalid_recipient",
                "message": "Lead email address is not valid for delivery.",
            }
        is_supp, supp_reason = SuppressionService(db, tenant_id).is_suppressed(
            email=recipient_email,
            channel="email",
        )
        if is_supp:
            return {
                "sent": False,
                "channel": "email",
                "reason": "suppressed",
                "message": f"Email recipient is suppressed: {supp_reason}",
            }
    elif ch == "whatsapp":
        phone = extract_lead_phone(lead)
        is_supp, supp_reason = SuppressionService(db, tenant_id).is_suppressed(
            phone=phone,
            channel="whatsapp",
        )
        if is_supp:
            return {
                "sent": False,
                "channel": "whatsapp",
                "reason": "suppressed",
                "message": f"WhatsApp recipient is suppressed: {supp_reason}",
            }

    if ch not in ("call", "follow-up call", "phone"):
        gate = PreSendGatekeeper.evaluate(
            subject=subject or f"{ch.title()} touch",
            body=body or "",
            step_number=step_number,
            min_words=8 if ch == "email" else 3,
            require_subject=ch == "email",
        )
        if not gate.is_valid:
            return {
                "sent": False,
                "channel": ch,
                "reason": "deliverability_gate_blocked",
                "message": "; ".join(gate.violations),
                "violations": gate.violations,
            }

    if ch == "email":
        res = send_email_with_status(
            db,
            tenant_id,
            recipient_email,
            subject or f"Following up: {lead.company or 'Partnership'}",
            body,
        )
        return res

    elif ch == "whatsapp":
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
            human_approved=human_approved,
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

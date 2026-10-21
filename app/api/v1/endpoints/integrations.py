"""Unified Webhook Ingress and Integrations Router for OctaOS."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.services.credentials import get_decrypted_credential
from app.services.integrations.sendgrid_service import SendGridService
from app.services.integrations.calendly_service import CalendlyService
from app.services.integrations.landingi_forms_service import LandingiFormsService
from app.services.integrations.zapier_workato_service import ZapierWorkatoService
from app.services.integrations.twilio_service import TwilioService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/{provider}/{tenant_id}")
async def verify_webhook_challenge(
    provider: str,
    tenant_id: str,
    request: Request,
    db: Session = Depends(deps.get_db),
):
    """
    Handles challenge verification for Meta, WhatsApp, Calendly, and Webhook providers.
    """
    params = dict(request.query_params)
    hub_challenge = params.get("hub.challenge") or params.get("challenge")
    if hub_challenge:
        return Response(content=str(hub_challenge), media_type="text/plain")

    return {"status": "active", "provider": provider, "tenant_id": tenant_id}


@router.post("/webhooks/{provider}/{tenant_id}")
async def receive_integration_webhook(
    provider: str,
    tenant_id: str,
    request: Request,
    db: Session = Depends(deps.get_db),
):
    """
    Universal Inbound Webhook Listener.
    Dispatches events from SendGrid, Calendly, Google Forms, Landingi, Zapier, Workato, Twilio, Formstack.
    """
    prov_lower = provider.lower()
    
    # Parse payload (handles JSON or Form-Data)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    elif "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload = dict(form_data)
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

    logger.info(f"Received inbound webhook from '{prov_lower}' for tenant '{tenant_id}'")

    # Dispatch to appropriate connector service
    if prov_lower == "calendly":
        event_name = payload.get("event") or "invitee.created"
        event_payload = payload.get("payload", payload)
        result = CalendlyService(db, tenant_id).process_webhook(event_name, event_payload)
        return {"status": "processed", "provider": "calendly", "result": result}

    elif prov_lower in ("google_forms", "googleforms"):
        result = LandingiFormsService(db, tenant_id).ingest_submission("Google Forms", payload)
        return {"status": "processed", "provider": "google_forms", "result": result}

    elif prov_lower == "landingi":
        result = LandingiFormsService(db, tenant_id).ingest_submission("Landingi", payload)
        return {"status": "processed", "provider": "landingi", "result": result}

    elif prov_lower == "formstack":
        result = LandingiFormsService(db, tenant_id).ingest_submission("Formstack", payload)
        return {"status": "processed", "provider": "formstack", "result": result}

    elif prov_lower == "sendgrid":
        events = payload if isinstance(payload, list) else [payload]
        result = SendGridService(db, tenant_id).process_webhook_events(events)
        return {"status": "processed", "provider": "sendgrid", "result": result}

    elif prov_lower in ("zapier", "workato"):
        action = payload.get("action") or "create_lead"
        data = payload.get("data") or payload
        result = ZapierWorkatoService(db, tenant_id).execute_inbound_action(prov_lower, action, data)
        return {"status": "processed", "provider": prov_lower, "result": result}

    elif prov_lower in ("twilio", "twilio_sms"):
        from_phone = payload.get("From", "")
        body = payload.get("Body", "")
        result = TwilioService(db, tenant_id).handle_inbound_sms(from_phone, body)
        return {"status": "processed", "provider": "twilio", "result": result}

    return {
        "status": "acknowledged",
        "provider": prov_lower,
        "tenant_id": tenant_id,
        "payload_keys": list(payload.keys()) if isinstance(payload, dict) else len(payload),
    }

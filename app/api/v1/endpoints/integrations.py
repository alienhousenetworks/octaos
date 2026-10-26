"""Unified Webhook Ingress and Integrations Router for OctaOS."""
from __future__ import annotations

import logging
import hmac
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.services.credentials import get_decrypted_credential, normalize_provider
from app.services.integrations.webhook_security import verify_timestamped_hmac
from app.services.integrations.sendgrid_service import SendGridService
from app.services.integrations.calendly_service import CalendlyService
from app.services.integrations.landingi_forms_service import LandingiFormsService
from app.services.integrations.zapier_workato_service import ZapierWorkatoService
from app.services.integrations.twilio_service import TwilioService

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_local_development() -> bool:
    return bool(settings.DEV) and (settings.ENVIRONMENT or "").strip().lower() in {
        "development", "dev", "local", "test"
    }


def _webhook_secret(db: Session, tenant_id: str, provider: str) -> Optional[str]:
    # Webhook signing secrets use a separate encrypted credential record so they
    # do not overwrite the provider's API/OAuth credential.
    normalized = normalize_provider(provider)
    secret, _ = get_decrypted_credential(db, tenant_id, f"{normalized}_webhook")
    return secret


def _require_webhook_signature(
    db: Session, tenant_id: str, provider: str, request: Request, raw_body: bytes
) -> None:
    secret = _webhook_secret(db, tenant_id, provider)
    if not secret:
        if _is_local_development():
            logger.warning(
                "Webhook signature is not configured for provider=%s tenant=%s; "
                "permissive handling is development-only.",
                normalize_provider(provider), tenant_id,
            )
            return
        raise HTTPException(
            status_code=503,
            detail="Webhook signature verification is not configured for this tenant/provider.",
        )

    valid = verify_timestamped_hmac(
        secret=secret,
        timestamp=request.headers.get("X-OctaOS-Timestamp"),
        signature=request.headers.get("X-OctaOS-Signature"),
        body=raw_body,
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid or expired webhook signature.")


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
        secret = _webhook_secret(db, tenant_id, provider)
        verify_token = params.get("hub.verify_token") or params.get("verify_token")
        if not secret:
            if not _is_local_development():
                raise HTTPException(
                    status_code=503,
                    detail="Webhook challenge verification is not configured.",
                )
        elif not verify_token or not hmac.compare_digest(secret, verify_token):
            raise HTTPException(status_code=403, detail="Invalid webhook verification token.")
        return Response(content=str(hub_challenge), media_type="text/plain")

    if not _webhook_secret(db, tenant_id, provider) and not _is_local_development():
        raise HTTPException(status_code=503, detail="Webhook verification is not configured.")
    return {"status": "active", "provider": normalize_provider(provider)}


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
    prov_lower = normalize_provider(provider)
    raw_body = await request.body()
    _require_webhook_signature(db, tenant_id, prov_lower, request, raw_body)

    # Parse payload (handles JSON or Form-Data) only after authenticating ingress.
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

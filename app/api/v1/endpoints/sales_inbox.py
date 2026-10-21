"""API endpoints for Omnichannel Unified Sales Inbox & Cadence Control Plane.

Provides:
- GET  /api/v1/sales-inbox/threads: Aggregated conversation threads across Email, WhatsApp, and LinkedIn.
- GET  /api/v1/sales-inbox/threads/{lead_id}/messages: Chronological message history for a lead.
- POST /api/v1/sales-inbox/threads/{lead_id}/reply: Immediate multi-channel outbound message dispatch.
- POST /api/v1/sales-inbox/threads/{lead_id}/ai-suggest: Contextual AI copilot suggested replies.
- POST /api/v1/sales-inbox/threads/{lead_id}/pause-cadence: Pause automated cadence for a lead.
- POST /api/v1/sales-inbox/threads/{lead_id}/resume-cadence: Resume automated cadence for a lead.
- POST /api/v1/sales-inbox/cadence/run: Manually trigger durable cadence runner dispatch.
- GET  /api/v1/sales-inbox/cadence/stats: Live cadence runner statistics.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.models.deal_room import DealRoom
from app.models.verticals import Lead
from app.services.sales.cadence_runner import DurableCadenceRunner
from app.services.sales.touch_dispatcher import dispatch_sales_touch

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──

class OutboundReplyRequest(BaseModel):
    channel: str = Field("email", description="Channel: email, whatsapp, linkedin")
    body: str = Field(..., min_length=1, description="Message content")
    subject: Optional[str] = Field(None, description="Subject line for email")


class AISuggestRequest(BaseModel):
    intent: Optional[str] = Field("demo_booking", description="Objective: demo_booking, pricing, case_study, followup")


# ── Endpoints ──

@router.get("/threads")
def list_sales_threads(
    channel: Optional[str] = Query(None, description="Filter by channel: email, whatsapp, linkedin"),
    search: Optional[str] = Query(None, description="Search by name, company, or email"),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> List[Dict[str, Any]]:
    """Lists aggregated omnichannel conversation threads for the tenant."""
    query = db.query(Lead).filter(Lead.tenant_id == tenant_id)
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            (Lead.name.ilike(s)) | (Lead.company.ilike(s)) | (Lead.email.ilike(s))
        )

    leads = query.order_by(Lead.updated_at.desc()).limit(150).all()
    threads: List[Dict[str, Any]] = []

    # Map deal rooms by lead_id
    deal_rooms = db.query(DealRoom).filter(DealRoom.tenant_id == tenant_id).all()
    rooms_by_lead = {r.lead_id: r for r in deal_rooms if r.lead_id}

    for lead in leads:
        data = lead.data or {}
        raw_conv = data.get("conversations") or data.get("conversation") or []
        schedule = data.get("outreach_schedule") or []

        # Find last message
        last_msg = None
        unread = False
        primary_channel = "email"

        if raw_conv and isinstance(raw_conv, list):
            valid_msgs = [m for m in raw_conv if isinstance(m, dict) and m.get("content")]
            if valid_msgs:
                last_msg = valid_msgs[-1]
                primary_channel = str(last_msg.get("channel") or "email").lower()
                if last_msg.get("direction") == "inbound" and not last_msg.get("read"):
                    unread = True

        # Check next scheduled cadence touch
        next_step = None
        is_cadence_active = not data.get("cadence_paused", False) and lead.status not in (
            "closed_won", "closed_lost", "replied"
        )
        if isinstance(schedule, list):
            for step in schedule:
                if step.get("status") == "pending":
                    next_step = step
                    break

        room = rooms_by_lead.get(lead.id)

        # Apply channel filter if requested
        if channel and primary_channel != channel.lower():
            continue

        threads.append({
            "lead_id": lead.id,
            "contact_name": lead.name or "Unknown Contact",
            "company": lead.company or "Independent",
            "email": lead.email or getattr(lead, "company_email", ""),
            "phone": lead.phone or getattr(lead, "mobile_no", ""),
            "status": lead.status,
            "channel": primary_channel,
            "message_count": len(raw_conv) if isinstance(raw_conv, list) else 0,
            "unread": unread,
            "last_message": {
                "direction": last_msg.get("direction", "outbound") if last_msg else "outbound",
                "content": last_msg.get("content", "Cadence touch scheduled") if last_msg else "No messages yet",
                "author": last_msg.get("author", "Sales AI Agent") if last_msg else "System",
                "at": last_msg.get("at", (lead.updated_at or lead.created_at or datetime.now(timezone.utc)).isoformat()) if last_msg else "",
            },
            "deal_room_id": room.id if room else None,
            "deal_room_stage": room.stage if room else lead.status,
            "cadence_active": is_cadence_active and (next_step is not None),
            "cadence_paused": bool(data.get("cadence_paused")),
            "next_step": next_step,
            "target_context": lead.target_context or "",
        })

    return threads


@router.get("/threads/{lead_id}/messages")
def get_thread_messages(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Fetches chronological messages and cadence schedule for a thread."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead thread not found")

    data = dict(lead.data or {})
    raw_conv = data.get("conversations") or data.get("conversation") or []
    schedule = list(data.get("outreach_schedule") or [])

    messages: List[Dict[str, Any]] = []
    if isinstance(raw_conv, list):
        for idx, m in enumerate(raw_conv):
            if isinstance(m, dict):
                messages.append({
                    "id": f"msg-{idx}",
                    "direction": m.get("direction", "outbound"),
                    "channel": str(m.get("channel") or "email").lower(),
                    "subject": m.get("subject"),
                    "content": m.get("content", ""),
                    "author": m.get("author", "Sales AI Agent"),
                    "at": m.get("at", datetime.now(timezone.utc).isoformat()),
                    "sent": m.get("sent", True),
                    "delivery_details": m.get("delivery_details"),
                })

    room = db.query(DealRoom).filter(DealRoom.tenant_id == tenant_id, DealRoom.lead_id == lead.id).first()

    return {
        "lead": {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "company": lead.company,
            "status": lead.status,
            "score": lead.score,
            "priority": lead.priority,
            "committee_role": data.get("committee_role", "economic_buyer"),
            "domain_archetype": data.get("domain_archetype"),
            "cadence_paused": bool(data.get("cadence_paused")),
        },
        "deal_room": {
            "id": room.id if room else None,
            "stage": room.stage if room else lead.status,
            "is_multi_threaded": getattr(room, "is_multi_threaded", False) if room else False,
        } if room else None,
        "messages": messages,
        "schedule": schedule,
    }


@router.post("/threads/{lead_id}/reply")
def send_thread_reply(
    lead_id: str,
    payload: OutboundReplyRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Sends a real outbound reply across Email, WhatsApp, or LinkedIn via the unified touch dispatcher."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead thread not found")

    channel = payload.channel.lower().strip()
    subject = payload.subject or f"Regarding: {lead.company or 'Our Partnership'}"
    body = payload.body.strip()

    # Dispatch via production dispatcher
    res = dispatch_sales_touch(
        db,
        tenant_id,
        lead,
        channel=channel,
        body=body,
        subject=subject,
        step_number=99,
    )

    now = datetime.now(timezone.utc)
    data = dict(lead.data or {})
    conv = list(data.get("conversation") or data.get("conversations") or [])

    outbound_entry = {
        "direction": "outbound",
        "channel": channel,
        "content": body,
        "subject": subject,
        "author": current_user.name or current_user.email or "Sales Rep",
        "at": now.isoformat(),
        "sent": res.get("sent", False),
        "delivery_details": res.get("message") or res.get("reason"),
    }
    conv.append(outbound_entry)
    data["conversation"] = conv
    data["conversations"] = conv
    lead.data = data
    lead.updated_at = now
    db.commit()

    return {
        "ok": res.get("sent", False),
        "channel": channel,
        "message": res.get("message", "Dispatched"),
        "entry": outbound_entry,
    }


@router.post("/threads/{lead_id}/ai-suggest")
def get_ai_suggested_replies(
    lead_id: str,
    payload: AISuggestRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Generates 3 tailored AI copilot reply options for the current lead thread."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    company = lead.company or "your team"
    contact = lead.name or "there"
    intent = payload.intent or "demo_booking"

    # Contextual high-converting objection handlers and reply templates
    suggestions = [
        {
            "id": "sug-1",
            "title": "Meeting Request with Calendar Link",
            "channel": "email",
            "body": f"Hi {contact},\n\nThanks for connecting! I'd love to show you how we've helped similar teams at {company} streamline revenue operations and eliminate friction.\n\nDo you have 15 minutes this Thursday or Friday? Alternatively, feel free to pick a convenient slot directly on my calendar: https://cal.com/octaos-sales/intro\n\nBest regards,\n{current_user.name or 'Sales AI'}",
        },
        {
            "id": "sug-2",
            "title": "Overcome Pricing & ROI Concerns",
            "channel": "email",
            "body": f"Hi {contact},\n\nUnderstood regarding budget constraints. Many companies in your space had similar initial considerations, but achieved full ROI within 45 days through automation savings.\n\nWe offer flexible quarterly pilot milestones so you only scale once measurable pipeline is generated. Would you be open to reviewing the milestone model?\n\nBest regards,\n{current_user.name or 'Sales AI'}",
        },
        {
            "id": "sug-3",
            "title": "Direct WhatsApp / SMS Touch",
            "channel": "whatsapp",
            "body": f"Hi {contact}, following up regarding {company}. Let me know if you are free for a brief 5-minute call today to see if we can assist with your current priorities!",
        },
    ]

    return {
        "intent": intent,
        "lead_id": lead_id,
        "suggestions": suggestions,
    }


@router.post("/threads/{lead_id}/pause-cadence")
def pause_lead_cadence(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Pauses automated cadence execution for a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    data = dict(lead.data or {})
    data["cadence_paused"] = True
    lead.data = data
    db.commit()

    runner = DurableCadenceRunner(db, tenant_id)
    runner.outbox.cancel_pending_for_lead(lead_id=lead.id, reason="cadence_paused_by_user")

    return {"status": "paused", "lead_id": lead_id}


@router.post("/threads/{lead_id}/resume-cadence")
def resume_lead_cadence(
    lead_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Resumes automated cadence execution for a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    data = dict(lead.data or {})
    data["cadence_paused"] = False
    lead.data = data
    db.commit()

    return {"status": "active", "lead_id": lead_id}


@router.post("/cadence/run")
def trigger_cadence_run(
    max_touches: int = Query(50, ge=1, le=200),
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Manually triggers immediate durable cadence execution for this tenant."""
    runner = DurableCadenceRunner(db, tenant_id)
    return runner.run_tenant_cadence(max_touches=max_touches)


@router.get("/cadence/stats")
def get_cadence_stats(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, Any]:
    """Returns live cadence enrollment and execution metrics."""
    runner = DurableCadenceRunner(db, tenant_id)
    return runner.get_cadence_stats()

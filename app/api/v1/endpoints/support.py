from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional, Any
from datetime import datetime, timezone
import re
from pydantic import BaseModel

from app.api import deps
from app.core.config import settings
from app.core.rbac import Action, Resource, require_permission
from app.models.base import User, Tenant
from app.models.verticals import Ticket, TicketMessage, SupportAgentPresence
from app.models.base import APICredential
from app.services.webhook_security import (
    check_and_store_idempotency,
    ensure_tenant_active,
    payload_sha256,
    verify_email_hmac,
    verify_meta_signature,
    verify_whatsapp_token,
)
from app.services.support_chat_service import SupportChatService
from app.services.widget_script import get_widget_embed_js

router = APIRouter()

class ReplyRequest(BaseModel):
    content: str

class SettingsRequest(BaseModel):
    whatsapp_auto_reply: bool = True
    email_auto_reply: bool = True
    widget_auto_reply: bool = True
    live_chat_enabled: bool = True
    widget_title: Optional[str] = "Customer Support"
    widget_welcome: Optional[str] = "Hi there! How can we assist you today?"
    widget_color: Optional[str] = "#2563eb"
    # review_first = AI drafts only (human approves) | auto_send = send after delay if policy allows
    reply_mode: str = "review_first"

class WidgetMessageRequest(BaseModel):
    session_id: str
    message: str = ""
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    sender_phone: Optional[str] = None
    action: Optional[str] = None  # "chat", "request_handoff"

class RaiseTicketRequest(BaseModel):
    session_id: str
    problem: str
    name: str
    email: str
    mobile_no: str

class AgentPresenceRequest(BaseModel):
    is_online: bool

class EmailWebhookRequest(BaseModel):
    sender: str
    subject: str
    content: str

class StudioConfigRequest(BaseModel):
    agent_name: Optional[str] = "Ava"
    company_name: Optional[str] = "Acme Technologies"
    agent_avatar: Optional[str] = "bot"
    tone: Optional[str] = "professional_friendly"
    default_language: Optional[str] = "en"
    signature: Optional[str] = "Warm regards,\nAva & The Support Team"
    greeting_message: Optional[str] = "Hello! I'm Ava from customer support. How can I assist you today?"
    escalation_message: Optional[str] = "I'm connecting you with a live specialist now. A representative will be with you shortly."
    fallback_message: Optional[str] = "Our live agents are currently assisting other customers. A priority support ticket has been registered."
    handoff_timeout_seconds: Optional[int] = 300

from app.services.support_identity_service import SupportIdentityService
from app.services.support_outbound_service import SupportOutboundService

def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def _ticket_to_dict(t: Ticket) -> dict:
    return {
        "id": t.id,
        "subject": t.subject,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "channel": t.channel,
        "customer_contact": t.customer_contact,
        "customer_name": t.customer_name,
        "customer_email": t.customer_email,
        "customer_phone": t.customer_phone,
        "customer_id": t.customer_id,
        "owner_type": t.owner_type or ("human_handling" if t.status == "human_handling" else ("pending_human" if t.status == "pending_human" else "ai")),
        "handoff_started_at": _iso(t.handoff_started_at),
        "handoff_deadline_at": _iso(t.handoff_deadline_at),
        "handoff_generation": t.handoff_generation or 0,
        "claimed_by": t.claimed_by,
        "claimed_at": _iso(t.claimed_at),
        "resolved_at": _iso(t.resolved_at),
        "session_id": t.session_id,
        "mode": t.mode or "ai",
        "approval_status": t.approval_status,
        "created_at": _iso(t.created_at),
        "extra_data": t.extra_data or {},
    }


def _message_to_dict(m: TicketMessage) -> dict:
    return {
        "id": m.id,
        "ticket_id": m.ticket_id,
        "sender": m.sender,
        "content": m.content,
        "direction": m.direction or ("outbound" if m.sender == "agent" else "inbound"),
        "channel": m.channel,
        "delivery_status": m.delivery_status or "delivered",
        "created_at": _iso(m.created_at),
    }


@router.get("/tickets")
def get_tickets(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.READ)),
    room_id: Optional[str] = None,
    room_slug: Optional[str] = None,
) -> Any:
    q = db.query(Ticket).filter(Ticket.tenant_id == tenant_id)
    if room_slug and room_slug.lower() not in ("all", "all_rooms", "*"):
        from app.models.rooms import SectionRoom
        rm = db.query(SectionRoom).filter(
            SectionRoom.tenant_id == tenant_id,
            SectionRoom.section == "support",
            SectionRoom.slug == room_slug.lower(),
        ).first()
        if rm:
            # When viewing the default room, include unassigned tickets (room_id IS NULL)
            # so web widget & webhook tickets are always visible to support agents
            if rm.slug == "default":
                q = q.filter(or_(Ticket.room_id == rm.id, Ticket.room_id.is_(None)))
            else:
                q = q.filter(Ticket.room_id == rm.id)
        elif room_id:
            q = q.filter(Ticket.room_id == room_id)
    elif room_id:
        q = q.filter(Ticket.room_id == room_id)
    tickets = q.order_by(Ticket.created_at.desc()).all()
    return [_ticket_to_dict(t) for t in tickets]

@router.get("/tickets/{ticket_id}/messages")
def get_ticket_messages(
    ticket_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    messages = db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at.asc()).all()
    return [_message_to_dict(m) for m in messages]

@router.post("/tickets/{ticket_id}/reply")
async def manual_reply(
    ticket_id: str,
    payload: ReplyRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.TICKETS, Action.UPDATE)),
) -> Any:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Human agent owns the ticket
    ticket.status = "human_handling"
    ticket.owner_type = "human_handling"
    ticket.mode = "human"
    if not ticket.claimed_by:
        ticket.claimed_by = user.id
    if not ticket.claimed_at:
        ticket.claimed_at = datetime.now(timezone.utc)
    db.commit()

    outbound = SupportOutboundService(db, tenant_id)
    try:
        res = await outbound.send(
            ticket_id=ticket.id,
            channel=ticket.channel or "widget",
            recipient=ticket.customer_contact or "customer",
            content=payload.content,
            sender_type="agent",
            is_ai_caller=False,
        )
        msg_dict = {
            "id": res.get("message_id"),
            "ticket_id": ticket.id,
            "sender": "agent",
            "content": payload.content,
            "direction": "outbound",
            "channel": ticket.channel,
            "delivery_status": res.get("delivery_status", "delivered"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": "success", "message": msg_dict}
    except ValueError as e:
        ve_str = str(e)
        provider = None
        for p in ["linkedin", "meta", "facebook", "instagram", "twitter", "gmail", "whatsapp", "apollo", "hunter", "google_places", "google_calendar", "smtp"]:
            if p in ve_str.lower():
                provider = p
                break
        if provider:
            msg_text = f"I need your {provider} credentials to complete this action."
            return {"status": "action_required", "message": msg_text}
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tickets/{ticket_id}/ai-draft")
async def generate_ai_draft(
    ticket_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.READ)),
) -> Any:
    """Generate a high-quality, KB-grounded response suggestion for human support reps."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    messages = db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at.asc()).all()
    
    last_customer_msg = ""
    history_str = ""
    for m in messages:
        history_str += f"{m.sender.upper()}: {m.content}\n"
        if m.sender == "customer" and m.content:
            last_customer_msg = m.content

    query_text = last_customer_msg or ticket.subject or ticket.description or "Customer inquiry"

    from app.services.kb_rag import KnowledgeRAGService
    from app.services.llm_gateway import LLMGateway

    rag = KnowledgeRAGService(db, tenant_id)
    kb_result = rag.answer_context(query_text, department="Support")
    knowledge_context = kb_result.get("context", "") if kb_result.get("answer_allowed") else ""
    citations = kb_result.get("citations", [])

    llm = LLMGateway(db, tenant_id)
    system_prompt = (
        "You are an expert customer support agent copilot. "
        "Draft a helpful, polite, and accurate response to the customer. "
        "Base your answer on the provided Company Knowledge Base when available. "
        "Keep the reply concise, professional, empathetic, and ready to send. "
        "Do not include placeholders like [Your Name] or mention that you are an AI assistant."
    )
    prompt = (
        f"Conversation History:\n{history_str or 'Customer opened ticket: ' + (ticket.description or ticket.subject or '')}\n\n"
        f"Knowledge Base Context:\n{knowledge_context or 'Rely on standard customer support best practices.'}\n\n"
        f"Customer Inquiry: {query_text}\n\n"
        "Draft the exact response for the human agent to send to the customer:"
    )

    try:
        draft = await llm.complete(
            prompt=prompt,
            model=None,
            provider=None,
            system_prompt=system_prompt,
        )
    except Exception as e:
        draft = f"Thank you for reaching out regarding '{ticket.subject}'. We are reviewing your request and will assist you right away."

    return {
        "status": "success",
        "ticket_id": ticket.id,
        "draft": (draft or "").strip(),
        "citations": citations[:3] if citations else [],
    }


@router.post("/tickets/{ticket_id}/ai-triage")
async def triage_ticket(
    ticket_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.READ)),
) -> Any:
    """Analyze customer sentiment, urgency level, category, and root issue summary."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    messages = db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at.asc()).all()
    history_str = "\n".join([f"{m.sender}: {m.content}" for m in messages if m.content]) or ticket.description or ticket.subject or ""

    from app.services.llm_gateway import LLMGateway
    import json
    llm = LLMGateway(db, tenant_id)

    system_prompt = (
        "You are an AI Support Triage Classifier. Analyze the support ticket and respond ONLY with a valid JSON object with keys: "
        "'sentiment' (one of: 'positive', 'neutral', 'frustrated', 'urgent'), "
        "'urgency' (one of: 'P1', 'P2', 'P3'), "
        "'category' (one of: 'Bug / Technical Issue', 'Billing & Payments', 'Account & Access', 'Feature Request', 'General Inquiry'), "
        "'summary' (one clear sentence summarizing the root customer problem), "
        "'suggested_action' (brief phrase like 'Review billing invoice', 'Provide reset instructions', 'Investigate bug report')."
    )
    prompt = f"Ticket Subject: {ticket.subject}\nChannel: {ticket.channel}\nContent:\n{history_str}\n\nReturn ONLY raw JSON."

    try:
        res = await llm.complete(prompt=prompt, model=None, provider=None, system_prompt=system_prompt)
        clean_res = re.sub(r"^```json\s*|\s*```$", "", res.strip(), flags=re.MULTILINE).strip()
        data = json.loads(clean_res)
    except Exception:
        data = {
            "sentiment": "neutral",
            "urgency": "P2" if ticket.priority == "high" else "P3",
            "category": "General Inquiry",
            "summary": ticket.subject or "Customer inquiry",
            "suggested_action": "Respond to customer inquiry",
        }

    extra = dict(ticket.extra_data or {})
    extra["ai_insights"] = data
    ticket.extra_data = extra
    if data.get("urgency") == "P1":
        ticket.priority = "high"
    db.commit()
    db.refresh(ticket)

    return {"status": "success", "ticket_id": ticket.id, "ai_insights": data}


@router.get("/customers/{customer_id}/history")
def get_customer_history(
    customer_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.READ)),
) -> Any:
    service = SupportIdentityService(db, tenant_id)
    return service.get_customer_history(customer_id)

@router.get("/studio/config")
def get_studio_config(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.READ)),
) -> Any:
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == "support_studio"
    ).first()
    if cred and cred.settings:
        return cred.settings
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    t_name = tenant.name if tenant else "Acme Technologies"
    return {
        "agent_name": "Ava",
        "company_name": t_name,
        "agent_avatar": "bot",
        "tone": "professional_friendly",
        "default_language": "en",
        "signature": f"Warm regards,\nAva & The {t_name} Support Team",
        "greeting_message": f"Hello! I'm Ava from {t_name} customer support. How can I assist you today?",
        "escalation_message": "Connecting you with our live support team now! A representative will connect with you shortly.",
        "fallback_message": f"Our live support agents are currently assisting other customers. A priority support ticket has been registered.",
        "handoff_timeout_seconds": 300,
    }

@router.post("/studio/config")
def save_studio_config(
    payload: StudioConfigRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.UPDATE)),
) -> Any:
    config_dict = payload.model_dump()
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == "support_studio"
    ).first()
    if not cred:
        cred = APICredential(
            tenant_id=tenant_id,
            provider="support_studio",
            encrypted_key="studio_config",
            settings=config_dict
        )
        db.add(cred)
    else:
        cred.settings = config_dict
    db.commit()
    db.refresh(cred)
    return {"status": "success", "config": cred.settings}

def _default_support_settings() -> dict:
    return {
        "whatsapp_auto_reply": True,
        "email_auto_reply": True,
        "widget_auto_reply": True,
        "live_chat_enabled": True,
        "widget_title": "Customer Support",
        "widget_welcome": "Hi there! How can we assist you today?",
        "widget_color": "#2563eb",
        "reply_mode": "review_first",  # safer default: draft for human review
    }


@router.get("/settings")
def get_support_settings(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.READ)),
) -> Any:
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == "support"
    ).first()
    base = _default_support_settings()
    if cred and cred.settings:
        base.update(cred.settings)
    # Reflect enterprise policy if present
    try:
        from app.services.policy_engine import PolicyEngine
        pol = PolicyEngine(db, tenant_id).get_or_create_policy()
        if pol.default_mode == "auto_with_rules":
            base["reply_mode"] = "auto_send"
        elif pol.default_mode == "draft_only":
            base["reply_mode"] = "review_first"
    except Exception:
        pass
    return base


@router.post("/settings")
def save_support_settings(
    payload: SettingsRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(require_permission(Resource.TICKETS, Action.UPDATE)),
) -> Any:
    mode = (payload.reply_mode or "review_first").lower()
    if mode not in ("review_first", "auto_send"):
        raise HTTPException(400, "reply_mode must be review_first or auto_send")

    settings_dict = {
        "whatsapp_auto_reply": payload.whatsapp_auto_reply,
        "email_auto_reply": payload.email_auto_reply,
        "widget_auto_reply": payload.widget_auto_reply,
        "live_chat_enabled": payload.live_chat_enabled,
        "widget_title": payload.widget_title,
        "widget_welcome": payload.widget_welcome,
        "widget_color": payload.widget_color,
        "reply_mode": mode,
    }
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == "support"
    ).first()
    if not cred:
        cred = APICredential(
            tenant_id=tenant_id,
            provider="support",
            encrypted_key="support_settings",
            settings=settings_dict,
        )
        db.add(cred)
    else:
        merged = dict(cred.settings or {})
        merged.update(settings_dict)
        cred.settings = merged

    # Sync HITL policy engine so Support auto-replies respect this choice
    try:
        from app.services.policy_engine import PolicyEngine
        PolicyEngine(db, tenant_id).update_policy({
            "default_mode": "auto_with_rules" if mode == "auto_send" else "draft_only",
        })
    except Exception:
        pass

    db.commit()
    db.refresh(cred)
    return {"status": "success", "settings": cred.settings}


# ── Human Handoff & Claim / Resolve Endpoints ──────────────────────────────

@router.post("/tickets/{ticket_id}/claim")
def claim_ticket(
    ticket_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.TICKETS, Action.UPDATE)),
) -> Any:
    service = SupportChatService(db, tenant_id)
    try:
        return service.claim_ticket(ticket_id, user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
    _: User = Depends(require_permission(Resource.TICKETS, Action.UPDATE)),
) -> Any:
    service = SupportChatService(db, tenant_id)
    try:
        return service.resolve_ticket(ticket_id, user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/agent/presence")
def update_agent_presence(
    payload: AgentPresenceRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    user: User = Depends(deps.get_current_user),
) -> Any:
    service = SupportChatService(db, tenant_id)
    user_name = user.name or user.email.split("@")[0]
    return service.update_agent_presence(user.id, user_name, payload.is_online)


@router.get("/agent/presence")
def get_agent_presence(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(deps.get_current_user),
) -> Any:
    service = SupportChatService(db, tenant_id)
    return service.check_agent_availability()


# ── Public Embeddable Support Widget Endpoints ─────────────────────────────

@router.get("/widget/config/{tenant_id}")
def get_widget_config(
    tenant_id: str,
    db: Session = Depends(deps.get_db),
) -> Any:
    tenant = ensure_tenant_active(db, tenant_id)
    resolved_tenant_id = tenant.id
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == resolved_tenant_id,
        APICredential.provider == "support"
    ).first()
    settings_dict = _default_support_settings()
    if cred and cred.settings:
        settings_dict.update(cred.settings)

    tenant_name = tenant.name if tenant else "Support"

    service = SupportChatService(db, resolved_tenant_id)
    avail = service.check_agent_availability()

    custom_title = settings_dict.get("widget_title")
    title = custom_title if (custom_title and custom_title != "Customer Support") else f"{tenant_name} Support"

    return {
        "tenant_id": resolved_tenant_id,
        "tenant_name": tenant_name,
        "title": title,
        "welcome_message": settings_dict.get("widget_welcome") or "Hi there! How can we assist you today?",
        "brand_color": settings_dict.get("widget_color") or "#2563eb",
        "live_chat_available": avail.get("available", False),
        "online_agents_count": avail.get("online_agents_count", 0),
        "ai_enabled": True
    }


@router.post("/widget/message/{tenant_id}")
async def widget_message(
    tenant_id: str,
    payload: WidgetMessageRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    tenant = ensure_tenant_active(db, tenant_id)
    resolved_tenant_id = tenant.id
    service = SupportChatService(db, resolved_tenant_id)
    return await service.handle_visitor_message(
        session_id=payload.session_id,
        message=payload.message,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        sender_phone=payload.sender_phone,
        action=payload.action
    )


@router.post("/widget/raise-ticket/{tenant_id}")
def widget_raise_ticket(
    tenant_id: str,
    payload: RaiseTicketRequest,
    db: Session = Depends(deps.get_db),
) -> Any:
    tenant = ensure_tenant_active(db, tenant_id)
    resolved_tenant_id = tenant.id
    service = SupportChatService(db, resolved_tenant_id)
    return service.raise_ticket_from_widget(
        session_id=payload.session_id,
        problem=payload.problem,
        name=payload.name,
        email=payload.email,
        mobile_no=payload.mobile_no
    )


@router.get("/widget/poll/{tenant_id}/{session_id}")
def widget_poll(
    tenant_id: str,
    session_id: str,
    db: Session = Depends(deps.get_db),
) -> Any:
    tenant = ensure_tenant_active(db, tenant_id)
    resolved_tenant_id = tenant.id
    ticket = db.query(Ticket).filter(
        Ticket.tenant_id == resolved_tenant_id,
        Ticket.session_id == session_id
    ).order_by(Ticket.created_at.desc()).first()

    if not ticket:
        return {"ticket": None, "messages": [], "mode": "ai"}

    messages = db.query(TicketMessage).filter(
        TicketMessage.ticket_id == ticket.id
    ).order_by(TicketMessage.created_at.asc()).all()

    service = SupportChatService(db, resolved_tenant_id)
    avail = service.check_agent_availability()

    agent_name = None
    if ticket.claimed_by:
        agent_user = db.query(User).filter(User.id == ticket.claimed_by).first()
        if agent_user:
            agent_name = agent_user.name or agent_user.email.split("@")[0]

    return {
        "ticket": {
            "id": ticket.id,
            "status": ticket.status,
            "mode": ticket.mode or "ai",
            "claimed_by": ticket.claimed_by,
            "agent_name": agent_name
        },
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ],
        "live_chat_available": avail.get("available", False)
    }


@router.get("/widget/embed.js")
def widget_embed_js(request: Request) -> Any:
    base_url = str(request.base_url).rstrip("/")
    js_code = get_widget_embed_js(default_api_base=base_url)
    return Response(
        content=js_code,
        media_type="application/javascript",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )


@router.get("/whatsapp/webhook/{tenant_id}")
def verify_whatsapp_webhook(
    tenant_id: str,
    db: Session = Depends(deps.get_db),
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
) -> Any:
    ensure_tenant_active(db, tenant_id)
    if hub_mode == "subscribe" and hub_challenge:
        if not verify_whatsapp_token(db, tenant_id, hub_verify_token):
            raise HTTPException(status_code=403, detail="Invalid verify token")
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    return "Invalid webhook verification request"


@router.post("/whatsapp/webhook/{tenant_id}")
async def receive_whatsapp_webhook(
    tenant_id: str,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    ensure_tenant_active(db, tenant_id)
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")
    if settings.META_APP_SECRET:
        if not verify_meta_signature(settings.META_APP_SECRET, raw, sig):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
    elif not settings.DEV:
        raise HTTPException(status_code=503, detail="META_APP_SECRET not configured")

    import json
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])
        if messages:
            msg = messages[0]
            event_id = msg.get("id") or payload_sha256(raw)
            if not check_and_store_idempotency(
                db,
                tenant_id=tenant_id,
                provider="whatsapp",
                event_id=str(event_id),
                payload_hash=payload_sha256(raw),
            ):
                return {"status": "duplicate"}
            sender = msg.get("from")
            text_body = msg.get("text", {}).get("body", "")
            if sender and text_body:
                from app.services.agents.support import SupportAgent
                agent = SupportAgent(db, tenant_id)
                await agent.handle_incoming_message(
                    channel="whatsapp",
                    sender=sender,
                    content=text_body,
                    external_id=msg.get("id"),
                )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error parsing WhatsApp webhook: {e}")
    return {"status": "ok"}


@router.post("/email/webhook/{tenant_id}")
async def receive_email_webhook(
    tenant_id: str,
    request: Request,
    db: Session = Depends(deps.get_db),
) -> Any:
    from app.services.agents.support import SupportAgent

    ensure_tenant_active(db, tenant_id)
    raw = await request.body()
    sig = (
        request.headers.get("X-Octa-Signature")
        or request.headers.get("X-Hub-Signature-256")
        or request.headers.get("X-Signature")
    )
    # Per-tenant secret from API credentials settings, else global
    secret = settings.EMAIL_WEBHOOK_HMAC_SECRET
    cred = (
        db.query(APICredential)
        .filter(
            APICredential.tenant_id == tenant_id,
            APICredential.provider.in_(["email_webhook", "smtp", "support"]),
        )
        .first()
    )
    if cred and cred.settings and cred.settings.get("webhook_hmac_secret"):
        secret = cred.settings.get("webhook_hmac_secret")
    if secret:
        if not verify_email_hmac(secret, raw, sig):
            raise HTTPException(status_code=403, detail="Invalid email webhook signature")
    elif not settings.DEV:
        raise HTTPException(status_code=503, detail="Email webhook HMAC secret not configured")

    sender = None
    subject = None
    content = None
    external_id = None

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data") or content_type.startswith(
        "application/x-www-form-urlencoded"
    ):
        # Re-parse from body is hard; use form after signature check on raw
        form_data = await request.form()
        sender = form_data.get("sender") or form_data.get("from")
        subject = form_data.get("subject", "")
        content = (
            form_data.get("stripped-text")
            or form_data.get("body-plain")
            or form_data.get("text")
            or form_data.get("body-html")
            or form_data.get("html")
        )
        external_id = form_data.get("Message-Id") or form_data.get("message-id")
    else:
        try:
            import json
            json_data = json.loads(raw.decode("utf-8") or "{}")
            sender = json_data.get("sender") or json_data.get("from")
            subject = json_data.get("subject", "")
            content = (
                json_data.get("stripped-text")
                or json_data.get("body-plain")
                or json_data.get("content")
                or json_data.get("text")
            )
            external_id = json_data.get("message_id") or json_data.get("Message-Id")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

    if not sender or not content:
        raise HTTPException(status_code=400, detail="Missing sender or content")

    eid = str(external_id or payload_sha256(raw))
    if not check_and_store_idempotency(
        db, tenant_id=tenant_id, provider="email", event_id=eid, payload_hash=payload_sha256(raw)
    ):
        return {"status": "duplicate"}

    agent = SupportAgent(db, tenant_id)
    try:
        await agent.handle_incoming_message(
            channel="email",
            sender=str(sender),
            content=str(content),
            subject=str(subject) if subject else None,
            external_id=str(external_id) if external_id else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel

from app.api import deps
from app.models.verticals import Ticket, TicketMessage
from app.models.base import APICredential

router = APIRouter()

class ReplyRequest(BaseModel):
    content: str

class SettingsRequest(BaseModel):
    whatsapp_auto_reply: bool
    email_auto_reply: bool


class EmailWebhookRequest(BaseModel):
    sender: str
    subject: str
    content: str

@router.get("/tickets")
def get_tickets(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    tickets = db.query(Ticket).filter(Ticket.tenant_id == tenant_id).order_by(Ticket.created_at.desc()).all()
    return tickets

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
    return messages

@router.post("/tickets/{ticket_id}/reply")
async def manual_reply(
    ticket_id: str,
    payload: ReplyRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.tenant_id == tenant_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    msg = TicketMessage(
        ticket_id=ticket.id,
        sender="agent",
        content=payload.content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    from app.services.agents.support import SupportAgent
    agent = SupportAgent(db, tenant_id)
    try:
        await agent.send_message(ticket.channel, ticket.customer_contact, payload.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"status": "success", "message": msg}

@router.get("/settings")
def get_support_settings(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == "support"
    ).first()
    if not cred:
        return {"whatsapp_auto_reply": True, "email_auto_reply": True}
    return cred.settings or {"whatsapp_auto_reply": True, "email_auto_reply": True}

@router.post("/settings")
def save_support_settings(
    payload: SettingsRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == "support"
    ).first()
    if not cred:
        cred = APICredential(
            tenant_id=tenant_id,
            provider="support",
            encrypted_key="support_settings",
            settings=payload.dict()
        )
        db.add(cred)
    else:
        cred.settings = payload.dict()
    db.commit()
    return {"status": "success", "settings": cred.settings}


@router.get("/whatsapp/webhook/{tenant_id}")
def verify_whatsapp_webhook(
    tenant_id: str,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
) -> Any:
    if hub_mode == "subscribe" and hub_challenge:
        # In a production app we verify hub_verify_token matches configured credentials
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    return "Invalid webhook verification request"

@router.post("/whatsapp/webhook/{tenant_id}")
async def receive_whatsapp_webhook(
    tenant_id: str,
    payload: dict,
    db: Session = Depends(deps.get_db)
) -> Any:
    try:
        entry = payload.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])
        if messages:
            msg = messages[0]
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
    except Exception as e:
        print(f"Error parsing WhatsApp webhook: {e}")
    return {"status": "ok"}

@router.post("/email/webhook/{tenant_id}")
async def receive_email_webhook(
    tenant_id: str,
    request: Request,
    db: Session = Depends(deps.get_db)
) -> Any:
    from app.services.agents.support import SupportAgent
    
    sender = None
    subject = None
    content = None
    external_id = None

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data") or content_type.startswith("application/x-www-form-urlencoded"):
        form_data = await request.form()
        sender = form_data.get("sender") or form_data.get("from")
        subject = form_data.get("subject", "")
        content = form_data.get("stripped-text") or form_data.get("body-plain") or form_data.get("text") or form_data.get("body-html") or form_data.get("html")
        external_id = form_data.get("Message-Id") or form_data.get("message-id")
    else:
        try:
            json_data = await request.json()
            sender = json_data.get("sender") or json_data.get("from")
            subject = json_data.get("subject", "")
            content = json_data.get("stripped-text") or json_data.get("body-plain") or json_data.get("content") or json_data.get("text")
            external_id = json_data.get("message_id") or json_data.get("Message-Id")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

    if not sender or not content:
        raise HTTPException(status_code=400, detail="Missing sender or content")

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

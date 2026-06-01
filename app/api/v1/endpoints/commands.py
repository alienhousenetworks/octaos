from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, List, Optional
from pydantic import BaseModel
from app.api import deps
from app.services.agents.orchestrator import OrchestratorAgent
from app.models.base import APICredential
from app.models.verticals import ContentPost, Lead
import re
from app.models.agents import ActivityLog, KnowledgeDocument
from app.core.security import encrypt_api_key

router = APIRouter()

class CommandRequest(BaseModel):
    prompt: str
    provider: Optional[str] = "anthropic"
    model: Optional[str] = None

class APIKeyUpdate(BaseModel):
    provider: str
    key: str

class KnowledgeDocCreate(BaseModel):
    department: str
    doc_type: str
    content: str

@router.post("/execute")
async def execute_command(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    request: CommandRequest
) -> Any:
    # 1. Check if user has a primary AI key (for selected provider, or fallback to any primary)
    req_provider = request.provider or "anthropic"
    primary_key = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == req_provider
    ).first()
    
    if not primary_key:
        primary_key = db.query(APICredential).filter(
            APICredential.tenant_id == tenant_id,
            APICredential.provider.in_(["anthropic", "openai", "gemini"])
        ).first()

    # 2. If no key, intercept the prompt
    if not primary_key:
        # Check if the user is pasting a key (simple heuristic)
        if "sk-" in request.prompt or "sk_ant" in request.prompt.lower():
            # Extract key
            match = re.search(r'(sk-[a-zA-Z0-9_\-]+)', request.prompt)
            if match:
                key = match.group(1)
                provider = "anthropic" if "ant" in key.lower() else "openai"
                cred = APICredential(tenant_id=tenant_id, provider=provider, encrypted_key=encrypt_api_key(key))
                db.add(cred)
                
                # Log this activity
                log = ActivityLog(tenant_id=tenant_id, agent_name="System", action="Configuration", description=f"Saved {provider} API key.")
                db.add(log)
                db.commit()
                
                return {"plan": {}, "results": [{"status": "success", "message": f"Awesome! I have saved your {provider} API key. I am now fully operational. What would you like to do?"}]}
            
        # Return fallback asking for key
        log = ActivityLog(tenant_id=tenant_id, agent_name="System", action="ActionRequired", description="Waiting for primary AI API key.")
        db.add(log)
        db.commit()
        return {"plan": {}, "results": [{"status": "action_required", "message": "Hi! Before I can start managing your business, I need an AI brain. Please reply with your Claude or OpenAI API key."}]}

    orchestrator = OrchestratorAgent(db, tenant_id)
    try:
        result = await orchestrator.handle_prompt(
            prompt=request.prompt,
            provider=request.provider,
            model=request.model
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return result

@router.post("/keys")
def update_api_key(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    request: APIKeyUpdate
) -> Any:
    cred = db.query(APICredential).filter(
        APICredential.tenant_id == tenant_id,
        APICredential.provider == request.provider
    ).first()
    
    if cred:
        cred.encrypted_key = encrypt_api_key(request.key)
    else:
        cred = APICredential(
            tenant_id=tenant_id,
            provider=request.provider,
            encrypted_key=encrypt_api_key(request.key)
        )
        db.add(cred)
    
    db.commit()
    return {"message": f"{request.provider} key updated successfully"}

@router.get("/keys")
def get_configured_keys(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    creds = db.query(APICredential).filter(APICredential.tenant_id == tenant_id).all()
    return {"configured_providers": [c.provider for c in creds]}

@router.get("/queue")
def get_content_queue(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    
    posts_to_check = db.query(ContentPost).filter(ContentPost.tenant_id == tenant_id).all()
    needs_commit = False
    
    for p in posts_to_check:
        # Delete if published
        if p.status == 'published' or p.approval_status == 'published':
            db.delete(p)
            needs_commit = True
            continue
            
        # Delete if pending and out of date (older than 2 days)
        if p.approval_status == 'pending' and p.created_at:
            created_at = p.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at < now - timedelta(days=2):
                db.delete(p)
                needs_commit = True
                continue

    if needs_commit:
        db.commit()

    posts = db.query(ContentPost).filter(ContentPost.tenant_id == tenant_id).order_by(ContentPost.day).all()
    leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).all()
    
    posts_data = [{"id": p.id, "platform": p.platform, "content": p.content, "day": p.day, "status": p.status, "scheduled_at": p.scheduled_at} for p in posts]
    leads_data = [{"id": l.id, "name": l.name, "company": l.company, "source": l.source, "status": l.status} for l in leads]
    return {"posts": posts_data, "leads": leads_data}

@router.get("/timeline")
def get_timeline(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    logs = db.query(ActivityLog).filter(ActivityLog.tenant_id == tenant_id).order_by(ActivityLog.created_at.desc()).limit(50).all()
    return [{"id": log.id, "agent_name": log.agent_name, "action": log.action, "description": log.description, "status": log.status, "created_at": log.created_at.isoformat()} for log in logs]

@router.post("/knowledge")
def add_knowledge_doc(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    request: KnowledgeDocCreate
) -> Any:
    doc = KnowledgeDocument(
        tenant_id=tenant_id,
        department=request.department,
        doc_type=request.doc_type,
        content=request.content
    )
    db.add(doc)
    db.commit()
    return {"message": "Knowledge document added successfully"}

@router.get("/knowledge")
def get_knowledge_docs(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.tenant_id == tenant_id).all()
    return [{"id": d.id, "department": d.department, "doc_type": d.doc_type, "content": d.content, "created_at": d.created_at.isoformat() if d.created_at else None} for d in docs]

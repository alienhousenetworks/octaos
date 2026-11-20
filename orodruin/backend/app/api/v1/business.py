from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.business.models import (
    CRMDeal,
    ContentAsset,
    HRCandidate,
    MarketingCampaign,
    SupportTicket,
    WorkflowRun,
)
from app.core.inference.service import InferenceError, InferenceService
from app.core.permissions.rbac import Action, Resource, require_permission
from app.core.tenancy.models import User
from app.db import get_db

router = APIRouter(prefix="/api/v1/business", tags=["business"])


class CreateDealRequest(BaseModel):
    title: str
    company_name: str
    lead_id: Optional[str] = None
    stage: str = "qualified"
    value_usd: float = 0.0


class CreateCampaignRequest(BaseModel):
    name: str
    channel: str = "linkedin"
    strategy_brief_id: Optional[str] = None


class GenerateContentRequest(BaseModel):
    campaign_id: Optional[str] = None
    asset_type: str = Field(pattern="^(text|image|video)$")
    prompt: str = Field(min_length=3, max_length=2000)


class CreateCandidateRequest(BaseModel):
    name: str
    role_applied: str
    score: float = 0.0


class CreateTicketRequest(BaseModel):
    subject: str
    description: str
    priority: str = "medium"


@router.get("/deals")
def list_deals(
    current_user: User = Depends(require_permission(Resource.LEADS, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = db.query(CRMDeal).filter(CRMDeal.tenant_id == current_user.tenant_id).all()
    return [{"id": d.id, "title": d.title, "company_name": d.company_name, "stage": d.stage, "value_usd": d.value_usd} for d in rows]


@router.post("/deals")
def create_deal(
    payload: CreateDealRequest,
    current_user: User = Depends(require_permission(Resource.LEADS, Action.CREATE)),
    db: Session = Depends(get_db),
):
    deal = CRMDeal(tenant_id=current_user.tenant_id, owner_user_id=current_user.id, **payload.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return {"id": deal.id, "title": deal.title, "company_name": deal.company_name, "stage": deal.stage, "value_usd": deal.value_usd}


@router.get("/campaigns")
def list_campaigns(
    current_user: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = db.query(MarketingCampaign).filter(MarketingCampaign.tenant_id == current_user.tenant_id).all()
    return [{"id": c.id, "name": c.name, "channel": c.channel, "status": c.status, "metrics": c.metrics_json} for c in rows]


@router.post("/campaigns")
def create_campaign(
    payload: CreateCampaignRequest,
    current_user: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    db: Session = Depends(get_db),
):
    camp = MarketingCampaign(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(camp)
    db.commit()
    db.refresh(camp)
    return {"id": camp.id, "name": camp.name, "channel": camp.channel, "status": camp.status}


@router.post("/content/generate")
async def generate_content_asset(
    payload: GenerateContentRequest,
    current_user: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    db: Session = Depends(get_db),
):
    inf = InferenceService()
    text_out: Optional[str] = None
    asset_url: Optional[str] = None
    model_used = inf.text_model

    if payload.asset_type == "text":
        try:
            text_out = await inf.generate_text(payload.prompt)
        except InferenceError:
            text_out = f"[Draft queued for local LLM {inf.text_model}] {payload.prompt}"
    elif payload.asset_type == "image":
        model_used = inf.image_model
        try:
            res = await inf.generate_image(payload.prompt)
            asset_url = res.get("asset_url")
        except InferenceError:
            asset_url = None
    else:
        model_used = inf.video_model
        try:
            res = await inf.generate_video(payload.prompt)
            asset_url = res.get("asset_url")
        except InferenceError:
            asset_url = None

    asset = ContentAsset(
        tenant_id=current_user.tenant_id,
        campaign_id=payload.campaign_id,
        asset_type=payload.asset_type,
        prompt=payload.prompt,
        text_content=text_out,
        asset_url=asset_url,
        model_used=model_used,
        status="pending_approval",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {
        "id": asset.id,
        "asset_type": asset.asset_type,
        "model_used": asset.model_used,
        "text_content": asset.text_content,
        "asset_url": asset.asset_url,
        "status": asset.status,
    }


@router.get("/content")
def list_content_assets(
    current_user: User = Depends(require_permission(Resource.CAMPAIGNS, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = db.query(ContentAsset).filter(ContentAsset.tenant_id == current_user.tenant_id).all()
    return [
        {
            "id": a.id,
            "asset_type": a.asset_type,
            "prompt": a.prompt,
            "model_used": a.model_used,
            "status": a.status,
            "text_content": a.text_content,
            "asset_url": a.asset_url,
        }
        for a in rows
    ]


@router.post("/content/{asset_id}/approve")
def approve_content_asset(
    asset_id: str,
    current_user: User = Depends(require_permission(Resource.PUBLISH, Action.EXECUTE)),
    db: Session = Depends(get_db),
):
    asset = db.query(ContentAsset).filter(ContentAsset.id == asset_id, ContentAsset.tenant_id == current_user.tenant_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Content asset not found.")
    asset.status = "approved"
    db.commit()
    return {"id": asset.id, "status": asset.status}


@router.get("/hr/candidates")
def list_candidates(
    current_user: User = Depends(require_permission(Resource.HR, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = db.query(HRCandidate).filter(HRCandidate.tenant_id == current_user.tenant_id).all()
    return [{"id": c.id, "name": c.name, "role_applied": c.role_applied, "stage": c.stage, "score": c.score} for c in rows]


@router.post("/hr/candidates")
def create_candidate(
    payload: CreateCandidateRequest,
    current_user: User = Depends(require_permission(Resource.HR, Action.CREATE)),
    db: Session = Depends(get_db),
):
    c = HRCandidate(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "name": c.name, "role_applied": c.role_applied, "stage": c.stage}


@router.get("/support/tickets")
def list_tickets(
    current_user: User = Depends(require_permission(Resource.TICKETS, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = db.query(SupportTicket).filter(SupportTicket.tenant_id == current_user.tenant_id).all()
    return [{"id": t.id, "subject": t.subject, "priority": t.priority, "status": t.status} for t in rows]


@router.post("/support/tickets")
def create_ticket(
    payload: CreateTicketRequest,
    current_user: User = Depends(require_permission(Resource.TICKETS, Action.CREATE)),
    db: Session = Depends(get_db),
):
    t = SupportTicket(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "subject": t.subject, "priority": t.priority, "status": t.status}


@router.get("/workflows")
def list_workflows(
    current_user: User = Depends(require_permission(Resource.WORKFLOWS, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = db.query(WorkflowRun).filter(WorkflowRun.tenant_id == current_user.tenant_id).all()
    return [{"id": w.id, "name": w.name, "status": w.status, "steps": w.steps_json} for w in rows]

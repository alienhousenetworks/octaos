"""Industry packs, the sales workforce map, and the record copilot."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.models.base import User
from app.models.verticals import BusinessProfile, Lead
from app.services.sales_os.copilot.record import advise_record
from app.services.sales_os.verticals.registry import get_pack, list_packs, preview_switch, resolve_pack_id
from app.services.sales_os.workforce.organization import organization

router = APIRouter()


class PackSelect(BaseModel):
    pack_id: str = Field(min_length=1, max_length=64)


class CopilotAsk(BaseModel):
    lead_id: str = Field(min_length=1, max_length=64)
    question: str = Field(default="What should we do next with this customer?", max_length=2000)


def _profile(db: Session, tenant_id: str) -> BusinessProfile | None:
    return db.query(BusinessProfile).filter(BusinessProfile.tenant_id == tenant_id).first()


def _lead_dict(lead: Lead) -> dict[str, Any]:
    data = lead.data if isinstance(lead.data, dict) else {}
    return {
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "company": lead.company,
        "source": lead.source,
        "status": lead.status,
        "score": lead.score,
        "company_email": lead.company_email,
        "mobile_no": lead.mobile_no,
        "why": lead.why,
        "need_of_what": lead.need_of_what,
        "target_context": lead.target_context,
        "evidence_url": data.get("evidence_url"),
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
        "data": data,
    }


@router.get("/verticals")
def read_verticals() -> dict[str, Any]:
    packs = list_packs()
    return {
        "count": len(packs),
        "note": "Packs change labels and guardrails. They do not copy the CRM.",
        "packs": packs,
    }


def _active_sales_pack_id(profile: BusinessProfile | None) -> str | None:
    if not profile:
        return None
    return getattr(profile, "sales_industry_pack_id", None) or getattr(profile, "industry_pack_id", None)


@router.get("/verticals/active")
def read_active_vertical(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    profile = _profile(db, tenant_id)
    pack_id = resolve_pack_id(_active_sales_pack_id(profile))
    pack = get_pack(pack_id) if pack_id else None
    count = db.query(Lead).filter(Lead.tenant_id == tenant_id).count()
    return {
        "selected": pack is not None,
        "pack": pack,
        "records": count,
    }


@router.post("/verticals/active")
def select_vertical(
    body: PackSelect,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    pack_id = resolve_pack_id(body.pack_id)
    if pack_id is None:
        raise HTTPException(status_code=404, detail="Unknown industry pack")
    profile = _profile(db, tenant_id)
    current = resolve_pack_id(_active_sales_pack_id(profile))
    count = db.query(Lead).filter(Lead.tenant_id == tenant_id).count()
    if profile is None:
        profile = BusinessProfile(tenant_id=tenant_id, sales_industry_pack_id=pack_id, industry_pack_id=pack_id)
        db.add(profile)
    else:
        profile.sales_industry_pack_id = pack_id
        if not getattr(profile, "industry_pack_id", None):
            profile.industry_pack_id = pack_id
    db.commit()
    preview = preview_switch(current, pack_id, count)
    preview["records_preserved"] = db.query(Lead).filter(Lead.tenant_id == tenant_id).count()
    return preview


@router.get("/verticals/{pack_id}")
def read_vertical(pack_id: str) -> dict[str, Any]:
    pack = get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Unknown industry pack")
    return pack


class StageTransitionCheck(BaseModel):
    current_stage: str
    next_stage: str


@router.post("/verticals/transition/validate")
def validate_stage_transition(
    body: StageTransitionCheck,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    from app.services.sales_os.industry_runtime.manifest import validate_manifest
    from app.services.sales_os.industry_runtime.pipeline_engine import PipelineEngine

    profile = _profile(db, tenant_id)
    pack_id = resolve_pack_id(_active_sales_pack_id(profile))
    pack = get_pack(pack_id) if pack_id else None
    if not pack or "pipeline_stages" not in pack:
        return {"allowed": True, "reason": "No strict transitions defined"}
    manifest = validate_manifest(pack)
    engine = PipelineEngine(manifest)
    engine.validate_transition(body.current_stage, body.next_stage)
    return {"allowed": True, "current_stage": body.current_stage, "next_stage": body.next_stage}



@router.get("/workforce")
def read_workforce() -> dict[str, Any]:
    return organization()


@router.post("/copilot/record")
def copilot_for_record(
    body: CopilotAsk,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    lead = (
        db.query(Lead)
        .filter(Lead.id == body.lead_id, Lead.tenant_id == tenant_id)
        .first()
    )
    if lead is None:
        raise HTTPException(status_code=404, detail="Record not found")
    profile = _profile(db, tenant_id)
    pack_id = resolve_pack_id(_active_sales_pack_id(profile))
    return advise_record(_lead_dict(lead), pack_id, body.question)

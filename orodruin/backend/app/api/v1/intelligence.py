from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions.rbac import Action, Resource, require_permission
from app.core.tenancy.models import User
from app.db import get_db
from app.intelligence.models import (
    CompanyProfile,
    IntelligenceLead,
    MarketSignal,
    StrategyBrief,
)
from app.intelligence.service import IntelligenceEngine

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


class ResearchCompanyRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    domain: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class DiscoverLeadsRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=255)
    industry: Optional[str] = None
    region: Optional[str] = None
    company_profile_id: Optional[str] = None
    count: int = Field(default=5, ge=1, le=25)


class MarketTrendRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=255)
    region: Optional[str] = None
    signal_type: str = "trend"
    lat: Optional[float] = None
    lon: Optional[float] = None


class StrategyBriefRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    company_profile_id: Optional[str] = None
    topic: Optional[str] = None
    channels: Optional[list[str]] = None


@router.post("/companies/research")
async def research_company(
    payload: ResearchCompanyRequest,
    current_user: User = Depends(require_permission(Resource.INTELLIGENCE, Action.CREATE)),
    db: Session = Depends(get_db),
):
    engine = IntelligenceEngine(db, current_user.tenant_id)
    profile = await engine.research_company(**payload.model_dump())
    return {
        "id": profile.id,
        "name": profile.name,
        "domain": profile.domain,
        "industry": profile.industry,
        "country": profile.country,
        "lat": profile.lat,
        "lon": profile.lon,
        "summary": profile.summary,
        "products": profile.products_json,
        "competitors": profile.competitors_json,
        "opportunities": profile.opportunities_json,
        "risks": profile.risks_json,
        "evidence": profile.evidence_json,
        "classification": profile.classification,
        "confidence": profile.confidence,
    }


@router.get("/companies")
def list_companies(
    current_user: User = Depends(require_permission(Resource.INTELLIGENCE, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(CompanyProfile)
        .filter(CompanyProfile.tenant_id == current_user.tenant_id)
        .order_by(CompanyProfile.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "domain": r.domain,
            "industry": r.industry,
            "country": r.country,
            "lat": r.lat,
            "lon": r.lon,
            "summary": r.summary,
            "classification": r.classification,
            "confidence": r.confidence,
        }
        for r in rows
    ]


@router.post("/leads/discover")
async def discover_leads(
    payload: DiscoverLeadsRequest,
    current_user: User = Depends(require_permission(Resource.LEADS, Action.CREATE)),
    db: Session = Depends(get_db),
):
    engine = IntelligenceEngine(db, current_user.tenant_id)
    leads = await engine.discover_leads(**payload.model_dump())
    return [
        {
            "id": l.id,
            "company_name": l.company_name,
            "contact_role": l.contact_role,
            "contact_email": l.contact_email,
            "contact_verified": l.contact_verified,
            "industry": l.industry,
            "location": l.location,
            "opportunity": l.opportunity,
            "trigger_signal": l.trigger_signal,
            "evidence": l.evidence_json,
            "classification": l.classification,
            "fit_score": l.fit_score,
            "priority": l.priority,
            "next_action": l.next_action,
            "status": l.status,
        }
        for l in leads
    ]


@router.get("/leads")
def list_leads(
    current_user: User = Depends(require_permission(Resource.LEADS, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(IntelligenceLead)
        .filter(IntelligenceLead.tenant_id == current_user.tenant_id)
        .order_by(IntelligenceLead.created_at.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "company_name": l.company_name,
            "contact_role": l.contact_role,
            "contact_verified": l.contact_verified,
            "industry": l.industry,
            "location": l.location,
            "lat": l.lat,
            "lon": l.lon,
            "opportunity": l.opportunity,
            "fit_score": l.fit_score,
            "priority": l.priority,
            "status": l.status,
            "classification": l.classification,
        }
        for l in rows
    ]


@router.post("/signals/analyze")
async def analyze_market_signal(
    payload: MarketTrendRequest,
    current_user: User = Depends(require_permission(Resource.INTELLIGENCE, Action.CREATE)),
    db: Session = Depends(get_db),
):
    engine = IntelligenceEngine(db, current_user.tenant_id)
    s = await engine.analyze_market_trend(**payload.model_dump())
    return {
        "id": s.id,
        "topic": s.topic,
        "region": s.region,
        "signal_type": s.signal_type,
        "summary": s.summary,
        "business_impact": s.business_impact,
        "evidence": s.evidence_json,
        "classification": s.classification,
        "confidence": s.confidence,
    }


@router.get("/signals")
def list_market_signals(
    current_user: User = Depends(require_permission(Resource.INTELLIGENCE, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(MarketSignal)
        .filter(MarketSignal.tenant_id == current_user.tenant_id)
        .order_by(MarketSignal.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "topic": s.topic,
            "region": s.region,
            "signal_type": s.signal_type,
            "summary": s.summary,
            "business_impact": s.business_impact,
            "confidence": s.confidence,
            "lat": s.lat,
            "lon": s.lon,
        }
        for s in rows
    ]


@router.post("/strategy")
async def create_strategy_brief(
    payload: StrategyBriefRequest,
    current_user: User = Depends(require_permission(Resource.CAMPAIGNS, Action.CREATE)),
    db: Session = Depends(get_db),
):
    engine = IntelligenceEngine(db, current_user.tenant_id)
    brief = await engine.generate_strategy_brief(**payload.model_dump())
    return {
        "id": brief.id,
        "title": brief.title,
        "target_audience": brief.target_audience,
        "sales_strategy": brief.sales_strategy,
        "marketing_strategy": brief.marketing_strategy,
        "campaign_brief": brief.campaign_brief,
        "recommended_channels": brief.recommended_channels,
        "status": brief.status,
    }


@router.get("/map-overlay")
def business_map_overlay(
    current_user: User = Depends(require_permission(Resource.INTELLIGENCE, Action.READ)),
    db: Session = Depends(get_db),
):
    """GeoJSON FeatureCollection plotting tenant companies, leads, and market signals on Orodruin's map."""
    features = []
    for c in db.query(CompanyProfile).filter(CompanyProfile.tenant_id == current_user.tenant_id).all():
        if c.lat is not None and c.lon is not None:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [c.lon, c.lat]},
                    "properties": {"kind": "company", "id": c.id, "name": c.name, "industry": c.industry},
                }
            )
    for l in db.query(IntelligenceLead).filter(IntelligenceLead.tenant_id == current_user.tenant_id).all():
        if l.lat is not None and l.lon is not None:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [l.lon, l.lat]},
                    "properties": {"kind": "lead", "id": l.id, "name": l.company_name, "priority": l.priority},
                }
            )
    for s in db.query(MarketSignal).filter(MarketSignal.tenant_id == current_user.tenant_id).all():
        if s.lat is not None and s.lon is not None:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [s.lon, s.lat]},
                    "properties": {"kind": "signal", "id": s.id, "name": s.topic, "impact": s.business_impact},
                }
            )
    return {"type": "FeatureCollection", "features": features}

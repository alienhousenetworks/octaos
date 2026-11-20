"""Native 100% Orodruin Global OSINT & Intelligence API endpoints for OctaOS."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.services.orodruin_intel import OrodruinIntelService

router = APIRouter()


class AnalyzeIntelRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=255)
    region: Optional[str] = None
    company_name: Optional[str] = None


@router.get("/signals")
async def get_osint_signals(
    topic: str = Query(default="technology", min_length=2, max_length=200),
    region: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=12, ge=1, le=30),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().fetch_signals(topic=topic, region=region, limit=limit)


@router.post("/analyze")
async def analyze_osint_strategy(
    payload: AnalyzeIntelRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().analyze_for_strategy(
        db,
        str(current_user.tenant_id),
        topic=payload.topic,
        region=payload.region,
        company_name=payload.company_name,
    )


@router.get("/geolocate")
async def geolocate_ip(
    ip: str = Query(min_length=7, max_length=64),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().geolocate_ip(ip)


@router.get("/cyber")
async def cyber_lookup(
    ip: str = Query(min_length=7, max_length=64),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().cyber_lookup(ip)


@router.get("/ransomware")
async def recent_ransomware(
    limit: int = Query(default=12, ge=1, le=30),
    current_user=Depends(get_current_user),
):
    try:
        return {"items": await OrodruinIntelService().get_ransomware(limit=limit)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ransomware feed unavailable: {exc}") from exc


@router.get("/awards")
async def federal_awards(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
    current_user=Depends(get_current_user),
):
    return {"items": await OrodruinIntelService().finance_awards(q, limit=limit)}


@router.get("/papers")
async def arxiv_papers(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
    current_user=Depends(get_current_user),
):
    return {"items": await OrodruinIntelService().research_papers(q, limit=limit)}


@router.get("/markets")
async def live_markets(current_user=Depends(get_current_user)):
    return await OrodruinIntelService().get_markets()


@router.get("/prediction")
async def prediction_markets(
    limit: int = Query(default=8, ge=1, le=20),
    current_user=Depends(get_current_user),
):
    return {"items": await OrodruinIntelService().get_prediction_markets(limit=limit)}


@router.get("/sanctions")
async def search_sanctions(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
    current_user=Depends(get_current_user),
):
    return {"items": await OrodruinIntelService().search_sanctions(q, limit=limit)}


@router.get("/graph")
async def actor_graph(
    topic: str = Query(default="technology"),
    region: Optional[str] = Query(default=None),
    current_user=Depends(get_current_user),
):
    svc = OrodruinIntelService()
    feed = await svc.fetch_signals(topic=topic, region=region, limit=12)
    return svc.build_actor_graph(feed["signals"], topic)


@router.get("/map-overlay")
async def get_map_overlay(
    topic: str = Query(default="technology"),
    region: Optional[str] = Query(default=None),
    current_user=Depends(get_current_user),
):
    svc = OrodruinIntelService()
    feed = await svc.fetch_signals(topic=topic, region=region, limit=15)
    features = []
    for s in feed["signals"]:
        if s.get("lat") is not None and s.get("lon") is not None:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                "properties": {
                    "source": s.get("source"),
                    "category": s.get("category"),
                    "title": s.get("title"),
                    "url": s.get("url"),
                },
            })
    return {"type": "FeatureCollection", "features": features}

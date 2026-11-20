"""Orodruin Global OSINT & Intelligence API endpoints for OctaOS."""
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.services.orodruin_intel import OrodruinIntelService

router = APIRouter()
ORODRUIN_API_URL = os.getenv("ORODRUIN_API_URL", "http://127.0.0.1:8001").rstrip("/")


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
    svc = OrodruinIntelService()
    return await svc.fetch_signals(topic=topic, region=region, limit=limit)


@router.post("/analyze")
async def analyze_osint_strategy(
    payload: AnalyzeIntelRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = OrodruinIntelService()
    return await svc.analyze_for_strategy(
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
    svc = OrodruinIntelService()
    return await svc.geolocate_ip(ip)


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


@router.get("/proxy/{path:path}")
async def proxy_orodruin_get(
    path: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Authenticated bridge to Orodruin's 41 OSINT endpoints (/api/*)."""
    clean_path = path.lstrip("/")
    target = f"{ORODRUIN_API_URL}/api/{clean_path}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(target, params=dict(request.query_params))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Orodruin service unavailable at {target}: {exc}") from exc

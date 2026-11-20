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


@router.get("/cameras")
async def live_cameras(
    limit: int = Query(default=80, ge=1, le=300),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().fetch_cameras(limit=limit)


@router.get("/flights")
async def live_flights(
    limit: int = Query(default=250, ge=1, le=1000),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().fetch_flights(limit=limit)


@router.get("/disasters")
async def live_disasters(
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().fetch_disasters(limit=limit)


@router.get("/weather-radar")
async def weather_radar(current_user=Depends(get_current_user)):
    return await OrodruinIntelService().fetch_weather_radar()


@router.get("/deep-search")
async def deep_web_search(
    q: str = Query(min_length=2, max_length=250),
    count: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().deep_search(db, str(current_user.tenant_id), q, count=count)


@router.get("/weather")
async def get_weather(lat: float = Query(...), lon: float = Query(...), current_user=Depends(get_current_user)):
    return await OrodruinIntelService().fetch_weather(lat, lon)


@router.get("/airquality")
async def get_air_quality(lat: float = Query(...), lon: float = Query(...), current_user=Depends(get_current_user)):
    return await OrodruinIntelService().fetch_air_quality(lat, lon)


@router.get("/spaceweather")
async def get_space_weather(current_user=Depends(get_current_user)):
    return await OrodruinIntelService().fetch_space_weather()


@router.get("/geocode")
async def geocode_place(q: str = Query(min_length=2), limit: int = Query(default=5, ge=1, le=10), current_user=Depends(get_current_user)):
    return {"results": await OrodruinIntelService().geocode(q, limit=limit)}


@router.get("/route")
async def route_between(
    from_lat: float = Query(...),
    from_lon: float = Query(...),
    to_lat: float = Query(...),
    to_lon: float = Query(...),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().route(from_lat, from_lon, to_lat, to_lon)


@router.get("/breaches")
async def get_breaches(limit: int = Query(default=12, ge=1, le=30), current_user=Depends(get_current_user)):
    return {"items": await OrodruinIntelService().fetch_breaches(limit=limit)}


@router.get("/news")
async def get_news_rss(limit: int = Query(default=15, ge=1, le=30), current_user=Depends(get_current_user)):
    return {"items": await OrodruinIntelService().fetch_news_rss(limit=limit)}


@router.get("/cables")
async def get_submarine_cables(limit: int = Query(default=80, ge=1, le=200), current_user=Depends(get_current_user)):
    return await OrodruinIntelService().fetch_submarine_cables(limit=limit)


@router.get("/satellites")
async def get_satellites(limit: int = Query(default=40, ge=1, le=100), current_user=Depends(get_current_user)):
    return await OrodruinIntelService().fetch_satellites(limit=limit)


@router.get("/area-intel")
async def get_area_intel(lat: float = Query(...), lon: float = Query(...), current_user=Depends(get_current_user)):
    return await OrodruinIntelService().area_intel(lat, lon)


class FindLeadsRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    industry: Optional[str] = None
    geography: Optional[str] = None
    buyer_roles: Optional[str] = None
    count: int = Field(default=8, ge=1, le=20)
    save_to_crm: bool = False


@router.post("/find-leads")
async def find_company_leads(
    payload: FindLeadsRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().find_company_leads(
        db,
        str(current_user.tenant_id),
        query=payload.query,
        industry=payload.industry,
        geography=payload.geography,
        buyer_roles=payload.buyer_roles,
        count=payload.count,
        save_to_crm=payload.save_to_crm,
    )


class RegisterSiteRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    industry: str = "general"
    site_type: str = "facility"
    lat: Optional[float] = None
    lon: Optional[float] = None
    camera_url: Optional[str] = None
    telemetry_url: Optional[str] = None
    metrics: dict = Field(default_factory=dict)
    notes: Optional[str] = None


class SiteReportRequest(BaseModel):
    site_id: Optional[str] = None
    focus: Optional[str] = None


@router.get("/sites")
def list_tenant_sites(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return {"items": OrodruinIntelService().list_sites(db, str(current_user.tenant_id))}


@router.post("/sites")
def register_tenant_site(
    payload: RegisterSiteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return OrodruinIntelService().register_site(
        db,
        str(current_user.tenant_id),
        **payload.model_dump(),
    )


@router.post("/site-report")
async def generate_site_report(
    payload: SiteReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await OrodruinIntelService().generate_site_report(
        db,
        str(current_user.tenant_id),
        site_id=payload.site_id,
        focus=payload.focus,
    )

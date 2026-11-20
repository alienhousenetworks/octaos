"""Native 100% Orodruin OSINT & Intelligence integration for OctaOS.

Provides direct async access to public OSINT feeds (GDELT, USGS, NASA EONET,
Shodan InternetDB, ransomware.live, USASpending, ArXiv, CoinGecko, Polymarket,
ip-api, OpenSanctions) and fuses them with LLMGateway + LearningLoop.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote_plus

import httpx
from sqlalchemy.orm import Session


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrodruinIntelService:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 12.0):
        self.sidecar_url = (base_url or os.getenv("ORODRUIN_API_URL", "")).strip().rstrip("/")
        self.timeout = timeout

    async def fetch_signals(
        self,
        *,
        topic: str = "technology",
        region: Optional[str] = None,
        limit: int = 12,
    ) -> dict[str, Any]:
        signals: list[dict[str, Any]] = []
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            # 1. GDELT 2.0 Doc API
            try:
                q = f"{topic} {region}".strip() if region else topic
                gdelt_url = (
                    "https://api.gdeltproject.org/api/v2/doc/doc"
                    f"?query={quote_plus(q)}&mode=ArtList&maxrecords={min(limit, 10)}&format=json"
                )
                r = await client.get(gdelt_url)
                if r.is_success:
                    for art in (r.json().get("articles") or [])[:limit]:
                        signals.append({
                            "source": "gdelt",
                            "category": "news",
                            "title": art.get("title") or "GDELT Article",
                            "url": art.get("url") or "",
                            "domain": art.get("domain"),
                            "country": art.get("sourcecountry"),
                            "timestamp": art.get("seendate") or _now_iso(),
                        })
            except Exception as exc:
                errors.append(f"gdelt: {exc}")

            # 2. USGS Earthquakes (2.5+ past day)
            try:
                r = await client.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson")
                if r.is_success:
                    for feat in (r.json().get("features") or [])[:6]:
                        props = feat.get("properties") or {}
                        coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
                        signals.append({
                            "source": "usgs",
                            "category": "seismic",
                            "title": props.get("title") or "Seismic Event",
                            "url": props.get("url") or "",
                            "lon": coords[0],
                            "lat": coords[1],
                            "magnitude": props.get("mag"),
                            "timestamp": _now_iso(),
                        })
            except Exception as exc:
                errors.append(f"usgs: {exc}")

            # 3. NASA EONET natural events
            try:
                r = await client.get("https://eonet.gsfc.nasa.gov/api/v3/events?limit=6&status=open")
                if r.is_success:
                    for ev in (r.json().get("events") or [])[:6]:
                        geom = (ev.get("geometry") or [{}])[0]
                        coords = geom.get("coordinates") if isinstance(geom.get("coordinates"), list) else [None, None]
                        lon, lat = (coords[0], coords[1]) if len(coords) >= 2 and isinstance(coords[0], (int, float)) else (None, None)
                        signals.append({
                            "source": "nasa_eonet",
                            "category": "hazard",
                            "title": ev.get("title") or "Natural Event",
                            "url": ev.get("link") or "",
                            "lon": lon,
                            "lat": lat,
                            "timestamp": geom.get("date") or _now_iso(),
                        })
            except Exception as exc:
                errors.append(f"eonet: {exc}")

        return {
            "topic": topic,
            "region": region,
            "count": len(signals),
            "signals": signals,
            "errors": errors,
            "retrieved_at": _now_iso(),
        }

    async def cyber_lookup(self, ip: str) -> dict[str, Any]:
        """Shodan InternetDB lookup (free, no key required)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"https://internetdb.shodan.io/{quote_plus(ip)}")
            if r.status_code == 404:
                return {"ip": ip, "ports": [], "vulns": [], "hostnames": [], "tags": []}
            r.raise_for_status()
            return r.json()

    async def get_ransomware(self, limit: int = 12) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get("https://api.ransomware.live/v2/recentvictims")
            r.raise_for_status()
            data = r.json()
            return (data if isinstance(data, list) else [])[:limit]

    async def finance_awards(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """USASpending federal contract awards."""
        payload = {
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency", "Description"],
            "filters": {"keywords": [query], "award_type_codes": ["A", "B", "C", "D"]},
            "limit": limit,
            "page": 1,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post("https://api.usaspending.gov/api/v2/search/spending_by_award/", json=payload)
            r.raise_for_status()
            return r.json().get("results") or []

    async def research_papers(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """ArXiv Atom search."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"https://export.arxiv.org/api/query?search_query=all:{quote_plus(query)}&max_results={limit}"
            )
            r.raise_for_status()
            entries = re.findall(r"<entry>(.*?)</entry>", r.text, flags=re.DOTALL)
            papers = []
            for entry in entries:
                title = re.search(r"<title>(.*?)</title>", entry, flags=re.DOTALL)
                link = re.search(r"<id>(.*?)</id>", entry, flags=re.DOTALL)
                published = re.search(r"<published>(.*?)</published>", entry, flags=re.DOTALL)
                papers.append({
                    "title": " ".join(title.group(1).split()) if title else "Untitled",
                    "url": link.group(1).strip() if link else "",
                    "published": published.group(1).strip() if published else "",
                })
            return papers

    async def get_markets(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin,ethereum,solana", "vs_currencies": "usd", "include_24hr_change": "true"},
            )
            r.raise_for_status()
            return r.json()

    async def get_prediction_markets(self, limit: int = 8) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                "https://gamma-api.polymarket.com/markets",
                params={"limit": limit, "active": "true", "closed": "false"},
            )
            r.raise_for_status()
            data = r.json()
            return [
                {"question": m.get("question"), "volume": m.get("volumeNum"), "slug": m.get("slug")}
                for m in (data if isinstance(data, list) else [])[:limit]
            ]

    async def search_sanctions(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                "https://api.opensanctions.org/search/default",
                params={"q": query, "limit": limit},
            )
            if not r.is_success:
                return []
            return [
                {
                    "id": item.get("id"),
                    "caption": item.get("caption"),
                    "schema": item.get("schema"),
                    "datasets": item.get("datasets", []),
                }
                for item in (r.json().get("results") or [])[:limit]
            ]

    async def geolocate_ip(self, ip: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"http://ip-api.com/json/{quote_plus(ip)}")
            r.raise_for_status()
            return r.json()

    def build_actor_graph(self, signals: list[dict[str, Any]], topic: str) -> dict[str, Any]:
        """Build an entity/source co-occurrence graph for native frontend visualization."""
        nodes: dict[str, dict[str, Any]] = {
            f"topic:{topic}": {"id": f"topic:{topic}", "label": topic, "kind": "topic", "weight": 3}
        }
        edges: list[dict[str, Any]] = []
        for idx, sig in enumerate(signals[:15]):
            src = sig.get("source") or "osint"
            src_id = f"src:{src}"
            if src_id not in nodes:
                nodes[src_id] = {"id": src_id, "label": src.upper(), "kind": "source", "weight": 2}
                edges.append({"source": f"topic:{topic}", "target": src_id, "weight": 1})
            country = sig.get("country") or sig.get("category")
            if country:
                c_id = f"entity:{country}"
                if c_id not in nodes:
                    nodes[c_id] = {"id": c_id, "label": str(country), "kind": "entity", "weight": 1}
                nodes[c_id]["weight"] += 1
                edges.append({"source": src_id, "target": c_id, "weight": 1})
        return {"nodes": list(nodes.values()), "edges": edges}

    async def analyze_for_strategy(
        self,
        db: Session,
        tenant_id: str,
        *,
        topic: str,
        region: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fuse live OSINT signals with LLMGateway + LearningLoop + UI actions."""
        from app.services.learning_loop import LearningLoop
        from app.services.llm_gateway import LLMGateway

        loop = LearningLoop(db, tenant_id)
        strategy_ctx = loop.get_strategy_context("orodruin_intel", "market_strategy")
        decision_id = loop.record_decision(
            agent_name="orodruin_intel",
            task_type="market_strategy",
            strategy_used="osint_fused_strategy_v1",
            prompt_version="v1",
            confidence_score=0.80,
            context_features={"topic": topic, "region": region, "company": company_name, "learning_ctx": strategy_ctx},
        )

        feed = await self.fetch_signals(topic=topic, region=region, limit=10)
        graph = self.build_actor_graph(feed["signals"], topic)
        top_headlines = [f"- [{s['source']}] {s['title']} ({s.get('url', '')})" for s in feed["signals"][:8]]

        gateway = LLMGateway(db, tenant_id)
        if gateway.has_configured_provider():
            prompt = (
                f"You are OctaOS Global Intelligence (native Orodruin OSINT engine).\n"
                f"Topic: {topic}\nRegion: {region or 'Global'}\nCompany Focus: {company_name or 'General'}\n\n"
                f"Live Signals:\n" + "\n".join(top_headlines or ["No external headlines returned."]) + "\n\n"
                "Provide:\n"
                "1. Market Situation & Trend Summary (grounded in the signals above)\n"
                "2. Target Lead Segments & Buying Triggers (do NOT invent email addresses)\n"
                "3. Sales & Marketing Strategy + Image/Video Post Ideas"
            )
            try:
                analysis_text = await gateway.complete(prompt=prompt)
            except Exception as exc:
                analysis_text = f"LLM synthesis unavailable ({exc}). Review raw OSINT signals below."
        else:
            analysis_text = (
                f"Collected {feed['count']} live OSINT signals for '{topic}' ({region or 'Global'}). "
                "Configure a model provider (NVIDIA NIM, OpenRouter, OpenAI, or local) in Integrations to enable AI strategy synthesis."
            )

        # Pick first geolocated signal for UI focus_map action
        geo_sig = next((s for s in feed["signals"] if s.get("lat") is not None and s.get("lon") is not None), None)
        ui_actions = []
        if geo_sig:
            ui_actions.append({"action": "focus_map", "lat": geo_sig["lat"], "lon": geo_sig["lon"], "zoom": 4})

        loop.record_outcome_and_update(
            decision_id=decision_id,
            result_status="success",
            behavioral_signals={"signals_collected": feed["count"], "llm_synthesized": bool(gateway.has_configured_provider())},
            quality_score=86.0 if feed["count"] > 0 else 55.0,
        )

        return {
            "decision_id": decision_id,
            "topic": topic,
            "region": region,
            "signals_count": feed["count"],
            "signals": feed["signals"],
            "graph": graph,
            "ui_actions": ui_actions,
            "strategy_analysis": analysis_text,
            "retrieved_at": feed["retrieved_at"],
        }


    async def fetch_cameras(self, limit: int = 80) -> dict[str, Any]:
        """Fetch live public traffic cameras (TfL London + Singapore LTA) with zero API keys."""
        features: list[dict[str, Any]] = []
        headers = {"User-Agent": "OctaOS-Intelligence/1.0"}
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                r = await client.get("https://api.tfl.gov.uk/Place/Type/JamCam", headers=headers)
                if r.is_success:
                    for p in (r.json() if isinstance(r.json(), list) else [])[:limit]:
                        lat, lon = p.get("lat"), p.get("lon")
                        if lat is None or lon is None:
                            continue
                        ap = {x.get("key"): x.get("value") for x in (p.get("additionalProperties") or [])}
                        features.append({
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "properties": {
                                "id": p.get("id"),
                                "title": p.get("commonName") or "TfL Camera",
                                "source": "TfL London",
                                "city": "London",
                                "country": "GB",
                                "image": ap.get("imageUrl"),
                                "mp4": ap.get("videoUrl"),
                            },
                        })
            except Exception:
                pass

            if len(features) < limit:
                try:
                    r = await client.get("https://api.data.gov.sg/v1/transport/traffic-images", headers=headers)
                    if r.is_success:
                        items = (r.json().get("items") or [{}])[0].get("cameras") or []
                        for c in items[: max(0, limit - len(features))]:
                            loc = c.get("location") or {}
                            if loc.get("latitude") is None or loc.get("longitude") is None:
                                continue
                            features.append({
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [loc["longitude"], loc["latitude"]]},
                                "properties": {
                                    "id": f"sg-{c.get('camera_id')}",
                                    "title": f"Singapore Cam {c.get('camera_id')}",
                                    "source": "LTA Singapore",
                                    "city": "Singapore",
                                    "country": "SG",
                                    "image": c.get("image"),
                                    "mp4": None,
                                },
                            })
                except Exception:
                    pass

        return {"type": "FeatureCollection", "count": len(features), "features": features}

    async def fetch_flights(self, limit: int = 250) -> dict[str, Any]:
        """Fetch live OpenSky ADS-B aircraft positions."""
        features: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.get("https://opensky-network.org/api/states/all")
                if r.is_success:
                    for s in (r.json().get("states") or [])[:limit]:
                        lon, lat = s[5], s[6]
                        if lon is None or lat is None:
                            continue
                        features.append({
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "properties": {
                                "icao24": s[0],
                                "callsign": (s[1] or "").strip() or s[0],
                                "country": s[2],
                                "altitude_m": s[7],
                                "velocity_ms": s[9],
                                "heading": s[10],
                            },
                        })
            except Exception:
                pass
        return {"type": "FeatureCollection", "count": len(features), "features": features}

    async def fetch_disasters(self, limit: int = 50) -> dict[str, Any]:
        """Fetch live GDACS global disaster alerts."""
        features: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.get("https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP")
                if r.is_success:
                    raw = (r.json().get("features") or [])[:limit]
                    for feat in raw:
                        props = feat.get("properties") or {}
                        features.append({
                            "type": "Feature",
                            "geometry": feat.get("geometry"),
                            "properties": {
                                "id": props.get("eventid"),
                                "name": props.get("name") or props.get("eventname"),
                                "event_type": props.get("eventtype"),
                                "alert_level": props.get("alertlevel"),
                                "country": props.get("country"),
                                "url": props.get("url", {}).get("report") if isinstance(props.get("url"), dict) else props.get("url"),
                            },
                        })
            except Exception:
                pass
        return {"type": "FeatureCollection", "count": len(features), "features": features}

    async def fetch_weather_radar(self) -> dict[str, Any]:
        """Fetch RainViewer live precipitation radar tile URL."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.get("https://api.rainviewer.com/public/weather-maps.json")
                if r.is_success:
                    data = r.json()
                    host = data.get("host", "https://tilecache.rainviewer.com")
                    past = (data.get("radar") or {}).get("past") or []
                    if past:
                        path = past[-1]["path"]
                        return {"tile_url": f"{host}{path}/256/{{z}}/{{x}}/{{y}}/2/1_1.png", "time": past[-1].get("time")}
            except Exception:
                pass
        return {"tile_url": None, "time": None}

    async def deep_search(self, db: Session, tenant_id: str, query: str, count: int = 8) -> dict[str, Any]:
        """Run OctaOS EnterpriseWebResearchService + GDELT fallback for deep browser/web research."""
        try:
            from app.services.research.enterprise_web import EnterpriseWebResearchService
            svc = EnterpriseWebResearchService(db, tenant_id)
            if hasattr(svc, "search"):
                res = await svc.search(query=query, count=count)
                return {"engine": "enterprise_web_research", "query": query, "results": res}
        except Exception:
            pass
        feed = await self.fetch_signals(topic=query, limit=count)
        return {"engine": "gdelt_osint_fallback", "query": query, "results": feed["signals"]}


    async def fetch_weather(self, lat: float, lon: float) -> dict[str, Any]:
        """Open-Meteo current weather (free, no key)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": lat, "longitude": lon, "current_weather": "true"},
            )
            r.raise_for_status()
            return r.json()

    async def fetch_air_quality(self, lat: float, lon: float) -> dict[str, Any]:
        """Open-Meteo air quality (PM2.5, PM10, NO2, CO, O3 — free, no key)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={"latitude": lat, "longitude": lon, "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone"},
            )
            r.raise_for_status()
            return r.json()

    async def fetch_space_weather(self) -> dict[str, Any]:
        """NOAA SWPC planetary Kp index & solar flux (free, no key)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json")
            r.raise_for_status()
            rows = r.json()
            latest = rows[-1] if isinstance(rows, list) and len(rows) > 1 else []
            return {"latest": latest, "count": len(rows) if isinstance(rows, list) else 0}

    async def geocode(self, q: str, limit: int = 5) -> list[dict[str, Any]]:
        """Nominatim OpenStreetMap geocoding."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": limit},
                headers={"User-Agent": "OctaOS-Intelligence/1.0"},
            )
            r.raise_for_status()
            return [
                {"display_name": x.get("display_name"), "lat": float(x["lat"]), "lon": float(x["lon"])}
                for x in (r.json() if isinstance(r.json(), list) else [])
            ]

    async def route(self, from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> dict[str, Any]:
        """OSRM driving route."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"https://router.project-osrm.org/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}",
                params={"overview": "full", "geometries": "geojson"},
            )
            r.raise_for_status()
            data = r.json()
            routes = data.get("routes") or []
            if not routes:
                return {"error": "No route found"}
            return {"distance_m": routes[0].get("distance"), "duration_s": routes[0].get("duration"), "geometry": routes[0].get("geometry")}

    async def fetch_breaches(self, limit: int = 12) -> list[dict[str, Any]]:
        """Have I Been Pwned public breach catalog."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get("https://haveibeenpwned.com/api/v3/breaches", headers={"User-Agent": "OctaOS-Intelligence/1.0"})
            if not r.is_success:
                return []
            items = sorted(r.json(), key=lambda x: x.get("BreachDate", ""), reverse=True)[:limit]
            return [{"name": b.get("Name"), "domain": b.get("Domain"), "date": b.get("BreachDate"), "pwn_count": b.get("PwnCount")} for b in items]

    async def fetch_news_rss(self, limit: int = 15) -> list[dict[str, Any]]:
        """Public RSS world/tech news feeds."""
        feeds = [
            ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
            ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ]
        items: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for src, url in feeds:
                try:
                    r = await client.get(url)
                    if not r.is_success:
                        continue
                    for m in re.findall(r"<item>(.*?)</item>", r.text, flags=re.DOTALL)[: limit // 2]:
                        t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", m, flags=re.DOTALL)
                        l = re.search(r"<link>(.*?)</link>", m, flags=re.DOTALL)
                        items.append({
                            "source": src,
                            "title": " ".join(t.group(1).split()) if t else "News",
                            "url": l.group(1).strip() if l else "",
                        })
                except Exception:
                    pass
        return items[:limit]

    async def fetch_submarine_cables(self, limit: int = 80) -> dict[str, Any]:
        """TeleGeography global submarine cable systems."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.get("https://www.submarinecablemap.com/api/v3/cable/cable-geo.json")
                if r.is_success:
                    feats = (r.json().get("features") or [])[:limit]
                    return {"type": "FeatureCollection", "count": len(feats), "features": feats}
            except Exception:
                pass
        return {"type": "FeatureCollection", "count": 0, "features": []}

    async def fetch_satellites(self, limit: int = 40) -> dict[str, Any]:
        """CelesTrak active stations TLE catalog."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.get("https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json")
                if r.is_success:
                    rows = (r.json() if isinstance(r.json(), list) else [])[:limit]
                    return {"count": len(rows), "satellites": [{"name": x.get("OBJECT_NAME"), "norad_id": x.get("NORAD_CAT_ID"), "inclination": x.get("INCLINATION")} for x in rows]}
            except Exception:
                pass
        return {"count": 0, "satellites": []}

    async def area_intel(self, lat: float, lon: float) -> dict[str, Any]:
        """Unified area briefing: weather + air quality + nearby signals."""
        wx = await self.fetch_weather(lat, lon)
        aq = await self.fetch_air_quality(lat, lon)
        return {"lat": lat, "lon": lon, "weather": wx.get("current_weather"), "air_quality": aq.get("current")}

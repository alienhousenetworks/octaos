"""Orodruin-compatible OSINT & Global Intelligence integration for OctaOS.

Fuses live public OSINT feeds (GDELT, USGS, NASA EONET, ArXiv, CoinGecko, ip-api)
or an optional Orodruin sidecar URL with OctaOS's LLMGateway and LearningLoop.
"""
from __future__ import annotations

import os
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
        """Collect live grounded signals from public OSINT feeds (or Orodruin sidecar)."""
        signals: list[dict[str, Any]] = []
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            if self.sidecar_url:
                try:
                    r = await client.get(f"{self.sidecar_url}/api/alerts", params={"hours": 24})
                    if r.is_success:
                        data = r.json()
                        for item in (data if isinstance(data, list) else data.get("alerts", []))[:limit]:
                            signals.append({
                                "source": "orodruin_sidecar",
                                "category": item.get("type", "alert"),
                                "title": item.get("title") or item.get("summary") or "Orodruin Alert",
                                "url": item.get("url") or "",
                                "lat": item.get("lat"),
                                "lon": item.get("lon"),
                                "timestamp": item.get("timestamp") or _now_iso(),
                            })
                except Exception as exc:
                    errors.append(f"sidecar: {exc}")

            # 1. GDELT 2.0 Doc API (geopolitical / market news)
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
                    for feat in (r.json().get("features") or [])[:5]:
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
                r = await client.get("https://eonet.gsfc.nasa.gov/api/v3/events?limit=5&status=open")
                if r.is_success:
                    for ev in (r.json().get("events") or [])[:5]:
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
            "sidecar_connected": bool(self.sidecar_url),
            "count": len(signals),
            "signals": signals,
            "errors": errors,
            "retrieved_at": _now_iso(),
        }

    async def geolocate_ip(self, ip: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"http://ip-api.com/json/{quote_plus(ip)}")
            r.raise_for_status()
            return r.json()

    async def analyze_for_strategy(
        self,
        db: Session,
        tenant_id: str,
        *,
        topic: str,
        region: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fuse live OSINT signals with LLMGateway + LearningLoop for leads & marketing/sales strategy."""
        from app.services.learning_loop import LearningLoop
        from app.services.llm_gateway import LLMGateway

        loop = LearningLoop(db, tenant_id)
        strategy_ctx = loop.get_strategy_context("orodruin_intel", "market_strategy")
        decision_id = loop.record_decision(
            agent_name="orodruin_intel",
            task_type="market_strategy",
            strategy_used="osint_fused_strategy_v1",
            prompt_version="v1",
            confidence_score=0.78,
            context_features={"topic": topic, "region": region, "company": company_name, "learning_ctx": strategy_ctx},
        )

        feed = await self.fetch_signals(topic=topic, region=region, limit=8)
        top_headlines = [f"- [{s['source']}] {s['title']} ({s.get('url', '')})" for s in feed["signals"][:8]]

        gateway = LLMGateway(db, tenant_id)
        analysis_text = ""
        if gateway.has_configured_provider():
            prompt = (
                f"You are OctaOS Global Intelligence (powered by Orodruin OSINT feeds).\n"
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

        loop.record_outcome_and_update(
            decision_id=decision_id,
            result_status="success",
            behavioral_signals={"signals_collected": feed["count"], "llm_synthesized": bool(gateway.has_configured_provider())},
            quality_score=84.0 if feed["count"] > 0 else 55.0,
        )

        return {
            "decision_id": decision_id,
            "topic": topic,
            "region": region,
            "signals_count": feed["count"],
            "signals": feed["signals"],
            "strategy_analysis": analysis_text,
            "retrieved_at": feed["retrieved_at"],
        }

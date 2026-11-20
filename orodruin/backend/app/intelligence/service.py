from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.inference.service import InferenceError, InferenceService
from app.intelligence.models import (
    CompanyProfile,
    IntelligenceLead,
    MarketSignal,
    StrategyBrief,
)
from app.models import Event, Sanction


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IntelligenceEngine:
    """Combines Orodruin OSINT feeds with business research and local AI synthesis."""

    def __init__(self, db: Session, tenant_id: str, inference: Optional[InferenceService] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.inference = inference or InferenceService()

    def _osint_context_for_query(self, query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Pull grounded OSINT evidence from Orodruin's ingested GDELT events & sanctions."""
        events = (
            self.db.query(Event)
            .filter(Event.geo_fullname.ilike(f"%{query}%"))
            .order_by(Event.date_added.desc())
            .limit(5)
            .all()
        )
        sanctions = (
            self.db.query(Sanction)
            .filter(Sanction.name.ilike(f"%{query}%"))
            .limit(5)
            .all()
        )
        evidence: list[dict[str, Any]] = []
        osint_hits: list[dict[str, Any]] = []
        for ev in events:
            if ev.source_url:
                evidence.append(
                    {
                        "source": ev.source_url,
                        "published_at": ev.date_added.isoformat() if ev.date_added else None,
                        "retrieved_at": _now_iso(),
                        "classification": "RAW",
                    }
                )
            osint_hits.append(
                {
                    "type": "gdelt_event",
                    "location": ev.geo_fullname,
                    "country": ev.geo_country,
                    "lat": ev.lat,
                    "lon": ev.lon,
                    "goldstein": ev.goldstein,
                }
            )
        for s in sanctions:
            osint_hits.append({"type": "sanction_match", "name": s.name, "program": getattr(s, "program", None)})
        return osint_hits, evidence

    async def research_company(
        self,
        *,
        name: str,
        domain: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> CompanyProfile:
        osint_hits, evidence = self._osint_context_for_query(country or name)
        if domain:
            evidence.append(
                {
                    "source": f"https://{domain.lstrip('https://').lstrip('http://')}",
                    "published_at": None,
                    "retrieved_at": _now_iso(),
                    "classification": "EXTERNAL",
                }
            )

        schema_hint = (
            '{"summary": str, "products": [str], "competitors": [str], '
            '"opportunities": [str], "risks": [str], "confidence": float}'
        )
        prompt = (
            f"Analyze company '{name}' (domain={domain}, industry={industry}, country={country}). "
            f"OSINT context hits: {osint_hits}. Provide concise factual analysis."
        )
        try:
            data = await self.inference.generate_structured(prompt=prompt, schema_hint=schema_hint)
            classification = "DERIVED"
        except InferenceError:
            data = {
                "summary": f"Baseline intelligence profile for {name} ({industry or 'General'}).",
                "products": [],
                "competitors": [],
                "opportunities": ["Market expansion and outbound intelligence monitoring"],
                "risks": [f"OSINT hits detected: {len(osint_hits)}"],
                "confidence": 0.55,
            }
            classification = "MEASURED"

        profile = CompanyProfile(
            tenant_id=self.tenant_id,
            name=name,
            domain=domain,
            industry=industry,
            country=country,
            lat=lat,
            lon=lon,
            summary=str(data.get("summary") or ""),
            products_json=list(data.get("products") or []),
            competitors_json=list(data.get("competitors") or []),
            opportunities_json=list(data.get("opportunities") or []),
            risks_json=list(data.get("risks") or []),
            evidence_json=evidence,
            classification=classification,
            confidence=float(data.get("confidence") or 0.6),
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    async def discover_leads(
        self,
        *,
        topic: str,
        industry: Optional[str] = None,
        region: Optional[str] = None,
        company_profile_id: Optional[str] = None,
        count: int = 5,
    ) -> list[IntelligenceLead]:
        osint_hits, evidence = self._osint_context_for_query(region or topic)
        schema_hint = (
            '{"leads": [{"company_name": str, "contact_role": str, "industry": str, '
            '"location": str, "opportunity": str, "trigger_signal": str, '
            '"fit_score": float, "priority": "high|medium|low", "next_action": str}]}'
        )
        prompt = (
            f"Identify up to {count} B2B prospect organizations for topic='{topic}', "
            f"industry='{industry}', region='{region}'. OSINT signals: {osint_hits}. "
            "Do NOT invent personal emails or unverified contact names."
        )
        try:
            res = await self.inference.generate_structured(prompt=prompt, schema_hint=schema_hint)
            items = res.get("leads") or []
        except InferenceError:
            items = [
                {
                    "company_name": f"{topic.title()} Prospect ({region or 'Global'})",
                    "contact_role": "VP of Operations",
                    "industry": industry or topic,
                    "location": region or "Global",
                    "opportunity": f"Demand signal aligned with {topic}",
                    "trigger_signal": f"OSINT/market signal count={len(osint_hits)}",
                    "fit_score": 0.72,
                    "priority": "high",
                    "next_action": "Verify decision-maker via CRM/connector and prepare outreach brief.",
                }
            ]

        created: list[IntelligenceLead] = []
        for item in items[:count]:
            # Never trust LLM-generated emails; require explicit verification
            lead = IntelligenceLead(
                tenant_id=self.tenant_id,
                company_profile_id=company_profile_id,
                company_name=str(item.get("company_name") or "Unknown Organization"),
                contact_name=None,
                contact_role=item.get("contact_role"),
                contact_email=None,
                contact_verified=False,
                industry=item.get("industry") or industry,
                location=item.get("location") or region,
                opportunity=str(item.get("opportunity") or f"Opportunity in {topic}"),
                trigger_signal=item.get("trigger_signal"),
                evidence_json=evidence,
                classification="DERIVED",
                fit_score=float(item.get("fit_score") or 0.65),
                priority=str(item.get("priority") or "medium"),
                next_action=item.get("next_action"),
                status="new",
            )
            self.db.add(lead)
            created.append(lead)
        self.db.commit()
        for lead in created:
            self.db.refresh(lead)
        return created

    async def analyze_market_trend(
        self,
        *,
        topic: str,
        region: Optional[str] = None,
        signal_type: str = "trend",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> MarketSignal:
        osint_hits, evidence = self._osint_context_for_query(region or topic)
        schema_hint = '{"summary": str, "business_impact": str, "confidence": float}'
        prompt = f"Analyze market/competitor trend for topic='{topic}', region='{region}', osint={osint_hits}."
        try:
            data = await self.inference.generate_structured(prompt=prompt, schema_hint=schema_hint)
        except InferenceError:
            data = {
                "summary": f"Observed market/OSINT activity around {topic} in {region or 'Global'}.",
                "business_impact": "Potential demand shift requiring targeted campaign messaging.",
                "confidence": 0.65,
            }
        signal = MarketSignal(
            tenant_id=self.tenant_id,
            topic=topic,
            region=region,
            signal_type=signal_type,
            summary=str(data.get("summary") or ""),
            evidence_json=evidence,
            classification="DERIVED",
            confidence=float(data.get("confidence") or 0.65),
            business_impact=data.get("business_impact"),
            lat=lat,
            lon=lon,
        )
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    async def generate_strategy_brief(
        self,
        *,
        title: str,
        company_profile_id: Optional[str] = None,
        topic: Optional[str] = None,
        channels: Optional[list[str]] = None,
    ) -> StrategyBrief:
        company = None
        if company_profile_id:
            company = (
                self.db.query(CompanyProfile)
                .filter(CompanyProfile.id == company_profile_id, CompanyProfile.tenant_id == self.tenant_id)
                .first()
            )
        context_text = f"Company={company.name if company else 'General'}, Topic={topic or 'Growth'}"
        schema_hint = (
            '{"target_audience": str, "sales_strategy": str, '
            '"marketing_strategy": str, "campaign_brief": str}'
        )
        try:
            data = await self.inference.generate_structured(
                prompt=f"Create unified sales & marketing strategy brief for {context_text}.",
                schema_hint=schema_hint,
            )
        except InferenceError:
            data = {
                "target_audience": f"Decision-makers impacted by {topic or 'market shifts'}",
                "sales_strategy": f"Prioritize high-fit leads for {company.name if company else 'target accounts'} with evidence-backed outreach.",
                "marketing_strategy": f"Publish educational and product-led image/video posts addressing {topic or 'core pain points'}.",
                "campaign_brief": f"Multi-channel campaign ({', '.join(channels or ['linkedin', 'instagram'])}) driven by live intelligence.",
            }

        brief = StrategyBrief(
            tenant_id=self.tenant_id,
            company_profile_id=company_profile_id,
            title=title,
            target_audience=data.get("target_audience"),
            sales_strategy=str(data.get("sales_strategy") or ""),
            marketing_strategy=str(data.get("marketing_strategy") or ""),
            campaign_brief=str(data.get("campaign_brief") or ""),
            recommended_channels=channels or ["linkedin", "instagram", "email"],
            evidence_json=company.evidence_json if company else [],
            classification="DERIVED",
            status="draft",
        )
        self.db.add(brief)
        self.db.commit()
        self.db.refresh(brief)
        return brief

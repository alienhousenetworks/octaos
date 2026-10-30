"""Industry News & Innovation Radar.

Fetches and scores recent industry news, tech breakthroughs, and trending topics
that are relevant to the tenant's brand and industry.

Strategy (in priority order):
  1. Apify / Firecrawl web scrape (if API key configured).
  2. Curated static innovation signals per industry (always available, zero cost).

Results are scored for brand relevance and returned as NewsSignal dicts.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------- #
# Curated Industry Innovation Signals
# These are evergreen, time-tested signals — refreshed periodically by the team.
# Format: category -> list of {topic, signal, relevance_keywords}
# ---------------------------------------------------------------------------- #

_INDUSTRY_SIGNALS: Dict[str, List[Dict[str, Any]]] = {
    "technology": [
        {"topic": "Agentic AI & Autonomous Systems", "signal": "Agentic AI systems that operate autonomously across multi-step tasks are becoming the new competitive moat for enterprise software companies in 2026.", "keywords": ["ai", "automation", "agent", "workflow", "autonomous"]},
        {"topic": "AI Infrastructure Cost Collapse", "signal": "GPU inference costs have dropped 10x in 18 months — enabling even mid-market companies to deploy production AI at scale for the first time.", "keywords": ["ai", "infrastructure", "cost", "scale", "compute"]},
        {"topic": "Multimodal AI for Business", "signal": "Businesses are moving beyond text-only AI to multimodal workflows — images, video, and audio now processed end-to-end.", "keywords": ["multimodal", "video", "image", "media", "content"]},
        {"topic": "API Economy Expansion", "signal": "The API economy is expected to generate $14.2 trillion in value by 2027 — every business is now a software business.", "keywords": ["api", "saas", "integration", "platform", "software"]},
        {"topic": "Zero-Trust Security by Default", "signal": "Zero-trust architecture has moved from enterprise best practice to regulatory requirement in most sectors.", "keywords": ["security", "trust", "compliance", "data", "protection"]},
    ],
    "saas": [
        {"topic": "Product-Led Growth Dominance", "signal": "PLG companies are growing 2x faster than sales-led peers — the product has become the primary acquisition channel.", "keywords": ["product", "growth", "acquisition", "freemium", "user"]},
        {"topic": "AI-Native SaaS Pricing Disruption", "signal": "Usage-based pricing is replacing seat licenses — customers pay for outcomes, not access.", "keywords": ["pricing", "usage", "subscription", "revenue", "model"]},
        {"topic": "Customer Success AI", "signal": "AI-powered customer success tools are reducing churn by up to 30% by predicting at-risk accounts before human teams notice.", "keywords": ["customer", "success", "retention", "churn", "ai"]},
    ],
    "fintech": [
        {"topic": "Embedded Finance Acceleration", "signal": "Embedded finance is projected to exceed $7 trillion in transactions by 2028 — every platform is becoming a financial services provider.", "keywords": ["embedded", "finance", "payment", "banking", "platform"]},
        {"topic": "AI Credit & Risk Models", "signal": "Alternative data and AI credit models are approving 3x more borrowers than traditional models while maintaining lower default rates.", "keywords": ["credit", "risk", "ai", "lending", "data"]},
        {"topic": "Real-Time Payment Infrastructure", "signal": "Real-time payments are now table stakes — companies offering T+2 settlement are losing deals to instant alternatives.", "keywords": ["payment", "real-time", "settlement", "transfer", "bank"]},
    ],
    "health": [
        {"topic": "AI Diagnostics Accuracy", "signal": "AI-assisted diagnostics are now matching or exceeding specialist-level accuracy in radiology, dermatology, and pathology.", "keywords": ["ai", "diagnostic", "health", "medical", "accuracy"]},
        {"topic": "Preventive Health Economy", "signal": "Preventive health spending is growing 4x faster than sick-care spending — the business model is shifting from treatment to prevention.", "keywords": ["preventive", "wellness", "health", "lifestyle", "care"]},
        {"topic": "Interoperability Standards", "signal": "Healthcare interoperability mandates are opening massive data exchange opportunities for innovators.", "keywords": ["interoperability", "ehr", "data", "health", "records"]},
    ],
    "retail": [
        {"topic": "AI-Personalized Commerce", "signal": "Retailers using AI personalization report 25-35% higher average order value and 40% lower cart abandonment.", "keywords": ["personalization", "ai", "commerce", "recommendation", "retail"]},
        {"topic": "Social Commerce Growth", "signal": "Social commerce is growing 3x faster than traditional e-commerce, with 72% of Gen Z shoppers buying directly from social platforms.", "keywords": ["social", "commerce", "instagram", "tiktok", "shopping"]},
        {"topic": "Supply Chain AI", "signal": "AI-driven demand forecasting is reducing inventory overstock by 30% and stock-outs by 65% for leading retailers.", "keywords": ["supply chain", "inventory", "forecast", "logistics", "demand"]},
    ],
    "education": [
        {"topic": "Personalized Learning at Scale", "signal": "Adaptive learning platforms are improving knowledge retention by 50% compared to one-size-fits-all curricula.", "keywords": ["learning", "adaptive", "education", "personalized", "ai"]},
        {"topic": "Micro-Credential Boom", "signal": "Demand for micro-credentials and stackable certificates grew 400% in 2025 as employers value demonstrable skills over degrees.", "keywords": ["micro-credential", "certification", "skills", "upskill", "learning"]},
    ],
    "real estate": [
        {"topic": "PropTech Intelligence Layer", "signal": "AI-driven property valuation models are now within 2% accuracy of human appraisers — transforming underwriting speed.", "keywords": ["proptech", "valuation", "ai", "property", "data"]},
        {"topic": "ESG Real Estate Premium", "signal": "Green-certified buildings now command a 12-18% rental premium as corporate tenants mandate ESG compliance.", "keywords": ["esg", "green", "sustainability", "building", "real estate"]},
    ],
}

# Universal innovation signals applicable to any industry
_UNIVERSAL_SIGNALS: List[Dict[str, Any]] = [
    {"topic": "Generative AI Adoption Tipping Point", "signal": "84% of enterprise decision-makers are now piloting or deploying generative AI — the early-mover advantage window is closing fast.", "keywords": ["generative ai", "enterprise", "adoption", "competitive"]},
    {"topic": "Automation-First Workforce", "signal": "Companies deploying automation-first operations report 3x higher revenue per employee than industry peers.", "keywords": ["automation", "workforce", "efficiency", "operations", "scale"]},
    {"topic": "Data Sovereignty & Privacy", "signal": "Data sovereignty is the next frontier — companies that own and control their data infrastructure will define the next decade.", "keywords": ["data", "privacy", "sovereignty", "compliance", "gdpr"]},
    {"topic": "Customer Experience as Differentiation", "signal": "73% of customers cite experience as a key factor in purchasing decisions — CX is now a revenue function, not a cost center.", "keywords": ["customer experience", "cx", "satisfaction", "retention", "nps"]},
]


_VIRAL_REEL_FORMATS: List[Dict[str, Any]] = [
    {
        "format": "counter_intuitive_truth",
        "hook_template": "Why the top 1% of {industry} teams are quietly stopping {common_habit}...",
        "structure": "0-1.5s: Bold contrarian claim | 1.5-6s: The fatal flaw in common practice | 6-12s: The modern playbook | 12-15s: Save for later",
        "retention_type": "high_watch_time",
    },
    {
        "format": "workflow_teardown",
        "hook_template": "We tested 50+ {industry} tools so you don't have to. Here are the only 3 that matter...",
        "structure": "0-2s: Tool interface teaser | 2-8s: Rapid-fire pros & cons | 8-13s: Winning stack | 13-15s: Comment for full breakdown",
        "retention_type": "high_save_rate",
    },
    {
        "format": "behind_the_scenes_audit",
        "hook_template": "The single most expensive bottleneck {industry} companies ignore until it's too late...",
        "structure": "0-2s: Shocking cost stat | 2-7s: Where the leak actually happens | 7-12s: The automated fix | 12-15s: Save this for your team",
        "retention_type": "high_share_rate",
    },
]


class NewsRadar:
    """
    Fetches and scores industry news and innovation signals for the tenant.

    Signals are matched against the tenant's industry and business context
    to return the most relevant hooks for content generation.
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def get_viral_reel_hooks(self, industry: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return structured high-retention video frameworks tailored for modern short-form algorithms."""
        ind_clean = (industry or "technology").capitalize()
        habits = {
            "technology": "manual task switching",
            "saas": "per-seat billing expansion",
            "fintech": "legacy T+2 settlement",
            "health": "reactive episodic care",
            "retail": "blanket discounts",
            "education": "rigid static courses",
            "real estate": "cold portal outreach",
        }
        habit = habits.get((industry or "").lower(), "manual repetitive work")
        return [
            {
                "format": fmt["format"],
                "hook": fmt["hook_template"].format(industry=ind_clean, common_habit=habit),
                "structure": fmt["structure"],
                "retention_type": fmt["retention_type"],
            }
            for fmt in _VIRAL_REEL_FORMATS
        ]

    def get_signals(
        self,
        industry: Optional[str] = None,
        brand_keywords: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Return the most relevant innovation signals for this tenant.
        
        Args:
            industry: Tenant's industry (used to select domain signals).
            brand_keywords: Keywords from brand knowledge (product names, USP terms).
            limit: Max signals to return.
        
        Returns:
            List of NewsSignal dicts with topic, signal, and relevance_score.
        """
        # Prioritize fresh live news when available
        live_news = self.get_live_news(industry=industry, limit=max(2, limit // 2))
        candidates = list(live_news)

        candidates.extend(self._get_industry_signals(industry))
        candidates.extend(_UNIVERSAL_SIGNALS)

        # Score each signal for brand relevance
        scored = []
        for sig in candidates:
            score = self._score_relevance(sig, industry, brand_keywords)
            scored.append({**sig, "relevance_score": score})

        # Sort by relevance descending, deduplicate by topic
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        seen_topics: set = set()
        results = []
        for item in scored:
            if item["topic"] not in seen_topics:
                seen_topics.add(item["topic"])
                results.append(item)
                if len(results) >= limit:
                    break

        logger.info(f"[NewsRadar] Returning {len(results)} signals for industry='{industry}'")
        return results

    def get_top_signals(
        self,
        limit: int = 5,
        brand_context: Optional[str] = None,
        brand_keywords: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Convenience alias for get_signals with brand_context as industry."""
        return self.get_signals(industry=brand_context, brand_keywords=brand_keywords, limit=limit)

    def get_live_news(
        self,
        industry: Optional[str] = None,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Attempt to fetch live news via Apify/Firecrawl.
        Falls back to curated signals on any failure.
        """
        try:
            return self._fetch_live_via_apify(industry, limit)
        except Exception as exc:
            logger.debug(f"[NewsRadar] Live fetch failed ({exc}), using curated signals.")
            return []

    # ------------------------------------------------------------------ #
    # Private
    # ------------------------------------------------------------------ #

    def _get_industry_signals(self, industry: Optional[str]) -> List[Dict[str, Any]]:
        if not industry:
            return list(_UNIVERSAL_SIGNALS)
        industry_lower = industry.lower()
        for key, signals in _INDUSTRY_SIGNALS.items():
            if key in industry_lower:
                return list(signals)
        return list(_UNIVERSAL_SIGNALS)

    def _score_relevance(
        self,
        signal: Dict[str, Any],
        industry: Optional[str],
        brand_keywords: Optional[List[str]],
    ) -> float:
        score = 0.5  # Base score
        signal_text = (signal.get("topic", "") + " " + signal.get("signal", "")).lower()
        keywords = signal.get("keywords", [])

        # Industry match bonus
        if industry:
            industry_lower = industry.lower()
            for key in _INDUSTRY_SIGNALS:
                if key in industry_lower:
                    score += 0.3
                    break

        # Brand keyword overlap bonus
        if brand_keywords:
            for kw in brand_keywords:
                kw_lower = kw.lower()
                if kw_lower in signal_text:
                    score += 0.1
                for sig_kw in keywords:
                    if kw_lower in sig_kw:
                        score += 0.05

        return min(1.0, score)

    def _fetch_live_via_apify(self, industry: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Fetch live news via Apify transport client if token is configured."""
        from app.integrations.apify.client import ApifyTransportClient
        from asgiref.sync import async_to_sync

        token = ApifyTransportClient.resolve_token(self.db, self.tenant_id)
        if not token:
            return []

        search_query = f"{industry or 'technology'} innovation news 2026 latest"
        client = ApifyTransportClient(token=token)
        try:
            res = async_to_sync(client.run_actor)(
                actor_key="market_news",
                raw_input={"queries": search_query, "resultsPerPage": limit},
                max_charge_usd=1.00,
                limit=limit,
                db=self.db,
                tenant_id=self.tenant_id,
            )
            if res.status != "succeeded":
                logger.debug(f"[NewsRadar] Apify fetch returned status {res.status}: {res.error_message}")
                return []

            signals = []
            for item in res.items[:limit]:
                organic = item.get("organicResults", [])
                for result in organic[:1]:
                    signals.append({
                        "topic": (result.get("title") or "Industry News")[:80],
                        "signal": (result.get("description") or "")[:300],
                        "keywords": [],
                        "relevance_score": 0.75,
                        "source": "live_search",
                        "url": result.get("url", ""),
                    })
            return signals
        except Exception as exc:
            logger.debug(f"[NewsRadar] Apify fetch error: {exc}")
            return []

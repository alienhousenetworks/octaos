"""Marketing Vertical Packs Registry and Preview Switch Engine."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.services.marketing.verticals.packs import PACKS, PACK_ORDER

DEFAULT_TERMINOLOGY = {
    "campaign": "Marketing Campaign",
    "post": "Social Post",
    "asset": "Creative Asset",
    "offer": "Promotion / Offer",
    "cta": "Call to Action",
    "audience": "Target Audience",
}


PACK_ALIASES: Dict[str, str] = {
    "service_company": "business_services",
    "services": "business_services",
    "professional_services": "business_services",
    "agency": "business_services",
}


def list_marketing_packs() -> List[Dict[str, Any]]:
    """Return all registered 18 marketing vertical packs."""
    return [dict(PACKS[pack_id]) for pack_id in PACK_ORDER]


def get_marketing_pack(pack_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Get a marketing pack by ID."""
    resolved = resolve_marketing_pack_id(pack_id)
    if not resolved or resolved not in PACKS:
        return None
    return dict(PACKS[resolved])


def resolve_marketing_pack_id(pack_id: Optional[str]) -> Optional[str]:
    """Validate and resolve a marketing pack ID."""
    if not pack_id:
        return None
    normalized = pack_id.lower().strip().replace(" ", "_").replace("-", "_")
    if normalized in PACKS:
        return normalized
    if normalized in PACK_ALIASES:
        return PACK_ALIASES[normalized]
    return None


def default_terminology() -> Dict[str, str]:
    return dict(DEFAULT_TERMINOLOGY)


def terminology_for(pack_id: Optional[str]) -> Dict[str, str]:
    pack = get_marketing_pack(pack_id)
    if not pack:
        return default_terminology()
    return dict(pack.get("terminology", DEFAULT_TERMINOLOGY))


def get_content_pillars(pack_id: Optional[str]) -> List[Dict[str, Any]]:
    pack = get_marketing_pack(pack_id)
    if not pack:
        return []
    return list(pack.get("content_pillars", []))


def get_compliance_rules(pack_id: Optional[str]) -> Dict[str, Any]:
    pack = get_marketing_pack(pack_id)
    if not pack:
        return {"prohibited_guarantees": [], "taboo_words": [], "required_disclosures": []}
    return dict(pack.get("compliance_guardrails", {}))


def get_visual_tokens(pack_id: Optional[str]) -> Dict[str, Any]:
    pack = get_marketing_pack(pack_id)
    if not pack:
        return {}
    return dict(pack.get("visual_creative_tokens", {}))


def get_calendar_events(pack_id: Optional[str]) -> List[Dict[str, Any]]:
    pack = get_marketing_pack(pack_id)
    if not pack:
        return []
    return list(pack.get("industry_calendar_events", []))


def preview_marketing_switch(
    current_id: Optional[str],
    next_id: Optional[str],
    campaigns_count: int = 0,
    posts_count: int = 0,
) -> Dict[str, Any]:
    """Describe a marketing pack change without deleting or mutating records."""
    if not next_id or str(next_id).lower().strip() in ("general", "none", "clear", "default"):
        current = get_marketing_pack(current_id) if current_id else None
        return {
            "from_pack_id": current["id"] if current else None,
            "to_pack_id": None,
            "to_name": "General (Standard)",
            "to_version": "1.0.0",
            "campaigns_preserved": campaigns_count,
            "posts_preserved": posts_count,
            "records_deleted": 0,
            "terminology": default_terminology(),
            "readiness": "ready",
            "domain_status": "available",
            "domain_note": "Standard marketing campaign mode for any business.",
            "funnel_stages": [],
            "content_pillars": [],
            "compliance_guardrails": {"prohibited_guarantees": [], "taboo_words": [], "required_disclosures": []},
            "visual_creative_tokens": {},
            "industry_calendar_events": [],
            "capabilities": {},
            "incompatible": [],
            "effect": "Marketing workspace returned to General standard campaign mode. All existing posts and campaigns remain intact.",
        }

    nxt = get_marketing_pack(next_id)
    if nxt is None:
        raise KeyError(f"Unknown marketing pack ID: {next_id}")
    current = get_marketing_pack(current_id) if current_id else None

    return {
        "from_pack_id": current["id"] if current else None,
        "to_pack_id": nxt["id"],
        "to_name": nxt["name"],
        "to_version": nxt["version"],
        "campaigns_preserved": campaigns_count,
        "posts_preserved": posts_count,
        "records_deleted": 0,
        "terminology": nxt["terminology"],
        "readiness": nxt["readiness"],
        "domain_status": nxt["domain_status"],
        "domain_note": nxt["domain_note"],
        "funnel_stages": nxt.get("funnel_stages", []),
        "content_pillars": nxt.get("content_pillars", []),
        "compliance_guardrails": nxt.get("compliance_guardrails", {}),
        "visual_creative_tokens": nxt.get("visual_creative_tokens", {}),
        "industry_calendar_events": nxt.get("industry_calendar_events", []),
        "capabilities": nxt.get("capabilities", {}),
        "incompatible": [],
        "effect": "Marketing prompts, content pillars, compliance rules, and visual tokens update. Existing campaigns and drafts stay.",
    }

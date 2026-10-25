"""Industry-neutral Sales defaults. Legacy pack data is retained only for migration compatibility."""
from __future__ import annotations

from typing import Any

from app.services.sales_os.verticals.packs import PACKS

SHARED_TERMINOLOGY = {
    "lead": "Lead",
    "leads": "Leads",
    "account": "Account",
    "accounts": "Accounts",
    "contact": "Contact",
    "contacts": "Contacts",
    "opportunity": "Opportunity",
    "opportunities": "Opportunities",
    "pipeline": "Pipeline",
}


PACK_ALIASES: dict[str, str] = {
    "service_company": "business_services",
    "services": "business_services",
    "professional_services": "business_services",
    "agency": "business_services",
}


def list_packs() -> list[dict[str, Any]]:
    """No industry packs are exposed to the general Sales runtime."""
    return []


def get_pack(pack_id: str) -> dict[str, Any] | None:
    resolved = resolve_pack_id(pack_id)
    pack = PACKS.get(resolved) if resolved else None
    return dict(pack) if pack else None


def resolve_pack_id(pack_id: str | None) -> str | None:
    if not pack_id:
        return None
    normalized = pack_id.lower().strip().replace(" ", "_").replace("-", "_")
    if normalized in PACKS:
        return normalized
    if normalized in PACK_ALIASES:
        return PACK_ALIASES[normalized]
    return None


def shared_terminology() -> dict[str, str]:
    return dict(SHARED_TERMINOLOGY)


def terminology_for(pack_id: str | None = None) -> dict[str, str]:
    """Use universal CRM terminology regardless of any legacy stored pack ID."""
    return shared_terminology()


def preview_switch(current_id: str | None, next_id: str, record_count: int) -> dict[str, Any]:
    """Describe a pack change. The change never deletes CRM records."""
    nxt = get_pack(next_id)
    if nxt is None:
        raise KeyError(next_id)
    current = get_pack(current_id) if current_id else None
    return {
        "from_pack_id": current["id"] if current else None,
        "to_pack_id": nxt["id"],
        "to_name": nxt["name"],
        "to_version": nxt["version"],
        "records_preserved": record_count,
        "records_deleted": 0,
        "terminology": nxt["terminology"],
        "readiness": nxt["readiness"],
        "domain_status": nxt["domain_status"],
        "domain_note": nxt["domain_note"],
        "pipeline_stages": nxt.get("pipeline_stages", []),
        "fields": nxt.get("fields", []),
        "capabilities": nxt.get("capabilities", {}),
        "incompatible": [],
        "effect": "Labels, qualification prompts, and AI guardrails change. Stored leads, accounts, and deals stay.",
    }

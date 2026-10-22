"""Look up industry packs and preview a switch that keeps existing records."""
from __future__ import annotations

from typing import Any

from app.services.sales_os.verticals.packs import PACK_ORDER, PACKS

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


def list_packs() -> list[dict[str, Any]]:
    return [dict(PACKS[pack_id]) for pack_id in PACK_ORDER]


def get_pack(pack_id: str) -> dict[str, Any] | None:
    pack = PACKS.get(pack_id)
    return dict(pack) if pack else None


def resolve_pack_id(pack_id: str | None) -> str | None:
    if pack_id and pack_id in PACKS:
        return pack_id
    return None


def shared_terminology() -> dict[str, str]:
    return dict(SHARED_TERMINOLOGY)


def terminology_for(pack_id: str | None) -> dict[str, str]:
    pack = get_pack(pack_id) if pack_id else None
    if not pack:
        return shared_terminology()
    return dict(pack["terminology"])


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

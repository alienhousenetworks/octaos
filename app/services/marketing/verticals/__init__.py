"""Marketing Industry Vertical Packs and Compliance Engine."""
from app.services.marketing.verticals.registry import (
    get_marketing_pack,
    list_marketing_packs,
    preview_marketing_switch,
    resolve_marketing_pack_id,
    terminology_for,
)
from app.services.marketing.verticals.compliance import IndustryComplianceEngine

__all__ = [
    "get_marketing_pack",
    "list_marketing_packs",
    "preview_marketing_switch",
    "resolve_marketing_pack_id",
    "terminology_for",
    "IndustryComplianceEngine",
]

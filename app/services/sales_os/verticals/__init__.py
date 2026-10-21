"""Versioned industry packs. Packs configure the shared CRM. They do not fork it."""

from app.services.sales_os.verticals.registry import (
    get_pack,
    list_packs,
    preview_switch,
    resolve_pack_id,
    shared_terminology,
)

__all__ = [
    "get_pack",
    "list_packs",
    "preview_switch",
    "resolve_pack_id",
    "shared_terminology",
]

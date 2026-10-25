"""Normalized inbound lead ingestion for listing portals and ad platforms."""
import hashlib
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.models.verticals import Lead
from app.models.sales_intelligence import SignalEvidence

router = APIRouter()


def _normalize_portal_payload(source_key: str, body: dict[str, Any]) -> dict[str, Any]:
    """Normalize vendor-specific webhook structures into canonical lead attributes."""
    if source_key == "zillow":
        contact = body.get("contact", body)
        return {
            "name": contact.get("name") or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip() or "Zillow Inquirer",
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "project_name": body.get("property", {}).get("address") or body.get("property_address") or "Zillow Property Inquiry",
            "unit_preference": body.get("bedrooms") or body.get("property", {}).get("beds"),
            "budget": body.get("price") or body.get("budget"),
            "property_type": body.get("property_type", "Residential"),
            "timeline": body.get("timeframe", "30 Days"),
        }
    elif source_key == "meta_ads":
        field_data = {f.get("name"): f.get("values", [None])[0] for f in body.get("field_data", [])} if "field_data" in body else body
        return {
            "name": field_data.get("full_name") or f"{field_data.get('first_name', '')} {field_data.get('last_name', '')}".strip() or "Meta Lead Ad Inquirer",
            "email": field_data.get("email"),
            "phone": field_data.get("phone_number") or field_data.get("phone"),
            "project_name": field_data.get("project") or body.get("campaign_name") or "Meta Ad Campaign Project",
            "unit_preference": field_data.get("configuration") or field_data.get("bhk"),
            "budget": field_data.get("budget_range") or field_data.get("budget"),
            "property_type": "Residential",
            "timeline": field_data.get("timeline", "Immediate"),
        }
    else:  # Generic webhook format
        return {
            "name": body.get("name") or body.get("buyer_name") or body.get("full_name") or "Inbound Buyer",
            "email": body.get("email"),
            "phone": body.get("phone") or body.get("mobile"),
            "project_name": body.get("project_name") or body.get("project") or body.get("property") or "General Project Inquiry",
            "unit_preference": body.get("unit_preference") or body.get("bhk") or body.get("unit_type"),
            "budget": body.get("budget") or body.get("price_range"),
            "property_type": body.get("property_type", "Residential"),
            "timeline": body.get("timeline") or body.get("purchase_timeline", "30 Days"),
        }


@router.post("/inbound/leads/{source_key}")
async def ingest_inbound_lead(
    source_key: str,
    request: Request,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
) -> dict[str, Any]:
    """Ingest, deduplicate, and record provenance for inbound real estate inquiries."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    raw_payload_str = str(sorted(body.items())) if isinstance(body, dict) else str(body)
    payload_hash = hashlib.sha256(raw_payload_str.encode("utf-8")).hexdigest()

    # Deduplication check
    existing_evidence = (
        db.query(SignalEvidence)
        .filter(
            SignalEvidence.tenant_id == tenant_id,
            SignalEvidence.payload_hash == payload_hash,
            SignalEvidence.source_key == source_key,
        )
        .first()
    )
    if existing_evidence:
        return {
            "status": "deduplicated",
            "message": "Duplicate inquiry payload detected; skipped to prevent duplicate records.",
            "evidence_id": existing_evidence.id,
        }

    # Normalize fields
    normalized = _normalize_portal_payload(source_key, body)

    # Persist immutable provenance
    evidence = SignalEvidence(
        tenant_id=tenant_id,
        source_key=source_key,
        payload_hash=payload_hash,
        claim=f"Inbound real estate inquiry from {source_key}: {normalized.get('name')} for {normalized.get('project_name')}",
        excerpt=str(body)[:500],
    )
    db.add(evidence)

    # Persist in shared CRM
    from app.models.rooms import SectionRoom
    sales_room = db.query(SectionRoom).filter(
        SectionRoom.tenant_id == tenant_id,
        SectionRoom.section == "sales",
        SectionRoom.slug == "default"
    ).first()

    lead = Lead(
        tenant_id=tenant_id,
        room_id=sales_room.id if sales_room else None,
        name=normalized.get("name"),
        email=normalized.get("email"),
        phone=normalized.get("phone"),
        company=normalized.get("project_name"),
        source=f"portal:{source_key}",
        status="inquiry",
        need_of_what=normalized.get("unit_preference"),
        how_much=str(normalized.get("budget")) if normalized.get("budget") else None,
        why=f"Inquired via {source_key} for {normalized.get('project_name')}. Unit: {normalized.get('unit_preference') or 'Not specified'}.",
        data={
            "property_type": normalized.get("property_type"),
            "unit_preference": normalized.get("unit_preference"),
            "budget": normalized.get("budget"),
            "purchase_timeline": normalized.get("timeline"),
            "source_evidence_id": evidence.id,
            "raw_inquiry": body,
        },
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {
        "status": "created",
        "lead_id": lead.id,
        "evidence_id": evidence.id,
        "normalized_name": lead.name,
        "project": lead.company,
    }

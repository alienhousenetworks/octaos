"""Real Estate funnel and inventory analytics service."""
from typing import Any
from sqlalchemy.orm import Session

from app.models.verticals import Lead
from app.models.real_estate import RealEstateSiteVisit, RealEstateUnitHold, RealEstateUnit


def get_real_estate_funnel_analytics(db: Session, tenant_id: str) -> dict[str, Any]:
    """Calculate conversion rates across real estate pipeline stages and inventory occupancy."""
    total_inquiries = db.query(Lead).filter(Lead.tenant_id == tenant_id).count()
    qualified_count = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.status == "qualified").count()
    visits_count = db.query(RealEstateSiteVisit).filter(RealEstateSiteVisit.tenant_id == tenant_id).count()
    completed_visits = db.query(RealEstateSiteVisit).filter(RealEstateSiteVisit.tenant_id == tenant_id, RealEstateSiteVisit.status == "completed").count()
    holds_count = db.query(RealEstateUnitHold).filter(RealEstateUnitHold.tenant_id == tenant_id).count()
    bookings_count = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.status.in_(["booking", "closed_won"])).count()

    total_units = db.query(RealEstateUnit).filter(RealEstateUnit.tenant_id == tenant_id).count()
    available_units = db.query(RealEstateUnit).filter(RealEstateUnit.tenant_id == tenant_id, RealEstateUnit.status == "available").count()
    held_units = db.query(RealEstateUnit).filter(RealEstateUnit.tenant_id == tenant_id, RealEstateUnit.status.in_(["hold_requested", "confirmed_hold"])).count()
    booked_units = db.query(RealEstateUnit).filter(RealEstateUnit.tenant_id == tenant_id, RealEstateUnit.status == "booked").count()

    return {
        "funnel": {
            "inquiries": total_inquiries,
            "qualified": qualified_count,
            "site_visits_scheduled": visits_count,
            "site_visits_completed": completed_visits,
            "holds_requested": holds_count,
            "bookings_confirmed": bookings_count,
        },
        "conversion_rates": {
            "inquiry_to_visit_pct": round((visits_count / total_inquiries * 100), 1) if total_inquiries > 0 else 0.0,
            "visit_to_hold_pct": round((holds_count / visits_count * 100), 1) if visits_count > 0 else 0.0,
            "hold_to_booking_pct": round((bookings_count / holds_count * 100), 1) if holds_count > 0 else 0.0,
            "overall_conversion_pct": round((bookings_count / total_inquiries * 100), 1) if total_inquiries > 0 else 0.0,
        },
        "inventory_snapshot": {
            "total_units": total_units,
            "available_units": available_units,
            "held_units": held_units,
            "booked_units": booked_units,
            "occupancy_rate_pct": round((booked_units / total_units * 100), 1) if total_units > 0 else 0.0,
        },
    }

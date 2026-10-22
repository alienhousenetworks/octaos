"""Site visit & property tour management service."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.real_estate import RealEstateSiteVisit, RealEstateProject, RealEstateUnit


class VisitService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def list_visits_for_lead(self, lead_id: str) -> list[dict]:
        """List all site visits scheduled for an inquiry."""
        visits = (
            self.db.query(RealEstateSiteVisit)
            .filter(
                RealEstateSiteVisit.tenant_id == self.tenant_id,
                RealEstateSiteVisit.lead_id == lead_id,
            )
            .order_by(RealEstateSiteVisit.scheduled_at.desc())
            .all()
        )
        return [
            {
                "id": v.id,
                "lead_id": v.lead_id,
                "project_id": v.project_id,
                "unit_id": v.unit_id,
                "scheduled_at": v.scheduled_at.isoformat(),
                "status": v.status,
                "assigned_agent": v.assigned_agent,
                "escort_contact": v.escort_contact,
                "pickup_required": v.pickup_required,
                "tour_feedback": v.tour_feedback,
                "buyer_interest_level": v.buyer_interest_level,
            }
            for v in visits
        ]

    def schedule_visit(
        self,
        lead_id: str,
        project_id: str,
        scheduled_at: datetime,
        unit_id: str | None = None,
        assigned_agent: str | None = None,
        escort_contact: str | None = None,
        pickup_required: bool = False,
    ) -> dict:
        """Schedule a new site visit."""
        visit = RealEstateSiteVisit(
            tenant_id=self.tenant_id,
            lead_id=lead_id,
            project_id=project_id,
            unit_id=unit_id,
            scheduled_at=scheduled_at,
            assigned_agent=assigned_agent,
            escort_contact=escort_contact,
            pickup_required=pickup_required,
            status="scheduled",
        )
        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)
        return {
            "id": visit.id,
            "lead_id": visit.lead_id,
            "project_id": visit.project_id,
            "scheduled_at": visit.scheduled_at.isoformat(),
            "status": visit.status,
        }

    def record_gps_check_in(
        self,
        visit_id: str,
        latitude: float,
        longitude: float,
        accuracy: float,
        manual_exception_reason: str | None = None,
    ) -> dict:
        """
        Record salesperson GPS check-in at a property.
        Validates whether device coordinates fall within the property geofence (250m).
        Permits manual exception with audit trail if GPS is inaccurate or in deadzone.
        """
        import math

        visit = (
            self.db.query(RealEstateSiteVisit)
            .filter(
                RealEstateSiteVisit.id == visit_id,
                RealEstateSiteVisit.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")

        project = self.db.query(RealEstateProject).filter(RealEstateProject.id == visit.project_id).first()
        
        # Calculate distance to project if project has coordinates
        distance_meters = 0.0
        is_verified = False
        GEOFENCE_RADIUS_METERS = 250.0

        if project and project.latitude and project.longitude:
            r = 6371000.0
            phi1, phi2 = math.radians(latitude), math.radians(project.latitude)
            dphi = math.radians(project.latitude - latitude)
            dlambda = math.radians(project.longitude - longitude)
            a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2)
            c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
            distance_meters = round(r * c, 1)

            if distance_meters <= GEOFENCE_RADIUS_METERS:
                is_verified = True
            elif not manual_exception_reason:
                raise HTTPException(
                    status_code=400,
                    detail=f"Check-in rejected: {distance_meters}m from property location (geofence radius is {GEOFENCE_RADIUS_METERS}m). A manual exception reason is required.",
                )
        else:
            # If project unlocated, mark verified if accuracy is reasonable
            is_verified = True if accuracy <= 100 else False

        now = datetime.now(timezone.utc)
        visit.check_in_latitude = latitude
        visit.check_in_longitude = longitude
        visit.check_in_accuracy = accuracy
        visit.check_in_verified = is_verified
        visit.check_in_exception_reason = manual_exception_reason
        visit.actual_arrival_at = now
        visit.status = "arrived"
        self.db.commit()

        return {
            "id": visit.id,
            "status": visit.status,
            "actual_arrival_at": now.isoformat(),
            "check_in_verified": is_verified,
            "distance_meters": distance_meters,
            "exception_logged": bool(manual_exception_reason),
        }

    def record_visit_outcome(
        self,
        visit_id: str,
        status: str,  # completed, cancelled, no_show
        tour_feedback: str | None = None,
        buyer_interest_level: str | None = None,
        buyer_objections: list[str] | None = None,
        agreed_next_step: str | None = None,
    ) -> dict:
        """Update outcome after showing."""
        visit = self.db.query(RealEstateSiteVisit).filter(
            RealEstateSiteVisit.id == visit_id,
            RealEstateSiteVisit.tenant_id == self.tenant_id,
        ).first()
        if not visit:
            raise HTTPException(status_code=404, detail="Visit not found")

        visit.status = status
        visit.actual_departure_at = datetime.now(timezone.utc)
        if tour_feedback:
            visit.tour_feedback = tour_feedback
        if buyer_interest_level:
            visit.buyer_interest_level = buyer_interest_level
        if buyer_objections is not None:
            visit.buyer_objections = buyer_objections
        if agreed_next_step:
            visit.agreed_next_step = agreed_next_step

        self.db.commit()
        return {
            "id": visit.id,
            "status": visit.status,
            "buyer_interest_level": visit.buyer_interest_level,
            "agreed_next_step": visit.agreed_next_step,
            "actual_departure_at": visit.actual_departure_at.isoformat() if visit.actual_departure_at else None,
        }


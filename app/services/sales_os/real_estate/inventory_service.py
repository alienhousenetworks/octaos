"""Atomic unit inventory reservation service with optimistic concurrency control."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.real_estate import (
    RealEstateUnit,
    RealEstateUnitHold,
    RealEstateProject,
    RealEstateBooking,
    RealEstateProjectAssignment,
)
from app.models.base import User


class InventoryService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def list_projects(self) -> list[dict]:
        """List tenant-scoped property development projects with team counts and coordinates."""
        projects = self.db.query(RealEstateProject).filter(
            RealEstateProject.tenant_id == self.tenant_id
        ).order_by(RealEstateProject.created_at.desc()).all()

        results = []
        for p in projects:
            team_count = (
                self.db.query(RealEstateProjectAssignment)
                .filter(
                    RealEstateProjectAssignment.tenant_id == self.tenant_id,
                    RealEstateProjectAssignment.project_id == p.id,
                    RealEstateProjectAssignment.is_active == True,
                )
                .count()
            )
            results.append({
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "location": p.location,
                "city": p.city,
                "address": p.address,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "status": p.status,
                "total_units": p.total_units or 0,
                "available_units": p.available_units or 0,
                "hold_duration_hours": p.hold_duration_hours or 48,
                "rera_number": p.rera_number,
                "amenities": p.amenities or [],
                "assigned_team_count": team_count,
            })
        return results

    def create_project(
        self,
        name: str,
        code: str | None = None,
        location: str | None = None,
        city: str | None = None,
        address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        rera_number: str | None = None,
        amenities: list | None = None,
        hold_duration_hours: int = 48,
        status: str = "active",
        total_units: int = 0,
    ) -> dict:
        """Create a new property project with complete geographic and legal specifications."""
        project = RealEstateProject(
            tenant_id=self.tenant_id,
            name=name,
            code=code or name.lower().replace(" ", "_").replace("-", "_"),
            location=location,
            city=city,
            address=address,
            latitude=latitude,
            longitude=longitude,
            rera_number=rera_number,
            amenities=amenities or [],
            hold_duration_hours=hold_duration_hours,
            status=status,
            total_units=total_units,
            available_units=total_units,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return {
            "id": project.id,
            "name": project.name,
            "code": project.code,
            "location": project.location,
            "city": project.city,
            "address": project.address,
            "latitude": project.latitude,
            "longitude": project.longitude,
            "status": project.status,
            "rera_number": project.rera_number,
            "total_units": project.total_units,
            "available_units": project.available_units,
        }

    def get_project(self, project_id: str) -> dict:
        """Retrieve complete project dossier including units inventory and assigned team."""
        project = (
            self.db.query(RealEstateProject)
            .filter(
                RealEstateProject.id == project_id,
                RealEstateProject.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Assigned sales team
        assignments = (
            self.db.query(RealEstateProjectAssignment, User)
            .join(User, User.id == RealEstateProjectAssignment.user_id)
            .filter(
                RealEstateProjectAssignment.tenant_id == self.tenant_id,
                RealEstateProjectAssignment.project_id == project_id,
                RealEstateProjectAssignment.is_active == True,
            )
            .all()
        )
        team_members = [
            {
                "assignment_id": a.id,
                "user_id": u.id,
                "name": u.name or u.email,
                "email": u.email,
                "phone": u.phone_no,
                "role": a.role,
                "ai_recommended": a.ai_recommended,
                "ai_match_score": a.ai_match_score,
                "ai_recommendation_reason": a.ai_recommendation_reason,
            }
            for a, u in assignments
        ]

        units = self.list_units(project_id)

        return {
            "id": project.id,
            "name": project.name,
            "code": project.code,
            "location": project.location,
            "city": project.city,
            "address": project.address,
            "latitude": project.latitude,
            "longitude": project.longitude,
            "status": project.status,
            "total_units": project.total_units or len(units),
            "available_units": sum(1 for u in units if u["status"] == "available"),
            "hold_duration_hours": project.hold_duration_hours,
            "rera_number": project.rera_number,
            "amenities": project.amenities or [],
            "units": units,
            "team": team_members,
            "assigned_team_count": len(team_members),
        }

    def update_project(self, project_id: str, **kwargs) -> dict:
        """Update property project specifications."""
        project = (
            self.db.query(RealEstateProject)
            .filter(
                RealEstateProject.id == project_id,
                RealEstateProject.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        allowed_fields = {
            "name", "code", "location", "city", "address",
            "latitude", "longitude", "rera_number", "amenities",
            "hold_duration_hours", "status", "total_units", "available_units"
        }
        for k, v in kwargs.items():
            if k in allowed_fields and v is not None:
                setattr(project, k, v)

        self.db.commit()
        self.db.refresh(project)
        return self.get_project(project_id)

    def list_units(self, project_id: str, unit_type: str | None = None, status: str | None = None) -> list[dict]:
        """List units for a project with lazy reconciliation of expired holds."""
        self.reconcile_expired_holds(project_id)
        query = self.db.query(RealEstateUnit).filter(
            RealEstateUnit.tenant_id == self.tenant_id,
            RealEstateUnit.project_id == project_id,
        )
        if unit_type:
            query = query.filter(RealEstateUnit.unit_type == unit_type)
        if status:
            query = query.filter(RealEstateUnit.status == status)

        return [
            {
                "id": u.id,
                "project_id": u.project_id,
                "tower": u.tower,
                "unit_number": u.unit_number,
                "floor": u.floor,
                "unit_type": u.unit_type,
                "carpet_sqft": u.carpet_sqft,
                "base_price": u.base_price,
                "status": u.status,
                "version": u.version,
                "attributes": u.attributes or {},
            }
            for u in query.order_by(RealEstateUnit.unit_number).all()
        ]

    def create_unit(self, project_id: str, unit_number: str, unit_type: str, base_price: float, tower: str | None = None, floor: int | None = None, carpet_sqft: float | None = None) -> dict:
        """Add a unit to project inventory."""
        unit = RealEstateUnit(
            tenant_id=self.tenant_id,
            project_id=project_id,
            unit_number=unit_number,
            unit_type=unit_type,
            base_price=base_price,
            tower=tower,
            floor=floor,
            carpet_sqft=carpet_sqft,
            status="available",
        )
        self.db.add(unit)
        # Update project unit counts
        project = self.db.query(RealEstateProject).filter(RealEstateProject.id == project_id, RealEstateProject.tenant_id == self.tenant_id).first()
        if project:
            project.total_units = (project.total_units or 0) + 1
            project.available_units = (project.available_units or 0) + 1
        self.db.commit()
        self.db.refresh(unit)
        return {"id": unit.id, "unit_number": unit.unit_number, "status": unit.status}

    def request_unit_hold(self, unit_id: str, lead_id: str, deposit_amount: float = 0.0, notes: str | None = None) -> dict:
        """Atomically request or confirm a unit hold using optimistic concurrency locking."""
        unit = (
            self.db.query(RealEstateUnit)
            .filter(RealEstateUnit.id == unit_id, RealEstateUnit.tenant_id == self.tenant_id)
            .with_for_update()
            .first()
        )
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        # Lazy reconcile if hold expired
        if unit.status != "available":
            self.reconcile_unit_status(unit)
            if unit.status != "available":
                raise HTTPException(
                    status_code=409,
                    detail=f"Unit {unit.unit_number} is currently {unit.status.replace('_', ' ')} and cannot be held."
                )

        project = self.db.query(RealEstateProject).filter(
            RealEstateProject.id == unit.project_id,
            RealEstateProject.tenant_id == self.tenant_id
        ).first()
        hold_hours = project.hold_duration_hours if project else 48
        expires_at = datetime.now(timezone.utc) + timedelta(hours=hold_hours)

        token = str(uuid.uuid4())
        is_confirmed = deposit_amount > 0
        hold = RealEstateUnitHold(
            tenant_id=self.tenant_id,
            unit_id=unit.id,
            lead_id=lead_id,
            status="confirmed" if is_confirmed else "requested",
            confirmed_at=datetime.now(timezone.utc) if is_confirmed else None,
            expires_at=expires_at,
            deposit_amount=deposit_amount,
            deposit_verified=is_confirmed,
            concurrency_token=token,
            notes=notes,
        )
        unit.status = "confirmed_hold" if is_confirmed else "hold_requested"
        unit.version += 1
        if project and project.available_units and project.available_units > 0:
            project.available_units -= 1

        self.db.add(hold)
        self.db.commit()
        self.db.refresh(hold)

        return {
            "hold_id": hold.id,
            "unit_id": unit.id,
            "unit_number": unit.unit_number,
            "status": hold.status,
            "expires_at": hold.expires_at.isoformat(),
            "deposit_amount": hold.deposit_amount,
            "concurrency_token": token,
        }

    def release_hold(self, hold_id: str, reason: str = "Released by user") -> dict:
        """Release a hold and return the unit to available status."""
        hold = self.db.query(RealEstateUnitHold).filter(
            RealEstateUnitHold.id == hold_id,
            RealEstateUnitHold.tenant_id == self.tenant_id,
        ).first()
        if not hold:
            raise HTTPException(status_code=404, detail="Hold not found")

        hold.status = "released"
        unit = self.db.query(RealEstateUnit).filter(RealEstateUnit.id == hold.unit_id).first()
        if unit:
            unit.status = "available"
            unit.version += 1
            project = self.db.query(RealEstateProject).filter(RealEstateProject.id == unit.project_id).first()
            if project:
                project.available_units = (project.available_units or 0) + 1
        self.db.commit()
        return {"hold_id": hold.id, "status": "released", "unit_status": "available"}

    def reconcile_expired_holds(self, project_id: str) -> int:
        """Release expired holds back to available state, strictly preserving units that have committed bookings."""
        now = datetime.now(timezone.utc)
        expired_holds = (
            self.db.query(RealEstateUnitHold)
            .join(RealEstateUnit, RealEstateUnit.id == RealEstateUnitHold.unit_id)
            .filter(
                RealEstateUnitHold.tenant_id == self.tenant_id,
                RealEstateUnit.project_id == project_id,
                RealEstateUnitHold.status.in_(["requested", "confirmed"]),
                RealEstateUnitHold.expires_at < now,
            )
            .all()
        )

        count = 0
        for hold in expired_holds:
            hold.status = "expired"
            unit = self.db.query(RealEstateUnit).filter(RealEstateUnit.id == hold.unit_id).first()
            if unit and unit.status in ("hold_requested", "confirmed_hold"):
                # Check if unit has an active booking
                active_booking = (
                    self.db.query(RealEstateBooking)
                    .filter(
                        RealEstateBooking.unit_id == unit.id,
                        RealEstateBooking.status.notin_(["cancelled", "refunded"]),
                    )
                    .first()
                )
                if active_booking:
                    unit.status = "booked"
                else:
                    unit.status = "available"
                    project = self.db.query(RealEstateProject).filter(RealEstateProject.id == unit.project_id).first()
                    if project:
                        project.available_units = (project.available_units or 0) + 1
                unit.version += 1
                count += 1
        if count > 0:
            self.db.commit()
        return count

    def reconcile_all_expired_holds(self) -> int:
        """Tenant-wide scheduled reconciliation of all expired holds."""
        projects = self.db.query(RealEstateProject).filter(RealEstateProject.tenant_id == self.tenant_id).all()
        total = 0
        for p in projects:
            total += self.reconcile_expired_holds(p.id)
        return total

    def reconcile_unit_status(self, unit: RealEstateUnit) -> None:
        """Check and reconcile single unit status against active holds and bookings."""
        now = datetime.now(timezone.utc)
        active_booking = (
            self.db.query(RealEstateBooking)
            .filter(
                RealEstateBooking.unit_id == unit.id,
                RealEstateBooking.status.notin_(["cancelled", "refunded"]),
            )
            .first()
        )
        if active_booking:
            if unit.status != "booked":
                unit.status = "booked"
                unit.version += 1
                self.db.commit()
            return

        active_hold = self.db.query(RealEstateUnitHold).filter(
            RealEstateUnitHold.unit_id == unit.id,
            RealEstateUnitHold.status.in_(["requested", "confirmed"]),
            RealEstateUnitHold.expires_at >= now,
        ).first()
        if not active_hold and unit.status in ("hold_requested", "confirmed_hold"):
            unit.status = "available"
            unit.version += 1
            project = self.db.query(RealEstateProject).filter(RealEstateProject.id == unit.project_id).first()
            if project:
                project.available_units = (project.available_units or 0) + 1
            self.db.commit()


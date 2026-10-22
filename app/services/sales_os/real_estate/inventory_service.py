"""Atomic unit inventory reservation service with optimistic concurrency control."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.real_estate import RealEstateUnit, RealEstateUnitHold, RealEstateProject


class InventoryService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def list_projects(self) -> list[dict]:
        """List tenant-scoped property development projects."""
        projects = self.db.query(RealEstateProject).filter(
            RealEstateProject.tenant_id == self.tenant_id
        ).order_by(RealEstateProject.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "location": p.location,
                "city": p.city,
                "status": p.status,
                "total_units": p.total_units,
                "available_units": p.available_units,
                "hold_duration_hours": p.hold_duration_hours,
                "rera_number": p.rera_number,
                "amenities": p.amenities or [],
            }
            for p in projects
        ]

    def create_project(self, name: str, code: str | None = None, location: str | None = None, city: str | None = None, hold_duration_hours: int = 48) -> dict:
        """Create a new property project."""
        project = RealEstateProject(
            tenant_id=self.tenant_id,
            name=name,
            code=code or name.lower().replace(" ", "_"),
            location=location,
            city=city,
            hold_duration_hours=hold_duration_hours,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return {"id": project.id, "name": project.name, "code": project.code}

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
        """Release expired holds back to available state."""
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
                unit.status = "available"
                unit.version += 1
                count += 1
        if count > 0:
            self.db.commit()
        return count

    def reconcile_unit_status(self, unit: RealEstateUnit) -> None:
        now = datetime.now(timezone.utc)
        active_hold = self.db.query(RealEstateUnitHold).filter(
            RealEstateUnitHold.unit_id == unit.id,
            RealEstateUnitHold.status.in_(["requested", "confirmed"]),
            RealEstateUnitHold.expires_at >= now,
        ).first()
        if not active_hold and unit.status in ("hold_requested", "confirmed_hold"):
            unit.status = "available"
            unit.version += 1
            self.db.commit()

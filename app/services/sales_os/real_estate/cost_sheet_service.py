"""
Enterprise CPQ & Dynamic Cost Sheet Engine.
Computes authoritative real estate pricing breakdowns, floor rise charges (FRC),
preferential location charges (PLC), amenities, car parking, statutory taxes (GST/Stamp Duty),
and automated milestone payment schedules.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.real_estate import (
    RealEstateUnit,
    RealEstateProject,
    RealEstateCostSheet,
)
from app.models.verticals import Lead


class CostSheetService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def calculate_cost_sheet(
        self,
        unit_id: str,
        lead_id: Optional[str] = None,
        base_rate_per_sqft: Optional[float] = None,
        floor_rise_rate_per_sqft: float = 45.0,
        plc_type: Optional[str] = None,
        plc_rate_per_sqft: Optional[float] = None,
        car_parking_slots: int = 1,
        car_parking_charges_per_slot: float = 300000.0,
        clubhouse_charges: float = 250000.0,
        infrastructure_development_charges: float = 150000.0,
        gst_rate_pct: float = 5.0,
        stamp_duty_pct: float = 5.6,
        registration_fee_est: float = 30000.0,
        payment_plan_type: str = "construction_linked",
        maintenance_rate_monthly_sqft: float = 3.0,
    ) -> Dict[str, Any]:
        """
        Calculates complete CPQ pricing and milestone breakdown without persisting.
        Enables instant interactive pricing quotes and cost sensitivity analysis.
        """
        unit = (
            self.db.query(RealEstateUnit)
            .filter(
                RealEstateUnit.id == unit_id,
                RealEstateUnit.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        project = (
            self.db.query(RealEstateProject)
            .filter(
                RealEstateProject.id == unit.project_id,
                RealEstateProject.tenant_id == self.tenant_id,
            )
            .first()
        )

        lead = None
        if lead_id:
            lead = (
                self.db.query(Lead)
                .filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id)
                .first()
            )

        # 1. Base Dimensions & Rates
        carpet_sqft = unit.carpet_sqft or 1000.0
        super_builtup_sqft = round(carpet_sqft * 1.30, 1)  # Standard 30% loading
        effective_base_rate = (
            base_rate_per_sqft
            if (base_rate_per_sqft and base_rate_per_sqft > 0)
            else round(unit.base_price / carpet_sqft, 2)
        )
        base_unit_value = round(carpet_sqft * effective_base_rate, 2)

        # 2. Floor Rise Charges (FRC): Starts above 3rd floor
        floor_num = unit.floor or 1
        floor_rise_total = 0.0
        if floor_num > 3:
            floors_above_base = floor_num - 3
            floor_rise_total = round(floors_above_base * floor_rise_rate_per_sqft * carpet_sqft, 2)

        # 3. Preferential Location Charges (PLC)
        unit_attrs = unit.attributes or {}
        chosen_plc_type = plc_type or unit_attrs.get("facing") or unit_attrs.get("view")
        plc_total = 0.0
        if chosen_plc_type:
            effective_plc_rate = (
                plc_rate_per_sqft
                if (plc_rate_per_sqft and plc_rate_per_sqft > 0)
                else round(effective_base_rate * 0.04, 2)  # Default 4% PLC premium
            )
            plc_total = round(effective_plc_rate * carpet_sqft, 2)
        else:
            effective_plc_rate = 0.0

        # 4. Infrastructure & Parking
        parking_total = round(car_parking_slots * car_parking_charges_per_slot, 2)
        infra_total = round(infrastructure_development_charges, 2)
        club_total = round(clubhouse_charges, 2)

        # 5. Gross Consideration (Base Agreement Value)
        gross_consideration = round(
            base_unit_value
            + floor_rise_total
            + plc_total
            + club_total
            + infra_total
            + parking_total,
            2,
        )

        # 6. Statutory Taxes & Government Levies
        gst_amount = round(gross_consideration * (gst_rate_pct / 100.0), 2)
        stamp_duty_amount = round(gross_consideration * (stamp_duty_pct / 100.0), 2)
        reg_fee = round(registration_fee_est, 2)
        maintenance_advance = round(carpet_sqft * maintenance_rate_monthly_sqft * 12, 2)  # 1 year advance

        # 7. Total Effective All-Inclusive Price
        total_effective_price = round(
            gross_consideration + gst_amount + stamp_duty_amount + reg_fee + maintenance_advance,
            2,
        )

        # 8. Milestone Payment Schedule
        milestones = self._generate_milestone_schedule(
            payment_plan_type=payment_plan_type,
            gross_consideration=gross_consideration,
            gst_amount=gst_amount,
        )

        return {
            "unit_id": unit.id,
            "unit_number": unit.unit_number,
            "unit_type": unit.unit_type,
            "project_id": project.id if project else unit.project_id,
            "project_name": project.name if project else "Project",
            "lead_id": lead_id,
            "buyer_name": lead.name if lead else None,
            "currency": "INR",
            "carpet_sqft": carpet_sqft,
            "super_builtup_sqft": super_builtup_sqft,
            "base_rate_per_sqft": effective_base_rate,
            "base_unit_value": base_unit_value,
            "floor_number": floor_num,
            "floor_rise_rate_per_sqft": floor_rise_rate_per_sqft,
            "floor_rise_total": floor_rise_total,
            "plc_type": chosen_plc_type,
            "plc_rate_per_sqft": effective_plc_rate,
            "plc_total": plc_total,
            "clubhouse_charges": club_total,
            "infrastructure_development_charges": infra_total,
            "car_parking_slots": car_parking_slots,
            "car_parking_charges": parking_total,
            "gross_consideration": gross_consideration,
            "gst_rate_pct": gst_rate_pct,
            "gst_amount": gst_amount,
            "stamp_duty_pct": stamp_duty_pct,
            "stamp_duty_amount": stamp_duty_amount,
            "registration_fee_est": reg_fee,
            "maintenance_advance": maintenance_advance,
            "total_effective_price": total_effective_price,
            "payment_plan_type": payment_plan_type,
            "milestone_schedule": milestones,
        }

    def save_cost_sheet(
        self,
        unit_id: str,
        lead_id: Optional[str] = None,
        base_rate_per_sqft: Optional[float] = None,
        floor_rise_rate_per_sqft: float = 45.0,
        plc_type: Optional[str] = None,
        plc_rate_per_sqft: Optional[float] = None,
        car_parking_slots: int = 1,
        car_parking_charges_per_slot: float = 300000.0,
        clubhouse_charges: float = 250000.0,
        infrastructure_development_charges: float = 150000.0,
        gst_rate_pct: float = 5.0,
        stamp_duty_pct: float = 5.6,
        registration_fee_est: float = 30000.0,
        payment_plan_type: str = "construction_linked",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates and persists the official Cost Sheet record.
        Supersedes any existing active cost sheet for the same lead and unit.
        """
        calc = self.calculate_cost_sheet(
            unit_id=unit_id,
            lead_id=lead_id,
            base_rate_per_sqft=base_rate_per_sqft,
            floor_rise_rate_per_sqft=floor_rise_rate_per_sqft,
            plc_type=plc_type,
            plc_rate_per_sqft=plc_rate_per_sqft,
            car_parking_slots=car_parking_slots,
            car_parking_charges_per_slot=car_parking_charges_per_slot,
            clubhouse_charges=clubhouse_charges,
            infrastructure_development_charges=infrastructure_development_charges,
            gst_rate_pct=gst_rate_pct,
            stamp_duty_pct=stamp_duty_pct,
            registration_fee_est=registration_fee_est,
            payment_plan_type=payment_plan_type,
        )

        # Supersede any previous active cost sheet
        existing_sheets = (
            self.db.query(RealEstateCostSheet)
            .filter(
                RealEstateCostSheet.tenant_id == self.tenant_id,
                RealEstateCostSheet.unit_id == unit_id,
                RealEstateCostSheet.lead_id == lead_id,
                RealEstateCostSheet.status == "active",
            )
            .all()
        )
        for s in existing_sheets:
            s.status = "superseded"

        cost_sheet = RealEstateCostSheet(
            tenant_id=self.tenant_id,
            unit_id=unit_id,
            project_id=calc["project_id"],
            lead_id=lead_id,
            currency="INR",
            carpet_sqft=calc["carpet_sqft"],
            super_builtup_sqft=calc["super_builtup_sqft"],
            base_rate_per_sqft=calc["base_rate_per_sqft"],
            base_unit_value=calc["base_unit_value"],
            floor_number=calc["floor_number"],
            floor_rise_rate_per_sqft=calc["floor_rise_rate_per_sqft"],
            floor_rise_total=calc["floor_rise_total"],
            plc_type=calc["plc_type"],
            plc_rate_per_sqft=calc["plc_rate_per_sqft"],
            plc_total=calc["plc_total"],
            clubhouse_charges=calc["clubhouse_charges"],
            infrastructure_development_charges=calc["infrastructure_development_charges"],
            car_parking_slots=calc["car_parking_slots"],
            car_parking_charges=calc["car_parking_charges"],
            gross_consideration=calc["gross_consideration"],
            gst_rate_pct=calc["gst_rate_pct"],
            gst_amount=calc["gst_amount"],
            stamp_duty_pct=calc["stamp_duty_pct"],
            stamp_duty_amount=calc["stamp_duty_amount"],
            registration_fee_est=calc["registration_fee_est"],
            maintenance_advance=calc["maintenance_advance"],
            total_effective_price=calc["total_effective_price"],
            payment_plan_type=calc["payment_plan_type"],
            milestone_schedule=calc["milestone_schedule"],
            status="active",
            notes=notes,
        )

        self.db.add(cost_sheet)
        self.db.commit()
        self.db.refresh(cost_sheet)

        calc["id"] = cost_sheet.id
        calc["status"] = cost_sheet.status
        calc["created_at"] = cost_sheet.created_at.isoformat() if cost_sheet.created_at else None
        return calc

    def get_cost_sheet(self, cost_sheet_id: str) -> Dict[str, Any]:
        """Fetch cost sheet by ID."""
        cs = (
            self.db.query(RealEstateCostSheet)
            .filter(
                RealEstateCostSheet.id == cost_sheet_id,
                RealEstateCostSheet.tenant_id == self.tenant_id,
            )
            .first()
        )
        if not cs:
            raise HTTPException(status_code=404, detail="Cost sheet not found")

        unit = self.db.query(RealEstateUnit).filter(RealEstateUnit.id == cs.unit_id).first()
        project = self.db.query(RealEstateProject).filter(RealEstateProject.id == cs.project_id).first()
        lead = self.db.query(Lead).filter(Lead.id == cs.lead_id).first() if cs.lead_id else None

        return {
            "id": cs.id,
            "unit_id": cs.unit_id,
            "unit_number": unit.unit_number if unit else None,
            "unit_type": unit.unit_type if unit else None,
            "project_id": cs.project_id,
            "project_name": project.name if project else None,
            "lead_id": cs.lead_id,
            "buyer_name": lead.name if lead else None,
            "currency": cs.currency,
            "carpet_sqft": cs.carpet_sqft,
            "super_builtup_sqft": cs.super_builtup_sqft,
            "base_rate_per_sqft": cs.base_rate_per_sqft,
            "base_unit_value": cs.base_unit_value,
            "floor_number": cs.floor_number,
            "floor_rise_rate_per_sqft": cs.floor_rise_rate_per_sqft,
            "floor_rise_total": cs.floor_rise_total,
            "plc_type": cs.plc_type,
            "plc_rate_per_sqft": cs.plc_rate_per_sqft,
            "plc_total": cs.plc_total,
            "clubhouse_charges": cs.clubhouse_charges,
            "infrastructure_development_charges": cs.infrastructure_development_charges,
            "car_parking_slots": cs.car_parking_slots,
            "car_parking_charges": cs.car_parking_charges,
            "gross_consideration": cs.gross_consideration,
            "gst_rate_pct": cs.gst_rate_pct,
            "gst_amount": cs.gst_amount,
            "stamp_duty_pct": cs.stamp_duty_pct,
            "stamp_duty_amount": cs.stamp_duty_amount,
            "registration_fee_est": cs.registration_fee_est,
            "maintenance_advance": cs.maintenance_advance,
            "total_effective_price": cs.total_effective_price,
            "payment_plan_type": cs.payment_plan_type,
            "milestone_schedule": cs.milestone_schedule,
            "status": cs.status,
            "notes": cs.notes,
            "created_at": cs.created_at.isoformat() if cs.created_at else None,
        }

    def get_latest_cost_sheet_for_unit(self, unit_id: str, lead_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch the most recent active cost sheet for a unit."""
        query = self.db.query(RealEstateCostSheet).filter(
            RealEstateCostSheet.unit_id == unit_id,
            RealEstateCostSheet.tenant_id == self.tenant_id,
            RealEstateCostSheet.status == "active",
        )
        if lead_id:
            query = query.filter(RealEstateCostSheet.lead_id == lead_id)

        cs = query.order_by(RealEstateCostSheet.created_at.desc()).first()
        if not cs:
            return None
        return self.get_cost_sheet(cs.id)

    def _generate_milestone_schedule(
        self,
        payment_plan_type: str,
        gross_consideration: float,
        gst_amount: float,
    ) -> List[Dict[str, Any]]:
        """Generates RERA-compliant staged milestone payment schedules."""
        all_in_base = gross_consideration + gst_amount

        if payment_plan_type == "down_payment":
            # 10 : 80 : 10 plan
            return [
                {
                    "stage_index": 1,
                    "milestone_name": "Booking Deposit (EOI)",
                    "percentage": 10.0,
                    "amount": round(all_in_base * 0.10, 2),
                    "timeline": "Immediate upon Booking",
                },
                {
                    "stage_index": 2,
                    "milestone_name": "Agreement for Sale (Down Payment)",
                    "percentage": 80.0,
                    "amount": round(all_in_base * 0.80, 2),
                    "timeline": "Within 30 Days of Booking",
                },
                {
                    "stage_index": 3,
                    "milestone_name": "Handover & Notice of Possession",
                    "percentage": 10.0,
                    "amount": round(all_in_base * 0.10, 2),
                    "timeline": "Upon Physical Handover",
                },
            ]
        elif payment_plan_type == "subvention":
            # 10 : 75 : 15 plan
            return [
                {
                    "stage_index": 1,
                    "milestone_name": "Buyer Upfront Contribution",
                    "percentage": 10.0,
                    "amount": round(all_in_base * 0.10, 2),
                    "timeline": "Upon Booking Application",
                },
                {
                    "stage_index": 2,
                    "milestone_name": "Bank Loan Disbursement",
                    "percentage": 75.0,
                    "amount": round(all_in_base * 0.75, 2),
                    "timeline": "Construction Progress Linked",
                },
                {
                    "stage_index": 3,
                    "milestone_name": "Possession & Handover",
                    "percentage": 15.0,
                    "amount": round(all_in_base * 0.15, 2),
                    "timeline": "Upon Occupancy Certificate (OC)",
                },
            ]
        else:
            # Default Construction-Linked Plan (CLP) - RERA Aligned
            stages = [
                ("Booking Token / EOI", 10.0, "Immediate upon Reservation"),
                ("Execution of Agreement for Sale", 10.0, "Within 21 Days"),
                ("Completion of Foundation & Plinth", 10.0, "Milestone Certificate 1"),
                ("Casting of Slabs 1 through 4", 15.0, "Milestone Certificate 2"),
                ("Casting of Slabs 5 through 8", 15.0, "Milestone Certificate 3"),
                ("Completion of Top Roof Slab", 15.0, "Milestone Certificate 4"),
                ("Brickwork & Internal Plastering", 10.0, "Milestone Certificate 5"),
                ("Flooring, Plumbing & Electrical", 10.0, "Milestone Certificate 6"),
                ("Notice of Possession & Handover", 5.0, "Upon Occupancy Certificate"),
            ]
            return [
                {
                    "stage_index": idx + 1,
                    "milestone_name": name,
                    "percentage": pct,
                    "amount": round(all_in_base * (pct / 100.0), 2),
                    "timeline": timeline,
                }
                for idx, (name, pct, timeline) in enumerate(stages)
            ]

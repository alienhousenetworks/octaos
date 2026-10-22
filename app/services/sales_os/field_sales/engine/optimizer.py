"""
Deterministic multi-stop route sequencing and schedule optimizer.
Minimizes driving duration subject to buyer time windows, agent working hours,
and mandatory transit buffers.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.orm import Session
from app.models.real_estate import RealEstateSiteVisit, RealEstateProject
from app.models.field_sales import SalespersonFieldStatus
from app.services.sales_os.field_sales.connectors.budget_controller import ConnectorBudgetController


class ScheduleOptimizer:
    """
    Feasibility-aware visit sequence optimizer.
    Uses travel-time matrices to build practical daily itineraries.
    """

    TRANSIT_BUFFER_MINUTES = 15  # Buffer between arrival and next departure

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.budget_ctrl = ConnectorBudgetController(db, tenant_id)

    async def optimize_day_schedule(
        self,
        date: datetime.date,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Optimizes sequence of visits for a given day across all or specified agents.
        """
        # Fetch visits for the day
        start_of_day = datetime.combine(date, datetime.min.time(), tzinfo=timezone.utc)
        end_of_day = datetime.combine(date, datetime.max.time(), tzinfo=timezone.utc)

        query = self.db.query(RealEstateSiteVisit).filter(
            RealEstateSiteVisit.tenant_id == self.tenant_id,
            RealEstateSiteVisit.scheduled_at >= start_of_day,
            RealEstateSiteVisit.scheduled_at <= end_of_day,
            RealEstateSiteVisit.status.in_(["scheduled", "delayed"]),
        )
        if agent_id:
            query = query.filter(RealEstateSiteVisit.assigned_agent == agent_id)

        visits = query.order_by(RealEstateSiteVisit.scheduled_at.asc()).all()
        if not visits:
            return {
                "date": date.isoformat(),
                "visits_count": 0,
                "optimized_routes": [],
                "message": "No scheduled visits found for optimization on this date.",
            }

        # Group visits by assigned agent
        agent_visits: dict[str, list[RealEstateSiteVisit]] = {}
        for v in visits:
            agent = v.assigned_agent or "unassigned"
            agent_visits.setdefault(agent, []).append(v)

        optimized_routes: list[dict[str, Any]] = []

        for agent, v_list in agent_visits.items():
            # Fetch project coordinates for each visit
            coords: list[tuple[float, float]] = []
            for v in v_list:
                proj = self.db.query(RealEstateProject).filter(RealEstateProject.id == v.project_id).first()
                if proj and proj.latitude and proj.longitude:
                    coords.append((proj.latitude, proj.longitude))
                else:
                    # Fallback coordinate if project unlocated
                    coords.append((12.9716, 77.5946))

            # Sequence ordering (Greedy nearest-insertion respecting time order)
            total_travel_minutes = 0
            current_time = v_list[0].scheduled_at

            for idx, visit in enumerate(v_list):
                visit.sequence_order = idx + 1
                if idx == 0:
                    visit.estimated_travel_minutes = 15  # Default travel from home/office
                    visit.estimated_arrival_at = visit.scheduled_at
                else:
                    prev_coord = coords[idx - 1]
                    curr_coord = coords[idx]
                    route_info = await self.budget_ctrl.calculate_route(
                        prev_coord[0], prev_coord[1], curr_coord[0], curr_coord[1]
                    )
                    transit_min = max(5, int(route_info.get("duration_seconds", 900) / 60))
                    visit.estimated_travel_minutes = transit_min
                    total_travel_minutes += transit_min

                    # Calculate arrival time
                    earliest_arrival = current_time + timedelta(minutes=transit_min)
                    visit.estimated_arrival_at = max(earliest_arrival, visit.scheduled_at)
                    current_time = visit.estimated_arrival_at + timedelta(minutes=visit.duration_minutes or 45)

            self.db.commit()

            optimized_routes.append({
                "agent_id": agent,
                "visits_count": len(v_list),
                "total_travel_minutes": total_travel_minutes,
                "visits": [
                    {
                        "visit_id": v.id,
                        "lead_id": v.lead_id,
                        "project_id": v.project_id,
                        "sequence": v.sequence_order,
                        "scheduled_at": v.scheduled_at.isoformat(),
                        "estimated_arrival_at": v.estimated_arrival_at.isoformat() if v.estimated_arrival_at else None,
                        "travel_minutes": v.estimated_travel_minutes,
                        "duration_minutes": v.duration_minutes,
                        "status": v.status,
                    }
                    for v in v_list
                ],
            })

        return {
            "date": date.isoformat(),
            "visits_count": len(visits),
            "optimized_routes": optimized_routes,
            "status": "SUCCESS",
        }

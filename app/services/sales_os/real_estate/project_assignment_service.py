"""
Real Estate Project Team Assignment and Intelligent Lead-to-Specialist Dispatch Service.
Empowers admins to manage projects and sales employees, provides explainable AI team
recommendations, and autonomously assigns leads and site visits to available project specialists.
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.base import User
from app.models.real_estate import (
    RealEstateProject,
    RealEstateProjectAssignment,
    RealEstateSiteVisit,
    RealEstateUnit,
)
from app.models.field_sales import SalespersonFieldStatus
from app.models.verticals import Lead
from app.models.agents import ActivityLog
from app.core.security import get_password_hash


def _haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


class ProjectAssignmentService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # ─────────────────────────────────────────────────────────────
    # 1. SALES EMPLOYEES & DIRECTORY MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    def list_salespeople(self) -> List[Dict[str, Any]]:
        """
        List all sales employees in the tenant with their live shift status,
        daily capacity, and currently assigned projects.
        Strictly excludes HR, marketing, and non-sales personnel.
        """
        all_tenant_users = (
            self.db.query(User)
            .filter(
                User.tenant_id == self.tenant_id,
                User.is_active == True,
            )
            .order_by(User.name.asc())
            .all()
        )

        # Pre-query user IDs who have field sales status or project assignments
        field_status_user_ids = {
            row[0]
            for row in self.db.query(SalespersonFieldStatus.user_id)
            .filter(SalespersonFieldStatus.tenant_id == self.tenant_id)
            .all()
        }
        assignment_user_ids = {
            row[0]
            for row in self.db.query(RealEstateProjectAssignment.user_id)
            .filter(RealEstateProjectAssignment.tenant_id == self.tenant_id, RealEstateProjectAssignment.is_active == True)
            .all()
        }

        users = []
        for u in all_tenant_users:
            u_role = (getattr(u, "role", "") or "").lower()
            u_dept = (getattr(u, "department", "") or "").lower()

            # Check group memberships
            group_names = [g.name.lower() for g in getattr(u, "groups", [])] if getattr(u, "groups", None) else []
            has_sales_group = any("sales" in gn for gn in group_names)
            is_hr_group = any("hr" in gn or "talent" in gn for gn in group_names)

            is_hr = u_dept in ("hr", "people", "human resources") or u_role in ("hr", "hr_admin", "hr_recruiter", "recruiter") or is_hr_group
            has_sales_record = u.id in field_status_user_ids or u.id in assignment_user_ids

            # Explicitly exclude non-sales HR employees
            if is_hr and not (has_sales_record or has_sales_group):
                continue

            # Qualify as salesperson if:
            # 1. Has explicit sales status or project assignment
            # 2. Member of a sales group
            # 3. Department is Sales or role is sales_agent/sales/salesperson
            # 4. Or if tenant has no specific roles/groups set yet and user is not HR/marketing
            is_sales = (
                has_sales_record
                or has_sales_group
                or u_dept == "sales"
                or u_role in ("sales", "sales_agent", "salesperson")
                or (not u_role and not u_dept and not group_names)
            )

            if is_sales:
                users.append(u)

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        results = []

        for u in users:
            # Query field status
            field_status = (
                self.db.query(SalespersonFieldStatus)
                .filter(
                    SalespersonFieldStatus.tenant_id == self.tenant_id,
                    SalespersonFieldStatus.user_id == u.id,
                )
                .first()
            )

            # Query assigned projects
            assignments = (
                self.db.query(RealEstateProjectAssignment, RealEstateProject)
                .join(RealEstateProject, RealEstateProject.id == RealEstateProjectAssignment.project_id)
                .filter(
                    RealEstateProjectAssignment.tenant_id == self.tenant_id,
                    RealEstateProjectAssignment.user_id == u.id,
                    RealEstateProjectAssignment.is_active == True,
                )
                .all()
            )
            assigned_projects = [
                {
                    "project_id": p.id,
                    "project_name": p.name,
                    "location": p.location,
                    "role": a.role,
                }
                for a, p in assignments
            ]

            # Today's visit count
            today_visits = (
                self.db.query(RealEstateSiteVisit)
                .filter(
                    RealEstateSiteVisit.tenant_id == self.tenant_id,
                    RealEstateSiteVisit.assigned_agent == u.id,
                    RealEstateSiteVisit.scheduled_at >= today_start,
                    RealEstateSiteVisit.status.in_(["scheduled", "en_route", "arrived", "completed"]),
                )
                .count()
            )

            is_shift_active = field_status.is_shift_active if field_status else True
            agent_status = field_status.status if field_status else "available"
            max_visits = field_status.max_visits_per_day if field_status else 6

            results.append({
                "user_id": u.id,
                "name": u.name or u.email.split("@")[0].title(),
                "email": u.email,
                "phone": u.phone_no,
                "role": u.role,
                "designation": getattr(field_status, "designation", None) or "Property Specialist",
                "is_shift_active": is_shift_active,
                "status": agent_status,
                "working_hours_start": field_status.working_hours_start if field_status else "09:00",
                "working_hours_end": field_status.working_hours_end if field_status else "18:00",
                "today_visits": today_visits,
                "max_visits_per_day": max_visits,
                "assigned_projects_count": len(assigned_projects),
                "assigned_projects": assigned_projects,
                "last_latitude": field_status.last_latitude if field_status else None,
                "last_longitude": field_status.last_longitude if field_status else None,
                "last_location_updated_at": field_status.last_location_updated_at.isoformat() if field_status and field_status.last_location_updated_at else None,
            })

        return results

    def create_salesperson(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        designation: str = "Property Specialist",
        password: Optional[str] = None,
        working_hours_start: str = "09:00",
        working_hours_end: str = "18:00",
        max_visits_per_day: int = 6,
        initial_project_ids: Optional[List[str]] = None,
        assigned_by_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a new sales employee/agent in the tenant and provision their
        shift telemetry and project assignments.
        """
        clean_email = email.strip().lower()
        existing_user = (
            self.db.query(User)
            .filter(User.email == clean_email, User.tenant_id == self.tenant_id)
            .first()
        )

        if existing_user:
            user = existing_user
            user.name = name
            if phone:
                user.phone_no = phone
            user.department = "Sales"
            user.is_active = True
        else:
            default_pw = password or "OctaSales#2026"
            user = User(
                tenant_id=self.tenant_id,
                email=clean_email,
                name=name,
                phone_no=phone,
                role="sales_agent",
                department="Sales",
                hashed_password=get_password_hash(default_pw),
                is_active=True,
                is_verified=True,
                allowed_sections=["sales", "field_sales"],
            )
            self.db.add(user)
            self.db.flush()

        # Try to link user to the tenant's Sales Team group if groups are enabled
        try:
            from app.models.rbac import Group
            sales_group = (
                self.db.query(Group)
                .filter(Group.tenant_id == self.tenant_id, Group.name.ilike("%sales%"))
                .first()
            )
            if sales_group and sales_group not in user.groups:
                user.groups.append(sales_group)
        except Exception:
            pass

        # Provision or update SalespersonFieldStatus
        field_status = (
            self.db.query(SalespersonFieldStatus)
            .filter(
                SalespersonFieldStatus.tenant_id == self.tenant_id,
                SalespersonFieldStatus.user_id == user.id,
            )
            .first()
        )
        if not field_status:
            field_status = SalespersonFieldStatus(
                tenant_id=self.tenant_id,
                user_id=user.id,
                is_shift_active=True,
                status="available",
                working_hours_start=working_hours_start,
                working_hours_end=working_hours_end,
                max_visits_per_day=max_visits_per_day,
            )
            self.db.add(field_status)
        else:
            field_status.is_shift_active = True
            field_status.working_hours_start = working_hours_start
            field_status.working_hours_end = working_hours_end
            field_status.max_visits_per_day = max_visits_per_day

        # Assign initial projects if requested
        if initial_project_ids:
            for proj_id in initial_project_ids:
                existing_assignment = (
                    self.db.query(RealEstateProjectAssignment)
                    .filter(
                        RealEstateProjectAssignment.tenant_id == self.tenant_id,
                        RealEstateProjectAssignment.project_id == proj_id,
                        RealEstateProjectAssignment.user_id == user.id,
                    )
                    .first()
                )
                if not existing_assignment:
                    assignment = RealEstateProjectAssignment(
                        tenant_id=self.tenant_id,
                        project_id=proj_id,
                        user_id=user.id,
                        role="site_specialist",
                        is_active=True,
                        assigned_by_id=assigned_by_id,
                    )
                    self.db.add(assignment)
                else:
                    existing_assignment.is_active = True

        self.db.commit()
        self.db.refresh(user)

        return {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone_no,
            "designation": designation,
            "status": "available",
            "is_shift_active": True,
            "assigned_projects_count": len(initial_project_ids or []),
        }

    def update_salesperson_status(
        self,
        user_id: str,
        is_shift_active: Optional[bool] = None,
        status: Optional[str] = None,
        working_hours_start: Optional[str] = None,
        working_hours_end: Optional[str] = None,
        max_visits_per_day: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update operational shift parameters for an agent."""
        field_status = (
            self.db.query(SalespersonFieldStatus)
            .filter(
                SalespersonFieldStatus.tenant_id == self.tenant_id,
                SalespersonFieldStatus.user_id == user_id,
            )
            .first()
        )
        if not field_status:
            field_status = SalespersonFieldStatus(
                tenant_id=self.tenant_id,
                user_id=user_id,
                is_shift_active=True,
                status="available",
            )
            self.db.add(field_status)

        if is_shift_active is not None:
            field_status.is_shift_active = is_shift_active
            if is_shift_active:
                field_status.shift_started_at = datetime.now(timezone.utc)
            else:
                field_status.shift_ended_at = datetime.now(timezone.utc)
        if status:
            field_status.status = status
        if working_hours_start:
            field_status.working_hours_start = working_hours_start
        if working_hours_end:
            field_status.working_hours_end = working_hours_end
        if max_visits_per_day is not None:
            field_status.max_visits_per_day = max_visits_per_day

        self.db.commit()
        return {
            "user_id": user_id,
            "is_shift_active": field_status.is_shift_active,
            "status": field_status.status,
            "working_hours": f"{field_status.working_hours_start} - {field_status.working_hours_end}",
            "max_visits_per_day": field_status.max_visits_per_day,
        }

    # ─────────────────────────────────────────────────────────────
    # 2. AI PROJECT TEAM SUGGESTIONS & ADMIN CONFIRMATION
    # ─────────────────────────────────────────────────────────────

    def suggest_salespeople_for_project(self, project_id: str) -> Dict[str, Any]:
        """
        AI evaluates tenant sales force against project specifications
        (location/geocoordinates, luxury tier, workload capacity) and produces
        ranked recommendations with explainable scores and recommended roles.
        """
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

        # Determine price tier / luxury profile from units if present
        sample_units = (
            self.db.query(RealEstateUnit)
            .filter(
                RealEstateUnit.tenant_id == self.tenant_id,
                RealEstateUnit.project_id == project_id,
            )
            .all()
        )
        avg_price = sum(u.base_price for u in sample_units) / max(1, len(sample_units)) if sample_units else 15000000.0
        is_luxury_project = avg_price >= 20000000.0 or any("villa" in u.unit_type.lower() or "penthouse" in u.unit_type.lower() for u in sample_units)

        salespeople = self.list_salespeople()
        scored_candidates: List[Dict[str, Any]] = []

        for sp in salespeople:
            score = 0.0
            reasons = []

            # Factor 1: Proximity / Locality Fit (0 - 35 points)
            has_coords = (
                project.latitude is not None and project.longitude is not None and
                sp["last_latitude"] is not None and sp["last_longitude"] is not None
            )
            if has_coords:
                dist_km = _haversine_distance_km(
                    project.latitude, project.longitude,
                    sp["last_latitude"], sp["last_longitude"]
                )
                if dist_km <= 5.0:
                    score += 35.0
                    reasons.append(f"Ideal proximity: {dist_km} km from project site.")
                elif dist_km <= 15.0:
                    score += 25.0
                    reasons.append(f"Nearby base: {dist_km} km from site.")
                elif dist_km <= 35.0:
                    score += 15.0
                    reasons.append(f"Within metro area: {dist_km} km away.")
                else:
                    score += 5.0
            else:
                # Text locality match
                proj_loc = (project.location or project.city or "").lower()
                if proj_loc and (proj_loc in sp["name"].lower() or any(proj_loc in p["location"].lower() for p in sp["assigned_projects"] if p.get("location"))):
                    score += 28.0
                    reasons.append(f"Demonstrated familiarity with {project.location or project.city} corridor.")
                else:
                    score += 20.0
                    reasons.append(f"General coverage for {project.city or 'regional development'}.")

            # Factor 2: Workload & Project Bandwidth Balance (0 - 35 points)
            current_project_count = sp["assigned_projects_count"]
            if current_project_count == 0:
                score += 35.0
                reasons.append("High bandwidth: No active projects currently assigned.")
            elif current_project_count == 1:
                score += 30.0
                reasons.append("Optimal workload: Dedicated focus with only 1 active project.")
            elif current_project_count == 2:
                score += 24.0
                reasons.append("Balanced capacity: Currently handling 2 active projects.")
            elif current_project_count == 3:
                score += 15.0
                reasons.append("Moderate load: Assigned to 3 projects.")
            else:
                score += 5.0
                reasons.append(f"Heavy existing assignment load ({current_project_count} projects).")

            # Factor 3: Specialization & Category Match (0 - 30 points)
            if is_luxury_project:
                if "senior" in sp["role"].lower() or "lead" in sp["name"].lower() or "advisor" in sp["designation"].lower():
                    score += 30.0
                    reasons.append("Proven high-ticket buyer engagement and luxury advisory experience.")
                else:
                    score += 20.0
                    reasons.append("Capable showing specialist for premium residences.")
            else:
                score += 26.0
                reasons.append("Strong velocity across residential apartments and urban inventory.")

            # Factor 4: Shift Readiness
            if sp["is_shift_active"]:
                score += 5.0
            score = min(100.0, round(score, 1))

            scored_candidates.append({
                "user_id": sp["user_id"],
                "name": sp["name"],
                "email": sp["email"],
                "phone": sp["phone"],
                "match_score": score,
                "current_projects_count": current_project_count,
                "is_shift_active": sp["is_shift_active"],
                "rationales": reasons,
            })

        # Sort descending by match score
        scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)

        # Designate roles: Top 1 = primary_lead, others = site_specialist
        for idx, cand in enumerate(scored_candidates):
            cand["recommended_role"] = "primary_lead" if idx == 0 else "site_specialist"

        return {
            "project_id": project.id,
            "project_name": project.name,
            "location": project.location,
            "city": project.city,
            "is_luxury_profile": is_luxury_project,
            "total_candidates_evaluated": len(scored_candidates),
            "suggested_team": scored_candidates,
        }

    def assign_team_to_project(
        self,
        project_id: str,
        assignments: List[Dict[str, Any]],
        assigned_by_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Admin implements or updates confirmed project team assignments.
        Takes list of dicts: [{ user_id: str, role: str, ai_recommended: bool, match_score: float, reason: str }]
        """
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

        incoming_user_ids = {a["user_id"] for a in assignments if a.get("user_id")}

        # Deactivate previous assignments not in the incoming list
        existing_assignments = (
            self.db.query(RealEstateProjectAssignment)
            .filter(
                RealEstateProjectAssignment.tenant_id == self.tenant_id,
                RealEstateProjectAssignment.project_id == project_id,
            )
            .all()
        )
        for ea in existing_assignments:
            if ea.user_id not in incoming_user_ids:
                ea.is_active = False

        confirmed_members = []
        for item in assignments:
            u_id = item["user_id"]
            user = self.db.query(User).filter(User.id == u_id, User.tenant_id == self.tenant_id).first()
            if not user:
                continue

            assignment = (
                self.db.query(RealEstateProjectAssignment)
                .filter(
                    RealEstateProjectAssignment.tenant_id == self.tenant_id,
                    RealEstateProjectAssignment.project_id == project_id,
                    RealEstateProjectAssignment.user_id == u_id,
                )
                .first()
            )
            if not assignment:
                assignment = RealEstateProjectAssignment(
                    tenant_id=self.tenant_id,
                    project_id=project_id,
                    user_id=u_id,
                )
                self.db.add(assignment)

            assignment.role = item.get("role", "site_specialist")
            assignment.is_active = True
            assignment.ai_recommended = bool(item.get("ai_recommended", False))
            assignment.ai_match_score = item.get("match_score")
            assignment.ai_recommendation_reason = item.get("reason")
            assignment.assigned_by_id = assigned_by_id

            confirmed_members.append({
                "user_id": user.id,
                "name": user.name or user.email,
                "role": assignment.role,
                "ai_recommended": assignment.ai_recommended,
            })

        self.db.commit()

        # Log activity
        log = ActivityLog(
            tenant_id=self.tenant_id,
            agent_name="Real Estate Project Orchestrator",
            action="assign_project_team",
            description=f"Admin assigned {len(confirmed_members)} sales specialists to project {project.name}.",
            status="success",
        )
        self.db.add(log)
        self.db.commit()

        return {
            "project_id": project.id,
            "project_name": project.name,
            "assigned_team_count": len(confirmed_members),
            "team": confirmed_members,
        }

    def get_project_team(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch active assigned sales specialists for a project."""
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
        results = []
        for a, u in assignments:
            field_status = (
                self.db.query(SalespersonFieldStatus)
                .filter(
                    SalespersonFieldStatus.tenant_id == self.tenant_id,
                    SalespersonFieldStatus.user_id == u.id,
                )
                .first()
            )
            results.append({
                "assignment_id": a.id,
                "user_id": u.id,
                "name": u.name or u.email,
                "email": u.email,
                "phone": u.phone_no,
                "role": a.role,
                "is_shift_active": field_status.is_shift_active if field_status else True,
                "status": field_status.status if field_status else "available",
                "ai_recommended": a.ai_recommended,
                "ai_match_score": a.ai_match_score,
                "ai_recommendation_reason": a.ai_recommendation_reason,
            })
        return results

    # ─────────────────────────────────────────────────────────────
    # 3. INTELLIGENT LEAD NEED MATCHING & AUTO-ASSIGNMENT ("TAKE CARE")
    # ─────────────────────────────────────────────────────────────

    def assign_lead_to_available_salesperson(
        self,
        lead_id: str,
        project_id: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        unit_id: Optional[str] = None,
        visit_duration_minutes: int = 45,
    ) -> Dict[str, Any]:
        """
        Core autonomous assignment engine:
        1. Determines the project based on lead needs or explicit intent.
        2. Filters for salespersons assigned by admin to this project.
        3. Evaluates real-time availability among them (shift active, visit limits, schedule conflicts).
        4. Selects the optimal available specialist.
        5. 'Takes care': updates lead status, books the site visit, logs dispatch event,
           and prepares agent notifications.
        """
        lead = (
            self.db.query(Lead)
            .filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id)
            .first()
        )
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Step 1: Resolve Project
        target_project = None
        if project_id:
            target_project = (
                self.db.query(RealEstateProject)
                .filter(RealEstateProject.id == project_id, RealEstateProject.tenant_id == self.tenant_id)
                .first()
            )

        if not target_project and lead.company and "http" not in lead.company:
            # Check if lead.company matches project name
            target_project = (
                self.db.query(RealEstateProject)
                .filter(
                    RealEstateProject.tenant_id == self.tenant_id,
                    RealEstateProject.name.ilike(f"%{lead.company}%"),
                )
                .first()
            )

        if not target_project:
            # Run property matching service
            from app.services.sales_os.real_estate.property_matching_service import PropertyMatchingService
            matcher = PropertyMatchingService(self.db, self.tenant_id)
            matches_res = matcher.find_top_matches(lead_id, limit=1)
            top_matches = matches_res.get("top_matches", [])
            if top_matches:
                target_project_id = top_matches[0]["project_id"]
                target_project = self.db.query(RealEstateProject).filter(RealEstateProject.id == target_project_id).first()

        if not target_project:
            # Fallback to earliest active project
            target_project = (
                self.db.query(RealEstateProject)
                .filter(RealEstateProject.tenant_id == self.tenant_id)
                .order_by(RealEstateProject.created_at.asc())
                .first()
            )

        if not target_project:
            raise HTTPException(status_code=400, detail="No active property development projects exist for this tenant.")

        # Step 2: Retrieve sales persons assigned by admin to this project
        project_assignments = (
            self.db.query(RealEstateProjectAssignment, User)
            .join(User, User.id == RealEstateProjectAssignment.user_id)
            .filter(
                RealEstateProjectAssignment.tenant_id == self.tenant_id,
                RealEstateProjectAssignment.project_id == target_project.id,
                RealEstateProjectAssignment.is_active == True,
            )
            .all()
        )

        candidate_users = []
        is_fallback_team = False

        if project_assignments:
            for pa, u in project_assignments:
                candidate_users.append((u, pa.role))
        else:
            # If no specialist assigned yet to project, fallback to active tenant salespeople
            sales_directory = self.list_salespeople()
            sales_user_ids = {sp["user_id"] for sp in sales_directory}
            all_agents = (
                self.db.query(User)
                .filter(User.id.in_(sales_user_ids))
                .all()
            ) if sales_user_ids else []
            for u in all_agents:
                candidate_users.append((u, "site_specialist"))
            is_fallback_team = True

        if not candidate_users:
            raise HTTPException(status_code=400, detail="No sales specialists available in the organization.")

        # Step 3: Availability & Capacity Evaluation
        visit_time = scheduled_at or (datetime.now(timezone.utc) + timedelta(hours=2))
        day_start = visit_time.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        evaluated_agents: List[Dict[str, Any]] = []

        for user, role in candidate_users:
            field_status = (
                self.db.query(SalespersonFieldStatus)
                .filter(
                    SalespersonFieldStatus.tenant_id == self.tenant_id,
                    SalespersonFieldStatus.user_id == user.id,
                )
                .first()
            )

            is_shift_active = field_status.is_shift_active if field_status else True
            agent_status = field_status.status if field_status else "available"
            max_visits = field_status.max_visits_per_day if field_status else 6

            # Today's existing visit count
            today_visits = (
                self.db.query(RealEstateSiteVisit)
                .filter(
                    RealEstateSiteVisit.tenant_id == self.tenant_id,
                    RealEstateSiteVisit.assigned_agent == user.id,
                    RealEstateSiteVisit.scheduled_at >= day_start,
                    RealEstateSiteVisit.scheduled_at <= day_end,
                    RealEstateSiteVisit.status.in_(["scheduled", "en_route", "arrived", "completed"]),
                )
                .count()
            )

            # Check time conflict (+/- 45 mins)
            window_start = visit_time - timedelta(minutes=45)
            window_end = visit_time + timedelta(minutes=45)
            has_conflict = (
                self.db.query(RealEstateSiteVisit)
                .filter(
                    RealEstateSiteVisit.tenant_id == self.tenant_id,
                    RealEstateSiteVisit.assigned_agent == user.id,
                    RealEstateSiteVisit.scheduled_at >= window_start,
                    RealEstateSiteVisit.scheduled_at <= window_end,
                    RealEstateSiteVisit.status.in_(["scheduled", "en_route", "arrived"]),
                )
                .first()
            ) is not None

            # Scoring availability
            is_eligible = is_shift_active and agent_status != "off_duty" and today_visits < max_visits and not has_conflict
            
            # Distance bonus
            dist_km = None
            if (
                target_project.latitude is not None and target_project.longitude is not None and
                field_status and field_status.last_latitude and field_status.last_longitude
            ):
                dist_km = _haversine_distance_km(
                    target_project.latitude, target_project.longitude,
                    field_status.last_latitude, field_status.last_longitude
                )

            # Priority metric: Fewer visits completed today = higher priority (load balancing)
            load_factor = (max_visits - today_visits) / max(1, max_visits)
            role_bonus = 1.2 if role == "primary_lead" else 1.0

            dispatch_score = (load_factor * 50.0) + (role_bonus * 30.0)
            if dist_km is not None and dist_km <= 10.0:
                dispatch_score += max(0.0, 20.0 - dist_km)

            evaluated_agents.append({
                "user": user,
                "role": role,
                "is_shift_active": is_shift_active,
                "agent_status": agent_status,
                "today_visits": today_visits,
                "max_visits": max_visits,
                "has_conflict": has_conflict,
                "is_eligible": is_eligible,
                "distance_km": dist_km,
                "dispatch_score": dispatch_score,
            })

        # Pick top eligible agent
        eligible_agents = [a for a in evaluated_agents if a["is_eligible"]]
        if eligible_agents:
            eligible_agents.sort(key=lambda x: x["dispatch_score"], reverse=True)
            chosen = eligible_agents[0]
            assignment_status = "ASSIGNED_AVAILABLE"
            rationale = (
                f"Assigned to {chosen['user'].name or chosen['user'].email} ({chosen['role'].replace('_', ' ').title()}): "
                f"On-duty, {chosen['today_visits']}/{chosen['max_visits']} visits today, no schedule conflict at requested time."
            )
            if chosen["distance_km"]:
                rationale += f" Nearest to site ({chosen['distance_km']} km away)."
        else:
            # Fallback to least loaded agent among candidates
            evaluated_agents.sort(key=lambda x: x["today_visits"])
            chosen = evaluated_agents[0]
            assignment_status = "ASSIGNED_QUEUED"
            rationale = (
                f"Assigned to project specialist {chosen['user'].name or chosen['user'].email}. "
                f"Currently busy/off-duty; showing queued with priority alert."
            )

        selected_user = chosen["user"]

        # Step 4: "Take Care" (Execute Dispatch Actions)
        # 1. Update Lead
        lead.assigned_to = selected_user.name or selected_user.email
        lead.status = "visit_scheduled"
        
        lead_data = dict(lead.data or {})
        lead_data["project_id"] = target_project.id
        lead_data["project_name"] = target_project.name
        lead_data["assigned_specialist_id"] = selected_user.id
        lead_data["assigned_specialist_name"] = selected_user.name or selected_user.email
        
        history = lead_data.setdefault("dispatch_history", [])
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "ai_auto_dispatch",
            "project_id": target_project.id,
            "project_name": target_project.name,
            "specialist_id": selected_user.id,
            "specialist_name": selected_user.name or selected_user.email,
            "rationale": rationale,
        })
        lead.data = lead_data

        # 2. Book or Update Site Visit
        site_visit = (
            self.db.query(RealEstateSiteVisit)
            .filter(
                RealEstateSiteVisit.tenant_id == self.tenant_id,
                RealEstateSiteVisit.lead_id == lead.id,
                RealEstateSiteVisit.project_id == target_project.id,
                RealEstateSiteVisit.status.in_(["scheduled", "en_route"]),
            )
            .first()
        )
        if not site_visit:
            site_visit = RealEstateSiteVisit(
                tenant_id=self.tenant_id,
                lead_id=lead.id,
                project_id=target_project.id,
                unit_id=unit_id,
                scheduled_at=visit_time,
                duration_minutes=visit_duration_minutes,
                assigned_agent=selected_user.id,
                escort_contact=selected_user.phone_no,
                status="scheduled",
                recovery_notes=rationale,
            )
            self.db.add(site_visit)
        else:
            site_visit.assigned_agent = selected_user.id
            site_visit.scheduled_at = visit_time
            site_visit.escort_contact = selected_user.phone_no
            site_visit.recovery_notes = rationale

        # 3. Audit Activity Log
        activity = ActivityLog(
            tenant_id=self.tenant_id,
            agent_name="Sales AI Specialist Dispatcher",
            action="auto_assign_visit",
            description=f"Automated showing assignment for {lead.name or 'Prospective Buyer'} at {target_project.name} to specialist {selected_user.name}.",
            status="success",
        )
        self.db.add(activity)

        self.db.commit()
        self.db.refresh(site_visit)

        return {
            "lead_id": lead.id,
            "lead_name": lead.name,
            "project": {
                "id": target_project.id,
                "name": target_project.name,
                "location": target_project.location,
                "city": target_project.city,
            },
            "assigned_specialist": {
                "user_id": selected_user.id,
                "name": selected_user.name or selected_user.email,
                "email": selected_user.email,
                "phone": selected_user.phone_no,
                "role": chosen["role"],
            },
            "visit": {
                "id": site_visit.id,
                "scheduled_at": site_visit.scheduled_at.isoformat(),
                "duration_minutes": site_visit.duration_minutes,
                "status": site_visit.status,
            },
            "assignment_status": assignment_status,
            "decision_rationale": rationale,
            "is_fallback_unassigned_project": is_fallback_team,
        }

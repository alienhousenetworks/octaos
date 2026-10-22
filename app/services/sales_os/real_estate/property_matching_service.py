"""AI property matching engine respecting real database inventory with explainability evidence."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.real_estate import RealEstateUnit, RealEstateProject, RealEstateSiteVisit
from app.models.verticals import Lead


class PropertyMatchingService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def find_top_matches(self, lead_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Ranks available units against buyer requirements using hard constraints first and
        preference scoring second. Returns structured match explanations and next-best actions.
        """
        lead = (
            self.db.query(Lead)
            .filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id)
            .first()
        )
        if not lead:
            raise HTTPException(status_code=404, detail="Inquiry lead not found")

        lead_data = lead.data or {}
        # Parse profile requirements
        profile = self._extract_buyer_profile(lead, lead_data)

        # Query all available or hold-requested units for the tenant
        query = (
            self.db.query(RealEstateUnit, RealEstateProject)
            .join(RealEstateProject, RealEstateProject.id == RealEstateUnit.project_id)
            .filter(
                RealEstateUnit.tenant_id == self.tenant_id,
                RealEstateUnit.status.in_(["available", "hold_requested"]),
            )
        )

        # Filter by project if lead specifies a firm project
        if profile.get("project_id"):
            query = query.filter(RealEstateUnit.project_id == profile["project_id"])
        elif profile.get("project_name"):
            query = query.filter(RealEstateProject.name.ilike(f"%{profile['project_name']}%"))

        candidate_rows = query.all()
        scored_matches: List[Dict[str, Any]] = []

        for unit, project in candidate_rows:
            match_res = self._score_unit_fit(unit, project, profile)
            if match_res["eligible"]:
                scored_matches.append(match_res)

        # Sort by match score descending
        scored_matches.sort(key=lambda x: x["match_score"], reverse=True)
        top_matches = scored_matches[:limit]

        # Determine next-best action
        next_action = self._determine_next_best_action(lead, top_matches)

        return {
            "lead_id": lead.id,
            "buyer_name": lead.name,
            "profile_analyzed": profile,
            "total_inventory_evaluated": len(candidate_rows),
            "matched_count": len(scored_matches),
            "top_matches": top_matches,
            "next_best_action": next_action,
        }

    def _extract_buyer_profile(self, lead: Lead, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize buyer preferences from explicit lead fields and data payload."""
        # 1. Budget extraction
        raw_budget = lead.how_much or data.get("budget") or ""
        budget_min, budget_max = self._parse_budget_bounds(raw_budget)

        # 2. Unit configuration (e.g. 2BHK, 3BHK, Villa)
        pref = str(lead.need_of_what or data.get("unit_preference") or "").strip().upper()
        norm_config = None
        for config in ["1BHK", "2BHK", "3BHK", "4BHK", "PENTHOUSE", "VILLA", "PLOT"]:
            if config in pref:
                norm_config = config
                break

        return {
            "project_id": data.get("project_id"),
            "project_name": lead.company if (lead.company and "http" not in lead.company) else None,
            "unit_config": norm_config or (pref if len(pref) <= 12 else None),
            "budget_min": budget_min,
            "budget_max": budget_max,
            "property_type": data.get("property_type") or "Residential",
            "purchase_purpose": data.get("purchase_purpose") or "Self-Use",
            "financing_status": data.get("financing_status"),
            "purchase_timeline": data.get("purchase_timeline") or "30 Days",
        }

    def _parse_budget_bounds(self, raw_text: str) -> tuple[Optional[float], Optional[float]]:
        if not raw_text:
            return None, None

        # Clean string
        cleaned = raw_text.replace(",", "").replace("$", "").replace("₹", "").strip().lower()

        # Handle crore / lakh / k / m notation
        # e.g., "1.5 cr", "85 L", "1.2M", "500k-700k"
        numbers = re.findall(r"(\d+(?:\.\d+)?)\s*(cr|crore|l|lakh|k|m)?", cleaned)
        if not numbers:
            return None, None

        parsed_nums: List[float] = []
        for val_str, unit in numbers:
            try:
                num = float(val_str)
                if unit in ("cr", "crore"):
                    num *= 10000000.0
                elif unit in ("l", "lakh"):
                    num *= 100000.0
                elif unit == "m":
                    num *= 1000000.0
                elif unit == "k":
                    num *= 1000.0
                parsed_nums.append(num)
            except ValueError:
                pass

        if len(parsed_nums) == 1:
            # Single value: treat as upper bound budget
            return None, parsed_nums[0]
        elif len(parsed_nums) >= 2:
            return min(parsed_nums[0], parsed_nums[1]), max(parsed_nums[0], parsed_nums[1])

        return None, None

    def _score_unit_fit(
        self,
        unit: RealEstateUnit,
        project: RealEstateProject,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluates constraints and calculates a 0-100 fit score with explainability."""
        pros: List[str] = []
        cons: List[str] = []
        unknowns: List[str] = []
        score = 50.0  # Baseline

        # Hard Constraint 1: Configuration check
        req_config = profile.get("unit_config")
        unit_type = (unit.unit_type or "").upper()
        if req_config:
            if req_config in unit_type:
                score += 25.0
                pros.append(f"Matches desired configuration ({unit.unit_type})")
            else:
                # Soft mismatch
                score -= 20.0
                cons.append(f"Unit configuration ({unit.unit_type}) differs from preference ({req_config})")

        # Hard Constraint 2: Budget check with 15% elasticity
        price = unit.base_price
        b_max = profile.get("budget_max")
        b_min = profile.get("budget_min")

        if b_max:
            if price <= b_max:
                score += 20.0
                pros.append(f"Base price fits comfortably within budget")
            elif price <= b_max * 1.15:
                score += 5.0
                cons.append(f"Price exceeds maximum budget by {int(((price/b_max) - 1.0)*100)}% (within negotiable range)")
            else:
                # Beyond budget filter
                return {"eligible": False}

        if b_min and price < b_min * 0.8:
            score -= 10.0
            cons.append("Price is below stated minimum expectation")

        # Floor and Facing scoring
        if unit.floor:
            if unit.floor >= 10:
                score += 5.0
                pros.append(f"High-rise floor ({unit.floor}) offering scenic views")
            elif unit.floor <= 2:
                pros.append(f"Convenient low floor ({unit.floor}) with garden proximity")

        # Availability state check
        if unit.status == "hold_requested":
            score -= 10.0
            cons.append("Unit currently has an unconfirmed hold request; available for backup reservation")
        else:
            pros.append("Ready for immediate reservation and booking lock")

        # Unknowns check
        if not profile.get("financing_status"):
            unknowns.append("Buyer financing status (cash vs mortgage assistance) is unverified")
        if not profile.get("purchase_timeline"):
            unknowns.append("Definitive move-in timeline unconfirmed")

        final_score = max(10, min(99, int(score)))

        return {
            "eligible": True,
            "unit_id": unit.id,
            "unit_number": unit.unit_number,
            "tower": unit.tower,
            "floor": unit.floor,
            "unit_type": unit.unit_type,
            "carpet_sqft": unit.carpet_sqft,
            "base_price": unit.base_price,
            "status": unit.status,
            "project_id": project.id,
            "project_name": project.name,
            "location": project.location or project.city,
            "match_score": final_score,
            "pros": pros,
            "cons": cons,
            "unknowns": unknowns,
        }

    def _determine_next_best_action(self, lead: Lead, top_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Determines the most strategic sales action based on lead and showing state."""
        # Check existing visits
        recent_visit = (
            self.db.query(RealEstateSiteVisit)
            .filter(RealEstateSiteVisit.lead_id == lead.id, RealEstateSiteVisit.tenant_id == self.tenant_id)
            .order_by(RealEstateSiteVisit.scheduled_at.desc())
            .first()
        )

        if not recent_visit:
            if top_matches:
                best = top_matches[0]
                return {
                    "action_code": "schedule_site_visit",
                    "title": "Schedule Private Site Tour",
                    "description": f"Recommend showing {best['unit_type']} ({best['unit_number']}) at {best['project_name']} based on {best['match_score']}% preference fit.",
                    "priority": "high",
                    "suggested_unit_id": best["unit_id"],
                }
            return {
                "action_code": "qualify_requirements",
                "title": "Clarify Unit & Budget Preferences",
                "description": "Engage prospect to record preferred unit configuration and budget ceiling.",
                "priority": "medium",
            }

        if recent_visit.status == "completed":
            if recent_visit.buyer_interest_level in ("high", "ready_to_buy"):
                return {
                    "action_code": "request_unit_hold",
                    "title": "Secure 48-Hour Unit Reservation",
                    "description": "High intent showing completed. Offer atomic unit hold with token deposit.",
                    "priority": "urgent",
                    "suggested_unit_id": recent_visit.unit_id or (top_matches[0]["unit_id"] if top_matches else None),
                }
            elif recent_visit.buyer_interest_level == "medium":
                return {
                    "action_code": "address_objections",
                    "title": "Address Stated Buyer Objections",
                    "description": f"Send tailored floorplans or discuss financing assistance for objections: {', '.join(recent_visit.buyer_objections or ['pricing'])}.",
                    "priority": "medium",
                }

        if recent_visit.status in ("no_show", "cancelled"):
            return {
                "action_code": "reschedule_visit",
                "title": "Offer Alternative Showing Window",
                "description": "Previous showing was not completed. Re-engage via WhatsApp with convenient weekend slots.",
                "priority": "high",
            }

        return {
            "action_code": "confirm_upcoming_visit",
            "title": "Confirm Showing Details & Route",
            "description": f"Showing scheduled for {recent_visit.scheduled_at.strftime('%Y-%m-%d %H:%M')}. Ensure escort is assigned.",
            "priority": "medium",
        }

"""
Interview Availability & Conflict Checking Service.
Detects scheduling overlaps across interviewer panels and suggests conflict-free alternative slots.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.hr import Interview, InterviewPanelist


class InterviewAvailabilityService:
    @staticmethod
    def check_conflicts(
        db: Session,
        tenant_id: str,
        start_utc: datetime,
        duration_minutes: int,
        panelist_emails: List[str],
        exclude_interview_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Checks whether any panelist has an active interview overlapping with [start_utc, start_utc + duration_minutes].
        """
        end_utc = start_utc + timedelta(minutes=duration_minutes)
        conflicts = []

        if not panelist_emails:
            return {"has_conflict": False, "conflicts": []}

        # Query overlapping interviews for this tenant
        query = db.query(Interview, InterviewPanelist).join(
            InterviewPanelist, Interview.id == InterviewPanelist.interview_id
        ).filter(
            Interview.tenant_id == tenant_id,
            Interview.status.in_(["scheduled", "confirmed", "proposed"]),
            InterviewPanelist.email.in_(panelist_emails),
            # Overlap condition: start < other_end AND other_start < end
            Interview.starts_at < end_utc,
            Interview.ends_at > start_utc,
        )

        if exclude_interview_id:
            query = query.filter(Interview.id != exclude_interview_id)

        rows = query.all()

        for interview, panelist in rows:
            conflicts.append({
                "panelist_email": panelist.email,
                "panelist_name": panelist.name,
                "conflicting_interview_id": interview.id,
                "round_name": interview.round_name,
                "starts_at": interview.starts_at.isoformat() if interview.starts_at else None,
                "ends_at": interview.ends_at.isoformat() if interview.ends_at else None,
            })

        has_conflict = len(conflicts) > 0

        # Propose 3 alternative slots if there is a conflict
        suggested_slots = []
        if has_conflict:
            candidate_deltas = [timedelta(hours=1), timedelta(hours=2), timedelta(days=1)]
            for delta in candidate_deltas:
                alt_start = start_utc + delta
                # Quick check if alt_start is free
                alt_conflict = InterviewAvailabilityService.check_conflicts(
                    db=db,
                    tenant_id=tenant_id,
                    start_utc=alt_start,
                    duration_minutes=duration_minutes,
                    panelist_emails=panelist_emails,
                    exclude_interview_id=exclude_interview_id,
                )
                if not alt_conflict["has_conflict"]:
                    suggested_slots.append({
                        "starts_at": alt_start.isoformat(),
                        "ends_at": (alt_start + timedelta(minutes=duration_minutes)).isoformat(),
                    })
                if len(suggested_slots) >= 3:
                    break

        return {
            "has_conflict": has_conflict,
            "conflicts": conflicts,
            "suggested_slots": suggested_slots,
        }

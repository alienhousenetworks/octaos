"""Meeting Service for Sales OS: Calendar bookings and reply coordination."""
import logging
from typing import Any, Callable, Dict, Optional
from sqlalchemy.orm import Session

from app.models.verticals import Lead
from app.services.sales.meeting_booking import book_meeting_for_lead

logger = logging.getLogger(__name__)


class MeetingService:
    def __init__(self, db: Session, tenant_id: str, log_activity: Optional[Callable] = None):
        self.db = db
        self.tenant_id = tenant_id
        self._log_activity = log_activity or (lambda *args, **kwargs: None)

    async def schedule_meeting(self, params: dict) -> dict:
        """Schedule meeting for interested leads using configured calendar tool."""
        tool = params.get("tool", "google_calendar")

        leads = (
            self.db.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                Lead.status.in_(("replied", "contacted")),
            )
            .all()
        )
        booked_count = 0
        waiting = 0
        for lead in leads:
            data = lead.data or {}
            if not data.get("prospect_interested"):
                if lead.status == "contacted":
                    waiting += 1
                continue
            if lead.status == "meeting_scheduled":
                continue
            suggested_time = data.get("reply_classification", {}).get("suggested_time")
            if not suggested_time:
                waiting += 1
                data["meeting_coordination_status"] = "coordinating_slots"
                lead.data = data
                continue
            if book_meeting_for_lead(
                self.db,
                self.tenant_id,
                lead,
                tool=tool,
                suggested_time=suggested_time,
                log_activity=self._log_activity,
            ):
                booked_count += 1

        if waiting and booked_count == 0:
            self._log_activity(
                "Awaiting Real Replies",
                f"{waiting} leads contacted — meetings book automatically when they reply "
                "(email webhook, WhatsApp webhook, or Gmail poll).",
                "success",
            )

        self.db.commit()
        return {"status": "success", "booked_meetings": booked_count, "awaiting_replies": waiting}

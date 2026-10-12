from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from app.models.base import Base
import uuid
from sqlalchemy.sql import func
from datetime import datetime, timezone, timedelta

class ScheduledTrigger(Base):
    """
    Persistent scheduled trigger for autonomous agents (e.g. Sales Lead Generation, Campaign Planner).
    """
    __tablename__ = "scheduled_triggers"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    target_type = Column(String, nullable=False, index=True)  # "lead_generation", "campaign_planner"
    name = Column(String, nullable=True)

    # Schedule parameters
    frequency = Column(String, default="daily")  # once, hourly, daily, weekly, monthly, yearly
    time_of_day = Column(String, default="15:00")  # HH:MM (24-hour format)
    day_of_week = Column(Integer, nullable=True)  # 0=Monday .. 6=Sunday
    day_of_month = Column(Integer, nullable=True)  # 1..31
    interval_hours = Column(Integer, default=1)  # For hourly frequency

    # Execution directives
    instructions = Column(Text, nullable=True)  # Role / prompt guidelines
    config = Column(JSON, default=dict)  # Target options (lead_count, days, platforms, etc.)

    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String, default="idle")  # idle, success, failed, running
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def calculate_next_run(self, from_time: datetime = None) -> datetime:
        """
        Calculates the next run datetime in UTC.
        """
        now = from_time or datetime.now(timezone.utc)
        
        # Parse time of day
        try:
            parts = (self.time_of_day or "15:00").split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            hour, minute = 15, 0

        freq = (self.frequency or "daily").lower()

        if freq == "hourly":
            step = max(1, self.interval_hours or 1)
            candidate = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=step)
            while candidate <= now:
                candidate += timedelta(hours=step)
            return candidate

        elif freq == "daily":
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        elif freq == "weekly":
            target_dow = self.day_of_week if self.day_of_week is not None else 0  # Default Monday
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = (target_dow - now.weekday()) % 7
            if days_ahead == 0 and candidate <= now:
                days_ahead = 7
            candidate += timedelta(days=days_ahead)
            return candidate

        elif freq == "monthly":
            target_dom = max(1, min(28, self.day_of_month or 1))
            candidate = now.replace(day=target_dom, hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                # Next month
                month = now.month + 1
                year = now.year
                if month > 12:
                    month = 1
                    year += 1
                candidate = candidate.replace(year=year, month=month)
            return candidate

        elif freq == "yearly":
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate = candidate.replace(year=now.year + 1)
            return candidate

        elif freq == "once":
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(minutes=5)
            return candidate

        # Default fallback: daily
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

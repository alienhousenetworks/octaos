"""Durable background tasks for Real Estate hold expiration and showing reminders."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.base import Tenant
from app.models.real_estate import RealEstateSiteVisit, RealEstateProject
from app.models.verticals import Lead
from app.services.sales_os.real_estate.inventory_service import InventoryService


logger = logging.getLogger(__name__)


def expire_stale_holds_job(tenant_id: str | None = None) -> Dict[str, Any]:
    """
    Durable worker task to scan and release expired unit holds.
    Guarantees active bookings are preserved.
    """
    db: Session = SessionLocal()
    try:
        tenants: List[str] = []
        if tenant_id:
            tenants = [tenant_id]
        else:
            all_tenants = db.query(Tenant.id).all()
            tenants = [t[0] for t in all_tenants]

        total_released = 0
        details: Dict[str, int] = {}

        for tid in tenants:
            inv = InventoryService(db, tid)
            released = inv.reconcile_all_expired_holds()
            if released > 0:
                details[tid] = released
                total_released += released

        logger.info(f"expire_stale_holds_job completed: {total_released} holds released across {len(details)} tenants")
        return {
            "status": "success",
            "total_released": total_released,
            "tenant_breakdown": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error executing expire_stale_holds_job: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


def dispatch_upcoming_visit_reminders_job(window_minutes: int = 120) -> Dict[str, Any]:
    """
    Dispatches automated WhatsApp visit reminders to buyers 2 hours before scheduled showing.
    Includes project name and Google Maps coordinates/directions link.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=window_minutes)

        # Find visits scheduled in the upcoming window that are still 'scheduled'
        upcoming_visits = (
            db.query(RealEstateSiteVisit)
            .filter(
                RealEstateSiteVisit.status == "scheduled",
                RealEstateSiteVisit.scheduled_at >= now,
                RealEstateSiteVisit.scheduled_at <= window_end,
            )
            .all()
        )

        sent_count = 0
        skipped_count = 0

        for visit in upcoming_visits:
            lead = db.query(Lead).filter(Lead.id == visit.lead_id, Lead.tenant_id == visit.tenant_id).first()
            project = db.query(RealEstateProject).filter(RealEstateProject.id == visit.project_id).first()

            if not lead or not lead.phone:
                skipped_count += 1
                continue

            # Check if reminder already dispatched in extra data or notes
            reminder_key = f"reminder_sent_{visit.id}"
            lead_data = lead.data or {}
            if lead_data.get(reminder_key):
                skipped_count += 1
                continue

            proj_name = project.name if project else "our development"
            maps_link = ""
            if project and project.latitude and project.longitude:
                maps_link = f"\n📍 Location Pin: https://maps.google.com/?q={project.latitude},{project.longitude}"
            elif project and project.address:
                maps_link = f"\n📍 Address: {project.address}"

            local_time_str = visit.scheduled_at.strftime("%I:%M %p")
            msg_body = (
                f"Hello {lead.name or 'there'}! This is a friendly reminder for your scheduled private property tour at "
                f"{proj_name} today at {local_time_str}.{maps_link}\n"
                f"Your sales escort will be waiting to welcome you. If you need to adjust timing, reply to this message."
            )

            from app.services.sales.touch_dispatcher import send_whatsapp_with_status
            res = send_whatsapp_with_status(db, visit.tenant_id, lead.phone, msg_body)

            if res.get("sent"):
                sent_count += 1
                lead.data = {**lead_data, reminder_key: datetime.now(timezone.utc).isoformat()}
                db.commit()
            else:
                skipped_count += 1

        return {
            "status": "success",
            "evaluated_visits": len(upcoming_visits),
            "reminders_sent": sent_count,
            "skipped": skipped_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in dispatch_upcoming_visit_reminders_job: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


# Celery task registration if celery is present
try:
    from app.core.celery_app import celery_app

    @celery_app.task(name="expire_stale_holds_task")
    def expire_stale_holds_task(tenant_id: str | None = None):
        return expire_stale_holds_job(tenant_id)

    @celery_app.task(name="dispatch_upcoming_visit_reminders_task")
    def dispatch_upcoming_visit_reminders_task(window_minutes: int = 120):
        return dispatch_upcoming_visit_reminders_job(window_minutes)

except Exception as celery_err:
    logger.debug(f"Celery task registration bypassed: {celery_err}")

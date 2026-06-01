"""Route inbound email/WhatsApp to sales leads before support tickets."""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.services.sales.lead_matching import find_lead_for_inbound


async def route_incoming_to_sales(
    db: Session,
    tenant_id: str,
    channel: str,
    sender: str,
    content: str,
    *,
    subject: Optional[str] = None,
    external_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    If sender matches an active sales lead, queue sales reply processing.
    Returns {"handled": bool, ...}.
    """
    lead = find_lead_for_inbound(db, tenant_id, channel, sender)
    if not lead:
        return {"handled": False}

    celery_app.send_task(
        "process_sales_inbound_task",
        args=[tenant_id, lead.id, channel, content, subject, external_id],
    )
    return {"handled": True, "lead_id": lead.id, "queued": True}

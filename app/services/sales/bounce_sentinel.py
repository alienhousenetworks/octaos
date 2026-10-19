"""Bounce Sentinel & Automated Domain Deliverability Circuit Breaker.

Protects tenant domain reputation by:
1. Detecting Non-Delivery Reports (NDRs) and bounce notices from mailer-daemon / postmaster.
2. Extracting the bounced recipient address.
3. Adding the recipient address to Suppression with reason 'bounced'.
4. Atomically cancelling all pending outbox touches for that prospect.
5. Monitoring the rolling 24-hour bounce rate: if bounces exceed 3.0% (min 3 bounces),
   trips the tenant circuit-breaker ('sending_paused' = True) to prevent domain blacklisting.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Set, Tuple, Any

from sqlalchemy.orm import Session

from app.models.base import APICredential
from app.models.deal_room import SalesOutboxItem
from app.models.verticals import Lead
from app.services.sales.outbox_service import SalesOutboxService
from app.services.sales_os.governance.suppression import SuppressionService

logger = logging.getLogger(__name__)

BOUNCE_SENDERS = (
    "mailer-daemon",
    "postmaster",
    "mail-delivery-system",
    "delivery-failure",
)

BOUNCE_SUBJECT_KEYWORDS = (
    "delivery status notification (failure)",
    "undelivered mail returned to sender",
    "mail delivery failed",
    "failure notice",
    "address not found",
    "message not delivered",
)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


class BounceSentinel:
    @classmethod
    def is_bounce(cls, from_email: str, subject: str) -> bool:
        """Check if an incoming message is an NDR bounce notice."""
        from_lower = (from_email or "").lower()
        subj_lower = (subject or "").lower()

        for sender in BOUNCE_SENDERS:
            if sender in from_lower:
                return True

        for keyword in BOUNCE_SUBJECT_KEYWORDS:
            if keyword in subj_lower:
                return True

        return False

    @classmethod
    def extract_bounced_email(cls, body: str, known_candidate_emails: Optional[Set[str]] = None) -> Optional[str]:
        """Extract the recipient email that failed delivery from the NDR body."""
        if not body:
            return None

        # Check for explicit headers in NDR body
        hdr_match = re.search(r"(?:Final-Recipient|X-Failed-Recipients|To|failed):\s*(?:rfc822;\s*)?([^\s<>\"']+@[^\s<>\"']+)", body, re.IGNORECASE)
        if hdr_match:
            email = hdr_match.group(1).strip("<>").strip().lower()
            return email

        # Search for any known candidate emails appearing in the body
        all_emails = [e.lower() for e in EMAIL_REGEX.findall(body)]
        if known_candidate_emails:
            for e in all_emails:
                if e in known_candidate_emails:
                    return e

        # Otherwise pick the first non-system email
        for e in all_emails:
            if not any(sys_kw in e for sys_kw in ("googlemail", "google.com", "mailer-daemon", "postmaster")):
                return e

        return None

    @classmethod
    def record_bounce(
        cls,
        db: Session,
        tenant_id: str,
        bounced_email: str,
        reason: str = "bounced",
    ) -> Dict[str, Any]:
        """Record bounce, suppress contact, cancel outbox, and evaluate circuit breaker."""
        bounced_email = bounced_email.strip().lower()
        logger.warning(f"Recording bounce for {bounced_email} in tenant {tenant_id}")

        # 1. Suppress email
        suppression = SuppressionService(db, tenant_id)
        suppression.suppress(email=bounced_email, reason=reason)

        # 2. Cancel pending outbox items
        outbox = SalesOutboxService(db, tenant_id)
        cancelled = outbox.cancel_pending_for_lead(recipient_email=bounced_email, reason="bounce_detected")

        # 3. Update lead status if exists
        lead = db.query(Lead).filter(
            Lead.tenant_id == tenant_id,
            (Lead.email == bounced_email) | (Lead.personal_email == bounced_email) | (Lead.company_email == bounced_email)
        ).first()
        if lead:
            lead.status = "bounced"
            data = dict(lead.data or {})
            data["bounced_at"] = datetime.now(timezone.utc).isoformat()
            lead.data = data

        # 4. Update rolling 24h bounce history in APICredential
        cred = db.query(APICredential).filter_by(tenant_id=tenant_id, provider="sales").first()
        if not cred:
            cred = APICredential(tenant_id=tenant_id, provider="sales", encrypted_key="internal_settings", settings={})
            db.add(cred)

        settings = dict(cred.settings or {})
        now = datetime.now(timezone.utc)
        cutoff_24h = now - timedelta(hours=24)

        history = list(settings.get("bounce_history", []))
        # Keep only timestamps within last 24h
        history = [ts for ts in history if datetime.fromisoformat(ts) > cutoff_24h]
        history.append(now.isoformat())
        settings["bounce_history"] = history
        settings["bounce_count_24h"] = len(history)

        # 5. Check Circuit Breaker
        # Count total sent outbox items in the last 24h
        total_sent_24h = (
            db.query(SalesOutboxItem)
            .filter(
                SalesOutboxItem.tenant_id == tenant_id,
                SalesOutboxItem.status == "sent",
                SalesOutboxItem.sent_at >= cutoff_24h,
            )
            .count()
        )

        bounce_count = len(history)
        denominator = max(total_sent_24h + bounce_count, bounce_count)
        bounce_rate = round(float(bounce_count) / float(denominator), 4) if denominator > 0 else 0.0

        circuit_tripped = False
        # If bounce rate >= 3.0% with at least 3 bounces, trip circuit breaker
        if bounce_count >= 3 and bounce_rate >= 0.03:
            settings["sending_paused"] = True
            settings["paused_reason"] = f"Circuit breaker tripped: {bounce_rate * 100:.1f}% bounce rate ({bounce_count} bounces in 24h)."
            circuit_tripped = True
            logger.critical(
                f"[CIRCUIT BREAKER] Tenant {tenant_id} outbound PAUSED! Bounce rate: {bounce_rate*100:.1f}%"
            )

        cred.settings = settings
        db.commit()

        return {
            "bounced_email": bounced_email,
            "cancelled_outbox_items": cancelled,
            "bounce_count_24h": bounce_count,
            "bounce_rate_24h": bounce_rate,
            "circuit_tripped": circuit_tripped,
            "sending_paused": settings.get("sending_paused", False),
        }

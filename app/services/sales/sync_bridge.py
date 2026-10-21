"""Bidirectional synchronization bridge ensuring zero split-brain across Lead, DealRoom, and SalesIntelligence."""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.verticals import Lead
from app.models.deal_room import DealRoom, BuyingCommitteeMember, SuppressionRecord
from app.models.sales_intelligence import SalesCompany, AccountContact, SalesOpportunity
from app.services.sales_os.discovery.identity import canonical_domain, domain_from_email
from app.services.sales_os.governance.suppression import SuppressionService

logger = logging.getLogger(__name__)


class SalesSyncBridge:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.suppression = SuppressionService(db, tenant_id)

    def _resolve_domain(self, lead: Lead) -> Optional[str]:
        domain = None
        if lead.data and lead.data.get("website"):
            domain = canonical_domain(lead.data.get("website"))
        if not domain and lead.company:
            domain = canonical_domain(lead.company)
        if not domain and lead.email:
            domain = domain_from_email(lead.email)
        return domain

    def sync_lead_entities(self, lead: Lead, auto_commit: bool = False) -> Dict[str, Any]:
        """
        Ensures a Lead has corresponding linked DealRoom, BuyingCommitteeMember,
        SalesCompany, AccountContact, and SalesOpportunity records.
        """
        domain = self._resolve_domain(lead)
        company_name = lead.company or (domain.split('.')[0].capitalize() if domain else "Target Account")
        now = datetime.now(timezone.utc)

        # 1. DealRoom Resolution
        deal_room = None
        data = dict(lead.data or {})
        deal_room_id = data.get("deal_room_id")
        if deal_room_id:
            deal_room = self.db.query(DealRoom).filter_by(id=deal_room_id, tenant_id=self.tenant_id).first()
        if not deal_room and domain:
            deal_room = self.db.query(DealRoom).filter_by(tenant_id=self.tenant_id, domain=domain).first()

        if not deal_room and domain:
            deal_room = DealRoom(
                tenant_id=self.tenant_id,
                company_name=company_name,
                domain=domain,
                website=data.get("website") or f"https://{domain}",
                stage="discovered",
                last_activity_at=now,
            )
            self.db.add(deal_room)
            self.db.flush()

        if deal_room:
            data["deal_room_id"] = deal_room.id
            lead.data = data

            # BuyingCommitteeMember Resolution
            if lead.email:
                bcm = self.db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id, email=lead.email).first()
                if not bcm:
                    bcm = BuyingCommitteeMember(
                        deal_room_id=deal_room.id,
                        tenant_id=self.tenant_id,
                        name=lead.name or "Decision Maker",
                        email=lead.email,
                        phone=lead.phone,
                        title=data.get("title") or "Executive",
                        role_type="economic_buyer",
                        engagement_state="uncontacted",
                    )
                    self.db.add(bcm)
                    self.db.flush()

                member_count = self.db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room.id).count()
                if member_count >= 2:
                    deal_room.is_multi_threaded = True
                    self.db.flush()

        # 2. Canonical SalesCompany Resolution
        sales_company = None
        if lead.sales_company_id:
            sales_company = self.db.query(SalesCompany).filter_by(id=lead.sales_company_id, tenant_id=self.tenant_id).first()
        if not sales_company and domain:
            sales_company = self.db.query(SalesCompany).filter_by(tenant_id=self.tenant_id, canonical_domain=domain).first()

        if not sales_company and domain:
            sales_company = SalesCompany(
                tenant_id=self.tenant_id,
                canonical_domain=domain,
                display_name=company_name,
                website=data.get("website") or f"https://{domain}",
                deal_room_id=deal_room.id if deal_room else None,
            )
            self.db.add(sales_company)
            self.db.flush()

        if sales_company:
            lead.sales_company_id = sales_company.id
            if deal_room and not sales_company.deal_room_id:
                sales_company.deal_room_id = deal_room.id

            # Canonical AccountContact Resolution
            if lead.email and not lead.sales_contact_id:
                contact = self.db.query(AccountContact).filter_by(tenant_id=self.tenant_id, company_id=sales_company.id, email=lead.email).first()
                if not contact:
                    contact = AccountContact(
                        tenant_id=self.tenant_id,
                        company_id=sales_company.id,
                        full_name=lead.name or "Contact",
                        email=lead.email,
                        phone=lead.phone,
                    )
                    self.db.add(contact)
                    self.db.flush()
                lead.sales_contact_id = contact.id

            # Canonical SalesOpportunity Resolution
            if not lead.sales_opportunity_id:
                opp = self.db.query(SalesOpportunity).filter_by(tenant_id=self.tenant_id, company_id=sales_company.id).first()
                if not opp:
                    opp = SalesOpportunity(
                        tenant_id=self.tenant_id,
                        company_id=sales_company.id,
                        stage="discovered",
                        score=float(lead.score or 0),
                    )
                    self.db.add(opp)
                    self.db.flush()
                lead.sales_opportunity_id = opp.id

        if auto_commit:
            self.db.commit()

        return {
            "deal_room_id": deal_room.id if deal_room else None,
            "sales_company_id": sales_company.id if sales_company else None,
            "sales_opportunity_id": lead.sales_opportunity_id,
            "sales_contact_id": lead.sales_contact_id,
        }

    def sync_outreach_sent(self, lead: Lead, sent_actual: bool = True, auto_commit: bool = True) -> None:
        """Invoked when outreach is dispatched to ensure all pipeline stages advance."""
        self.sync_lead_entities(lead, auto_commit=False)
        now = datetime.now(timezone.utc)

        stage = "in_cadence" if sent_actual else "outreach_ready"
        comm_state = "contacted" if sent_actual else "uncontacted"

        data = lead.data or {}
        deal_room_id = data.get("deal_room_id")
        if deal_room_id:
            room = self.db.query(DealRoom).filter_by(id=deal_room_id, tenant_id=self.tenant_id).first()
            if room:
                room.stage = stage
                room.last_activity_at = now
            if lead.email:
                bcm = self.db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room_id, email=lead.email).first()
                if bcm:
                    bcm.engagement_state = comm_state

        if lead.sales_opportunity_id:
            opp = self.db.query(SalesOpportunity).filter_by(id=lead.sales_opportunity_id, tenant_id=self.tenant_id).first()
            if opp and opp.stage == "discovered":
                opp.stage = "qualified"

        if auto_commit:
            self.db.commit()

    def sync_reply_received(
        self,
        lead: Lead,
        intent: str,
        reply_text: str,
        auto_commit: bool = True,
    ) -> None:
        """Invoked when a prospect responds to outreach."""
        self.sync_lead_entities(lead, auto_commit=False)
        now = datetime.now(timezone.utc)

        is_unsubscribe = intent in ("unsubscribe", "opt_out", "dnc") or any(
            w in reply_text.lower() for w in ("unsubscribe", "remove me", "stop emailing", "leave me alone", "do not contact")
        )

        data = dict(lead.data or {})
        deal_room_id = data.get("deal_room_id")
        domain = self._resolve_domain(lead)

        if is_unsubscribe:
            # 1. Enforce strict multi-channel suppression
            if lead.email:
                self.suppression.add_suppression(
                    identifier_type="email",
                    identifier_value=lead.email,
                    reason="prospect_unsubscribe_reply",
                    origin="inbound_reply_sync",
                )
            if domain:
                self.suppression.add_suppression(
                    identifier_type="domain",
                    identifier_value=domain,
                    reason="prospect_unsubscribe_reply",
                    origin="inbound_reply_sync",
                )

            # 2. Synchronize Lead
            lead.status = "opt_out"

            # 3. Synchronize DealRoom & Committee
            if deal_room_id:
                room = self.db.query(DealRoom).filter_by(id=deal_room_id, tenant_id=self.tenant_id).first()
                if room:
                    room.stage = "closed_lost"
                    room.last_activity_at = now
                if lead.email:
                    bcm = self.db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room_id, email=lead.email).first()
                    if bcm:
                        bcm.engagement_state = "opt_out"

            # 4. Synchronize SalesOpportunity
            if lead.sales_opportunity_id:
                opp = self.db.query(SalesOpportunity).filter_by(id=lead.sales_opportunity_id, tenant_id=self.tenant_id).first()
                if opp:
                    opp.stage = "closed_lost"

            logger.info(f"Synchronized unsubscribe for lead {lead.email} across Lead, DealRoom, and SuppressionRecord.")

        else:
            # Positive / Engaged reply
            lead.status = "replied"

            if deal_room_id:
                room = self.db.query(DealRoom).filter_by(id=deal_room_id, tenant_id=self.tenant_id).first()
                if room:
                    room.stage = "engaged"
                    room.last_activity_at = now
                if lead.email:
                    bcm = self.db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room_id, email=lead.email).first()
                    if bcm:
                        bcm.engagement_state = "engaged"

            if lead.sales_opportunity_id:
                opp = self.db.query(SalesOpportunity).filter_by(id=lead.sales_opportunity_id, tenant_id=self.tenant_id).first()
                if opp and opp.stage in ("discovered", "qualified"):
                    opp.stage = "evaluating"

            logger.info(f"Synchronized engaged reply for lead {lead.email} across Lead, DealRoom, and SalesOpportunity.")

        if auto_commit:
            self.db.commit()

    def sync_meeting_booked(self, lead: Lead, auto_commit: bool = True) -> None:
        """Invoked when a calendar meeting is successfully booked."""
        self.sync_lead_entities(lead, auto_commit=False)
        now = datetime.now(timezone.utc)

        lead.status = "meeting_scheduled"

        data = lead.data or {}
        deal_room_id = data.get("deal_room_id")
        if deal_room_id:
            room = self.db.query(DealRoom).filter_by(id=deal_room_id, tenant_id=self.tenant_id).first()
            if room:
                room.stage = "evaluating"
                room.last_activity_at = now
            if lead.email:
                bcm = self.db.query(BuyingCommitteeMember).filter_by(deal_room_id=deal_room_id, email=lead.email).first()
                if bcm:
                    bcm.engagement_state = "champion"

        if lead.sales_opportunity_id:
            opp = self.db.query(SalesOpportunity).filter_by(id=lead.sales_opportunity_id, tenant_id=self.tenant_id).first()
            if opp:
                opp.stage = "evaluating"

        if auto_commit:
            self.db.commit()
        logger.info(f"Synchronized meeting booked for lead {lead.email} across Lead, DealRoom, and SalesOpportunity.")

    def reconcile_tenant_leads_to_canonical(self, limit: int = 500) -> Dict[str, Any]:
        """
        Transactional reconciliation engine ensuring zero split-brain between legacy
        leads and canonical Sales OS entities (SalesCompany, AccountContact, DealRoom, BuyingCommittee).
        """
        leads = (
            self.db.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                (Lead.sales_company_id.is_(None)) | (Lead.sales_contact_id.is_(None))
            )
            .limit(limit)
            .all()
        )

        scanned = len(leads)
        promoted = 0
        linked_rooms = 0
        errors = []

        for lead in leads:
            try:
                res = self.sync_lead_entities(lead, auto_commit=False)
                if res.get("sales_company_id"):
                    promoted += 1
                if res.get("deal_room_id"):
                    linked_rooms += 1
            except Exception as e:
                errors.append({"lead_id": lead.id, "error": str(e)})
                logger.error(f"Reconciliation error on lead {lead.id}: {e}")

        self.db.commit()
        return {
            "tenant_id": self.tenant_id,
            "scanned": scanned,
            "promoted_to_canonical": promoted,
            "linked_deal_rooms": linked_rooms,
            "errors": errors,
        }

"""Channel partner / broker attribution and commission service."""
from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.real_estate import RealEstateBrokerAttribution


class PartnerService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def get_attribution_for_lead(self, lead_id: str) -> dict | None:
        """Get broker attribution record for an inquiry."""
        partner = (
            self.db.query(RealEstateBrokerAttribution)
            .filter(
                RealEstateBrokerAttribution.tenant_id == self.tenant_id,
                RealEstateBrokerAttribution.lead_id == lead_id,
            )
            .first()
        )
        if not partner:
            return None
        return {
            "id": partner.id,
            "lead_id": partner.lead_id,
            "brokerage_name": partner.brokerage_name,
            "broker_agent_name": partner.broker_agent_name,
            "broker_email": partner.broker_email,
            "broker_phone": partner.broker_phone,
            "rera_id": partner.rera_id,
            "commission_pct": partner.commission_pct,
            "agreement_verified": partner.agreement_verified,
            "status": partner.status,
        }

    def attribute_broker(
        self,
        lead_id: str,
        brokerage_name: str,
        broker_agent_name: str | None = None,
        broker_email: str | None = None,
        broker_phone: str | None = None,
        rera_id: str | None = None,
        commission_pct: float = 2.0,
        agreement_doc_url: str | None = None,
    ) -> dict:
        """Create or update broker attribution on an inquiry."""
        partner = (
            self.db.query(RealEstateBrokerAttribution)
            .filter(
                RealEstateBrokerAttribution.tenant_id == self.tenant_id,
                RealEstateBrokerAttribution.lead_id == lead_id,
            )
            .first()
        )
        if not partner:
            partner = RealEstateBrokerAttribution(
                tenant_id=self.tenant_id,
                lead_id=lead_id,
                brokerage_name=brokerage_name,
            )
            self.db.add(partner)

        partner.brokerage_name = brokerage_name
        partner.broker_agent_name = broker_agent_name
        partner.broker_email = broker_email
        partner.broker_phone = broker_phone
        partner.rera_id = rera_id
        partner.commission_pct = commission_pct
        partner.agreement_doc_url = agreement_doc_url

        self.db.commit()
        self.db.refresh(partner)
        return {
            "id": partner.id,
            "brokerage_name": partner.brokerage_name,
            "commission_pct": partner.commission_pct,
            "status": partner.status,
        }

    def calculate_commission(self, lead_id: str, booking_amount: float) -> dict:
        """Calculate payable commission based on stored attribution agreement."""
        partner = self.get_attribution_for_lead(lead_id)
        pct = partner["commission_pct"] if partner else 2.0
        payable = (booking_amount * pct) / 100.0
        return {
            "booking_amount": booking_amount,
            "commission_pct": pct,
            "payable_commission": payable,
            "brokerage_name": partner["brokerage_name"] if partner else None,
            "attributed": partner is not None,
        }

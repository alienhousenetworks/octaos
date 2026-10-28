from typing import Optional
from sqlalchemy.orm import Session
from app.models.verticals import Lead
from app.services.llm_gateway import LLMGateway
from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper


class SalesService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def score_lead(self, lead_id: str):
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id).first()
        if not lead:
            return None
        
        # Name, company, and source do not support a qualification score.
        data = dict(lead.data or {})
        data["qualification"] = {
            "decision": "needs_review",
            "rationale": "Name, company, and source are not enough evidence to score this lead.",
            "unknowns": ["industry", "size", "revenue", "intent", "evidence"],
            "contract_id": "sales.lightweight_score",
        }
        lead.data = data
        lead.status = "needs_review"
        self.db.commit()
        return None

    async def generate_outreach(self, lead_id: str, instructions: str = "") -> Optional[str]:
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id).first()
        if not lead:
            return None
        
        # Try routing to DealRoom ComposerAgent if a DealRoom exists for this lead
        try:
            from app.models.deal_room import DealRoom
            from app.services.sales_os.discovery.identity import canonical_domain, domain_from_email
            from app.services.sales_os.agents.composer import ComposerAgent

            domain = canonical_domain(lead.company) or domain_from_email(lead.email or "")
            if domain:
                room = self.db.query(DealRoom).filter_by(tenant_id=self.tenant_id, domain=domain).first()
                if room:
                    composer = ComposerAgent(self.db, self.tenant_id)
                    result = await composer.execute(room.id, {"channel": "email"})
                    if result and result.data and result.data.get("body"):
                        return result.data.get("body")
        except Exception:
            pass

        # Fallback to direct prompt with strict gatekeeper sanitization
        data = lead.data or {}
        title = (data.get("contact") or {}).get("title") or ""

        from app.models.base import User
        from app.models.verticals import BusinessProfile
        bp = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
        company_name = bp.company_name if (bp and bp.company_name) else "our company"
        sender_website = (bp.website or "").strip() if bp and bp.website else ""
        user = self.db.query(User).filter_by(tenant_id=self.tenant_id).order_by(User.is_superuser.desc(), User.id.asc()).first()
        employee_name = user.name.strip() if (user and user.name and user.name.strip()) else None

        if employee_name:
            sender_rule = f"Write on behalf of {employee_name} at {company_name}. Sign off with: Best regards, {employee_name}, {company_name}."
        else:
            sender_rule = f"Write on behalf of {company_name}. Do NOT invent any employee or sender name. Sign off strictly with: Best regards, The {company_name} Team."
        if sender_website:
            sender_rule += f" The only website in the signature is {sender_website}."
        else:
            sender_rule += " Do not invent a website."
        sender_rule += " Never end the email with the prospect's own website or email domain."

        prompt = (
            f"Write a personalized short outreach email (under 120 words, body only, no placeholders, no clichés) "
            f"for {lead.name} {f'({title}) ' if title else ''}at {lead.company}. Found via {lead.source}.\n"
            f"Why now: {lead.why or data.get('why_now') or 'n/a'}\n"
            f"Pain points: {data.get('pain_points') or 'n/a'}\n"
            f"Our offer: {lead.need_of_what or 'n/a'}\n"
            f"Sender & Context: {sender_rule}\n"
            f"Never use clichés like 'hope this finds you well' or 'in today's fast-paced world'.\n"
            f"Use only verified facts; do not invent any fake human personas."
        )
        if instructions:
            prompt += f"\nUser instructions to follow: {instructions}"
        
        raw_message = await self.llm.complete(prompt, model="claude-3-sonnet-20240229")
        cleaned_body = PreSendGatekeeper.strip_html(raw_message or "")
        from app.services.sales.contact_quality import correct_sender_signature, prospect_hosts

        return correct_sender_signature(
            cleaned_body,
            prospect_hosts=prospect_hosts(lead),
            sender_website=sender_website or None,
        )

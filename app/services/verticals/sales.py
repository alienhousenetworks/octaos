from sqlalchemy.orm import Session
from app.models.verticals import Lead
from app.services.llm_gateway import LLMGateway

class SalesService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = LLMGateway(db, tenant_id)

    async def score_lead(self, lead_id: str):
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id).first()
        if not lead:
            return
        
        # Scoring logic using AI
        prompt = f"Score this lead from 0-100 based on quality: Name: {lead.name}, Company: {lead.company}, Source: {lead.source}. Just return the number."
        score_str = await self.llm.complete(prompt, model="claude-3-haiku-20240307")
        try:
            lead.score = int(score_str.strip())
        except:
            lead.score = 50 # Default if AI fails
        
        lead.status = "scored"
        self.db.commit()
        return lead.score

    async def generate_outreach(self, lead_id: str, instructions: str = ""):
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id).first()
        if not lead:
            return
        
        data = lead.data or {}
        title = (data.get("contact") or {}).get("title") or ""

        from app.models.base import User
        from app.models.verticals import BusinessProfile
        bp = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
        company_name = bp.company_name if (bp and bp.company_name) else "our company"
        user = self.db.query(User).filter_by(tenant_id=self.tenant_id).order_by(User.is_superuser.desc(), User.id.asc()).first()
        employee_name = user.name.strip() if (user and user.name and user.name.strip()) else None

        if employee_name:
            sender_rule = f"Write on behalf of {employee_name} at {company_name}. Sign off with: Best regards, {employee_name}, {company_name}."
        else:
            sender_rule = f"Write on behalf of {company_name}. Do NOT invent any employee or sender name. Sign off strictly with: Best regards, The {company_name} Team."

        prompt = (
            f"Write a personalized short outreach email (under 120 words, body only, no placeholders) "
            f"for {lead.name} {f'({title}) ' if title else ''}at {lead.company}. Found via {lead.source}.\n"
            f"Why now: {lead.why or data.get('why_now') or 'n/a'}\n"
            f"Pain points: {data.get('pain_points') or 'n/a'}\n"
            f"Our offer: {lead.need_of_what or 'n/a'}\n"
            f"Sender & Context: {sender_rule}\n"
            f"Use only the facts above; do not invent any fake human personas."
        )
        if instructions:
            prompt += f"\nUser instructions to follow: {instructions}"
        message = await self.llm.complete(prompt, model="claude-3-sonnet-20240229")
        return message

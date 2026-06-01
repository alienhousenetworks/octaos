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

    async def generate_outreach(self, lead_id: str):
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == self.tenant_id).first()
        if not lead:
            return
        
        prompt = f"Write a personalized short outreach email for {lead.name} from {lead.company}. They were found via {lead.source}."
        message = await self.llm.complete(prompt, model="claude-3-sonnet-20240229")
        return message

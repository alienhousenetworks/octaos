from sqlalchemy.orm import Session
from app.services.llm_gateway import LLMGateway
from app.models.agents import KnowledgeDocument, ActivityLog

class BaseAgent:
    def __init__(self, db: Session, tenant_id: str, agent_name: str):
        self.db = db
        self.tenant_id = tenant_id
        self.agent_name = agent_name
        self.llm = LLMGateway(db, tenant_id)

    def log_activity(self, action: str, description: str, status: str = "success"):
        log = ActivityLog(
            tenant_id=self.tenant_id,
            agent_name=self.agent_name,
            action=action,
            description=description,
            status=status
        )
        self.db.add(log)
        self.db.commit()

    def get_knowledge_context(self, department: str = None) -> str:
        query = self.db.query(KnowledgeDocument).filter(
            KnowledgeDocument.tenant_id == self.tenant_id
        )
        if department:
            query = query.filter(KnowledgeDocument.department.in_([department, "General"]))
        
        docs = query.all()
        if not docs:
            return ""
        
        context = (
            "Company Guidelines & Knowledge Base:\n"
            "CRITICAL INSTRUCTION: You must strictly adhere to the company guidelines, brand rules, "
            "contact details (e.g. email, phone), and websites listed below. Incorporate them "
            "into your generated output (social posts, emails, replies, etc.) whenever relevant.\n\n"
        )
        for doc in docs:
            context += f"- [{doc.doc_type}]: {doc.content}\n"
        return context

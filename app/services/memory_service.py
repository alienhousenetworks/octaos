from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.memory import GlobalMemory, EpisodicMemory, CrossAgentContext, ManagerFeedback

class MemoryService:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    # --- Global Memory ---
    def get_global_rules(self, category: Optional[str] = None) -> List[GlobalMemory]:
        query = self.db.query(GlobalMemory).filter_by(tenant_id=self.tenant_id, is_active=True)
        if category:
            query = query.filter_by(category=category)
        return query.all()

    def add_global_rule(self, category: str, rule_name: str, content: str) -> GlobalMemory:
        rule = GlobalMemory(
            tenant_id=self.tenant_id,
            category=category,
            rule_name=rule_name,
            content=content
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    # --- Episodic Memory ---
    def save_episodic_memory(self, department: str, action_type: str, context: str, action_taken: str, outcome: str, embedding: Optional[list] = None) -> EpisodicMemory:
        memory = EpisodicMemory(
            tenant_id=self.tenant_id,
            department=department,
            action_type=action_type,
            context=context,
            action_taken=action_taken,
            outcome=outcome,
            embedding=embedding
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def search_episodic_memory(self, embedding_query: list, department: str, limit: int = 5) -> List[EpisodicMemory]:
        # Using pgvector's L2 distance `<->` operator
        # This requires the pgvector extension and the Vector type to be properly set up.
        memories = self.db.query(EpisodicMemory).filter(
            EpisodicMemory.tenant_id == self.tenant_id,
            EpisodicMemory.department == department
        ).order_by(EpisodicMemory.embedding.l2_distance(embedding_query)).limit(limit).all()
        return memories

    # --- Cross Agent Context (Watercooler) ---
    def broadcast_context(self, source_agent: str, entity_id: str, entity_type: str, message: str, target_agent: Optional[str] = None, expires_at: Optional[datetime] = None) -> CrossAgentContext:
        context = CrossAgentContext(
            tenant_id=self.tenant_id,
            source_agent=source_agent,
            target_agent=target_agent,
            entity_id=entity_id,
            entity_type=entity_type,
            message=message,
            expires_at=expires_at
        )
        self.db.add(context)
        self.db.commit()
        self.db.refresh(context)
        return context

    def get_context_for_entity(self, entity_id: str, agent_name: str) -> List[CrossAgentContext]:
        now = datetime.now(timezone.utc)
        query = self.db.query(CrossAgentContext).filter(
            CrossAgentContext.tenant_id == self.tenant_id,
            CrossAgentContext.entity_id == entity_id,
            (CrossAgentContext.target_agent == None) | (CrossAgentContext.target_agent == agent_name),
            (CrossAgentContext.expires_at == None) | (CrossAgentContext.expires_at > now)
        )
        return query.all()

    # --- Manager Feedback ---
    def submit_manager_feedback(self, department: str, original_output: str, edited_output: str, manager_comment: Optional[str] = None, task_id: Optional[str] = None) -> ManagerFeedback:
        feedback = ManagerFeedback(
            tenant_id=self.tenant_id,
            department=department,
            task_id=task_id,
            original_output=original_output,
            edited_output=edited_output,
            manager_comment=manager_comment
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

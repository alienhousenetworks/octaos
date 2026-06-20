import json
from typing import List
from sqlalchemy.orm import Session
from app.models.memory import ManagerFeedback
from app.services.memory_service import MemoryService
from app.services.ai_gateway.llm_gateway import LLMGateway # assuming some gateway exists, use abstract or direct
from app.core.config import settings

class LearningService:
    def __init__(self, db: Session):
        self.db = db

    async def process_pending_feedback(self, tenant_id: str):
        """
        Analyzes unprocessed ManagerFeedback records and generates new Global Rules.
        """
        feedbacks = self.db.query(ManagerFeedback).filter(
            ManagerFeedback.tenant_id == tenant_id,
            ManagerFeedback.is_processed == False
        ).all()

        if not feedbacks:
            return {"processed": 0}

        memory_service = MemoryService(self.db, tenant_id)
        # Using a simplistic LLM interaction pattern here for illustration
        
        # Group feedbacks by department
        feedbacks_by_dept = {}
        for f in feedbacks:
            if f.department not in feedbacks_by_dept:
                feedbacks_by_dept[f.department] = []
            feedbacks_by_dept[f.department].append(f)

        processed_count = 0
        new_rules_count = 0

        for dept, dept_feedbacks in feedbacks_by_dept.items():
            # In a real scenario, we'd invoke the LLM to extract the Delta and propose a rule.
            # Example prompt to LLM:
            # "Here are N edits a manager made to an AI's output. 
            # Original: {f.original}, Edited: {f.edited}, Comment: {f.comment}. 
            # What systemic rule should the AI learn from this?"
            
            # Simulated LLM generation of a rule:
            if dept_feedbacks:
                # We mock the rule generation for now, assuming an LLM parsed them.
                # In production: await llm.complete(prompt)
                learned_rule = f"Extracted from {len(dept_feedbacks)} feedback instances: Always adhere strictly to manager tonal corrections."
                
                # Save the new rule to GlobalMemory
                memory_service.add_global_rule(
                    category=f"{dept}_guidelines",
                    rule_name=f"Learned Rule Batch {dept_feedbacks[0].id[:6]}",
                    content=learned_rule
                )
                new_rules_count += 1
                
                # Mark as processed
                for f in dept_feedbacks:
                    f.is_processed = True
                    processed_count += 1

        self.db.commit()
        return {"processed": processed_count, "new_rules": new_rules_count}

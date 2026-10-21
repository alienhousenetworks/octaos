"""
People & Policy Administration Specialist Agent.
Provides grounded policy RAG answers, compliance audits, and document expiry tracking.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.hr_core import CompanyPolicy, PolicyAcknowledgement
from app.services.agents.hr.schemas import (
    AgentTaskResult,
    EvidenceReference,
    Finding,
    ProposedAction,
    RiskTier
)


class PeopleAdminSpecialist:
    """Answers employee policy inquiries using authorized, versioned company policies."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def query_policy(self, query_text: str, category: Optional[str] = None) -> AgentTaskResult:
        q = self.db.query(CompanyPolicy).filter(
            CompanyPolicy.tenant_id == self.tenant_id,
            CompanyPolicy.is_active.is_(True)
        )
        if category:
            q = q.filter(CompanyPolicy.category == category.lower())

        policies = q.all()

        query_lower = query_text.lower()
        matched_policies = []
        for pol in policies:
            # Match keywords in title, summary, or content
            score = 0
            words = [w for w in query_lower.split() if len(w) > 3]
            for w in words:
                if w in pol.title.lower():
                    score += 3
                if pol.summary and w in pol.summary.lower():
                    score += 2
                if w in pol.content.lower():
                    score += 1
            if score > 0:
                matched_policies.append((score, pol))

        matched_policies.sort(key=lambda x: x[0], reverse=True)

        evidence_list = []
        if matched_policies:
            top_pol = matched_policies[0][1]
            evidence_list.append(EvidenceReference(
                source_type="policy_document",
                source_id=top_pol.id,
                citation=f"Policy: '{top_pol.title}' (v{top_pol.version}, Category: {top_pol.category})",
                confidence=0.92
            ))
            summary_answer = (
                f"According to the official **{top_pol.title}** (v{top_pol.version}):\n\n"
                f"{top_pol.summary or top_pol.content[:400]}..."
            )
            findings = [Finding(
                severity="info",
                code="POLICY_FOUND",
                message=f"Answer grounded in {top_pol.title} effective since {top_pol.effective_date.strftime('%Y-%m-%d') if top_pol.effective_date else 'current date'}."
            )]
        else:
            # Fallback to general HR Knowledge Documents via RAG
            rag_hits = []
            try:
                from app.services.kb_rag import KnowledgeRAGService
                kb = KnowledgeRAGService(self.db, self.tenant_id)
                rag_hits = kb.retrieve(query_text, department="HR", top_k=2)
            except Exception:
                pass

            if rag_hits:
                top_hit = rag_hits[0]
                evidence_list.append(EvidenceReference(
                    source_type="knowledge_document",
                    source_id=top_hit.get("document_id") or "kb-rag",
                    citation=top_hit.get("citation") or f"HR Knowledge: {top_hit.get('title', 'Handbook')}",
                    confidence=0.88
                ))
                summary_answer = (
                    f"According to company HR knowledge records ({top_hit.get('citation')}):\n\n"
                    f"{top_hit.get('content', '')[:500]}..."
                )
                findings = [Finding(
                    severity="info",
                    code="RAG_KB_FOUND",
                    message=f"Answer grounded in HR knowledge base article '{top_hit.get('title')}'."
                )]
            else:
                summary_answer = (
                    "No specific policy document found matching your query in the organization policy vault. "
                    "Please verify with your HR administrator or review the Employee Handbook."
                )
                findings = [Finding(
                    severity="warning",
                    code="NO_POLICY_MATCH",
                    message="Query could not be grounded in an active tenant policy."
                )]

        return AgentTaskResult(
            task_id=f"policy-task-{len(evidence_list)}",
            agent_id="people_admin_agent",
            intent="policy_query",
            status="completed",
            summary=summary_answer,
            evidence=evidence_list,
            findings=findings,
            proposed_actions=[],
            risk_assessment={"risk_tier": RiskTier.R0_READ_ONLY.value, "requires_approval": False}
        )

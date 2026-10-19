"""Conversational HR copilot. It drafts and explains. It does not send or hire by itself."""
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.hr import Application, HRAgentInvocation, InterviewFeedback, JobRequisition


class HROrchestrator:
    def handle(self, db: Session, tenant_id: str, user_id: str, utterance: str) -> Dict[str, Any]:
        text = (utterance or "").strip()
        lower = text.lower()
        blocked = any(word in lower for word in ("reject", "hire them", "send the offer", "send offer"))
        if blocked:
            self._log(db, tenant_id, user_id, "blocked", "L1")
            return {
                "autonomy": "L1",
                "tool": None,
                "message": "That action needs a person to submit it for approval. I will not reject, hire, or send from this chat.",
            }
        if "requisition" in lower or "open role" in lower or "blocker" in lower:
            rows = db.query(JobRequisition).filter_by(tenant_id=tenant_id).all()
            open_rows = [r for r in rows if r.status in {"open", "draft", "pending_approval"}]
            self._log(db, tenant_id, user_id, "summarize_requisitions", "L0")
            return {
                "autonomy": "L0",
                "tool": "summarize_requisitions",
                "requisitions": [
                    {"id": r.id, "title": r.title, "status": r.status, "headcount_approved": r.headcount_approved, "headcount_filled": r.headcount_filled}
                    for r in open_rows
                ],
            }
        if "feedback" in lower:
            waiting = (
                db.query(Application)
                .filter_by(tenant_id=tenant_id, current_stage="interviewing", status="active")
                .all()
            )
            pending = []
            for app in waiting:
                feedback = db.query(InterviewFeedback).filter(
                    InterviewFeedback.interview_id.isnot(None)
                ).count()
                pending.append({"application_id": app.id, "stage": app.current_stage, "feedback_rows_in_tenant": feedback})
            self._log(db, tenant_id, user_id, "waiting_feedback", "L0")
            return {"autonomy": "L0", "tool": "waiting_feedback", "applications": pending}
        if "strongest" in lower or "best candidate" in lower:
            apps = db.query(Application).filter_by(tenant_id=tenant_id, status="active").limit(5).all()
            self._log(db, tenant_id, user_id, "list_active", "L0")
            return {
                "autonomy": "L0",
                "tool": "list_active",
                "message": "These are active applications. A score is not a hiring decision.",
                "applications": [{"id": a.id, "stage": a.current_stage, "candidate_id": a.candidate_id} for a in apps],
            }
        self._log(db, tenant_id, user_id, "clarify", "L0")
        return {
            "autonomy": "L0",
            "tool": None,
            "message": "I can summarize open requisitions, list applications waiting in interview, or list active applications. I do not email candidates from chat.",
        }

    def _log(self, db: Session, tenant_id: str, user_id: str, tool: str, autonomy: str) -> None:
        db.add(HRAgentInvocation(
            tenant_id=tenant_id,
            user_id=user_id,
            tool=tool,
            autonomy=autonomy,
            prompt_version="hr_copilot_rules_v1",
            model_id=None,
            cost_accounted=True,
        ))
        db.flush()

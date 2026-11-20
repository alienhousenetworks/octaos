from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions.rbac import Action, Resource, require_permission
from app.core.tenancy.models import User
from app.db import get_db
from app.learning.models import DecisionRecord, NegativePatternMemory, StrategyPerformance
from app.learning.service import LearningLoop

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


class RecordDecisionRequest(BaseModel):
    agent_name: str
    task_type: str
    strategy_used: str
    prompt_version: str = "v1"
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)
    context_features: dict[str, Any] = Field(default_factory=dict)


class RecordOutcomeRequest(BaseModel):
    decision_id: str
    result_status: str  # success|failure|partial
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    user_feedback_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    behavioral_signals: dict[str, Any] = Field(default_factory=dict)
    failure_category: Optional[str] = None


@router.get("/summary")
def learning_summary(
    current_user: User = Depends(require_permission(Resource.LEARNING, Action.READ)),
    db: Session = Depends(get_db),
):
    decisions = db.query(DecisionRecord).filter(DecisionRecord.tenant_id == current_user.tenant_id).all()
    strategies = db.query(StrategyPerformance).filter(StrategyPerformance.tenant_id == current_user.tenant_id).all()
    negatives = db.query(NegativePatternMemory).filter(NegativePatternMemory.tenant_id == current_user.tenant_id).all()
    completed = [d for d in decisions if d.result_status is not None]
    successes = [d for d in completed if d.result_status == "success"]
    return {
        "total_decisions": len(decisions),
        "evaluated_decisions": len(completed),
        "overall_success_rate": round(len(successes) / len(completed), 3) if completed else 0.0,
        "strategies_tracked": len(strategies),
        "negative_patterns_count": len(negatives),
    }


@router.get("/strategies")
def list_strategies(
    current_user: User = Depends(require_permission(Resource.LEARNING, Action.READ)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(StrategyPerformance)
        .filter(StrategyPerformance.tenant_id == current_user.tenant_id)
        .order_by(StrategyPerformance.weighted_reward_score.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "agent_name": s.agent_name,
            "task_type": s.task_type,
            "strategy_name": s.strategy_name,
            "success_count": s.success_count,
            "failure_count": s.failure_count,
            "weighted_reward_score": round(s.weighted_reward_score, 2),
            "rolling_success_rate": round(s.rolling_success_rate, 3),
            "recent_trend_score": round(s.recent_trend_score, 2),
        }
        for s in rows
    ]


@router.post("/decisions")
def record_decision(
    payload: RecordDecisionRequest,
    current_user: User = Depends(require_permission(Resource.LEARNING, Action.EXECUTE)),
    db: Session = Depends(get_db),
):
    loop = LearningLoop(db, current_user.tenant_id)
    rec = loop.record_decision(**payload.model_dump())
    return {"id": rec.id, "agent_name": rec.agent_name, "strategy_used": rec.strategy_used}


@router.post("/outcomes")
def record_outcome(
    payload: RecordOutcomeRequest,
    current_user: User = Depends(require_permission(Resource.LEARNING, Action.UPDATE)),
    db: Session = Depends(get_db),
):
    loop = LearningLoop(db, current_user.tenant_id)
    rec = loop.record_outcome(**payload.model_dump())
    if not rec:
        raise HTTPException(status_code=404, detail="Decision record not found.")
    return {"id": rec.id, "result_status": rec.result_status, "quality_score": rec.quality_score}

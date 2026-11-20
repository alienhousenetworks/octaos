from datetime import datetime, timezone
import random
from typing import Any, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.learning.models import DecisionRecord, NegativePatternMemory, StrategyPerformance


class LearningLoop:
    """Central closed-loop evaluation & strategy optimization engine."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def get_strategy_context(self, agent_name: str, task_type: str) -> dict[str, Any]:
        strategies = (
            self.db.query(StrategyPerformance)
            .filter(
                StrategyPerformance.tenant_id == self.tenant_id,
                StrategyPerformance.agent_name == agent_name,
                StrategyPerformance.task_type == task_type,
            )
            .order_by(desc(StrategyPerformance.weighted_reward_score))
            .all()
        )
        negatives = (
            self.db.query(NegativePatternMemory)
            .filter(
                NegativePatternMemory.tenant_id == self.tenant_id,
                NegativePatternMemory.agent_name == agent_name,
                NegativePatternMemory.task_type == task_type,
            )
            .limit(5)
            .all()
        )
        if not strategies:
            return {
                "mode": "EXPLORATION",
                "selected_strategy": "evidence_first_v1",
                "top_strategies": [],
                "avoid_patterns": [n.pattern_signature for n in negatives],
            }

        top = strategies[:3]
        bottom = strategies[-2:] if len(strategies) > 3 else []
        if random.random() < 0.20:
            safe = [s for s in strategies if s not in bottom] or strategies
            chosen = random.choice(safe).strategy_name
            mode = "EXPLORATION"
        else:
            chosen = top[0].strategy_name
            mode = "EXPLOITATION"

        return {
            "mode": mode,
            "selected_strategy": chosen,
            "top_strategies": [
                {"name": s.strategy_name, "reward": round(s.weighted_reward_score, 3), "success_rate": round(s.rolling_success_rate, 3)}
                for s in top
            ],
            "avoid_patterns": [n.pattern_signature for n in negatives],
        }

    def record_decision(
        self,
        *,
        agent_name: str,
        task_type: str,
        strategy_used: str,
        prompt_version: str = "v1",
        confidence_score: float = 0.7,
        context_features: Optional[dict[str, Any]] = None,
    ) -> DecisionRecord:
        record = DecisionRecord(
            tenant_id=self.tenant_id,
            agent_name=agent_name,
            task_type=task_type,
            strategy_used=strategy_used,
            prompt_version=prompt_version,
            confidence_score=confidence_score,
            context_features=context_features or {},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def record_outcome(
        self,
        *,
        decision_id: str,
        result_status: str,
        quality_score: Optional[float] = None,
        user_feedback_score: Optional[float] = None,
        behavioral_signals: Optional[dict[str, Any]] = None,
        failure_category: Optional[str] = None,
    ) -> Optional[DecisionRecord]:
        decision = (
            self.db.query(DecisionRecord)
            .filter(DecisionRecord.id == decision_id, DecisionRecord.tenant_id == self.tenant_id)
            .first()
        )
        if not decision:
            return None

        decision.result_status = result_status
        decision.quality_score = quality_score
        decision.user_feedback_score = user_feedback_score
        decision.behavioral_signals = behavioral_signals or {}
        decision.outcome_timestamp = datetime.now(timezone.utc)

        # Compute normalized reward [0..100]
        base = 85.0 if result_status == "success" else (50.0 if result_status == "partial" else 15.0)
        if quality_score is not None:
            base = (base + float(quality_score)) / 2.0
        if user_feedback_score is not None:
            base = (base + float(user_feedback_score)) / 2.0

        perf = (
            self.db.query(StrategyPerformance)
            .filter(
                StrategyPerformance.tenant_id == self.tenant_id,
                StrategyPerformance.agent_name == decision.agent_name,
                StrategyPerformance.task_type == decision.task_type,
                StrategyPerformance.strategy_name == decision.strategy_used,
            )
            .first()
        )
        if not perf:
            perf = StrategyPerformance(
                tenant_id=self.tenant_id,
                agent_name=decision.agent_name,
                task_type=decision.task_type,
                strategy_name=decision.strategy_used,
                success_count=0,
                failure_count=0,
                weighted_reward_score=base,
                rolling_success_rate=1.0 if result_status == "success" else 0.0,
                recent_trend_score=0.0,
            )
            self.db.add(perf)
        else:
            alpha = 0.3
            prev = perf.weighted_reward_score
            perf.weighted_reward_score = (1 - alpha) * prev + alpha * base
            perf.recent_trend_score = perf.weighted_reward_score - prev

        if result_status == "success":
            perf.success_count += 1
        else:
            perf.failure_count += 1
            if failure_category:
                self.db.add(
                    NegativePatternMemory(
                        tenant_id=self.tenant_id,
                        agent_name=decision.agent_name,
                        task_type=decision.task_type,
                        failure_reason_category=failure_category,
                        pattern_signature=f"strategy={decision.strategy_used}",
                    )
                )

        total = perf.success_count + perf.failure_count
        perf.rolling_success_rate = (perf.success_count / total) if total > 0 else 0.0

        self.db.commit()
        self.db.refresh(decision)
        return decision

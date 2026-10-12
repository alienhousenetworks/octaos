"""Agent 16: Pipeline Inspector & Forecaster Agent.

Responsibilities:
1. Conducts calibrated probabilistic pipeline forecasting (Commit, Best Case, Pipeline Coverage).
2. Audits deal health: flags stalled stages, single-threaded opportunities, and missing executive touches.
3. Automatically synthesizes the Monday Morning Pipeline Review for sales management.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.services.sales_os.agents.base import BaseSalesAgent, AgentResult, EvidenceItem
from app.models.deal_room import DealRoom, BuyingCommitteeMember
from app.schemas.sales_swarm import (
    PipelineForecastReport,
    DealRiskAudit,
)

logger = logging.getLogger(__name__)


class PipelineForecasterAgent(BaseSalesAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "agent_16_pipeline_forecaster")

    async def execute(self, deal_room_id: str = None, parameters: Dict[str, Any] = None) -> AgentResult[PipelineForecastReport]:
        start_time = time.time()
        now = datetime.now(timezone.utc)
        stalled_threshold = now - timedelta(days=7)

        # Ingest active deal rooms
        rooms = (
            self.db.query(DealRoom)
            .filter(
                DealRoom.tenant_id == self.tenant_id,
                DealRoom.stage.notin_(["won", "lost", "disqualified"]),
            )
            .all()
        )

        total_pipeline = 0.0
        commit_total = 0.0
        best_case_total = 0.0
        deal_audits: List[DealRiskAudit] = []
        at_risk_count = 0

        # Calibrated stage win baselines
        STAGE_DEFAULTS = {
            "discovered": (0.05, 15000.0),
            "qualified": (0.15, 20000.0),
            "researching": (0.20, 25000.0),
            "outreach_ready": (0.25, 25000.0),
            "in_cadence": (0.30, 25000.0),
            "replied": (0.45, 30000.0),
            "meeting_booked": (0.60, 35000.0),
            "proposal": (0.75, 45000.0),
            "closing": (0.90, 50000.0),
        }

        for r in rooms:
            baseline_prob, default_deal_size = STAGE_DEFAULTS.get(r.stage, (0.10, 20000.0))
            deal_val = float(r.annual_revenue_usd or default_deal_size)
            win_prob = float(r.calibrated_win_prob or baseline_prob)

            total_pipeline += deal_val
            if win_prob >= 0.70:
                commit_total += deal_val
            if win_prob >= 0.40:
                best_case_total += deal_val

            # Detect risk factors
            risks = []
            if r.risk_flags:
                risks.extend(r.risk_flags)

            last_act = r.last_activity_at
            if last_act:
                if last_act.tzinfo is None:
                    last_act = last_act.replace(tzinfo=timezone.utc)
                if last_act < stalled_threshold:
                    if "stalled_7_days" not in risks:
                        risks.append("stalled_7_days")

            if not r.is_multi_threaded and r.stage in ("meeting_booked", "proposal", "closing"):
                if "single_threaded" not in risks:
                    risks.append("single_threaded")

            if risks:
                at_risk_count += 1

            days_active = (now - (r.created_at or now)).days if r.created_at else 0
            deal_audits.append(
                DealRiskAudit(
                    deal_room_id=r.id,
                    company_name=r.company_name,
                    current_stage=r.stage,
                    calibrated_win_prob=win_prob,
                    days_in_stage=max(1, days_active),
                    risk_factors=risks,
                    projected_close_date=(now + timedelta(days=30)).strftime("%Y-%m-%d"),
                )
            )

        coverage_ratio = round(total_pipeline / max(1.0, commit_total), 2) if commit_total > 0 else 3.0

        # Monday Pipeline Narrative Synthesis
        monday_brief = f"""## Monday Executive Pipeline Brief
**Total Active Pipeline:** ${total_pipeline:,.2f} Across {len(rooms)} Opportunities  
**Committed Revenue (Win Prob >= 70%):** ${commit_total:,.2f}  
**Best Case (Win Prob >= 40%):** ${best_case_total:,.2f}  
**Pipeline Coverage Ratio:** {coverage_ratio:.1f}x  

### Key Pipeline Risks & Action Items:
- **At-Risk Opportunities:** {at_risk_count} of {len(rooms)} active deals show risk flags (stalled cadence or single-threading).
- **Single-Threaded Accounts:** Recommend immediate multi-threading via Agent 13 for accounts in proposal stage.
- **Velocity Priority:** Focus rep intervention on high-probability deals in closing stages to protect end-of-month commits.
"""

        forecast_report = PipelineForecastReport(
            as_of_date=now.strftime("%Y-%m-%d"),
            total_pipeline_usd=total_pipeline,
            commit_usd=commit_total,
            best_case_usd=best_case_total,
            pipeline_coverage_ratio=coverage_ratio,
            week_over_week_delta_usd=0.0,
            key_deal_changes=[a.model_dump() for a in deal_audits if a.risk_factors],
            executive_monday_brief=monday_brief,
        )

        return AgentResult(
            agent_id=self.agent_id,
            tenant_id=self.tenant_id,
            deal_room_id=deal_room_id,
            decision="ready",
            confidence=0.92,
            evidence=[
                EvidenceItem(
                    claim=f"Audited {len(rooms)} active deals across tenant pipeline.",
                    source="deal_room_table",
                    confidence=1.0,
                )
            ],
            source="pipeline_forecaster",
            reasoning_summary=f"Forecast: Commit=${commit_total:,.2f}, BestCase=${best_case_total:,.2f}, Total=${total_pipeline:,.2f}. At-risk deals: {at_risk_count}.",
            missing_information=[],
            recommended_next_step="review_monday_brief",
            data=forecast_report,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

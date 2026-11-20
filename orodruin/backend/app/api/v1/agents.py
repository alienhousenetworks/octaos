from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.business.models import WorkflowRun
from app.core.inference.service import InferenceService
from app.core.permissions.rbac import Action, Resource, require_permission
from app.core.tenancy.models import User
from app.db import get_db
from app.intelligence.service import IntelligenceEngine
from app.learning.service import LearningLoop

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentExecuteRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    company_name: Optional[str] = None
    topic: Optional[str] = None
    region: Optional[str] = None


@router.get("/ai-config")
def get_fixed_ai_config(
    current_user: User = Depends(require_permission(Resource.AGENTS, Action.READ)),
):
    """Read-only view of the fixed local-first AI configuration (Model Manager UI removed)."""
    return InferenceService().config_summary()


@router.post("/execute")
async def execute_agent_goal(
    payload: AgentExecuteRequest,
    current_user: User = Depends(require_permission(Resource.AGENTS, Action.EXECUTE)),
    db: Session = Depends(get_db),
):
    """Unified intelligence -> leads -> strategy -> learning orchestration loop."""
    loop = LearningLoop(db, current_user.tenant_id)
    strategy_ctx = loop.get_strategy_context("orchestrator", "intelligence_to_strategy")
    decision = loop.record_decision(
        agent_name="orchestrator",
        task_type="intelligence_to_strategy",
        strategy_used=strategy_ctx["selected_strategy"],
        context_features={"topic": payload.topic, "region": payload.region},
    )

    intel = IntelligenceEngine(db, current_user.tenant_id)
    company_name = payload.company_name or payload.topic or "Target Market"
    profile = await intel.research_company(name=company_name, country=payload.region)
    leads = await intel.discover_leads(
        topic=payload.topic or payload.goal,
        region=payload.region,
        company_profile_id=profile.id,
        count=3,
    )
    brief = await intel.generate_strategy_brief(
        title=f"Strategy: {company_name}",
        company_profile_id=profile.id,
        topic=payload.topic or payload.goal,
    )

    wf = WorkflowRun(
        tenant_id=current_user.tenant_id,
        name=f"Auto-Orchestration: {company_name}",
        status="completed",
        steps_json=["research_company", "discover_leads", "generate_strategy_brief"],
        output_json={"company_id": profile.id, "lead_count": len(leads), "strategy_id": brief.id},
    )
    db.add(wf)
    db.commit()

    loop.record_outcome(
        decision_id=decision.id,
        result_status="success",
        quality_score=82.0,
        behavioral_signals={"leads_found": len(leads), "strategy_created": True},
    )

    return {
        "decision_id": decision.id,
        "strategy_mode": strategy_ctx["mode"],
        "company": {"id": profile.id, "name": profile.name, "summary": profile.summary},
        "leads_discovered": len(leads),
        "strategy_brief": {
            "id": brief.id,
            "title": brief.title,
            "sales_strategy": brief.sales_strategy,
            "marketing_strategy": brief.marketing_strategy,
        },
    }

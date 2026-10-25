from fastapi import APIRouter, HTTPException, Depends
from app.api.deps import get_current_user
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.octa_orchestrator.orchestrator.manager import AIManagerOrchestrator
from app.octa_orchestrator.telemetry.proxy import router as telemetry_router

router = APIRouter(prefix="/orchestrator", tags=["AI Manager Orchestrator"])
router.include_router(telemetry_router)

class ExecuteGoalRequest(BaseModel):
    goal: str
    risk_level: Optional[str] = "NORMAL"

@router.post("/execute")
async def execute_manager_goal(payload: ExecuteGoalRequest, current_user=Depends(get_current_user)):
    """
    Triggers the AI Executive Manager to decompose goals into a DAG task graph,
    route tasks dynamically to SLMs/Frontier models, enforce quality gates, and deliver high ROI outcomes.
    """
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="Goal prompt cannot be empty.")
        
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="An active tenant is required for orchestration.")

    user_context = {
        "user_id": str(current_user.id),
        "tenant_id": str(tenant_id),
        "role": getattr(current_user, "role", "user"),
        "is_superuser": bool(getattr(current_user, "is_system_admin", False)),
        "is_system_admin": bool(getattr(current_user, "is_system_admin", False)),
        "allowed_sections": getattr(current_user, "allowed_sections", None),
    }
    manager = AIManagerOrchestrator(
        tenant_id=str(tenant_id),
        user_context=user_context,
    )
    try:
        result = await manager.execute_goal(payload.goal, payload.risk_level)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Orchestration failed. Check the run logs for a redacted diagnostic reference.")

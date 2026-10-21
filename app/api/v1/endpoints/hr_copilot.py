"""
Universal HR Copilot API Endpoints.
Coordinates conversational multi-agent dialogue, task planning, and human-in-the-loop approvals.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.api import deps
from app.models.base import User
from app.services.agents.hr.schemas import CopilotChatRequest, CopilotChatResponse
from app.services.agents.hr.orchestrator import HREnterpriseOrchestrator
from app.services.agents.hr.approval_bridge import HRApprovalBridge
from app.services.agents.hr.schemas import RiskTier

router = APIRouter()


class SubmitApprovalPayload(BaseModel):
    action_type: str
    title: str
    resource_id: Optional[str] = None
    payload: Dict[str, Any]
    rationale: str
    risk_tier: str = "R3"


@router.post("/chat", response_model=CopilotChatResponse)
async def chat_with_hr_copilot(
    request: CopilotChatRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Primary conversational agent interface for all 16 HR submodules.
    Retrieves authorized context, classifies intents, and returns evidence-backed responses.
    """
    orchestrator = HREnterpriseOrchestrator(db, tenant_id, current_user.id)
    return await orchestrator.handle_message(request)


@router.post("/actions/submit-approval")
def submit_action_for_approval(
    payload: SubmitApprovalPayload,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Binds an agent-proposed action into the OctaOS Enterprise Approvals queue
    with cryptographic SHA-256 integrity verification.
    """
    bridge = HRApprovalBridge(db, tenant_id)
    risk_tier = RiskTier(payload.risk_tier) if payload.risk_tier in [r.value for r in RiskTier] else RiskTier.R3_MATERIAL

    approval_req = bridge.submit_for_approval(
        action_type=payload.action_type,
        title=payload.title,
        resource_id=payload.resource_id,
        payload=payload.payload,
        rationale=payload.rationale,
        requested_by=current_user.id,
        risk_tier=risk_tier
    )

    return {
        "approval_request_id": approval_req.id,
        "action_type": approval_req.action_type,
        "status": approval_req.status,
        "message": f"Action successfully queued for executive approval under ticket #{approval_req.id[:8]}."
    }

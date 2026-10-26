"""Adapter that maps OctaOS's existing AI gateway onto the common agent contract."""
from __future__ import annotations

from app.services.ai_gateway import ai_gateway
from app.services.agent_runtime.protocol import AgentOutcome, AgentRequest


class AIGatewayAgentAdapter:
    """Provider-neutral adapter around the existing tenant-aware AI gateway.

    The gateway may fail over internally and currently returns text only. Therefore
    the adapter reports the requested provider/model as routing intent, not verified
    actual-provider telemetry; actual usage must come from the gateway's usage ledger.
    """

    provider_name = "octaos-ai-gateway"

    def __init__(self, db, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def execute(self, request: AgentRequest) -> AgentOutcome:
        if request.tenant_id != self.tenant_id:
            raise PermissionError("TENANT_MISMATCH")
        output = await ai_gateway.executeRequest(
            db=self.db,
            tenant_id=self.tenant_id,
            prompt=request.goal,
            provider=request.provider,
            model=request.model,
            system_prompt=request.system_prompt,
            task_type=request.task_type,
        )
        if not isinstance(output, str):
            raise TypeError("AI gateway returned a non-text result for a text agent request.")
        return AgentOutcome(
            status="completed" if output.strip() else "failed",
            output=output if output.strip() else None,
            provider=request.provider or "gateway-routed",
            model=request.model or "gateway-routed",
            input_tokens=max(0, len(request.goal + (request.system_prompt or "")) // 4),
            output_tokens=max(0, len(output) // 4),
        )

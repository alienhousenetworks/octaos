"""Adapter that maps OctaOS's existing AI gateway onto the common agent contract."""
from __future__ import annotations

from app.services.ai_gateway import ai_gateway
from app.services.agent_runtime.protocol import AgentOutcome, AgentRequest


class AIGatewayAgentAdapter:
    """Provider-neutral adapter around the existing tenant-aware AI gateway.

    The gateway still returns text, but its usage callback supplies the provider/model
    that actually succeeded plus measured tokens and cost. If no usage callback is emitted,
    provider/model fall back to routing intent and token/cost metrics remain unavailable.
    """

    provider_name = "octaos-ai-gateway"

    def __init__(self, db, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def execute(self, request: AgentRequest) -> AgentOutcome:
        if request.tenant_id != self.tenant_id:
            raise PermissionError("TENANT_MISMATCH")
        usage: dict[str, object] = {}

        def capture_usage(record: dict[str, object]) -> None:
            usage.update(record)

        output = await ai_gateway.executeRequest(
            db=self.db,
            tenant_id=self.tenant_id,
            prompt=request.goal,
            provider=request.provider,
            model=request.model,
            system_prompt=request.system_prompt,
            task_type=request.task_type,
            usage_callback=capture_usage,
            allowed_providers=list(request.allowed_providers) or None,
        )
        if not isinstance(output, str):
            raise TypeError("AI gateway returned a non-text result for a text agent request.")
        return AgentOutcome(
            status="completed" if output.strip() else "failed",
            output=output if output.strip() else None,
            provider=str(usage.get("provider") or request.provider or "gateway-routed"),
            model=str(usage.get("model") or request.model or "gateway-routed"),
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cost=float(usage["cost_usd"]) if usage.get("cost_usd") is not None else None,
        )

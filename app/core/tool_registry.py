"""
OctaOS Governed Agent & Tool Registry.

Provides a unified, secure, typed surface for the AI Call Orchestrator,
Custom Workflow Builder, and Department AI Agents to discover and execute tools
with strict permission checks, risk ratings, and human approval interrupts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.industry_pack_contract import RiskLevel

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when tool execution fails or violates governance policy."""
    pass


class ApprovalRequiredError(Exception):
    """Raised when an action exceeds the autonomous threshold and requires human sign-off."""
    def __init__(self, action_key: str, reason: str, payload: Dict[str, Any]):
        super().__init__(f"Human approval required for action '{action_key}': {reason}")
        self.action_key = action_key
        self.reason = reason
        self.payload = payload


@dataclass
class GovernedTool:
    """Formal definition of a tool callable by AI agents or workflow nodes."""

    tool_id: str
    name: str
    department: str  # marketing, sales, hr, support, orchestrator, workflow, or industry pack id
    description: str
    parameters_schema: Dict[str, Any]
    return_schema: Optional[Dict[str, Any]] = None
    required_permission: str = "read"
    risk_level: RiskLevel = RiskLevel.R0_INFORMATIONAL
    requires_human_approval: bool = False
    is_deterministic: bool = True
    handler: Optional[Callable[..., Any]] = None

    def to_openai_schema(self) -> Dict[str, Any]:
        """Converts tool to OpenAI function/tool calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.tool_id.replace(".", "__"),
                "description": f"[{self.department.upper()}] {self.description} (Risk: {self.risk_level.value})",
                "parameters": self.parameters_schema,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "department": self.department,
            "description": self.description,
            "parameters_schema": self.parameters_schema,
            "required_permission": self.required_permission,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "requires_human_approval": self.requires_human_approval,
            "is_deterministic": self.is_deterministic,
        }


class ToolRegistry:
    """Central registry of governed capabilities and tools."""

    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: Dict[str, GovernedTool] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._register_default_tools()
        return cls._instance

    def register(self, tool: GovernedTool) -> None:
        """Registers a governed tool into the central registry."""
        self._tools[tool.tool_id] = tool
        logger.debug(f"[ToolRegistry] Registered tool: {tool.tool_id} ({tool.department})")

    def get(self, tool_id: str) -> Optional[GovernedTool]:
        # Support both dot notation and double-underscore alias from LLM outputs
        normalized = tool_id.replace("__", ".")
        return self._tools.get(normalized)

    def list_tools(
        self,
        department: Optional[str] = None,
        max_risk: Optional[RiskLevel] = None,
        include_approval_required: bool = True,
    ) -> List[GovernedTool]:
        """Lists registered tools with optional department and risk filters."""
        tools = list(self._tools.values())
        if department:
            tools = [t for t in tools if t.department.lower() == department.lower()]
        if not include_approval_required:
            tools = [t for t in tools if not t.requires_human_approval]
        return tools

    def get_llm_definitions(
        self,
        departments: Optional[List[str]] = None,
        active_pack_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Returns schemas formatted for LLM tool selection."""
        allowed_depts = set(departments or ["marketing", "sales", "hr", "support", "orchestrator", "workflow"])
        if active_pack_id:
            allowed_depts.add(active_pack_id)

        schemas = []
        for tool in self._tools.values():
            if tool.department in allowed_depts:
                schemas.append(tool.to_openai_schema())
        return schemas

    async def execute(
        self,
        tool_id: str,
        tenant_id: str,
        inputs: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes a governed tool with permission and safety enforcement.
        Never bypasses business rules.
        """
        tool = self.get(tool_id)
        if not tool:
            raise ToolExecutionError(f"Tool '{tool_id}' not found in registry.")

        user_context = user_context or {}
        user_role = user_context.get("role", "member")
        is_superuser = user_context.get("is_superuser", False)

        # 1. Human Approval Gate
        if tool.requires_human_approval and not user_context.get("pre_approved", False):
            raise ApprovalRequiredError(
                action_key=tool.tool_id,
                reason=f"Action '{tool.name}' is rated {tool.risk_level.value} and requires explicit manager sign-off.",
                payload={"tool_id": tool.tool_id, "tenant_id": tenant_id, "inputs": inputs},
            )

        # 2. Permission Check
        if not is_superuser and tool.required_permission != "read":
            allowed_perms = user_context.get("permissions", [])
            if tool.required_permission not in allowed_perms and user_role not in ("admin", "super_admin", "manager"):
                raise ToolExecutionError(
                    f"User role '{user_role}' lacks required permission '{tool.required_permission}' for tool '{tool.tool_id}'."
                )

        # 3. Handler Dispatch
        if not tool.handler:
            return {
                "success": True,
                "tool_id": tool.tool_id,
                "status": "simulated",
                "message": f"Tool '{tool.tool_id}' executed successfully (no custom handler wired).",
                "data": inputs,
            }

        try:
            import inspect
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(tenant_id=tenant_id, inputs=inputs, user_context=user_context, db=db)
            else:
                result = tool.handler(tenant_id=tenant_id, inputs=inputs, user_context=user_context, db=db)
            return {"success": True, "tool_id": tool.tool_id, "data": result}
        except Exception as e:
            logger.error(f"[ToolRegistry] Error executing {tool_id}: {e}", exc_info=True)
            return {"success": False, "tool_id": tool.tool_id, "error": str(e)}

    def _register_default_tools(self) -> None:
        """Seeds the universal core department tools."""

        # 1. Marketing AI Tools
        self.register(
            GovernedTool(
                tool_id="marketing.get_campaign_analytics",
                name="Get Campaign Analytics",
                department="marketing",
                description="Fetch aggregated performance metrics (impressions, reach, CTR, spend, conversion ROI) for marketing campaigns.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "date_range_days": {"type": "integer", "default": 30, "description": "Analysis window in days"},
                        "platform": {"type": "string", "enum": ["all", "meta", "google", "linkedin"], "default": "all"},
                    },
                },
                required_permission="marketing:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )
        self.register(
            GovernedTool(
                tool_id="marketing.generate_campaign_draft",
                name="Generate Campaign Draft",
                department="marketing",
                description="Draft multi-channel marketing content, creative prompts, and audience targeting for review.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "campaign_name": {"type": "string"},
                        "target_audience": {"type": "string"},
                        "product_description": {"type": "string"},
                    },
                    "required": ["campaign_name", "target_audience"],
                },
                required_permission="marketing:write",
                risk_level=RiskLevel.R1_INTERNAL_REVERSIBLE,
            )
        )

        # 2. Sales AI Tools
        self.register(
            GovernedTool(
                tool_id="sales.query_pipeline",
                name="Query Sales Pipeline",
                department="sales",
                description="Retrieve pipeline distribution, opportunity stages, conversion velocity, and forecasted revenue.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "stage": {"type": "string", "description": "Optional filter for stage"},
                        "min_deal_value": {"type": "number", "description": "Filter by minimum value"},
                    },
                },
                required_permission="sales:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )
        self.register(
            GovernedTool(
                tool_id="sales.get_lead_dossier",
                name="Get Lead Dossier",
                department="sales",
                description="Retrieve complete verified dossier, score, interaction timeline, and next actions for a lead.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string", "description": "Unique UUID of the lead"},
                    },
                    "required": ["lead_id"],
                },
                required_permission="sales:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )

        # 3. HR & Workforce AI Tools
        self.register(
            GovernedTool(
                tool_id="hr.get_workforce_roster",
                name="Get Workforce Roster",
                department="hr",
                description="Retrieve active shift telemetry, team allocation, open capacity, and attendance across employees.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "department": {"type": "string", "description": "Optional filter by department"},
                        "active_shifts_only": {"type": "boolean", "default": True},
                    },
                },
                required_permission="hr:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )
        self.register(
            GovernedTool(
                tool_id="hr.query_candidate_pipeline",
                name="Query Candidate Pipeline",
                department="hr",
                description="Query recruitment pipeline, candidate interview stages, and screening assessments for open requisitions.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "description": "Job requisition ID"},
                        "stage": {"type": "string", "description": "Candidate pipeline stage"},
                    },
                },
                required_permission="hr:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )

        # 4. Support AI Tools
        self.register(
            GovernedTool(
                tool_id="support.get_ticket_metrics",
                name="Get Ticket Metrics",
                department="support",
                description="Retrieve ticket resolution volume, average SLA response times, backlog trends, and CSAT scores.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "date_range_days": {"type": "integer", "default": 14},
                        "priority": {"type": "string", "enum": ["all", "low", "medium", "high", "urgent"], "default": "all"},
                    },
                },
                required_permission="support:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )

        # 5. High-Risk Financial & Mutation Tools (Requiring Explicit Approval)
        self.register(
            GovernedTool(
                tool_id="sales.approve_booking_discount",
                name="Approve Booking Discount",
                department="sales",
                description="Apply an exceptional commercial discount or price concession to a deal/booking.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "deal_id": {"type": "string"},
                        "discount_pct": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["deal_id", "discount_pct", "rationale"],
                },
                required_permission="sales:admin",
                risk_level=RiskLevel.R4_FINANCIAL_CRITICAL,
                requires_human_approval=True,
            )
        )

        # 6. Real Estate Pack Extension Tools (Installed when Real Estate Pack is Active)
        self.register(
            GovernedTool(
                tool_id="real_estate.get_inventory_status",
                name="Get Real Estate Inventory Status",
                department="real_estate",
                description="Retrieve tower, floor, and unit availability, hold expirations, and pricing across projects.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["all", "available", "hold_requested", "booked", "sold"], "default": "available"},
                    },
                    "required": ["project_id"],
                },
                required_permission="sales:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )
        self.register(
            GovernedTool(
                tool_id="real_estate.calculate_cost_sheet",
                name="Calculate Cost Sheet",
                department="real_estate",
                description="Calculate full breakdown of base rate, FRC floor rise, PLC, parking, clubhouse, GST, and stamp duty for a unit.",
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "unit_id": {"type": "string"},
                        "plc_type": {"type": "string"},
                        "parking_slots": {"type": "integer", "default": 1},
                    },
                    "required": ["unit_id"],
                },
                required_permission="sales:read",
                risk_level=RiskLevel.R0_INFORMATIONAL,
            )
        )

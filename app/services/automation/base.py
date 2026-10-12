"""
Enterprise Automation Engine Abstraction Layer.
Defines canonical OctaOS Intermediate Representation (IR), engine adapter contracts,
and execution observability models.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EngineType(str, Enum):
    ACTIVEPIECES = "activepieces"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    ARCHIVED = "archived"


class FailureClassification(str, Enum):
    USER_CONFIGURATION = "user_configuration"      # e.g., expired OAuth token, missing required field
    WORKFLOW_LOGIC = "workflow_logic"              # e.g., invalid data mapping or division by zero in code
    EXTERNAL_SERVICE = "external_service"          # e.g., HubSpot 503, Slack rate limit
    PLATFORM_RUNTIME = "platform_runtime"          # e.g., Activepieces container timeout
    SECURITY_POLICY = "security_policy"            # e.g., Action blocked by enterprise governance
    QUOTA_EXCEEDED = "quota_exceeded"              # e.g., Monthly execution quota exhausted


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ─────────────────────────────────────────────────────────────────────────────
# Canonical OctaOS Automation Intermediate Representation (IR)
# ─────────────────────────────────────────────────────────────────────────────

class TriggerIR(BaseModel):
    type: str = Field(..., description="octaos_event | webhook | schedule | manual")
    event: Optional[str] = Field(None, description="OctaOS event name, e.g. lead.qualified, ticket.escalated")
    config: Dict[str, Any] = Field(default_factory=dict, description="Filter rules, cron expression, etc.")
    display_name: Optional[str] = None


class StepIR(BaseModel):
    id: str = Field(..., description="Unique step identifier within the flow")
    type: str = Field("action", description="action | condition | loop | agent_delegate")
    piece: str = Field(..., description="Piece identifier, e.g. slack, hubspot, gmail, google_sheets, octaos")
    action: str = Field(..., description="Action name, e.g. send_message, create_deal, trigger_agent")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Input parameters and mapping expressions")
    next_step_id: Optional[str] = None
    on_failure: str = Field("stop", description="stop | continue | retry")
    display_name: Optional[str] = None


class AutomationIR(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    category: str = "operations"
    trigger: TriggerIR
    steps: List[StepIR] = Field(default_factory=list)
    required_connections: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionResultIR(BaseModel):
    id: str
    external_execution_id: Optional[str] = None
    status: str  # running, succeeded, failed, retrying, cancelled
    failure_classification: Optional[FailureClassification] = None
    failure_reason: Optional[str] = None
    duration_ms: int = 0
    trigger_context: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ConnectionStatusIR(BaseModel):
    piece_name: str
    display_name: str
    status: str  # connected | expired | disconnected
    account_name: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    last_verified_at: Optional[str] = None


class TenantWorkspaceInfo(BaseModel):
    tenant_id: str
    engine_type: EngineType
    workspace_url: str
    subdomain: str
    status: str
    master_key_configured: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Automation Engine Adapter Interface
# ─────────────────────────────────────────────────────────────────────────────

class AutomationEngineAdapter(ABC):
    """
    Abstract contract for automation engines.
    Isolates OctaOS business logic and AI layer from specific engine quirks.
    """

    @property
    @abstractmethod
    def engine_type(self) -> EngineType:
        """Returns the engine type."""
        pass

    @abstractmethod
    async def provision_tenant_workspace(self, tenant_id: str, subdomain: str) -> TenantWorkspaceInfo:
        """Provision or ensure an isolated workspace exists for this tenant."""
        pass

    @abstractmethod
    async def compile_and_deploy_workflow(
        self,
        tenant_id: str,
        workflow_ir: AutomationIR,
        previous_external_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compiles the OctaOS IR into engine format and deploys/registers the workflow.
        Returns {'external_id': str, 'compiled_schema': dict, 'webhook_url': Optional[str]}.
        """
        pass

    @abstractmethod
    async def activate_workflow(self, tenant_id: str, external_id: str, active: bool) -> bool:
        """Enables or pauses the workflow execution inside the engine."""
        pass

    @abstractmethod
    async def trigger_workflow_manually(
        self,
        tenant_id: str,
        external_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Manually runs an execution for testing or forced triggering."""
        pass

    @abstractmethod
    async def get_workflow_editor_url(
        self,
        tenant_id: str,
        external_id: str,
        user_email: str,
    ) -> str:
        """
        Generates a secure, authenticated URL for visual canvas editing in OctaOS.
        """
        pass

    @abstractmethod
    async def fetch_executions(
        self,
        tenant_id: str,
        external_id: str,
        limit: int = 10,
    ) -> List[ExecutionResultIR]:
        """Fetches execution logs and categorizes failures."""
        pass

    @abstractmethod
    async def list_connections(self, tenant_id: str) -> List[ConnectionStatusIR]:
        """Discovers connection health for the tenant without leaking raw tokens."""
        pass

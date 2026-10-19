"""Agent contract schema. Prompts, policy, and output schemas are separate fields."""
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LifecycleStatus(str, Enum):
    draft = "draft"
    testing = "testing"
    active = "active"
    deprecated = "deprecated"
    disabled = "disabled"


class PromptRecord(BaseModel):
    prompt_id: str
    version: str
    template: str


class DataPermissions(BaseModel):
    reads: list[str] = Field(default_factory=list)
    writes: list[str] = Field(default_factory=list)


class ToolPermissions(BaseModel):
    allowed: list[str] = Field(default_factory=list)
    external_actions: bool = False


class EvidenceRequirements(BaseModel):
    factual_claims_require_evidence: bool = True
    distinguish_fact_from_inference: bool = True
    allow_unknowns: bool = True


class TimeoutRetry(BaseModel):
    timeout_seconds: int = 60
    max_attempts: int = 2
    retry_on: list[str] = Field(default_factory=lambda: ["transient_provider_error"])
    no_retry_on: list[str] = Field(default_factory=lambda: ["invalid_input", "policy_denial"])


class IdempotencySpec(BaseModel):
    key_fields: list[str] = Field(default_factory=lambda: ["tenant_id", "input_snapshot_hash", "version"])


class ObservabilitySpec(BaseModel):
    record: list[str] = Field(
        default_factory=lambda: [
            "execution_id",
            "trace_id",
            "prompt_version",
            "model_id",
            "latency_ms",
            "token_usage",
            "cost",
            "validation_result",
        ]
    )


class LlmConfig(BaseModel):
    """Allowed model settings. Named llm_config because Pydantic reserves model_config."""

    provider: str
    model_id: str
    temperature: float = 0.0
    max_tokens: int = 1200
    fallback_policy: str = "fail_closed"


class FailurePolicy(BaseModel):
    missing_evidence: str = "insufficient_evidence"
    invalid_output: str = "reject_and_retry_within_limit"
    exhausted_retries: str = "mark_failed_and_alert"
    unavailable_model: str = "insufficient_evidence"


class AgentContract(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: str
    version: str
    purpose: str
    lifecycle_status: LifecycleStatus
    uses_llm: bool
    system_prompt: Optional[PromptRecord] = None
    prompt_version: Optional[str] = None
    prompt_variables_schema: dict[str, Any] = Field(default_factory=dict)
    task_prompt_template: Optional[PromptRecord] = None
    task_prompts: dict[str, PromptRecord] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    data_permissions: DataPermissions = Field(default_factory=DataPermissions)
    tool_permissions: ToolPermissions = Field(default_factory=ToolPermissions)
    evidence_requirements: EvidenceRequirements = Field(default_factory=EvidenceRequirements)
    policy_requirements: list[str] = Field(default_factory=list)
    timeout_and_retry: TimeoutRetry = Field(default_factory=TimeoutRetry)
    idempotency: IdempotencySpec = Field(default_factory=IdempotencySpec)
    evaluation_suite: list[str] = Field(default_factory=list)
    observability: ObservabilitySpec = Field(default_factory=ObservabilitySpec)
    llm_config: Optional[LlmConfig] = Field(default=None, alias="model_config")
    approval_requirements: list[str] = Field(default_factory=list)
    failure_policy: FailurePolicy = Field(default_factory=FailurePolicy)

    @model_validator(mode="after")
    def prompt_is_explicit(self) -> "AgentContract":
        if self.uses_llm:
            if self.system_prompt is None or not self.system_prompt.template.strip():
                raise ValueError(f"{self.agent_id} uses an LLM and requires system_prompt")
            if self.prompt_version != self.system_prompt.version:
                raise ValueError(f"{self.agent_id} prompt_version must match system_prompt.version")
            if self.task_prompt_template is None and not self.task_prompts:
                raise ValueError(f"{self.agent_id} requires a task prompt")
            if self.llm_config is None:
                raise ValueError(f"{self.agent_id} requires llm_config")
            if self.llm_config.fallback_policy != "fail_closed":
                raise ValueError(f"{self.agent_id} must fail closed when the model is unavailable")
        else:
            if self.system_prompt is not None or self.task_prompt_template is not None or self.task_prompts:
                raise ValueError(f"{self.agent_id} is pure code and cannot carry a prompt")
            if self.llm_config is not None or self.prompt_version is not None:
                raise ValueError(f"{self.agent_id} is pure code and cannot select a model")
        if self.tool_permissions.external_actions and "policy_engine" not in self.policy_requirements:
            raise ValueError(f"{self.agent_id} external actions require the policy engine")
        if self.lifecycle_status == LifecycleStatus.active and not self.evaluation_suite:
            raise ValueError(f"{self.agent_id} cannot be active without an evaluation suite")
        return self

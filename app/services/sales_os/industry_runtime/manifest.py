"""Validated industry pack manifest models and startup validator."""
from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class StageDefinition(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    label: str
    color: str = "#75AFCB"
    is_terminal: bool = False
    terminal_outcome: Literal["won", "lost"] | None = None
    valid_transitions: list[str] = Field(default_factory=list)


class SchemaFieldDefinition(BaseModel):
    key: str
    label: str
    type: Literal["string", "number", "currency", "enum", "boolean", "date", "object", "array"]
    required: bool = False
    options: list[str] | None = None
    default: Any | None = None
    description: str | None = None


class PackCapability(BaseModel):
    id: str
    name: str
    status: CapabilityStatus = CapabilityStatus.NOT_IMPLEMENTED
    module_path: str | None = None
    description: str | None = None


class IndustryPackManifest(BaseModel):
    id: str
    version: str = "1.0.0"
    name: str
    summary: str
    readiness: Literal["production_ready", "representative", "configuration"] = "configuration"
    domain_status: str = "not_built"
    domain_note: str = ""
    terminology: dict[str, str]
    objects: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)
    pipeline_stages: list[StageDefinition] = Field(default_factory=list)
    fields: list[SchemaFieldDefinition] = Field(default_factory=list)
    capabilities: dict[str, PackCapability] = Field(default_factory=dict)
    qualification: list[str] = Field(default_factory=list)
    record_tabs: list[str] = Field(default_factory=lambda: ["Overview", "Qualification", "Activity", "History"])
    ai_guidance: dict[str, list[str]] = Field(default_factory=dict)
    representative: bool = False


def validate_manifest(raw: dict[str, Any]) -> IndustryPackManifest:
    """Validate a raw pack dictionary against the manifest specification."""
    return IndustryPackManifest.model_validate(raw)

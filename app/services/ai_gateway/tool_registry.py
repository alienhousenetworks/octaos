"""
Governed Tool Registry bridge module for ai_gateway.
Re-exports canonical registry from app.core.tool_registry.
"""
from app.core.tool_registry import (
    ToolRegistry,
    GovernedTool,
    ToolExecutionError,
    ApprovalRequiredError,
    RiskLevel,
)

__all__ = [
    "ToolRegistry",
    "GovernedTool",
    "ToolExecutionError",
    "ApprovalRequiredError",
    "RiskLevel",
]

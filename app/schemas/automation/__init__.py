"""Automation schema definitions."""
from app.schemas.automation.graph import (
    AutomationGraph,
    AutomationNode,
    AutomationEdge,
    NodePosition,
    NodePortKind,
    RetryPolicy,
    WorkflowSettings,
    convert_legacy_ir_to_graph,
    convert_graph_to_legacy_ir,
)

__all__ = [
    "AutomationGraph",
    "AutomationNode",
    "AutomationEdge",
    "NodePosition",
    "NodePortKind",
    "RetryPolicy",
    "WorkflowSettings",
    "convert_legacy_ir_to_graph",
    "convert_graph_to_legacy_ir",
]

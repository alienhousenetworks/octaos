"""
Canonical OctaOS Automation Graph Intermediate Representation (IR).
Defines versioned graph topology, typed handles, nodes, edges, retry policies, and workflow settings.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json
import uuid
from pydantic import BaseModel, Field


class NodePortKind(str, Enum):
    TRIGGER = "trigger"
    DATA = "data"
    CONTROL_TRUE = "true"
    CONTROL_FALSE = "false"
    ERROR = "error"
    BRANCH = "branch"


class NodePosition(BaseModel):
    x: float = 0.0
    y: float = 0.0


class RetryPolicy(BaseModel):
    max_attempts: int = 3
    initial_interval_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    retryable_errors: List[str] = Field(
        default_factory=lambda: ["RATE_LIMIT", "TIMEOUT", "503", "502", "NETWORK_ERROR"]
    )


class AutomationNode(BaseModel):
    id: str
    type: str  # trigger | action | condition | switch | merge | mcp_tool | ai_agent | http | code
    name: str
    version: str = "1.0.0"
    position: NodePosition = Field(default_factory=NodePosition)
    tool_id: Optional[str] = None  # e.g., "octaos:lead:qualified" or "mcp:github:create_issue"
    config: Dict[str, Any] = Field(default_factory=dict)
    input_mappings: Dict[str, Any] = Field(default_factory=dict)
    credential_refs: List[str] = Field(default_factory=list)
    retry_policy: Optional[RetryPolicy] = None
    timeout_seconds: int = 120
    is_compensable: bool = False
    requires_approval: bool = False
    display_icon: Optional[str] = None
    description: Optional[str] = None


class AutomationEdge(BaseModel):
    id: str
    source: str
    source_handle: str = "output"
    target: str
    target_handle: str = "input"
    kind: NodePortKind = NodePortKind.DATA
    condition: Optional[Dict[str, Any]] = None  # Branch rule expression


class WorkflowSettings(BaseModel):
    timezone: str = "UTC"
    execution_timeout_seconds: int = 900
    concurrency_limit: int = 5
    error_workflow_id: Optional[str] = None
    idempotency_key_expression: Optional[str] = None


class AutomationGraph(BaseModel):
    schema_version: str = "2.0.0"
    workflow_id: Optional[str] = None
    version: int = 1
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    category: str = "operations"
    nodes: List[AutomationNode] = Field(default_factory=list)
    edges: List[AutomationEdge] = Field(default_factory=list)
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def calculate_hash(self) -> str:
        """Computes a deterministic execution-relevant hash of the graph structure."""
        normalized_nodes = []
        for n in sorted(self.nodes, key=lambda x: x.id):
            normalized_nodes.append({
                "id": n.id,
                "type": n.type,
                "tool_id": n.tool_id,
                "config": n.config,
                "input_mappings": n.input_mappings,
                "retry_policy": n.retry_policy.model_dump() if n.retry_policy else None,
                "timeout_seconds": n.timeout_seconds,
            })

        normalized_edges = []
        for e in sorted(self.edges, key=lambda x: x.id):
            normalized_edges.append({
                "source": e.source,
                "source_handle": e.source_handle,
                "target": e.target,
                "target_handle": e.target_handle,
                "kind": e.kind.value if hasattr(e.kind, "value") else str(e.kind),
                "condition": e.condition,
            })

        payload = {
            "version": self.version,
            "nodes": normalized_nodes,
            "edges": normalized_edges,
            "settings": self.settings.model_dump(),
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def convert_legacy_ir_to_graph(
    ir_dict: Dict[str, Any],
    name: str = "Workflow",
    slug: str = "workflow",
    category: str = "operations",
    workflow_id: Optional[str] = None,
) -> AutomationGraph:
    """
    Seamlessly converts legacy linear AutomationIR (trigger + steps) into a full AutomationGraph
    with automated horizontal layout spacing for visual canvas display.
    """
    if not isinstance(ir_dict, dict):
        ir_dict = {}

    nodes: List[AutomationNode] = []
    edges: List[AutomationEdge] = []

    # 1. Trigger node
    raw_trigger = ir_dict.get("trigger") or {}
    trigger_type = raw_trigger.get("type", "octaos_event")
    trigger_event = raw_trigger.get("event") or raw_trigger.get("trigger_event") or "manual"
    trigger_name = raw_trigger.get("display_name") or f"Trigger: {trigger_event}"

    trigger_id = "node_trigger"
    nodes.append(
        AutomationNode(
            id=trigger_id,
            type="trigger",
            name=trigger_name,
            position=NodePosition(x=100.0, y=200.0),
            tool_id=f"octaos:event:{trigger_event}" if trigger_type == "octaos_event" else f"webhook:{trigger_event}",
            config=raw_trigger.get("config", {}),
            description=f"Initiates workflow on {trigger_event}",
            display_icon="Zap",
        )
    )

    # 2. Sequential steps
    raw_steps = ir_dict.get("steps") or []
    prev_node_id = trigger_id

    for idx, step in enumerate(raw_steps):
        step_id = step.get("id") or f"step_{idx + 1}"
        piece = step.get("piece", "action")
        action = step.get("action", "run")
        display_name = step.get("display_name") or f"{piece.capitalize()}: {action}"
        pos_x = 100.0 + (idx + 1) * 320.0
        pos_y = 200.0

        nodes.append(
            AutomationNode(
                id=step_id,
                type="action",
                name=display_name,
                position=NodePosition(x=pos_x, y=pos_y),
                tool_id=f"{piece}:{action}",
                config=step.get("parameters", {}),
                description=f"Executes {piece} {action}",
                display_icon="Layers",
            )
        )

        edges.append(
            AutomationEdge(
                id=f"edge_{prev_node_id}_to_{step_id}",
                source=prev_node_id,
                source_handle="output",
                target=step_id,
                target_handle="input",
                kind=NodePortKind.DATA,
            )
        )
        prev_node_id = step_id

    wf_name = ir_dict.get("name") or name
    wf_slug = ir_dict.get("slug") or slug
    wf_desc = ir_dict.get("description") or ""
    wf_cat = ir_dict.get("category") or category

    graph = AutomationGraph(
        workflow_id=workflow_id,
        name=wf_name,
        slug=wf_slug,
        description=wf_desc,
        category=wf_cat,
        nodes=nodes,
        edges=edges,
        settings=WorkflowSettings(),
        metadata={"migrated_from_legacy_ir": True},
    )
    return graph


def convert_graph_to_legacy_ir(graph: AutomationGraph) -> Dict[str, Any]:
    """
    Downsamples an AutomationGraph back into legacy linear AutomationIR structure
    for backwards compatibility with existing Activepieces adapters.
    """
    trigger_node = next((n for n in graph.nodes if n.type == "trigger"), None)
    action_nodes = [n for n in graph.nodes if n.type != "trigger"]

    trigger_data = {
        "type": "octaos_event" if "octaos" in (trigger_node.tool_id or "") else "webhook",
        "event": (trigger_node.tool_id or "manual").split(":")[-1] if trigger_node else "manual",
        "display_name": trigger_node.name if trigger_node else "Trigger",
        "config": trigger_node.config if trigger_node else {},
    }

    steps_data = []
    for n in action_nodes:
        tool_parts = (n.tool_id or "action:run").split(":")
        piece = tool_parts[0] if len(tool_parts) > 1 else "octaos"
        action = tool_parts[1] if len(tool_parts) > 1 else tool_parts[0]

        steps_data.append({
            "id": n.id,
            "piece": piece,
            "action": action,
            "display_name": n.name,
            "parameters": n.config,
        })

    return {
        "name": graph.name,
        "slug": graph.slug or graph.name.lower().replace(" ", "-"),
        "description": graph.description,
        "category": graph.category,
        "trigger": trigger_data,
        "steps": steps_data,
        "required_connections": list({(n.tool_id or "").split(":")[0] for n in action_nodes if ":" in (n.tool_id or "")}),
    }

"""Static validation for versioned OctaOS visual workflows.

This validator is intentionally side-effect-free. Call it before publishing or
starting a run, then persist the validated immutable definition/version.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


ALLOWED_NODE_TYPES = {
    "start", "end", "agent", "tool", "condition", "approval", "delay",
    "transform", "subflow", "loop", "parallel", "webhook", "entity_action",
}
REQUIRED_CONFIG_KEYS = {
    "agent": ("agent_id",),
    "tool": ("tool_name",),
    "condition": ("expression",),
    "approval": ("title",),
    "delay": ("seconds",),
    "subflow": ("flow_id",),
    "webhook": ("connection_ref",),
    "entity_action": ("action", "entity_type"),
}
FORBIDDEN_SECRET_KEYS = {"api_key", "access_token", "refresh_token", "password", "secret", "client_secret"}


@dataclass(frozen=True)
class WorkflowIssue:
    code: str
    message: str
    node_id: str | None = None


@dataclass(frozen=True)
class WorkflowValidation:
    valid: bool
    issues: tuple[WorkflowIssue, ...]
    node_count: int
    edge_count: int


def _contains_forbidden_secret(value: Any, path: str = "definition") -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_SECRET_KEYS:
                return True
            if _contains_forbidden_secret(child, f"{path}.{key}"):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_secret(item, path) for item in value)
    return False


def validate_workflow(definition: Mapping[str, Any], *, max_nodes: int = 200) -> WorkflowValidation:
    issues: list[WorkflowIssue] = []
    nodes = definition.get("nodes", [])
    edges = definition.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return WorkflowValidation(False, (WorkflowIssue("INVALID_SHAPE", "nodes and edges must be arrays"),), 0, 0)
    if not nodes:
        issues.append(WorkflowIssue("EMPTY_WORKFLOW", "Workflow must contain at least one node."))
    if len(nodes) > max_nodes:
        issues.append(WorkflowIssue("NODE_LIMIT", f"Workflow exceeds the {max_nodes}-node limit."))
    if _contains_forbidden_secret(definition):
        issues.append(WorkflowIssue("SECRET_IN_DEFINITION", "Workflow definitions must reference tenant-managed connections; secrets cannot be embedded."))

    node_by_id: dict[str, Mapping[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            issues.append(WorkflowIssue("INVALID_NODE", f"Node at index {index} must be an object."))
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str) or not node_id.strip():
            issues.append(WorkflowIssue("MISSING_NODE_ID", f"Node at index {index} has no valid id."))
            continue
        if node_id in node_by_id:
            issues.append(WorkflowIssue("DUPLICATE_NODE_ID", f"Duplicate node id '{node_id}'.", node_id))
            continue
        node_by_id[node_id] = node
        if node_type not in ALLOWED_NODE_TYPES:
            issues.append(WorkflowIssue("UNKNOWN_NODE_TYPE", f"Unsupported node type '{node_type}'.", node_id))
            continue
        config = node.get("config", {})
        if not isinstance(config, Mapping):
            issues.append(WorkflowIssue("INVALID_CONFIG", "Node config must be an object.", node_id))
            continue
        for required in REQUIRED_CONFIG_KEYS.get(str(node_type), ()):
            if not config.get(required):
                issues.append(WorkflowIssue("MISSING_CONFIG", f"Node requires config.{required}.", node_id))
        if node_type == "delay":
            seconds = config.get("seconds")
            if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or seconds < 0 or seconds > 86400:
                issues.append(WorkflowIssue("INVALID_DELAY", "Delay must be between 0 and 86400 seconds.", node_id))

    adjacency: dict[str, list[str]] = defaultdict(list)
    indegree = {node_id: 0 for node_id in node_by_id}
    edge_pairs: set[tuple[str, str]] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, Mapping):
            issues.append(WorkflowIssue("INVALID_EDGE", f"Edge at index {index} must be an object."))
            continue
        source, target = edge.get("source"), edge.get("target")
        if source not in node_by_id or target not in node_by_id:
            issues.append(WorkflowIssue("DANGLING_EDGE", f"Edge at index {index} references a missing node."))
            continue
        pair = (str(source), str(target))
        if pair in edge_pairs:
            issues.append(WorkflowIssue("DUPLICATE_EDGE", f"Duplicate edge '{source}' -> '{target}'.", str(source)))
            continue
        edge_pairs.add(pair)
        adjacency[str(source)].append(str(target))
        indegree[str(target)] += 1

    # Acyclic topological validation. Loops must be represented as bounded loop
    # nodes with explicit exits, not by arbitrary graph cycles.
    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for target in adjacency[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(node_by_id):
        issues.append(WorkflowIssue("CYCLE_DETECTED", "Workflow graph contains a cycle; use a bounded loop node instead."))

    starts = [node for node in node_by_id.values() if node.get("type") == "start"]
    ends = [node for node in node_by_id.values() if node.get("type") == "end"]
    if len(starts) != 1:
        issues.append(WorkflowIssue("START_COUNT", "Workflow must have exactly one start node."))
    if len(ends) < 1:
        issues.append(WorkflowIssue("END_MISSING", "Workflow must have at least one end node."))

    return WorkflowValidation(not issues, tuple(issues), len(nodes), len(edges))

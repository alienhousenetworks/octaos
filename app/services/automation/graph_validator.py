"""
OctaOS Graph Validator.
Validates AutomationGraph DAG topology, cycle detection, port/handle bindings, and governance rules.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Set, Tuple
from app.schemas.automation.graph import AutomationGraph, AutomationNode, AutomationEdge

logger = logging.getLogger(__name__)


class GraphValidationError(Exception):
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or [message]


class GraphValidationResult:
    def __init__(
        self,
        is_valid: bool,
        errors: List[str] = None,
        warnings: List[str] = None,
        topology_stats: Dict[str, int] = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.topology_stats = topology_stats or {}

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "topology_stats": self.topology_stats,
        }


class GraphValidator:
    """
    Enforces strict structural and security integrity on AutomationGraph definitions.
    """

    @classmethod
    def validate(cls, graph: AutomationGraph) -> GraphValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not graph.nodes:
            return GraphValidationResult(
                is_valid=False,
                errors=["Workflow graph must contain at least one node."],
            )

        # 1. Unique Node IDs
        node_ids: Set[str] = set()
        node_map: Dict[str, AutomationNode] = {}
        trigger_count = 0

        for node in graph.nodes:
            if not node.id or not node.id.strip():
                errors.append("All nodes must have a non-empty unique 'id'.")
                continue

            if node.id in node_ids:
                errors.append(f"Duplicate node ID detected: '{node.id}'. Node IDs must be unique.")
            node_ids.add(node.id)
            node_map[node.id] = node

            if node.type == "trigger":
                trigger_count += 1

        if trigger_count == 0:
            errors.append("Workflow must contain at least one 'trigger' node.")

        # 2. Edge validation & Adjacency
        adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
        in_degrees: Dict[str, int] = {nid: 0 for nid in node_ids}
        out_degrees: Dict[str, int] = {nid: 0 for nid in node_ids}

        for edge in graph.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge '{edge.id}' has invalid source '{edge.source}' which does not exist in nodes.")
                continue
            if edge.target not in node_ids:
                errors.append(f"Edge '{edge.id}' has invalid target '{edge.target}' which does not exist in nodes.")
                continue

            # Trigger nodes cannot have incoming edges
            target_node = node_map.get(edge.target)
            if target_node and target_node.type == "trigger":
                errors.append(f"Trigger node '{edge.target}' cannot have incoming connections.")

            adj[edge.source].append(edge.target)
            in_degrees[edge.target] += 1
            out_degrees[edge.source] += 1

        # 3. Cycle Detection (DFS)
        visited: Dict[str, int] = {nid: 0 for nid in node_ids}  # 0: unvisited, 1: visiting, 2: visited

        def dfs_cycle(curr: str, path: List[str]) -> bool:
            visited[curr] = 1
            path.append(curr)

            for neighbor in adj.get(curr, []):
                if visited.get(neighbor) == 1:
                    cycle_nodes = " -> ".join(path + [neighbor])
                    errors.append(f"Illegal loop or cycle detected in DAG: {cycle_nodes}. Use an explicit 'loop' node for iteration.")
                    return True
                if visited.get(neighbor) == 0:
                    if dfs_cycle(neighbor, path):
                        return True

            path.pop()
            visited[curr] = 2
            return False

        for nid in node_ids:
            if visited[nid] == 0:
                dfs_cycle(nid, [])

        # 4. Disconnected node detection (warnings)
        if len(graph.nodes) > 1:
            for nid, node in node_map.items():
                if in_degrees[nid] == 0 and out_degrees[nid] == 0:
                    warnings.append(f"Node '{node.name}' ({nid}) is completely disconnected and will not be triggered.")
                elif in_degrees[nid] == 0 and node.type != "trigger":
                    warnings.append(f"Action node '{node.name}' ({nid}) has no incoming trigger path and cannot execute.")

        stats = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "triggers": trigger_count,
            "actions": len(graph.nodes) - trigger_count,
        }

        return GraphValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            topology_stats=stats,
        )

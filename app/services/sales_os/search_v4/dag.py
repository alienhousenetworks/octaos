"""Versioned sales DAG definition. The live Sales AI path stays on run_sales_ai_v3_workflow until parity is measured."""
SALES_V4_DAG_VERSION = "sales-discovery-v4.0"

NODE_TYPES = {
    "agent",
    "skill",
    "tool",
    "condition",
    "approval",
    "event",
    "entity",
    "parallel",
    "compensation",
}

SALES_V4_NODES = [
    {"id": "campaign", "type": "skill", "skill_id": "discovery.compile_campaign"},
    {"id": "discover", "type": "tool", "tool": "search_v4"},
    {"id": "qualify", "type": "skill", "skill_id": "sales.qualify_lead"},
    {"id": "policy", "type": "condition"},
    {"id": "nurture", "type": "entity"},
    {"id": "compose", "type": "skill", "skill_id": "sales.compose_outreach"},
    {"id": "approve", "type": "approval"},
    {"id": "hold", "type": "compensation"},
    {"id": "monitor", "type": "event"},
    {"id": "book", "type": "skill", "skill_id": "sales.handle_reply"},
]

SALES_V4_EDGES = [
    ("campaign", "discover"),
    ("discover", "qualify"),
    ("qualify", "policy"),
    ("policy", "nurture"),
    ("policy", "compose"),
    ("compose", "approve"),
    ("approve", "hold"),
    ("approve", "monitor"),
    ("monitor", "book"),
]


def validate_dag(nodes: list[dict], edges: list[tuple[str, str]]) -> list[str]:
    """Return validation errors. An empty list means the graph is usable."""
    errors = []
    ids = [node.get("id") for node in nodes]
    if len(ids) != len(set(ids)) or any(not node_id for node_id in ids):
        errors.append("Every node needs a unique id.")
    known = set(ids)
    for node in nodes:
        if node.get("type") not in NODE_TYPES:
            errors.append(f"Node {node.get('id')} has an unknown type.")
    adjacency = {node_id: [] for node_id in known}
    for source, target in edges:
        if source not in known or target not in known:
            errors.append(f"Edge {source}->{target} names a missing node.")
            continue
        adjacency[source].append(target)
    visiting = set()
    visited = set()

    def walk(node_id: str) -> None:
        if node_id in visiting:
            errors.append(f"Cycle at {node_id}.")
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for child in adjacency.get(node_id, []):
            walk(child)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in known:
        walk(node_id)
    return errors

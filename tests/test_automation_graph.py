"""Unit tests for AutomationGraph and GraphValidator."""
import pytest
from app.schemas.automation.graph import (
    AutomationGraph,
    AutomationNode,
    AutomationEdge,
    NodePosition,
    NodePortKind,
    convert_legacy_ir_to_graph,
    convert_graph_to_legacy_ir,
)
from app.services.automation.graph_validator import GraphValidator


def test_valid_dag_validation():
    nodes = [
        AutomationNode(id="n1", type="trigger", name="Lead Arrived", position=NodePosition(x=0, y=0)),
        AutomationNode(id="n2", type="action", name="Enrich Lead", position=NodePosition(x=200, y=0)),
        AutomationNode(id="n3", type="action", name="Notify Slack", position=NodePosition(x=400, y=0)),
    ]
    edges = [
        AutomationEdge(id="e1", source="n1", target="n2"),
        AutomationEdge(id="e2", source="n2", target="n3"),
    ]
    graph = AutomationGraph(name="Test Flow", nodes=nodes, edges=edges)

    result = GraphValidator.validate(graph)
    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.topology_stats["total_nodes"] == 3
    assert result.topology_stats["total_edges"] == 2


def test_cycle_detection_fails():
    nodes = [
        AutomationNode(id="n1", type="trigger", name="Start", position=NodePosition(x=0, y=0)),
        AutomationNode(id="n2", type="action", name="Step B", position=NodePosition(x=200, y=0)),
        AutomationNode(id="n3", type="action", name="Step C", position=NodePosition(x=400, y=0)),
    ]
    # Create cycle: n1 -> n2 -> n3 -> n2
    edges = [
        AutomationEdge(id="e1", source="n1", target="n2"),
        AutomationEdge(id="e2", source="n2", target="n3"),
        AutomationEdge(id="e3", source="n3", target="n2"),
    ]
    graph = AutomationGraph(name="Cycle Flow", nodes=nodes, edges=edges)

    result = GraphValidator.validate(graph)
    assert result.is_valid is False
    assert any("Illegal loop or cycle detected" in err for err in result.errors)


def test_legacy_ir_conversion():
    legacy_ir = {
        "name": "Legacy Flow",
        "slug": "legacy-flow",
        "category": "sales",
        "trigger": {
            "type": "octaos_event",
            "event": "lead.qualified",
            "display_name": "OctaOS: Lead Qualified",
            "config": {"score": 80},
        },
        "steps": [
            {
                "id": "step_1",
                "piece": "slack",
                "action": "send_message",
                "display_name": "Slack: Alert",
                "parameters": {"channel": "#sales"},
            },
            {
                "id": "step_2",
                "piece": "hubspot",
                "action": "create_deal",
                "display_name": "HubSpot: Deal",
                "parameters": {"amount": 5000},
            },
        ],
    }

    graph = convert_legacy_ir_to_graph(legacy_ir)
    assert len(graph.nodes) == 3
    assert graph.nodes[0].type == "trigger"
    assert graph.nodes[1].id == "step_1"
    assert graph.nodes[2].id == "step_2"
    assert len(graph.edges) == 2

    # Check round-trip conversion
    converted_back = convert_graph_to_legacy_ir(graph)
    assert converted_back["name"] == "Legacy Flow"
    assert len(converted_back["steps"]) == 2
    assert converted_back["steps"][0]["piece"] == "slack"

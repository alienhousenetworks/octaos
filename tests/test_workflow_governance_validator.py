from app.services.workflow_governance.validator import validate_workflow


def valid_graph():
    return {
        "nodes": [
            {"id": "start", "type": "start", "config": {}},
            {"id": "agent-1", "type": "agent", "config": {"agent_id": "sales"}},
            {"id": "end", "type": "end", "config": {}},
        ],
        "edges": [
            {"source": "start", "target": "agent-1"},
            {"source": "agent-1", "target": "end"},
        ],
    }


def test_valid_workflow_passes():
    result = validate_workflow(valid_graph())
    assert result.valid
    assert result.node_count == 3


def test_unknown_node_and_missing_config_are_reported():
    graph = valid_graph()
    graph["nodes"][1] = {"id": "tool-1", "type": "tool", "config": {}}
    result = validate_workflow(graph)
    assert not result.valid
    assert {issue.code for issue in result.issues} >= {"MISSING_CONFIG"}


def test_cycle_is_rejected():
    graph = valid_graph()
    graph["edges"].append({"source": "end", "target": "start"})
    assert "CYCLE_DETECTED" in {issue.code for issue in validate_workflow(graph).issues}


def test_secret_values_cannot_be_embedded_in_definition():
    graph = valid_graph()
    graph["nodes"][1]["config"]["api_key"] = "not-allowed"
    assert "SECRET_IN_DEFINITION" in {issue.code for issue in validate_workflow(graph).issues}


def test_dangling_edges_and_duplicate_node_ids_are_rejected():
    graph = valid_graph()
    graph["nodes"].append({"id": "end", "type": "end", "config": {}})
    graph["edges"].append({"source": "missing", "target": "end"})
    codes = {issue.code for issue in validate_workflow(graph).issues}
    assert "DUPLICATE_NODE_ID" in codes
    assert "DANGLING_EDGE" in codes

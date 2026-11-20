from app.services.agents.tools import tool_registry
from app.services.orodruin_intel import OrodruinIntelService


def test_orodruin_tools_registered():
    expected = [
        "orodruin.signals",
        "orodruin.geolocate_ip",
        "orodruin.cyber_lookup",
        "orodruin.ransomware",
        "orodruin.finance_awards",
        "orodruin.research_papers",
        "orodruin.markets",
        "orodruin.prediction_markets",
        "orodruin.search_sanctions",
        "orodruin.ui_action",
    ]
    for name in expected:
        assert tool_registry.get(name) is not None, f"Missing tool: {name}"


def test_orodruin_actor_graph_builder():
    svc = OrodruinIntelService()
    graph = svc.build_actor_graph(
        [{"source": "gdelt", "category": "news", "country": "US"}],
        topic="cloud security",
    )
    assert len(graph["nodes"]) >= 2
    assert len(graph["edges"]) >= 1

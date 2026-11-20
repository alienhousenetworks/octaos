from app.services.agents.tools import tool_registry
from app.services.orodruin_intel import OrodruinIntelService


def test_orodruin_tools_registered():
    assert tool_registry.get("orodruin.signals") is not None
    assert tool_registry.get("orodruin.geolocate_ip") is not None


def test_orodruin_service_instantiation():
    svc = OrodruinIntelService()
    assert svc.timeout > 0

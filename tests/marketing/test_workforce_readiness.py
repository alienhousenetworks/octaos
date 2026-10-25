"""Readiness must distinguish configured integrations from live-verified capability."""
from app.models.base import APICredential
from app.services.marketing.workforce_readiness import get_marketing_workforce_readiness


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or []

    def query(self, model):
        assert model is APICredential
        return FakeQuery(self.rows)


def test_missing_provider_keys_are_not_claimed_as_working():
    result = get_marketing_workforce_readiness(FakeDB(), "tenant-a")
    capabilities = {item["id"]: item for item in result["capabilities"]}
    assert capabilities["brand_product_understanding"]["status"] == "in_app_component"
    assert capabilities["buffer_publishing"]["status"] == "needs_connection"
    assert capabilities["revenue_attribution"]["status"] == "needs_configuration"
    assert all(item["live_verified"] is False for item in result["capabilities"])


def test_buffer_readiness_reports_mapping_without_exposing_token():
    row = APICredential(
        tenant_id="tenant-a",
        provider="buffer",
        encrypted_key="encrypted-secret-not-returned",
        settings={"connected": True, "channel_map": {"instagram": "channel-123"}},
    )
    result = get_marketing_workforce_readiness(FakeDB([row]), "tenant-a")
    assert result["connected_buffer"] is True
    assert result["buffer_channel_map"] == {"instagram": "channel-123"}
    assert "encrypted-secret-not-returned" not in str(result)
    buffer_capability = next(item for item in result["capabilities"] if item["id"] == "buffer_publishing")
    assert buffer_capability["status"] == "configured"
    assert buffer_capability["live_verified"] is False

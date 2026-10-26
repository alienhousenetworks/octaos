import pytest

from app.services.runtime_governance.portable_packs import (
    PackValidationError, build_portable_pack, prepare_pack_install,
)


def test_pack_export_accepts_reusable_definitions():
    manifest = build_portable_pack(
        name="Sales Starter", version="1.2.0", description="A reusable sales team",
        agents=[{"name": "Sales AI", "prompt_template": "Use supplied evidence."}],
        workflows=[{"nodes": [], "edges": []}],
        required_tools=["lead.read", "lead.score", "lead.read"],
    )
    assert manifest["required_tools"] == ["lead.read", "lead.score"]


@pytest.mark.parametrize("bad_key", ["api_key", "tenant_id", "conversation_history", "client_secret"])
def test_pack_export_rejects_secrets_and_tenant_data(bad_key):
    with pytest.raises(PackValidationError):
        build_portable_pack(
            name="Bad Pack", version="1.0.0", description="",
            agents=[{"name": "agent", bad_key: "sensitive"}], workflows=[],
        )


def test_install_preview_defaults_connections_and_schedules_off():
    manifest = build_portable_pack(
        name="Support Starter", version="1.0.0", description="",
        agents=[], workflows=[],
    )
    preview = prepare_pack_install(manifest)
    assert preview["install_defaults"]["connections_enabled"] is False
    assert preview["install_defaults"]["schedules_enabled"] is False
    assert preview["install_defaults"]["require_admin_review"] is True


def test_invalid_pack_version_rejected():
    with pytest.raises(PackValidationError):
        build_portable_pack(name="Pack", version="latest", description="", agents=[], workflows=[])

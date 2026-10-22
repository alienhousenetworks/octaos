"""Tests for Industry Engine Manifest validation and PipelineEngine."""
import pytest
from fastapi import HTTPException
from app.services.sales_os.industry_runtime.manifest import (
    validate_manifest,
    IndustryPackManifest,
    CapabilityStatus,
)
from app.services.sales_os.industry_runtime.pipeline_engine import PipelineEngine
from app.services.sales_os.verticals.packs import PACKS


def test_all_eighteen_packs_validate_cleanly():
    """Verify that all 18 registered vertical packs conform strictly to the IndustryPackManifest schema."""
    assert len(PACKS) == 18
    for pack_id, pack_dict in PACKS.items():
        manifest = validate_manifest(pack_dict)
        assert manifest.id == pack_id
        assert len(manifest.pipeline_stages) > 0
        assert all(isinstance(stage.id, str) and stage.id for stage in manifest.pipeline_stages)


def test_real_estate_capabilities_and_stages():
    """Verify Real Estate pack contains rich capabilities and stable stage IDs."""
    estate_manifest = validate_manifest(PACKS["real_estate"])
    assert estate_manifest.id == "real_estate"
    assert estate_manifest.readiness == "representative"

    # Check capabilities
    assert "inventory_catalog" in estate_manifest.capabilities
    assert estate_manifest.capabilities["inventory_catalog"].status == CapabilityStatus.AVAILABLE
    assert "atomic_unit_reservation" in estate_manifest.capabilities
    assert "site_visit_scheduler" in estate_manifest.capabilities

    # Check pipeline stages
    stage_ids = [s.id for s in estate_manifest.pipeline_stages]
    assert stage_ids == ["inquiry", "qualified", "site_visit", "hold_requested", "booking", "cancelled"]


def test_pipeline_engine_transition_validation():
    """Verify PipelineEngine enforces valid stage progression."""
    estate_manifest = validate_manifest(PACKS["real_estate"])
    engine = PipelineEngine(estate_manifest)

    # Valid transitions
    engine.validate_transition("inquiry", "qualified")
    engine.validate_transition("qualified", "site_visit")
    engine.validate_transition("site_visit", "hold_requested")
    engine.validate_transition("hold_requested", "booking")

    # Invalid jump
    with pytest.raises(HTTPException) as exc_info:
        engine.validate_transition("inquiry", "booking")
    assert exc_info.value.status_code == 400
    assert "Invalid stage transition" in exc_info.value.detail


def test_pipeline_engine_legacy_stage_mapping():
    """Verify legacy stages map safely to real estate stages without deleting records."""
    assert PipelineEngine.map_legacy_stage("saas", "real_estate", "new") == "inquiry"
    assert PipelineEngine.map_legacy_stage("saas", "real_estate", "meeting_scheduled") == "site_visit"
    assert PipelineEngine.map_legacy_stage("saas", "real_estate", "closed_won") == "booking"
    assert PipelineEngine.map_legacy_stage("saas", "real_estate", "closed_lost") == "cancelled"

    # Reverse mapping
    assert PipelineEngine.map_legacy_stage("real_estate", "saas", "booking") == "closed_won"
    assert PipelineEngine.map_legacy_stage("real_estate", "saas", "cancelled") == "closed_lost"

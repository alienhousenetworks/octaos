"""Regression tests for CEO v5 routes consumed by the OctaOS workspace UI."""

from app.api.v1.api import api_router


def test_ceo_v5_workspace_routes_are_registered():
    registered_paths = {route.path for route in api_router.routes}

    # These paths are called by the CEO / Objectives & execution workspace.
    assert "/ceo/cockpit/vitals" in registered_paths
    assert "/ceo/interactive/company-context" in registered_paths
    assert "/ceo/interactive/plan" in registered_paths
    assert "/ceo/interactive/assign-and-execute" in registered_paths
    assert "/ceo/workflows/{workflow_id}/projection" in registered_paths
    assert "/ceo/workflows/{workflow_id}/start" in registered_paths
    assert "/ceo/workflows/{workflow_id}/pause" in registered_paths
    assert "/ceo/workflows/{workflow_id}/resume" in registered_paths

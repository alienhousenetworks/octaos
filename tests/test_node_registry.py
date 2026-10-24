"""
Unit tests for visual workflow NodeRegistry and enterprise catalog discovery.
"""
import pytest
from app.services.automation.node_registry import NodeRegistry, ENTERPRISE_CATALOG


def test_catalog_structure_and_categories():
    catalog = NodeRegistry.get_catalog(mode="all")
    category_ids = [cat["id"] for cat in catalog]
    assert "triggers" in category_ids
    assert "control_flow" in category_ids
    assert "document_intelligence" in category_ids
    assert "native_modules" in category_ids


def test_native_modules_includes_all_departments():
    catalog = NodeRegistry.get_catalog(mode="all")
    native_cat = next((cat for cat in catalog if cat["id"] == "native_modules"), None)
    assert native_cat is not None

    all_nodes = []
    for fam in native_cat["families"]:
        all_nodes.extend(fam["nodes"])

    node_ids = {n["node_id"] for n in all_nodes}

    # Verify Marketing, Sales, HR, Support, Orchestrator, Pack, Governance nodes exist
    assert "octaos.sales.score_lead" in node_ids
    assert "octaos.hr.parse_resume" in node_ids
    assert "octaos.support.create_ticket" in node_ids
    assert "octaos.marketing.launch_campaign" in node_ids
    assert "octaos.orchestrator.dispatch_goal" in node_ids
    assert "octaos.industry_pack.execute_action" in node_ids
    assert "octaos.governance.hitl_approval" in node_ids


def test_catalog_filtering_by_mode():
    doc_catalog = NodeRegistry.get_catalog(mode="document")
    for cat in doc_catalog:
        for fam in cat["families"]:
            for node in fam["nodes"]:
                assert node["mode"] in ("all", "document")

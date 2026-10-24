"""
Unit tests for OctaOS Industry Solution Pack Contract.
"""
import pytest
from app.core.industry_pack_contract import (
    IndustryPackManifest,
    PackPipelineStage,
    PackSpecializedAgent,
    PackWorkflowTemplate,
    PackApprovalPolicy,
    PackReadiness,
    RiskLevel,
)


def test_industry_pack_manifest_creation():
    stage_inquiry = PackPipelineStage(
        id="inquiry",
        label="New Inquiry",
        color="#75AFCB",
        valid_transitions=["site_visit", "lost"],
    )
    stage_won = PackPipelineStage(
        id="booked",
        label="Confirmed Booking",
        is_terminal=True,
        terminal_outcome="won",
    )

    agent_concierge = PackSpecializedAgent(
        agent_id="re_concierge",
        name="Real Estate Concierge AI",
        department="sales",
        description="Assists buyers with unit selection and site visit booking.",
        system_prompt_template="You are a professional real estate specialist.",
        allowed_tool_ids=["real_estate.get_inventory_status", "real_estate.calculate_cost_sheet"],
        risk_ceiling=RiskLevel.R1_INTERNAL_REVERSIBLE,
    )

    workflow_lead = PackWorkflowTemplate(
        template_id="lead_to_visit",
        name="Lead to Site Visit Dispatch",
        category="Sales",
        description="Auto-qualifies inbound leads and schedules tour.",
        trigger_type="event",
    )

    policy_discount = PackApprovalPolicy(
        action_key="price_discount",
        threshold_value=2.5,
        threshold_unit="percentage",
        approver_role="sales_head",
        description="Discounts over 2.5% require Sales Head approval",
    )

    manifest = IndustryPackManifest(
        pack_id="real_estate",
        version="1.0.0",
        name="Real Estate Solution Pack",
        summary="End-to-end real estate sales, marketing, inventory, and visits.",
        readiness=PackReadiness.PRODUCTION_READY,
        target_verticals=["Residential", "Commercial", "Plots"],
        domain_models=["real_estate_projects", "real_estate_units", "real_estate_bookings"],
        pipeline_stages=[stage_inquiry, stage_won],
        agents=[agent_concierge],
        workflow_templates=[workflow_lead],
        approval_policies=[policy_discount],
        external_portals=["broker", "developer", "customer"],
    )

    d = manifest.to_dict()
    assert d["pack_id"] == "real_estate"
    assert d["version"] == "1.0.0"
    assert d["readiness"] == "production_ready"
    assert len(d["pipeline_stages"]) == 2
    assert d["pipeline_stages"][1]["is_terminal"] is True
    assert d["pipeline_stages"][1]["terminal_outcome"] == "won"
    assert len(d["agents"]) == 1
    assert d["agents"][0]["allowed_tool_ids"] == ["real_estate.get_inventory_status", "real_estate.calculate_cost_sheet"]
    assert "broker" in d["external_portals"]
    assert "developer" in d["external_portals"]
    assert "customer" in d["external_portals"]

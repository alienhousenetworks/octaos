import json
import os
import pytest
from app.schemas.orchestrator_briefing import BriefingResponse


def test_briefing_fixtures_validate_schema():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    fixture_files = [
        "briefing_healthy.json",
        "briefing_struggling.json",
        "briefing_empty_state.json",
    ]
    
    for filename in fixture_files:
        filepath = os.path.join(fixtures_dir, filename)
        assert os.path.exists(filepath), f"Fixture not found: {filepath}"
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        briefing = BriefingResponse.model_validate(data)
        assert briefing.schema_version == "1.0"
        assert briefing.briefing_text
        assert briefing.metrics.tenant_id
        assert len(briefing.charts) >= 1
        assert len(briefing.findings) >= 1
        assert len(briefing.improvement_plan) >= 1
        assert len(briefing.trace) >= 1


def test_briefing_schema_custom_instance():
    from app.schemas.orchestrator_briefing import MetricsPayload, MetricValue, PlotlyChartSpec, Finding, ActionItem, AgentTraceEntry
    
    payload = MetricsPayload(
        tenant_id="tenant-test",
        harvested_at="2026-10-04T12:00:00Z",
        empty_state=False,
        items={
            "leads.total": MetricValue(
                metric_id="leads.total",
                name="Total Leads",
                value=50.0,
                formatted="50",
                unit="count",
                direction="up",
                category="sales"
            )
        }
    )
    
    briefing = BriefingResponse(
        briefing_text="Test summary",
        metrics=payload,
        charts=[
            PlotlyChartSpec(
                chart_id="test_chart",
                title="Test Chart",
                spec={"data": [], "layout": {}}
            )
        ],
        findings=[
            Finding(
                id="F-1",
                title="Test Finding",
                evidence="Evidence text",
                root_cause="Root cause",
                impact="Impact",
                severity="WARNING"
            )
        ],
        improvement_plan=[
            ActionItem(
                id="ACT-1",
                phase="7d",
                title="Immediate Fix",
                description="Fix description",
                department="Sales"
            )
        ],
        trace=[
            AgentTraceEntry(
                agent_id=1,
                name="Classifier",
                role="Classifier",
                execution_type="rule_based",
                summary="Detected"
            )
        ]
    )
    
    assert briefing.mode == "analytics"
    assert briefing.metrics.items["leads.total"].value == 50.0

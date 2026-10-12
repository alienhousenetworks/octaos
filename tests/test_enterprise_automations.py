import pytest
from app.services.automation.base import AutomationIR, TriggerIR, StepIR, RiskLevel, EngineType
from app.services.automation.compiler import FlowCompiler
from app.services.automation.templates import find_matching_template, ENTERPRISE_TEMPLATES
from app.services.automation.ai_service import AIAutomationService
from app.services.automation.activepieces_adapter import ActivepiecesEngineAdapter
from app.services.automation.factory import get_automation_engine
from app.models.automations import AutomationWorkflow, AutomationExecution, AutomationTenantEnvironment


def test_enterprise_templates_structure():
    """Verify all predefined enterprise templates are valid and have canonical IR."""
    assert len(ENTERPRISE_TEMPLATES) >= 4
    for tpl in ENTERPRISE_TEMPLATES:
        assert "id" in tpl
        assert "name" in tpl
        assert "default_ir" in tpl
        ir = AutomationIR(**tpl["default_ir"])
        assert ir.trigger.type in ["octaos_event", "webhook", "schedule", "manual"]
        assert len(ir.steps) > 0


def test_template_keyword_matching():
    """Verify natural language prompt correctly triggers Template-First matching."""
    prompt = "When a qualified lead arrives, send a slack message and create a deal in hubspot"
    matched = find_matching_template(prompt)
    assert matched is not None
    assert matched["id"] == "tpl_lead_qualification_slack_crm"


def test_flow_compiler_to_activepieces():
    """Verify canonical AutomationIR compiles into valid Activepieces Flow schema."""
    ir = AutomationIR(
        name="Lead Qualified to Slack",
        slug="lead-qualified-slack",
        description="Notify sales in Slack",
        category="sales",
        trigger=TriggerIR(type="octaos_event", event="lead.qualified"),
        steps=[
            StepIR(
                id="s1",
                piece="slack",
                action="send_message",
                parameters={"channel": "#sales", "text": "Qualified lead!"},
            ),
            StepIR(
                id="s2",
                piece="hubspot",
                action="create_deal",
                parameters={"dealname": "Enterprise Deal"},
            ),
        ],
        required_connections=["slack", "hubspot", "octaos"],
    )

    compiled = FlowCompiler.compile_to_activepieces(ir)
    assert compiled["displayName"] == "Lead Qualified to Slack"
    assert "trigger" in compiled
    assert compiled["trigger"]["type"] == "PIECE_TRIGGER"
    assert compiled["trigger"]["settings"]["pieceName"] == "@octaos/piece-octaos"
    assert compiled["trigger"]["settings"]["triggerName"] == "lead.qualified"
    assert "nextAction" in compiled["trigger"]
    assert compiled["trigger"]["nextAction"]["settings"]["pieceName"] == "@activepieces/piece-slack"
    assert "nextAction" in compiled["trigger"]["nextAction"]
    assert compiled["trigger"]["nextAction"]["nextAction"]["settings"]["pieceName"] == "@activepieces/piece-hubspot"


@pytest.mark.asyncio
async def test_activepieces_adapter_operations():
    """Verify Activepieces adapter compiles and provisions workflows."""
    adapter = ActivepiecesEngineAdapter(base_url="http://localhost:8080")
    assert adapter.engine_type == EngineType.ACTIVEPIECES

    workspace_info = await adapter.provision_tenant_workspace(
        tenant_id="tenant-test-123",
        subdomain="tenant-test-123.flows.octaos.org",
    )
    assert workspace_info.tenant_id == "tenant-test-123"
    assert "tenant-test-123.flows.octaos.org" in workspace_info.subdomain

    ir = AutomationIR(
        name="Test Flow",
        slug="test-flow",
        trigger=TriggerIR(type="octaos_event", event="ticket.escalated"),
        steps=[StepIR(id="1", piece="slack", action="send_message")],
    )

    deployed = await adapter.compile_and_deploy_workflow("tenant-test-123", ir)
    assert "external_id" in deployed
    assert "compiled_schema" in deployed

    editor_url = await adapter.get_workflow_editor_url("tenant-test-123", deployed["external_id"], "admin@octaos.org")
    assert deployed["external_id"] in editor_url

    test_run = await adapter.trigger_workflow_manually("tenant-test-123", deployed["external_id"], {"ticket_id": "123"})
    assert test_run["status"] == "succeeded"


def test_multi_gate_governance_validation():
    """Verify multi-gate validation intercepts unsafe code and verifies structural soundness."""
    service = AIAutomationService(db=None, tenant_id="tenant-123")  # type: ignore

    # 1. Valid IR
    valid_ir = AutomationIR(
        name="Safe Flow",
        slug="safe-flow",
        trigger=TriggerIR(type="octaos_event", event="lead.created"),
        steps=[StepIR(id="s1", piece="slack", action="send_message")],
    )
    gates = service.validate_pipeline(valid_ir, "Notify team")
    assert all(g.passed for g in gates)

    # 2. Dangerous SQL pattern interception
    unsafe_ir = AutomationIR(
        name="Unsafe Flow",
        slug="unsafe-flow",
        trigger=TriggerIR(type="octaos_event", event="lead.created"),
        steps=[StepIR(id="s1", piece="slack", action="send_message", parameters={"text": "DROP TABLE users;"})],
    )
    gates_unsafe = service.validate_pipeline(unsafe_ir, "Drop table")
    security_gate = next(g for g in gates_unsafe if g.gate_name == "Security Validation")
    assert security_gate.passed is False

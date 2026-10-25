"""
Unit tests for hardened AIManagerOrchestrator with Governed ToolRegistry.
"""
import pytest
from app.octa_orchestrator.orchestrator.manager import AIManagerOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_initialization_and_tool_registry():
    orch = AIManagerOrchestrator(tenant_id="tenant-test")
    assert orch.tool_registry is not None
    assert orch.tenant_id == "tenant-test"


@pytest.mark.asyncio
async def test_orchestrator_executes_goal_with_governed_tools(monkeypatch):
    orch = AIManagerOrchestrator(tenant_id="tenant-test")
    goal = "Analyze our marketing campaign spend and sales pipeline conversion"

    # Keep the unit test deterministic: no live planner or model-provider calls.
    from app.octa_orchestrator.orchestrator.decomposer import ExecutionPlanDAG, SubTask
    class MockDecomposer:
        async def decompose_goal(self, goal, model_name="gpt-4o"):
            return ExecutionPlanDAG(
                goal=goal,
                tasks=[SubTask(
                    task_id="task_analytics",
                    description="Summarize available marketing metrics",
                    assigned_agent="analytics_agent",
                    dependencies=[],
                    roi_priority=1,
                )],
                estimated_total_roi="Not assessed",
            )
    class MockResponse:
        status_code = 503
        def json(self):
            return {}
    class MockClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            return MockResponse()

    import app.octa_orchestrator.orchestrator.manager as manager_module
    monkeypatch.setattr(manager_module.httpx, "AsyncClient", lambda: MockClient())
    orch.decomposer = MockDecomposer()
    result = await orch.execute_goal(goal)

    assert "trajectory_id" in result
    assert result["user_goal"] == goal
    assert result["sub_tasks_executed"] >= 1
    assert "results" in result
    assert "logs" in result
    assert "execution_time_ms" in result


@pytest.mark.asyncio
async def test_orchestrator_captures_pending_approvals_for_critical_actions():
    orch = AIManagerOrchestrator(
        tenant_id="tenant-test",
        user_context={"role": "sales_rep", "pre_approved": False, "is_superuser": False},
    )
    # A task with price discount / concession requires human approval
    from app.octa_orchestrator.orchestrator.decomposer import ExecutionPlanDAG, SubTask
    
    # Mock decomposer to return a discount sub-task
    class MockDecomposer:
        async def decompose_goal(self, goal, model_name="gpt-4o"):
            return ExecutionPlanDAG(
                goal=goal,
                tasks=[
                    SubTask(
                        task_id="task_discount_1",
                        description="Approve discount price concession for buyer on unit 402",
                        assigned_agent="sales_agent",
                        dependencies=[],
                        roi_priority=1,
                    )
                ],
                estimated_total_roi="High",
            )
            
    orch.decomposer = MockDecomposer()
    result = await orch.execute_goal("Give a 5% discount price concession on unit 402")

    assert len(result["pending_approvals"]) == 1
    approval = result["pending_approvals"][0]
    assert approval["action_key"] == "sales.approve_booking_discount"
    assert "requires explicit manager sign-off" in approval["reason"]
    assert "[APPROVAL PENDING]" in result["results"]["task_discount_1"]

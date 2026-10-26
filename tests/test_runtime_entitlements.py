import pytest

from app.services.runtime_governance.entitlements import (
    EntitlementDenied, PlanEntitlements, enforce_feature, enforce_run_admission,
)


@pytest.fixture
def plan():
    return PlanEntitlements.from_mapping({
        "plan_id": "growth",
        "enabled_features": ["sales_ai", "workflow_builder"],
        "max_concurrent_runs": 3,
        "monthly_task_limit": 1000,
        "monthly_cost_limit": "250.00",
        "allowed_providers": ["openai", "anthropic"],
    })


def test_feature_entitlement_is_server_enforceable(plan):
    enforce_feature(plan, "sales_ai")
    with pytest.raises(EntitlementDenied):
        enforce_feature(plan, "computer_use")


def test_run_admission_accepts_within_limits(plan):
    enforce_run_admission(
        plan, active_runs=1, monthly_tasks=20, monthly_cost="100.00",
        requested_provider="openai", estimated_cost="5.50",
    )


@pytest.mark.parametrize("overrides", [
    {"active_runs": 3, "monthly_tasks": 20, "monthly_cost": "10", "requested_provider": "openai"},
    {"active_runs": 0, "monthly_tasks": 1000, "monthly_cost": "10", "requested_provider": "openai"},
    {"active_runs": 0, "monthly_tasks": 20, "monthly_cost": "249", "requested_provider": "openai", "estimated_cost": "2"},
    {"active_runs": 0, "monthly_tasks": 20, "monthly_cost": "10", "requested_provider": "unsupported"},
])
def test_run_admission_fails_closed(overrides, plan):
    args = dict(active_runs=0, monthly_tasks=0, monthly_cost="0", requested_provider="openai")
    args.update(overrides)
    with pytest.raises(EntitlementDenied):
        enforce_run_admission(plan, **args)


def test_invalid_plan_limits_rejected():
    with pytest.raises(ValueError):
        PlanEntitlements.from_mapping({"plan_id": "x", "enabled_features": [], "max_concurrent_runs": -1,
                                       "monthly_task_limit": 10, "monthly_cost_limit": 5, "allowed_providers": []})

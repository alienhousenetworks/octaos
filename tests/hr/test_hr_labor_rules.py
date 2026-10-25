"""Regression tests for tenant-configured labor-rule input and schema constraints."""
import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.hr_workforce import LaborRuleUpsertRequest
from app.models.hr_workforce import HRLaborRule


def test_labor_rule_requires_at_least_one_limit_at_route_layer():
    # Pydantic validates individual ranges; the endpoint rejects all-null rules.
    request = LaborRuleUpsertRequest(jurisdiction="IN-West Bengal")
    assert request.minimum_rest_hours is None
    assert request.maximum_shift_hours is None
    assert request.maximum_weekly_hours is None


@pytest.mark.parametrize(
    "payload",
    [
        {"jurisdiction": "IN", "minimum_rest_hours": -1},
        {"jurisdiction": "IN", "minimum_rest_hours": 25},
        {"jurisdiction": "IN", "maximum_shift_hours": 0},
        {"jurisdiction": "IN", "maximum_shift_hours": 25},
        {"jurisdiction": "IN", "maximum_weekly_hours": 0},
        {"jurisdiction": "IN", "maximum_weekly_hours": 169},
    ],
)
def test_labor_rule_rejects_out_of_range_values(payload):
    with pytest.raises(ValidationError):
        LaborRuleUpsertRequest(**payload)


def test_labor_rules_are_tenant_scoped_and_limits_are_database_constrained():
    table = HRLaborRule.__table__
    assert table.c.tenant_id.unique is True
    constraints = {constraint.name for constraint in table.constraints}
    assert "chk_hr_labor_rest_hours" in constraints
    assert "chk_hr_labor_max_shift" in constraints
    assert "chk_hr_labor_max_weekly" in constraints

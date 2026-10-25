"""Regression tests for tenant-configured labor-rule input and schema constraints."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import deps
from app.api.v1.endpoints import hr_workforce
from app.api.v1.endpoints.hr_workforce import LaborRuleUpsertRequest
from app.models.hr_workforce import HRLaborRule


def test_labor_rule_requires_at_least_one_limit_at_route_layer():
    app = FastAPI()
    app.include_router(hr_workforce.router, prefix="/workforce")
    app.dependency_overrides[deps.get_db] = lambda: SimpleNamespace()
    app.dependency_overrides[deps.get_current_tenant_id] = lambda: "tenant-a"
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(
        id="hr-user", role="member", is_system_admin=False, is_superuser=False,
        user_permissions=[SimpleNamespace(codename="hr.manage_workforce")], groups=[]
    )
    response = TestClient(app).put("/workforce/labor-rules", json={"jurisdiction": "IN-West Bengal"})
    assert response.status_code == 422
    assert "at least one labor limit" in response.json()["detail"]


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

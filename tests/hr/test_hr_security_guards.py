from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.hr_people import _require_hr_access
from app.api.v1.endpoints.hr_workforce import _require_hr_role
from app.services.agents.hr.risk_classifier import HRRiskClassifier
from app.services.agents.hr.schemas import RiskTier, AutonomyLevel


def user(role="member", **kwargs):
    return SimpleNamespace(role=role, is_system_admin=False, is_superuser=False, **kwargs)


def test_hr_people_read_denies_regular_member():
    with pytest.raises(HTTPException) as exc:
        _require_hr_access(user("member"))
    assert exc.value.status_code == 403


def test_hr_people_write_denies_manager():
    with pytest.raises(HTTPException) as exc:
        _require_hr_access(user("manager"), write=True)
    assert exc.value.status_code == 403


def test_hr_people_write_allows_hr_admin():
    _require_hr_access(user("hr_admin"), write=True)


def test_workforce_approval_denies_recruiter():
    with pytest.raises(HTTPException) as exc:
        _require_hr_role(user("hr_recruiter"), approve=True)
    assert exc.value.status_code == 403


def test_workforce_approval_allows_hr_manager():
    _require_hr_role(user("hr_manager"), approve=True)


def test_unknown_agent_action_is_approval_gated():
    tier, autonomy, requires_approval = HRRiskClassifier.classify_action("employee.custom_write")
    assert tier == RiskTier.R3_MATERIAL
    assert autonomy == AutonomyLevel.L3_APPROVAL_GATED
    assert requires_approval is True


def test_high_consequence_action_never_runs_autonomously():
    tier, autonomy, requires_approval = HRRiskClassifier.classify_action("employee.terminate")
    assert tier == RiskTier.R4_HIGH_CONSEQUENCE
    assert autonomy == AutonomyLevel.L4_RESTRICTED
    assert requires_approval is True

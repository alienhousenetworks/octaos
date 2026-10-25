from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.hr_people import _require_hr_access
from app.api.v1.endpoints.hr_workforce import _require_hr_role, _as_utc
from app.models.hr_workforce import LeaveLedgerEntry
from app.services.agents.hr.risk_classifier import HRRiskClassifier
from app.services.agents.hr.schemas import RiskTier, AutonomyLevel


def user(role="member", permissions=(), **kwargs):
    return SimpleNamespace(
        role=role, is_system_admin=False, is_superuser=False,
        user_permissions=[SimpleNamespace(codename=code) for code in permissions],
        groups=[], **kwargs
    )


def test_hr_people_read_denies_regular_member():
    with pytest.raises(HTTPException) as exc:
        _require_hr_access(user("member"))
    assert exc.value.status_code == 403


def test_hr_people_write_denies_manager():
    with pytest.raises(HTTPException) as exc:
        _require_hr_access(user("manager"), write=True)
    assert exc.value.status_code == 403


def test_hr_people_write_allows_hr_admin():
    _require_hr_access(user("hr_admin", permissions=["hr.manage_employees"]), write=True)


def test_workforce_approval_denies_recruiter():
    with pytest.raises(HTTPException) as exc:
        _require_hr_role(user("hr_recruiter"), approve=True)
    assert exc.value.status_code == 403


def test_workforce_approval_allows_hr_manager():
    _require_hr_role(user("hr_manager", permissions=["hr.manage_leave"]), approve=True)


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


def test_leave_ledger_has_partial_unique_reference_index():
    indexes = {index.name: index for index in LeaveLedgerEntry.__table__.indexes}
    index = indexes["uq_leave_ledger_reference_once"]
    assert index.unique is True
    assert index.dialect_options["postgresql"]["where"] is not None
    assert index.dialect_options["sqlite"]["where"] is not None


def test_naive_attendance_timestamp_is_normalized_to_utc():
    value = datetime(2026, 10, 25, 9, 30)
    normalized = _as_utc(value)
    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 9

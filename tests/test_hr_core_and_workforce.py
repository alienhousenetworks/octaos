"""
Unit and integration tests for OctaOS HR Core, Workforce, and Agent Runtime.
Verifies employee identity, immutable leave ledgers, AI coverage impact, risk tiers, and approval bridge.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, Tenant, User
from app.models.enterprise import ApprovalRequest
from app.models.hr_core import EmployeeProfile, Department, CompanyPolicy
from app.models.hr_workforce import LeaveType, LeaveLedgerEntry, LeaveRequest, AttendanceRecord
from app.services.agents.hr.schemas import RiskTier, AutonomyLevel, CopilotChatRequest
from app.services.agents.hr.risk_classifier import HRRiskClassifier
from app.services.agents.hr.approval_bridge import HRApprovalBridge
from app.services.agents.hr.specialists.leave_impact import LeaveImpactSpecialist
from app.services.agents.hr.specialists.people_admin import PeopleAdminSpecialist
from app.services.agents.hr.orchestrator import HREnterpriseOrchestrator


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create dummy tenant and user
    t = Tenant(id="tenant-test-1", name="Acme Corp")
    u = User(id="user-test-1", tenant_id="tenant-test-1", email="admin@acme.com", role="admin", hashed_password="fakehashpassword123")
    session.add(t)
    session.add(u)
    session.commit()

    yield session
    session.close()


def test_employee_and_department_creation(test_db):
    dept = Department(tenant_id="tenant-test-1", name="Engineering", code="ENG")
    test_db.add(dept)
    test_db.commit()

    emp = EmployeeProfile(
        tenant_id="tenant-test-1",
        employee_number="EMP-0001",
        first_name="Alice",
        last_name="Smith",
        email="alice@acme.com",
        job_title="Staff Software Engineer",
        department_id=dept.id,
        department_name="Engineering",
        skills=["Python", "FastAPI", "React"]
    )
    test_db.add(emp)
    test_db.commit()

    assert emp.id is not None
    assert emp.full_name == "Alice Smith"
    assert emp.department_name == "Engineering"
    assert "Python" in emp.skills


def test_immutable_leave_ledger_balance_calculation(test_db):
    dept = Department(tenant_id="tenant-test-1", name="Engineering")
    test_db.add(dept)
    test_db.commit()

    emp = EmployeeProfile(
        tenant_id="tenant-test-1",
        employee_number="EMP-0002",
        first_name="Bob",
        last_name="Jones",
        email="bob@acme.com",
        job_title="DevOps Lead",
        department_id=dept.id
    )
    test_db.add(emp)

    ltype = LeaveType(
        tenant_id="tenant-test-1",
        name="Annual Leave",
        code="ANNUAL",
        annual_allowance_days=25.0
    )
    test_db.add(ltype)
    test_db.commit()

    evaluator = LeaveImpactSpecialist(test_db, "tenant-test-1")
    # Initial balance is 0
    assert evaluator.get_employee_balance(emp.id, ltype.id) == 0.0

    # 1. Annual Grant (+25 days)
    e1 = LeaveLedgerEntry(
        tenant_id="tenant-test-1",
        employee_id=emp.id,
        leave_type_id=ltype.id,
        transaction_type="grant",
        amount_days=25.0,
        note="2026 Annual Allocation"
    )
    test_db.add(e1)
    test_db.commit()
    assert evaluator.get_employee_balance(emp.id, ltype.id) == 25.0

    # 2. Approved Vacation Deduction (-5 days)
    e2 = LeaveLedgerEntry(
        tenant_id="tenant-test-1",
        employee_id=emp.id,
        leave_type_id=ltype.id,
        transaction_type="deduction",
        amount_days=-5.0,
        note="Trip to Hawaii"
    )
    test_db.add(e2)
    test_db.commit()
    assert evaluator.get_employee_balance(emp.id, ltype.id) == 20.0

    # 3. Cancelled Day Reversal (+1 day)
    e3 = LeaveLedgerEntry(
        tenant_id="tenant-test-1",
        employee_id=emp.id,
        leave_type_id=ltype.id,
        transaction_type="reversal",
        amount_days=1.0,
        note="Returned early by 1 day"
    )
    test_db.add(e3)
    test_db.commit()
    assert evaluator.get_employee_balance(emp.id, ltype.id) == 21.0


def test_leave_impact_and_coverage_simulation(test_db):
    dept = Department(tenant_id="tenant-test-1", name="Customer Support")
    test_db.add(dept)
    test_db.commit()

    # Create 3 support agents
    emp1 = EmployeeProfile(tenant_id="tenant-test-1", employee_number="EMP-10", first_name="Agent", last_name="One", email="a1@acme.com", job_title="Support", department_id=dept.id)
    emp2 = EmployeeProfile(tenant_id="tenant-test-1", employee_number="EMP-11", first_name="Agent", last_name="Two", email="a2@acme.com", job_title="Support", department_id=dept.id)
    emp3 = EmployeeProfile(tenant_id="tenant-test-1", employee_number="EMP-12", first_name="Agent", last_name="Three", email="a3@acme.com", job_title="Support", department_id=dept.id)
    test_db.add_all([emp1, emp2, emp3])

    ltype = LeaveType(tenant_id="tenant-test-1", name="Casual Leave", code="CASUAL", annual_allowance_days=10.0)
    test_db.add(ltype)
    test_db.commit()

    # Credit emp1 with 10 days
    test_db.add(LeaveLedgerEntry(tenant_id="tenant-test-1", employee_id=emp1.id, leave_type_id=ltype.id, transaction_type="grant", amount_days=10.0))
    test_db.commit()

    evaluator = LeaveImpactSpecialist(test_db, "tenant-test-1")
    s_date = datetime.now() + timedelta(days=5)
    e_date = s_date + timedelta(days=2)

    # Simulation 1: No peers on leave -> adequate coverage (2/3 peers in office = 67%)
    res1 = evaluator.evaluate_leave_request(emp1.id, "CASUAL", s_date, e_date, 3.0)
    assert res1.is_staffing_adequate is True
    assert res1.conflicting_leaves_count == 0
    assert res1.current_balance == 10.0
    assert res1.projected_balance == 7.0

    # Simulate Peer 2 already booked on leave
    booked_leave = LeaveRequest(
        tenant_id="tenant-test-1",
        employee_id=emp2.id,
        leave_type_id=ltype.id,
        start_date=s_date,
        end_date=e_date,
        days_requested=3.0,
        status="approved"
    )
    test_db.add(booked_leave)
    test_db.commit()

    # Simulation 2: Now emp1 requests overlapping days -> peer 2 is away -> only emp3 remains (1/3 = 33% -> critical)
    res2 = evaluator.evaluate_leave_request(emp1.id, "CASUAL", s_date, e_date, 3.0)
    assert res2.conflicting_leaves_count == 1
    assert res2.is_staffing_adequate is False
    assert res2.risk_tier == RiskTier.R3_MATERIAL
    assert res2.requires_approval is True


def test_risk_classifier_rules():
    # R0 Read-only
    tier, autonomy, req_app = HRRiskClassifier.classify_action("policy.query")
    assert tier == RiskTier.R0_READ_ONLY
    assert req_app is False

    # R1 Draft
    tier, autonomy, req_app = HRRiskClassifier.classify_action("leave.simulate_coverage")
    assert tier == RiskTier.R1_LOW_IMPACT
    assert req_app is False

    # R3 Material
    tier, autonomy, req_app = HRRiskClassifier.classify_action("leave.approve")
    assert tier == RiskTier.R3_MATERIAL
    assert req_app is True

    # R4 High Consequence
    tier, autonomy, req_app = HRRiskClassifier.classify_action("employee.terminate")
    assert tier == RiskTier.R4_HIGH_CONSEQUENCE
    assert req_app is True


def test_approval_bridge_and_mutation_detection(test_db):
    bridge = HRApprovalBridge(test_db, "tenant-test-1")

    payload = {"employee_id": "emp-1", "days": 5, "start_date": "2026-11-01"}
    req = bridge.submit_for_approval(
        action_type="leave.approve",
        title="Approve 5 days leave",
        resource_id="emp-1",
        payload=payload,
        rationale="Coverage verified",
        requested_by="user-test-1",
        risk_tier=RiskTier.R3_MATERIAL
    )

    assert req.id is not None
    assert req.status == "pending"

    # Cannot authorize while status is 'pending'
    assert bridge.verify_authorization(req.id, payload) is False

    # Mark approved by manager
    req.status = "approved"
    test_db.commit()

    # Exactly matching payload authorizes cleanly
    assert bridge.verify_authorization(req.id, payload) is True

    # Tampered / mutated payload (e.g. days secretly altered from 5 to 50) is detected and rejected!
    mutated_payload = {"employee_id": "emp-1", "days": 50, "start_date": "2026-11-01"}
    assert bridge.verify_authorization(req.id, mutated_payload) is False


def test_people_admin_policy_rag(test_db):
    p1 = CompanyPolicy(
        tenant_id="tenant-test-1",
        title="Remote Work & Hybrid Schedule Policy",
        category="remote",
        summary="Employees can work up to 2 days remotely per week with manager approval.",
        content="Full policy details for remote work..."
    )
    test_db.add(p1)
    test_db.commit()

    specialist = PeopleAdminSpecialist(test_db, "tenant-test-1")
    result = specialist.query_policy("Can I work remotely two days a week?")

    assert len(result.evidence) > 0
    assert "Remote Work & Hybrid Schedule Policy" in result.summary
    assert result.findings[0].code == "POLICY_FOUND"


@pytest.mark.asyncio
async def test_universal_hr_copilot_guardrails_and_leave_query(test_db):
    dept = Department(tenant_id="tenant-test-1", name="Engineering")
    test_db.add(dept)
    test_db.commit()

    emp = EmployeeProfile(
        tenant_id="tenant-test-1",
        employee_number="EMP-0099",
        first_name="Diana",
        last_name="Prince",
        email="diana@acme.com",
        job_title="Security Lead",
        department_id=dept.id
    )
    test_db.add(emp)
    test_db.commit()

    orchestrator = HREnterpriseOrchestrator(test_db, "tenant-test-1", "user-test-1")

    # 1. Guardrail test: Hostile / unapproved termination command is strictly blocked
    res_blocked = await orchestrator.handle_message(CopilotChatRequest(message="Please fire them immediately"))
    assert res_blocked.autonomy_level == AutonomyLevel.L4_RESTRICTED
    assert "Restricted" in res_blocked.reply

    # 2. Leave coverage analysis test
    res_leave = await orchestrator.handle_message(CopilotChatRequest(message="Check whether approving this leave request will create a staffing gap"))
    assert res_leave.specialist_agent == "Leave & Workforce Impact Agent"
    assert res_leave.task_result is not None
    assert "Coverage Assessment" in res_leave.reply

    # 3. Employee count query: "how many emplyee are there"
    res_count = await orchestrator.handle_message(CopilotChatRequest(message="how many emplyee are there"))
    assert "1 active employee" in res_count.reply.lower() or "1" in res_count.reply
    assert "Try asking:" not in res_count.reply

    # 4. Greeting / typo query: "hwq"
    res_greet = await orchestrator.handle_message(CopilotChatRequest(message="hwq"))
    assert "Try asking:" not in res_greet.reply
    assert len(res_greet.reply) > 10

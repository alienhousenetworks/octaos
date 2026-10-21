"""
Leave Impact Specialist Agent.
Provides deterministic leave ledger balance calculation and AI team coverage impact assessment.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.hr_core import EmployeeProfile
from app.models.hr_workforce import LeaveType, LeaveLedgerEntry, LeaveRequest
from app.services.agents.hr.schemas import (
    LeaveCoverageEvaluation,
    RiskTier,
    AgentTaskResult,
    EvidenceReference,
    Finding,
    ProposedAction
)
from app.services.agents.hr.risk_classifier import HRRiskClassifier


class LeaveImpactSpecialist:
    """Evaluates employee leave requests against balance ledgers and department coverage."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def get_employee_balance(self, employee_id: str, leave_type_id: str) -> float:
        """Sums immutable ledger transactions for an authoritative, tamper-evident balance."""
        res = self.db.query(func.coalesce(func.sum(LeaveLedgerEntry.amount_days), 0.0)).filter(
            LeaveLedgerEntry.tenant_id == self.tenant_id,
            LeaveLedgerEntry.employee_id == employee_id,
            LeaveLedgerEntry.leave_type_id == leave_type_id
        ).scalar()
        return float(res)

    def evaluate_leave_request(
        self,
        employee_id: str,
        leave_type_code: str,
        start_date: datetime,
        end_date: datetime,
        days_requested: float
    ) -> LeaveCoverageEvaluation:
        # 1. Fetch employee
        emp = self.db.query(EmployeeProfile).filter_by(
            id=employee_id, tenant_id=self.tenant_id
        ).first()
        if not emp:
            raise ValueError(f"Employee {employee_id} not found in tenant {self.tenant_id}")

        # 2. Fetch leave type
        ltype = self.db.query(LeaveType).filter_by(
            tenant_id=self.tenant_id, code=leave_type_code.upper()
        ).first()
        if not ltype:
            # Fallback or create default if first run
            ltype = self.db.query(LeaveType).filter_by(tenant_id=self.tenant_id).first()
            if not ltype:
                ltype = LeaveType(
                    tenant_id=self.tenant_id,
                    name="Annual Leave",
                    code="ANNUAL",
                    annual_allowance_days=20.0
                )
                self.db.add(ltype)
                self.db.commit()
                self.db.refresh(ltype)

        # 3. Calculate Ledger Balance
        current_balance = self.get_employee_balance(employee_id, ltype.id)
        projected_balance = current_balance - days_requested

        # 4. Department Staffing Coverage Simulation
        dept_id = emp.department_id
        dept_coworkers_count = self.db.query(EmployeeProfile).filter(
            EmployeeProfile.tenant_id == self.tenant_id,
            EmployeeProfile.department_id == dept_id,
            EmployeeProfile.status == "active"
        ).count() if dept_id else 5

        # Fallback to minimum 1
        team_size = max(dept_coworkers_count, 1)

        # Query overlapping leaves for peers in same department
        overlapping_leaves = self.db.query(LeaveRequest).join(
            EmployeeProfile, LeaveRequest.employee_id == EmployeeProfile.id
        ).filter(
            LeaveRequest.tenant_id == self.tenant_id,
            LeaveRequest.status.in_(["approved", "pending"]),
            LeaveRequest.employee_id != employee_id,
            EmployeeProfile.department_id == dept_id,
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).count() if dept_id else 0

        # Calculate coverage score
        remaining_in_office = max(0, team_size - overlapping_leaves - 1)
        coverage_score = round(remaining_in_office / team_size, 2)
        is_adequate = coverage_score >= 0.5  # At least 50% staffing retained

        # Determine Risk Tier
        if not is_adequate:
            risk = RiskTier.R3_MATERIAL
            requires_approval = True
            explanation = (
                f"Coverage score is critical ({int(coverage_score*100)}%). "
                f"{overlapping_leaves} peer(s) already scheduled off during this window. "
                f"Team size: {team_size}, remaining in office: {remaining_in_office}."
            )
        elif projected_balance < 0:
            risk = RiskTier.R3_MATERIAL
            requires_approval = True
            explanation = (
                f"Insufficient balance. Current balance is {current_balance} days, requested {days_requested} days. "
                f"Projected balance will be negative ({projected_balance} days)."
            )
        else:
            risk = RiskTier.R2_REVERSIBLE
            requires_approval = ltype.requires_approval
            explanation = (
                f"Adequate team coverage ({int(coverage_score*100)}%). "
                f"No major staffing collisions detected. Balance is sufficient."
            )

        return LeaveCoverageEvaluation(
            employee_id=emp.id,
            employee_name=emp.full_name,
            leave_type=ltype.name,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            days_requested=days_requested,
            current_balance=current_balance,
            projected_balance=projected_balance,
            coverage_score=coverage_score,
            is_staffing_adequate=is_adequate,
            conflicting_leaves_count=overlapping_leaves,
            department_team_size=team_size,
            active_in_office_count=remaining_in_office,
            risk_tier=risk,
            requires_approval=requires_approval,
            explanation=explanation
        )

"""
OctaOS HR Workforce & Compensation Models.
Defines immutable leave ledgers, leave requests, daily attendance punches, and shift rosters.
"""
import uuid
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Integer, Float, Text, JSON,
    UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.models.base import Base


def _id() -> str:
    return str(uuid.uuid4())


class LeaveType(Base):
    """Configured leave category (Annual, Sick, Casual, Parental, Unpaid)."""
    __tablename__ = "hr_leave_types"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)  # ANNUAL, SICK, CASUAL, PARENTAL, UNPAID
    annual_allowance_days = Column(Float, nullable=False, default=15.0)
    requires_approval = Column(Boolean, nullable=False, default=True)
    requires_documentation = Column(Boolean, nullable=False, default=False)
    is_paid = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_leave_type_tenant_code"),
    )


class LeaveLedgerEntry(Base):
    """
    Immutable ledger of leave transactions.
    Balance is always derived by summing ledger amounts:
    SUM(amount_days) WHERE employee_id and leave_type_id.
    """
    __tablename__ = "hr_leave_ledger_entries"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    leave_type_id = Column(String, ForeignKey("hr_leave_types.id"), nullable=False, index=True)
    transaction_type = Column(String, nullable=False)  # accrual, grant, deduction, reversal, carryover
    amount_days = Column(Float, nullable=False)  # positive for grants/accruals, negative for usage
    reference_id = Column(String, nullable=True, index=True)  # e.g., leave_request_id
    note = Column(String, nullable=True)
    created_by_user_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "uq_leave_ledger_reference_once",
            "tenant_id", "transaction_type", "reference_id",
            unique=True,
            postgresql_where=reference_id.is_not(None),
            sqlite_where=reference_id.is_not(None),
        ),
    )


class LeaveRequest(Base):
    """Formal employee leave application with AI coverage assessment and approval routing."""
    __tablename__ = "hr_leave_requests"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    leave_type_id = Column(String, ForeignKey("hr_leave_types.id"), nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    days_requested = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    
    # State & Governance
    status = Column(String, nullable=False, default="pending", index=True)  # pending, approved, rejected, cancelled
    approver_user_id = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # AI Coverage & Risk Assessment
    coverage_score = Column(Float, nullable=True)  # 0.0 to 1.0 (1.0 = perfect coverage, 0.0 = critical gap)
    conflict_count = Column(Integer, nullable=False, default=0)
    ai_risk_level = Column(String, nullable=True, default="low")  # low, medium, high
    ai_coverage_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AttendanceRecord(Base):
    """Daily employee punch timesheet with anomaly detection."""
    __tablename__ = "hr_attendance_records"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    work_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    clock_in = Column(DateTime(timezone=True), nullable=True)
    clock_out = Column(DateTime(timezone=True), nullable=True)
    break_minutes = Column(Integer, nullable=False, default=60)
    total_hours = Column(Float, nullable=False, default=0.0)
    
    status = Column(String, nullable=False, default="present")  # present, absent, half_day, late, on_leave
    anomaly_detected = Column(Boolean, nullable=False, default=False)
    anomaly_type = Column(String, nullable=True)  # missing_clock_out, late_arrival, unauthorized_overtime
    is_verified = Column(Boolean, nullable=False, default=False)
    correction_note = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_id", "work_date", name="uq_attendance_emp_date"),
    )


class ShiftRoster(Base):
    """Scheduled shift planning period for a department or location."""
    __tablename__ = "hr_shift_rosters"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    department_id = Column(String, ForeignKey("hr_departments.id"), nullable=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Engineering Week 43 2026"
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="draft")  # draft, published, archived
    is_optimized = Column(Boolean, nullable=False, default=False)
    optimization_score = Column(Float, nullable=True)
    constraint_violations = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ShiftAssignment(Base):
    """Individual shift assignment for an employee within a roster."""
    __tablename__ = "hr_shift_assignments"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    roster_id = Column(String, ForeignKey("hr_shift_rosters.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    shift_name = Column(String, nullable=False)  # Morning (09:00 - 17:00), Evening, Night, On-Call
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    role_required = Column(String, nullable=True)
    status = Column(String, nullable=False, default="scheduled")  # scheduled, swapped, completed, absent
    created_at = Column(DateTime(timezone=True), server_default=func.now())



class AttendanceAuditEvent(Base):
    """Append-only record of attendance changes; corrections require a separate authorized event."""
    __tablename__ = "hr_attendance_audit_events"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    attendance_record_id = Column(String, ForeignKey("hr_attendance_records.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    actor_user_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # clock_in, clock_out, correction_requested
    occurred_at_utc = Column(DateTime(timezone=True), nullable=False)
    local_timezone = Column(String, nullable=False, default="UTC")
    local_work_date = Column(String, nullable=False)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=False)
    source = Column(String, nullable=False, default="self_service")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmployeeAvailability(Base):
    """Employee availability window used by workforce scheduling."""
    __tablename__ = "hr_employee_availability"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False, index=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, default="available")  # available, unavailable, leave
    source = Column(String, nullable=False, default="employee")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="chk_hr_availability_window"),
    )


class ShiftDemand(Base):
    """Explicit staffing demand; optimizer must not invent required coverage."""
    __tablename__ = "hr_shift_demands"

    id = Column(String, primary_key=True, default=_id)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    roster_id = Column(String, ForeignKey("hr_shift_rosters.id"), nullable=False, index=True)
    shift_name = Column(String, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    role_required = Column(String, nullable=True)
    required_headcount = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "roster_id", "shift_name", "starts_at", "role_required", name="uq_hr_shift_demand_slot"),
        CheckConstraint("ends_at > starts_at", name="chk_hr_shift_demand_window"),
        CheckConstraint("required_headcount >= 1", name="chk_hr_shift_demand_headcount"),
    )

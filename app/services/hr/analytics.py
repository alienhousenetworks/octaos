"""Recruitment metrics from stored rows. Missing inputs return insufficient_data, never zero."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.hr import Application, HRCostEntry, JobRequisition, StageTransition
from app.models.workflows import Workflow


def envelope(metric: str, status: str, value: Any, unit: str, sample_size: int, missing: List[str]) -> Dict[str, Any]:
    return {
        "metric": metric,
        "status": status,
        "value": value,
        "unit": unit,
        "sample_size": sample_size,
        "missing": missing,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


class RecruitmentAnalytics:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def time_to_fill(self) -> Dict[str, Any]:
        reqs = self.db.query(JobRequisition).filter_by(tenant_id=self.tenant_id).all()
        if not any(r.opened_at_confirmed and r.opened_at for r in reqs):
            return envelope("time_to_fill", "insufficient_data", None, "days", 0, ["opened_at_confirmed"])
        samples = []
        for req in reqs:
            if not req.opened_at_confirmed or not req.opened_at:
                continue
            hires = (
                self.db.query(StageTransition)
                .join(Application, Application.id == StageTransition.application_id)
                .filter(
                    Application.requisition_id == req.id,
                    StageTransition.to_stage == "hired",
                )
                .all()
            )
            for hire in hires:
                if hire.created_at and req.opened_at:
                    samples.append((hire.created_at - req.opened_at).total_seconds() / 86400)
        if not samples:
            return envelope("time_to_fill", "insufficient_data", None, "days", 0, ["hired_stage"])
        return envelope("time_to_fill", "ok", round(sum(samples) / len(samples), 2), "days", len(samples), [])

    def source_quality(self) -> Dict[str, Any]:
        apps = self.db.query(Application).filter_by(tenant_id=self.tenant_id).all()
        terminal = [a for a in apps if a.status in {"hired", "rejected"} or a.current_stage in {"hired", "offer"}]
        if len(terminal) < 5:
            return envelope("source_quality", "insufficient_data", None, "ratio", len(terminal), ["sample_size"])
        hired = [a for a in terminal if a.status == "hired" or a.current_stage == "hired"]
        return envelope("source_quality", "ok", round(len(hired) / len(terminal), 4), "ratio", len(terminal), [])

    def workload(self) -> Dict[str, Any]:
        apps = self.db.query(Application).filter_by(tenant_id=self.tenant_id, status="active").all()
        buckets: Dict[str, int] = {}
        for app in apps:
            req = self.db.query(JobRequisition).filter_by(id=app.requisition_id).first()
            key = (req.recruiter_user_id if req and req.recruiter_user_id else "unassigned")
            buckets[key] = buckets.get(key, 0) + 1
        return envelope("workload", "ok", buckets, "applications", len(apps), [])

    def plan_vs_actual(self) -> Dict[str, Any]:
        reqs = self.db.query(JobRequisition).filter_by(tenant_id=self.tenant_id).all()
        if any(r.headcount_approved is None for r in reqs):
            return envelope("plan_vs_actual", "insufficient_data", None, "headcount", len(reqs), ["headcount_approved"])
        approved = sum(r.headcount_approved or 0 for r in reqs)
        filled = sum(r.headcount_filled or 0 for r in reqs)
        return envelope("plan_vs_actual", "ok", {"approved": approved, "filled": filled}, "headcount", len(reqs), [])

    def workflow_completion_rate(self) -> Dict[str, Any]:
        rows = self.db.query(Workflow).filter_by(tenant_id=self.tenant_id, vertical="hr").all()
        running_family = [r for r in rows if r.status in {"RUNNING", "COMPLETED", "CANCELLED"}]
        if not any(r.status == "RUNNING" or r.status in {"COMPLETED", "CANCELLED"} for r in rows):
            if not any(r.status == "RUNNING" for r in rows) and not any(r.status in {"COMPLETED", "CANCELLED"} for r in rows):
                return envelope("workflow_completion_rate", "insufficient_data", None, "ratio", 0, ["running_anchor"])
        if not running_family:
            return envelope("workflow_completion_rate", "insufficient_data", None, "ratio", 0, ["running_anchor"])
        done = [r for r in running_family if r.status in {"COMPLETED", "CANCELLED"}]
        return envelope("workflow_completion_rate", "ok", round(len(done) / len(running_family), 4), "ratio", len(running_family), [])

    def cost_per_hire(self) -> Dict[str, Any]:
        costs = self.db.query(HRCostEntry).filter_by(tenant_id=self.tenant_id).all()
        hires = self.db.query(Application).filter_by(tenant_id=self.tenant_id, status="hired").count()
        if not costs or not hires:
            return envelope("cost_per_hire", "insufficient_data", None, "currency", hires, ["hr_cost_entries" if not costs else "hires"])
        total = sum(float(c.amount) for c in costs)
        return envelope("cost_per_hire", "ok", round(total / hires, 2), costs[0].currency, hires, [])

    def metric(self, name: str) -> Dict[str, Any]:
        methods = {
            "time_to_fill": self.time_to_fill,
            "source_quality": self.source_quality,
            "workload": self.workload,
            "plan_vs_actual": self.plan_vs_actual,
            "workflow_completion_rate": self.workflow_completion_rate,
            "cost_per_hire": self.cost_per_hire,
        }
        fn = methods.get(name)
        if not fn:
            return envelope(name, "insufficient_data", None, "", 0, ["unknown_metric"])
        return fn()

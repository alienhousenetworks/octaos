from typing import Any, Dict

from app.core.rbac import normalize_role

SALARY_KEYS = {
    "salary", "base_amount", "min_amount", "mid_amount", "max_amount",
    "financial_impact", "legacy_salary_text", "salary_expectation", "amount",
}
NOTE_KEYS = {"notes", "interview_notes", "free_text"}
RECRUITER_ROLES = {"hr_recruiter", "agent", "member", "employee", "read_only"}
ADMIN_EQ = {"hr_admin", "admin", "super_admin", "organization_admin"}


class HRFieldPolicy:
    def __init__(self, role: str):
        self.raw = (role or "agent").lower()
        self.role = normalize_role(role or "agent")

    def can_see_salary(self, authored_by: str | None = None, viewer_id: str | None = None) -> bool:
        if self.role in ADMIN_EQ or self.raw in ADMIN_EQ or self.role == "executive":
            return True
        if self.role in {"hr_hiring_manager", "manager"} and authored_by and viewer_id and authored_by == viewer_id:
            return True
        return False

    def can_see_notes(self) -> bool:
        if self.role in ADMIN_EQ or self.raw in ADMIN_EQ:
            return True
        if self.role in {"hr_hiring_manager", "manager"}:
            return True
        return False

    def can_read_document(self, classification: str) -> bool:
        if classification == "identity":
            return self.role in ADMIN_EQ or self.raw in ADMIN_EQ
        if classification == "interview_notes":
            return self.can_see_notes()
        if classification == "compensation":
            return self.can_see_salary()
        if self.role == "executive":
            return classification == "recruiting"
        if self.role == "read_only":
            return False
        return True

    def redact(self, payload: Dict[str, Any], authored_by: str | None = None, viewer_id: str | None = None) -> Dict[str, Any]:
        hidden_salary = not self.can_see_salary(authored_by, viewer_id)
        hidden_notes = not self.can_see_notes()
        return _walk(payload, hidden_salary, hidden_notes)


def _walk(value: Any, hidden_salary: bool, hidden_notes: bool) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if hidden_salary and key in SALARY_KEYS:
                continue
            if hidden_notes and key in NOTE_KEYS:
                continue
            out[key] = _walk(item, hidden_salary, hidden_notes)
        return out
    if isinstance(value, list):
        return [_walk(item, hidden_salary, hidden_notes) for item in value]
    return value

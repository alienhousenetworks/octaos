from app.core.rbac import normalize_role

HR_ADMIN_EQ = {"hr_admin", "admin", "super_admin"}
R3 = "R3_EXTERNAL_IRREVERSIBLE"
R4 = "R4_FINANCIAL_CRITICAL"


def _role(role: str) -> str:
    normalized = normalize_role(role or "")
    return normalized


def can_decide(requester_role: str, approver_role: str, requester_id: str | None, approver_id: str) -> bool:
    if requester_id and requester_id == approver_id:
        return False
    req = _role(requester_role)
    appr = _role(approver_role)
    if req in {"hr_recruiter", "hr_hiring_manager", "manager", "agent"}:
        return appr in HR_ADMIN_EQ
    if req in HR_ADMIN_EQ:
        return appr in HR_ADMIN_EQ or appr == "executive"
    if req == "executive":
        return appr in HR_ADMIN_EQ
    return False


def r4_pair_ok(existing_roles: list[str], new_role: str) -> bool:
    roles = [_role(r) for r in existing_roles] + [_role(new_role)]
    has_admin = any(r in HR_ADMIN_EQ for r in roles)
    has_exec = any(r == "executive" for r in roles)
    return has_admin and has_exec

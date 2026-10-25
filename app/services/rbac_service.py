"""
OctaOS RBAC Service.
Manages system permissions catalogue, tenant-scoped default groups, and permission resolution.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.base import User
from app.models.rbac import Permission, Group


# Complete catalogue of standard permissions across OctaOS domains
SYSTEM_PERMISSIONS = [
    # Sales Domain
    {"name": "Can view leads & CRM", "codename": "sales.view_leads", "content_type": "sales", "description": "Access to view CRM leads, accounts, and contact intelligence"},
    {"name": "Can manage leads & contacts", "codename": "sales.manage_leads", "content_type": "sales", "description": "Create, edit, and update customer and prospect records"},
    {"name": "Can conduct field sales visits", "codename": "sales.field_visits", "content_type": "sales", "description": "Access to field sales dispatch, GPS shift telemetry, and site visits"},
    {"name": "Can view sales pipeline & analytics", "codename": "sales.view_pipeline", "content_type": "sales", "description": "View sales funnel analytics, stages, and metrics"},
    {"name": "Can manage deal rooms & CPQ", "codename": "sales.manage_deals", "content_type": "sales", "description": "Access deal rooms, price proposals, cost sheets, and contracts"},
    {"name": "Can allocate project sales teams", "codename": "sales.assign_projects", "content_type": "sales", "description": "Assign specialists and project leads to real estate properties"},

    # HR & People Domain
    {"name": "Can view employee directory", "codename": "hr.view_employees", "content_type": "hr", "description": "View organizational directory and employee profile cards"},
    {"name": "Can manage employee profiles", "codename": "hr.manage_employees", "content_type": "hr", "description": "Create, update, onboard, and offboard employees"},
    {"name": "Can view ATS candidate pipeline", "codename": "hr.view_candidates", "content_type": "hr", "description": "View applicants, resumes, scores, and recruitment stages"},
    {"name": "Can manage hiring & interviews", "codename": "hr.manage_hiring", "content_type": "hr", "description": "Schedule candidate interviews, invite panelists, and manage stages"},
    {"name": "Can review and approve leave requests", "codename": "hr.manage_leave", "content_type": "hr", "description": "Approve or decline employee time-off and PTO requests"},
    {"name": "Can generate candidate offers", "codename": "hr.manage_offers", "content_type": "hr", "description": "Generate employment contracts and send offer letters"},
    {"name": "Can manage workforce scheduling", "codename": "hr.manage_workforce", "content_type": "hr", "description": "Manage attendance policies, shift rosters, staffing demand, and schedule publication"},
    {"name": "Can manage performance reviews", "codename": "hr.manage_performance", "content_type": "hr", "description": "Create, submit, and administer performance review cycles"},
    {"name": "Can manage compensation proposals", "codename": "hr.manage_compensation", "content_type": "hr", "description": "Create compensation proposals and participate in authorized approval workflows"},
    {"name": "Can manage HR service desk", "codename": "hr.manage_service_requests", "content_type": "hr", "description": "Assign, update, and resolve internal employee service requests"},
    {"name": "Can manage onboarding and offboarding", "codename": "hr.manage_lifecycle", "content_type": "hr", "description": "Manage governed onboarding and offboarding checklists and verification"},

    # Marketing Domain
    {"name": "Can view marketing campaigns", "codename": "marketing.view_campaigns", "content_type": "marketing", "description": "View marketing calendar, campaign performance, and radar"},
    {"name": "Can manage marketing campaigns", "codename": "marketing.manage_campaigns", "content_type": "marketing", "description": "Create and edit omnichannel ad campaigns and cadences"},
    {"name": "Can publish social content", "codename": "marketing.publish_content", "content_type": "marketing", "description": "Approve and publish social media posts and newsletters"},
    {"name": "Can view marketing analytics", "codename": "marketing.view_analytics", "content_type": "marketing", "description": "Inspect ROI analytics, lead attribution, and traffic reports"},

    # Support Domain
    {"name": "Can view support tickets", "codename": "support.view_tickets", "content_type": "support", "description": "View customer service tickets and SLA status"},
    {"name": "Can manage support tickets", "codename": "support.manage_tickets", "content_type": "support", "description": "Assign, re-route, update priority, and resolve customer issues"},
    {"name": "Can reply to support conversations", "codename": "support.respond_conversations", "content_type": "support", "description": "Directly message customers across omni-channel support rooms"},

    # Executive & Boardroom Domain
    {"name": "Can view boardroom minutes", "codename": "ceo.view_boardroom", "content_type": "ceo", "description": "Access strategic boardroom discussions, minutes, and charters"},
    {"name": "Can trigger autonomous runs", "codename": "ceo.trigger_autonomous_runs", "content_type": "ceo", "description": "Trigger CEO autopilot actions and multi-agent workflows"},
    {"name": "Can sign off on approvals", "codename": "ceo.sign_approvals", "content_type": "ceo", "description": "Sign off on human-in-the-loop governance proposals"},

    # Administration Domain
    {"name": "Can manage users, groups & RBAC", "codename": "admin.manage_rbac", "content_type": "admin", "description": "Full access to create, edit, and assign roles, groups, and permissions"},
    {"name": "Can manage integrations & BYOK", "codename": "admin.manage_integrations", "content_type": "admin", "description": "Configure API keys, LLM gateways, and MCP integrations"},
    {"name": "Can view & manage billing", "codename": "admin.manage_billing", "content_type": "admin", "description": "Access subscription invoices, plans, and quota limits"},
    {"name": "Can manage system settings", "codename": "admin.manage_system_settings", "content_type": "admin", "description": "Update company branding, custom subdomains, and tenant configs"},
]


# Default group templates for new and existing tenants
DEFAULT_GROUP_TEMPLATES = [
    {
        "name": "Administrators",
        "description": "Full unrestricted administrative access to all OctaOS modules, users, and settings.",
        "permission_codenames": ["*"],  # All permissions
    },
    {
        "name": "Sales Team",
        "description": "Access to CRM pipeline, leads prospecting, deal desks, and field sales site visits.",
        "permission_codenames": [
            "sales.view_leads",
            "sales.manage_leads",
            "sales.field_visits",
            "sales.view_pipeline",
            "sales.manage_deals",
            "sales.assign_projects",
        ],
    },
    {
        "name": "HR & Talent Team",
        "description": "Responsible for candidate recruitment, employee directory, leave management, and offers.",
        "permission_codenames": [
            "hr.view_employees",
            "hr.manage_employees",
            "hr.view_candidates",
            "hr.manage_hiring",
            "hr.manage_leave",
            "hr.manage_offers",
            "hr.manage_workforce",
            "hr.manage_performance",
            "hr.manage_compensation",
            "hr.manage_service_requests",
            "hr.manage_lifecycle",
        ],
    },
    {
        "name": "Marketing Ops",
        "description": "Plan, execute, and monitor marketing campaigns, brand channels, and audience analytics.",
        "permission_codenames": [
            "marketing.view_campaigns",
            "marketing.manage_campaigns",
            "marketing.publish_content",
            "marketing.view_analytics",
        ],
    },
    {
        "name": "Customer Support",
        "description": "Respond to incoming customer inquiries, maintain support queues, and resolve tickets.",
        "permission_codenames": [
            "support.view_tickets",
            "support.manage_tickets",
            "support.respond_conversations",
        ],
    },
    {
        "name": "Executive Council",
        "description": "Participate in strategic governance, inspect boardroom deliberations, and execute oversight.",
        "permission_codenames": [
            "ceo.view_boardroom",
            "ceo.trigger_autonomous_runs",
            "ceo.sign_approvals",
            "sales.view_pipeline",
            "marketing.view_analytics",
            "hr.view_employees",
            "admin.manage_system_settings",
        ],
    },
]


def ensure_system_permissions(db: Session) -> Dict[str, Permission]:
    """
    Ensure all standard permissions exist in the database.
    Returns a dictionary mapping codename -> Permission model.
    """
    existing_perms = {p.codename: p for p in db.query(Permission).all()}
    created_any = False

    for spec in SYSTEM_PERMISSIONS:
        codename = spec["codename"]
        if codename not in existing_perms:
            perm = Permission(
                name=spec["name"],
                codename=codename,
                content_type=spec["content_type"],
                description=spec.get("description", ""),
            )
            db.add(perm)
            existing_perms[codename] = perm
            created_any = True

    if created_any:
        db.commit()

    return existing_perms


def ensure_tenant_default_groups(db: Session, tenant_id: str) -> List[Group]:
    """
    Ensure the standard default groups exist for a specific tenant and have
    the appropriate permissions assigned.
    """
    all_perms = ensure_system_permissions(db)
    existing_groups = {
        g.name.lower(): g
        for g in db.query(Group).filter(Group.tenant_id == tenant_id).all()
    }
    created_any = False
    result_groups = []

    for tmpl in DEFAULT_GROUP_TEMPLATES:
        name_lower = tmpl["name"].lower()
        group = existing_groups.get(name_lower)
        if not group:
            group = Group(
                tenant_id=tenant_id,
                name=tmpl["name"],
                description=tmpl["description"],
            )
            db.add(group)
            db.flush()
            existing_groups[name_lower] = group
            created_any = True

        # Assign permissions if missing
        target_perms: List[Permission] = []
        if "*" in tmpl["permission_codenames"]:
            target_perms = list(all_perms.values())
        else:
            for codename in tmpl["permission_codenames"]:
                if codename in all_perms:
                    target_perms.append(all_perms[codename])

        current_perm_ids = {p.id for p in group.permissions}
        for p in target_perms:
            if p.id not in current_perm_ids:
                group.permissions.append(p)
                created_any = True

        result_groups.append(group)

    if created_any:
        db.commit()

    return result_groups


def get_user_all_permissions(db: Session, user: User) -> Set[str]:
    """
    Compute effective set of permission codenames for a user.
    Django-style rule:
      1. Superusers and global system admins automatically have ALL permissions.
      2. Otherwise: Direct user permissions UNION permissions from all user's groups.
    """
    if getattr(user, "is_superuser", False) or getattr(user, "is_system_admin", False):
        all_perms = db.query(Permission.codename).all()
        return {p[0] for p in all_perms}

    effective_perms: Set[str] = set()

    # 1. Direct permissions
    if user.user_permissions:
        for p in user.user_permissions:
            effective_perms.add(p.codename)

    # 2. Group permissions
    if user.groups:
        for group in user.groups:
            if group.permissions:
                for p in group.permissions:
                    effective_perms.add(p.codename)

    return effective_perms


def user_has_perm(db: Session, user: User, perm_codename: str) -> bool:
    """
    Check if a user has a specific permission codename.
    """
    if getattr(user, "is_superuser", False) or getattr(user, "is_system_admin", False):
        return True

    effective = get_user_all_permissions(db, user)
    return perm_codename in effective


def user_is_salesperson(user: User) -> bool:
    """
    Determine if a user belongs to the Sales team / is a salesperson.
    Checks:
      1. User is member of a group with 'sales' in the name (e.g. 'Sales Team', 'Field Sales').
      2. User has 'sales' role or department == 'Sales'.
      3. User has explicit 'sales.field_visits' or 'sales.view_leads' direct permissions.
    """
    if getattr(user, "department", None) and user.department.lower() == "sales":
        return True

    if getattr(user, "role", None) and user.role.lower() in ("sales", "sales_agent", "salesperson"):
        return True

    if getattr(user, "groups", None):
        for g in user.groups:
            if "sales" in g.name.lower():
                return True

    return False


def user_is_hr(user: User) -> bool:
    """
    Determine if a user belongs strictly to the HR / People team.
    """
    if getattr(user, "department", None) and user.department.lower() in ("hr", "human resources", "people"):
        return True

    if getattr(user, "role", None) and user.role.lower() in ("hr", "hr_admin", "hr_recruiter", "recruiter"):
        return True

    if getattr(user, "groups", None):
        for g in user.groups:
            if "hr" in g.name.lower() or "talent" in g.name.lower():
                return True

    return False

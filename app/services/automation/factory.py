"""
Automation Engine Factory.
Resolves the Activepieces engine adapter based on tenant configuration or system defaults.
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.automations import AutomationTenantEnvironment
from app.services.automation.base import AutomationEngineAdapter
from app.services.automation.activepieces_adapter import ActivepiecesEngineAdapter


def get_automation_engine(tenant_id: str, db: Optional[Session] = None) -> AutomationEngineAdapter:
    """
    Returns the configured Activepieces engine adapter for the tenant.
    """
    if db:
        env = db.query(AutomationTenantEnvironment).filter_by(tenant_id=tenant_id).first()
        if env and env.workspace_url:
            return ActivepiecesEngineAdapter(base_url=env.workspace_url)

    # Platform default
    return ActivepiecesEngineAdapter()

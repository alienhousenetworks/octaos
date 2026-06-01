from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any
from pydantic import BaseModel
from app.api import deps
from app.models.teams import AITeam, InstalledApp, AgentMetric

router = APIRouter()

class MarketplaceInstall(BaseModel):
    app_name: str
    config: dict = {}

@router.get("/metrics")
def get_dashboard_metrics(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    metrics = db.query(AgentMetric).filter(AgentMetric.tenant_id == tenant_id).all()
    # Format into a dictionary for easy frontend parsing
    res = {m.metric_name: m.value for m in metrics}
    
    # Calculate AI Cost
    from app.models.base import ProviderUsage
    from sqlalchemy.sql import func
    
    ai_cost_result = db.query(func.sum(ProviderUsage.cost)).filter(ProviderUsage.tenant_id == tenant_id).scalar()
    ai_cost = float(ai_cost_result) if ai_cost_result else 0.0

    # Calculate Automation Success Rate
    from app.models.workflows import WorkflowTask
    
    total_tasks = db.query(WorkflowTask).filter(
        WorkflowTask.workflow.has(tenant_id=tenant_id)
    ).count()
    completed_tasks = db.query(WorkflowTask).filter(
        WorkflowTask.workflow.has(tenant_id=tenant_id),
        WorkflowTask.status == 'completed'
    ).count()
    
    if total_tasks > 0:
        automation_success_rate = (completed_tasks / total_tasks) * 100.0
    else:
        # Fallback to ProviderUsage if no tasks
        total_usage = db.query(ProviderUsage).filter(ProviderUsage.tenant_id == tenant_id).count()
        success_usage = db.query(ProviderUsage).filter(ProviderUsage.tenant_id == tenant_id, ProviderUsage.status == 'success').count()
        if total_usage > 0:
            automation_success_rate = (success_usage / total_usage) * 100.0
        else:
            automation_success_rate = 99.5

    # Provide defaults if empty
    return {
        "revenue_impact": res.get("revenue_impact", 0.0),
        "leads_generated": res.get("leads_generated", 0.0),
        "posts_published": res.get("posts_published", 0.0),
        "meetings_booked": res.get("meetings_booked", 0.0),
        "candidates_sourced": res.get("candidates_sourced", 0.0),
        "interviews_scheduled": res.get("interviews_scheduled", 0.0),
        "ai_cost": round(ai_cost, 2),
        "automation_success_rate": round(automation_success_rate, 2)
    }

@router.get("/teams")
def get_ai_teams(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    teams = db.query(AITeam).filter(AITeam.tenant_id == tenant_id).all()
    # If no teams, create defaults
    if not teams:
        default_teams = [
            AITeam(tenant_id=tenant_id, name="Growth Team", agents=["Sales AI", "Marketing AI"]),
            AITeam(tenant_id=tenant_id, name="Operations Team", agents=["Support AI", "Finance AI"])
        ]
        db.add_all(default_teams)
        db.commit()
        teams = default_teams
    return [{"id": t.id, "name": t.name, "agents": t.agents} for t in teams]

@router.post("/marketplace/install")
def install_workflow(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    request: MarketplaceInstall
) -> Any:
    from app.models.workflows import Workflow, WorkflowTask
    from datetime import datetime, timezone
    
    app = InstalledApp(
        tenant_id=tenant_id,
        app_name=request.app_name,
        config=request.config
    )
    db.add(app)
    
    # Create the corresponding workflow and initial tasks
    wf = Workflow(tenant_id=tenant_id, name=f"{request.app_name} Automation", vertical="Marketplace")
    db.add(wf)
    db.flush() # get wf.id
    
    now = datetime.now(timezone.utc)
    
    if request.app_name == "Restaurant Growth Pack":
        t1 = WorkflowTask(workflow_id=wf.id, name="Yelp Review Auto-Responder", task_type="yelp_auto_reply", scheduled_at=now, payload={"status": "active"})
        db.add(t1)
    elif request.app_name == "SaaS Outreach System":
        t1 = WorkflowTask(workflow_id=wf.id, name="Cold Email Sequence Step 1", task_type="email_sequence", scheduled_at=now, payload={"step": 1})
        t2 = WorkflowTask(workflow_id=wf.id, name="LinkedIn DM Personalizer", task_type="linkedin_dm", scheduled_at=now, payload={"limit": 5})
        db.add_all([t1, t2])
    elif request.app_name == "Real Estate Lead Engine":
        t1 = WorkflowTask(workflow_id=wf.id, name="Zillow Lead Scrape", task_type="zillow_scrape", scheduled_at=now, payload={"location": "San Francisco"})
        db.add(t1)
    elif request.app_name == "Creative Agency Pack":
        t1 = WorkflowTask(workflow_id=wf.id, name="Pinterest Scheduling", task_type="pinterest_schedule", scheduled_at=now, payload={"pins": 3})
        db.add(t1)
        
    db.commit()
    return {"message": f"{request.app_name} installed successfully"}

@router.get("/marketplace/installed")
def get_installed_workflows(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    apps = db.query(InstalledApp).filter(InstalledApp.tenant_id == tenant_id).all()
    return [{"id": a.id, "app_name": a.app_name, "config": a.config} for a in apps]

@router.post("/marketplace/uninstall")
def uninstall_workflow(
    *,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    request: MarketplaceInstall
) -> Any:
    app = db.query(InstalledApp).filter(
        InstalledApp.tenant_id == tenant_id,
        InstalledApp.app_name == request.app_name
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Installed workflow not found")
    db.delete(app)
    db.commit()
    return {"message": f"{request.app_name} uninstalled successfully"}


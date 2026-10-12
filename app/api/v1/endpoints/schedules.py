from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Optional, Dict
from pydantic import BaseModel
from datetime import datetime, timezone

from app.api import deps
from app.models.base import User
from app.models.schedules import ScheduledTrigger
from app.models.verticals import BusinessProfile
from app.core.rbac import Action, Resource, require_permission

router = APIRouter()

class ScheduleUpsertRequest(BaseModel):
    frequency: Optional[str] = "daily"
    time_of_day: Optional[str] = "15:00"
    day_of_week: Optional[int] = 0
    day_of_month: Optional[int] = 1
    interval_hours: Optional[int] = 1
    instructions: Optional[str] = ""
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True

@router.get("/{target_type}")
def get_schedule(
    target_type: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get active schedule and trigger details for a target agent (e.g. lead_generation, campaign_planner).
    """
    schedule = (
        db.query(ScheduledTrigger)
        .filter(
            ScheduledTrigger.tenant_id == tenant_id,
            ScheduledTrigger.target_type == target_type
        )
        .first()
    )

    if not schedule:
        # Default prompt presets
        default_instructions = ""
        if target_type in ("lead_generation", "prompt_sales_agent"):
            default_instructions = (
                "ROLE\n"
                "You are Sales Intelligence Analyst.\n"
                "Find observable digital marketing weakness or decision-makers we can reach this week.\n"
                "Prefer high-intent accounts fitting our ICP.\n"
                "WHAT WE SELL: B2B solutions tailored to qualified opportunities."
            )
        elif target_type == "configured_sales_engine":
            default_instructions = (
                "Execute structured B2B outbound campaign using configured enterprise profile, ICP criteria, and discovery providers."
            )
        elif target_type == "campaign_planner":
            default_instructions = (
                "ROLE\n"
                "You are Campaign Strategist and Creative Director.\n"
                "Plan and generate high-impact narrative marketing content for the upcoming cycle.\n"
                "Focus on thought leadership, client outcomes, product capabilities, and clear calls to action."
            )

        return {
            "id": None,
            "target_type": target_type,
            "frequency": "daily",
            "time_of_day": "15:00",
            "day_of_week": 0,
            "day_of_month": 1,
            "interval_hours": 1,
            "instructions": default_instructions,
            "config": {"days": 30, "cadence": "daily", "lead_count": 50},
            "is_active": True,
            "last_run_at": None,
            "next_run_at": None,
            "last_status": "idle",
            "last_error": None
        }

    return {
        "id": schedule.id,
        "target_type": schedule.target_type,
        "frequency": schedule.frequency,
        "time_of_day": schedule.time_of_day,
        "day_of_week": schedule.day_of_week,
        "day_of_month": schedule.day_of_month,
        "interval_hours": schedule.interval_hours,
        "instructions": schedule.instructions,
        "config": schedule.config or {},
        "is_active": schedule.is_active,
        "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "last_status": schedule.last_status,
        "last_error": schedule.last_error
    }


@router.post("/{target_type}")
def save_schedule(
    target_type: str,
    req: ScheduleUpsertRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create or update schedule trigger settings and compute the next scheduled run.
    """
    schedule = (
        db.query(ScheduledTrigger)
        .filter(
            ScheduledTrigger.tenant_id == tenant_id,
            ScheduledTrigger.target_type == target_type
        )
        .first()
    )

    if not schedule:
        schedule = ScheduledTrigger(
            tenant_id=tenant_id,
            target_type=target_type,
            name=f"{target_type.replace('_', ' ').title()} Trigger"
        )
        db.add(schedule)

    schedule.frequency = req.frequency or "daily"
    schedule.time_of_day = req.time_of_day or "15:00"
    schedule.day_of_week = req.day_of_week
    schedule.day_of_month = req.day_of_month
    schedule.interval_hours = req.interval_hours or 1
    schedule.instructions = req.instructions or ""
    schedule.config = req.config or {}
    schedule.is_active = req.is_active if req.is_active is not None else True

    # Compute next run time
    if schedule.is_active:
        schedule.next_run_at = schedule.calculate_next_run()
    else:
        schedule.next_run_at = None

    db.commit()
    db.refresh(schedule)

    return {
        "id": schedule.id,
        "target_type": schedule.target_type,
        "frequency": schedule.frequency,
        "time_of_day": schedule.time_of_day,
        "day_of_week": schedule.day_of_week,
        "day_of_month": schedule.day_of_month,
        "interval_hours": schedule.interval_hours,
        "instructions": schedule.instructions,
        "config": schedule.config or {},
        "is_active": schedule.is_active,
        "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "last_status": schedule.last_status,
        "message": "Schedule trigger saved successfully."
    }


@router.delete("/{target_type}")
def delete_schedule(
    target_type: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Deactivate or remove schedule for target agent.
    """
    schedule = (
        db.query(ScheduledTrigger)
        .filter(
            ScheduledTrigger.tenant_id == tenant_id,
            ScheduledTrigger.target_type == target_type
        )
        .first()
    )
    if schedule:
        schedule.is_active = False
        schedule.next_run_at = None
        db.commit()

    return {"message": f"Schedule for {target_type} deactivated."}


@router.post("/{target_type}/run-now")
async def run_schedule_now(
    target_type: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id),
    _: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Execute the scheduled workflow immediately in the background.
    """
    import asyncio
    import logging
    sched_logger = logging.getLogger(__name__)

    schedule = (
        db.query(ScheduledTrigger)
        .filter(
            ScheduledTrigger.tenant_id == tenant_id,
            ScheduledTrigger.target_type == target_type
        )
        .first()
    )

    instructions = schedule.instructions if schedule else None
    config = schedule.config or {} if schedule else {}

    if target_type in ("lead_generation", "prompt_sales_agent"):
        provider = config.get("provider", "auto")
        model = config.get("model")
        count = int(config.get("count") or config.get("lead_count") or 50)
        freshness = config.get("freshness") or "30_days"
        prompt_text = instructions or "Find high-intent B2B target accounts fitting current market opportunities."
        
        # Reset workflow status tagged as prompt_agent without mutating profile.extra_context
        profile = db.query(BusinessProfile).filter(BusinessProfile.tenant_id == tenant_id).first()
        if profile:
            profile.v3_workflow_status = {
                "workflow_type": "prompt_agent",
                "workflow_name": "Prompt-Based Sales Agent",
                "instructions": prompt_text,
                "status": "executing",
                "current_step": 1,
                "steps": {
                    "1": { "name": "Understand Directive & Synthesize Criteria", "status": "executing", "result": "Analyzing prompt directive..." },
                    "2": { "name": "Market Discovery", "status": "pending", "result": "" },
                    "3": { "name": "Lead Qualification", "status": "pending", "result": "" },
                    "4": { "name": "Pain Point Discovery", "status": "pending", "result": "" },
                    "5": { "name": "Decision Maker Discovery", "status": "pending", "result": "" },
                    "6": { "name": "Lead Scoring", "status": "pending", "result": "" },
                    "7": { "name": "Outreach Generation", "status": "pending", "result": "" },
                    "8": { "name": "Multi-Channel Outreach", "status": "pending", "result": "" },
                    "9": { "name": "Conversation AI", "status": "pending", "result": "" },
                    "10": { "name": "Meeting Conversion", "status": "pending", "result": "" }
                },
                "logs": [
                    "Initializing Scheduled Prompt-Based Sales Agent...",
                    f"Executing prompt directive: {prompt_text[:80]}..."
                ]
            }
            db.commit()

        # Run directly in background event loop
        async def _execute_scheduled_lead_gen():
            from app.db.session import SessionLocal
            from app.services.agents.sales import SalesAgent
            bg_db = SessionLocal()
            try:
                agent = SalesAgent(bg_db, tenant_id)
                await agent.run_sales_ai_v3_workflow(
                    provider=provider if provider != "auto" else None,
                    model=model,
                    count=count,
                    freshness=freshness,
                    mode="prompt_agent",
                    prompt_instructions=prompt_text,
                )
            except Exception as e:
                sched_logger.error(f"Error executing scheduled lead gen: {e}", exc_info=True)
            finally:
                bg_db.close()

        asyncio.create_task(_execute_scheduled_lead_gen())
        
        if schedule:
            schedule.last_run_at = datetime.now(timezone.utc)
            schedule.last_status = "running"
            schedule.next_run_at = schedule.calculate_next_run()
            db.commit()

        return {"message": "⚡ Scheduled Prompt-Based Sales Agent workflow initiated!"}

    elif target_type == "configured_sales_engine":
        provider = config.get("provider", "auto")
        model = config.get("model")
        count = int(config.get("count") or config.get("lead_count") or 50)
        freshness = config.get("freshness") or "30_days"

        profile = db.query(BusinessProfile).filter(BusinessProfile.tenant_id == tenant_id).first()
        if profile:
            profile.v3_workflow_status = {
                "workflow_type": "configured_engine",
                "workflow_name": "Configured Sales Engine",
                "status": "executing",
                "current_step": 1,
                "steps": {
                    "1": { "name": "Understand Service & Generate ICP", "status": "executing", "result": "Analyzing your product/service parameters..." },
                    "2": { "name": "Market Discovery", "status": "pending", "result": "" },
                    "3": { "name": "Lead Qualification", "status": "pending", "result": "" },
                    "4": { "name": "Pain Point Discovery", "status": "pending", "result": "" },
                    "5": { "name": "Decision Maker Discovery", "status": "pending", "result": "" },
                    "6": { "name": "Lead Scoring", "status": "pending", "result": "" },
                    "7": { "name": "Outreach Generation", "status": "pending", "result": "" },
                    "8": { "name": "Multi-Channel Outreach", "status": "pending", "result": "" },
                    "9": { "name": "Conversation AI", "status": "pending", "result": "" },
                    "10": { "name": "Meeting Conversion", "status": "pending", "result": "" }
                },
                "logs": [
                    "Initializing Scheduled Configured Sales Engine...",
                    "Loading structured business configuration & ICP targets."
                ]
            }
            db.commit()

        async def _execute_scheduled_configured_engine():
            from app.db.session import SessionLocal
            from app.services.agents.sales import SalesAgent
            bg_db = SessionLocal()
            try:
                agent = SalesAgent(bg_db, tenant_id)
                await agent.run_sales_ai_v3_workflow(
                    provider=provider if provider != "auto" else None,
                    model=model,
                    count=count,
                    freshness=freshness,
                    mode="configured_engine",
                )
            except Exception as e:
                sched_logger.error(f"Error executing scheduled configured engine: {e}", exc_info=True)
            finally:
                bg_db.close()

        asyncio.create_task(_execute_scheduled_configured_engine())

        if schedule:
            schedule.last_run_at = datetime.now(timezone.utc)
            schedule.last_status = "running"
            schedule.next_run_at = schedule.calculate_next_run()
            db.commit()

        return {"message": "⚙️ Scheduled Configured Sales Engine workflow initiated!"}

    elif target_type == "campaign_planner":
        from app.worker.tasks import generate_campaign_task
        topic = config.get("topic") or (instructions[:80] if instructions else "Quarterly Campaign")
        days = int(config.get("days", 30))
        platforms = config.get("platforms", ["linkedin", "instagram", "facebook"])
        
        params = {
            "topic": topic,
            "days": days,
            "platforms": platforms,
            "generate_images": config.get("generate_images", True),
            "instructions": instructions
        }
        generate_campaign_task.delay(tenant_id, params)

        if schedule:
            schedule.last_run_at = datetime.now(timezone.utc)
            schedule.last_status = "running"
            schedule.next_run_at = schedule.calculate_next_run()
            db.commit()

        return {"message": f"Autonomous {days}-day Campaign Planner workflow initiated!"}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported target_type: {target_type}")

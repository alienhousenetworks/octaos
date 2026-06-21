from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, List, Optional
from app.api import deps
from pydantic import BaseModel
from app.models.video import VideoProject, VideoAsset, VideoRender
from app.models.agents import ActivityLog
from datetime import datetime

router = APIRouter()

class VideoCreateRequest(BaseModel):
    prompt: str
    title: Optional[str] = "Untitled Video"

@router.post("/create")
def create_video_project(
    req: VideoCreateRequest,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    project = VideoProject(
        tenant_id=tenant_id,
        title=req.title,
        prompt=req.prompt,
        status="planning"
    )
    db.add(project)
    
    log = ActivityLog(
        tenant_id=tenant_id,
        agent_name="Video AI",
        action="Video Project Created",
        description=f"Created video project: {req.title}",
        status="success"
    )
    db.add(log)
    db.commit()
    db.refresh(project)
    
    # Trigger Celery workflow for video generation here
    from app.worker.tasks import plan_video_task
    plan_video_task.delay(tenant_id, project.id)
    
    return project

@router.get("/{project_id}")
def get_video_project(
    project_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    project = db.query(VideoProject).filter(VideoProject.id == project_id, VideoProject.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/{project_id}/render")
def trigger_video_render(
    project_id: str,
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    project = db.query(VideoProject).filter(VideoProject.id == project_id, VideoProject.tenant_id == tenant_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status == "rendering":
        raise HTTPException(status_code=400, detail="Video is already rendering")
    
    from app.worker.tasks import render_video_task
    render_video_task.delay(tenant_id, project.id)
    
    return {"status": "processing", "message": "Render task queued"}

@router.get("/")
def list_video_projects(
    db: Session = Depends(deps.get_db),
    tenant_id: str = Depends(deps.get_current_tenant_id)
) -> Any:
    return db.query(VideoProject).filter(VideoProject.tenant_id == tenant_id).order_by(VideoProject.created_at.desc()).all()

@router.get("/templates")
def list_video_templates() -> Any:
    return {
        "templates": [
            {"id": "linkedin_ad", "name": "LinkedIn Explainer", "duration": 30, "aspect_ratio": "16:9"},
            {"id": "instagram_reel", "name": "Instagram Reel Demo", "duration": 30, "aspect_ratio": "9:16"}
        ]
    }

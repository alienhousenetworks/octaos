from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.memory_service import MemoryService
from app.models.memory import ManagerFeedback
from pydantic import BaseModel

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ManagerFeedbackCreate(BaseModel):
    tenant_id: str
    department: str
    original_output: str
    edited_output: str
    manager_comment: str = None
    task_id: str = None

@router.post("/feedback")
def submit_feedback(feedback: ManagerFeedbackCreate, db: Session = Depends(get_db)):
    """
    Called by the UI when a human manager edits an AI generated action (e.g. an email draft).
    The delta is captured as feedback for the Learning Service.
    """
    memory_service = MemoryService(db, feedback.tenant_id)
    record = memory_service.submit_manager_feedback(
        department=feedback.department,
        original_output=feedback.original_output,
        edited_output=feedback.edited_output,
        manager_comment=feedback.manager_comment,
        task_id=feedback.task_id
    )
    return {"status": "success", "feedback_id": record.id}

@router.get("/feedback/pending/{tenant_id}")
def get_pending_feedback(tenant_id: str, db: Session = Depends(get_db)):
    """
    Get all unprocessed feedback for UI display or debugging.
    """
    feedbacks = db.query(ManagerFeedback).filter_by(tenant_id=tenant_id, is_processed=False).all()
    return {"feedbacks": feedbacks}

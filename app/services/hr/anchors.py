from sqlalchemy.orm import Session

from app.models.workflows import Workflow
from app.services.executive_os.state_machine import WorkflowState, validate_workflow_transition


def ensure_application_anchor(db: Session, tenant_id: str, application) -> Workflow:
    if application.workflow_id:
        existing = db.query(Workflow).filter_by(id=application.workflow_id, tenant_id=tenant_id).first()
        if existing:
            return existing
    workflow = Workflow(
        tenant_id=tenant_id,
        name=f"hr.application:{application.id}",
        vertical="hr",
        department="hr",
        status=WorkflowState.COMPILED.value,
    )
    db.add(workflow)
    db.flush()
    application.workflow_id = workflow.id
    db.flush()
    return workflow


def mark_running(db: Session, workflow: Workflow) -> None:
    current = workflow.status
    try:
        state = WorkflowState(current)
    except ValueError:
        workflow.status = WorkflowState.RUNNING.value
        return
    if state == WorkflowState.COMPILED and validate_workflow_transition(state, WorkflowState.RUNNING):
        workflow.status = WorkflowState.RUNNING.value
    elif state == WorkflowState.RUNNING:
        return

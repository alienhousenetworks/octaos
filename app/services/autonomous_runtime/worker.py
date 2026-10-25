"""Celery entry point for autonomous task execution."""
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.autonomous_work import AutonomousTask
from app.services.autonomous_runtime import AutonomousRuntime


@celery_app.task(name="octaos.execute_autonomous_task", bind=True, max_retries=0)
def execute_autonomous_task(self, task_id: str, tenant_id: str):
    db = SessionLocal()
    try:
        task = db.query(AutonomousTask).filter(
            AutonomousTask.id == task_id,
            AutonomousTask.tenant_id == tenant_id,
        ).first()
        if not task:
            return {"status": "not_found", "task_id": task_id}
        runtime = AutonomousRuntime(db)
        task = runtime.execute_registered_handler(task)
        return {
            "task_id": task.id,
            "status": task.status,
            "error_code": task.error_code,
            "blocker": task.blocker,
        }
    finally:
        db.close()

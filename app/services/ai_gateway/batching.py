from sqlalchemy.orm import Session
from app.models.base import AIBatchJob
from typing import List, Dict, Any, Optional
import datetime
import logging

logger = logging.getLogger(__name__)

class BatchExecutionEngine:
    @staticmethod
    def createBatch(db: Session, tenant_id: str, provider: str, model: str, tasks: List[Dict[str, Any]]) -> AIBatchJob:
        """
        Creates a new AIBatchJob record.
        """
        job = AIBatchJob(
            tenant_id=tenant_id,
            provider=provider,
            model=model,
            status="pending",
            total_tasks=len(tasks),
            completed_tasks=0,
            failed_tasks=0,
            results={"tasks": tasks, "completed": []}
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    async def submitToProvider(db: Session, batch_id: str, adapter: Any) -> AIBatchJob:
        """
        Submits the batch job. If supported natively, uses the adapter.
        Otherwise, queues a Celery worker to explicitly run an internal batch.
        """
        job = db.query(AIBatchJob).filter(AIBatchJob.id == batch_id).first()
        if not job:
            raise Exception("Batch job not found.")

        # Extract tasks
        tasks = job.results.get("tasks", [])
        
        job.status = "processing"
        db.commit()

        if adapter.supports_native_batching(job.model):
            try:
                logger.info(f"Submitting batch job {batch_id} natively to {job.provider}...")
                provider_batch_id = await adapter.submit_native_batch(tasks, job.model)
                job.provider_batch_id = provider_batch_id
                
                res = job.results or {}
                res["batch_type"] = "provider"
                job.results = res
                
                db.commit()
            except Exception as e:
                logger.error(f"Failed to submit native batch: {e}. Falling back to internal batching.")
                
                res = job.results or {}
                res["batch_type"] = "internal"
                job.results = res
                db.commit()
                
                # Fallback to local
                from app.worker.tasks import execute_local_batch_task
                execute_local_batch_task.delay(batch_id)
        else:
            # Execute local batch using Celery worker
            logger.info(f"Executing internal batch job {batch_id} for {job.provider} / {job.model} via Celery...")
            res = job.results or {}
            res["batch_type"] = "internal"
            job.results = res
            db.commit()
            
            from app.worker.tasks import execute_local_batch_task
            execute_local_batch_task.delay(batch_id)

        return job

    @staticmethod
    async def monitorBatch(db: Session, batch_id: str, adapter: Any) -> Dict[str, Any]:
        """
        Updates the status of a batch job. For native batches, calls the provider.
        """
        job = db.query(AIBatchJob).filter(AIBatchJob.id == batch_id).first()
        if not job:
            return {"status": "not_found"}

        if job.status in ["completed", "failed"]:
            res = job.results or {}
            return {
                "status": job.status,
                "completed_tasks": job.completed_tasks,
                "total_tasks": job.total_tasks,
                "batch_type": res.get("batch_type", "unknown"),
                "results": res.get("completed", []) if isinstance(res, dict) else []
            }

        # If it's a native batch and has provider_batch_id
        if job.provider_batch_id:
            try:
                status_data = await adapter.check_native_batch_status(job.provider_batch_id)
                if status_data["status"] == "completed":
                    job.status = "completed"
                    job.completed_tasks = status_data["completed_tasks"]
                    job.failed_tasks = job.total_tasks - status_data["completed_tasks"]
                    job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    job.results = {"completed": status_data["results"]}
                    
                    # Track usage and cost for completed tasks
                    # Calculate token usage and savings
                    # (This is handled by the caller or periodic tracking worker)
                elif status_data["status"] == "failed":
                    job.status = "failed"
                    job.completed_at = datetime.datetime.now(datetime.timezone.utc)
                else:
                    # Still processing
                    job.completed_tasks = status_data.get("completed_tasks", 0)
                
                db.commit()
            except Exception as e:
                logger.error(f"Error monitoring native batch {job.provider_batch_id}: {e}")
        
        res = job.results or {}
        return {
            "status": job.status,
            "completed_tasks": job.completed_tasks,
            "total_tasks": job.total_tasks,
            "batch_type": res.get("batch_type", "unknown"),
            "results": res.get("completed", []) if isinstance(res, dict) else []
        }

    @staticmethod
    def retryFailures(db: Session, batch_id: str) -> None:
        """
        Identifies failed tasks in an internal or native batch and schedules a retry.
        """
        job = db.query(AIBatchJob).filter(AIBatchJob.id == batch_id).first()
        if not job or job.status != "failed":
            return

        # Re-set status to pending to trigger reprocessing
        job.status = "pending"
        job.failed_tasks = 0
        db.commit()

        # Re-trigger local task queue
        from app.worker.tasks import execute_local_batch_task
        execute_local_batch_task.delay(batch_id)

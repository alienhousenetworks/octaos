import asyncio
import pytest
from app.db.session import SessionLocal
from app.models.base import Tenant
from app.models.workflows import Workflow, WorkflowTask
from app.services.agents.ceo import CEOService

@pytest.mark.asyncio
async def test_ceo_pipeline():
    db = SessionLocal()
    try:
        # Find or create a tenant
        tenant = db.query(Tenant).first()
        if not tenant:
            tenant = Tenant(name="Test Growth Inc", subdomain="test-growth")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"Created new test tenant: {tenant.id}")
        else:
            print(f"Using existing tenant: {tenant.id}")

        tenant_id = tenant.id
        service = CEOService(db, tenant_id)

        objective = "Help me grow my AI business."
        print(f"\n--- 1. Generating plan for objective: '{objective}' ---")
        
        # Use gemini as the provider for test stability
        workflow = await service.generate_plan(objective, provider="gemini")
        print(f"Created Workflow ID: {workflow.id} (Status: {workflow.status})")

        # Query and display tasks
        tasks = db.query(WorkflowTask).filter_by(workflow_id=workflow.id).all()
        print(f"Generated {len(tasks)} tasks:")
        for t in tasks:
            depends = t.payload.get("depends_on", [])
            print(f"  - [{t.status.upper()}] Task: {t.name} (Type: {t.task_type}, Dept: {t.payload.get('department')}, Depends: {depends})")

        print(f"\n--- 2. Executing Workflow DAG ---")
        await service.execute_workflow(workflow.id)

        # Refresh tasks
        db.refresh(workflow)
        tasks = db.query(WorkflowTask).filter_by(workflow_id=workflow.id).all()
        print(f"\nWorkflow Final Status: {workflow.status}")
        print("Tasks Execution Summary:")
        for t in tasks:
            print(f"  - [{t.status.upper()}] {t.name}")
            if t.result:
                report_preview = t.result.get("report", "")[:120]
                print(f"    Result Preview: {report_preview}...")

        # Display final wrap up report
        summary_task = next((t for t in tasks if t.task_type == "ceo_summary"), None)
        if summary_task and summary_task.result:
            print(f"\n=== CEO Final Executive Summary ===")
            print(summary_task.result.get("report"))

        assert workflow.status == "completed", "Workflow execution should succeed and complete."
        print("\nPipeline test completed successfully!")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_ceo_pipeline())

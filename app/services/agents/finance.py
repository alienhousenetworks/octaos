from app.services.agents.base import BaseAgent
from app.models.teams import AgentMetric

class FinanceAgent(BaseAgent):
    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "Finance AI")

    async def execute_task(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("parameters", {})
        
        if action == "track_roi":
            return await self._track_roi(params)
        return {"status": "Unknown action"}

    async def _track_roi(self, params: dict):
        amount = params.get("amount", 1500.0)
        self.log_activity("Track ROI", f"Updating revenue impact by ${amount}")
        
        metric = self.db.query(AgentMetric).filter(
            AgentMetric.tenant_id == self.tenant_id,
            AgentMetric.metric_name == "revenue_impact"
        ).first()
        
        if not metric:
            metric = AgentMetric(tenant_id=self.tenant_id, metric_name="revenue_impact", value=0.0)
            self.db.add(metric)
            
        metric.value += amount
        self.db.commit()
        
        return {"status": "success", "revenue_added": amount}

    async def daily_routine(self):
        self.log_activity("Daily Routine", "Reconciling daily ad spend.", status="success")

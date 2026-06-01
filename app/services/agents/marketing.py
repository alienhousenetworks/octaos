from app.services.agents.base import BaseAgent
from app.models.verticals import ContentPost
from app.models.teams import AgentMetric

class MarketingAgent(BaseAgent):
    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "Marketing AI")

    async def execute_task(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("parameters", {})
        
        if action == "create_posts":
            return await self._create_posts(params)
        elif action == "generate_campaign":
            return await self._generate_campaign(params)
        return {"status": "Unknown action"}

    async def _generate_campaign(self, params: dict):
        from app.worker.tasks import generate_campaign_task
        # Trigger Celery task in background
        generate_campaign_task.delay(self.tenant_id, params)
        self.log_activity("Campaign Generation", f"Queued 30-day campaign generation in the background.", status="pending")
        return {"status": "queued", "message": "30-day marketing campaign generation queued in the background."}

    async def _create_posts(self, params: dict):
        days = params.get("days", 3)
        topic = params.get("topic", "our business")
        platforms = params.get("platforms", ["linkedin"])
        
        knowledge = self.get_knowledge_context("Marketing")
        
        self.log_activity("Generate Content", f"Generating {days} days of content about {topic}")
        
        count = 0
        for day in range(1, days + 1):
            for platform in platforms:
                prompt = f"Create a short engaging post for {platform} about {topic}. {knowledge}"
                content = await self.llm.complete(prompt, model="claude-3-haiku-20240307")
                
                post = ContentPost(
                    tenant_id=self.tenant_id,
                    platform=platform,
                    content=content,
                    day=day,
                    approval_status="pending"
                )
                self.db.add(post)
                count += 1
        self.db.commit()

        metric = self.db.query(AgentMetric).filter(
            AgentMetric.tenant_id == self.tenant_id,
            AgentMetric.metric_name == "posts_generated",
        ).first()
        if not metric:
            metric = AgentMetric(tenant_id=self.tenant_id, metric_name="posts_generated", value=0.0)
            self.db.add(metric)
        metric.value += count
        self.db.commit()

        return {"status": "success", "generated_posts": count}

    async def daily_routine(self):
        self.log_activity("Daily Routine", "Auto-generating a daily awareness post.", status="success")
        await self._create_posts({"days": 1, "topic": "daily inspiration / company awareness", "platforms": ["linkedin"]})

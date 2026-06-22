import json
import logging
from sqlalchemy.orm import Session
from app.services.agents.base import BaseAgent
from app.models.video import VideoProject
from app.models.verticals import BusinessProfile

logger = logging.getLogger(__name__)

class VideoAgent(BaseAgent):
    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id, "Video Studio AI", "marketing")

    async def execute_task(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("parameters", {})
        
        if action == "plan_video":
            return await self.plan_video(params.get("project_id"))
        
        return {"status": "error", "message": f"Unknown action: {action}"}

    async def plan_video(self, project_id: str) -> dict:
        project = self.db.query(VideoProject).filter(VideoProject.id == project_id, VideoProject.tenant_id == self.tenant_id).first()
        if not project:
            return {"status": "error", "message": "Video project not found"}

        self.log_activity("Video Planning Started", f"Started planning for: {project.title}")
        
        # Get business profile for context
        profile = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
        biz_context = ""
        if profile:
            biz_context = f"""
Company Name: {profile.company_name}
Industry: {profile.industry}
Description: {profile.service_description}
USP: {profile.usp}
"""

        prompt = f"""
You are the AI Director for a Motion Graphics Video Studio.
Your task is to generate a structured JSON blueprint for a Remotion video.

USER REQUEST: {project.prompt}

BUSINESS CONTEXT:
{biz_context}

CONSTRAINTS:
- The video should be approximately {project.duration_seconds} seconds long.
- Use a 16:9 or 9:16 aspect ratio based on the user's request.
- The output MUST be valid JSON matching the exact schema below.

JSON SCHEMA:
{{
  "version": "1.0",
  "title": "String",
  "duration": {project.duration_seconds},
  "aspect_ratio": "16:9",
  "voiceover": "String (full script of the video narration)",
  "scenes": [
    {{
      "id": "scene_1",
      "type": "HeroScene",
      "duration": 5,
      "headline": "Main Text",
      "subheadline": "Secondary Text",
      "animation": "fade-in",
      "assets": [],
      "voiceover_segment": "Narration specifically for this scene"
    }}
  ]
}}

VALID SCENE TYPES: HeroScene, FeatureScene, TimelineScene, ComparisonScene, StatisticsScene, AgentScene, DashboardScene, QuoteScene, CTAScene, LogoReveal, OutroScene

Generate ONLY the JSON object. Do not wrap it in markdown code blocks.
"""

        result_str = ""
        try:
            # Let the LLMGateway figure out the best model or use the default
            result_str = await self.llm.complete(
                prompt=prompt,
                model=project.llm_model,
                provider=project.llm_provider,
                system_prompt="You are a JSON generating system. Output ONLY raw JSON."
            )
            
            # Clean up JSON using regex to find the first '{' and last '}'
            import re
            cleaned = result_str.strip()
            # Find JSON block
            json_match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group(1)
            else:
                raise Exception("No JSON object found in LLM response.")
            
            blueprint = json.loads(cleaned)
            
            project.blueprint = blueprint
            project.status = "planned"
            self.db.commit()
            
            self.log_activity("Video Planning Completed", f"Successfully planned: {project.title}")
            return {"status": "success", "blueprint": blueprint}
            
        except Exception as e:
            logger.error(f"Failed to generate video blueprint: {e}")
            project.status = "failed"
            project.blueprint = {"error": str(e), "raw_response": result_str}
            self.db.commit()
            self.log_activity("Video Planning Failed", str(e), "failed")
            return {"status": "error", "message": str(e)}

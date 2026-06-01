import json
from app.services.agents.base import BaseAgent
from app.services.agents.marketing import MarketingAgent
from app.services.agents.sales import SalesAgent
from app.services.agents.support import SupportAgent
from app.services.agents.finance import FinanceAgent
from app.services.agents.hr import HRAgent

from app.models.base import APICredential

class OrchestratorAgent(BaseAgent):
    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "Orchestrator AI")

    async def handle_prompt(self, prompt: str, provider: str = "anthropic", model: str = None) -> dict:
        # Check if the user is providing a key manually
        # e.g., "Here is my linkedin key: 12345"
        import re
        key_match = re.search(r'(?:key|token|credential|smtp|api key) is\s*[:=]?\s*([a-zA-Z0-9_\-\.\:\@\/]+)', prompt, re.IGNORECASE)
        provider_match = re.search(r'(linkedin|meta|facebook|instagram|twitter|gmail|whatsapp|apollo|hunter|google_places|google_calendar|smtp)', prompt, re.IGNORECASE)
        
        if key_match and provider_match:
            provider = provider_match.group(1).lower()
            key = key_match.group(1)
            from app.services.credentials import save_credential

            save_credential(self.db, self.tenant_id, provider, key)
            self.log_activity("Configuration", f"Saved {provider} API key.")
            return {"plan": {}, "results": [{"status": "success", "message": f"I've saved your {provider} configuration. What task should I execute next?"}]}

        # Get existing keys to inform the LLM
        creds = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id).all()
        configured_providers = [c.provider for c in creds]

        system_prompt = f"""You are the Orchestrator AI. Break down the user's high-level goal into tasks for specialized department agents.
Currently configured API keys/credentials: {configured_providers}.

Available Agents & Actions:
- Marketing:
  - "create_posts": parameters: {{"days": int, "topic": str, "platforms": list}}
  - "generate_campaign": parameters: {{"topic": str, "days": int, "platforms": list, "text_provider": str, "image_provider": str, "video_provider": str, "generate_images": bool, "generate_videos": bool}}
- Sales:
  - "generate_leads": parameters: {{"provider": "apollo" | "hunter" | "google_places" | "free_search" | "free_places", "query": str, "count": int}}
    * Lead Source Decision Rules:
      - Choose "free_search" (B2B public web directories/scraping simulation) or "free_places" (local business Google Maps scraping simulation) if:
        1. The user's prompt explicitly mentions "free", "no apollo", "no paid keys", "free sources", etc.
        2. OR the user doesn't specify a paid platform and the keys for "apollo", "hunter", or "google_places" are NOT in the configured credentials list.
      - If the user specifies "apollo", "hunter", or "google_places" but its key is missing and they didn't specify free, schedule "request_key" for that provider first.
      - For local brick-and-mortar business searches (e.g. "gyms in Boston", "plumbers in Texas"), prefer "google_places" (if key configured) or "free_places" (if no key/free requested).
      - For corporate B2B profiles (e.g. "software companies", "marketing agencies", "founders"), prefer "apollo" or "hunter" (if key configured) or "free_search" (if no key/free requested).
  - "sales_outreach": parameters: {{"channel": "smtp" | "gmail" | "whatsapp" | "free_outreach", "subject": str, "body_template": str}}
    * Outreach Channel Decision Rules:
      - If the user wants to email or contact, check if "smtp" or "gmail" key is configured. If "smtp" is configured, choose "smtp". If "gmail" is configured, choose "gmail".
      - If neither is configured but they asked to email, choose "smtp" as preferred, but if the key is missing, schedule "request_key" for "smtp".
      - If the user requests "whatsapp", check if "whatsapp" is configured. If not, schedule "request_key" for "whatsapp".
      - If they specify "free outreach" or "simulated outreach", choose "free_outreach".
  - "schedule_meeting": parameters: {{"tool": "google_calendar" | "free_scheduling", "count": int}}
    * Scheduling Tool Decision Rules:
      - If "google_calendar" key is configured, choose "google_calendar". Otherwise, default to "free_scheduling".
- HR:
  - "source_candidates": parameters: {{"role": str, "requirements": str, "salary": str, "count": int}}
  - "candidate_outreach": parameters: {{"channel": "smtp" | "gmail" | "free_outreach", "subject": str, "body_template": str, "candidate_id": str | None}}
    * Candidate Outreach Decision Rules:
      - If SMTP or gmail credentials aren't present in configured keys, choose "free_outreach".
  - "schedule_interview": parameters: {{"tool": "google_calendar" | "free_scheduling", "candidate_id": str | None}}
    * Interview Decision Rules:
      - If "google_calendar" key is configured, choose "google_calendar", otherwise default to "free_scheduling".

- System:
  - "request_key": parameters: {{"provider": str}} - use this to ask the user for a missing key (e.g. "smtp", "apollo", "google_places", "whatsapp", etc.).

If a task requires an external platform that is NOT in the configured keys list, and the task has no free fallback, or the user specifically demanded that paid platform, DO NOT schedule that task. Instead, return a single task with department 'System', action 'request_key', and parameters {{"provider": "missing_provider_name"}}.

Output MUST be valid JSON only.
Format:
{{
    "tasks": [
        {{"department": "Marketing" | "Sales" | "Support" | "Finance" | "HR" | "System", "action": "create_posts" | "generate_leads" | "sales_outreach" | "schedule_meeting" | "source_candidates" | "candidate_outreach" | "schedule_interview" | "request_key", "parameters": {{}}}}
    ]
}}"""
        response = await self.llm.complete(prompt=prompt, system_prompt=system_prompt, provider=provider, model=model)
        import logging
        logger = logging.getLogger(__name__)
        try:
            import re
            response_clean = response.strip()
            # Robust extraction of JSON substring
            json_match = re.search(r'\{.*\}', response_clean, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_clean
            plan = json.loads(json_str)
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to parse plan. Raw response: {response}. Error: {e}")
            print(f"[Orchestrator] Failed to parse plan. Raw response: {response}. Error: {e}")
            raise Exception(f"Failed to parse orchestrator plan. Error: {str(e)}. Raw response: {response[:200]}...")

        self.log_activity("Delegate Tasks", f"Delegated goal: '{prompt}'")
        
        results = []
        for task in plan.get("tasks", []):
            dept = task.get("department")
            if dept == "Marketing":
                agent = MarketingAgent(self.db, self.tenant_id)
                res = await agent.execute_task(task)
                results.append(res)
            elif dept == "Sales":
                agent = SalesAgent(self.db, self.tenant_id)
                res = await agent.execute_task(task)
                results.append(res)
            elif dept == "Support":
                agent = SupportAgent(self.db, self.tenant_id)
                res = await agent.execute_task(task)
                results.append(res)
            elif dept == "Finance":
                agent = FinanceAgent(self.db, self.tenant_id)
                res = await agent.execute_task(task)
                results.append(res)
            elif dept == "HR":
                agent = HRAgent(self.db, self.tenant_id)
                res = await agent.execute_task(task)
                results.append(res)
            elif dept == "System" and task.get("action") == "request_key":
                provider = task.get("parameters", {}).get("provider", "unknown")
                if provider == "smtp":
                    msg = "I need your SMTP outgoing mail credentials. Please reply with: 'My smtp credential is: smtp://username:password@smtp.mailtrap.io:2525'."
                else:
                    msg = f"I need your {provider} API key to complete this task. Please reply with 'My {provider} key is: [YOUR_KEY]'."
                self.log_activity("Action Required", msg)
                results.append({"status": "action_required", "message": msg})
            else:
                self.log_activity("Skip Task", f"No agent for {dept}", status="pending")
        return {"plan": plan, "results": results}

    async def run_daily_ops(self):
        self.log_activity("Daily Autonomous Ops", "Initiating morning routines for all agents.")
        
        marketing = MarketingAgent(self.db, self.tenant_id)
        await marketing.daily_routine()
        
        sales = SalesAgent(self.db, self.tenant_id)
        await sales.daily_routine()

        hr = HRAgent(self.db, self.tenant_id)
        await hr.daily_routine()
        
        return {"status": "Daily ops complete"}

import json
import logging
from typing import Optional, List, Dict, Any
from app.services.agents.base import BaseAgent
from app.services.agents.marketing import MarketingAgent
from app.services.agents.sales import SalesAgent
from app.services.agents.support import SupportAgent
from app.services.agents.finance import FinanceAgent
from app.services.agents.hr import HRAgent

from app.models.base import APICredential

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "Orchestrator AI")

    async def handle_prompt(
        self,
        prompt: str,
        provider: str = None,
        model: str = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> dict:
        from app.core.config import settings
        from app.services.ai_gateway import ai_gateway

        configured_provs = ai_gateway._get_configured_providers(self.db, self.tenant_id)
        if not provider or provider.lower() in ("auto", "none"):
            pref = getattr(settings, "DEFAULT_AI_PROVIDER", None) or ""
            if pref and (pref in configured_provs or ai_gateway._get_api_key(self.db, self.tenant_id, pref)):
                provider = pref
            elif configured_provs:
                provider = configured_provs[0]
            else:
                provider = pref or "openrouter"

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

        # Build structured multi-turn conversation history
        conversation_context = ""
        if messages:
            history_lines = []
            for m in messages:
                role = (m.get("role") or "").lower()
                content = (m.get("content") or "").strip()
                if not content or "Welcome to the Orchestrator AI Console" in content:
                    continue
                if role == "user":
                    history_lines.append(f"User: {content}")
                elif role in ("assistant", "system"):
                    history_lines.append(f"Orchestrator AI: {content}")
            if history_lines:
                conversation_context = "Previous Conversation History:\n" + "\n".join(history_lines)

        effective_prompt = prompt
        if conversation_context:
            effective_prompt = f"{conversation_context}\n\nCurrent User Request:\n{prompt}"

        # Intent routing: branch into analytics/hybrid vs execution
        from app.services.agents.intent_router import IntentRouter
        mode, confidence = IntentRouter.classify(prompt, messages=messages)

        if mode in ["analytics", "hybrid"]:
            from app.services.agents.executive_swarm import ExecutiveSwarmCoordinator
            coordinator = ExecutiveSwarmCoordinator(self.db, self.tenant_id)
            briefing = await coordinator.execute_report(
                prompt=effective_prompt,
                mode=mode,
                confidence=confidence,
                provider=provider,
                model=model,
            )
            self.log_activity("Executive Briefing", f"Generated C-Suite {mode.capitalize()} Briefing for '{prompt}'")
            return {
                "mode": mode,
                "briefing": briefing.model_dump(),
                "plan": briefing.draft_execution_plan or {},
                "results": [
                    {
                        "status": "success",
                        "message": briefing.briefing_text,
                    }
                ],
            }

        # Get existing keys to inform the LLM
        creds = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id).all()
        configured_providers = [c.provider for c in creds]

        # Query live database counts for operational grounding
        from app.models.verticals import Candidate, Lead
        try:
            cand_count = self.db.query(Candidate).filter_by(tenant_id=self.tenant_id).count()
            lead_count = self.db.query(Lead).filter_by(tenant_id=self.tenant_id).count()
            operational_stats = f"Live Database Counts: {cand_count} Candidate(s)/Resume(s) currently on file; {lead_count} Lead(s) in CRM."
        except Exception:
            operational_stats = "Live Database Counts: 0 Candidate(s)/Resume(s) on file; 0 Lead(s) in CRM."

        # Inject company-dedicated knowledge base context (directives, brand rules, RAG)
        company_knowledge = self.get_knowledge_context("orchestrator", "General")

        system_prompt = f"""You are the Orchestrator AI, the central coordination brain of OctaOS.
Your job is to assist company leadership, answer questions about operations, and coordinate specialized department agents (Marketing, Sales, Support, HR, Finance).

{company_knowledge}

Currently configured API keys/credentials: {configured_providers}.
{operational_stats}

Available Agents & Actions:
- Marketing:
  - "create_posts": parameters: {{"days": int, "topic": str, "platforms": list}}
  - "generate_campaign": parameters: {{"topic": str, "days": int, "platforms": list, "text_provider": str, "image_provider": str, "video_provider": str, "generate_images": bool, "generate_videos": bool}}
- Sales:
  - "generate_leads": parameters: {{"provider": "apollo" | "hunter" | "google_places", "query": str, "count": int}}
    * Lead Source Decision Rules:
      - If the user specifies "apollo", "hunter", or "google_places" but its key is missing, schedule "request_key" for that provider first.
      - For local brick-and-mortar business searches (e.g. "gyms in Boston", "plumbers in Texas"), prefer "google_places" (if key configured).
      - For corporate B2B profiles (e.g. "software companies", "marketing agencies", "founders"), prefer "apollo" or "hunter" (if key configured).
  - "sales_outreach": parameters: {{"channel": "smtp" | "gmail" | "whatsapp", "subject": str, "body_template": str}}
  - "schedule_meeting": parameters: {{"tool": "google_calendar", "count": int}}
- HR:
  - "source_candidates": parameters: {{"role": str, "requirements": str, "salary": str, "count": int}}
  - "candidate_outreach": parameters: {{"channel": "smtp" | "gmail", "subject": str, "body_template": str, "candidate_id": str | None}}
  - "schedule_interview": parameters: {{"tool": "google_calendar", "candidate_id": str | None}}
- System:
  - "request_key": parameters: {{"provider": str}} - use this to ask the user for a missing key.

Guidelines:
1. If the user asks a conversational question, operational inquiry, or asks for advice, provide a clear, helpful response in the "message" field. (Use the operational database counts above if asked about candidate, resume, or lead counts).
2. If the user request requires executing tasks, include them in the "tasks" array. If no execution tasks are needed, leave "tasks" as an empty list [].
3. Adhere strictly to the company knowledge base and guidelines above.
4. Multi-turn conversation context: If previous conversation history is provided, maintain context across turns. For example, if you asked the user clarifying questions about a role, task, campaign, or parameters in previous turns, interpret the user's latest reply in the context of those prior questions.

Output MUST be valid JSON only.
Format:
{{
    "message": "Direct conversational response, guidance, or operational explanation.",
    "tasks": [
        {{"department": "Marketing" | "Sales" | "Support" | "Finance" | "HR" | "System", "action": "...", "parameters": {{}}}}
    ]
}}"""
        from app.services.ai_gateway.ai_parser import AIRetryManager, OrchestratorPlan

        async def gateway_call(prompt, system_prompt, provider, model):
            return await self.llm.complete(prompt=prompt, system_prompt=system_prompt, provider=provider, model=model)

        plan = {}
        try:
            plan_model = await AIRetryManager.call_with_retry(
                gateway_call_fn=gateway_call,
                model_class=OrchestratorPlan,
                prompt=effective_prompt,
                system_prompt=system_prompt,
                provider=provider,
                model=model
            )
            plan = plan_model.model_dump()
        except Exception as e:
            logger.info(f"[Orchestrator] Direct plan parsing fallback: {e}; generating conversational response.")
            try:
                conv_resp = await self.llm.complete(
                    prompt=effective_prompt,
                    system_prompt=f"You are the Orchestrator AI for OctaOS. Assist the user with their request.\n\n{company_knowledge}\n\n{operational_stats}",
                    provider=provider,
                    model=model
                )
                if conv_resp:
                    plan = {"message": conv_resp.strip(), "tasks": []}
            except Exception as ce:
                logger.error(f"[Orchestrator] Conversational fallback error: {ce}")
                plan = {"message": "I processed your request, but could not reach the language model provider. Please check your API key in Settings.", "tasks": []}

        self.log_activity("Delegate Tasks", f"Delegated goal: '{prompt}'")
        
        results = []
        if plan.get("message"):
            results.append({"status": "success", "message": plan["message"]})

        for task in plan.get("tasks", []):
            dept = task.get("department")
            try:
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
            except ValueError as ve:
                ve_str = str(ve)
                provider = None
                # Identify missing provider from exception message
                for p in ["linkedin", "meta", "facebook", "instagram", "twitter", "gmail", "whatsapp", "apollo", "hunter", "google_places", "google_calendar", "smtp", "greenhouse", "lever", "openai", "anthropic", "gemini"]:
                    if p in ve_str.lower():
                        provider = p
                        break
                if provider:
                    if provider == "smtp":
                        msg = "I need your SMTP outgoing mail credentials. Please reply with: 'My smtp credential is: smtp://username:password@smtp.mailtrap.io:2525'."
                    else:
                        msg = f"I need your {provider} API key to complete this task. Please reply with 'My {provider} key is: [YOUR_KEY]'."
                    self.log_activity("Action Required", msg)
                    results.append({"status": "action_required", "message": msg})
                else:
                    raise ve
        return {"mode": "execution", "plan": plan, "results": results}

    async def run_daily_ops(self):
        self.log_activity("Daily Autonomous Ops", "Initiating morning routines for all agents.")
        
        marketing = MarketingAgent(self.db, self.tenant_id)
        await marketing.daily_routine()
        
        sales = SalesAgent(self.db, self.tenant_id)
        await sales.daily_routine()

        hr = HRAgent(self.db, self.tenant_id)
        await hr.daily_routine()
        
        return {"status": "Daily ops complete"}

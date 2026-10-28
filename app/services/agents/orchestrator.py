import json
import logging
import re
from typing import Optional, List, Dict, Any
from app.services.agents.base import BaseAgent
from app.services.agents.marketing import MarketingAgent
from app.services.agents.sales import SalesAgent
from app.services.agents.support import SupportAgent
from app.services.agents.finance import FinanceAgent
from app.services.agents.hr import HRAgent
from app.services.agents.connected_systems import (
    clients_addressed_by,
    connection_facts,
    correct_assistant_reply,
    ensure_mcp_message_task,
    load_connected_systems,
    mcp_handoff_note,
)

from app.models.base import APICredential

logger = logging.getLogger(__name__)


_LEAD_PROVIDER_NAMES = {
    "apollo": "apollo",
    "hunter": "hunter",
    "google places": "google_places",
    "google_places": "google_places",
    "google maps": "google_places",
    "apify": "apify",
}

_OPEN_WEB_TERMS = (
    "web search",
    "websearch",
    "internet",
    "public web",
    "open web",
    "any source",
    "scrape",
    "scraping",
    "crawl",
    "browser",
    "firecrawl",
    "linkedin",
    "reddit",
    "instagram",
    "facebook",
)


def infer_lead_provider(prompt: str, requested_provider: Optional[str] = None) -> str:
    """Choose the real discovery path for a lead request.

    Open-web discovery is a first-class, credential-free path when Firecrawl or
    the public-search fallback is available. Keep an explicitly named provider
    intact, but do not let the old three-provider default hide web discovery.
    """
    text = _current_request_text(prompt).lower()
    for phrase, provider in _LEAD_PROVIDER_NAMES.items():
        if re.search(rf"\b{re.escape(phrase)}\b", text):
            return provider
    if any(term in text for term in _OPEN_WEB_TERMS):
        return "web_search"

    requested = (requested_provider or "").strip().lower()
    if requested in {"web_search", "free_search", "web", "internet", "open_web"}:
        return "web_search"
    if requested in _LEAD_PROVIDER_NAMES.values():
        return requested
    if requested:
        # Unknown provider values are left for the normal credential/error path
        # rather than silently changing an explicit user choice.
        return requested

    return "web_search"


def _lead_provider_was_explicitly_requested(prompt: str) -> bool:
    text = _current_request_text(prompt).lower()
    return any(re.search(rf"\b{re.escape(phrase)}\b", text) for phrase in _LEAD_PROVIDER_NAMES)


def _current_request_text(prompt: str) -> str:
    """Ignore quoted conversation history when resolving provider intent."""
    match = re.search(r"current user request:\s*(.*)\Z", prompt or "", re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else (prompt or "")


def _message_connected_client(
    agent: "OrchestratorAgent",
    request: str,
    client_hint: str = "",
    text: str = "",
) -> str:
    """Place a message on the named MCP client and return the real handoff."""
    from app.services.mcp.client_channel import queue_client_message

    snapshot = load_connected_systems(agent.db, agent.tenant_id)
    lookup = " ".join(part for part in (client_hint, request) if part).strip()
    clients = clients_addressed_by(snapshot, lookup or request)
    if not clients:
        known = ", ".join(
            str(client.get("name") or "unnamed")
            for client in (snapshot.get("mcp_clients") or [])
        ) or "none"
        return f"MCP handoff: no saved client matched that request. Saved MCP clients: {known}."
    body = (text or request).strip()
    if not body.lower().startswith("message from the octaos assistant"):
        body = f"Message from the OctaOS assistant: {body}"
    lines = []
    for client in clients:
        if not client.get("id"):
            lines.append(f"MCP handoff: {client.get('name') or 'MCP client'} has no saved credential id, so nothing was queued.")
            continue
        placed = queue_client_message(
            agent.db,
            tenant_id=agent.tenant_id,
            credential_id=str(client["id"]),
            client_name=str(client.get("name") or "MCP client"),
            text=body,
        )
        lines.append(mcp_handoff_note(placed))
    return "\n".join(lines)


def knowledge_query_for_turn(prompt: str, messages: Optional[List[Dict[str, Any]]] = None) -> str:
    """Build the company-knowledge search from this turn and earlier user turns.

    The retrieval query used to be the literal task name "orchestrator", so a
    question such as "what is AlienHouse Networks" never met the crawled site.
    A follow-up that only says the website was crawled still needs the company
    name from the previous user turn.
    """
    parts: List[str] = []
    for message in messages or []:
        if str(message.get("role") or "").lower() != "user":
            continue
        content = str(message.get("content") or "").strip()
        if not content or "I'm OctaOS. Choose a specialist" in content:
            continue
        parts.append(content)
    current = (prompt or "").strip()
    if current and current not in parts:
        parts.append(current)
    return "\n".join(parts)[-4000:]

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
        current_request = _current_request_text(prompt)
        key_match = re.search(r'(?:key|token|credential|smtp|api key) is\s*[:=]?\s*([a-zA-Z0-9_\-\.\:\@\/]+)', current_request, re.IGNORECASE)
        provider_match = re.search(r'(linkedin|meta|facebook|instagram|twitter|gmail|whatsapp|apollo|hunter|google_places|google_calendar|smtp)', current_request, re.IGNORECASE)
        
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
            recent_leads = (
                self.db.query(Lead.company, Lead.email)
                .filter(Lead.tenant_id == self.tenant_id, Lead.email.isnot(None))
                .order_by(Lead.created_at.desc())
                .limit(12)
                .all()
            )
            shown = [
                f"{company} ({email})"
                for company, email in recent_leads
                if company and email and "example.com" not in email.lower()
            ]
            sample = f" Named sample, not the full CRM: {'; '.join(shown)}." if shown else ""
            operational_stats = (
                f"Live Database Counts: {cand_count} Candidate(s)/Resume(s) currently on file; "
                f"{lead_count} Lead(s) in the CRM. {sample} "
                "Do not describe the sample size as the number of leads."
            )
        except Exception:
            operational_stats = "Live Database Counts: 0 Candidate(s)/Resume(s) on file; 0 Lead(s) in CRM."

        # Search the tenant library with the user's question. The task label
        # "orchestrator" matches none of the crawled website pages.
        knowledge_query = knowledge_query_for_turn(current_request, messages) or current_request
        try:
            company_knowledge = self.get_knowledge_context(knowledge_query, "General")
        except Exception as knowledge_error:
            logger.warning("Company knowledge lookup failed: %s", knowledge_error)
            company_knowledge = ""
        try:
            from app.services.rag.hybrid_engine import HybridRAGEngine
            knowledge_hits = HybridRAGEngine(self.db, self.tenant_id).retrieve(
                knowledge_query, department="general", top_k=6,
            )
        except Exception as knowledge_error:
            logger.warning("Company knowledge hits failed: %s", knowledge_error)
            knowledge_hits = []
        connection_snapshot = load_connected_systems(self.db, self.tenant_id)
        connected_systems = connection_facts(connection_snapshot, current_request)

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
  - "generate_leads": parameters: {{"provider": "web_search" | "apify" | "apollo" | "hunter" | "google_places" | "<configured source id>", "query": str, "count": int, "freshness": str}}
    * Lead Source Decision Rules:
      - "web_search" is the enterprise multi-channel public research path. It covers buyer-language web searches, public RFP/tender pages, funding and business news, hiring signals, company/contact pages, and permitted public Reddit/X/LinkedIn search results. It uses Firecrawl or DuckDuckGo for web discovery, and does not require Apollo, Hunter, or Google Places credentials.
      - Use a 14-day freshness window by default ("freshness": "14_days"). India is searched first, followed by the United States and United Kingdom unless the user specifies another geography order.
      - If the user says web search, internet, scrape, public web, any source, or does not name a provider, use "web_search" by default.
      - If the user explicitly specifies Apollo, Hunter, Google Places, or Apify, use that provider and request its credential only when that provider is unavailable.
      - Do not tell the user that web search, Firecrawl, Apify, or public web discovery is unavailable when handling lead research.
      - For public social, hiring, directory, or signal research, use web_search unless the user explicitly requests a configured Apify/source provider. Respect robots, terms, privacy, and login/access boundaries; do not claim a contact is verified unless the source supports it.
      - For local brick-and-mortar business searches, web_search may be used unless the user explicitly requests Google Places.
  - "draft_outreach": parameters: {{"query": str, "count": int, "tag": str, "company": str, "email": str, "instructions": str}}
    * Use this when the user asks Sales to email, draft, qualify, or reach leads already in the CRM, including leads tagged AHN ICP.
    * It reads those real leads, researches the public web only when the user asks for new companies or the CRM has no real match, fills real contact details, and stores an unsent draft.
    * It must not invent a person or company, must not use lead@example.com, and must not send.
  - "sales_outreach": parameters: {{"channel": "smtp" | "gmail" | "whatsapp", "subject": str, "body_template": str}}
    * This sends mail. Use it only when the user explicitly says to send and a mailbox is already connected. Otherwise use "draft_outreach".
  - "schedule_meeting": parameters: {{"tool": "google_calendar", "count": int}}
- HR:
  - "source_candidates": parameters: {{"role": str, "requirements": str, "salary": str, "count": int}}
  - "candidate_outreach": parameters: {{"channel": "smtp" | "gmail", "subject": str, "body_template": str, "candidate_id": str | None}}
  - "schedule_interview": parameters: {{"tool": "google_calendar", "candidate_id": str | None}}
- System:
  - "message_mcp_client": parameters: {{"client": str, "text": str}}
    * Use this only when the user asks to message, tell, text, notify, or ping a saved MCP client.
    * client is the name or type from the records. text is the message to place.
    * Do not use it when the user only asks whether a system can be reached.
  - "request_key": parameters: {{"provider": str}} - use this to ask the user for a missing key.

Connection records for this turn. This JSON is a lookup of what is saved and what is absent. It is not an answer to copy:
{connected_systems}

Guidelines:
1. If the user asks a conversational question, operational inquiry, or asks for advice, provide a clear, helpful response in the "message" field. (Use the operational database counts above if asked about candidate, resume, or lead counts).
2. If the user request requires executing tasks, include them in the "tasks" array. If no execution tasks are needed, leave "tasks" as an empty list [].
3. Adhere strictly to the company knowledge base and guidelines above. When those excerpts describe the company or its website, answer from them and cite the source URL. Do not say the company knowledge base is empty, and do not ask the user to paste website content that is already in the excerpts. If a specific fact is absent from the excerpts, say that fact was not in the retrieved pages.
4. Multi-turn conversation context: If previous conversation history is provided, maintain context across turns. For example, if you asked the user clarifying questions about a role, task, campaign, or parameters in previous turns, interpret the user's latest reply in the context of those prior questions. If an earlier turn printed a fixed connection card, do not repeat that card. Answer this turn from the records.
5. Write the reply in your own words from the connection records. When asked_about is present, answer that system: say whether it is saved or absent. An MCP client and a provider API key are different records. A missing provider key does not make an MCP client one-way and does not block message_mcp_client. inbuilt_model_route is the server model answering this turn; a provider with configured false only means no tenant API key is saved. Do not paste the JSON. Do not answer a question about one system by reciting every other system. Do not say you cannot check connections. Do not claim a client displayed a message.
6. If the user asks whether the company offers consulting, marketing, hiring, or another service, answer from the knowledge excerpts and cite the page URL. Leave tasks empty for that question.
7. Say that email or WhatsApp can be sent only when mailbox_connected or whatsapp_configured is true in those records. Otherwise say an unsent draft can be stored.

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
                    system_prompt=(
                        "You are the Orchestrator AI for OctaOS. Answer in your own words. "
                        "When the company knowledge excerpts answer the question, use them and cite the source URL. "
                        "Do not claim the knowledge base has no information about the company when those excerpts are present. "
                        "The connection JSON is a lookup of what is saved and what is absent. "
                        "Answer the system the user asked about. Do not paste the JSON or recite every system. "
                        "An MCP client and a provider API key are different. A missing key does not make an MCP client one-way. "
                        "If an earlier turn printed a fixed connection card, do not repeat it.\n\n"
                        f"{company_knowledge}\n\n{connected_systems}\n\n{operational_stats}"
                    ),
                    provider=provider,
                    model=model
                )
                if conv_resp:
                    plan = {"message": conv_resp.strip(), "tasks": []}
            except Exception as ce:
                logger.error(f"[Orchestrator] Conversational fallback error: {ce}")
                plan = {"message": "I processed your request, but could not reach the language model provider. Please check your API key in Settings.", "tasks": []}

        corrected = correct_assistant_reply(
            plan.get("message") or "",
            current_request,
            knowledge_hits,
            connection_snapshot,
        )
        plan["message"] = corrected["message"]
        if corrected["drop_tasks"]:
            plan["tasks"] = []
        else:
            plan["tasks"] = ensure_mcp_message_task(plan.get("tasks"), current_request)

        self.log_activity("Delegate Tasks", f"Delegated goal: '{prompt}'")
        
        results = []
        if plan.get("message"):
            results.append({"status": "success", "message": plan["message"]})

        current_request = _current_request_text(prompt)
        for task in plan.get("tasks", []):
            dept = task.get("department")
            try:
                # The planner is allowed to fill in query/count, but provider
                # selection for lead discovery must not regress to the legacy
                # Apollo/Hunter/Places-only behaviour. Preserve an explicit
                # provider choice; otherwise route to the real open-web path.
                if dept == "Sales" and task.get("action") == "generate_leads":
                    params = task.setdefault("parameters", {})
                    requested_provider = params.get("provider")
                    if not _lead_provider_was_explicitly_requested(current_request):
                        params["provider"] = "web_search"
                    else:
                        params["provider"] = infer_lead_provider(current_request, requested_provider)
                if dept == "Sales" and task.get("action") in ("draft_outreach", "qualify_leads", "outreach_draft", "research_and_draft"):
                    params = task.setdefault("parameters", {})
                    params.setdefault("instructions", current_request)
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
                elif dept == "System" and task.get("action") == "message_mcp_client":
                    params = task.get("parameters") or {}
                    handoff = _message_connected_client(
                        self,
                        current_request,
                        client_hint=str(params.get("client") or ""),
                        text=str(params.get("text") or ""),
                    )
                    self.log_activity("Message MCP Client", handoff.split("\n", 1)[0])
                    results.append({"status": "success", "message": handoff})
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

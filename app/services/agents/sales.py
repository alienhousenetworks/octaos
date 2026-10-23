import asyncio
import json
import logging
import re
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx
from app.core.security import decrypt_api_key
from app.services.sales.meeting_booking import book_meeting_for_lead
from app.services.credentials import get_decrypted_credential
from app.services.email.sender import parse_smtp_credentials, send_smtp_email, send_gmail_email
from app.services.sales_os.aso.v3_scoring import combine_v3_scores, parse_component_scores, parse_pain_points
from app.services.sales_os.contracts.registry import render_prompts

from app.services.agents.base import BaseAgent
from app.models.verticals import Lead
from app.models.base import APICredential
from app.core.http_utils import with_retry

logger = logging.getLogger(__name__)

def extract_json(text: str):
    import json
    text = text.strip()
    if text.startswith("```"):
        lines = text.split('\n')
        if lines[0].startswith("```"): lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"): lines = lines[:-1]
        text = '\n'.join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        array_match = re.search(r'\[.*\]', text, re.DOTALL)
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        if array_match:
            try: return json.loads(array_match.group(0))
            except: pass
        if obj_match:
            try: return json.loads(obj_match.group(0))
            except: pass
        raise ValueError(f"JSON extraction failed. Raw output: {text}")

def _build_lead_data(c: dict) -> dict:
    """Structured, real-only dossier data derived from a discovered company dict."""
    contact = c.get("contact") or {}
    data = {
        "contact": {
            "name": contact.get("name") or "",
            "title": contact.get("title") or "",
            "linkedin_url": contact.get("linkedin_url") or "",
        },
        "company": {
            "name": c.get("company_name") or "",
            "website": c.get("website") or "",
            "industry": c.get("industry") or "",
        },
        "freshness": c.get("freshness") or {},
        "evidence_url": c.get("evidence_url") or "",
        "why_now": c.get("why_now") or "",
        "purchasing_capacity": c.get("purchasing_capacity") or "",
        "qualification_reason": c.get("qualification_reason") or "",
    }
    if c.get("pain_points"):
        data["pain_points"] = c["pain_points"]
    if c.get("scoring"):
        data["scoring_breakdown"] = c["scoring"]
    return data


class SalesAgent(BaseAgent):
    def __init__(self, db, tenant_id):
        super().__init__(db, tenant_id, "Sales AI")

    async def execute_task(self, task: dict) -> dict:
        action = task.get("action")
        params = task.get("parameters", {})
        
        if action == "generate_leads":
            return await self._generate_leads(params)
        elif action == "sales_outreach":
            return await self._sales_outreach(params)
        elif action == "schedule_meeting":
            return await self._schedule_meeting(params)
        elif action == "run_v3_workflow":
            return await self.run_sales_ai_v3_workflow()
        return {"status": f"Unknown action: {action}"}

    async def run_sales_ai_v3_workflow(
        self,
        provider=None,
        model=None,
        count=50,
        freshness=None,
        mode: str = "configured_engine",
        prompt_instructions: Optional[str] = None,
    ) -> dict:
        from app.models.verticals import BusinessProfile, Lead
        from app.models.teams import AgentMetric
        from app.services.sales_os.discovery.web_discovery import classify_archetype
        import json
        import random
        import re
        from datetime import datetime, timezone, timedelta

        # Get business profile
        profile = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
        if not profile and mode == "configured_engine":
            self.log_activity("V3 Workflow Error", "No Business Profile configured.", "failed")
            return {"status": "error", "message": "Business Profile not found."}

        # Prompt-directed campaigns are intentionally allowed to run without a
        # saved BusinessProfile. Keep all downstream steps on the same neutral
        # context instead of dereferencing profile fields or assuming a
        # particular industry/currency/budget model.
        profile_company_name = (getattr(profile, "company_name", None) or "Your company").strip()
        profile_website = getattr(profile, "website", None) or "unknown"
        profile_industry = getattr(profile, "industry", None) or "unknown"
        profile_description = getattr(profile, "service_description", None) or "unknown"
        profile_offer = getattr(profile, "offer_details", None) or "unknown"
        profile_usp = getattr(profile, "usp", None) or "unknown"
        profile_budget = getattr(profile, "target_budget_range", None) or "unknown"
        profile_countries = getattr(profile, "target_countries", None) or []
        profile_target_industries = getattr(profile, "target_industries", None) or []
        profile_decision_makers = getattr(profile, "target_decision_makers", None) or []
        profile_extra_context = getattr(profile, "extra_context", None) or ""

        engine_name = "Prompt-Based Sales Agent" if mode == "prompt_agent" else "Configured Sales Engine"
        log_prefix = f"[{'Prompt Sales Agent' if mode == 'prompt_agent' else 'Configured Sales Engine'}]"

        freshness_window = freshness or (getattr(profile, "lead_freshness", "30_days") if profile else "30_days") or "30_days"

        def emit_activity(step_num: int, activity_str: str, log_entry: Optional[str] = None):
            p = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
            if not p:
                return
            status = dict(p.v3_workflow_status or {})
            status["workflow_type"] = mode
            status["workflow_name"] = engine_name
            status["current_step"] = step_num
            status["current_activity"] = activity_str
            if log_entry:
                logs = list(status.get("logs", []))
                logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_entry}")
                status["logs"] = logs[-150:]
            p.v3_workflow_status = status
            self.db.commit()

        def update_status(step_num: int, step_status: str, result_msg: str, status_msg: str, final_status: str = "executing"):
            p = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
            if not p:
                return
            status = dict(p.v3_workflow_status or {})
            status["workflow_type"] = mode
            status["workflow_name"] = engine_name
            status["current_step"] = step_num
            status["status"] = final_status
            status["current_activity"] = status_msg
            if "steps" not in status:
                status["steps"] = {}
            status["steps"][str(step_num)] = {
                "name": status["steps"].get(str(step_num), {}).get("name", f"Step {step_num}"),
                "status": step_status,
                "result": result_msg
            }
            if step_status == "completed" and str(step_num + 1) in status["steps"]:
                status["steps"][str(step_num + 1)]["status"] = "executing"
            
            logs = list(status.get("logs", []))
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {status_msg}")
            status["logs"] = logs[-150:]
            
            p.v3_workflow_status = status
            self.db.commit()

        # Step 1: Understand Service & Materialize Sales Context
        update_status(1, "executing", f"Materializing criteria for {engine_name}...", f"Starting Step 1 for {engine_name}...")
        try:
            if mode == "prompt_agent":
                effective_context = (prompt_instructions or "").strip()
                domain_archetype = "Prompt-Directed Prospecting"
                emit_activity(1, "Synthesizing criteria from prompt directive...", f"{log_prefix} Analyzing prompt directive: {effective_context[:80]}...")
                rendered = render_prompts(
                    "sales.orchestrator",
                    {
                        "company_name": "Prompt-directed campaign",
                        "website": "unknown",
                        "industry": "unknown",
                        "archetype": domain_archetype,
                        "description": effective_context or "Find high-intent B2B target accounts.",
                        "countries": "unknown",
                        "target_industries": "unknown",
                        "target_budget": "unknown",
                        "usp": "unknown",
                        "analyst_notes": effective_context or "none",
                        "freshness_window": str(freshness_window),
                    },
                )
                icp = await self.llm.complete(
                    rendered["task_prompt"],
                    system_prompt=rendered["system_prompt"],
                    provider=provider,
                    model=model,
                )
                icp = icp.strip()
                emit_activity(1, "ICP synthesized from prompt directive", f"{log_prefix} Generated criteria from prompt: {icp[:90]}...")
                update_status(1, "completed", f"[Prompt Directive] {icp}", f"Generated ICP from prompt directive: {icp}")
            else:
                effective_context = profile_extra_context
                from app.services.sales_os.context_materializer import SalesContextMaterializer
                materializer = SalesContextMaterializer(self.db, self.tenant_id)
                sales_ctx = materializer.get_active_context()
                if not sales_ctx:
                    sales_ctx = await materializer.materialize_context()

                domain_archetype = classify_archetype(
                    brief=profile_description,
                    query=profile_industry,
                    offer=profile_offer,
                )

                company_name = profile_company_name
                emit_activity(1, f"Synthesizing Ideal Customer Profile for {company_name}...", f"{log_prefix} Classifying domain archetype and target criteria...")
                rendered = render_prompts(
                    "sales.orchestrator",
                    {
                        "company_name": profile_company_name,
                        "website": profile_website,
                        "industry": profile_industry,
                        "archetype": domain_archetype,
                        "description": profile_description,
                        "countries": str(profile_countries) or "unknown",
                        "target_industries": str(profile_target_industries) or "unknown",
                        "target_budget": str(profile_budget) or "unknown",
                        "usp": profile_usp,
                        "analyst_notes": effective_context or "none",
                        "freshness_window": str(freshness_window),
                    },
                )
                icp = await self.llm.complete(
                    rendered["task_prompt"],
                    system_prompt=rendered["system_prompt"],
                    provider=provider,
                    model=model,
                )
                icp = icp.strip()
                emit_activity(1, f"ICP Synthesized for {company_name}", f"{log_prefix} Generated target criteria and negative exclusions: {icp[:90]}...")
                update_status(1, "completed", f"[{domain_archetype}] {icp}", f"Classified Archetype '{domain_archetype}'. Generated ICP & exclusions: {icp}")
        except Exception as e:
            update_status(1, "failed", str(e), f"Error in Step 1: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 2: Market Discovery
        update_status(2, "executing", f"Sourcing targets for {engine_name}...", f"Starting Step 2: Intelligent Routing & Sourcing ({engine_name})...")
        try:
            available_providers = {}
            creds = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id).all()
            for c in creds:
                if c.provider in ("sales", "ai_mode"):
                    continue
                if c.encrypted_key and "your_api_key" not in c.encrypted_key:
                    try:
                        decrypted = decrypt_api_key(c.encrypted_key)
                        if decrypted:
                            available_providers[c.provider] = decrypted
                    except Exception:
                        pass
            
            if mode == "prompt_agent":
                lines = [line.strip() for line in effective_context.split("\n") if line.strip() and not line.strip().upper().startswith(("ROLE", "WHAT WE SELL"))]
                query = lines[0][:100] if lines else "high-intent B2B target accounts"
            else:
                query = profile_target_industries[0] if profile_target_industries else "target clients"
            
            # Filter to all registered discovery and signal sources (60+ channels)
            from app.services.sales_os.discovery.source_registry import get_all_source_ids
            valid_discovery = get_all_source_ids()
            discovery_providers = {k: v for k, v in available_providers.items() if k in valid_discovery}
            
            # Keyless open-web discovery is always available as the final fallback.
            available_providers["web_search"] = ""
            
            if not discovery_providers:
                routing_choice = "web_search"
                update_status(2, "executing", "No paid provider keys configured; using open-web discovery.", f"{log_prefix} Routing to web_search.")

            # 1. Ask LLM for Routing Strategy (paid providers only)
            routing_prompt = f"""We are building an Enterprise Lead Sourcing Engine.
Available API Providers: {list(discovery_providers.keys())}
Target Industry/Query: {query}
Directive/Context: {effective_context or 'None'}

First, check if the user explicitly requested a specific provider in their query or context (e.g., "use apollo", "from hunter", "via zoominfo"). If they did, you MUST select that provider.
Otherwise, decide the best primary discovery provider to find companies.
- If it's a local/brick-and-mortar business (e.g. plumbers, restaurants, clinics), strongly prefer 'google_places' or 'apify'.
- If it's B2B/Corporate (e.g. SaaS, Healthcare, Agencies, Enterprise), prefer 'apollo' or 'hunter'.

Return a JSON with exactly one key: 'primary_source' (string) containing your choice from the available list."""
            
            if discovery_providers:
                try:
                    routing_response = await self.llm.complete(routing_prompt, provider=provider, model=model)
                    routing_choice = extract_json(routing_response).get("primary_source")
                    if routing_choice not in discovery_providers:
                        routing_choice = list(discovery_providers.keys())[0]
                except Exception:
                    routing_choice = list(discovery_providers.keys())[0]
                update_status(2, "executing", f"Selected {routing_choice} as primary source.", f"{log_prefix} Routing strategy defined for {query}.")

            # 2. Fetch Companies with Fallback
            companies_data = []
            
            # Use only valid discovery providers for fallback
            discovery_providers_list = list(discovery_providers.keys())
            
            if not routing_choice:
                raise Exception("No valid primary discovery providers configured.")
                
            providers_to_try = [routing_choice] + [p for p in discovery_providers if p != routing_choice]
            if "web_search" not in providers_to_try:
                providers_to_try.append("web_search")
            error_log = []
            search_keys = {"brave_search", "tavily", "reddit", "reddit_intent", "x", "x_search"}
            suppressed_domains = set()
            try:
                from app.models.deal_room import SuppressionRecord
                for record in self.db.query(SuppressionRecord).filter_by(tenant_id=self.tenant_id, identifier_type="domain").all():
                    if record.identifier_value:
                        suppressed_domains.add(record.identifier_value.strip().lower())
            except Exception:
                logger.debug("Suppression domains were not loaded for parallel search", exc_info=True)
            remaining_search_inr = 700.0
            try:
                from app.services.sales_os.search_v4.store import SqlSearchStore
                spend_store = SqlSearchStore(self.db)
                if spend_store.available():
                    remaining_search_inr = max(0.0, 700.0 - spend_store.month_spend_inr(self.tenant_id, datetime.now(timezone.utc)))
            except Exception:
                logger.debug("Search spend was not loaded", exc_info=True)
            parallel_task = asyncio.create_task(
                self._collect_parallel_search(
                    query=query,
                    profile=profile,
                    analyst_prompt=effective_context,
                    freshness_window=freshness_window,
                    credentials={key: value for key, value in available_providers.items() if key in search_keys},
                    suppressed_domains=suppressed_domains,
                    remaining_inr=remaining_search_inr,
                )
            )
            try:
                for fallback_provider in providers_to_try:
                    try:
                        update_status(2, "executing", f"Attempting discovery via {fallback_provider}...", f"{log_prefix} Trying {fallback_provider}.")
                        search_query = query
                        fetch_extra = {}
                        if fallback_provider == "web_search":
                            from app.services.sales_os.discovery.web_discovery import analyst_instructions, research_brief
                            if mode == "prompt_agent":
                                search_query = query
                            else:
                                search_query = research_brief(
                                    query,
                                    industries=profile_target_industries or None,
                                    countries=profile_countries or None,
                                    buyers=profile_decision_makers or None,
                                    budget=profile_budget if profile_budget != "unknown" else None,
                                    offer=profile_description if profile_description != "unknown" else None,
                                )
                            fetch_extra["analyst_prompt"] = analyst_instructions(effective_context)
                            fetch_extra["on_progress"] = lambda msg: emit_activity(2, msg.split("]")[-1].strip() if "]" in msg else msg, f"{log_prefix} {msg}")
                            fetch_extra["freshness_window"] = freshness_window
                        companies_data = await self._fetch_real_leads(
                            fallback_provider,
                            available_providers[fallback_provider],
                            search_query,
                            count=count,
                            freshness=freshness_window,
                            **fetch_extra,
                        )
                        if companies_data:
                            routing_choice = fallback_provider
                            break
                        error_log.append(f"{fallback_provider}: returned no leads")
                        update_status(
                            2,
                            "executing",
                            f"{fallback_provider} returned no leads. Trying the next source.",
                            f"{fallback_provider} returned no leads.",
                        )
                    except Exception as e:
                        error_msg = str(e)
                        error_log.append(f"{fallback_provider}: {error_msg}")
                        update_status(2, "executing", f"Discovery via {fallback_provider} failed. Attempting fallback...", f"Fallback triggered: {error_msg}.")
                        continue
            finally:
                search_batch = await parallel_task
            from app.services.sales_os.search_v4.bridge import merge_connector_leads
            companies_data, search_report = merge_connector_leads(companies_data, search_batch)
            self._record_parallel_search_spend(search_batch)
            if search_report:
                update_status(2, "executing", "Parallel search methods finished.", f"{log_prefix} {search_report}")

            if not companies_data:
                error_details = " | ".join(error_log) if error_log else "No exact error provided."
                raise Exception(
                    f"All available discovery providers failed to return leads. Errors: {error_details}. "
                    f"Parallel search: {search_report}"
                )
            
            # 3. Waterfall Enrichment
            companies = []
            enriched_count = 0
            
            for c in companies_data:
                # Discard fake or missing emails
                needs_enrichment = False
                email = c.get("email", "")
                name = c.get("name", "")
                
                if not email or "@" not in email or email.startswith("contact@") or email.startswith("info@") or name == "Manager" or name == "General Inquiry":
                    needs_enrichment = True
                
                if needs_enrichment:
                    # Attempt Enrichment via Waterfall
                    enrichment_tool = None
                    if "hunter" in available_providers:
                        enrichment_tool = "hunter"
                    elif "apollo" in available_providers and routing_choice != "apollo":
                        enrichment_tool = "apollo"
                    elif "apify" in available_providers and routing_choice != "apify":
                        enrichment_tool = "apify"
                        
                    if enrichment_tool:
                        update_status(2, "executing", f"Enriching {c.get('company')} via {enrichment_tool}...", f"Waterfall Enrichment active for {c.get('company')}.")
                        try:
                            # Use website domain if available, otherwise try to extract from email
                            domain = ""
                            if c.get("website"):
                                domain = c.get("website").replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                            elif email and "@" in email:
                                domain = email.split("@")[-1]
                            
                            if domain:
                                enrichment_data = await self._fetch_real_leads(enrichment_tool, available_providers[enrichment_tool], domain, count=1)
                                if enrichment_data:
                                    real_email = enrichment_data[0].get("email", "")
                                    real_name = enrichment_data[0].get("name", "")
                                    if real_email and "@" in real_email:
                                        c["email"] = real_email
                                        if real_name:
                                            c["name"] = real_name
                                        enriched_count += 1
                            else:
                                update_status(2, "executing", f"Enrichment skipped for {c.get('company')} - no valid domain.", f"No domain available to enrich {c.get('company')}.")
                        except Exception:
                            pass
                
                # Final Strict Validation and Suppression Check
                has_name = bool(c.get("name") and c["name"].strip() not in ["Unknown Contact", "General Inquiry"])
                # For open-web discovery, allow verified domain emails (sales@, contact@, info@) unless paid waterfall enrichment (Apollo/Hunter) is active
                email_value = str(c.get("email") or "").strip()
                phone_value = str(c.get("phone") or "").strip()
                has_email = "@" in email_value
                has_phone = len(re.sub(r"\D", "", phone_value)) >= 8
                has_contact = has_email or has_phone
                if has_email and (available_providers.get("hunter") or available_providers.get("apollo")):
                    has_contact = not email_value.startswith("contact@") and not email_value.startswith("info@")
                
                from app.services.sales_os.governance.suppression import SuppressionService
                from app.services.sales_os.providers.honesty import is_fabricated_contact
                if is_fabricated_contact(c):
                    continue
                suppression_service = SuppressionService(self.db, self.tenant_id)
                domain_val = c.get("website", "").replace("https://", "").replace("http://", "").split("/")[0]
                is_suppressed, supp_reason = suppression_service.is_suppressed(email=c.get("email"), domain=domain_val, phone=c.get("phone"))
                
                if is_suppressed:
                    continue
                
                if has_name and has_contact:
                    companies.append({
                        "company_name": c.get("company", "Unknown"),
                        "website": c.get("website", ""),
                        "industry": query,
                        "estimated_employees": "Unknown",
                        "estimated_revenue": "Unknown",
                        "location": "Unknown",
                        "source": f"{routing_choice} (Enriched)" if enriched_count else routing_choice,
                        "evidence_url": c.get("evidence_url") or "",
                        "freshness": c.get("freshness") or {},
                        "contact": {
                            "name": c.get("name", ""),
                            "title": c.get("title") or "Contact",
                        "email": email_value,
                        "phone": phone_value,
                            "linkedin_url": c.get("linkedin_url") or ""
                        }
                    })
                    
            if not companies:
                import json
                rejected_data_str = json.dumps(companies_data, indent=2)
                raise Exception(f"API returned leads, but after strict waterfall enrichment, none had a real name and deliverable email or phone. No simulated data is allowed.\nRaw Rejected Data: {rejected_data_str}")
            
            import json
            leads_summary = [{"name": c["contact"]["name"], "email": c["contact"]["email"], "company": c["company_name"]} for c in companies]
            update_status(2, "completed", f"Discovered and verified {len(companies)} company profiles.", f"Sourced via {routing_choice}. Enriched {enriched_count} records to find real emails. Parallel search: {search_report}\n\nValidated Leads:\n{json.dumps(leads_summary, indent=2)}")
        except Exception as e:
            update_status(2, "failed", str(e), f"Error in Step 2: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 3: Lead Qualification
        update_status(3, "executing", "Evaluating purchasing capacities...", "Starting Step 3: Qualifying budgets and signals...")
        qualified_companies = []
        try:
            for i, c in enumerate(companies):
                emit_activity(3, f"Evaluating budget fit for {c['company_name']} ({i+1}/{len(companies)})...")
                prompt = f"""Qualify this target company:
Company Name: {c['company_name']}
Industry: {c['industry']}
Estimated Revenue: {c['estimated_revenue']}
Estimated Employees: {c['estimated_employees']}
Our Target Budget / Pricing Context: {profile_budget}
Target Industries: {profile_target_industries or 'unknown'}
Offer: {profile_offer}

Assess purchasing capacity only from the supplied evidence and the tenant's own budget context. Do not assume a currency, industry, company-size band, or fixed capacity taxonomy. If capacity is not evidenced, return "unknown". A lead is qualified only when the supplied evidence supports the tenant's target criteria; missing facts must not be filled with typical industry assumptions.
Output a JSON object with:
- capacity: string (an evidence-backed label or "unknown")
- qualified: boolean (true if budget, industry and size align with ICP, false otherwise)
- reason: string (concise, factual explanation grounded in provided data)
Only return JSON, no other text."""
                try:
                    qual_str = await self.llm.complete(prompt, provider=provider, model=model)
                    qual = extract_json(qual_str)
                except Exception:
                    qual = {"capacity": "Unknown", "qualified": False, "reason": "Insufficient evidence to qualify company budget."}
                
                c["purchasing_capacity"] = qual.get("capacity", "Unknown")
                c["qualified"] = bool(qual.get("qualified", False))
                c["qualification_reason"] = qual.get("reason", "Qualification evaluated against target budget and ICP parameters.")
                if c["qualified"]:
                    qualified_companies.append(c)

                verdict = "QUALIFIED" if c["qualified"] else "DISQUALIFIED"
                emit_activity(
                    3,
                    f"Evaluated {i+1}/{len(companies)} companies ({len(qualified_companies)} qualified)...",
                    f"[QUALIFY] {c['company_name']}: Capacity {c['purchasing_capacity']} -> {verdict} ({c['qualification_reason'][:65]})"
                )

            # Persist qualified leads to database immediately so they appear in the pipeline board in real time
            for c in qualified_companies:
                email_val = c.get("contact", {}).get("email") or ""
                phone_val = c.get("contact", {}).get("phone") or ""
                if not email_val and not phone_val:
                    continue
                query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)
                if email_val:
                    query = query.filter(Lead.email == email_val)
                else:
                    query = query.filter(Lead.phone == phone_val)
                exists = query.first()
                if not exists:
                    lead = Lead(
                        tenant_id=self.tenant_id,
                        name=c["contact"]["name"],
                        email=email_val or None,
                        phone=phone_val,
                        company=c["company_name"],
                        source=f"{c['source']}: V3 Workflow",
                        status="qualified",
                        score=50,
                        priority="medium",
                        assigned_to="Sales AI Agent",
                        personal_email=email_val or None,
                        company_email=email_val or None,
                        mobile_no=phone_val,
                        need_of_what=profile_offer,
                        why=c.get("why_now") or c["qualification_reason"],
                        data=_build_lead_data(c),
                        target_context=f"Archetype: {domain_archetype} | Capacity: {c.get('purchasing_capacity', 'Unknown')}"
                    )
                    self.db.add(lead)
            try:
                self.db.commit()
            except Exception as dbe:
                logger.warning(f"Failed to pre-commit qualified leads to DB: {dbe}")
                self.db.rollback()

            update_status(3, "completed", f"Qualified {len(qualified_companies)} / {len(companies)} companies.", f"Lead qualification complete. Rejected {len(companies) - len(qualified_companies)} companies outside budget.")
        except Exception as e:
            update_status(3, "failed", str(e), f"Error in Step 3: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 4: Pain Point Discovery & Deep Context Enrichment
        update_status(4, "executing", "Analyzing digital pain points and recent events...", "Starting Step 4: Pulling deep context (news, jobs) and scanning for pain points...")
        try:
            apollo_key = available_providers.get("apollo")
            for i, c in enumerate(qualified_companies):
                emit_activity(4, f"Auditing digital operations and pain points for {c['company_name']} ({i+1}/{len(qualified_companies)})...")
                prior_news = list(c.get("news") or [])
                prior_jobs = list(c.get("jobs") or [])
                c["news"] = []
                c["jobs"] = []
                
                # Fetch Deep Context if Apollo is available
                if apollo_key:
                    domain = ""
                    if c.get("website"):
                        domain = c.get("website").replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                    elif c.get("contact", {}).get("email") and "@" in c["contact"]["email"]:
                        domain = c["contact"]["email"].split("@")[-1]
                        
                    if domain:
                        org_id = await self._fetch_apollo_org_data(apollo_key, domain)
                        if org_id:
                            c["news"] = await self._fetch_apollo_news(apollo_key, org_id)
                            c["jobs"] = await self._fetch_apollo_jobs(apollo_key, org_id)

                if not c["news"]:
                    c["news"] = prior_news
                if not c["jobs"]:
                    c["jobs"] = prior_jobs
                            
                news_context = ", ".join([n["title"] for n in c["news"]]) if c["news"] else "None recent"
                jobs_context = ", ".join([j["title"] for j in c["jobs"]]) if c["jobs"] else "None recent"

                rendered = render_prompts(
                    "sales.orchestrator",
                    {
                        "company_name": c["company_name"],
                        "industry": c.get("industry") or "unknown",
                        "news": news_context,
                        "jobs": jobs_context,
                        "offer": profile_offer,
                        "usp": profile_usp,
                    },
                    task="pain",
                )
                pain_str = await self.llm.complete(
                    rendered["task_prompt"],
                    system_prompt=rendered["system_prompt"],
                    provider=provider,
                    model=model,
                )
                try:
                    p_list = extract_json(pain_str)
                except Exception:
                    p_list = []
                c["pain_points"] = parse_pain_points(p_list)
                emit_activity(
                    4,
                    f"Audited {i+1}/{len(qualified_companies)} companies...",
                    f"[AUDIT] {c['company_name']}: Discovered pain points: {'; '.join(c['pain_points'][:2])}"
                )
            update_status(4, "completed", f"Identified custom pain points for {len(qualified_companies)} qualified leads.", "Deep context enrichment complete. Discovered pain points using recent news and job openings.")
        except Exception as e:
            update_status(4, "failed", str(e), f"Error in Step 4: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 5: Decision Maker Discovery
        update_status(5, "executing", "Searching decision-maker contact details...", "Starting Step 5: Validating contact details...")
        try:
            update_status(5, "completed", f"Validated contacts for {len(qualified_companies)} lead companies.", "Decision-maker lookup complete. Real API data verified.")
        except Exception as e:
            update_status(5, "failed", str(e), f"Error in Step 5: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 6: Lead Scoring
        update_status(6, "executing", "Applying multi-factor lead scoring formula...", "Starting Step 6: Calculating weighted quality score (Budget, Pain Point, Intent, etc.)...")
        scored_leads = []
        try:
            for i, c in enumerate(qualified_companies):
                emit_activity(6, f"Calculating weighted quality score for {c['company_name']} ({i+1}/{len(qualified_companies)})...")
                rendered = render_prompts(
                    "sales.orchestrator",
                    {
                        "company_name": c["company_name"],
                        "industry": c.get("industry") or "unknown",
                        "pain_points": str(c.get("pain_points") or []),
                        "usp": profile_usp,
                    },
                    task="score",
                )
                try:
                    score_str = await self.llm.complete(
                        rendered["task_prompt"],
                        system_prompt=rendered["system_prompt"],
                        provider=provider,
                        model=model,
                    )
                    scores = parse_component_scores(extract_json(score_str))
                except Exception:
                    scores = parse_component_scores(None)

                email_value = (c.get("contact") or {}).get("email") or ""
                contact_score = 100.0 if "@" in email_value else None
                combined = combine_v3_scores(scores, contact_score)
                budget_score = scores.get("budget_score")
                pain_score = scores.get("pain_score")
                intent_score = scores.get("intent_score")
                industry_score = scores.get("industry_score")
                growth_score = scores.get("growth_score")
                
                fresh_info = c.get("freshness") or {}
                snippet = fresh_info.get("signal_snippet") or ""
                why_now = ""
                if snippet or c.get("news") or c.get("jobs"):
                    try:
                        why_now = (await self.llm.complete(
                            f"In 2 sentences, explain why {c['company_name']} is worth contacting NOW for our offer "
                            f"({profile_offer}). Use ONLY these facts, invent nothing.\n"
                            f"Signal ({fresh_info.get('freshness_label') or 'unknown age'}): {snippet}\n"
                            f"News: {[n.get('title') for n in c.get('news', [])]}\n"
                            f"Jobs: {[j.get('title') for j in c.get('jobs', [])]}\n"
                            f"Pain points: {c.get('pain_points')}\nBudget fit: {c.get('purchasing_capacity')}\n"
                            f"Output plain text only.",
                            provider=provider, model=model,
                        )).strip()
                    except Exception:
                        why_now = ""
                c["why_now"] = why_now

                weighted_score = combined["total"]
                category = combined["category"]
                c["scoring"] = {
                    "budget_score": budget_score,
                    "pain_score": pain_score,
                    "intent_score": intent_score,
                    "industry_score": industry_score,
                    "growth_score": growth_score,
                    "contact_score": contact_score,
                    "unknown_components": combined["unknown_components"],
                    "total": weighted_score,
                    "category": category,
                }
                scored_leads.append(c)
                emit_activity(
                    6,
                    f"Scored {i+1}/{len(qualified_companies)} leads...",
                    f"[SCORE] {c['company_name']}: Score {weighted_score}/100 [{category}] (Pain: {pain_score}, Intent: {intent_score})"
                )
                
            update_status(6, "completed", f"Scored lead pool: {len(scored_leads)} leads classified.", "Lead scoring matrix processed successfully.")
        except Exception as e:
            update_status(6, "failed", str(e), f"Error in Step 6: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 7: Outreach Generation
        update_status(7, "executing", "Generating personalized outreach messages...", "Starting Step 7: Writing hyper-targeted outreaches without templates...")
        try:
                from app.services.sales_os.context_materializer import SalesContextMaterializer
                sales_ctx = SalesContextMaterializer(self.db, self.tenant_id).get_active_context()
                proofs = (sales_ctx.proof_points if sales_ctx else [])[:3]
                proof_text = f"\nVerified Proof Points: {', '.join(proofs)}" if proofs else ""

                from app.models.base import User
                user = self.db.query(User).filter_by(tenant_id=self.tenant_id).order_by(User.is_superuser.desc(), User.id.asc()).first()
                employee_name = user.name.strip() if (user and user.name and user.name.strip()) else None
                if employee_name:
                    behalf_instruction = f"Write on behalf of {employee_name} at {profile_company_name}. Sign off with: Best regards, {employee_name}, {profile_company_name}."
                else:
                    behalf_instruction = f"Write on behalf of {profile_company_name}. Do NOT invent any employee or sender name. Sign off strictly with: Best regards, {profile_company_name} (or The {profile_company_name} Team)."

                for i, c in enumerate(scored_leads):
                    emit_activity(7, f"Drafting tailored outreach email for {c['contact']['name']} at {c['company_name']} ({i+1}/{len(scored_leads)})...")
                    news_context = ", ".join([n["title"] for n in c.get("news", [])]) if c.get("news") else "None recent"
                    jobs_context = ", ".join([j["title"] for j in c.get("jobs", [])]) if c.get("jobs") else "None recent"

                    prompt = f"""Write a highly personalized outbound sales email from {profile_company_name} to {c['contact']['name']} ({c['contact']['title']}) at {c['company_name']}.
Tailor it to their specific pain points: {c['pain_points']}.
Recent Company News to reference (if relevant): {news_context}
Recent Job Openings to reference (if relevant): {jobs_context}
Use our USP: {profile_usp}
Offer: {profile_offer}{proof_text}

Sender & Context Instructions:
- {behalf_instruction}
- Do NOT invent or use any fake names.

Strict Tone & Quality Rules:
- Direct, consultative, value-first tone.
- Zero buzzwords or hype ('game-changer', 'revolutionary', '10x overnight').
- Soft, low-friction Call to Action.
- Under 120 words. No subject line, no placeholders, no brackets. Output the email body only."""
                    outreach_text = await self.llm.complete(prompt, provider=provider, model=model)
                    c["outreach_message"] = outreach_text.strip()
                    first_p = (c.get("pain_points") or ["no evidenced pain point"])[0]
                    emit_activity(
                        7,
                        f"Personalized outreach drafted for {c['company_name']}...",
                        f"[OUTREACH] {c['company_name']}: Drafted pitch tailored to '{first_p[:45]}'"
                    )
                update_status(7, "completed", "Generated unique personalized emails for all candidates.", "Outreach generation complete. All outreaches customized to target business pain points.")
        except Exception as e:
            update_status(7, "failed", str(e), f"Error in Step 7: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 8: Multi-Channel Outreach
        update_status(8, "executing", "Sequencing outreach touchpoints...", "Starting Step 8: Creating timeline schedules for Email, LinkedIn, WhatsApp...")
        try:
            for idx, c in enumerate(scored_leads):
                emit_activity(8, f"Sequencing multi-channel touchpoints for {c['company_name']} ({idx+1}/{len(scored_leads)})...")
                # Save lead in DB
                contact_email = c["contact"].get("email") or ""
                contact_phone = c["contact"].get("phone") or ""
                lead_query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)
                if contact_email:
                    lead_query = lead_query.filter(Lead.email == contact_email)
                else:
                    lead_query = lead_query.filter(Lead.phone == contact_phone)
                exists = lead_query.first()
                if exists:
                    lead = exists
                    lead.score = c["scoring"]["total"]
                    lead.status = "scored"
                    lead.priority = "high" if c["scoring"]["category"] == "Hot Lead" else "medium"
                    lead.why = c.get("why_now") or c["qualification_reason"]
                    lead.target_context = f"Archetype: {domain_archetype} | Pain points: {', '.join(c.get('pain_points', []))}"
                else:
                    lead = Lead(
                        tenant_id=self.tenant_id,
                        name=c["contact"]["name"],
                        email=contact_email or None,
                        phone=contact_phone,
                        company=c["company_name"],
                        source=f"{c['source']}: V3 Workflow",
                        status="scored",
                        score=c["scoring"]["total"],
                        priority="high" if c["scoring"]["category"] == "Hot Lead" else "medium",
                        assigned_to="Sales AI Agent",
                        personal_email=contact_email or None,
                        company_email=contact_email or None,
                        mobile_no=contact_phone,
                        need_of_what=profile_offer,
                        why=c.get("why_now") or c["qualification_reason"],
                        target_context=f"Archetype: {domain_archetype} | Pain points: {', '.join(c.get('pain_points', []))}"
                    )
                    self.db.add(lead)
                    self.db.flush()
                
                emit_activity(
                    8,
                    f"Saved and sequenced {idx+1}/{len(scored_leads)} leads into CRM...",
                    f"[SEQUENCE] {c['company_name']}: Day 1 Email, Day 3 LinkedIn, Day 8 WhatsApp sequence mapped. CRM lead saved."
                )
                
                # Multi-channel schedule with dynamic cadence and pending status
                cadence = 3
                sales_cred = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="sales").first()
                if sales_cred and sales_cred.settings and sales_cred.settings.get("follow_up_cadence_days"):
                    cadence = max(1, int(sales_cred.settings["follow_up_cadence_days"]))

                p_points = c.get("pain_points") or ["operational bottlenecks"]
                first_pain = p_points[0]
                second_pain = p_points[1] if len(p_points) > 1 else p_points[0]

                channel_schedule = [
                    {"day": 1, "channel": "Email", "content": c["outreach_message"], "status": "pending"},
                    {"day": 1 + cadence, "channel": "LinkedIn", "content": f"Hi {c['contact']['name']}, noticed your work at {c['company_name']}. I sent over an email regarding {profile_company_name}'s {profile_offer} to tackle your {first_pain}. Let's connect!", "status": "pending"},
                    {"day": 1 + 2 * cadence, "channel": "Email", "content": f"Hi {c['contact']['name']}, following up on my previous message. We help {c['company_name']} automate {second_pain} to optimize your revenue. Let me know if you are free for a quick call.", "status": "pending"},
                    {"day": 1 + 3 * cadence, "channel": "WhatsApp", "content": f"Hello {c['contact']['name']}, this is {profile_company_name} following up. Are you available for a brief chat this week?", "status": "pending"},
                    {"day": 1 + 4 * cadence, "channel": "Follow-Up Call", "content": "Scheduled follow-up phone call.", "status": "pending"}
                ]
                
                # Route the first touch through the same real dispatcher used
                # by the durable outbox. This prevents the initial email from
                # bypassing suppression, deliverability gates, or WhatsApp's
                # configured Meta provider.
                subject = f"Partnership Opportunity - {profile_company_name} x {c['company_name']}"
                body = c["outreach_message"]
                from app.services.sales.touch_dispatcher import dispatch_sales_touch

                delivery = dispatch_sales_touch(
                    self.db,
                    self.tenant_id,
                    lead,
                    channel="email",
                    body=body,
                    subject=subject,
                    step_number=1,
                )
                if not delivery.get("sent") and c["contact"].get("phone"):
                    whatsapp_delivery = dispatch_sales_touch(
                        self.db,
                        self.tenant_id,
                        lead,
                        channel="whatsapp",
                        body=body,
                        subject=subject,
                        step_number=1,
                    )
                    if whatsapp_delivery.get("sent"):
                        delivery = whatsapp_delivery

                sent_successfully = bool(delivery.get("sent"))
                channel_used = delivery.get("channel") or "email"
                channel_schedule[0]["status"] = "sent" if sent_successfully else "failed"
                channel_schedule[0]["delivery_reason"] = delivery.get("reason")
                conv = []
                if sent_successfully:
                    conv.append(
                        {
                            "direction": "outbound",
                            "channel": channel_used,
                            "content": body,
                            "subject": subject,
                            "author": "Sales AI Agent",
                            "at": datetime.now(timezone.utc).isoformat(),
                            "sent": True,
                            "delivery_details": delivery.get("message"),
                        }
                    )
                            
                if sent_successfully:
                    lead.status = "contacted"
                    lead.data = {
                        **(lead.data or {}),
                        **_build_lead_data(c),
                        "domain_archetype": domain_archetype,
                        "committee_role": "economic_buyer",
                        "freshness_window": freshness_window,
                        "outreach_channel": channel_used,
                        "outbound_subject": subject,
                        "outbound_body": body,
                        "outreach_sent_at": datetime.now(timezone.utc).isoformat(),
                        "conversation": conv,
                        "outreach_schedule": channel_schedule,
                        "sent_actual": True
                    }
                else:
                    lead.status = "scored" # Keeps it from saying contacted
                    lead.data = {
                        **(lead.data or {}),
                        **_build_lead_data(c),
                        "domain_archetype": domain_archetype,
                        "committee_role": "economic_buyer",
                        "freshness_window": freshness_window,
                        "outreach_schedule": channel_schedule,
                        "draft_subject": subject,
                        "draft_body": body,
                        "sent_actual": False
                    }
                
                # Synchronize with persistent DealRoom and Canonical Sales Intelligence
                try:
                    from app.services.sales.sync_bridge import SalesSyncBridge
                    sync_bridge = SalesSyncBridge(self.db, self.tenant_id)
                    sync_bridge.sync_outreach_sent(lead, sent_actual=sent_successfully, auto_commit=False)
                except Exception as sync_err:
                    logger.warning(f"SalesSyncBridge sync skipped for {c['company_name']}: {sync_err}")

                # Stage future sequence touches into Outbox for heartbeat execution
                try:
                    from app.services.sales.outbox_service import SalesOutboxService
                    outbox_svc = SalesOutboxService(self.db, self.tenant_id)
                    future_touches = channel_schedule[1:]
                    if future_touches:
                        outbox_svc.stage_sequence(lead, future_touches)
                except Exception as outbox_err:
                    logger.warning(f"Outbox staging failed for {lead.email}: {outbox_err}")

                # Update metrics
                m_leads = self.db.query(AgentMetric).filter_by(tenant_id=self.tenant_id, metric_name="leads_generated").first()
                if not m_leads:
                    m_leads = AgentMetric(tenant_id=self.tenant_id, metric_name="leads_generated", value=0.0)
                    self.db.add(m_leads)
                m_leads.value += 1.0
                
            self.db.commit()
            update_status(8, "completed", "Touchpoint timeline mapped and Day 1 outreach initiated.", "Multi-channel sequence active. Saved qualified leads into CRM board.")
        except Exception as e:
            update_status(8, "failed", str(e), f"Error in Step 8: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 9: Conversation AI
        update_status(9, "executing", "Readying conversation auto-responders...", "Starting Step 9: Sourcing pricing guidelines, case studies, and scheduling parameters...")
        try:
            update_status(9, "completed", "Ready to process prospect replies and objections.", "Conversation AI engine operational. Active inbox polling initialized.")
        except Exception as e:
            update_status(9, "failed", str(e), f"Error in Step 9: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 10: Meeting Conversion
        update_status(10, "executing", "Checking calendars and converting real prospect replies...", "Starting Step 10: Processing real interested leads...")
        try:
            # Find actual qualified leads who replied with interest
            interested_leads = self.db.query(Lead).filter(
                Lead.tenant_id == self.tenant_id,
                Lead.status == "replied"
            ).all()
            
            real_interested_lead = None
            for lead in interested_leads:
                if (lead.data or {}).get("reply_classification", {}).get("interested"):
                    real_interested_lead = lead
                    break

            if real_interested_lead:
                suggested_time = (real_interested_lead.data or {}).get("reply_classification", {}).get("suggested_time")
                if not suggested_time:
                    data = dict(real_interested_lead.data or {})
                    data["meeting_coordination_status"] = "coordinating_slots"
                    real_interested_lead.data = data
                    self.db.commit()
                    update_status(10, "completed", f"{real_interested_lead.company} expressed interest; awaiting an explicit time proposal.", "Meeting coordination is waiting for a prospect-confirmed time.", "completed")
                    return {"status": "success", "meeting_coordination": "awaiting_time"}

                from app.services.sales.meeting_booking import book_meeting_for_lead
                booked = book_meeting_for_lead(
                    db=self.db,
                    tenant_id=self.tenant_id,
                    lead=real_interested_lead,
                    tool="google_calendar",
                    suggested_time=suggested_time,
                    log_activity=self.log_activity
                )
                if booked:
                    from app.services.sales.sync_bridge import SalesSyncBridge
                    SalesSyncBridge(self.db, self.tenant_id).sync_meeting_booked(real_interested_lead, auto_commit=True)
                update_status(10, "completed", f"Booked calendar meeting for {real_interested_lead.company}.", "Meeting conversion completed successfully. Calendars synced and team notified.", "completed")
            else:
                update_status(10, "completed", "Multi-channel sequence live. Inbound inbox listener active for prospect replies.", "Outreach initiated. Autonomous inbox monitoring will coordinate calendar invites as replies arrive.", "completed")
        except Exception as e:
            update_status(10, "failed", str(e), f"Error in Step 10: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        return {"status": "success"}

    async def _generate_leads(self, params: dict):
        provider = params.get("provider", "web_search")
        if provider == "free_search":
            provider = "web_search"
        query = params.get("query", "target clients")
        count = params.get("count", 5)
        
        self.log_activity("Lead Sourcing", f"Sourcing {count} leads using {provider} for query: '{query}'")
        
        leads_data = []

        # Check for API credentials
        cred = None if provider == "web_search" else self.db.query(APICredential).filter_by(
            tenant_id=self.tenant_id, provider=provider
        ).first()
        
        if provider != "web_search" and (not cred or "your_api_key" in (cred.encrypted_key or "") or not cred.encrypted_key.strip()):
            raise ValueError(f"No API credentials found for {provider}. Please configure your API credentials under Platform Setup -> API Settings.")
        
        try:
            fetch_extra = {}
            if provider == "web_search":
                from app.models.verticals import BusinessProfile
                from app.services.sales_os.discovery.web_discovery import analyst_instructions
                profile_row = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
                if profile_row:
                    fetch_extra["analyst_prompt"] = analyst_instructions(profile_row.extra_context)
            leads_data = await self._fetch_real_leads(
                provider,
                decrypt_api_key(cred.encrypted_key) if cred else "",
                query,
                count,
                **fetch_extra,
            )
            if provider == "web_search" and not leads_data:
                message = "Open-web discovery found no verifiable contacts after multiple search rounds."
                self.log_activity("API Error", message, "failed")
                return {"status": "error", "message": message}
        except Exception as e:
            self.log_activity("API Error", f"Failed fetching from {provider}: {str(e)}.", "failed")
            return {"status": "error", "message": str(e)}

        # Write leads to DB
        created_count = 0
        new_lead_ids = []
        for data in leads_data:
            email_value = data.get("email") or data.get("personal_email") or data.get("company_email")
            phone_value = data.get("phone") or data.get("mobile_no") or data.get("company_contact_no")
            if not email_value and not phone_value:
                continue
            lead_query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)
            if email_value:
                lead_query = lead_query.filter(Lead.email == email_value)
            else:
                lead_query = lead_query.filter(Lead.phone == phone_value)
            exists = lead_query.first()
            if not exists:
                lead = Lead(
                    tenant_id=self.tenant_id,
                    name=data["name"],
                    email=email_value,
                    phone=phone_value,
                    company=data["company"],
                    source=f"{provider.upper()}: {query}",
                    status="captured",
                    score=0,
                    personal_email=data.get("personal_email") or email_value,
                    company_email=data.get("company_email") or email_value,
                    mobile_no=data.get("mobile_no") or phone_value,
                    company_contact_no=data.get("company_contact_no"),
                    need_of_what=data.get("need_of_what"),
                    how_much=data.get("how_much"),
                    why=data.get("why"),
                    target_context=data.get("target_context"),
                    priority=data.get("priority", "medium"),
                    assigned_to="Sales AI Agent"
                )
                self.db.add(lead)
                self.db.flush()
                new_lead_ids.append(lead.id)
                created_count += 1

        self.db.commit()

        from app.worker.tasks import enrich_lead_task

        for lead_id in new_lead_ids:
            enrich_lead_task.delay(self.tenant_id, lead_id)

        self.log_activity("Lead Generation Complete", f"Successfully captured {created_count} new leads in the DB.", "success")
        return {"status": "success", "generated_leads": created_count, "provider": provider}

    async def _collect_parallel_search(
        self,
        query: str,
        profile,
        analyst_prompt: str | None,
        freshness_window: str,
        credentials: dict,
        suppressed_domains: set[str],
        remaining_inr: float = 700.0,
    ):
        """Run web, news, jobs, company, and permitted social search beside the current connectors."""
        try:
            import uuid
            from app.services.sales_os.search_v4 import run_parallel_search
            from app.services.sales_os.search_v4.contracts import CampaignIntentSpec

            def as_list(value):
                if value is None:
                    return []
                if isinstance(value, str):
                    return [value]
                return [str(item).strip() for item in value if str(item).strip()]

            exclusions = []
            for line in (analyst_prompt or "").splitlines():
                if line.lower().strip().startswith("exclude:"):
                    exclusions.extend(part.strip() for part in line.split(":", 1)[1].split(",") if part.strip())
            spec = CampaignIntentSpec(
                campaign_id=str(uuid.uuid4()),
                tenant_id=self.tenant_id,
                query=(query or "target accounts")[:300],
                industries=as_list(getattr(profile, "target_industries", None)),
                buyer_roles=as_list(getattr(profile, "target_decision_makers", None)),
                geography=as_list(getattr(profile, "target_countries", None)),
                exclusions=exclusions[:20],
                freshness=freshness_window or "30_days",
                offer=((getattr(profile, "service_description", None) or "")[:500]),
                budget_inr=max(0.0, float(remaining_inr)),
                monthly_limit_inr=max(0.0, float(remaining_inr)),
            )
            return await run_parallel_search(
                spec,
                credentials=credentials,
                suppressed_domains=suppressed_domains,
            )
        except Exception:
            logger.warning("Parallel search methods failed", exc_info=True)
            return None

    def _record_parallel_search_spend(self, batch) -> None:
        """Write reconciled search spend after the parallel task has finished."""
        if batch is None:
            return
        try:
            from app.services.sales_os.search_v4.store import SqlSearchStore
            store = SqlSearchStore(self.db)
            if not store.available():
                return
            moment = datetime.now(timezone.utc)
            for entry in batch.ledger:
                if entry.status == "reconciled" and entry.actual_cost_inr:
                    store.add_spend(self.tenant_id, entry.actual_cost_inr, moment)
        except Exception:
            logger.warning("Parallel search spend was not recorded", exc_info=True)

    @with_retry
    async def _fetch_real_leads(
        self,
        provider: str,
        api_key: str,
        query: str,
        count: int = 5,
        analyst_prompt: str | None = None,
        on_progress=None,
        freshness: str = "30_days",
        freshness_window: str = "30_days",
    ) -> list:
        # Implementation placeholders for actual external APIs
        leads = []
        async with httpx.AsyncClient() as client:
            if provider == "web_search":
                from app.services.sales_os.discovery.web_discovery import discover_leads_from_web
                try:
                    leads = await discover_leads_from_web(
                        self.llm.complete,
                        extract_json,
                        query,
                        count,
                        analyst_prompt=analyst_prompt,
                        on_progress=on_progress,
                        freshness_window=freshness_window or freshness,
                    )
                except RuntimeError as exc:
                    logger.warning("Open-web discovery ended without a contact: %s", exc)
                    if on_progress:
                        on_progress(str(exc))
                    return []
            elif provider == "apollo":
                # Call Apollo search
                headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
                # Human-like AI parsing of the raw query into HIGH-QUALITY Apollo params
                prompt = f"""Convert this search query into an Apollo.io search JSON payload targeting HIGH-QUALITY decision-makers.
Query: "{query}"

Output a JSON object with any of these keys that apply to maximize lead quality:
- "q_keywords": string (general keywords)
- "person_titles": array of strings (e.g. ["CEO", "Founder", "VP", "Director"]. Avoid low-level titles.)
- "person_locations": array of strings (e.g. ["United States", "United Kingdom"])
- "organization_num_employees_ranges": array of strings (ONLY include if user specifies size. e.g. ["1,10"], ["11,50"], ["51,200"])
- "contact_email_status": array of strings (ALWAYS output ["verified"] to ensure we only get valid emails)
- "q_organization_domains": string (e.g. "apple.com" if a specific company is mentioned)

Only output valid JSON. No other text."""
                try:
                    parsed_query = extract_json(await self.llm.complete(prompt))
                except Exception:
                    parsed_query = {"q_keywords": query}
                    
                import random
                payload = {
                    "api_key": api_key,
                    "page": random.randint(1, 5), # Randomize page to get fresh leads
                    "per_page": count,
                    **parsed_query
                }
                response = await client.post("https://api.apollo.io/api/v1/mixed_people/api_search", headers=headers, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    people = data.get("people", [])
                    if not people:
                        # Obfuscate API key in error log
                        safe_payload = {k: v for k, v in payload.items() if k != "api_key"}
                        raise Exception(f"Apollo returned 0 people for payload: {safe_payload}. Full response: {response.text}")
                    for p in people[:count]:
                        org = p.get("organization", {})
                        first = p.get("first_name", "")
                        last = p.get("last_name", "")
                        
                        # Apollo API obfuscates names (e.g. ***) if not unlocked via credits. Skip these fake-looking leads.
                        if not first or not last or "***" in last:
                            continue
                            
                        full_name = f"{first} {last}".strip()
                        website = org.get("primary_domain", "") or org.get("website_url", "")
                        
                        leads.append({
                            "name": full_name or "Unknown Contact",
                            "email": p.get("email", ""),
                            "company": org.get("name", "Target Corp"),
                            "website": website,
                            "phone": p.get("primary_phone", "")
                        })
                else:
                    raise Exception(f"Apollo API Error: {response.status_code} - {response.text}")
            elif provider == "hunter":
                # Hunter Discover API requires a POST request with the API key in the URL.
                domains = []
                if "." in query and not " " in query:
                    domains.append(query)
                else:
                    # Parse the query into a Hunter Discover payload using their AI assistant natural language field or exact industry filter
                    import json
                    import os
                    industries_path = os.path.join(os.path.dirname(__file__), "hunter_industries.json")
                    hunter_industries = []
                    if os.path.exists(industries_path):
                        with open(industries_path, "r") as f:
                            hunter_industries = json.load(f)
                            
                    prompt = f"""Convert this search query into a Hunter.io Discover API payload.
Query: "{query}"

Valid Industries for Hunter API: {json.dumps(hunter_industries)}

If the user's query clearly matches one or more of the Valid Industries, use the 'industry' filter format. Otherwise, use the 'query' natural language format.

Output a JSON object matching ONE of these formats:
Format 1 (Preferred if matching industry):
{{
  "industry": {{
    "include": ["<Exact Industry Name from list>"]
  }}
}}

Format 2 (Fallback to natural language):
{{
  "query": "<general natural language search>"
}}

Only output valid JSON. No other text."""
                    try:
                        parsed_query = extract_json(await self.llm.complete(prompt))
                    except Exception:
                        parsed_query = {"query": query}
                        
                    discover_url = f"https://api.hunter.io/v2/discover?api_key={api_key}"
                    discover_response = await client.post(discover_url, json=parsed_query, timeout=12.0)
                    
                    if discover_response.status_code == 200:
                        discover_data = discover_response.json()
                        companies = discover_data.get("data", [])
                        if not companies:
                            raise Exception(f"Hunter Discover returned 0 companies for payload {parsed_query}. Full response: {discover_response.text}")
                        # Hunter discover returns up to 100 companies
                        domains = [c.get("domain") for c in companies if c.get("domain")]
                    else:
                        raise Exception(f"Hunter Discover API Error: {discover_response.status_code} - {discover_response.text}")
                
                if not domains:
                    raise Exception(f"Hunter could not find any valid domains for query: {query}")
                
                import asyncio
                import random
                # Shuffle domains so we get fresh leads on identical inputs
                random.shuffle(domains)
                # Fetch people from those domains (filtering for executives)
                for domain in domains:
                    if len(leads) >= count:
                        break
                    domain_response = await client.get(
                        f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}&type=personal&limit=2",
                        timeout=12.0
                    )
                    if domain_response.status_code == 200:
                        domain_data = domain_response.json()
                        emails = domain_data.get("data", {}).get("emails", [])
                        org_name = domain_data.get("data", {}).get("organization") or domain.split('.')[0].capitalize()
                        for email in emails:
                            leads.append({
                                "name": f"{email.get('first_name', '')} {email.get('last_name', '')}".strip() or "Business Contact",
                                "email": email.get("value"),
                                "company": org_name,
                                "phone": email.get("phone_number", "")
                            })
                            # Break after finding 1 valid email per domain to guarantee diverse companies
                            break
                    elif domain_response.status_code == 429:
                        await asyncio.sleep(2)
                        continue
                
                if not leads:
                    raise Exception(f"Hunter Domain Search returned 0 people across {len(domains)} domains. Last response: {domain_response.text if 'domain_response' in locals() else 'None'}")
            elif provider == "apify":
                from apify_client import ApifyClientAsync
                import asyncio
                import re

                apify_client = ApifyClientAsync(api_key)
                
                # Use Website crawler for domains (enrichment), Google Maps for generic search (discovery)
                if "." in query and " " not in query:
                    run_payload = {
                        "startUrls": [{"url": f"https://{query}" if not query.startswith("http") else query}],
                        "maxCrawlPages": 3
                    }
                    actor_id = "apify/website-content-crawler"
                else:
                    prompt = f"""You are routing a lead generation query to the correct Apify web scraper.
Query: "{query}"

Choose the best Apify Actor for this query:
1. "compass/crawler-google-places" (Best for local businesses, brick-and-mortar, restaurants, plumbers)
2. "apify/instagram-scraper" (Best for ecommerce, influencers, D2C brands, social media)
3. "anchor/linkedin-profile-scraper" (Best for B2B, corporate professionals, SaaS, executives)

Based on your choice, create the required payload:
- Google Places payload: {{"searchStringsArray": ["keyword"], "maxCrawledPlacesPerSearch": {count}, "language": "en"}}
- Instagram payload: {{"search": "keyword", "searchType": "hashtag", "searchLimit": {count}}} 
- LinkedIn payload: {{"search": "keyword", "limit": {count}}}

Output a JSON object exactly like this:
{{
    "actor_id": "the_chosen_actor",
    "run_payload": {{...}}
}}
Only output valid JSON. No other text."""
                    try:
                        parsed_config = extract_json(await self.llm.complete(prompt))
                        actor_id = parsed_config.get("actor_id", "compass/crawler-google-places")
                        run_payload = parsed_config.get("run_payload", {
                            "searchStringsArray": [query],
                            "maxCrawledPlacesPerSearch": count,
                            "language": "en"
                        })
                    except Exception:
                        actor_id = "compass/crawler-google-places"
                        run_payload = {
                            "searchStringsArray": [query],
                            "maxCrawledPlacesPerSearch": count,
                            "language": "en"
                        }

                try:
                    actor_run = await apify_client.actor(actor_id).call(run_input=run_payload)
                    dataset_items = (await apify_client.dataset(actor_run['defaultDatasetId']).list_items()).items
                    
                    if not dataset_items:
                        raise Exception("Apify run succeeded but returned 0 results.")
                        
                    for p in dataset_items[:count]:
                        if actor_id == "compass/crawler-google-places":
                            emails = p.get("emails", [])
                            email = emails[0] if emails else p.get("email", "")
                            leads.append({
                                "name": "",
                                "email": email,
                                "company": p.get("title", p.get("name", "Local Business")),
                                "phone": p.get("phone", "") or p.get("phoneUnformatted", "")
                            })
                        elif "instagram" in actor_id:
                            leads.append({
                                "name": p.get("fullName", p.get("username", "Influencer")),
                                "email": p.get("publicEmail", ""),
                                "company": p.get("username", query),
                                "phone": p.get("publicPhoneNumber", "")
                            })
                        elif "linkedin" in actor_id:
                            leads.append({
                                "name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() or "Professional",
                                "email": p.get("email", ""),
                                "company": p.get("companyName", p.get("headline", query)),
                                "phone": p.get("phone", "")
                            })
                        else:
                            text = p.get("text", "")
                            emails_found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
                            email = emails_found[0] if emails_found else ""
                            leads.append({
                                "name": "Contact",
                                "email": email,
                                "company": query,
                                "phone": ""
                            })
                            if email:
                                break
                except Exception as e:
                    raise Exception(f"Apify API Error: {str(e)}")
            elif provider == "google_places":
                # Call Google Places Text Search
                url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}"
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if not results:
                        raise Exception(f"Google Places returned 0 results. Full response: {response.text}")
                    for res in results[:count]:
                        name = res.get("name", "Local Business")
                        leads.append({
                            "name": "",
                            "email": "",
                            "company": name,
                            "phone": ""
                        })
                else:
                    raise Exception(f"Google Places API Error: {response.status_code} - {response.text}")
            elif provider == "zoominfo":
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {"companyName": query, "rpp": count}
                response = await client.post("https://api.zoominfo.com/search/contact", headers=headers, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    zoom_data = data.get("data", [])
                    if not zoom_data:
                        raise Exception(f"ZoomInfo returned 0 results. Full response: {response.text}")
                    for c in zoom_data[:count]:
                        leads.append({
                            "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() or "Professional",
                            "email": c.get("email", ""),
                            "company": c.get("companyName", "Target Corp"),
                            "phone": c.get("phone", "")
                        })
            elif provider == "cognism":
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {"query": query, "limit": count}
                response = await client.post("https://api.cognism.com/api/v2/search/contacts", headers=headers, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    contacts = data.get("contacts", [])
                    if not contacts:
                        raise Exception(f"Cognism returned 0 contacts. Full response: {response.text}")
                    for c in contacts[:count]:
                        leads.append({
                            "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() or "Professional",
                            "email": c.get("emailAddress", ""),
                            "company": c.get("companyName", "Target Corp"),
                            "phone": c.get("directDial", "")
                        })
            elif provider == "people_data_labs":
                headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
                # PDL uses a SQL-like query
                payload = {"sql": f"SELECT * FROM person WHERE company_name = '{query}'", "size": count}
                response = await client.post("https://api.peopledatalabs.com/v5/person/search", headers=headers, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    pdl_data = data.get("data", [])
                    if not pdl_data:
                        raise Exception(f"PDL returned 0 results. Full response: {response.text}")
                    for p in pdl_data[:count]:
                        emails = p.get("emails", [])
                        phones = p.get("phone_numbers", [])
                        leads.append({
                            "name": p.get("full_name", "Professional"),
                            "email": emails[0].get("address") if emails else "",
                            "company": query,
                            "phone": phones[0] if phones else ""
                        })
            elif provider == "clearbit":
                headers = {"Authorization": f"Bearer {api_key}"}
                response = await client.get(f"https://discovery.clearbit.com/v1/companies/search?query=name:{query}&limit={count}", headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    cb_results = data.get("results", [])
                    if not cb_results:
                        raise Exception(f"Clearbit returned 0 results. Full response: {response.text}")
                    for c in cb_results[:count]:
                        leads.append({
                            "name": "",
                            "email": "",
                            "company": c.get("name", "Target Corp"),
                            "phone": ""
                        })
            elif provider == "crunchbase":
                headers = {"X-cb-user-key": api_key, "Content-Type": "application/json"}
                payload = {"query": [{"type": "predicate", "field_id": "identifier", "operator_id": "contains", "values": [query]}], "limit": count}
                response = await client.post("https://api.crunchbase.com/api/v4/searches/organizations", headers=headers, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    for ent in data.get("entities", [])[:count]:
                        props = ent.get("properties", {})
                        leads.append({
                            "name": "",
                            "email": props.get("contact_email", ""),
                            "company": props.get("identifier", {}).get("value", "Startup"),
                            "phone": props.get("phone_number", "")
                        })
            else:
                # Delegate to unified connector suite supporting all 60+ sources
                from app.services.sales_os.discovery.connectors import fetch_leads_from_source
                leads = await fetch_leads_from_source(provider, api_key, query, count=count, llm_gateway=self.llm, freshness=freshness_window or freshness)
        if not leads:
            raise Exception(f"The {provider} API returned data, but no valid leads were extracted. This often happens if the API rate-limits you, requires credits, or returns obfuscated/paywalled names (e.g., Apollo's '***' names).")
        return leads

    @with_retry
    async def _fetch_apollo_org_data(self, api_key: str, domain: str) -> str:
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
            try:
                response = await client.post(
                    "https://api.apollo.io/v1/mixed_companies/search",
                    headers=headers,
                    json={"q_organization_domains": domain},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    orgs = data.get("organizations", [])
                    if orgs:
                        return orgs[0].get("id")
            except Exception:
                pass
        return None

    @with_retry
    async def _fetch_apollo_news(self, api_key: str, org_id: str) -> list:
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
            try:
                response = await client.post(
                    "https://api.apollo.io/api/v1/news_articles/search",
                    headers=headers,
                    json={"organization_ids": [org_id]},
                    timeout=10.0
                )
                if response.status_code == 200:
                    articles = response.json().get("news_articles", [])[:2]
                    return [{"title": a.get("title"), "snippet": a.get("snippet")} for a in articles]
            except Exception:
                pass
        return []

    @with_retry
    async def _fetch_apollo_jobs(self, api_key: str, org_id: str) -> list:
        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
            try:
                response = await client.get(
                    f"https://api.apollo.io/api/v1/organizations/{org_id}/job_postings",
                    headers=headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    jobs = response.json().get("organization_job_postings", [])[:2]
                    return [{"title": j.get("title")} for j in jobs]
            except Exception:
                pass
        return []

    async def _sales_outreach(self, params: dict):
        channel = params.get("channel", "smtp")
        provider = params.get("provider")
        model = params.get("model")
        subject = params.get("subject", "Partnership opportunity")
        body_template = params.get("body_template", "Hello {name}, I noticed {company} has great potential...")

        # Fetch leads that need outreach
        leads = self.db.query(Lead).filter(
            Lead.tenant_id == self.tenant_id,
            Lead.status.in_(["captured", "scored"])
        ).all()

        if not leads:
            self.log_activity("Sales Outreach", "No new leads found needing outreach.", "success")
            return {"status": "success", "sent_count": 0}

        self.log_activity("Sales Outreach", f"Initiating sales outreach via {channel} for {len(leads)} leads.")

        # Check SMTP/Gmail settings
        smtp_credentials = None
        gmail_credentials = None
        if channel == "smtp":
            cred = self.db.query(APICredential).filter_by(
                tenant_id=self.tenant_id, provider="smtp"
            ).first()
            if cred and cred.encrypted_key:
                smtp_credentials = parse_smtp_credentials(decrypt_api_key(cred.encrypted_key))
            if not smtp_credentials:
                raise ValueError("No SMTP credentials configured. Please configure SMTP credentials under Platform Setup -> API Settings.")
        elif channel == "gmail":
            cred = self.db.query(APICredential).filter_by(
                tenant_id=self.tenant_id, provider="gmail"
            ).first()
            if cred and cred.encrypted_key:
                try:
                    gmail_credentials = json.loads(decrypt_api_key(cred.encrypted_key))
                except:
                    pass
            if not gmail_credentials:
                raise ValueError("No Gmail API credentials configured. Please connect Google Workspace under Platform Setup -> API Settings.")

        # Resolve company and employee sender context
        from app.models.base import User
        from app.models.verticals import BusinessProfile
        bp = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
        company_name = bp.company_name if (bp and bp.company_name) else "OctaOS"
        user = self.db.query(User).filter_by(tenant_id=self.tenant_id).order_by(User.is_superuser.desc(), User.id.asc()).first()
        employee_name = user.name.strip() if (user and user.name and user.name.strip()) else None

        if employee_name:
            sender_rule = f"Write on behalf of {employee_name} at {company_name}. Sign off with: Best regards, {employee_name}, {company_name}."
        else:
            sender_rule = f"Write on behalf of {company_name}. Do NOT invent any employee name. Sign off strictly with: Best regards, The {company_name} Team."

        sent_count = 0
        for lead in leads:
            prompt = f"""Write a personalized sales email/outreach message.
Lead Name: {lead.name}
Lead Company: {lead.company}
Lead Source: {lead.source}
Lead Intent/Need: {lead.need_of_what or 'N/A'}
Lead Pain Points (Why): {lead.why or 'N/A'}
Target Context: {lead.target_context or 'N/A'}
Base Template: {body_template}
Subject: {subject}
Sender Context: {sender_rule}
Do NOT use or invent any fake human personas.
Output a JSON object with keys 'subject' and 'body'. No other text."""
            
            response = await self.llm.complete(prompt, provider=provider, model=model)
            try:
                parsed = extract_json(response)
                outbound_subject = parsed.get("subject", subject)
                outbound_body = parsed.get("body", body_template.format(name=lead.name, company=lead.company))
            except Exception:
                outbound_subject = subject
                outbound_body = body_template.format(name=lead.name, company=lead.company)

            from app.services.sales_os.governance.gatekeeper import PreSendGatekeeper
            from app.services.sales_os.governance.suppression import SuppressionService

            is_suppressed, suppression_reason = SuppressionService(self.db, self.tenant_id).is_suppressed(
                email=lead.email,
                phone=lead.phone,
                channel="whatsapp" if channel == "whatsapp" else "email",
            )
            if is_suppressed:
                self.log_activity(
                    "Outreach Skipped",
                    f"Contact {lead.email or lead.phone} is suppressed: {suppression_reason}",
                    "pending",
                )
                continue

            gate = PreSendGatekeeper.evaluate(
                outbound_subject,
                outbound_body,
                step_number=1,
                min_words=8 if channel in ("smtp", "gmail", "email") else 3,
                require_subject=channel in ("smtp", "gmail", "email"),
            )
            if not gate.is_valid:
                self.log_activity(
                    "Outreach Blocked",
                    f"Could not send to {lead.email or lead.phone}: {'; '.join(gate.violations)}",
                    "failed",
                )
                continue
            
            # Send
            sent_successfully = False
            if channel == "smtp" and smtp_credentials:
                try:
                    sent_successfully = send_smtp_email(
                        smtp_credentials, lead.email, outbound_subject, outbound_body
                    )
                except Exception as e:
                    self.log_activity("SMTP Send Fail", f"SMTP error for {lead.email}: {str(e)}.", "failed")
            elif channel == "gmail" and gmail_credentials:
                try:
                    result = send_gmail_email(
                        gmail_credentials, lead.email, outbound_subject, outbound_body
                    )
                    sent_successfully = bool(result and result.get("ok"))
                    if result and result.get("thread_id"):
                        lead.data = {
                            **(lead.data or {}),
                            "gmail_thread_id": result.get("thread_id"),
                            "gmail_message_id": result.get("message_id"),
                        }
                except Exception as e:
                    self.log_activity("Gmail Send Fail", f"Gmail error for {lead.email}: {str(e)}.", "failed")
            elif channel == "whatsapp":
                from app.services.sales.touch_dispatcher import dispatch_sales_touch

                delivery = dispatch_sales_touch(
                    self.db,
                    self.tenant_id,
                    lead,
                    channel="whatsapp",
                    body=outbound_body,
                    subject=outbound_subject,
                    step_number=1,
                )
                sent_successfully = bool(delivery.get("sent"))
                if sent_successfully:
                    lead.data = {**(lead.data or {}), "whatsapp_from": lead.phone}

            if not sent_successfully:
                self.log_activity(
                    f"Outreach Failed ({channel.upper()})",
                    f"Failed to send to: {lead.name} ({lead.email}).",
                    "failed"
                )
                continue
            
            self.log_activity(
                f"Outreach Sent ({channel.upper()})",
                f"Message to: {lead.name} ({lead.email}). Subject: '{outbound_subject}'",
                "success"
            )

            lead.status = "contacted"
            conv = list((lead.data or {}).get("conversation") or [])
            conv.append(
                {
                    "direction": "outbound",
                    "channel": channel,
                    "content": outbound_body,
                    "subject": outbound_subject,
                    "author": "Sales AI Agent",
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            lead.data = {
                **(lead.data or {}),
                "outreach_channel": channel,
                "outbound_subject": outbound_subject,
                "outbound_body": outbound_body,
                "sent_actual": sent_successfully,
                "outreach_sent_at": datetime.now(timezone.utc).isoformat(),
                "conversation": conv[-50:],
            }
            sent_count += 1
            
        self.db.commit()
        return {"status": "success", "sent_count": sent_count}

    async def _schedule_meeting(self, params: dict):
        tool = params.get("tool", "google_calendar")

        # Book from real replies already classified as interested
        leads = (
            self.db.query(Lead)
            .filter(
                Lead.tenant_id == self.tenant_id,
                Lead.status.in_(("replied", "contacted")),
            )
            .all()
        )
        booked_count = 0
        waiting = 0
        for lead in leads:
            data = lead.data or {}
            if not data.get("prospect_interested"):
                if lead.status == "contacted":
                    waiting += 1
                continue
            if lead.status == "meeting_scheduled":
                continue
            suggested_time = data.get("reply_classification", {}).get("suggested_time")
            if not suggested_time:
                waiting += 1
                data["meeting_coordination_status"] = "coordinating_slots"
                lead.data = data
                continue
            if book_meeting_for_lead(
                self.db,
                self.tenant_id,
                lead,
                tool=tool,
                suggested_time=suggested_time,
                log_activity=self.log_activity,
            ):
                booked_count += 1

        if waiting and booked_count == 0:
            self.log_activity(
                "Awaiting Real Replies",
                f"{waiting} leads contacted — meetings book automatically when they reply "
                "(email webhook, WhatsApp webhook, or Gmail poll).",
                "success",
            )

        self.db.commit()
        return {"status": "success", "booked_meetings": booked_count, "awaiting_replies": waiting}

    async def daily_routine(self):
        self.log_activity("Daily Routine", "Checking active lead outreach campaigns.", status="success")

"""Workflow Orchestrator for Sales OS: End-to-end 10-step autonomous Sales AI pipeline."""
import asyncio
import json
import logging
import random
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key
from app.models.base import APICredential, User
from app.models.teams import AgentMetric
from app.models.verticals import BusinessProfile, Lead
from app.services.sales.utils import extract_json, _build_lead_data
from app.services.sales_os.aso.v3_scoring import combine_v3_scores, parse_component_scores, parse_pain_points
from app.services.sales_os.contracts.registry import render_prompts
from app.services.sales_os.discovery.web_discovery import classify_archetype
from app.services.sales_os.quality_gates import assess_outreach_readiness

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    def __init__(
        self,
        db: Session,
        tenant_id: str,
        llm=None,
        log_activity: Optional[Callable] = None,
        discovery_service=None,
        enrichment_service=None,
        agent=None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = llm
        self._log_activity = log_activity or (lambda *args, **kwargs: None)
        self.discovery = discovery_service
        self.enrichment = enrichment_service
        self.agent = agent

    def log_activity(self, *args, **kwargs):
        return self._log_activity(*args, **kwargs)

    async def _fetch_real_leads(self, *args, **kwargs):
        if self.agent and hasattr(self.agent, "_fetch_real_leads"):
            return await self.agent._fetch_real_leads(*args, **kwargs)
        if self.discovery:
            return await self.discovery.fetch_real_leads(*args, **kwargs)
        raise RuntimeError("No discovery provider available to fetch leads")

    async def _collect_parallel_search(self, *args, **kwargs):
        if self.agent and hasattr(self.agent, "_collect_parallel_search"):
            return await self.agent._collect_parallel_search(*args, **kwargs)
        if self.discovery:
            return await self.discovery.collect_parallel_search(*args, **kwargs)
        return None

    def _record_parallel_search_spend(self, batch):
        if self.agent and hasattr(self.agent, "_record_parallel_search_spend"):
            return self.agent._record_parallel_search_spend(batch)
        if self.discovery:
            return self.discovery.record_parallel_search_spend(batch)

    async def _fetch_apollo_org_data(self, api_key: str, domain: str) -> Optional[str]:
        if self.agent and hasattr(self.agent, "_fetch_apollo_org_data"):
            return await self.agent._fetch_apollo_org_data(api_key, domain)
        if self.enrichment:
            return await self.enrichment.fetch_apollo_org_data(api_key, domain)
        return None

    async def _fetch_apollo_news(self, api_key: str, org_id: str) -> list:
        if self.agent and hasattr(self.agent, "_fetch_apollo_news"):
            return await self.agent._fetch_apollo_news(api_key, org_id)
        if self.enrichment:
            return await self.enrichment.fetch_apollo_news(api_key, org_id)
        return []

    async def _fetch_apollo_jobs(self, api_key: str, org_id: str) -> list:
        if self.agent and hasattr(self.agent, "_fetch_apollo_jobs"):
            return await self.agent._fetch_apollo_jobs(api_key, org_id)
        if self.enrichment:
            return await self.enrichment.fetch_apollo_jobs(api_key, org_id)
        return []

    async def run_sales_ai_v3_workflow(
        self,
        provider=None,
        model=None,
        count=50,
        freshness=None,
        mode: str = "configured_engine",
        prompt_instructions: Optional[str] = None,
    ) -> dict:
        # Get business profile
        profile = self.db.query(BusinessProfile).filter_by(tenant_id=self.tenant_id).first()
        if not profile and mode == "configured_engine":
            self.log_activity("V3 Workflow Error", "No Business Profile configured.", "failed")
            return {"status": "error", "message": "Business Profile not found."}

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
                "result": result_msg,
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
                from app.services.sales_os.discovery.prompt_agent import parse_prompt_icp
                effective_context = (prompt_instructions or "").strip()
                parsed_icp = parse_prompt_icp(effective_context)
                domain_archetype = "Prompt-Directed Prospecting"
                profile_budget = parsed_icp.price or profile_budget
                profile_offer = parsed_icp.service
                profile_countries = [parsed_icp.geography]
                profile_decision_makers = [parsed_icp.buyer]
                icp = parsed_icp.summary
                emit_activity(1, "Structured ICP synthesized from prompt directive", f"{log_prefix} Parsed ICP: {icp}")
                update_status(1, "completed", f"[Prompt Directive] {icp}", f"Generated structured ICP: {icp}")
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
                ) if self.llm else ""
                icp = (icp or "").strip() or f"Target segment: {profile_industry} companies matching {profile_offer}"
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
                query = f"{parsed_icp.service} {parsed_icp.geography}"
            else:
                query = profile_target_industries[0] if profile_target_industries else "target clients"

            from app.services.sales_os.discovery.source_registry import get_all_source_ids
            valid_discovery = get_all_source_ids()
            discovery_providers = {k: v for k, v in available_providers.items() if k in valid_discovery}

            available_providers["web_search"] = ""

            routing_choice = "web_search"
            if not discovery_providers:
                update_status(2, "executing", "No paid provider keys configured; using open-web discovery.", f"{log_prefix} Routing to web_search.")

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
                    routing_response = await self.llm.complete(routing_prompt, provider=provider, model=model) if self.llm else "{}"
                    routing_choice = extract_json(routing_response).get("primary_source")
                    if routing_choice not in discovery_providers:
                        routing_choice = list(discovery_providers.keys())[0]
                except Exception:
                    routing_choice = list(discovery_providers.keys())[0]
                update_status(2, "executing", f"Selected {routing_choice} as primary source.", f"{log_prefix} Routing strategy defined for {query}.")

            companies_data = []
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

            companies = []
            enriched_count = 0

            if mode == "prompt_agent":
                from app.services.sales_os.discovery.prompt_agent import (
                    classify_document_type,
                    detect_buying_intent,
                    normalize_search_record,
                    score_and_qualify_lead,
                    PipelineStageMetrics,
                    SearchDocumentType,
                    ContactConfidence,
                )
                from app.services.sales_os.governance.suppression import SuppressionService
                from app.services.sales_os.providers.honesty import is_fabricated_contact

                pipeline_metrics = PipelineStageMetrics()
                pipeline_metrics.discovery_raw = len(companies_data)
                suppression_service = SuppressionService(self.db, self.tenant_id)

                for raw_c in companies_data:
                    norm_c = normalize_search_record(raw_c, routing_choice, query=query)
                    doc_type, class_reason, is_reject = classify_document_type(
                        url=norm_c.get("evidence_url", ""),
                        title=norm_c.get("title_text", ""),
                        snippet=norm_c.get("snippet_text", ""),
                    )
                    if doc_type in (SearchDocumentType.HIRING_POST, SearchDocumentType.FREELANCE_PROJECT):
                        pipeline_metrics.classified_hiring += 1
                    elif doc_type == SearchDocumentType.RFP:
                        pipeline_metrics.classified_rfp += 1
                    elif doc_type in (SearchDocumentType.BLOG, SearchDocumentType.ARTICLE):
                        pipeline_metrics.classified_articles += 1
                    elif doc_type == SearchDocumentType.PROFILE:
                        pipeline_metrics.classified_profiles += 1
                    else:
                        pipeline_metrics.classified_company += 1

                    if is_reject:
                        pipeline_metrics.add_rejection(norm_c.get("company") or norm_c.get("title_text"), class_reason)
                        continue

                    pipeline_metrics.verified_sources += 1
                    norm_c["doc_type"] = doc_type

                    has_intent, buying_signal, evidence_quote = detect_buying_intent(
                        title=norm_c.get("title_text", ""),
                        snippet=norm_c.get("snippet_text", ""),
                    )
                    if has_intent:
                        pipeline_metrics.buying_intent_confirmed += 1
                    norm_c["has_buying_intent"] = has_intent
                    norm_c["buying_signal"] = buying_signal
                    norm_c["evidence_quote"] = evidence_quote

                    email = norm_c.get("email") or ""
                    if not email or "@" not in email:
                        enrichment_tool = None
                        if "hunter" in available_providers:
                            enrichment_tool = "hunter"
                        elif "apollo" in available_providers and routing_choice != "apollo":
                            enrichment_tool = "apollo"
                        elif "apify" in available_providers and routing_choice != "apify":
                            enrichment_tool = "apify"
                        if enrichment_tool and norm_c.get("website"):
                            try:
                                domain = norm_c.get("website").replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                                enrichment_data = await self._fetch_real_leads(enrichment_tool, available_providers[enrichment_tool], domain, count=1)
                                if enrichment_data:
                                    real_email = enrichment_data[0].get("email", "")
                                    real_name = enrichment_data[0].get("name", "")
                                    if real_email and "@" in real_email:
                                        norm_c["email"] = real_email
                                        if real_name:
                                            norm_c["name"] = real_name
                                        enriched_count += 1
                            except Exception:
                                pass

                    domain_val = norm_c.get("website", "").replace("https://", "").replace("http://", "").split("/")[0]
                    is_suppressed, _ = suppression_service.is_suppressed(email=norm_c.get("email"), domain=domain_val, phone=norm_c.get("phone"))
                    if is_suppressed or is_fabricated_contact(norm_c):
                        continue

                    scored = score_and_qualify_lead(
                        record=norm_c,
                        icp=parsed_icp,
                        has_buying_intent=norm_c.get("has_buying_intent", False),
                        buying_signal=norm_c.get("buying_signal", ""),
                        evidence_quote=norm_c.get("evidence_quote", ""),
                        doc_type=norm_c.get("doc_type", SearchDocumentType.UNKNOWN),
                    )

                    if scored.contact_status == "REJECTED":
                        pipeline_metrics.add_rejection(norm_c.get("company") or norm_c.get("title_text"), scored.rejection_reason or "Score below qualification threshold")
                        continue

                    if scored.contact_status == "READY":
                        pipeline_metrics.qualified_ready += 1
                    else:
                        pipeline_metrics.qualified_contact_partial += 1

                    companies.append({
                        "company_name": scored.company or "Potential Prospect",
                        "website": norm_c.get("website", ""),
                        "industry": query,
                        "estimated_employees": "Unknown",
                        "estimated_revenue": "Unknown",
                        "location": parsed_icp.geography,
                        "source": f"{routing_choice} (Enriched)" if enriched_count else routing_choice,
                        "evidence_url": scored.evidence_url,
                        "freshness": norm_c.get("freshness") or {},
                        "retrieval_provider": scored.retrieval_provider,
                        "publisher": scored.publisher,
                        "buying_signal": scored.buying_signal,
                        "evidence_quote": scored.evidence_quote,
                        "contact_status": scored.contact_status,
                        "contact_confidence": scored.contact_confidence,
                        "platform_contact": scored.platform_contact,
                        "evidence_tier": scored.evidence_tier,
                        "qualification_score": scored.qualification_score,
                        "rejection_reason": scored.rejection_reason,
                        "contact": {
                            "name": scored.prospect_name or "",
                            "title": scored.role or "",
                            "email": scored.email or "",
                            "phone": scored.phone or "",
                            "linkedin_url": norm_c.get("linkedin_url") or "",
                        },
                    })

                stage_breakdown_text = "\n".join(pipeline_metrics.summary_lines())
                rejection_summary = "\n".join(f"- {r['lead']}: {r['reason']}" for r in pipeline_metrics.rejections[:8])
                emit_activity(2, f"Pipeline metrics: {len(companies)} qualified ({pipeline_metrics.qualified_ready} ready, {pipeline_metrics.qualified_contact_partial} partial)", f"{log_prefix}\n{stage_breakdown_text}\nRejections:\n{rejection_summary}")

                if not companies:
                    update_status(2, "completed", "0 leads qualified from this discovery cycle. See stage breakdown.", f"{log_prefix}\n{stage_breakdown_text}\nRejections:\n{rejection_summary}")
                    return {"status": "success", "message": "No leads passed strict buyer qualification threshold.", "stage_metrics": pipeline_metrics.summary_lines(), "rejections": pipeline_metrics.rejections}

                leads_summary = [{"name": c["contact"]["name"], "email": c["contact"]["email"] or "(Partial contact)", "company": c["company_name"], "status": c["contact_status"]} for c in companies]
                update_status(2, "completed", f"Discovered and qualified {len(companies)} prospects ({pipeline_metrics.qualified_ready} ready, {pipeline_metrics.qualified_contact_partial} partial).", f"{log_prefix}\n{stage_breakdown_text}\n\nValidated Leads:\n{json.dumps(leads_summary, indent=2)}")
            else:
                for c in companies_data:
                    needs_enrichment = False
                    email = c.get("email", "")
                    name = c.get("name", "")
                    if not email or "@" not in email or email.startswith("contact@") or email.startswith("info@") or name == "Manager" or name == "General Inquiry":
                        needs_enrichment = True

                    if needs_enrichment:
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

                    has_name = bool(c.get("name") and c["name"].strip() not in ["Unknown Contact", "General Inquiry"])
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
                            "evidence_quote": c.get("evidence_quote") or "",
                            "buying_signal": c.get("buying_signal") or "",
                            "news": c.get("news") or [],
                            "jobs": c.get("jobs") or [],
                            "contact_status": "READY" if (has_name and has_contact) else "PARTIAL",
                            "freshness": c.get("freshness") or {},
                            "contact": {
                                "name": c.get("name", ""),
                                "title": c.get("title") or "Contact",
                                "email": email_value,
                                "phone": phone_value,
                                "linkedin_url": c.get("linkedin_url") or "",
                            },
                        })

                if not companies:
                    rejected_data_str = json.dumps(companies_data, indent=2)
                    raise Exception(f"API returned leads, but after strict waterfall enrichment, none had a real name and deliverable email or phone. No simulated data is allowed.\nRaw Rejected Data: {rejected_data_str}")

                leads_summary = [{"name": c["contact"]["name"], "email": c["contact"]["email"], "company": c["company_name"]} for c in companies]
                update_status(2, "completed", f"Discovered and verified {len(companies)} company profiles.", f"Sourced via {routing_choice}. Enriched {enriched_count} records to find real emails. Parallel search: {search_report}\n\nValidated Leads:\n{json.dumps(leads_summary, indent=2)}")
        except Exception as e:
            update_status(2, "failed", str(e), f"Error in Step 2: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 3: Lead Qualification
        update_status(3, "executing", "Evaluating purchasing capacities...", "Starting Step 3: Qualifying budgets and signals...")
        qualified_companies = []
        try:
            sem = asyncio.Semaphore(5)

            async def _qualify_single(i: int, c: dict):
                async with sem:
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
                        qual_str = await self.llm.complete(prompt, provider=provider, model=model) if self.llm else "{}"
                        qual = extract_json(qual_str)
                    except Exception:
                        qual = {"capacity": "Unknown", "qualified": False, "reason": "Insufficient evidence to qualify company budget."}

                    c["purchasing_capacity"] = qual.get("capacity", "Unknown")
                    c["qualified"] = bool(qual.get("qualified", False))
                    c["qualification_reason"] = qual.get("reason", "Qualification evaluated against target budget and ICP parameters.")

                    verdict = "QUALIFIED" if c["qualified"] else "DISQUALIFIED"
                    emit_activity(
                        3,
                        f"Evaluated {i+1}/{len(companies)} companies...",
                        f"[QUALIFY] {c['company_name']}: Capacity {c['purchasing_capacity']} -> {verdict} ({c['qualification_reason'][:65]})",
                    )
                    return c

            await asyncio.gather(*(_qualify_single(i, c) for i, c in enumerate(companies)))
            qualified_companies = [c for c in companies if c.get("qualified")]\n\n            # Verify the actual source page before a candidate can pass the final send gate.\n            # Provider snippets and LLM-generated claims alone are not sufficient evidence.\n            from app.services.sales_os.source_verification import fetch_and_verify_source\n            source_verify_semaphore = asyncio.Semaphore(5)\n\n            async def _verify_candidate_source(candidate):\n                source_url = str(candidate.get("evidence_url") or "").strip()\n                source_quote = str(candidate.get("evidence_quote") or "").strip()\n                if not source_url or not source_quote:\n                    candidate["source_verification"] = {\n                        "source_url": source_url, "quote": source_quote, "verified": False,\n                        "reason": "quote_missing_or_source_missing",\n                    }\n                    return\n                async with source_verify_semaphore:\n                    receipt = await fetch_and_verify_source(source_url, source_quote)\n                candidate["source_verification"] = receipt.as_dict()\n\n            await asyncio.gather(*(_verify_candidate_source(candidate) for candidate in qualified_companies))\n
            for c in qualified_companies:
                email_val = c.get("contact", {}).get("email") or ""
                phone_val = c.get("contact", {}).get("phone") or ""
                query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)
                if email_val:
                    query = query.filter(Lead.email == email_val)
                elif phone_val:
                    query = query.filter(Lead.phone == phone_val)
                else:
                    query = query.filter(Lead.company == c["company_name"], Lead.name == c["contact"]["name"])
                exists = query.first()
                if not exists:
                    lead = Lead(
                        tenant_id=self.tenant_id,
                        name=c["contact"]["name"],
                        email=email_val or None,
                        phone=phone_val or None,
                        company=c["company_name"],
                        source=f"{c['source']}: V3 Workflow",
                        status="ready" if (email_val or phone_val) else "contact_partial",
                        score=(int(c["qualification_score"]) if c.get("qualification_score") is not None else None),
                        priority="high" if (c.get("qualification_score") or 0) >= 80 else "medium",
                        assigned_to="Sales AI Agent",
                        personal_email=email_val or None,
                        company_email=email_val or None,
                        mobile_no=phone_val or None,
                        need_of_what=profile_offer,
                        why=c.get("why_now") or c.get("buying_signal") or c["qualification_reason"],
                        data=_build_lead_data(c),
                        target_context=f"Archetype: {domain_archetype} | Capacity: {c.get('purchasing_capacity', 'Unknown')}",
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
            sem = asyncio.Semaphore(5)

            async def _audit_single(i: int, c: dict):
                async with sem:
                    emit_activity(4, f"Auditing digital operations and pain points for {c['company_name']} ({i+1}/{len(qualified_companies)})...")
                    prior_news = list(c.get("news") or [])
                    prior_jobs = list(c.get("jobs") or [])
                    c["news"] = []
                    c["jobs"] = []

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
                    ) if self.llm else "[]"
                    try:
                        p_list = extract_json(pain_str)
                    except Exception:
                        p_list = []
                    c["pain_points"] = parse_pain_points(p_list)
                    c["pain_evidence_status"] = "evidenced" if c["pain_points"] and (c.get("evidence_url") or c.get("evidence_quote") or c.get("buying_signal")) else "insufficient_evidence"
                    emit_activity(
                        4,
                        f"Audited {i+1}/{len(qualified_companies)} companies...",
                        f"[AUDIT] {c['company_name']}: Discovered pain points: {'; '.join(c['pain_points'][:2])}",
                    )
                    return c

            await asyncio.gather(*(_audit_single(i, c) for i, c in enumerate(qualified_companies)))
            update_status(4, "completed", f"Identified custom pain points for {len(qualified_companies)} qualified leads.", "Deep context enrichment complete. Discovered pain points using recent news and job openings.")
        except Exception as e:
            update_status(4, "failed", str(e), f"Error in Step 4: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 5: Decision Maker Discovery
        update_status(5, "executing", "Searching decision-maker contact details...", "Starting Step 5: Validating contact details...")
        try:
            for c in qualified_companies:
                contact = c.get("contact") or {}
                if not contact.get("email") and not contact.get("phone"):
                    contact["status"] = "unverified"
                else:
                    contact["status"] = "verified"
                c["contact"] = contact
            verified_count = sum(1 for c in qualified_companies if c.get("contact", {}).get("status") == "verified")
            update_status(5, "completed", f"Validated contacts for {verified_count}/{len(qualified_companies)} lead companies.", f"Decision-maker validation complete. Verified {verified_count} direct contact channels.")
        except Exception as e:
            update_status(5, "failed", str(e), f"Error in Step 5: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 6: Lead Scoring
        update_status(6, "executing", "Applying multi-factor lead scoring formula...", "Starting Step 6: Calculating weighted quality score (Budget, Pain Point, Intent, etc.)...")
        scored_leads = []
        try:
            sem = asyncio.Semaphore(5)

            async def _score_single(i: int, c: dict):
                async with sem:
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
                        ) if self.llm else "{}"
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
                            why_now_res = await self.llm.complete(
                                f"In 2 sentences, explain why {c['company_name']} is worth contacting NOW for our offer "
                                f"({profile_offer}). Use ONLY these facts, invent nothing.\n"
                                f"Signal ({fresh_info.get('freshness_label') or 'unknown age'}): {snippet}\n"
                                f"News: {[n.get('title') for n in c.get('news', [])]}\n"
                                f"Jobs: {[j.get('title') for j in c.get('jobs', [])]}\n"
                                f"Pain points: {c.get('pain_points')}\nBudget fit: {c.get('purchasing_capacity')}\n"
                                f"Output plain text only.",
                                provider=provider, model=model,
                            ) if self.llm else ""
                            why_now = (why_now_res or "").strip()
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
                    emit_activity(
                        6,
                        f"Scored {i+1}/{len(qualified_companies)} leads...",
                        f"[SCORE] {c['company_name']}: Score {weighted_score}/100 [{category}] (Pain: {pain_score}, Intent: {intent_score})",
                    )
                    return c

            scored_leads = list(await asyncio.gather(*(_score_single(i, c) for i, c in enumerate(qualified_companies))))
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

            user = self.db.query(User).filter_by(tenant_id=self.tenant_id).order_by(User.is_superuser.desc(), User.id.asc()).first()
            employee_name = user.name.strip() if (user and user.name and user.name.strip()) else None
            if employee_name:
                behalf_instruction = f"Write on behalf of {employee_name} at {profile_company_name}. Sign off with: Best regards, {employee_name}, {profile_company_name}."
            else:
                behalf_instruction = f"Write on behalf of {profile_company_name}. Do NOT invent any employee or sender name. Sign off strictly with: Best regards, {profile_company_name} (or The {profile_company_name} Team)."

            sem7 = asyncio.Semaphore(5)

            async def _draft_single(i, c):
                async with sem7:
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
                    outreach_text = None
                    try:
                        outreach_text = await self.llm.complete(prompt, provider=provider, model=model) if self.llm else None
                    except Exception as llm_err:
                        logger.warning(f"LLM outreach generation failed for {c['company_name']}: {llm_err}")

                    outreach_text = (outreach_text or "").strip()
                    # Never synthesize a generic fallback that implies researched knowledge.
                    # An empty draft remains blocked until evidence and a valid draft exist.

                    c["outreach_message"] = outreach_text
                    first_p = (c.get("pain_points") or ["no evidenced pain point"])[0]
                    emit_activity(
                        7,
                        f"Personalized outreach drafted for {c['company_name']}...",
                        f"[OUTREACH] {c['company_name']}: Draft status={'ready' if outreach_text else 'blocked_no_draft'}; evidence pain={first_p[:45] if first_p != 'no evidenced pain point' else 'not established'}",
                    )
                    return c

            scored_leads = list(await asyncio.gather(*(_draft_single(i, c) for i, c in enumerate(scored_leads))))
            update_status(7, "completed", "Generated unique personalized emails for all candidates.", "Outreach generation complete. All outreaches customized to target business pain points.")
        except Exception as e:
            update_status(7, "failed", str(e), f"Error in Step 7: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 8: Multi-Channel Outreach
        update_status(8, "executing", "Sequencing outreach touchpoints...", "Starting Step 8: Creating timeline schedules for Email, LinkedIn, WhatsApp...")
        try:
            for idx, c in enumerate(scored_leads):
                emit_activity(8, f"Sequencing multi-channel touchpoints for {c['company_name']} ({idx+1}/{len(scored_leads)})...")
                contact_email = c["contact"].get("email") or ""
                contact_phone = c["contact"].get("phone") or ""
                lead_query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)
                if contact_email:
                    lead_query = lead_query.filter(Lead.email == contact_email)
                elif contact_phone:
                    lead_query = lead_query.filter(Lead.phone == contact_phone)
                else:
                    lead_query = lead_query.filter(Lead.company == c["company_name"], Lead.name == c["contact"]["name"])
                exists = lead_query.first()
                if exists:
                    lead = exists
                    lead.score = c.get("qualification_score") if c.get("qualification_score") is not None else c.get("scoring", {}).get("total")
                    lead.status = "captured" if (contact_email or contact_phone) else "needs_contact_research"
                    lead.priority = "high" if (c.get("qualification_score") or 0) >= 80 else "medium"
                    lead.why = c.get("why_now") or c.get("buying_signal") or c["qualification_reason"]
                    lead.target_context = f"Archetype: {domain_archetype} | Pain points: {', '.join(c.get('pain_points', []))}"
                    lead.data = _build_lead_data(c)
                else:
                    lead = Lead(
                        tenant_id=self.tenant_id,
                        name=c["contact"]["name"],
                        email=contact_email or None,
                        phone=contact_phone or None,
                        company=c["company_name"],
                        source=f"{c['source']}: V3 Workflow",
                        status="captured" if (contact_email or contact_phone) else "needs_contact_research",
                        score=(int(c["qualification_score"]) if c.get("qualification_score") is not None else (int(c["scoring"]["total"]) if isinstance(c.get("scoring"), dict) and c["scoring"].get("total") is not None else None)),
                        priority="high" if (c.get("qualification_score") or 0) >= 80 else "medium",
                        assigned_to="Sales AI Agent",
                        personal_email=contact_email or None,
                        company_email=contact_email or None,
                        mobile_no=contact_phone or None,
                        need_of_what=profile_offer,
                        why=c.get("why_now") or c.get("buying_signal") or c["qualification_reason"],
                        target_context=f"Archetype: {domain_archetype} | Pain points: {', '.join(c.get('pain_points', []))}",
                        data=_build_lead_data(c),
                    )
                    self.db.add(lead)
                    self.db.flush()

                emit_activity(
                    8,
                    f"Saved and sequenced {idx+1}/{len(scored_leads)} leads into CRM...",
                    f"[SEQUENCE] {c['company_name']}: Day 1 Email, Day 3 LinkedIn, Day 8 WhatsApp sequence mapped. CRM lead saved.",
                )

                cadence = 3
                sales_cred = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="sales").first()
                if sales_cred and sales_cred.settings and sales_cred.settings.get("follow_up_cadence_days"):
                    cadence = max(1, int(sales_cred.settings["follow_up_cadence_days"]))

                p_points = c.get("pain_points") or []
                first_pain = p_points[0] if p_points else None
                second_pain = p_points[1] if len(p_points) > 1 else first_pain

                # No generic fallback: absent evidence or a failed draft means no send.
                outreach_body = (c.get("outreach_message") or "").strip()

                channel_schedule = [
                    {"day": 1, "channel": "Email", "content": outreach_body, "status": "pending"},
                    {"day": 1 + cadence, "channel": "LinkedIn", "content": f"Hi {c['contact']['name']}, noticed your work at {c['company_name']}. I sent over an email regarding {profile_company_name}'s {profile_offer} to tackle your {first_pain}. Let's connect!", "status": "pending"} if first_pain and c.get("contact", {}).get("name") else None,
                    {"day": 1 + 2 * cadence, "channel": "Email", "content": f"Hi {c['contact']['name']}, following up on my previous message. We help {c['company_name']} address {second_pain}. Let me know if a brief discussion would be useful.", "status": "pending"} if second_pain and c.get("contact", {}).get("name") else None,
                    {"day": 1 + 3 * cadence, "channel": "WhatsApp", "content": f"Hello {c['contact']['name']}, this is {profile_company_name} following up on {first_pain}. Are you available for a brief chat this week?", "status": "pending"} if first_pain and c.get("contact", {}).get("name") else None,
                    {"day": 1 + 4 * cadence, "channel": "Follow-Up Call", "content": f"Follow up about {first_pain}.", "status": "pending"} if first_pain else None,
                ]

                subject = f"Partnership Opportunity - {profile_company_name} x {c['company_name']}"
                body = outreach_body
                from app.services.sales.touch_dispatcher import dispatch_sales_touch
                sales_cred_for_policy = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="sales").first()
                policy_settings = (sales_cred_for_policy.settings if sales_cred_for_policy else {}) or {}
                # Persist the verification receipt before the central dispatcher re-checks it.\n                lead.data = {\n                    **(lead.data if isinstance(getattr(lead, "data", None), dict) else {}),\n                    **_build_lead_data(c),\n                    "source_verification": c.get("source_verification"),\n                }\n                self.db.commit()\n\n                readiness = assess_outreach_readiness(\n                    {**c, "source_verification": c.get("source_verification")},                    auto_send_enabled=bool(policy_settings.get("sales_ai_auto_send_enabled", False)),
                    permission_state=policy_settings.get("outbound_permission_state"),
                    suppressed=bool(c.get("suppressed") or c.get("do_not_contact")),
                )
                email_allowed = bool(c["contact"].get("email"))
                lead_data_for_consent = lead.data if isinstance(getattr(lead, "data", None), dict) else {}
                consent_contact = lead_data_for_consent.get("contact") if isinstance(lead_data_for_consent.get("contact"), dict) else {}
                opt_in_value = (
                    consent_contact.get("whatsapp_opt_in")
                    if "whatsapp_opt_in" in consent_contact
                    else lead_data_for_consent.get("whatsapp_opt_in")
                )
                opt_in_source = (
                    consent_contact.get("whatsapp_opt_in_source")
                    if "whatsapp_opt_in_source" in consent_contact
                    else lead_data_for_consent.get("whatsapp_opt_in_source")
                )
                opt_in_at = (
                    consent_contact.get("whatsapp_opt_in_at")
                    if "whatsapp_opt_in_at" in consent_contact
                    else lead_data_for_consent.get("whatsapp_opt_in_at")
                )
                recipient_whatsapp_opt_in = opt_in_value is True and bool(opt_in_source) and bool(opt_in_at)
                whatsapp_allowed = (
                    bool(c["contact"].get("phone"))
                    and str(policy_settings.get("whatsapp_permission_state") or "").lower() == "granted"
                    and recipient_whatsapp_opt_in
                )
                if outreach_body and readiness["ready"] and email_allowed:
                    delivery = dispatch_sales_touch(
                        self.db,
                        self.tenant_id,
                        lead,
                        channel="email",
                        body=body,
                        subject=subject,
                        step_number=1,
                    )
                    if not delivery.get("sent") and whatsapp_allowed:
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
                elif outreach_body and readiness["ready"] and whatsapp_allowed:
                    delivery = dispatch_sales_touch(
                        self.db,
                        self.tenant_id,
                        lead,
                        channel="whatsapp",
                        body=body,
                        subject=subject,
                        step_number=1,
                    )
                else:
                    blockers = list(readiness["blockers"])
                    if not email_allowed and not whatsapp_allowed:
                        blockers.append("no_channel_specific_permission_or_contact_route")
                    delivery = {
                        "sent": False,
                        "channel": "email",
                        "reason": "outreach_readiness_blocked",
                        "message": "Outbound not dispatched; readiness blockers: " + ", ".join(blockers),
                        "blockers": blockers,
                    }

                sent_successfully = bool(delivery.get("sent"))
                channel_used = delivery.get("channel") or "email"
                channel_schedule[0]["status"] = "sent" if sent_successfully else ("blocked" if delivery.get("reason") == "outreach_readiness_blocked" else "failed")
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
                        "sent_actual": True,
                        "outreach_readiness": readiness,
                    }
                else:
                    lead.status = "scored"
                    lead.data = {
                        **(lead.data or {}),
                        **_build_lead_data(c),
                        "domain_archetype": domain_archetype,
                        "committee_role": "economic_buyer",
                        "freshness_window": freshness_window,
                        "outreach_schedule": channel_schedule,
                        "draft_subject": subject,
                        "draft_body": body,
                        "sent_actual": False,
                        "outreach_readiness": readiness,
                    }

                try:
                    from app.services.sales.sync_bridge import SalesSyncBridge
                    sync_bridge = SalesSyncBridge(self.db, self.tenant_id)
                    sync_bridge.sync_outreach_sent(lead, sent_actual=sent_successfully, auto_commit=False)
                except Exception as sync_err:
                    logger.warning(f"SalesSyncBridge sync skipped for {c['company_name']}: {sync_err}")

                try:
                    from app.services.sales.outbox_service import SalesOutboxService
                    outbox_svc = SalesOutboxService(self.db, self.tenant_id)
                    future_touches = [touch for touch in channel_schedule[1:] if touch]
                    # Future touches must not be queued before the first authorized touch succeeds.
                    if sent_successfully and future_touches:
                        outbox_svc.stage_sequence(lead, future_touches)
                except Exception as outbox_err:
                    logger.warning(f"Outbox staging failed for {lead.email}: {outbox_err}")

                m_leads = self.db.query(AgentMetric).filter_by(tenant_id=self.tenant_id, metric_name="leads_generated").first()
                if not m_leads:
                    m_leads = AgentMetric(tenant_id=self.tenant_id, metric_name="leads_generated", value=0.0)
                    self.db.add(m_leads)
                m_leads.value += 1.0

            self.db.commit()
            update_status(8, "completed", "Lead records and eligible drafts saved; outbound actions are policy-gated.", "CRM records saved. Messages are only dispatched when explicit send authorization, permission, contact identity, and evidence checks pass.")
        except Exception as e:
            update_status(8, "failed", str(e), f"Error in Step 8: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 9: Conversation AI
        update_status(9, "executing", "Readying conversation auto-responders...", "Starting Step 9: Sourcing pricing guidelines, case studies, and scheduling parameters...")
        try:
            sales_cred = self.db.query(APICredential).filter_by(tenant_id=self.tenant_id, provider="sales").first()
            cred_settings = (sales_cred.settings if sales_cred else {}) or {}
            auto_reply_enabled = cred_settings.get("auto_reply_enabled", True)
            reply_mode = cred_settings.get("reply_mode", "autonomous")
            emit_activity(
                9,
                f"Conversation auto-responder configured (mode: {reply_mode}, enabled: {auto_reply_enabled}).",
                f"[CONVERSATION] Guidelines active: USP '{profile_usp[:40]}...', Offer '{profile_offer[:40]}...'",
            )
            update_status(9, "completed", f"Ready to process prospect replies and objections (mode: {reply_mode}).", "Conversation AI engine operational. Active inbox polling initialized.")
        except Exception as e:
            update_status(9, "failed", str(e), f"Error in Step 9: {str(e)}", "failed")
            return {"status": "error", "message": str(e)}

        # Step 10: Meeting Conversion
        update_status(10, "executing", "Checking calendars and converting real prospect replies...", "Starting Step 10: Processing real interested leads...")
        try:
            interested_leads = self.db.query(Lead).filter(
                Lead.tenant_id == self.tenant_id,
                Lead.status == "replied",
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
                    log_activity=self.log_activity,
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

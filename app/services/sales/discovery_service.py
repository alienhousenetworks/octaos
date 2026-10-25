"""Discovery Service for Sales OS: Lead generation, parallel search, and external provider sourcing."""
import asyncio
import json
import logging
import os
import random
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from app.core.http_utils import with_retry
from app.core.security import decrypt_api_key
from app.models.base import APICredential
from app.models.verticals import Lead
from app.services.sales.utils import extract_json

logger = logging.getLogger(__name__)


class DiscoveryService:
    def __init__(self, db: Session, tenant_id: str, llm=None, log_activity: Optional[Callable] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.llm = llm
        self._log_activity = log_activity or (lambda *args, **kwargs: None)

    async def generate_leads(self, params: dict) -> dict:
        """Source leads from external providers or web discovery and persist them to DB."""
        provider = params.get("provider", "web_search")
        if provider == "free_search":
            provider = "web_search"
        query = params.get("query", "target clients")
        count = params.get("count", 5)

        self._log_activity("Lead Sourcing", f"Sourcing {count} leads using {provider} for query: '{query}'")

        leads_data = []

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
            leads_data = await self.fetch_real_leads(
                provider,
                decrypt_api_key(cred.encrypted_key) if cred else "",
                query,
                count,
                **fetch_extra,
            )
            if provider == "web_search" and not leads_data:
                message = "Open-web discovery found no verifiable contacts after multiple search rounds."
                self._log_activity("API Error", message, "failed")
                return {"status": "error", "message": message}
        except Exception as e:
            self._log_activity("API Error", f"Failed fetching from {provider}: {str(e)}.", "failed")
            return {"status": "error", "message": str(e)}

        # Write leads to DB
        created_count = 0
        new_lead_ids = []
        for data in leads_data:
            email_value = data.get("email") or data.get("personal_email") or data.get("company_email")
            phone_value = data.get("phone") or data.get("mobile_no") or data.get("company_contact_no")
            company_value = data.get("company") or data.get("company_name")
            display_name = data.get("name") or data.get("contact_name") or company_value
            # Account discovery is valuable even when no verified person/contact is available.
            # Preserve the account as research work instead of silently dropping it.
            if not company_value or not display_name:
                continue
            lead_query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)
            if email_value:
                lead_query = lead_query.filter(Lead.email == email_value)
            elif phone_value:
                lead_query = lead_query.filter(Lead.phone == phone_value)
            else:
                lead_query = lead_query.filter(
                    Lead.company == company_value,
                    Lead.email.is_(None),
                    Lead.phone.is_(None),
                )
            exists = lead_query.first()
            if not exists:
                source_url = data.get("evidence_url") or data.get("source_url") or data.get("url")
                evidence_quote = data.get("evidence_quote") or data.get("snippet") or data.get("description")
                from app.models.rooms import SectionRoom
                sales_room = self.db.query(SectionRoom).filter(
                    SectionRoom.tenant_id == self.tenant_id,
                    SectionRoom.section == "sales",
                    SectionRoom.slug == "default"
                ).first()
                lead = Lead(
                    tenant_id=self.tenant_id,
                    room_id=sales_room.id if sales_room else None,
                    name=display_name,
                    email=email_value,
                    phone=phone_value,
                    company=company_value,
                    source=f"{provider.upper()}: {query}",
                    status="captured" if (email_value or phone_value) else "needs_contact_research",
                    score=None,
                    personal_email=data.get("personal_email"),
                    company_email=data.get("company_email") or email_value,
                    mobile_no=data.get("mobile_no") or phone_value,
                    company_contact_no=data.get("company_contact_no"),
                    need_of_what=data.get("need_of_what"),
                    how_much=data.get("how_much"),
                    why=data.get("why"),
                    target_context=data.get("target_context"),
                    priority=data.get("priority", "medium"),
                    assigned_to="Sales AI Agent",
                    data={
                        "discovery": {
                            "provider": provider,
                            "query": query,
                            "evidence_url": source_url,
                            "evidence_quote": evidence_quote,
                            "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        },
                        "contact_verification": {
                            "status": "unknown",
                            "reason": "Discovery output is not equivalent to independent contact verification.",
                        },
                    },
                )
                self.db.add(lead)
                self.db.flush()
                new_lead_ids.append(lead.id)
                created_count += 1

        self.db.commit()

        from app.worker.tasks import enrich_lead_task

        for lead_id in new_lead_ids:
            enrich_lead_task.delay(self.tenant_id, lead_id)

        self._log_activity("Lead Generation Complete", f"Successfully captured {created_count} new leads in the DB.", "success")
        return {"status": "success", "generated_leads": created_count, "provider": provider}

    async def collect_parallel_search(
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

    def record_parallel_search_spend(self, batch) -> None:
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
    async def fetch_real_leads(
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
        """Fetch verifiable leads from the chosen provider."""
        leads = []
        async with httpx.AsyncClient() as client:
            if provider == "web_search":
                from app.services.sales_os.discovery.web_discovery import discover_leads_from_web
                try:
                    leads = await discover_leads_from_web(
                        self.llm.complete if self.llm else None,
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
                headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": api_key}
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
                    parsed_query = extract_json(await self.llm.complete(prompt)) if self.llm else {"q_keywords": query}
                except Exception:
                    parsed_query = {"q_keywords": query}

                payload = {
                    "api_key": api_key,
                    "page": random.randint(1, 5),
                    "per_page": count,
                    **parsed_query,
                }
                response = await client.post("https://api.apollo.io/api/v1/mixed_people/api_search", headers=headers, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    people = data.get("people", [])
                    if not people:
                        safe_payload = {k: v for k, v in payload.items() if k != "api_key"}
                        raise Exception(f"Apollo returned 0 people for payload: {safe_payload}. Full response: {response.text}")
                    for p in people[:count]:
                        org = p.get("organization", {})
                        first = p.get("first_name", "")
                        last = p.get("last_name", "")
                        if not first or not last or "***" in last:
                            continue
                        full_name = f"{first} {last}".strip()
                        website = org.get("primary_domain", "") or org.get("website_url", "")
                        leads.append({
                            "name": full_name or "Unknown Contact",
                            "email": p.get("email", ""),
                            "company": org.get("name", "Target Corp"),
                            "website": website,
                            "phone": p.get("primary_phone", ""),
                        })
                else:
                    raise Exception(f"Apollo API Error: {response.status_code} - {response.text}")
            elif provider == "hunter":
                domains = []
                if "." in query and " " not in query:
                    domains.append(query)
                else:
                    industries_path = os.path.join(os.path.dirname(__file__), "../agents/hunter_industries.json")
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
                        parsed_query = extract_json(await self.llm.complete(prompt)) if self.llm else {"query": query}
                    except Exception:
                        parsed_query = {"query": query}

                    discover_url = f"https://api.hunter.io/v2/discover?api_key={api_key}"
                    discover_response = await client.post(discover_url, json=parsed_query, timeout=12.0)
                    if discover_response.status_code == 200:
                        discover_data = discover_response.json()
                        companies = discover_data.get("data", [])
                        if not companies:
                            raise Exception(f"Hunter Discover returned 0 companies for payload {parsed_query}. Full response: {discover_response.text}")
                        domains = [c.get("domain") for c in companies if c.get("domain")]
                    else:
                        raise Exception(f"Hunter Discover API Error: {discover_response.status_code} - {discover_response.text}")

                if not domains:
                    raise Exception(f"Hunter could not find any valid domains for query: {query}")

                random.shuffle(domains)
                for domain in domains:
                    if len(leads) >= count:
                        break
                    domain_response = await client.get(
                        f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}&type=personal&limit=2",
                        timeout=12.0,
                    )
                    if domain_response.status_code == 200:
                        domain_data = domain_response.json()
                        emails = domain_data.get("data", {}).get("emails", [])
                        org_name = domain_data.get("data", {}).get("organization") or domain.split(".")[0].capitalize()
                        for email in emails:
                            leads.append({
                                "name": f"{email.get('first_name', '')} {email.get('last_name', '')}".strip() or "Business Contact",
                                "email": email.get("value"),
                                "company": org_name,
                                "phone": email.get("phone_number", ""),
                            })
                            break
                    elif domain_response.status_code == 429:
                        await asyncio.sleep(2)
                        continue

                if not leads:
                    raise Exception(f"Hunter Domain Search returned 0 people across {len(domains)} domains.")
            elif provider == "apify":
                from apify_client import ApifyClientAsync
                apify_client = ApifyClientAsync(api_key)

                if "." in query and " " not in query:
                    run_payload = {
                        "startUrls": [{"url": f"https://{query}" if not query.startswith("http") else query}],
                        "maxCrawlPages": 3,
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
                        parsed_config = extract_json(await self.llm.complete(prompt)) if self.llm else {}
                        actor_id = parsed_config.get("actor_id", "compass/crawler-google-places")
                        run_payload = parsed_config.get("run_payload", {
                            "searchStringsArray": [query],
                            "maxCrawledPlacesPerSearch": count,
                            "language": "en",
                        })
                    except Exception:
                        actor_id = "compass/crawler-google-places"
                        run_payload = {
                            "searchStringsArray": [query],
                            "maxCrawledPlacesPerSearch": count,
                            "language": "en",
                        }

                try:
                    actor_run = await apify_client.actor(actor_id).call(run_input=run_payload)
                    dataset_items = (await apify_client.dataset(actor_run["defaultDatasetId"]).list_items()).items
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
                                "phone": p.get("phone", "") or p.get("phoneUnformatted", ""),
                            })
                        elif "instagram" in actor_id:
                            leads.append({
                                "name": p.get("fullName", p.get("username", "Influencer")),
                                "email": p.get("publicEmail", ""),
                                "company": p.get("username", ""),
                                "phone": p.get("publicPhoneNumber", ""),
                            })
                        elif "linkedin" in actor_id:
                            leads.append({
                                "name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip() or "Professional",
                                "email": p.get("email", ""),
                                "company": p.get("companyName", p.get("headline", "")),
                                "phone": p.get("phone", ""),
                            })
                        else:
                            text = p.get("text", "")
                            emails_found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
                            email = emails_found[0] if emails_found else ""
                            leads.append({
                                "name": p.get("name", "Contact"),
                                "email": email,
                                "company": p.get("company", ""),
                                "phone": "",
                            })
                            if email:
                                break
                except Exception as e:
                    raise Exception(f"Apify API Error: {str(e)}")
            elif provider == "google_places":
                url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={api_key}"
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if not results:
                        raise Exception(f"Google Places returned 0 results. Full response: {response.text}")
                    for res in results[:count]:
                        leads.append({
                            "name": "",
                            "email": "",
                            "company": res.get("name", "Local Business"),
                            "phone": "",
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
                            "phone": c.get("phone", ""),
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
                            "phone": c.get("directDial", ""),
                        })
            elif provider == "people_data_labs":
                headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
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
                            "company": p.get("job_company_name", p.get("company", "")),
                            "phone": phones[0] if phones else "",
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
                            "phone": "",
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
                            "phone": props.get("phone_number", ""),
                        })
            else:
                from app.services.sales_os.discovery.connectors import fetch_leads_from_source
                leads = await fetch_leads_from_source(provider, api_key, query, count=count, llm_gateway=self.llm, freshness=freshness_window or freshness)

        if not leads:
            raise Exception(f"The {provider} API returned data, but no valid leads were extracted. This often happens if the API rate-limits you, requires credits, or returns obfuscated/paywalled names (e.g., Apollo's '***' names).")
        return leads

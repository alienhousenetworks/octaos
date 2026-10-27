"""General web search. Brave or Tavily when configured, otherwise DuckDuckGo."""
import httpx
from datetime import datetime, timedelta, timezone

from app.services.sales_os.search_v4.connectors.base import ConnectorResult, Hit, failure_from_status
from app.services.sales_os.search_v4.connectors.extract import contact_from_text, page_text, title_of
from app.services.sales_os.search_v4.contracts import SearchTask
from app.services.sales_os.search_v4.urls import host_of, is_company_site
from app.services.sales_os.search_v4.connectors.safe_fetch import safe_get

_HEADERS = {"User-Agent": "OctaOS-Sales/1.0 (search-v4)", "Accept": "application/json"}


class WebSearchConnector:
    def __init__(self, credentials: dict[str, str]):
        self.credentials = credentials

    async def execute(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        try:
            if task.provider == "brave":
                return await self._brave(task, client)
            if task.provider == "tavily":
                return await self._tavily(task, client)
            return await self._duckduckgo(task, client)
        except httpx.TimeoutException:
            return ConnectorResult(status="failed", failure_class="transient", reason="The web search timed out.")
        except httpx.HTTPError as exc:
            return ConnectorResult(status="failed", failure_class="transient", reason=f"The web search request failed: {exc.__class__.__name__}.")

    async def _brave(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": task.query, "count": 5},
            headers={**_HEADERS, "X-Subscription-Token": self.credentials.get("brave_search", "")},
        )
        if response.status_code != 200:
            failure, reason = failure_from_status(response.status_code)
            return ConnectorResult(status="failed", failure_class=failure, reason=reason)
        rows = ((response.json() or {}).get("web") or {}).get("results") or []
        hits = [
            Hit(
                url=row.get("url") or "",
                title=row.get("title") or "",
                snippet=row.get("description") or "",
                provider_native_id=row.get("url"),
            )
            for row in rows
            if row.get("url")
        ]
        hits = await self._enrich(client, hits)
        return self._done(hits, task.estimated_cost_inr, billable=True)

    async def _tavily(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        response = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": self.credentials.get("tavily", ""), "query": task.query, "max_results": 5},
            headers=_HEADERS,
        )
        if response.status_code != 200:
            failure, reason = failure_from_status(response.status_code)
            return ConnectorResult(status="failed", failure_class=failure, reason=reason)
        rows = (response.json() or {}).get("results") or []
        hits = [
            Hit(url=row.get("url") or "", title=row.get("title") or "", snippet=row.get("content") or "", provider_native_id=row.get("url"))
            for row in rows
            if row.get("url")
        ]
        hits = await self._enrich(client, hits)
        return self._done(hits, task.estimated_cost_inr, billable=True)

    async def _duckduckgo(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        from app.services.sales_os.discovery.web_discovery import _search

        from app.services.sales_os.discovery.web_discovery import calculate_freshness_window_days

        max_days = calculate_freshness_window_days(task.freshness_window)
        df_param = "w" if max_days <= 14 else ("m" if max_days <= 30 else None)
        query = task.query
        if max_days < 9999:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
            query = f"{query} after:{cutoff.date().isoformat()}"
        urls = await _search(client, query, 5, df_param=df_param)
        hits = [Hit(url=url, provider_native_id=url) for url in urls]
        hits = await self._enrich(client, hits)
        return self._done(hits, 0.0, billable=False)

    async def _enrich(self, client: httpx.AsyncClient, hits: list[Hit]) -> list[Hit]:
        enriched: list[Hit] = []
        for hit in hits[:4]:
            if not is_company_site(hit.url):
                enriched.append(hit)
                continue
            try:
                response = await safe_get(
                    client,
                    hit.url,
                    headers={"User-Agent": _HEADERS["User-Agent"], "Accept": "text/html"},
                )
            except Exception:
                enriched.append(hit)
                continue
            if response.status_code != 200:
                enriched.append(hit)
                continue
            raw = response.text or ""
            text = page_text(raw)[:4000]
            name, email = contact_from_text(text, hit.url)
            # A company homepage often links the actual inbox from a contact
            # page. Fetch only a small, bounded set of conventional paths; do
            # not crawl arbitrary links. Each request and redirect is revalidated.
            if not email:
                from urllib.parse import urljoin

                for path in ("/contact", "/contact-us", "/about", "/about-us", "/team"):
                    try:
                        contact_response = await safe_get(
                            client,
                            urljoin(hit.url, path),
                            headers={"User-Agent": _HEADERS["User-Agent"], "Accept": "text/html"},
                        )
                    except Exception:
                        continue
                    if contact_response.status_code != 200:
                        continue
                    contact_raw = contact_response.text or ""
                    contact_text = page_text(contact_raw)[:4000]
                    contact_name, contact_email = contact_from_text(contact_text, hit.url)
                    if contact_email:
                        name = contact_name or name
                        email = contact_email
                        text = f"{text}\n{contact_text}"[:4000]
                        break
            hit.title = hit.title or title_of(raw)
            hit.page_excerpt = text[:700]
            hit.snippet = hit.snippet or text[:320]
            hit.contact_name = name
            hit.contact_email = email
            hit.company_domain = host_of(hit.url)
            if not hit.company_name:
                hit.company_name = (hit.title.split("|")[0].split("-")[0].strip()[:120] or hit.company_domain or "")
            enriched.append(hit)
        return enriched

    def _done(self, hits: list[Hit], cost: float, billable: bool) -> ConnectorResult:
        usable = [hit for hit in hits if hit.url]
        if not usable:
            return ConnectorResult(status="empty", reason="The web search completed and returned no usable URLs.", actual_cost_inr=cost, billable=billable)
        return ConnectorResult(status="ok", hits=usable, actual_cost_inr=cost, billable=billable)

"""Fetch one known company URL. The query must already be that URL."""
import httpx

from app.services.sales_os.search_v4.connectors.base import ConnectorResult, Hit
from app.services.sales_os.search_v4.connectors.extract import contact_from_text, page_text, title_of
from app.services.sales_os.search_v4.contracts import SearchTask
from app.services.sales_os.search_v4.urls import host_of, is_company_site
from app.services.sales_os.search_v4.connectors.safe_fetch import safe_get

_HEADERS = {"User-Agent": "OctaOS-Sales/1.0 (search-v4)", "Accept": "text/html"}


class CompanyPageConnector:
    async def execute(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        if not task.query.startswith("http"):
            return ConnectorResult(status="failed", failure_class="invalid", reason="A company fetch requires an http URL.")
        if not is_company_site(task.query):
            return ConnectorResult(status="empty", reason="The URL is a board or social host, so it was not fetched as a company page.")
        try:
            response = await safe_get(client, task.query, headers=_HEADERS)
        except httpx.TimeoutException:
            return ConnectorResult(status="failed", failure_class="transient", reason="The company page timed out.")
        except ValueError as exc:
            return ConnectorResult(status="failed", failure_class="invalid", reason=str(exc)[:240])
        except httpx.HTTPError as exc:
            return ConnectorResult(status="failed", failure_class="transient", reason=f"The company page request failed: {exc.__class__.__name__}.")
        if response.status_code != 200:
            return ConnectorResult(status="failed", failure_class="provider", reason=f"The company page returned HTTP {response.status_code}.")
        raw = response.text or ""
        text = page_text(raw)[:4000]
        if not text:
            return ConnectorResult(status="empty", reason="The company page completed and contained no readable text.")
        name, email = contact_from_text(text, task.query)
        title = title_of(raw) or host_of(task.query)
        hit = Hit(
            url=task.query,
            title=title,
            snippet=text[:320],
            page_excerpt=text[:700],
            company_name=title.split("|")[0].strip()[:120],
            company_domain=host_of(task.query),
            contact_name=name,
            contact_email=email,
            provider_native_id=task.query,
        )
        return ConnectorResult(status="ok", hits=[hit], billable=False)

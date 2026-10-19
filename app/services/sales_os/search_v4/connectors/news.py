"""Public news headlines. A headline is a signal, not a contact."""
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from app.services.sales_os.search_v4.connectors.base import ConnectorResult, Hit, failure_from_status
from app.services.sales_os.search_v4.contracts import SearchTask

_HEADERS = {"User-Agent": "OctaOS-Sales/1.0 (search-v4)", "Accept": "application/rss+xml"}


def _items(xml_text: str) -> list[tuple[str, str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    rows = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title:
            rows.append((title, link))
    return rows


class NewsConnector:
    async def execute(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        url = f"https://news.google.com/rss/search?q={quote_plus(task.query)}&hl=en-US&gl=US&ceid=US:en"
        try:
            response = await client.get(url, headers=_HEADERS)
        except httpx.TimeoutException:
            return ConnectorResult(status="failed", failure_class="transient", reason="The news search timed out.")
        except httpx.HTTPError as exc:
            return ConnectorResult(status="failed", failure_class="transient", reason=f"The news search failed: {exc.__class__.__name__}.")
        if response.status_code != 200:
            failure, reason = failure_from_status(response.status_code)
            return ConnectorResult(status="failed", failure_class=failure, reason=reason)
        hits = []
        for title, link in _items(response.text or "")[:5]:
            company = title.split(" - ")[0].strip()[:160]
            hits.append(Hit(url=link or url, title=title, snippet=title, company_name=company, provider_native_id=link or title))
        if not hits:
            return ConnectorResult(status="empty", reason="The news feed completed and returned no items.", billable=False)
        return ConnectorResult(status="ok", hits=hits, billable=False)

"""Public hiring signals from Hacker News search. No person or inbox is invented."""
import httpx
from datetime import datetime, timezone

from app.services.sales_os.search_v4.connectors.base import ConnectorResult, Hit, failure_from_status
from app.services.sales_os.search_v4.contracts import SearchTask

_HEADERS = {"User-Agent": "OctaOS-Sales/1.0 (search-v4)", "Accept": "application/json"}


class JobsConnector:
    async def execute(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        try:
            response = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": task.query, "tags": "story", "hitsPerPage": 5},
                headers=_HEADERS,
            )
        except httpx.TimeoutException:
            return ConnectorResult(status="failed", failure_class="transient", reason="The hiring search timed out.")
        except httpx.HTTPError as exc:
            return ConnectorResult(status="failed", failure_class="transient", reason=f"The hiring search failed: {exc.__class__.__name__}.")
        if response.status_code != 200:
            failure, reason = failure_from_status(response.status_code)
            return ConnectorResult(status="failed", failure_class=failure, reason=reason)
        hits = []
        for row in (response.json() or {}).get("hits") or []:
            title = (row.get("title") or "").strip()
            url = row.get("url") or f"https://news.ycombinator.com/item?id={row.get('objectID')}"
            if not title:
                continue
            published_at = None
            if row.get("created_at"):
                try:
                    published_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
                except (TypeError, ValueError):
                    published_at = None
            hits.append(
                Hit(
                    url=url,
                    title=title,
                    snippet=title,
                    published_at=published_at,
                    provider_native_id=str(row.get("objectID") or ""),
                    company_name=title.split(" is hiring")[0].split(" (")[0][:120],
                )
            )
        if not hits:
            return ConnectorResult(status="empty", reason="The hiring search completed and returned no stories.", billable=False)
        return ConnectorResult(status="ok", hits=hits, billable=False)

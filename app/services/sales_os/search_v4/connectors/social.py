"""Permitted social search. Missing credentials are UNAVAILABLE, not an empty web result."""
import httpx

from app.services.sales_os.search_v4.connectors.base import ConnectorResult, Hit, failure_from_status
from app.services.sales_os.search_v4.contracts import SearchTask

_HEADERS = {"User-Agent": "OctaOS-Sales/1.0 (search-v4)"}


def _split_pair(secret: str) -> tuple[str, str] | None:
    for separator in (":", "|"):
        if separator in secret:
            left, right = secret.split(separator, 1)
            if left.strip() and right.strip():
                return left.strip(), right.strip()
    return None


class RedditConnector:
    def __init__(self, credentials: dict[str, str]):
        self.credentials = credentials

    async def execute(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        pair = _split_pair(self.credentials.get("reddit") or "")
        if pair is None:
            return ConnectorResult(
                status="unavailable",
                reason="Reddit official search is not configured. No Reddit posts were searched.",
            )
        client_id, client_secret = pair
        try:
            token_response = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers=_HEADERS,
            )
        except httpx.HTTPError as exc:
            return ConnectorResult(status="failed", failure_class="transient", reason=f"Reddit token request failed: {exc.__class__.__name__}.")
        if token_response.status_code != 200:
            failure, reason = failure_from_status(token_response.status_code)
            return ConnectorResult(status="failed", failure_class=failure, reason=reason)
        token = (token_response.json() or {}).get("access_token")
        if not token:
            return ConnectorResult(status="failed", failure_class="permission", reason="Reddit did not return an access token.")
        try:
            response = await client.get(
                "https://oauth.reddit.com/search",
                params={"q": task.query, "limit": 5, "sort": "new", "type": "link"},
                headers={**_HEADERS, "Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            return ConnectorResult(status="failed", failure_class="transient", reason=f"Reddit search failed: {exc.__class__.__name__}.")
        if response.status_code != 200:
            failure, reason = failure_from_status(response.status_code)
            return ConnectorResult(status="failed", failure_class=failure, reason=reason)
        children = ((response.json() or {}).get("data") or {}).get("children") or []
        hits = []
        for child in children:
            data = child.get("data") or {}
            title = (data.get("title") or "").strip()
            permalink = data.get("permalink") or ""
            if not title:
                continue
            url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink
            hits.append(
                Hit(
                    url=url or "https://www.reddit.com",
                    title=title,
                    snippet=(data.get("selftext") or title)[:500],
                    provider_native_id=str(data.get("id") or ""),
                )
            )
        if not hits:
            return ConnectorResult(status="empty", reason="Reddit search completed and returned no posts.")
        return ConnectorResult(status="ok", hits=hits)


class XConnector:
    def __init__(self, credentials: dict[str, str]):
        self.credentials = credentials

    async def execute(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        token = self.credentials.get("x_search") or ""
        if not token:
            return ConnectorResult(
                status="unavailable",
                reason="X official search is not configured. No X posts were searched.",
            )
        try:
            response = await client.get(
                "https://api.x.com/2/tweets/search/recent",
                params={"query": task.query, "max_results": 10, "tweet.fields": "created_at,text"},
                headers={**_HEADERS, "Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            return ConnectorResult(status="failed", failure_class="transient", reason=f"X search failed: {exc.__class__.__name__}.")
        if response.status_code != 200:
            failure, reason = failure_from_status(response.status_code)
            return ConnectorResult(status="failed", failure_class=failure, reason=reason)
        hits = []
        for row in (response.json() or {}).get("data") or []:
            text = (row.get("text") or "").strip()
            post_id = str(row.get("id") or "")
            if not text or not post_id:
                continue
            hits.append(
                Hit(
                    url=f"https://x.com/i/web/status/{post_id}",
                    title=text[:140],
                    snippet=text[:500],
                    provider_native_id=post_id,
                )
            )
        if not hits:
            return ConnectorResult(status="empty", reason="X search completed and returned no posts.")
        return ConnectorResult(status="ok", hits=hits)

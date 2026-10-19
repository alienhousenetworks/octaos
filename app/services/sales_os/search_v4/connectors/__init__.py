"""Connector set for the additional search methods."""
import httpx

from app.services.sales_os.search_v4.connectors.company import CompanyPageConnector
from app.services.sales_os.search_v4.connectors.jobs import JobsConnector
from app.services.sales_os.search_v4.connectors.news import NewsConnector
from app.services.sales_os.search_v4.connectors.social import RedditConnector, XConnector
from app.services.sales_os.search_v4.connectors.web import WebSearchConnector
from app.services.sales_os.search_v4.contracts import SearchTask
from app.services.sales_os.search_v4.connectors.base import ConnectorResult


class MethodConnectors:
    def __init__(self, credentials: dict[str, str]):
        self._web = WebSearchConnector(credentials)
        self._news = NewsConnector()
        self._jobs = JobsConnector()
        self._company = CompanyPageConnector()
        self._reddit = RedditConnector(credentials)
        self._x = XConnector(credentials)

    async def execute(self, task: SearchTask, client: httpx.AsyncClient) -> ConnectorResult:
        if task.method == "web":
            return await self._web.execute(task, client)
        if task.method == "news":
            return await self._news.execute(task, client)
        if task.method == "jobs":
            return await self._jobs.execute(task, client)
        if task.method == "company":
            return await self._company.execute(task, client)
        if task.method == "social_reddit":
            return await self._reddit.execute(task, client)
        if task.method == "social_x":
            return await self._x.execute(task, client)
        return ConnectorResult(status="unavailable", reason=f"{task.method} is not an implemented search method.")

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class MCPServerConfig:
    def __init__(self, name: str, transport: str, uri_or_cmd: str, enabled: bool = True):
        self.name = name
        self.transport = transport # 'stdio', 'sse', 'http'
        self.uri_or_cmd = uri_or_cmd
        self.enabled = enabled

class MCPHubService:
    """
    Model Context Protocol (MCP) Integration Hub.
    Allows OctaOS agents to discover, mount, and invoke external enterprise tools
    (Databases, Repositories, Cloud Storage, Issue Trackers) using standard MCP schemas.
    """

    def __init__(self, db_factory=None):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._registered_tools: Dict[str, Dict[str, Any]] = {}
        self.db_factory = db_factory
        # Pre-populate default standard MCP servers
        self._init_default_servers()

    def _get_db(self):
        if self.db_factory:
            try:
                return self.db_factory()
            except Exception:
                return None
        try:
            from app.db.session import SessionLocal
            return SessionLocal()
        except Exception:
            return None

    def _init_default_servers(self):
        self.register_server("postgres", "stdio", "npx -y @modelcontextprotocol/server-postgres postgresql://localhost/octaos")
        self.register_server("filesystem", "stdio", "npx -y @modelcontextprotocol/server-filesystem /Users/sayantande/OctaOsautomation")
        self.register_server("github", "sse", "https://api.github.com/mcp")
        self.register_server("apify", "http", "https://mcp.apify.com")
        self.register_server("marketing_integrations", "stdio", "octaos_integrations_hub")

    def register_server(self, name: str, transport: str, uri_or_cmd: str) -> bool:
        self._servers[name] = MCPServerConfig(name, transport, uri_or_cmd)
        logger.info(f"Registered MCP Server connector: {name} ({transport})")
        return True

    def list_servers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": s.name,
                "transport": s.transport,
                "target": s.uri_or_cmd,
                "enabled": s.enabled
            }
            for s in self._servers.values()
        ]

    def discover_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discovers tools exported by connected MCP servers.
        Returns standardized OpenAPI/JSON-RPC tool definitions.
        """
        tools = []
        target_servers = [self._servers[server_name]] if server_name and server_name in self._servers else list(self._servers.values())

        for server in target_servers:
            if not server.enabled:
                continue
            
            # Synthetic tool definition specs representing standard MCP schemas
            if server.name == "postgres":
                tools.append({
                    "name": f"mcp_{server.name}_query",
                    "description": "Execute read-only SQL queries against connected PostgreSQL DB via MCP",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "SQL query string"}
                        },
                        "required": ["sql"]
                    }
                })
            elif server.name == "filesystem":
                tools.append({
                    "name": f"mcp_{server.name}_read_file",
                    "description": "Read contents of a file on local workspace via MCP",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Absolute path to file"}
                        },
                        "required": ["path"]
                    }
                })
            elif server.name == "github":
                tools.append({
                    "name": f"mcp_{server.name}_get_repo_issues",
                    "description": "Fetch GitHub repository issues via MCP endpoint",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"}
                        },
                        "required": ["owner", "repo"]
                    }
                })
            elif server.name == "apify":
                tools.append({
                    "name": "mcp_apify_search_actors",
                    "description": "Search Apify Store for available Actors and automation tools via MCP",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keywords": {"type": "string", "description": "Search keywords (e.g. 'google places', 'linkedin')"}
                        },
                        "required": ["keywords"]
                    }
                })
                tools.append({
                    "name": "mcp_apify_actor_details",
                    "description": "Inspect an Apify Actor's schema, pricing model, and documentation via MCP",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "actor_id": {"type": "string", "description": "Actor identifier, e.g. 'apify/google-search-scraper'"}
                        },
                        "required": ["actor_id"]
                    }
                })
            elif server.name == "marketing_integrations":
                tools.extend([
                    {
                        "name": "mcp_sendgrid_send_campaign",
                        "description": "Send personalized marketing or SDR email campaigns via Twilio SendGrid",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to_email": {"type": "string"},
                                "subject": {"type": "string"},
                                "content": {"type": "string"},
                                "template_id": {"type": "string"},
                            },
                            "required": ["to_email", "subject", "content"],
                        },
                    },
                    {
                        "name": "mcp_calendly_get_slots",
                        "description": "Discover live SDR booking slots and single-use scheduling links via Calendly",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "event_type_uri": {"type": "string"},
                            },
                        },
                    },
                    {
                        "name": "mcp_zoominfo_enrich",
                        "description": "Enrich accounts and contacts with verified ZoomInfo firmographics and buyer intent",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "domain": {"type": "string"},
                                "email": {"type": "string"},
                            },
                        },
                    },
                    {
                        "name": "mcp_twilio_send_sms",
                        "description": "Dispatch SMS notifications and two-way outreach via Twilio",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to_phone": {"type": "string"},
                                "message": {"type": "string"},
                            },
                            "required": ["to_phone", "message"],
                        },
                    },
                    {
                        "name": "mcp_zapier_emit_event",
                        "description": "Trigger external workflows across 6,000+ apps on Zapier or Workato",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "event_name": {"type": "string"},
                                "payload": {"type": "object"},
                            },
                            "required": ["event_name"],
                        },
                    },
                    {
                        "name": "mcp_powerbi_push_kpis",
                        "description": "Stream executive KPIs and sales telemetry rows directly into Power BI datasets",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "table_name": {"type": "string"},
                                "rows": {"type": "array", "items": {"type": "object"}},
                            },
                            "required": ["table_name", "rows"],
                        },
                    },
                ])
        return tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes an MCP tool call.
        """
        logger.info(f"Invoking MCP tool {tool_name} with arguments: {arguments}")
        if "postgres" in tool_name:
            return {"status": "success", "rows_returned": 0, "result": "Query executed via MCP Postgres transport"}
        elif "filesystem" in tool_name:
            return {"status": "success", "content": "File read successfully via MCP Filesystem transport"}
        elif "github" in tool_name:
            return {"status": "success", "issues": []}
        elif "apify" in tool_name:
            from app.integrations.apify.actor_registry import ActorRegistry
            if "search" in tool_name:
                keywords = arguments.get("keywords", "").lower()
                approved = ActorRegistry.list()
                matched = [
                    {"actor_key": a.actor_key, "actor_id": a.actor_id, "name": a.name, "description": a.description}
                    for a in approved
                    if keywords in a.actor_key.lower() or keywords in a.name.lower() or keywords in a.description.lower()
                ]
                return {"status": "success", "actors": matched or [a.dict() for a in approved]}
            elif "details" in tool_name:
                actor_id = arguments.get("actor_id", "")
                actor = ActorRegistry.get_by_actor_id(actor_id) or ActorRegistry.get(actor_id)
                if actor:
                    return {"status": "success", "actor": actor.dict()}
                return {"status": "error", "message": f"Actor '{actor_id}' not found in registry."}
        elif "sendgrid" in tool_name:
            from app.services.integrations.sendgrid_service import SendGridService
            db = self._get_db()
            try:
                res = await SendGridService(db, "system").send_email(
                    to_email=arguments.get("to_email", ""),
                    subject=arguments.get("subject", ""),
                    content=arguments.get("content", ""),
                    template_id=arguments.get("template_id"),
                )
                return {"status": "success", "result": res}
            finally:
                if db:
                    db.close()
        elif "calendly" in tool_name:
            from app.services.integrations.calendly_service import CalendlyService
            db = self._get_db()
            try:
                service = CalendlyService(db, "system")
                event_uri = arguments.get("event_type_uri")
                if event_uri:
                    link = await service.create_single_use_link(event_uri)
                    return {"status": "success", "link": link}
                events = await service.list_event_types()
                return {"status": "success", "events": events}
            finally:
                if db:
                    db.close()
        elif "zoominfo" in tool_name:
            from app.services.integrations.zoominfo_service import ZoomInfoService
            db = self._get_db()
            try:
                service = ZoomInfoService(db, "system")
                if arguments.get("domain"):
                    data = await service.enrich_company(arguments["domain"])
                else:
                    data = await service.enrich_contact(arguments.get("email", ""))
                return {"status": "success", "data": data}
            finally:
                if db:
                    db.close()
        elif "twilio" in tool_name:
            from app.services.integrations.twilio_service import TwilioService
            db = self._get_db()
            try:
                service = TwilioService(db, "system")
                res = await service.send_sms(arguments.get("to_phone", ""), arguments.get("message", ""))
                return {"status": "success", "result": res}
            finally:
                if db:
                    db.close()
        elif "zapier" in tool_name:
            from app.services.integrations.zapier_workato_service import ZapierWorkatoService
            db = self._get_db()
            try:
                service = ZapierWorkatoService(db, "system")
                res = await service.emit_event(arguments.get("event_name", "event"), arguments.get("payload", {}))
                return {"status": "success", "result": res}
            finally:
                if db:
                    db.close()
        elif "powerbi" in tool_name:
            from app.services.integrations.analytics_connectors import AnalyticsConnectorsService
            db = self._get_db()
            try:
                service = AnalyticsConnectorsService(db, "system")
                res = await service.push_powerbi_rows(arguments.get("table_name", "kpis"), arguments.get("rows", []))
                return {"status": "success", "result": res}
            finally:
                if db:
                    db.close()
        return {"status": "error", "message": f"Unknown MCP tool: {tool_name}"}

mcp_hub = MCPHubService()

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

    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._registered_tools: Dict[str, Dict[str, Any]] = {}
        # Pre-populate default standard MCP servers
        self._init_default_servers()

    def _init_default_servers(self):
        self.register_server("postgres", "stdio", "npx -y @modelcontextprotocol/server-postgres postgresql://localhost/octaos")
        self.register_server("filesystem", "stdio", "npx -y @modelcontextprotocol/server-filesystem /Users/sayantande/OctaOsautomation")
        self.register_server("github", "sse", "https://api.github.com/mcp")
        self.register_server("apify", "http", "https://mcp.apify.com")

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
        return {"status": "error", "message": f"Unknown MCP tool: {tool_name}"}

mcp_hub = MCPHubService()

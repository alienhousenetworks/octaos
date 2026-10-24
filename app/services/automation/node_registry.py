"""
OctaOS Enterprise Node Registry.
Defines the three-level hierarchy (Category -> Family -> Node) with versioned input/output
JSON schemas, credential requirements, permissions, and execution bindings.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeDefinition(BaseModel):
    node_id: str
    name: str
    family: str
    category: str  # triggers | control_flow | document_intelligence | data_transform | connectivity | ai_agents | native_modules
    version: str = "1.0.0"
    description: str
    icon: str = "Layers"
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    default_config: Dict[str, Any] = Field(default_factory=dict)
    credential_type: Optional[str] = None  # None | oauth | api_key | secret_ref
    risk_level: str = "low"  # low | medium | high | critical
    requires_approval: bool = False
    is_available: bool = True
    mode: str = "all"  # all | general | document | ai_agent


class NodeFamily(BaseModel):
    id: str
    name: str
    category: str
    description: str
    nodes: List[NodeDefinition] = Field(default_factory=list)


class NodeCategory(BaseModel):
    id: str
    name: str
    description: str
    families: List[NodeFamily] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Canonical Enterprise Catalog
# ─────────────────────────────────────────────────────────────────────────────

ENTERPRISE_CATALOG: List[NodeCategory] = [
    NodeCategory(
        id="triggers",
        name="Triggers & Ingress",
        description="Initiate workflows on events, schedules, webhooks, or files.",
        families=[
            NodeFamily(
                id="webhooks_ingress",
                name="Webhooks & Direct Ingress",
                category="triggers",
                description="Inbound webhook listeners, polling, and manual starts.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.trigger.webhook",
                        name="Inbound Webhook",
                        family="webhooks_ingress",
                        category="triggers",
                        description="Triggers workflow when an HTTP POST payload is received.",
                        icon="Globe",
                        default_config={"method": "POST", "path": "/webhook/v1/event"},
                    ),
                    NodeDefinition(
                        node_id="octaos.trigger.manual",
                        name="Manual Execution",
                        family="webhooks_ingress",
                        category="triggers",
                        description="User-initiated workflow execution with customizable fixture payload.",
                        icon="Play",
                        default_config={"test": True},
                    ),
                    NodeDefinition(
                        node_id="octaos.trigger.cron",
                        name="Schedule / Cron",
                        family="webhooks_ingress",
                        category="triggers",
                        description="Executes on an automated recurring schedule.",
                        icon="Clock",
                        default_config={"cron": "0 9 * * 1-5", "timezone": "UTC"},
                    ),
                ],
            ),
            NodeFamily(
                id="domain_events",
                name="OctaOS Domain Events",
                category="triggers",
                description="Native business events published by CRM, HR, Billing, and Support.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.event.lead_qualified",
                        name="Lead Qualified",
                        family="domain_events",
                        category="triggers",
                        description="Fires when a CRM prospect crosses qualification threshold.",
                        icon="Target",
                        default_config={"min_score": 75},
                    ),
                    NodeDefinition(
                        node_id="octaos.event.ticket_escalated",
                        name="Ticket Escalated (P1)",
                        family="domain_events",
                        category="triggers",
                        description="Fires on urgent customer support SLA breach.",
                        icon="AlertTriangle",
                        default_config={"severity": "urgent"},
                    ),
                    NodeDefinition(
                        node_id="octaos.event.deal_won",
                        name="Deal Won",
                        family="domain_events",
                        category="triggers",
                        description="Fires when a high-value deal room closes won.",
                        icon="Zap",
                    ),
                    NodeDefinition(
                        node_id="octaos.event.document_completed",
                        name="Document Processed",
                        family="domain_events",
                        category="triggers",
                        description="Fires when cascading OCR & text extraction completes.",
                        icon="FileText",
                        mode="document",
                    ),
                    NodeDefinition(
                        node_id="octaos.event.payment_confirmed",
                        name="Payment Confirmed",
                        family="domain_events",
                        category="triggers",
                        description="Fires on verified Razorpay/Stripe subscription confirmation.",
                        icon="DollarSign",
                    ),
                ],
            ),
        ],
    ),
    NodeCategory(
        id="control_flow",
        name="Control Flow & Logic",
        description="Branching, conditional routing, merging, and loop iterations.",
        families=[
            NodeFamily(
                id="branching",
                name="Condition & Branching",
                category="control_flow",
                description="Split or route executions based on expressions.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.control.if_condition",
                        name="IF / Condition",
                        family="branching",
                        category="control_flow",
                        description="Splits execution into True and False branches.",
                        icon="GitFork",
                        default_config={"field": "score", "operator": "gte", "value": 80},
                    ),
                    NodeDefinition(
                        node_id="octaos.control.switch_router",
                        name="Switch / Router",
                        family="branching",
                        category="control_flow",
                        description="Routes payload across multiple output paths based on rules.",
                        icon="GitFork",
                        default_config={"cases": [{"value": "VIP", "route": "vip_route"}]},
                    ),
                    NodeDefinition(
                        node_id="octaos.control.merge_branches",
                        name="Merge Branches",
                        family="branching",
                        category="control_flow",
                        description="Synchronizes parallel execution paths (All, Any, First Success).",
                        icon="Layers",
                        default_config={"mode": "all"},
                    ),
                    NodeDefinition(
                        node_id="octaos.control.loop_for_each",
                        name="Loop / For Each",
                        family="branching",
                        category="control_flow",
                        description="Iterates over an array of items with concurrency batching.",
                        icon="RefreshCw",
                        default_config={"items_path": "items", "batch_size": 5},
                    ),
                    NodeDefinition(
                        node_id="octaos.control.delay",
                        name="Wait / Delay",
                        family="branching",
                        category="control_flow",
                        description="Pauses execution for a specified number of seconds.",
                        icon="Clock",
                        default_config={"wait_seconds": 30},
                    ),
                ],
            ),
        ],
    ),
    NodeCategory(
        id="document_intelligence",
        name="Document Intelligence",
        description="Extract, sanitize, validate, compare, and populate enterprise documents.",
        families=[
            NodeFamily(
                id="doc_extraction",
                name="Cascading Extraction",
                category="document_intelligence",
                description="Invokes OctaOS DocumentProcessingPipeline (Native, RapidOCR, Vision).",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.document.submit",
                        name="OctaOS Document Extractor",
                        family="doc_extraction",
                        category="document_intelligence",
                        description="Cascading parser: Native DOCX/PDF -> RapidOCR -> Multimodal Vision.",
                        icon="FileText",
                        default_config={"department": "General", "enable_ocr": True},
                        mode="document",
                    ),
                    NodeDefinition(
                        node_id="octaos.document.map_fields",
                        name="Extract Structured Fields",
                        family="doc_extraction",
                        category="document_intelligence",
                        description="Maps document text into a validated JSON Schema using LLM Gateway.",
                        icon="Sliders",
                        default_config={"schema": {"name": "string", "amount": "number", "date": "string"}},
                        mode="document",
                    ),
                    NodeDefinition(
                        node_id="octaos.document.validate",
                        name="Validate Document Data",
                        family="doc_extraction",
                        category="document_intelligence",
                        description="Checks extracted fields for completeness, regex rules, and confidence.",
                        icon="CheckCircle2",
                        default_config={"min_confidence": 0.75, "required_fields": ["name", "email"]},
                        mode="document",
                    ),
                    NodeDefinition(
                        node_id="octaos.document.compare",
                        name="Compare Document Versions",
                        family="doc_extraction",
                        category="document_intelligence",
                        description="Identifies additions, modifications, and deletions between two drafts.",
                        icon="GitFork",
                        mode="document",
                    ),
                ],
            ),
            NodeFamily(
                id="doc_generation",
                name="Generation & Review",
                category="document_intelligence",
                description="Populates Jinja2/DOCX templates and stages human review.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.document.populate_template",
                        name="Populate Document Template",
                        family="doc_generation",
                        category="document_intelligence",
                        description="Fills authorized DOCX template with verified fields via TemplateEngine.",
                        icon="FileCheck",
                        default_config={"template_id": "standard_offer_letter"},
                        mode="document",
                    ),
                    NodeDefinition(
                        node_id="octaos.document.request_review",
                        name="Stage Document Review",
                        family="doc_generation",
                        category="document_intelligence",
                        description="Routes document with low confidence scores to Human Review Studio.",
                        icon="ShieldAlert",
                        requires_approval=True,
                        risk_level="high",
                        mode="document",
                    ),
                ],
            ),
        ],
    ),
    NodeCategory(
        id="data_transform",
        name="Data Transformation",
        description="Shape, map, filter, aggregate, and validate structured payloads.",
        families=[
            NodeFamily(
                id="data_shaping",
                name="Fields & Arrays",
                category="data_transform",
                description="Modify object keys, format values, and filter arrays.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.data.set_fields",
                        name="Set Fields",
                        family="data_shaping",
                        category="data_transform",
                        description="Assign constants or calculated variables to workflow state.",
                        icon="Sliders",
                        default_config={"fields": {"status": "processed"}},
                    ),
                    NodeDefinition(
                        node_id="octaos.data.filter",
                        name="Filter Array",
                        family="data_shaping",
                        category="data_transform",
                        description="Filters an array of records using conditions.",
                        icon="Filter",
                        default_config={"field": "active", "equals": True},
                    ),
                    NodeDefinition(
                        node_id="octaos.data.parse_csv",
                        name="Parse CSV",
                        family="data_shaping",
                        category="data_transform",
                        description="Parses CSV string or uploaded file into JSON array.",
                        icon="Database",
                    ),
                    NodeDefinition(
                        node_id="octaos.data.json_to_csv",
                        name="Generate CSV",
                        family="data_shaping",
                        category="data_transform",
                        description="Converts JSON records into downloadable CSV format.",
                        icon="FileText",
                    ),
                ],
            ),
        ],
    ),
    NodeCategory(
        id="connectivity",
        name="Connectivity & Transport",
        description="REST APIs, GraphQL, MCP Tools, Cloud Storage, and Email.",
        families=[
            NodeFamily(
                id="universal_transport",
                name="Universal APIs & MCP",
                category="connectivity",
                description="Interact with any HTTP endpoint or registered MCP server.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.transport.http_request",
                        name="HTTP / REST Request",
                        family="universal_transport",
                        category="connectivity",
                        description="Executes authenticated REST API calls with custom headers and body.",
                        icon="Globe",
                        default_config={"method": "GET", "url": "https://api.example.com"},
                    ),
                    NodeDefinition(
                        node_id="octaos.mcp.invoke_tool",
                        name="MCP Tool Call",
                        family="universal_transport",
                        category="connectivity",
                        description="Invokes an authorized tool on a connected MCP server.",
                        icon="Bot",
                        default_config={"server_slug": "github", "tool_name": "create_issue"},
                    ),
                    NodeDefinition(
                        node_id="octaos.transport.email_send",
                        name="Send Email",
                        family="universal_transport",
                        category="connectivity",
                        description="Sends an email message via configured Gmail/SMTP gateway.",
                        icon="Mail",
                        default_config={"to": "{{email}}", "subject": "Notification"},
                    ),
                    NodeDefinition(
                        node_id="octaos.transport.slack_message",
                        name="Slack Notification",
                        family="universal_transport",
                        category="connectivity",
                        description="Dispatches a message or block alert to a Slack channel.",
                        icon="MessageSquare",
                        default_config={"channel": "#alerts", "message": "Automation Triggered"},
                    ),
                ],
            ),
        ],
    ),
    NodeCategory(
        id="ai_agents",
        name="AI & Agent Orchestration",
        description="LLM prompts, specialized autonomous agents, RAG search, and evaluations.",
        families=[
            NodeFamily(
                id="agent_orchestration",
                name="AI Agents & RAG",
                category="ai_agents",
                description="Autonomous agents and knowledge base vector retrieval.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.ai.llm_prompt",
                        name="LLM Prompt & Completion",
                        family="agent_orchestration",
                        category="ai_agents",
                        description="Prompts any configured provider (Claude, GPT-4o, Gemini, Grok).",
                        icon="Sparkles",
                        default_config={"model": "claude-sonnet-4-6", "prompt": "Analyze: {{text}}"},
                        mode="ai_agent",
                    ),
                    NodeDefinition(
                        node_id="octaos.ai.agent_dispatch",
                        name="Invoke OctaOS AI Worker",
                        family="agent_orchestration",
                        category="ai_agents",
                        description="Dispatches dedicated task to Sales, Support, HR, or Marketing agent.",
                        icon="Bot",
                        default_config={"agent_role": "sales_qualifier", "instructions": "Evaluate lead intent"},
                        mode="ai_agent",
                    ),
                    NodeDefinition(
                        node_id="octaos.ai.rag_search",
                        name="Knowledge RAG Search",
                        family="agent_orchestration",
                        category="ai_agents",
                        description="Queries tenant knowledge base with semantic passage retrieval.",
                        icon="Database",
                        default_config={"query": "{{query}}", "department": "General"},
                        mode="ai_agent",
                    ),
                ],
            ),
        ],
    ),
    NodeCategory(
        id="native_modules",
        name="OctaOS Business Modules",
        description="First-class integration with Sales OS, HR OS, Support, and Governance.",
        families=[
            NodeFamily(
                id="sales_hr_ops",
                name="Enterprise Operations",
                category="native_modules",
                description="Direct calls to internal OctaOS domain engines.",
                nodes=[
                    NodeDefinition(
                        node_id="octaos.sales.score_lead",
                        name="Score & Qualify Lead",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Executes OctaOS Sales AI buying signal and qualification model.",
                        icon="Target",
                    ),
                    NodeDefinition(
                        node_id="octaos.hr.parse_resume",
                        name="Parse Candidate Resume",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Extracts candidate skills, experience, and contact info via HR ResumeParser.",
                        icon="Briefcase",
                        mode="document",
                    ),
                    NodeDefinition(
                        node_id="octaos.hr.prepare_contract",
                        name="Prepare Employment Agreement",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Generates governed employment contract using ContractService.",
                        icon="FileCheck",
                        requires_approval=True,
                        mode="document",
                    ),
                    NodeDefinition(
                        node_id="octaos.support.create_ticket",
                        name="Create Support Ticket",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Logs customer support ticket with priority classification.",
                        icon="MessageSquare",
                    ),
                    NodeDefinition(
                        node_id="octaos.marketing.launch_campaign",
                        name="Launch Marketing Campaign",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Triggers multi-channel campaign creation and ad creative publishing.",
                        icon="Megaphone",
                    ),
                    NodeDefinition(
                        node_id="octaos.orchestrator.dispatch_goal",
                        name="Dispatch Orchestrator Sub-Goal",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Delegates a cross-department operational goal to the AI Call Orchestrator.",
                        icon="Bot",
                    ),
                    NodeDefinition(
                        node_id="octaos.industry_pack.execute_action",
                        name="Execute Industry Pack Action",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Executes a governed tool from the active industry solution pack (e.g. Real Estate, SaaS, Manufacturing).",
                        icon="Briefcase",
                    ),
                    NodeDefinition(
                        node_id="octaos.governance.hitl_approval",
                        name="Executive HITL Approval Gate",
                        family="sales_hr_ops",
                        category="native_modules",
                        description="Enforces human review in OctaOS Boardroom before proceeding.",
                        icon="ShieldAlert",
                        requires_approval=True,
                        risk_level="high",
                    ),
                ],
            ),
        ],
    ),
]


class NodeRegistry:
    """Manages node definitions and dynamic discovery for the visual canvas."""

    @classmethod
    def get_catalog(cls, mode: str = "all") -> List[Dict[str, Any]]:
        """Returns the filtered 3-level catalog according to canvas mode."""
        catalog_list = []
        for cat in ENTERPRISE_CATALOG:
            cat_dict = {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "families": [],
            }
            for fam in cat.families:
                filtered_nodes = [
                    n.model_dump()
                    for n in fam.nodes
                    if mode == "all" or n.mode == "all" or n.mode == mode
                ]
                if filtered_nodes:
                    cat_dict["families"].append({
                        "id": fam.id,
                        "name": fam.name,
                        "category": fam.category,
                        "description": fam.description,
                        "nodes": filtered_nodes,
                    })
            if cat_dict["families"]:
                catalog_list.append(cat_dict)
        return catalog_list

    @classmethod
    def find_node(cls, node_id: str) -> Optional[NodeDefinition]:
        """Finds node definition by unique identifier with alias resilience."""
        clean_id = node_id.strip()
        for cat in ENTERPRISE_CATALOG:
            for fam in cat.families:
                for n in fam.nodes:
                    if n.node_id == clean_id:
                        return n
                    # Alias normalization (e.g. octaos.doc.* <-> octaos.document.*)
                    if clean_id.replace(".doc.", ".document.") == n.node_id or clean_id.replace(".document.", ".doc.") == n.node_id:
                        return n
        return None

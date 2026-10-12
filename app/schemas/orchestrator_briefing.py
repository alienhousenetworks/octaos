"""
Pydantic contracts and schemas for the Hybrid Orchestrator Executive Briefing.
Defines versioned schemas for metrics, findings, Plotly charts, improvement plans, and the 10-agent trace.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    """A strongly-grounded metric value with human formatting and trend info."""
    metric_id: str = Field(..., description="Stable metric key, e.g. 'leads.conversion_rate'")
    name: str = Field(..., description="Human readable name")
    value: float = Field(..., description="Raw numeric scalar")
    formatted: str = Field(..., description="Formatted string, e.g. '18.4%' or '$124,500'")
    unit: str = Field(default="", description="Unit of measurement: %, USD, count, hours")
    change_pct_wow: Optional[float] = Field(default=None, description="Week over week percentage change")
    change_pct_mom: Optional[float] = Field(default=None, description="Month over month percentage change")
    direction: Literal["up", "down", "neutral"] = "neutral"
    category: Literal["marketing", "sales", "finance", "support", "hr", "operations"] = "operations"


class MetricsPayload(BaseModel):
    """Typed dictionary of verified tenant metrics harvested directly from SQL."""
    tenant_id: str
    harvested_at: str
    data_freshness: str = "live"
    empty_state: bool = False
    
    # Core Grounded Metrics Map (Keyed by stable metric_id)
    items: Dict[str, MetricValue] = Field(default_factory=dict)
    
    # Raw aggregates for deterministic chart builders
    raw_funnel: Dict[str, int] = Field(default_factory=dict)
    raw_deal_stages: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    raw_ticket_distribution: Dict[str, int] = Field(default_factory=dict)
    raw_channel_performance: List[Dict[str, Any]] = Field(default_factory=list)
    raw_agent_activity: Dict[str, int] = Field(default_factory=dict)


class Finding(BaseModel):
    """Audited operational weakness or workflow bottleneck with citations."""
    id: str = Field(..., description="Unique finding identifier, e.g. 'W-LEADS-01'")
    title: str = Field(..., description="Brief headline of the finding")
    severity: Literal["CRITICAL", "WARNING", "ADVISORY"] = "WARNING"
    category: Literal["revenue_leak", "bottleneck", "sla_breach", "conversion_drop", "credential_missing", "operational_drag"] = "bottleneck"
    metric_citations: List[str] = Field(default_factory=list, description="List of metric_ids supporting this finding")
    evidence: str = Field(..., description="Factual evidence extracted from the metrics payload")
    root_cause: str = Field(..., description="Underlying systemic or process cause")
    impact: str = Field(..., description="Business impact (revenue, delay, reputation, or lost deals)")


class PlotlyChartSpec(BaseModel):
    """Pure-function Plotly chart specification for native browser rendering."""
    chart_id: str = Field(..., description="Unique chart identifier, e.g. 'funnel_chart'")
    title: str = Field(..., description="Chart display title")
    description: str = Field(default="", description="Data analyst commentary")
    category: Literal["funnel", "financial", "operations", "overview"] = "overview"
    spec: Dict[str, Any] = Field(..., description="Standard Plotly JSON containing 'data', 'layout', 'config'")


class ActionItem(BaseModel):
    """Concrete, phased improvement recommendation with approval guard."""
    id: str = Field(..., description="Unique action key, e.g. 'ACT-7D-01'")
    phase: Literal["7d", "30d", "90d"] = "7d"
    title: str = Field(..., description="Actionable title")
    description: str = Field(..., description="Specific operational instruction")
    department: Literal["Marketing", "Sales", "Support", "HR", "Finance", "System", "Executive"] = "Executive"
    action_type: str = Field(default="remedy_bottleneck", description="Associated execution action")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Pre-filled parameters for execution")
    estimated_roi: str = Field(default="", description="Projected gain or turnaround")
    requires_approval: bool = True
    status: Literal["pending_approval", "approved", "executing", "completed"] = "pending_approval"


class AgentTraceEntry(BaseModel):
    """Audit entry documenting the execution of one of the 10 Swarm stages."""
    agent_id: int = Field(..., ge=1, le=10, description="Stage index (1 to 10)")
    name: str = Field(..., description="Agent or stage title")
    role: str = Field(..., description="Functional specialization")
    execution_type: Literal["deterministic", "llm", "rule_based"] = "deterministic"
    latency_ms: int = Field(default=0, description="Execution duration in milliseconds")
    status: Literal["success", "warning", "fallback", "skipped"] = "success"
    summary: str = Field(..., description="Key contribution or finding output")


class BriefingResponse(BaseModel):
    """Root contract for the Executive Briefing response."""
    schema_version: str = "1.0"
    mode: Literal["analytics", "hybrid", "execution"] = "analytics"
    job_id: Optional[str] = None
    data_freshness: str = "live"
    empty_state: bool = False
    
    # Executive Summary synthesized by Agent 10
    briefing_text: str = Field(..., description="Senior C-level briefing narrative")
    
    # Grounded structured sections
    metrics: MetricsPayload
    charts: List[PlotlyChartSpec] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    improvement_plan: List[ActionItem] = Field(default_factory=list)
    
    # 10-Agent Swarm execution timeline
    trace: List[AgentTraceEntry] = Field(default_factory=list)
    
    # Hybrid Mode: Pending draft action plan requiring explicit confirmation
    draft_execution_plan: Optional[Dict[str, Any]] = None

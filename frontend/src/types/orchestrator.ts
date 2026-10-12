/**
 * TypeScript contract interfaces for the Hybrid Orchestrator Executive Briefing.
 * Strictly typed with no explicit 'any'.
 */

export interface MetricValue {
  metric_id: string;
  name: string;
  value: number;
  formatted: string;
  unit: string;
  change_pct_wow?: number | null;
  change_pct_mom?: number | null;
  direction: 'up' | 'down' | 'neutral';
  category: 'marketing' | 'sales' | 'finance' | 'support' | 'hr' | 'operations';
}

export interface MetricsPayload {
  tenant_id: string;
  harvested_at: string;
  data_freshness: string;
  empty_state: boolean;
  items: Record<string, MetricValue>;
  raw_funnel: Record<string, number>;
  raw_deal_stages: Record<string, Record<string, unknown>>;
  raw_ticket_distribution: Record<string, number>;
  raw_channel_performance: Array<Record<string, unknown>>;
  raw_agent_activity: Record<string, number>;
}

export interface Finding {
  id: string;
  title: string;
  severity: 'CRITICAL' | 'WARNING' | 'ADVISORY';
  category: 'revenue_leak' | 'bottleneck' | 'sla_breach' | 'conversion_drop' | 'credential_missing' | 'operational_drag';
  metric_citations: string[];
  evidence: string;
  root_cause: string;
  impact: string;
}

export interface PlotlyChartSpec {
  chart_id: string;
  title: string;
  description: string;
  category: 'funnel' | 'financial' | 'operations' | 'overview';
  spec: {
    data: unknown[];
    layout: Record<string, unknown>;
    config?: Record<string, unknown>;
  };
}

export interface ActionItem {
  id: string;
  phase: '7d' | '30d' | '90d';
  title: string;
  description: string;
  department: 'Marketing' | 'Sales' | 'Support' | 'HR' | 'Finance' | 'System' | 'Executive';
  action_type: string;
  parameters: Record<string, unknown>;
  estimated_roi: string;
  requires_approval: boolean;
  status: 'pending_approval' | 'approved' | 'executing' | 'completed';
}

export interface AgentTraceEntry {
  agent_id: number; // 1 to 10
  name: string;
  role: string;
  execution_type: 'deterministic' | 'llm' | 'rule_based';
  latency_ms: number;
  status: 'success' | 'warning' | 'fallback' | 'skipped';
  summary: string;
}

export interface BriefingResponse {
  schema_version: string;
  mode: 'analytics' | 'hybrid' | 'execution';
  job_id?: string | null;
  data_freshness: string;
  empty_state: boolean;
  briefing_text: string;
  metrics: MetricsPayload;
  charts: PlotlyChartSpec[];
  findings: Finding[];
  improvement_plan: ActionItem[];
  trace: AgentTraceEntry[];
  draft_execution_plan?: Record<string, unknown> | null;
}

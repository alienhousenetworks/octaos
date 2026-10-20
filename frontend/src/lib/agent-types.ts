export type LifecycleState = 'draft' | 'testing' | 'published' | 'degraded' | 'suspended' | 'archived';

export type RuntimeState = 'idle' | 'running' | 'failed' | 'awaiting_approval';

export type AutonomyLevel = 'L0' | 'L1' | 'L2' | 'L3';

export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH';

export type SideEffect = 'READ' | 'WRITE';

export interface ToolGrant {
  id: string;
  label: string;
  risk: RiskTier;
  sideEffect: SideEffect;
  approval?: boolean;
  enabled?: boolean;
  description?: string;
}

export interface AgentItem {
  id: string;
  name: string;
  slug: string;
  department: string;
  role: string;
  description: string;
  avatar_icon: string;
  is_system: boolean;
  version: number;
  provider: string;
  model: string;
  temperature: number;
  system_prompt: string;
  tools: string[];
  knowledge_access?: string[];
  total_executions: number;
  lifecycle_state?: LifecycleState;
  runtime_state?: RuntimeState;
  created_at?: string | null;
}

export interface WorkforceSummary {
  registered_agents: number;
  system_agents: number;
  custom_agents: number;
  running_now: number | null;
  total_executions: number;
  success_rate: number | null;
  needs_attention: number;
  pending_approvals: number;
}

export interface ActivityLogItem {
  id: string;
  action: string;
  description?: string;
  status: 'success' | 'pending' | 'failed';
  created_at?: string | null;
}

export interface ExecutionTraceItem {
  tool: string;
  args: Record<string, any>;
  duration_ms?: number;
  status?: 'authorized' | 'completed' | 'failed' | 'pending_approval';
}

export interface TestExecutionResult {
  output: string;
  tool_calls: ExecutionTraceItem[];
  lifecycle?: 'draft' | 'validated' | 'authorized' | 'queued' | 'running' | 'completed' | 'failed';
  latency_ms?: number;
}

export type NodePortKind = 'trigger' | 'data' | 'true' | 'false' | 'error' | 'branch';

export interface NodePosition {
  x: number;
  y: number;
}

export interface RetryPolicy {
  max_attempts: number;
  initial_interval_seconds: number;
  backoff_multiplier: number;
  retryable_errors: string[];
}

export interface AutomationNode {
  id: string;
  type: string;
  name: string;
  version: string;
  position: NodePosition;
  tool_id?: string;
  config: Record<string, any>;
  input_mappings: Record<string, any>;
  credential_refs: string[];
  retry_policy?: RetryPolicy;
  timeout_seconds: number;
  is_compensable: boolean;
  requires_approval: boolean;
  display_icon?: string;
  description?: string;
}

export interface AutomationEdge {
  id: string;
  source: string;
  source_handle?: string;
  target: string;
  target_handle?: string;
  kind: NodePortKind;
  condition?: Record<string, any>;
}

export interface WorkflowSettings {
  timezone: string;
  execution_timeout_seconds: number;
  concurrency_limit: number;
  error_workflow_id?: string;
  idempotency_key_expression?: string;
}

export interface AutomationGraph {
  schema_version: string;
  workflow_id?: string;
  version: number;
  name: string;
  slug?: string;
  description?: string;
  category: string;
  nodes: AutomationNode[];
  edges: AutomationEdge[];
  settings: WorkflowSettings;
  metadata: Record<string, any>;
}

export interface GraphValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  topology_stats: {
    total_nodes: number;
    total_edges: number;
    triggers: number;
    actions: number;
  };
}

export type CanvasMode = 'general' | 'document' | 'ai_agent';

export type DocumentLifecycleState =
  | 'SUBMITTED'
  | 'EXTRACTED'
  | 'VALIDATED'
  | 'APPROVED'
  | 'DELIVERED';

export interface NodeDefinition {
  node_id: string;
  name: string;
  family: string;
  category: string;
  version: string;
  description: string;
  icon: string;
  input_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
  default_config?: Record<string, any>;
  credential_type?: string | null;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requires_approval: boolean;
  is_available: boolean;
  mode: 'all' | 'general' | 'document' | 'ai_agent';
}

export interface NodeFamily {
  id: string;
  name: string;
  category: string;
  description: string;
  nodes: NodeDefinition[];
}

export interface NodeCategory {
  id: string;
  name: string;
  description: string;
  families: NodeFamily[];
}

export interface DocumentExtractionResult {
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  doc_type: string;
  department: string;
  extraction_stage: string;
  status: 'succeeded' | 'partial' | 'failed';
  text_content: string;
  page_count: number;
  tables: Array<{
    sheet_or_page: string | number;
    row_count: number;
    headers: string[];
    rows: any[][];
  }>;
  tokens_detected: string[];
  confidence_score: number;
  extracted_at: string;
}

export interface DocumentValidationResult {
  is_valid: boolean;
  requires_human_review: boolean;
  confidence_score: number;
  missing_required_fields: string[];
  flagged_fields: Array<{
    field: string;
    value: any;
    reason: string;
    severity: string;
  }>;
  validated_at: string;
}

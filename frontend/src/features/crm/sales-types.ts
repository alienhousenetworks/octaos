export type SalesSection =
  | 'home'
  | 'accounts'
  | 'inbox'
  | 'prospecting'
  | 'pipeline'
  | 'intelligence'
  | 'deal_desk'
  | 'stepper'
  | 'deal_rooms'
  | 'agent_center'
  | 'analytics'
  | 'config'
  | 'prompt_agent'
  | 'configured_engine'
  | 'industries'
  | 'campaigns'
  | 'field_sales';

export type LeadStatus =
  | 'new'
  | 'qualified'
  | 'contacted'
  | 'meeting_scheduled'
  | 'closed_won'
  | 'closed_lost'
  | string;

export interface Lead {
  id: string;
  name: string;
  email: string;
  phone?: string;
  company: string;
  source: string;
  status: LeadStatus;
  score?: number;
  priority?: 'high' | 'medium' | 'low';
  assigned_to?: string;
  personal_email?: string;
  company_email?: string;
  mobile_no?: string;
  company_contact_no?: string;
  need_of_what?: string;
  how_much?: string;
  why?: string;
  target_context?: string;
  data?: LeadData;
  created_at?: string;
  updated_at?: string;
  website?: string;
  purchasing_capacity?: string;
  qualification_reason?: string;
  evidence_url?: string;
  freshness?: {
    age_days?: number;
    freshness_label?: string;
    event_date?: string;
    date_source?: string;
  };
}

export interface FollowUpStep {
  day: number;
  channel: string;
  content: string;
  status?: 'pending' | 'sent' | 'skipped';
}

export interface LeadData {
  contact?: { name?: string; title?: string; linkedin_url?: string };
  company?: { name?: string; website?: string; industry?: string };
  freshness?: Lead['freshness'] & { signal_snippet?: string };
  evidence_url?: string;
  why_now?: string;
  purchasing_capacity?: string;
  qualification_reason?: string;
  pain_points?: string[];
  scoring_breakdown?: Record<string, number | string>;
  outreach_schedule?: FollowUpStep[];
  draft_subject?: string;
  draft_body?: string;
  sent_actual?: boolean;
  conversation?: any[];
  [key: string]: any;
}

export interface WorkflowStep {
  name: string;
  status: 'pending' | 'executing' | 'completed' | 'failed';
  result?: string;
}

export interface WorkflowStatus {
  workflow_type?: string;
  workflow_name?: string;
  instructions?: string;
  status: 'idle' | 'executing' | 'completed' | 'failed';
  current_step: number;
  current_activity?: string;
  steps: Record<string, WorkflowStep>;
  logs: string[];
}

export interface SalesSettings {
  sales_auto_reply: boolean;
  reply_mode: 'review_first' | 'auto_send';
  auto_book_meetings: boolean;
  meeting_duration_minutes: number;
  buffer_minutes: number;
  follow_up_cadence_days: number;
  max_ai_touchpoints: number;
  sales_ai_auto_send_enabled: boolean;
  outbound_permission_state: 'unknown' | 'granted' | 'denied';
  whatsapp_permission_state: 'unknown' | 'granted' | 'denied';
}

export interface BusinessProfileData {
  company_name: string;
  website: string;
  industry: string;
  service_description: string;
  target_countries: string;
  target_industries: string;
  target_company_size: string;
  target_budget_range: string;
  target_decision_makers: string;
  usp: string;
  case_studies: string;
  offer_details: string;
  extra_context: string;
  primary_source: string;
  calendars: string;
  communication_channels: string[];
  sales_emails: string;
  support_emails: string;
  lead_freshness: string;
}

export const parseBudget = (budgetString: string | null | undefined): number => {
  if (!budgetString) return 0;
  let clean = budgetString.toLowerCase().replace(/[\s\$,]/g, '');
  if (!clean) return 0;
  let multiplier = 1;
  if (clean.includes('k')) {
    multiplier = 1000;
    clean = clean.replace('k', '');
  } else if (clean.includes('m')) {
    multiplier = 1000000;
    clean = clean.replace('m', '');
  }
  clean = clean.replace(/[^0-9\.]/g, '');
  const numeric = parseFloat(clean);
  return isNaN(numeric) ? 0 : numeric * multiplier;
};

export const fmtCurrency = (val: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(val);
};

export interface FieldSalesOverview {
  today_scheduled: number;
  today_completed: number;
  today_delayed: number;
  today_no_shows: number;
  completion_rate_pct: number;
  active_salespeople: number;
  connector_budget: {
    daily_quota: number;
    calls_used: number;
    calls_remaining: number;
    quota_used_pct: number;
    cache_hits: number;
    cache_efficiency_pct: number;
    estimated_daily_cost_usd: number;
    status: string;
  };
}

export interface SalespersonLiveStatus {
  user_id: string;
  name: string;
  email?: string;
  status: string;
  is_shift_active: boolean;
  latitude?: number;
  longitude?: number;
  accuracy?: number;
  battery_level?: number;
  speed?: number;
  last_updated?: string;
}

export interface FieldVisitPin {
  visit_id: string;
  project_name: string;
  project_location?: string;
  latitude: number;
  longitude: number;
  buyer_name: string;
  buyer_phone?: string;
  scheduled_at: string;
  status: string;
  assigned_agent?: string;
  sequence_order?: number;
  estimated_travel_minutes?: number;
}

export interface RecoveryProposal {
  id: string;
  trigger_type: string;
  status: string;
  affected_user_id?: string;
  rationale: string;
  proposed_changes: Array<{
    visit_id: string;
    lead_id?: string;
    action: string;
    original_time: string;
    proposed_time: string;
    original_agent: string;
    proposed_agent: string;
    rationale: string;
    customer_message_draft?: string;
  }>;
  created_at?: string;
}

export interface FieldSalesAnalysisReport {
  tenant_id: string;
  period_days: number;
  generated_at: string;
  executive_summary: {
    total_scheduled_visits: number;
    completed_visits: number;
    no_shows: number;
    cancellations: number;
    completion_rate_pct: number;
    geofence_compliance_pct: number;
  };
  conversion_funnel: {
    inquiries: number;
    completed_showings: number;
    unit_holds: number;
    confirmed_bookings: number;
    inquiry_to_visit_pct: number;
    visit_to_hold_pct: number;
    hold_to_booking_pct: number;
  };
  travel_and_efficiency: {
    total_transit_minutes: number;
    total_showing_minutes: number;
    transit_to_showing_ratio: number;
    verified_on_site_check_ins: number;
    manual_exceptions: number;
  };
  buyer_insights: {
    interest_distribution: Record<string, number>;
    top_objections: Array<{ objection: string; count: number }>;
  };
  recovery_health: {
    delay_incidents: number;
    proposals_applied: number;
    acceptance_rate_pct: number;
  };
  connector_costs: {
    total_mapping_requests: number;
    cache_hits: number;
    billable_calls: number;
    total_spend_usd: number;
    cost_per_completed_visit_usd: number;
  };
  strategic_recommendations: string[];
}

export interface RealEstateProjectItem {
  id: string;
  name: string;
  code?: string;
  location?: string;
  city?: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  rera_number?: string;
  amenities?: string[];
  hold_duration_hours?: number;
  status?: string;
  total_units?: number;
  available_units?: number;
  assigned_team_count?: number;
  units?: any[];
  team?: Array<{
    assignment_id?: string;
    user_id: string;
    name: string;
    email?: string;
    phone?: string;
    role: string;
    ai_recommended?: boolean;
    ai_match_score?: number;
    ai_recommendation_reason?: string;
  }>;
}

export interface SalespersonDirectoryItem {
  user_id: string;
  name: string;
  email: string;
  phone?: string;
  role: string;
  designation?: string;
  is_shift_active: boolean;
  status: string;
  working_hours_start?: string;
  working_hours_end?: string;
  today_visits: number;
  max_visits_per_day: number;
  assigned_projects_count: number;
  assigned_projects?: Array<{
    project_id: string;
    project_name: string;
    location?: string;
    role?: string;
  }>;
}

export interface AITeamSuggestion {
  user_id: string;
  name: string;
  email: string;
  phone?: string;
  match_score: number;
  recommended_role: string;
  current_projects_count: number;
  is_shift_active: boolean;
  rationales: string[];
}

export interface AutoAssignResult {
  lead_id: string;
  lead_name?: string;
  project: {
    id: string;
    name: string;
    location?: string;
    city?: string;
  };
  assigned_specialist: {
    user_id: string;
    name: string;
    email?: string;
    phone?: string;
    role?: string;
  };
  visit: {
    id: string;
    scheduled_at: string;
    duration_minutes?: number;
    status: string;
  };
  assignment_status: string;
  decision_rationale: string;
  is_fallback_unassigned_project?: boolean;
}


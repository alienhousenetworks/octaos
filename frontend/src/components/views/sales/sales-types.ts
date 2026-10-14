export type SalesSection =
  | 'prospecting'
  | 'pipeline'
  | 'stepper'
  | 'deal_rooms'
  | 'analytics'
  | 'config'
  | 'prompt_agent'
  | 'configured_engine';

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

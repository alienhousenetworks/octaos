export interface SalesTerminology {
  lead: string;
  leads: string;
  account: string;
  accounts: string;
  contact: string;
  contacts: string;
  opportunity: string;
  opportunities: string;
  pipeline: string;
}

export interface VerticalPack {
  id: string;
  version: string;
  name: string;
  summary: string;
  readiness: 'configuration' | 'representative' | string;
  domain_status: string;
  domain_note: string;
  terminology: SalesTerminology;
  objects: string[];
  stages: string[];
  qualification: string[];
  record_tabs: string[];
  ai_guidance: { allowed: string[]; prohibited: string[] };
  representative: boolean;
}

export interface CopilotEvidence {
  claim: string;
  source: string;
  verification_status: string;
  note: string;
  observed_at?: string | null;
}

export interface CopilotAction {
  id: 'review_follow_up' | 'prepare_proposal' | 'schedule_meeting' | string;
  label: string;
  preview: string;
  executes: boolean;
  requires_confirmation: boolean;
}

export interface CopilotAdvice {
  record: { id?: string; name?: string | null; company?: string | null; status?: string | null };
  pack: { id: string; name: string; version: string } | null;
  terminology: SalesTerminology;
  question: string;
  answer: string;
  recommendation: string;
  confidence: 'low' | 'medium' | 'high' | string;
  confidence_basis: string;
  readiness: {
    label: string;
    value: string | null;
    source: string;
    verification_status: string;
    note: string;
  };
  deal_health: {
    label: string;
    value: string | null;
    source: string;
    verification_status: string;
    note: string;
  };
  evidence: CopilotEvidence[];
  unknowns: string[];
  actions: CopilotAction[];
  prohibited: string[];
  invented: boolean;
}

export const SHARED_TERMS: SalesTerminology = {
  lead: 'Lead',
  leads: 'Leads',
  account: 'Account',
  accounts: 'Accounts',
  contact: 'Contact',
  contacts: 'Contacts',
  opportunity: 'Opportunity',
  opportunities: 'Opportunities',
  pipeline: 'Pipeline',
};

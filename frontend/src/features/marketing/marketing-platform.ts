export interface MarketingTerminology {
  campaign: string;
  post: string;
  asset: string;
  offer: string;
  cta: string;
  audience: string;
}

export interface MarketingFunnelStage {
  id: string;
  label: string;
  channels: string[];
  description?: string;
}

export interface MarketingContentPillar {
  id: string;
  label: string;
  description: string;
  hooks: string[];
  sample_angles?: string[];
}

export interface MarketingComplianceGuardrails {
  prohibited_guarantees: string[];
  taboo_words: string[];
  required_disclosures: string[];
}

export interface MarketingVisualTokens {
  aesthetic?: string;
  lighting?: string;
  color_palette?: string[];
  camera_framing?: string;
  motion_pace?: string;
}

export interface IndustryCalendarEvent {
  month: string;
  name: string;
  hook: string;
}

export interface MarketingVerticalPack {
  id: string;
  version: string;
  name: string;
  summary: string;
  readiness: 'configuration' | 'representative' | string;
  representative: boolean;
  domain_status: string;
  domain_note: string;
  terminology: MarketingTerminology;
  funnel_stages: MarketingFunnelStage[];
  content_pillars: MarketingContentPillar[];
  compliance_guardrails: MarketingComplianceGuardrails;
  visual_creative_tokens: MarketingVisualTokens;
  industry_calendar_events: IndustryCalendarEvent[];
  capabilities?: Record<string, { status: string; description: string }>;
}

export interface MarketingComplianceResult {
  passed: boolean;
  pack_id?: string;
  pack_name?: string;
  violations: string[];
  warnings: string[];
  required_disclosures: string[];
  remediation_suggestions: string[];
  cleaned_content: string;
}

export interface RealEstateProjectSummary {
  id: string;
  name: string;
  code?: string;
  location?: string;
  city?: string;
  status?: string;
  total_units: number;
  available_units: number;
  rera_number?: string;
  amenities: string[];
  unit_types: string[];
  min_price?: number;
  max_price?: number;
}

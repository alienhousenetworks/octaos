'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Sparkles, Zap, ArrowRight, Loader2, Bot, Layers, CheckCircle2, 
  Activity, SlidersHorizontal, ChevronRight, HelpCircle, Shield,
  Save, Globe, Building, Mail, Calendar, Phone, Check
} from 'lucide-react';
import { WorkflowStatus, BusinessProfileData } from './sales-types';

interface SalesProspectingPanelProps {
  workflowStatus: WorkflowStatus;
  profile: BusinessProfileData;
  setProfile: (updater: (prev: BusinessProfileData) => BusinessProfileData) => void;
  onSaveProfile: () => Promise<void>;
  profileSaving: boolean;
  promptDirective: string;
  setPromptDirective: (val: string) => void;
  promptLeadCount: number;
  setPromptLeadCount: (val: number) => void;
  promptFreshness: string;
  setPromptFreshness: (val: string) => void;
  promptRunning: boolean;
  onRunPromptAgent: (prompt?: string) => Promise<void>;
  onRunConfiguredEngine: () => Promise<void>;
  onSwitchToStepper: () => void;
  selectedProvider: string;
  setSelectedProvider: (val: string) => void;
  selectedModel: string;
  setSelectedModel: (val: string) => void;
  initialMode?: 'prompt' | 'configured';
}

const PROMPT_TEMPLATES = [
  {
    title: 'B2B SaaS Growth',
    prompt: 'Find Series-A to Series-B B2B SaaS companies in North America with 20–100 employees currently scaling their outbound sales team or hiring SDRs.',
  },
  {
    title: 'Manufacturing & Industrial',
    prompt: 'Identify mid-market industrial manufacturing and fabrication companies in UAE or India needing ERP, workflow automation, or inventory efficiency.',
  },
  {
    title: 'Healthcare & Clinics',
    prompt: 'Find multi-location private healthcare clinics, dental networks, or diagnostic centers with 10–50 staff seeking automated patient scheduling.',
  },
  {
    title: 'High-Growth E-Commerce',
    prompt: 'Prospect Shopify Plus direct-to-consumer apparel and beauty brands generating >$2M annual revenue looking to optimize marketing attribution.',
  },
];

export default function SalesProspectingPanel({
  workflowStatus,
  profile,
  setProfile,
  onSaveProfile,
  profileSaving,
  promptDirective,
  setPromptDirective,
  promptLeadCount,
  setPromptLeadCount,
  promptFreshness,
  setPromptFreshness,
  promptRunning,
  onRunPromptAgent,
  onRunConfiguredEngine,
  onSwitchToStepper,
  selectedProvider,
  setSelectedProvider,
  selectedModel,
  setSelectedModel,
  initialMode = 'prompt',
}: SalesProspectingPanelProps) {
  const [activeMode, setActiveMode] = useState<'prompt' | 'configured'>(initialMode);
  const [runningPlaybook, setRunningPlaybook] = useState(false);

  const updateProfileField = (field: keyof BusinessProfileData, val: any) => {
    setProfile((prev) => ({ ...prev, [field]: val }));
  };

  const handlePlaybookRun = async () => {
    setRunningPlaybook(true);
    try {
      await onRunConfiguredEngine();
    } finally {
      setRunningPlaybook(false);
    }
  };

  const isExecuting = workflowStatus.status === 'executing';

  return (
    <div className="space-y-6">
      {/* Live Execution Alert Banner */}
      {isExecuting && (
        <Card className="bg-[#29323E] border border-[#414C5A] p-4 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="relative">
              <span className="w-3 h-3 rounded-full bg-primary block animate-ping" />
              <span className="w-3 h-3 rounded-full bg-primary block absolute inset-0" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-foreground">
                  Sales workflow running · Step {workflowStatus.current_step || 1} of 10
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  ({workflowStatus.workflow_name || 'Prospecting Run'})
                </span>
              </div>
              <p className="text-sm font-medium text-foreground mt-0.5">
                {workflowStatus.current_activity || 'Executing autonomous prospecting pipeline...'}
              </p>
            </div>
          </div>
          <Button
            size="sm"
            onClick={onSwitchToStepper}
            className="bg-primary hover:opacity-90 text-primary-foreground font-semibold text-xs rounded-xl px-4 flex items-center gap-1.5 shadow-sm whitespace-nowrap"
          >
            <Activity size={14} /> Open Live Stepper <ArrowRight size={14} />
          </Button>
        </Card>
      )}

      {/* Mode Switcher Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-1.5 rounded-2xl border border-border shadow-sm">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setActiveMode('prompt')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeMode === 'prompt'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            <Sparkles size={14} /> ⚡ Prompt-Based Sales Agent
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('configured')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeMode === 'configured'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            <SlidersHorizontal size={14} /> ⚙️ Configured Sales Engine
          </button>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 text-xs text-muted-foreground">
          <Shield size={13} className="text-primary" />
          <span>Provider and contact readiness depend on configured, verified sources</span>
        </div>
      </div>

      {/* ── MODE 1: PROMPT SALES AGENT ── */}
      {activeMode === 'prompt' && (
        <Card className="bg-card border border-border rounded-2xl p-6 shadow-sm relative overflow-hidden space-y-5">
          <div>
            <div className="flex items-center justify-between">
              <label className="text-sm font-bold text-foreground flex items-center gap-2">
                <span className="w-1.5 h-4 bg-primary rounded-full inline-block" />
                <Bot size={16} className="text-primary" />
                What accounts and decision-makers are you looking for?
              </label>
              <span className="text-xs text-muted-foreground font-medium">
                Grounded multi-source agentic discovery
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Describe your target criteria, buyer titles, company signals, or geography in natural language. The autonomous agent parses ICP parameters, verifies domains, and scores accounts.
            </p>
          </div>

          {/* Prompt Textarea */}
          <div className="relative">
            <Textarea
              rows={4}
              value={promptDirective}
              onChange={(e) => setPromptDirective(e.target.value)}
              placeholder="e.g. Find B2B SaaS companies in the United States with 15-50 employees that raised seed/Series A in the last 12 months, targeting VP of Sales or Chief Revenue Officer..."
              className="bg-muted/30 border-border rounded-xl p-4 text-sm text-foreground placeholder:text-muted-foreground focus:bg-card focus:border-primary/60 focus:ring-primary/20 leading-relaxed resize-y"
            />
          </div>

          {/* Prompt Template Shortcuts */}
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
              One-Click Prompt Directives:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
              {PROMPT_TEMPLATES.map((tmpl, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPromptDirective(tmpl.prompt)}
                  className="text-left p-3 rounded-xl border border-border bg-muted/40 hover:bg-muted/40 hover:border-primary/40 transition-all group shadow-2xs"
                >
                  <span className="text-xs font-bold text-foreground group-hover:text-primary block">
                    {tmpl.title}
                  </span>
                  <span className="text-[11px] text-muted-foreground line-clamp-2 mt-1 leading-snug">
                    {tmpl.prompt}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Parameters Strip */}
          <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 border-t border-border">
            {/* Lead Volume */}
            <div>
              <label className="text-xs font-bold text-muted-foreground block mb-2">
                Target Lead Volume:
              </label>
              <div className="flex gap-1.5">
                {[10, 25, 50, 100].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setPromptLeadCount(count)}
                    className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
                      promptLeadCount === count
                        ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                        : 'border-border bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/50'
                    }`}
                  >
                    {count}
                  </button>
                ))}
              </div>
            </div>

            {/* Freshness Window */}
            <div>
              <label className="text-xs font-bold text-muted-foreground block mb-2">
                Signal Freshness Window:
              </label>
              <div className="flex gap-1.5">
                {[
                  { id: '7_days', label: '7d' },
                  { id: '14_days', label: '14d' },
                  { id: '30_days', label: '30d' },
                  { id: '90_days', label: '90d' },
                  { id: 'all', label: 'Evergreen' },
                ].map((fresh) => (
                  <button
                    key={fresh.id}
                    type="button"
                    onClick={() => setPromptFreshness(fresh.id)}
                    className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
                      promptFreshness === fresh.id
                        ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                        : 'border-border bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/50'
                    }`}
                  >
                    {fresh.label}
                  </button>
                ))}
              </div>
            </div>

            {/* AI Engine Model */}
            <div>
              <label className="text-xs font-bold text-muted-foreground block mb-2">
                Reasoning Provider:
              </label>
              <select
                value={selectedProvider}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedProvider(val);
                  if (val === 'nvidia') {
                    setSelectedModel?.('meta/llama-3.3-70b-instruct');
                  } else if (val === 'openrouter') {
                    setSelectedModel?.('meta-llama/llama-3.3-70b-instruct');
                  } else if (val === 'together') {
                    setSelectedModel?.('meta-llama/Llama-3.3-70B-Instruct-Turbo');
                  } else if (val === 'openai') {
                    setSelectedModel?.('gpt-4o');
                  } else if (val === 'anthropic') {
                    setSelectedModel?.('claude-sonnet-4-6');
                  } else if (val === 'gemini') {
                    setSelectedModel?.('gemini-2.5-flash');
                  } else if (val === 'groq') {
                    setSelectedModel?.('openai/gpt-oss-120b');
                  } else {
                    setSelectedModel?.('');
                  }
                }}
                className="w-full h-8 text-xs bg-muted/30 border border-border rounded-lg px-2.5 text-foreground focus:bg-card focus:border-primary/60 outline-none"
              >
                <option value="auto">System Default (Environment / .env)</option>
                <option value="nvidia">NVIDIA NIM (Llama 3.3 70B)</option>
                <option value="openrouter">OpenRouter (Llama 3.3 70B)</option>
                <option value="openai">OpenAI (GPT-4o / Mini)</option>
                <option value="anthropic">Anthropic (Claude 3.5 Sonnet)</option>
                <option value="gemini">Google Gemini 2.0</option>
                <option value="groq">Groq (GPT OSS 120B)</option>
                <option value="together">Together AI (Llama 3.3 70B)</option>
              </select>
            </div>
          </div>

          {/* Launch Action */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <CheckCircle2 size={14} className="text-primary" />
              <span>Auto-generates ICP exclusions, verifies emails, and injects into CRM</span>
            </div>

            <Button
              onClick={(event) => {
                const field = event.currentTarget.closest('.rounded-2xl')?.querySelector('textarea');
                void onRunPromptAgent(field?.value || promptDirective);
              }}
              disabled={promptRunning || !promptDirective.trim()}
              className="w-full sm:w-auto h-11 px-8 bg-primary hover:opacity-90 text-primary-foreground font-bold text-sm rounded-xl shadow-sm disabled:opacity-50 transition-all flex items-center justify-center gap-2"
            >
              {promptRunning ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Launching Agent...
                </>
              ) : (
                <>
                  <Sparkles size={16} /> Launch Autonomous Prospecting
                </>
              )}
            </Button>
          </div>
        </Card>
      )}

      {/* ── MODE 2: DETAILED CONFIGURED SALES ENGINE ── */}
      {activeMode === 'configured' && (
        <Card className="bg-card border border-border rounded-2xl p-6 shadow-sm space-y-6">
          {/* Header & Description */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
            <div>
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <span className="w-1.5 h-4 bg-primary rounded-full inline-block" />
                <SlidersHorizontal size={17} className="text-primary" />
                Configured Sales AI V3 Engine Configuration
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Configure your product parameters, ICP criteria, discovery sources, and outreach channels.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onSaveProfile}
                disabled={profileSaving}
                className="text-xs rounded-xl border-border bg-card hover:bg-muted/30 text-foreground shadow-sm"
              >
                {profileSaving ? <Loader2 size={13} className="animate-spin mr-1.5" /> : <Save size={13} className="mr-1.5" />}
                Save Changes
              </Button>
              <Button
                size="sm"
                onClick={handlePlaybookRun}
                disabled={runningPlaybook || profileSaving}
                className="bg-primary hover:opacity-90 text-primary-foreground font-bold text-xs rounded-xl shadow-sm"
              >
                {runningPlaybook ? <Loader2 size={13} className="animate-spin mr-1.5" /> : <Zap size={13} className="mr-1.5" />}
                Launch Engine V3
              </Button>
            </div>
          </div>

          {/* Form Section 1: Company & Product Profile */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
              <Building size={14} className="text-primary" />
              Company Profile &amp; Value Proposition
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Company / Brand Name</label>
                <Input
                  value={profile.company_name}
                  onChange={(e) => updateProfileField('company_name', e.target.value)}
                  placeholder="e.g. Acme Corporation"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Website URL</label>
                <Input
                  value={profile.website}
                  onChange={(e) => updateProfileField('website', e.target.value)}
                  placeholder="https://acme.com"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Industry Sector</label>
                <Input
                  value={profile.industry}
                  onChange={(e) => updateProfileField('industry', e.target.value)}
                  placeholder="B2B SaaS, Manufacturing, Healthcare..."
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <div className="sm:col-span-1">
                <label className="text-xs font-bold text-muted-foreground block mb-1">Unique Selling Proposition (USP)</label>
                <Textarea
                  rows={2}
                  value={profile.usp}
                  onChange={(e) => updateProfileField('usp', e.target.value)}
                  placeholder="Why do buyers choose your offer over competitors?"
                  className="text-xs bg-muted/30 border-border text-foreground resize-none"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-xs font-bold text-muted-foreground block mb-1">Product / Service Offering Description</label>
                <Textarea
                  rows={2}
                  value={profile.service_description}
                  onChange={(e) => updateProfileField('service_description', e.target.value)}
                  placeholder="Detailed breakdown of your software, services, deliverable outcomes, or packages..."
                  className="text-xs bg-muted/30 border-border text-foreground resize-none"
                />
              </div>
            </div>
          </div>

          {/* Form Section 2: ICP Targeting Criteria */}
          <div className="space-y-4 pt-2 border-t border-border">
            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
              <Globe size={14} className="text-primary" />
              Ideal Customer Profile (ICP) &amp; Sourcing Filters
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Target Countries</label>
                <Input
                  value={profile.target_countries}
                  onChange={(e) => updateProfileField('target_countries', e.target.value)}
                  placeholder="United States, United Kingdom, UAE, India"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Target Industries</label>
                <Input
                  value={profile.target_industries}
                  onChange={(e) => updateProfileField('target_industries', e.target.value)}
                  placeholder="SaaS, Manufacturing, Healthcare, Logistics"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Target Company Size</label>
                <Input
                  value={profile.target_company_size}
                  onChange={(e) => updateProfileField('target_company_size', e.target.value)}
                  placeholder="10-100 employees, 50-250"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Target Budget Range</label>
                <select
                  value={profile.target_budget_range}
                  onChange={(e) => updateProfileField('target_budget_range', e.target.value)}
                  className="w-full h-9 text-xs bg-muted/30 border border-border rounded-md px-2.5 text-foreground"
                >
                  <option value="1L-5L">1L–5L ($1k–$5k)</option>
                  <option value="5L-15L">5L–15L ($5k–$20k)</option>
                  <option value="15L+">15L+ ($20k+ Enterprise)</option>
                  <option value="20K-1L">20K–1L (Entry/SMB)</option>
                  <option value="1M+">Enterprise ($100k+)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Target Decision Maker Roles</label>
                <Input
                  value={profile.target_decision_makers}
                  onChange={(e) => updateProfileField('target_decision_makers', e.target.value)}
                  placeholder="Founder, CEO, CTO, VP of Sales, Head of RevOps"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Primary Discovery Provider</label>
                <select
                  value={profile.primary_source}
                  onChange={(e) => updateProfileField('primary_source', e.target.value)}
                  className="w-full h-9 text-xs bg-muted/30 border border-border rounded-md px-2.5 text-foreground"
                >
                  <option value="auto">Auto (Intelligent Routing)</option>
                  <option value="apollo">Apollo.io</option>
                  <option value="hunter">Hunter.io</option>
                  <option value="google_places">Google Places (Local)</option>
                  <option value="apify">Apify Scraper</option>
                  <option value="zoominfo">ZoomInfo</option>
                  <option value="web_search">Universal Open-Web</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Lead Signal Freshness</label>
                <select
                  value={profile.lead_freshness}
                  onChange={(e) => updateProfileField('lead_freshness', e.target.value)}
                  className="w-full h-9 text-xs bg-muted/30 border border-border rounded-md px-2.5 text-foreground"
                >
                  <option value="7_days">7 Days (High Urgency)</option>
                  <option value="14_days">14 Days</option>
                  <option value="30_days">30 Days (Standard)</option>
                  <option value="90_days">90 Days (Quarterly)</option>
                  <option value="all">Evergreen</option>
                </select>
              </div>
            </div>
          </div>

          {/* Form Section 3: Communication & Inboxes */}
          <div className="space-y-4 pt-2 border-t border-border">
            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
              <Mail size={14} className="text-primary" />
              Outreach Inboxes &amp; Meeting Links
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Calendar Link</label>
                <Input
                  value={profile.calendars}
                  onChange={(e) => updateProfileField('calendars', e.target.value)}
                  placeholder="https://calendly.com/your-org/demo"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Sales Outbound Emails</label>
                <Input
                  value={profile.sales_emails}
                  onChange={(e) => updateProfileField('sales_emails', e.target.value)}
                  placeholder="sales@company.com, rep@company.com"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Support Inboxes</label>
                <Input
                  value={profile.support_emails}
                  onChange={(e) => updateProfileField('support_emails', e.target.value)}
                  placeholder="support@company.com"
                  className="text-xs bg-muted/30 border-border text-foreground"
                />
              </div>
            </div>

            {/* Channels Checkboxes */}
            <div>
              <label className="text-xs font-bold text-muted-foreground block mb-1.5">
                Enabled Communication Channels
              </label>
              <div className="flex flex-wrap gap-4 p-3 rounded-xl border border-border bg-muted/40">
                {['email', 'whatsapp', 'linkedin', 'sms', 'telegram'].map((ch) => (
                  <label key={ch} className="flex items-center gap-2 cursor-pointer text-xs capitalize text-foreground font-medium">
                    <input
                      type="checkbox"
                      checked={profile.communication_channels?.includes(ch)}
                      onChange={(e) => {
                        const current = profile.communication_channels || [];
                        if (e.target.checked) {
                          updateProfileField('communication_channels', [...current, ch]);
                        } else {
                          updateProfileField('communication_channels', current.filter((c) => c !== ch));
                        }
                      }}
                      className="rounded border-border text-primary focus:ring-primary"
                    />
                    <span>{ch}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Proof Points & Negative Exclusions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Case Studies / Proof Points</label>
                <Textarea
                  rows={2}
                  value={profile.case_studies}
                  onChange={(e) => updateProfileField('case_studies', e.target.value)}
                  placeholder="Delivered 3x pipeline acceleration for manufacturing client..."
                  className="text-xs bg-muted/30 border-border text-foreground resize-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted-foreground block mb-1">Negative ICP Exclusions &amp; Extra Context</label>
                <Textarea
                  rows={2}
                  value={profile.extra_context}
                  onChange={(e) => updateProfileField('extra_context', e.target.value)}
                  placeholder="Do not prospect recruitment agencies or businesses with <10 staff..."
                  className="text-xs bg-muted/30 border-border text-foreground resize-none"
                />
              </div>
            </div>
          </div>

          {/* Form Actions Footer */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground">
              Parameters are persisted to your tenant profile and used for all autonomous playbooks.
            </p>

            <div className="flex items-center gap-2.5 w-full sm:w-auto">
              <Button
                variant="outline"
                onClick={onSaveProfile}
                disabled={profileSaving}
                className="flex-1 sm:flex-none h-11 px-6 text-xs font-bold rounded-xl border-border bg-card hover:bg-muted/30 text-foreground shadow-sm"
              >
                {profileSaving ? (
                  <>
                    <Loader2 size={14} className="animate-spin mr-1.5" /> Saving...
                  </>
                ) : (
                  <>
                    <Save size={14} className="mr-1.5" /> Save Configuration
                  </>
                )}
              </Button>

              <Button
                onClick={handlePlaybookRun}
                disabled={runningPlaybook || profileSaving}
                className="flex-1 sm:flex-none h-11 px-8 bg-primary hover:opacity-90 text-primary-foreground font-bold text-xs rounded-xl shadow-sm disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              >
                {runningPlaybook ? (
                  <>
                    <Loader2 size={15} className="animate-spin" /> Launching Engine V3...
                  </>
                ) : (
                  <>
                    <Zap size={15} /> Launch Configured Sales Engine V3
                  </>
                )}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}


'use client';

import React, { useState } from 'react';
import { MarketingVerticalPack } from './marketing-platform';
import { ShieldCheck, Sparkles, AlertTriangle, Calendar, Layers, Eye } from 'lucide-react';

interface MarketingIndustriesProps {
  packs: MarketingVerticalPack[];
  activeId: string | null;
  loading: boolean;
  error: string | null;
  savingId: string | null;
  notice: string | null;
  onSelect: (packId: string) => void;
  onOpenRealEstateHub?: () => void;
}

const GENERAL_PACK: MarketingVerticalPack = {
  id: 'general',
  version: '1.0.0',
  name: 'General (Standard Marketing)',
  summary: 'Universal multi-channel marketing campaigns, brand awareness, product launches, and seasonal promotions without vertical-specific compliance restrictions.',
  readiness: 'ready',
  representative: false,
  domain_status: 'available',
  domain_note: 'Standard marketing campaigns suited for any enterprise, business, or startup.',
  terminology: {
    campaign: 'Marketing Campaign',
    post: 'Social Post',
    asset: 'Creative Asset',
    offer: 'Promotion / Offer',
    cta: 'Call to Action',
    audience: 'Target Audience',
  },
  funnel_stages: [
    { id: 'awareness', label: 'Brand Awareness & Reach', channels: ['linkedin', 'instagram', 'facebook'] },
    { id: 'consideration', label: 'Value Proposition & Education', channels: ['linkedin', 'facebook'] },
    { id: 'conversion', label: 'Offer & Lead Conversion', channels: ['linkedin', 'instagram', 'facebook'] },
  ],
  content_pillars: [
    { id: 'brand_story', label: 'Brand Story & Vision', description: 'Company mission, milestones, leadership, and culture.', hooks: ['Why we started this company', 'Our core mission and guiding principles'] },
    { id: 'product_spotlight', label: 'Product & Service Spotlight', description: 'Core value proposition, features, and differentiators.', hooks: ['How our platform solves this core challenge', 'A look under the hood at our newest release'] },
    { id: 'customer_wins', label: 'Customer Proof & Testimonials', description: 'Case studies, customer wins, and tangible results.', hooks: ['How our customer achieved 3x ROI', 'Customer spotlight: lessons learned'] },
    { id: 'industry_insights', label: 'Thought Leadership', description: 'Industry trends, commentary, and actionable tips.', hooks: ['Top 3 trends shaping our space this year', 'What we learned from analyzing market benchmarks'] },
  ],
  compliance_guardrails: {
    prohibited_guarantees: [],
    taboo_words: [],
    required_disclosures: [],
  },
  visual_creative_tokens: {
    aesthetic: 'Clean, modern, professional digital creative direction',
    color_palette: ['#7888D9', '#AAB5C4', '#414C5A'],
  },
  industry_calendar_events: [],
};

export default function MarketingIndustries({
  packs,
  activeId,
  loading,
  error,
  savingId,
  notice,
  onSelect,
  onOpenRealEstateHub,
}: MarketingIndustriesProps) {
  const allPacks = [GENERAL_PACK, ...packs];
  const currentActiveId = activeId || 'general';
  const [openId, setOpenId] = useState<string | null>(currentActiveId);
  const open = allPacks.find((pack) => pack.id === (openId || currentActiveId)) || GENERAL_PACK;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Marketing Industry Packs</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Choose an industry vertical to customize campaign funnels, content pillars, compliance rules, and visual creative tokens, or keep it General for standard marketing.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeId && (
            <button
              type="button"
              disabled={savingId === 'general'}
              onClick={() => onSelect('general')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted/40 hover:text-foreground transition shadow-xs"
              title="Return to general campaign mode without vertical-specific compliance rules"
            >
              Reset to General
            </button>
          )}
          {activeId === 'real_estate' && onOpenRealEstateHub && (
            <button
              type="button"
              onClick={onOpenRealEstateHub}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-medium text-white hover:bg-emerald-700 shadow-sm transition"
            >
              <Sparkles className="size-3.5" />
              Launch Property Campaign
            </button>
          )}
        </div>
      </div>

      {error ? (
        <p className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-primary">
          {notice}
        </p>
      ) : null}
      {loading ? <p className="text-sm text-muted-foreground">Loading marketing packs…</p> : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        {/* Industry Cards Grid */}
        <div className="grid gap-2.5 sm:grid-cols-2">
          {allPacks.map((pack) => {
            const selected = pack.id === currentActiveId;
            const isOpen = pack.id === open.id;
            return (
              <button
                key={pack.id}
                type="button"
                onClick={() => setOpenId(pack.id)}
                className={`group rounded-xl border p-3.5 text-left transition-all ${
                  selected
                    ? 'border-primary bg-primary/5 ring-1 ring-primary/40 shadow-sm'
                    : isOpen
                    ? 'border-primary/50 bg-card shadow-sm'
                    : 'border-border bg-card hover:border-primary/30 hover:bg-muted/20'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold group-hover:text-primary transition-colors">
                      {pack.name}
                    </span>
                    {selected && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-medium text-primary">
                        Active
                      </span>
                    )}
                  </div>
                  <span className="rounded-full border border-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {pack.id === 'general' ? 'General' : pack.representative ? 'Representative' : 'Configuration'}
                  </span>
                </div>
                <p className="mt-1.5 text-xs text-muted-foreground line-clamp-2">{pack.summary}</p>
                <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground border-t border-border/50 pt-2">
                  <span>Pillars: {pack.content_pillars?.length || 0}</span>
                  <span className="capitalize">{pack.domain_status?.replace('_', ' ')}</span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Pack Details Drawer */}
        {open ? (
          <aside className="rounded-2xl border border-border bg-card p-5 space-y-5 h-fit shadow-sm">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                  Pack {open.version} · {open.readiness}
                </span>
                {open.id === currentActiveId && (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                    <ShieldCheck className="size-3.5" /> Active Workspace
                  </span>
                )}
              </div>
              <h2 className="mt-1 text-lg font-bold">{open.name}</h2>
              <p className="mt-1 text-xs text-muted-foreground">{open.domain_note || open.summary}</p>
            </div>

            {/* Terminology */}
            <div className="space-y-1.5 rounded-lg bg-muted/40 p-3 text-xs">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <Layers className="size-3.5 text-primary" /> Terminology
              </span>
              <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-border/40 text-[11px]">
                <div>
                  <span className="text-muted-foreground">Campaign:</span> {open.terminology.campaign}
                </div>
                <div>
                  <span className="text-muted-foreground">Post:</span> {open.terminology.post}
                </div>
                <div>
                  <span className="text-muted-foreground">Offer:</span> {open.terminology.offer}
                </div>
                <div>
                  <span className="text-muted-foreground">CTA:</span> {open.terminology.cta}
                </div>
              </div>
            </div>

            {/* Content Pillars */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Sparkles className="size-3.5 text-primary" /> Core Content Pillars ({open.content_pillars?.length || 0})
              </h3>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {open.content_pillars?.map((pillar) => (
                  <div key={pillar.id} className="rounded-md border border-border/60 bg-muted/20 p-2 text-xs">
                    <span className="font-medium text-foreground">{pillar.label}</span>
                    <p className="text-[11px] text-muted-foreground mt-0.5">{pillar.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Compliance Guardrails */}
            <div className="space-y-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs">
              <span className="font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="size-3.5" /> Statutory Compliance & Guardrails
              </span>
              <p className="text-[11px] text-muted-foreground mt-1">
                AI will automatically prevent:
              </p>
              <ul className="list-disc list-inside text-[11px] text-muted-foreground space-y-0.5">
                {open.compliance_guardrails?.taboo_words?.slice(0, 4).map((tw, idx) => (
                  <li key={idx}>Never claim &quot;{tw}&quot;</li>
                ))}
                <li>Zero unsupported absolute guarantees</li>
              </ul>
              {open.compliance_guardrails?.required_disclosures?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-amber-500/20 text-[11px] text-muted-foreground">
                  <span className="font-medium text-foreground">Required Disclosures:</span>
                  <p className="italic mt-0.5">{open.compliance_guardrails.required_disclosures[0]}</p>
                </div>
              )}
            </div>

            {/* Visual Tokens */}
            {open.visual_creative_tokens && (
              <div className="space-y-1.5 text-xs">
                <span className="font-semibold text-muted-foreground flex items-center gap-1.5">
                  <Eye className="size-3.5" /> Visual Creative Direction
                </span>
                <p className="text-[11px] text-muted-foreground">
                  {open.visual_creative_tokens.aesthetic}
                </p>
                {open.visual_creative_tokens.color_palette && (
                  <div className="flex items-center gap-1.5 mt-1">
                    {open.visual_creative_tokens.color_palette.map((color, idx) => (
                      <div
                        key={idx}
                        className="size-4 rounded-full border border-black/10 shadow-xs"
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Calendar Events */}
            {open.industry_calendar_events && open.industry_calendar_events.length > 0 && (
              <div className="space-y-1.5 text-xs">
                <span className="font-semibold text-muted-foreground flex items-center gap-1.5">
                  <Calendar className="size-3.5" /> Industry Calendar Moments
                </span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {open.industry_calendar_events.map((ev, idx) => (
                    <span
                      key={idx}
                      className="rounded bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                    >
                      {ev.month}: {ev.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Action Button */}
            <div className="pt-2">
              <button
                type="button"
                disabled={savingId === open.id || open.id === currentActiveId}
                onClick={() => onSelect(open.id)}
                className="w-full rounded-lg bg-primary px-3 py-2.5 text-xs font-semibold text-primary-foreground disabled:opacity-60 transition"
              >
                {open.id === currentActiveId
                  ? (open.id === 'general' ? 'Active General Mode' : 'Active Industry Pack')
                  : savingId === open.id
                  ? 'Switching…'
                  : open.id === 'general'
                  ? 'Use General (Standard)'
                  : `Use ${open.name}`}
              </button>
            </div>
          </aside>
        ) : null}
      </div>
    </div>
  );
}

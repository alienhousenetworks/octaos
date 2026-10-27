'use client';

import React from 'react';
import {
  ArrowDownRight,
  ArrowRight,
  Bot,
  CalendarDays,
  CircleDot,
  ClipboardCheck,
  GitFork,
  Inbox,
  Radar,
  Settings2,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { Lead, SalesSection } from './sales-types';
import { SHARED_TERMS, VerticalPack } from './sales-platform';

interface SalesHomeProps {
  companyName: string;
  pack: VerticalPack | null;
  leads: Lead[];
  onOpen: (section: SalesSection) => void;
  onOpenLead: (lead: Lead) => void;
  onOpenConfig: () => void;
  onOpenCampaignsModule: () => void;
  onOpenWorkflows: () => void;
}

type SalesAction = {
  number: string;
  title: string;
  description: string;
  detail: string;
  icon: React.ReactNode;
  actionLabel: string;
  onClick: () => void;
};

export default function SalesHome({
  companyName,
  pack,
  leads,
  onOpen,
  onOpenLead,
  onOpenConfig,
  onOpenCampaignsModule,
  onOpenWorkflows,
}: SalesHomeProps) {
  const terms = pack?.terminology || SHARED_TERMS;
  const recent = leads.slice(0, 5);

  const actions: SalesAction[] = [
    {
      number: '01',
      title: 'Define your target market',
      description: 'Tell Sales AI who you sell to, where you sell, and what makes your offer relevant.',
      detail: 'Business profile · ICP · target market · geographies · offer',
      icon: <Settings2 size={18} />,
      actionLabel: 'Configure targeting',
      onClick: () => onOpen('config'),
    },
    {
      number: '02',
      title: 'Find and research prospects',
      description: 'Build a prospecting brief, run available discovery sources, and inspect source evidence and missing data.',
      detail: 'Search brief · providers · evidence · contact research',
      icon: <Radar size={18} />,
      actionLabel: 'Open prospecting',
      onClick: () => onOpen('prospecting'),
    },
    {
      number: '03',
      title: 'Review and qualify leads',
      description: 'Inspect records, source context, contact readiness, and blockers before moving prospects forward.',
      detail: 'CRM · lead dossier · qualification · suppression',
      icon: <ClipboardCheck size={18} />,
      actionLabel: 'Review CRM',
      onClick: () => onOpen('pipeline'),
    },
    {
      number: '04',
      title: 'Engage, handle replies, book meetings',
      description: 'Work from approved outreach and the shared inbox. Track actual delivery and calendar confirmations.',
      detail: 'Campaigns · inbox · approvals · calendar',
      icon: <CalendarDays size={18} />,
      actionLabel: 'Open inbox',
      onClick: () => onOpen('inbox'),
    },
  ];

  const modules: { label: string; description: string; icon: React.ReactNode; onClick: () => void }[] = [
    { label: 'Lead pipeline', description: 'Records, stages and ownership', icon: <Users size={17} />, onClick: () => onOpen('pipeline') },
    { label: 'AI agents', description: 'Agent registry and run visibility', icon: <Bot size={17} />, onClick: () => onOpen('agent_center') },
    { label: 'Campaigns', description: 'Outreach and follow-up sequences', icon: <Inbox size={17} />, onClick: onOpenCampaignsModule },
    { label: 'Workflow automation', description: 'Triggers and connected processes', icon: <GitFork size={17} />, onClick: onOpenWorkflows },
    { label: 'Sales intelligence', description: 'Research and buying context', icon: <CircleDot size={17} />, onClick: () => onOpen('intelligence') },
    { label: 'Performance', description: 'Available reporting and outcomes', icon: <ArrowDownRight size={17} />, onClick: () => onOpen('analytics') },
  ];

  return (
    <div className="mx-auto w-full max-w-[1440px] space-y-6 pb-8">
      <section className="overflow-hidden rounded-2xl border border-[#414C5A] bg-[#29323E]">
        <div className="flex flex-col gap-5 border-b border-[#414C5A] px-5 py-5 md:flex-row md:items-center md:justify-between md:px-7">
          <div className="min-w-0">
            <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-[#AAB5C4]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#7888D9]" />
              Sales workspace
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-[#E5EAF1] md:text-3xl">From prospect discovery to booked meetings</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#AAB5C4]">
              A guided workspace for finding the right accounts, checking evidence, qualifying contacts, coordinating outreach, and following real replies.
              Configure the process once; use the same path for each campaign.
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-start gap-1 rounded-xl border border-[#414C5A] bg-[#202630] px-4 py-3 md:min-w-52">
            <span className="text-xs text-[#AAB5C4]">Current workspace</span>
            <span className="max-w-60 truncate text-sm font-semibold text-[#E5EAF1]">{companyName || 'Your organization'}</span>
            <button type="button" onClick={onOpenConfig} className="mt-1 inline-flex items-center gap-1.5 text-xs font-medium text-[#A1AEF0] hover:text-white">
              Configure business context <ArrowRight size={13} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 divide-y divide-[#414C5A] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <div className="px-5 py-4 md:px-7">
            <div className="text-xs text-[#AAB5C4]">Stored lead records</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-[#E5EAF1]">{leads.length.toLocaleString()}</div>
            <p className="mt-1 text-xs text-[#8592A3]">Loaded from this workspace's current lead data</p>
          </div>
          <div className="px-5 py-4 md:px-7">
            <div className="text-xs text-[#AAB5C4]">Recommended starting point</div>
            <div className="mt-1 text-base font-semibold text-[#E5EAF1]">Targeting and ICP</div>
            <p className="mt-1 text-xs text-[#8592A3]">Define the buyer before running discovery</p>
          </div>
          <div className="px-5 py-4 md:px-7">
            <div className="text-xs text-[#AAB5C4]">Automation policy</div>
            <div className="mt-1 inline-flex items-center gap-2 text-base font-semibold text-[#E5EAF1]"><ShieldCheck size={17} className="text-[#A1AEF0]" /> Evidence and permission gated</div>
            <p className="mt-1 text-xs text-[#8592A3]">Missing evidence or authorization should block sending</p>
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Your sales workflow</h2>
            <p className="mt-1 text-sm text-muted-foreground">Follow the sequence. Each step opens the existing Sales workspace for that task.</p>
          </div>
          <button type="button" onClick={() => onOpen('config')} className="inline-flex items-center gap-2 self-start rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:border-primary/50 hover:bg-muted/40">
            <Settings2 size={15} /> Sales settings
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          {actions.map((item) => (
            <article key={item.number} className="group flex min-w-0 flex-col rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/40 sm:p-5">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/40 text-primary">{item.icon}</div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-semibold tabular-nums tracking-wider text-muted-foreground">{item.number}</span>
                    <h3 className="text-sm font-semibold text-foreground">{item.title}</h3>
                  </div>
                  <p className="mt-2 text-sm leading-5 text-muted-foreground">{item.description}</p>
                  <p className="mt-3 text-xs leading-5 text-muted-foreground">{item.detail}</p>
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <button type="button" onClick={item.onClick} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90">
                  {item.actionLabel} <ArrowRight size={15} />
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Sales tools</h2>
          <p className="mt-1 text-sm text-muted-foreground">Open a focused workspace without navigating through a crowded menu.</p>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {modules.map((item) => (
            <button key={item.label} type="button" onClick={item.onClick} className="flex min-w-0 items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-muted/20">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted/50 text-primary">{item.icon}</span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-foreground">{item.label}</span>
                <span className="mt-0.5 block text-xs text-muted-foreground">{item.description}</span>
              </span>
              <ArrowRight size={15} className="shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
            </button>
          ))}
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="flex flex-col gap-2 border-b border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Recently loaded {terms.leads.toLowerCase()}</h2>
            <p className="mt-1 text-xs text-muted-foreground">Records returned by the current workspace query; this list is not a live activity feed.</p>
          </div>
          <button type="button" onClick={() => onOpen('pipeline')} className="inline-flex items-center gap-1.5 self-start text-sm font-medium text-primary hover:underline">
            Open all records <ArrowRight size={14} />
          </button>
        </div>
        {recent.length === 0 ? (
          <div className="flex flex-col items-start gap-3 px-5 py-8">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted/50 text-muted-foreground"><Users size={19} /></div>
            <div>
              <p className="text-sm font-medium text-foreground">No lead records are loaded yet</p>
              <p className="mt-1 max-w-xl text-sm text-muted-foreground">Start by defining your target market, then open Prospecting to search with the providers configured for your workspace. Discovery results may need enrichment before they become qualified contacts.</p>
            </div>
            <button type="button" onClick={() => onOpen('prospecting')} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground">
              Start prospecting <ArrowRight size={15} />
            </button>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {recent.map((lead) => (
              <li key={lead.id}>
                <button type="button" onClick={() => onOpenLead(lead)} className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/30 sm:px-5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border bg-muted/40 text-xs font-semibold text-foreground">
                    {(lead.name || '?').trim().slice(0, 1).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-foreground">{lead.name || 'Unnamed record'}</span>
                    <span className="mt-0.5 block truncate text-xs text-muted-foreground">{lead.company || 'Company not recorded'}</span>
                  </span>
                  <span className="hidden max-w-40 truncate rounded-md border border-border px-2 py-1 text-xs text-muted-foreground sm:block">{lead.status || 'Status unavailable'}</span>
                  <ArrowRight size={15} className="shrink-0 text-muted-foreground" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/20 px-4 py-3 text-xs leading-5 text-muted-foreground">
        <ShieldCheck size={15} className="mt-0.5 shrink-0" />
        <p>Important: a generated draft is not a sent message, a provider connection is not proof of delivery, and a proposed meeting is not booked until the calendar confirms it. Review evidence, permissions, and provider status in the relevant workflow before enabling automation.</p>
      </div>
    </div>
  );
}

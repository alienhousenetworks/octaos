'use client';

import React from 'react';
import {
  Bot,
  Building2,
  GitFork,
  LineChart,
  Megaphone,
  Radar,
  Shield,
  Sparkles,
  Users,
  Workflow,
} from 'lucide-react';
import { Lead, SalesSection } from './sales-types';
import { SHARED_TERMS, VerticalPack } from './sales-platform';

interface SalesHomeProps {
  companyName: string;
  pack: VerticalPack | null;
  leads: Lead[];
  onOpen: (section: SalesSection) => void;
  onOpenLead: (lead: Lead) => void;
  onOpenIndustries: () => void;
  onOpenCampaignsModule: () => void;
  onOpenWorkflows: () => void;
}

const modules: { id: SalesSection | 'workflows'; label: string; icon: React.ReactNode }[] = [
  { id: 'pipeline', label: 'CRM', icon: <Users size={18} /> },
  { id: 'agent_center', label: 'AI Workforce', icon: <Bot size={18} /> },
  { id: 'workflows', label: 'Automation', icon: <GitFork size={18} /> },
  { id: 'prospecting', label: 'Prospecting', icon: <Radar size={18} /> },
  { id: 'campaigns', label: 'Campaigns', icon: <Megaphone size={18} /> },
  { id: 'analytics', label: 'Analytics', icon: <LineChart size={18} /> },
];

export default function SalesHome({
  companyName,
  pack,
  leads,
  onOpen,
  onOpenLead,
  onOpenIndustries,
  onOpenCampaignsModule,
  onOpenWorkflows,
}: SalesHomeProps) {
  const terms = pack?.terminology || SHARED_TERMS;
  const recent = leads.slice(0, 5);

  const openModule = (id: (typeof modules)[number]['id']) => {
    if (id === 'workflows') {
      onOpenWorkflows();
      return;
    }
    onOpen(id);
  };

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-[#24344d] bg-[#132033] text-white px-5 py-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1d4ed8]/30 text-[#93c5fd]">
              <Sparkles size={18} />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Sales</h1>
              <p className="text-sm text-[#b7c3d6]">One workspace. The industry pack only changes the language and the rules.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onOpenIndustries}
            className="text-left text-sm text-[#d5deea] hover:text-white"
          >
            <span className="text-[#93c5fd]">{companyName || 'Organization'}</span>
            <span className="mx-1.5 text-[#6e7f99]">·</span>
            <span>{pack ? pack.name : 'Choose an industry'}</span>
            <span className="mx-1.5 text-[#6e7f99]">·</span>
            <span>Sales workspace</span>
          </button>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
          {modules.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => openModule(item.id)}
              className="flex items-center gap-3 rounded-xl border border-[#2c4060] bg-[#1a2c45] px-4 py-4 text-left hover:border-[#3b82f6]"
            >
              <span className="text-[#93c5fd]">{item.icon}</span>
              <span className="text-sm font-medium">{item.label}</span>
            </button>
          ))}
        </div>
      </section>

      <div className="grid gap-3 lg:grid-cols-2">
        <WorkspaceCard
          icon={<Building2 size={16} />}
          title="Sales workspace"
          body={`${terms.leads}, ${terms.accounts.toLowerCase()}, contacts, ${terms.opportunities.toLowerCase()}, products, quotes, activities, and forecasts.`}
          onClick={() => onOpen('pipeline')}
        />
        <WorkspaceCard
          icon={<Sparkles size={16} />}
          title="Intelligence workspace"
          body="Research, buying signals, stored scores, deal risks, and next steps grounded in the record."
          onClick={() => onOpen('intelligence')}
        />
        <WorkspaceCard
          icon={<Workflow size={16} />}
          title="Execution workspace"
          body="Campaigns, cadences, visual flows, approvals, connector jobs, and delivery logs."
          onClick={() => onOpen('inbox')}
        />
        <WorkspaceCard
          icon={<Shield size={16} />}
          title="Administration"
          body="Industry packs, pipelines, policies, agent permissions, integrations, and audit."
          onClick={onOpenIndustries}
        />
      </div>

      <section className="rounded-2xl border border-border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Recent {terms.leads.toLowerCase()}</h2>
          <button type="button" onClick={() => onOpen('pipeline')} className="text-xs font-medium text-primary">
            Open CRM
          </button>
        </div>
        {recent.length === 0 ? (
          <p className="text-sm text-muted-foreground">No records are stored in this workspace yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {recent.map((lead) => (
              <li key={lead.id}>
                <button
                  type="button"
                  onClick={() => onOpenLead(lead)}
                  className="flex w-full items-center justify-between gap-3 py-2.5 text-left hover:text-primary"
                >
                  <span>
                    <span className="block text-sm font-medium">{lead.name || 'Unnamed record'}</span>
                    <span className="block text-xs text-muted-foreground">{lead.company || 'No company stored'}</span>
                  </span>
                  <span className="text-xs text-muted-foreground">{lead.status || 'No status'}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <TextLink onClick={onOpenCampaignsModule}>Marketing campaigns</TextLink>
          <TextLink onClick={onOpenWorkflows}>Workflow canvas</TextLink>
          <TextLink onClick={() => onOpen('config')}>Sales rules</TextLink>
        </div>
      </section>
    </div>
  );
}

function WorkspaceCard({
  icon,
  title,
  body,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-2xl border border-border bg-card p-4 text-left hover:border-primary/40"
    >
      <div className="mb-2 flex items-center gap-2 text-primary">{icon}<span className="font-semibold text-foreground">{title}</span></div>
      <p className="text-sm text-muted-foreground">{body}</p>
    </button>
  );
}

function TextLink({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="rounded-md border border-border px-2 py-1 text-muted-foreground hover:text-foreground">
      {children}
    </button>
  );
}

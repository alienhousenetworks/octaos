'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bot, Wrench } from 'lucide-react';
import { useWorkspace } from '@/lib/workspace';
import { pathForView } from '@/lib/navigation';
import { AgentItem } from '@/lib/agent-types';
import SalesView from '@/features/crm/sales-view';
import CampaignsView from '@/components/views/campaigns-view';
import SupportView from '@/components/views/support-view';
import HREnterpriseSuite from '@/features/people/hr-suite';
import CEOView from '@/components/views/ceo-view';
import AIOptimizationView from '@/components/views/ai-optimization-view';
import CoordinationView from '@/components/views/coordination-view';
import OrchestratorView from '@/components/views/orchestrator-view';
import TeamsView from '@/components/views/teams-view';
import ApprovalsView from '@/components/views/approvals-view';
import MarketplaceView from '@/components/views/marketplace-view';
import AutomationsView from '@/features/automations/automations-view';

export type AgentWorkspaceKind =
  | 'general'
  | 'sales'
  | 'marketing'
  | 'support'
  | 'people'
  | 'hiring'
  | 'finance'
  | 'ceo'
  | 'governance'
  | 'activity'
  | 'teams'
  | 'approvals'
  | 'marketplace'
  | 'workflows'
  | 'custom';

export function resolveAgentWorkspace(
  agent: { slug?: string; department?: string } | null,
  scope: string,
  explicitGeneral: boolean,
): AgentWorkspaceKind {
  if (explicitGeneral) return 'general';
  const slug = (agent?.slug || '').toLowerCase();
  const dept = (agent?.department || '').toLowerCase();
  if (agent) {
    if (slug === 'sales_ai' || dept === 'sales') return 'sales';
    if (slug === 'marketing_ai' || dept === 'marketing') return 'marketing';
    if (slug === 'support_ai' || dept === 'support') return 'support';
    if (slug === 'hr_ai' || dept === 'hr') return scope === 'hiring' ? 'hiring' : 'people';
    if (slug === 'finance_ai' || dept === 'finance') return 'finance';
    if (slug === 'ceo_ai' || dept === 'executive') return 'ceo';
    return 'custom';
  }
  switch (scope) {
    case 'sales': return 'sales';
    case 'marketing': return 'marketing';
    case 'support': return 'support';
    case 'people': return 'people';
    case 'hiring': return 'hiring';
    case 'objectives': return 'ceo';
    case 'governance': return 'governance';
    case 'activity': return 'activity';
    case 'teams': return 'teams';
    case 'approvals': return 'approvals';
    case 'costs': return 'finance';
    case 'marketplace': return 'marketplace';
    case 'workflows': return 'workflows';
    default: return 'general';
  }
}

function CustomAgentWorkspace({ agent }: { agent: AgentItem | null }) {
  if (!agent) return null;
  const tools = Array.isArray(agent.tools) ? agent.tools : [];
  const knowledge = Array.isArray(agent.knowledge_access) ? agent.knowledge_access : [];
  const prompt = (agent.system_prompt || '').trim();
  return (
    <div data-testid="agent-workspace" data-workspace="custom" className="rounded-2xl border border-white/[0.08] bg-[#121714] p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-[#9af18b]"><Bot className="size-3.5" /> Custom agent</div>
          <h2 className="text-xl font-semibold">{agent.name}</h2>
          <p className="mt-1 text-sm text-white/60">{agent.role || 'Custom workspace'}</p>
        </div>
        <Link href={'/app/agents/' + encodeURIComponent(agent.id) + '?tab=console'} className="rounded-lg border border-[#7de56b]/25 px-3 py-2 text-xs text-[#a4f196] hover:bg-[#7de56b]/10">Open cockpit</Link>
      </div>
      {agent.description && <p className="mt-4 max-w-3xl text-sm leading-6 text-white/70">{agent.description}</p>}
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/10 p-3">
          <p className="text-[11px] uppercase tracking-wide text-white/40">Provider</p>
          <p className="mt-1 text-sm">{agent.provider || 'Not set'} · {agent.model || 'Model not set'}</p>
        </div>
        <div className="rounded-xl border border-white/10 p-3">
          <p className="text-[11px] uppercase tracking-wide text-white/40">Department</p>
          <p className="mt-1 text-sm">{agent.department || 'General'} · {agent.is_system ? 'Built-in' : 'Custom'}</p>
        </div>
        <div className="rounded-xl border border-white/10 p-3">
          <p className="text-[11px] uppercase tracking-wide text-white/40">Version</p>
          <p className="mt-1 text-sm">{agent.version ? 'v' + agent.version : 'Unversioned'} · {agent.total_executions || 0} runs</p>
        </div>
      </div>
      <div className="mt-5">
        <div className="mb-2 flex items-center gap-2 text-sm font-medium"><Wrench className="size-4 text-[#8be977]" /> Tools</div>
        {tools.length === 0 ? <p className="text-xs text-white/45">No tools are configured for this agent.</p> : (
          <div className="flex flex-wrap gap-2">
            {tools.map((tool) => <span key={tool} className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-white/75">{tool}</span>)}
          </div>
        )}
      </div>
      <div className="mt-5">
        <p className="mb-2 text-sm font-medium">Knowledge this agent can use</p>
        {knowledge.length === 0 ? <p className="text-xs text-white/45">No department knowledge is attached. It still uses the shared classic library when a tool allows it.</p> : (
          <div className="flex flex-wrap gap-2">
            {knowledge.map((item) => <span key={item} className="rounded-full bg-[#7de56b]/10 px-2.5 py-1 text-xs text-[#b6f5a8]">{item}</span>)}
          </div>
        )}
      </div>
      <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-4">
        <p className="text-sm font-medium">Instructions</p>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-white/70">{prompt ? prompt.slice(0, 900) : 'This agent has no saved instructions yet. Add them from the cockpit.'}</p>
      </div>
    </div>
  );
}

export default function AgentWorkspaceBody({ kind, agent }: { kind: AgentWorkspaceKind; agent: AgentItem | null }) {
  const workspace = useWorkspace();
  const router = useRouter();
  if (kind === 'general') return null;
  if (kind === 'custom') return <CustomAgentWorkspace agent={agent} />;

  const shared = {
    token: workspace.token,
    API_URL: workspace.apiUrl,
    fetchWithAuth: workspace.fetchWithAuth,
    fetchData: workspace.fetchData,
  };
  let body: React.ReactNode = null;
  if (kind === 'sales') {
    body = <SalesView {...shared} timeline={workspace.timeline} section="home" />;
  } else if (kind === 'marketing') {
    body = <CampaignsView {...shared} activeView="campaigns" configuredProviders={workspace.configuredProviders} />;
  } else if (kind === 'support') {
    body = <SupportView {...shared} tenantId={workspace.tenantId} />;
  } else if (kind === 'people' || kind === 'hiring') {
    body = <HREnterpriseSuite {...shared} screen={kind === 'hiring' ? 'hiring' : 'people'} />;
  } else if (kind === 'finance') {
    body = <AIOptimizationView {...shared} metrics={workspace.metrics} />;
  } else if (kind === 'ceo') {
    body = <CEOView {...shared} timeline={workspace.timeline} setActiveView={(viewId) => router.push(pathForView(viewId))} />;
  } else if (kind === 'governance') {
    body = <CoordinationView {...shared} />;
  } else if (kind === 'activity') {
    body = (
      <OrchestratorView
        {...shared}
        apps={workspace.apps}
        configuredProviders={workspace.configuredProviders}
        timeline={workspace.timeline}
        queue={workspace.queue}
        handleApprovePost={workspace.handleApprovePost}
        handleRejectPost={workspace.handleRejectPost}
      />
    );
  } else if (kind === 'teams') {
    body = <TeamsView {...shared} teams={workspace.teams} setTeams={workspace.setTeams} />;
  } else if (kind === 'approvals') {
    body = <ApprovalsView {...shared} />;
  } else if (kind === 'marketplace') {
    body = <MarketplaceView {...shared} apps={workspace.apps} />;
  } else if (kind === 'workflows') {
    body = <AutomationsView {...shared} userProfile={workspace.userProfile} />;
  }
  if (!body) return null;
  return (
    <div data-testid="agent-workspace" data-workspace={kind} className="rounded-2xl border border-white/[0.08] bg-background p-2 md:p-4">
      {body}
    </div>
  );
}

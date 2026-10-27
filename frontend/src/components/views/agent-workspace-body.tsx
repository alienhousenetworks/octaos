'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Activity, Bot, BriefcaseBusiness, CheckCircle2, CircleDollarSign, Command, GitBranch, MessageSquareText, Radar, ShieldCheck, Sparkles, Target, Users, Wrench, Zap } from 'lucide-react';
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
      <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(0,1.2fr)_minmax(260px,.8fr)]">
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="flex items-center justify-between gap-3"><p className="text-sm font-medium">System instructions</p><span className="text-[10px] uppercase tracking-wider text-white/35">Read-only preview</span></div>
          <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs leading-6 text-white/65">{prompt ? prompt.slice(0, 6000) : 'No saved instructions. Open the cockpit to configure this agent.'}</pre>
        </div>
        <div className="rounded-xl border border-[#7de56b]/20 bg-[#7de56b]/[0.045] p-4">
          <div className="flex items-center gap-2 text-sm font-medium"><Sparkles className="size-4 text-[#9af18b]" /> Test this agent</div>
          <p className="mt-2 text-xs leading-5 text-white/55">Open the agent console to send a test prompt with its saved configuration and inspect the returned output and tool trace.</p>
          <Link href={'/app/agents/' + encodeURIComponent(agent.id) + '?tab=console'} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#9af18b] px-3 py-2.5 text-xs font-semibold text-[#10170f] hover:bg-[#b5f6a8]"><Command className="size-3.5" /> Open live test console</Link>
          <p className="mt-3 text-[10px] leading-4 text-white/35">Tests may invoke enabled tools. Review permissions and approval rules before running side-effecting actions.</p>
        </div>
      </div>
    </div>
  );
}

const WORKSPACE_SKINS: Record<Exclude<AgentWorkspaceKind, 'general' | 'custom'>, { eyebrow: string; title: string; description: string; accent: string; border: string; glow: string; icon: React.ElementType; actions: string[] }> = {
  sales: { eyebrow: 'Revenue operations', title: 'Sales AI Command Center', description: 'Pipeline execution, account research and sales workflows in one focused workspace.', accent: '#a7f3c2', border: 'border-emerald-300/20', glow: 'from-emerald-400/15 via-amber-300/[0.06] to-transparent', icon: Target, actions: ['Score new leads', 'Draft personalized outreach', 'Analyze stalled deals'] },
  marketing: { eyebrow: 'Creative growth system', title: 'Marketing AI Studio & Radar', description: 'Create campaign concepts, align messaging with brand knowledge and move into channel execution.', accent: '#d8b4fe', border: 'border-fuchsia-300/20', glow: 'from-violet-400/20 via-fuchsia-400/[0.07] to-transparent', icon: Radar, actions: ['Generate omnichannel campaign', 'Run trend research', 'Synthesize channel copy'] },
  support: { eyebrow: 'Customer resolution operations', title: 'Support AI Resolution Center', description: 'Work support queues, improve reusable answers and inspect SLA risks using connected support data.', accent: '#a5f3fc', border: 'border-cyan-300/20', glow: 'from-cyan-400/20 via-sky-400/[0.07] to-transparent', icon: MessageSquareText, actions: ['Triage unassigned tickets', 'Draft a knowledge article', 'Review SLA risks'] },
  people: { eyebrow: 'People operations', title: 'People & Talent AI Suite', description: 'Coordinate employee operations, document workflows and onboarding with clear human review.', accent: '#fda4af', border: 'border-rose-300/20', glow: 'from-rose-400/20 via-orange-300/[0.07] to-transparent', icon: Users, actions: ['Review people operations', 'Draft onboarding plan', 'Audit HR documents'] },
  hiring: { eyebrow: 'Talent acquisition', title: 'Hiring Intelligence Workspace', description: 'Review candidate pipelines and build consistent, job-related screening workflows.', accent: '#fda4af', border: 'border-rose-300/20', glow: 'from-rose-400/20 via-pink-300/[0.07] to-transparent', icon: BriefcaseBusiness, actions: ['Review candidate pipeline', 'Draft role scorecard', 'Build interview plan'] },
  finance: { eyebrow: 'AI efficiency & economics', title: 'AI Optimization & Token Economics', description: 'Inspect reported usage and provider performance before changing routing or model policies.', accent: '#99f6e4', border: 'border-teal-300/20', glow: 'from-teal-400/20 via-emerald-300/[0.07] to-transparent', icon: CircleDollarSign, actions: ['Review model routing', 'Investigate provider latency', 'Prepare usage review'] },
  ceo: { eyebrow: 'Strategy & execution', title: 'Executive War Room', description: 'Review objectives, cross-functional delivery and strategic decisions in the existing executive workspace.', accent: '#fcd34d', border: 'border-amber-300/20', glow: 'from-amber-400/20 via-orange-300/[0.07] to-transparent', icon: Target, actions: ['Prepare executive briefing', 'Review objective blockers', 'Run alignment check'] },
  governance: { eyebrow: 'Policy & decision assurance', title: 'Multi-Agent Governance Boardroom', description: 'Inspect coordination, governance and decision workflows without presenting unverified consensus as fact.', accent: '#c7d2fe', border: 'border-indigo-300/20', glow: 'from-indigo-400/20 via-slate-300/[0.07] to-transparent', icon: ShieldCheck, actions: ['Review pending decisions', 'Inspect policy risks', 'Prepare deliberation brief'] },
  activity: { eyebrow: 'Runtime operations', title: 'Live Orchestrator & Task DAGs', description: 'Inspect existing execution queues, run history and workflow traces from the native orchestrator.', accent: '#bef264', border: 'border-lime-300/20', glow: 'from-lime-400/15 via-emerald-300/[0.06] to-transparent', icon: GitBranch, actions: ['Inspect failed runs', 'Review queue health', 'Trace a workflow'] },
  teams: { eyebrow: 'Workforce coordination', title: 'AI Teams Workspace', description: 'Coordinate registered teams and their work using the existing team management tools.', accent: '#bfdbfe', border: 'border-blue-300/20', glow: 'from-blue-400/15 via-cyan-300/[0.06] to-transparent', icon: Users, actions: ['Review team assignments', 'Plan team handoffs', 'Audit team access'] },
  approvals: { eyebrow: 'Human-in-the-loop control', title: 'Approvals Command Center', description: 'Review pending decisions and preserve human approval for governed or high-impact actions.', accent: '#fde68a', border: 'border-yellow-300/20', glow: 'from-yellow-400/15 via-amber-300/[0.06] to-transparent', icon: CheckCircle2, actions: ['Review pending approvals', 'Summarize decision risks', 'Prepare approval checklist'] },
  marketplace: { eyebrow: 'Capabilities & integrations', title: 'AI Capability Marketplace', description: 'Explore available integrations and installed capabilities through the native marketplace.', accent: '#c4b5fd', border: 'border-violet-300/20', glow: 'from-violet-400/15 via-indigo-300/[0.06] to-transparent', icon: Zap, actions: ['Review installed capabilities', 'Find a workflow integration', 'Audit enabled apps'] },
  workflows: { eyebrow: 'Automation design', title: 'Workflow Automation Studio', description: 'Build and inspect workflows using the existing automation builder and its configured integrations.', accent: '#bef264', border: 'border-lime-300/20', glow: 'from-lime-400/15 via-green-300/[0.06] to-transparent', icon: GitBranch, actions: ['Design a workflow', 'Review failed automations', 'Map a manual process'] },
};

export default function AgentWorkspaceBody({ kind, agent, onQuickAction }: { kind: AgentWorkspaceKind; agent: AgentItem | null; onQuickAction?: (prompt: string) => void }) {
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
  const skin = WORKSPACE_SKINS[kind];
  const SkinIcon = skin.icon;
  return (
    <div data-testid="agent-workspace" data-workspace={kind} data-workspace-skin={kind} className={'overflow-hidden rounded-2xl border bg-[#0f1310] ' + skin.border}>
      <header className={'relative overflow-hidden border-b border-white/[0.07] bg-gradient-to-br ' + skin.glow + ' px-5 py-6 md:px-7 md:py-7'}>
        <div className="pointer-events-none absolute -right-12 -top-16 size-56 rounded-full border border-white/[0.06]" />
        <div className="pointer-events-none absolute -right-2 -top-6 size-36 rounded-full border border-white/[0.06]" />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.18em]" style={{ color: skin.accent }}><SkinIcon className="size-3.5" /> {skin.eyebrow}</div>
            <h2 className="text-2xl font-semibold tracking-tight text-white md:text-3xl">{skin.title}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/55">{skin.description}</p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs text-white/60"><Activity className="size-3.5" style={{ color: skin.accent }} /><span>Native workspace connected</span></div>
        </div>
        <div className="relative mt-6 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {skin.actions.map((action) => (
            <button key={action} type="button" onClick={() => onQuickAction?.(action + '. Use connected OctaOS data and approved company knowledge. Separate verified facts from assumptions, and do not claim an action completed unless the system confirms it.')} className="group flex min-h-11 items-center justify-between gap-3 rounded-xl border border-white/[0.09] bg-black/20 px-3.5 py-3 text-left text-xs font-medium text-white/80 transition hover:border-white/20 hover:bg-black/35">
              <span>{action}</span><Sparkles className="size-3.5 shrink-0 opacity-55 transition group-hover:opacity-100" style={{ color: skin.accent }} />
            </button>
          ))}
        </div>
      </header>
      <div className="p-2 md:p-4">{body}</div>
    </div>
  );
}

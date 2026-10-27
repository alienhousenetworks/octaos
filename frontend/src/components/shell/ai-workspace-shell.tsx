'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useInterfaceMode, pathForAgentSlug, sectionAssistant, knowledgeDepartmentForScope } from '@/lib/interface-mode';
import { crumbForPath } from '@/lib/navigation';
import { useWorkspace, useWorkspaceFeed } from '@/lib/workspace';
import { AgentItem } from '@/lib/agent-types';
import ClassicKnowledgeShelf from '@/components/shell/classic-knowledge-shelf';
import {
  Bot, ChevronDown, FileText, Globe2, LayoutDashboard, Menu,
  MessageSquare, Plus, Search, Settings2, ShieldCheck, Sparkles, Workflow, X,
} from 'lucide-react';

const LINKS = [
  { href: '/app/assistant', label: 'Assistant', icon: MessageSquare },
  { href: '/app/research', label: 'Search Intelligence', icon: Search },
  { href: '/app/home', label: 'Overview', icon: LayoutDashboard },
  { href: '/app/knowledge', label: 'Knowledge', icon: FileText },
  { href: '/app/agents', label: 'Agent Studio', icon: Bot },
  { href: '/app/sales', label: 'Sales', icon: Sparkles },
  { href: '/app/campaigns', label: 'Marketing', icon: Sparkles },
  { href: '/app/support', label: 'Support', icon: MessageSquare },
  { href: '/app/hr', label: 'People', icon: Bot },
  { href: '/app/automations', label: 'Workflows', icon: Workflow },
  { href: '/app/approvals', label: 'Approvals', icon: ShieldCheck },
  { href: '/app/settings/integrations', label: 'Integrations', icon: Globe2 },
];

function agentMatches(agent: AgentItem, query: string) {
  const haystack = [agent.name, agent.role, agent.department, agent.slug, agent.description].join(' ').toLowerCase();
  return haystack.includes(query);
}

function WorkspaceNav({
  pathname,
  accountLabel,
  search,
  setSearch,
  agents,
  agentsLoading,
  agentsError,
  requestedAgent,
  onNavigate,
}: {
  pathname: string;
  accountLabel?: string;
  search: string;
  setSearch: (value: string) => void;
  agents: AgentItem[];
  agentsLoading: boolean;
  agentsError: string;
  requestedAgent: string;
  onNavigate?: () => void;
}) {
  const { setMode } = useInterfaceMode();
  const query = search.trim().toLowerCase();
  const links = LINKS.filter((item) => !query || item.label.toLowerCase().includes(query));
  const visibleAgents = agents.filter((agent) => !query || agentMatches(agent, query));
  const generalActive = pathname === '/app/assistant' && (!requestedAgent || requestedAgent === 'orchestrator');

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex h-[68px] items-center gap-3 border-b border-white/[0.08] px-5">
        <div className="flex size-9 items-center justify-center rounded-xl bg-[#1b2a1d] text-[#82ee70]"><Sparkles className="size-5" /></div>
        <div className="min-w-0"><div className="truncate text-sm font-semibold tracking-tight">OctaOS</div><div className="text-[11px] text-white/45">AI Workspace</div></div>
        <span className="ml-auto rounded-full border border-[#70d95e]/20 bg-[#70d95e]/10 px-2 py-0.5 text-[10px] text-[#8bed78]">AI</span>
      </div>
      <div className="flex gap-2 px-3 pt-4">
        <Link href="/app/assistant" onClick={onNavigate} className="flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-[#78e565] px-3 text-sm font-semibold text-[#0b1609] transition hover:bg-[#91f280]"><Plus className="size-4" /> New chat</Link>
        <Link href="/app/agents" onClick={onNavigate} aria-label="Open Agent Studio" title="Open Agent Studio" className="flex size-10 items-center justify-center rounded-xl border border-white/10 text-white/70 hover:bg-white/[0.06]"><Bot className="size-4" /></Link>
      </div>
      <div className="px-3 pt-4">
        <label className="flex h-9 items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 text-white/45 focus-within:border-[#78e565]/40"><Search className="size-4 shrink-0" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search AIs" aria-label="Search AIs" className="min-w-0 flex-1 bg-transparent text-xs text-white outline-none placeholder:text-white/35" /></label>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="px-4 pb-2 pt-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">Your AIs {agents.length > 0 ? `· ${agents.length}` : ''}</div>
        <nav aria-label="AI agents" data-testid="ai-agent-roster" className="space-y-1 px-2.5">
          {(!query || 'general assistant'.includes(query) || 'orchestrator'.includes(query)) && (
            <Link href="/app/assistant" onClick={onNavigate} className={'flex min-h-10 items-center gap-3 rounded-xl px-3 py-2 text-[12px] ' + (generalActive ? 'bg-[#1b241c] text-white' : 'text-white/55 hover:bg-white/[0.05] hover:text-white')}>
              <MessageSquare className="size-4 shrink-0 text-white/40" />
              <span className="min-w-0 flex-1 truncate">General assistant</span>
            </Link>
          )}
          {agentsLoading && <p className="px-3 py-2 text-xs text-white/40">Loading registered AIs…</p>}
          {agentsError && <p className="px-3 py-2 text-xs text-amber-300">{agentsError}</p>}
          {visibleAgents.map((agent) => {
            const href = pathForAgentSlug(agent.slug, agent.id);
            const active = pathname === href || (pathname === '/app/assistant' && (requestedAgent === agent.slug || requestedAgent === agent.id));
            return (
              <Link key={agent.id} href={href} onClick={onNavigate} data-agent-slug={agent.slug} className={'flex min-h-10 items-center gap-3 rounded-xl px-3 py-2 text-[12px] ' + (active ? 'bg-[#1b241c] text-white' : 'text-white/55 hover:bg-white/[0.05] hover:text-white')}>
                <Bot className="size-4 shrink-0 text-[#8be977]" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate">{agent.name}</span>
                  <span className="block truncate text-[10px] text-white/35">{agent.department || 'General'} · {agent.is_system ? 'Built-in' : 'Custom'}</span>
                </span>
              </Link>
            );
          })}
          {!agentsLoading && !agentsError && visibleAgents.length === 0 && <p className="px-3 py-2 text-xs text-white/40">{query ? 'No matching AIs' : 'No registered AIs yet. Create one in Agent Studio.'}</p>}
        </nav>
        <div className="px-4 pb-2 pt-6 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">Workspace</div>
        <nav className="space-y-1 px-2.5 pb-4">
          {links.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} onClick={onNavigate} className={'flex h-10 items-center gap-3 rounded-xl px-3 text-[13px] transition ' + (pathname === href || pathname.startsWith(href + '/') ? 'bg-white/[0.08] text-white' : 'text-white/60 hover:bg-white/[0.05] hover:text-white')}>
              <Icon className="size-4 text-[#8be977]" />{label}
            </Link>
          ))}
          {links.length === 0 && <p className="px-3 py-2 text-xs text-white/40">No matching pages</p>}
        </nav>
      </div>
      <div className="border-t border-white/[0.08] p-3">
        <div className="mb-3 flex items-center gap-2 rounded-xl bg-white/[0.035] p-2.5"><div className="flex size-8 items-center justify-center rounded-full bg-[#29352b] text-xs font-semibold text-[#a4f196]">{(accountLabel || 'U').slice(0, 1).toUpperCase()}</div><div className="min-w-0 flex-1"><div className="truncate text-xs font-medium">{accountLabel || 'Your workspace'}</div><div className="text-[10px] text-white/40">Current organization</div></div><Settings2 className="size-4 text-white/40" /></div>
        <button type="button" onClick={() => setMode('classic')} className="flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-white/10 text-xs text-white/70 transition hover:bg-white/[0.06] hover:text-white"><LayoutDashboard className="size-4" /> Switch to Classic</button>
      </div>
    </div>
  );
}

export default function AIWorkspaceShell({ children, accountLabel }: { children: React.ReactNode; accountLabel?: string }) {
  const pathname = usePathname();
  const [requestedAgent, setRequestedAgent] = useState('');
  const { setMode } = useInterfaceMode();
  const workspace = useWorkspace();
  useWorkspaceFeed(true);
  const crumb = crumbForPath(pathname);
  const pageChat = sectionAssistant(pathname);
  const isKnowledge = pathname === '/app/knowledge' || pathname.startsWith('/app/knowledge/');
  const isChat = pathname === '/app/assistant' || pageChat !== null;
  const [contextOpen, setContextOpen] = useState(true);
  const [navOpen, setNavOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [agentsError, setAgentsError] = useState('');

  useEffect(() => {
    const syncAgent = () => setRequestedAgent(new URLSearchParams(window.location.search).get('agent') || '');
    syncAgent();
    setNavOpen(false);
    window.addEventListener('popstate', syncAgent);
    window.addEventListener('octaos-agent-query', syncAgent);
    return () => {
      window.removeEventListener('popstate', syncAgent);
      window.removeEventListener('octaos-agent-query', syncAgent);
    };
  }, [pathname]);

  useEffect(() => {
    if (!workspace.token) return;
    let active = true;
    setAgentsLoading(true);
    setAgentsError('');
    workspace.fetchWithAuth(workspace.apiUrl + '/dashboard/agents')
      .then(async (response) => {
        if (!response.ok) throw new Error('The agent list is unavailable (' + response.status + ').');
        const data = await response.json();
        if (!active) return;
        setAgents(Array.isArray(data) ? data as AgentItem[] : []);
      })
      .catch((err) => { if (active) setAgentsError(err instanceof Error ? err.message : 'Could not load AIs.'); })
      .finally(() => { if (active) setAgentsLoading(false); });
    return () => { active = false; };
  }, [workspace.token, workspace.apiUrl, workspace.fetchWithAuth]);

  const navProps = {
    pathname,
    accountLabel,
    search,
    setSearch,
    agents,
    agentsLoading,
    agentsError,
    requestedAgent,
    onNavigate: () => setNavOpen(false),
  };

  return (
    <div className="ai-workspace-shell flex h-[100dvh] min-h-0 overflow-hidden bg-[#0b0d0c] text-[#f4f6f3]">
      <aside className="hidden w-[248px] shrink-0 flex-col border-r border-white/[0.08] bg-[#101311] max-lg:w-[218px] md:flex">
        <WorkspaceNav {...navProps} />
      </aside>
      {navOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button type="button" aria-label="Close navigation" className="absolute inset-0 bg-black/60" onClick={() => setNavOpen(false)} />
          <aside className="relative flex h-full w-[280px] flex-col border-r border-white/[0.08] bg-[#101311]">
            <button type="button" aria-label="Close sidebar" className="absolute top-4 right-3 z-10 rounded-md p-1 text-white/50 hover:text-white" onClick={() => setNavOpen(false)}><X className="size-4" /></button>
            <WorkspaceNav {...navProps} />
          </aside>
        </div>
      )}

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[68px] shrink-0 items-center gap-3 border-b border-white/[0.08] bg-[#0d100e] px-4 md:px-7">
          <button type="button" className="inline-flex size-9 items-center justify-center rounded-lg border border-white/10 text-white/70 md:hidden" aria-label="Open navigation" onClick={() => setNavOpen(true)}><Menu className="size-4" /></button>
          <div className="flex size-9 items-center justify-center rounded-xl border border-[#7de56b]/20 bg-[#172219] text-[#83eb70]"><Bot className="size-4" /></div>
          <div className="min-w-0"><h1 className="truncate text-sm font-semibold">{crumb.name}</h1><p className="truncate text-[11px] text-white/45">{pageChat ? pageChat.title + ' workspace' : crumb.section}{agents.length > 0 ? ` · ${agents.length} AIs` : ''}</p></div>
          <div className="ml-auto flex items-center gap-2">
            <div role="group" aria-label="Interface mode" data-testid="interface-mode-toggle" className="inline-flex shrink-0 items-center rounded-lg border border-white/10 bg-white/[0.04] p-0.5">
              <button type="button" aria-pressed="true" className="h-8 rounded-md bg-[#78e565] px-2.5 text-xs font-semibold text-[#0b1609]" title="AI chat is showing on this page">AI</button>
              <button type="button" aria-pressed="false" onClick={() => setMode('classic')} className="h-8 rounded-md px-2.5 text-xs text-white/70 hover:text-white" title="Show the classic layout on this page">Classic</button>
            </div>
            <span className="hidden items-center gap-1.5 rounded-full border border-white/[0.08] px-2.5 py-1 text-[10px] text-white/50 sm:inline-flex"><span className="size-1.5 rounded-full bg-[#82e96e]" /> Workspace ready</span>
            <button type="button" onClick={() => setContextOpen(!contextOpen)} className="flex h-9 items-center gap-2 rounded-lg border border-white/10 px-3 text-xs text-white/70 hover:bg-white/[0.05]" aria-expanded={contextOpen}><Settings2 className="size-4" /><span className="hidden sm:inline">Context</span><ChevronDown className={'size-3 transition ' + (contextOpen ? 'rotate-180' : '')} /></button>
          </div>
        </header>
        <div className="flex min-h-0 flex-1">
          <main className="ai-workspace-chat min-w-0 flex-1 overflow-y-auto px-3 py-4 md:px-6 md:py-5">
            <div className="w-full">
              {!isKnowledge && !isChat && (
                <details className="mb-4 rounded-2xl border border-white/[0.09] bg-[#101311] px-4 py-3 lg:hidden">
                  <summary className="cursor-pointer text-sm font-medium text-white/80">Company knowledge</summary>
                  <div className="pt-3">
                    <ClassicKnowledgeShelf knowledge={workspace.knowledge} department="all" />
                  </div>
                </details>
              )}
              {children}
            </div>
          </main>
          {contextOpen && (
            <aside className="w-[300px] shrink-0 overflow-y-auto border-l border-white/[0.08] bg-[#101311] px-4 py-5 max-xl:w-[260px] max-lg:hidden">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold">Context & tools</h2>
                <button type="button" aria-label="Close context panel" onClick={() => setContextOpen(false)} className="rounded-md p-1 text-white/40 hover:bg-white/[0.06] hover:text-white"><X className="size-4" /></button>
              </div>
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3">
                <div className="mb-2 flex items-center gap-2 text-xs font-medium"><Sparkles className="size-4 text-[#8be977]" /> {pageChat?.title || crumb.name}</div>
                <p className="text-[11px] leading-5 text-white/45">{agents.length} registered {agents.length === 1 ? 'AI is' : 'AIs are'} available in this workspace. Actions still follow organization permissions.</p>
              </div>
              {!isKnowledge && !isChat && (
                <div className="mt-4">
                  <ClassicKnowledgeShelf knowledge={workspace.knowledge} department="all" limit={5} />
                </div>
              )}
              {isChat && (
                <p className="mt-4 text-xs leading-5 text-white/50">This chat uses the same classic Knowledge library. The documents are listed on the page, filtered to this section when it has a department.</p>
              )}
              {isKnowledge && (
                <p className="mt-4 text-xs leading-5 text-white/50">This page is the classic Knowledge library. Every AI section uses these same documents.</p>
              )}
              <div className="mb-2 mt-6 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/35">Work tools</div>
              <div className="space-y-1">
                {LINKS.slice(0, 6).map(({ href, label, icon: Icon }) => (
                  <Link key={href} href={href} className="flex items-center gap-3 rounded-lg px-2.5 py-2 text-xs text-white/65 transition hover:bg-white/[0.05] hover:text-white"><Icon className="size-4 text-[#8be977]" /><span className="flex-1">{label}</span></Link>
                ))}
              </div>
              <Link href="/app/approvals" className="mt-4 flex items-start gap-3 rounded-xl border border-white/[0.08] p-3 hover:bg-white/[0.035]"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-[#8be977]" /><span><span className="block text-xs font-medium">Approvals</span><span className="mt-1 block text-[11px] leading-4 text-white/40">Review actions that require authorization.</span></span></Link>
              <Link href="/app/settings/integrations" className="mt-4 inline-flex text-xs text-[#a3f194] hover:underline">Manage integrations →</Link>
            </aside>
          )}
        </div>
      </section>
    </div>
  );
}

'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useInterfaceMode, pathForAgentSlug, sectionAssistant } from '@/lib/interface-mode';
import { crumbForPath, visibleGroups, isItemActive } from '@/lib/navigation';
import { useWorkspace, useWorkspaceFeed } from '@/lib/workspace';
import { AgentItem } from '@/lib/agent-types';
import CommandPalette from '@/components/shell/command-palette';
import {
  Bot, LayoutDashboard, Menu,
  MessageSquare, Plus, Search, Settings2, ShieldCheck, Sparkles, Workflow, X,
  Clock3, ListTodo, PanelRight, PanelRightClose, SlidersHorizontal, CheckCircle2,
  FileText, Globe2,
} from 'lucide-react';

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
  profile,
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
  profile?: any;
  onNavigate?: () => void;
}) {
  const { setMode } = useInterfaceMode();
  const query = search.trim().toLowerCase();
  const groups = visibleGroups(profile);
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
      <div className="px-3 pt-3">
        <label className="flex h-9 items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 text-white/45 focus-within:border-[#78e565]/40"><Search className="size-4 shrink-0" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search AIs & screens" aria-label="Search AIs" className="min-w-0 flex-1 bg-transparent text-xs text-white outline-none placeholder:text-white/35" /></label>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-3">
        {/* Roster of Registered AI Specialists */}
        <div className="px-2 pb-1.5 pt-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">AI Specialists {agents.length > 0 ? `· ${agents.length}` : ''}</div>
        <nav aria-label="AI agents" data-testid="ai-agent-roster" className="space-y-0.5">
          {(!query || 'general assistant'.includes(query) || 'orchestrator'.includes(query)) && (
            <Link href="/app/assistant" onClick={onNavigate} className={'flex min-h-9 items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[12px] ' + (generalActive ? 'bg-[#1b241c] text-white font-medium' : 'text-white/60 hover:bg-white/[0.05] hover:text-white')}>
              <MessageSquare className="size-3.5 shrink-0 text-white/40" />
              <span className="min-w-0 flex-1 truncate">General assistant</span>
            </Link>
          )}
          {agentsLoading && <p className="px-2.5 py-1 text-xs text-white/40">Loading registered AIs…</p>}
          {agentsError && <p className="px-2.5 py-1 text-xs text-amber-300">{agentsError}</p>}
          {visibleAgents.map((agent) => {
            const href = pathForAgentSlug(agent.slug, agent.id);
            const active = pathname === href || (pathname === '/app/assistant' && (requestedAgent === agent.slug || requestedAgent === agent.id));
            return (
              <Link key={agent.id} href={href} onClick={onNavigate} data-agent-slug={agent.slug} className={'flex min-h-9 items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[12px] ' + (active ? 'bg-[#1b241c] text-white font-medium' : 'text-white/60 hover:bg-white/[0.05] hover:text-white')}>
                <Bot className="size-3.5 shrink-0 text-[#8be977]" />
                <span className="min-w-0 flex-1 truncate">
                  <span className="block truncate">{agent.name}</span>
                </span>
              </Link>
            );
          })}
        </nav>

        {/* Complete Grouped Workspace Navigation with Permissions */}
        {groups.map((group) => {
          const matchingItems = group.items.filter((item) => !query || item.name.toLowerCase().includes(query) || (item.keywords || '').toLowerCase().includes(query));
          if (matchingItems.length === 0) return null;
          return (
            <div key={group.label} className="mt-4">
              <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">{group.label}</p>
              <nav className="space-y-0.5">
                {matchingItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = isItemActive(item, pathname);
                  return (
                    <Link
                      key={item.id}
                      href={item.href}
                      onClick={onNavigate}
                      className={'flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-[12px] transition ' + (isActive ? 'bg-white/[0.1] text-white font-medium' : 'text-white/60 hover:bg-white/[0.05] hover:text-white')}
                    >
                      <Icon className={`size-3.5 shrink-0 ${isActive ? 'text-[#8be977]' : 'text-white/45'}`} />
                      <span className="truncate">{item.name}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>
          );
        })}
      </div>
      <div className="border-t border-white/[0.08] p-3">
        <div className="mb-2 flex items-center gap-2 rounded-xl bg-white/[0.035] p-2"><div className="flex size-7 items-center justify-center rounded-full bg-[#29352b] text-xs font-semibold text-[#a4f196]">{(accountLabel || 'U').slice(0, 1).toUpperCase()}</div><div className="min-w-0 flex-1"><div className="truncate text-xs font-medium">{accountLabel || 'Your workspace'}</div></div><Settings2 className="size-3.5 text-white/40" /></div>
        <button type="button" onClick={() => setMode('classic')} className="flex h-9 w-full items-center justify-center gap-2 rounded-xl border border-white/10 text-xs text-white/70 transition hover:bg-white/[0.06] hover:text-white"><LayoutDashboard className="size-3.5" /> Switch to Classic</button>
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
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [rightPanelTab, setRightPanelTab] = useState<'chats' | 'tasks' | 'configure'>('chats');
  const [recentChats, setRecentChats] = useState<Array<{ key: string; title: string; thread: string; updatedAt: number }>>([]);
  const [navOpen, setNavOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [agentsError, setAgentsError] = useState('');

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

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

  useEffect(() => {
    try {
      const prefix = 'octaos-universal-assistant-messages:' + String(workspace.tenantId || 'default') + ':';
      const rows: Array<{ key: string; title: string; thread: string; updatedAt: number }> = [];
      for (let index = 0; index < localStorage.length; index += 1) {
        const key = localStorage.key(index);
        if (!key || !key.startsWith(prefix)) continue;
        try {
          const messages = JSON.parse(localStorage.getItem(key) || '[]');
          if (!Array.isArray(messages)) continue;
          const firstUser = messages.find((message: any) => message?.role === 'user' && typeof message.content === 'string' && message.content.trim());
          if (!firstUser) continue;
          const latest = messages[messages.length - 1];
          rows.push({
            key,
            title: String(firstUser.content).replace(/\s+/g, ' ').slice(0, 68),
            thread: key.slice(prefix.length),
            updatedAt: Date.parse(latest?.createdAt || firstUser.createdAt || '') || 0,
          });
        } catch { /* Ignore malformed local history entries. */ }
      }
      rows.sort((a, b) => b.updatedAt - a.updatedAt);
      setRecentChats(rows.slice(0, 30));
    } catch {
      setRecentChats([]);
    }
  }, [pathname, workspace.tenantId]);

  const navProps = {
    pathname,
    accountLabel,
    search,
    setSearch,
    agents,
    agentsLoading,
    agentsError,
    requestedAgent,
    profile: workspace.userProfile,
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
        <header className="flex h-[64px] shrink-0 items-center gap-3 border-b border-white/[0.08] bg-[#0d100e] px-4 md:px-6">
          <button type="button" className="inline-flex size-9 items-center justify-center rounded-lg border border-white/10 text-white/70 md:hidden" aria-label="Open navigation" onClick={() => setNavOpen(true)}><Menu className="size-4" /></button>
          <div className="flex size-8 items-center justify-center rounded-lg border border-[#7de56b]/20 bg-[#172219] text-[#83eb70]"><Bot className="size-4" /></div>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-semibold">{crumb.name}</h1>
            <p className="truncate text-[11px] text-white/45">{pageChat ? pageChat.title + ' workspace' : crumb.section}{agents.length > 0 ? ` · ${agents.length} AIs` : ''}</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div role="group" aria-label="Interface mode" data-testid="interface-mode-toggle" className="inline-flex shrink-0 items-center rounded-lg border border-white/10 bg-white/[0.04] p-0.5">
              <button type="button" aria-pressed="true" className="h-7 rounded-md bg-[#78e565] px-2.5 text-xs font-semibold text-[#0b1609]" title="AI chat is showing on this page">AI</button>
              <button type="button" aria-pressed="false" onClick={() => setMode('classic')} className="h-7 rounded-md px-2.5 text-xs text-white/70 hover:text-white" title="Show the classic layout on this page">Classic</button>
            </div>
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="hidden h-8 items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 text-xs text-white/75 hover:bg-white/[0.06] sm:inline-flex"
            >
              <Search className="size-3.5 text-white/50" />
              <span>Search</span>
              <span className="rounded bg-white/10 px-1 py-0.2 text-[10px] text-white/40">⌘K</span>
            </button>
            <span className="hidden items-center gap-1.5 rounded-full border border-white/[0.08] px-2.5 py-1 text-[10px] text-white/50 lg:inline-flex"><span className="size-1.5 rounded-full bg-[#82e96e]" /> Ready</span>
            <button type="button" onClick={() => { setRightPanelTab('chats'); setRightPanelOpen((open) => !open); }} className={`flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-xs transition ${rightPanelOpen ? 'border-[#78e565]/40 bg-[#78e565]/10 text-[#8bed78]' : 'border-white/10 text-white/75 hover:bg-white/[0.05]'}`} aria-expanded={rightPanelOpen} aria-label={rightPanelOpen ? 'Hide history and tasks' : 'Show history and tasks'}>{rightPanelOpen ? <PanelRightClose className="size-3.5" /> : <PanelRight className="size-3.5" />}<span className="hidden sm:inline">Activity</span></button>
            <button type="button" onClick={() => { setRightPanelTab('configure'); setRightPanelOpen(true); }} className="flex h-8 items-center gap-1.5 rounded-lg border border-white/10 px-2.5 text-xs text-white/75 hover:bg-white/[0.05]" aria-expanded={rightPanelOpen && rightPanelTab === 'configure'}><SlidersHorizontal className="size-3.5" /><span className="hidden sm:inline">Settings</span></button>
          </div>
        </header>

        {/* Workspace Canvas with Contextual Slide-Over Drawer */}
        <div className="relative flex min-h-0 flex-1 overflow-hidden">
          <main className="ai-workspace-chat min-w-0 flex-1 overflow-y-auto px-4 py-4 md:px-7 md:py-6">
            <div className="w-full">
              {children}
            </div>
          </main>

          {/* Slide-over Drawer: Stays out of the way until toggled */}
          {rightPanelOpen && (
            <>
              <div
                className="fixed inset-0 z-30 bg-black/40 lg:hidden"
                onClick={() => setRightPanelOpen(false)}
              />
              <aside aria-label="History, tasks and configuration" className="fixed inset-y-0 right-0 z-40 flex w-[320px] max-w-[90vw] shrink-0 flex-col border-l border-white/[0.08] bg-[#101311] shadow-2xl">
                <div className="flex h-[64px] shrink-0 items-center justify-between border-b border-white/[0.08] px-4">
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold">{rightPanelTab === 'configure' ? 'Workspace configuration' : rightPanelTab === 'tasks' ? 'Tasks & activity' : 'Recent conversations'}</h2>
                    <p className="mt-0.5 text-[11px] text-white/40">{rightPanelTab === 'configure' ? 'Optional settings' : rightPanelTab === 'tasks' ? 'From workspace feed' : 'Continue where you left off'}</p>
                  </div>
                  <button type="button" aria-label="Hide right panel" onClick={() => setRightPanelOpen(false)} className="rounded-lg p-1.5 text-white/50 hover:bg-white/[0.06] hover:text-white"><X className="size-4" /></button>
                </div>
                <div className="grid grid-cols-3 gap-1 border-b border-white/[0.08] p-2">
                  <button type="button" onClick={() => setRightPanelTab('chats')} className={'flex items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] ' + (rightPanelTab === 'chats' ? 'bg-white/[0.09] text-white font-medium' : 'text-white/45 hover:bg-white/[0.04]')}><MessageSquare className="size-3.5" /> Chats</button>
                  <button type="button" onClick={() => setRightPanelTab('tasks')} className={'flex items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] ' + (rightPanelTab === 'tasks' ? 'bg-white/[0.09] text-white font-medium' : 'text-white/45 hover:bg-white/[0.04]')}><ListTodo className="size-3.5" /> Tasks</button>
                  <button type="button" onClick={() => setRightPanelTab('configure')} className={'flex items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] ' + (rightPanelTab === 'configure' ? 'bg-white/[0.09] text-white font-medium' : 'text-white/45 hover:bg-white/[0.04]')}><Settings2 className="size-3.5" /> Settings</button>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto p-3">
                  {rightPanelTab === 'chats' && (
                    <div className="space-y-1">
                      <Link href="/app/assistant" onClick={() => setRightPanelOpen(false)} className="mb-3 flex items-center gap-2 rounded-xl border border-[#78e565]/25 bg-[#78e565]/[0.07] px-3 py-2 text-xs font-medium text-[#a3f194]"><Plus className="size-4" /> Start a new conversation</Link>
                      {recentChats.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-white/10 px-3 py-8 text-center"><MessageSquare className="mx-auto mb-2 size-5 text-white/30" /><p className="text-xs text-white/65">No saved conversations yet</p><p className="mt-1 text-[11px] text-white/35">Your conversations appear here after you send a message.</p></div>
                      ) : recentChats.map((chat) => (
                        <Link key={chat.key} href={chat.thread === 'orchestrator' ? '/app/assistant?agent=orchestrator' : '/app/assistant?agent=' + encodeURIComponent(chat.thread)} onClick={() => setRightPanelOpen(false)} className="group block rounded-xl px-3 py-2.5 hover:bg-white/[0.055]">
                          <span className="flex items-start gap-2"><MessageSquare className="mt-0.5 size-3.5 shrink-0 text-white/35" /><span className="min-w-0 flex-1"><span className="block break-words text-xs leading-5 text-white/80 group-hover:text-white">{chat.title}</span><span className="mt-0.5 block text-[10px] text-white/35">{chat.updatedAt ? new Date(chat.updatedAt).toLocaleDateString() : 'Saved conversation'}</span></span></span>
                        </Link>
                      ))}
                    </div>
                  )}
                  {rightPanelTab === 'tasks' && (
                    <div className="space-y-2.5">
                      <Link href="/app/automations" onClick={() => setRightPanelOpen(false)} className="flex items-center justify-between rounded-xl border border-white/[0.09] px-3 py-2.5 hover:bg-white/[0.04]"><span className="flex items-center gap-2 text-xs text-white/75"><Workflow className="size-4 text-[#8be977]" /> Workflows</span><span className="text-[10px] text-white/35">Open</span></Link>
                      <Link href="/app/approvals" onClick={() => setRightPanelOpen(false)} className="flex items-center justify-between rounded-xl border border-white/[0.09] px-3 py-2.5 hover:bg-white/[0.04]"><span className="flex items-center gap-2 text-xs text-white/75"><ShieldCheck className="size-4 text-[#8be977]" /> Pending approvals</span><span className="text-[10px] text-white/35">Review</span></Link>
                      <div className="px-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/35">Recent activity</div>
                      {workspace.timeline.length === 0 ? <div className="rounded-xl border border-dashed border-white/10 px-3 py-6 text-center"><Clock3 className="mx-auto mb-2 size-5 text-white/30" /><p className="text-xs text-white/60">No recent activity</p></div> : workspace.timeline.slice(0, 10).map((item: any, index: number) => <div key={item.id || item.event_id || index} className="rounded-xl border border-white/[0.07] px-3 py-2.5"><div className="flex items-start gap-2"><CheckCircle2 className="mt-0.5 size-3.5 shrink-0 text-[#8be977]" /><div className="min-w-0"><p className="break-words text-xs text-white/75">{item.title || item.message || item.action || item.event_type || 'Workspace event'}</p><p className="mt-0.5 text-[10px] text-white/35">{item.created_at || item.timestamp || item.status || 'Activity record'}</p></div></div></div>)}
                    </div>
                  )}
                  {rightPanelTab === 'configure' && (
                    <div className="space-y-2">
                      <p className="mb-2 text-xs leading-5 text-white/45">Quick access to workspace management.</p>
                      {[
                        { title: 'AI agents', description: 'Instructions, role and agent versions', href: '/app/agents', icon: Bot },
                        { title: 'Models & providers', description: 'Connected AI providers and models', href: '/app/settings/integrations', icon: Sparkles },
                        { title: 'Tools & integrations', description: 'Connections available to your workspace', href: '/app/settings/integrations', icon: Globe2 },
                        { title: 'Knowledge & context', description: 'Shared company knowledge and sources', href: '/app/knowledge', icon: FileText },
                        { title: 'Permissions & approvals', description: 'Review governed actions and access', href: '/app/approvals', icon: ShieldCheck },
                      ].map(({ title, description, href, icon: Icon }) => <Link key={title} href={href} onClick={() => setRightPanelOpen(false)} className="flex items-start gap-3 rounded-xl border border-white/[0.08] p-2.5 transition hover:bg-white/[0.04]"><Icon className="mt-0.5 size-4 shrink-0 text-[#8be977]" /><span><span className="block text-xs font-medium text-white/85">{title}</span><span className="mt-0.5 block text-[11px] leading-4 text-white/40">{description}</span></span></Link>)}
                    </div>
                  )}
                </div>
              </aside>
            </>
          )}
        </div>
      </section>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} profile={workspace.userProfile} />
    </div>
  );
}

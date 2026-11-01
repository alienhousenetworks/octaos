'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useInterfaceMode } from '@/lib/interface-mode';
import { useWorkspace } from '@/lib/workspace';
import { AgentItem } from '@/lib/agent-types';
import CommandPalette from '@/components/shell/command-palette';
import {
  Bot,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Plus,
  Search,
  Settings2,
  Sparkles,
  X,
  Clock,
  Trash2,
  Cpu,
} from 'lucide-react';

interface AIWorkspaceShellProps {
  children: React.ReactNode;
  accountLabel?: string;
}

interface RecentThread {
  key: string;
  threadId: string;
  title: string;
  agentSlug?: string;
  updatedAt: number;
}

const BUILTIN_SPECIALISTS = [
  {
    slug: 'orchestrator',
    name: 'General Orchestrator',
    role: 'Autonomous Coordinator',
    department: 'Executive',
    color: '#34d399',
    kind: 'crown',
    href: '/app/assistant',
  },
  {
    slug: 'sales_ai',
    name: 'Sales Specialist',
    role: 'Pipeline & Lead Research',
    department: 'Sales',
    color: '#22c55e',
    kind: 'tie',
    href: '/app/sales',
  },
  {
    slug: 'marketing_ai',
    name: 'Marketing Specialist',
    role: 'Campaigns & Creative Copy',
    department: 'Marketing',
    color: '#38bdf8',
    kind: 'horn',
    href: '/app/campaigns',
  },
  {
    slug: 'support_ai',
    name: 'Support Specialist',
    role: 'Customer QA & Ticketing',
    department: 'Support',
    color: '#c084fc',
    kind: 'headset',
    href: '/app/support',
  },
  {
    slug: 'hr_ai',
    name: 'People & HR Specialist',
    role: 'Hiring & People Operations',
    department: 'People',
    color: '#fbbf24',
    kind: 'glasses',
    href: '/app/hr',
  },
  {
    slug: 'ceo_ai',
    name: 'CEO & Strategy',
    role: 'Objectives & Governance',
    department: 'Strategy',
    color: '#fb7185',
    kind: 'hat',
    href: '/app/ceo',
  },
];

const OCTO_PROPS: Record<string, React.ReactNode> = {
  crown: <path d="M7 6l2-3 3 2 3-2 2 3z" fill="#fde047" />,
  tie: <path d="M12 16l-1.5 1.5 1.5 4 1.5-4z" fill="#1e293b" />,
  horn: <path d="M17 6l4-2v5l-4-2z" fill="#f1f5f9" />,
  headset: <path d="M5 12a7 7 0 0114 0" fill="none" stroke="#e2e8f0" strokeWidth="1.5" />,
  glasses: <g fill="none" stroke="#1e293b" strokeWidth="1"><circle cx="9.5" cy="11" r="2" /><circle cx="14.5" cy="11" r="2" /></g>,
  hat: <path d="M8 6h8v-4H8zM6 6h12v1H6z" fill="#1e293b" />,
  none: null,
};

// Small SVG octopus; `kind` picks its accessory so each specialist looks different.
function Octopus({ color, kind = 'none' }: { color: string; kind?: string }) {
  return (
    <svg viewBox="0 0 24 24" className="size-5 shrink-0" aria-hidden>
      <path d="M4 12a8 8 0 0116 0v3c0 1-1 2-2 1.5-1 2-3 2-3.5 0-.5 2-3.5 2-4 0-.5 2-2.5 2-3.5 0C5 17 4 16 4 15z" fill={color} />
      {OCTO_PROPS[kind]}
      <circle cx="9.5" cy="11" r="1.1" fill="#0c0f13" />
      <circle cx="14.5" cy="11" r="1.1" fill="#0c0f13" />
    </svg>
  );
}

// Stable color for custom agents.
const CUSTOM_COLORS = ['#f97316', '#2dd4bf', '#a3e635', '#f472b6', '#818cf8'];
const colorFor = (key: string) =>
  CUSTOM_COLORS[[...key].reduce((n, ch) => n + ch.charCodeAt(0), 0) % CUSTOM_COLORS.length];

export default function AIWorkspaceShell({ children, accountLabel }: AIWorkspaceShellProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { setMode } = useInterfaceMode();
  const workspace = useWorkspace();

  const [requestedAgent, setRequestedAgent] = useState('');
  const [navOpen, setNavOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [recentThreads, setRecentThreads] = useState<RecentThread[]>([]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    const syncAgent = () => {
      setRequestedAgent(new URLSearchParams(window.location.search).get('agent') || '');
    };
    syncAgent();
    setNavOpen(false);
    window.addEventListener('popstate', syncAgent);
    window.addEventListener('octaos-agent-query', syncAgent);
    return () => {
      window.removeEventListener('popstate', syncAgent);
      window.removeEventListener('octaos-agent-query', syncAgent);
    };
  }, [pathname, searchParams]);

  // Load Agents
  useEffect(() => {
    if (!workspace.token) return;
    let active = true;
    setAgentsLoading(true);
    workspace
      .fetchWithAuth(`${workspace.apiUrl}/dashboard/agents`)
      .then(async (res) => {
        if (!res.ok) return;
        const data = await res.json();
        if (active && Array.isArray(data)) setAgents(data);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setAgentsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [workspace.token, workspace.apiUrl, workspace.fetchWithAuth]);

  // Load Recent Threads from LocalStorage
  const loadRecentThreads = () => {
    try {
      const tenantKey = String(workspace.tenantId || 'default');
      const prefix1 = `octaos-assistant-thread:${tenantKey}:`;
      const prefix2 = `octaos-universal-assistant-messages:${tenantKey}:`;
      const threads: RecentThread[] = [];

      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key) continue;
        let threadId = '';
        if (key.startsWith(prefix1)) {
          threadId = key.slice(prefix1.length);
        } else if (key.startsWith(prefix2)) {
          threadId = key.slice(prefix2.length);
        } else {
          continue;
        }

        try {
          const raw = localStorage.getItem(key);
          const messages = JSON.parse(raw || '[]');
          if (!Array.isArray(messages) || messages.length === 0) continue;

          const firstUser = messages.find(
            (m: any) => m.role === 'user' && typeof m.content === 'string' && m.content.trim()
          );
          const latest = messages[messages.length - 1];
          const title = firstUser
            ? String(firstUser.content).replace(/\s+/g, ' ').slice(0, 48)
            : `Session with ${threadId}`;

          threads.push({
            key,
            threadId,
            title,
            agentSlug: threadId,
            updatedAt: Date.parse(latest?.createdAt || firstUser?.createdAt || '') || Date.now(),
          });
        } catch {}
      }

      threads.sort((a, b) => b.updatedAt - a.updatedAt);
      setRecentThreads(threads.slice(0, 20));
    } catch {
      setRecentThreads([]);
    }
  };

  useEffect(() => {
    loadRecentThreads();
  }, [pathname, workspace.tenantId]);

  const deleteThread = (key: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      localStorage.removeItem(key);
      loadRecentThreads();
    } catch {}
  };

  const query = search.trim().toLowerCase();

  // Combine custom agents that are not built-in
  const customAgents = agents.filter(
    (a) => !BUILTIN_SPECIALISTS.some((b) => b.slug === a.slug || b.name === a.name)
  );

  const filteredBuiltins = BUILTIN_SPECIALISTS.filter(
    (b) =>
      !query ||
      b.name.toLowerCase().includes(query) ||
      b.role.toLowerCase().includes(query) ||
      b.department.toLowerCase().includes(query)
  );

  const filteredCustom = customAgents.filter(
    (a) =>
      !query ||
      a.name.toLowerCase().includes(query) ||
      (a.role || '').toLowerCase().includes(query) ||
      (a.department || '').toLowerCase().includes(query)
  );

  const isBuiltinActive = (item: (typeof BUILTIN_SPECIALISTS)[0]) => {
    if (pathname === item.href) return true;
    if (pathname === '/app/assistant') {
      if (item.slug === 'orchestrator' && (!requestedAgent || requestedAgent === 'orchestrator')) return true;
      if (requestedAgent === item.slug) return true;
    }
    return false;
  };

  const navContent = (
    <div className="flex h-full min-h-0 flex-col bg-[#0c0f13] text-white/90 select-none">
      {/* Workspace Header */}
      <div className="flex h-14 shrink-0 items-center gap-2.5 border-b border-white/[0.08] px-4 bg-[#10141a]">
        <div className="flex size-7 items-center justify-center rounded-lg bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/25">
          <Sparkles className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-xs font-semibold tracking-tight text-white">OctaOS</span>
            <span className="rounded-full bg-[#10b981]/15 border border-[#10b981]/30 px-1.5 py-0.2 text-[9px] font-mono text-[#34d399]">
              LIVE
            </span>
          </div>
          <p className="truncate text-[10px] text-white/40">Multi-Agent Workstation</p>
        </div>
      </div>

      {/* Action Strip: New Session & Studio */}
      <div className="flex items-center gap-2 p-3">
        <Link
          href="/app/assistant"
          onClick={() => setNavOpen(false)}
          className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#10b981] px-3 text-xs font-semibold text-black transition hover:bg-[#34d399]"
        >
          <Plus className="size-3.5" />
          <span>New Session</span>
        </Link>
        <Link
          href="/app/agents"
          onClick={() => setNavOpen(false)}
          title="Open Agent Studio"
          className="flex size-8 items-center justify-center rounded-lg border border-white/10 text-white/60 hover:bg-white/[0.06] hover:text-white transition"
        >
          <Bot className="size-4" />
        </Link>
      </div>

      {/* Search Input */}
      <div className="px-3 pb-2">
        <label className="flex h-8 items-center gap-2 rounded-lg border border-white/[0.08] bg-[#141920] px-2.5 text-xs text-white/45 focus-within:border-[#10b981]/50">
          <Search className="size-3.5 shrink-0 text-white/40" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter specialists & threads..."
            className="min-w-0 flex-1 bg-transparent text-xs text-white outline-none placeholder:text-white/30"
          />
        </label>
      </div>

      {/* Scrollable Specialists & Recent Conversations */}
      <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-2 space-y-4">
        {/* SPECIALIST ROSTER */}
        <div>
          <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-white/35">
            AI Specialists
          </div>
          <nav className="space-y-0.5">
            {filteredBuiltins.map((item) => {
              const active = isBuiltinActive(item);
                            return (
                <Link
                  key={item.slug}
                  href={item.href}
                  onClick={() => setNavOpen(false)}
                  className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs transition ${
                    active
                      ? 'bg-white/[0.07] text-white font-medium'
                      : 'text-white/65 hover:bg-white/[0.04] hover:text-white'
                  }`}
                >
                  <Octopus color={item.color} kind={item.kind} />
                  <div className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-[11px]">{item.name}</span>
                  </div>
                  
                </Link>
              );
            })}

            {/* Custom Agents */}
            {filteredCustom.map((agent) => {
              const href = `/app/assistant?agent=${encodeURIComponent(agent.slug || agent.id)}`;
              const active = requestedAgent === agent.slug || requestedAgent === agent.id;
              return (
                <Link
                  key={agent.id}
                  href={href}
                  onClick={() => setNavOpen(false)}
                  className={`group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs transition ${
                    active
                      ? 'bg-white/[0.07] text-white font-medium'
                      : 'text-white/65 hover:bg-white/[0.04] hover:text-white'
                  }`}
                >
                  <Octopus color={colorFor(agent.slug || agent.id)} />
                  <div className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-[11px]">{agent.name}</span>
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* RECENT SESSIONS & THREADS */}
        <div>
          <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-white/35">
            Recent Sessions ({recentThreads.length})
          </div>
          {recentThreads.length === 0 ? (
            <p className="px-2.5 text-[11px] text-white/30 italic">No previous sessions found</p>
          ) : (
            <div className="space-y-0.5">
              {recentThreads.map((thread) => (
                <div
                  key={thread.key}
                  onClick={() => {
                    setNavOpen(false);
                    router.push(
                      thread.threadId === 'orchestrator'
                        ? '/app/assistant?agent=orchestrator'
                        : `/app/assistant?agent=${encodeURIComponent(thread.threadId)}`
                    );
                  }}
                  className="group flex cursor-pointer items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-xs text-white/65 hover:bg-white/[0.04] hover:text-white transition"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <MessageSquare className="size-3.5 shrink-0 text-white/35 group-hover:text-[#34d399]" />
                    <span className="truncate text-[11px]">{thread.title}</span>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => deleteThread(thread.key, e)}
                    title="Delete thread"
                    className="opacity-0 group-hover:opacity-100 rounded p-1 text-white/30 hover:text-rose-400 hover:bg-white/[0.06] transition"
                  >
                    <Trash2 className="size-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* FOOTER: User profile + Switch to Classic Mode */}
      <div className="border-t border-white/[0.08] p-3 bg-[#10141a]">
        <div className="mb-2 flex items-center gap-2 rounded-lg bg-white/[0.03] p-2 border border-white/[0.06]">
          <div className="flex size-6 items-center justify-center rounded-full bg-[#10b981]/20 text-[10px] font-bold text-[#34d399]">
            {(accountLabel || 'U').slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-white/85">{accountLabel || 'User Workspace'}</p>
          </div>
          <Link
            href="/app/settings"
            title="Settings"
            className="text-white/40 hover:text-white transition"
          >
            <Settings2 className="size-3.5" />
          </Link>
        </div>

        {/* Clean Switch to Classic Button */}
        <button
          type="button"
          onClick={() => setMode('classic')}
          className="flex h-8 w-full items-center justify-center gap-2 rounded-lg border border-white/10 text-xs text-white/70 transition hover:bg-white/[0.06] hover:text-white"
        >
          <LayoutDashboard className="size-3.5" />
          <span>Switch to Classic Mode</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-[100dvh] min-h-0 overflow-hidden bg-[#090b0e] text-[#f4f6f3]">
      {/* DESKTOP SIDEBAR */}
      <aside className="hidden w-[240px] shrink-0 border-r border-white/[0.08] md:flex flex-col">
        {navContent}
      </aside>

      {/* MOBILE DRAWER */}
      {navOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setNavOpen(false)}
          />
          <aside className="relative flex h-full w-[260px] flex-col border-r border-white/[0.08] bg-[#0c0f13] shadow-2xl">
            <button
              type="button"
              onClick={() => setNavOpen(false)}
              className="absolute top-3.5 right-3 z-10 rounded-md p-1 text-white/40 hover:text-white"
            >
              <X className="size-4" />
            </button>
            {navContent}
          </aside>
        </div>
      )}

      {/* MAIN WORKSTATION STAGE */}
      <section className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
        {children}
      </section>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} profile={workspace.userProfile} />
    </div>
  );
}

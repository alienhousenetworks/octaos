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
    color: '#2dd4bf',
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
      <circle cx="9.5" cy="11" r="1.1" fill="#0d1116" />
      <circle cx="14.5" cy="11" r="1.1" fill="#0d1116" />
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
      .catch(() => { })
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
        } catch { }
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
    } catch { }
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
    <div className="flex h-full min-h-0 flex-col bg-[#0d1116] text-foreground select-none">
      {/* Workspace Header */}
      <div className="flex h-14 shrink-0 items-center gap-2.5 border-b border-[#1d2530] px-4 bg-[#11161c]">
        <div className="flex size-7 items-center justify-center rounded-md bg-[#e5a93c]/12 text-[#e5a93c] border border-[#e5a93c]/30">
          <Sparkles className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="truncate font-heading text-xs font-semibold tracking-tight text-foreground">OctaOS</span>
            <span className="rounded-md bg-[#2dd4bf]/12 border border-[#2dd4bf]/30 px-1.5 py-0.2 text-[10px] font-mono text-[#2dd4bf]">
              Live
            </span>
          </div>
          <p className="truncate text-[11px] text-muted-foreground">AI Workstation</p>
        </div>
      </div>

      {/* Action Strip: New Session & Studio */}
      <div className="flex items-center gap-2 p-3">
        <Link
          href="/app/assistant"
          onClick={() => setNavOpen(false)}
          className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-md bg-[#e5a93c] px-3 text-xs font-semibold text-[#0a0d10] transition hover:bg-[#f0bc5e]"
        >
          <Plus className="size-3.5" />
          <span>New session</span>
        </Link>
        <Link
          href="/app/agents"
          onClick={() => setNavOpen(false)}
          title="Open Agent Studio"
          className="flex size-8 items-center justify-center rounded-md border border-[#222b36] text-muted-foreground hover:bg-[#171e26] hover:text-foreground transition"
        >
          <Bot className="size-4" />
        </Link>
      </div>

      {/* Search Input */}
      <div className="px-3 pb-2">
        <label className="flex h-8 items-center gap-2 rounded-md border border-[#222b36] bg-[#0a0d10] px-2.5 text-xs text-muted-foreground focus-within:border-[#e5a93c]">
          <Search className="size-3.5 shrink-0 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter specialists & threads..."
            className="min-w-0 flex-1 bg-transparent text-xs text-foreground outline-none placeholder:text-[#647182]"
          />
        </label>
      </div>

      {/* Scrollable Specialists & Recent Conversations */}
      <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-2 space-y-4">
        {/* SPECIALIST ROSTER */}
        <div>
          <div className="px-2 pb-1.5 text-xs font-medium text-muted-foreground">
            Specialists
          </div>
          <nav className="space-y-0.5">
            {filteredBuiltins.map((item) => {
              const active = isBuiltinActive(item);
              return (
                <Link
                  key={item.slug}
                  href={item.href}
                  onClick={() => setNavOpen(false)}
                  className={`group flex items-center gap-2.5 rounded-md border px-2.5 py-2 text-xs transition ${active
                    ? 'border-[#e5a93c]/30 bg-[#171e26] text-foreground font-medium'
                    : 'border-transparent text-muted-foreground hover:bg-[#171e26] hover:text-foreground'
                    }`}
                >
                  <Octopus color={item.color} kind={item.kind} />
                  <div className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-[12px]">{item.name}</span>
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
                  className={`group flex items-center gap-2.5 rounded-md border px-2.5 py-2 text-xs transition ${active
                    ? 'border-[#e5a93c]/30 bg-[#171e26] text-foreground font-medium'
                    : 'border-transparent text-muted-foreground hover:bg-[#171e26] hover:text-foreground'
                    }`}
                >
                  <Octopus color={colorFor(agent.slug || agent.id)} />
                  <div className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-[12px]">{agent.name}</span>
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* RECENT SESSIONS & THREADS */}
        <div>
          <div className="px-2 pb-1.5 text-xs font-medium text-muted-foreground">
            Recent sessions ({recentThreads.length})
          </div>
          {recentThreads.length === 0 ? (
            <p className="px-2.5 text-xs text-[#647182]">No previous sessions yet</p>
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
                  className="group flex cursor-pointer items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-[#171e26] hover:text-foreground transition"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <MessageSquare className="size-3.5 shrink-0 text-[#647182] group-hover:text-[#e5a93c]" />
                    <span className="truncate text-[12px]">{thread.title}</span>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => deleteThread(thread.key, e)}
                    title="Delete thread"
                    className="opacity-0 group-hover:opacity-100 rounded p-1 text-[#647182] hover:text-destructive hover:bg-[#222b36] transition"
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
      <div className="border-t border-[#1d2530] p-3 bg-[#11161c]">
        <div className="mb-2 flex items-center gap-2 rounded-md bg-[#0a0d10] p-2 border border-[#222b36]">
          <div className="flex size-6 items-center justify-center rounded-md bg-[#e5a93c]/15 text-[11px] font-bold text-[#e5a93c]">
            {(accountLabel || 'U').slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-foreground">{accountLabel || 'User Workspace'}</p>
          </div>
          <Link
            href="/app/settings"
            title="Settings"
            className="text-muted-foreground hover:text-foreground transition"
          >
            <Settings2 className="size-3.5" />
          </Link>
        </div>

        {/* Clean Switch to Classic Button */}
        <button
          type="button"
          onClick={() => setMode('classic')}
          className="flex h-8 w-full items-center justify-center gap-2 rounded-md border border-[#222b36] text-xs text-muted-foreground transition hover:bg-[#171e26] hover:text-foreground"
        >
          <LayoutDashboard className="size-3.5" />
          <span>Switch to Classic Mode</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="ai-shell flex h-[100dvh] min-h-0 overflow-hidden bg-[#0a0d10] text-[#f4f6f3]">
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
          <aside className="relative flex h-full w-[260px] flex-col border-r border-white/[0.08] bg-[#0d1116] shadow-2xl">
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

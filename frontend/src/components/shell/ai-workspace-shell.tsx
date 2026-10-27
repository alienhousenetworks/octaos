'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ArrowUp, Bot, ChevronDown, CircleHelp, FileText,
  FolderKanban, Globe2, LayoutDashboard, MessageSquare,
  Plus, Search, Settings2, ShieldCheck, Sparkles, Workflow, X
} from 'lucide-react';

export default function AIWorkspaceShell({ children, accountLabel }: { children: React.ReactNode; accountLabel?: string }) {
  const pathname = usePathname();
  const [contextOpen, setContextOpen] = useState(true);
  const [search, setSearch] = useState('');
  const links = [
    { href: '/app/agents', label: 'Agent Studio', icon: Bot },
    { href: '/app/knowledge', label: 'Knowledge', icon: FileText },
    { href: '/app/automations', label: 'Workflows', icon: Workflow },
    { href: '/app/settings/integrations', label: 'Integrations', icon: Globe2 },
  ];
  const conversations = [
    { label: 'General assistant', href: '/app/assistant' },
    { label: 'Marketing workspace', href: '/app/campaigns' },
    { label: 'Sales workspace', href: '/app/sales' },
    { label: 'Support workspace', href: '/app/support' },
  ].filter((item) => item.label.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="ai-workspace-shell flex h-[100dvh] min-h-0 overflow-hidden bg-[#0b0d0c] text-[#f4f6f3]">
      <aside className="flex w-[248px] shrink-0 flex-col border-r border-white/[0.08] bg-[#101311] max-lg:w-[218px] max-md:hidden">
        <div className="flex h-[68px] items-center gap-3 border-b border-white/[0.08] px-5">
          <div className="flex size-9 items-center justify-center rounded-xl bg-[#1b2a1d] text-[#82ee70]"><Sparkles className="size-5" /></div>
          <div className="min-w-0"><div className="truncate text-sm font-semibold tracking-tight">OctaOS</div><div className="text-[11px] text-white/45">AI Workspace</div></div>
          <span className="ml-auto rounded-full border border-[#70d95e]/20 bg-[#70d95e]/10 px-2 py-0.5 text-[10px] text-[#8bed78]">AI</span>
        </div>
        <div className="flex gap-2 px-3 pt-4">
          <Link href="/app/assistant" className="flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-[#78e565] px-3 text-sm font-semibold text-[#0b1609] transition hover:bg-[#91f280]"><Plus className="size-4" /> New chat</Link>
          <Link href="/app/agents" aria-label="Open Agent Studio" title="Open Agent Studio" className="flex size-10 items-center justify-center rounded-xl border border-white/10 text-white/70 hover:bg-white/[0.06]"><Bot className="size-4" /></Link>
        </div>
        <div className="px-3 pt-4">
          <label className="flex h-9 items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 text-white/45 focus-within:border-[#78e565]/40"><Search className="size-4 shrink-0" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search workspaces" aria-label="Search workspaces" className="min-w-0 flex-1 bg-transparent text-xs text-white outline-none placeholder:text-white/35" /></label>
        </div>
        <div className="px-4 pb-2 pt-6 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">Workspace</div>
        <nav className="space-y-1 px-2.5">
          {links.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={'flex h-10 items-center gap-3 rounded-xl px-3 text-[13px] transition ' + (pathname === href || pathname.startsWith(href + '/') ? 'bg-white/[0.08] text-white' : 'text-white/60 hover:bg-white/[0.05] hover:text-white')}><Icon className="size-4 text-[#8be977]" />{label}</Link>)}
        </nav>
        <div className="px-4 pb-2 pt-7 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">Jump back in</div>
        <nav className="space-y-1 px-2.5">
          {conversations.map((item) => <Link key={item.href} href={item.href} className={'flex min-h-10 items-center gap-3 rounded-xl px-3 py-2 text-[12px] ' + (pathname === item.href ? 'bg-[#1b241c] text-white' : 'text-white/55 hover:bg-white/[0.05] hover:text-white')}><MessageSquare className="size-4 shrink-0 text-white/40" /><span className="truncate">{item.label}</span></Link>)}
          {conversations.length === 0 && <p className="px-3 py-2 text-xs text-white/40">No matching workspaces</p>}
        </nav>
        <div className="mt-auto border-t border-white/[0.08] p-3">
          <div className="mb-3 flex items-center gap-2 rounded-xl bg-white/[0.035] p-2.5"><div className="flex size-8 items-center justify-center rounded-full bg-[#29352b] text-xs font-semibold text-[#a4f196]">{(accountLabel || 'U').slice(0,1).toUpperCase()}</div><div className="min-w-0 flex-1"><div className="truncate text-xs font-medium">{accountLabel || 'Your workspace'}</div><div className="text-[10px] text-white/40">Current organization</div></div><Settings2 className="size-4 text-white/40" /></div>
          <button type="button" onClick={() => { localStorage.setItem('octaos-interface-mode', 'classic'); window.location.assign('/app/home'); }} className="flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-white/10 text-xs text-white/70 transition hover:bg-white/[0.06] hover:text-white"><LayoutDashboard className="size-4" /> Switch to Classic</button>
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[68px] shrink-0 items-center gap-3 border-b border-white/[0.08] bg-[#0d100e] px-5 md:px-7">
          <div className="flex size-9 items-center justify-center rounded-xl border border-[#7de56b]/20 bg-[#172219] text-[#83eb70]"><Bot className="size-4" /></div>
          <div className="min-w-0"><h1 className="text-sm font-semibold">OctaOS AI Assistant</h1><p className="text-[11px] text-white/45">Research, plan and coordinate work</p></div>
          <div className="ml-auto flex items-center gap-2"><span className="hidden items-center gap-1.5 rounded-full border border-white/[0.08] px-2.5 py-1 text-[10px] text-white/50 sm:inline-flex"><span className="size-1.5 rounded-full bg-[#82e96e]" /> Workspace ready</span><button type="button" onClick={() => setContextOpen(!contextOpen)} className="flex h-9 items-center gap-2 rounded-lg border border-white/10 px-3 text-xs text-white/70 hover:bg-white/[0.05]" aria-expanded={contextOpen}><Settings2 className="size-4" /><span className="hidden sm:inline">Context</span><ChevronDown className={'size-3 transition ' + (contextOpen ? 'rotate-180' : '')} /></button></div>
        </header>
        <div className="flex min-h-0 flex-1">
          <main className="ai-workspace-chat min-w-0 flex-1 overflow-y-auto px-3 py-4 sm:px-5 md:px-8 md:py-6"><div className="mx-auto w-full max-w-[1050px]">{children}</div></main>
          {contextOpen && <aside className="w-[270px] shrink-0 overflow-y-auto border-l border-white/[0.08] bg-[#101311] px-4 py-5 max-xl:w-[238px] max-lg:hidden">
            <div className="mb-5 flex items-center justify-between"><h2 className="text-sm font-semibold">Context & tools</h2><button type="button" aria-label="Close context panel" onClick={() => setContextOpen(false)} className="rounded-md p-1 text-white/40 hover:bg-white/[0.06] hover:text-white"><X className="size-4" /></button></div>
            <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-3"><div className="mb-2 flex items-center gap-2 text-xs font-medium"><Sparkles className="size-4 text-[#8be977]" /> Assistant</div><p className="text-[11px] leading-5 text-white/45">General OctaOS orchestration assistant. Available actions depend on your organization permissions and configured services.</p></div>
            <div className="mb-2 mt-6 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/35">Work tools</div>
            <div className="space-y-1">{links.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className="flex items-center gap-3 rounded-lg px-2.5 py-2.5 text-xs text-white/65 transition hover:bg-white/[0.05] hover:text-white"><Icon className="size-4 text-[#8be977]" /><span className="flex-1">{label}</span><ArrowUp className="size-3 rotate-45 text-white/25" /></Link>)}</div>
            <div className="mb-2 mt-6 text-[10px] font-semibold uppercase tracking-[0.14em] text-white/35">Governance</div>
            <Link href="/app/approvals" className="flex items-start gap-3 rounded-xl border border-white/[0.08] p-3 hover:bg-white/[0.035]"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-[#8be977]" /><span><span className="block text-xs font-medium">Approvals</span><span className="mt-1 block text-[11px] leading-4 text-white/40">Review actions that require authorization.</span></span></Link>
            <Link href="/app/knowledge" className="mt-2 flex items-start gap-3 rounded-xl border border-white/[0.08] p-3 hover:bg-white/[0.035]"><FolderKanban className="mt-0.5 size-4 shrink-0 text-[#8be977]" /><span><span className="block text-xs font-medium">Knowledge & files</span><span className="mt-1 block text-[11px] leading-4 text-white/40">Open authorized company knowledge.</span></span></Link>
            <div className="mt-6 rounded-xl bg-[#172019] p-3"><div className="flex items-center gap-2 text-xs font-medium text-[#a3f194]"><CircleHelp className="size-4" /> Connected capabilities</div><p className="mt-2 text-[11px] leading-5 text-white/50">Check Integrations for provider configuration. This panel does not assume that an unconfigured service is connected.</p><Link href="/app/settings/integrations" className="mt-2 inline-flex text-xs text-[#a3f194] hover:underline">Manage integrations →</Link></div>
          </aside>}
        </div>
      </section>
    </div>
  );
}

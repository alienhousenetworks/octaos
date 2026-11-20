'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowRight,
  Check,
  ChevronRight,
  CircleDot,
  Command,
  LockKeyhole,
  Network,
  ShieldCheck,
  Sparkles,
  Waypoints,
} from 'lucide-react';
import { getAccessToken } from '@/lib/auth-session';
import { HanddrawnLoopDiagram } from '@/components/handdraw/handdraw-illustrations';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

type AgentKey = 'orchestrator' | 'revenue' | 'care' | 'people';

const agents: Array<{
  id: AgentKey;
  name: string;
  role: string;
  description: string;
  action: string;
  color: string;
}> = [
  {
    id: 'orchestrator',
    name: 'Atlas',
    role: 'Operations orchestrator',
    description: 'Turns a business intent into an accountable plan with owners, dependencies, and evidence.',
    action: 'Planning a launch sequence',
    color: 'mint',
  },
  {
    id: 'revenue',
    name: 'Relay',
    role: 'Revenue operations',
    description: 'Qualifies signals, prepares outreach, and keeps every customer-facing action inside policy.',
    action: 'Triaging 18 high-intent accounts',
    color: 'blue',
  },
  {
    id: 'care',
    name: 'Harbor',
    role: 'Customer operations',
    description: 'Resolves repeatable support work from governed knowledge and routes exceptions to people.',
    action: 'Resolving a shipping exception',
    color: 'amber',
  },
  {
    id: 'people',
    name: 'Northstar',
    role: 'People operations',
    description: 'Moves candidates and employee requests forward while preserving permissions and audit trails.',
    action: 'Preparing an interview brief',
    color: 'violet',
  },
];

function navigate(router: ReturnType<typeof useRouter>, path: '/login' | '/signup') {
  router.push(path);
}

export default function LandingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [activeAgent, setActiveAgent] = useState<AgentKey>('orchestrator');

  useEffect(() => {
    const invite = searchParams.get('token');
    if (invite) {
      router.replace(`/signup?token=${encodeURIComponent(invite)}`);
      return;
    }
    if (getAccessToken()) router.replace('/app/home');
  }, [router, searchParams]);

  useEffect(() => {
    fetch(`${API_URL}/auth/settings`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data?.logo_url) setLogoUrl(data.logo_url);
      })
      .catch(() => undefined);
  }, []);

  const selectedAgent = agents.find((agent) => agent.id === activeAgent) ?? agents[0];

  return (
    <main className="landing-page min-h-screen overflow-hidden bg-[#0a0d10] text-[#eceff4]">
      <header className="landing-header mx-auto flex max-w-[1360px] items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
        <a href="#top" className="flex items-center gap-3" aria-label="OctaOS home">
          {logoUrl ? (
            <img src={logoUrl} alt="OctaOS" className="h-8 w-auto max-w-[150px] object-contain" />
          ) : (
            <span className="landing-mark"><CircleDot className="size-4" /></span>
          )}
          <span className="font-heading text-[15px] font-semibold tracking-[-0.02em]">OctaOS</span>
        </a>
        <nav className="hidden items-center gap-8 text-[13px] text-[#8b98a8] md:flex" aria-label="Marketing">
          <a href="#operating-model" className="transition-colors hover:text-white">Operating model</a>
          <a href="#workforce" className="transition-colors hover:text-white">AI workforce</a>
          <a href="#trust" className="transition-colors hover:text-white">Trust center</a>
        </nav>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => navigate(router, '/login')} className="landing-quiet-button hidden sm:inline-flex">Sign in</button>
          <button type="button" onClick={() => navigate(router, '/signup')} className="landing-primary-button">Open workspace <ArrowRight className="size-3.5" /></button>
        </div>
      </header>

      <section id="top" className="landing-hero mx-auto grid max-w-[1360px] gap-14 px-5 pb-24 pt-16 sm:px-8 lg:grid-cols-[minmax(0,1.02fr)_minmax(430px,.98fr)] lg:items-center lg:px-12 lg:pb-32 lg:pt-24">
        <div>
          <div className="landing-kicker"><span className="landing-live-dot" /> Governed AI operations for enterprise teams</div>
          <h1 className="mt-6 max-w-[730px] text-[clamp(3.1rem,6.5vw,5.8rem)] font-semibold leading-[.96] tracking-[-0.045em] text-[#eceff4]">
            Intent in. Accountability out.
          </h1>
          <p className="mt-7 max-w-[590px] text-[17px] leading-8 text-[#8b98a8] sm:text-[18px]">
            OctaOS gives enterprise teams a controlled way to turn goals into work, coordinate AI specialists, and verify the evidence behind every outcome.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <button type="button" onClick={() => navigate(router, '/signup')} className="landing-primary-button h-11 justify-center px-5 text-[14px]">Build your operating layer <ArrowRight className="size-4" /></button>
            <a href="#workforce" className="landing-secondary-button h-11 justify-center px-5 text-[14px]">See the control room <ChevronRight className="size-4" /></a>
          </div>
          <div className="mt-9 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#8b98a8]">
            <span className="flex items-center gap-2"><Check className="size-3.5 text-[#2dd4bf]" /> Tenant-isolated by default</span>
            <span className="flex items-center gap-2"><Check className="size-3.5 text-[#2dd4bf]" /> Human approval for risk</span>
            <span className="flex items-center gap-2"><Check className="size-3.5 text-[#2dd4bf]" /> Full execution trace</span>
          </div>
        </div>

        <div className="landing-command-map" aria-label="Illustration of a governed work execution">
          <div className="flex items-center justify-between border-b border-[#222b36] px-5 py-3.5 text-[12px] text-[#8b98a8]">
            <span className="flex items-center gap-2"><Command className="size-3.5 text-[#e5a93c]" /> Command center · Live run</span>
            <span className="flex items-center gap-1.5 text-[#2dd4bf]"><span className="landing-live-dot" /> Synced</span>
          </div>
          <div className="p-5 sm:p-7">
            <div className="flex items-start gap-3">
              <div className="mt-1 flex size-8 shrink-0 items-center justify-center rounded-md border border-[#e5a93c]/30 bg-[#e5a93c]/10 text-[#e5a93c]"><Sparkles className="size-4" /></div>
              <div>
                <p className="text-[12px] font-medium text-[#8b98a8]">Operator request</p>
                <p className="mt-1 text-[15px] leading-6 text-[#eceff4]">“Prepare the Q3 launch plan and flag anything that needs my approval.”</p>
              </div>
            </div>
            <div className="my-5 ml-4 h-7 border-l border-dashed border-[#2d3846]" />
            <HanddrawnLoopDiagram className="mb-4 rounded-md border border-[#1d2530] bg-[#0a0d10] p-2" />
            <div className="space-y-2.5">
              {[
                ['01', 'Context assembled', 'Knowledge, policy, and owners loaded', 'done'],
                ['02', 'Work graph generated', '7 actions · 3 dependencies · 1 gate', 'done'],
                ['03', 'Approval required', 'Budget change before external publish', 'wait'],
              ].map(([number, title, detail, state]) => (
                <div key={number} className={`landing-run-row ${state === 'wait' ? 'landing-run-row-wait' : ''}`}>
                  <span className="font-mono text-[11px] text-[#647182]">{number}</span>
                  <div className="min-w-0 flex-1"><p className="text-[13px] font-medium text-[#eceff4]">{title}</p><p className="mt-0.5 truncate text-[12px] text-[#8b98a8]">{detail}</p></div>
                  <span className={`size-2 rounded-full ${state === 'wait' ? 'bg-[#e5a93c]' : 'bg-[#2dd4bf]'}`} />
                </div>
              ))}
            </div>
            <div className="mt-5 flex items-center justify-between border-t border-[#222b36] pt-4 text-[12px]">
              <span className="text-[#8b98a8]">Trace <span className="font-mono text-[#eceff4]">run_8H2K91</span></span>
              <span className="text-[#2dd4bf]">Evidence attached</span>
            </div>
          </div>
        </div>
      </section>

      <section id="operating-model" className="border-y border-[#1d2530] bg-[#0d1116]">
        <div className="mx-auto grid max-w-[1360px] gap-0 px-5 sm:px-8 lg:grid-cols-3 lg:px-12">
          {[
            { icon: Waypoints, title: 'Coordinate', text: 'One work graph across departments, tools, and people.' },
            { icon: ShieldCheck, title: 'Govern', text: 'Policies and approvals sit inside the execution path.' },
            { icon: Network, title: 'Prove', text: 'Every result carries state, source, owner, and trace.' },
          ].map(({ icon: Icon, title, text }, index) => (
            <div key={title} className={`flex gap-4 py-7 lg:px-8 ${index > 0 ? 'border-t border-[#1d2530] lg:border-l lg:border-t-0' : ''}`}>
              <Icon className="mt-0.5 size-5 shrink-0 text-[#e5a93c]" />
              <div><h2 className="text-[15px] font-medium text-[#eceff4]">{title}</h2><p className="mt-1 text-[13px] leading-6 text-[#8b98a8]">{text}</p></div>
            </div>
          ))}
        </div>
      </section>

      <section id="workforce" className="mx-auto max-w-[1360px] px-5 py-24 sm:px-8 lg:px-12 lg:py-28">
        <div className="grid gap-12 lg:grid-cols-[.75fr_1.25fr] lg:gap-20">
          <div>
            <div className="landing-kicker">A workforce with boundaries</div>
            <h2 className="mt-4 max-w-[480px] text-4xl font-semibold leading-[1.05] tracking-[-.035em] text-[#eceff4] sm:text-5xl">Specialists that know when to act—and when to ask.</h2>
            <p className="mt-6 max-w-[410px] text-[15px] leading-7 text-[#8b98a8]">Deploy purpose-built agents across the business without losing the operating context your team has built.</p>
            <a href="#trust" className="mt-8 inline-flex items-center gap-2 text-[13px] font-medium text-[#e5a93c] hover:text-[#f0bc5e]">Explore the trust model <ArrowRight className="size-3.5" /></a>
          </div>
          <div className="landing-workforce-grid">
            <div className="landing-agent-list" role="tablist" aria-label="AI workforce">
              {agents.map((agent) => (
                <button key={agent.id} type="button" role="tab" aria-selected={activeAgent === agent.id} onClick={() => setActiveAgent(agent.id)} onKeyDown={(event) => { if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); const index = agents.findIndex((item) => item.id === activeAgent); const next = event.key === 'ArrowDown' ? (index + 1) % agents.length : (index - 1 + agents.length) % agents.length; setActiveAgent(agents[next].id); } }} className={`landing-agent-tab ${activeAgent === agent.id ? 'landing-agent-tab-active' : ''}`}>
                  <span className={`landing-agent-orb landing-agent-orb-${agent.color}`} />
                  <span className="min-w-0 text-left"><span className="block text-[13px] font-medium text-[#eceff4]">{agent.name}</span><span className="mt-0.5 block truncate text-[12px] text-[#8b98a8]">{agent.role}</span></span>
                  <ChevronRight className="ml-auto size-4 text-[#647182]" />
                </button>
              ))}
            </div>
            <div className="landing-agent-detail" role="tabpanel">
              <div className="flex items-center justify-between"><span className="landing-status-pill"><span className="landing-live-dot" /> Available</span><span className="font-mono text-[11px] text-[#647182]">agent/{selectedAgent.id}</span></div>
              <h3 className="mt-10 text-3xl font-semibold tracking-[-.03em] text-[#eceff4]">{selectedAgent.name}</h3>
              <p className="mt-2 text-[13px] text-[#e5a93c]">{selectedAgent.role}</p>
              <p className="mt-6 max-w-[420px] text-[15px] leading-7 text-[#8b98a8]">{selectedAgent.description}</p>
              <div className="mt-10 border-t border-[#222b36] pt-5"><p className="text-[12px] font-medium text-[#647182]">Current signal</p><p className="mt-1.5 text-[13px] text-[#eceff4]">{selectedAgent.action}</p></div>
            </div>
          </div>
        </div>
      </section>

      <section id="trust" className="border-t border-[#1d2530] bg-[#0d1116]">
        <div className="mx-auto grid max-w-[1360px] gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[.9fr_1.1fr] lg:px-12 lg:py-24">
          <div><div className="landing-kicker"><LockKeyhole className="size-3.5" /> Designed for consequential work</div><h2 className="mt-4 max-w-[520px] text-4xl font-semibold leading-[1.06] tracking-[-.035em] text-[#eceff4]">Fast enough for today. Governed enough for tomorrow.</h2></div>
          <div className="grid gap-3 sm:grid-cols-2">
            {['Scoped tools and tenant boundaries', 'Explicit draft, approved, and delivered states', 'Retryable runs with terminal failure reasons', 'Audit-ready evidence and request correlation'].map((item) => <div key={item} className="flex gap-3 rounded-md border border-[#222b36] bg-[#11161c] p-4 text-[13px] leading-5 text-[#8b98a8]"><Check className="mt-0.5 size-4 shrink-0 text-[#2dd4bf]" />{item}</div>)}
          </div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-[1360px] flex-col gap-4 px-5 py-8 text-[12px] text-[#647182] sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12">
        <span>© {new Date().getFullYear()} OctaOS. The operating layer for accountable work.</span>
        <span className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-[#2dd4bf]" /> Systems ready for your next decision</span>
      </footer>
    </main>
  );
}

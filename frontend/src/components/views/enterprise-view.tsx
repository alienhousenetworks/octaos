'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import PageHeader from '@/components/shell/page-header';
import {
  Calendar,
  TrendingUp,
  Briefcase,
  MessageSquare,
  CheckCircle2,
  Sparkles,
  Zap,
  ShieldCheck,
  Lock,
  Users,
  Check,
  Layers,
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

type Tab = 'approvals' | 'policy' | 'billing' | 'employees' | 'roi' | 'crm' | 'compliance' | 'ops';

export default function EnterpriseView({
  token,
  mode = 'control',
  API_URL: propApiUrl,
}: {
  token: string;
  mode?: 'approvals' | 'control';
  API_URL?: string;
}) {
  const API_URL = propApiUrl || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
  const [tab, setTab] = useState<Tab>(mode === 'approvals' ? 'approvals' : 'policy');
  const [approvals, setApprovals] = useState<any[]>([]);
  const [policy, setPolicy] = useState<any>(null);
  const [entitlements, setEntitlements] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [agentCatalog, setAgentCatalog] = useState<any[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>(['marketing', 'sales']);
  const [employees, setEmployees] = useState<any[]>([]);
  const [standup, setStandup] = useState<any>(null);
  const [roi, setRoi] = useState<any>(null);
  const [dlq, setDlq] = useState<any[]>([]);
  const [crm, setCrm] = useState<any[]>([]);
  const [gdprEmail, setGdprEmail] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const load = async () => {
    setLoading(true);
    setMessage('');
    try {
      if (tab === 'approvals') {
        const r = await fetch(`${API_URL}/enterprise/approvals`, { headers });
        if (r.ok) setApprovals(await r.json());
      }
      if (tab === 'policy') {
        const r = await fetch(`${API_URL}/enterprise/policy`, { headers });
        if (r.ok) setPolicy(await r.json());
      }
      if (tab === 'billing') {
        const [e, p, c] = await Promise.all([
          fetch(`${API_URL}/enterprise/billing/entitlements`, { headers }),
          fetch(`${API_URL}/enterprise/billing/plans`),
          fetch(`${API_URL}/enterprise/billing/agent-catalog`),
        ]);
        if (e.ok) setEntitlements(await e.json());
        if (p.ok) setPlans(await p.json());
        if (c.ok) setAgentCatalog(await c.json());
      }
      if (tab === 'employees') {
        const [emp, st] = await Promise.all([
          fetch(`${API_URL}/enterprise/ai-employees`, { headers }),
          fetch(`${API_URL}/enterprise/ai-employees/standup`, { headers }),
        ]);
        if (emp.ok) setEmployees(await emp.json());
        if (st.ok) setStandup(await st.json());
      }
      if (tab === 'roi') {
        const r = await fetch(`${API_URL}/enterprise/roi/dashboard`, { headers });
        if (r.ok) setRoi(await r.json());
      }
      if (tab === 'crm') {
        const r = await fetch(`${API_URL}/enterprise/crm/connections`, { headers });
        if (r.ok) setCrm(await r.json());
      }
      if (tab === 'ops') {
        const r = await fetch(`${API_URL}/enterprise/ops/dlq`, { headers });
        if (r.ok) setDlq(await r.json());
      }
    } catch (e: any) {
      setMessage(e.message || 'Load failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, token]);

  const review = async (id: string, approve: boolean) => {
    const r = await fetch(`${API_URL}/enterprise/approvals/${id}/review`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ approve, note: approve ? 'Approved from UI' : 'Rejected from UI' }),
    });
    if (r.ok) {
      setMessage(approve ? 'Approved' : 'Rejected');
      load();
    } else {
      setMessage(await r.text());
    }
  };

  const savePolicy = async () => {
    if (!policy) return;
    const r = await fetch(`${API_URL}/enterprise/policy`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        default_mode: policy.default_mode,
        min_confidence: Number(policy.min_confidence),
        max_auto_amount: Number(policy.max_auto_amount),
        support_refuse_if_not_in_kb: !!policy.support_refuse_if_not_in_kb,
        channel_kill_switches: policy.channel_kill_switches || {},
        agent_kill_switches: policy.agent_kill_switches || {},
      }),
    });
    setMessage(r.ok ? 'Policy saved' : await r.text());
    load();
  };

  const changePlan = async (code: string) => {
    const r = await fetch(`${API_URL}/enterprise/billing/plan`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ plan_code: code }),
    });
    setMessage(r.ok ? `Plan set to ${code}` : await r.text());
    load();
  };

  const loadRazorpayScript = (): Promise<boolean> =>
    new Promise((resolve) => {
      if (typeof window !== 'undefined' && (window as any).Razorpay) {
        resolve(true);
        return;
      }
      const s = document.createElement('script');
      s.src = 'https://checkout.razorpay.com/v1/checkout.js';
      s.onload = () => resolve(true);
      s.onerror = () => resolve(false);
      document.body.appendChild(s);
    });

  const payWithRazorpay = async (planCode: string) => {
    setMessage('');
    try {
      const orderRes = await fetch(`${API_URL}/enterprise/billing/razorpay/create-order`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ plan_code: planCode }),
      });
      if (!orderRes.ok) {
        setMessage(await orderRes.text());
        return;
      }
      const order = await orderRes.json();
      const ok = await loadRazorpayScript();
      if (!ok) {
        setMessage('Failed to load Razorpay checkout script');
        return;
      }
      const rzp = new (window as any).Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: order.name || 'OctaOS',
        description: order.description,
        order_id: order.razorpay_order_id,
        prefill: order.prefill || {},
        notes: order.notes || {},
        theme: order.theme || { color: '#7888D9' },
        handler: async (response: any) => {
          const v = await fetch(`${API_URL}/enterprise/billing/razorpay/verify`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          });
          if (v.ok) {
            setMessage(`Payment successful — plan ${planCode} activated`);
            load();
          } else {
            setMessage(await v.text());
          }
        },
      });
      rzp.on('payment.failed', (resp: any) => {
        setMessage(resp?.error?.description || 'Payment failed');
      });
      rzp.open();
    } catch (e: any) {
      setMessage(e.message || 'Razorpay error');
    }
  };

  const payWithRazorpayForAgents = async (agentCodes: string[]) => {
    setMessage('');
    try {
      const orderRes = await fetch(`${API_URL}/enterprise/billing/razorpay/create-order`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ agent_codes: agentCodes }),
      });
      if (!orderRes.ok) {
        setMessage(await orderRes.text());
        return;
      }
      const order = await orderRes.json();
      const ok = await loadRazorpayScript();
      if (!ok) {
        setMessage('Failed to load Razorpay checkout script');
        return;
      }
      const rzp = new (window as any).Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: order.name || 'OctaOS AI Employees',
        description: order.description,
        order_id: order.razorpay_order_id,
        prefill: order.prefill || {},
        notes: order.notes || {},
        theme: { color: '#7888D9' },
        handler: async (response: any) => {
          const v = await fetch(`${API_URL}/enterprise/billing/razorpay/verify`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          });
          if (v.ok) {
            setMessage(`Payment successful — selected agents activated!`);
            load();
          } else {
            setMessage(await v.text());
          }
        },
      });
      rzp.on('payment.failed', (resp: any) => {
        setMessage(resp?.error?.description || 'Payment failed');
      });
      rzp.open();
    } catch (e: any) {
      setMessage(e.message || 'Razorpay error');
    }
  };

  const activateAgentsDirect = async (agentCodes: string[]) => {
    setMessage('');
    try {
      const r = await fetch(`${API_URL}/enterprise/billing/subscribe-agents`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ agent_codes: agentCodes }),
      });
      if (r.ok) {
        setMessage(`Activated ${agentCodes.join(', ')} successfully!`);
        load();
      } else {
        setMessage(await r.text());
      }
    } catch (e: any) {
      setMessage(e.message || 'Activation error');
    }
  };

  const toggleAgentSelection = (agentId: string) => {
    if (selectedAgents.includes(agentId)) {
      if (selectedAgents.length === 1) return; // Keep at least 1
      setSelectedAgents(selectedAgents.filter((a) => a !== agentId));
    } else {
      setSelectedAgents([...selectedAgents, agentId]);
    }
  };

  const calculateBundleTotals = () => {
    const catalog = agentCatalog.length > 0 ? agentCatalog : [
      { id: 'marketing', name: 'Campaign Planner AI', price_usd_monthly: 49, price_inr_monthly: 3999 },
      { id: 'sales', name: 'Sales AI SDR', price_usd_monthly: 79, price_inr_monthly: 5999 },
      { id: 'hr', name: 'HR Recruiter AI', price_usd_monthly: 49, price_inr_monthly: 3999 },
      { id: 'support', name: 'Customer Support AI', price_usd_monthly: 49, price_inr_monthly: 3999 },
    ];
    const picked = catalog.filter((c) => selectedAgents.includes(c.id));
    const rawInr = picked.reduce((acc, c) => acc + (c.price_inr_monthly || 0), 0);
    const rawUsd = picked.reduce((acc, c) => acc + (c.price_usd_monthly || 0), 0);
    const discount = selectedAgents.length >= 2 ? 0.90 : 1.0;
    return {
      count: picked.length,
      rawInr,
      rawUsd,
      finalInr: Math.round(rawInr * discount),
      finalUsd: Math.round(rawUsd * discount),
      hasDiscount: selectedAgents.length >= 2,
    };
  };

  const isAgentActiveInSub = (agentId: string): boolean => {
    if (!entitlements) return false;
    const allowed: string[] = entitlements.allowed_agents || [];
    return allowed.includes('*') || allowed.map((a: string) => String(a).toLowerCase()).includes(agentId.toLowerCase());
  };

  const gdpr = async (type: 'export' | 'delete') => {
    const r = await fetch(`${API_URL}/enterprise/compliance/gdpr/${type}`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ subject_email: gdprEmail }),
    });
    if (r.ok) {
      const data = await r.json();
      setMessage(`${type} completed: ${data.id}`);
    } else setMessage(await r.text());
  };

  const replayDlq = async (id: string) => {
    const r = await fetch(`${API_URL}/enterprise/ops/dlq/${id}/replay`, { method: 'POST', headers });
    setMessage(r.ok ? 'Replay queued' : await r.text());
    load();
  };

  const allTabs: { id: Tab; label: string }[] = [
    { id: 'approvals', label: 'Approvals' },
    { id: 'policy', label: 'Policy' },
    { id: 'billing', label: 'Billing' },
    { id: 'employees', label: 'AI Employees' },
    { id: 'roi', label: 'ROI' },
    { id: 'crm', label: 'CRM Sync' },
    { id: 'compliance', label: 'Compliance' },
    { id: 'ops', label: 'Ops / DLQ' },
  ];
  const tabs = allTabs.filter((item) => (mode === 'approvals' ? item.id === 'approvals' : item.id !== 'approvals'));

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <PageHeader
        title={mode === 'approvals' ? 'Approvals' : 'Enterprise'}
        description={mode === 'approvals' ? 'Review actions that are waiting for a person.' : 'Policy, billing, employees, and operations.'}
      />
      <div className={mode === 'control' ? 'grid grid-cols-1 gap-6 md:grid-cols-[210px_minmax(0,1fr)]' : ''}>
      {mode === 'control' && (
        <nav className="flex gap-1 overflow-auto md:flex-col bg-[#111318] p-2 rounded-xl border border-white/[0.08] h-fit" aria-label="Enterprise sections">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors ${
                tab === item.id
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      )}
      <div className="space-y-4 min-w-0">

      {message && (
        <div className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded px-3 py-2">
          {message}
        </div>
      )}
      {loading && <div className="text-xs text-muted-foreground">Loading…</div>}

      {tab === 'approvals' && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-white">Pending HITL approvals</h3>
          {approvals.length === 0 && <p className="text-xs text-muted-foreground">No pending approvals.</p>}
          {approvals.map((a) => (
            <Card key={a.id} className="p-4 bg-black/40 border-white/10 space-y-2">
              <div className="flex justify-between gap-2">
                <div>
                  <div className="text-sm font-medium text-white">{a.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {a.action_type} · {a.channel || '—'} · conf {(a.confidence ?? 0).toFixed?.(2) ?? a.confidence}
                  </div>
                  <div className="text-xs text-amber-300/80 mt-1">{a.policy_reason}</div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => review(a.id, true)}>Approve</Button>
                  <Button size="sm" variant="outline" onClick={() => review(a.id, false)}>Reject</Button>
                </div>
              </div>
              {a.payload?.draft && (
                <pre className="text-xs whitespace-pre-wrap text-zinc-300 bg-black/50 p-2 rounded max-h-40 overflow-auto">
                  {a.payload.draft}
                </pre>
              )}
            </Card>
          ))}
        </div>
      )}

      {tab === 'policy' && policy && (
        <Card className="p-4 bg-black/40 border-white/10 space-y-3">
          <h3 className="text-sm font-semibold text-white">Outbound / HITL policy</h3>
          <label className="text-xs block">
            Default mode
            <select
              className="mt-1 w-full bg-black/60 border border-white/10 rounded px-2 py-1 text-sm"
              value={policy.default_mode}
              onChange={(e) => setPolicy({ ...policy, default_mode: e.target.value })}
            >
              <option value="draft_only">Draft only (recommended)</option>
              <option value="auto_with_rules">Auto with rules</option>
            </select>
          </label>
          <label className="text-xs block">
            Min confidence
            <Input
              type="number"
              step="0.05"
              value={policy.min_confidence ?? 0.85}
              onChange={(e) => setPolicy({ ...policy, min_confidence: e.target.value })}
            />
          </label>
          <label className="text-xs block">
            Max auto amount
            <Input
              type="number"
              value={policy.max_auto_amount ?? 0}
              onChange={(e) => setPolicy({ ...policy, max_auto_amount: e.target.value })}
            />
          </label>
          <label className="text-xs flex items-center gap-2">
            <input
              type="checkbox"
              checked={!!policy.support_refuse_if_not_in_kb}
              onChange={(e) => setPolicy({ ...policy, support_refuse_if_not_in_kb: e.target.checked })}
            />
            Support: refuse if not in knowledge base
          </label>
          <Button onClick={savePolicy}>Save policy</Button>
        </Card>
      )}

      {tab === 'billing' && (
        <div className="space-y-6">
          {/* Active Workforce Overview Card */}
          {entitlements && (
            <Card className="p-6 bg-gradient-to-r from-zinc-950 to-zinc-900 border-white/10 shadow-xl space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-white/10">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Current Plan</span>
                    <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {entitlements.status || 'Active'}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-white mt-1">{entitlements.plan?.name}</h3>
                </div>

                <div className="flex flex-wrap gap-2 items-center">
                  <span className="text-xs text-zinc-400 mr-1">Active AI Employees:</span>
                  {[
                    { id: 'marketing', label: 'Campaign Planner', icon: Calendar, color: 'text-violet-400 border-violet-500/30 bg-violet-500/10' },
                    { id: 'sales', label: 'Sales SDR', icon: TrendingUp, color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' },
                    { id: 'hr', label: 'HR Recruiter', icon: Briefcase, color: 'text-amber-400 border-amber-500/30 bg-amber-500/10' },
                    { id: 'support', label: 'Customer Support', icon: MessageSquare, color: 'text-blue-400 border-blue-500/30 bg-blue-500/10' },
                  ].map((ag) => {
                    const active = isAgentActiveInSub(ag.id);
                    const AgIcon = ag.icon;
                    return (
                      <span
                        key={ag.id}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${
                          active
                            ? ag.color
                            : 'bg-zinc-900/60 text-zinc-500 border-zinc-800 line-through opacity-60'
                        }`}
                      >
                        <AgIcon size={12} />
                        {ag.label} {active ? '✓' : ''}
                      </span>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                  <span className="text-muted-foreground block">Seats</span>
                  <span className="text-base font-bold text-white mt-0.5 block">
                    {entitlements.seats_used} / {entitlements.seat_limit ?? '∞'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                  <span className="text-muted-foreground block">Monthly Actions</span>
                  <span className="text-base font-bold text-white mt-0.5 block">
                    {entitlements.actions_used_period ?? 0} / {entitlements.action_quota_monthly ?? '—'}
                  </span>
                  <span className="text-[10px] text-zinc-500">Resets monthly</span>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                  <span className="text-muted-foreground block">Weekly Quota</span>
                  <span className="text-base font-bold text-white mt-0.5 block">
                    {entitlements.actions_used_weekly ?? 0} / {entitlements.weekly_action_quota ?? '—'}
                  </span>
                  <span className="text-[10px] text-zinc-500">Resets weekly</span>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                  <span className="text-muted-foreground block">Plan Cost</span>
                  <span className="text-base font-bold text-white mt-0.5 block">
                    ₹{entitlements.plan?.price_inr_monthly ?? 0}/mo
                  </span>
                  <span className="text-[10px] text-zinc-500">${entitlements.plan?.price_usd_monthly ?? 0} USD</span>
                </div>
              </div>
            </Card>
          )}

          {/* Standalone Agent Subscriptions Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Hire Individual AI Employees</h3>
                <p className="text-xs text-muted-foreground">
                  Choose only the agents you need right now. Deploy separately with zero forced bundling.
                </p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {[
                {
                  id: 'marketing',
                  code: 'campaign_planner',
                  name: 'Campaign Planner AI',
                  persona: 'Jules — Senior Copywriter & Multi-channel Autopilot',
                  icon: Calendar,
                  color: 'text-violet-400 bg-violet-600/10 border-violet-500/20',
                  priceInr: '₹3,999',
                  priceUsd: '$49',
                  quota: '10,000 actions/mo',
                  points: [
                    '30-day autonomous marketing calendar across LinkedIn & Meta',
                    'High-converting copy generation & visual graphic prompts',
                    'Direct social scheduling with human approval queue',
                  ],
                },
                {
                  id: 'sales',
                  code: 'sales_ai',
                  name: 'Sales AI SDR',
                  persona: 'Alex — Outbound SDR & Deal Room Manager',
                  icon: TrendingUp,
                  color: 'text-emerald-400 bg-emerald-600/10 border-emerald-500/20',
                  priceInr: '₹5,999',
                  priceUsd: '$79',
                  quota: '15,000 actions/mo',
                  points: [
                    'B2B Lead scraper (Google Places, Apollo, Web registries)',
                    'Automated cold email sequencing & LinkedIn DM drafts',
                    'Interactive deal rooms, sales pipeline & CRM sync',
                  ],
                },
                {
                  id: 'hr',
                  code: 'hr_ai',
                  name: 'HR Recruiter AI',
                  persona: 'Hunter — Technical Recruiter & Candidate Screening',
                  icon: Briefcase,
                  color: 'text-amber-400 bg-amber-600/10 border-amber-500/20',
                  priceInr: '₹3,999',
                  priceUsd: '$49',
                  quota: '10,000 actions/mo',
                  points: [
                    'Resume parsing & job specification percentage match scoring',
                    'Automated candidate screening questionnaires & tests',
                    'Google Calendar & Google Meet interview coordinator',
                  ],
                },
                {
                  id: 'support',
                  code: 'support_ai',
                  name: 'Customer Support AI',
                  persona: 'Sam — Omnichannel 24/7 Support Specialist',
                  icon: MessageSquare,
                  color: 'text-blue-400 bg-blue-600/10 border-blue-500/20',
                  priceInr: '₹3,999',
                  priceUsd: '$49',
                  quota: '15,000 actions/mo',
                  points: [
                    '24/7 WhatsApp Cloud API & Email auto-responses',
                    'Company Knowledge-Base (RAG) grounded accuracy',
                    'Human interception override & SLA breach monitoring',
                  ],
                },
              ].map((ag) => {
                const AgIcon = ag.icon;
                const active = isAgentActiveInSub(ag.id);
                return (
                  <Card
                    key={ag.id}
                    className={`p-5 bg-zinc-950/70 border transition-all ${
                      active ? 'border-emerald-500/30 bg-emerald-950/10' : 'border-white/10 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-2.5 rounded-xl border ${ag.color}`}>
                          <AgIcon size={20} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white text-base">{ag.name}</span>
                            {active && (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                ACTIVE
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-zinc-400 block">{ag.persona}</span>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="text-base font-bold text-white">{ag.priceInr}</div>
                        <span className="text-[10px] text-zinc-400 block">{ag.priceUsd} / mo</span>
                      </div>
                    </div>

                    <div className="my-3 space-y-1.5 border-t border-b border-white/5 py-3">
                      {ag.points.map((pt, idx) => (
                        <div key={idx} className="flex items-start gap-2 text-xs text-zinc-300">
                          <CheckCircle2 size={13} className="text-emerald-400 mt-0.5 shrink-0" />
                          <span>{pt}</span>
                        </div>
                      ))}
                      <div className="text-[11px] text-zinc-500 pt-1 font-mono">Quota: {ag.quota}</div>
                    </div>

                    <div className="flex flex-wrap gap-2 pt-1">
                      <Button
                        size="sm"
                        onClick={() => payWithRazorpay(ag.code)}
                        className="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-xs"
                      >
                        Hire with Razorpay ({ag.priceInr})
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => changePlan(ag.code)}
                        className="border-white/10 hover:bg-white/5 text-xs text-zinc-300"
                      >
                        Instant Activate
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Interactive Multi-Agent A-la-carte Configurator */}
          <Card className="p-6 bg-gradient-to-br from-zinc-950 via-zinc-900 to-black border-violet-500/20 shadow-2xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <Layers size={18} className="text-violet-400" />
                <h3 className="text-base font-semibold text-white">Build Your Custom AI Team (A-la-carte)</h3>
              </div>
              <span className="text-xs text-violet-400 bg-violet-500/10 px-2.5 py-1 rounded-full border border-violet-500/20">
                10% Discount on 2+ Agents
              </span>
            </div>

            <p className="text-xs text-zinc-400">
              Select any custom combination of agents. Your team quota and multi-agent bundling discount are calculated in real time.
            </p>

            {/* Checkbox selector */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { id: 'marketing', name: 'Campaign Planner', priceInr: 3999, priceUsd: 49, icon: Calendar },
                { id: 'sales', name: 'Sales AI SDR', priceInr: 5999, priceUsd: 79, icon: TrendingUp },
                { id: 'hr', name: 'HR Recruiter', priceInr: 3999, priceUsd: 49, icon: Briefcase },
                { id: 'support', name: 'Customer Support', priceInr: 3999, priceUsd: 49, icon: MessageSquare },
              ].map((ag) => {
                const isSelected = selectedAgents.includes(ag.id);
                const AgIcon = ag.icon;
                return (
                  <div
                    key={ag.id}
                    onClick={() => toggleAgentSelection(ag.id)}
                    className={`cursor-pointer p-4 rounded-xl border transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-violet-950/20 border-violet-500/40 shadow-inner'
                        : 'bg-zinc-900/40 border-white/5 opacity-60 hover:opacity-100'
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={`h-4 w-4 rounded border flex items-center justify-center ${isSelected ? 'bg-violet-600 border-violet-500' : 'border-zinc-700'}`}>
                        {isSelected && <Check size={11} className="text-white" />}
                      </div>
                      <div>
                        <span className="text-xs font-semibold text-white block">{ag.name}</span>
                        <span className="text-[11px] text-zinc-400 font-mono">₹{ag.priceInr.toLocaleString()}</span>
                      </div>
                    </div>
                    <AgIcon size={16} className={isSelected ? 'text-violet-400' : 'text-zinc-600'} />
                  </div>
                );
              })}
            </div>

            {/* Live Calculation Bar */}
            {(() => {
              const totals = calculateBundleTotals();
              return (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/5 mt-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-zinc-400">Selected Team:</span>
                      <span className="text-xs font-bold text-white">{totals.count} AI Employees</span>
                      {totals.hasDiscount && (
                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-bold">
                          10% BUNDLE SAVINGS
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2 mt-0.5">
                      <span className="text-xl font-bold text-white">₹{totals.finalInr.toLocaleString()}</span>
                      <span className="text-xs text-zinc-400">/ month (${totals.finalUsd} USD)</span>
                      {totals.hasDiscount && (
                        <span className="text-xs text-zinc-500 line-through">₹{totals.rawInr.toLocaleString()}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 w-full sm:w-auto">
                    <Button
                      size="sm"
                      onClick={() => payWithRazorpayForAgents(selectedAgents)}
                      className="bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs flex-1 sm:flex-initial"
                    >
                      Subscribe Custom Team (₹{totals.finalInr.toLocaleString()})
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => activateAgentsDirect(selectedAgents)}
                      className="border-white/10 hover:bg-white/5 text-xs text-zinc-300 flex-1 sm:flex-initial"
                    >
                      Activate Custom Team
                    </Button>
                  </div>
                </div>
              );
            })()}
          </Card>

          {/* All-in-One Full Workforce Option */}
          <Card className="p-6 bg-gradient-to-r from-violet-950/30 to-indigo-950/30 border-violet-500/30 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-400 border border-violet-500/20 mb-2">
                <Sparkles size={12} /> Complete Enterprise Bundle
              </div>
              <h3 className="text-lg font-bold text-white">All-In-One AI Workforce (Full Access)</h3>
              <p className="text-xs text-zinc-400 mt-1 max-w-xl">
                Unlocks the complete suite: Campaign Planner, Sales AI SDR, HR Recruiter, Customer Support, plus CEO Workspace and Executive Boardroom. Highest quota (100,000 actions/mo).
              </p>
            </div>

            <div className="text-left md:text-right shrink-0 space-y-2">
              <div className="text-2xl font-bold text-white">
                ₹11,999 <span className="text-xs text-zinc-400 font-normal">/ mo ($149)</span>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => payWithRazorpay('all_access')}
                  className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold text-xs"
                >
                  Get All-In-One Bundle
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => changePlan('all_access')}
                  className="border-white/10 hover:bg-white/5 text-xs text-zinc-300"
                >
                  Activate All
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {tab === 'employees' && (
        <div className="space-y-4">
          <div className="grid md:grid-cols-3 gap-3">
            {employees.map((e) => (
              <Card key={e.id} className="p-4 bg-black/40 border-white/10">
                <div className="font-medium text-white">{e.name}</div>
                <div className="text-xs text-muted-foreground">{e.role_key} · {e.status}</div>
                <div className="text-xs mt-2">Quota {e.used_today}/{e.quota_daily}</div>
              </Card>
            ))}
          </div>
          {standup?.standups && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-white">Daily stand-up</h3>
              {standup.standups.map((s: any) => (
                <Card key={s.employee_id} className="p-3 bg-black/40 border-white/10 text-xs space-y-1">
                  <div className="font-medium text-white">{s.name}</div>
                  <div>Needs approval: {s.needs_approval}</div>
                  <div>Did: {s.did?.length || 0} actions · Failed: {s.failed?.length || 0}</div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'roi' && roi && (
        <div className="grid md:grid-cols-3 gap-3">
          <Card className="p-4 bg-black/40 border-white/10">
            <div className="text-xs text-muted-foreground">AI spend</div>
            <div className="text-xl font-semibold text-white">${(roi.ai_spend_usd || 0).toFixed(2)}</div>
          </Card>
          <Card className="p-4 bg-black/40 border-white/10">
            <div className="text-xs text-muted-foreground">Hours saved</div>
            <div className="text-xl font-semibold text-white">{roi.hours_saved}</div>
          </Card>
          <Card className="p-4 bg-black/40 border-white/10">
            <div className="text-xs text-muted-foreground">Net ROI</div>
            <div className="text-xl font-semibold text-emerald-400">${(roi.net_roi_usd || 0).toFixed(2)}</div>
          </Card>
          <Card className="p-4 bg-black/40 border-white/10 md:col-span-3 text-xs space-y-1">
            <div>Cost / meeting: {roi.cost_per_meeting_usd != null ? `$${roi.cost_per_meeting_usd.toFixed(2)}` : '—'}</div>
            <div>Cost / ticket: {roi.cost_per_resolved_ticket_usd != null ? `$${roi.cost_per_resolved_ticket_usd.toFixed(2)}` : '—'}</div>
            <div>ROI multiple: {roi.roi_multiple ?? '—'}</div>
            <div className="pt-2 font-medium text-white">Quality samples</div>
            {(roi.quality_samples || []).slice(0, 5).map((s: any) => (
              <div key={s.id} className="text-zinc-400">
                {s.agent} · {s.task_type} · conf {s.confidence} · {s.result_status || 'pending'}
              </div>
            ))}
          </Card>
        </div>
      )}

      {tab === 'crm' && (
        <div className="space-y-2 text-sm">
          <p className="text-xs text-muted-foreground">
            Connect HubSpot / Salesforce / Zendesk / Freshdesk via API (POST /enterprise/crm/connect).
          </p>
          {crm.length === 0 && <p className="text-xs">No CRM connections yet.</p>}
          {crm.map((c) => (
            <Card key={c.id} className="p-3 bg-black/40 border-white/10 text-xs">
              {c.provider} · {c.sync_status} · last {c.last_sync_at || 'never'}
            </Card>
          ))}
        </div>
      )}

      {tab === 'compliance' && (
        <Card className="p-4 bg-black/40 border-white/10 space-y-3">
          <h3 className="text-sm font-semibold text-white">GDPR subject requests</h3>
          <Input placeholder="subject@email.com" value={gdprEmail} onChange={(e) => setGdprEmail(e.target.value)} />
          <div className="flex gap-2">
            <Button size="sm" onClick={() => gdpr('export')}>Export</Button>
            <Button size="sm" variant="outline" onClick={() => gdpr('delete')}>Delete / anonymize</Button>
          </div>
        </Card>
      )}

      {tab === 'ops' && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-white">Dead-letter queue</h3>
          {dlq.length === 0 && <p className="text-xs text-muted-foreground">No failed jobs.</p>}
          {dlq.map((j) => (
            <Card key={j.id} className="p-3 bg-black/40 border-white/10 text-xs flex justify-between gap-2">
              <div>
                <div className="text-white">{j.task_name}</div>
                <div className="text-red-300/80">{j.error_message}</div>
              </div>
              <Button size="sm" onClick={() => replayDlq(j.id)}>Replay</Button>
            </Card>
          ))}
        </div>
      )}
      </div>
      </div>
    </div>
  );
}

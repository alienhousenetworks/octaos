'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Calendar,
  TrendingUp,
  Briefcase,
  MessageSquare,
  Lock,
  Sparkles,
  CheckCircle2,
  Zap,
  ArrowRight,
  ShieldCheck,
  Loader2,
} from 'lucide-react';

interface AgentLockedScreenProps {
  agentKey: 'marketing' | 'sales' | 'hr' | 'support';
  token: string | null;
  API_URL: string;
  fetchData: () => Promise<void>;
}

const AGENT_DATA = {
  marketing: {
    id: 'marketing',
    planCode: 'campaign_planner',
    name: 'Campaign Planner AI',
    persona: 'Jules — Senior Autonomous Copywriter & Campaign Planner',
    icon: Calendar,
    color: 'from-violet-600 to-indigo-600',
    textColor: 'text-violet-400',
    borderColor: 'border-violet-500/30',
    priceInr: '₹3,999',
    priceUsd: '$49',
    quota: '10,000 actions / mo',
    description:
      'Autonomous marketing operations. Generates 30-day multi-channel social campaigns, high-converting visual prompts, viral copy, and publishes directly to LinkedIn, Meta, and Instagram.',
    features: [
      '30-Day Multi-Channel Campaign Calendar & Autopilot',
      'AI Copywriter, Hook Generator & DALL-E 3 Graphic Prompts',
      'One-click Social Publishing & Scheduling',
      'Regional Context Radar & Competitor Signal Ingestion',
      'Human-in-the-Loop Approval Queue & Brand Safety',
    ],
    sampleOutput:
      '☕️ "Work hard, coffee harder! 18-hour cold brew launch campaign for LinkedIn & Meta scheduled for next 30 days. Day 4 graphic prompt rendered with 98% brand match."',
  },
  sales: {
    id: 'sales',
    planCode: 'sales_ai',
    name: 'Sales AI SDR & Deal Engine',
    persona: 'Alex — Outbound SDR & Revenue Intelligence Agent',
    icon: TrendingUp,
    color: 'from-emerald-600 to-teal-600',
    textColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/30',
    priceInr: '₹5,999',
    priceUsd: '$79',
    quota: '15,000 actions / mo',
    description:
      'Autonomous B2B outbound engine. Finds qualified leads from Google Maps, Apollo, and web registries, enriches contacts, sends personalized cold email sequences, and runs interactive Deal Rooms.',
    features: [
      'B2B Lead Discovery (Google Places, Apollo & Apify Scraping)',
      'Automated Multi-step Cold Email Sequences & SMTP Dispatch',
      'Interactive Deal Rooms & Real-time Buyer Stage Tracking',
      'Sales Activity Stepper, Lead Scoring & Evidence Ledger',
      'CRM Two-Way Synchronization (HubSpot, Salesforce, Pipedrive)',
    ],
    sampleOutput:
      '🎯 "Extracted 25 CTO leads at early-stage AI startups in NY. Verified emails, drafted personalized outbound value propositions, and queued 3 follow-ups."',
  },
  hr: {
    id: 'hr',
    planCode: 'hr_ai',
    name: 'HR Recruiter AI',
    persona: 'Hunter — Technical Recruiter & Talent Screening Specialist',
    icon: Briefcase,
    color: 'from-amber-600 to-orange-600',
    textColor: 'text-amber-400',
    borderColor: 'border-amber-500/30',
    priceInr: '₹3,999',
    priceUsd: '$49',
    quota: '10,000 actions / mo',
    description:
      'Autonomous talent acquisition. Ingests candidate CVs, calculates job-fit match scores, conducts automated preliminary email screening tests, and coordinates Google Meet interviews.',
    features: [
      'AI Resume Parsing & Job Description Match Scoring',
      'Automated Candidate Screening Questionnaires & Evaluations',
      'Google Calendar & Google Meet Interview Scheduling',
      'Candidate Pipeline Tracking & Talent Ledger',
      'Automated Offer & Onboarding Readiness Checklists',
    ],
    sampleOutput:
      '💼 "Reviewed 18 developer resumes against Senior Fullstack spec. Candidate Sarah J. scored 96% match. Sent screening questionnaire and booked Google Meet for May 24."',
  },
  support: {
    id: 'support',
    planCode: 'support_ai',
    name: 'Customer Support AI',
    persona: 'Sam — 24/7 Omnichannel Customer Support Employee',
    icon: MessageSquare,
    color: 'from-blue-600 to-cyan-600',
    textColor: 'text-blue-400',
    borderColor: 'border-blue-500/30',
    priceInr: '₹3,999',
    priceUsd: '$49',
    quota: '15,000 actions / mo',
    description:
      '24/7 customer service automation. Resolves tickets across WhatsApp and Email using company Knowledge-Base RAG documents, with seamless human takeover and SLA monitoring.',
    features: [
      'WhatsApp Cloud API & Email Ticket Auto-Resolution',
      'Company Knowledge-Base (RAG) Grounded Answers',
      'Human Takeover Override (Yields to human staff instantly)',
      'Human-like Delay Timers (4-5 min WhatsApp, 20 min Email)',
      'Automated Ticket Escalations & SLA Breach Alerter',
    ],
    sampleOutput:
      '💬 "Customer inquired via WhatsApp about pricing refund policy. Drafted response grounded in uploaded Knowledge Base docs and answered within 4 minutes."',
  },
};

export default function AgentLockedScreen({
  agentKey,
  token,
  API_URL,
  fetchData,
}: AgentLockedScreenProps) {
  const router = useRouter();
  const agent = AGENT_DATA[agentKey] || AGENT_DATA.marketing;
  const Icon = agent.icon;

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

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

  const handleHireAgent = async () => {
    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
      // First attempt order creation via Razorpay
      const orderRes = await fetch(`${API_URL}/enterprise/billing/razorpay/create-order`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ plan_code: agent.planCode }),
      });

      if (orderRes.ok) {
        const order = await orderRes.json();
        const ok = await loadRazorpayScript();
        if (ok && (window as any).Razorpay) {
          const rzp = new (window as any).Razorpay({
            key: order.key_id,
            amount: order.amount_paise,
            currency: order.currency,
            name: 'OctaOS AI Employee',
            description: `Hire ${agent.name}`,
            order_id: order.razorpay_order_id,
            prefill: order.prefill || {},
            notes: order.notes || {},
            theme: { color: '#8b5cf6' },
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
                setSuccessMsg(`Payment successful! ${agent.name} is now hired and active.`);
                await fetchData();
              } else {
                setErrorMsg(await v.text());
              }
            },
          });
          rzp.open();
          setLoading(false);
          return;
        }
      }

      // If Razorpay is not configured or in free/dev mode, activate directly
      const directRes = await fetch(`${API_URL}/enterprise/billing/subscribe-agents`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ agent_codes: [agent.id] }),
      });

      if (directRes.ok) {
        setSuccessMsg(`${agent.name} successfully unlocked!`);
        await fetchData();
      } else {
        const err = await directRes.text();
        setErrorMsg(err || 'Failed to activate agent license.');
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Error occurred while activating agent.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl py-8 px-4 space-y-8 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-zinc-900/90 to-black/90 p-8 shadow-2xl backdrop-blur-xl">
        <div className={`absolute -right-16 -top-16 h-64 w-64 rounded-full bg-gradient-to-br ${agent.color} opacity-20 blur-3xl pointer-events-none`} />

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
          <div className="flex items-center gap-4">
            <div className={`p-4 rounded-2xl bg-gradient-to-tr ${agent.color} shadow-lg shadow-black/40 text-white`}>
              <Icon className="h-8 w-8" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <Lock size={11} /> Agent License Required
                </span>
                <span className="text-xs text-muted-foreground font-mono">Standalone Hire</span>
              </div>
              <h1 className="text-2xl md:text-3xl font-bold text-white mt-1.5">{agent.name}</h1>
              <p className="text-sm text-zinc-400">{agent.persona}</p>
            </div>
          </div>

          <div className="text-left md:text-right bg-white/5 border border-white/10 rounded-2xl p-4 min-w-[200px]">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider block">Price</span>
            <div className="text-2xl font-bold text-white mt-0.5">
              {agent.priceInr} <span className="text-xs text-zinc-400 font-normal">/ mo ({agent.priceUsd})</span>
            </div>
            <span className="text-xs text-emerald-400 block mt-0.5 font-medium">{agent.quota}</span>
          </div>
        </div>

        <p className="mt-6 text-sm md:text-base text-zinc-300 leading-relaxed max-w-3xl">
          {agent.description}
        </p>

        {errorMsg && (
          <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-medium">
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium flex items-center gap-2">
            <CheckCircle2 size={14} /> {successMsg}
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button
            size="lg"
            onClick={handleHireAgent}
            disabled={loading}
            className={`bg-gradient-to-r ${agent.color} hover:opacity-90 text-white font-semibold shadow-lg shadow-black/40`}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin mr-2" />
                Activating...
              </>
            ) : (
              <>
                <Zap size={16} className="mr-2 fill-current" />
                Hire {agent.name} ({agent.priceInr}/mo)
              </>
            )}
          </Button>

          <Button
            variant="outline"
            size="lg"
            onClick={() => router.push('/app/settings/enterprise')}
            className="border-white/10 hover:bg-white/5 text-zinc-300"
          >
            Explore All Plans & Multi-Agent Bundles
            <ArrowRight size={15} className="ml-2" />
          </Button>
        </div>
      </div>

      {/* Capabilities & Output Preview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Features Column - 7 cols */}
        <Card className="md:col-span-7 bg-zinc-950/60 border-white/10 p-6 rounded-2xl shadow-xl backdrop-blur-md">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={18} className={agent.textColor} />
            <h2 className="text-base font-semibold text-white">What this AI employee executes for you</h2>
          </div>
          <div className="space-y-3">
            {agent.features.map((feat, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 text-xs md:text-sm text-zinc-300">
                <CheckCircle2 size={16} className={`${agent.textColor} shrink-0 mt-0.5`} />
                <span>{feat}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Live Output Mockup Column - 5 cols */}
        <Card className="md:col-span-5 bg-zinc-950/60 border-white/10 p-6 rounded-2xl shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-white/10 mb-4">
              <span className="text-xs uppercase tracking-wider text-zinc-400 font-semibold">Autonomous Output Preview</span>
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>

            <div className="p-4 rounded-xl bg-black/60 border border-white/10 text-xs text-zinc-300 leading-relaxed font-mono">
              {agent.sampleOutput}
            </div>

            <div className="mt-4 p-3 rounded-xl bg-primary/5 border border-primary/10 text-xs text-zinc-400 flex items-start gap-2">
              <ShieldCheck size={16} className="text-violet-400 shrink-0 mt-0.5" />
              <span>Full isolation: Your prompts, leads, and customer data are scoped strictly to your tenant organization.</span>
            </div>
          </div>

          <div className="pt-4 mt-4 border-t border-white/10 text-center">
            <span className="text-xs text-zinc-500">Cancel or upgrade anytime with prorated billing.</span>
          </div>
        </Card>
      </div>
    </div>
  );
}

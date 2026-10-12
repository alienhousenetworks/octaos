'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Eye,
  EyeOff,
  TrendingUp,
  Target,
  DollarSign,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Users,
  Share2,
  Bot,
  Zap,
  BarChart3,
  Layers,
  ShieldCheck,
  ArrowUpRight,
  Sparkles,
  Inbox,
  Filter,
} from 'lucide-react';
import PageHeader from '@/components/shell/page-header';
import Stat from '@/components/shell/stat';
import StatusBadge from '@/components/shell/status-badge';
import { EmptyState } from '@/components/shell/states';

interface DashboardViewProps {
  metrics: any;
  timeline: any[];
  queue: { posts: any[]; leads: any[] };
  apps: any[];
  setActiveView: (view: string) => void;
  uninstallApp: (appName: string) => Promise<void>;
  handleApprovePost: (postId: string) => Promise<void>;
  handleRejectPost: (postId: string) => Promise<void>;
}

function metricValue(value: unknown) {
  if (value === undefined || value === null || value === '') return '—';
  return value as React.ReactNode;
}

export default function DashboardView({
  metrics,
  timeline,
  queue,
  apps,
  setActiveView,
  uninstallApp,
  handleApprovePost,
  handleRejectPost,
}: DashboardViewProps) {
  const [hideRevenue, setHideRevenue] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'revenue' | 'content' | 'operations'>('all');

  const posts = queue?.posts || [];
  const leads = queue?.leads || [];
  const pending = posts.length + leads.length;

  // Primary Metrics
  const rate = metrics?.automation_success_rate;
  const revenue = metrics?.revenue_impact;
  const pipelineVal = metrics?.pipeline_value;
  const aiCost = metrics?.ai_cost;

  // Daily Tasks
  const daily = metrics?.daily_tasks;
  const dates = daily?.dates || ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'];
  const mDaily = daily?.marketing || [0, 0, 0, 0, 0, 0, 0];
  const sDaily = daily?.sales || [0, 0, 0, 0, 0, 0, 0];
  const supDaily = daily?.support || [0, 0, 0, 0, 0, 0, 0];
  const totalsDaily = daily?.totals || mDaily.map((m: number, i: number) => m + (sDaily[i] || 0) + (supDaily[i] || 0));
  const maxDaily = Math.max(1, ...totalsDaily);

  // Cross-Vertical Structured Analytics
  const funnel = metrics?.funnel || {
    captured: metrics?.leads_generated || leads.length,
    contacted: Math.max(0, (metrics?.leads_generated || leads.length) - (metrics?.lead_metrics?.uncontacted || 0)),
    qualified: metrics?.leads_generated ? Math.round(Number(metrics.leads_generated) * 0.4) : 0,
    converted: metrics?.leads_generated ? Math.round(Number(metrics.leads_generated) * 0.15) : 0,
  };

  const dealStages = metrics?.deal_stages || {};
  const channelPerf = metrics?.channel_performance || [];
  const ticketData = metrics?.ticket_analytics || {
    open: 0,
    pending_human: 0,
    resolved: Number(metrics?.tickets_resolved || 0),
    sla_compliance: 100,
    sla_breach_rate: 0,
  };
  const leadMetrics = metrics?.lead_metrics || {
    total: Number(metrics?.leads_generated || 0),
    unassigned: 0,
    uncontacted: 0,
    conversion_rate: 0,
    wow_change: 0,
  };
  const marketingMetrics = metrics?.marketing_metrics || {
    total_posts: Number(metrics?.posts_published || 0),
    total_impressions: 0,
    avg_engagement_rate: 0,
  };
  const agentFleet = metrics?.agent_fleet || {
    total_actions: timeline.length,
    agent_activity: {},
  };
  const flowPerf = metrics?.flow_performance || {
    total_runs: 0,
    succeeded_runs: 0,
    failed_runs: 0,
    success_rate: rate,
    ai_cost: aiCost,
  };

  // Agent activity sorted
  const sortedAgents = Object.entries(agentFleet.agent_activity || {})
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, 6);

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-in fade-in duration-300">
      {/* Header with Quick Actions & Live Indicator */}
      <PageHeader
        title="Workspace Overview"
        description="Unified real-time analytics across revenue, marketing channels, and autonomous agent operations."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant={pending > 0 ? 'default' : 'outline'}
              onClick={() => setActiveView('approvals')}
              className="relative"
            >
              {pending > 0 ? (
                <>
                  <span className="mr-1.5 flex h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                  Review {pending} approvals
                </>
              ) : (
                'Approvals queue'
              )}
            </Button>
          </div>
        }
      />

      {/* Domain Navigation Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <div className="flex items-center gap-1 rounded-lg bg-secondary/50 p-1 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('all')}
            className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
              activeTab === 'all'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            All Analytics
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('revenue')}
            className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
              activeTab === 'revenue'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Revenue & Pipeline
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('content')}
            className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
              activeTab === 'content'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Marketing & Reach
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('operations')}
            className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
              activeTab === 'operations'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Agent Operations
          </button>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Live telemetry active</span>
        </div>
      </div>

      {/* Top Executive KPI Ribbon */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
        <Stat
          label="Closed Revenue"
          value={
            <span className="inline-flex items-center gap-1.5">
              {hideRevenue || revenue === undefined || revenue === null
                ? hideRevenue
                  ? '••••'
                  : '—'
                : `$${Number(revenue).toLocaleString()}`}
              <button
                type="button"
                aria-label={hideRevenue ? 'Show revenue' : 'Hide revenue'}
                onClick={() => setHideRevenue((val) => !val)}
                className="text-muted-foreground hover:text-foreground transition-colors ml-0.5"
              >
                {hideRevenue ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
              </button>
            </span>
          }
          hint="Attributed closed sales"
        />

        <Stat
          label="Deal Pipeline"
          value={
            pipelineVal !== undefined && pipelineVal !== null && pipelineVal > 0
              ? `$${Number(pipelineVal).toLocaleString()}`
              : '—'
          }
          hint="Active sales opportunities"
        />

        <Stat
          label="Leads Sourced"
          value={
            <span className="flex items-baseline gap-2">
              <span>{metricValue(metrics?.leads_generated ?? leadMetrics.total)}</span>
              {leadMetrics.conversion_rate > 0 && (
                <span className="text-xs text-emerald-400 font-normal">
                  {leadMetrics.conversion_rate}% conv
                </span>
              )}
            </span>
          }
          hint="Total indexed prospects"
        />

        <Stat
          label="Content Reach"
          value={
            marketingMetrics.total_impressions > 0
              ? `${Number(marketingMetrics.total_impressions).toLocaleString()}`
              : metricValue(metrics?.posts_published)
          }
          hint={marketingMetrics.total_impressions > 0 ? 'Total social impressions' : 'Posts published'}
        />

        <Stat
          label="AI Compute Spend"
          value={
            aiCost !== undefined && aiCost !== null
              ? `$${Number(aiCost).toFixed(3)}`
              : '—'
          }
          hint="Flow engine & models"
        />

        <Stat
          label="Flow Success"
          value={rate === undefined || rate === null || rate === '' ? '—' : `${rate}%`}
          hint={flowPerf.total_runs ? `${flowPerf.succeeded_runs}/${flowPerf.total_runs} completed runs` : 'Autonomous tasks'}
        />

        <Stat
          label="Support SLA"
          value={ticketData.sla_compliance ? `${ticketData.sla_compliance}%` : '—'}
          hint={ticketData.open > 0 ? `${ticketData.open} open tickets` : 'All resolved within SLA'}
        />
      </div>

      {/* SECTION 1: REVENUE & PIPELINE ANALYTICS */}
      {(activeTab === 'all' || activeTab === 'revenue') && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-tight flex items-center gap-2">
              <TrendingUp className="size-4 text-emerald-400" />
              Acquisition & Pipeline Velocity
            </h2>
            <Button variant="ghost" size="sm" onClick={() => setActiveView('sales')} className="text-xs">
              Open Sales Pipeline <ArrowUpRight className="size-3.5 ml-1" />
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* 4-Stage Lead Conversion Funnel */}
            <div className="rounded-lg border border-border bg-card p-4 space-y-4 lg:col-span-2">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium">Lead Conversion Funnel</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">Prospect progression from capture to conversion</p>
                </div>
                {leadMetrics.wow_change !== 0 && leadMetrics.wow_change !== null && (
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                      leadMetrics.wow_change > 0
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-rose-500/10 text-rose-400'
                    }`}
                  >
                    {leadMetrics.wow_change > 0 ? '+' : ''}
                    {leadMetrics.wow_change}% WoW
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 pt-1">
                <div className="rounded-md border border-border/60 bg-secondary/30 p-3">
                  <div className="text-xs text-muted-foreground">1. Captured</div>
                  <div className="text-xl font-semibold mt-1">{funnel.captured || 0}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">Raw prospects</div>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: '100%' }} />
                  </div>
                </div>

                <div className="rounded-md border border-border/60 bg-secondary/30 p-3">
                  <div className="text-xs text-muted-foreground">2. Contacted</div>
                  <div className="text-xl font-semibold mt-1">{funnel.contacted || 0}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {funnel.captured ? `${Math.round(((funnel.contacted || 0) / funnel.captured) * 100)}% reach` : '0% reach'}
                  </div>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-indigo-400"
                      style={{
                        width: `${funnel.captured ? Math.min(100, Math.round(((funnel.contacted || 0) / funnel.captured) * 100)) : 0}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="rounded-md border border-border/60 bg-secondary/30 p-3">
                  <div className="text-xs text-muted-foreground">3. Qualified</div>
                  <div className="text-xl font-semibold mt-1">{funnel.qualified || 0}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {funnel.captured ? `${Math.round(((funnel.qualified || 0) / funnel.captured) * 100)}% qualified` : '0% qualified'}
                  </div>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-emerald-400"
                      style={{
                        width: `${funnel.captured ? Math.min(100, Math.round(((funnel.qualified || 0) / funnel.captured) * 100)) : 0}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="rounded-md border border-border/60 bg-secondary/30 p-3">
                  <div className="text-xs text-muted-foreground">4. Converted</div>
                  <div className="text-xl font-semibold mt-1">{funnel.converted || 0}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {funnel.captured ? `${Math.round(((funnel.converted || 0) / funnel.captured) * 100)}% win rate` : '0% win rate'}
                  </div>
                  <div className="mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-amber-400"
                      style={{
                        width: `${funnel.captured ? Math.min(100, Math.round(((funnel.converted || 0) / funnel.captured) * 100)) : 0}%`,
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Triage Alerts */}
              {(leadMetrics.unassigned > 0 || leadMetrics.uncontacted > 0) && (
                <div className="flex flex-wrap items-center gap-3 rounded-md bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-xs text-amber-300">
                  <AlertTriangle className="size-4 shrink-0 text-amber-400" />
                  <span>
                    Attention required: <strong>{leadMetrics.unassigned} unassigned</strong> leads and{' '}
                    <strong>{leadMetrics.uncontacted} uncontacted</strong> prospects waiting for engagement.
                  </span>
                </div>
              )}
            </div>

            {/* Deal Rooms & Stage Distribution */}
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Deal Rooms by Stage</h3>
                <span className="text-xs text-muted-foreground">
                  {Object.keys(dealStages).length > 0 ? `${Object.keys(dealStages).length} stages` : 'Empty'}
                </span>
              </div>

              {Object.keys(dealStages).length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No active deal room opportunities tracked.
                </div>
              ) : (
                <div className="space-y-2.5 pt-1">
                  {Object.entries(dealStages).map(([stage, data]: [string, any]) => (
                    <div key={stage} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="size-2 rounded-full bg-primary" />
                        <span className="capitalize font-medium">{stage.replace(/_/g, ' ')}</span>
                        <span className="text-muted-foreground">({data.count})</span>
                      </div>
                      <span className="font-semibold text-foreground">
                        ${Number(data.value || 0).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="pt-2 border-t border-border/60 flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Total Open Value</span>
                <span className="font-bold text-foreground">
                  ${Number(pipelineVal || 0).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 2: MARKETING & CONTENT REACH */}
      {(activeTab === 'all' || activeTab === 'content') && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-tight flex items-center gap-2">
              <Share2 className="size-4 text-indigo-400" />
              Content Reach & Multi-Channel Performance
            </h2>
            <Button variant="ghost" size="sm" onClick={() => setActiveView('campaigns')} className="text-xs">
              Open Campaigns <ArrowUpRight className="size-3.5 ml-1" />
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Multi-Channel Distribution */}
            <div className="rounded-lg border border-border bg-card p-4 lg:col-span-2 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium">Channel Distribution</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">Cross-platform publish volume and audience engagement</p>
                </div>
                <div className="text-xs text-muted-foreground">
                  Avg engagement: <strong className="text-foreground">{marketingMetrics.avg_engagement_rate}%</strong>
                </div>
              </div>

              {channelPerf.length === 0 ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 py-2">
                  {['LinkedIn', 'Twitter / X', 'Instagram', 'Facebook'].map((plat) => (
                    <div key={plat} className="rounded-md border border-border/50 bg-secondary/20 p-3 text-center">
                      <p className="text-xs font-medium text-foreground">{plat}</p>
                      <p className="text-lg font-semibold mt-1">0</p>
                      <p className="text-[11px] text-muted-foreground">0 impressions</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 py-2">
                  {channelPerf.map((ch: any) => (
                    <div key={ch.platform} className="rounded-md border border-border/60 bg-secondary/30 p-3">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold capitalize text-foreground">{ch.platform}</p>
                        <span className="text-[10px] rounded bg-primary/10 text-primary px-1.5 py-0.5">
                          {ch.engagement_rate}% ER
                        </span>
                      </div>
                      <p className="text-xl font-bold mt-1.5">{ch.posts || 0} posts</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {Number(ch.impressions || 0).toLocaleString()} impressions
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Pipeline Stage Health */}
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <h3 className="text-sm font-medium">Publishing Pipeline</h3>
              <dl className="space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Waiting for review</dt>
                  <dd className="font-semibold text-amber-400">{posts.length} posts</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Published live</dt>
                  <dd className="font-semibold text-foreground">
                    {metricValue(metrics?.posts_published ?? marketingMetrics.total_posts)}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Total social impressions</dt>
                  <dd className="font-semibold text-foreground">
                    {Number(marketingMetrics.total_impressions || 0).toLocaleString()}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Benchmark engagement rate</dt>
                  <dd className="font-semibold text-emerald-400">
                    {marketingMetrics.avg_engagement_rate}%
                  </dd>
                </div>
              </dl>
              <div className="pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs"
                  onClick={() => setActiveView('campaigns')}
                >
                  Create new campaign post
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 3: AGENT FLEET & OPERATIONAL VELOCITY */}
      {(activeTab === 'all' || activeTab === 'operations') && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-tight flex items-center gap-2">
              <Activity className="size-4 text-violet-400" />
              Agent Fleet Velocity & 7-Day Execution
            </h2>
            <Button variant="ghost" size="sm" onClick={() => setActiveView('orchestrator')} className="text-xs">
              Open Orchestrator <ArrowUpRight className="size-3.5 ml-1" />
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {/* Stacked 7-Day Activity Chart */}
            <div className="rounded-lg border border-border bg-card p-4 lg:col-span-2 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-medium">Daily Task Execution (Last 7 Days)</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">Automated workload volume grouped by department</p>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <span className="size-2.5 rounded-sm bg-indigo-500" /> Marketing
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="size-2.5 rounded-sm bg-emerald-500" /> Sales
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="size-2.5 rounded-sm bg-violet-500" /> Support / Ops
                  </span>
                </div>
              </div>

              {/* Stacked Bar Columns */}
              <div className="grid grid-cols-7 gap-2 pt-2">
                {dates.map((d: string, index: number) => {
                  const m = mDaily[index] || 0;
                  const s = sDaily[index] || 0;
                  const sup = supDaily[index] || 0;
                  const total = totalsDaily[index] || m + s + sup;
                  const barHeight = Math.max(8, Math.round((total / maxDaily) * 110));

                  const mPct = total > 0 ? (m / total) * 100 : 0;
                  const sPct = total > 0 ? (s / total) * 100 : 0;
                  const supPct = total > 0 ? (sup / total) * 100 : 0;

                  return (
                    <div key={index} className="flex flex-col items-center group">
                      <span className="text-[11px] font-semibold text-foreground mb-1 group-hover:text-primary transition-colors">
                        {total}
                      </span>
                      <div className="flex h-28 w-full max-w-10 flex-col-reverse justify-start overflow-hidden rounded-md bg-secondary/40 p-0.5">
                        <div
                          className="flex flex-col-reverse w-full rounded-sm overflow-hidden transition-all duration-300"
                          style={{ height: `${barHeight}px` }}
                        >
                          {mPct > 0 && <div className="w-full bg-indigo-500" style={{ height: `${mPct}%` }} />}
                          {sPct > 0 && <div className="w-full bg-emerald-500" style={{ height: `${sPct}%` }} />}
                          {supPct > 0 && <div className="w-full bg-violet-500" style={{ height: `${supPct}%` }} />}
                        </div>
                      </div>
                      <p className="mt-1.5 text-[11px] text-muted-foreground whitespace-nowrap">{d}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* AI Agent Telemetry & Reliability */}
            <div className="rounded-lg border border-border bg-card p-4 space-y-4">
              <div>
                <h3 className="text-sm font-medium">Agent Fleet Health</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Autonomous execution and top active agents</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Workflow Success Rate</span>
                  <span className="font-semibold text-foreground">
                    {rate !== undefined && rate !== null ? `${rate}%` : '100%'}
                  </span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full bg-emerald-500"
                    style={{ width: `${rate !== undefined && rate !== null ? rate : 100}%` }}
                  />
                </div>

                <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
                  <div className="rounded-md border border-border/50 bg-secondary/30 p-2">
                    <span className="text-muted-foreground text-[10px]">Total Runs</span>
                    <p className="font-semibold text-sm mt-0.5">{flowPerf.total_runs || 0}</p>
                  </div>
                  <div className="rounded-md border border-border/50 bg-secondary/30 p-2">
                    <span className="text-muted-foreground text-[10px]">AI Compute</span>
                    <p className="font-semibold text-sm mt-0.5">
                      ${Number(flowPerf.ai_cost || 0).toFixed(3)}
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-border/60">
                  <p className="text-[11px] font-medium text-muted-foreground mb-2">Most Active Autonomous Agents</p>
                  {sortedAgents.length === 0 ? (
                    <p className="text-xs text-muted-foreground py-2 text-center">No agent executions logged yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {sortedAgents.map(([agent, count]) => (
                        <div key={agent} className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-1.5 truncate">
                            <Bot className="size-3.5 text-primary shrink-0" />
                            <span className="truncate font-medium">{agent}</span>
                          </div>
                          <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground font-semibold">
                            {count as number} actions
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 4: OPERATIONAL ACTION HUB */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Needs a decision */}
        <section className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold flex items-center gap-1.5">
              <Inbox className="size-4 text-primary" /> Needs a decision
            </h2>
            <span className="text-xs text-muted-foreground">{pending} awaiting review</span>
          </div>
          <div className="divide-y divide-border max-h-[380px] overflow-y-auto">
            {pending === 0 && (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">Nothing is waiting for decision.</p>
            )}
            {posts.slice(0, 6).map((post) => (
              <div key={post.id} className="space-y-2 px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <StatusBadge status={post.platform || 'review'} />
                  <span className="text-xs text-muted-foreground">{post.day ? `Day ${post.day}` : 'Post'}</span>
                </div>
                <p className="line-clamp-2 text-sm">{post.content}</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => handleRejectPost(post.id)}>
                    Reject
                  </Button>
                  <Button size="sm" onClick={() => handleApprovePost(post.id)}>
                    Approve
                  </Button>
                </div>
              </div>
            ))}
            {leads.slice(0, 4).map((lead) => (
              <div key={lead.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <div>
                  <p className="font-medium">{lead.name}</p>
                  <p className="text-xs text-muted-foreground">{lead.company}</p>
                </div>
                <StatusBadge status={lead.source || lead.status} />
              </div>
            ))}
          </div>
        </section>

        {/* Live Activity Stream */}
        <section className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="text-sm font-semibold flex items-center gap-1.5">
              <Activity className="size-4 text-muted-foreground" /> Activity Stream
            </h2>
            <span className="text-xs text-muted-foreground">Real-time actions</span>
          </div>
          <div className="divide-y divide-border max-h-[380px] overflow-y-auto">
            {timeline.length === 0 && (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">No activity recorded yet.</p>
            )}
            {timeline.slice(0, 8).map((log) => (
              <div key={log.id} className="px-4 py-3">
                <p className="text-sm">
                  <span className="font-medium text-foreground">{log.agent_name}</span>
                  <span className="text-muted-foreground"> · {log.action}</span>
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{log.description}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Installed Apps Marketplace Ribbon */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold flex items-center gap-1.5">
            <Layers className="size-4 text-primary" /> Installed Agent Packs
          </h2>
          <Button variant="outline" size="sm" onClick={() => setActiveView('marketplace')}>
            Browse Marketplace
          </Button>
        </div>
        {apps.length === 0 ? (
          <EmptyState
            title="No apps installed"
            description="Install a marketplace pack when you want an automated agent workflow in this workspace."
            action={<Button onClick={() => setActiveView('marketplace')}>Browse marketplace</Button>}
          />
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {apps.map((app) => (
              <div
                key={app.id}
                className="flex items-center justify-between rounded-lg border border-border bg-card px-3 py-3"
              >
                <p className="truncate text-sm font-medium">{app.app_name}</p>
                <Button variant="ghost" size="sm" onClick={() => uninstallApp(app.app_name)}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}


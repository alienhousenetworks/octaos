'use client';

import React, { useState, useEffect } from 'react';
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
  Briefcase,
  Cpu,
  Clock,
  Building2,
  Calendar,
  Database,
  Coins,
  Loader2,
} from 'lucide-react';
import PageHeader from '@/components/shell/page-header';
import StatusBadge from '@/components/shell/status-badge';
import { EmptyState } from '@/components/shell/states';
import KpiMetricCard from '@/components/analytics/kpi-metric-card';
import StackedBarChart, { CategoryDef, StackedDataPoint } from '@/components/analytics/stacked-bar-chart';
import LeaderboardCard, { LeaderboardItem } from '@/components/analytics/leaderboard-card';
import ReliabilityGauge from '@/components/analytics/reliability-gauge';
import RoiPanel from '@/components/analytics/roi-panel';
import AgentDirectoryView from '@/features/workforce/agent-directory-view';

interface DashboardViewProps {
  metrics: any;
  timeline: any[];
  queue: { posts: any[]; leads: any[] };
  apps: any[];
  setActiveView: (view: string) => void;
  uninstallApp: (appName: string) => Promise<void>;
  handleApprovePost: (postId: string) => Promise<void>;
  handleRejectPost: (postId: string) => Promise<void>;
  API_URL?: string;
  fetchWithAuth?: (url: string, options?: RequestInit) => Promise<Response>;
  token?: string | null;
}

type DepartmentTab = 'executive' | 'sales' | 'marketing' | 'support' | 'ai_platform' | 'hr';
type PeriodTab = '7d' | '14d' | '30d';

function formatTokens(val: number): string {
  if (!val || val === 0) return '0';
  if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `${Math.round(val / 1_000)}K`;
  return `${val}`;
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
  API_URL,
  fetchWithAuth,
  token,
}: DashboardViewProps) {
  const [homeView, setHomeView] = useState<'workforce' | 'analytics'>('workforce');
  const [selectedDept, setSelectedDept] = useState<DepartmentTab>('executive');
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodTab>('7d');
  const [hideRevenue, setHideRevenue] = useState(false);
  const [currentMetrics, setCurrentMetrics] = useState<any>(metrics || {});
  const [loadingPeriod, setLoadingPeriod] = useState(false);

  // Sync if parent updates metrics prop
  useEffect(() => {
    if (metrics) {
      setCurrentMetrics(metrics);
    }
  }, [metrics]);

  // Fetch updated period metrics dynamically when selectedPeriod changes
  useEffect(() => {
    if (!fetchWithAuth || !API_URL) return;
    let isMounted = true;
    setLoadingPeriod(true);
    fetchWithAuth(`${API_URL}/dashboard/metrics?period=${selectedPeriod}`)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setCurrentMetrics(data);
        }
      })
      .catch((err) => console.error('Failed to fetch period metrics', err))
      .finally(() => {
        if (isMounted) setLoadingPeriod(false);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedPeriod, API_URL, fetchWithAuth]);

  const posts = queue?.posts || [];
  const leads = queue?.leads || [];
  const pending = posts.length + leads.length;

  // Primary Business Metrics & Harvested Data
  const rate: number | null = typeof currentMetrics?.automation_success_rate === 'number' ? currentMetrics.automation_success_rate : null;
  const revenue = currentMetrics?.revenue_impact ?? 0;
  const pipelineVal = currentMetrics?.pipeline_value ?? 0;
  const aiCost = currentMetrics?.ai_cost ?? 0;

  // Real Token Intelligence from Backend
  const tokenUsage = currentMetrics?.token_usage || {
    total_requests: 0,
    total_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    cached_tokens: 0,
    cache_hit_rate: 0,
    cache_hits_count: 0,
    blended_cost_per_m: 0,
  };

  // Sparklines and Deltas from backend
  const sparklines = currentMetrics?.sparklines || {
    requests: [],
    tokens: [],
    cached: [],
    cost: [],
    dates: [],
  };

  const deltas = currentMetrics?.deltas || {
    requests: null,
    tokens: null,
    cost: null,
    cache_hit_rate: null,
    blended_cost_per_m: null,
    tasks: null,
    leads: null,
    posts: null,
    tickets: null,
    revenue: null,
    pipeline: null,
    candidates: null,
  };

  // Cross-Vertical Structured Analytics from backend
  const funnel = currentMetrics?.funnel || {
    captured: currentMetrics?.leads_generated || leads.length,
    contacted: Math.max(0, (currentMetrics?.leads_generated || leads.length) - (currentMetrics?.lead_metrics?.uncontacted || 0)),
    qualified: 0,
    converted: 0,
  };

  const ticketData = currentMetrics?.ticket_analytics || {
    open: 0,
    pending_human: 0,
    resolved: Number(currentMetrics?.tickets_resolved || 0),
    sla_compliance: 100,
    sla_breach_rate: 0,
    autonomous_deflection_rate: 0,
    avg_resolution_latency_min: 0,
  };

  const leadMetrics = currentMetrics?.lead_metrics || {
    total: Number(currentMetrics?.leads_generated || 0),
    unassigned: 0,
    uncontacted: 0,
    conversion_rate: 0,
    wow_change: deltas.leads ?? null,
  };

  const marketingMetrics = currentMetrics?.marketing_metrics || {
    total_posts: Number(currentMetrics?.posts_published || 0),
    total_impressions: 0,
    avg_engagement_rate: 0,
    brand_citation_rate: 0,
  };

  const hrMetrics = currentMetrics?.hr_metrics || {
    candidates_sourced: Number(currentMetrics?.candidates_sourced || 0),
    screening_pass_rate: 0,
    interviews_scheduled: Number(currentMetrics?.interviews_scheduled || 0),
    time_to_screen_hours: 0,
    hiring_value_created: 0,
  };

  // Reliability & Failure-to-Success Data from live backend
  const reliability = currentMetrics?.reliability || {
    total_runs: tokenUsage.total_requests || 0,
    succeeded: 0,
    recovered_on_retry: 0,
    waiting_approval: pending,
    terminal_failed: 0,
    success_rate: rate,
    error_causes: [],
  };

  // Financial ROI Intelligence from live backend
  const roiIntel = currentMetrics?.roi_intelligence || {
    total_spend: aiCost,
    labor_value_usd: 0,
    hours_saved: 0,
    net_roi_multiple: 0,
    won_revenue: revenue,
    unit_economics: {
      cost_per_lead: null,
      cost_per_ticket: null,
      cost_per_campaign: null,
      blended_per_million_ops: tokenUsage.blended_cost_per_m || 0,
    },
  };

  // Leaderboards from live backend
  const leaderboards = currentMetrics?.leaderboards || {
    top_models: [],
    top_apps: [],
    top_agents: [],
  };

  // Real Work-Type Stacked Chart Data
  const workTypeCategories: CategoryDef[] = [
    { key: 'marketing', label: 'Marketing', color: '#7888D9' },
    { key: 'finance', label: 'Finance', color: '#64B99A' },
    { key: 'sales', label: 'Sales', color: '#75AFCB' },
    { key: 'general', label: 'General / Ops', color: '#AAB5C4' },
    { key: 'support', label: 'Support', color: '#D9AD68' },
  ];

  const workTypeData: StackedDataPoint[] = currentMetrics?.request_volume_by_worktype || [];

  // Token Breakdown Data
  const tokenBreakdownCategories: CategoryDef[] = [
    { key: 'prompt', label: 'Prompt Tokens', color: '#75AFCB' },
    { key: 'completion', label: 'Completion Tokens', color: '#7888D9' },
    { key: 'cached', label: 'Cached / Reasoning', color: '#64B99A' },
  ];

  const tokenBreakdownData: StackedDataPoint[] = currentMetrics?.token_breakdown_series || [];

  // Prompt Token Caching Data
  const promptCachingCategories: CategoryDef[] = [
    { key: 'uncached', label: 'Uncached', color: '#414C5A' },
    { key: 'cached', label: 'Cached', color: '#64B99A' },
  ];

  const promptCachingData: StackedDataPoint[] = currentMetrics?.prompt_caching_series || [];

  // Request Volume by Model dynamically derived from active top models
  const dynamicModelPalette = ['#7888D9', '#64B99A', '#75AFCB', '#D9AD68', '#AAB5C4', '#D9828B'];
  const modelCategories: CategoryDef[] =
    currentMetrics?.top_model_names && currentMetrics.top_model_names.length > 0
      ? currentMetrics.top_model_names.map((name: string, idx: number) => ({
          key: name,
          label: name.split('/').pop() || name,
          color: dynamicModelPalette[idx % dynamicModelPalette.length],
        }))
      : [
          { key: 'gemini', label: 'Gemini', color: '#10B981' },
          { key: 'llama', label: 'Llama', color: '#EC4899' },
          { key: 'claude', label: 'Claude', color: '#38BDF8' },
        ];

  const modelData: StackedDataPoint[] = currentMetrics?.request_volume_by_model || [];

  // Department Option Menu configuration
  const departmentOptions: { id: DepartmentTab; label: string; icon: React.ReactNode }[] = [
    { id: 'executive', label: 'Executive Cockpit', icon: <Target className="h-3.5 w-3.5" /> },
    { id: 'sales', label: 'Sales & Revenue', icon: <TrendingUp className="h-3.5 w-3.5" /> },
    { id: 'marketing', label: 'Marketing & SEO', icon: <Share2 className="h-3.5 w-3.5" /> },
    { id: 'support', label: 'Customer Support', icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
    { id: 'ai_platform', label: 'AI & Infra Platform', icon: <Cpu className="h-3.5 w-3.5" /> },
    { id: 'hr', label: 'People & HR', icon: <Briefcase className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-in fade-in duration-300">
      {/* Top Workforce vs Analytics Switcher */}
      <div className="flex items-center justify-between border-b border-border/80 pb-4">
        <div className="flex items-center gap-1.5 rounded-xl border border-border bg-card/60 p-1 text-xs backdrop-blur-md">
          <button
            type="button"
            onClick={() => setHomeView('workforce')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 font-semibold transition-all ${
              homeView === 'workforce'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Bot className="size-4" />
            AI Workforce
          </button>
          <button
            type="button"
            onClick={() => setHomeView('analytics')}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 font-semibold transition-all ${
              homeView === 'analytics'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <BarChart3 className="size-4" />
            Executive Analytics
          </button>
        </div>
      </div>

      {homeView === 'workforce' ? (
        <AgentDirectoryView
          API_URL={API_URL || ''}
          fetchWithAuth={fetchWithAuth || (async () => new Response())}
          token={token || null}
          onSelectAgent={(agentId) => setActiveView(`agents/${agentId}`)}
        />
      ) : (
        <>
          {/* Header with Quick Actions & Live Indicator */}
          <PageHeader
        title="Enterprise Intelligence Cockpit"
        description="Comprehensive real-time telemetry from token volume and task velocity to multi-channel execution and business ROI."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant={pending > 0 ? 'default' : 'outline'}
              onClick={() => setActiveView('approvals')}
              className="relative shadow-sm"
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

      {/* DEPARTMENT & TIME-PERIOD OPTIONS MENU */}
      <div className="flex flex-col gap-3 rounded-xl border border-border/70 bg-card/60 p-2.5 backdrop-blur-md sm:flex-row sm:items-center sm:justify-between">
        {/* Department Option Tabs */}
        <div className="flex flex-wrap items-center gap-1">
          {departmentOptions.map((dept) => {
            const isActive = selectedDept === dept.id;
            return (
              <button
                key={dept.id}
                type="button"
                onClick={() => setSelectedDept(dept.id)}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-secondary/70 hover:text-foreground'
                }`}
              >
                {dept.icon}
                {dept.label}
              </button>
            );
          })}
        </div>

        {/* Time-Range Selector & Live Telemetry Pill */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <div className="flex items-center rounded-lg border border-border/70 bg-background/60 p-0.5 text-xs">
            {(['7d', '14d', '30d'] as PeriodTab[]).map((period) => (
              <button
                key={period}
                type="button"
                onClick={() => setSelectedPeriod(period)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium uppercase transition-colors ${
                  selectedPeriod === period
                    ? 'bg-secondary text-foreground font-bold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {period}
              </button>
            ))}
          </div>

          <div className="hidden sm:flex items-center gap-1.5 rounded-lg border border-border/40 bg-background/40 px-2.5 py-1 text-[11px] text-muted-foreground">
            {loadingPeriod ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin text-primary" />
                <span>Updating telemetry...</span>
              </>
            ) : (
              <>
                <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>Telemetry live</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* SECTION 1: TOKEN & INVOCATION VELOCITY HERO STRIP */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Coins className="h-3.5 w-3.5 text-primary" /> Token & Execution Velocity
          </span>
          <span className="text-[11px] font-mono text-muted-foreground">
            {tokenUsage.total_requests.toLocaleString()} logged operations · {formatTokens(tokenUsage.total_tokens)} tok
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiMetricCard
            label="Requests"
            value={formatTokens(tokenUsage.total_requests)}
            sparklineData={sparklines.requests}
            deltaPct={deltas.requests}
            deltaText="vs prev period"
            hint="Total completed API calls"
            onExplore={() => setActiveView('orchestrator')}
          />
          <KpiMetricCard
            label="Token volume"
            value={formatTokens(tokenUsage.total_tokens)}
            sparklineData={sparklines.tokens}
            deltaPct={deltas.tokens}
            deltaText="vs prev period"
            hint="Prompt + completion volume"
            onExplore={() => setActiveView('ai_optimization')}
          />
          <KpiMetricCard
            label="Cache hit rate"
            value={`${tokenUsage.cache_hit_rate}%`}
            sparklineData={sparklines.cached}
            deltaPct={deltas.cache_hit_rate}
            deltaText="vs prev period"
            hint={`${tokenUsage.cache_hits_count || 0} cache hits logged`}
          />
          <KpiMetricCard
            label="Blended $/1M"
            value={`$${Number(tokenUsage.blended_cost_per_m || 0).toFixed(2)}`}
            sparklineData={sparklines.cost}
            deltaPct={deltas.blended_cost_per_m}
            deltaText="vs prev period"
            hint="Blended operational price"
          />
        </div>
      </div>

      {/* SECTION 2: DEPARTMENT-SPECIFIC BUSINESS KPI STRIP */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5 text-emerald-400" /> Operational Outcomes & Growth
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {selectedDept === 'executive' && (
            <>
              <KpiMetricCard
                label="Labor Value Generated"
                value={`$${Math.round(roiIntel.labor_value_usd || 0).toLocaleString()}`}
                sparklineData={sparklines.requests}
                deltaPct={deltas.tasks}
                deltaText="vs prev period"
                hint="Equivalent workforce savings"
                onExplore={() => setActiveView('ceo')}
              />
              <KpiMetricCard
                label="Net ROI Multiple"
                value={roiIntel.net_roi_multiple > 0 ? `${roiIntel.net_roi_multiple}x` : '0x'}
                sparklineData={sparklines.cost}
                deltaPct={deltas.revenue}
                deltaText="efficiency gain"
                hint="Return over AI compute"
                onExplore={() => setActiveView('ai_optimization')}
              />
              <KpiMetricCard
                label="Autonomous Success"
                value={rate === null ? '—' : `${rate}%`}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="vs prev period"
                hint={reliability.total_runs > 0 ? `${reliability.succeeded}/${reliability.total_runs} tasks clean` : 'No execution data yet'}
                onExplore={() => setActiveView('orchestrator')}
              />
              <KpiMetricCard
                label="Workforce Hours Saved"
                value={`${Math.round(roiIntel.hours_saved || 0)} hrs`}
                sparklineData={sparklines.requests}
                deltaPct={deltas.tasks}
                deltaText="vs prev period"
                hint="Autonomous agent execution"
              />
              <KpiMetricCard
                label="Active Pipeline"
                value={`$${Number(pipelineVal).toLocaleString()}`}
                sparklineData={sparklines.tokens}
                deltaPct={deltas.pipeline}
                deltaText="pipeline velocity"
                hint="Active sales deals"
                onExplore={() => setActiveView('deal_rooms')}
              />
            </>
          )}

          {selectedDept === 'sales' && (
            <>
              <KpiMetricCard
                label="Closed Won Revenue"
                value={
                  <span className="inline-flex items-center gap-1.5">
                    {hideRevenue ? '••••' : `$${Number(revenue).toLocaleString()}`}
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
                sparklineData={sparklines.requests}
                deltaPct={deltas.revenue}
                deltaText="vs prev period"
                hint="Attributed closed sales"
                onExplore={() => setActiveView('sales')}
              />
              <KpiMetricCard
                label="Active Pipeline Value"
                value={`$${Number(pipelineVal).toLocaleString()}`}
                sparklineData={sparklines.tokens}
                deltaPct={deltas.pipeline}
                deltaText="pipeline velocity"
                hint="Active deals in flight"
                onExplore={() => setActiveView('deal_rooms')}
              />
              <KpiMetricCard
                label="Total Indexed Leads"
                value={leadMetrics.total.toLocaleString()}
                sparklineData={sparklines.requests}
                deltaPct={deltas.leads}
                deltaText="vs prev period"
                hint={`${leadMetrics.conversion_rate}% conversion rate`}
                onExplore={() => setActiveView('sales')}
              />
              <KpiMetricCard
                label="Cost per Qualified Lead"
                value={
                  roiIntel.unit_economics?.cost_per_lead !== undefined && roiIntel.unit_economics?.cost_per_lead !== null
                    ? `$${Number(roiIntel.unit_economics.cost_per_lead).toFixed(2)}`
                    : '—'
                }
                sparklineData={sparklines.cost}
                deltaPct={null}
                isNegativeGood={true}
                deltaText="unit efficiency"
                hint="Enrichment & outreach cost"
              />
              <KpiMetricCard
                label="Qualified Opportunities"
                value={funnel.qualified || 0}
                sparklineData={sparklines.requests}
                deltaPct={deltas.leads}
                deltaText="vs prev period"
                hint="Meeting booked or SQL"
                onExplore={() => setActiveView('sales')}
              />
            </>
          )}

          {selectedDept === 'marketing' && (
            <>
              <KpiMetricCard
                label="Total Impressions"
                value={marketingMetrics.total_impressions.toLocaleString()}
                sparklineData={sparklines.tokens}
                deltaPct={deltas.posts}
                deltaText="vs prev period"
                hint="Cross-platform social reach"
                onExplore={() => setActiveView('campaigns')}
              />
              <KpiMetricCard
                label="Published Content Posts"
                value={marketingMetrics.total_posts.toLocaleString()}
                sparklineData={sparklines.requests}
                deltaPct={deltas.posts}
                deltaText="vs prev period"
                hint="Autonomous campaigns"
                onExplore={() => setActiveView('campaigns')}
              />
              <KpiMetricCard
                label="Avg Engagement Rate"
                value={`${marketingMetrics.avg_engagement_rate}%`}
                sparklineData={sparklines.tokens}
                deltaPct={null}
                deltaText="interaction boost"
                hint="Clicks, replies & citations"
              />
              <KpiMetricCard
                label="Cost per Published Post"
                value={
                  roiIntel.unit_economics?.cost_per_campaign !== undefined && roiIntel.unit_economics?.cost_per_campaign !== null
                    ? `$${Number(roiIntel.unit_economics.cost_per_campaign).toFixed(2)}`
                    : '—'
                }
                sparklineData={sparklines.cost}
                deltaPct={null}
                isNegativeGood={true}
                deltaText="vs prev period"
                hint="Generation & distribution"
              />
              <KpiMetricCard
                label="Brand Citation Velocity"
                value={`${marketingMetrics.brand_citation_rate ?? 0}%`}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="engine visibility"
                hint="AI engine presence rate"
              />
            </>
          )}

          {selectedDept === 'support' && (
            <>
              <KpiMetricCard
                label="Tickets Resolved"
                value={ticketData.resolved.toLocaleString()}
                sparklineData={sparklines.requests}
                deltaPct={deltas.tickets}
                deltaText="vs prev period"
                hint="Closed customer issues"
                onExplore={() => setActiveView('support')}
              />
              <KpiMetricCard
                label="Autonomous Deflection"
                value={`${ticketData.autonomous_deflection_rate ?? 0}%`}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="deflection rate"
                hint="Zero human touch needed"
                onExplore={() => setActiveView('support')}
              />
              <KpiMetricCard
                label="Support SLA Compliance"
                value={`${ticketData.sla_compliance}%`}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="within agreement"
                hint={`${ticketData.open || 0} open tickets pending`}
              />
              <KpiMetricCard
                label="Cost per Resolved Ticket"
                value={
                  roiIntel.unit_economics?.cost_per_ticket !== undefined && roiIntel.unit_economics?.cost_per_ticket !== null
                    ? `$${Number(roiIntel.unit_economics.cost_per_ticket).toFixed(2)}`
                    : '—'
                }
                sparklineData={sparklines.cost}
                deltaPct={null}
                isNegativeGood={true}
                deltaText="vs prev period"
                hint="Tier-1 support efficiency"
              />
              <KpiMetricCard
                label="Avg Resolution Latency"
                value={ticketData.avg_resolution_latency_min > 0 ? `${ticketData.avg_resolution_latency_min}m` : '—'}
                sparklineData={sparklines.requests}
                deltaPct={null}
                isNegativeGood={true}
                deltaText="faster turnaround"
                hint="From receipt to resolution"
              />
            </>
          )}

          {selectedDept === 'ai_platform' && (
            <>
              <KpiMetricCard
                label="Token Volume"
                value={formatTokens(tokenUsage.total_tokens)}
                sparklineData={sparklines.tokens}
                deltaPct={deltas.tokens}
                deltaText="vs prev period"
                hint="Prompt + completion volume"
                onExplore={() => setActiveView('ai_optimization')}
              />
              <KpiMetricCard
                label="Context Cache Hit Rate"
                value={`${tokenUsage.cache_hit_rate}%`}
                sparklineData={sparklines.cached}
                deltaPct={deltas.cache_hit_rate}
                deltaText="cache reuse"
                hint="Saves LLM tokens"
              />
              <KpiMetricCard
                label="Blended $/1M Tokens"
                value={`$${Number(tokenUsage.blended_cost_per_m || 0).toFixed(2)}`}
                sparklineData={sparklines.cost}
                deltaPct={deltas.blended_cost_per_m}
                isNegativeGood={true}
                deltaText="cost per million"
                hint="Blended model pricing"
              />
              <KpiMetricCard
                label="Tool Execution Success"
                value={`${rate}%`}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="reliability"
                hint="API & DB tools executed"
                onExplore={() => setActiveView('orchestrator')}
              />
              <KpiMetricCard
                label="Active Models"
                value={leaderboards.top_models.length}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="model fleet"
                hint="Active LLMs in workload"
                onExplore={() => setActiveView('ai_optimization')}
              />
            </>
          )}

          {selectedDept === 'hr' && (
            <>
              <KpiMetricCard
                label="Candidates Sourced"
                value={hrMetrics.candidates_sourced.toLocaleString()}
                sparklineData={sparklines.requests}
                deltaPct={deltas.candidates}
                deltaText="vs prev period"
                hint="Indexed talent profiles"
                onExplore={() => setActiveView('hr')}
              />
              <KpiMetricCard
                label="Screening Pass Rate"
                value={`${hrMetrics.screening_pass_rate}%`}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="qualification rate"
                hint="Automated skill validation"
              />
              <KpiMetricCard
                label="Interviews Scheduled"
                value={hrMetrics.interviews_scheduled.toLocaleString()}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="vs prev period"
                hint="Calendar sync automated"
                onExplore={() => setActiveView('hr')}
              />
              <KpiMetricCard
                label="Time to Screen"
                value={hrMetrics.time_to_screen_hours > 0 ? `${hrMetrics.time_to_screen_hours}h` : '—'}
                sparklineData={sparklines.requests}
                deltaPct={null}
                isNegativeGood={true}
                deltaText="turnaround"
                hint="Avg turnaround time"
              />
              <KpiMetricCard
                label="Hiring Value Created"
                value={`$${Math.round(hrMetrics.hiring_value_created).toLocaleString()}`}
                sparklineData={sparklines.requests}
                deltaPct={null}
                deltaText="recruiting savings"
                hint="Saved agency fees"
              />
            </>
          )}
        </div>
      </div>

      {/* SECTION 3: REQUEST VOLUME BY WORK TYPE */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column (2 spans): Request Volume by Work Type Chart */}
        <div className="lg:col-span-2">
          <StackedBarChart
            title="Request Volume by Work Type"
            subtitle="Live distribution across Marketing, Sales, Support, Finance, and General Operations"
            categories={workTypeCategories}
            data={workTypeData}
            yAxisFormatter={(v) => `${v}`}
            onExplore={() => setActiveView('orchestrator')}
          />
        </div>

        {/* Right Column (1 span): Top Apps / Work Type Leaderboard */}
        <div className="space-y-6">
          <LeaderboardCard
            title="Top Work Types by Invocations"
            items={leaderboards.top_apps || []}
            onExplore={() => setActiveView('teams')}
          />
        </div>
      </div>

      {/* SECTION 4: TOKEN DEEP DIVE */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left: Token Breakdown */}
        <StackedBarChart
          title="Token Breakdown"
          subtitle="Prompt Tokens vs. Completion Tokens vs. Cached / Reasoning Tokens"
          categories={tokenBreakdownCategories}
          data={tokenBreakdownData}
          yAxisFormatter={(v) => formatTokens(v)}
          onExplore={() => setActiveView('ai_optimization')}
        />

        {/* Right: Prompt Token Caching */}
        <StackedBarChart
          title="Prompt Token Caching"
          subtitle="Uncached Prompt Tokens vs. Cached Prompt Tokens over time"
          categories={promptCachingCategories}
          data={promptCachingData}
          yAxisFormatter={(v) => formatTokens(v)}
          onExplore={() => setActiveView('ai_optimization')}
        />
      </div>

      {/* SECTION 5: REQUEST VOLUME BY MODEL */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Column (2 spans): Model Distribution Chart */}
        <div className="lg:col-span-2">
          <StackedBarChart
            title="Request Volume by Model Architecture"
            subtitle="Execution throughput across foundation model fleet"
            categories={modelCategories}
            data={modelData}
            yAxisFormatter={(v) => `${v}`}
            onExplore={() => setActiveView('ai_optimization')}
          />
        </div>

        {/* Right Column (1 span): Top Models Leaderboard */}
        <div className="space-y-6">
          <LeaderboardCard
            title="Top Foundation Models by Usage"
            items={leaderboards.top_models || []}
            onExplore={() => setActiveView('ai_optimization')}
          />
        </div>
      </div>

      {/* SECTION 6: EXECUTION RELIABILITY & FAILURE-TO-SUCCESS GAUGE */}
      <ReliabilityGauge
        totalRuns={reliability.total_runs}
        succeeded={reliability.succeeded}
        recoveredOnRetry={reliability.recovered_on_retry}
        waitingApproval={reliability.waiting_approval}
        terminalFailed={reliability.terminal_failed}
        errorCauses={reliability.error_causes}
      />

      {/* SECTION 7: FINANCIAL ROI & LABOR VALUE PANEL */}
      <RoiPanel
        totalSpend={roiIntel.total_spend}
        laborValueUsd={roiIntel.labor_value_usd}
        hoursSaved={roiIntel.hours_saved}
        netRoiMultiple={roiIntel.net_roi_multiple}
        wonRevenue={revenue}
        unitEconomics={{
          costPerLead: roiIntel.unit_economics?.cost_per_lead ?? roiIntel.unit_economics?.costPerLead ?? null,
          costPerTicket: roiIntel.unit_economics?.cost_per_ticket ?? roiIntel.unit_economics?.costPerTicket ?? null,
          costPerCampaign: roiIntel.unit_economics?.cost_per_campaign ?? roiIntel.unit_economics?.costPerCampaign ?? null,
          blendedPerMillionOps: roiIntel.unit_economics?.blended_per_million_ops ?? roiIntel.unit_economics?.blendedPerMillionOps ?? tokenUsage.blended_cost_per_m ?? null,
        }}
        onExplore={() => setActiveView('ai_optimization')}
      />

      {/* SECTION 8: OPERATIONAL ACTION HUB (Preserved) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Needs a decision */}
        <section className="rounded-xl border border-border/70 bg-card/60 p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-border/40 pb-3">
            <h2 className="text-sm font-semibold flex items-center gap-1.5 text-foreground">
              <Inbox className="size-4 text-primary" /> Needs a Decision
            </h2>
            <span className="text-xs text-muted-foreground">{pending} awaiting review</span>
          </div>
          <div className="divide-y divide-border/30 max-h-[380px] overflow-y-auto">
            {pending === 0 && (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">Nothing is waiting for decision.</p>
            )}
            {posts.slice(0, 6).map((post) => (
              <div key={post.id} className="space-y-2 py-3">
                <div className="flex items-center justify-between gap-2">
                  <StatusBadge status={post.platform || 'review'} />
                  <span className="text-xs text-muted-foreground">{post.day ? `Day ${post.day}` : 'Post'}</span>
                </div>
                <p className="line-clamp-2 text-sm text-foreground">{post.content}</p>
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
              <div key={lead.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-medium text-foreground">{lead.name}</p>
                  <p className="text-xs text-muted-foreground">{lead.company}</p>
                </div>
                <StatusBadge status={lead.source || lead.status} />
              </div>
            ))}
          </div>
        </section>

        {/* Live Activity Stream */}
        <section className="rounded-xl border border-border/70 bg-card/60 p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-border/40 pb-3">
            <h2 className="text-sm font-semibold flex items-center gap-1.5 text-foreground">
              <Activity className="size-4 text-emerald-400" /> Real-Time Telemetry Stream
            </h2>
            <span className="text-xs text-muted-foreground">Live actions</span>
          </div>
          <div className="divide-y divide-border/30 max-h-[380px] overflow-y-auto">
            {timeline.length === 0 && (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">No activity recorded yet.</p>
            )}
            {timeline.slice(0, 8).map((log) => (
              <div key={log.id} className="py-2.5">
                <p className="text-sm">
                  <span className="font-semibold text-foreground">{log.agent_name}</span>
                  <span className="text-muted-foreground"> · {log.action}</span>
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{log.description}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* SECTION 9: INSTALLED AGENT PACKS MARKETPLACE RIBBON (Preserved) */}
      <section className="rounded-xl border border-border/70 bg-card/60 p-5 shadow-sm backdrop-blur-md space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold flex items-center gap-1.5 text-foreground">
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
                className="flex items-center justify-between rounded-lg border border-border/50 bg-background/50 px-3 py-3 transition-colors hover:border-border"
              >
                <p className="truncate text-sm font-medium text-foreground">{app.app_name}</p>
                <Button variant="ghost" size="sm" onClick={() => uninstallApp(app.app_name)}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
        )}
      </section>
        </>
      )}
    </div>
  );
}

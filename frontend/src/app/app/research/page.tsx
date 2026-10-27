'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileSearch,
  Globe2,
  Loader2,
  Radar,
  RefreshCw,
  Search,
  ShieldCheck,
} from 'lucide-react';
import { useWorkspace } from '@/lib/workspace';

type ProviderState = {
  id: string;
  configured: boolean;
  state: string;
  health: string;
};

type ResearchJobSummary = {
  job_id: string;
  status: string;
  query: string;
  created_at?: string | null;
  updated_at?: string | null;
  source_count: number;
  task_count: number;
};

type ResearchSource = {
  record_id: string;
  title: string;
  url: string;
  canonical_url?: string;
  snippet?: string;
  excerpt?: string;
  provider?: string;
  method?: string;
  published_at?: string | null;
  retrieved_at?: string | null;
  company?: string;
};

type ResearchClaim = {
  record_id: string;
  claim: string;
  passage: string;
  source_url: string;
  verification_state: string;
  freshness_ok?: boolean | null;
  notes?: string[];
};

type ResearchResult = {
  job_id: string;
  status: string;
  query: string;
  freshness?: string;
  geography?: string[];
  contacts?: Array<Record<string, unknown>>;
  extras?: Array<Record<string, unknown>>;
  methods?: Array<Record<string, unknown>>;
  tasks?: Array<Record<string, unknown>>;
  sources?: ResearchSource[];
  claims?: ResearchClaim[];
  notes?: string[];
  report?: string;
  counts?: Record<string, number>;
  usage?: Array<Record<string, unknown>>;
};

const FRESHNESS_OPTIONS = [
  { value: '24_hours', label: 'Past 24 hours' },
  { value: '7_days', label: 'Past 7 days' },
  { value: '14_days', label: 'Past 14 days' },
  { value: '30_days', label: 'Past 30 days' },
  { value: '90_days', label: 'Past 90 days' },
  { value: 'all', label: 'Any date' },
];

function statusLabel(status?: string) {
  const value = (status || 'unknown').toLowerCase();
  if (value === 'succeeded') return 'Completed';
  if (value === 'partial') return 'Partial results';
  if (value === 'failed') return 'Failed';
  if (value === 'cancelled') return 'Cancelled';
  if (value === 'running') return 'Running';
  return value.replaceAll('_', ' ');
}

function formatDate(value?: string | null) {
  if (!value) return 'Date not provided';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date not provided' : date.toLocaleString();
}

function prettyName(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function ResearchWorkspacePage() {
  const workspace = useWorkspace();
  const [query, setQuery] = useState('');
  const [geography, setGeography] = useState('India');
  const [industries, setIndustries] = useState('');
  const [buyerRoles, setBuyerRoles] = useState('');
  const [exclusions, setExclusions] = useState('');
  const [freshness, setFreshness] = useState('14_days');
  const [count, setCount] = useState('10');
  const [budget, setBudget] = useState('100');
  const [providers, setProviders] = useState<ProviderState[]>([]);
  const [jobs, setJobs] = useState<ResearchJobSummary[]>([]);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState('');
  const [providersError, setProvidersError] = useState('');

  const loadWorkspaceData = useCallback(async () => {
    if (!workspace.token) return;
    setHistoryLoading(true);
    setProvidersError('');
    try {
      const [providerResponse, jobsResponse] = await Promise.all([
        workspace.fetchWithAuth(workspace.apiUrl + '/research/providers'),
        workspace.fetchWithAuth(workspace.apiUrl + '/research/jobs?limit=20'),
      ]);
      if (providerResponse.ok) {
        const body = await providerResponse.json();
        setProviders(Array.isArray(body.providers) ? body.providers : []);
      } else {
        setProvidersError('Provider configuration could not be loaded (' + providerResponse.status + ').');
      }
      if (jobsResponse.ok) {
        const body = await jobsResponse.json();
        setJobs(Array.isArray(body.items) ? body.items : []);
      }
    } catch {
      setProvidersError('Search service could not be reached. Check the API connection and retry.');
    } finally {
      setHistoryLoading(false);
    }
  }, [workspace.token, workspace.apiUrl, workspace.fetchWithAuth]);

  useEffect(() => {
    void loadWorkspaceData();
  }, [loadWorkspaceData]);

  const sourceCount = result?.counts?.sources ?? result?.sources?.length ?? 0;
  const claimCount = result?.counts?.claims ?? result?.claims?.length ?? 0;
  const availableProviderCount = useMemo(() => providers.filter((provider) => provider.configured).length, [providers]);

  const waitForJob = async (jobId: string) => {
    let latest: ResearchResult | null = null;
    for (let attempt = 0; attempt < 45; attempt += 1) {
      const response = await workspace.fetchWithAuth(workspace.apiUrl + '/research/jobs/' + encodeURIComponent(jobId));
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : 'Research status could not be loaded (' + response.status + ').';
        throw new Error(detail);
      }
      latest = body as ResearchResult;
      setResult(latest);
      const state = (latest.status || '').toLowerCase();
      if (!['queued', 'running'].includes(state)) return latest;
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
    }
    return latest;
  };

  const openJob = async (jobId: string) => {
    setError('');
    setLoading(true);
    try {
      const response = await workspace.fetchWithAuth(workspace.apiUrl + '/research/jobs/' + encodeURIComponent(jobId));
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : 'Research history could not be opened (' + response.status + ').';
        throw new Error(detail);
      }
      setResult(body as ResearchResult);
      setQuery(String(body.query || ''));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research history could not be opened.');
    } finally {
      setLoading(false);
    }
  };

  const resumeJob = async (jobId: string) => {
    setError('');
    setLoading(true);
    try {
      const response = await workspace.fetchWithAuth(workspace.apiUrl + '/research/jobs/' + encodeURIComponent(jobId) + '/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : 'Research job could not be resumed (' + response.status + ').';
        throw new Error(detail);
      }
      await waitForJob(jobId);
      await loadWorkspaceData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research job could not be resumed.');
    } finally {
      setLoading(false);
    }
  };

  const runSearch = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanedQuery = query.trim();
    if (cleanedQuery.length < 3 || loading) return;
    setError('');
    setLoading(true);
    setResult(null);
    const splitList = (value: string) => value.split(',').map((item) => item.trim()).filter(Boolean);
    try {
      const response = await workspace.fetchWithAuth(workspace.apiUrl + '/research/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: cleanedQuery,
          count: Number(count),
          freshness,
          geography: splitList(geography),
          industries: splitList(industries),
          buyer_roles: splitList(buyerRoles),
          exclusions: splitList(exclusions),
          budget_inr: Number(budget),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string'
          ? body.detail
          : typeof body.detail?.message === 'string'
            ? body.detail.message
            : 'Research could not be completed (' + response.status + ').';
        throw new Error(detail);
      }
      const jobId = String(body.job_id || '');
      if (jobId) await waitForJob(jobId);
      else setResult(body as ResearchResult);
      await loadWorkspaceData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research could not be completed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 pb-10">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <Radar className="size-3.5" /> Shared Search Intelligence
          </div>
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Research beyond the search box.</h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground md:text-base">
            Search across configured public sources, inspect source passages, and keep research results tied to evidence. Provider configuration is shown separately from live provider health.
          </p>
        </div>
        <button type="button" onClick={() => void loadWorkspaceData()} className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-card px-3 text-sm font-medium transition hover:bg-accent">
          <RefreshCw className={'size-4 ' + (historyLoading ? 'animate-spin' : '')} /> Refresh
        </button>
      </header>

      <section className="grid gap-3 sm:grid-cols-3" aria-label="Search service overview">
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground"><Globe2 className="size-4 text-primary" /> Search providers</div>
          <div className="mt-2 text-2xl font-semibold tabular-nums">{providers.length ? availableProviderCount + ' / ' + providers.length : '—'}</div>
          <p className="mt-1 text-xs text-muted-foreground">Configured or fallback-capable sources; not a live health check.</p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground"><FileSearch className="size-4 text-primary" /> Recent investigations</div>
          <div className="mt-2 text-2xl font-semibold tabular-nums">{jobs.length}</div>
          <p className="mt-1 text-xs text-muted-foreground">Persisted search jobs available to this tenant.</p>
        </div>
        <div className="rounded-2xl border border-border bg-card p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground"><ShieldCheck className="size-4 text-primary" /> Evidence-first output</div>
          <div className="mt-2 text-2xl font-semibold">Source-linked</div>
          <p className="mt-1 text-xs text-muted-foreground">Claims and citations remain inspectable instead of being treated as guaranteed truth.</p>
        </div>
      </section>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,0.8fr)]">
        <section className="rounded-2xl border border-border bg-card p-4 md:p-6">
          <div className="mb-5 flex items-start gap-3">
            <div className="rounded-xl bg-primary/10 p-2.5 text-primary"><Search className="size-5" /></div>
            <div>
              <h2 className="text-lg font-semibold">Start an investigation</h2>
              <p className="mt-1 text-sm text-muted-foreground">Describe what you need to learn. Search depth is bounded by the budget and source availability.</p>
            </div>
          </div>
          <form onSubmit={runSearch} className="space-y-4">
            <label className="block space-y-2">
              <span className="text-sm font-medium">Research objective</span>
              <textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                minLength={3}
                maxLength={300}
                required
                rows={4}
                placeholder="Example: Compare Indian ERP vendors serving manufacturers, find public pricing and recent product changes, and cite the source for each claim."
                className="w-full resize-y rounded-xl border border-input bg-background px-3.5 py-3 text-sm leading-6 outline-none transition placeholder:text-muted-foreground/70 focus:border-primary focus:ring-2 focus:ring-primary/15"
              />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-muted-foreground">Geography (comma separated)</span>
                <input value={geography} onChange={(event) => setGeography(event.target.value)} maxLength={400} placeholder="India, United States" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary" />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-muted-foreground">Freshness</span>
                <select value={freshness} onChange={(event) => setFreshness(event.target.value)} className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary">
                  {FRESHNESS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-muted-foreground">Industries (optional)</span>
                <input value={industries} onChange={(event) => setIndustries(event.target.value)} maxLength={800} placeholder="Manufacturing, logistics" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary" />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-muted-foreground">Buyer roles (optional)</span>
                <input value={buyerRoles} onChange={(event) => setBuyerRoles(event.target.value)} maxLength={800} placeholder="CIO, Head of Operations" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary" />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-muted-foreground">Exclude terms or domains</span>
                <input value={exclusions} onChange={(event) => setExclusions(event.target.value)} maxLength={1200} placeholder="jobs, example.com" className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary" />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-muted-foreground">Maximum results</span>
                <select value={count} onChange={(event) => setCount(event.target.value)} className="h-10 w-full rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary">
                  {[5, 10, 20, 30, 50, 100].map((value) => <option key={value} value={value}>{value} results</option>)}
                </select>
              </label>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-border bg-muted/25 p-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium">Per-run budget ceiling</p>
                <p className="mt-1 text-xs text-muted-foreground">Paid providers are only used when configured and within this ceiling.</p>
              </div>
              <select value={budget} onChange={(event) => setBudget(event.target.value)} className="h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary">
                {[0, 25, 50, 100, 250, 500, 700].map((value) => <option key={value} value={value}>₹{value}</option>)}
              </select>
            </div>
            {error && <div role="alert" className="flex items-start gap-2 rounded-xl border border-destructive/25 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="mt-0.5 size-4 shrink-0" /><span>{error}</span></div>}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="max-w-md text-xs leading-5 text-muted-foreground">Public source availability varies. Unavailable providers and unsupported claims are not replaced with invented results.</p>
              <button disabled={loading || query.trim().length < 3} type="submit" className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50">
                {loading ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
                {loading ? 'Researching…' : 'Run research'}
                {!loading && <ArrowUpRight className="size-4" />}
              </button>
            </div>
          </form>
        </section>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">Provider configuration</h2>
              <span className="text-xs text-muted-foreground">No health claim</span>
            </div>
            {providersError && <p role="status" className="mt-3 text-xs text-amber-700 dark:text-amber-300">{providersError}</p>}
            <div className="mt-3 space-y-2">
              {providers.map((provider) => (
                <div key={provider.id} className="flex items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-2.5">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className={'size-2 rounded-full ' + (provider.configured ? 'bg-emerald-500' : 'bg-muted-foreground/40')} />
                    <span className="truncate text-sm font-medium">{prettyName(provider.id)}</span>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">{provider.state.replaceAll('_', ' ')}</span>
                </div>
              ))}
              {!providers.length && !providersError && <p className="py-4 text-sm text-muted-foreground">Provider state has not been returned yet.</p>}
            </div>
          </section>
          <section className="rounded-2xl border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">Recent investigations</h2>
              {historyLoading && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
            </div>
            <div className="mt-3 space-y-2">
              {jobs.map((job) => (
                <button key={job.job_id} type="button" onClick={() => void openJob(job.job_id)} className="w-full rounded-xl border border-border/70 p-3 text-left transition hover:border-primary/30 hover:bg-accent/50">
                  <div className="flex items-start justify-between gap-2">
                    <span className="line-clamp-2 text-sm font-medium">{job.query || 'Research job'}</span>
                    <ArrowUpRight className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                    <span>{statusLabel(job.status)}</span>
                    <span>{job.source_count} sources</span>
                    <span>{formatDate(job.updated_at || job.created_at)}</span>
                  </div>
                </button>
              ))}
              {!jobs.length && !historyLoading && <p className="py-3 text-sm leading-5 text-muted-foreground">Your saved investigations will appear here after a search has been stored.</p>}
            </div>
          </section>
        </aside>
      </div>

      {result && (
        <section className="space-y-4 rounded-2xl border border-border bg-card p-4 md:p-6" aria-live="polite">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 text-xs font-medium text-primary"><CheckCircle2 className="size-4" /> Research record</div>
              <h2 className="text-xl font-semibold">{result.query}</h2>
              <p className="mt-1 text-sm text-muted-foreground">Run ID: <span className="font-mono text-xs">{result.job_id}</span></p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {['running', 'failed'].includes((result.status || '').toLowerCase()) && (
                <button type="button" disabled={loading} onClick={() => void resumeJob(result.job_id)} className="inline-flex h-9 items-center gap-2 rounded-lg border border-primary/25 px-3 text-xs font-medium text-primary transition hover:bg-primary/5 disabled:opacity-50">
                  {loading ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />} Resume run
                </button>
              )}
              <span className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium"><Activity className="size-3.5" /> {statusLabel(result.status)}</span>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            {[
              ['Sources', sourceCount],
              ['Evidence claims', claimCount],
              ['Search tasks', result.counts?.tasks ?? result.tasks?.length ?? result.methods?.length ?? 0],
              ['Qualified contacts', result.counts?.qualified ?? result.contacts?.length ?? 0],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-xl border border-border bg-muted/20 p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
              </div>
            ))}
          </div>
          {result.notes?.length ? <div className="rounded-xl border border-amber-500/25 bg-amber-500/5 p-3 text-sm"><p className="font-medium">Research limitations</p><ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">{result.notes.map((note, index) => <li key={index}>{note}</li>)}</ul></div> : null}
          <div className="grid gap-5 xl:grid-cols-2">
            <div>
              <h3 className="mb-3 flex items-center gap-2 font-semibold"><Globe2 className="size-4 text-primary" /> Source documents</h3>
              <div className="space-y-3">
                {(result.sources || []).map((source) => (
                  <article key={source.record_id || source.url} className="rounded-xl border border-border/80 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <h4 className="text-sm font-semibold leading-5">{source.title || source.company || 'Untitled source'}</h4>
                      {source.url && <a href={source.url} target="_blank" rel="noreferrer" className="shrink-0 text-primary hover:underline" aria-label="Open source"><ExternalLink className="size-4" /></a>}
                    </div>
                    <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground">{source.excerpt || source.snippet || 'No extractable passage was returned.'}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {source.provider && <span className="rounded-md bg-muted px-2 py-1">{prettyName(source.provider)}</span>}
                      {source.method && <span>{prettyName(source.method)}</span>}
                      <span className="inline-flex items-center gap-1"><Clock3 className="size-3" /> Retrieved {formatDate(source.retrieved_at)}</span>
                    </div>
                    {source.url && <p className="mt-2 break-all text-xs text-primary/80">{source.url}</p>}
                  </article>
                ))}
                {!result.sources?.length && <p className="rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">No source documents were persisted for this run. Review task statuses and provider availability below.</p>}
              </div>
            </div>
            <div>
              <h3 className="mb-3 flex items-center gap-2 font-semibold"><ShieldCheck className="size-4 text-primary" /> Claims and evidence</h3>
              <div className="space-y-3">
                {(result.claims || []).map((claim, index) => (
                  <article key={claim.record_id || index} className="rounded-xl border border-border/80 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Claim {index + 1}</span>
                      <span className="rounded-md border border-border px-2 py-1 text-xs">{prettyName(claim.verification_state || 'unverified')}</span>
                    </div>
                    <p className="mt-2 text-sm font-medium leading-6">{claim.claim || 'Extracted evidence'}</p>
                    <blockquote className="mt-3 border-l-2 border-primary/40 pl-3 text-sm leading-6 text-muted-foreground">{claim.passage || 'No supporting passage was recorded.'}</blockquote>
                    {claim.source_url && <a href={claim.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 break-all text-xs text-primary hover:underline">Open supporting source <ExternalLink className="size-3 shrink-0" /></a>}
                    {claim.freshness_ok === false && <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">This source did not meet the requested freshness window.</p>}
                    {claim.notes?.length ? <ul className="mt-2 list-disc pl-4 text-xs text-muted-foreground">{claim.notes.map((note, noteIndex) => <li key={noteIndex}>{note}</li>)}</ul> : null}
                  </article>
                ))}
                {!result.claims?.length && <p className="rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">No claim-level evidence was returned. OctaOS will not fill this gap with generated facts.</p>}
              </div>
            </div>
          </div>
          {(result.tasks || result.methods)?.length ? (
            <details className="rounded-xl border border-border p-4">
              <summary className="cursor-pointer text-sm font-semibold">Inspect search execution details</summary>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-xs">
                  <thead><tr className="border-b border-border text-muted-foreground"><th className="px-2 py-2 font-medium">Method</th><th className="px-2 py-2 font-medium">Provider</th><th className="px-2 py-2 font-medium">Status</th><th className="px-2 py-2 font-medium">Query</th><th className="px-2 py-2 font-medium">Details</th></tr></thead>
                  <tbody>
                    {(result.tasks || result.methods || []).map((task, index) => (
                      <tr key={String(task.task_id || index)} className="border-b border-border/60 align-top">
                        <td className="px-2 py-2">{prettyName(String(task.method || 'web'))}</td>
                        <td className="px-2 py-2">{prettyName(String(task.provider || 'unknown'))}</td>
                        <td className="px-2 py-2">{statusLabel(String(task.status || 'unknown'))}</td>
                        <td className="max-w-xs px-2 py-2">{String(task.query || '')}</td>
                        <td className="max-w-xs px-2 py-2 text-muted-foreground">{String(task.reason || task.failure_class || '')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          ) : null}
        </section>
      )}
    </main>
  );
}

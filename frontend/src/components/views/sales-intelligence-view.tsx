'use client';

import React, { useEffect, useMemo, useState } from 'react';
import PageHeader from '@/components/shell/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface SalesIntelligenceViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

function money(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 })}`;
}

export default function SalesIntelligenceView({ token, API_URL, fetchWithAuth }: SalesIntelligenceViewProps) {
  const [sources, setSources] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [roi, setRoi] = useState<any | null>(null);
  const [query, setQuery] = useState('');
  const [budget, setBudget] = useState('');
  const [executePublic, setExecutePublic] = useState(false);
  const [plan, setPlan] = useState<any | null>(null);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [opportunity, setOpportunity] = useState<any | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sourceFilter, setSourceFilter] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!token) return;
    const [sourceRes, companyRes, roiRes] = await Promise.all([
      fetchWithAuth(`${API_URL}/sales-os/sources`),
      fetchWithAuth(`${API_URL}/sales-os/companies`),
      fetchWithAuth(`${API_URL}/sales-os/attribution/roi`),
    ]);
    if (sourceRes.ok) setSources(await sourceRes.json());
    if (companyRes.ok) setCompanies(await companyRes.json());
    if (roiRes.ok) setRoi(await roiRes.json());
  };

  useEffect(() => {
    load().catch(() => setError('Source intelligence could not be loaded.'));
  }, [token]);

  const visibleSources = useMemo(() => {
    const needle = sourceFilter.trim().toLowerCase();
    if (!needle) return sources;
    return sources.filter((source) =>
      `${source.id} ${source.name} ${source.implementation} ${source.activation_status}`.toLowerCase().includes(needle),
    );
  }, [sources, sourceFilter]);

  const openCompany = async (companyId: string) => {
    setSelectedId(companyId);
    setEvidence([]);
    setOpportunity(null);
    const [evidenceRes, opportunityRes] = await Promise.all([
      fetchWithAuth(`${API_URL}/sales-os/companies/${companyId}/evidence`),
      fetchWithAuth(`${API_URL}/sales-os/companies/${companyId}/opportunity`),
    ]);
    if (evidenceRes.ok) setEvidence(await evidenceRes.json());
    if (opportunityRes.ok) setOpportunity(await opportunityRes.json());
    if (opportunityRes.status === 404) setOpportunity(null);
  };

  const submitPlan = async () => {
    if (!query.trim()) {
      setError('Enter a company domain or search query.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        query: query.trim(),
        execute: executePublic,
        provider_keys: executePublic ? ['hn_hiring', 'dns_mx_inspect'] : undefined,
      };
      if (budget.trim() !== '') {
        const parsed = Number(budget);
        if (Number.isNaN(parsed)) {
          setError('Budget must be a number. Leave it blank when no spend is approved.');
          setBusy(false);
          return;
        }
        body.budget = parsed;
      }
      const response = await fetchWithAuth(`${API_URL}/sales-os/discovery/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setError('The discovery plan was not accepted.');
        return;
      }
      const data = await response.json();
      setPlan(data);
      await load();
      if (data.company_id) await openCompany(data.company_id);
    } catch {
      setError('The discovery plan could not be sent.');
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="mx-auto max-w-6xl">
        <PageHeader title="Source intelligence" description="Sign in to review sources, evidence, and scores." />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="Source intelligence"
        description="Accounts, evidence, and source ROI. A blank field means the value is unknown. Attribution is not a causal claim."
      />

      {error && <p className="text-sm text-destructive">{error}</p>}

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Discovery plan</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Planning does not call paid providers. Public Hacker News and DNS lookups run only when you turn that option on.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="acme.com" aria-label="Discovery query" />
          <Input value={budget} onChange={(event) => setBudget(event.target.value)} placeholder="Approved budget USD" aria-label="Approved budget" />
          <Button onClick={submitPlan} disabled={busy}>
            {busy ? 'Working' : executePublic ? 'Run public sources' : 'Plan only'}
          </Button>
        </div>
        <label className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
          <input type="checkbox" checked={executePublic} onChange={(event) => setExecutePublic(event.target.checked)} />
          Run public sources (Hacker News hiring and DNS). This makes network calls and does not spend provider credits.
        </label>
        {plan && (
          <div className="mt-4 overflow-x-auto">
            <p className="mb-2 text-sm">
              Run {plan.run_id || '—'} · {plan.status || '—'} · tier {plan.tier6_state || '—'}
            </p>
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">Provider</th>
                  <th className="py-2 pr-3 font-medium">Action</th>
                  <th className="py-2 pr-3 font-medium">Reason</th>
                  <th className="py-2 font-medium">Estimate</th>
                </tr>
              </thead>
              <tbody>
                {(plan.steps || []).slice(0, 40).map((step: any) => (
                  <tr key={`${step.provider_key}-${step.reason}`} className="border-t border-border">
                    <td className="py-2 pr-3">{step.provider_key}</td>
                    <td className="py-2 pr-3">{step.action}</td>
                    <td className="py-2 pr-3">{step.reason}</td>
                    <td className="py-2">{money(step.estimated_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Companies</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[28rem] text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">Account</th>
                  <th className="py-2 pr-3 font-medium">Score</th>
                  <th className="py-2 font-medium">Tier 6</th>
                </tr>
              </thead>
              <tbody>
                {companies.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-3 text-muted-foreground">No canonical accounts yet.</td>
                  </tr>
                )}
                {companies.map((company) => (
                  <tr key={company.id} className="border-t border-border">
                    <td className="py-2 pr-3">
                      <button type="button" className="text-left hover:underline" onClick={() => openCompany(company.id)}>
                        {company.display_name || company.canonical_domain || company.id}
                      </button>
                      <div className="text-xs text-muted-foreground">{company.canonical_domain || 'Domain unknown'}</div>
                    </td>
                    <td className="py-2 pr-3">{company.score ?? '—'}</td>
                    <td className="py-2">{company.tier6_state || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Evidence</h2>
          {selectedId && opportunity && (
            <p className="mt-2 text-sm text-muted-foreground">
              Score {opportunity.score ?? '—'} · {opportunity.score_version || 'unversioned'} · {opportunity.tier6_state || '—'}
            </p>
          )}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[28rem] text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">Source</th>
                  <th className="py-2 pr-3 font-medium">Claim</th>
                  <th className="py-2 font-medium">SHA-256</th>
                </tr>
              </thead>
              <tbody>
                {evidence.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-3 text-muted-foreground">Select an account to see stored evidence.</td>
                  </tr>
                )}
                {evidence.map((item) => (
                  <tr key={item.id} className="border-t border-border">
                    <td className="py-2 pr-3">{item.source_key}</td>
                    <td className="max-w-[16rem] truncate py-2 pr-3">{item.claim || '—'}</td>
                    <td className="py-2 font-mono text-xs" title={item.payload_hash}>{item.payload_hash?.slice(0, 12) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-semibold">Source ROI</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Causal attribution: {roi?.attribution_is_causal === false ? 'no' : roi ? String(roi.attribution_is_causal) : '—'}
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <div><dt className="text-muted-foreground">Spend</dt><dd>{money(roi?.spend)}</dd></div>
          <div><dt className="text-muted-foreground">Meetings</dt><dd>{roi?.meetings ?? '—'}</dd></div>
          <div><dt className="text-muted-foreground">Revenue</dt><dd>{money(roi?.revenue)}</dd></div>
          <div><dt className="text-muted-foreground">Sample</dt><dd>{roi?.sample_size ?? '—'}</dd></div>
        </dl>
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-sm font-semibold">Sources ({sources.length})</h2>
          <Input className="sm:max-w-xs" value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)} placeholder="Filter sources" aria-label="Filter sources" />
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-2 pr-3 font-medium">Source</th>
                <th className="py-2 pr-3 font-medium">Implementation</th>
                <th className="py-2 pr-3 font-medium">Activation</th>
                <th className="py-2 pr-3 font-medium">Callable</th>
                <th className="py-2 font-medium">Estimate</th>
              </tr>
            </thead>
            <tbody>
              {visibleSources.map((source) => (
                <tr key={source.id} className="border-t border-border">
                  <td className="py-2 pr-3">
                    <div>{source.name}</div>
                    <div className="text-xs text-muted-foreground">{source.id}</div>
                  </td>
                  <td className="py-2 pr-3">{source.implementation}</td>
                  <td className="py-2 pr-3">{source.activation_status}</td>
                  <td className="py-2 pr-3">{source.sales_os_callable ? 'yes' : 'no'}</td>
                  <td className="py-2">{money(source.estimated_cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

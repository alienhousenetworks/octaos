'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  Radar,
  MapPin,
  TrendingUp,
  Plus,
  Search,
  Navigation,
  Clock,
  Compass,
  DollarSign,
  Layers,
  Filter,
  ArrowUpRight,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RefreshCw,
  Briefcase,
  ShieldCheck,
  Building2,
  User,
  ChevronRight,
  Send,
  Calendar,
  X,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { notify } from '@/lib/notify';

interface SalesIntelligenceViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

function money(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

type SubTab = 'signals' | 'territory' | 'roi' | 'discovery';

export default function SalesIntelligenceView({
  token,
  API_URL,
  fetchWithAuth,
}: SalesIntelligenceViewProps) {
  const [activeTab, setActiveTab] = useState<SubTab>('signals');

  // ── Signals Bus State ──
  const [signalsFeed, setSignalsFeed] = useState<any[]>([]);
  const [selectedSignalAccount, setSelectedSignalAccount] = useState<any | null>(null);
  const [accountSignalsDetail, setAccountSignalsDetail] = useState<any | null>(null);
  const [signalFamilyFilter, setSignalFamilyFilter] = useState<string>('all');
  const [signalsLoading, setSignalsLoading] = useState(false);
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [ingesting, setIngesting] = useState(false);

  // Ingest Form
  const [ingestForm, setIngestForm] = useState({
    company_id: '',
    signal_type: 'funding_round',
    family: 'funding',
    summary: '',
    base_strength: 75,
    source_confidence: 0.9,
    half_life_days: 30,
    source_key: 'crunchbase',
    source_url: '',
  });

  // ── Territory Route Planner State ──
  const [repId, setRepId] = useState('rep_field_1');
  const [latitude, setLatitude] = useState(37.7749);
  const [longitude, setLongitude] = useState(-122.4194);
  const [routePlan, setRoutePlan] = useState<any | null>(null);
  const [territoryLoading, setTerritoryLoading] = useState(false);

  // ── Source ROI State ──
  const [sourceRoi, setSourceRoi] = useState<any | null>(null);
  const [roiLoading, setRoiLoading] = useState(false);

  // ── Discovery / Legacy State ──
  const [sources, setSources] = useState<any[]>([]);
  const [companies, setCompanies] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [budget, setBudget] = useState('');
  const [executePublic, setExecutePublic] = useState(false);
  const [plan, setPlan] = useState<any | null>(null);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Fetchers ──
  const fetchSignalsFeed = async () => {
    if (!token) return;
    setSignalsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/signals/feed?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setSignalsFeed(data);
      }
    } catch (err) {
      console.error('Failed to load signals feed:', err);
    } finally {
      setSignalsLoading(false);
    }
  };

  const fetchAccountSignals = async (companyId: string) => {
    if (!token || !companyId) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/signals/accounts/${companyId}`);
      if (res.ok) {
        const data = await res.json();
        setAccountSignalsDetail(data);
      }
    } catch (err) {
      console.error('Failed to load account signals detail:', err);
    }
  };

  const fetchTerritoryPlan = async () => {
    if (!token) return;
    setTerritoryLoading(true);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/sales-crm/territory/plan?rep_id=${encodeURIComponent(repId)}&lat=${latitude}&lon=${longitude}`
      );
      if (res.ok) {
        const data = await res.json();
        setRoutePlan(data);
      }
    } catch (err) {
      console.error('Failed to fetch territory plan:', err);
    } finally {
      setTerritoryLoading(false);
    }
  };

  const fetchSourceRoi = async () => {
    if (!token) return;
    setRoiLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/intelligence/source-roi`);
      if (res.ok) {
        const data = await res.json();
        setSourceRoi(data);
      }
    } catch (err) {
      console.error('Failed to fetch source ROI:', err);
    } finally {
      setRoiLoading(false);
    }
  };

  const fetchDiscoveryData = async () => {
    if (!token) return;
    setDiscoveryLoading(true);
    try {
      const [srcRes, compRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/sales-os/sources`),
        fetchWithAuth(`${API_URL}/sales-os/companies`),
      ]);
      if (srcRes.ok) setSources(await srcRes.json());
      if (compRes.ok) setCompanies(await compRes.json());
    } catch (err) {
      console.error('Failed to load discovery data:', err);
    } finally {
      setDiscoveryLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'signals') fetchSignalsFeed();
    if (activeTab === 'territory') fetchTerritoryPlan();
    if (activeTab === 'roi') fetchSourceRoi();
    if (activeTab === 'discovery') fetchDiscoveryData();
  }, [activeTab, token]);

  // Initial load of companies for ingest selection
  useEffect(() => {
    if (token) {
      fetchWithAuth(`${API_URL}/sales-os/companies`)
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => {
          setCompanies(data);
          if (data.length > 0 && !ingestForm.company_id) {
            setIngestForm((prev) => ({ ...prev, company_id: data[0].id }));
          }
        })
        .catch(() => {});
    }
  }, [token]);

  // Handle Signal Ingestion
  const handleIngestSignal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ingestForm.company_id || !ingestForm.summary) {
      notify.error('Please select an account and provide a signal summary');
      return;
    }
    setIngesting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/signals/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ingestForm),
      });
      if (res.ok) {
        const data = await res.json();
        notify.success('Intent signal verified and ingested into bus with convergence bonus!');
        setIsIngestModalOpen(false);
        setIngestForm({
          company_id: companies[0]?.id || '',
          signal_type: 'funding_round',
          family: 'funding',
          summary: '',
          base_strength: 75,
          source_confidence: 0.9,
          half_life_days: 30,
          source_key: 'crunchbase',
          source_url: '',
        });
        fetchSignalsFeed();
      } else {
        notify.error('Failed to ingest intent signal');
      }
    } catch (err) {
      console.error(err);
      notify.error('Network error ingesting signal');
    } finally {
      setIngesting(false);
    }
  };

  // Filtered signals feed
  const filteredSignals = useMemo(() => {
    if (signalFamilyFilter === 'all') return signalsFeed;
    return signalsFeed.filter((s) => s.family === signalFamilyFilter);
  }, [signalsFeed, signalFamilyFilter]);

  // Family badge styling
  const familyBadge = (family: string) => {
    switch (family) {
      case 'funding':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'hiring':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'leadership':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
      case 'tech_adoption':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'first_party_web':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      default:
        return 'bg-muted text-muted-foreground border-border';
    }
  };

  return (
    <div className="space-y-6">
      {/* ── SUB-NAVIGATION & ACTIONS ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
          <button
            onClick={() => setActiveTab('signals')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors shrink-0 ${
              activeTab === 'signals'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
            }`}
          >
            <Radar size={14} />
            <span>Intent Signal Bus</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-background/20 font-bold">
              {signalsFeed.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('territory')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors shrink-0 ${
              activeTab === 'territory'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
            }`}
          >
            <Compass size={14} />
            <span>Territory Route Planner</span>
          </button>

          <button
            onClick={() => setActiveTab('roi')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors shrink-0 ${
              activeTab === 'roi'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
            }`}
          >
            <DollarSign size={14} />
            <span>Source Attribution ROI</span>
          </button>

          <button
            onClick={() => setActiveTab('discovery')}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-colors shrink-0 ${
              activeTab === 'discovery'
                ? 'bg-primary text-primary-foreground shadow-xs'
                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
            }`}
          >
            <Sparkles size={14} />
            <span>Discovery Engine</span>
          </button>
        </div>

        {activeTab === 'signals' && (
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={fetchSignalsFeed}
              disabled={signalsLoading}
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw size={13} className={signalsLoading ? 'animate-spin' : ''} />
              Refresh
            </Button>
            <Button
              size="sm"
              onClick={() => setIsIngestModalOpen(true)}
              className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground"
            >
              <Plus size={13} />
              Ingest Signal
            </Button>
          </div>
        )}

        {activeTab === 'territory' && (
          <div className="flex items-center gap-2 shrink-0">
            <Button
              size="sm"
              variant="outline"
              onClick={fetchTerritoryPlan}
              disabled={territoryLoading}
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw size={13} className={territoryLoading ? 'animate-spin' : ''} />
              Recalculate Route
            </Button>
          </div>
        )}
      </div>

      {/* ── TAB 1: INTENT SIGNAL BUS ── */}
      {activeTab === 'signals' && (
        <div className="space-y-5">
          {/* Executive Convergence Explainer Card */}
          <div className="rounded-xl border border-border bg-gradient-to-r from-card via-card to-primary/5 p-4 sm:p-5 shadow-xs">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <h3 className="text-sm font-semibold text-foreground">
                    Real-Time Multi-Source Convergence Bus
                  </h3>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                    Half-Life Decay Enabled
                  </span>
                </div>
                <p className="text-xs text-muted-foreground max-w-2xl">
                  Signals are continuously ingested from Hacker News, LinkedIn, SEC filings, and domain MX records. When distinct evidence families converge (e.g., funding + hiring surge), an automatic compounding multiplier (+15%) elevates account propensity.
                </p>
              </div>

              {/* Family Filters */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {['all', 'funding', 'hiring', 'leadership', 'tech_adoption', 'first_party_web'].map((fam) => (
                  <button
                    key={fam}
                    onClick={() => setSignalFamilyFilter(fam)}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                      signalFamilyFilter === fam
                        ? 'bg-foreground text-background font-semibold'
                        : 'bg-muted/60 text-muted-foreground hover:bg-muted'
                    }`}
                  >
                    {fam === 'all' ? 'All Signals' : fam.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Grid Layout: Live Feed (Left) & Account Stacking Detail (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Live Signals Stream */}
            <div className="lg:col-span-7 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Verified Signals Stream ({filteredSignals.length})
                </h4>
                <span className="text-xs text-muted-foreground">Ordered by observation freshness</span>
              </div>

              {filteredSignals.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border bg-card/50 p-12 text-center">
                  <Radar size={32} className="mx-auto text-muted-foreground/40 mb-3" />
                  <h5 className="text-sm font-medium text-foreground">No Intent Signals Found</h5>
                  <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                    No active intent signals matching this family. Ingest signals or run discovery to populate the bus.
                  </p>
                  <Button
                    size="sm"
                    onClick={() => setIsIngestModalOpen(true)}
                    className="mt-4 text-xs h-8 gap-1.5"
                  >
                    <Plus size={13} /> Ingest First Signal
                  </Button>
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[640px] overflow-y-auto pr-1">
                  {filteredSignals.map((sig) => (
                    <div
                      key={sig.id}
                      onClick={() => {
                        setSelectedSignalAccount(sig);
                        fetchAccountSignals(sig.company_id);
                      }}
                      className={`group cursor-pointer rounded-xl border p-3.5 transition-all ${
                        selectedSignalAccount?.id === sig.id
                          ? 'border-primary bg-primary/5 shadow-xs'
                          : 'border-border bg-card hover:border-primary/40 hover:bg-card/80'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                              {sig.company_name}
                            </span>
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${familyBadge(sig.family)}`}>
                              {sig.family}
                            </span>
                            <span className="text-[10px] text-muted-foreground font-mono">
                              via {sig.source_key}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {sig.summary}
                          </p>
                        </div>

                        <div className="text-right shrink-0">
                          <div className="flex items-center gap-1 justify-end">
                            <span className="text-xs font-mono font-bold text-foreground">
                              {sig.effective_strength}
                            </span>
                            <span className="text-[10px] text-muted-foreground">pts</span>
                          </div>
                          <span className="text-[10px] text-muted-foreground block mt-0.5">
                            {sig.age_days}d ago
                          </span>
                        </div>
                      </div>

                      <div className="mt-2.5 pt-2 border-t border-border/50 flex items-center justify-between text-[11px] text-muted-foreground">
                        <span>Domain: {sig.canonical_domain || 'Unspecified'}</span>
                        <span className="flex items-center gap-1 text-primary group-hover:translate-x-0.5 transition-transform">
                          View Stacking <ChevronRight size={12} />
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Account Stacking & Convergence Inspector */}
            <div className="lg:col-span-5 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Account Intent Stacking & Multi-Source Convergence
              </h4>

              {selectedSignalAccount ? (
                <div className="rounded-xl border border-border bg-card p-4 space-y-4 shadow-xs">
                  <div className="flex items-start justify-between gap-2 border-b border-border pb-3">
                    <div>
                      <h3 className="text-sm font-bold text-foreground">
                        {selectedSignalAccount.company_name}
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        {selectedSignalAccount.canonical_domain || 'Domain not specified'} · {selectedSignalAccount.industry || 'Technology'}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                        Composite Intent
                      </span>
                      <span className="text-base font-mono font-extrabold text-primary">
                        {accountSignalsDetail?.intent_score ?? selectedSignalAccount.intent_score ?? '—'}
                      </span>
                    </div>
                  </div>

                  {/* Convergence Bonus Callout */}
                  {accountSignalsDetail?.convergence && (
                    <div className="rounded-lg border border-primary/20 bg-primary/10 p-3 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-primary flex items-center gap-1.5">
                          <Sparkles size={13} /> Multi-Source Convergence Bonus
                        </span>
                        <span className="text-xs font-mono font-bold text-primary">
                          +{Math.round((accountSignalsDetail.convergence.bonus || 0) * 100)}%
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Bonus applied due to independent corroborating evidence across distinct families.
                      </p>
                      {accountSignalsDetail.convergence.families && (
                        <div className="flex items-center gap-1 pt-1 flex-wrap">
                          {accountSignalsDetail.convergence.families.map((f: string) => (
                            <span key={f} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-background/50 border border-border">
                              {f}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Account Signals List */}
                  <div className="space-y-2">
                    <span className="text-xs font-semibold text-foreground">
                      Active Decayed Signals ({accountSignalsDetail?.signals?.length || 1})
                    </span>

                    {(accountSignalsDetail?.signals || [selectedSignalAccount]).map((s: any) => (
                      <div
                        key={s.id}
                        className="rounded-lg border border-border/70 bg-muted/20 p-2.5 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-foreground">{s.signal_type}</span>
                          <span className="font-mono text-emerald-400 font-bold">
                            {s.effective_strength ?? s.base_strength} pts
                          </span>
                        </div>
                        <p className="text-muted-foreground text-[11px]">{s.summary}</p>
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1 border-t border-border/40">
                          <span>Half-life: {s.half_life_days || 30}d</span>
                          <span>Age: {s.age_days || 0}d</span>
                          <span>Confidence: {Math.round((s.source_confidence || 0.8) * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center text-muted-foreground">
                  <Radar size={24} className="mx-auto mb-2 opacity-50" />
                  <p className="text-xs font-medium">Select an account from the stream</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Click any signal to inspect decayed strengths and convergence bonuses.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 2: TERRITORY ROUTE PLANNER ── */}
      {activeTab === 'territory' && (
        <div className="space-y-5">
          {/* Header Controls Bar */}
          <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <Compass size={16} className="text-primary" />
                  Territory Route Planner & Field Itinerary Agent
                </h3>
                <p className="text-xs text-muted-foreground">
                  Optimizes daily field sales itineraries using Traveling Salesperson clustering, drive time minimization, and backup contingency accounts.
                </p>
              </div>

              {/* Rep & GPS Presets */}
              <div className="flex items-center gap-2 flex-wrap">
                <select
                  value={repId}
                  onChange={(e) => setRepId(e.target.value)}
                  className="h-8 rounded-md border border-border bg-background px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="rep_field_1">Sarah Jenkins (West Bay Area)</option>
                  <option value="rep_field_2">David Kim (NY Metro)</option>
                  <option value="rep_field_3">Alex Rivera (London City)</option>
                </select>

                <div className="flex items-center gap-1 bg-muted/40 p-1 rounded-md border border-border text-xs">
                  <button
                    onClick={() => {
                      setLatitude(37.7749);
                      setLongitude(-122.4194);
                    }}
                    className={`px-2 py-0.5 rounded text-[11px] ${
                      latitude === 37.7749 ? 'bg-background font-semibold text-foreground shadow-xs' : 'text-muted-foreground'
                    }`}
                  >
                    SF
                  </button>
                  <button
                    onClick={() => {
                      setLatitude(40.7128);
                      setLongitude(-74.006);
                    }}
                    className={`px-2 py-0.5 rounded text-[11px] ${
                      latitude === 40.7128 ? 'bg-background font-semibold text-foreground shadow-xs' : 'text-muted-foreground'
                    }`}
                  >
                    NYC
                  </button>
                  <button
                    onClick={() => {
                      setLatitude(51.5074);
                      setLongitude(-0.1278);
                    }}
                    className={`px-2 py-0.5 rounded text-[11px] ${
                      latitude === 51.5074 ? 'bg-background font-semibold text-foreground shadow-xs' : 'text-muted-foreground'
                    }`}
                  >
                    LDN
                  </button>
                </div>

                <Button
                  size="sm"
                  onClick={fetchTerritoryPlan}
                  disabled={territoryLoading}
                  className="h-8 text-xs gap-1.5"
                >
                  {territoryLoading ? <RefreshCw size={13} className="animate-spin" /> : <Navigation size={13} />}
                  Compute Route
                </Button>
              </div>
            </div>
          </div>

          {/* Route Metrics Row */}
          {routePlan && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
                <span className="text-[11px] text-muted-foreground block font-medium">Total Driving Distance</span>
                <span className="text-lg font-bold font-mono text-foreground mt-0.5 block">
                  {routePlan.total_travel_distance_km ?? 0} km
                </span>
                <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-1">
                  <CheckCircle2 size={11} /> TSP Distance Minimized
                </span>
              </div>

              <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
                <span className="text-[11px] text-muted-foreground block font-medium">Total Driving Time</span>
                <span className="text-lg font-bold font-mono text-foreground mt-0.5 block">
                  {routePlan.total_driving_time_minutes ?? 0} min
                </span>
                <span className="text-[10px] text-muted-foreground mt-1 block">
                  Excludes in-office meetings
                </span>
              </div>

              <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
                <span className="text-[11px] text-muted-foreground block font-medium">Confirmed Stops</span>
                <span className="text-lg font-bold font-mono text-primary mt-0.5 block">
                  {routePlan.stops?.length ?? 0} Accounts
                </span>
                <span className="text-[10px] text-muted-foreground mt-1 block">
                  Optimized arrival windows
                </span>
              </div>

              <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
                <span className="text-[11px] text-muted-foreground block font-medium">Contingency Accounts</span>
                <span className="text-lg font-bold font-mono text-amber-400 mt-0.5 block">
                  {routePlan.contingency_accounts?.length ?? 0} Available
                </span>
                <span className="text-[10px] text-muted-foreground mt-1 block">
                  Nearby fill-ins for cancellations
                </span>
              </div>
            </div>
          )}

          {/* Stops Timeline & Contingencies */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Stops Itinerary */}
            <div className="lg:col-span-8 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Sequential Field Itinerary
              </h4>

              {territoryLoading ? (
                <div className="rounded-xl border border-border bg-card p-12 text-center">
                  <RefreshCw size={24} className="mx-auto text-primary animate-spin mb-2" />
                  <p className="text-xs text-muted-foreground">Running territory cluster optimization...</p>
                </div>
              ) : routePlan?.stops && routePlan.stops.length > 0 ? (
                <div className="space-y-3">
                  {routePlan.stops.map((stop: any, idx: number) => (
                    <div
                      key={stop.stop_number || idx}
                      className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-xs relative overflow-hidden"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold text-xs shrink-0">
                            #{stop.stop_number || idx + 1}
                          </div>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4 className="text-sm font-bold text-foreground">
                                {stop.company_name}
                              </h4>
                              {stop.deal_size && (
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                                  {money(stop.deal_size)} Deal
                                </span>
                              )}
                              <span className="text-[11px] text-muted-foreground">
                                {stop.city || 'Local Territory'}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                              <span className="flex items-center gap-1">
                                <Clock size={12} /> {stop.arrival_time || '09:30 AM'} - {stop.departure_time || '10:30 AM'}
                              </span>
                              <span className="flex items-center gap-1">
                                <Navigation size={12} /> {stop.distance_from_previous_km ?? 0} km from prev ({stop.travel_time_minutes ?? 15}m drive)
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="text-[11px] font-medium text-foreground block">
                            {stop.contact_name || 'Key Executive'}
                          </span>
                          <span className="text-[10px] text-muted-foreground block">
                            {stop.contact_title || 'Decision Maker'}
                          </span>
                        </div>
                      </div>

                      {/* Talking Points */}
                      {stop.talking_points && stop.talking_points.length > 0 && (
                        <div className="rounded-lg bg-muted/30 border border-border/50 p-2.5 space-y-1">
                          <span className="text-[11px] font-semibold text-foreground block">
                            High-Impact Meeting Agenda & Talking Points:
                          </span>
                          <ul className="list-disc list-inside text-xs text-muted-foreground space-y-0.5">
                            {stop.talking_points.map((pt: string, pIdx: number) => (
                              <li key={pIdx}>{pt}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-card p-12 text-center text-muted-foreground">
                  <Compass size={28} className="mx-auto mb-2 opacity-40" />
                  <p className="text-sm font-medium">No active territory stops planned</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Click "Compute Route" above to generate an itinerary for this representative.
                  </p>
                </div>
              )}
            </div>

            {/* Contingency Accounts Sidebar */}
            <div className="lg:col-span-4 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Contingency & Drop-In Accounts
              </h4>

              {routePlan?.contingency_accounts && routePlan.contingency_accounts.length > 0 ? (
                <div className="space-y-2">
                  {routePlan.contingency_accounts.map((acc: any, cIdx: number) => (
                    <div
                      key={cIdx}
                      className="rounded-xl border border-border bg-card p-3 space-y-1.5 shadow-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-foreground">
                          {acc.company_name}
                        </span>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {acc.distance_from_base_km ?? 5} km away
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {acc.contingency_reason || 'Nearby account with open pipeline or strong intent signals.'}
                      </p>
                      {acc.deal_size && (
                        <div className="text-[10px] text-emerald-400 font-mono">
                          Pipeline: {money(acc.deal_size)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-card/40 p-6 text-center text-xs text-muted-foreground">
                  No backup contingency accounts needed for this route density.
                </div>
              )}

              {/* Cryptographic Provenance */}
              {routePlan?.evidence_hashes && routePlan.evidence_hashes.length > 0 && (
                <div className="rounded-xl border border-border bg-card p-3 space-y-1">
                  <span className="text-[11px] font-semibold text-foreground block">
                    Cryptographic Audit Trail
                  </span>
                  <p className="text-[10px] text-muted-foreground">
                    Route generated deterministically with SHA-256 evidence validation:
                  </p>
                  <div className="space-y-0.5 pt-1">
                    {routePlan.evidence_hashes.slice(0, 3).map((hash: string, hIdx: number) => (
                      <span
                        key={hIdx}
                        className="block font-mono text-[9px] text-muted-foreground/80 truncate"
                        title={hash}
                      >
                        {hash}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 3: SOURCE ATTRIBUTION ROI ── */}
      {activeTab === 'roi' && (
        <div className="space-y-5">
          <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              <DollarSign size={16} className="text-emerald-400" />
              Multi-Touch Source Attribution & ROI Analytics
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Tracks actual provider spend across Apollo, LinkedIn, Hacker News, ZoomInfo, and Hunter against downstream pipeline creation, booked meetings, and closed-won revenue.
            </p>
          </div>

          {/* Top Aggregate Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <span className="text-[11px] text-muted-foreground block font-medium">Total Provider Spend</span>
              <span className="text-lg font-bold font-mono text-foreground mt-0.5 block">
                {money(sourceRoi?.totals?.spend ?? 0)}
              </span>
              <span className="text-[10px] text-muted-foreground mt-1 block">API & enrichment costs</span>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <span className="text-[11px] text-muted-foreground block font-medium">Booked Meetings</span>
              <span className="text-lg font-bold font-mono text-primary mt-0.5 block">
                {sourceRoi?.totals?.meetings ?? 0}
              </span>
              <span className="text-[10px] text-muted-foreground mt-1 block">Qualified sales conversations</span>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <span className="text-[11px] text-muted-foreground block font-medium">Closed-Won ARR</span>
              <span className="text-lg font-bold font-mono text-emerald-400 mt-0.5 block">
                {money(sourceRoi?.totals?.revenue ?? 0)}
              </span>
              <span className="text-[10px] text-emerald-400/80 mt-1 block">Directly attributed deals</span>
            </div>

            <div className="rounded-xl border border-border bg-card p-3.5 shadow-xs">
              <span className="text-[11px] text-muted-foreground block font-medium">Aggregate ROI Multiple</span>
              <span className="text-lg font-bold font-mono text-purple-400 mt-0.5 block">
                {sourceRoi?.totals?.roi_multiple ? `${Number(sourceRoi.totals.roi_multiple).toFixed(1)}x` : '—'}
              </span>
              <span className="text-[10px] text-muted-foreground mt-1 block">Return on acquisition spend</span>
            </div>
          </div>

          {/* Provider Breakdown Table */}
          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-xs">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Attribution by Provider Key
              </h4>
              <span className="text-xs text-muted-foreground">
                First-Touch & Linear Allocation Model
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/40 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="py-2.5 px-4 font-medium">Provider</th>
                    <th className="py-2.5 px-4 font-medium">Verified Leads</th>
                    <th className="py-2.5 px-4 font-medium">Meetings</th>
                    <th className="py-2.5 px-4 font-medium">Actual Spend</th>
                    <th className="py-2.5 px-4 font-medium">Attributed ARR</th>
                    <th className="py-2.5 px-4 font-medium">Cost / Meeting</th>
                    <th className="py-2.5 px-4 font-medium">ROI Multiple</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {sourceRoi?.by_provider ? (
                    Object.entries(sourceRoi.by_provider).map(([provKey, stats]: [string, any]) => (
                      <tr key={provKey} className="hover:bg-muted/20 transition-colors">
                        <td className="py-2.5 px-4 font-semibold text-foreground flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-primary" />
                          {provKey}
                        </td>
                        <td className="py-2.5 px-4 font-mono">{stats.verified_leads ?? 0}</td>
                        <td className="py-2.5 px-4 font-mono font-bold text-foreground">
                          {stats.meetings ?? 0}
                        </td>
                        <td className="py-2.5 px-4 font-mono">{money(stats.spend)}</td>
                        <td className="py-2.5 px-4 font-mono font-bold text-emerald-400">
                          {money(stats.revenue)}
                        </td>
                        <td className="py-2.5 px-4 font-mono">
                          {stats.cost_per_meeting ? money(stats.cost_per_meeting) : '—'}
                        </td>
                        <td className="py-2.5 px-4 font-mono font-bold">
                          {stats.roi_multiple ? (
                            <span className="text-purple-400">{Number(stats.roi_multiple).toFixed(1)}x</span>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground">
                        No attribution cost records currently registered.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 4: DISCOVERY ENGINE & EVIDENCE ── */}
      {activeTab === 'discovery' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
            <h3 className="text-sm font-semibold text-foreground">
              Autonomous Discovery & Evidence Registry
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Execute public DNS MX inspection, Hacker News hiring scrapes, or inspect canonical accounts and their cryptographic evidence chains.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="acme.com or query"
                aria-label="Discovery query"
                className="text-xs h-9"
              />
              <Input
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="Approved budget USD (optional)"
                aria-label="Approved budget"
                className="text-xs h-9"
              />
              <Button
                onClick={async () => {
                  if (!query.trim()) {
                    notify.error('Enter a company domain or search query');
                    return;
                  }
                  setDiscoveryLoading(true);
                  try {
                    const body: Record<string, unknown> = {
                      query: query.trim(),
                      execute: executePublic,
                      provider_keys: executePublic ? ['hn_hiring', 'dns_mx_inspect'] : undefined,
                    };
                    if (budget.trim() !== '') {
                      const parsed = Number(budget);
                      if (!Number.isNaN(parsed)) body.budget = parsed;
                    }
                    const response = await fetchWithAuth(`${API_URL}/sales-os/discovery/runs`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(body),
                    });
                    if (response.ok) {
                      const data = await response.json();
                      setPlan(data);
                      notify.success('Discovery plan initiated!');
                      fetchDiscoveryData();
                    }
                  } catch (err) {
                    notify.error('Discovery plan execution failed');
                  } finally {
                    setDiscoveryLoading(false);
                  }
                }}
                disabled={discoveryLoading}
                className="text-xs h-9"
              >
                {discoveryLoading ? 'Running...' : executePublic ? 'Run Public Sources' : 'Generate Plan Only'}
              </Button>
            </div>
            <label className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={executePublic}
                onChange={(e) => setExecutePublic(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary"
              />
              Run public Hacker News and DNS MX discovery (no paid credits consumed).
            </label>
          </div>

          {/* Companies & Evidence Split */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Canonical Companies ({companies.length})
              </h4>
              <div className="max-h-[400px] overflow-y-auto space-y-1.5">
                {companies.map((comp) => (
                  <div
                    key={comp.id}
                    onClick={async () => {
                      setSelectedCompanyId(comp.id);
                      const res = await fetchWithAuth(`${API_URL}/sales-os/companies/${comp.id}/evidence`);
                      if (res.ok) setEvidence(await res.json());
                    }}
                    className={`cursor-pointer rounded-lg p-2.5 text-xs transition-colors border ${
                      selectedCompanyId === comp.id
                        ? 'border-primary bg-primary/5 font-semibold'
                        : 'border-border/60 hover:bg-muted/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-foreground">{comp.display_name || comp.canonical_domain || comp.id}</span>
                      <span className="font-mono text-primary">{comp.score ?? '—'} pts</span>
                    </div>
                    <span className="text-[11px] text-muted-foreground">{comp.canonical_domain || 'Domain unknown'}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-4 shadow-xs">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                Cryptographic Evidence Records ({evidence.length})
              </h4>
              <div className="max-h-[400px] overflow-y-auto space-y-2">
                {evidence.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-8 text-center">
                    Select a canonical company to inspect its evidence chain.
                  </p>
                ) : (
                  evidence.map((ev) => (
                    <div key={ev.id} className="rounded-lg border border-border/70 bg-muted/20 p-2.5 text-xs space-y-1">
                      <div className="flex items-center justify-between font-medium">
                        <span className="text-primary">{ev.source_key}</span>
                        <span className="font-mono text-[10px] text-muted-foreground">{ev.payload_hash?.slice(0, 12)}</span>
                      </div>
                      <p className="text-muted-foreground text-[11px]">{ev.claim || 'Observation logged'}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── INGEST SIGNAL MODAL ── */}
      {isIngestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-xl border border-border bg-card p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Radar size={16} className="text-primary" />
                <h3 className="text-sm font-bold text-foreground">
                  Ingest Intent Signal into Bus
                </h3>
              </div>
              <button
                onClick={() => setIsIngestModalOpen(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleIngestSignal} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-medium text-foreground mb-1">
                  Target Canonical Account
                </label>
                <select
                  value={ingestForm.company_id}
                  onChange={(e) => setIngestForm({ ...ingestForm, company_id: e.target.value })}
                  className="w-full h-8 rounded-md border border-border bg-background px-2.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                >
                  <option value="">Select an account...</option>
                  {companies.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.display_name || c.canonical_domain || c.id}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-foreground mb-1">
                    Signal Family
                  </label>
                  <select
                    value={ingestForm.family}
                    onChange={(e) => {
                      const fam = e.target.value;
                      setIngestForm({
                        ...ingestForm,
                        family: fam,
                        signal_type: fam === 'funding' ? 'funding_round' : fam === 'hiring' ? 'hiring_expansion' : 'leadership_hire',
                      });
                    }}
                    className="w-full h-8 rounded-md border border-border bg-background px-2.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="funding">Funding ($ Series A/B/C)</option>
                    <option value="hiring">Hiring (Expansion/Surge)</option>
                    <option value="leadership">Leadership (New CXO/VP)</option>
                    <option value="tech_adoption">Tech Adoption (Stack Change)</option>
                    <option value="first_party_web">First-Party Web (Pricing Visit)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-foreground mb-1">
                    Signal Type Name
                  </label>
                  <Input
                    value={ingestForm.signal_type}
                    onChange={(e) => setIngestForm({ ...ingestForm, signal_type: e.target.value })}
                    className="h-8 text-xs"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">
                  Signal Summary / Observation Note
                </label>
                <Textarea
                  value={ingestForm.summary}
                  onChange={(e) => setIngestForm({ ...ingestForm, summary: e.target.value })}
                  placeholder="e.g., Closed $25M Series B led by Index Ventures; actively expanding enterprise sales team."
                  rows={2}
                  className="text-xs"
                  required
                />
              </div>

              <div className="grid grid-cols-3 gap-2.5">
                <div>
                  <label className="block font-medium text-foreground mb-1">
                    Strength (1-100)
                  </label>
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={ingestForm.base_strength}
                    onChange={(e) => setIngestForm({ ...ingestForm, base_strength: Number(e.target.value) })}
                    className="h-8 text-xs"
                  />
                </div>

                <div>
                  <label className="block font-medium text-foreground mb-1">
                    Confidence (0-1)
                  </label>
                  <Input
                    type="number"
                    step={0.05}
                    min={0.1}
                    max={1.0}
                    value={ingestForm.source_confidence}
                    onChange={(e) => setIngestForm({ ...ingestForm, source_confidence: Number(e.target.value) })}
                    className="h-8 text-xs"
                  />
                </div>

                <div>
                  <label className="block font-medium text-foreground mb-1">
                    Half-Life (Days)
                  </label>
                  <Input
                    type="number"
                    min={1}
                    max={365}
                    value={ingestForm.half_life_days}
                    onChange={(e) => setIngestForm({ ...ingestForm, half_life_days: Number(e.target.value) })}
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-foreground mb-1">
                    Source Key
                  </label>
                  <Input
                    value={ingestForm.source_key}
                    onChange={(e) => setIngestForm({ ...ingestForm, source_key: e.target.value })}
                    placeholder="crunchbase, linkedin, etc."
                    className="h-8 text-xs"
                  />
                </div>

                <div>
                  <label className="block font-medium text-foreground mb-1">
                    Source URL
                  </label>
                  <Input
                    value={ingestForm.source_url}
                    onChange={(e) => setIngestForm({ ...ingestForm, source_url: e.target.value })}
                    placeholder="https://..."
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsIngestModalOpen(false)}
                  className="h-8 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={ingesting}
                  className="h-8 text-xs gap-1.5"
                >
                  {ingesting ? <RefreshCw size={13} className="animate-spin" /> : <Radar size={13} />}
                  Verify & Ingest
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

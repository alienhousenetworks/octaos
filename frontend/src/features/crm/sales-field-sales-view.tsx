'use client';

import React, { useState, useEffect } from 'react';
import {
  Navigation, MapPin, Calendar, Clock, AlertTriangle, CheckCircle2,
  TrendingUp, Users, Cpu, Sparkles, RefreshCw, Compass, DollarSign,
  ChevronRight, Car, Building2, Phone, ShieldCheck, Check, X,
  BarChart3, FileText, ArrowRight, Zap, BatteryCharging,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { notify } from '@/lib/notify';
import {
  FieldSalesOverview,
  SalespersonLiveStatus,
  FieldVisitPin,
  RecoveryProposal,
  FieldSalesAnalysisReport,
} from './sales-types';

interface SalesFieldSalesViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

export default function SalesFieldSalesView({
  token,
  API_URL,
  fetchWithAuth,
}: SalesFieldSalesViewProps) {
  // Navigation sub-tabs
  type SubView = 'overview' | 'dispatch_map' | 'schedule' | 'priority_leads' | 'ai_studio' | 'orchestrator_report';
  const [activeSubView, setActiveSubView] = useState<SubView>('overview');

  // Data states
  const [loading, setLoading] = useState(false);
  const [overview, setOverview] = useState<FieldSalesOverview | null>(null);
  const [salespeople, setSalespeople] = useState<SalespersonLiveStatus[]>([]);
  const [visits, setVisits] = useState<FieldVisitPin[]>([]);
  const [scheduleVisits, setScheduleVisits] = useState<any[]>([]);
  const [priorityLeads, setPriorityLeads] = useState<any[]>([]);
  const [proposals, setProposals] = useState<RecoveryProposal[]>([]);
  const [analysisReport, setAnalysisReport] = useState<FieldSalesAnalysisReport | null>(null);

  // AI Prompt bar
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiPlanning, setAiPlanning] = useState(false);
  const [aiResult, setAiResult] = useState<any | null>(null);

  // Fetch initial data
  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [ovRes, mapRes, leadsRes, propRes, repRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/sales-os/field-sales/overview`),
        fetchWithAuth(`${API_URL}/sales-os/field-sales/dispatch-map`),
        fetchWithAuth(`${API_URL}/sales-os/field-sales/priority-leads`),
        fetchWithAuth(`${API_URL}/sales-os/field-sales/ai/proposals`),
        fetchWithAuth(`${API_URL}/sales-os/field-sales/analysis-report?period_days=30`),
      ]);

      if (ovRes.ok) setOverview(await ovRes.json());
      if (mapRes.ok) {
        const mapData = await mapRes.json();
        setSalespeople(mapData.salespeople || []);
        setVisits(mapData.visits || []);
      }
      if (leadsRes.ok) setPriorityLeads(await leadsRes.json());
      if (propRes.ok) setProposals(await propRes.json());
      if (repRes.ok) setAnalysisReport(await repRes.json());
    } catch (err) {
      console.error('Failed to load field sales data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  // Load schedule when switching to schedule tab
  useEffect(() => {
    if (activeSubView === 'schedule' && token) {
      fetchWithAuth(`${API_URL}/sales-os/field-sales/schedule`)
        .then((res) => res.json())
        .then((data) => setScheduleVisits(data.visits || []))
        .catch((err) => console.error(err));
    }
  }, [activeSubView, token]);

  // AI natural language planning
  const handleExecuteAiPlan = async (promptText?: string) => {
    const textToRun = promptText || aiPrompt;
    if (!textToRun.trim() || !token) return;
    setAiPlanning(true);
    setAiResult(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/field-sales/ai/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: textToRun }),
      });
      if (res.ok) {
        const data = await res.json();
        setAiResult(data);
        notify.success('AI planning proposal generated');
        loadData();
      } else {
        notify.error('AI planning engine could not process request');
      }
    } catch (err) {
      notify.error('Error contacting AI scheduling service');
    } finally {
      setAiPlanning(false);
    }
  };

  // Proposal approve / reject
  const handleProposalAction = async (proposalId: string, action: 'approve' | 'reject') => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/field-sales/ai/proposals/${proposalId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Dispatcher action from web console' }),
      });
      if (res.ok) {
        notify.success(`Proposal ${action === 'approve' ? 'applied' : 'rejected'}`);
        loadData();
      } else {
        notify.error(`Failed to ${action} proposal`);
      }
    } catch (err) {
      notify.error('Network error updating proposal');
    }
  };

  return (
    <div className="space-y-6" id="field-sales-container">
      {/* ── SUB-HEADER NAVIGATION ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-card border border-border rounded-xl p-3 shadow-xs">
        <div className="flex items-center gap-1.5 flex-wrap">
          {[
            { id: 'overview', label: 'Overview', icon: <TrendingUp size={14} /> },
            { id: 'dispatch_map', label: 'Live Dispatch Map', icon: <Compass size={14} /> },
            { id: 'schedule', label: 'Team Schedule', icon: <Calendar size={14} /> },
            { id: 'priority_leads', label: 'Priority Showings', icon: <Users size={14} /> },
            { id: 'ai_studio', label: 'AI Recovery Studio', icon: <Sparkles size={14} />, badge: proposals.filter(p => p.status === 'pending_review').length || undefined },
            { id: 'orchestrator_report', label: 'Orchestrator Analysis', icon: <BarChart3 size={14} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSubView(tab.id as SubView)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeSubView === tab.id
                  ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                  : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.badge ? (
                <span className="w-4 h-4 rounded-full bg-amber-500 text-black text-[10px] font-bold flex items-center justify-center">
                  {tab.badge}
                </span>
              ) : null}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={loading}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Sync Telemetry
          </Button>
        </div>
      </div>

      {/* ── 1. SUB-VIEW: EXECUTIVE OVERVIEW & KPIS ── */}
      {activeSubView === 'overview' && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Today's Visits</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-foreground">{overview?.today_scheduled || 0}</span>
                <span className="text-xs text-muted-foreground">stops</span>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-medium text-emerald-500 uppercase tracking-wider">Completed</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-emerald-400">{overview?.today_completed || 0}</span>
                <span className="text-xs text-emerald-500/80">({overview?.completion_rate_pct || 0}%)</span>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-medium text-amber-500 uppercase tracking-wider">Delayed / At Risk</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-amber-400">{overview?.today_delayed || 0}</span>
                <span className="text-xs text-amber-500/80">trips</span>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-medium text-rose-500 uppercase tracking-wider">No-Shows</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-rose-400">{overview?.today_no_shows || 0}</span>
                <span className="text-xs text-rose-500/80">missed</span>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-medium text-primary uppercase tracking-wider">Active Fleet</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-primary">{overview?.active_salespeople || 0}</span>
                <span className="text-xs text-primary/80">specialists</span>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
              <span className="text-[11px] font-medium text-cyan-400 uppercase tracking-wider">Mapping Budget</span>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold text-cyan-400">
                  {overview?.connector_budget?.calls_used || 0}/{overview?.connector_budget?.daily_quota || 500}
                </span>
                <span className="text-xs text-cyan-400/80">
                  ${overview?.connector_budget?.estimated_daily_cost_usd || 0}
                </span>
              </div>
            </div>
          </div>

          {/* Quick AI Dispatch Assistant Banner */}
          <div className="bg-gradient-to-r from-primary/10 via-card to-card border border-primary/20 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/20 text-primary flex items-center justify-center shrink-0">
                <Sparkles size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">AI Dispatch & Route Commander</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Natural language optimization for property showings, traffic-aware recovery, and peer handovers.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 w-full md:w-auto">
              <input
                type="text"
                placeholder="e.g. Plan tomorrow's visits for all agents..."
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleExecuteAiPlan()}
                className="bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary w-full md:w-80"
              />
              <Button
                size="sm"
                onClick={() => handleExecuteAiPlan()}
                disabled={aiPlanning || !aiPrompt.trim()}
                className="h-8 text-xs shrink-0"
              >
                {aiPlanning ? <RefreshCw size={12} className="animate-spin" /> : 'Optimize'}
              </Button>
            </div>
          </div>

          {/* Today's Active Route Overview */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Live Fleet Telemetry List */}
            <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Car size={14} className="text-primary" /> Active Field Salespeople
                </h4>
                <span className="text-[11px] font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                  {salespeople.filter((s) => s.is_shift_active).length} Online
                </span>
              </div>
              <div className="divide-y divide-border/40 mt-2 max-h-72 overflow-y-auto">
                {salespeople.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-6 text-center">No salesperson telemetry recorded today.</p>
                ) : (
                  salespeople.map((agent) => (
                    <div key={agent.user_id} className="py-2.5 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-2.5 h-2.5 rounded-full ${agent.is_shift_active ? 'bg-emerald-400 animate-pulse' : 'bg-muted-foreground'}`} />
                        <div>
                          <p className="text-xs font-medium text-foreground">{agent.name}</p>
                          <p className="text-[10px] text-muted-foreground capitalize">
                            Status: <span className="text-foreground">{agent.status.replace('_', ' ')}</span> • Battery: {agent.battery_level || 95}%
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] px-2 py-0.5 rounded bg-muted/60 text-muted-foreground font-mono">
                          {agent.last_updated ? new Date(agent.last_updated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Idle'}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Upcoming Showings Timeline */}
            <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Building2 size={14} className="text-cyan-400" /> Today's Showings Itinerary
                </h4>
                <span className="text-[11px] text-muted-foreground">{visits.length} scheduled</span>
              </div>
              <div className="divide-y divide-border/40 mt-2 max-h-72 overflow-y-auto">
                {visits.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-6 text-center">No property visits scheduled for today.</p>
                ) : (
                  visits.map((visit) => (
                    <div key={visit.visit_id} className="py-2.5 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 text-primary text-xs font-bold flex items-center justify-center">
                          #{visit.sequence_order || 1}
                        </div>
                        <div>
                          <p className="text-xs font-medium text-foreground">{visit.project_name}</p>
                          <p className="text-[10px] text-muted-foreground">Buyer: {visit.buyer_name} ({visit.buyer_phone || 'No Phone'})</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs font-semibold text-foreground">
                          {new Date(visit.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                        <span className={`text-[9px] uppercase px-1.5 py-0.2 rounded font-semibold ${
                          visit.status === 'completed'
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : visit.status === 'delayed'
                            ? 'bg-amber-500/10 text-amber-400'
                            : 'bg-primary/10 text-primary'
                        }`}>
                          {visit.status}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 2. SUB-VIEW: LIVE DISPATCH MAP & FLEET TRACKING ── */}
      {activeSubView === 'dispatch_map' && (
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Compass size={16} className="text-primary" /> Real-Time Field Dispatch Grid
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Live coordinates from salesperson phones cross-referenced against real estate project geofences.
                </p>
              </div>
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Active Agent
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Property Site
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400" /> Delayed Showing
                </span>
              </div>
            </div>

            {/* Interactive Visual Map Representation */}
            <div className="mt-5 relative w-full h-96 rounded-xl bg-neutral-950 border border-neutral-800 overflow-hidden flex items-center justify-center">
              {/* Grid Background */}
              <div
                className="absolute inset-0 opacity-20"
                style={{
                  backgroundImage: 'radial-gradient(#38bdf8 1px, transparent 1px), radial-gradient(#6366f1 1px, transparent 1px)',
                  backgroundSize: '24px 24px',
                  backgroundPosition: '0 0, 12px 12px',
                }}
              />

              {/* Render Pins on the Map Canvas */}
              <div className="absolute inset-8">
                {/* Property pins */}
                {visits.map((v, i) => (
                  <div
                    key={v.visit_id}
                    className="absolute cursor-pointer transition-transform hover:scale-110"
                    style={{
                      left: `${15 + (i * 22) % 70}%`,
                      top: `${20 + (i * 28) % 65}%`,
                    }}
                  >
                    <div className="relative group">
                      <div className="w-8 h-8 rounded-full bg-cyan-500/20 border-2 border-cyan-400 text-cyan-300 flex items-center justify-center font-bold text-xs shadow-lg shadow-cyan-500/20">
                        <Building2 size={14} />
                      </div>
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 hidden group-hover:flex flex-col bg-neutral-900 border border-neutral-700 rounded-lg p-2 text-[10px] w-48 shadow-xl z-20">
                        <span className="font-bold text-foreground">{v.project_name}</span>
                        <span className="text-muted-foreground">Buyer: {v.buyer_name}</span>
                        <span className="text-cyan-400">Scheduled: {new Date(v.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </div>
                  </div>
                ))}

                {/* Salesperson live markers */}
                {salespeople.map((agent, i) => (
                  <div
                    key={agent.user_id}
                    className="absolute cursor-pointer transition-transform hover:scale-110"
                    style={{
                      left: `${30 + (i * 25) % 60}%`,
                      top: `${40 + (i * 20) % 50}%`,
                    }}
                  >
                    <div className="relative group">
                      <div className="w-9 h-9 rounded-full bg-emerald-500/20 border-2 border-emerald-400 text-emerald-300 flex items-center justify-center font-bold text-xs shadow-lg shadow-emerald-500/20">
                        <Car size={16} />
                      </div>
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 hidden group-hover:flex flex-col bg-neutral-900 border border-neutral-700 rounded-lg p-2 text-[10px] w-48 shadow-xl z-20">
                        <span className="font-bold text-foreground">{agent.name}</span>
                        <span className="text-emerald-400 capitalize">Status: {agent.status}</span>
                        <span className="text-muted-foreground">GPS Accuracy: ±{Math.round(agent.accuracy || 8)}m</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Live Status Overlay Card */}
              <div className="absolute bottom-4 left-4 bg-neutral-900/90 backdrop-blur-md border border-neutral-700 rounded-lg p-3 text-xs max-w-xs shadow-lg">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Field Sales Telemetry</span>
                <p className="text-foreground font-medium mt-1">
                  GPS reporting active for {salespeople.filter(s => s.is_shift_active).length} salesperson(s). Road travel duration calculated via Road Network Connector.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 3. SUB-VIEW: TEAM SCHEDULE TIMELINE ── */}
      {activeSubView === 'schedule' && (
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Calendar size={16} className="text-primary" /> Daily Showing Itinerary & Route Buffers
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Sequential appointments with guaranteed 15-minute travel buffers and geofence verification markers.
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleExecuteAiPlan("Optimize today's itinerary")}
                className="h-8 text-xs gap-1.5"
              >
                <Sparkles size={12} className="text-primary" /> Re-balance Itinerary
              </Button>
            </div>

            <div className="divide-y divide-border mt-3">
              {scheduleVisits.length === 0 ? (
                <p className="text-xs text-muted-foreground py-10 text-center">No schedule records found for today.</p>
              ) : (
                scheduleVisits.map((v) => (
                  <div key={v.id} className="py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 text-primary font-bold text-xs flex items-center justify-center shrink-0">
                        #{v.sequence_order || 1}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-foreground">{v.project_name}</h4>
                          <span className="text-[10px] text-muted-foreground font-mono">({v.project_location || 'Main Site'})</span>
                          {v.check_in_verified ? (
                            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20 font-semibold">
                              <ShieldCheck size={10} /> Verified On-Site
                            </span>
                          ) : null}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Buyer: <span className="text-foreground font-medium">{v.buyer_name}</span> • Specialist: {v.assigned_agent || 'Unassigned'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 text-xs shrink-0">
                      <div className="text-right">
                        <span className="font-semibold text-foreground">
                          {new Date(v.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <p className="text-[10px] text-muted-foreground">
                          Duration: {v.duration_minutes || 45}m • Transit: {v.estimated_travel_minutes || 15}m
                        </p>
                      </div>
                      <span className={`px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase ${
                        v.status === 'completed'
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : v.status === 'delayed'
                          ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          : 'bg-primary/15 text-primary border border-primary/30'
                      }`}>
                        {v.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── 4. SUB-VIEW: PRIORITIZED SHOWINGS & LEADS ── */}
      {activeSubView === 'priority_leads' && (
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Users size={16} className="text-primary" /> Buyer Showing Priority Queue
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  High-intent real estate inquiries prioritized by purchasing capacity and property configuration match.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
              {priorityLeads.map((lead) => (
                <div key={lead.id} className="bg-background border border-border rounded-xl p-4 shadow-xs flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-foreground">{lead.name}</h4>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                        Score {lead.score}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-1">Budget: {lead.budget}</p>
                    <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5 italic">"{lead.why}"</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground font-mono">{lead.phone || 'No phone'}</span>
                    <Button
                      size="sm"
                      onClick={() => handleExecuteAiPlan(`Plan showing for ${lead.name} near active project cluster`)}
                      className="h-7 text-[11px] gap-1"
                    >
                      <Sparkles size={11} /> Plan Showing
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── 5. SUB-VIEW: AI DISPATCH & RECOVERY STUDIO ── */}
      {activeSubView === 'ai_studio' && (
        <div className="space-y-6">
          {/* Prompt Box */}
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-3">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Sparkles size={16} className="text-primary" /> Autonomous Dispatch & Recovery Studio
            </h3>
            <p className="text-xs text-muted-foreground">
              Provide natural-language instructions to re-optimize routes, formulate delay recovery, or reassign tours.
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. Rearrange remaining visits for the salesperson delayed at the current property..."
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleExecuteAiPlan()}
                className="bg-background border border-border rounded-lg px-3 py-2 text-xs text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary flex-1"
              />
              <Button
                onClick={() => handleExecuteAiPlan()}
                disabled={aiPlanning || !aiPrompt.trim()}
                className="text-xs h-9 px-4 gap-1.5"
              >
                {aiPlanning ? <RefreshCw size={13} className="animate-spin" /> : <Zap size={13} />}
                Generate Plan
              </Button>
            </div>

            {/* Quick Suggestions Chips */}
            <div className="flex items-center gap-2 flex-wrap pt-1">
              <span className="text-[10px] text-muted-foreground font-semibold uppercase">Quick Prompts:</span>
              {[
                "Plan tomorrow's property visits for all available salespeople",
                "Rearrange remaining visits for the salesperson delayed at current showing",
                "Find high-priority families near active visit eligible today",
              ].map((chip) => (
                <button
                  key={chip}
                  onClick={() => {
                    setAiPrompt(chip);
                    handleExecuteAiPlan(chip);
                  }}
                  className="text-[10px] px-2 py-0.5 rounded bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground transition-all"
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {/* AI Plan Execution Result (if generated) */}
          {aiResult && (
            <div className="bg-primary/5 border border-primary/20 rounded-xl p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold text-primary tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 size={13} /> {aiResult.intent}
                </span>
                <span className="text-xs text-muted-foreground">Preview Mode</span>
              </div>
              <p className="text-xs text-foreground font-medium leading-relaxed">{aiResult.summary}</p>
            </div>
          )}

          {/* Pending Recovery Proposals List */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <AlertTriangle size={14} className="text-amber-400" /> Pending Schedule Recovery Proposals ({proposals.length})
            </h4>

            {proposals.length === 0 ? (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <CheckCircle2 size={24} className="text-emerald-400 mx-auto mb-2" />
                <p className="text-xs text-foreground font-medium">All schedules are running smoothly on time.</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">No schedule recovery interventions required.</p>
              </div>
            ) : (
              proposals.map((prop) => (
                <div key={prop.id} className="bg-card border border-border rounded-xl p-5 shadow-xs space-y-4">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-3 border-b border-border">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-foreground">Recovery Proposal #{prop.id.slice(0, 8)}</span>
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                          prop.status === 'applied' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                        }`}>
                          {prop.status}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">{prop.rationale}</p>
                    </div>

                    {prop.status === 'pending_review' ? (
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleProposalAction(prop.id, 'reject')}
                          className="h-8 text-xs text-rose-400 hover:text-rose-300 gap-1"
                        >
                          <X size={12} /> Reject
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleProposalAction(prop.id, 'approve')}
                          className="h-8 text-xs gap-1"
                        >
                          <Check size={12} /> Approve Schedule
                        </Button>
                      </div>
                    ) : null}
                  </div>

                  {/* Proposed Changes Diff Table */}
                  <div className="divide-y divide-border/40 text-xs">
                    {prop.proposed_changes?.map((ch, idx) => (
                      <div key={idx} className="py-2.5 flex flex-col md:flex-row md:items-center justify-between gap-2">
                        <div>
                          <span className="font-semibold text-foreground capitalize">{ch.action.replace('_', ' ')}</span>
                          <p className="text-[11px] text-muted-foreground">{ch.rationale}</p>
                          {ch.customer_message_draft ? (
                            <p className="text-[10px] text-cyan-400/90 italic mt-1 bg-cyan-950/30 p-1.5 rounded border border-cyan-800/30">
                              💬 Proposed message: "{ch.customer_message_draft}"
                            </p>
                          ) : null}
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-[11px] text-muted-foreground line-through">
                            Original: {new Date(ch.original_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </p>
                          <p className="text-xs font-bold text-emerald-400">
                            Proposed: {new Date(ch.proposed_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── 6. SUB-VIEW: ORCHESTRATOR ANALYSIS REPORT ── */}
      {activeSubView === 'orchestrator_report' && (
        <div className="space-y-6">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <BarChart3 size={16} className="text-primary" /> Orchestrator Executive Analysis Report
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Full 30-day funnel conversion, salesperson transit vs showing ratio, recurring objections, and strategic guidance.
                </p>
              </div>
              <span className="text-[11px] text-muted-foreground font-mono">
                Report generated: {analysisReport?.generated_at ? new Date(analysisReport.generated_at).toLocaleDateString() : 'Live'}
              </span>
            </div>

            {/* Funnel Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5">
              <div className="bg-background border border-border rounded-xl p-4">
                <span className="text-[10px] uppercase font-bold text-muted-foreground">Inquiries</span>
                <p className="text-2xl font-bold text-foreground mt-1">{analysisReport?.conversion_funnel?.inquiries || 0}</p>
                <p className="text-[11px] text-muted-foreground">Qualified leads</p>
              </div>

              <div className="bg-background border border-border rounded-xl p-4">
                <span className="text-[10px] uppercase font-bold text-cyan-400">Site Visits Completed</span>
                <p className="text-2xl font-bold text-cyan-400 mt-1">{analysisReport?.conversion_funnel?.completed_showings || 0}</p>
                <p className="text-[11px] text-cyan-500/80">{analysisReport?.conversion_funnel?.inquiry_to_visit_pct || 0}% conversion</p>
              </div>

              <div className="bg-background border border-border rounded-xl p-4">
                <span className="text-[10px] uppercase font-bold text-amber-400">Unit Holds</span>
                <p className="text-2xl font-bold text-amber-400 mt-1">{analysisReport?.conversion_funnel?.unit_holds || 0}</p>
                <p className="text-[11px] text-amber-500/80">{analysisReport?.conversion_funnel?.visit_to_hold_pct || 0}% showing-to-hold</p>
              </div>

              <div className="bg-background border border-border rounded-xl p-4">
                <span className="text-[10px] uppercase font-bold text-emerald-400">Confirmed Bookings</span>
                <p className="text-2xl font-bold text-emerald-400 mt-1">{analysisReport?.conversion_funnel?.confirmed_bookings || 0}</p>
                <p className="text-[11px] text-emerald-500/80">{analysisReport?.conversion_funnel?.hold_to_booking_pct || 0}% closed won</p>
              </div>
            </div>

            {/* Travel Efficiency & Objections Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
              {/* Field Efficiency */}
              <div className="bg-background border border-border rounded-xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <Car size={13} className="text-primary" /> Route & Transit Efficiency
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-border/40">
                    <span className="text-muted-foreground">Total Transit Minutes</span>
                    <span className="font-semibold text-foreground">{analysisReport?.travel_and_efficiency?.total_transit_minutes || 0}m</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-border/40">
                    <span className="text-muted-foreground">Total Showing Minutes</span>
                    <span className="font-semibold text-foreground">{analysisReport?.travel_and_efficiency?.total_showing_minutes || 0}m</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-border/40">
                    <span className="text-muted-foreground">Transit-to-Showing Ratio</span>
                    <span className="font-semibold text-primary">{analysisReport?.travel_and_efficiency?.transit_to_showing_ratio || 0}x</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-muted-foreground">Geofence Verified Check-Ins</span>
                    <span className="font-semibold text-emerald-400">{analysisReport?.executive_summary?.geofence_compliance_pct || 100}%</span>
                  </div>
                </div>
              </div>

              {/* Top Objections */}
              <div className="bg-background border border-border rounded-xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <FileText size={13} className="text-amber-400" /> Top Buyer Objections Recorded
                </h4>
                <div className="space-y-2">
                  {analysisReport?.buyer_insights?.top_objections?.map((obj, i) => (
                    <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-border/40">
                      <span className="text-muted-foreground">{obj.objection}</span>
                      <span className="font-bold text-foreground px-2 py-0.5 rounded bg-muted/60">{obj.count} times</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Strategic Guidance Box */}
            <div className="mt-6 bg-gradient-to-r from-card via-background to-card border border-border rounded-xl p-4 space-y-2">
              <span className="text-[10px] uppercase font-bold text-primary tracking-wider flex items-center gap-1.5">
                <Zap size={12} /> Strategic Orchestrator Recommendations
              </span>
              <ul className="space-y-1.5">
                {analysisReport?.strategic_recommendations?.map((rec, i) => (
                  <li key={i} className="text-xs text-foreground flex items-start gap-2">
                    <span className="text-primary mt-0.5">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

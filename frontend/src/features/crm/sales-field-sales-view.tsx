'use client';

import React, { useState, useEffect } from 'react';
import {
  Navigation, MapPin, Calendar, Clock, AlertTriangle, CheckCircle2,
  TrendingUp, Users, Cpu, Sparkles, RefreshCw, Compass, DollarSign,
  ChevronRight, Car, Building2, Phone, ShieldCheck, Check, X,
  BarChart3, FileText, ArrowRight, Zap, BatteryCharging, Plus,
  UserPlus, Layers, Briefcase, Award, CheckSquare, Search, Sliders,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { notify } from '@/lib/notify';
import {
  FieldSalesOverview,
  SalespersonLiveStatus,
  FieldVisitPin,
  RecoveryProposal,
  FieldSalesAnalysisReport,
  RealEstateProjectItem,
  SalespersonDirectoryItem,
  AITeamSuggestion,
  AutoAssignResult,
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
  type SubView = 'overview' | 'projects' | 'team' | 'dispatch_map' | 'schedule' | 'priority_leads' | 'ai_studio' | 'orchestrator_report';
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

  // Projects State
  const [projects, setProjects] = useState<RealEstateProjectItem[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [isAddProjectOpen, setIsAddProjectOpen] = useState(false);
  const [isSavingProject, setIsSavingProject] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    code: '',
    location: '',
    city: 'Bangalore',
    address: '',
    latitude: 12.9716,
    longitude: 77.5946,
    rera_number: '',
    hold_duration_hours: 48,
    total_units: 50,
    amenities: 'Clubhouse, Swimming Pool, Gym, 24/7 Security',
    status: 'active',
  });

  // Project Team Allocation State
  const [managingProject, setManagingProject] = useState<RealEstateProjectItem | null>(null);
  const [projectTeamDrawerOpen, setProjectTeamDrawerOpen] = useState(false);
  const [aiSuggestionsLoading, setAiSuggestionsLoading] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<AITeamSuggestion[]>([]);
  const [selectedTeamAssignments, setSelectedTeamAssignments] = useState<Record<string, { role: string; ai_recommended: boolean; match_score?: number; reason?: string }>>({});
  const [isSavingTeam, setIsSavingTeam] = useState(false);

  // Sales Force & Rosters State
  const [salesTeam, setSalesTeam] = useState<SalespersonDirectoryItem[]>([]);
  const [salesTeamLoading, setSalesTeamLoading] = useState(false);
  const [isAddSalespersonOpen, setIsAddSalespersonOpen] = useState(false);
  const [isSavingSalesperson, setIsSavingSalesperson] = useState(false);
  const [newSalesperson, setNewSalesperson] = useState({
    name: '',
    email: '',
    phone: '',
    designation: 'Property Specialist',
    working_hours_start: '09:00',
    working_hours_end: '18:00',
    max_visits_per_day: 6,
    initial_project_ids: [] as string[],
  });

  // Autonomous Lead Dispatch State
  const [autoAssignModalOpen, setAutoAssignModalOpen] = useState(false);
  const [autoAssignResult, setAutoAssignResult] = useState<AutoAssignResult | null>(null);
  const [autoAssigningLeadId, setAutoAssigningLeadId] = useState<string | null>(null);

  // AI Prompt bar
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiPlanning, setAiPlanning] = useState(false);
  const [aiResult, setAiResult] = useState<any | null>(null);

  // Load Projects
  const loadProjects = async () => {
    if (!token) return;
    setProjectsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/projects`);
      if (res.ok) {
        setProjects(await res.json());
      }
    } catch (err) {
      console.error('Failed to load projects', err);
    } finally {
      setProjectsLoading(false);
    }
  };

  // Load Sales Force Directory
  const loadSalesTeam = async () => {
    if (!token) return;
    setSalesTeamLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/salespeople`);
      if (res.ok) {
        setSalesTeam(await res.json());
      }
    } catch (err) {
      console.error('Failed to load sales team', err);
    } finally {
      setSalesTeamLoading(false);
    }
  };

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

      loadProjects();
      loadSalesTeam();
    } catch (err) {
      console.error('Failed to load field sales data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  // Load sub-view specific data
  useEffect(() => {
    if (activeSubView === 'schedule' && token) {
      fetchWithAuth(`${API_URL}/sales-os/field-sales/schedule`)
        .then((res) => res.json())
        .then((data) => setScheduleVisits(data.visits || []))
        .catch((err) => console.error(err));
    } else if (activeSubView === 'projects' && token) {
      loadProjects();
    } else if (activeSubView === 'team' && token) {
      loadSalesTeam();
    }
  }, [activeSubView, token]);

  // Project Management Handlers
  const handleCreateProject = async () => {
    if (!newProject.name.trim() || !token) {
      notify.error('Project name is required');
      return;
    }
    setIsSavingProject(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newProject,
          amenities: newProject.amenities.split(',').map((s) => s.trim()).filter(Boolean),
        }),
      });
      if (res.ok) {
        notify.success(`Project "${newProject.name}" created successfully`);
        setIsAddProjectOpen(false);
        setNewProject({
          name: '',
          code: '',
          location: '',
          city: 'Bangalore',
          address: '',
          latitude: 12.9716,
          longitude: 77.5946,
          rera_number: '',
          hold_duration_hours: 48,
          total_units: 50,
          amenities: 'Clubhouse, Swimming Pool, Gym, 24/7 Security',
          status: 'active',
        });
        loadProjects();
      } else {
        notify.error('Failed to create project');
      }
    } catch (err) {
      notify.error('Error creating project');
    } finally {
      setIsSavingProject(false);
    }
  };

  const handleOpenTeamModal = async (project: RealEstateProjectItem) => {
    setManagingProject(project);
    setProjectTeamDrawerOpen(true);
    setAiSuggestions([]);
    setSelectedTeamAssignments({});

    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/projects/${project.id}`);
      if (res.ok) {
        const fullProj = await res.json();
        setManagingProject(fullProj);
        const prefill: Record<string, { role: string; ai_recommended: boolean; match_score?: number; reason?: string }> = {};
        fullProj.team?.forEach((m: any) => {
          prefill[m.user_id] = {
            role: m.role || 'site_specialist',
            ai_recommended: m.ai_recommended || false,
            match_score: m.ai_match_score,
            reason: m.ai_recommendation_reason,
          };
        });
        setSelectedTeamAssignments(prefill);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleFetchAiTeamSuggestions = async (projectId: string) => {
    if (!token) return;
    setAiSuggestionsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/projects/${projectId}/ai-team-suggestions`);
      if (res.ok) {
        const data = await res.json();
        setAiSuggestions(data.suggested_team || []);
        // Automatically preselect recommended team
        const updated = { ...selectedTeamAssignments };
        (data.suggested_team || []).slice(0, 3).forEach((sug: AITeamSuggestion) => {
          updated[sug.user_id] = {
            role: sug.recommended_role,
            ai_recommended: true,
            match_score: sug.match_score,
            reason: sug.rationales[0],
          };
        });
        setSelectedTeamAssignments(updated);
        notify.success('AI evaluated sales specialists and generated optimal team suggestions');
      } else {
        notify.error('Failed to get AI team recommendations');
      }
    } catch (err) {
      notify.error('Network error fetching AI team suggestions');
    } finally {
      setAiSuggestionsLoading(false);
    }
  };

  const handleSaveProjectTeam = async () => {
    if (!managingProject || !token) return;
    setIsSavingTeam(true);
    try {
      const assignments = Object.entries(selectedTeamAssignments).map(([userId, details]) => ({
        user_id: userId,
        role: details.role,
        ai_recommended: details.ai_recommended,
        match_score: details.match_score,
        reason: details.reason,
      }));

      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/projects/${managingProject.id}/team`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignments }),
      });
      if (res.ok) {
        notify.success(`Sales team confirmed for ${managingProject.name}`);
        setProjectTeamDrawerOpen(false);
        loadProjects();
      } else {
        notify.error('Failed to update project team');
      }
    } catch (err) {
      notify.error('Network error saving project team');
    } finally {
      setIsSavingTeam(false);
    }
  };

  // Sales Force Directory Handlers
  const handleCreateSalesperson = async () => {
    if (!newSalesperson.name.trim() || !newSalesperson.email.trim() || !token) {
      notify.error('Name and Email are required');
      return;
    }
    setIsSavingSalesperson(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/salespeople`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSalesperson),
      });
      if (res.ok) {
        notify.success(`Specialist "${newSalesperson.name}" added to sales force`);
        setIsAddSalespersonOpen(false);
        setNewSalesperson({
          name: '',
          email: '',
          phone: '',
          designation: 'Property Specialist',
          working_hours_start: '09:00',
          working_hours_end: '18:00',
          max_visits_per_day: 6,
          initial_project_ids: [],
        });
        loadSalesTeam();
      } else {
        notify.error('Failed to create salesperson');
      }
    } catch (err) {
      notify.error('Error creating salesperson');
    } finally {
      setIsSavingSalesperson(false);
    }
  };

  const handleToggleAgentShift = async (userId: string, currentActive: boolean) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/salespeople/${userId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          is_shift_active: !currentActive,
          status: !currentActive ? 'available' : 'off_duty',
        }),
      });
      if (res.ok) {
        notify.success(`Shift status updated`);
        loadSalesTeam();
      }
    } catch (err) {
      notify.error('Failed to update shift status');
    }
  };

  // Autonomous Lead Auto-Dispatch Handler
  const handleAutoAssignLead = async (leadId: string) => {
    if (!token) return;
    setAutoAssigningLeadId(leadId);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/leads/${leadId}/auto-assign-visit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data: AutoAssignResult = await res.json();
        setAutoAssignResult(data);
        setAutoAssignModalOpen(true);
        notify.success(`Lead assigned to specialist ${data.assigned_specialist.name}`);
        loadData();
      } else {
        notify.error('Auto-dispatch failed');
      }
    } catch (err) {
      notify.error('Error contacting auto-dispatch service');
    } finally {
      setAutoAssigningLeadId(null);
    }
  };

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
            { id: 'projects', label: 'Projects & Inventory', icon: <Building2 size={14} /> },
            { id: 'team', label: 'Sales Force & Rosters', icon: <Users size={14} /> },
            { id: 'dispatch_map', label: 'Live Dispatch Map', icon: <Compass size={14} /> },
            { id: 'schedule', label: 'Team Schedule', icon: <Calendar size={14} /> },
            { id: 'priority_leads', label: 'Priority Showings', icon: <Navigation size={14} /> },
            { id: 'ai_studio', label: 'AI Recovery Studio', icon: <Sparkles size={14} />, badge: proposals.filter((p) => p.status === 'pending_review').length || undefined },
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

      {/* ── 2. SUB-VIEW: PROJECTS & INVENTORY CATALOG ── */}
      {activeSubView === 'projects' && (
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Building2 size={16} className="text-primary" /> Property Developments & Master Projects
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Configure project coordinates, unit inventory, and assigned sales specialist teams.
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setIsAddProjectOpen(true)}
                className="h-8 text-xs gap-1.5 self-start sm:self-auto bg-primary text-primary-foreground font-semibold"
              >
                <Plus size={14} /> Add New Project
              </Button>
            </div>

            {projectsLoading ? (
              <div className="py-12 flex flex-col items-center justify-center text-muted-foreground text-xs gap-2">
                <RefreshCw size={18} className="animate-spin text-primary" />
                <span>Loading property development portfolio...</span>
              </div>
            ) : projects.length === 0 ? (
              <div className="py-12 text-center border-2 border-dashed border-border rounded-xl p-6 mt-4">
                <Building2 size={32} className="mx-auto text-muted-foreground mb-2" />
                <h4 className="text-sm font-bold text-foreground">No projects registered yet</h4>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  Add your first real estate project with location, RERA, and unit inventory to enable AI team matching.
                </p>
                <Button size="sm" onClick={() => setIsAddProjectOpen(true)} className="mt-4 text-xs gap-1">
                  <Plus size={12} /> Create Project
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-5">
                {projects.map((proj) => (
                  <div key={proj.id} className="bg-background border border-border rounded-xl p-4 shadow-xs flex flex-col justify-between hover:border-primary/40 transition-all">
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                            {proj.name}
                          </h4>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            CODE: {proj.code || proj.id.slice(0, 8)}
                          </span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                          proj.status === 'active'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : proj.status === 'pre_launch'
                            ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          {proj.status || 'Active'}
                        </span>
                      </div>

                      <div className="mt-3 space-y-1 text-xs">
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <MapPin size={13} className="text-primary shrink-0" />
                          <span className="truncate">{proj.location ? `${proj.location}, ` : ''}{proj.city || 'Bangalore'}</span>
                        </div>
                        {proj.address && (
                          <p className="text-[11px] text-muted-foreground line-clamp-1 pl-4.5">
                            {proj.address}
                          </p>
                        )}
                        {proj.rera_number && (
                          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                            <ShieldCheck size={12} className="text-emerald-400 shrink-0" />
                            <span className="truncate">RERA: {proj.rera_number}</span>
                          </div>
                        )}
                      </div>

                      {/* Units & Inventory Metric Badges */}
                      <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-border/60 text-center">
                        <div className="bg-muted/40 rounded p-1.5">
                          <span className="text-[9px] uppercase tracking-wider text-muted-foreground block">Total Units</span>
                          <span className="text-xs font-bold text-foreground">{proj.total_units || 0}</span>
                        </div>
                        <div className="bg-muted/40 rounded p-1.5">
                          <span className="text-[9px] uppercase tracking-wider text-muted-foreground block">Available</span>
                          <span className="text-xs font-bold text-emerald-400">{proj.available_units || 0}</span>
                        </div>
                        <div className="bg-muted/40 rounded p-1.5">
                          <span className="text-[9px] uppercase tracking-wider text-muted-foreground block">Hold Window</span>
                          <span className="text-xs font-bold text-foreground">{proj.hold_duration_hours || 48}h</span>
                        </div>
                      </div>

                      {/* Amenities Pills */}
                      {proj.amenities && proj.amenities.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-3">
                          {proj.amenities.slice(0, 3).map((a, i) => (
                            <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground">
                              {a}
                            </span>
                          ))}
                          {proj.amenities.length > 3 && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground">
                              +{proj.amenities.length - 3} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Team Allocation Footer */}
                    <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs">
                        <Users size={13} className="text-primary" />
                        <span className="font-semibold text-foreground">
                          {proj.assigned_team_count || 0}
                        </span>
                        <span className="text-muted-foreground text-[11px]">Specialist(s)</span>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleOpenTeamModal(proj)}
                        className="h-7 text-[11px] gap-1 font-semibold hover:border-primary/50"
                      >
                        <Sparkles size={11} className="text-primary" /> Team & AI Match
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 3. SUB-VIEW: SALES FORCE DIRECTORY & ROSTERS ── */}
      {activeSubView === 'team' && (
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Users size={16} className="text-primary" /> Sales Specialists & Showing Rosters
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Manage field sales representatives, working shift hours, daily showing limits, and project allocations.
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setIsAddSalespersonOpen(true)}
                className="h-8 text-xs gap-1.5 self-start sm:self-auto bg-primary text-primary-foreground font-semibold"
              >
                <UserPlus size={14} /> Add Sales Specialist
              </Button>
            </div>

            {salesTeamLoading ? (
              <div className="py-12 flex flex-col items-center justify-center text-muted-foreground text-xs gap-2">
                <RefreshCw size={18} className="animate-spin text-primary" />
                <span>Loading sales force directory...</span>
              </div>
            ) : salesTeam.length === 0 ? (
              <div className="py-12 text-center border-2 border-dashed border-border rounded-xl p-6 mt-4">
                <Users size={32} className="mx-auto text-muted-foreground mb-2" />
                <h4 className="text-sm font-bold text-foreground">No specialists in the directory</h4>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  Add property specialists to dispatch tours and manage showing appointments.
                </p>
                <Button size="sm" onClick={() => setIsAddSalespersonOpen(true)} className="mt-4 text-xs gap-1">
                  <UserPlus size={12} /> Add First Specialist
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-5">
                {salesTeam.map((sp) => (
                  <div key={sp.user_id} className="bg-background border border-border rounded-xl p-4 shadow-xs flex flex-col justify-between hover:border-primary/40 transition-all">
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="text-xs font-bold text-foreground">{sp.name}</h4>
                          <span className="text-[10px] text-muted-foreground font-mono">{sp.email}</span>
                        </div>
                        <button
                          onClick={() => handleToggleAgentShift(sp.user_id, sp.is_shift_active)}
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold flex items-center gap-1 transition-all ${
                            sp.is_shift_active
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : 'bg-muted text-muted-foreground'
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${sp.is_shift_active ? 'bg-emerald-400 animate-pulse' : 'bg-neutral-500'}`} />
                          {sp.is_shift_active ? 'On Duty' : 'Off Duty'}
                        </button>
                      </div>

                      <div className="mt-3 space-y-1.5 text-xs">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Designation:</span>
                          <span className="font-semibold text-foreground">{sp.designation || 'Specialist'}</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Shift Hours:</span>
                          <span className="font-mono text-foreground">{sp.working_hours_start || '09:00'} - {sp.working_hours_end || '18:00'}</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="text-muted-foreground">Phone:</span>
                          <span className="font-mono text-foreground">{sp.phone || 'Not configured'}</span>
                        </div>
                      </div>

                      {/* Daily Load Meter */}
                      <div className="mt-3 pt-3 border-t border-border/60">
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                          <span>Today's Showing Load</span>
                          <span className="font-bold text-foreground">{sp.today_visits} / {sp.max_visits_per_day} visits</span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              sp.today_visits >= sp.max_visits_per_day
                                ? 'bg-rose-500'
                                : sp.today_visits >= sp.max_visits_per_day * 0.7
                                ? 'bg-amber-500'
                                : 'bg-emerald-400'
                            }`}
                            style={{ width: `${Math.min(100, (sp.today_visits / Math.max(1, sp.max_visits_per_day)) * 100)}%` }}
                          />
                        </div>
                      </div>

                      {/* Assigned Projects */}
                      <div className="mt-3 pt-2">
                        <span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">
                          Assigned Projects ({sp.assigned_projects_count || 0})
                        </span>
                        {sp.assigned_projects && sp.assigned_projects.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {sp.assigned_projects.map((p, i) => (
                              <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                                {p.project_name} ({p.role === 'primary_lead' ? 'Lead' : 'Specialist'})
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-[10px] text-muted-foreground italic">No projects currently assigned</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 4. SUB-VIEW: LIVE DISPATCH MAP & FLEET TRACKING ── */}
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
                  backgroundImage: 'radial-gradient(#414C5A 1px, transparent 1px)',
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
                  <div className="mt-4 pt-3 border-t border-border flex items-center justify-between gap-2">
                    <span className="text-[10px] text-muted-foreground font-mono truncate">{lead.phone || 'No phone'}</span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Button
                        size="sm"
                        disabled={autoAssigningLeadId === lead.id}
                        onClick={() => handleAutoAssignLead(lead.id)}
                        className="h-7 text-[11px] gap-1 bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
                      >
                        <Zap size={11} className={autoAssigningLeadId === lead.id ? 'animate-spin' : ''} />
                        Auto-Dispatch
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleExecuteAiPlan(`Plan showing for ${lead.name} near active project cluster`)}
                        className="h-7 text-[11px] gap-1"
                      >
                        <Sparkles size={11} /> Plan
                      </Button>
                    </div>
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

      {/* ── MODAL 1: ADD PROPERTY PROJECT ── */}
      {isAddProjectOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <Building2 size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">Add Property Development Project</h3>
                  <p className="text-xs text-muted-foreground">Register new development specs, geocoordinates, and units.</p>
                </div>
              </div>
              <button
                onClick={() => setIsAddProjectOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Project Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Sobha Royal Pavilion"
                    value={newProject.name}
                    onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Project Code</label>
                  <input
                    type="text"
                    placeholder="e.g. SRP_EAST"
                    value={newProject.code}
                    onChange={(e) => setNewProject({ ...newProject, code: e.target.value })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Location / Locality</label>
                  <input
                    type="text"
                    placeholder="e.g. Sarjapur Road"
                    value={newProject.location}
                    onChange={(e) => setNewProject({ ...newProject, location: e.target.value })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">City</label>
                  <input
                    type="text"
                    placeholder="e.g. Bangalore"
                    value={newProject.city}
                    onChange={(e) => setNewProject({ ...newProject, city: e.target.value })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">Full Site Address</label>
                <input
                  type="text"
                  placeholder="e.g. Sarjapur Main Rd, Hadosiddapura, Bengaluru 560035"
                  value={newProject.address}
                  onChange={(e) => setNewProject({ ...newProject, address: e.target.value })}
                  className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Latitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={newProject.latitude}
                    onChange={(e) => setNewProject({ ...newProject, latitude: parseFloat(e.target.value) || 0 })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Longitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={newProject.longitude}
                    onChange={(e) => setNewProject({ ...newProject, longitude: parseFloat(e.target.value) || 0 })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Total Units</label>
                  <input
                    type="number"
                    value={newProject.total_units}
                    onChange={(e) => setNewProject({ ...newProject, total_units: parseInt(e.target.value, 10) || 0 })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Hold Window (Hours)</label>
                  <input
                    type="number"
                    value={newProject.hold_duration_hours}
                    onChange={(e) => setNewProject({ ...newProject, hold_duration_hours: parseInt(e.target.value, 10) || 48 })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Status</label>
                  <select
                    value={newProject.status}
                    onChange={(e) => setNewProject({ ...newProject, status: e.target.value })}
                    className="w-full h-8 px-2 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  >
                    <option value="active">Active</option>
                    <option value="pre_launch">Pre-Launch</option>
                    <option value="planning">Planning</option>
                    <option value="sold_out">Sold Out</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">RERA Number</label>
                <input
                  type="text"
                  placeholder="e.g. PRM/KA/RERA/1251/308/PR/190204/002338"
                  value={newProject.rera_number}
                  onChange={(e) => setNewProject({ ...newProject, rera_number: e.target.value })}
                  className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">Amenities (comma-separated)</label>
                <input
                  type="text"
                  value={newProject.amenities}
                  onChange={(e) => setNewProject({ ...newProject, amenities: e.target.value })}
                  placeholder="Clubhouse, Pool, Gymnasium, 24/7 Security"
                  className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddProjectOpen(false)}
                className="h-8 text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleCreateProject}
                disabled={isSavingProject}
                className="h-8 text-xs gap-1.5"
              >
                {isSavingProject ? <RefreshCw size={12} className="animate-spin" /> : <Plus size={12} />}
                Create Project
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 2: PROJECT TEAM ALLOCATION & AI SUGGESTIONS ── */}
      {projectTeamDrawerOpen && managingProject && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between pb-3 border-b border-border">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-foreground">
                    Project Sales Team: {managingProject.name}
                  </h3>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-bold uppercase">
                    {managingProject.city || 'Bangalore'}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Admin team configuration. AI evaluates proximity, workload, and performance to recommend optimal specialists.
                </p>
              </div>
              <button
                onClick={() => setProjectTeamDrawerOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X size={16} />
              </button>
            </div>

            {/* AI Team Suggestion Banner */}
            <div className="bg-gradient-to-r from-primary/15 via-card to-card border border-primary/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-primary/20 text-primary flex items-center justify-center shrink-0">
                  <Sparkles size={18} />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-foreground">AI Sales Specialist Matcher</h4>
                  <p className="text-[11px] text-muted-foreground">
                    Analyzes locality distance, existing project allocations, and conversion history.
                  </p>
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => handleFetchAiTeamSuggestions(managingProject.id)}
                disabled={aiSuggestionsLoading}
                className="h-7.5 text-xs gap-1.5 shrink-0 bg-primary font-semibold"
              >
                {aiSuggestionsLoading ? <RefreshCw size={12} className="animate-spin" /> : <Sparkles size={12} />}
                AI Recommend Team
              </Button>
            </div>

            {/* AI Recommendations List */}
            {aiSuggestions.length > 0 && (
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-bold text-primary tracking-wider flex items-center gap-1.5">
                  <Award size={12} /> AI Ranked Suggestions (Select to assign)
                </span>
                <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1">
                  {aiSuggestions.map((sug) => {
                    const isSelected = !!selectedTeamAssignments[sug.user_id];
                    return (
                      <div
                        key={sug.user_id}
                        onClick={() => {
                          const updated = { ...selectedTeamAssignments };
                          if (isSelected) {
                            delete updated[sug.user_id];
                          } else {
                            updated[sug.user_id] = {
                              role: sug.recommended_role,
                              ai_recommended: true,
                              match_score: sug.match_score,
                              reason: sug.rationales[0],
                            };
                          }
                          setSelectedTeamAssignments(updated);
                        }}
                        className={`p-3 rounded-xl border text-xs cursor-pointer transition-all flex items-start justify-between gap-3 ${
                          isSelected
                            ? 'bg-primary/10 border-primary/40 shadow-xs'
                            : 'bg-background border-border hover:border-primary/30'
                        }`}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-foreground">{sug.name}</span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
                              {sug.match_score}% Match
                            </span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-muted text-muted-foreground uppercase font-mono">
                              {sug.recommended_role.replace('_', ' ')}
                            </span>
                          </div>
                          <ul className="text-[11px] text-muted-foreground space-y-0.5">
                            {sug.rationales.map((r, i) => (
                              <li key={i} className="flex items-center gap-1">
                                <span className="text-primary">•</span> {r}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div className="shrink-0 pt-0.5">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            readOnly
                            className="w-4 h-4 rounded text-primary border-border focus:ring-0"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Current / Confirmed Team Section */}
            <div className="space-y-2 pt-2 border-t border-border">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-foreground uppercase tracking-wider">
                  Configured Project Specialists ({Object.keys(selectedTeamAssignments).length})
                </span>
                <span className="text-[10px] text-muted-foreground">Admin confirmation required to activate</span>
              </div>

              {Object.keys(selectedTeamAssignments).length === 0 ? (
                <div className="text-center py-6 border border-dashed border-border rounded-xl text-xs text-muted-foreground">
                  No specialists currently assigned. Use "AI Recommend Team" or add agents manually below.
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {Object.entries(selectedTeamAssignments).map(([userId, details]) => {
                    const agent = salesTeam.find((s) => s.user_id === userId) || { name: userId, email: '' };
                    return (
                      <div key={userId} className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-background border border-border text-xs">
                        <div>
                          <span className="font-semibold text-foreground">{agent.name}</span>
                          {details.ai_recommended && (
                            <span className="ml-2 text-[9px] px-1 rounded bg-primary/10 text-primary font-mono">AI Recommended</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <select
                            value={details.role}
                            onChange={(e) => {
                              setSelectedTeamAssignments({
                                ...selectedTeamAssignments,
                                [userId]: { ...details, role: e.target.value },
                              });
                            }}
                            className="h-7 px-2 rounded border border-border bg-card text-[11px] text-foreground focus:outline-none"
                          >
                            <option value="primary_lead">Primary Lead</option>
                            <option value="site_specialist">Site Specialist</option>
                            <option value="relationship_manager">Relationship Manager</option>
                          </select>
                          <button
                            onClick={() => {
                              const updated = { ...selectedTeamAssignments };
                              delete updated[userId];
                              setSelectedTeamAssignments(updated);
                            }}
                            className="p-1 rounded text-rose-400 hover:bg-rose-500/10"
                            title="Remove agent from team"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Quick Add from Sales Pool */}
            <div className="pt-2 border-t border-border flex items-center gap-2">
              <span className="text-[11px] text-muted-foreground shrink-0">Quick Add:</span>
              <select
                onChange={(e) => {
                  const uid = e.target.value;
                  if (uid && !selectedTeamAssignments[uid]) {
                    setSelectedTeamAssignments({
                      ...selectedTeamAssignments,
                      [uid]: { role: 'site_specialist', ai_recommended: false },
                    });
                  }
                  e.target.value = '';
                }}
                className="h-7.5 px-2 rounded-lg border border-border bg-background text-[11px] text-foreground focus:outline-none w-full"
              >
                <option value="">Select an agent from the sales force...</option>
                {salesTeam
                  .filter((s) => !selectedTeamAssignments[s.user_id])
                  .map((s) => (
                    <option key={s.user_id} value={s.user_id}>
                      {s.name} ({s.designation || 'Specialist'})
                    </option>
                  ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setProjectTeamDrawerOpen(false)}
                className="h-8 text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveProjectTeam}
                disabled={isSavingTeam}
                className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground font-semibold"
              >
                {isSavingTeam ? <RefreshCw size={12} className="animate-spin" /> : <Check size={12} />}
                Confirm & Implement Team
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 3: ADD SALES SPECIALIST ── */}
      {isAddSalespersonOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  <UserPlus size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">Add Sales Specialist</h3>
                  <p className="text-xs text-muted-foreground">Provision field agent profile, shift hours, and capacity.</p>
                </div>
              </div>
              <button
                onClick={() => setIsAddSalespersonOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">Full Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rahul Sharma"
                  value={newSalesperson.name}
                  onChange={(e) => setNewSalesperson({ ...newSalesperson, name: e.target.value })}
                  className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-foreground mb-1">Email Address *</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. rahul.sharma@sobha.com"
                  value={newSalesperson.email}
                  onChange={(e) => setNewSalesperson({ ...newSalesperson, email: e.target.value })}
                  className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Phone Number</label>
                  <input
                    type="text"
                    placeholder="+91 98765 43210"
                    value={newSalesperson.phone}
                    onChange={(e) => setNewSalesperson({ ...newSalesperson, phone: e.target.value })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Role / Designation</label>
                  <input
                    type="text"
                    placeholder="e.g. Senior Luxury Specialist"
                    value={newSalesperson.designation}
                    onChange={(e) => setNewSalesperson({ ...newSalesperson, designation: e.target.value })}
                    className="w-full h-8 px-2.5 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Shift Start</label>
                  <input
                    type="text"
                    value={newSalesperson.working_hours_start}
                    onChange={(e) => setNewSalesperson({ ...newSalesperson, working_hours_start: e.target.value })}
                    className="w-full h-8 px-2 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Shift End</label>
                  <input
                    type="text"
                    value={newSalesperson.working_hours_end}
                    onChange={(e) => setNewSalesperson({ ...newSalesperson, working_hours_end: e.target.value })}
                    className="w-full h-8 px-2 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1">Max Visits/Day</label>
                  <input
                    type="number"
                    value={newSalesperson.max_visits_per_day}
                    onChange={(e) => setNewSalesperson({ ...newSalesperson, max_visits_per_day: parseInt(e.target.value, 10) || 6 })}
                    className="w-full h-8 px-2 rounded-lg border border-border bg-background text-foreground text-xs focus:ring-1 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>

              {/* Initial Projects Selection */}
              {projects.length > 0 && (
                <div>
                  <label className="block text-[11px] font-semibold text-foreground mb-1.5">Assign Initial Project(s)</label>
                  <div className="space-y-1 max-h-32 overflow-y-auto border border-border rounded-lg p-2 bg-background">
                    {projects.map((p) => {
                      const isAssigned = newSalesperson.initial_project_ids.includes(p.id);
                      return (
                        <label key={p.id} className="flex items-center gap-2 text-[11px] text-foreground cursor-pointer py-0.5">
                          <input
                            type="checkbox"
                            checked={isAssigned}
                            onChange={() => {
                              const updated = isAssigned
                                ? newSalesperson.initial_project_ids.filter((id) => id !== p.id)
                                : [...newSalesperson.initial_project_ids, p.id];
                              setNewSalesperson({ ...newSalesperson, initial_project_ids: updated });
                            }}
                            className="w-3.5 h-3.5 rounded text-primary border-border focus:ring-0"
                          />
                          <span>{p.name} ({p.location || p.city})</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddSalespersonOpen(false)}
                className="h-8 text-xs"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleCreateSalesperson}
                disabled={isSavingSalesperson}
                className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground font-semibold"
              >
                {isSavingSalesperson ? <RefreshCw size={12} className="animate-spin" /> : <UserPlus size={12} />}
                Add Specialist
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 4: AUTONOMOUS LEAD DISPATCH RESULT ── */}
      {autoAssignModalOpen && autoAssignResult && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center shrink-0">
                  <CheckCircle2 size={20} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">Showing Successfully Assigned!</h3>
                  <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">
                    {autoAssignResult.assignment_status.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setAutoAssignModalOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-md"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3 bg-muted/40 p-3 rounded-xl border border-border/60">
                <div>
                  <span className="text-[10px] uppercase text-muted-foreground font-semibold block">Matched Project</span>
                  <span className="font-bold text-foreground text-sm">{autoAssignResult.project.name}</span>
                  <span className="text-muted-foreground block text-[11px]">{autoAssignResult.project.location || autoAssignResult.project.city}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase text-muted-foreground font-semibold block">Assigned Specialist</span>
                  <span className="font-bold text-foreground text-sm">{autoAssignResult.assigned_specialist.name}</span>
                  <span className="text-primary block text-[11px] font-mono">{autoAssignResult.assigned_specialist.phone || autoAssignResult.assigned_specialist.email}</span>
                </div>
              </div>

              {/* Showing Time */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-background border border-border">
                <div className="flex items-center gap-2">
                  <Calendar size={15} className="text-primary" />
                  <div>
                    <span className="font-semibold text-foreground">Showing Appointment Booked</span>
                    <p className="text-[11px] text-muted-foreground">
                      {new Date(autoAssignResult.visit.scheduled_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} at{' '}
                      {new Date(autoAssignResult.visit.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
                  {autoAssignResult.visit.duration_minutes || 45} mins
                </span>
              </div>

              {/* Explainable AI Decision Rationale */}
              <div className="bg-gradient-to-r from-primary/10 via-card to-card border border-primary/20 rounded-xl p-3.5 space-y-1.5">
                <span className="text-[10px] font-bold uppercase text-primary tracking-wider flex items-center gap-1.5">
                  <Sparkles size={12} /> Autonomous AI Dispatch Decision
                </span>
                <p className="text-xs text-foreground font-medium">
                  {autoAssignResult.decision_rationale}
                </p>
              </div>

              {/* Take Care Execution Summary */}
              <div className="space-y-1.5 pt-1 text-[11px] text-muted-foreground">
                <div className="flex items-center gap-2 text-emerald-400">
                  <Check size={13} />
                  <span>Lead stage updated to <strong>Visit Scheduled</strong></span>
                </div>
                <div className="flex items-center gap-2 text-emerald-400">
                  <Check size={13} />
                  <span>Showing added to <strong>{autoAssignResult.assigned_specialist.name}'s</strong> itinerary</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-400">
                  <Check size={13} />
                  <span>Dispatch history recorded in audit timeline</span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-border flex justify-end">
              <Button
                size="sm"
                onClick={() => setAutoAssignModalOpen(false)}
                className="h-8 text-xs font-semibold px-4"
              >
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

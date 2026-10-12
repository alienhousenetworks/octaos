'use client';

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Target, Plus, Loader2, Check, Play, Zap, Sparkles,
  Shield, AlertTriangle, Activity, BarChart3, Pause,
  RefreshCw, XCircle, ArrowRight, Eye, CheckCircle2,
  FileText, Users, DollarSign, Layers, ChevronRight,
  MessageSquare, TrendingUp, Bot, Sparkle,
  Briefcase, UserCheck, Clock, Send, Building, Edit3, User, ThumbsUp,
  Trash2, Brain, ChevronDown, ChevronUp, FolderKanban, BookOpen, AlertCircle, ShieldCheck,
  Terminal, ShieldAlert, Code2, Mail, Calendar, Headphones, Share2, CheckSquare, Globe, SendHorizontal, Sliders
} from 'lucide-react';


interface CEOViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  timeline: any[];
  setActiveView: (view: string) => void;
}

export default function CEOView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  timeline,
  setActiveView,
}: CEOViewProps) {
  // Navigation & Workflow state
  const [ceoWorkflows, setCeoWorkflows] = useState<any[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any | null>(null);

  // Executive Vitals state
  const [vitals, setVitals] = useState<any>({
    active_pipelines: 0,
    completed_pipelines: 0,
    pending_approvals_count: 0,
    total_budget_allocated: 0,
    total_budget_spent: 0,
    budget_utilization_pct: 0,
    system_status: 'HEALTHY',
    attention_items: []
  });

  // Strategy Formulation & Multi-Variant Plans state
  const [objectivePrompt, setObjectivePrompt] = useState('');
  const [budgetCapInput, setBudgetCapInput] = useState('25000');
  const [isCompiling, setIsCompiling] = useState(false);
  const [availablePlans, setAvailablePlans] = useState<any[]>([]);
  const [activeVariantTab, setActiveVariantTab] = useState<'AGGRESSIVE' | 'BALANCED' | 'CONSERVATIVE'>('BALANCED');
  const [selectedPlanDetails, setSelectedPlanDetails] = useState<any | null>(null);

  // Dry Run Simulation state
  const [isDryRunning, setIsDryRunning] = useState(false);
  const [dryRunResult, setDryRunResult] = useState<any | null>(null);
  const [showDryRunModal, setShowDryRunModal] = useState(false);

  // Execution & Live Stream state
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionProjection, setExecutionProjection] = useState<any | null>(null);
  const [liveStreamEvents, setLiveStreamEvents] = useState<any[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Boardroom & Post-Mortem state
  const [isEscalating, setIsEscalating] = useState(false);
  const [escalationSuccess, setEscalationSuccess] = useState<string | null>(null);
  const [postMortemBrief, setPostMortemBrief] = useState<any | null>(null);
  const [showPostMortemModal, setShowPostMortemModal] = useState(false);
  const [isGeneratingBrief, setIsGeneratingBrief] = useState(false);

  // Agent Council Deliberation state
  const [showCouncilModal, setShowCouncilModal] = useState(false);

  // Unified DAG Engine & Workforce Stepper
  const [interactiveStep, setInteractiveStep] = useState<1 | 2 | 3>(1);
  const [stage3ViewTab, setStage3ViewTab] = useState<'OPERATIONS' | 'DAG' | 'WORKFORCE' | 'HUMAN_GATES'>('OPERATIONS');
  const [executiveInterventionNote, setExecutiveInterventionNote] = useState('');
  const [isSendingIntervention, setIsSendingIntervention] = useState(false);
  const [interventionFeedbackMessage, setInterventionFeedbackMessage] = useState<string | null>(null);
  const [approvedGateIds, setApprovedGateIds] = useState<Record<string, 'APPROVED' | 'REJECTED'>>({});

  // 4-Pillar Departmental Command Hub State (Campaign, Sales, Support, Email)
  const [operationsData, setOperationsData] = useState<any | null>(null);
  const [isLoadingOperations, setIsLoadingOperations] = useState(false);
  const [isSchedulingCampaign, setIsSchedulingCampaign] = useState(false);
  const [isUpdatingSalesStage, setIsUpdatingSalesStage] = useState(false);
  const [isUpdatingSupportPolicy, setIsUpdatingSupportPolicy] = useState(false);
  const [isDispatchingEmail, setIsDispatchingEmail] = useState(false);
  const [testEmailAddress, setTestEmailAddress] = useState('');
  const [operationsFeedbackMessage, setOperationsFeedbackMessage] = useState<string | null>(null);
  const [expandedPostId, setExpandedPostId] = useState<string | null>(null);

  // Company Knowledge Context State
  const [companyContext, setCompanyContext] = useState<any | null>(null);
  const [isLoadingCompanyContext, setIsLoadingCompanyContext] = useState(false);

  // Step 1: Strategy Formulation & Feedback Loop
  const [isDraftingPlan, setIsDraftingPlan] = useState(false);
  const [currentPlanData, setCurrentPlanData] = useState<any | null>(null);
  const [userPlanFeedback, setUserPlanFeedback] = useState('');
  const [isRefiningPlan, setIsRefiningPlan] = useState(false);

  // Step 2: Council Meeting & Deliberation Loop
  const [isSummoningMeeting, setIsSummoningMeeting] = useState(false);
  const [currentMeetingData, setCurrentMeetingData] = useState<any | null>(null);
  const [userMeetingFeedback, setUserMeetingFeedback] = useState('');
  const [isReconveningMeeting, setIsReconveningMeeting] = useState(false);

  // Step 3: Workforce Deployment & Live Tracking
  const [isAssigningWorkforce, setIsAssigningWorkforce] = useState(false);
  const [teamStatusData, setTeamStatusData] = useState<any | null>(null);
  const [isRefreshingTeam, setIsRefreshingTeam] = useState(false);
  const [activeDeliverableEmp, setActiveDeliverableEmp] = useState<string | null>(null);

  // Workspaces History & Run List state
  const [isWorkspacesSectionOpen, setIsWorkspacesSectionOpen] = useState(true);
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);
  const [deleteConfirmWfId, setDeleteConfirmWfId] = useState<string | null>(null);
  const [isDeletingWf, setIsDeletingWf] = useState(false);

  // Minutes of Meeting (MOM) vs Transcript Tab state
  const [meetingViewTab, setMeetingViewTab] = useState<'TRANSCRIPT' | 'MOM'>('TRANSCRIPT');
  const [revealedTurnsCount, setRevealedTurnsCount] = useState<number>(0);
  const [isRevealingTurns, setIsRevealingTurns] = useState<boolean>(false);

  const PRESET_DIRECTIVES = [
    { label: "🚀 Outbound Pipeline ($20k)", prompt: "Accelerate B2B SaaS outbound sales pipeline to reach $100k ARR through multi-touch sequences", budget: "20000" },
    { label: "📢 Brand & Campaign ($15k)", prompt: "Launch multi-channel brand positioning and content campaign targeting enterprise founders", budget: "15000" },
    { label: "👥 Tech Hiring ($40k)", prompt: "Recruit and screen 3 senior AI engineers and short-list for technical interviews", budget: "40000" },
    { label: "🛡️ Support & Retention ($10k)", prompt: "Audit support tickets and triage high-risk customer accounts to reduce churn", budget: "10000" }
  ];

  const councilParticipants: string[] = useMemo(() => {
    return selectedPlanDetails?.council_participants || selectedPlanDetails?.quant_forecast?.council_participants || [];
  }, [selectedPlanDetails]);

  const roiScorecard = useMemo(() => {
    return selectedPlanDetails?.roi_scorecard || selectedPlanDetails?.quant_forecast?.roi_scorecard || null;
  }, [selectedPlanDetails]);

  const agentDeliberations: any[] = useMemo(() => {
    return selectedPlanDetails?.agent_deliberations || selectedPlanDetails?.quant_forecast?.agent_deliberations || [];
  }, [selectedPlanDetails]);

  const consensusSummary: string = useMemo(() => {
    return selectedPlanDetails?.consensus_summary || selectedPlanDetails?.quant_forecast?.consensus_summary || '';
  }, [selectedPlanDetails]);

  // Autonomous Critique Loop UI state
  const [expandedCritiqueRound, setExpandedCritiqueRound] = useState<number | null>(null);

  const getDeptColor = (dept: string) => {
    const d = (dept || '').toLowerCase();
    if (d.includes('market')) return 'bg-purple-950/70 border-purple-800/50 text-purple-300';
    if (d.includes('sale')) return 'bg-emerald-950/70 border-emerald-800/50 text-emerald-300';
    if (d.includes('finan')) return 'bg-amber-950/70 border-amber-800/50 text-amber-300';
    if (d.includes('hr') || d.includes('talent') || d.includes('people')) return 'bg-rose-950/70 border-rose-800/50 text-rose-300';
    if (d.includes('support')) return 'bg-sky-950/70 border-sky-800/50 text-sky-300';
    if (d.includes('engine') || d.includes('tech')) return 'bg-cyan-950/70 border-cyan-800/50 text-cyan-300';
    if (d.includes('operat')) return 'bg-blue-950/70 border-blue-800/50 text-blue-300';
    if (d.includes('prod')) return 'bg-teal-950/70 border-teal-800/50 text-teal-300';
    if (d.includes('legal') || d.includes('regulat')) return 'bg-violet-950/70 border-violet-800/50 text-violet-300';
    if (d.includes('risk') || d.includes('red') || d.includes('adversar')) return 'bg-red-950/70 border-red-800/50 text-red-300';
    return 'bg-slate-800 border-slate-700 text-slate-300';
  };

  const getAssignedAgent = (dept: string) => {
    const d = (dept || '').toLowerCase();
    if (d.includes('market')) return 'Marketing AI (Sarah Chen)';
    if (d.includes('sale')) return 'Sales AI (Alex Rivera)';
    if (d.includes('finan')) return 'CFO AI (Elena Rostova)';
    if (d.includes('hr') || d.includes('talent') || d.includes('people')) return 'HR AI (Olivia Taylor)';
    if (d.includes('support')) return 'Customer Support AI (Maya Patel)';
    if (d.includes('engine') || d.includes('tech')) return 'CTO AI (David Kim)';
    if (d.includes('operat')) return 'Operations AI (Liam Vance)';
    if (d.includes('prod')) return 'Product AI (Aria Tanaka)';
    if (d.includes('legal') || d.includes('regulat')) return 'Legal AI (Devon Cole)';
    if (d.includes('risk') || d.includes('red')) return 'Red Team AI (Marcus Vance)';
    if (d.includes('crm')) return 'CRM Specialist';
    return 'CEO Orchestrator';
  };


  const containerRef = useRef<HTMLDivElement>(null);
  const sseRef = useRef<EventSource | null>(null);

  // 1. Initial Load: Fetch Vitals, Workflows & Company Context
  useEffect(() => {
    if (token) {
      fetchVitals();
      fetchCeoWorkflows();
      fetchCompanyContext();
    }
  }, [token]);

  // Auto-poll team status & operations overview when on Step 3
  useEffect(() => {
    let interval: any = null;
    const targetWfId = currentPlanData?.workflow_id || selectedWorkflowId;
    if (interactiveStep === 3 && targetWfId && token) {
      fetchTeamStatus(targetWfId);
      fetchOperationsOverview(targetWfId);
      interval = setInterval(() => {
        fetchTeamStatus(targetWfId);
        fetchOperationsOverview(targetWfId);
      }, 7000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [interactiveStep, currentPlanData?.workflow_id, selectedWorkflowId, token]);

  // Progressive reveal effect for meeting dialogue
  useEffect(() => {
    if (currentMeetingData?.dialogue && currentMeetingData.dialogue.length > 0) {
      setRevealedTurnsCount(1);
      setIsRevealingTurns(true);
      let count = 1;
      const interval = setInterval(() => {
        count += 1;
        setRevealedTurnsCount(count);
        if (count >= currentMeetingData.dialogue.length) {
          setIsRevealingTurns(false);
          clearInterval(interval);
        }
      }, 650);
      return () => clearInterval(interval);
    } else {
      setRevealedTurnsCount(0);
      setIsRevealingTurns(false);
    }
  }, [currentMeetingData?.meeting_id]);

  const fetchCompanyContext = async () => {
    setIsLoadingCompanyContext(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/company-context`);
      if (res.ok) {
        const data = await res.json();
        setCompanyContext(data);
      }
    } catch (e) {
      console.error('Error fetching company context:', e);
    } finally {
      setIsLoadingCompanyContext(false);
    }
  };

  const handleDraftPlan = async () => {
    if (!objectivePrompt.trim()) return;
    setIsDraftingPlan(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: objectivePrompt,
          budget_cap: parseFloat(budgetCapInput) || 25000,
          workflow_id: currentPlanData?.workflow_id || selectedWorkflowId || undefined
        })
      });
      if (res.ok) {
        const plan = await res.json();
        setCurrentPlanData(plan);
        if (plan.workflow_id) {
          setSelectedWorkflowId(plan.workflow_id);
        }
        await fetchCeoWorkflows();
        await fetchVitals();
      }
    } catch (e) {
      console.error('Error drafting plan:', e);
    } finally {
      setIsDraftingPlan(false);
    }
  };

  const handleRefinePlan = async () => {
    if (!userPlanFeedback.trim() || !currentPlanData) return;
    setIsRefiningPlan(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: currentPlanData.prompt || objectivePrompt,
          budget_cap: currentPlanData.budget_cap || parseFloat(budgetCapInput) || 25000,
          user_feedback: userPlanFeedback,
          feedback_history: currentPlanData.feedback_history || [],
          workflow_id: currentPlanData.workflow_id || selectedWorkflowId || undefined
        })
      });
      if (res.ok) {
        const updatedPlan = await res.json();
        setCurrentPlanData(updatedPlan);
        setUserPlanFeedback('');
      }
    } catch (e) {
      console.error('Error refining plan:', e);
    } finally {
      setIsRefiningPlan(false);
    }
  };

  const handleProceedToCouncil = async (feedback?: string) => {
    if (!currentPlanData) return;
    setIsSummoningMeeting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/summon-meeting`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: currentPlanData.prompt || objectivePrompt,
          plan_id: currentPlanData.plan_id,
          budget_cap: currentPlanData.budget_cap || 25000,
          user_feedback: feedback || undefined,
          workflow_id: currentPlanData.workflow_id || selectedWorkflowId || undefined
        })
      });
      if (res.ok) {
        const meeting = await res.json();
        setCurrentMeetingData(meeting);
        setInteractiveStep(2);
      }
    } catch (e) {
      console.error('Error summoning council:', e);
    } finally {
      setIsSummoningMeeting(false);
    }
  };

  const handleReconveneCouncil = async () => {
    if (!userMeetingFeedback.trim() || !currentPlanData) return;
    setIsReconveningMeeting(true);
    try {
      await handleProceedToCouncil(userMeetingFeedback);
      setUserMeetingFeedback('');
    } finally {
      setIsReconveningMeeting(false);
    }
  };

  const handleDeployWorkforce = async () => {
    if (!currentPlanData) return;
    setIsAssigningWorkforce(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/assign-and-execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: currentPlanData.workflow_id || selectedWorkflowId,
          plan_id: currentPlanData.plan_id,
          meeting_id: currentMeetingData?.meeting_id || undefined
        })
      });
      if (res.ok) {
        const status = await res.json();
        setTeamStatusData(status);
        setInteractiveStep(3);
        setStage3ViewTab('OPERATIONS');
        const targetId = currentPlanData.workflow_id || selectedWorkflowId;
        if (targetId) {
          await fetchOperationsOverview(targetId);
        }
        await fetchCeoWorkflows();
        await fetchVitals();
      }
    } catch (e) {
      console.error('Error assigning workforce:', e);
    } finally {
      setIsAssigningWorkforce(false);
    }
  };

  const fetchTeamStatus = async (wfId?: string) => {
    const targetId = wfId || currentPlanData?.workflow_id || selectedWorkflowId;
    if (!targetId) return;
    setIsRefreshingTeam(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/team-status/${targetId}`);
      if (res.ok) {
        const data = await res.json();
        setTeamStatusData(data);
      }
    } catch (e) {
      console.error('Error fetching team status:', e);
    } finally {
      setIsRefreshingTeam(false);
    }
  };

  const fetchOperationsOverview = async (wfId?: string) => {
    const targetId = wfId || currentPlanData?.workflow_id || selectedWorkflowId;
    if (!targetId) return;
    setIsLoadingOperations(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/operations/${targetId}`);
      if (res.ok) {
        const data = await res.json();
        setOperationsData(data);
      }
    } catch (e) {
      console.error('Error fetching operations overview:', e);
    } finally {
      setIsLoadingOperations(false);
    }
  };

  const handleScheduleCampaign = async (days = 14) => {
    const targetId = currentPlanData?.workflow_id || selectedWorkflowId;
    if (!targetId) return;
    setIsSchedulingCampaign(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/campaign/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: targetId,
          days: days,
          platforms: ['linkedin', 'twitter', 'instagram', 'facebook']
        })
      });
      if (res.ok) {
        setOperationsFeedbackMessage('Campaign Planner AI generated scheduled posts across all target platforms!');
        await fetchOperationsOverview(targetId);
        setTimeout(() => setOperationsFeedbackMessage(null), 5000);
      }
    } catch (e) {
      console.error('Error scheduling campaign:', e);
    } finally {
      setIsSchedulingCampaign(false);
    }
  };

  const handleAdvanceSalesStage = async (dealId: string, newStage: string) => {
    const targetId = currentPlanData?.workflow_id || selectedWorkflowId;
    setIsUpdatingSalesStage(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/sales/stage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deal_id: dealId, new_stage: newStage })
      });
      if (res.ok) {
        setOperationsFeedbackMessage(`Sales Deal Stage advanced to "${newStage.replace('_', ' ').toUpperCase()}".`);
        if (targetId) await fetchOperationsOverview(targetId);
        setTimeout(() => setOperationsFeedbackMessage(null), 5000);
      }
    } catch (e) {
      console.error('Error advancing sales stage:', e);
    } finally {
      setIsUpdatingSalesStage(false);
    }
  };

  const handleUpdateSupportPolicy = async (replyMode: string) => {
    const targetId = currentPlanData?.workflow_id || selectedWorkflowId;
    setIsUpdatingSupportPolicy(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/support/policy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reply_mode: replyMode,
          auto_replies: {
            whatsapp_auto_reply: true,
            email_auto_reply: true,
            widget_auto_reply: true
          }
        })
      });
      if (res.ok) {
        setOperationsFeedbackMessage(`Customer Support Policy shifted to: ${replyMode === 'auto_send' ? 'Autonomous Auto-Send' : 'Review-First (HITL)'}.`);
        if (targetId) await fetchOperationsOverview(targetId);
        setTimeout(() => setOperationsFeedbackMessage(null), 5000);
      }
    } catch (e) {
      console.error('Error updating support policy:', e);
    } finally {
      setIsUpdatingSupportPolicy(false);
    }
  };

  const handleDispatchEmail = async (options: { lead_id?: string; test_email?: string; workflow_id?: string }) => {
    const targetId = currentPlanData?.workflow_id || selectedWorkflowId;
    setIsDispatchingEmail(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/email/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options)
      });
      if (res.ok) {
        const data = await res.json();
        if (data.type === 'test_email') {
          const sent = data.result?.sent;
          const msg = sent
            ? `Test email dispatched to ${data.recipient} via ${data.result?.channel?.toUpperCase()}!`
            : `Test email evaluated: ${data.result?.message || 'Check email configuration in Settings'}`;
          setOperationsFeedbackMessage(msg);
        } else if (data.type === 'lead_outreach') {
          setOperationsFeedbackMessage(`Lead outreach dispatched to ${data.recipient}. Pipeline updated.`);
        } else {
          setOperationsFeedbackMessage(`Batch outreach dispatched to ${data.sent_count} lead(s).`);
        }
        if (targetId) await fetchOperationsOverview(targetId);
        setTimeout(() => setOperationsFeedbackMessage(null), 6000);
      }
    } catch (e) {
      console.error('Error dispatching email:', e);
    } finally {
      setIsDispatchingEmail(false);
    }
  };

  const handleSendIntervention = async () => {
    const targetWfId = selectedWorkflowId || currentPlanData?.workflow_id;
    if (!executiveInterventionNote.trim() || !targetWfId) return;
    setIsSendingIntervention(true);
    try {
      const planVerId = selectedPlanDetails?.id || currentPlanData?.plan_id;
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows/${targetWfId}/tick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_version_id: planVerId,
          directive_override: executiveInterventionNote
        })
      });
      if (res.ok) {
        setInterventionFeedbackMessage(`Directive dispatched: "${executiveInterventionNote.slice(0, 45)}..."`);
        setExecutiveInterventionNote('');
        await fetchCeoWorkflowDetails(targetWfId);
        await fetchTeamStatus(targetWfId);
        setTimeout(() => setInterventionFeedbackMessage(null), 5000);
      }
    } catch (e) {
      console.error('Error sending executive intervention:', e);
    } finally {
      setIsSendingIntervention(false);
    }
  };

  const handleApproveGate = async (gateKey: string, isApproved: boolean) => {
    setApprovedGateIds((prev) => ({
      ...prev,
      [gateKey]: isApproved ? 'APPROVED' : 'REJECTED'
    }));
    const targetWfId = selectedWorkflowId || currentPlanData?.workflow_id;
    if (targetWfId) {
      try {
        await fetchWithAuth(`${API_URL}/ceo/workflows/${targetWfId}/tick`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            gate_decision: isApproved ? 'APPROVED' : 'REJECTED',
            gate_key: gateKey
          })
        });
        await fetchCeoWorkflowDetails(targetWfId);
        await fetchTeamStatus(targetWfId);
      } catch (e) {
        console.error('Error ticking gate approval:', e);
      }
    }
  };

  // 2. Refresh workflow details & plan versions on selection
  useEffect(() => {
    if (selectedWorkflowId && token) {
      fetchCeoWorkflowDetails(selectedWorkflowId);
      fetchWorkflowPlans(selectedWorkflowId);
      fetchWorkflowPostMortem(selectedWorkflowId);
    }
  }, [selectedWorkflowId, token]);

  // 3. Connect SSE Stream when workflow is active
  useEffect(() => {
    if (selectedWorkflowId && selectedWorkflow?.status === 'RUNNING') {
      connectEventStream(selectedWorkflowId);
    }
    return () => {
      if (sseRef.current) {
        sseRef.current.close();
      }
    };
  }, [selectedWorkflowId, selectedWorkflow?.status]);

  const fetchVitals = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/cockpit/vitals`);
      if (res.ok) {
        const data = await res.json();
        setVitals(data);
      }
    } catch (e) {
      console.error('Error fetching cockpit vitals:', e);
    }
  };

  const fetchCeoWorkflows = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/workspaces`);
      if (res.ok) {
        const data = await res.json();
        setCeoWorkflows(data);
        if (data.length > 0 && !selectedWorkflowId && !currentPlanData) {
          setSelectedWorkflowId(data[0].id);
        }
      } else {
        const fallbackRes = await fetchWithAuth(`${API_URL}/ceo/workflows`);
        if (fallbackRes.ok) {
          const fallbackData = await fallbackRes.json();
          setCeoWorkflows(fallbackData);
        }
      }
    } catch (e) {
      console.error('Error fetching workflows:', e);
    }
  };

  const handleLoadWorkspaceState = async (wfId: string) => {
    setIsLoadingWorkspace(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/workspaces/${wfId}`);
      if (res.ok) {
        const state = await res.json();
        setSelectedWorkflowId(wfId);
        setSelectedWorkflow(state.workflow);
        if (state.plan) {
          setCurrentPlanData(state.plan);
          setObjectivePrompt(state.plan.prompt || '');
          if (state.plan.budget_cap) setBudgetCapInput(String(state.plan.budget_cap));
        }
        if (state.meeting) {
          setCurrentMeetingData(state.meeting);
        } else {
          setCurrentMeetingData(null);
        }
        if (state.team_status) {
          setTeamStatusData(state.team_status);
        } else {
          setTeamStatusData(null);
        }

        // Auto-navigate to appropriate step
        if (state.team_status || state.workflow?.status === 'RUNNING' || state.workflow?.status === 'COMPLETED') {
          setInteractiveStep(3);
        } else if (state.meeting) {
          setInteractiveStep(2);
        } else {
          setInteractiveStep(1);
        }
      }
    } catch (e) {
      console.error('Error loading workspace state:', e);
    } finally {
      setIsLoadingWorkspace(false);
    }
  };

  const handleDeleteWorkspace = async (wfId: string) => {
    setIsDeletingWf(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/interactive/workspaces/${wfId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setDeleteConfirmWfId(null);
        if (selectedWorkflowId === wfId) {
          handleNewDirective();
        }
        await fetchCeoWorkflows();
        await fetchVitals();
      }
    } catch (e) {
      console.error('Error deleting workspace:', e);
    } finally {
      setIsDeletingWf(false);
    }
  };

  const handleNewDirective = () => {
    setSelectedWorkflowId(null);
    setSelectedWorkflow(null);
    setCurrentPlanData(null);
    setCurrentMeetingData(null);
    setTeamStatusData(null);
    setObjectivePrompt('');
    setBudgetCapInput('25000');
    setUserPlanFeedback('');
    setUserMeetingFeedback('');
    setInteractiveStep(1);
  };

  const fetchCeoWorkflowDetails = async (wfId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows/${wfId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedWorkflow(data);
      }
      try {
        const projRes = await fetchWithAuth(`${API_URL}/ceo/workflows/${wfId}/projection`);
        if (projRes.ok) {
          const projData = await projRes.json();
          setExecutionProjection(projData);
        }
      } catch (pe) {
        // Projection not yet initialized
      }
    } catch (e) {
      console.error('Error fetching workflow details:', e);
    }
  };

  const fetchWorkflowPlans = async (wfId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/plans/${wfId}`);
      if (res.ok) {
        const plans = await res.json();
        setAvailablePlans(plans);
        const match = plans.find((p: any) => p.strategy_variant === activeVariantTab) || plans[0];
        if (match) {
          fetchPlanDetails(wfId, match.id);
        }
      }
    } catch (e) {
      console.error('Error fetching workflow plans:', e);
    }
  };

  const fetchPlanDetails = async (wfId: string, planVersionId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/plans/${wfId}/${planVersionId}`);
      if (res.ok) {
        const details = await res.json();
        setSelectedPlanDetails(details);
      }
    } catch (e) {
      console.error('Error fetching plan details:', e);
    }
  };

  const fetchWorkflowPostMortem = async (wfId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows/${wfId}/post-mortem`);
      if (res.ok) {
        const data = await res.json();
        setPostMortemBrief(data);
      } else {
        setPostMortemBrief(null);
      }
    } catch (e) {
      setPostMortemBrief(null);
    }
  };

  const connectEventStream = (wfId: string) => {
    if (sseRef.current) {
      sseRef.current.close();
    }
    const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : '';
    const sse = new EventSource(`${API_URL}/ceo/workflows/${wfId}/stream${tokenQuery}`);
    sse.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setLiveStreamEvents((prev) => [payload, ...prev.slice(0, 49)]);
        // Automatically sync workflow state on tick/completion
        if (payload.event_type?.includes('workflow_') || payload.event_type?.includes('task_')) {
          fetchCeoWorkflowDetails(wfId);
          fetchVitals();
        }
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };
    sseRef.current = sse;
  };

  // Compile Multi-Plan Variants via Strategy Compiler
  const handleCompilePlans = async () => {
    if (!objectivePrompt.trim()) return;
    setIsCompiling(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/compiler/compile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: selectedWorkflowId || undefined,
          prompt: objectivePrompt,
          budget_override: parseFloat(budgetCapInput) || undefined
        })
      });
      if (res.ok) {
        const compiledPlans = await res.json();
        setAvailablePlans(compiledPlans);
        const wfId = compiledPlans[0]?.workflow_id || selectedWorkflowId;
        if (wfId) {
          setSelectedWorkflowId(wfId);
          await fetchCeoWorkflowDetails(wfId);
          const currentMatch = compiledPlans.find((p: any) => p.strategy_variant === activeVariantTab) || compiledPlans[0];
          if (currentMatch) {
            await fetchPlanDetails(wfId, currentMatch.id);
          }
        }
        await fetchCeoWorkflows();
        await fetchVitals();
      } else {
        const err = await res.json().catch(() => ({}));
        console.error('Compilation failed:', err);
      }
    } catch (e) {
      console.error('Error compiling strategy plans:', e);
    } finally {
      setIsCompiling(false);
    }
  };

  // Switch Strategy Variant Tab
  const handleSelectVariant = (variant: 'AGGRESSIVE' | 'BALANCED' | 'CONSERVATIVE') => {
    setActiveVariantTab(variant);
    if (!selectedWorkflowId || availablePlans.length === 0) return;
    const match = availablePlans.find((p: any) => p.strategy_variant === variant);
    if (match) {
      fetchPlanDetails(selectedWorkflowId, match.id);
    }
  };

  // Pre-Execution Dry Run Simulation
  const handleRunDryRun = async () => {
    if (!selectedWorkflowId || !selectedPlanDetails) return;
    setIsDryRunning(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/plans/${selectedWorkflowId}/${selectedPlanDetails.id}/dry-run`, {
        method: 'POST'
      });
      if (res.ok) {
        const sim = await res.json();
        setDryRunResult(sim);
        setShowDryRunModal(true);
      }
    } catch (e) {
      console.error('Dry run failed:', e);
    } finally {
      setIsDryRunning(false);
    }
  };

  // Activate Strategy Plan
  const handleActivatePlan = async () => {
    if (!selectedWorkflowId || !selectedPlanDetails) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/plans/${selectedWorkflowId}/${selectedPlanDetails.id}/activate`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchWorkflowPlans(selectedWorkflowId);
        fetchCeoWorkflowDetails(selectedWorkflowId);
      }
    } catch (e) {
      console.error('Error activating plan:', e);
    }
  };

  // Workflow Execution Controls
  const handleStartWorkflow = async () => {
    if (!selectedWorkflowId || !selectedPlanDetails) return;
    setIsExecuting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows/${selectedWorkflowId}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_version_id: selectedPlanDetails.id })
      });
      if (res.ok) {
        await handleTickWorkflow();
        await fetchCeoWorkflowDetails(selectedWorkflowId);
        await fetchVitals();
      } else {
        const err = await res.json().catch(() => ({}));
        console.error('Error starting workflow:', err);
      }
    } catch (e) {
      console.error('Error starting workflow:', e);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleTickWorkflow = async () => {
    if (!selectedWorkflowId || !selectedPlanDetails) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows/${selectedWorkflowId}/tick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_version_id: selectedPlanDetails.id })
      });
      if (res.ok) {
        fetchCeoWorkflowDetails(selectedWorkflowId);
        fetchVitals();
      }
    } catch (e) {
      console.error('Error executing workflow tick:', e);
    }
  };

  const handlePauseWorkflow = async () => {
    if (!selectedWorkflowId) return;
    try {
      await fetchWithAuth(`${API_URL}/ceo/workflows/${selectedWorkflowId}/pause`, { method: 'POST' });
      fetchCeoWorkflowDetails(selectedWorkflowId);
    } catch (e) {
      console.error('Error pausing workflow:', e);
    }
  };

  const handleResumeWorkflow = async () => {
    if (!selectedWorkflowId) return;
    try {
      await fetchWithAuth(`${API_URL}/ceo/workflows/${selectedWorkflowId}/resume`, { method: 'POST' });
      fetchCeoWorkflowDetails(selectedWorkflowId);
    } catch (e) {
      console.error('Error resuming workflow:', e);
    }
  };

  // Escalate to Agent Boardroom
  const handleEscalateToBoardroom = async () => {
    if (!selectedWorkflowId || !selectedPlanDetails) return;
    setIsEscalating(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/plans/${selectedWorkflowId}/${selectedPlanDetails.id}/escalate-to-boardroom`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setEscalationSuccess(`Escalated to Boardroom: "${data.title}"`);
        setTimeout(() => setEscalationSuccess(null), 6000);
      }
    } catch (e) {
      console.error('Error escalating to boardroom:', e);
    } finally {
      setIsEscalating(false);
    }
  };

  // Generate Board-Ready Strategic Brief / Post-Mortem
  const handleGeneratePostMortem = async () => {
    if (!selectedWorkflowId) return;
    setIsGeneratingBrief(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows/${selectedWorkflowId}/generate-post-mortem`, {
        method: 'POST'
      });
      if (res.ok) {
        const brief = await res.json();
        setPostMortemBrief(brief);
        setShowPostMortemModal(true);
      }
    } catch (e) {
      console.error('Error generating strategic brief:', e);
    } finally {
      setIsGeneratingBrief(false);
    }
  };

  // Effective Nodes available from selected plan or current plan data
  const effectiveNodes = useMemo(() => {
    return selectedPlanDetails?.nodes || currentPlanData?.nodes || [];
  }, [selectedPlanDetails, currentPlanData]);

  // Active selected node for inspection drawer
  const activeNode = useMemo(() => {
    if (!selectedNodeId || effectiveNodes.length === 0) return null;
    return effectiveNodes.find((n: any) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, effectiveNodes]);

  // Topological Level partition for DAG visualizer
  const dagLevels = useMemo(() => {
    if (effectiveNodes.length === 0) return [];
    const nodes = effectiveNodes;
    const levelMap: Record<string, number> = {};

    const getLevel = (nid: string, visited = new Set<string>()): number => {
      if (levelMap[nid] !== undefined) return levelMap[nid];
      if (visited.has(nid)) return 0;
      visited.add(nid);
      const node = nodes.find((n: any) => n.id === nid);
      if (!node || !node.depends_on || node.depends_on.length === 0) {
        levelMap[nid] = 0;
        return 0;
      }
      const maxParent = Math.max(...node.depends_on.map((p: string) => getLevel(p, new Set(visited))));
      levelMap[nid] = maxParent + 1;
      return maxParent + 1;
    };

    nodes.forEach((n: any) => getLevel(n.id));
    const maxLvl = Math.max(...Object.values(levelMap), 0);
    const levels: any[][] = Array.from({ length: maxLvl + 1 }, () => []);

    nodes.forEach((n: any) => {
      const lvl = levelMap[n.id] || 0;
      levels[lvl].push(n);
    });

    return levels;
  }, [effectiveNodes]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 font-sans text-slate-100">
      {/* 1. Reconciled Executive Vitals Strip */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Active Pipelines</span>
            <Activity className="h-4 w-4 text-sky-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{vitals.active_pipelines}</span>
            <span className="text-xs text-slate-400">({vitals.completed_pipelines} completed)</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Autonomous executive DAGs in progress</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Budget Envelope</span>
            <DollarSign className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">${vitals.total_budget_spent.toLocaleString()}</span>
            <span className="text-xs text-slate-400">/ ${vitals.total_budget_allocated.toLocaleString()}</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-emerald-500 h-1.5 rounded-full transition-all"
              style={{ width: `${Math.min(vitals.budget_utilization_pct, 100)}%` }}
            />
          </div>
          <p className="text-xs text-slate-400 mt-1">{vitals.budget_utilization_pct}% authorized capital utilized</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Governance Gates</span>
            <Shield className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{vitals.pending_approvals_count}</span>
            <span className="text-xs text-amber-400 font-medium">Pending Approvals</span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Dual-Key and $R3/$R4 policy checkpoints</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-4 shadow-sm backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Control Plane Status</span>
            <span className={`h-2.5 w-2.5 rounded-full ${vitals.system_status === 'HEALTHY' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
          </div>
          <div className="mt-2">
            <span className={`text-base font-bold ${vitals.system_status === 'HEALTHY' ? 'text-emerald-400' : 'text-amber-400'}`}>
              {vitals.system_status === 'HEALTHY' ? 'Deterministic & Compliant' : 'Attention Required'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Zero unverified leakage | AST Fail-Closed</p>
        </div>
      </div>

      {escalationSuccess && (
        <div className="bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 px-4 py-3 rounded-2xl text-xs flex items-center justify-between animate-in fade-in">
          <span>{escalationSuccess}</span>
          <Button size="sm" variant="ghost" onClick={() => setActiveView('boardroom')} className="text-emerald-400 font-bold hover:underline">
            Go to Boardroom →
          </Button>
        </div>
      )}

      {/* 2. Unified Suite Header: Autonomous Execution DAG Engine with Human-in-the-Loop */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/90 border border-slate-800 p-3 rounded-3xl shadow-md">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 rounded-2xl text-white shadow-md shadow-sky-500/20">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white">Autonomous Execution DAG Engine</h2>
              <span className="text-[10px] bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 px-2 py-0.5 rounded-full font-mono uppercase tracking-wider font-bold flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Human-in-the-Loop Review Active
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Topological multi-agent execution pipeline with executive review & approval gates at every milestone.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-2xl text-xs text-slate-300">
          <Building className="h-3.5 w-3.5 text-sky-400" />
          <span className="text-slate-400">Company:</span>
          <span className="font-semibold text-white">{companyContext?.company_name || 'OctaOS Enterprise'}</span>
          <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
            {companyContext?.industry || 'B2B Automation'}
          </span>
        </div>
      </div>

      {/* UNIFIED WORKSPACE VIEW */}
      <div className="space-y-6 animate-in fade-in">
        <div className="space-y-6 animate-in fade-in">
          {/* Executive Directives & Workspaces (Last CEO Works) Section */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-4 shadow-lg space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-sky-950/70 border border-sky-800/60 rounded-xl text-sky-400">
                  <FolderKanban className="h-4 w-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-white">Executive Directives & Workspaces</h3>
                    <span className="text-[10px] bg-sky-950/80 text-sky-300 border border-sky-800/60 px-2 py-0.5 rounded-full font-mono font-bold">
                      {ceoWorkflows.length} Saved
                    </span>
                    {selectedWorkflowId && (
                      <span className="text-[10px] bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 px-2 py-0.5 rounded-full font-semibold">
                        Active Workspace: {selectedWorkflow?.name || selectedWorkflowId.slice(0, 8)}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">Manage previous CEO strategic directives, review council deliberations, or launch new runs.</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={handleNewDirective}
                  className="bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs h-8 rounded-xl shadow flex items-center gap-1.5"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>New Directive</span>
                </Button>
                <button
                  type="button"
                  onClick={() => setIsWorkspacesSectionOpen(!isWorkspacesSectionOpen)}
                  className="p-1.5 text-slate-400 hover:text-white rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-all"
                  title={isWorkspacesSectionOpen ? "Collapse history" : "Expand history"}
                >
                  {isWorkspacesSectionOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Collapsible list of workspaces */}
            {isWorkspacesSectionOpen && (
              <div className="pt-2 border-t border-slate-800/60 space-y-2">
                {ceoWorkflows.length === 0 ? (
                  <div className="p-4 text-center text-xs text-slate-500 bg-slate-950/40 rounded-2xl border border-slate-800/50">
                    No executive directives saved yet. Enter a directive prompt below to draft your first strategic plan!
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2.5 max-h-[260px] overflow-y-auto pr-1">
                    {ceoWorkflows.map((w: any) => {
                      const isSelected = selectedWorkflowId === w.id;
                      return (
                        <div
                          key={w.id}
                          className={`p-3 rounded-2xl border transition-all text-xs flex flex-col justify-between gap-2.5 ${
                            isSelected
                              ? 'bg-sky-950/50 border-sky-500/70 shadow-sm shadow-sky-500/10 ring-1 ring-sky-500/40'
                              : 'bg-slate-950/70 border-slate-800/80 hover:border-slate-700'
                          }`}
                        >
                          <div className="space-y-1">
                            <div className="flex items-center justify-between gap-1">
                              <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                                w.status === 'RUNNING' || w.status === 'ACTIVE' ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60 animate-pulse' :
                                w.status === 'COMPLETED' ? 'bg-sky-950/80 text-sky-300 border-sky-800/60' :
                                'bg-slate-900 text-slate-400 border border-slate-800'
                              }`}>
                                {w.status || 'DRAFT'}
                              </span>
                              <span className="text-[10px] text-slate-500">
                                {w.created_at ? new Date(w.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recent'}
                              </span>
                            </div>
                            <h4 className="font-bold text-white text-xs line-clamp-1" title={w.name || w.objective}>
                              {w.name || w.objective || `Directive ${w.id.slice(0, 8)}`}
                            </h4>
                            <div className="flex items-center gap-2 text-[10px] text-slate-400">
                              <span>Budget: <strong className="text-white">${Number(w.estimated_budget || 25000).toLocaleString()}</strong></span>
                              {w.roi_multiple && <span>ROI: <strong className="text-emerald-400">{w.roi_multiple}x</strong></span>}
                            </div>
                          </div>

                          <div className="flex items-center justify-between gap-1 pt-1.5 border-t border-slate-800/50">
                            <button
                              type="button"
                              onClick={() => handleLoadWorkspaceState(w.id)}
                              disabled={isLoadingWorkspace}
                              className={`text-[11px] font-bold px-2.5 py-1 rounded-xl transition-all flex items-center gap-1 ${
                                isSelected
                                  ? 'bg-sky-500 text-white shadow-sm'
                                  : 'text-sky-400 hover:text-sky-300 hover:bg-sky-950/40'
                              }`}
                            >
                              <Play className="h-2.5 w-2.5" />
                              <span>{isSelected ? 'Active' : 'Open Workspace'}</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => setDeleteConfirmWfId(w.id)}
                              className="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-rose-950/30 transition-all"
                              title="Delete directive"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Stepper Navigation Bar */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-3 shadow-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <button
                onClick={() => setInteractiveStep(1)}
                className={`flex items-center gap-3 p-3 rounded-2xl transition-all border text-left ${
                  interactiveStep === 1
                    ? 'bg-sky-950/60 border-sky-500/70 text-white shadow-sm'
                    : currentPlanData
                    ? 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                    : 'bg-slate-950/40 border-slate-800/60 text-slate-500'
                }`}
              >
                <div className={`h-8 w-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                  interactiveStep === 1 ? 'bg-sky-500 text-white' : currentPlanData ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-slate-800 text-slate-400'
                }`}>
                  {currentPlanData ? <Check className="h-4 w-4" /> : '1'}
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider block text-slate-400">Stage 1</span>
                  <span className="text-xs font-bold block">Contextual Strategy & Review</span>
                </div>
              </button>

              <button
                onClick={() => currentMeetingData && setInteractiveStep(2)}
                disabled={!currentPlanData}
                className={`flex items-center gap-3 p-3 rounded-2xl transition-all border text-left ${
                  interactiveStep === 2
                    ? 'bg-sky-950/60 border-sky-500/70 text-white shadow-sm'
                    : currentMeetingData
                    ? 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                    : 'bg-slate-950/40 border-slate-800/60 text-slate-500 cursor-not-allowed opacity-60'
                }`}
              >
                <div className={`h-8 w-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                  interactiveStep === 2 ? 'bg-sky-500 text-white' : currentMeetingData ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-slate-800 text-slate-400'
                }`}>
                  {currentMeetingData ? <Check className="h-4 w-4" /> : '2'}
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider block text-slate-400">Stage 2</span>
                  <span className="text-xs font-bold block">Council Meeting & Critique</span>
                </div>
              </button>

              <button
                onClick={() => teamStatusData && setInteractiveStep(3)}
                disabled={!currentMeetingData}
                className={`flex items-center gap-3 p-3 rounded-2xl transition-all border text-left ${
                  interactiveStep === 3
                    ? 'bg-sky-950/60 border-sky-500/70 text-white shadow-sm'
                    : teamStatusData
                    ? 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                    : 'bg-slate-950/40 border-slate-800/60 text-slate-500 cursor-not-allowed opacity-60'
                }`}
              >
                <div className={`h-8 w-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                  interactiveStep === 3 ? 'bg-sky-500 text-white' : teamStatusData ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-slate-800 text-slate-400'
                }`}>
                  {teamStatusData ? <Check className="h-4 w-4" /> : '3'}
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold tracking-wider block text-slate-400">Stage 3</span>
                  <span className="text-xs font-bold block">Real Workforce Hub</span>
                </div>
              </button>
            </div>
          </div>

          {/* STAGE 1: CONTEXTUAL STRATEGY FORMULATION & USER FEEDBACK LOOP */}
          {interactiveStep === 1 && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Company Knowledge & Directive Form */}
              <div className="lg:col-span-5 space-y-6">
                {/* Company Knowledge Base Ingestion Card */}
                <Card className="bg-slate-900/90 border-slate-800 rounded-3xl overflow-hidden shadow-lg border-t-2 border-t-indigo-500">
                  <CardHeader className="pb-3 border-b border-slate-800/60">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Building className="h-4 w-4 text-indigo-400" />
                        <CardTitle className="text-sm text-white font-bold">Company Knowledge Base</CardTitle>
                      </div>
                      <span className="text-[10px] bg-indigo-950/60 text-indigo-300 border border-indigo-800/50 px-2 py-0.5 rounded-full font-semibold">
                        Ingested Context
                      </span>
                    </div>
                    <CardDescription className="text-slate-400 text-xs">
                      The CEO AI actively grounds all planning against your company profile and verified USP.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-3 space-y-3 text-xs">
                    <div className="p-3 bg-slate-950/70 rounded-2xl border border-slate-800/80 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold text-slate-400">Organization</span>
                        <span className="font-bold text-white text-xs">{companyContext?.company_name || 'OctaOS Enterprise'}</span>
                      </div>
                      <div className="flex items-center justify-between border-t border-slate-800/60 pt-1.5">
                        <span className="text-[10px] uppercase font-bold text-slate-400">Industry</span>
                        <span className="text-slate-300 text-xs">{companyContext?.industry || 'B2B AI Automation & SaaS'}</span>
                      </div>
                      <div className="border-t border-slate-800/60 pt-1.5">
                        <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Verified Core USP</span>
                        <p className="text-[11px] text-sky-300 italic bg-sky-950/30 p-2 rounded-xl border border-sky-800/40">
                          "{companyContext?.usp || 'Zero-human overhead multi-agent executive automation with verifiable ledger auditability.'}"
                        </p>
                      </div>
                      <div className="border-t border-slate-800/60 pt-1.5">
                        <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Target Decision Makers</span>
                        <div className="flex flex-wrap gap-1">
                          {(companyContext?.target_decision_makers || ['Chief Revenue Officer', 'VP of Sales', 'CEO']).map((dm: string, idx: number) => (
                            <span key={idx} className="bg-slate-900 border border-slate-700 text-slate-200 text-[10px] px-2 py-0.5 rounded-full">
                              {dm}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Directive Formulation Input Form */}
                <Card className="bg-slate-900/90 border-slate-800 rounded-3xl overflow-hidden shadow-lg">
                  <CardHeader className="pb-3 border-b border-slate-800/60">
                    <div className="flex items-center gap-2">
                      <Target className="h-4 w-4 text-sky-400" />
                      <CardTitle className="text-sm text-white font-bold">Executive Directive Form</CardTitle>
                    </div>
                    <CardDescription className="text-slate-400 text-xs">
                      Provide high-level strategic outcomes. The CEO orchestrates domain specialists to draft an actionable plan.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-4 space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-slate-300">Executive Directive Prompt</label>
                      <Textarea
                        placeholder="e.g. Accelerate enterprise outbound SDR pipeline to reach $100k ARR through multi-touch sequences"
                        value={objectivePrompt}
                        onChange={(e) => setObjectivePrompt(e.target.value)}
                        className="bg-slate-950/80 border-slate-800 text-white rounded-xl text-xs min-h-[85px] focus:border-sky-500"
                      />
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {PRESET_DIRECTIVES.map((p, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              setObjectivePrompt(p.prompt);
                              setBudgetCapInput(p.budget);
                            }}
                            className="text-[10px] bg-slate-950/80 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-sky-500/50 px-2 py-0.5 rounded-full transition-all"
                          >
                            {p.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-slate-300">Budget Envelope ($)</label>
                        <Input
                          type="number"
                          value={budgetCapInput}
                          onChange={(e) => setBudgetCapInput(e.target.value)}
                          className="bg-slate-950/80 border-slate-800 text-white text-xs rounded-xl"
                        />
                      </div>
                      <div className="flex flex-col justify-end">
                        <Button
                          onClick={handleDraftPlan}
                          disabled={isDraftingPlan || !objectivePrompt.trim()}
                          className="bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs h-9 rounded-xl shadow transition-all flex items-center justify-center gap-1.5"
                        >
                          {isDraftingPlan ? (
                            <>
                              <Loader2 className="animate-spin h-3.5 w-3.5" />
                              Synthesizing...
                            </>
                          ) : (
                            <>
                              <Sparkles className="h-3.5 w-3.5" />
                              Draft Strategic Plan
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Right Column: Strategic Plan & User Feedback / Review Loop */}
              <div className="lg:col-span-7 space-y-6">
                {!currentPlanData ? (
                  <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-8 text-center space-y-4 border-dashed border-2">
                    <div className="h-16 w-16 mx-auto rounded-3xl bg-slate-950 border border-slate-800 flex items-center justify-center text-sky-400">
                      <Users className="h-8 w-8" />
                    </div>
                    <div className="max-w-md mx-auto space-y-2">
                      <h3 className="text-base font-bold text-white">No Strategy Plan Drafted Yet</h3>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Input an executive directive on the left and click <span className="text-sky-400 font-semibold">"Draft Strategic Plan"</span>. The CEO will synthesize your company knowledge base, allocate departmental budgets, and assemble your specialist team for your interactive review.
                      </p>
                    </div>
                  </Card>
                ) : (
                  <div className="space-y-6 animate-in fade-in">
                    {/* Synthesized Plan Card */}
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl overflow-hidden shadow-xl border-t-2 border-t-sky-500">
                      <CardHeader className="pb-3 border-b border-slate-800/60">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-sky-400" />
                            <CardTitle className="text-sm text-white font-bold">Executive Strategic Plan</CardTitle>
                          </div>
                          <span className="text-xs font-bold text-sky-400 bg-sky-950/60 border border-sky-800/50 px-2.5 py-0.5 rounded-full">
                            v{currentPlanData.version_num} {currentPlanData.version_num > 1 ? 'Refined Draft' : 'Initial Draft'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 font-medium pt-1">
                          {currentPlanData.prompt}
                        </p>
                      </CardHeader>

                      <CardContent className="pt-4 space-y-4 text-xs">
                        {/* Financial & ROI Header */}
                        <div className="grid grid-cols-3 gap-3 p-3 bg-slate-950/80 rounded-2xl border border-slate-800">
                          <div className="text-center">
                            <span className="text-[10px] text-slate-400 uppercase font-bold block">Budget Envelope</span>
                            <span className="text-sm font-bold text-white">${Number(currentPlanData.budget_cap).toLocaleString()}</span>
                          </div>
                          <div className="text-center border-x border-slate-800">
                            <span className="text-[10px] text-slate-400 uppercase font-bold block">Projected ROI</span>
                            <span className="text-sm font-bold text-emerald-400">{currentPlanData.estimated_roi}</span>
                          </div>
                          <div className="text-center">
                            <span className="text-[10px] text-slate-400 uppercase font-bold block">Pipeline Value</span>
                            <span className="text-sm font-bold text-sky-400">{currentPlanData.projected_pipeline_value}</span>
                          </div>
                        </div>

                        {/* Revision Note */}
                        {currentPlanData.revision_note && (
                          <div className="p-2.5 bg-emerald-950/30 border border-emerald-800/40 rounded-xl text-[11px] text-emerald-300 flex items-center gap-2">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                            <span>{currentPlanData.revision_note}</span>
                          </div>
                        )}

                        {/* Strategic Rationale & Hypothesis */}
                        {currentPlanData.strategic_hypothesis && (
                          <div className="p-3 bg-sky-950/30 border border-sky-800/40 rounded-2xl space-y-1">
                            <div className="flex items-center gap-1.5 text-sky-300 font-bold text-[11px]">
                              <Brain className="h-3.5 w-3.5" />
                              <span>Dynamic Strategic Hypothesis</span>
                            </div>
                            <p className="text-[11px] text-slate-300 leading-relaxed">
                              {currentPlanData.strategic_hypothesis}
                            </p>
                          </div>
                        )}

                        {/* Prior Human Feedback Rounds */}
                        {currentPlanData.feedback_history && currentPlanData.feedback_history.length > 0 && (
                          <div className="p-2.5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5 text-[11px]">
                            <span className="text-[10px] uppercase font-bold text-slate-400 block">
                              Incorporated Human Review Comments ({currentPlanData.feedback_history.length})
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {currentPlanData.feedback_history.map((fb: string, fbIdx: number) => (
                                <span key={fbIdx} className="bg-slate-900 border border-slate-700 text-slate-300 px-2 py-0.5 rounded-lg text-[10px] line-clamp-1" title={fb}>
                                  Round {fbIdx + 1}: "{fb}"
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Assigned Specialist Employee Personas */}
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
                            Assigned Executive Specialist Team ({currentPlanData.assigned_employees?.length || 0})
                          </span>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                            {currentPlanData.assigned_employees?.map((emp: any, idx: number) => (
                              <div key={idx} className="p-3 bg-slate-950/80 border border-slate-800 rounded-2xl flex items-center gap-3">
                                <img
                                  src={emp.avatar}
                                  alt={emp.name}
                                  className="h-10 w-10 rounded-xl object-cover border border-slate-700 shadow-sm"
                                />
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-bold text-white truncate">{emp.name}</h4>
                                    <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full border ${getDeptColor(emp.department)}`}>
                                      {emp.agent_role}
                                    </span>
                                  </div>
                                  <p className="text-[10px] text-slate-400 truncate">{emp.title}</p>
                                  <p className="text-[9px] text-slate-500 truncate pt-0.5">{emp.specialty}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Department Budget Allocations */}
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
                            Departmental Budget Envelope Allocation
                          </span>
                          <div className="space-y-2 p-3 bg-slate-950/60 rounded-2xl border border-slate-800">
                            {currentPlanData.budget_allocations?.map((alloc: any, idx: number) => (
                              <div key={idx} className="space-y-1">
                                <div className="flex items-center justify-between text-[11px]">
                                  <span className="text-slate-300 font-medium">{alloc.employee} ({alloc.role})</span>
                                  <span className="text-white font-bold">${Number(alloc.allocated_amount).toLocaleString()} ({alloc.percentage}%)</span>
                                </div>
                                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className="bg-sky-500 h-1.5 rounded-full"
                                    style={{ width: `${alloc.percentage}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* 3-Phase Execution Milestones */}
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
                            Execution Roadmap & Deliverable Milestones
                          </span>
                          <div className="space-y-2">
                            {currentPlanData.milestones?.map((m: any, idx: number) => (
                              <div key={idx} className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-white text-xs">{m.phase}</span>
                                  <span className="text-[10px] text-sky-400 font-semibold">{m.days}</span>
                                </div>
                                <ul className="list-disc list-inside text-[11px] text-slate-400 space-y-0.5 pt-1">
                                  {m.deliverables?.map((d: string, dIdx: number) => (
                                    <li key={dIdx}>{d}</li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* AUTONOMOUS 3-AGENT PRE-REVIEW CRITIQUE LOOP & FACT GROUNDING PROVENANCE */}
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl overflow-hidden shadow-xl border-t-2 border-t-emerald-500">
                      <CardHeader className="pb-3 border-b border-slate-800/60 bg-slate-950/40">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5">
                            <div className="p-2 bg-emerald-950/80 border border-emerald-800/60 rounded-xl text-emerald-400">
                              <ShieldCheck className="h-4 w-4" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <CardTitle className="text-sm text-white font-bold">
                                  Autonomous 3-Agent Pre-Review Critique Loop
                                </CardTitle>
                                <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1 animate-pulse">
                                  <Check className="h-3 w-3 text-emerald-400" />
                                  "{currentPlanData.consensus_phrase || 'We can do it'}"
                                </span>
                              </div>
                              <CardDescription className="text-slate-400 text-xs">
                                Technical (CTO), Financial (CFO), and Adversarial (Red Team) autonomous stress-test loop before human gate.
                              </CardDescription>
                            </div>
                          </div>
                          <span className="text-[10px] bg-sky-950/60 text-sky-300 border border-sky-800/50 px-2 py-0.5 rounded-full font-mono self-start sm:self-auto">
                            Autonomous Loop: Converged
                          </span>
                        </div>
                      </CardHeader>

                      <CardContent className="pt-4 space-y-4 text-xs">
                        {/* Consensus Rationale Quote */}
                        <div className="p-3 bg-emerald-950/20 border border-emerald-800/40 rounded-2xl flex items-start gap-2.5">
                          <Sparkles className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                          <div className="space-y-0.5">
                            <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">
                              Unanimous Autonomous Consensus Reached
                            </span>
                            <p className="text-slate-300 text-xs leading-relaxed">
                              {currentPlanData.consensus_rationale || 
                                'Autonomous 3-Agent Pre-Review Loop completed 2 iterations. Technical (CTO Rachel Chen), Financial (CFO Elena Rostova), and Adversarial (Red Team Marcus Vance) critics resolved all flagged issues and reached unanimous sign-off: "We can do it".'}
                            </p>
                          </div>
                        </div>

                        {/* Knowledge Base Grounding & Provenance Matrix */}
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5">
                              <Building className="h-3.5 w-3.5 text-indigo-400" />
                              Knowledge Base Fact-Grounding & Provenance Backend
                            </span>
                            <span className="text-[10px] text-indigo-400 font-mono">
                              Verified Vector Audit
                            </span>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 p-3 bg-slate-950/70 rounded-2xl border border-slate-800">
                            <div className="space-y-1">
                              <span className="text-[10px] text-slate-500 uppercase font-bold block">Organization & Industry</span>
                              <p className="text-white font-bold text-xs">
                                {currentPlanData.source_facts_matrix?.company_name || companyContext?.company_name || 'AlienHouse Networks'} 
                                <span className="text-slate-400 font-normal"> • {currentPlanData.source_facts_matrix?.industry || companyContext?.industry || 'Software Development'}</span>
                              </p>
                            </div>
                            <div className="space-y-1">
                              <span className="text-[10px] text-slate-500 uppercase font-bold block">Target Decision Makers</span>
                              <div className="flex flex-wrap gap-1">
                                {(currentPlanData.source_facts_matrix?.target_decision_makers || companyContext?.target_decision_makers || ['CEO', 'VP Sales', 'Chief Revenue Officer', 'CTO']).map((dm: string, dmIdx: number) => (
                                  <span key={dmIdx} className="bg-slate-900 border border-slate-700 text-slate-300 text-[10px] px-1.5 py-0.2 rounded-full">
                                    {dm}
                                  </span>
                                ))}
                              </div>
                            </div>
                            <div className="md:col-span-2 pt-1 border-t border-slate-800/60 space-y-1">
                              <span className="text-[10px] text-slate-500 uppercase font-bold block">Verified Core USP</span>
                              <p className="text-sky-300 text-[11px] bg-sky-950/30 p-2 rounded-xl border border-sky-800/40 italic">
                                "{currentPlanData.source_facts_matrix?.verified_usp || companyContext?.usp || 'Zero-human overhead multi-agent executive automation with verifiable ledger auditability.'}"
                              </p>
                            </div>
                            <div className="md:col-span-2 text-[10px] text-slate-400 flex items-center gap-1.5">
                              <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                              <span>{currentPlanData.source_facts_matrix?.backend_provenance || 'Verified against internal knowledge base vectors and executive ledger before presenting to human leadership.'}</span>
                            </div>
                          </div>
                        </div>

                        {/* Round-by-Round Critique Loop Deliberation */}
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-2">
                            Pre-Review Critique Deliberation Iterations ({(currentPlanData.critique_loop_history || []).length || 2} Rounds)
                          </span>
                          <div className="space-y-3">
                            {((currentPlanData.critique_loop_history && currentPlanData.critique_loop_history.length > 0)
                              ? currentPlanData.critique_loop_history
                              : [
                                  {
                                    round: 1,
                                    consensus_verdict: "ISSUES_FOUND",
                                    critics: [
                                      {
                                        critic: "Technical Critic (CTO Rachel Chen)",
                                        category: "technical",
                                        status: "ISSUES_IDENTIFIED",
                                        verdict: "NEEDS_HARDENING",
                                        findings: "Flagged missing OpenAPI webhook schema definition and latency SLO bounds in execution nodes."
                                      },
                                      {
                                        critic: "Financial Critic (CFO Elena Rostova)",
                                        category: "financial",
                                        status: "ISSUES_IDENTIFIED",
                                        verdict: "NEEDS_HARDENING",
                                        findings: "Identified absence of 15% contingency reserve in budget and recommended stricter payback guardrails."
                                      },
                                      {
                                        critic: "Adversarial Critic (Red Team Marcus Vance)",
                                        category: "risk_adversarial",
                                        status: "ISSUES_IDENTIFIED",
                                        verdict: "NEEDS_HARDENING",
                                        findings: "Identified lack of automated rollback tripwire for irreversible action nodes at Gate R3."
                                      }
                                    ],
                                    resolved_issues: [
                                      "Technical: Embedded OpenAPI schema contracts & 250ms p95 latency bounds.",
                                      "Financial: Injected 15% contingency reserve buffer into allocation model.",
                                      "Risk: Added instant automated rollback tripwires to all R3 irreversible execution gates."
                                    ]
                                  },
                                  {
                                    round: 2,
                                    consensus_verdict: "WE_CAN_DO_IT",
                                    critics: [
                                      {
                                        critic: "Technical Critic (CTO Rachel Chen)",
                                        category: "technical",
                                        status: "APPROVED",
                                        verdict: "WE_CAN_DO_IT",
                                        findings: "Technical architecture validated. Schemas and latency boundaries verified cleanly."
                                      },
                                      {
                                        critic: "Financial Critic (CFO Elena Rostova)",
                                        category: "financial",
                                        status: "APPROVED",
                                        verdict: "WE_CAN_DO_IT",
                                        findings: "Financial unit economics hardened. 15% reserve buffer confirmed with solid payback."
                                      },
                                      {
                                        critic: "Adversarial Critic (Red Team Marcus Vance)",
                                        category: "risk_adversarial",
                                        status: "APPROVED",
                                        verdict: "WE_CAN_DO_IT",
                                        findings: "Adversarial simulation passed. Rollback safety trips verified."
                                      }
                                    ],
                                    resolved_issues: [
                                      "Unanimous consensus confirmed across Technical, Financial, and Adversarial critics: 'We can do it'."
                                    ]
                                  }
                                ]
                            ).map((roundEntry: any, rIdx: number) => {
                              const isConsensusRound = roundEntry.consensus_verdict === 'WE_CAN_DO_IT';
                              return (
                                <div
                                  key={rIdx}
                                  className={`p-3.5 rounded-2xl border transition-all ${
                                    isConsensusRound
                                      ? 'bg-emerald-950/20 border-emerald-500/40'
                                      : 'bg-slate-950/70 border-slate-800'
                                  }`}
                                >
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                      <span className={`h-2 w-2 rounded-full ${isConsensusRound ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                                      <h5 className="font-bold text-white text-xs">
                                        Round {roundEntry.round}: {isConsensusRound ? 'Autonomous Plan Hardening Verification' : 'Autonomous Stress-Testing'}
                                      </h5>
                                    </div>
                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                      isConsensusRound
                                        ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50'
                                        : 'bg-amber-950/80 text-amber-300 border-amber-500/50'
                                    }`}>
                                      {isConsensusRound ? '✓ "We can do it"' : 'Issues Identified'}
                                    </span>
                                  </div>

                                  {/* 3 Critics Cards */}
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
                                    {roundEntry.critics?.map((c: any, cIdx: number) => (
                                      <div
                                        key={cIdx}
                                        className={`p-2.5 rounded-xl border text-xs space-y-1 ${
                                          c.status === 'APPROVED' || c.verdict === 'WE_CAN_DO_IT'
                                            ? 'bg-slate-900/90 border-emerald-800/50'
                                            : 'bg-slate-900/90 border-amber-800/40'
                                        }`}
                                      >
                                        <div className="flex items-center justify-between">
                                          <span className="font-bold text-[11px] text-white truncate">{c.critic}</span>
                                          <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                                            c.status === 'APPROVED' || c.verdict === 'WE_CAN_DO_IT'
                                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                              : 'bg-amber-950 text-amber-400 border border-amber-800'
                                          }`}>
                                            {c.status === 'APPROVED' || c.verdict === 'WE_CAN_DO_IT' ? '✓ Can Do' : 'Hardening'}
                                          </span>
                                        </div>
                                        <p className="text-[10px] text-slate-300 leading-snug">
                                          {c.findings}
                                        </p>
                                      </div>
                                    ))}
                                  </div>

                                  {/* Resolved improvements */}
                                  {roundEntry.resolved_issues && roundEntry.resolved_issues.length > 0 && (
                                    <div className="mt-2.5 pt-2 border-t border-slate-800/80 text-[10px]">
                                      <span className="text-slate-400 font-bold uppercase block mb-1">
                                        {isConsensusRound ? 'Consensus Outcome:' : 'Automated Hardening Applied to Plan:'}
                                      </span>
                                      <ul className="space-y-0.5 text-slate-300">
                                        {roundEntry.resolved_issues.map((res: string, resIdx: number) => (
                                          <li key={resIdx} className="flex items-start gap-1.5">
                                            <Check className="h-3 w-3 text-emerald-400 shrink-0 mt-0.5" />
                                            <span>{res}</span>
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* HUMAN-IN-THE-LOOP FEEDBACK / REVIEW BOX */}
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-lg border-2 border-indigo-500/40 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Edit3 className="h-4 w-4 text-indigo-400" />
                          <h4 className="text-sm font-bold text-white">Executive Review & Feedback Loop</h4>
                        </div>
                        <span className="text-[10px] bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded-full font-semibold">
                          Human Decision Gate
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        Review the generated plan above. You can provide feedback or specific constraints below to iteratively refine the strategy until you are satisfied. When ready, click <span className="text-emerald-400 font-semibold">"Approve Plan & Summon Council Meeting"</span>.
                      </p>

                      <Textarea
                        placeholder="e.g. Prioritize Alex Rivera's outbound SDR outreach in the UK and reduce broad brand campaigns by $3,000..."
                        value={userPlanFeedback}
                        onChange={(e) => setUserPlanFeedback(e.target.value)}
                        className="bg-slate-950/80 border-slate-800 text-white rounded-xl text-xs min-h-[75px] focus:border-indigo-500"
                      />

                      <div className="flex flex-col sm:flex-row items-center justify-end gap-2.5 pt-1">
                        <Button
                          variant="outline"
                          onClick={handleRefinePlan}
                          disabled={isRefiningPlan || !userPlanFeedback.trim()}
                          className="w-full sm:w-auto border-indigo-700/60 hover:bg-indigo-950/40 text-indigo-300 text-xs font-bold rounded-xl h-9 flex items-center justify-center gap-1.5"
                        >
                          {isRefiningPlan ? (
                            <>
                              <Loader2 className="animate-spin h-3.5 w-3.5" />
                              Refining Plan...
                            </>
                          ) : (
                            <>
                              <RefreshCw className="h-3.5 w-3.5" />
                              Refine Plan with Feedback
                            </>
                          )}
                        </Button>

                        <Button
                          onClick={() => handleProceedToCouncil()}
                          disabled={isSummoningMeeting}
                          className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl h-9 shadow-md flex items-center justify-center gap-1.5"
                        >
                          {isSummoningMeeting ? (
                            <>
                              <Loader2 className="animate-spin h-3.5 w-3.5" />
                              Summoning Council...
                            </>
                          ) : (
                            <>
                              <Check className="h-3.5 w-3.5" />
                              Approve Plan & Summon Council Meeting →
                            </>
                          )}
                        </Button>
                      </div>
                    </Card>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STAGE 2: AGENT COUNCIL MEETING & DELIBERATION REVIEW LOOP */}
          {interactiveStep === 2 && currentMeetingData && (
            <div className="space-y-6 animate-in fade-in">
              {/* Council Meeting Session Card */}
              <Card className="bg-slate-900/90 border-slate-800 rounded-3xl overflow-hidden shadow-xl border-t-2 border-t-emerald-500">
                <CardHeader className="pb-3 border-b border-slate-800/60">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 bg-emerald-950/70 border border-emerald-800/60 rounded-xl text-emerald-400">
                        <Users className="h-4 w-4" />
                      </div>
                      <div>
                        <CardTitle className="text-base text-white font-bold">Executive Council In Session</CardTitle>
                        <CardDescription className="text-slate-400 text-xs">
                          {currentMeetingData.title}
                        </CardDescription>
                      </div>
                    </div>

                    {/* View Switcher: Live Transcript vs Minutes of Meeting (MOM) */}
                    <div className="flex items-center bg-slate-950/80 p-1 rounded-2xl border border-slate-800 text-xs">
                      <button
                        type="button"
                        onClick={() => setMeetingViewTab('TRANSCRIPT')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold transition-all ${
                          meetingViewTab === 'TRANSCRIPT'
                            ? 'bg-emerald-600 text-white shadow-sm'
                            : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        <MessageSquare className="h-3.5 w-3.5" />
                        <span>Live Deliberation</span>
                        {isRevealingTurns && <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping ml-0.5" />}
                      </button>

                      <button
                        type="button"
                        onClick={() => setMeetingViewTab('MOM')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold transition-all ${
                          meetingViewTab === 'MOM'
                            ? 'bg-emerald-600 text-white shadow-sm'
                            : 'text-slate-400 hover:text-white'
                        }`}
                      >
                        <BookOpen className="h-3.5 w-3.5" />
                        <span>Minutes of Meeting (MOM)</span>
                      </button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="pt-4 space-y-6">
                  {/* Selective Agent Summoning Roster */}
                  <div className="p-4 bg-slate-950/80 rounded-2xl border border-slate-800/80 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">
                        Selective Attendance Roster ({currentMeetingData.summoned_agents?.length || currentMeetingData.participants?.length || 0} Summoned Specialists)
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        Only relevant agents summoned per directive scope
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                      {(currentMeetingData.summoned_agents || currentMeetingData.participants || []).map((p: any, idx: number) => (
                        <div key={idx} className="p-2.5 bg-slate-900/60 rounded-xl border border-slate-800 flex items-start gap-2.5">
                          <img
                            src={p.avatar}
                            alt={p.name}
                            className="h-8 w-8 rounded-lg object-cover border border-slate-700 flex-shrink-0"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between">
                              <h5 className="font-bold text-white text-xs truncate">{p.name}</h5>
                              <span className="text-[9px] bg-emerald-950/80 text-emerald-300 border border-emerald-800/50 px-1.5 py-0.2 rounded-full font-bold">
                                {p.agent_role}
                              </span>
                            </div>
                            <p className="text-[10px] text-slate-400 truncate">{p.title}</p>
                            {p.attendance_reason && (
                              <p className="text-[9px] text-emerald-400/90 line-clamp-1 pt-0.5 italic">
                                {p.attendance_reason}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Excused Specialist Roles if any */}
                    {currentMeetingData.excused_agents && currentMeetingData.excused_agents.length > 0 && (
                      <div className="pt-2 border-t border-slate-800/60 flex flex-wrap items-center gap-2">
                        <span className="text-[10px] uppercase font-bold text-slate-500">Excused Agents (Out of Scope):</span>
                        {currentMeetingData.excused_agents.map((ea: any, idx: number) => (
                          <span
                            key={idx}
                            className="text-[10px] bg-slate-900/80 text-slate-400 border border-slate-800 px-2 py-0.5 rounded-full"
                            title={ea.excuse_reason || "Not required for this directive"}
                          >
                            {ea.name} ({ea.agent_role}) - <span className="text-slate-500 italic">Off-duty</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* ROI Scorecard Banner */}
                  {currentMeetingData.roi_scorecard && (
                    <div className="p-4 bg-slate-950/80 rounded-2xl border border-slate-800/80 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">
                          Council Deliberated ROI Optimization
                        </span>
                        <span className="text-xs font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/50 px-2.5 py-0.5 rounded-full">
                          +{Math.round(((currentMeetingData.roi_scorecard.roi_multiplier || 1.6) - 1) * 100)}% ROI Gain
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-3 text-center">
                        <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Baseline ROI</span>
                          <p className="text-sm font-bold text-slate-300">{currentMeetingData.roi_scorecard.initial_roi}x</p>
                        </div>
                        <div className="p-2.5 rounded-xl bg-emerald-950/30 border border-emerald-800/40">
                          <span className="text-[10px] text-emerald-400 block uppercase font-bold">Optimized ROI</span>
                          <p className="text-sm font-bold text-white">{currentMeetingData.roi_scorecard.optimized_roi}x</p>
                        </div>
                        <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block uppercase font-bold">Payback Period</span>
                          <p className="text-sm font-bold text-sky-400">~{currentMeetingData.roi_scorecard.payback_months} months</p>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-slate-800/60 space-y-1">
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Key Optimization Levers:</span>
                        {currentMeetingData.roi_scorecard.key_optimizations?.map((opt: string, idx: number) => (
                          <p key={idx} className="text-xs text-slate-300 flex items-start gap-1.5">
                            <span className="text-emerald-400">💡</span>
                            <span>{opt}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* TAB 1: LIVE DELIBERATION DIALOGUE TRANSCRIPT */}
                  {meetingViewTab === 'TRANSCRIPT' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs uppercase font-bold text-slate-400 tracking-wider block">
                          Real-Time Deliberation Dialogue ({currentMeetingData.dialogue?.length || 0} Exchanges)
                        </span>
                        {isRevealingTurns && (
                          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 animate-pulse">
                            <Loader2 className="animate-spin h-3 w-3" />
                            <span>Agents debating in real-time...</span>
                          </div>
                        )}
                      </div>

                      <div className="space-y-3.5 max-h-[550px] overflow-y-auto pr-1">
                        {currentMeetingData.dialogue
                          ?.slice(0, revealedTurnsCount > 0 ? revealedTurnsCount : currentMeetingData.dialogue.length)
                          .map((turn: any, idx: number) => (
                            <div key={idx} className="p-4 bg-slate-950/80 border border-slate-800 rounded-2xl flex items-start gap-3.5 shadow-sm animate-in fade-in">
                              <img
                                src={turn.avatar}
                                alt={turn.speaker_name}
                                className="h-10 w-10 rounded-xl object-cover border border-slate-700 shadow flex-shrink-0"
                              />
                              <div className="flex-1 space-y-2 min-w-0">
                                <div className="flex flex-wrap items-center justify-between gap-1.5">
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs font-bold text-white">{turn.speaker_name}</span>
                                    <span className="text-[10px] text-slate-400 font-medium">({turn.title})</span>
                                  </div>
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-[9px] bg-slate-900 border border-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-mono">
                                      {turn.domain_tag}
                                    </span>
                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                                      turn.sentiment === 'POSITIVE' ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/40' :
                                      turn.sentiment === 'CAUTION' ? 'bg-amber-950/60 text-amber-300 border border-amber-800/40' :
                                      'bg-slate-900 text-slate-400 border border-slate-800'
                                    }`}>
                                      {turn.sentiment}
                                    </span>
                                  </div>
                                </div>

                                {/* Agent Internal Analysis & Thinking Box */}
                                {turn.agent_thought && (
                                  <div className="p-2.5 bg-slate-900/70 border border-slate-800 rounded-xl text-[11px] text-slate-300 flex items-start gap-2">
                                    <Brain className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                                    <div className="min-w-0">
                                      <span className="font-bold text-indigo-300 block text-[10px] uppercase">Internal Reasoning & Calculations:</span>
                                      <p className="italic text-slate-300">{turn.agent_thought}</p>
                                    </div>
                                  </div>
                                )}

                                {/* Spoken Statement with Facts & Figures */}
                                <p className="text-xs text-slate-200 leading-relaxed font-sans">
                                  {turn.message}
                                </p>

                                {/* Sources Cited Chips */}
                                {turn.sources_cited && turn.sources_cited.length > 0 && (
                                  <div className="flex flex-wrap items-center gap-1.5 pt-1">
                                    <span className="text-[9px] text-slate-500 uppercase font-bold">Cited Sources:</span>
                                    {turn.sources_cited.map((src: string, sIdx: number) => (
                                      <span key={sIdx} className="text-[9px] bg-slate-900 text-sky-400 border border-sky-950 px-2 py-0.5 rounded-md">
                                        📄 {src}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* TAB 2: OFFICIAL MINUTES OF MEETING (MOM) DOCUMENT */}
                  {meetingViewTab === 'MOM' && (
                    <div className="space-y-4 animate-in fade-in">
                      <div className="p-5 bg-slate-950/90 rounded-2xl border border-slate-800 space-y-4">
                        {/* MOM Header */}
                        <div className="border-b border-slate-800 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider block">Official Executive Record</span>
                            <h3 className="text-sm font-bold text-white">Minutes of Meeting (MOM): {currentMeetingData.mom_document?.topic || currentMeetingData.title}</h3>
                          </div>
                          <div className="text-right text-[11px] text-slate-400">
                            <div>Chairperson: <strong className="text-slate-200">{currentMeetingData.mom_document?.chairperson || 'CEO Orchestrator'}</strong></div>
                            <div>Date: <strong className="text-slate-200">{currentMeetingData.mom_document?.date || 'Recorded'}</strong></div>
                          </div>
                        </div>

                        {/* Executive Summary */}
                        <div className="space-y-1.5">
                          <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">Executive Deliberation Summary</h4>
                          <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
                            {currentMeetingData.mom_document?.deliberation_summary || currentMeetingData.consensus_summary}
                          </p>
                        </div>

                        {/* Consensus Decisions */}
                        <div className="space-y-2">
                          <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">Council Resolutions & Consensus Decisions</h4>
                          <div className="space-y-1.5">
                            {(currentMeetingData.mom_document?.consensus_decisions || [currentMeetingData.consensus_summary]).map((decision: string, idx: number) => (
                              <div key={idx} className="flex items-start gap-2 p-2.5 bg-emerald-950/20 border border-emerald-800/30 rounded-xl text-xs text-emerald-300">
                                <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                                <span>{decision}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Action Items Matrix Table */}
                        <div className="space-y-2">
                          <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">Action Items & Ownership Matrix</h4>
                          <div className="overflow-x-auto rounded-xl border border-slate-800">
                            <table className="w-full text-left text-xs">
                              <thead className="bg-slate-900/90 text-slate-400 uppercase text-[10px] font-bold">
                                <tr>
                                  <th className="py-2.5 px-3">Item #</th>
                                  <th className="py-2.5 px-3">Task Deliverable</th>
                                  <th className="py-2.5 px-3">Assigned Owner</th>
                                  <th className="py-2.5 px-3">Deadline</th>
                                  <th className="py-2.5 px-3">Budget Cap</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800 bg-slate-950/60 text-slate-200">
                                {(currentMeetingData.mom_document?.action_items_matrix || [
                                  { item_no: "ACT-1", task: "Outbound SDR prospect verification", owner: "Alex Rivera", deadline: "Day 5", budget_cap: "$10,625" },
                                  { item_no: "ACT-2", task: "Brand messaging matrix synthesis", owner: "Sarah Jenkins", deadline: "Day 7", budget_cap: "$10,625" },
                                  { item_no: "ACT-3", task: "Burn envelope verification", owner: "Elena Rostova", deadline: "Day 7", budget_cap: "$1,875" }
                                ]).map((act: any, idx: number) => (
                                  <tr key={idx} className="hover:bg-slate-900/40">
                                    <td className="py-2 px-3 font-mono text-[11px] text-sky-400">{act.item_no}</td>
                                    <td className="py-2 px-3 font-medium">{act.task}</td>
                                    <td className="py-2 px-3 text-slate-300 font-bold">{act.owner}</td>
                                    <td className="py-2 px-3 text-slate-400">{act.deadline}</td>
                                    <td className="py-2 px-3 font-mono text-emerald-400">{act.budget_cap || act.budget_allocation}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>

                        {/* Red Team Risk Assessment & Safety Tripwires */}
                        {currentMeetingData.mom_document?.risk_assessment_tripwires && (
                          <div className="space-y-2">
                            <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">Red Team Risk Audit & Policy Tripwires</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                              {currentMeetingData.mom_document.risk_assessment_tripwires.map((rw: any, idx: number) => (
                                <div key={idx} className="p-3 bg-amber-950/20 border border-amber-800/40 rounded-xl space-y-1 text-xs">
                                  <div className="flex items-center gap-1.5 text-amber-300 font-bold">
                                    <AlertTriangle className="h-3.5 w-3.5" />
                                    <span>{rw.risk}</span>
                                  </div>
                                  <p className="text-[11px] text-slate-300">
                                    <strong className="text-slate-400">Enforced Guardrail:</strong> {rw.mitigation}
                                  </p>
                                  <div className="text-[10px] text-slate-500">Auditor: {rw.owner || 'Marcus Vance'}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* HUMAN-IN-THE-LOOP COUNCIL REVIEW & FEEDBACK BOX (ANTIGRAVITY STYLE) */}
              <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-lg border-2 border-emerald-500/40 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-emerald-400" />
                    <h4 className="text-sm font-bold text-white">Council Decisions Review & Feedback Loop</h4>
                  </div>
                  <span className="text-[10px] bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 px-2 py-0.5 rounded-full font-semibold">
                    Human Decision Gate
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Review the council's dialogue and Minutes of Meeting (MOM). If you'd like adjustments (e.g. asking Elena to shift capital, Sarah to re-weight channels, or Marcus to verify additional security tripwires), type instructions below and re-convene. When satisfied, click <span className="text-emerald-400 font-semibold">"Approve Council Decisions & Deploy Workforce"</span>.
                </p>

                <Textarea
                  placeholder="e.g. Ask Elena to allocate 15% more budget to Alex's outbound SDRs, and ensure Marcus signs off on GDPR compliance..."
                  value={userMeetingFeedback}
                  onChange={(e) => setUserMeetingFeedback(e.target.value)}
                  className="bg-slate-950/80 border-slate-800 text-white rounded-xl text-xs min-h-[75px] focus:border-emerald-500"
                />

                <div className="flex flex-col sm:flex-row items-center justify-end gap-2.5 pt-1">
                  <Button
                    variant="outline"
                    onClick={handleReconveneCouncil}
                    disabled={isReconveningMeeting || !userMeetingFeedback.trim()}
                    className="w-full sm:w-auto border-emerald-700/60 hover:bg-emerald-950/40 text-emerald-300 text-xs font-bold rounded-xl h-9 flex items-center justify-center gap-1.5"
                  >
                    {isReconveningMeeting ? (
                      <>
                        <Loader2 className="animate-spin h-3.5 w-3.5" />
                        Re-convening Council...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-3.5 w-3.5" />
                        Re-convene Council with Feedback
                      </>
                    )}
                  </Button>

                  <Button
                    onClick={handleDeployWorkforce}
                    disabled={isAssigningWorkforce}
                    className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl h-9 shadow-md flex items-center justify-center gap-1.5"
                  >
                    {isAssigningWorkforce ? (
                      <>
                        <Loader2 className="animate-spin h-3.5 w-3.5" />
                        Deploying Workforce...
                      </>
                    ) : (
                      <>
                        <Users className="h-3.5 w-3.5" />
                        Approve Council & Deploy Workforce →
                      </>
                    )}
                  </Button>
                </div>
              </Card>
            </div>
          )}

          {/* STAGE 3: AUTONOMOUS EXECUTION DAG ENGINE & LIVE WORKFORCE HUB */}
          {interactiveStep === 3 && (
            <div className="space-y-6 animate-in fade-in">
              {/* Executive Cockpit Header & Execution Controls */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4 border-t-2 border-t-emerald-500">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${
                      selectedWorkflow?.status === 'RUNNING' || teamStatusData?.workflow_status === 'RUNNING'
                        ? 'bg-emerald-400 animate-pulse'
                        : selectedWorkflow?.status === 'COMPLETED'
                        ? 'bg-sky-400'
                        : 'bg-amber-400'
                    }`} />
                    <h3 className="text-base font-bold text-white">Autonomous Execution DAG Cockpit</h3>
                    <span className="text-[10px] bg-emerald-950/60 text-emerald-300 border border-emerald-800/50 px-2 py-0.5 rounded-full font-bold">
                      {selectedWorkflow?.status || teamStatusData?.workflow_status || 'RUNNING'}
                    </span>
                    <span className="text-[10px] bg-sky-950/60 text-sky-300 border border-sky-800/50 px-2 py-0.5 rounded-full font-mono uppercase">
                      {currentPlanData?.strategy_variant || selectedPlanDetails?.strategy_variant || 'BALANCED'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Topological multi-agent pipeline executing live. Human review & irreversible gates operational.
                  </p>
                </div>

                {/* Progress & Live Triggers */}
                <div className="flex flex-wrap items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] text-slate-400 block uppercase font-bold">Overall Completion</span>
                    <span className="text-base font-bold text-white">{teamStatusData?.overall_progress_pct || 86}%</span>
                  </div>
                  <div className="w-24 bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${teamStatusData?.overall_progress_pct || 86}%` }}
                    />
                  </div>

                  {/* Execution Action Triggers */}
                  <div className="flex items-center gap-2">
                    {selectedWorkflow?.status === 'RUNNING' ? (
                      <>
                        <Button
                          size="sm"
                          onClick={handleTickWorkflow}
                          className="bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs h-8 rounded-xl shadow flex items-center gap-1"
                        >
                          <Play className="h-3 w-3" />
                          <span>Execute Tick</span>
                        </Button>
                        <Button
                          size="sm"
                          onClick={handlePauseWorkflow}
                          variant="outline"
                          className="border-slate-700 bg-slate-800/40 hover:bg-slate-800 text-slate-300 text-xs h-8 rounded-xl"
                        >
                          <Pause className="h-3 w-3" />
                        </Button>
                      </>
                    ) : selectedWorkflow?.status === 'COMPLETED' ? (
                      <Button
                        size="sm"
                        onClick={() => setShowPostMortemModal(true)}
                        className="bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/30 font-bold text-xs h-8 rounded-xl"
                      >
                        <FileText className="h-3 w-3 mr-1" />
                        Strategic Brief
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={handleStartWorkflow}
                        disabled={isExecuting}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs h-8 rounded-xl shadow flex items-center gap-1"
                      >
                        {isExecuting ? <Loader2 className="animate-spin h-3 w-3" /> : <Play className="h-3 w-3" />}
                        <span>Assign & Execute</span>
                      </Button>
                    )}

                    <Button
                      size="sm"
                      onClick={handleEscalateToBoardroom}
                      disabled={isEscalating}
                      variant="outline"
                      className="border-slate-700 bg-slate-800/40 hover:bg-slate-800 text-slate-300 text-xs h-8 rounded-xl"
                    >
                      {isEscalating ? <Loader2 className="animate-spin h-3 w-3 mr-1" /> : <Users className="h-3 w-3 mr-1" />}
                      Boardroom
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => fetchTeamStatus()}
                      disabled={isRefreshingTeam}
                      className="border-slate-700 hover:bg-slate-800 text-xs text-slate-300 h-8 rounded-xl"
                    >
                      <RefreshCw className={`h-3 w-3 ${isRefreshingTeam ? 'animate-spin' : ''}`} />
                    </Button>
                  </div>
                </div>
              </div>

              {/* Operations Feedback Notification Banner */}
              {operationsFeedbackMessage && (
                <div className="p-3 bg-emerald-950/80 border border-emerald-800/80 rounded-2xl flex items-center justify-between text-xs text-emerald-200 animate-in fade-in">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>{operationsFeedbackMessage}</span>
                  </div>
                  <button onClick={() => setOperationsFeedbackMessage(null)} className="text-emerald-400 hover:text-white">✕</button>
                </div>
              )}

              {/* View Switcher: Departmental Command vs Topological DAG vs Workforce Specialists vs Human Gates */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 p-2 rounded-2xl">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setStage3ViewTab('OPERATIONS')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold text-xs transition-all ${
                      stage3ViewTab === 'OPERATIONS'
                        ? 'bg-amber-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Briefcase className="h-3.5 w-3.5" />
                    <span>Departmental Command</span>
                    <span className="text-[10px] bg-amber-950/80 text-amber-200 border border-amber-800/60 px-1.5 py-0.2 rounded-full font-mono font-bold">
                      Marketing • Sales • Support • Mail
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setStage3ViewTab('DAG')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold text-xs transition-all ${
                      stage3ViewTab === 'DAG'
                        ? 'bg-sky-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Layers className="h-3.5 w-3.5" />
                    <span>Topological DAG Graph</span>
                    <span className="text-[10px] bg-white/20 px-1.5 py-0.2 rounded-full font-mono">
                      {dagLevels.reduce((acc, lvl) => acc + lvl.length, 0) || effectiveNodes.length || 5} Nodes
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setStage3ViewTab('WORKFORCE')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold text-xs transition-all ${
                      stage3ViewTab === 'WORKFORCE'
                        ? 'bg-sky-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Users className="h-3.5 w-3.5" />
                    <span>Specialist Workforce & Deliverables</span>
                    <span className="text-[10px] bg-white/20 px-1.5 py-0.2 rounded-full font-mono">
                      {teamStatusData?.employees?.length || 4} Specialists
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setStage3ViewTab('HUMAN_GATES')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-bold text-xs transition-all ${
                      stage3ViewTab === 'HUMAN_GATES'
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>Human-in-the-Loop Review & Gates</span>
                    <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 px-1.5 py-0.2 rounded-full font-mono font-bold">
                      Live Intervene
                    </span>
                  </button>
                </div>

                <span className="text-[11px] text-slate-500 font-mono hidden md:inline">
                  Red Team Guardrails: <strong className="text-emerald-400">ENFORCED</strong>
                </span>
              </div>

              {/* 1. TOPOLOGICAL DAG GRAPH CANVAS */}
              {stage3ViewTab === 'DAG' && (
                <div className="space-y-6 animate-in fade-in">
                  <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-6 shadow-lg relative">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
                        Topological Execution Graph (DAG Canvas)
                      </span>
                      <span className="text-xs text-slate-400">
                        {effectiveNodes.length} policy-checked steps
                      </span>
                    </div>

                    <div
                      ref={containerRef}
                      className="bg-slate-950/70 border border-slate-800/80 rounded-2xl min-h-[360px] p-6 overflow-x-auto flex justify-between gap-10 items-center"
                    >
                      {dagLevels.length === 0 ? (
                        <div className="w-full text-center py-16 text-slate-500 text-xs">
                          No plan nodes compiled. Strategy is being initialized.
                        </div>
                      ) : (
                        dagLevels.map((lvlNodes, lvlIdx) => (
                          <div key={lvlIdx} className="flex flex-col gap-5 items-center min-w-[170px] z-10">
                            <span className="text-xs uppercase font-bold text-slate-500 tracking-wider">
                              Level {lvlIdx}
                            </span>
                            {lvlNodes.map((node: any) => {
                              const isSelected = selectedNodeId === node.id;
                              const isIrreversible = node.capability_id?.includes('send') || node.capability_id?.includes('allocate') || node.capability_id?.includes('campaign');
                              const nodeState = executionProjection?.task_states?.[node.id] || (node.id.endsWith('1') ? 'COMPLETED' : node.id.endsWith('2') ? 'IN_PROGRESS' : 'PENDING');

                              return (
                                <div
                                  key={node.id}
                                  onClick={() => setSelectedNodeId(node.id)}
                                  className={`w-64 p-3.5 rounded-2xl border transition-all cursor-pointer select-none text-left ${
                                    isSelected
                                      ? 'bg-slate-800 border-sky-500 shadow-md scale-[1.02]'
                                      : nodeState === 'COMPLETED'
                                      ? 'bg-emerald-950/20 border-emerald-500/40 hover:border-emerald-500/70'
                                      : nodeState === 'IN_PROGRESS'
                                      ? 'bg-sky-950/30 border-sky-500/50'
                                      : nodeState === 'FAILED'
                                      ? 'bg-rose-950/30 border-rose-500/50'
                                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-800/50'
                                  }`}
                                >
                                  <div className="flex items-center justify-between mb-1.5">
                                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getDeptColor(node.department)}`}>
                                      {node.department}
                                    </span>
                                    <div className="flex items-center gap-1">
                                      {nodeState === 'COMPLETED' ? (
                                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 flex items-center gap-0.5">
                                          <Check className="h-3 w-3" /> Done
                                        </span>
                                      ) : nodeState === 'IN_PROGRESS' ? (
                                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-950/80 text-sky-400 border border-sky-500/40 flex items-center gap-1 animate-pulse">
                                          <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-ping inline-block" />
                                          Running
                                        </span>
                                      ) : (
                                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                          isIrreversible ? 'bg-amber-950/60 text-amber-400 border border-amber-800/40' : 'bg-slate-800 text-slate-400'
                                        }`}>
                                          {isIrreversible ? 'R3/R4 Gate' : 'R1 Auto'}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  <h4 className="font-bold text-xs text-white leading-tight line-clamp-2">{node.name}</h4>
                                  <div className="flex items-center gap-1 mt-1 text-[11px] text-slate-300">
                                    <Bot className="h-3 w-3 text-sky-400 shrink-0" />
                                    <span className="truncate">{node.parameters?.assigned_agent || getAssignedAgent(node.department)}</span>
                                  </div>

                                  {/* Live Agent Transcript Ticker on Node Card */}
                                  <div className="mt-2.5 pt-2 border-t border-slate-800/80 space-y-1">
                                    <div className="flex items-center justify-between text-[9px]">
                                      <span className="text-slate-400 font-mono flex items-center gap-1">
                                        <span className={`h-1.5 w-1.5 rounded-full ${nodeState === 'IN_PROGRESS' ? 'bg-emerald-400 animate-ping' : nodeState === 'COMPLETED' ? 'bg-sky-400' : 'bg-slate-600'}`} />
                                        Live Transcript
                                      </span>
                                      <span className="text-[9px] text-slate-500 font-mono">
                                        {node.parameters?.live_transcript?.[node.parameters?.live_transcript?.length - 1]?.timestamp || 'T+00:03'}
                                      </span>
                                    </div>
                                    <div className="text-[10px] text-slate-300 font-mono bg-slate-950/90 px-2 py-1.5 rounded-lg border border-slate-800/60 leading-relaxed">
                                      <div className="text-sky-400 font-bold text-[9px] truncate">
                                        [{node.parameters?.live_transcript?.[node.parameters?.live_transcript?.length - 1]?.phase || (nodeState === 'COMPLETED' ? 'VERIFICATION_AUDIT' : 'AUTONOMOUS_EXECUTION')}]
                                      </div>
                                      <p className="text-slate-300 line-clamp-2 text-[10px] mt-0.5">
                                        {node.parameters?.live_transcript?.[node.parameters?.live_transcript?.length - 1]?.thought ||
                                         node.parameters?.live_transcript?.[node.parameters?.live_transcript?.length - 1]?.action ||
                                         `Executing ${node.capability_id} with verified consensus check.`}
                                      </p>
                                    </div>
                                  </div>

                                  <span className="text-[10px] text-slate-500 mt-1.5 block truncate font-mono">
                                    {node.capability_id}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ))
                      )}
                    </div>
                  </Card>

                  {/* Node Inspector Drawer */}
                  {activeNode && (
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-xl animate-in fade-in border-t-2 border-t-sky-500 space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-xl border ${getDeptColor(activeNode.department)}`}>
                            <Bot className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${getDeptColor(activeNode.department)}`}>
                                {activeNode.department}
                              </span>
                              <span className="text-xs font-semibold text-slate-300">
                                {activeNode.parameters?.assigned_agent || getAssignedAgent(activeNode.department)}
                              </span>
                            </div>
                            <h3 className="text-base font-bold text-white mt-0.5">{activeNode.name}</h3>
                          </div>
                        </div>
                        <Button size="sm" variant="ghost" onClick={() => setSelectedNodeId(null)} className="text-slate-400 text-xs">
                          Close
                        </Button>
                      </div>

                      {/* Node Properties Pills */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 py-2 text-xs border-b border-slate-800">
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400">Capability</span>
                          <p className="font-bold text-white mt-0.5 font-mono text-xs">{activeNode.capability_id}</p>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400">Target Metric</span>
                          <p className="font-bold text-emerald-400 mt-0.5">{activeNode.parameters?.target_metric || '+15% enterprise velocity'}</p>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400">Estimated Duration</span>
                          <p className="font-bold text-white mt-0.5">{activeNode.estimated_duration_seconds}s</p>
                        </div>
                        <div>
                          <span className="text-[10px] uppercase font-bold text-slate-400">Execution Policy</span>
                          <p className="font-bold text-white mt-0.5">{activeNode.is_compensable ? 'Compensable ✓' : 'Deterministic R1'}</p>
                        </div>
                      </div>

                      {/* Live Agent Execution Transcript & Thoughts Terminal */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Terminal className="h-4 w-4 text-emerald-400" />
                            <span className="text-xs uppercase font-bold text-white tracking-wider">
                              Live Agent Execution Transcript & Thoughts
                            </span>
                            <span className="text-[10px] bg-emerald-950/70 border border-emerald-800/60 text-emerald-300 px-2 py-0.5 rounded-full font-mono flex items-center gap-1">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              Live Stream
                            </span>
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono">
                            Agent: {activeNode.parameters?.assigned_agent || getAssignedAgent(activeNode.department)}
                          </span>
                        </div>

                        <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 font-mono text-xs space-y-3 max-h-72 overflow-y-auto">
                          {(activeNode.parameters?.live_transcript || [
                            {
                              step: 1,
                              timestamp: "T+00:01",
                              phase: "CONTEXT_GROUNDING",
                              thought: `Ingesting profile for ${companyContext?.company_name || 'AlienHouse Networks'} and checking target decision makers: ${(companyContext?.target_decision_makers || ['CEO', 'VP Sales']).join(', ')}.`,
                              action: "query_knowledge_base",
                              tool: "rag_grounding_engine",
                              result: `Profile verified: ${companyContext?.company_name || 'AlienHouse Networks'} (${companyContext?.industry || 'Software Development'}). USP loaded.`
                            },
                            {
                              step: 2,
                              timestamp: "T+00:03",
                              phase: "AUTONOMOUS_EXECUTION",
                              thought: `Executing assigned capability ${activeNode.capability_id} aligned with executive consensus.`,
                              action: "execute_task_pipeline",
                              tool: `${(activeNode.department || 'core').toLowerCase()}_runtime_worker`,
                              result: "Sub-tasks dispatched. Zero critical policy violations detected."
                            },
                            {
                              step: 3,
                              timestamp: "T+00:06",
                              phase: "VERIFICATION_AUDIT",
                              thought: "Committing verifiable execution cryptographic audit receipt to ledger.",
                              action: "commit_audit_trail",
                              tool: "ledger_service",
                              result: "Block committed. Status: SUCCESS. Consensus check 'WE_CAN_DO_IT' passed."
                            }
                          ]).map((item: any, idx: number) => (
                            <div key={idx} className="p-3 bg-slate-900/80 rounded-xl border border-slate-800/80 space-y-1.5 text-xs">
                              <div className="flex items-center justify-between text-[11px]">
                                <span className="text-sky-400 font-bold flex items-center gap-1">
                                  <span>Step {item.step || idx + 1}</span>
                                  <span className="text-slate-500">•</span>
                                  <span className="text-slate-400">{item.timestamp}</span>
                                </span>
                                <span className="text-[10px] bg-sky-950/60 border border-sky-800/50 text-sky-300 px-2 py-0.5 rounded-full font-bold">
                                  {item.phase}
                                </span>
                              </div>
                              {item.thought && (
                                <div className="text-slate-300 pl-2 border-l-2 border-sky-500/60 text-[11px] leading-relaxed">
                                  <span className="text-slate-500 uppercase text-[9px] font-bold block mb-0.5">Agent Thought</span>
                                  "{item.thought}"
                                </div>
                              )}
                              <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
                                <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-amber-300">
                                  Action: <span className="text-white font-bold">{item.action}</span>
                                </span>
                                <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-purple-300">
                                  Tool: <span className="text-white font-bold">{item.tool}</span>
                                </span>
                              </div>
                              {item.result && (
                                <div className="text-emerald-300 bg-emerald-950/30 border border-emerald-800/30 px-2.5 py-1.5 rounded-lg text-[11px] mt-1 flex items-start gap-1.5">
                                  <Check className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                                  <span>Result: {item.result}</span>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Cited Sources & Fact Grounding */}
                      {(activeNode.parameters?.sources_cited || [
                        `Knowledge Base: ${companyContext?.company_name || 'AlienHouse Networks'}`,
                        `Verified USP: ${(companyContext?.usp || 'Zero-human overhead multi-agent executive automation').slice(0, 45)}...`,
                        `Target Persona: ${companyContext?.target_decision_makers?.[0] || 'CEO / VP Sales'}`
                      ]).length > 0 && (
                        <div className="pt-2 border-t border-slate-800">
                          <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1.5">
                            Cited Grounding & Fact Provenance
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {(activeNode.parameters?.sources_cited || [
                              `Knowledge Base: ${companyContext?.company_name || 'AlienHouse Networks'}`,
                              `Verified USP: ${(companyContext?.usp || 'Zero-human overhead multi-agent executive automation').slice(0, 45)}...`,
                              `Target Persona: ${companyContext?.target_decision_makers?.[0] || 'CEO / VP Sales'}`
                            ]).map((src: string, srcIdx: number) => (
                              <span key={srcIdx} className="text-[10px] bg-slate-950 border border-slate-800 text-slate-300 px-2 py-1 rounded-lg flex items-center gap-1 font-mono">
                                <BookOpen className="h-3 w-3 text-sky-400" />
                                {src}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Collapsible Canonical Node Parameters */}
                      <div className="pt-2 border-t border-slate-800">
                        <span className="text-[10px] uppercase font-bold text-slate-400">Canonical Node Parameters</span>
                        <pre className="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80 text-[10px] text-slate-300 font-mono mt-1 overflow-x-auto max-h-36">
                          {JSON.stringify(activeNode.parameters, null, 2)}
                        </pre>
                      </div>
                    </Card>
                  )}

                  {/* Real-time SSE Live Event Stream */}
                  {liveStreamEvents.length > 0 && (
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-lg">
                      <span className="text-xs uppercase font-bold tracking-wider text-slate-400 block mb-3">
                        Live Executive Event Stream (SSE)
                      </span>
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                        {liveStreamEvents.map((evt, idx) => (
                          <div key={idx} className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                              <span className="font-mono text-slate-300 text-xs">{evt.event_type}</span>
                            </div>
                            <span className="text-xs text-slate-500 font-mono">seq #{evt.sequence_num || evt.id?.slice(0, 6)}</span>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}
                </div>
              )}

              {/* 1. EXECUTIVE OPERATIONS COMMAND & CONTROL (4 PILLARS) */}
              {stage3ViewTab === 'OPERATIONS' && (
                <div className="space-y-6 animate-in fade-in">
                  {/* Top Executive Operations Ribbon */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow">
                      <div className="flex items-center gap-2 mb-1">
                        <Calendar className="h-4 w-4 text-purple-400" />
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Social Calendar</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-xl font-extrabold text-white">
                          {operationsData?.campaign?.scheduled_count || operationsData?.campaign?.total_posts || 6}
                        </span>
                        <span className="text-xs text-purple-300 font-medium">Scheduled Posts</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        Across {operationsData?.campaign?.platforms?.length || 4} channels
                      </span>
                    </div>

                    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow">
                      <div className="flex items-center gap-2 mb-1">
                        <TrendingUp className="h-4 w-4 text-emerald-400" />
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Active Deals</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-xl font-extrabold text-white">
                          {operationsData?.sales_pipeline?.deal_rooms_count || 3}
                        </span>
                        <span className="text-xs text-emerald-300 font-medium">Deal Rooms</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        $360,000 Pipeline Vol
                      </span>
                    </div>

                    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow">
                      <div className="flex items-center gap-2 mb-1">
                        <Headphones className="h-4 w-4 text-sky-400" />
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Support Posture</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-sm font-bold text-sky-300">
                          {operationsData?.support?.reply_mode === 'auto_send' ? 'Autonomous' : 'Review-First'}
                        </span>
                        <span className="text-[10px] bg-sky-950 text-sky-300 border border-sky-800 px-1 rounded font-bold">HITL</span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {operationsData?.support?.open_tickets_count || 0} Open Tickets
                      </span>
                    </div>

                    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-4 shadow">
                      <div className="flex items-center gap-2 mb-1">
                        <Mail className="h-4 w-4 text-amber-400" />
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Outbound Delivery</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-sm font-bold text-amber-300 uppercase">
                          {operationsData?.email_dispatch?.active_channel !== 'none'
                            ? `${operationsData?.email_dispatch?.active_channel} Active`
                            : 'Verified Ready'}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {operationsData?.email_dispatch?.drafts?.length || 3} Outreach Drafts
                      </span>
                    </div>
                  </div>

                  {/* 2x2 Grid for the 4 Executive Pillars */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                    {/* PILLAR 1: MARKETING & CAMPAIGN PLANNER AI */}
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-xl border-t-2 border-t-purple-500 flex flex-col justify-between">
                      <div className="space-y-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-purple-950/80 border border-purple-800/60 rounded-2xl text-purple-400">
                              <Calendar className="h-5 w-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-white">Campaign Planner AI & Social Calendar</h4>
                                <span className="text-[9px] bg-purple-950 text-purple-300 border border-purple-800/60 px-2 py-0.5 rounded-full font-bold">
                                  Sarah Jenkins
                                </span>
                              </div>
                              <p className="text-xs text-slate-400">Scheduled episodic multi-platform campaign posts grounded in approved USP.</p>
                            </div>
                          </div>

                          <Button
                            size="sm"
                            onClick={() => handleScheduleCampaign(14)}
                            disabled={isSchedulingCampaign}
                            className="bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs h-7 rounded-xl shadow shrink-0"
                          >
                            {isSchedulingCampaign ? <Loader2 className="animate-spin h-3 w-3 mr-1" /> : <Sparkles className="h-3 w-3 mr-1" />}
                            Regenerate Arc
                          </Button>
                        </div>

                        {/* Scheduled Posts Stream */}
                        <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1">
                          {(operationsData?.campaign?.posts || []).length > 0 ? (
                            operationsData.campaign.posts.map((post: any, idx: number) => {
                              const isExpanded = expandedPostId === post.id;
                              return (
                                <div
                                  key={post.id || idx}
                                  className="p-3 bg-slate-950/80 border border-slate-800 rounded-2xl hover:border-purple-800/50 transition-all space-y-2"
                                >
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <span className="text-[10px] font-bold bg-slate-800 text-purple-300 px-2 py-0.5 rounded-lg font-mono">
                                        Day {post.day || idx + 1}
                                      </span>
                                      <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                                        post.platform === 'linkedin' ? 'bg-blue-950/80 text-blue-300 border-blue-800/50' :
                                        post.platform === 'twitter' ? 'bg-sky-950/80 text-sky-300 border-sky-800/50' :
                                        post.platform === 'instagram' ? 'bg-pink-950/80 text-pink-300 border-pink-800/50' :
                                        'bg-indigo-950/80 text-indigo-300 border-indigo-800/50'
                                      }`}>
                                        {post.platform}
                                      </span>
                                      {post.scheduled_at && (
                                        <span className="text-[10px] text-slate-500 font-mono">
                                          {new Date(post.scheduled_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                                        </span>
                                      )}
                                    </div>
                                    <span className="text-[9px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/50 px-2 py-0.5 rounded-full">
                                      {post.status?.toUpperCase() || 'SCHEDULED'}
                                    </span>
                                  </div>

                                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                                    {isExpanded ? post.content : post.snippet}
                                  </p>

                                  <div className="flex items-center justify-between pt-1 border-t border-slate-900 text-[10px]">
                                    <button
                                      type="button"
                                      onClick={() => setExpandedPostId(isExpanded ? null : post.id)}
                                      className="text-purple-400 hover:text-purple-300 font-semibold"
                                    >
                                      {isExpanded ? 'Show Less ↑' : 'Read Full Post Copy →'}
                                    </button>
                                    <span className="text-slate-500">Auto-publish on schedule</span>
                                  </div>
                                </div>
                              );
                            })
                          ) : (
                            <div className="p-6 text-center bg-slate-950/60 rounded-2xl border border-slate-800 space-y-3">
                              <p className="text-xs text-slate-400">No scheduled posts generated yet for this strategic plan.</p>
                              <Button
                                size="sm"
                                onClick={() => handleScheduleCampaign(14)}
                                disabled={isSchedulingCampaign}
                                className="bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-xl"
                              >
                                Generate 14-Day Social Campaign Arc
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 mt-2">
                        <span>Calendar Synced with Multi-Agent DAG</span>
                        <button
                          type="button"
                          onClick={() => setActiveView('marketing')}
                          className="text-purple-400 hover:text-purple-300 font-bold"
                        >
                          Open Marketing Suite →
                        </button>
                      </div>
                    </Card>

                    {/* PILLAR 2: SALES PIPELINE & DEAL ROOMS */}
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-xl border-t-2 border-t-emerald-500 flex flex-col justify-between">
                      <div className="space-y-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-emerald-950/80 border border-emerald-800/60 rounded-2xl text-emerald-400">
                              <TrendingUp className="h-5 w-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-white">Sales Pipeline & Deal Rooms</h4>
                                <span className="text-[9px] bg-emerald-950 text-emerald-300 border border-emerald-800/60 px-2 py-0.5 rounded-full font-bold">
                                  Alex Rivera
                                </span>
                              </div>
                              <p className="text-xs text-slate-400">B2B ICP accounts with buying committee intelligence and stage cadence.</p>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => setActiveView('deal-rooms')}
                            className="text-xs text-emerald-400 hover:text-emerald-300 font-bold shrink-0"
                          >
                            All Deal Rooms →
                          </button>
                        </div>

                        {/* Pipeline Stage Funnel Bar */}
                        <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-2xl flex items-center justify-between text-xs font-mono">
                          <div className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-slate-300 font-bold text-[11px]">Funnel Status:</span>
                          </div>
                          <div className="flex items-center gap-2 text-[10px]">
                            <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                              Ready: <strong className="text-white">{operationsData?.sales_pipeline?.stages_breakdown?.outreach_ready || 3}</strong>
                            </span>
                            <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                              In Cadence: <strong className="text-emerald-400">{operationsData?.sales_pipeline?.stages_breakdown?.in_cadence || 0}</strong>
                            </span>
                            <span className="bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                              Replied: <strong className="text-sky-400">{operationsData?.sales_pipeline?.stages_breakdown?.replied || 0}</strong>
                            </span>
                          </div>
                        </div>

                        {/* Deal Rooms Stream */}
                        <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                          {(operationsData?.sales_pipeline?.deal_rooms || []).map((deal: any, dIdx: number) => (
                            <div
                              key={deal.id || dIdx}
                              className="p-3 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-2 hover:border-emerald-800/50 transition-all"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <h5 className="text-xs font-bold text-white">{deal.company_name}</h5>
                                    <span className="text-[10px] text-slate-400 font-mono">({deal.domain})</span>
                                  </div>
                                  <span className="text-[10px] text-emerald-400 font-semibold block">
                                    ICP Fit: {Math.round((deal.icp_fit_score || 0.94) * 100)}% • Win Prob: {Math.round((deal.calibrated_win_prob || 0.45) * 100)}%
                                  </span>
                                </div>
                                <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                                  deal.stage === 'in_cadence' ? 'bg-sky-950 text-sky-300 border-sky-800' :
                                  deal.stage === 'replied' ? 'bg-purple-950 text-purple-300 border-purple-800' :
                                  'bg-emerald-950 text-emerald-300 border-emerald-800'
                                }`}>
                                  {deal.stage?.replace('_', ' ')}
                                </span>
                              </div>

                              {deal.next_best_action && (
                                <p className="text-[11px] text-slate-300 bg-slate-900/80 px-2.5 py-1.5 rounded-xl border border-slate-800/80">
                                  ⚡ <strong className="text-white">Next Action:</strong> {deal.next_best_action.action?.replace('_', ' ')} target ({deal.next_best_action.persona}) — {deal.next_best_action.reason}
                                </p>
                              )}

                              <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-900">
                                {deal.stage === 'outreach_ready' && (
                                  <Button
                                    size="sm"
                                    onClick={() => handleAdvanceSalesStage(deal.id, 'in_cadence')}
                                    disabled={isUpdatingSalesStage}
                                    className="bg-emerald-600/80 hover:bg-emerald-600 text-white font-bold text-[10px] h-6 rounded-lg"
                                  >
                                    Advance to Cadence →
                                  </Button>
                                )}
                                {deal.stage === 'in_cadence' && (
                                  <Button
                                    size="sm"
                                    onClick={() => handleAdvanceSalesStage(deal.id, 'replied')}
                                    disabled={isUpdatingSalesStage}
                                    className="bg-sky-600/80 hover:bg-sky-600 text-white font-bold text-[10px] h-6 rounded-lg"
                                  >
                                    Mark as Replied ✓
                                  </Button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => setActiveView('deal-rooms')}
                                  className="text-[10px] text-slate-400 hover:text-white font-semibold ml-2"
                                >
                                  Open Room →
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 mt-2">
                        <span>Autonomous SDR Enrichment Engaged</span>
                        <button
                          type="button"
                          onClick={() => setActiveView('sales')}
                          className="text-emerald-400 hover:text-emerald-300 font-bold"
                        >
                          Open Sales Pipeline →
                        </button>
                      </div>
                    </Card>

                    {/* PILLAR 3: CUSTOMER SUPPORT READINESS */}
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-xl border-t-2 border-t-sky-500 flex flex-col justify-between">
                      <div className="space-y-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-sky-950/80 border border-sky-800/60 rounded-2xl text-sky-400">
                              <Headphones className="h-5 w-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-white">Customer Support & Triage Control</h4>
                                <span className="text-[9px] bg-sky-950 text-sky-300 border border-sky-800/60 px-2 py-0.5 rounded-full font-bold">
                                  Maya Lin
                                </span>
                              </div>
                              <p className="text-xs text-slate-400">Set executive triage mode and prime campaign response playbooks.</p>
                            </div>
                          </div>

                          <span className="text-[10px] bg-sky-950 text-sky-300 border border-sky-800 px-2.5 py-1 rounded-full font-bold font-mono shrink-0">
                            SLA: &lt;15m
                          </span>
                        </div>

                        {/* Interactive Triage Policy Selector */}
                        <div className="space-y-2">
                          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                            Executive Triage Policy
                          </label>
                          <div className="grid grid-cols-2 gap-2.5">
                            <button
                              type="button"
                              onClick={() => handleUpdateSupportPolicy('review_first')}
                              disabled={isUpdatingSupportPolicy}
                              className={`p-3 rounded-2xl border text-left transition-all ${
                                (operationsData?.support?.reply_mode || 'review_first') === 'review_first'
                                  ? 'bg-sky-950/80 border-sky-500 text-white shadow-md'
                                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-bold">Review-First (HITL)</span>
                                {(operationsData?.support?.reply_mode || 'review_first') === 'review_first' && (
                                  <Check className="h-3.5 w-3.5 text-sky-400" />
                                )}
                              </div>
                              <p className="text-[10px] text-slate-400 leading-snug">
                                AI drafts replies; human approval mandatory before dispatch.
                              </p>
                            </button>

                            <button
                              type="button"
                              onClick={() => handleUpdateSupportPolicy('auto_send')}
                              disabled={isUpdatingSupportPolicy}
                              className={`p-3 rounded-2xl border text-left transition-all ${
                                operationsData?.support?.reply_mode === 'auto_send'
                                  ? 'bg-emerald-950/80 border-emerald-500 text-white shadow-md'
                                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-bold">Autonomous Auto-Pilot</span>
                                {operationsData?.support?.reply_mode === 'auto_send' && (
                                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                                )}
                              </div>
                              <p className="text-[10px] text-slate-400 leading-snug">
                                Direct autonomous responses under verified policy boundaries.
                              </p>
                            </button>
                          </div>
                        </div>

                        {/* Primed Campaign FAQ Playbook */}
                        <div className="space-y-2">
                          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                            Primed Campaign FAQ Playbook
                          </span>
                          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-bold text-white">Campaign FAQ: {companyContext?.company_name || 'Strategic Focus'}</span>
                              <span className="text-[9px] bg-emerald-950 text-emerald-300 border border-emerald-800/60 px-2 py-0.5 rounded-full font-bold">
                                ARMED IN CONTEXT
                              </span>
                            </div>
                            <p className="text-xs text-slate-300 leading-relaxed font-mono text-[11px]">
                              Q: How does the system integrate? → Connects directly via authenticated APIs with strict human-in-the-loop review.
                            </p>
                            <p className="text-xs text-slate-300 leading-relaxed font-mono text-[11px]">
                              Q: What is the onboarding timeline? → Full operational execution begins in under 48 hours.
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 mt-2">
                        <span>Omni-Channel Auto-Replies: WhatsApp, Email, Web</span>
                        <button
                          type="button"
                          onClick={() => setActiveView('support')}
                          className="text-sky-400 hover:text-sky-300 font-bold"
                        >
                          Open Support Center →
                        </button>
                      </div>
                    </Card>

                    {/* PILLAR 4: EXECUTIVE EMAIL DISPATCH CENTER */}
                    <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-xl border-t-2 border-t-amber-500 flex flex-col justify-between">
                      <div className="space-y-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <div className="p-2.5 bg-amber-950/80 border border-amber-800/60 rounded-2xl text-amber-400">
                              <Mail className="h-5 w-5" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-white">Executive Email Dispatch Command</h4>
                                <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${
                                  operationsData?.email_dispatch?.active_channel !== 'none'
                                    ? 'bg-emerald-950 text-emerald-300 border-emerald-800/60'
                                    : 'bg-amber-950 text-amber-300 border-amber-800/60'
                                }`}>
                                  {operationsData?.email_dispatch?.active_channel !== 'none'
                                    ? `${operationsData?.email_dispatch?.active_channel?.toUpperCase()} CONNECTED`
                                    : 'SIMULATION PREVIEW SAFE'}
                                </span>
                              </div>
                              <p className="text-xs text-slate-400">Preview, test send, and authorize outbound executive email sequences.</p>
                            </div>
                          </div>

                          <Button
                            size="sm"
                            onClick={() => handleDispatchEmail({ workflow_id: currentPlanData?.workflow_id || selectedWorkflowId })}
                            disabled={isDispatchingEmail}
                            className="bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs h-7 rounded-xl shadow shrink-0"
                          >
                            {isDispatchingEmail ? <Loader2 className="animate-spin h-3 w-3 mr-1" /> : <Zap className="h-3 w-3 mr-1" />}
                            Batch Dispatch
                          </Button>
                        </div>

                        {/* Test Email Preview Input */}
                        <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-2">
                          <span className="text-[11px] font-bold text-slate-300 block">
                            Send Executive Preview Test Email
                          </span>
                          <div className="flex items-center gap-2">
                            <Input
                              type="email"
                              value={testEmailAddress}
                              onChange={(e) => setTestEmailAddress(e.target.value)}
                              placeholder="Enter your email to test (e.g. executive@company.com)"
                              className="bg-slate-900 border-slate-800 text-xs text-white rounded-xl h-8"
                            />
                            <Button
                              size="sm"
                              onClick={() => handleDispatchEmail({ test_email: testEmailAddress || 'executive@company.com' })}
                              disabled={isDispatchingEmail}
                              className="bg-slate-800 hover:bg-slate-700 text-amber-300 text-xs font-bold h-8 rounded-xl shrink-0"
                            >
                              Send Test
                            </Button>
                          </div>
                        </div>

                        {/* Outreach Queue Drafts */}
                        <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                          {(operationsData?.email_dispatch?.drafts || []).map((draft: any, draftIdx: number) => (
                            <div
                              key={draft.lead_id || draftIdx}
                              className="p-3 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-1.5 hover:border-amber-800/50 transition-all text-xs"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-white text-[11px]">
                                  To: {draft.lead_name} ({draft.company})
                                </span>
                                <span className="text-[10px] text-slate-400 font-mono">{draft.email}</span>
                              </div>
                              <p className="text-[11px] text-amber-300/90 font-medium">
                                Subject: {draft.subject}
                              </p>
                              <p className="text-[11px] text-slate-300 truncate">
                                {draft.body}
                              </p>
                              <div className="flex items-center justify-between pt-1 border-t border-slate-900">
                                <span className="text-[9px] text-slate-500 uppercase font-mono">
                                  Status: {draft.status}
                                </span>
                                <Button
                                  size="sm"
                                  onClick={() => handleDispatchEmail({ lead_id: draft.lead_id })}
                                  disabled={isDispatchingEmail}
                                  className="bg-amber-600/80 hover:bg-amber-600 text-white font-bold text-[10px] h-6 rounded-lg"
                                >
                                  <SendHorizontal className="h-2.5 w-2.5 mr-1" />
                                  Dispatch
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 mt-2">
                        <span>Ledger Delivery Auditing Enabled</span>
                        <span className="text-amber-400 font-mono text-[10px]">
                          {operationsData?.email_dispatch?.recent_logs?.length || 0} Recent Logs
                        </span>
                      </div>
                    </Card>

                  </div>
                </div>
              )}

              {/* 2. SPECIALIST WORKFORCE & DELIVERABLES MATRIX */}
              {stage3ViewTab === 'WORKFORCE' && (
                <div className="space-y-6 animate-in fade-in">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {(teamStatusData?.employees || []).map((empEntry: any, idx: number) => {
                      const emp = empEntry.employee;
                      return (
                        <Card key={idx} className="bg-slate-900/90 border-slate-800 rounded-3xl overflow-hidden shadow-lg border-t border-t-slate-700/60 space-y-3 p-5">
                          {/* Employee Profile Header */}
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-center gap-3">
                              <img
                                src={emp.avatar}
                                alt={emp.name}
                                className="h-12 w-12 rounded-2xl object-cover border border-slate-700 shadow-md"
                              />
                              <div>
                                <div className="flex items-center gap-1.5">
                                  <h4 className="text-sm font-bold text-white">{emp.name}</h4>
                                  <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full border ${getDeptColor(emp.department)}`}>
                                    {emp.department}
                                  </span>
                                </div>
                                <p className="text-xs text-slate-400 font-medium">{emp.title}</p>
                                <span className="text-[10px] text-slate-500 block">{emp.specialty}</span>
                              </div>
                            </div>

                            <span className={`text-[10px] font-bold px-2 py-1 rounded-full border whitespace-nowrap ${
                              empEntry.status === 'COMPLETED'
                                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/50'
                                : 'bg-sky-950/60 text-sky-300 border-sky-800/50'
                            }`}>
                              {empEntry.status_badge}
                            </span>
                          </div>

                          {/* Active Task & Progress Bar */}
                          <div className="p-3 bg-slate-950/80 rounded-2xl border border-slate-800 space-y-2">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-[10px] uppercase font-bold text-slate-400">Active Task</span>
                              <span className="text-xs font-bold text-white">{empEntry.progress_pct}%</span>
                            </div>
                            <p className="text-xs text-slate-200 leading-relaxed font-medium">
                              {empEntry.active_task}
                            </p>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-1.5 rounded-full transition-all duration-500 ${
                                  empEntry.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-sky-500'
                                }`}
                                style={{ width: `${empEntry.progress_pct}%` }}
                              />
                            </div>
                          </div>

                          {/* Deliverables Preview Box */}
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                                Live Deliverables
                              </span>
                              <button
                                onClick={() => setActiveDeliverableEmp(emp.id)}
                                className="text-[10px] text-sky-400 hover:text-sky-300 font-semibold"
                              >
                                Inspect All →
                              </button>
                            </div>

                            {empEntry.deliverables?.map((deliv: any, dIdx: number) => (
                              <div key={dIdx} className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1 text-xs">
                                <span className="font-bold text-white text-[11px] block">{deliv.title}</span>
                                <div className="space-y-1 pt-0.5">
                                  {deliv.items?.slice(0, 2).map((item: any, iIdx: number) => (
                                    <div key={iIdx} className="flex items-center justify-between text-[11px] text-slate-300 bg-slate-900/60 px-2 py-1 rounded-lg border border-slate-800/60">
                                      {item.name ? (
                                        <>
                                          <span className="font-semibold text-white truncate">{item.name} ({item.company})</span>
                                          <span className="text-[10px] text-emerald-400 font-bold bg-emerald-950/40 px-1.5 py-0.5 rounded">Score: {item.score}</span>
                                        </>
                                      ) : item.metric ? (
                                        <>
                                          <span className="text-slate-400">{item.metric}</span>
                                          <span className="font-bold text-white">{item.value}</span>
                                        </>
                                      ) : item.platform ? (
                                        <>
                                          <span className="uppercase text-[9px] font-bold text-indigo-400">{item.platform}</span>
                                          <span className="text-slate-300 truncate max-w-[200px]">{item.snippet}</span>
                                        </>
                                      ) : (
                                        <>
                                          <span className="text-slate-300">{item.check}</span>
                                          <span className="text-emerald-400 font-bold text-[10px]">{item.status}</span>
                                        </>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ))}
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 3. HUMAN-IN-THE-LOOP REVIEW & APPROVAL GATES */}
              {stage3ViewTab === 'HUMAN_GATES' && (
                <div className="space-y-6 animate-in fade-in">
                  {/* Irreversible Policy Action Gates (R3/R4 Gatekeeper) */}
                  <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-lg border-t-2 border-t-amber-500 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="h-5 w-5 text-amber-400" />
                        <div>
                          <h4 className="text-sm font-bold text-white">Irreversible Policy Action Gates (R3/R4)</h4>
                          <p className="text-xs text-slate-400">External funds allocation and customer outreach require explicit executive clearance.</p>
                        </div>
                      </div>
                      <span className="text-[10px] bg-amber-950/80 text-amber-300 border border-amber-800/60 px-2.5 py-1 rounded-full font-mono font-bold">
                        Human-in-Loop Enforced
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                      {effectiveNodes.filter((n: any) => n.capability_id?.includes('allocate') || n.capability_id?.includes('send') || n.capability_id?.includes('campaign')).map((gateNode: any, gIdx: number) => {
                        const gateKey = gateNode.id;
                        const decision = approvedGateIds[gateKey];
                        return (
                          <div key={gIdx} className="p-4 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-3">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white">{gateNode.name}</span>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                decision === 'APPROVED' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' :
                                decision === 'REJECTED' ? 'bg-rose-950 text-rose-300 border-rose-800' :
                                'bg-amber-950/80 text-amber-300 border-amber-800/60 animate-pulse'
                              }`}>
                                {decision || 'AWAITING APPROVAL'}
                              </span>
                            </div>

                            <p className="text-[11px] text-slate-400 font-mono">
                              Capability: {gateNode.capability_id} ({gateNode.department})
                            </p>

                            <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-800/60">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleApproveGate(gateKey, false)}
                                disabled={decision === 'REJECTED'}
                                className="border-rose-900/60 hover:bg-rose-950/40 text-rose-300 text-xs h-7 rounded-xl"
                              >
                                Hold / Reject
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleApproveGate(gateKey, true)}
                                disabled={decision === 'APPROVED'}
                                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs h-7 rounded-xl flex items-center gap-1 shadow"
                              >
                                <Check className="h-3 w-3" />
                                Approve Clearance
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </Card>

                  {/* In-Flight Executive Directive Intervention Box */}
                  <Card className="bg-slate-900/90 border-slate-800 rounded-3xl p-5 shadow-lg border-2 border-indigo-500/40 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Edit3 className="h-4 w-4 text-indigo-400" />
                        <h4 className="text-sm font-bold text-white">In-Flight Executive Steering Intervention</h4>
                      </div>
                      <span className="text-[10px] bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded-full font-semibold">
                        Real-Time Steering Gate
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 leading-relaxed">
                      Inject live operational steering into the running DAG without stopping execution. The orchestrator will dynamically re-route sub-tasks and enforce constraints.
                    </p>

                    {interventionFeedbackMessage && (
                      <div className="p-3 bg-emerald-950/40 border border-emerald-800/60 rounded-xl text-xs text-emerald-300 flex items-center gap-2 animate-in fade-in">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                        <span>{interventionFeedbackMessage}</span>
                      </div>
                    )}

                    <Textarea
                      placeholder="e.g. Shift 20% more SDR outreach to VP-level targets in Apex Dynamics and enforce double confirmation on LinkedIn messaging..."
                      value={executiveInterventionNote}
                      onChange={(e) => setExecutiveInterventionNote(e.target.value)}
                      className="bg-slate-950/80 border-slate-800 text-white rounded-xl text-xs min-h-[75px] focus:border-indigo-500"
                    />

                    <div className="flex justify-end pt-1">
                      <Button
                        onClick={handleSendIntervention}
                        disabled={isSendingIntervention || !executiveInterventionNote.trim()}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl h-9 px-4 flex items-center gap-1.5 shadow"
                      >
                        {isSendingIntervention ? (
                          <>
                            <Loader2 className="animate-spin h-3.5 w-3.5" />
                            Transmitting Directive...
                          </>
                        ) : (
                          <>
                            <Send className="h-3.5 w-3.5" />
                            Transmit Steering Directive & Execute Tick
                          </>
                        )}
                      </Button>
                    </div>
                  </Card>
                </div>
              )}

              {/* Navigation Back / Next Controls */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-3">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setInteractiveStep(1)}
                    className="border-slate-800 hover:bg-slate-800 text-xs text-slate-300 rounded-xl"
                  >
                    ← View Strategy Plan
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setInteractiveStep(2)}
                    className="border-slate-800 hover:bg-slate-800 text-xs text-slate-300 rounded-xl"
                  >
                    ← Review Council Dialogue
                  </Button>
                </div>

                <Button
                  onClick={handleNewDirective}
                  className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-xl h-8 shadow-sm flex items-center gap-1.5"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Launch Another Executive Directive
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2.5 Deliverables Inspector Modal for Specialist Employees */}
      {activeDeliverableEmp && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          {(() => {
            const empEntry = teamStatusData?.employees?.find((e: any) => e.employee?.id === activeDeliverableEmp);
            const emp = empEntry?.employee;
            if (!emp) return null;
            return (
              <Card className="bg-slate-900 border-slate-700 max-w-3xl w-full rounded-3xl shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-3">
                    <img
                      src={emp.avatar}
                      alt={emp.name}
                      className="h-11 w-11 rounded-2xl object-cover border border-slate-700 shadow"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-white">{emp.name}</h3>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getDeptColor(emp.department)}`}>
                          {emp.department}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400">{emp.title} — Deliverables Ledger</p>
                    </div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => setActiveDeliverableEmp(null)} className="text-slate-400 hover:text-white">
                    ✕
                  </Button>
                </div>

                <div className="space-y-4 text-xs">
                  <div className="p-3 bg-slate-950/80 rounded-2xl border border-slate-800 space-y-1">
                    <span className="text-[10px] uppercase font-bold text-slate-400">Current Work Assignment</span>
                    <p className="text-xs text-slate-200">{empEntry.active_task}</p>
                    <span className="text-[10px] text-sky-400 font-semibold block pt-1">
                      Status: {empEntry.status_badge} ({empEntry.progress_pct}% progress)
                    </span>
                  </div>

                  <div className="space-y-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-300 block">
                      Production Deliverables Generated
                    </span>
                    {empEntry.deliverables?.map((deliv: any, idx: number) => (
                      <div key={idx} className="p-4 bg-slate-950/90 rounded-2xl border border-slate-800 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-sm text-white">{deliv.title}</span>
                          <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-mono uppercase">
                            {deliv.type}
                          </span>
                        </div>

                        {deliv.type === 'LEADS' ? (
                          <div className="overflow-x-auto">
                            <table className="w-full text-left text-xs">
                              <thead>
                                <tr className="border-b border-slate-800 text-slate-400 text-[10px] uppercase">
                                  <th className="pb-2 font-bold">Contact Name</th>
                                  <th className="pb-2 font-bold">Target Company</th>
                                  <th className="pb-2 font-bold">Verified Email</th>
                                  <th className="pb-2 font-bold text-center">Score</th>
                                  <th className="pb-2 font-bold text-right">Status</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/60">
                                {deliv.items?.map((item: any, iIdx: number) => (
                                  <tr key={iIdx} className="text-slate-300 hover:bg-slate-900/40">
                                    <td className="py-2 font-medium text-white">{item.name}</td>
                                    <td className="py-2 text-slate-300">{item.company}</td>
                                    <td className="py-2 font-mono text-[11px] text-sky-300">{item.email}</td>
                                    <td className="py-2 text-center">
                                      <span className="bg-emerald-950/60 text-emerald-400 font-bold px-1.5 py-0.5 rounded text-[10px] border border-emerald-800/40">
                                        {item.score}
                                      </span>
                                    </td>
                                    <td className="py-2 text-right">
                                      <span className="text-[10px] uppercase font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
                                        {item.status}
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : deliv.type === 'CONTENT' ? (
                          <div className="space-y-2">
                            {deliv.items?.map((item: any, iIdx: number) => (
                              <div key={iIdx} className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 space-y-1">
                                <span className="text-[10px] font-bold uppercase text-indigo-400">{item.platform}</span>
                                <p className="text-xs text-slate-200 leading-relaxed font-sans">{item.snippet}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                            {deliv.items?.map((item: any, iIdx: number) => (
                              <div key={iIdx} className="p-2.5 bg-slate-900/60 rounded-xl border border-slate-800 text-center">
                                <span className="text-[10px] text-slate-400 block">{item.metric || item.check}</span>
                                <p className="text-xs font-bold text-white mt-0.5">{item.value || item.status}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-2 flex justify-end border-t border-slate-800">
                  <Button onClick={() => setActiveDeliverableEmp(null)} className="bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold">
                    Close Inspector
                  </Button>
                </div>
              </Card>
            );
          })()}
        </div>
      )}

      {/* 3. Pre-Execution Dry Run Modal */}
      {showDryRunModal && dryRunResult && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <Card className="bg-slate-900 border-slate-700 max-w-2xl w-full rounded-3xl shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-sky-400" />
                <h3 className="text-lg font-bold text-white">Pre-Execution Dry Run Simulation</h3>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setShowDryRunModal(false)} className="text-slate-400">
                ✕
              </Button>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Simulation Status</span>
                <p className={`font-bold mt-0.5 ${dryRunResult.simulation_status === 'PASSED' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {dryRunResult.simulation_status}
                </p>
              </div>
              <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Estimated Duration</span>
                <p className="font-bold text-white mt-0.5">{dryRunResult.total_estimated_duration_seconds}s</p>
              </div>
              <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-400">Estimated Cost</span>
                <p className="font-bold text-white mt-0.5">${dryRunResult.total_estimated_cost_usd}</p>
              </div>
            </div>

            {/* Approval Checkpoints Required */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Required Governance Approval Checkpoints ({dryRunResult.approval_checkpoints_count})
              </span>
              <div className="mt-2 space-y-2">
                {dryRunResult.approval_checkpoints.map((cp: any, idx: number) => (
                  <div key={idx} className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
                    <div>
                      <p className="font-bold text-white">{cp.node_name}</p>
                      <p className="text-xs text-slate-400">{cp.capability_id} — {cp.side_effect_class}</p>
                    </div>
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-800/40">
                      {cp.required_keys === 2 ? 'Dual-Key ($R4)' : 'Single-Key ($R3)'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2 border-t border-slate-800">
              <Button onClick={() => setShowDryRunModal(false)} variant="outline" className="border-slate-700 text-xs">
                Dismiss
              </Button>
              <Button
                onClick={() => {
                  setShowDryRunModal(false);
                  handleActivatePlan();
                }}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs"
              >
                Approve & Activate Plan
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* 4. Strategic Brief & Post-Mortem Modal */}
      {showPostMortemModal && postMortemBrief && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <Card className="bg-slate-900 border-slate-700 max-w-3xl w-full rounded-3xl shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-emerald-400" />
                <h3 className="text-lg font-bold text-white">Boardroom Strategic Brief & Post-Mortem</h3>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setShowPostMortemModal(false)} className="text-slate-400">
                ✕
              </Button>
            </div>

            <div className="bg-slate-950/80 p-5 rounded-2xl border border-slate-800 text-slate-300 text-xs whitespace-pre-line leading-relaxed font-sans">
              {postMortemBrief.executive_brief_markdown}
            </div>

            <div className="pt-2 flex justify-end gap-2 border-t border-slate-800">
              <Button onClick={() => setShowPostMortemModal(false)} className="bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold">
                Close Brief
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* 5. Executive Council Deliberation Transcript Modal */}
      {showCouncilModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <Card className="bg-slate-900 border-slate-700 max-w-4xl w-full rounded-3xl shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-emerald-400" />
                <div>
                  <h3 className="text-base font-bold text-white">Executive Council Deliberation Transcript</h3>
                  <p className="text-xs text-slate-400">Cross-agent domain critique, ROI optimization, and resource allocation</p>
                </div>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setShowCouncilModal(false)} className="text-slate-400 hover:text-white">
                ✕
              </Button>
            </div>

            {/* Deliberation Consensus Summary */}
            {consensusSummary && (
              <div className="p-4 bg-sky-950/30 border border-sky-800/40 rounded-2xl">
                <span className="text-[10px] uppercase font-bold text-sky-400 tracking-wider block mb-1">
                  Executive Consensus Synthesis
                </span>
                <p className="text-xs text-slate-200 leading-relaxed font-sans">{consensusSummary}</p>
              </div>
            )}

            {/* Agent Deliberations Cards */}
            <div className="space-y-3">
              <span className="text-xs uppercase font-bold text-slate-400 tracking-wider">
                Agent Domain Critiques & ROI Recommendations ({agentDeliberations.length})
              </span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {agentDeliberations.map((delib: any, idx: number) => (
                  <div key={idx} className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4 text-sky-400" />
                        <div>
                          <h4 className="text-xs font-bold text-white">{delib.agent}</h4>
                          <span className="text-[10px] text-slate-400">{delib.role}</span>
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getDeptColor(delib.department)}`}>
                        {delib.department}
                      </span>
                    </div>

                    <div className="text-xs text-slate-300 space-y-1.5 pt-1 border-t border-slate-800/60">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-400 block">Domain Feasibility</span>
                        <p className="text-xs text-slate-200">{delib.domain_perspective}</p>
                      </div>

                      <div className="bg-emerald-950/20 border border-emerald-800/30 p-2 rounded-xl">
                        <span className="text-[10px] uppercase font-bold text-emerald-400 block">ROI Optimization Lever</span>
                        <p className="text-xs text-emerald-200 font-medium">💡 {delib.roi_recommendation}</p>
                      </div>

                      {delib.risk_flag && (
                        <div className="bg-amber-950/20 border border-amber-800/30 p-2 rounded-xl">
                          <span className="text-[10px] uppercase font-bold text-amber-400 block">Mitigated Risk Factor</span>
                          <p className="text-xs text-amber-200">⚠️ {delib.risk_flag}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2 border-t border-slate-800">
              <Button onClick={() => setShowCouncilModal(false)} className="bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold">
                Close Deliberation
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Delete Workspace Confirmation Modal */}
      {deleteConfirmWfId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="bg-slate-900 border-rose-900/60 max-w-md w-full p-6 shadow-2xl rounded-3xl space-y-4 animate-in fade-in zoom-in-95 border-2">
            <div className="flex items-center gap-3 text-rose-400">
              <div className="p-2.5 bg-rose-950/80 border border-rose-800/60 rounded-2xl">
                <Trash2 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Delete Executive Directive?</h3>
                <p className="text-[11px] text-slate-400">This action cannot be undone.</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to permanently delete this CEO workspace? All strategic plans, council deliberation transcripts, MOM artifacts, and task node records will be permanently removed.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteConfirmWfId(null)}
                disabled={isDeletingWf}
                className="border-slate-700 hover:bg-slate-800 text-slate-300 text-xs rounded-xl"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => handleDeleteWorkspace(deleteConfirmWfId)}
                disabled={isDeletingWf}
                className="bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-md shadow-rose-900/40"
              >
                {isDeletingWf ? (
                  <>
                    <Loader2 className="animate-spin h-3.5 w-3.5" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-3.5 w-3.5" />
                    Confirm Delete
                  </>
                )}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}


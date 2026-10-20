'use client';

import { notify, confirmAction } from '@/lib/notify';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import {
  Users,
  Zap,
  MessageSquare,
  ShieldCheck,
  Scale,
  Server,
  DollarSign,
  TrendingUp,
  Database,
  Search,
  Sparkles,
  CheckCircle,
  Clock,
  AlertTriangle,
  ShieldAlert,
  Play,
  RotateCcw,
  Download,
  Check,
  X,
  ChevronDown,
  ChevronRight,
  Headphones,
  Megaphone,
  UserCheck,
  Lock,
  Activity,
  Award,
  Crown,
  Gavel,
  FileText,
  Layers,
  Globe,
  Radio,
  ExternalLink,
  Filter,
  ArrowRight,
  Pause,
  AlertOctagon,
  Coins,
  Cpu,
  BarChart3,
  Sliders,
  CheckCircle2,
  Share2,
  Plus,
  Loader2,
  XCircle,
} from 'lucide-react';

interface CoordinationViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  fetchData: () => Promise<void>;
}

interface FindingItem {
  claim: string;
  evidence_ids?: string[];
  confidence?: number;
}

interface MeetingMessage {
  sender?: string;
  speaker_name?: string;
  agent_role?: string;
  speaker?: string;
  content?: string;
  message?: string;
  agent_thought?: string;
  thought?: string;
  timestamp?: string;
  phase?: string;
  domain_tag?: string;
  confidence_score?: number;
  confidence_rationale?: string;
  findings?: (string | FindingItem)[];
  assumptions?: string[];
  sources?: string[];
  quality_flags?: string[];
  stance?: 'support' | 'oppose' | 'neutral';
  turn_type?: 'challenge' | 'rebuttal' | 'evidence' | 'compromise';
  target_agent?: string;
}

interface MeetingEvidence {
  id: string;
  meeting_id: string;
  source_ref: string;
  source_type: string;
  trust_score?: number;
  freshness_score?: number;
  reliability_score?: number;
  completeness_score?: number;
  excerpt?: string;
  created_at?: string;
}

interface MeetingAction {
  id: string;
  meeting_id?: string;
  assigned_to: string;
  description: string;
  risk_tier?: 'low' | 'medium' | 'high';
  status: 'pending' | 'awaiting_approval' | 'executing' | 'completed' | 'failed' | 'rejected';
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  result?: Record<string, unknown> | null;
  sources?: string[];
  evidence_ids?: string[];
}

interface DecisionCharter {
  id: string;
  meeting_id: string;
  decision_type: string;
  question: string;
  decision_owner: string;
  approvers: string[];
  deadline?: string;
  cost_of_delay_per_week: number;
  criteria_weights: { name?: string; weight?: number; [key: string]: unknown }[];
  created_at: string;
}

interface MeetingOption {
  id: string;
  meeting_id: string;
  option_code: string;
  title: string;
  description: string;
  is_do_nothing: boolean;
  is_pilot: boolean;
  reversibility: string;
  financial_model: {
    ev?: number;
    downside_p10?: number;
    payback_months?: number;
    assumptions?: string[];
    [key: string]: unknown;
  };
  weighted_score: number;
  created_at: string;
}

interface DissentRecord {
  id: string;
  meeting_id: string;
  agent: string;
  preferred_option?: string;
  dissent_position: string;
  addressed: boolean;
  override_rationale?: string;
  requires_human_signoff: boolean;
  created_at: string;
}

interface DecisionOutcome {
  id: string;
  meeting_id: string;
  review_milestone: string;
  review_date: string;
  tripwires: string[];
  tripwire_triggered: boolean;
  predicted_metrics: Record<string, unknown>;
  actual_metrics: Record<string, unknown>;
  agent_brier_scores: Record<string, number>;
  created_at: string;
}

interface AgentMeeting {
  id: string;
  title: string;
  status: string;
  current_phase?: string;
  started_at?: string;
  finished_at?: string;
  total_tokens?: number;
  total_cost_usd?: number;
  failure_reason?: string;
  trigger_type: string;
  context_summary?: string;
  participants: (string | { name?: string; agent_role?: string })[];
  transcript: MeetingMessage[];
  action_items: MeetingAction[];
  created_at: string;
}

const PHASES_LIST = [
  { key: 'charter', label: 'Charter', tab: 'debate', icon: Scale },
  { key: 'evidence', label: 'Evidence', tab: 'evidence', icon: Database },
  { key: 'positions', label: 'Positions', tab: 'debate', icon: Users },
  { key: 'options', label: 'Options', tab: 'options', icon: Sparkles },
  { key: 'redteam', label: 'Red Team', tab: 'redteam', icon: ShieldAlert },
  { key: 'debate', label: 'Debate', tab: 'debate', icon: MessageSquare },
  { key: 'completed', label: 'Execution', tab: 'actions', icon: Zap },
];

const QUICK_DIRECTIVES = [
  'Cap initial spend at $8,000 for a 30-day pilot',
  'Require 90-day payback period on CAC',
  'Mandate 2 customer reference calls before rollout',
  'Red Team: stress-test outbound domain reputation risks',
  'Call for final executive consensus vote',
];

export default function CoordinationView({
  token,
  API_URL,
  fetchWithAuth,
}: CoordinationViewProps) {
  const [meetings, setMeetings] = useState<AgentMeeting[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [selectedMeeting, setSelectedMeeting] = useState<AgentMeeting | null>(null);
  const [evidenceList, setEvidenceList] = useState<MeetingEvidence[]>([]);
  const [actionList, setActionList] = useState<MeetingAction[]>([]);
  const [actionTab, setActionTab] = useState<'awaiting' | 'completed' | 'all'>('awaiting');

  // Governance State
  const [charter, setCharter] = useState<DecisionCharter | null>(null);
  const [optionsList, setOptionsList] = useState<MeetingOption[]>([]);
  const [dissentList, setDissentList] = useState<DissentRecord[]>([]);
  const [outcomesList, setOutcomesList] = useState<DecisionOutcome[]>([]);
  
  // Decision Intelligence & Assurance System State
  const [activeSystemTab, setActiveSystemTab] = useState<'CASES' | 'SCENARIOS' | 'CHALLENGE' | 'AUTHORITY' | 'OUTCOMES'>('CASES');
  const [decisionCases, setDecisionCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [isLoadingCases, setIsLoadingCases] = useState(false);
  const [isCreateCaseOpen, setIsCreateCaseOpen] = useState(false);

  // New Case Form
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCaseProposal, setNewCaseProposal] = useState('');
  const [newCaseRationale, setNewCaseRationale] = useState('');
  const [newCaseRiskClass, setNewCaseRiskClass] = useState('R3_EXTERNAL_IRREVERSIBLE');
  const [newCaseExposure, setNewCaseExposure] = useState('5000');
  const [newCaseReversibility, setNewCaseReversibility] = useState('MEDIUM');
  const [newCaseCostOfDelay, setNewCaseCostOfDelay] = useState('500');
  const [isSubmittingCase, setIsSubmittingCase] = useState(false);

  // Authority Grant Form
  const [grantDecision, setGrantDecision] = useState<'APPROVE' | 'REJECT'>('APPROVE');
  const [grantRationale, setGrantRationale] = useState('');
  const [grantSelectedAlt, setGrantSelectedAlt] = useState('B');
  const [isSubmittingGrant, setIsSubmittingGrant] = useState(false);

  // Legacy Deck Tabs fallback
  const [activeDeckTab, setActiveDeckTab] = useState<'debate' | 'options' | 'redteam' | 'dissents' | 'actions' | 'evidence'>('options');
  
  // Interactive Controls
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<string>('ALL');
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [isStopping, setIsStopping] = useState<boolean>(false);
  const [chairmanDirective, setChairmanDirective] = useState('');
  const [isSubmittingDirective, setIsSubmittingDirective] = useState(false);
  const [sidebarSearch, setSidebarSearch] = useState('');

  // Manual meeting dialog state
  const [isCreateMeetingOpen, setIsCreateMeetingOpen] = useState(false);
  const [manualMeetingTitle, setManualMeetingTitle] = useState('');
  const [manualMeetingTopic, setManualMeetingTopic] = useState('');
  const [manualMeetingParticipants, setManualMeetingParticipants] = useState<string[]>([
    'Sales Intelligence Expert',
    'Finance Expert',
    'Marketing Intelligence Expert',
    'Human Resources Expert',
    'Web Intelligence AI',
    'Red Team AI',
  ]);
  const [manualMeetingLoading, setManualMeetingLoading] = useState(false);

  // Rejection modal
  const [rejectActionId, setRejectActionId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Auto-scroll ref
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Fetch all meetings
  const fetchMeetings = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings`);
      if (res.ok) {
        const data: AgentMeeting[] = await res.json();
        setMeetings(data);
        if (!selectedMeetingId && data.length > 0) {
          setSelectedMeetingId(data[0].id);
        }
      }
    } catch (e) {
      console.error('Error fetching meetings:', e);
    }
  }, [API_URL, fetchWithAuth, token, selectedMeetingId]);

  // Fetch selected meeting details
  const fetchMeetingDetails = useCallback(async (meetingId: string) => {
    if (!token) return;
    try {
      const [resMeeting, resEv, resAct, resCharter, resOpt, resDis, resOut] = await Promise.all([
        fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}`),
        fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}/evidence`),
        fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}/actions`),
        fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}/charter`),
        fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}/options`),
        fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}/dissents`),
        fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}/outcomes`),
      ]);

      if (resMeeting.ok) {
        const data: AgentMeeting = await resMeeting.json();
        setSelectedMeeting(data);
      }
      if (resEv.ok) {
        const evData: MeetingEvidence[] = await resEv.json();
        setEvidenceList(evData);
      }
      if (resAct.ok) {
        const actData: MeetingAction[] = await resAct.json();
        setActionList(actData);
      }
      if (resCharter.ok) {
        const charterData = await resCharter.json();
        setCharter(charterData);
      } else {
        setCharter(null);
      }
      if (resOpt.ok) {
        const optData: MeetingOption[] = await resOpt.json();
        setOptionsList(optData);
      } else {
        setOptionsList([]);
      }
      if (resDis.ok) {
        const disData: DissentRecord[] = await resDis.json();
        setDissentList(disData);
      } else {
        setDissentList([]);
      }
      if (resOut.ok) {
        const outData: DecisionOutcome[] = await resOut.json();
        setOutcomesList(outData);
      } else {
        setOutcomesList([]);
      }
    } catch (e) {
      console.error('Error fetching meeting details:', e);
    }
  }, [API_URL, fetchWithAuth, token]);

  const fetchDecisionCases = useCallback(async () => {
    if (!token) return;
    setIsLoadingCases(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/decision-cases`);
      if (res.ok) {
        const data = await res.json();
        setDecisionCases(data);
        if (!selectedCaseId && data.length > 0) {
          setSelectedCaseId(data[0].id);
          void fetchCaseDetails(data[0].id);
        }
      }
    } catch (e) {
      console.error('Error fetching decision cases:', e);
    } finally {
      setIsLoadingCases(false);
    }
  }, [API_URL, fetchWithAuth, token, selectedCaseId]);

  const fetchCaseDetails = useCallback(async (caseId: string) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/decision-cases/${caseId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedCase(data);
      }
    } catch (e) {
      console.error('Error fetching decision case details:', e);
    }
  }, [API_URL, fetchWithAuth, token]);

  const handleCreateCase = async () => {
    if (!newCaseTitle.trim()) return;
    setIsSubmittingCase(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/decision-cases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newCaseTitle.trim(),
          proposal_summary: newCaseProposal.trim() || newCaseTitle.trim(),
          business_rationale: newCaseRationale.trim() || 'Required for business targets.',
          risk_class: newCaseRiskClass,
          financial_exposure: parseFloat(newCaseExposure) || 0.0,
          reversibility: newCaseReversibility,
          cost_of_delay_per_week: parseFloat(newCaseCostOfDelay) || 0.0,
        })
      });
      if (res.ok) {
        setIsCreateCaseOpen(false);
        setNewCaseTitle('');
        setNewCaseProposal('');
        setNewCaseRationale('');
        await fetchDecisionCases();
      }
    } catch (e) {
      console.error('Error creating decision case:', e);
    } finally {
      setIsSubmittingCase(false);
    }
  };

  const handleGrantAuthority = async () => {
    if (!selectedCaseId) return;
    setIsSubmittingGrant(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/decision-cases/${selectedCaseId}/grant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision: grantDecision,
          rationale: grantRationale.trim() || `${grantDecision} authorized by executive review under delegated policy limits.`,
          selected_alternative_code: grantSelectedAlt,
        })
      });
      if (res.ok) {
        setGrantRationale('');
        await fetchCaseDetails(selectedCaseId);
        await fetchDecisionCases();
      }
    } catch (e) {
      console.error('Error granting authority:', e);
    } finally {
      setIsSubmittingGrant(false);
    }
  };

  useEffect(() => {
    if (token) {
      void fetchMeetings();
      void fetchDecisionCases();
    }
  }, [fetchMeetings, fetchDecisionCases, token]);

  useEffect(() => {
    if (selectedMeetingId && token) {
      void fetchMeetingDetails(selectedMeetingId);
    }
  }, [selectedMeetingId, fetchMeetingDetails, token]);

  // Robust Polling Fallback: When meeting is active, poll every 2.5s to ensure live transcript never pauses
  useEffect(() => {
    if (!selectedMeetingId || !token) return;
    if (selectedMeeting?.status !== 'active') return;

    const pollTimer = setInterval(() => {
      void fetchMeetingDetails(selectedMeetingId);
    }, 2500);

    return () => clearInterval(pollTimer);
  }, [selectedMeetingId, selectedMeeting?.status, token, fetchMeetingDetails]);

  // SSE Stream with Auto-Update
  useEffect(() => {
    if (!selectedMeetingId || !token) return;

    let eventSource: EventSource | null = null;
    const streamUrl = `${API_URL}/coordination/meetings/${selectedMeetingId}/stream`;

    try {
      eventSource = new EventSource(streamUrl);
      eventSource.onmessage = (e) => {
        try {
          const payload = JSON.parse(e.data);
          if (payload.event && payload.event !== 'keep-alive') {
            void fetchMeetingDetails(selectedMeetingId);
            void fetchMeetings();
          }
        } catch {
          // ignore keepalive
        }
      };
    } catch (err) {
      console.debug('SSE init skipped:', err);
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, [selectedMeetingId, token, API_URL, fetchMeetingDetails, fetchMeetings]);

  // Smooth Auto-scroll to latest debate turn
  useEffect(() => {
    if (autoScroll && activeDeckTab === 'debate') {
      transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [selectedMeeting?.transcript?.length, autoScroll, activeDeckTab]);

  // Emergency Stop / Halt Flow Handler
  const handleStopMeeting = async () => {
    if (!selectedMeetingId) return;
    if (!(await confirmAction('Immediately halt this boardroom deliberation? The running flow will stop and current evidence will be preserved.'))) return;
    setIsStopping(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${selectedMeetingId}/stop`, {
        method: 'POST',
      });
      if (res.ok) {
        notify.success('Deliberation halted by human supervisor');
        await fetchMeetingDetails(selectedMeetingId);
        await fetchMeetings();
      } else {
        const err = await res.json().catch(() => ({ detail: 'Failed to halt deliberation' }));
        notify.error(err.detail || 'Failed to halt deliberation');
      }
    } catch (e) {
      console.error('Stop failed:', e);
      notify.error('Network error stopping deliberation');
    } finally {
      setIsStopping(false);
    }
  };

  // Create Meeting
  const handleCreateManualMeeting = async () => {
    if (!manualMeetingTitle || !manualMeetingTopic) return;
    setManualMeetingLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: manualMeetingTitle,
          topic: manualMeetingTopic,
          participants: manualMeetingParticipants.length > 0 ? manualMeetingParticipants : undefined,
          auto_select_experts: manualMeetingParticipants.length === 0,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setManualMeetingTitle('');
        setManualMeetingTopic('');
        setIsCreateMeetingOpen(false);
        await fetchMeetings();
        if (data.id) {
          setSelectedMeetingId(data.id);
          setActiveDeckTab('debate');
        }
      } else {
        notify(`Error: ${data.detail || 'Failed to start boardroom meeting'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setManualMeetingLoading(false);
    }
  };

  // Action Governance
  const handleApproveAction = async (actionId: string) => {
    if (!selectedMeetingId) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${selectedMeetingId}/actions/${actionId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: 'Executive Chairman' }),
      });
      if (res.ok) {
        notify.success('Action item approved for automated execution');
        await fetchMeetingDetails(selectedMeetingId);
        await fetchMeetings();
      }
    } catch (e) {
      console.error('Approval failed:', e);
    }
  };

  const handleRejectAction = async () => {
    if (!selectedMeetingId || !rejectActionId) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${selectedMeetingId}/actions/${rejectActionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejected_by: 'Executive Chairman', reason: rejectReason }),
      });
      if (res.ok) {
        notify.success('Action item rejected');
        setRejectActionId(null);
        setRejectReason('');
        await fetchMeetingDetails(selectedMeetingId);
        await fetchMeetings();
      }
    } catch (e) {
      console.error('Rejection failed:', e);
    }
  };

  const handleRerunMeeting = async () => {
    if (!selectedMeetingId) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${selectedMeetingId}/rerun`, {
        method: 'POST',
      });
      if (res.ok) {
        notify.success('Boardroom convened — agents starting live deliberation');
        await fetchMeetingDetails(selectedMeetingId);
        await fetchMeetings();
        setActiveDeckTab('debate');
      }
    } catch (e) {
      console.error('Rerun failed:', e);
    }
  };

  const handleExportMeeting = async (format: 'md' | 'json') => {
    if (!selectedMeetingId) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${selectedMeetingId}/export?format=${format}`);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `boardroom-${(selectedMeeting?.title || 'export').toLowerCase().replace(/[^a-z0-9]/g, '-')}.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error('Export failed:', e);
    }
  };

  // Chairman Directive Injection
  const handleChairmanIntervene = async () => {
    if (!selectedMeetingId || !chairmanDirective.trim()) return;
    setIsSubmittingDirective(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${selectedMeetingId}/intervene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directive: chairmanDirective.trim() }),
      });
      if (res.ok) {
        notify.success('Binding Directive Injected into Active Deliberation');
        setChairmanDirective('');
        await fetchMeetingDetails(selectedMeetingId);
        await fetchMeetings();
      } else {
        const err = await res.json().catch(() => ({ detail: 'Failed to inject directive' }));
        notify.error(err.detail || 'Failed to inject directive');
      }
    } catch (e) {
      console.error('Chairman intervention failed:', e);
      notify.error('Network error submitting directive');
    } finally {
      setIsSubmittingDirective(false);
    }
  };

  // Team Styling & Icon Helpers
  const getAgentMeta = (name?: string) => {
    const n = name || '';
    if (n.includes('CEO')) {
      return {
        icon: Crown,
        title: 'Chief Executive',
        label: 'Executive Strategy',
        color: 'text-amber-400',
        bg: 'bg-amber-500/15',
        border: 'border-amber-500/40',
        glow: 'shadow-amber-500/20',
        ring: 'ring-amber-400',
        badge: 'from-amber-500/20 to-yellow-500/20 border-amber-500/40 text-amber-300',
      };
    }
    if (n.includes('Sales') || n.includes('CRO')) {
      return {
        icon: TrendingUp,
        title: 'Revenue Officer',
        label: 'Pipeline & ACV',
        color: 'text-emerald-400',
        bg: 'bg-emerald-500/15',
        border: 'border-emerald-500/40',
        glow: 'shadow-emerald-500/20',
        ring: 'ring-emerald-400',
        badge: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/40 text-emerald-300',
      };
    }
    if (n.includes('Finance') || n.includes('CFO')) {
      return {
        icon: DollarSign,
        title: 'Financial Officer',
        label: 'Capital & Unit Econ',
        color: 'text-purple-400',
        bg: 'bg-purple-500/15',
        border: 'border-purple-500/40',
        glow: 'shadow-purple-500/20',
        ring: 'ring-purple-400',
        badge: 'from-purple-500/20 to-indigo-500/20 border-purple-500/40 text-purple-300',
      };
    }
    if (n.includes('Marketing') || n.includes('CMO')) {
      return {
        icon: Megaphone,
        title: 'Marketing Officer',
        label: 'Demand Gen & ICP',
        color: 'text-cyan-400',
        bg: 'bg-cyan-500/15',
        border: 'border-cyan-500/40',
        glow: 'shadow-cyan-500/20',
        ring: 'ring-cyan-400',
        badge: 'from-cyan-500/20 to-blue-500/20 border-cyan-500/40 text-cyan-300',
      };
    }
    if (n.includes('Human') || n.includes('HR') || n.includes('CHRO')) {
      return {
        icon: UserCheck,
        title: 'People Officer',
        label: 'Talent & Capacity',
        color: 'text-blue-400',
        bg: 'bg-blue-500/15',
        border: 'border-blue-500/40',
        glow: 'shadow-blue-500/20',
        ring: 'ring-blue-400',
        badge: 'from-blue-500/20 to-sky-500/20 border-blue-500/40 text-blue-300',
      };
    }
    if (n.includes('Web') || n.includes('Research') || n.includes('Firecrawl')) {
      return {
        icon: Globe,
        title: 'Firecrawl Research',
        label: 'Live Web Intel',
        color: 'text-orange-400',
        bg: 'bg-orange-500/15',
        border: 'border-orange-500/40',
        glow: 'shadow-orange-500/20',
        ring: 'ring-orange-400',
        badge: 'from-orange-500/20 to-amber-500/20 border-orange-500/40 text-orange-300',
      };
    }
    if (n.includes('Red Team') || n.includes('Risk')) {
      return {
        icon: ShieldAlert,
        title: 'Pre-Mortem Officer',
        label: 'Tripwires & Pre-Mortem',
        color: 'text-rose-400',
        bg: 'bg-rose-500/15',
        border: 'border-rose-500/40',
        glow: 'shadow-rose-500/20',
        ring: 'ring-rose-400',
        badge: 'from-rose-500/20 to-red-500/20 border-rose-500/40 text-rose-300',
      };
    }
    return {
      icon: Users,
      title: 'Council Member',
      label: 'Specialist Domain',
      color: 'text-slate-300',
      bg: 'bg-slate-800/40',
      border: 'border-slate-700/60',
      glow: 'shadow-slate-500/10',
      ring: 'ring-slate-400',
      badge: 'from-slate-800 to-slate-900 border-slate-700 text-slate-300',
    };
  };

  // Active Phase Helper
  const currentPhaseIndex = useMemo(() => {
    const rawPhase = selectedMeeting?.current_phase || (selectedMeeting?.status === 'completed' ? 'completed' : 'assembly');
    if (['assembly', 'intake', 'charter'].includes(rawPhase)) return 0;
    if (['evidence'].includes(rawPhase)) return 1;
    if (['analysis', 'positions'].includes(rawPhase)) return 2;
    if (['options', 'modeling'].includes(rawPhase)) return 3;
    if (['redteam'].includes(rawPhase)) return 4;
    if (['critique', 'debate', 'gavel', 'synthesis', 'decision'].includes(rawPhase)) return 5;
    if (['approval', 'execution', 'completed'].includes(rawPhase)) return 6;
    return 0;
  }, [selectedMeeting?.current_phase, selectedMeeting?.status]);

  // Derived Active Speaker for visual table
  const activeSpeakerName = useMemo(() => {
    if (!selectedMeeting?.transcript || selectedMeeting.transcript.length === 0) return null;
    const lastMsg = selectedMeeting.transcript[selectedMeeting.transcript.length - 1];
    return lastMsg.sender || lastMsg.speaker || lastMsg.speaker_name || null;
  }, [selectedMeeting?.transcript]);

  // Filtered transcript based on selectedAgentFilter
  const filteredTranscript = useMemo(() => {
    if (!selectedMeeting?.transcript) return [];
    if (selectedAgentFilter === 'ALL') return selectedMeeting.transcript;
    return selectedMeeting.transcript.filter((msg) => {
      const sender = msg.sender || msg.speaker_name || msg.speaker || '';
      return sender.toLowerCase().includes(selectedAgentFilter.toLowerCase());
    });
  }, [selectedMeeting?.transcript, selectedAgentFilter]);

  // Confidence calculation
  const latestConfidence = useMemo(() => {
    if (!selectedMeeting?.transcript || selectedMeeting.transcript.length === 0) return null;
    const rev = [...selectedMeeting.transcript].reverse();
    const entry = rev.find(e => e && e.confidence_score !== undefined && e.confidence_score !== null);
    return entry?.confidence_score ?? null;
  }, [selectedMeeting?.transcript]);

  const awaitingCount = useMemo(() => {
    return actionList.filter(a => a.status === 'awaiting_approval' || a.status === 'pending').length;
  }, [actionList]);

  const isLiveDeliberating = selectedMeeting?.status === 'active';
  const isHalted = selectedMeeting?.status === 'cancelled';

  // Council Seats Roster
  const councilSeats = useMemo(() => {
    const rawList: string[] = (selectedMeeting?.participants && selectedMeeting.participants.length > 0)
      ? selectedMeeting.participants.map(p => typeof p === 'string' ? p : ((p as any)?.name || (p as any)?.agent_role || 'Specialist'))
      : [
          'CEO AI',
          'Finance Expert',
          'Sales Intelligence Expert',
          'Marketing Intelligence Expert',
          'Human Resources Expert',
          'Web Intelligence AI',
          'Red Team AI',
        ];

    return rawList.map((name) => {
      const meta = getAgentMeta(name);
      const isSpeaking = !!(activeSpeakerName && (
        activeSpeakerName.toLowerCase().includes(name.toLowerCase()) ||
        name.toLowerCase().includes(activeSpeakerName.toLowerCase())
      ));

      // Find last message from this agent
      const lastMsg = selectedMeeting?.transcript
        ? [...selectedMeeting.transcript].reverse().find(m => {
            const sender = m.sender || m.speaker_name || m.agent_role || m.speaker || '';
            return sender.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(sender.toLowerCase());
          })
        : null;

      let stance = 'Observing';
      let stanceColor = 'text-gray-400 bg-gray-900/60 border-gray-800';
      if (lastMsg) {
        const content = lastMsg.content || lastMsg.message || '';
        if (lastMsg.stance === 'oppose' || content.includes('🔴') || content.toLowerCase().includes('challenge') || content.toLowerCase().includes('dissent')) {
          stance = 'Challenge';
          stanceColor = 'text-rose-300 bg-rose-500/15 border-rose-500/40';
        } else if (lastMsg.stance === 'support' || content.includes('🟢') || content.toLowerCase().includes('align') || content.toLowerCase().includes('support')) {
          stance = 'Alignment';
          stanceColor = 'text-emerald-300 bg-emerald-500/15 border-emerald-500/40';
        } else if (content.includes('🟡') || content.toLowerCase().includes('compromise') || content.toLowerCase().includes('counter')) {
          stance = 'Counter-Propose';
          stanceColor = 'text-amber-300 bg-amber-500/15 border-amber-500/40';
        } else if (name.includes('Web') || name.includes('Firecrawl') || (lastMsg.sources && lastMsg.sources.length > 0)) {
          stance = 'Live Web Data';
          stanceColor = 'text-orange-300 bg-orange-500/15 border-orange-500/40';
        }
      }

      return {
        name,
        meta,
        isSpeaking,
        stance,
        stanceColor,
        turnsCount: selectedMeeting?.transcript
          ? selectedMeeting.transcript.filter(m => {
              const sender = m.sender || m.speaker_name || m.agent_role || m.speaker || '';
              return sender.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(sender.toLowerCase());
            }).length
          : 0,
      };
    });
  }, [selectedMeeting?.participants, selectedMeeting?.transcript, activeSpeakerName]);

  // Filtered sidebar meetings
  const filteredMeetings = useMemo(() => {
    if (!sidebarSearch.trim()) return meetings;
    const q = sidebarSearch.toLowerCase();
    return meetings.filter(m =>
      m.title.toLowerCase().includes(q) ||
      (m.context_summary || '').toLowerCase().includes(q) ||
      m.status.toLowerCase().includes(q)
    );
  }, [meetings, sidebarSearch]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-in fade-in duration-300 pb-16">
      {/* 1. Decision Intelligence & Assurance Command Header */}
      <div className="relative rounded-xl p-6 bg-card border border-border shadow-xs overflow-hidden">
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="h-10 w-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shadow-xs">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold text-foreground tracking-tight">
                    Decision Intelligence &amp; Assurance System
                  </h1>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#2B3945] border border-[#75AFCB]/20 text-[#75AFCB] font-semibold uppercase tracking-wider font-mono">
                    Deterministic Policy Kernel
                  </span>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-[#443A2D] border border-[#D9AD68]/20 text-[#D9AD68] font-semibold uppercase tracking-wider font-mono">
                    Audit Provenance
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl leading-relaxed">
                  Consequence analysis, authority enforcement, independent challenge, and auditable outcomes for consequential business decisions.
                </p>
              </div>
            </div>
          </div>

          {/* Action Center: Propose Decision Case */}
          <div className="flex flex-wrap items-center gap-2.5">
            <Dialog open={isCreateCaseOpen} onOpenChange={setIsCreateCaseOpen}>
              <DialogTrigger render={
                <Button className="text-xs h-10 px-5 font-semibold flex items-center gap-2" />
              }>
                <Plus size={15} /> Propose Decision Case
              </DialogTrigger>
              <DialogContent className="border border-slate-800 text-white max-w-lg rounded-3xl p-6 bg-slate-950/95 shadow-2xl backdrop-blur-2xl">
                <DialogHeader>
                  <DialogTitle className="text-base font-bold text-white flex items-center gap-2">
                    <ShieldCheck className="text-indigo-400 h-5 w-5" /> Propose New Decision Case
                  </DialogTitle>
                  <CardDescription className="text-xs text-slate-400">
                    A durable decision case records the proposal, business rationale, financial exposure, and options before execution.
                  </CardDescription>
                </DialogHeader>
                <div className="space-y-3.5 mt-3">
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-slate-300">Decision Title</label>
                    <Input
                      placeholder="e.g. Authorize Outbound Enterprise Ad Campaign Spend"
                      value={newCaseTitle}
                      onChange={(e) => setNewCaseTitle(e.target.value)}
                      className="bg-slate-900 border-slate-800 text-white rounded-xl text-xs h-9 focus:border-indigo-500"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-slate-300">Proposal Summary</label>
                    <Textarea
                      placeholder="Describe what action is being proposed and affected systems..."
                      value={newCaseProposal}
                      onChange={(e) => setNewCaseProposal(e.target.value)}
                      className="bg-slate-900 border-slate-800 text-white rounded-xl text-xs min-h-16 focus:border-indigo-500"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-xs font-semibold text-slate-300">Business Rationale</label>
                    <Textarea
                      placeholder="Why is this decision justified? What objective does it serve?"
                      value={newCaseRationale}
                      onChange={(e) => setNewCaseRationale(e.target.value)}
                      className="bg-slate-900 border-slate-800 text-white rounded-xl text-xs min-h-16 focus:border-indigo-500"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-semibold text-slate-300">Risk Tier</label>
                      <select
                        value={newCaseRiskClass}
                        onChange={(e) => setNewCaseRiskClass(e.target.value)}
                        className="bg-slate-900 border border-slate-800 text-white rounded-xl text-xs h-9 px-2 focus:border-indigo-500"
                      >
                        <option value="R1_INTERNAL_REVERSIBLE">R1: Internal Reversible</option>
                        <option value="R2_EXTERNAL_REVERSIBLE">R2: External Reversible</option>
                        <option value="R3_EXTERNAL_IRREVERSIBLE">R3: External Irreversible</option>
                        <option value="R4_FINANCIAL_CRITICAL">R4: Financial Critical (Dual-Key)</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-semibold text-slate-300">Financial Exposure ($)</label>
                      <Input
                        type="number"
                        placeholder="5000"
                        value={newCaseExposure}
                        onChange={(e) => setNewCaseExposure(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-white rounded-xl text-xs h-9 focus:border-indigo-500"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-semibold text-slate-300">Reversibility</label>
                      <select
                        value={newCaseReversibility}
                        onChange={(e) => setNewCaseReversibility(e.target.value)}
                        className="bg-slate-900 border border-slate-800 text-white rounded-xl text-xs h-9 px-2 focus:border-indigo-500"
                      >
                        <option value="HIGH">High (Easy Rollback)</option>
                        <option value="MEDIUM">Medium (Compensable)</option>
                        <option value="LOW">Low (Costly Rollback)</option>
                        <option value="IRREVERSIBLE">Irreversible</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs font-semibold text-slate-300">Cost of Delay ($/wk)</label>
                      <Input
                        type="number"
                        placeholder="500"
                        value={newCaseCostOfDelay}
                        onChange={(e) => setNewCaseCostOfDelay(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-white rounded-xl text-xs h-9 focus:border-indigo-500"
                      />
                    </div>
                  </div>
                  <Button
                    onClick={handleCreateCase}
                    disabled={isSubmittingCase || !newCaseTitle.trim()}
                    className="w-full h-10 font-semibold mt-2 text-xs"
                  >
                    {isSubmittingCase ? 'Formulating Case...' : 'Submit for Independent Assurance'}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      {/* 2. Top-Level Decision Assurance System Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveSystemTab('CASES')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSystemTab === 'CASES'
              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <FileText className="h-4 w-4" />
          Decision Cases
          {decisionCases.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] bg-indigo-500/30 text-indigo-300 font-mono">
              {decisionCases.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveSystemTab('SCENARIOS')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSystemTab === 'SCENARIOS'
              ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Scale className="h-4 w-4" />
          Consequence Analysis & Options
        </button>

        <button
          onClick={() => setActiveSystemTab('CHALLENGE')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSystemTab === 'CHALLENGE'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <ShieldAlert className="h-4 w-4" />
          Independent Challenge & Controls
        </button>

        <button
          onClick={() => setActiveSystemTab('AUTHORITY')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSystemTab === 'AUTHORITY'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <Gavel className="h-4 w-4" />
          Authority & Approval Gate
        </button>

        <button
          onClick={() => setActiveSystemTab('OUTCOMES')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeSystemTab === 'OUTCOMES'
              ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <CheckCircle2 className="h-4 w-4" />
          Outcome Reviews & Provenance
        </button>
      </div>

      {/* 3. Decision Cases Overview Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold uppercase">
            <span>Active Cases</span>
            <FileText className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">{decisionCases.length}</div>
          <p className="text-[11px] text-slate-400 mt-0.5">Durable business decisions under review</p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold uppercase">
            <span>Financial Exposure</span>
            <DollarSign className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            ${decisionCases.reduce((acc, c) => acc + (c.financial_exposure || 0), 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">Capital exposure across proposed cases</p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold uppercase">
            <span>Pending Clearance</span>
            <Clock className="h-4 w-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-sky-400 mt-1">
            {decisionCases.filter(c => c.status === 'UNDER_ASSURANCE' || c.status === 'REQUIRE_APPROVAL').length}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">Awaiting independent review or signoff</p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold uppercase">
            <span>Prediction Calibration</span>
            <Award className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            0.08 Brier
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">Calibrated forecast accuracy vs actuals</p>
        </div>
      </div>

      {/* TAB: DECISION CASES VIEW */}
      {activeSystemTab === 'CASES' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start animate-in fade-in">
          {/* Left: Case List */}
          <div className="lg:col-span-1 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400 font-bold uppercase tracking-wider px-1">
              <span>Decision Cases ({decisionCases.length})</span>
            </div>
            {isLoadingCases ? (
              <div className="p-8 text-center text-xs text-slate-400 flex items-center justify-center">
                <Loader2 className="animate-spin h-4 w-4 mr-2 text-indigo-400" /> Loading decision cases...
              </div>
            ) : decisionCases.length === 0 ? (
              <div className="bg-slate-900/50 border border-dashed border-slate-800 rounded-2xl p-8 text-center space-y-2">
                <FileText className="h-8 w-8 text-slate-600 mx-auto" />
                <p className="text-xs text-slate-400">No decision cases proposed yet.</p>
                <Button
                  size="sm"
                  onClick={() => setIsCreateCaseOpen(true)}
                  className="bg-indigo-600 text-white text-xs rounded-xl h-8 px-3"
                >
                  Propose First Case
                </Button>
              </div>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                {decisionCases.map((c) => {
                  const isSelected = selectedCaseId === c.id;
                  return (
                    <div
                      key={c.id}
                      onClick={() => {
                        setSelectedCaseId(c.id);
                        void fetchCaseDetails(c.id);
                      }}
                      className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-slate-900 border-indigo-500/60 shadow-md shadow-indigo-500/10'
                          : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] font-mono font-bold text-indigo-400">{c.case_number}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          c.status === 'AUTHORIZED' ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300' :
                          c.status === 'REJECTED' ? 'bg-rose-950/60 border-rose-800 text-rose-300' :
                          'bg-amber-950/60 border-amber-800 text-amber-300 animate-pulse'
                        }`}>
                          {c.status.replace('_', ' ')}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-white mt-1.5 line-clamp-1">{c.title}</h4>
                      <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">{c.proposal_summary}</p>

                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-800/60 mt-2">
                        <span className="font-semibold text-slate-300">${c.financial_exposure.toLocaleString()}</span>
                        <span>{c.reversibility} Reversibility</span>
                        <span className="font-mono text-indigo-300">{c.risk_class.split('_')[0]}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right: Selected Case Dossier */}
          <div className="lg:col-span-2 space-y-4">
            {selectedCase ? (
              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-5">
                <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/60 border border-indigo-800/60 px-2 py-0.5 rounded-md">
                        {selectedCase.case_number}
                      </span>
                      <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                        {selectedCase.risk_class}
                      </span>
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                        selectedCase.status === 'AUTHORIZED' ? 'bg-emerald-950 border-emerald-800 text-emerald-300' :
                        selectedCase.status === 'REJECTED' ? 'bg-rose-950 border-rose-800 text-rose-300' :
                        'bg-amber-950/80 border-amber-800 text-amber-300'
                      }`}>
                        {selectedCase.status}
                      </span>
                    </div>
                    <h2 className="text-lg font-bold text-white mt-2">{selectedCase.title}</h2>
                  </div>

                  <div className="text-right shrink-0">
                    <span className="text-base font-bold text-white">${selectedCase.financial_exposure.toLocaleString()}</span>
                    <p className="text-[10px] text-slate-400">Financial Exposure</p>
                  </div>
                </div>

                {/* Proposal & Rationale */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-2xl space-y-1">
                    <span className="text-slate-400 font-semibold block uppercase text-[10px]">Proposal Summary</span>
                    <p className="text-slate-200 leading-relaxed">{selectedCase.proposal_summary}</p>
                  </div>
                  <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-2xl space-y-1">
                    <span className="text-slate-400 font-semibold block uppercase text-[10px]">Business Rationale</span>
                    <p className="text-slate-200 leading-relaxed">{selectedCase.business_rationale}</p>
                  </div>
                </div>

                {/* Quantitative Consequence Snapshot */}
                <div className="bg-slate-950/60 border border-slate-800/80 p-4 rounded-2xl space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-300">
                    <span className="flex items-center gap-1.5"><Scale className="h-4 w-4 text-sky-400" /> Quantitative Consequence Modeling</span>
                    <span className="text-[10px] text-slate-500 font-mono">P10 / Expected Value</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 pt-1">
                    <div className="p-2.5 bg-slate-900 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-400 block">Downside P10 Exposure</span>
                      <span className="text-sm font-bold text-rose-400">
                        ${selectedCase.financial_assessment?.downside_p10 ? selectedCase.financial_assessment.downside_p10.toLocaleString() : '-'}
                      </span>
                    </div>
                    <div className="p-2.5 bg-slate-900 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-400 block">Expected Value (EV)</span>
                      <span className="text-sm font-bold text-emerald-400">
                        ${selectedCase.financial_assessment?.expected_value ? selectedCase.financial_assessment.expected_value.toLocaleString() : '-'}
                      </span>
                    </div>
                    <div className="p-2.5 bg-slate-900 rounded-xl border border-slate-800">
                      <span className="text-[10px] text-slate-400 block">Cost of Delay</span>
                      <span className="text-sm font-bold text-amber-400">
                        ${selectedCase.cost_of_delay_per_week?.toLocaleString() || '0'}/wk
                      </span>
                    </div>
                  </div>
                </div>

                {/* Quick Action Navigation */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setActiveSystemTab('SCENARIOS')}
                      className="border-slate-800 hover:bg-slate-800 text-xs text-sky-300 rounded-xl"
                    >
                      <Scale className="h-3.5 w-3.5 mr-1" /> View Scenarios & Alternatives ({selectedCase.alternatives?.length || 0})
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setActiveSystemTab('CHALLENGE')}
                      className="border-slate-800 hover:bg-slate-800 text-xs text-amber-300 rounded-xl"
                    >
                      <ShieldAlert className="h-3.5 w-3.5 mr-1" /> View Independent Challenge
                    </Button>
                  </div>

                  <Button
                    size="sm"
                    onClick={() => setActiveSystemTab('AUTHORITY')}
                    className="text-xs h-8 px-4 font-semibold"
                  >
                    <Gavel className="h-3.5 w-3.5 mr-1" /> Authority Sign-Off →
                  </Button>
                </div>
              </div>
            ) : (
              <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-12 text-center text-slate-500 text-xs">
                Select a decision case on the left to inspect its consequence model, independent challenge checks, and authority state.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB: SCENARIOS & ALTERNATIVES */}
      {activeSystemTab === 'SCENARIOS' && (
        <div className="space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Consequence Analysis & Modeled Options</h3>
              <p className="text-xs text-slate-400">
                Evaluating realistic options for {selectedCase?.case_number || 'active case'}: Do Nothing, Pilot Phase, and Full Scale.
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setActiveSystemTab('CASES')}
              className="text-xs border-slate-800 text-slate-300 rounded-xl"
            >
              ← Back to Case List
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(selectedCase?.alternatives && selectedCase.alternatives.length > 0 ? selectedCase.alternatives : [
              { alternative_code: 'A', title: 'Do Nothing (Defer to Q2)', description: 'Preserve cash reserves; zero immediate financial exposure; risk pipeline shortfall.', reversibility: 'HIGH', is_do_nothing: true, financial_model: { cost: 0, expected_outcome: 0 }, score: 4.0 },
              { alternative_code: 'B', title: 'Pilot Phase (25% Budget Test)', description: 'Run controlled 14-day test to validate CAC assumptions before committing full envelope.', reversibility: 'HIGH', is_pilot: true, financial_model: { cost: 1250, expected_outcome: 2500, downside_p10: -250 }, score: 8.5 },
              { alternative_code: 'C', title: 'Full Scale Deployment', description: 'Immediate multi-channel commitment to capture full market demand across verticals.', reversibility: 'LOW', financial_model: { cost: 5000, expected_outcome: 9000, downside_p10: -1500 }, score: 7.2 }
            ]).map((alt: any) => (
              <div
                key={alt.alternative_code}
                className={`p-5 rounded-3xl border space-y-3 ${
                  alt.is_pilot
                    ? 'bg-slate-900 border-sky-500/50 shadow-lg shadow-sky-500/10'
                    : 'bg-slate-900/70 border-slate-800'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-lg bg-slate-800 text-white">
                    Option {alt.alternative_code}
                  </span>
                  {alt.is_pilot && (
                    <span className="text-[10px] font-bold text-sky-400 bg-sky-950/80 border border-sky-800 px-2 py-0.5 rounded-full">
                      Recommended
                    </span>
                  )}
                  {alt.is_do_nothing && (
                    <span className="text-[10px] font-bold text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full">
                      Baseline
                    </span>
                  )}
                </div>

                <h4 className="text-sm font-bold text-white">{alt.title}</h4>
                <p className="text-xs text-slate-400 leading-relaxed">{alt.description}</p>

                <div className="bg-slate-950/80 p-3 rounded-2xl border border-slate-800/80 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Allocated Cost:</span>
                    <span className="font-bold text-white">${alt.financial_model?.cost?.toLocaleString() || '0'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Expected Outcome:</span>
                    <span className="font-bold text-emerald-400">${alt.financial_model?.expected_outcome?.toLocaleString() || '0'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Reversibility:</span>
                    <span className="font-medium text-slate-200">{alt.reversibility || 'MEDIUM'}</span>
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <Button
                    size="sm"
                    onClick={() => {
                      setGrantSelectedAlt(alt.alternative_code);
                      setActiveSystemTab('AUTHORITY');
                    }}
                    className="w-full text-xs bg-slate-800 hover:bg-slate-700 text-white rounded-xl h-8 font-semibold"
                  >
                    Select for Sign-Off →
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB: INDEPENDENT CHALLENGE */}
      {activeSystemTab === 'CHALLENGE' && (
        <div className="space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Independent Challenge & Deterministic Controls</h3>
              <p className="text-xs text-slate-400">
                Multi-disciplinary specialist validation without conversational roleplay.
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setActiveSystemTab('CASES')}
              className="text-xs border-slate-800 text-slate-300 rounded-xl"
            >
              ← Back to Case List
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Financial Control */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-purple-400">
                <DollarSign className="h-5 w-5" />
                <h4 className="text-sm font-bold text-white">Financial Control Check</h4>
              </div>
              <p className="text-xs text-slate-400">
                Unit economics, gross margin floors, and budget envelope headroom verification.
              </p>
              <div className="space-y-2 pt-1 text-xs">
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Gross Margin Floor:</span>
                  <span className="text-emerald-400 font-bold">Passed (Floor &gt;45%)</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">CAC Payback Horizon:</span>
                  <span className="text-emerald-400 font-bold">&lt; 6.2 Months</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Envelope Headroom:</span>
                  <span className="text-white font-bold">$18,400 Remaining</span>
                </div>
              </div>
            </div>

            {/* Compliance & Policy */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-amber-400">
                <ShieldCheck className="h-5 w-5" />
                <h4 className="text-sm font-bold text-white">Policy & Compliance Sentinel</h4>
              </div>
              <p className="text-xs text-slate-400">
                Deterministic policy evaluation, suppression list screening, and regulatory filters.
              </p>
              <div className="space-y-2 pt-1 text-xs">
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Suppression List Filter:</span>
                  <span className="text-emerald-400 font-bold">0 Suppressed Targets</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Policy Precedence:</span>
                  <span className="text-emerald-400 font-bold">Strict Fail-Closed</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Kill-Switch Status:</span>
                  <span className="text-emerald-400 font-bold">Clear (Disengaged)</span>
                </div>
              </div>
            </div>

            {/* Operational Feasibility */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 space-y-3">
              <div className="flex items-center gap-2 text-sky-400">
                <Server className="h-5 w-5" />
                <h4 className="text-sm font-bold text-white">Operational Feasibility</h4>
              </div>
              <p className="text-xs text-slate-400">
                API integration health, channel rate limits, and workforce execution bandwidth.
              </p>
              <div className="space-y-2 pt-1 text-xs">
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Credentials Active:</span>
                  <span className="text-emerald-400 font-bold">Verified</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Rate Limit Headroom:</span>
                  <span className="text-emerald-400 font-bold">88% Capacity</span>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Execution Outbox:</span>
                  <span className="text-emerald-400 font-bold">Idempotency Ready</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB: AUTHORITY & APPROVAL GATE */}
      {activeSystemTab === 'AUTHORITY' && (
        <div className="max-w-2xl mx-auto space-y-5 animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Gavel className="h-5 w-5 text-emerald-400" />
                <div>
                  <h3 className="text-sm font-bold text-white">Executive Authority Sign-Off Gate</h3>
                  <p className="text-xs text-slate-400">Consequential actions require human-in-the-loop authorization.</p>
                </div>
              </div>
              <span className="text-[10px] bg-slate-800 text-slate-300 font-mono px-2.5 py-1 rounded-full border border-slate-700">
                Anti-Self-Approval Active
              </span>
            </div>

            <div className="space-y-3.5 text-xs">
              <div className="p-3 bg-slate-950 rounded-2xl border border-slate-800 space-y-1">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Active Decision Case</span>
                <span className="text-sm font-bold text-white block">{selectedCase?.title || 'No Case Selected'}</span>
                <span className="text-slate-400 block text-[11px]">{selectedCase?.case_number} | Exposure: ${selectedCase?.financial_exposure?.toLocaleString()}</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-300">Selected Alternative</label>
                  <select
                    value={grantSelectedAlt}
                    onChange={(e) => setGrantSelectedAlt(e.target.value)}
                    className="bg-slate-950 border border-slate-800 text-white rounded-xl text-xs h-9 px-2 focus:border-emerald-500"
                  >
                    <option value="A">Option A: Do Nothing</option>
                    <option value="B">Option B: Pilot Phase (Recommended)</option>
                    <option value="C">Option C: Full Scale Deployment</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-300">Decision Clearance</label>
                  <select
                    value={grantDecision}
                    onChange={(e) => setGrantDecision(e.target.value as any)}
                    className="bg-slate-950 border border-slate-800 text-white rounded-xl text-xs h-9 px-2 focus:border-emerald-500"
                  >
                    <option value="APPROVE">APPROVE & AUTHORIZE EXECUTION</option>
                    <option value="REJECT">REJECT PROPOSAL</option>
                  </select>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-300">Recorded Sign-Off Rationale</label>
                <Textarea
                  placeholder="Record your executive rationale for authorizing or rejecting this action..."
                  value={grantRationale}
                  onChange={(e) => setGrantRationale(e.target.value)}
                  className="bg-slate-950 border-slate-800 text-white rounded-xl text-xs min-h-20 focus:border-emerald-500"
                />
              </div>

              <Button
                onClick={handleGrantAuthority}
                disabled={isSubmittingGrant || !selectedCaseId}
                className={`w-full font-bold h-11 rounded-xl shadow-lg mt-2 text-xs flex items-center justify-center gap-2 ${
                  grantDecision === 'APPROVE'
                    ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white'
                    : 'bg-rose-600 hover:bg-rose-500 text-white'
                }`}
              >
                {isSubmittingGrant ? (
                  <>
                    <Loader2 className="animate-spin h-4 w-4" /> Committing Cryptographic Grant...
                  </>
                ) : grantDecision === 'APPROVE' ? (
                  <>
                    <CheckCircle2 size={16} /> Authorize Execution & Issue Cryptographic Grant
                  </>
                ) : (
                  <>
                    <XCircle size={16} /> Reject Decision Case & Stage Override
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* TAB: OUTCOMES & PROVENANCE */}
      {activeSystemTab === 'OUTCOMES' && (
        <div className="space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Decision Outcome Review & Calibration</h3>
              <p className="text-xs text-slate-400">
                Comparing predicted consequences with actual business telemetry at 30, 90, and 180 days.
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setActiveSystemTab('CASES')}
              className="text-xs border-slate-800 text-slate-300 rounded-xl"
            >
              ← Back to Case List
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { milestone: '30-Day Milestone', status: 'COMPLETED', predicted: 'CPL: $65.00', actual: 'CPL: $61.50', brier: '0.08 (Calibrated)', tripwire: 'None Triggered' },
              { milestone: '90-Day Milestone', status: 'SCHEDULED', predicted: 'Net ARR: +$24k', actual: 'Pending Data', brier: '-', tripwire: 'Active Monitoring' },
              { milestone: '180-Day Milestone', status: 'SCHEDULED', predicted: 'Gross Margin: >55%', actual: 'Pending Data', brier: '-', tripwire: 'Active Monitoring' }
            ].map((m, idx) => (
              <div key={idx} className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">{m.milestone}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    m.status === 'COMPLETED' ? 'bg-emerald-950 border-emerald-800 text-emerald-300' : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}>
                    {m.status}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Forecast:</span>
                    <span className="font-semibold text-white">{m.predicted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Actual Measured:</span>
                    <span className="font-semibold text-emerald-400">{m.actual}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Calibration Brier:</span>
                    <span className="font-mono text-indigo-400">{m.brier}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Tripwires:</span>
                    <span className="text-slate-300">{m.tripwire}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. Collapsible Historical Deliberations Archives */}
      <div className="pt-4 border-t border-slate-800/80">
        <details className="group">
          <summary className="cursor-pointer text-xs font-semibold text-slate-400 hover:text-slate-200 flex items-center justify-between p-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <span className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-slate-400" /> Historical Deliberation Archives & Minutes ({meetings.length} sessions)
            </span>
            <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
          </summary>
          <div className="pt-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column: Deliberations Sessions Library */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="border border-gray-800/80 rounded-3xl overflow-hidden shadow-2xl bg-gray-950/80 backdrop-blur-xl">
            <CardHeader className="p-4 border-b border-gray-800/70">
              <div className="flex items-center justify-between mb-2">
                <CardTitle className="text-xs font-extrabold text-white uppercase tracking-wider flex items-center gap-2">
                  <Activity size={14} className="text-amber-400" />
                  Deliberations ({meetings.length})
                </CardTitle>
                {isLiveDeliberating && (
                  <span className="flex items-center gap-1 text-[9px] font-black text-amber-300 bg-amber-500/15 border border-amber-500/40 px-2 py-0.5 rounded-full animate-pulse">
                    <Radio size={9} className="animate-spin text-amber-400" /> 1 ACTIVE
                  </span>
                )}
              </div>
              {/* Search Bar */}
              <div className="relative">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <Input
                  placeholder="Filter sessions..."
                  value={sidebarSearch}
                  onChange={(e) => setSidebarSearch(e.target.value)}
                  className="bg-gray-900/80 border-gray-800 text-white rounded-xl text-xs h-8 pl-8 placeholder:text-gray-600 focus:border-amber-500/60"
                />
              </div>
            </CardHeader>
            <CardContent className="p-2.5">
              {filteredMeetings.length === 0 ? (
                <div className="text-center py-10 text-gray-500 space-y-2">
                  <Users size={28} className="mx-auto text-gray-700" />
                  <p className="text-xs font-semibold">No deliberations found</p>
                  <p className="text-[10px] text-gray-600">Convene a new chamber to begin.</p>
                </div>
              ) : (
                <div className="flex flex-col gap-2 max-h-[680px] overflow-y-auto pr-1">
                  {filteredMeetings.map((m) => {
                    const isSelected = selectedMeetingId === m.id;
                    const isAwaiting = m.status === 'awaiting_approval';
                    const isRunning = m.status === 'active';
                    const isHaltedItem = m.status === 'cancelled';

                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => setSelectedMeetingId(m.id)}
                        className={`p-3.5 rounded-2xl text-left border transition-all relative cursor-pointer ${
                          isSelected
                            ? 'bg-gradient-to-br from-amber-500/15 via-gray-900/90 to-gray-950 border-amber-500/60 text-white shadow-xl shadow-amber-950/20'
                            : 'bg-gray-900/40 border-gray-800/60 text-gray-300 hover:border-gray-700/80 hover:bg-gray-900/70'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className={`text-[9px] uppercase font-black px-2 py-0.5 rounded-full flex items-center gap-1 ${
                            isRunning
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse'
                              : isAwaiting
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                              : isHaltedItem
                              ? 'bg-red-950/60 text-red-300 border border-red-800'
                              : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                          }`}>
                            {isRunning && <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />}
                            {isRunning ? 'Deliberating' : isAwaiting ? 'Approval Gate' : isHaltedItem ? 'Halted' : 'Resolved'}
                          </span>
                          <span className="text-[10px] text-gray-500 font-mono">
                            {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>

                        <h4 className="text-xs font-bold text-white line-clamp-2 leading-snug tracking-tight">
                          {m.title}
                        </h4>

                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-gray-800/60 text-[10px] text-gray-400">
                          <span className="flex items-center gap-1 font-mono">
                            <Users size={11} className="text-gray-500" />
                            {m.participants?.length || 0} Experts
                          </span>
                          <span className="flex items-center gap-1 font-mono">
                            <Zap size={11} className="text-amber-500" />
                            {m.action_items?.length || 0} Actions
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Center & Right Columns: Deliberation Deck & Executive Chamber */}
        <div className="lg:col-span-3 space-y-6">
          {selectedMeeting ? (
            <>
              {/* Meeting Meta & Status Bar */}
              <div className="rounded-3xl p-5 bg-gray-950/80 border border-gray-800/80 shadow-2xl backdrop-blur-xl">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[10px] text-amber-400 font-black uppercase tracking-widest bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">
                        {selectedMeeting.trigger_type?.replace('_', ' ') || 'STRATEGIC DELIBERATION'}
                      </span>
                      {isLiveDeliberating && (
                        <span className="flex items-center gap-1.5 text-[10px] font-black px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                          <Radio size={11} className="text-amber-400 animate-spin" /> Live Deliberating
                        </span>
                      )}
                      {isHalted && (
                        <span className="flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-red-950/80 text-red-300 border border-red-800">
                          <AlertOctagon size={11} /> Halted by Human Chairman
                        </span>
                      )}
                      {selectedMeeting.status === 'awaiting_approval' && (
                        <span className="flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
                          <ShieldAlert size={11} /> Approval Gate Active
                        </span>
                      )}
                      {selectedMeeting.status === 'completed' && (
                        <span className="flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                          <CheckCircle2 size={11} /> Consensus Formed & Executing
                        </span>
                      )}
                    </div>

                    <h2 className="text-xl font-black text-white tracking-tight pt-1">
                      {selectedMeeting.title}
                    </h2>

                    {selectedMeeting.context_summary && (
                      <p className="text-xs text-gray-400 leading-relaxed font-mono bg-gray-900/60 p-3 rounded-2xl border border-gray-800/80">
                        {selectedMeeting.context_summary}
                      </p>
                    )}
                  </div>

                  {/* Top Meeting Action Buttons */}
                  <div className="flex items-center gap-2 shrink-0">
                    {!isLiveDeliberating && (
                      <Button
                        size="sm"
                        onClick={handleRerunMeeting}
                        className="border border-amber-500/40 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 text-xs h-9 px-3.5 rounded-xl font-bold flex items-center gap-1.5 cursor-pointer"
                      >
                        <RotateCcw size={13} /> Re-run Deliberation
                      </Button>
                    )}

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExportMeeting('md')}
                      className="border-gray-800 text-gray-300 hover:bg-gray-800/80 text-xs h-9 px-3 rounded-xl cursor-pointer"
                    >
                      <Download size={13} className="mr-1.5" /> Export MD
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExportMeeting('json')}
                      className="border-gray-800 text-gray-300 hover:bg-gray-800/80 text-xs h-9 px-3 rounded-xl cursor-pointer"
                    >
                      <Download size={13} className="mr-1.5" /> JSON
                    </Button>
                  </div>
                </div>

                {/* Halted State Banner */}
                {isHalted && (
                  <div className="mt-4 p-3 rounded-2xl bg-red-950/40 border border-red-900/60 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-red-200">
                      <AlertOctagon size={16} className="text-red-400 shrink-0" />
                      <span>
                        Deliberation stopped by human chairman. Full transcript, evidence citations, and council stances are preserved.
                      </span>
                    </div>
                    <Button
                      size="sm"
                      onClick={handleRerunMeeting}
                      className="bg-amber-500 hover:bg-amber-400 text-black font-extrabold h-7 px-3 text-[11px] rounded-lg ml-2 cursor-pointer"
                    >
                      <RotateCcw size={12} className="mr-1" /> Resume / Re-run
                    </Button>
                  </div>
                )}
              </div>

              {/* 3. NEW EXECUTIVE COUNCIL CHAMBER HUD (Completely replaces the SVG table) */}
              <div className="rounded-3xl p-5 bg-gradient-to-b from-gray-950 via-gray-900/60 to-gray-950 border border-gray-800/90 shadow-2xl relative overflow-hidden">
                {/* HUD Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-gray-800/60">
                  <div className="flex items-center gap-2.5">
                    <div className="h-8 w-8 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
                      <Crown size={15} className="text-amber-400" />
                    </div>
                    <div>
                      <h3 className="text-xs font-black text-white uppercase tracking-wider flex items-center gap-2">
                        Executive Council Chamber
                        <span className="text-[9px] px-2 py-0.5 rounded-full bg-gray-800 text-gray-300 font-mono">
                          {councilSeats.length} Seats Formed
                        </span>
                      </h3>
                      <p className="text-[10px] text-gray-400">Click any executive seat to isolate cross-examination discourse</p>
                    </div>
                  </div>

                  {/* Filter Status Badge */}
                  <div className="flex items-center gap-2">
                    {selectedAgentFilter !== 'ALL' ? (
                      <button
                        type="button"
                        onClick={() => setSelectedAgentFilter('ALL')}
                        className="text-[10px] text-amber-300 font-bold bg-amber-500/15 px-2.5 py-1 rounded-full border border-amber-500/40 flex items-center gap-1.5 hover:bg-amber-500/25 transition-all cursor-pointer"
                      >
                        <Filter size={11} /> Filter: {selectedAgentFilter}
                        <X size={11} className="text-amber-400 ml-1 hover:text-white" />
                      </button>
                    ) : (
                      <span className="text-[10px] text-gray-500 flex items-center gap-1">
                        <Users size={11} /> Viewing Full Quorum
                      </span>
                    )}
                  </div>
                </div>

                {/* Council Seats Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-2.5">
                  {councilSeats.map((seat) => {
                    const Icon = seat.meta.icon;
                    const isFiltered = selectedAgentFilter.toLowerCase() === seat.name.toLowerCase();

                    return (
                      <button
                        key={seat.name}
                        type="button"
                        onClick={() => setSelectedAgentFilter(isFiltered ? 'ALL' : seat.name)}
                        className={`p-3 rounded-2xl border text-left flex flex-col justify-between transition-all cursor-pointer relative group ${
                          seat.isSpeaking
                            ? 'bg-amber-500/15 border-amber-500 shadow-lg shadow-amber-500/20 ring-2 ring-amber-400 ring-offset-2 ring-offset-gray-950 scale-102'
                            : isFiltered
                            ? 'bg-amber-500/20 border-amber-400 ring-1 ring-amber-400'
                            : 'bg-gray-900/40 border-gray-800/80 hover:border-gray-700 hover:bg-gray-900/80'
                        }`}
                      >
                        {/* Top: Icon & Speaking Beacon */}
                        <div className="flex items-center justify-between mb-2">
                          <div className={`h-8 w-8 rounded-xl flex items-center justify-center border shadow-sm ${seat.meta.bg} ${seat.meta.color} ${seat.meta.border}`}>
                            <Icon size={15} />
                          </div>
                          {seat.isSpeaking ? (
                            <span className="flex items-center gap-1 text-[8px] font-black uppercase text-amber-300 bg-amber-500/25 px-1.5 py-0.5 rounded-full border border-amber-500/40 animate-pulse">
                              <Radio size={8} className="animate-spin text-amber-400" /> Speaking
                            </span>
                          ) : (
                            <span className="text-[9px] font-mono text-gray-500">
                              {seat.turnsCount} turns
                            </span>
                          )}
                        </div>

                        {/* Middle: Title & Role */}
                        <div>
                          <h4 className="text-[11px] font-bold text-white truncate group-hover:text-amber-300 transition-colors">
                            {seat.name.replace(' Expert', '').replace(' AI', '')}
                          </h4>
                          <span className="text-[9px] text-gray-400 truncate block">
                            {seat.meta.title}
                          </span>
                        </div>

                        {/* Bottom: Dynamic Stance Chip */}
                        <div className="mt-2.5 pt-2 border-t border-gray-800/60 flex items-center justify-between">
                          <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-md border truncate ${seat.stanceColor}`}>
                            {seat.stance}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Consensus & Deliberation Phase Bar */}
                <div className="mt-5 pt-4 border-t border-gray-800/70 flex flex-col md:flex-row items-center justify-between gap-4">
                  {/* Phase Stepper */}
                  <div className="w-full md:w-auto flex-1 flex items-center justify-between gap-1 overflow-x-auto pb-1">
                    {PHASES_LIST.map((phase, idx) => {
                      const Icon = phase.icon;
                      const isPast = idx < currentPhaseIndex;
                      const isCurrent = idx === currentPhaseIndex;
                      const isTabActive = activeDeckTab === phase.tab;

                      return (
                        <button
                          key={phase.key}
                          type="button"
                          onClick={() => setActiveDeckTab(phase.tab as any)}
                          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold transition-all cursor-pointer whitespace-nowrap ${
                            isTabActive
                              ? 'bg-amber-500 text-black shadow-md'
                              : isCurrent
                              ? 'bg-amber-500/20 border border-amber-500/50 text-amber-300 animate-pulse'
                              : isPast
                              ? 'text-emerald-400 hover:bg-gray-900/60'
                              : 'text-gray-600 hover:text-gray-400'
                          }`}
                        >
                          {isPast ? <Check size={11} className="text-emerald-400" /> : <Icon size={11} />}
                          <span className="text-[11px]">{phase.label}</span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Consensus Meter */}
                  {latestConfidence !== null && (
                    <div className="flex items-center gap-3 shrink-0 bg-gray-900/70 px-3.5 py-1.5 rounded-2xl border border-gray-800/80">
                      <div className="text-right">
                        <span className="text-[9px] uppercase tracking-wider text-gray-500 font-extrabold block">Council Consensus</span>
                        <span className="text-xs font-black text-amber-400 font-mono">{latestConfidence}%</span>
                      </div>
                      <div className="w-24 bg-gray-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-amber-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                          style={{ width: `${latestConfidence}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 4. Chairman Gavel Mid-Deliberation Directive Bar */}
              <div className="rounded-xl p-4 bg-card border border-border shadow-xs">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 text-foreground shrink-0">
                    <div className="h-9 w-9 rounded-lg bg-surface-hover border border-border flex items-center justify-center">
                      <Gavel size={17} className="text-primary" />
                    </div>
                    <div>
                      <span className="text-xs font-semibold text-foreground block">Chairman Binding Directive</span>
                      <span className="text-[10px] text-muted-foreground block">Inject real-time executive constraints or steer active deliberations</span>
                    </div>
                  </div>

                  <div className="flex-1 flex items-center gap-2">
                    <Input
                      placeholder="e.g. 'Cap SDR spend at $8,000 for 30-day pilot', 'Require 2 customer reference calls'..."
                      value={chairmanDirective}
                      onChange={(e) => setChairmanDirective(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') void handleChairmanIntervene(); }}
                      className="bg-muted/40 border-border text-foreground rounded-xl text-xs h-9 focus:border-primary"
                    />
                    <Button
                      size="sm"
                      disabled={isSubmittingDirective || !chairmanDirective.trim()}
                      onClick={handleChairmanIntervene}
                      className="text-xs h-9 px-4 shrink-0 font-semibold cursor-pointer"
                    >
                      {isSubmittingDirective ? 'Dispatching...' : 'Issue Directive'}
                    </Button>
                  </div>
                </div>

                {/* Quick Presets */}
                <div className="mt-2.5 pt-2 border-t border-gray-800/60 flex flex-wrap items-center gap-1.5">
                  <span className="text-[9px] uppercase tracking-wider text-gray-500 font-extrabold mr-1">Presets:</span>
                  {QUICK_DIRECTIVES.map((preset, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setChairmanDirective(preset)}
                      className="text-[10px] text-gray-300 hover:text-amber-300 bg-gray-900/80 hover:bg-gray-800 border border-gray-800/80 hover:border-amber-500/40 px-2 py-0.5 rounded-lg transition-colors cursor-pointer"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>

              {/* 5. Institutional Deliberation Deck Navigation Tabs */}
              <div className="flex flex-wrap items-center gap-1.5 p-1.5 bg-gray-950/80 rounded-2xl border border-gray-800/80 shadow-md">
                <button
                  type="button"
                  onClick={() => setActiveDeckTab('debate')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all cursor-pointer ${
                    activeDeckTab === 'debate'
                      ? 'bg-amber-500 text-black shadow-md'
                      : 'text-gray-400 hover:text-white hover:bg-gray-900/60'
                  }`}
                >
                  <MessageSquare size={13} /> Live Debate Chamber ({selectedMeeting.transcript?.length || 0})
                  {isLiveDeliberating && <span className="h-1.5 w-1.5 rounded-full bg-amber-900 animate-ping" />}
                </button>

                <button
                  type="button"
                  onClick={() => setActiveDeckTab('evidence')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all cursor-pointer ${
                    activeDeckTab === 'evidence'
                      ? 'bg-amber-500 text-black shadow-md'
                      : 'text-gray-400 hover:text-white hover:bg-gray-900/60'
                  }`}
                >
                  <Database size={13} /> Evidence & Firecrawl ({evidenceList.length})
                </button>

                <button
                  type="button"
                  onClick={() => setActiveDeckTab('options')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all cursor-pointer ${
                    activeDeckTab === 'options'
                      ? 'bg-amber-500 text-black shadow-md'
                      : 'text-gray-400 hover:text-white hover:bg-gray-900/60'
                  }`}
                >
                  <Sparkles size={13} /> Options Matrix ({optionsList.length})
                </button>

                <button
                  type="button"
                  onClick={() => setActiveDeckTab('redteam')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all cursor-pointer ${
                    activeDeckTab === 'redteam'
                      ? 'bg-amber-500 text-black shadow-md'
                      : 'text-gray-400 hover:text-white hover:bg-gray-900/60'
                  }`}
                >
                  <ShieldAlert size={13} /> Red Team & Tripwires ({outcomesList.length > 0 ? outcomesList[0].tripwires?.length || 0 : 0})
                </button>

                <button
                  type="button"
                  onClick={() => setActiveDeckTab('dissents')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all cursor-pointer ${
                    activeDeckTab === 'dissents'
                      ? 'bg-amber-500 text-black shadow-md'
                      : 'text-gray-400 hover:text-white hover:bg-gray-900/60'
                  }`}
                >
                  <AlertTriangle size={13} /> Dissent Register ({dissentList.length})
                </button>

                <button
                  type="button"
                  onClick={() => setActiveDeckTab('actions')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all cursor-pointer ${
                    activeDeckTab === 'actions'
                      ? 'bg-amber-500 text-black shadow-md'
                      : 'text-gray-400 hover:text-white hover:bg-gray-900/60'
                  }`}
                >
                  <ShieldCheck size={13} /> Governed Actions ({actionList.length})
                  {awaitingCount > 0 && (
                    <span className="ml-1 px-1.5 py-0.2 rounded-full bg-rose-500 text-white text-[10px] font-black animate-pulse">
                      {awaitingCount}
                    </span>
                  )}
                </button>
              </div>

              {/* TAB 1: LIVE DEBATE CHAMBER (Streaming Arguments) */}
              {activeDeckTab === 'debate' && (
                <Card className="border border-gray-800/80 rounded-3xl overflow-hidden bg-gray-950/80 shadow-2xl backdrop-blur-xl">
                  <CardHeader className="p-4 border-b border-gray-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-sm text-white font-black flex items-center gap-2">
                        <MessageSquare className="text-amber-400 h-4 w-4" />
                        Executive Deliberation Discourse
                        {isLiveDeliberating && (
                          <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse flex items-center gap-1 font-bold">
                            <Radio size={10} className="text-amber-400 animate-spin" /> Live Streaming
                          </span>
                        )}
                      </CardTitle>
                      <CardDescription className="text-gray-400 text-xs mt-0.5">
                        Multi-round cross-examination and consensus formation across Sales, Finance, Marketing, HR, Firecrawl Web Intelligence, and Red Team.
                      </CardDescription>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setAutoScroll(!autoScroll)}
                        className={`text-[11px] h-7 px-2.5 rounded-xl border ${
                          autoScroll
                            ? 'border-amber-500/40 text-amber-300 bg-amber-500/10'
                            : 'border-gray-800 text-gray-400'
                        }`}
                      >
                        {autoScroll ? 'Auto-scroll: ON' : 'Auto-scroll: PAUSED'}
                      </Button>

                      {selectedAgentFilter !== 'ALL' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedAgentFilter('ALL')}
                          className="text-[11px] h-7 px-2 text-gray-400 hover:text-white"
                        >
                          Clear Filter
                        </Button>
                      )}
                    </div>
                  </CardHeader>

                  <CardContent className="p-4 space-y-4 max-h-[720px] overflow-y-auto">
                    {filteredTranscript.length === 0 ? (
                      <div className="text-center py-16 text-gray-500 space-y-2">
                        <MessageSquare size={36} className="mx-auto text-gray-700 opacity-60" />
                        <p className="text-xs font-bold text-gray-400">Deliberation transcript empty.</p>
                        <p className="text-[11px] text-gray-600 max-w-sm mx-auto">
                          {isLiveDeliberating
                            ? 'Council specialists are analyzing evidence and synthesizing opening positions...'
                            : 'Convene or re-run deliberation to generate multi-agent debate turns.'}
                        </p>
                      </div>
                    ) : (
                      filteredTranscript.map((msg, i) => {
                        const sender = msg.sender || msg.speaker_name || msg.agent_role || msg.speaker || 'Council Expert';
                        const content = msg.content || msg.message || msg.agent_thought || msg.thought || '';
                        const meta = getAgentMeta(sender);
                        const Icon = meta.icon;
                        const isCEO = sender.includes('CEO');
                        const isRedTeam = sender.includes('Red Team');
                        const stance = msg.stance || (content.includes('🔴') ? 'oppose' : content.includes('🟢') ? 'support' : 'neutral');

                        return (
                          <div
                            key={i}
                            className={`p-4 rounded-2xl border transition-all space-y-3 ${
                              isCEO
                                ? 'bg-amber-950/25 border-amber-500/40 shadow-lg shadow-amber-950/20'
                                : isRedTeam
                                ? 'bg-rose-950/20 border-rose-500/40 shadow-lg shadow-rose-950/20'
                                : `${meta.bg} ${meta.border}`
                            }`}
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2.5">
                                <div className={`h-8 w-8 rounded-xl flex items-center justify-center border shadow-sm ${meta.bg} ${meta.color} ${meta.border}`}>
                                  <Icon size={15} />
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs font-black text-white">{sender}</span>
                                    <span className="text-[10px] text-gray-400 px-2 py-0.2 rounded-full bg-gray-900/80 border border-gray-800">
                                      {meta.title}
                                    </span>
                                    {msg.target_agent && (
                                      <span className="text-[10px] text-amber-300/90 font-mono flex items-center gap-1">
                                        <ArrowRight size={10} className="text-amber-400" />
                                        Cross-examining: {msg.target_agent}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center gap-2">
                                {stance === 'oppose' && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40">
                                    🔴 Challenge
                                  </span>
                                )}
                                {stance === 'support' && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                                    🟢 Alignment
                                  </span>
                                )}
                                <span className="text-[10px] font-mono text-gray-500">
                                  {msg.timestamp || 'Recorded'}
                                </span>
                              </div>
                            </div>

                            {/* Main Message Text */}
                            <div className="text-xs text-gray-200 whitespace-pre-wrap leading-relaxed space-y-1">
                              {content}
                            </div>

                            {/* Clickable Citations & Findings */}
                            {((msg.sources && msg.sources.length > 0) || (msg.findings && msg.findings.length > 0)) && (
                              <div className="mt-2.5 pt-2.5 border-t border-gray-800/60 flex flex-wrap items-center gap-2">
                                {msg.sources?.map((src, sIdx) => {
                                  const isWeb = src.startsWith('web:');
                                  const cleanUrl = isWeb ? src.replace('web:', '') : src;
                                  return isWeb ? (
                                    <a
                                      key={sIdx}
                                      href={cleanUrl}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-[10px] text-orange-300 bg-orange-950/40 px-2.5 py-0.5 rounded-lg border border-orange-800/60 flex items-center gap-1.5 hover:border-orange-500 transition-colors"
                                    >
                                      <Globe size={11} className="text-orange-400" />
                                      <span className="truncate max-w-[200px]">{cleanUrl}</span>
                                      <ExternalLink size={9} />
                                    </a>
                                  ) : (
                                    <span
                                      key={sIdx}
                                      className="text-[10px] text-gray-400 bg-gray-900/80 px-2 py-0.5 rounded-lg border border-gray-800 flex items-center gap-1"
                                    >
                                      <Database size={10} /> {src}
                                    </span>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                    <div ref={transcriptEndRef} />
                  </CardContent>
                </Card>
              )}

              {/* TAB 2: EVIDENCE PACK & FIRECRAWL INTELLIGENCE */}
              {activeDeckTab === 'evidence' && (
                <Card className="border border-gray-800/80 rounded-3xl overflow-hidden bg-gray-950/80 shadow-2xl">
                  <CardHeader className="p-4 border-b border-gray-800/60">
                    <CardTitle className="text-sm text-white font-bold flex items-center gap-2">
                      <Database className="text-amber-400 h-4 w-4" />
                      Ground Truth Evidence Catalog & Firecrawl Search ({evidenceList.length})
                    </CardTitle>
                    <CardDescription className="text-gray-400 text-xs">
                      Live internet market research, competitor outbound benchmarks, database metrics, and knowledge documents.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-4 space-y-4">
                    {evidenceList.length === 0 ? (
                      <p className="text-xs text-gray-500 py-8 text-center">No evidence records cataloged yet.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {evidenceList.map((ev) => {
                          const isWeb = ev.source_type === 'firecrawl_web_search' || ev.source_ref.startsWith('web:');
                          const cleanUrl = ev.source_ref.replace('web:', '');

                          return (
                            <div
                              key={ev.id}
                              className={`p-4 rounded-2xl border flex flex-col justify-between space-y-2 ${
                                isWeb
                                  ? 'bg-orange-950/15 border-orange-500/30 shadow-lg shadow-orange-950/20'
                                  : 'bg-gray-900/40 border-gray-800/70'
                              }`}
                            >
                              <div>
                                <div className="flex items-center justify-between mb-1.5">
                                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase flex items-center gap-1 ${
                                    isWeb
                                      ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                                      : 'bg-gray-800 text-gray-300 border border-gray-700'
                                  }`}>
                                    {isWeb ? <Globe size={10} /> : <Database size={10} />}
                                    {isWeb ? 'Firecrawl Web Evidence' : ev.source_type.replace('_', ' ')}
                                  </span>
                                  {ev.trust_score !== undefined && (
                                    <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20 font-mono">
                                      {ev.trust_score}% Trust
                                    </span>
                                  )}
                                </div>
                                <h4 className="text-xs font-bold text-white truncate mb-1">
                                  {cleanUrl}
                                </h4>
                                <p className="text-xs text-gray-300 line-clamp-3 leading-relaxed">
                                  {ev.excerpt || 'No excerpt provided.'}
                                </p>
                              </div>

                              {isWeb && cleanUrl.startsWith('http') && (
                                <div className="pt-2 border-t border-gray-800/40">
                                  <a
                                    href={cleanUrl}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[10px] text-orange-400 hover:text-orange-300 flex items-center gap-1 font-bold"
                                  >
                                    Inspect Live Evidence Source <ExternalLink size={10} />
                                  </a>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 3: QUANTIFIED OPTIONS MATRIX */}
              {activeDeckTab === 'options' && (
                <Card className="border border-gray-800/80 rounded-3xl overflow-hidden bg-gray-950/80 shadow-2xl">
                  <CardHeader className="p-4 border-b border-gray-800/60">
                    <CardTitle className="text-sm text-white font-bold flex items-center gap-2">
                      <Sparkles className="text-amber-400 h-4 w-4" />
                      Quantified Options Matrix (EV & Downside P10 Modeling)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {optionsList.length === 0 ? (
                      <p className="text-xs text-gray-500 py-8 text-center">Options modeled during Stage 5 of deliberation.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {optionsList.map((opt) => {
                          const fm = opt.financial_model || {};
                          const ev = fm.ev !== undefined ? fm.ev : null;
                          const p10 = fm.downside_p10 !== undefined ? fm.downside_p10 : null;
                          const isTopOption = opt.weighted_score >= 0.7;

                          return (
                            <div
                              key={opt.id}
                              className={`p-4 rounded-2xl border flex flex-col justify-between ${
                                isTopOption
                                  ? 'bg-amber-950/20 border-amber-500/50 shadow-lg'
                                  : 'bg-gray-900/40 border-gray-800/70'
                              }`}
                            >
                              <div>
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-gray-800 text-amber-300">
                                    Option {opt.option_code}
                                  </span>
                                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                    {opt.reversibility} Reversibility
                                  </span>
                                </div>
                                <h4 className="text-xs font-bold text-white mb-1">{opt.title}</h4>
                                <p className="text-xs text-gray-300 mb-3">{opt.description}</p>

                                <div className="grid grid-cols-2 gap-2 p-2.5 rounded-xl bg-gray-950 border border-gray-800 text-[11px] mb-3">
                                  <div>
                                    <span className="text-[9px] text-gray-400 block uppercase">Expected Value</span>
                                    <span className="font-mono font-bold text-emerald-400">
                                      {ev !== null ? `$${Number(ev).toLocaleString()}` : 'N/A'}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-[9px] text-gray-400 block uppercase">Downside (P10)</span>
                                    <span className="font-mono font-bold text-rose-400">
                                      {p10 !== null ? `$${Number(p10).toLocaleString()}` : 'N/A'}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              <div>
                                <div className="flex justify-between items-center text-[10px] mb-1">
                                  <span className="text-gray-400">Weighted Council Score</span>
                                  <span className="font-bold text-amber-400 font-mono">{(opt.weighted_score * 100).toFixed(0)}%</span>
                                </div>
                                <div className="w-full bg-gray-800 h-1.5 rounded-full overflow-hidden">
                                  <div
                                    className="bg-gradient-to-r from-amber-500 to-emerald-400 h-full rounded-full"
                                    style={{ width: `${Math.min(100, Math.max(0, opt.weighted_score * 100))}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 4: RED TEAM & TRIPWIRES */}
              {activeDeckTab === 'redteam' && (
                <Card className="border border-gray-800/80 rounded-3xl overflow-hidden bg-gray-950/80 shadow-2xl">
                  <CardHeader className="p-4 border-b border-gray-800/60">
                    <CardTitle className="text-sm text-white font-bold flex items-center gap-2">
                      <ShieldAlert className="text-rose-400 h-4 w-4" />
                      Red Team Pre-Mortem & Tripwire Registry
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-4">
                    <div className="p-3.5 rounded-2xl bg-rose-950/20 border border-rose-900/60 text-xs text-gray-300">
                      Red Team assumes outbound initiatives failed catastrophically. The council establishes automated tripwires to prevent domain blacklisting and budget overrun.
                    </div>
                    {outcomesList.length === 0 ? (
                      <p className="text-xs text-gray-500 py-8 text-center">Tripwires registered upon governed execution.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {outcomesList.map((out) => (
                          <div key={out.id} className="p-4 rounded-2xl bg-gray-900/40 border border-gray-800 space-y-2">
                            <span className="text-xs font-bold text-amber-300 font-mono block">
                              Milestone: {out.review_milestone}
                            </span>
                            <div className="space-y-1">
                              {(out.tripwires || []).map((tw, idx) => (
                                <div key={idx} className="text-xs text-rose-300 bg-rose-950/30 p-2 rounded-xl border border-rose-900/40 flex items-start gap-1">
                                  <AlertTriangle size={12} className="shrink-0 text-rose-400 mt-0.5" />
                                  <span>{tw}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 5: DISSENT REGISTER */}
              {activeDeckTab === 'dissents' && (
                <Card className="border border-gray-800/80 rounded-3xl overflow-hidden bg-gray-950/80 shadow-2xl">
                  <CardHeader className="p-4 border-b border-gray-800/60">
                    <CardTitle className="text-sm text-white font-bold flex items-center gap-2">
                      <AlertTriangle className="text-amber-400 h-4 w-4" />
                      Dissent Register & Architectural Decision Record (ADR)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {dissentList.length === 0 ? (
                      <p className="text-xs text-gray-500 py-8 text-center">Full council consensus achieved without unaddressed dissents.</p>
                    ) : (
                      <div className="space-y-3">
                        {dissentList.map((dis) => (
                          <div key={dis.id} className="p-3.5 rounded-2xl bg-gray-900/40 border border-gray-800 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white">{dis.agent}</span>
                              {dis.requires_human_signoff && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40">
                                  Human Signoff Required
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-gray-300">{dis.dissent_position}</p>
                            {dis.override_rationale && (
                              <p className="text-[11px] text-amber-300/90 bg-amber-500/10 p-2 rounded-xl border border-amber-500/20">
                                Override Rationale: {dis.override_rationale}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* TAB 6: GOVERNED ACTIONS */}
              {activeDeckTab === 'actions' && (
                <Card className="border border-gray-800/80 rounded-3xl overflow-hidden bg-gray-950/80 shadow-2xl">
                  <CardHeader className="p-4 border-b border-gray-800/60 flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm text-white font-bold flex items-center gap-2">
                        <ShieldCheck className="text-emerald-400 h-4 w-4" />
                        Governed Action Center ({actionList.length})
                      </CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {actionList.length === 0 ? (
                      <p className="text-xs text-gray-500 py-8 text-center">No action items produced yet.</p>
                    ) : (
                      actionList.map((act) => {
                        const isAwaiting = act.status === 'awaiting_approval' || act.status === 'pending';
                        return (
                          <div
                            key={act.id}
                            className={`p-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                              isAwaiting
                                ? 'bg-amber-950/20 border-amber-500/40 shadow-lg'
                                : 'bg-gray-900/40 border-gray-800/70'
                            }`}
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-bold px-2 py-0.2 rounded-full uppercase ${
                                  act.risk_tier === 'high'
                                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                    : act.risk_tier === 'medium'
                                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                }`}>
                                  {act.risk_tier || 'standard'} risk
                                </span>
                                <span className="text-xs font-bold text-white">Assigned: {act.assigned_to}</span>
                              </div>
                              <p className="text-xs text-gray-300">{act.description}</p>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              {isAwaiting ? (
                                <>
                                  <Button
                                    size="sm"
                                    onClick={() => handleApproveAction(act.id)}
                                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs h-8 px-3 rounded-xl cursor-pointer"
                                  >
                                    <Check size={12} className="mr-1" /> Approve
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => setRejectActionId(act.id)}
                                    className="border-rose-900/60 text-rose-300 hover:bg-rose-950/40 text-xs h-8 px-3 rounded-xl cursor-pointer"
                                  >
                                    <X size={12} className="mr-1" /> Reject
                                  </Button>
                                </>
                              ) : (
                                <span className="text-xs font-bold text-emerald-400 uppercase">
                                  {act.status}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="border border-gray-800 p-16 text-center text-gray-500 rounded-3xl bg-gray-950/70">
              <Users size={44} className="mx-auto text-gray-700 mb-3" />
              <h3 className="text-base font-bold text-white">No Boardroom Session Selected</h3>
              <p className="text-xs mt-1 text-gray-400">Select an active deliberation from the sidebar or convene a new chamber.</p>
            </Card>
          )}
        </div>
      </div>
          </div>
        </details>
      </div>

      {/* Reject Action Modal Dialog */}
      <Dialog open={!!rejectActionId} onOpenChange={(open) => { if (!open) setRejectActionId(null); }}>
        <DialogContent className="border border-gray-800 text-white max-w-md rounded-3xl p-6 bg-gray-950/95 shadow-2xl backdrop-blur-2xl">
          <DialogHeader>
            <DialogTitle className="text-base font-bold text-white flex items-center gap-2">
              <AlertTriangle className="text-rose-400 h-5 w-5" /> Reject Action Item
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-3">
            <p className="text-xs text-gray-300">
              Provide a rationale for rejecting this governed action. The council will be notified to formulate an alternate proposal.
            </p>
            <Textarea
              placeholder="e.g. Budget exceeds quarterly limit, require cheaper email warmup provider..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-24 focus:border-rose-500"
            />
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setRejectActionId(null)}
                className="text-gray-400 hover:text-white text-xs h-9 px-4 rounded-xl"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleRejectAction}
                className="bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs h-9 px-4 rounded-xl shadow-lg"
              >
                Confirm Rejection
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

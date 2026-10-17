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
  
  // Tabs: defaults to 'debate'
  const [activeDeckTab, setActiveDeckTab] = useState<'debate' | 'options' | 'redteam' | 'dissents' | 'actions' | 'evidence'>('debate');
  
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

  useEffect(() => {
    if (token) {
      void fetchMeetings();
    }
  }, [fetchMeetings, token]);

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
      {/* 1. Elite Executive Command Header */}
      <div className="relative rounded-3xl p-6 bg-gradient-to-r from-gray-950 via-gray-900 to-gray-950 border border-gray-800/80 shadow-2xl overflow-hidden">
        {/* Subtle background ambient glow */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="h-11 w-11 rounded-2xl bg-gradient-to-tr from-amber-500 via-amber-600 to-yellow-400 p-0.5 shadow-lg shadow-amber-500/20">
                <div className="h-full w-full rounded-[14px] bg-gray-950 flex items-center justify-center">
                  <Crown className="text-amber-400 h-5 w-5" />
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-black text-white tracking-tight">
                    Executive AI Boardroom
                  </h1>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-gradient-to-r from-amber-500/20 via-yellow-500/20 to-amber-500/20 border border-amber-500/40 text-amber-300 font-extrabold uppercase tracking-wider shadow-sm">
                    Autonomous Quorum
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5 max-w-2xl leading-relaxed">
                  High-stakes multi-agent executive deliberation with live Firecrawl internet market validation, adversarial cross-examination, and human-in-the-loop governance.
                </p>
              </div>
            </div>
          </div>

          {/* Header Action Center */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* EMERGENCY STOP BUTTON */}
            {isLiveDeliberating && (
              <Button
                onClick={handleStopMeeting}
                disabled={isStopping}
                className="bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-black text-xs h-10 px-4 rounded-xl shadow-lg shadow-rose-950/60 border border-rose-400/40 animate-pulse cursor-pointer flex items-center gap-2"
              >
                <AlertOctagon size={15} className="text-white" />
                {isStopping ? 'Halting Flow...' : 'STOP DELIBERATION'}
              </Button>
            )}

            {/* Convene Modal Button */}
            <Dialog open={isCreateMeetingOpen} onOpenChange={setIsCreateMeetingOpen}>
              <DialogTrigger render={
                <Button className="bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-gray-950 font-black text-xs h-10 px-5 rounded-xl shadow-lg shadow-amber-500/20 cursor-pointer flex items-center gap-2 transition-transform active:scale-95" />
              }>
                <Users size={15} /> Convene New Chamber
              </DialogTrigger>
              <DialogContent className="border border-gray-800 text-white max-w-lg rounded-3xl p-6 bg-gray-950/95 shadow-2xl backdrop-blur-2xl">
                <DialogHeader>
                  <DialogTitle className="text-base font-bold text-white flex items-center gap-2">
                    <Crown className="text-amber-400 h-5 w-5" /> Convene Executive Deliberation
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 mt-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-300">Strategic Objective / Title</label>
                    <Input
                      placeholder="e.g. Accelerate B2B SaaS outbound sales pipeline to reach $100k ARR"
                      value={manualMeetingTitle}
                      onChange={(e) => setManualMeetingTitle(e.target.value)}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10 focus:border-amber-500"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-300">Context, Budget & Constraints</label>
                    <Textarea
                      placeholder="Describe target ICP, $20,000 budget envelope, multi-touch sequences, target ACV..."
                      value={manualMeetingTopic}
                      onChange={(e) => setManualMeetingTopic(e.target.value)}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-24 focus:border-amber-500"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-400">Assemble Specialized Quorum</label>
                    <div className="grid grid-cols-2 gap-2 mt-1">
                      {[
                        { name: 'Sales Intelligence Expert', desc: 'Outbound pipeline & conversion' },
                        { name: 'Finance Expert', desc: 'Budget & unit economics' },
                        { name: 'Marketing Intelligence Expert', desc: 'ICP demand gen & collateral' },
                        { name: 'Human Resources Expert', desc: 'SDR ramp & talent timeline' },
                        { name: 'Web Intelligence AI', desc: 'Live Firecrawl market discovery' },
                        { name: 'Red Team AI', desc: 'Pre-mortem & tripwires' },
                      ].map((team) => {
                        const isChecked = manualMeetingParticipants.includes(team.name);
                        return (
                          <button
                            key={team.name}
                            type="button"
                            onClick={() => {
                              if (isChecked) {
                                setManualMeetingParticipants(manualMeetingParticipants.filter(p => p !== team.name));
                              } else {
                                setManualMeetingParticipants([...manualMeetingParticipants, team.name]);
                              }
                            }}
                            className={`p-2.5 rounded-xl text-xs font-medium border text-left transition-all ${
                              isChecked
                                ? 'bg-amber-500/15 border-amber-500/60 text-white shadow-md'
                                : 'bg-gray-900/60 border-gray-800/80 text-gray-400 hover:border-gray-700'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-0.5">
                              <span className="font-bold truncate text-[11px]">{team.name}</span>
                              {isChecked && <Check size={12} className="text-amber-400 shrink-0" />}
                            </div>
                            <span className="text-[10px] text-gray-500 block truncate">{team.desc}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  <Button
                    onClick={handleCreateManualMeeting}
                    disabled={manualMeetingLoading || !manualMeetingTitle || !manualMeetingTopic}
                    className="w-full bg-gradient-to-r from-amber-500 via-amber-400 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-gray-950 font-black h-11 rounded-xl shadow-lg mt-3 text-xs"
                  >
                    {manualMeetingLoading ? 'Assembling Board & Starting Debate...' : 'Begin Governed Deliberation'}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      {/* 2. Main Executive Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
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
              <div className="rounded-3xl p-4 bg-gradient-to-r from-amber-950/30 via-gray-950 to-yellow-950/20 border border-amber-500/30 shadow-xl">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5 text-amber-400 shrink-0">
                    <div className="h-9 w-9 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shadow-inner">
                      <Gavel size={17} className="text-amber-400" />
                    </div>
                    <div>
                      <span className="text-xs font-black text-white block">Chairman Binding Directive</span>
                      <span className="text-[10px] text-gray-400 block">Inject real-time executive constraints or steer active deliberations</span>
                    </div>
                  </div>

                  <div className="flex-1 flex items-center gap-2">
                    <Input
                      placeholder="e.g. 'Cap SDR spend at $8,000 for 30-day pilot', 'Require 2 customer reference calls'..."
                      value={chairmanDirective}
                      onChange={(e) => setChairmanDirective(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') void handleChairmanIntervene(); }}
                      className="bg-gray-900/90 border-gray-800 text-white rounded-xl text-xs h-9 focus:border-amber-500"
                    />
                    <Button
                      size="sm"
                      disabled={isSubmittingDirective || !chairmanDirective.trim()}
                      onClick={handleChairmanIntervene}
                      className="bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-black text-xs h-9 px-4 rounded-xl shrink-0 shadow-lg cursor-pointer"
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

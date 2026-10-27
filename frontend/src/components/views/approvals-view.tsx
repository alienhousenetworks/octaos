'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Search,
  Filter,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Send,
  Sparkles,
  Layers,
  ArrowUpRight,
  UserCheck,
  Code2,
  FileText,
  Mail,
  Share2,
  CreditCard,
  Bot,
} from 'lucide-react';
import { notify } from '@/lib/notify';

interface ApprovalsViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
}

type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'all';
type CategoryFilter = 'all' | 'public_post' | 'first_touch_email' | 'refund' | 'agent_action';

interface ApprovalItem {
  id: string;
  action_type: string;
  channel?: string | null;
  agent_name?: string | null;
  title: string;
  payload: Record<string, any>;
  confidence?: number | null;
  status: string;
  policy_reason?: string | null;
  created_at?: string | null;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  review_note?: string | null;
  action_fingerprint?: string | null;
  action_binding?: Record<string, any> | null;
  execution_status?: string | null;
  execution_error?: string | null;
}

interface Metrics {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

export default function ApprovalsView({
  token,
  API_URL,
  fetchWithAuth,
}: ApprovalsViewProps) {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [metrics, setMetrics] = useState<Metrics>({ total: 0, pending: 0, approved: 0, rejected: 0 });
  const [loading, setLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  // Filters
  const [activeTab, setActiveTab] = useState<ApprovalStatus>('pending');
  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showRawPayload, setShowRawPayload] = useState<Record<string, boolean>>({});
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [bindingDrafts, setBindingDrafts] = useState<Record<string, string>>({});
  const [bindingSaveInProgress, setBindingSaveInProgress] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [itemsRes, metricsRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/enterprise/approvals?status=${activeTab}&limit=100`),
        fetchWithAuth(`${API_URL}/enterprise/approvals/metrics`),
      ]);

      if (itemsRes.ok) {
        const data = await itemsRes.json();
        setItems(Array.isArray(data) ? data : []);
      }
      if (metricsRes.ok) {
        const m = await metricsRes.json();
        setMetrics(m);
      }
    } catch (e: any) {
      console.error('Failed to load approvals:', e);
      notify('Failed to load approvals queue');
    } finally {
      setLoading(false);
    }
  }, [token, API_URL, fetchWithAuth, activeTab]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const requiresExactBinding = (item: ApprovalItem) => {
    const highRiskTypes = new Set([
      'first_touch_email', 'email_dispatch', 'public_post', 'price_quote', 'refund',
      'linkedin_dm', 'email.send', 'email.delete', 'crm.delete', 'payment',
      'billing', 'contract.sign', 'user.delete', 'browser.submit', 'webhook_post',
    ]);
    return highRiskTypes.has(item.action_type) && !item.action_fingerprint;
  };

  const handleReview = async (id: string, approve: boolean) => {
    const selected = items.find((item) => item.id === id);
    if (approve && selected && requiresExactBinding(selected)) {
      notify('Cannot approve: this action has no persisted exact-action fingerprint. Recreate it with an action binding.');
      return;
    }
    const note = reviewNotes[id] || (approve ? 'Approved from Enterprise Console' : 'Rejected by reviewer');
    setActionInProgress(id);

    // Optimistic UI update
    setItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              status: approve ? 'approved' : 'rejected',
              review_note: note,
              reviewed_at: new Date().toISOString(),
            }
          : item
      )
    );

    try {
      const res = await fetchWithAuth(`${API_URL}/enterprise/approvals/${id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approve, note }),
      });

      if (res.ok) {
        const response = await res.json().catch(() => ({}));
        notify(response.message || (approve ? 'Approval recorded' : 'Action rejected'));
        // Refresh metrics and current list
        loadData();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to submit review');
        loadData();
      }
    } catch (e) {
      console.error('Review error:', e);
      notify('Network error submitting decision');
      loadData();
    } finally {
      setActionInProgress(null);
    }
  };


  const saveActionBinding = async (item: ApprovalItem) => {
    const raw = bindingDrafts[item.id];
    if (!raw) {
      notify('Enter the exact action binding JSON before saving.');
      return;
    }
    let binding: Record<string, any>;
    try {
      binding = JSON.parse(raw);
    } catch {
      notify('Action binding must be valid JSON.');
      return;
    }
    setBindingSaveInProgress(item.id);
    try {
      const res = await fetchWithAuth(`${API_URL}/enterprise/approvals/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_binding: binding }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to save action binding');
        return;
      }
      notify('Action binding saved. Review state was reset; the action must be approved again.');
      setBindingDrafts((prev) => {
        const next = { ...prev };
        delete next[item.id];
        return next;
      });
      await loadData();
    } catch {
      notify('Network error saving action binding');
    } finally {
      setBindingSaveInProgress(null);
    }
  };

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // Category filter
      if (selectedCategory !== 'all') {
        if (selectedCategory === 'agent_action') {
          if (['public_post', 'first_touch_email', 'refund'].includes(item.action_type)) return false;
        } else if (item.action_type !== selectedCategory) {
          return false;
        }
      }

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = item.title?.toLowerCase().includes(q);
        const matchesReason = item.policy_reason?.toLowerCase().includes(q);
        const matchesAgent = item.agent_name?.toLowerCase().includes(q);
        const matchesChannel = item.channel?.toLowerCase().includes(q);
        const matchesPayload = JSON.stringify(item.payload || {}).toLowerCase().includes(q);
        return matchesTitle || matchesReason || matchesAgent || matchesChannel || matchesPayload;
      }

      return true;
    });
  }, [items, selectedCategory, searchQuery]);

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'public_post':
        return <Share2 className="w-3.5 h-3.5 text-blue-400" />;
      case 'first_touch_email':
      case 'email_dispatch':
        return <Mail className="w-3.5 h-3.5 text-amber-400" />;
      case 'refund':
      case 'price_quote':
        return <CreditCard className="w-3.5 h-3.5 text-emerald-400" />;
      default:
        return <Bot className="w-3.5 h-3.5 text-violet-400" />;
    }
  };

  const getConfidenceBadge = (confidence?: number | null) => {
    if (confidence === null || confidence === undefined) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-400 border border-zinc-700/60">
          N/A Conf
        </span>
      );
    }
    const pct = Math.round(confidence * 100);
    if (pct >= 85) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <ShieldCheck className="w-3 h-3" />
          {pct}% Conf
        </span>
      );
    }
    if (pct >= 60) {
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertTriangle className="w-3 h-3" />
          {pct}% Conf
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20">
        <AlertTriangle className="w-3 h-3" />
        {pct}% Low
      </span>
    );
  };

  const passRate = useMemo(() => {
    if (!metrics.total) return 100;
    return Math.round((metrics.approved / metrics.total) * 100);
  }, [metrics]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-16">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono mb-1">
            <span>Operations</span>
            <span>/</span>
            <span className="text-zinc-200">Governance & Human-in-the-Loop</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white flex items-center gap-2.5">
            Approvals Pipeline
            {metrics.pending > 0 && (
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 font-mono">
                {metrics.pending} pending
              </span>
            )}
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Enterprise verification gates for autonomous AI agents, social posts, outbound communications, and financial decisions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={loadData}
            disabled={loading}
            variant="outline"
            size="sm"
            className="h-8 border-white/[0.08] bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 text-xs font-medium gap-1.5 rounded-md"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-zinc-400' : ''}`} />
            Refresh Queue
          </Button>
        </div>
      </div>

      {/* Metric Cards (GCP/Apple style KPI Strip) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Pending Review</span>
            <Clock className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{metrics.pending}</span>
            <span className="text-[11px] text-amber-400/90 font-medium">Requires sign-off</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Approved Actions</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{metrics.approved}</span>
            <span className="text-[11px] text-emerald-400/90 font-medium">Executed to live</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Rejected Actions</span>
            <XCircle className="w-3.5 h-3.5 text-zinc-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{metrics.rejected}</span>
            <span className="text-[11px] text-zinc-400 font-medium">Blocked by policy</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Approval Ratio</span>
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{passRate}%</span>
            <span className="text-[11px] text-zinc-400 font-medium">Of total decisions</span>
          </div>
        </div>
      </div>

      {/* Tabs & Filters Bar */}
      <div className="space-y-3">
        {/* Apple/GCP Segmented Control */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="inline-flex p-1 rounded-lg bg-zinc-900/90 border border-white/[0.08]">
            <button
              onClick={() => setActiveTab('pending')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'pending'
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Pending ({metrics.pending})
            </button>
            <button
              onClick={() => setActiveTab('approved')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'approved'
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Approved ({metrics.approved})
            </button>
            <button
              onClick={() => setActiveTab('rejected')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'rejected'
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Rejected ({metrics.rejected})
            </button>
            <button
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'all'
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              All Records ({metrics.total})
            </button>
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search actions or agents…"
              className="h-8 pl-8 text-xs bg-zinc-900/60 border-white/[0.08] focus:border-zinc-500 rounded-md placeholder:text-zinc-500"
            />
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs text-zinc-400 scrollbar-none">
          <span className="text-[11px] text-zinc-500 uppercase tracking-wider font-semibold mr-1">Category:</span>
          {(
            [
              { id: 'all', label: 'All Items' },
              { id: 'public_post', label: 'Social & Posts' },
              { id: 'first_touch_email', label: 'Outbound Emails' },
              { id: 'refund', label: 'Financial & Quotes' },
              { id: 'agent_action', label: 'Agent Tasks' },
            ] as const
          ).map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedCategory(c.id)}
              className={`px-2.5 py-1 rounded-md text-xs transition-colors whitespace-nowrap ${
                selectedCategory === c.id
                  ? 'bg-white/[0.08] text-white font-medium border border-white/[0.12]'
                  : 'text-zinc-400 hover:text-zinc-200 border border-transparent hover:border-white/[0.06]'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* List of Approval Items */}
      <div className="space-y-3">
        {loading && items.length === 0 ? (
          <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-12 text-center text-xs text-zinc-400">
            <RefreshCw className="w-5 h-5 mx-auto mb-2 animate-spin text-zinc-500" />
            Loading approval queue…
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-12 text-center">
            <div className="w-10 h-10 rounded-full bg-zinc-800/80 text-zinc-400 flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-sm font-medium text-white">No actions require attention</h3>
            <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
              {searchQuery || selectedCategory !== 'all'
                ? 'No approval items match your current filter criteria.'
                : 'All pending agent proposals have been reviewed and dispatched.'}
            </p>
          </div>
        ) : (
          filteredItems.map((item) => {
            const isExpanded = expandedId === item.id;
            const isPending = item.status === 'pending';
            const showRaw = showRawPayload[item.id] || false;

            return (
              <div
                key={item.id}
                className={`rounded-xl border transition-all ${
                  isPending
                    ? 'border-white/[0.08] bg-[#111318] hover:border-white/[0.14]'
                    : 'border-white/[0.05] bg-[#0e1014] opacity-90'
                }`}
              >
                {/* Card Header Row */}
                <div className="p-4 sm:p-5">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Action Type Badge */}
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded-md bg-zinc-800/80 text-zinc-300 border border-zinc-700/50">
                          {getActionIcon(item.action_type)}
                          {item.action_type}
                        </span>

                        {/* Agent Origin */}
                        {item.agent_name && (
                          <span className="text-[11px] text-zinc-400 flex items-center gap-1 font-medium">
                            via <span className="text-zinc-200">{item.agent_name}</span>
                          </span>
                        )}

                        {/* Channel Badge */}
                        {item.channel && (
                          <span className="text-[11px] text-zinc-500 font-mono">
                            • {item.channel.toUpperCase()}
                          </span>
                        )}

                        {/* Confidence Score */}
                        {getConfidenceBadge(item.confidence)}

                        {/* Status Chip if not pending */}
                        {!isPending && (
                          <span
                            className={`text-[11px] font-mono font-medium px-2 py-0.5 rounded-md ${
                              item.status === 'approved'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}
                          >
                            {item.status.toUpperCase()}
                          </span>
                        )}
                      </div>

                      <h3 className="text-sm font-semibold text-white tracking-tight break-words">
                        {item.title}
                      </h3>

                      {item.policy_reason && (
                        <div className="text-xs text-amber-300/80 flex items-center gap-1.5 font-medium">
                          <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
                          <span>{item.policy_reason}</span>
                        </div>
                      )}
                      {item.execution_status && (
                        <div className="text-xs text-sky-300/90 flex items-center gap-1.5">
                          <Clock className="w-3 h-3 shrink-0" />
                          <span>Execution: {item.execution_status}</span>
                          {item.execution_error && <span className="text-rose-300">— {item.execution_error}</span>}
                        </div>
                      )}
                    </div>

                    {/* Quick Action Buttons (when pending) */}
                    {isPending ? (
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          size="sm"
                          onClick={() => handleReview(item.id, true)}
                          disabled={actionInProgress === item.id || requiresExactBinding(item)}
                          title={requiresExactBinding(item) ? "Exact action binding required before approval" : undefined}
                          className="h-8 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs rounded-lg px-3.5 shadow-sm shadow-emerald-950 flex items-center gap-1.5"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleReview(item.id, false)}
                          disabled={actionInProgress === item.id}
                          className="h-8 border-white/[0.08] bg-zinc-900/60 hover:bg-rose-950/40 hover:text-rose-300 hover:border-rose-800/40 text-zinc-300 text-xs font-medium rounded-lg px-3"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          Reject
                        </Button>
                        {requiresExactBinding(item) && (
                          <span className="max-w-[220px] text-[11px] leading-4 text-amber-300/90">
                            Exact action binding missing — approval is blocked for safety.
                          </span>
                        )}
                      </div>
                    ) : (
                      <div className="text-right text-[11px] text-zinc-500 font-mono shrink-0">
                        {item.reviewed_at && (
                          <div>{new Date(item.reviewed_at).toLocaleDateString()} {new Date(item.reviewed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                        )}
                        {item.reviewed_by && <div className="text-zinc-400">by {item.reviewed_by}</div>}
                      </div>
                    )}
                  </div>

                  {/* Summary Preview Snippet */}
                  {item.payload?.content || item.payload?.draft ? (
                    <div className="mt-3 p-3 rounded-lg bg-black/40 border border-white/[0.06] text-xs text-zinc-300 font-sans leading-relaxed whitespace-pre-wrap line-clamp-3">
                      {item.payload.content || item.payload.draft}
                    </div>
                  ) : null}

                  {/* Expand / Collapse Details Bar */}
                  <div className="mt-3 pt-3 border-t border-white/[0.05] flex items-center justify-between text-xs">
                    <div className="text-[11px] text-zinc-500 font-mono">
                      {item.created_at ? `Generated ${new Date(item.created_at).toLocaleString()}` : ''}
                    </div>

                    <button
                      onClick={() => setExpandedId(isExpanded ? null : item.id)}
                      className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 font-medium transition-colors"
                    >
                      {isExpanded ? (
                        <>
                          Hide Payload & Inspector <ChevronUp className="w-3.5 h-3.5" />
                        </>
                      ) : (
                        <>
                          Inspect Specifications <ChevronDown className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded Inspection Drawer */}
                {isExpanded && (
                  <div className="border-t border-white/[0.08] bg-black/20 p-4 sm:p-5 space-y-4">
                    {/* Review Note / Rationale Input (if pending) */}
                    {isPending && (
                      <div className="space-y-1.5">
                        <label className="text-[11px] uppercase tracking-wider text-zinc-400 font-semibold block">
                          Reviewer Annotation & Audit Note (Optional)
                        </label>
                        <Input
                          value={reviewNotes[item.id] || ''}
                          onChange={(e) =>
                            setReviewNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          placeholder="e.g. Cleared with Marketing lead; tone verified."
                          className="h-8 text-xs bg-zinc-900/80 border-white/[0.08] focus:border-zinc-500 rounded-md"
                        />
                      </div>
                    )}


                    {/* Exact action binding editor: saving resets the approval decision. */}
                    {isPending && (
                      <div className="space-y-2 rounded-lg border border-amber-500/20 bg-amber-500/[0.04] p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[11px] uppercase tracking-wider text-amber-200 font-semibold">
                            Exact action binding
                          </span>
                          {item.action_fingerprint && (
                            <span className="text-[10px] text-emerald-300 font-mono">Fingerprint persisted</span>
                          )}
                        </div>
                        <p className="text-xs text-zinc-400">
                          Bind this approval to one run, bot, tool, target, payload and policy version. Saving recalculates the fingerprint and resets any previous decision.
                        </p>
                        <Textarea
                          value={bindingDrafts[item.id] ?? JSON.stringify(item.action_binding ?? {
                            run_id: String(item.resource_id || ''),
                            bot_id: '',
                            tool_name: item.action_type,
                            target: '',
                            payload: {},
                            policy_version: '1',
                          }, null, 2)}
                          onChange={(e) => setBindingDrafts((prev) => ({ ...prev, [item.id]: e.target.value }))}
                          className="min-h-40 text-xs font-mono bg-zinc-950 border-white/[0.1]"
                          aria-label="Exact action binding JSON"
                        />
                        <div className="flex justify-end">
                          <Button
                            size="sm"
                            onClick={() => saveActionBinding(item)}
                            disabled={bindingSaveInProgress === item.id}
                            className="text-xs"
                          >
                            {bindingSaveInProgress === item.id ? 'Saving…' : 'Save binding and reset review'}
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Formatted Content Preview */}
                    {item.payload && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] uppercase tracking-wider text-zinc-400 font-semibold flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5 text-zinc-400" />
                            Payload Specifications
                          </span>
                          <button
                            onClick={() =>
                              setShowRawPayload((prev) => ({ ...prev, [item.id]: !prev[item.id] }))
                            }
                            className="text-[11px] text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1"
                          >
                            <Code2 className="w-3 h-3" />
                            {showRaw ? 'Show Formatted View' : 'View Raw JSON'}
                          </button>
                        </div>

                        {showRaw ? (
                          <pre className="text-xs font-mono p-3 rounded-lg bg-black/60 border border-white/[0.08] text-zinc-300 overflow-x-auto max-h-64">
                            {JSON.stringify(item.payload, null, 2)}
                          </pre>
                        ) : (
                          <div className="rounded-lg bg-black/40 border border-white/[0.06] p-3 text-xs space-y-2 font-mono">
                            {Object.entries(item.payload).map(([key, val]) => (
                              <div key={key} className="grid grid-cols-1 sm:grid-cols-[140px_minmax(0,1fr)] gap-1">
                                <span className="text-zinc-500">{key}:</span>
                                <span className="text-zinc-200 font-sans break-words whitespace-pre-wrap">
                                  {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Historical Review Note if already completed */}
                    {item.review_note && (
                      <div className="p-3 rounded-lg bg-zinc-900/60 border border-white/[0.06] text-xs">
                        <span className="text-zinc-500 block text-[11px] font-semibold uppercase tracking-wider">
                          Review Note:
                        </span>
                        <p className="text-zinc-200 mt-0.5">{item.review_note}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

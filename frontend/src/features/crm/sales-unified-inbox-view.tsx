'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Mail,
  MessageSquare,
  Phone,
  Send,
  Sparkles,
  Play,
  Pause,
  RefreshCw,
  Search,
  CheckCircle2,
  Clock,
  AlertCircle,
  Building2,
  User,
  ShieldCheck,
  ChevronRight,
  Loader2,
  Layers,
  ArrowUpRight,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { notify } from '@/lib/notify';

function LinkedInIcon({ size = 14, className = 'text-sky-400' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
      <rect x="2" y="9" width="4" height="12" />
      <circle cx="4" cy="4" r="2" />
    </svg>
  );
}

interface ThreadItem {
  lead_id: string;
  contact_name: string;
  company: string;
  email: string;
  phone: string;
  status: string;
  channel: string;
  message_count: number;
  unread: boolean;
  last_message: {
    direction: string;
    content: string;
    author: string;
    at: string;
  };
  deal_room_id?: string | null;
  deal_room_stage?: string;
  cadence_active: boolean;
  cadence_paused: boolean;
  next_step?: {
    day: number;
    channel: string;
    content: string;
    status: string;
  } | null;
}

interface MessageItem {
  id: string;
  direction: 'inbound' | 'outbound';
  channel: string;
  subject?: string;
  content: string;
  author: string;
  at: string;
  sent?: boolean;
  delivery_details?: string;
}

interface ThreadDetail {
  lead: {
    id: string;
    name: string;
    email: string;
    phone: string;
    company: string;
    status: string;
    score?: number;
    priority?: string;
    committee_role?: string;
    domain_archetype?: string;
    cadence_paused?: boolean;
  };
  deal_room?: {
    id: string;
    stage: string;
    is_multi_threaded?: boolean;
  } | null;
  messages: MessageItem[];
  schedule: Array<{
    day: number;
    channel: string;
    content: string;
    status: string;
    sent_at?: string;
  }>;
}

interface SalesUnifiedInboxViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

export default function SalesUnifiedInboxView({
  token,
  API_URL,
  fetchWithAuth,
}: SalesUnifiedInboxViewProps) {
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);

  const [activeThread, setActiveThread] = useState<ThreadDetail | null>(null);
  const [loadingMessages, setLoadingMessages] = useState(false);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [channelFilter, setChannelFilter] = useState<'all' | 'email' | 'whatsapp' | 'linkedin'>('all');

  // Composer State
  const [replyBody, setReplyBody] = useState('');
  const [replySubject, setReplySubject] = useState('');
  const [replyChannel, setReplyChannel] = useState<'email' | 'whatsapp'>('email');
  const [sending, setSending] = useState(false);

  // Cadence State
  const [cadenceStats, setCadenceStats] = useState<any>(null);
  const [runningCadence, setRunningCadence] = useState(false);

  // AI Suggestions
  const [suggesting, setSuggesting] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<any[]>([]);

  // 1. Fetch Threads
  const fetchThreads = async () => {
    if (!token) return;
    setLoadingThreads(true);
    try {
      const q = new URLSearchParams();
      if (channelFilter !== 'all') q.set('channel', channelFilter);
      if (searchQuery.trim()) q.set('search', searchQuery.trim());

      const res = await fetchWithAuth(`${API_URL}/sales-inbox/threads?${q.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setThreads(data);
        if (!selectedLeadId && data.length > 0) {
          setSelectedLeadId(data[0].lead_id);
        }
      }
    } catch (err) {
      console.error('Failed to load threads:', err);
    } finally {
      setLoadingThreads(false);
    }
  };

  // 2. Fetch Cadence Stats
  const fetchCadenceStats = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-inbox/cadence/stats`);
      if (res.ok) {
        const stats = await res.json();
        setCadenceStats(stats);
      }
    } catch (err) {
      console.error('Failed to load cadence stats:', err);
    }
  };

  // 3. Fetch Selected Thread Messages
  const fetchThreadDetail = async (leadId: string) => {
    if (!token || !leadId) return;
    setLoadingMessages(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-inbox/threads/${leadId}/messages`);
      if (res.ok) {
        const detail: ThreadDetail = await res.json();
        setActiveThread(detail);
        setReplySubject(`Re: Partnership Discussion with ${detail.lead.company || 'your team'}`);
        // Fetch AI suggestions for this lead
        fetchAiSuggestions(leadId);
      }
    } catch (err) {
      console.error('Failed to load thread messages:', err);
    } finally {
      setLoadingMessages(false);
    }
  };

  const fetchAiSuggestions = async (leadId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-inbox/threads/${leadId}/ai-suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent: 'demo_booking' }),
      });
      if (res.ok) {
        const data = await res.json();
        setAiSuggestions(data.suggestions || []);
      }
    } catch (err) {
      console.error('Failed to fetch AI suggestions:', err);
    }
  };

  useEffect(() => {
    fetchThreads();
    fetchCadenceStats();
  }, [channelFilter]);

  useEffect(() => {
    if (selectedLeadId) {
      fetchThreadDetail(selectedLeadId);
    }
  }, [selectedLeadId]);

  // Handle Send Reply
  const handleSendReply = async () => {
    if (!selectedLeadId || !replyBody.trim()) {
      notify('Please enter a message body.');
      return;
    }

    setSending(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-inbox/threads/${selectedLeadId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: replyChannel,
          body: replyBody.trim(),
          subject: replyChannel === 'email' ? replySubject.trim() : undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        notify(data.message || 'Outbound reply dispatched successfully');
        setReplyBody('');
        // Refresh active thread
        await fetchThreadDetail(selectedLeadId);
        await fetchThreads();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to dispatch reply');
      }
    } catch (err) {
      console.error(err);
      notify('Network error sending reply');
    } finally {
      setSending(false);
    }
  };

  // Trigger Immediate Cadence Run
  const handleTriggerCadenceRun = async () => {
    setRunningCadence(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-inbox/cadence/run?max_touches=50`, {
        method: 'POST',
      });
      if (res.ok) {
        const result = await res.json();
        notify(
          `Cadence Runner executed: ${result.touches_sent || 0} sent, ${result.cadences_halted_on_reply || 0} halted on reply`
        );
        await fetchCadenceStats();
        await fetchThreads();
        if (selectedLeadId) await fetchThreadDetail(selectedLeadId);
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to run cadence');
      }
    } catch (err) {
      console.error(err);
      notify('Network error executing cadence runner');
    } finally {
      setRunningCadence(false);
    }
  };

  // Toggle Pause/Resume Lead Cadence
  const handleTogglePauseCadence = async () => {
    if (!selectedLeadId || !activeThread) return;
    const isCurrentlyPaused = Boolean(activeThread.lead.cadence_paused);
    const endpoint = isCurrentlyPaused ? 'resume-cadence' : 'pause-cadence';

    try {
      const res = await fetchWithAuth(`${API_URL}/sales-inbox/threads/${selectedLeadId}/${endpoint}`, {
        method: 'POST',
      });
      if (res.ok) {
        notify(isCurrentlyPaused ? 'Cadence resumed for lead' : 'Cadence paused for lead');
        await fetchThreadDetail(selectedLeadId);
        await fetchThreads();
        await fetchCadenceStats();
      }
    } catch {
      notify('Failed to update cadence state');
    }
  };

  const getChannelIcon = (ch: string, size = 14) => {
    const c = ch.toLowerCase();
    if (c === 'whatsapp') return <MessageSquare size={size} className="text-emerald-400" />;
    if (c === 'linkedin') return <LinkedInIcon size={size} className="text-sky-400" />;
    if (c === 'call' || c === 'phone') return <Phone size={size} className="text-amber-400" />;
    return <Mail size={size} className="text-indigo-400" />;
  };

  const formatTimestamp = (iso?: string) => {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffHrs = (now.getTime() - d.getTime()) / (1000 * 3600);
      if (diffHrs < 24) {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Cadence Dispatch & Metrics Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-100">Omnichannel Unified Inbox</h2>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Phase 2 Durable Engine
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Live multi-channel message thread stream across Email, WhatsApp, and LinkedIn with atomic stop-on-reply.
            </p>
          </div>
        </div>

        {/* Right Stats & Run Button */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
          {cadenceStats && (
            <div className="hidden sm:flex items-center gap-3 text-xs bg-slate-950/80 border border-slate-800 px-3 py-1.5 rounded-lg">
              <div>
                <span className="text-slate-500">Enrolled:</span>{' '}
                <strong className="text-slate-200">{cadenceStats.active_enrolled_leads}</strong>
              </div>
              <span className="text-slate-700">•</span>
              <div>
                <span className="text-slate-500">Pending:</span>{' '}
                <strong className="text-amber-400">{cadenceStats.pending_touches}</strong>
              </div>
              <span className="text-slate-700">•</span>
              <div>
                <span className="text-slate-500">Delivered:</span>{' '}
                <strong className="text-emerald-400">{cadenceStats.completed_touches}</strong>
              </div>
            </div>
          )}

          <Button
            type="button"
            size="sm"
            onClick={handleTriggerCadenceRun}
            disabled={runningCadence}
            className="gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-600/20"
          >
            {runningCadence ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span>Dispatch Cadences Now</span>
          </Button>
        </div>
      </div>

      {/* Main 3-Pane Enterprise Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-[680px]">
        {/* ── LEFT PANE: THREAD LIST (col-span-3) ── */}
        <div className="lg:col-span-3 bg-slate-900/90 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          {/* Search & Channel Filter */}
          <div className="p-3 border-b border-slate-800 space-y-2.5">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
              <Input
                placeholder="Search leads, companies..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchThreads()}
                className="pl-8 h-8 text-xs bg-slate-950 border-slate-800 text-slate-200 placeholder:text-slate-500"
              />
            </div>

            {/* Filter Chips */}
            <div className="flex items-center gap-1">
              {(['all', 'email', 'whatsapp', 'linkedin'] as const).map((ch) => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => setChannelFilter(ch)}
                  className={`px-2 py-1 rounded-md text-[11px] font-medium transition-colors capitalize ${
                    channelFilter === ch
                      ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {ch === 'all' ? 'All Channels' : ch}
                </button>
              ))}
            </div>
          </div>

          {/* Thread Cards List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800/60 max-h-[580px]">
            {loadingThreads ? (
              <div className="flex flex-col items-center justify-center p-8 text-slate-500 gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                <span className="text-xs">Loading conversations…</span>
              </div>
            ) : threads.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                No active conversation threads found matching filters.
              </div>
            ) : (
              threads.map((t) => {
                const isSelected = t.lead_id === selectedLeadId;
                return (
                  <div
                    key={t.lead_id}
                    onClick={() => setSelectedLeadId(t.lead_id)}
                    className={`p-3 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-indigo-600/10 border-l-4 border-indigo-500 text-slate-100'
                        : 'hover:bg-slate-800/50 text-slate-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1 mb-1">
                      <div className="flex items-center gap-1.5 truncate">
                        {getChannelIcon(t.channel, 13)}
                        <span className="font-semibold text-xs truncate text-slate-100">
                          {t.contact_name}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 shrink-0">
                        {formatTimestamp(t.last_message.at)}
                      </span>
                    </div>

                    <div className="text-[11px] font-medium text-slate-400 truncate mb-1">
                      {t.company}
                    </div>

                    <p className="text-[11px] text-slate-500 line-clamp-1 italic">
                      {t.last_message.content || 'Cadence sequence active'}
                    </p>

                    <div className="flex items-center gap-1.5 mt-2">
                      {t.cadence_paused ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          Paused
                        </span>
                      ) : t.cadence_active && t.next_step ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" /> Day {t.next_step.day} {t.next_step.channel}
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-slate-800 text-slate-400">
                          {t.status}
                        </span>
                      )}

                      {t.unread && (
                        <span className="ml-auto w-2 h-2 rounded-full bg-indigo-500 ring-2 ring-indigo-500/30 shrink-0" />
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ── CENTER PANE: CONVERSATION STREAM & COMPOSER (col-span-6) ── */}
        <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
          {activeThread ? (
            <>
              {/* Thread Header */}
              <div className="p-3.5 border-b border-slate-800 flex items-center justify-between gap-3 bg-slate-950/60">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm">
                    {activeThread.lead.name.charAt(0)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-100">{activeThread.lead.name}</h3>
                      <span className="text-xs text-slate-400 font-medium">@{activeThread.lead.company}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 flex items-center gap-2">
                      <span>{activeThread.lead.email}</span>
                      {activeThread.lead.phone && (
                        <>
                          <span>•</span>
                          <span>{activeThread.lead.phone}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Cadence Control Button */}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleTogglePauseCadence}
                  className="h-7 text-xs gap-1.5 border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
                >
                  {activeThread.lead.cadence_paused ? (
                    <>
                      <Play className="w-3 h-3 text-emerald-400" /> Resume Cadence
                    </>
                  ) : (
                    <>
                      <Pause className="w-3 h-3 text-amber-400" /> Pause Cadence
                    </>
                  )}
                </Button>
              </div>

              {/* Message Bubbles Container */}
              <div className="flex-1 p-4 overflow-y-auto space-y-4 max-h-[380px] bg-slate-950/30">
                {loadingMessages ? (
                  <div className="flex flex-col items-center justify-center h-48 text-slate-500 gap-2">
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                    <span className="text-xs">Fetching messages…</span>
                  </div>
                ) : activeThread.messages.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 text-xs italic">
                    No communication records logged yet. Use the composer below to dispatch the first touch.
                  </div>
                ) : (
                  activeThread.messages.map((m) => {
                    const isOutbound = m.direction === 'outbound';
                    return (
                      <div
                        key={m.id}
                        className={`flex flex-col ${isOutbound ? 'items-end' : 'items-start'}`}
                      >
                        <div className="flex items-center gap-1.5 mb-1 px-1 text-[11px] text-slate-500">
                          <span>{m.author}</span>
                          <span>•</span>
                          <span>{formatTimestamp(m.at)}</span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono uppercase bg-slate-950 text-slate-400 border border-slate-800">
                            {m.channel}
                          </span>
                        </div>

                        <div
                          className={`max-w-[85%] rounded-2xl p-3.5 text-xs leading-relaxed shadow-sm ${
                            isOutbound
                              ? 'bg-gradient-to-r from-indigo-900/60 to-indigo-800/40 border border-indigo-700/50 text-slate-100 rounded-br-none'
                              : 'bg-slate-800/80 border border-slate-700 text-slate-200 rounded-bl-none'
                          }`}
                        >
                          {m.subject && (
                            <div className="font-semibold text-indigo-300 pb-1.5 mb-1.5 border-b border-indigo-500/20">
                              {m.subject}
                            </div>
                          )}
                          <div className="whitespace-pre-wrap">{m.content}</div>
                          {m.delivery_details && (
                            <div className="text-[10px] text-slate-400 mt-2 pt-1 border-t border-slate-700/50 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              <span>{m.delivery_details}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* AI Suggestion Chips */}
              {aiSuggestions.length > 0 && (
                <div className="px-3.5 py-2 border-t border-slate-800/80 bg-slate-950/70 flex items-center gap-2 overflow-x-auto">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400 flex items-center gap-1 shrink-0">
                    <Sparkles className="w-3 h-3" /> AI Copilot:
                  </span>
                  {aiSuggestions.map((sug) => (
                    <button
                      key={sug.id}
                      type="button"
                      onClick={() => {
                        setReplyBody(sug.body);
                        if (sug.channel) setReplyChannel(sug.channel);
                        notify(`Applied template: "${sug.title}"`);
                      }}
                      className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shrink-0 transition-colors"
                    >
                      {sug.title}
                    </button>
                  ))}
                </div>
              )}

              {/* Multi-Channel Reply Composer */}
              <div className="p-3.5 border-t border-slate-800 bg-slate-950 space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-slate-400 font-medium">Channel:</span>
                    <button
                      type="button"
                      onClick={() => setReplyChannel('email')}
                      className={`px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1 transition-colors ${
                        replyChannel === 'email'
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <Mail className="w-3 h-3" /> Email
                    </button>
                    <button
                      type="button"
                      onClick={() => setReplyChannel('whatsapp')}
                      className={`px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1 transition-colors ${
                        replyChannel === 'whatsapp'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <MessageSquare className="w-3 h-3" /> WhatsApp
                    </button>
                  </div>
                </div>

                {replyChannel === 'email' && (
                  <Input
                    placeholder="Subject line..."
                    value={replySubject}
                    onChange={(e) => setReplySubject(e.target.value)}
                    className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-200"
                  />
                )}

                <Textarea
                  placeholder={`Type your reply to ${activeThread.lead.name} via ${replyChannel}...`}
                  value={replyBody}
                  onChange={(e) => setReplyBody(e.target.value)}
                  rows={3}
                  className="text-xs bg-slate-900 border-slate-800 text-slate-200 resize-none"
                />

                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    Real dispatch via {replyChannel === 'email' ? 'authenticated SMTP/Gmail' : 'Meta WhatsApp Cloud API'}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleSendReply}
                    disabled={sending || !replyBody.trim()}
                    className="gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs px-4"
                  >
                    {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    <span>Send Message</span>
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center flex-1 p-8 text-slate-500 gap-2">
              <Mail className="w-8 h-8 text-slate-600" />
              <p className="text-xs">Select a conversation thread to inspect messages and reply.</p>
            </div>
          )}
        </div>

        {/* ── RIGHT PANE: DOSSIER & CADENCE PROGRESSION (col-span-3) ── */}
        <div className="lg:col-span-3 space-y-4">
          {activeThread ? (
            <>
              {/* Account Quick Card */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Prospect Profile
                  </span>
                  {activeThread.lead.score && (
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      Score: {activeThread.lead.score}/100
                    </span>
                  )}
                </div>

                <div>
                  <h4 className="text-sm font-bold text-slate-100">{activeThread.lead.name}</h4>
                  <div className="text-xs text-indigo-400 font-medium">{activeThread.lead.company}</div>
                </div>

                <div className="space-y-1.5 text-xs text-slate-400">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Committee Role:</span>
                    <span className="font-medium text-slate-300 capitalize">
                      {activeThread.lead.committee_role?.replace('_', ' ') || 'Economic Buyer'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Pipeline Stage:</span>
                    <span className="font-medium text-emerald-400 capitalize">
                      {activeThread.deal_room?.stage || activeThread.lead.status}
                    </span>
                  </div>
                </div>

                {activeThread.deal_room?.id && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (typeof window !== 'undefined') {
                        window.location.href = `/app/sales/deals?deal=${activeThread.deal_room?.id}`;
                      }
                    }}
                    className="w-full text-xs gap-1.5 border-slate-700 bg-slate-950 text-slate-300 hover:bg-slate-800"
                  >
                    <span>Open Deal Room</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </Button>
                )}
              </div>

              {/* Cadence Progression Stepper */}
              <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Cadence Sequence
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {activeThread.schedule.length} Touches
                  </span>
                </div>

                <div className="space-y-2">
                  {activeThread.schedule.map((step, idx) => {
                    const isSent = step.status === 'sent';
                    const isPending = step.status === 'pending';
                    const isHalted = step.status.includes('halted') || step.status === 'cancelled';
                    const isSuppressed = step.status === 'suppressed';

                    return (
                      <div
                        key={idx}
                        className={`p-2 rounded-lg border text-xs transition-colors ${
                          isSent
                            ? 'bg-emerald-500/5 border-emerald-500/20 text-slate-200'
                            : isPending
                            ? 'bg-indigo-500/5 border-indigo-500/20 text-slate-300'
                            : isHalted
                            ? 'bg-amber-500/5 border-amber-500/20 text-slate-400'
                            : 'bg-slate-950 border-slate-800 text-slate-400'
                        }`}
                      >
                        <div className="flex items-center justify-between font-semibold">
                          <span className="flex items-center gap-1.5">
                            {getChannelIcon(step.channel, 12)}
                            <span>Day {step.day} • {step.channel}</span>
                          </span>
                          <span
                            className={`text-[10px] px-1.5 py-0.2 rounded font-mono capitalize ${
                              isSent
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : isPending
                                ? 'bg-indigo-500/20 text-indigo-300'
                                : isHalted
                                ? 'bg-amber-500/20 text-amber-300'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {step.status}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 line-clamp-1 mt-1">
                          {step.content}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 text-center text-slate-500 text-xs">
              Select a conversation to see the prospect dossier and cadence progression.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

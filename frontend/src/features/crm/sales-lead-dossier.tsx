'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  X, Mail, Phone, ExternalLink, Sparkles, Building, Calendar, 
  Send, Trash2, Edit3, MessageSquare, CheckCircle2, AlertCircle,
  Clock, Shield, ArrowRight, UserCheck, Loader2
} from 'lucide-react';
import { Lead, FollowUpStep } from './sales-types';

interface SalesLeadDossierProps {
  lead: Lead | null;
  onClose: () => void;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onSendOutreach: (leadId: string) => Promise<void>;
  onSendSmartOutreach: (leadId: string) => Promise<void>;
  onGenerateDraft: (leadId: string, instructions: string) => Promise<{ subject: string; body: string } | null>;
  onSendDraft: (leadId: string, subject: string, body: string) => Promise<void>;
  onSaveSchedule: (leadId: string, schedule: FollowUpStep[]) => Promise<void>;
  onBookMeeting: (leadId: string, suggestedTime: string) => Promise<void>;
  onDeleteLead: (leadId: string) => Promise<void>;
  onLogNote: (leadId: string, content: string, channel: string, direction: string) => Promise<void>;
  onSaveLead: (leadId: string, updates: Partial<Lead>) => Promise<void>;
  actionLoading: boolean;
}

export default function SalesLeadDossier({
  lead,
  onClose,
  onUpdateStatus,
  onSendOutreach,
  onSendSmartOutreach,
  onGenerateDraft,
  onSendDraft,
  onSaveSchedule,
  onBookMeeting,
  onDeleteLead,
  onLogNote,
  onSaveLead,
  actionLoading,
}: SalesLeadDossierProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'signals' | 'outreach' | 'followups' | 'edit'>('overview');
  const [noteText, setNoteText] = useState('');
  const [noteChannel, setNoteChannel] = useState('note');
  const [noteDirection, setNoteDirection] = useState('internal');
  const [meetingTime, setMeetingTime] = useState('');

  // Edit states
  const [editName, setEditName] = useState(lead?.name || '');
  const [editCompany, setEditCompany] = useState(lead?.company || '');
  const [editEmail, setEditEmail] = useState(lead?.email || '');
  const [editPhone, setEditPhone] = useState(lead?.phone || '');
  const [editWhy, setEditWhy] = useState(lead?.why || '');
  const [editCapacity, setEditCapacity] = useState(lead?.purchasing_capacity || lead?.how_much || '');
  const [editScore, setEditScore] = useState(lead?.score != null ? String(lead.score) : '');

  // Outreach draft + follow-up schedule (re-synced when a different lead opens or data changes)
  const [draftSubject, setDraftSubject] = useState(lead?.data?.draft_subject || '');
  const [draftBody, setDraftBody] = useState(lead?.data?.draft_body || '');
  const [draftInstructions, setDraftInstructions] = useState('');
  const [schedule, setSchedule] = useState<FollowUpStep[]>(lead?.data?.outreach_schedule || []);
  React.useEffect(() => {
    setDraftSubject(lead?.data?.draft_subject || '');
    setDraftBody(lead?.data?.draft_body || '');
    setSchedule(lead?.data?.outreach_schedule || []);
    setMeetingTime('');
  }, [lead?.id, lead?.data?.draft_body, lead?.data?.outreach_schedule]);

  if (!lead) return null;

  const d = lead.data || {};
  const websiteUrl = d.company?.website || lead.website || '';
  const whyNow = d.why_now || lead.why || '';
  const evidenceUrl = d.evidence_url || lead.evidence_url || '';
  const fresh = d.freshness || lead.freshness;
  const painPoints = d.pain_points || [];
  const capacity = d.purchasing_capacity || lead.purchasing_capacity || lead.how_much || '';
  const notCaptured = <span className="text-muted-foreground/60 font-normal">Not captured</span>;

  const updateStep = (i: number, patch: Partial<FollowUpStep>) =>
    setSchedule((s) => s.map((st, idx) => (idx === i ? { ...st, ...patch } : st)));

  const handleLogNoteSubmit = async () => {
    if (!noteText.trim()) return;
    await onLogNote(lead.id, noteText, noteChannel, noteDirection);
    setNoteText('');
  };

  const handleSaveEdit = async () => {
    const updates: Partial<Lead> = {
      name: editName,
      company: editCompany,
      email: editEmail,
      phone: editPhone,
      why: editWhy,
      how_much: editCapacity,
    };
    if (editScore.trim() !== '' && Number.isFinite(Number(editScore))) {
      updates.score = Number(editScore);
    }
    await onSaveLead(lead.id, updates);
    setActiveTab('overview');
  };

  const conversation = (lead.data?.conversation || []) as any[];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-white border-l border-slate-200 h-full shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-300 text-slate-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Strip (aitdk-inspired clean header) */}
        <div className="p-6 border-b border-slate-200 bg-white">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 text-blue-700 font-extrabold flex items-center justify-center text-lg shrink-0 shadow-xs">
                {lead.company?.charAt(0).toUpperCase() || 'C'}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-slate-900">
                    {lead.company}
                  </h2>
                  {websiteUrl && (
                    <a
                      href={websiteUrl.startsWith('http') ? websiteUrl : `https://${websiteUrl}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-400 hover:text-blue-600 transition-colors p-0.5"
                      title="Visit company website"
                    >
                      <ExternalLink size={13} />
                    </a>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Contact: <span className="text-slate-800 font-semibold">{lead.name}</span>
                  {d.contact?.title ? ` · ${d.contact.title}` : ''}
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Quick Actions & Status Strip */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-500">Stage:</span>
              <select
                value={lead.status}
                onChange={(e) => onUpdateStatus(lead.id, e.target.value)}
                className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-800 focus:border-blue-500 outline-none"
              >
                <option value="new">New Prospect</option>
                <option value="qualified">Qualified ICP</option>
                <option value="contacted">In Outreach</option>
                <option value="meeting_scheduled">Meeting Booked</option>
                <option value="closed_won">Closed Won</option>
                <option value="closed_lost">Closed Lost</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-500">AI Fit Score:</span>
              <span className="px-2.5 py-0.5 rounded-md text-xs font-extrabold bg-emerald-600 text-white shadow-xs flex items-center gap-1">
                <Sparkles size={12} className="text-emerald-100" /> {lead.score != null ? `${lead.score}/100` : 'Not scored'}
              </span>
            </div>
          </div>

          {/* Dossier Tabs (Ahrefs & aitdk clean tab navigation) */}
          <div className="flex items-center gap-1 mt-4 -mb-2 border-b border-slate-200 overflow-x-auto no-scrollbar">
            {[
              { id: 'overview', label: 'Overview & Fit' },
              { id: 'signals', label: 'Intelligence Signals' },
              { id: 'outreach', label: `Outreach (${conversation.length})` },
              { id: 'followups', label: `Follow-ups (${schedule.length})` },
              { id: 'edit', label: 'Edit Account' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-2 text-xs font-bold border-b-2 -mb-[1px] transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/40">
          {/* TAB 1: OVERVIEW & FIT */}
          {activeTab === 'overview' && (
            <div className="space-y-5">
              {/* Metric Highlights (aitdk-inspired spec cells) */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs">
                  <span className="text-[11px] font-bold uppercase text-slate-500 block">
                    Purchasing Capacity
                  </span>
                  <span className="text-xs font-extrabold text-slate-900 mt-1 block">
                    {capacity || notCaptured}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs">
                  <span className="text-[11px] font-bold uppercase text-slate-500 block">
                    Priority Tier
                  </span>
                  <span className="text-xs font-extrabold text-slate-900 mt-1 capitalize block">
                    {lead.priority || notCaptured}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-2xs">
                  <span className="text-[11px] font-bold uppercase text-slate-500 block">
                    Lead Source
                  </span>
                  <span className="text-xs font-extrabold text-slate-900 mt-1 block truncate">
                    {lead.source?.replace(': V3 Workflow', '') || notCaptured}
                  </span>
                </div>
              </div>

              {/* Why Now (aitdk-style vertical bar indicator) */}
              <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/50 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-3.5 bg-blue-600 rounded-full" />
                    <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                      Why Now Signal
                    </span>
                  </div>
                  <span className="text-[10px] font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-md">
                    High Intent
                  </span>
                </div>
                <p className="text-xs text-slate-800 leading-relaxed font-medium">
                  {whyNow || 'No fresh signal captured for this lead.'}
                </p>
                {fresh?.freshness_label && (
                  <p className="text-[11px] text-slate-500">Signal age: {fresh.freshness_label}</p>
                )}
                {(d.qualification_reason || lead.qualification_reason) && (
                  <p className="text-[11px] text-slate-600 pt-1 border-t border-blue-200/60">
                    Qualification: {d.qualification_reason || lead.qualification_reason}
                  </p>
                )}
              </div>

              {/* Pain points */}
              {painPoints.length > 0 && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-2">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-3.5 bg-amber-500 rounded-full" />
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Identified Pain Points
                    </span>
                  </div>
                  <ul className="list-disc pl-4 text-xs text-slate-800 leading-relaxed space-y-1">
                    {painPoints.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}

              {/* Offer Fit */}
              {lead.need_of_what && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-3.5 bg-emerald-500 rounded-full" />
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Our Value Proposition
                    </span>
                  </div>
                  <p className="text-xs text-slate-800 leading-relaxed">
                    {lead.need_of_what}
                  </p>
                </div>
              )}

              {/* Company Details Table (aitdk-inspired alternating / structured spec table) */}
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-3.5 bg-slate-600 rounded-full" />
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                    Company Intelligence
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Company Name</span>
                    <span className="font-semibold text-slate-900">{lead.company || notCaptured}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Industry</span>
                    <span className="font-semibold text-slate-900">{d.company?.industry || notCaptured}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-500 uppercase block">Website</span>
                    <span className="font-semibold text-slate-900 truncate block">{websiteUrl || notCaptured}</span>
                  </div>
                </div>
              </div>

              {/* Person to contact */}
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-3.5 bg-blue-600 rounded-full" />
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
                    Decision Maker Coordinates
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <UserCheck size={16} className="text-blue-600 shrink-0" />
                    <div>
                      <span className="text-[10px] font-bold text-slate-500 uppercase block">Name &amp; Role</span>
                      <span className="text-slate-900 font-semibold">
                        {lead.name || notCaptured}{d.contact?.title ? ` — ${d.contact.title}` : ''}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <Mail size={16} className="text-blue-600 shrink-0" />
                    <div>
                      <span className="text-[10px] font-bold text-slate-500 uppercase block">Email Address</span>
                      <span className="font-mono text-slate-900 font-medium">{lead.email || notCaptured}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <Phone size={16} className="text-blue-600 shrink-0" />
                    <div>
                      <span className="text-[10px] font-bold text-slate-500 uppercase block">Phone / Mobile</span>
                      <span className="text-slate-900 font-medium">{lead.phone || lead.mobile_no || notCaptured}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <ExternalLink size={16} className="text-blue-600 shrink-0" />
                    <div>
                      <span className="text-[10px] font-bold text-slate-500 uppercase block">LinkedIn Profile</span>
                      {d.contact?.linkedin_url ? (
                        <a href={d.contact.linkedin_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 font-semibold underline">View Verified Profile</a>
                      ) : notCaptured}
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-2 space-y-2">
                <label className="block text-[10px] font-bold uppercase tracking-wide text-slate-500">
                  Prospect-agreed meeting time (your local timezone)
                </label>
                <Input
                  type="datetime-local"
                  value={meetingTime}
                  onChange={(e) => setMeetingTime(e.target.value)}
                  disabled={actionLoading}
                  className="text-xs bg-white border-slate-200 text-slate-900"
                />
                <div className="flex flex-wrap gap-2.5">
                  <Button
                    onClick={() => onSendOutreach(lead.id)}
                    disabled={actionLoading}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-xl h-10 shadow-sm"
                  >
                    {actionLoading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <Send size={14} className="mr-1.5" />}
                    Generate Grounded Outreach
                  </Button>
                  <Button
                    onClick={() => onBookMeeting(lead.id, meetingTime)}
                    disabled={actionLoading || !meetingTime}
                    variant="outline"
                    className="flex-1 text-xs font-semibold rounded-xl h-10 border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-sm"
                  >
                    <Calendar size={14} className="mr-1.5 text-blue-600" /> Book Meeting
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: INTELLIGENCE SIGNALS */}
          {activeTab === 'signals' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-3.5 bg-blue-600 rounded-full" />
                    <span className="text-xs font-bold uppercase text-slate-700">
                      Signal Freshness &amp; Verification
                    </span>
                  </div>
                  <span className="text-xs font-extrabold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                    {fresh?.freshness_label || 'Verified Active'}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-slate-600">
                  <p>Event Date: <span className="text-slate-900 font-semibold">{fresh?.event_date || notCaptured}</span></p>
                  <p>Date Source: <span className="text-slate-900 font-semibold">{fresh?.date_source || notCaptured}</span></p>
                  {d.freshness?.signal_snippet && (
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 mt-2">
                      <p className="italic text-slate-800">&ldquo;{d.freshness.signal_snippet}&rdquo;</p>
                    </div>
                  )}
                  {evidenceUrl && (
                    <p className="pt-2">
                      Evidence Source:{' '}
                      <a
                        href={evidenceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 font-semibold underline inline-flex items-center gap-1 ml-1"
                      >
                        Inspect Page <ExternalLink size={11} />
                      </a>
                    </p>
                  )}
                </div>
              </div>

              {lead.target_context && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-2">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-3.5 bg-purple-600 rounded-full" />
                    <span className="text-xs font-bold uppercase text-slate-700 block">
                      Target Archetype &amp; Context
                    </span>
                  </div>
                  <p className="text-xs text-slate-800 font-mono leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                    {lead.target_context}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: OUTREACH & CONVERSATION */}
          {activeTab === 'outreach' && (
            <div className="space-y-5">
              {/* Editable outreach draft */}
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-3.5 bg-blue-600 rounded-full" />
                  <span className="text-xs font-bold uppercase text-slate-700 block">
                    Customize Outbound Message
                  </span>
                </div>
                <Input
                  value={draftSubject}
                  onChange={(e) => setDraftSubject(e.target.value)}
                  placeholder="Subject line"
                  className="text-xs bg-slate-50 border-slate-200 text-slate-900"
                />
                <Textarea
                  rows={8}
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value)}
                  placeholder="No draft yet. Generate one, or write your own tailored message."
                  className="text-xs bg-slate-50 border-slate-200 text-slate-900 font-mono"
                />
                <Input
                  value={draftInstructions}
                  onChange={(e) => setDraftInstructions(e.target.value)}
                  placeholder="Prompt directives (e.g. emphasize cost reduction, concise 3 sentences, mention mutual investor)"
                  className="text-xs bg-slate-50 border-slate-200 text-slate-900"
                />
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    disabled={actionLoading}
                    onClick={async () => {
                      const r = await onGenerateDraft(lead.id, draftInstructions);
                      if (r) { setDraftSubject(r.subject); setDraftBody(r.body); }
                    }}
                    className="flex-1 text-xs rounded-xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-sm"
                  >
                    {actionLoading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <Sparkles size={14} className="mr-1.5 text-blue-600" />}
                    {draftBody ? 'Regenerate Draft' : 'Generate Draft'}
                  </Button>
                  <Button
                    disabled={actionLoading || !draftBody.trim()}
                    onClick={() => onSendDraft(lead.id, draftSubject, draftBody)}
                    className="flex-1 text-xs rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
                  >
                    <Send size={14} className="mr-1.5" /> Send This Message
                  </Button>
                </div>
              </div>

              {/* Conversation History */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase text-slate-500">
                  Interaction Timeline
                </h4>
                {conversation.length === 0 ? (
                  <div className="p-8 text-center border border-dashed border-slate-200 rounded-xl bg-white">
                    <Mail size={24} className="mx-auto text-slate-300 mb-2" />
                    <p className="text-xs text-slate-500">
                      No outreach messages sent yet.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {conversation.map((msg: any, i: number) => (
                      <div
                        key={i}
                        className={`p-4 rounded-xl border ${
                          msg.direction === 'outbound'
                            ? 'bg-blue-50/50 border-blue-200 ml-4'
                            : 'bg-white border-slate-200 mr-4 shadow-2xs'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1.5">
                          <span className="font-bold text-slate-900">
                            {msg.author || (msg.direction === 'outbound' ? 'Sales AI Agent' : lead.name)}
                          </span>
                          <span>{msg.at ? new Date(msg.at).toLocaleString() : ''}</span>
                        </div>
                        {msg.subject && (
                          <p className="text-xs font-bold text-slate-900 mb-1">
                            {msg.subject}
                          </p>
                        )}
                        <p className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed">
                          {msg.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Log Timeline Note */}
              <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-3">
                <span className="text-xs font-bold uppercase text-slate-700 block">
                  Log Internal Note / Offline Touchpoint
                </span>
                <Textarea
                  rows={2}
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Notes from call, demo agenda, buyer objections..."
                  className="text-xs bg-slate-50 border-slate-200 rounded-xl text-slate-900"
                />
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <select
                      value={noteChannel}
                      onChange={(e) => setNoteChannel(e.target.value)}
                      className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700"
                    >
                      <option value="note">Internal Note</option>
                      <option value="call">Phone Call</option>
                      <option value="meeting">Video Demo</option>
                      <option value="linkedin">LinkedIn Touch</option>
                    </select>
                  </div>
                  <Button
                    size="sm"
                    onClick={handleLogNoteSubmit}
                    disabled={!noteText.trim() || actionLoading}
                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-sm"
                  >
                    Log Note
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* TAB: FOLLOW-UP SCHEDULE */}
          {activeTab === 'followups' && (
            <div className="space-y-4">
              {schedule.length === 0 ? (
                <div className="p-8 text-center border border-dashed border-slate-200 rounded-xl bg-white">
                  <Clock size={24} className="mx-auto text-slate-300 mb-2" />
                  <p className="text-xs text-slate-500">
                    No follow-up schedule yet. It is created when the prospecting workflow sequences this lead.
                  </p>
                </div>
              ) : (
                <>
                  {schedule.map((st, i) => (
                    <div key={i} className="p-4 rounded-xl border border-slate-200 bg-white shadow-2xs space-y-2">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-semibold text-slate-600">Day</span>
                        <Input
                          type="number"
                          value={st.day}
                          onChange={(e) => updateStep(i, { day: Number(e.target.value) })}
                          className="w-16 h-7 text-xs bg-slate-50 border-slate-200"
                        />
                        <select
                          value={st.channel}
                          onChange={(e) => updateStep(i, { channel: e.target.value })}
                          className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-slate-700"
                        >
                          {['Email', 'LinkedIn', 'WhatsApp', 'Follow-Up Call'].map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                        <select
                          value={st.status || 'pending'}
                          onChange={(e) => updateStep(i, { status: e.target.value as FollowUpStep['status'] })}
                          className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 ml-auto text-slate-700"
                        >
                          <option value="pending">Pending</option>
                          <option value="sent">Sent</option>
                          <option value="skipped">Skipped</option>
                        </select>
                        <button
                          onClick={() => setSchedule((s) => s.filter((_, idx) => idx !== i))}
                          className="text-slate-400 hover:text-rose-600 p-1"
                          title="Remove step"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                      <Textarea
                        rows={3}
                        value={st.content}
                        onChange={(e) => updateStep(i, { content: e.target.value })}
                        className="text-xs bg-slate-50 border-slate-200 text-slate-900"
                      />
                    </div>
                  ))}
                </>
              )}
              <div className="flex justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setSchedule((s) => [
                      ...s,
                      { day: (s[s.length - 1]?.day || 0) + 3, channel: 'Email', content: '', status: 'pending' },
                    ])
                  }
                  className="text-xs rounded-xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-sm"
                >
                  Add Step
                </Button>
                <Button
                  size="sm"
                  disabled={actionLoading}
                  onClick={() => onSaveSchedule(lead.id, schedule)}
                  className="text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-sm"
                >
                  Save Schedule
                </Button>
              </div>
            </div>
          )}

          {/* TAB 4: EDIT ACCOUNT */}
          {activeTab === 'edit' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">Company Name</label>
                  <Input value={editCompany} onChange={(e) => setEditCompany(e.target.value)} className="text-xs bg-white border-slate-200 text-slate-900" />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">Contact Name</label>
                  <Input value={editName} onChange={(e) => setEditName(e.target.value)} className="text-xs bg-white border-slate-200 text-slate-900" />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">Email</label>
                  <Input value={editEmail} onChange={(e) => setEditEmail(e.target.value)} className="text-xs bg-white border-slate-200 text-slate-900" />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">Phone</label>
                  <Input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} className="text-xs bg-white border-slate-200 text-slate-900" />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">Purchasing Capacity</label>
                  <Input value={editCapacity} onChange={(e) => setEditCapacity(e.target.value)} className="text-xs bg-white border-slate-200 text-slate-900" />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-600 block mb-1">AI Score (0-100)</label>
                  <Input type="number" value={editScore} onChange={(e) => setEditScore(e.target.value)} className="text-xs bg-white border-slate-200 text-slate-900" placeholder="Not scored" />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 block mb-1">Qualification Rationale / Why</label>
                <Textarea rows={3} value={editWhy} onChange={(e) => setEditWhy(e.target.value)} className="text-xs bg-white border-slate-200 text-slate-900" />
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-200">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => onDeleteLead(lead.id)}
                  className="text-xs rounded-xl flex items-center gap-1.5"
                >
                  <Trash2 size={13} /> Delete Account
                </Button>

                <Button
                  onClick={handleSaveEdit}
                  disabled={actionLoading}
                  className="text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 shadow-sm"
                >
                  Save Changes
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


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
import { Lead } from './sales-types';

interface SalesLeadDossierProps {
  lead: Lead | null;
  onClose: () => void;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onSendOutreach: (leadId: string) => Promise<void>;
  onSendSmartOutreach: (leadId: string) => Promise<void>;
  onBookMeeting: (leadId: string) => Promise<void>;
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
  onBookMeeting,
  onDeleteLead,
  onLogNote,
  onSaveLead,
  actionLoading,
}: SalesLeadDossierProps) {
  if (!lead) return null;

  const [activeTab, setActiveTab] = useState<'overview' | 'signals' | 'outreach' | 'edit'>('overview');
  const [noteText, setNoteText] = useState('');
  const [noteChannel, setNoteChannel] = useState('note');
  const [noteDirection, setNoteDirection] = useState('internal');

  // Edit states
  const [editName, setEditName] = useState(lead.name || '');
  const [editCompany, setEditCompany] = useState(lead.company || '');
  const [editEmail, setEditEmail] = useState(lead.email || '');
  const [editPhone, setEditPhone] = useState(lead.phone || '');
  const [editWhy, setEditWhy] = useState(lead.why || '');
  const [editCapacity, setEditCapacity] = useState(lead.purchasing_capacity || lead.how_much || '');
  const [editScore, setEditScore] = useState(lead.score || 50);

  const handleLogNoteSubmit = async () => {
    if (!noteText.trim()) return;
    await onLogNote(lead.id, noteText, noteChannel, noteDirection);
    setNoteText('');
  };

  const handleSaveEdit = async () => {
    await onSaveLead(lead.id, {
      name: editName,
      company: editCompany,
      email: editEmail,
      phone: editPhone,
      why: editWhy,
      how_much: editCapacity,
      score: Number(editScore),
    });
    setActiveTab('overview');
  };

  const conversation = (lead.data?.conversation || []) as any[];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-background/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-card border-l border-border h-full shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Strip */}
        <div className="p-6 border-b border-border/60 bg-card/60 backdrop-blur-md">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold flex items-center justify-center text-lg shrink-0">
                {lead.company?.charAt(0).toUpperCase() || 'C'}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-foreground">
                    {lead.company}
                  </h2>
                  {lead.website && (
                    <a
                      href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-emerald-400 p-0.5"
                    >
                      <ExternalLink size={13} />
                    </a>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Contact: <span className="text-foreground font-medium">{lead.name}</span>
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Quick Actions & Status Strip */}
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border/40">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-muted-foreground">Stage:</span>
              <select
                value={lead.status}
                onChange={(e) => onUpdateStatus(lead.id, e.target.value)}
                className="text-xs font-semibold bg-background border border-border rounded-lg px-2.5 py-1 text-foreground focus:border-emerald-500 outline-none"
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
              <span className="text-xs font-semibold text-muted-foreground">AI Fit Score:</span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <Sparkles size={12} /> {lead.score ?? 50}/100
              </span>
            </div>
          </div>

          {/* Dossier Tabs */}
          <div className="flex items-center gap-1 mt-4 -mb-2 border-b border-border/40">
            {[
              { id: 'overview', label: 'Overview & Fit' },
              { id: 'signals', label: 'Intelligence Signals' },
              { id: 'outreach', label: `Outreach (${conversation.length})` },
              { id: 'edit', label: 'Edit Account' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-2 text-xs font-semibold border-b-2 -mb-[1px] transition-all ${
                  activeTab === tab.id
                    ? 'border-emerald-500 text-emerald-400'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* TAB 1: OVERVIEW & FIT */}
          {activeTab === 'overview' && (
            <div className="space-y-5">
              {/* Metric Highlights */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl border border-border/60 bg-background/40">
                  <span className="text-[11px] font-semibold uppercase text-muted-foreground block">
                    Purchasing Capacity
                  </span>
                  <span className="text-xs font-bold text-foreground mt-1 block">
                    {lead.purchasing_capacity || lead.how_much || 'Standard B2B'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-border/60 bg-background/40">
                  <span className="text-[11px] font-semibold uppercase text-muted-foreground block">
                    Priority Tier
                  </span>
                  <span className="text-xs font-bold text-foreground mt-1 capitalize block">
                    {lead.priority || 'Medium'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-border/60 bg-background/40">
                  <span className="text-[11px] font-semibold uppercase text-muted-foreground block">
                    Lead Source
                  </span>
                  <span className="text-xs font-bold text-foreground mt-1 block truncate">
                    {lead.source?.replace(': V3 Workflow', '') || 'Inbound'}
                  </span>
                </div>
              </div>

              {/* Qualification Thesis / Why Now */}
              <div className="p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 space-y-2">
                <div className="flex items-center gap-2">
                  <Sparkles size={15} className="text-emerald-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                    Why Now & Qualification Thesis
                  </span>
                </div>
                <p className="text-xs text-foreground/90 leading-relaxed">
                  {lead.why || lead.qualification_reason || 'Verified account fitting current ICP parameters and purchasing capacity criteria.'}
                </p>
              </div>

              {/* Offer Fit */}
              {lead.need_of_what && (
                <div className="p-4 rounded-2xl border border-border/60 bg-background/40 space-y-1.5">
                  <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Commercial Need / Opportunity
                  </span>
                  <p className="text-xs text-foreground leading-relaxed">
                    {lead.need_of_what}
                  </p>
                </div>
              )}

              {/* Contact Information */}
              <div className="p-4 rounded-2xl border border-border/60 bg-background/40 space-y-3">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider block">
                  Direct Contact Coordinates
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <Mail size={14} className="text-muted-foreground" />
                    <div>
                      <span className="text-[10px] text-muted-foreground block">Email</span>
                      <span className="font-mono text-foreground">{lead.email || '—'}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Phone size={14} className="text-muted-foreground" />
                    <div>
                      <span className="text-[10px] text-muted-foreground block">Phone</span>
                      <span className="text-foreground">{lead.phone || lead.mobile_no || '—'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2.5 pt-2">
                <Button
                  onClick={() => onSendOutreach(lead.id)}
                  disabled={actionLoading}
                  className="flex-1 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs rounded-xl h-10 shadow-lg shadow-emerald-500/20"
                >
                  {actionLoading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <Send size={14} className="mr-1.5" />}
                  Generate Grounded Outreach
                </Button>
                <Button
                  onClick={() => onBookMeeting(lead.id)}
                  disabled={actionLoading}
                  variant="outline"
                  className="flex-1 text-xs font-semibold rounded-xl h-10 border-border hover:bg-card"
                >
                  <Calendar size={14} className="mr-1.5" /> Book Meeting
                </Button>
              </div>
            </div>
          )}

          {/* TAB 2: INTELLIGENCE SIGNALS */}
          {activeTab === 'signals' && (
            <div className="space-y-4">
              <div className="p-4 rounded-2xl border border-border/60 bg-background/40 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-muted-foreground">
                    Signal Freshness & Verification
                  </span>
                  <span className="text-xs font-bold text-emerald-400">
                    {lead.freshness?.freshness_label || 'Active Web'}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-muted-foreground">
                  <p>Event Date: <span className="text-foreground font-medium">{lead.freshness?.event_date || 'Recent'}</span></p>
                  <p>Verification Source: <span className="text-foreground font-medium">{lead.freshness?.date_source || 'Universal Web Scrape'}</span></p>
                  {lead.evidence_url && (
                    <p className="pt-1">
                      Evidence Source:{' '}
                      <a
                        href={lead.evidence_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-emerald-400 underline inline-flex items-center gap-1 ml-1"
                      >
                        Inspect Page <ExternalLink size={11} />
                      </a>
                    </p>
                  )}
                </div>
              </div>

              {lead.target_context && (
                <div className="p-4 rounded-2xl border border-border/60 bg-background/40 space-y-2">
                  <span className="text-xs font-bold uppercase text-muted-foreground block">
                    Archetype & Context
                  </span>
                  <p className="text-xs text-foreground font-mono leading-relaxed">
                    {lead.target_context}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: OUTREACH & CONVERSATION */}
          {activeTab === 'outreach' && (
            <div className="space-y-5">
              {/* Conversation History */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase text-muted-foreground">
                  Interaction Timeline
                </h4>
                {conversation.length === 0 ? (
                  <div className="p-8 text-center border border-dashed border-border/60 rounded-2xl">
                    <Mail size={24} className="mx-auto text-muted-foreground/40 mb-2" />
                    <p className="text-xs text-muted-foreground">
                      No outreach messages sent yet.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {conversation.map((msg: any, i: number) => (
                      <div
                        key={i}
                        className={`p-4 rounded-2xl border ${
                          msg.direction === 'outbound'
                            ? 'bg-emerald-500/5 border-emerald-500/20 ml-4'
                            : 'bg-muted/40 border-border mr-4'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-1.5">
                          <span className="font-semibold text-foreground">
                            {msg.author || (msg.direction === 'outbound' ? 'Sales AI Agent' : lead.name)}
                          </span>
                          <span>{msg.at ? new Date(msg.at).toLocaleString() : ''}</span>
                        </div>
                        {msg.subject && (
                          <p className="text-xs font-bold text-foreground mb-1">
                            {msg.subject}
                          </p>
                        )}
                        <p className="text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed">
                          {msg.content}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Log Timeline Note */}
              <div className="p-4 rounded-2xl border border-border/60 bg-background/40 space-y-3">
                <span className="text-xs font-bold uppercase text-muted-foreground block">
                  Log Internal Note / Offline Touchpoint
                </span>
                <Textarea
                  rows={2}
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Notes from call, demo agenda, buyer objections..."
                  className="text-xs bg-background border-border/70 rounded-xl"
                />
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <select
                      value={noteChannel}
                      onChange={(e) => setNoteChannel(e.target.value)}
                      className="text-xs bg-background border border-border rounded-lg px-2 py-1 text-muted-foreground"
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
                    className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl"
                  >
                    Log Note
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: EDIT ACCOUNT */}
          {activeTab === 'edit' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">Company Name</label>
                  <Input value={editCompany} onChange={(e) => setEditCompany(e.target.value)} className="text-xs bg-background" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">Contact Name</label>
                  <Input value={editName} onChange={(e) => setEditName(e.target.value)} className="text-xs bg-background" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">Email</label>
                  <Input value={editEmail} onChange={(e) => setEditEmail(e.target.value)} className="text-xs bg-background" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">Phone</label>
                  <Input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} className="text-xs bg-background" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">Purchasing Capacity</label>
                  <Input value={editCapacity} onChange={(e) => setEditCapacity(e.target.value)} className="text-xs bg-background" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground block mb-1">AI Score (0-100)</label>
                  <Input type="number" value={editScore} onChange={(e) => setEditScore(Number(e.target.value))} className="text-xs bg-background" />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-muted-foreground block mb-1">Qualification Rationale / Why</label>
                <Textarea rows={3} value={editWhy} onChange={(e) => setEditWhy(e.target.value)} className="text-xs bg-background" />
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-border/40">
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
                  className="text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl px-5"
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

'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Search, Mail, Phone, ExternalLink, Sparkles, Filter, 
  ChevronRight, MoreHorizontal, CheckCircle2, AlertCircle, Clock,
  Trash2, Send, Calendar, Building, Check, Copy, ArrowUpRight,
  LayoutGrid, TableProperties, X, ChevronDown
} from 'lucide-react';
import { Lead } from './sales-types';

import { VerticalPack, SalesTerminology } from './sales-platform';

interface SalesTableViewProps {
  leads: Lead[];
  activePack?: VerticalPack | null;
  terms?: SalesTerminology;
  onSelectLead: (lead: Lead) => void;
  selectedLeadId?: string | null;
  onDeleteLead: (leadId: string, skipConfirm?: boolean) => Promise<void>;
  onBulkDeleteLeads?: (leadIds: string[]) => Promise<void>;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onOpenCreateLead: () => void;
  onOpenProspecting: () => void;
  viewMode?: 'table' | 'kanban';
  onViewModeChange?: (mode: 'table' | 'kanban') => void;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  new: { 
    label: 'New Prospect', 
    color: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
    dot: 'bg-[#AAB5C4]' 
  },
  inquiry: {
    label: 'New Inquiry',
    color: 'bg-[#2B3945] text-[#75AFCB] border border-[#75AFCB]/20',
    dot: 'bg-[#75AFCB]',
  },
  qualified: { 
    label: 'Qualified', 
    color: 'bg-[#2B3945] text-[#75AFCB] border border-[#75AFCB]/20',
    dot: 'bg-[#75AFCB]' 
  },
  contacted: { 
    label: 'In Outreach', 
    color: 'bg-[#343D61] text-[#A1AEF0] border border-[#7888D9]/30',
    dot: 'bg-[#7888D9]' 
  },
  meeting_scheduled: { 
    label: 'Meeting Booked', 
    color: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',
    dot: 'bg-[#D9AD68]' 
  },
  site_visit: {
    label: 'Site Visit',
    color: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',
    dot: 'bg-[#D9AD68]',
  },
  hold_requested: {
    label: 'Hold Requested',
    color: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',
    dot: 'bg-[#D9828B]',
  },
  booking: {
    label: 'Confirmed Booking',
    color: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20 font-semibold',
    dot: 'bg-[#64B99A]',
  },
  closed_won: { 
    label: 'Closed Won', 
    color: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20 font-semibold',
    dot: 'bg-[#64B99A]' 
  },
  cancelled: {
    label: 'Cancelled',
    color: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',
    dot: 'bg-[#D9828B]',
  },
  closed_lost: { 
    label: 'Closed Lost', 
    color: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',
    dot: 'bg-[#D9828B]' 
  },
};

export default function SalesTableView({
  leads,
  activePack,
  terms,
  onSelectLead,
  selectedLeadId,
  onDeleteLead,
  onBulkDeleteLeads,
  onUpdateStatus,
  onOpenCreateLead,
  onOpenProspecting,
  viewMode = 'table',
  onViewModeChange,
}: SalesTableViewProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  const [bulkUpdating, setBulkUpdating] = useState(false);

  const filteredLeads = leads.filter((lead) => {
    const matchesSearch =
      !searchTerm ||
      lead.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.company?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.need_of_what?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' || lead.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const toggleSelectAll = () => {
    if (selectedLeadIds.length === filteredLeads.length) {
      setSelectedLeadIds([]);
    } else {
      setSelectedLeadIds(filteredLeads.map((l) => l.id));
    }
  };

  const toggleSelectOne = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedLeadIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const copyToClipboard = (text: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedEmail(text);
    setTimeout(() => setCopiedEmail(null), 1500);
  };

  const handleBulkStatusChange = async (newStatus: string) => {
    setBulkUpdating(true);
    try {
      for (const id of selectedLeadIds) {
        await onUpdateStatus(id, newStatus);
      }
      setSelectedLeadIds([]);
    } finally {
      setBulkUpdating(false);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedLeadIds.length === 0) return;
    setBulkUpdating(true);
    try {
      if (onBulkDeleteLeads) {
        await onBulkDeleteLeads(selectedLeadIds);
      } else {
        if (!window.confirm(`Delete ${selectedLeadIds.length} selected accounts?`)) return;
        for (const id of selectedLeadIds) {
          await onDeleteLead(id, true);
        }
      }
      setSelectedLeadIds([]);
    } catch (e) {
      console.error(e);
    } finally {
      setBulkUpdating(false);
    }
  };

  // aitdk-inspired score badge pill (like 46/60 in green)
  const getScoreBadge = (score?: number) => {
    const val = score ?? 50;
    if (val >= 80) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20">
          <Sparkles size={11} className="text-[#64B99A]" /> {val}/100
        </span>
      );
    }
    if (val >= 60) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-[#343D61] text-[#A1AEF0] border border-[#7888D9]/30">
          {val}/100
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-medium bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]">
        {val}/100
      </span>
    );
  };

  return (
    <Card className="bg-card border border-border rounded-xl p-4 md:p-5 shadow-xs space-y-3.5 relative">
      {/* ── TOP INTEGRATED TOOLBAR (Search + Filter Pills + View Switcher) ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Left: Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by company, contact, email, or need..."
            className="pl-9 bg-muted/40 border-border rounded-xl text-xs h-9 text-foreground placeholder:text-muted-foreground focus:bg-card focus:border-primary"
          />
        </div>

        {/* Center: Stage Filter Pills (Ahrefs segmented filter bar) */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
          {[
            { id: 'all', label: `All (${leads.length})` },
            { id: 'qualified', label: 'Qualified ICP' },
            { id: 'contacted', label: 'In Outreach' },
            { id: 'meeting_scheduled', label: 'Meetings' },
            { id: 'closed_won', label: 'Won' },
            { id: 'closed_lost', label: 'Lost' },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setStatusFilter(pill.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                statusFilter === pill.id
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'bg-card border border-border hover:bg-surface-hover text-muted-foreground hover:text-foreground'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>

        {/* Right: Table vs Kanban Switcher */}
        {onViewModeChange && (
          <div className="flex items-center gap-1 bg-card p-0.5 rounded-lg border border-border shrink-0 self-end lg:self-auto">
            <button
              type="button"
              onClick={() => onViewModeChange('table')}
              className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                viewMode === 'table'
                  ? 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Table View"
            >
              <TableProperties size={13} /> Table
            </button>
            <button
              type="button"
              onClick={() => onViewModeChange('kanban')}
              className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                viewMode === 'kanban'
                  ? 'bg-primary/10 text-primary border border-primary/20'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Kanban Board"
            >
              <LayoutGrid size={13} /> Kanban
            </button>
          </div>
        )}
      </div>

      {/* ── HIGH-DENSITY ENTERPRISE TABLE ── */}
      <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-bold">
                <th className="py-2.5 px-3.5 w-8">
                  <input
                    type="checkbox"
                    checked={
                      filteredLeads.length > 0 &&
                      selectedLeadIds.length === filteredLeads.length
                    }
                    onChange={toggleSelectAll}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
                <th className="py-2.5 px-3.5 font-semibold uppercase tracking-wider text-[11px] text-muted-foreground">
                  {terms?.account || 'Account'} &amp; {terms?.lead || 'Decision Maker'}
                </th>
                <th className="py-2.5 px-3.5 font-semibold uppercase tracking-wider text-[11px] text-muted-foreground">
                  AI Fit Score
                </th>
                <th className="py-2.5 px-3.5 font-semibold uppercase tracking-wider text-[11px] text-muted-foreground">
                  Pipeline Stage
                </th>
                <th className="py-2.5 px-3.5 font-semibold uppercase tracking-wider text-[11px] text-muted-foreground">
                  Contact Coordinates
                </th>
                <th className="py-2.5 px-3.5 font-semibold uppercase tracking-wider text-[11px] text-muted-foreground">
                  Signal &amp; Source
                </th>
                <th className="py-2.5 px-3.5 text-right font-semibold uppercase tracking-wider text-[11px] text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredLeads.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 px-4 bg-card">
                    <div className="max-w-sm mx-auto space-y-3">
                      <div className="w-12 h-12 rounded-xl bg-surface-hover text-muted-foreground flex items-center justify-center mx-auto border border-border shadow-xs">
                        <Sparkles size={22} />
                      </div>
                      <h4 className="text-sm font-semibold text-foreground">
                        No accounts match active filters
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        Source fresh, ICP-verified accounts using autonomous prospecting or clear search terms.
                      </p>
                      <div className="flex items-center justify-center gap-2 pt-1">
                        <Button
                          size="sm"
                          onClick={onOpenProspecting}
                          className="text-xs font-semibold"
                        >
                          <Sparkles size={13} className="mr-1.5" /> Launch AI Prospector
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={onOpenCreateLead}
                          className="text-xs"
                        >
                          Add Manually
                        </Button>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredLeads.map((lead) => {
                  const isSelected = selectedLeadId === lead.id;
                  const isChecked = selectedLeadIds.includes(lead.id);
                  const stageObj = activePack?.pipeline_stages?.find(
                    (s) => s.id === lead.status || s.label.toLowerCase() === lead.status?.toLowerCase()
                  );
                  const st = stageObj
                    ? {
                        label: stageObj.label,
                        color: 'bg-primary/10 text-primary border border-primary/20',
                        dot: 'bg-primary',
                      }
                    : STATUS_CONFIG[lead.status] || {
                        label: lead.status?.replaceAll('_', ' ') || 'Unknown',
                        color: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
                        dot: 'bg-[#AAB5C4]',
                      };

                  return (
                    <tr
                      key={lead.id}
                      onClick={() => onSelectLead(lead)}
                      className={`hover:bg-surface-hover/50 transition-colors cursor-pointer group ${
                        isSelected ? 'bg-primary/10' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-3.5">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => toggleSelectOne(lead.id, e as any)}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded border-border text-primary focus:ring-ring"
                        />
                      </td>

                      {/* Account & Contact */}
                      <td className="py-3 px-3.5">
                        <div className="flex items-start gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-surface-hover border border-border text-foreground flex items-center justify-center text-xs font-semibold shrink-0 mt-0.5">
                            {lead.company?.charAt(0).toUpperCase() || 'C'}
                          </div>
                          <div>
                            <div className="font-semibold text-foreground group-hover:text-primary transition-colors flex items-center gap-1.5">
                              <span>{lead.company}</span>
                              {lead.website && (
                                <a
                                  href={
                                    lead.website.startsWith('http')
                                      ? lead.website
                                      : `https://${lead.website}`
                                  }
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  className="text-muted-foreground hover:text-primary transition-colors"
                                  title="Open website"
                                >
                                  <ExternalLink size={12} />
                                </a>
                              )}
                            </div>
                            <p className="text-[11px] text-muted-foreground mt-0.5">
                              <strong className="text-foreground">{lead.name}</strong>
                              {lead.assigned_to ? ` · ${lead.assigned_to}` : ''}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* AI Score (aitdk style) */}
                      <td className="py-3 px-3.5">
                        {getScoreBadge(lead.score)}
                      </td>

                      {/* Interactive Stage Picker (Direct In-Row Status Changer) */}
                      <td className="py-3 px-3.5" onClick={(e) => e.stopPropagation()}>
                        <div className="relative inline-block">
                          <select
                            value={lead.status}
                            onChange={(e) => onUpdateStatus(lead.id, e.target.value)}
                            className={`appearance-none cursor-pointer pl-2.5 pr-6 py-1 rounded-full text-[11px] font-semibold border transition-all outline-none ${st.color} [&>option]:bg-[#29323E] [&>option]:text-[#E5EAF1]`}
                          >
                            <option value="new">New Prospect</option>
                            <option value="qualified">ICP Qualified</option>
                            <option value="contacted">In Outreach</option>
                            <option value="meeting_scheduled">Meeting Booked</option>
                            <option value="closed_won">Closed Won</option>
                            <option value="closed_lost">Closed Lost</option>
                          </select>
                          <ChevronDown size={11} className="absolute right-2 top-2 pointer-events-none opacity-60" />
                        </div>
                      </td>

                      {/* Contact Details with Quick Copy */}
                      <td className="py-3 px-3.5">
                        <div className="space-y-1">
                          {lead.email ? (
                            <div className="flex items-center gap-1.5 text-foreground">
                              <Mail size={12} className="text-muted-foreground shrink-0" />
                              <span className="font-mono text-[11px] text-foreground">{lead.email}</span>
                              <button
                                type="button"
                                onClick={(e) => copyToClipboard(lead.email, e)}
                                className="text-muted-foreground hover:text-primary p-0.5 transition-colors"
                                title="Copy email"
                              >
                                {copiedEmail === lead.email ? (
                                  <Check size={11} className="text-[#64B99A]" />
                                ) : (
                                  <Copy size={11} />
                                )}
                              </button>
                            </div>
                          ) : (
                            <span className="text-muted-foreground text-[11px] italic">No email</span>
                          )}
                          {lead.phone && (
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                              <Phone size={11} className="shrink-0 text-muted-foreground" />
                              <a
                                href={`tel:${lead.phone}`}
                                onClick={(e) => e.stopPropagation()}
                                className="text-[11px] hover:text-primary font-mono transition-colors"
                              >
                                {lead.phone}
                              </a>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Freshness / Source */}
                      <td className="py-3 px-3.5">
                        <div>
                          <span className="text-[11px] font-semibold text-foreground block">
                            {lead.data?.freshness?.freshness_label || lead.freshness?.freshness_label || 'Active Verified'}
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            {lead.source?.replace(': V3 Workflow', '') || 'Inbound'}
                          </span>
                        </div>
                      </td>

                      {/* Row Action Buttons */}
                      <td className="py-3 px-3.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectLead(lead);
                            }}
                            className="h-7 px-2.5 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-all"
                          >
                            Dossier <ChevronRight size={13} className="ml-0.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onDeleteLead(lead.id);
                            }}
                            className="h-7 w-7 p-0 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                            title="Delete Lead"
                          >
                            <Trash2 size={13} />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── FOOTER BAR ── */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-1 pt-0.5">
        <span>
          Showing <strong className="text-slate-800">{filteredLeads.length}</strong> of <strong className="text-slate-800">{leads.length}</strong> accounts
        </span>
        <span className="text-[11px] text-slate-400">
          Click any row to open the 360° Lead Dossier
        </span>
      </div>

      {/* ── FLOATING BULK ACTION BAR (Industry Standard Apollo / Linear Style) ── */}
      {selectedLeadIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-40 bg-slate-900 text-white px-5 py-3 rounded-2xl shadow-2xl border border-slate-700 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-3 duration-200">
          <div className="flex items-center gap-2 border-r border-slate-700 pr-3">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-xs font-bold text-white">
              {selectedLeadIds.length} accounts selected
            </span>
          </div>

          {/* Quick Stage Transitions */}
          <div className="flex items-center gap-1.5">
            <Button
              size="sm"
              disabled={bulkUpdating}
              onClick={() => handleBulkStatusChange('qualified')}
              className="h-7 px-2.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg"
            >
              Mark Qualified
            </Button>
            <Button
              size="sm"
              disabled={bulkUpdating}
              onClick={() => handleBulkStatusChange('contacted')}
              className="h-7 px-2.5 text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white rounded-lg"
            >
              In Outreach
            </Button>
            <Button
              size="sm"
              disabled={bulkUpdating}
              onClick={() => handleBulkStatusChange('closed_won')}
              className="h-7 px-2.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg"
            >
              Close Won
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={bulkUpdating}
              onClick={handleBulkDelete}
              className="h-7 px-2.5 text-xs font-semibold border-slate-700 bg-slate-800 text-rose-300 hover:bg-rose-950/60 hover:text-rose-200 rounded-lg"
            >
              <Trash2 size={12} className="mr-1" /> Delete
            </Button>
          </div>

          <button
            type="button"
            onClick={() => setSelectedLeadIds([])}
            className="text-slate-400 hover:text-white p-1 rounded-md transition-colors ml-1"
            title="Clear Selection"
          >
            <X size={15} />
          </button>
        </div>
      )}
    </Card>
  );
}

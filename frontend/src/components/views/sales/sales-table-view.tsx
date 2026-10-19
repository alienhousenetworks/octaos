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

interface SalesTableViewProps {
  leads: Lead[];
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
    color: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100/70',
    dot: 'bg-blue-500' 
  },
  qualified: { 
    label: 'ICP Qualified', 
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100/70',
    dot: 'bg-emerald-500' 
  },
  contacted: { 
    label: 'In Outreach', 
    color: 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100/70',
    dot: 'bg-amber-500' 
  },
  meeting_scheduled: { 
    label: 'Meeting Booked', 
    color: 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100/70',
    dot: 'bg-purple-500' 
  },
  closed_won: { 
    label: 'Closed Won', 
    color: 'bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-700 font-bold',
    dot: 'bg-white' 
  },
  closed_lost: { 
    label: 'Closed Lost', 
    color: 'bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100/70',
    dot: 'bg-rose-500' 
  },
};

export default function SalesTableView({
  leads,
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
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-extrabold bg-emerald-600 text-white shadow-2xs">
          <Sparkles size={11} className="text-emerald-100" /> {val}/100
        </span>
      );
    }
    if (val >= 60) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-extrabold bg-blue-600 text-white shadow-2xs">
          {val}/100
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
        {val}/100
      </span>
    );
  };

  return (
    <Card className="bg-white border border-slate-200/90 rounded-2xl p-4 md:p-5 shadow-xs space-y-3.5 relative">
      {/* ── TOP INTEGRATED TOOLBAR (Search + Filter Pills + View Switcher) ── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Left: Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400 pointer-events-none" />
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by company, contact, email, or need..."
            className="pl-9 bg-slate-50 border-slate-200 rounded-xl text-xs h-9 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
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
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                statusFilter === pill.id
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-slate-100 hover:bg-slate-200/70 text-slate-600 hover:text-slate-900'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>

        {/* Right: Table vs Kanban Switcher */}
        {onViewModeChange && (
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-xl border border-slate-200 shrink-0 self-end lg:self-auto">
            <button
              type="button"
              onClick={() => onViewModeChange('table')}
              className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg transition-colors ${
                viewMode === 'table'
                  ? 'bg-white text-blue-600 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Table View"
            >
              <TableProperties size={13} /> Table
            </button>
            <button
              type="button"
              onClick={() => onViewModeChange('kanban')}
              className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg transition-colors ${
                viewMode === 'kanban'
                  ? 'bg-white text-blue-600 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Kanban Board"
            >
              <LayoutGrid size={13} /> Board
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
                <th className="py-2.5 px-3.5 font-bold uppercase tracking-wider text-[11px] text-slate-500">
                  Account &amp; Decision Maker
                </th>
                <th className="py-2.5 px-3.5 font-bold uppercase tracking-wider text-[11px] text-slate-500">
                  AI Fit Score
                </th>
                <th className="py-2.5 px-3.5 font-bold uppercase tracking-wider text-[11px] text-slate-500">
                  Pipeline Stage
                </th>
                <th className="py-2.5 px-3.5 font-bold uppercase tracking-wider text-[11px] text-slate-500">
                  Contact Coordinates
                </th>
                <th className="py-2.5 px-3.5 font-bold uppercase tracking-wider text-[11px] text-slate-500">
                  Signal &amp; Source
                </th>
                <th className="py-2.5 px-3.5 text-right font-bold uppercase tracking-wider text-[11px] text-slate-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLeads.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 px-4 bg-slate-50/40">
                    <div className="max-w-sm mx-auto space-y-3">
                      <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto border border-blue-100 shadow-2xs">
                        <Sparkles size={22} />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">
                        No accounts match active filters
                      </h4>
                      <p className="text-xs text-slate-500">
                        Source fresh, ICP-verified accounts using autonomous prospecting or clear search terms.
                      </p>
                      <div className="flex items-center justify-center gap-2 pt-1">
                        <Button
                          size="sm"
                          onClick={onOpenProspecting}
                          className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow-xs"
                        >
                          <Sparkles size={13} className="mr-1.5" /> Launch AI Prospector
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={onOpenCreateLead}
                          className="text-xs rounded-xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-xs"
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
                  const st = STATUS_CONFIG[lead.status] || {
                    label: lead.status,
                    color: 'bg-slate-100 text-slate-700 border-slate-200',
                    dot: 'bg-slate-400',
                  };

                  return (
                    <tr
                      key={lead.id}
                      onClick={() => onSelectLead(lead)}
                      className={`hover:bg-slate-50/80 transition-colors cursor-pointer group ${
                        isSelected ? 'bg-blue-50/50' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-3.5">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => toggleSelectOne(lead.id, e as any)}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>

                      {/* Account & Contact */}
                      <td className="py-3 px-3.5">
                        <div className="flex items-start gap-2.5">
                          <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-100 text-blue-700 flex items-center justify-center text-xs font-extrabold shrink-0 mt-0.5 shadow-2xs">
                            {lead.company?.charAt(0).toUpperCase() || 'C'}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900 group-hover:text-blue-600 transition-colors flex items-center gap-1.5">
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
                                  className="text-slate-400 hover:text-blue-600 transition-colors"
                                  title="Open website"
                                >
                                  <ExternalLink size={12} />
                                </a>
                              )}
                            </div>
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              <strong className="text-slate-700">{lead.name}</strong>
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
                            className={`appearance-none cursor-pointer pl-2.5 pr-6 py-1 rounded-full text-[11px] font-semibold border transition-all outline-none ${st.color}`}
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
                            <div className="flex items-center gap-1.5 text-slate-700">
                              <Mail size={12} className="text-slate-400 shrink-0" />
                              <span className="font-mono text-[11px] text-slate-800">{lead.email}</span>
                              <button
                                type="button"
                                onClick={(e) => copyToClipboard(lead.email, e)}
                                className="text-slate-400 hover:text-blue-600 p-0.5"
                                title="Copy email"
                              >
                                {copiedEmail === lead.email ? (
                                  <Check size={11} className="text-emerald-600" />
                                ) : (
                                  <Copy size={11} />
                                )}
                              </button>
                            </div>
                          ) : (
                            <span className="text-slate-400 text-[11px] italic">No email</span>
                          )}
                          {lead.phone && (
                            <div className="flex items-center gap-1.5 text-slate-500">
                              <Phone size={11} className="shrink-0 text-slate-400" />
                              <a
                                href={`tel:${lead.phone}`}
                                onClick={(e) => e.stopPropagation()}
                                className="text-[11px] hover:text-blue-600 font-mono"
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
                          <span className="text-[11px] font-semibold text-slate-800 block">
                            {lead.data?.freshness?.freshness_label || lead.freshness?.freshness_label || 'Active Verified'}
                          </span>
                          <span className="text-[10px] text-slate-500">
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

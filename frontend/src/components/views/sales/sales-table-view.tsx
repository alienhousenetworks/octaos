'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Search, Mail, Phone, ExternalLink, Sparkles, Filter, 
  ChevronRight, MoreHorizontal, CheckCircle2, AlertCircle, Clock,
  Trash2, Send, Calendar, Building, Check, Copy
} from 'lucide-react';
import { Lead } from './sales-types';

interface SalesTableViewProps {
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  selectedLeadId?: string | null;
  onDeleteLead: (leadId: string) => Promise<void>;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onOpenCreateLead: () => void;
  onOpenProspecting: () => void;
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  new: { label: 'New', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  qualified: { label: 'Qualified', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  contacted: { label: 'Contacted', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  meeting_scheduled: { label: 'Meeting Set', color: 'bg-violet-500/10 text-violet-400 border-violet-500/20' },
  closed_won: { label: 'Won', color: 'bg-emerald-600/20 text-emerald-300 border-emerald-500/40' },
  closed_lost: { label: 'Lost', color: 'bg-rose-500/10 text-rose-400 border-rose-500/20' },
};

export default function SalesTableView({
  leads,
  onSelectLead,
  selectedLeadId,
  onDeleteLead,
  onUpdateStatus,
  onOpenCreateLead,
  onOpenProspecting,
}: SalesTableViewProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedLeadIds, setSelectedLeadIds] = useState<string[]>([]);
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);

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

  const getScoreBadge = (score?: number) => {
    const val = score ?? 50;
    if (val >= 80) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <Sparkles size={11} /> {val}
        </span>
      );
    }
    if (val >= 60) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
          {val}
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-muted text-muted-foreground border border-border">
        {val}
      </span>
    );
  };

  return (
    <Card className="bg-card/40 backdrop-blur-md border-border/60 rounded-3xl p-5 shadow-2xl space-y-4">
      {/* Top Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search leads by name, company, email, or domain..."
            className="pl-9 bg-background/80 border-border/70 rounded-xl text-xs h-9 text-foreground focus:border-emerald-500"
          />
        </div>

        {/* Status Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar py-0.5">
          {[
            { id: 'all', label: 'All Leads' },
            { id: 'qualified', label: 'Qualified' },
            { id: 'contacted', label: 'Contacted' },
            { id: 'meeting_scheduled', label: 'Meetings' },
            { id: 'closed_won', label: 'Won' },
            { id: 'closed_lost', label: 'Lost' },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setStatusFilter(pill.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                statusFilter === pill.id
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-background/50 text-muted-foreground hover:text-foreground border border-border/40'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {/* Leads Table Container */}
      <div className="border border-border/60 rounded-2xl overflow-hidden bg-background/30">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-border/60 bg-muted/30 text-muted-foreground">
                <th className="py-3 px-4 w-8">
                  <input
                    type="checkbox"
                    checked={
                      filteredLeads.length > 0 &&
                      selectedLeadIds.length === filteredLeads.length
                    }
                    onChange={toggleSelectAll}
                    className="rounded border-border text-emerald-600 focus:ring-emerald-500"
                  />
                </th>
                <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[11px]">
                  Account & Contact
                </th>
                <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[11px]">
                  AI Score
                </th>
                <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[11px]">
                  Stage
                </th>
                <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[11px]">
                  Contact Details
                </th>
                <th className="py-3 px-4 font-semibold uppercase tracking-wider text-[11px]">
                  Signal / Freshness
                </th>
                <th className="py-3 px-4 text-right font-semibold uppercase tracking-wider text-[11px]">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {filteredLeads.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 px-4">
                    <div className="max-w-sm mx-auto space-y-3">
                      <div className="w-10 h-10 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto">
                        <Sparkles size={20} />
                      </div>
                      <h4 className="text-sm font-semibold text-foreground">
                        No leads match current criteria
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        Run autonomous prospecting to source fresh, verified accounts or clear active filters.
                      </p>
                      <div className="flex items-center justify-center gap-2 pt-2">
                        <Button
                          size="sm"
                          onClick={onOpenProspecting}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl"
                        >
                          <Sparkles size={13} className="mr-1.5" /> Launch Prospecting
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={onOpenCreateLead}
                          className="text-xs rounded-xl"
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
                    color: 'bg-muted text-muted-foreground border-border',
                  };

                  return (
                    <tr
                      key={lead.id}
                      onClick={() => onSelectLead(lead)}
                      className={`hover:bg-muted/40 transition-colors cursor-pointer group ${
                        isSelected ? 'bg-emerald-500/10' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => toggleSelectOne(lead.id, e as any)}
                          onClick={(e) => e.stopPropagation()}
                          className="rounded border-border text-emerald-600 focus:ring-emerald-500"
                        />
                      </td>

                      {/* Account & Contact */}
                      <td className="py-3 px-4">
                        <div className="flex items-start gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                            {lead.company?.charAt(0).toUpperCase() || 'C'}
                          </div>
                          <div>
                            <div className="font-semibold text-foreground group-hover:text-emerald-400 transition-colors flex items-center gap-1.5">
                              {lead.company}
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
                                  className="text-muted-foreground hover:text-emerald-400"
                                >
                                  <ExternalLink size={11} />
                                </a>
                              )}
                            </div>
                            <p className="text-[11px] text-muted-foreground">
                              {lead.name} {lead.assigned_to ? `· ${lead.assigned_to}` : ''}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* AI Score */}
                      <td className="py-3 px-4">
                        {getScoreBadge(lead.score)}
                      </td>

                      {/* Status Chip */}
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${st.color}`}
                        >
                          {st.label}
                        </span>
                      </td>

                      {/* Contact Details */}
                      <td className="py-3 px-4">
                        <div className="space-y-0.5">
                          {lead.email ? (
                            <div className="flex items-center gap-1.5 text-foreground">
                              <Mail size={12} className="text-muted-foreground shrink-0" />
                              <span className="font-mono text-[11px]">{lead.email}</span>
                              <button
                                type="button"
                                onClick={(e) => copyToClipboard(lead.email, e)}
                                className="text-muted-foreground hover:text-emerald-400 p-0.5"
                                title="Copy email"
                              >
                                {copiedEmail === lead.email ? (
                                  <Check size={11} className="text-emerald-400" />
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
                              <Phone size={11} className="shrink-0" />
                              <span className="text-[11px]">{lead.phone}</span>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Freshness / Source */}
                      <td className="py-3 px-4">
                        <div>
                          <span className="text-[11px] font-medium text-foreground block">
                            {lead.freshness?.freshness_label || 'Verified Lead'}
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            {lead.source?.replace(': V3 Workflow', '') || 'Inbound'}
                          </span>
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectLead(lead);
                            }}
                            className="h-7 px-2 text-[11px] text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 rounded-lg"
                          >
                            Dossier <ChevronRight size={12} className="ml-1" />
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

      {/* Footer Info */}
      <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
        <span>
          Showing {filteredLeads.length} of {leads.length} accounts
        </span>
        {selectedLeadIds.length > 0 && (
          <span className="text-emerald-400 font-semibold">
            {selectedLeadIds.length} accounts selected
          </span>
        )}
      </div>
    </Card>
  );
}

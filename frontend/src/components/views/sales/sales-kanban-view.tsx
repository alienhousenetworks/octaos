'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Building, Mail, Sparkles, ChevronRight, CheckCircle2, 
  ExternalLink, Calendar, Plus, ArrowRight, LayoutGrid, TableProperties
} from 'lucide-react';
import { Lead, parseBudget, fmtCurrency } from './sales-types';

interface SalesKanbanViewProps {
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onOpenCreateLead: () => void;
  viewMode?: 'table' | 'kanban';
  onViewModeChange?: (mode: 'table' | 'kanban') => void;
}

interface ColumnDef {
  id: string;
  label: string;
  color: string;
  accent: string;
  nextStatus?: string;
  nextLabel?: string;
}

const COLUMNS: ColumnDef[] = [
  {
    id: 'new',
    label: 'New Prospects',
    color: 'border-slate-200 bg-slate-50/80',
    accent: 'text-blue-600',
    nextStatus: 'qualified',
    nextLabel: 'Qualify',
  },
  {
    id: 'qualified',
    label: 'ICP Qualified',
    color: 'border-slate-200 bg-slate-50/80',
    accent: 'text-emerald-600',
    nextStatus: 'contacted',
    nextLabel: 'Send Outreach',
  },
  {
    id: 'contacted',
    label: 'In Outreach',
    color: 'border-slate-200 bg-slate-50/80',
    accent: 'text-amber-600',
    nextStatus: 'meeting_scheduled',
    nextLabel: 'Book Meeting',
  },
  {
    id: 'meeting_scheduled',
    label: 'Meeting Booked',
    color: 'border-slate-200 bg-slate-50/80',
    accent: 'text-purple-600',
    nextStatus: 'closed_won',
    nextLabel: 'Close Won',
  },
  {
    id: 'closed_won',
    label: 'Closed Won',
    color: 'border-emerald-200 bg-emerald-50/30',
    accent: 'text-emerald-700',
  },
  {
    id: 'closed_lost',
    label: 'Closed Lost',
    color: 'border-slate-200 bg-slate-50/80',
    accent: 'text-rose-600',
  },
];

export default function SalesKanbanView({
  leads,
  onSelectLead,
  onUpdateStatus,
  onOpenCreateLead,
  viewMode = 'kanban',
  onViewModeChange,
}: SalesKanbanViewProps) {
  return (
    <div className="space-y-4">
      {/* Top Toolbar with View Switcher */}
      <div className="flex items-center justify-between bg-white border border-slate-200/90 rounded-2xl p-3 shadow-xs">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-900">
            Pipeline Kanban Board
          </span>
          <span className="text-[11px] text-slate-500 font-medium">
            · {leads.length} accounts across 6 stages
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={onOpenCreateLead}
            className="h-8 px-3 text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white rounded-xl shadow-xs"
          >
            <Plus size={13} className="mr-1" /> Add Lead
          </Button>

          {onViewModeChange && (
            <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-xl border border-slate-200">
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
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-6 gap-3.5 items-start overflow-x-auto pb-4">
      {COLUMNS.map((col) => {
        const colLeads = leads.filter((l) => l.status === col.id);
        const colValue = colLeads.reduce(
          (acc, l) => acc + parseBudget(l.how_much || l.purchasing_capacity),
          0
        );

        return (
          <div
            key={col.id}
            className={`flex flex-col rounded-2xl border p-3.5 min-w-[260px] max-w-full shadow-xs ${col.color}`}
          >
            {/* Column Header */}
            <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-200">
              <div className="flex items-center gap-1.5">
                <span className={`text-xs font-bold ${col.accent}`}>
                  {col.label}
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-white border border-slate-200 text-slate-600">
                  {colLeads.length}
                </span>
              </div>
              {colValue > 0 && (
                <span className="text-[10px] font-bold text-slate-500 font-mono">
                  {fmtCurrency(colValue)}
                </span>
              )}
            </div>

            {/* Cards List */}
            <div className="space-y-2.5 min-h-[300px]">
              {colLeads.length === 0 ? (
                <div className="text-center py-10 border border-dashed border-slate-200 rounded-xl bg-white/50">
                  <span className="text-[11px] text-slate-400 block font-medium">
                    No accounts
                  </span>
                </div>
              ) : (
                colLeads.map((lead) => (
                  <Card
                    key={lead.id}
                    onClick={() => onSelectLead(lead)}
                    className="p-3.5 bg-white hover:bg-slate-50/80 border-slate-200 hover:border-blue-400 rounded-xl cursor-pointer shadow-xs hover:shadow-md transition-all group"
                  >
                    <div className="flex items-start justify-between gap-1.5">
                      <span className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1">
                        {lead.company}
                      </span>
                      {lead.score && (
                        <span className="text-[10px] font-extrabold px-1.5 py-0.5 rounded-md bg-emerald-600 text-white shrink-0 shadow-2xs">
                          {lead.score}
                        </span>
                      )}
                    </div>

                    <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                      {lead.name}
                    </p>

                    {lead.why && (
                      <p className="text-[10px] text-slate-600 line-clamp-2 mt-2 bg-slate-50 p-2 rounded-lg border border-slate-100">
                        {lead.why}
                      </p>
                    )}

                    {/* Bottom Metadata & Advance Action */}
                    <div className="flex items-center justify-between pt-2 mt-2 border-t border-slate-100">
                      <span className="text-[10px] font-bold text-slate-700 font-mono">
                        {lead.how_much || lead.purchasing_capacity || 'Qualified'}
                      </span>

                      {col.nextStatus && col.nextLabel && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            onUpdateStatus(lead.id, col.nextStatus!);
                          }}
                          className="h-6 px-2 text-[10px] font-bold text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md flex items-center gap-1"
                        >
                          {col.nextLabel} <ChevronRight size={10} />
                        </Button>
                      )}
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>
        );
      })}
      </div>
    </div>
  );
}


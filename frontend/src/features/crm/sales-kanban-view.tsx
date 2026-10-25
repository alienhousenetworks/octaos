'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Building, Mail, Sparkles, ChevronRight, CheckCircle2, 
  ExternalLink, Calendar, Plus, ArrowRight, LayoutGrid, TableProperties
} from 'lucide-react';
import { Lead, parseBudget, fmtCurrency } from './sales-types';

import { VerticalPack, SalesTerminology } from './sales-platform';

interface SalesKanbanViewProps {
  leads: Lead[];
  activePack?: VerticalPack | null;
  terms?: SalesTerminology;
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
    color: 'border-border bg-card/50',
    accent: 'text-muted-foreground',
    nextStatus: 'qualified',
    nextLabel: 'Qualify',
  },
  {
    id: 'qualified',
    label: 'ICP Qualified',
    color: 'border-border bg-card/50',
    accent: 'text-[#75AFCB]',
    nextStatus: 'contacted',
    nextLabel: 'Send Outreach',
  },
  {
    id: 'contacted',
    label: 'In Outreach',
    color: 'border-border bg-card/50',
    accent: 'text-[#A1AEF0]',
    nextStatus: 'meeting_scheduled',
    nextLabel: 'Book Meeting',
  },
  {
    id: 'meeting_scheduled',
    label: 'Meeting Booked',
    color: 'border-border bg-card/50',
    accent: 'text-[#D9AD68]',
    nextStatus: 'closed_won',
    nextLabel: 'Close Won',
  },
  {
    id: 'closed_won',
    label: 'Closed Won',
    color: 'border-[#64B99A]/30 bg-[#263D38]/30',
    accent: 'text-[#64B99A]',
  },
  {
    id: 'closed_lost',
    label: 'Closed Lost',
    color: 'border-border bg-card/50',
    accent: 'text-[#D9828B]',
  },
];

export default function SalesKanbanView({
  leads,
  activePack,
  terms,
  onSelectLead,
  onUpdateStatus,
  onOpenCreateLead,
  viewMode = 'kanban',
  onViewModeChange,
}: SalesKanbanViewProps) {
  const activeColumns: ColumnDef[] = React.useMemo(() => {
    if (activePack?.pipeline_stages && activePack.pipeline_stages.length > 0) {
      return activePack.pipeline_stages.map((st, idx) => ({
        id: st.id,
        label: st.label,
        color: 'border-border bg-card/50',
        accent: st.color || '#75AFCB',
        nextStatus: st.valid_transitions?.[0] || activePack.pipeline_stages?.[idx + 1]?.id,
        nextLabel: activePack.pipeline_stages?.[idx + 1]?.label ? `Move to ${activePack.pipeline_stages[idx + 1].label}` : undefined,
      }));
    }
    if (activePack?.stages && activePack.stages.length > 0) {
      return activePack.stages.map((stageName, idx) => {
        const id = stageName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
        return {
          id,
          label: stageName,
          color: 'border-border bg-card/50',
          accent: ['#75AFCB', '#A1AEF0', '#D9AD68', '#64B99A', '#D9828B'][idx % 5],
          nextStatus: activePack.stages[idx + 1]?.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, ''),
          nextLabel: activePack.stages[idx + 1] ? `Move to ${activePack.stages[idx + 1]}` : undefined,
        };
      });
    }
    return COLUMNS;
  }, [activePack]);

  const matchesColumn = (leadStatus: string | undefined, colId: string) => {
    if (leadStatus === colId) return true;
    if (activePack?.id === 'real_estate') {
      if (colId === 'inquiry' && (['new', 'contacted', 'captured', 'ready', 'contact_partial', 'discovered'].includes(leadStatus || '') || !leadStatus)) return true;
      if (colId === 'site_visit' && leadStatus === 'meeting_scheduled') return true;
      if (colId === 'booking' && leadStatus === 'closed_won') return true;
      if (colId === 'cancelled' && leadStatus === 'closed_lost') return true;
    }
    // If status is captured, ready, contact_partial or empty, map to the first pipeline column
    if (colId === activeColumns[0]?.id && (['captured', 'ready', 'contact_partial', 'discovered', 'new', 'inquiry'].includes(leadStatus || '') || !leadStatus)) return true;
    return false;
  };

  return (
    <div className="space-y-4">
      {/* Top Toolbar with View Switcher */}
      <div className="flex items-center justify-between bg-card border border-border rounded-xl p-3 shadow-xs">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-foreground">
            Pipeline Kanban Board
          </span>
          <span className="text-[11px] text-muted-foreground font-medium">
            · {leads.length} {terms?.leads.toLowerCase() || 'records'} across {activeColumns.length} stages
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={onOpenCreateLead}
            className="h-8 px-3 text-xs font-semibold"
          >
            <Plus size={13} className="mr-1" /> Add {terms?.lead || 'Lead'}
          </Button>

          {onViewModeChange && (
            <div className="flex items-center gap-1 bg-card p-0.5 rounded-lg border border-border">
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
                <LayoutGrid size={13} /> Board
              </button>
            </div>
          )}
        </div>
      </div>

      <div 
        className="grid gap-3.5 items-start overflow-x-auto pb-4"
        style={{ gridTemplateColumns: `repeat(${activeColumns.length}, minmax(260px, 1fr))` }}
      >
      {activeColumns.map((col) => {
        const colLeads = leads.filter((l) => matchesColumn(l.status, col.id));
        const colValue = colLeads.reduce(
          (acc, l) => acc + parseBudget(l.how_much || l.purchasing_capacity),
          0
        );

        return (
          <div
            key={col.id}
            className={`flex flex-col rounded-xl border p-3 min-w-[260px] max-w-full shadow-xs ${col.color}`}
          >
            {/* Column Header */}
            <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-border">
              <div className="flex items-center gap-1.5">
                <span className={`text-xs font-semibold ${col.accent}`}>
                  {col.label}
                </span>
                <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded-full bg-muted border border-border text-muted-foreground">
                  {colLeads.length}
                </span>
              </div>
              {colValue > 0 && (
                <span className="text-[10px] font-medium text-muted-foreground font-mono">
                  {fmtCurrency(colValue)}
                </span>
              )}
            </div>

            {/* Cards List */}
            <div className="space-y-2.5 min-h-[300px]">
              {colLeads.length === 0 ? (
                <div className="text-center py-10 border border-dashed border-border rounded-xl bg-card/30">
                  <span className="text-[11px] text-muted-foreground block font-medium">
                    No accounts
                  </span>
                </div>
              ) : (
                colLeads.map((lead) => (
                  <Card
                    key={lead.id}
                    onClick={() => onSelectLead(lead)}
                    className="p-3 bg-card hover:bg-surface-hover border-border hover:border-primary/40 rounded-xl cursor-pointer shadow-xs transition-all group"
                  >
                    <div className="flex items-start justify-between gap-1.5">
                      <span className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
                        {lead.company}
                      </span>
                      {lead.score && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20 shrink-0">
                          {lead.score}
                        </span>
                      )}
                    </div>

                    <p className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                      {lead.name}
                    </p>

                    {lead.why && (
                      <p className="text-[10px] text-muted-foreground line-clamp-2 mt-2 bg-muted/40 p-2 rounded-lg border border-border">
                        {lead.why}
                      </p>
                    )}

                    {/* Bottom Metadata & Advance Action */}
                    <div className="flex items-center justify-between pt-2 mt-2 border-t border-border">
                      <span className="text-[10px] font-semibold text-foreground font-mono">
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
                          className="h-6 px-2 text-[10px] font-semibold text-primary hover:text-primary-hover hover:bg-primary/10 rounded-md flex items-center gap-1"
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


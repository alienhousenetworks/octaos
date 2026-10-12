'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Building, Mail, Sparkles, ChevronRight, CheckCircle2, 
  ExternalLink, Calendar, Plus, ArrowRight
} from 'lucide-react';
import { Lead, parseBudget, fmtCurrency } from './sales-types';

interface SalesKanbanViewProps {
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onOpenCreateLead: () => void;
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
    color: 'border-blue-500/30 bg-blue-500/5',
    accent: 'text-blue-400',
    nextStatus: 'qualified',
    nextLabel: 'Qualify',
  },
  {
    id: 'qualified',
    label: 'ICP Qualified',
    color: 'border-emerald-500/30 bg-emerald-500/5',
    accent: 'text-emerald-400',
    nextStatus: 'contacted',
    nextLabel: 'Send Outreach',
  },
  {
    id: 'contacted',
    label: 'In Outreach',
    color: 'border-amber-500/30 bg-amber-500/5',
    accent: 'text-amber-400',
    nextStatus: 'meeting_scheduled',
    nextLabel: 'Book Meeting',
  },
  {
    id: 'meeting_scheduled',
    label: 'Meeting Booked',
    color: 'border-violet-500/30 bg-violet-500/5',
    accent: 'text-violet-400',
    nextStatus: 'closed_won',
    nextLabel: 'Close Won',
  },
  {
    id: 'closed_won',
    label: 'Closed Won',
    color: 'border-emerald-500/50 bg-emerald-500/10',
    accent: 'text-emerald-300',
  },
  {
    id: 'closed_lost',
    label: 'Closed Lost',
    color: 'border-rose-500/30 bg-rose-500/5',
    accent: 'text-rose-400',
  },
];

export default function SalesKanbanView({
  leads,
  onSelectLead,
  onUpdateStatus,
  onOpenCreateLead,
}: SalesKanbanViewProps) {
  return (
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
            className={`flex flex-col rounded-2xl border p-3 min-w-[260px] max-w-full backdrop-blur-md ${col.color}`}
          >
            {/* Column Header */}
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/40">
              <div className="flex items-center gap-1.5">
                <span className={`text-xs font-bold ${col.accent}`}>
                  {col.label}
                </span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-background/60 border border-border/40 text-muted-foreground">
                  {colLeads.length}
                </span>
              </div>
              {colValue > 0 && (
                <span className="text-[10px] font-semibold text-muted-foreground font-mono">
                  {fmtCurrency(colValue)}
                </span>
              )}
            </div>

            {/* Cards List */}
            <div className="space-y-2.5 min-h-[300px]">
              {colLeads.length === 0 ? (
                <div className="text-center py-10 border border-dashed border-border/40 rounded-xl">
                  <span className="text-[11px] text-muted-foreground block">
                    No deals
                  </span>
                </div>
              ) : (
                colLeads.map((lead) => (
                  <Card
                    key={lead.id}
                    onClick={() => onSelectLead(lead)}
                    className="p-3 bg-card/80 hover:bg-card border-border/70 hover:border-emerald-500/40 rounded-xl cursor-pointer shadow-md transition-all group"
                  >
                    <div className="flex items-start justify-between gap-1.5">
                      <span className="text-xs font-bold text-foreground group-hover:text-emerald-400 transition-colors line-clamp-1">
                        {lead.company}
                      </span>
                      {lead.score && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                          {lead.score}
                        </span>
                      )}
                    </div>

                    <p className="text-[11px] text-muted-foreground line-clamp-1 mt-0.5">
                      {lead.name}
                    </p>

                    {lead.why && (
                      <p className="text-[10px] text-muted-foreground/80 line-clamp-2 mt-1.5 bg-background/50 p-1.5 rounded-md border border-border/30">
                        {lead.why}
                      </p>
                    )}

                    {/* Bottom Metadata & Advance Action */}
                    <div className="flex items-center justify-between pt-2 mt-2 border-t border-border/30">
                      <span className="text-[10px] font-semibold text-emerald-400 font-mono">
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
                          className="h-6 px-2 text-[10px] font-semibold text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 rounded-md flex items-center gap-1"
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
  );
}

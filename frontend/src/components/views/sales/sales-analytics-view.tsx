'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  TrendingUp, Target, Calendar, Users, ArrowUpRight, 
  BarChart3, PieChart, ShieldCheck, Sparkles
} from 'lucide-react';
import { Lead, parseBudget, fmtCurrency } from './sales-types';

interface SalesAnalyticsViewProps {
  leads: Lead[];
  onOpenProspecting: () => void;
  onOpenPipeline: () => void;
}

export default function SalesAnalyticsView({
  leads,
  onOpenProspecting,
  onOpenPipeline,
}: SalesAnalyticsViewProps) {
  const totalLeads = leads.length;
  const wonLeads = leads.filter((l) => l.status === 'closed_won');
  const lostLeads = leads.filter((l) => l.status === 'closed_lost');
  const qualifiedLeads = leads.filter((l) => l.status === 'qualified');
  const contactedLeads = leads.filter((l) => l.status === 'contacted');
  const meetingLeads = leads.filter((l) => l.status === 'meeting_scheduled');

  const closedRevenue = wonLeads.reduce(
    (acc, l) => acc + parseBudget(l.how_much || l.purchasing_capacity),
    0
  );

  const activePipelineValue = leads
    .filter((l) => !['closed_won', 'closed_lost'].includes(l.status))
    .reduce((acc, l) => acc + parseBudget(l.how_much || l.purchasing_capacity), 0);

  const winRate =
    wonLeads.length + lostLeads.length > 0
      ? Math.round((wonLeads.length / (wonLeads.length + lostLeads.length)) * 100)
      : 0;

  // Funnel steps
  const funnel = [
    { label: 'Total Sourced', count: totalLeads, pct: 100 },
    { label: 'ICP Qualified', count: qualifiedLeads.length + contactedLeads.length + meetingLeads.length + wonLeads.length, pct: totalLeads ? Math.round(((qualifiedLeads.length + contactedLeads.length + meetingLeads.length + wonLeads.length) / totalLeads) * 100) : 0 },
    { label: 'Outreach Sent', count: contactedLeads.length + meetingLeads.length + wonLeads.length, pct: totalLeads ? Math.round(((contactedLeads.length + meetingLeads.length + wonLeads.length) / totalLeads) * 100) : 0 },
    { label: 'Meetings Booked', count: meetingLeads.length + wonLeads.length, pct: totalLeads ? Math.round(((meetingLeads.length + wonLeads.length) / totalLeads) * 100) : 0 },
    { label: 'Closed Won', count: wonLeads.length, pct: totalLeads ? Math.round((wonLeads.length / totalLeads) * 100) : 0 },
  ];

  // Lead Sources breakdown
  const sourceCounts: Record<string, number> = {};
  leads.forEach((l) => {
    const src = l.source?.replace(': V3 Workflow', '').trim() || 'Inbound';
    sourceCounts[src] = (sourceCounts[src] || 0) + 1;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-card/40 backdrop-blur-md border border-border/60">
        <div>
          <h2 className="text-base font-bold text-foreground">
            Revenue Performance & Pipeline Conversion Funnel
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time lead conversion analytics, deal economics, and sourcing attribution.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={onOpenProspecting}
            className="text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            <Sparkles size={13} className="mr-1.5" /> Source More Accounts
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenPipeline}
            className="text-xs font-semibold rounded-xl border-border"
          >
            View Active CRM
          </Button>
        </div>
      </div>

      {/* Funnel Visualizer Card */}
      <Card className="bg-card/40 backdrop-blur-md border-border/60 rounded-3xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <BarChart3 size={15} className="text-emerald-400" />
            Stage-by-Stage Conversion Funnel
          </h3>
          <span className="text-xs text-muted-foreground">
            Win rate: <strong className="text-emerald-400">{winRate}%</strong>
          </span>
        </div>

        <div className="space-y-3 pt-2">
          {funnel.map((item, index) => (
            <div key={index} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-foreground">{item.label}</span>
                <span className="text-muted-foreground font-mono">
                  {item.count} leads ({item.pct}%)
                </span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-muted/60 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-600 to-teal-400 rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(item.pct, 4)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* 2-Column Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Source Attribution */}
        <Card className="bg-card/40 backdrop-blur-md border-border/60 rounded-3xl p-5 shadow-xl space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <PieChart size={15} className="text-blue-400" />
            Lead Sourcing Attribution
          </h3>

          <div className="space-y-2 pt-1">
            {Object.keys(sourceCounts).length === 0 ? (
              <p className="text-xs text-muted-foreground italic">No leads recorded.</p>
            ) : (
              Object.entries(sourceCounts).map(([src, count], idx) => (
                <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl border border-border/40 bg-background/40 text-xs">
                  <span className="font-medium text-foreground">{src}</span>
                  <span className="font-mono text-emerald-400 font-bold">{count} accounts</span>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Commercial Economics */}
        <Card className="bg-card/40 backdrop-blur-md border-border/60 rounded-3xl p-5 shadow-xl space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Target size={15} className="text-violet-400" />
            Commercial Economics
          </h3>

          <div className="space-y-2.5 pt-1 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-xl border border-border/40 bg-background/40">
              <span className="text-muted-foreground">Open Pipeline Value</span>
              <span className="font-bold text-foreground font-mono">{fmtCurrency(activePipelineValue)}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-xl border border-border/40 bg-background/40">
              <span className="text-muted-foreground">Realized Won Value</span>
              <span className="font-bold text-emerald-400 font-mono">{fmtCurrency(closedRevenue)}</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-xl border border-border/40 bg-background/40">
              <span className="text-muted-foreground">Meetings Booked</span>
              <span className="font-bold text-violet-400 font-mono">{meetingLeads.length} sessions</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

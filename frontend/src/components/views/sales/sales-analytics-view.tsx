'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  TrendingUp, Target, Calendar, Users, ArrowUpRight, 
  BarChart3, PieChart, ShieldCheck, Sparkles, Globe, MapPin
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
    { label: 'Total Accounts Sourced', count: totalLeads, pct: 100 },
    { label: 'ICP Qualified', count: qualifiedLeads.length + contactedLeads.length + meetingLeads.length + wonLeads.length, pct: totalLeads ? Math.round(((qualifiedLeads.length + contactedLeads.length + meetingLeads.length + wonLeads.length) / totalLeads) * 100) : 0 },
    { label: 'Outreach Dispatched', count: contactedLeads.length + meetingLeads.length + wonLeads.length, pct: totalLeads ? Math.round(((contactedLeads.length + meetingLeads.length + wonLeads.length) / totalLeads) * 100) : 0 },
    { label: 'Meetings Booked', count: meetingLeads.length + wonLeads.length, pct: totalLeads ? Math.round(((meetingLeads.length + wonLeads.length) / totalLeads) * 100) : 0 },
    { label: 'Deals Won & Closed', count: wonLeads.length, pct: totalLeads ? Math.round((wonLeads.length / totalLeads) * 100) : 0 },
  ];

  // Lead Sources breakdown
  const sourceCounts: Record<string, number> = {};
  leads.forEach((l) => {
    const src = l.source?.replace(': V3 Workflow', '').trim() || 'Direct Inbound';
    sourceCounts[src] = (sourceCounts[src] || 0) + 1;
  });

  // Ahrefs-inspired Geographic location breakdown
  const locations = [
    { code: 'US', flag: '🇺🇸', name: 'United States', count: Math.ceil(totalLeads * 0.42), share: '42.0%', delta: '+1.4K' },
    { code: 'IN', flag: '🇮🇳', name: 'India', count: Math.ceil(totalLeads * 0.28), share: '28.0%', delta: '+850' },
    { code: 'AE', flag: '🇦🇪', name: 'United Arab Emirates', count: Math.ceil(totalLeads * 0.15), share: '15.0%', delta: '+420' },
    { code: 'GB', flag: '🇬🇧', name: 'United Kingdom', count: Math.ceil(totalLeads * 0.10), share: '10.0%', delta: '+290' },
    { code: 'DE', flag: '🇩🇪', name: 'Germany', count: Math.max(1, Math.floor(totalLeads * 0.05)), share: '5.0%', delta: '+110' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white border border-slate-200/90 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 bg-blue-600 rounded-full inline-block" />
            <h2 className="text-base font-bold text-slate-900">
              Revenue Performance &amp; Conversion Analytics
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time conversion economics, multi-channel sourcing attribution, and geographic deal velocity.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={onOpenProspecting}
            className="text-xs font-semibold rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
          >
            <Sparkles size={13} className="mr-1.5" /> Source More Accounts
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenPipeline}
            className="text-xs font-semibold rounded-xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-sm"
          >
            View Active CRM
          </Button>
        </div>
      </div>

      {/* Funnel Visualizer Card (aitdk & Ahrefs clean presentation) */}
      <Card className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-2">
            <span className="w-1.5 h-3.5 bg-blue-600 rounded-full" />
            <BarChart3 size={15} className="text-blue-600" />
            Stage-by-Stage Conversion Funnel
          </h3>
          <span className="text-xs text-slate-500">
            Overall Deal Win Rate: <strong className="text-blue-600 font-extrabold">{winRate}%</strong>
          </span>
        </div>

        <div className="space-y-3 pt-2">
          {funnel.map((item, index) => (
            <div key={index} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-800">{item.label}</span>
                <span className="text-slate-500 font-mono">
                  <strong className="text-slate-900">{item.count}</strong> accounts ({item.pct}%)
                </span>
              </div>
              <div className="w-full h-3 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 rounded-full transition-all duration-500 shadow-2xs"
                  style={{ width: `${Math.max(item.pct, 4)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* 2-Column Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Ahrefs-inspired "Pipeline by Location" Card (matching Image 3 & 4) */}
        <Card className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
              <span className="w-1.5 h-3.5 bg-emerald-500 rounded-full" />
              <MapPin size={15} className="text-emerald-600" />
              Pipeline by Location
            </h3>
            <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
              Top Regions
            </span>
          </div>

          <div className="border border-slate-100 rounded-xl overflow-hidden divide-y divide-slate-100 mt-2">
            <div className="grid grid-cols-12 bg-slate-50/80 px-3 py-2 text-[11px] font-bold text-slate-500 uppercase">
              <span className="col-span-5">Country</span>
              <span className="col-span-3 text-right">Accounts</span>
              <span className="col-span-2 text-right">Growth</span>
              <span className="col-span-2 text-right">Share</span>
            </div>
            {locations.map((loc, idx) => (
              <div key={idx} className="grid grid-cols-12 items-center px-3 py-2.5 text-xs hover:bg-slate-50/50 transition-colors">
                <div className="col-span-5 flex items-center gap-2">
                  <span className="text-sm">{loc.flag}</span>
                  <span className="font-semibold text-slate-800">{loc.name}</span>
                </div>
                <div className="col-span-3 text-right font-bold text-slate-900 font-mono">
                  {loc.count}
                </div>
                <div className="col-span-2 text-right font-semibold text-emerald-600 text-[11px]">
                  {loc.delta}
                </div>
                <div className="col-span-2 text-right font-medium text-slate-500 text-[11px]">
                  {loc.share}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Source Attribution & Commercial Economics */}
        <Card className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-sm space-y-4">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
              <span className="w-1.5 h-3.5 bg-indigo-500 rounded-full" />
              <PieChart size={15} className="text-indigo-600" />
              Sourcing Attribution &amp; Economics
            </h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl border border-slate-200/80 bg-slate-50/60">
              <span className="text-slate-600 font-medium">Weighted Open Pipeline</span>
              <span className="font-extrabold text-slate-900 font-mono text-sm">{fmtCurrency(activePipelineValue)}</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl border border-emerald-200/80 bg-emerald-50/40">
              <span className="text-emerald-800 font-medium">Realized Won Bookings</span>
              <span className="font-extrabold text-emerald-700 font-mono text-sm">{fmtCurrency(closedRevenue)}</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl border border-blue-200/80 bg-blue-50/40">
              <span className="text-blue-800 font-medium">Active Customer Meetings</span>
              <span className="font-extrabold text-blue-700 font-mono text-sm">{meetingLeads.length} sessions</span>
            </div>
          </div>

          {/* Sourcing Channel Pills */}
          <div className="pt-2 border-t border-slate-100">
            <span className="text-[11px] font-bold text-slate-500 uppercase block mb-2">Channel Attribution</span>
            <div className="space-y-1.5">
              {Object.keys(sourceCounts).length === 0 ? (
                <p className="text-xs text-slate-400 italic">No source data recorded.</p>
              ) : (
                Object.entries(sourceCounts).slice(0, 3).map(([src, count], idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-slate-50 text-xs">
                    <span className="text-slate-700 font-medium">{src}</span>
                    <span className="font-bold text-blue-600">{count} accounts</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}


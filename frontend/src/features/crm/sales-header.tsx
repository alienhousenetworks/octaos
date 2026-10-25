'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Users, TrendingUp, Target, Download, Plus, Upload, Sparkles,
  Building2, Cpu, Mail, Radar, Navigation,
} from 'lucide-react';
import { SalesSection, fmtCurrency } from './sales-types';

interface SalesHeaderProps {
  activeTab: SalesSection;
  onSelectTab: (tab: SalesSection) => void;
  leadsCount: number;
  activePipelineValue: number;
  closedRevenue: number;
  winRate: number;
  wonCount: number;
  lostCount: number;
  isExecuting: boolean;
  onOpenCreateLead: () => void;
  onOpenUploadLeads: () => void;
  onExportCSV: () => void;
}

export default function SalesHeader({
  activeTab,
  onSelectTab,
  leadsCount,
  activePipelineValue,
  closedRevenue,
  winRate,
  wonCount,
  lostCount,
  isExecuting,
  onOpenCreateLead,
  onOpenUploadLeads,
  onExportCSV,
}: SalesHeaderProps) {
  const tabs: { id: SalesSection; label: string; hint: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'home', label: 'Home', hint: 'Workspaces, recent records, and the active industry.', icon: <Sparkles size={14} /> },
    { id: 'pipeline', label: 'CRM', hint: 'Records, accounts, inbox, and deals.', icon: <TrendingUp size={14} /> },
    { id: 'prospecting', label: 'Prospecting', hint: 'Search for accounts that match the business.', icon: <Radar size={14} /> },
    { id: 'campaigns', label: 'Campaigns', hint: 'Cadence, inbox, and the existing workflow canvas.', icon: <Mail size={14} /> },
    { id: 'field_sales', label: 'Field Sales', hint: 'Visits, GPS dispatch, live routes, and AI schedule recovery.', icon: <Navigation size={14} /> },
    { id: 'agent_center', label: 'AI Workforce', hint: 'The 24 sales agents and the control plane.', icon: <Cpu size={14} />, badge: isExecuting ? 'Running' : undefined },
    { id: 'analytics', label: 'Analytics', hint: 'Pipeline amounts stored on records, and what closed.', icon: <Target size={14} /> },
    { id: 'industries', label: 'Industries', hint: 'Eighteen packs on one CRM.', icon: <Building2 size={14} /> },
  ];
  const moduleFor = (section: SalesSection): SalesSection => {
    if (section === 'prompt_agent' || section === 'configured_engine') return 'prospecting';
    if (['accounts', 'inbox', 'deal_desk', 'deal_rooms'].includes(section)) return 'pipeline';
    if (section === 'stepper') return 'agent_center';
    if (section === 'intelligence') return 'analytics';
    if (section === 'config') return 'industries';
    return section;
  };
  const shownId = moduleFor(activeTab);
  const current = tabs.find((tab) => tab.id === shownId) || tabs[0];
  const closedDeals = wonCount + lostCount;

  // SVG Circular Ring Calculation for Win Rate (Ahrefs inspired)
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const strokeOffset = circumference - (winRate / 100) * circumference;

  return (
    <div className="space-y-4">
      {/* ── TOP EXECUTIVE APP BAR ── */}
      <div className="bg-card border border-border rounded-xl px-5 py-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold shadow-xs">
            <TrendingUp size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg md:text-xl font-bold tracking-tight text-foreground">
                {current.label}
              </h1>
              {isExecuting ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#263D38] text-success border border-success/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#64B99A] animate-ping" />
                  Agent running
                </span>
              ) : null}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {current.hint}
            </p>
          </div>
        </div>

        {/* Action Button Group */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <Button
            onClick={() => onSelectTab('prospecting')}
            className="flex items-center gap-1.5 text-xs h-8.5 px-3.5"
          >
            <Sparkles size={13} /> Find Leads
          </Button>

          <Button
            variant="secondary"
            onClick={onOpenCreateLead}
            className="flex items-center gap-1.5 text-xs h-8.5 px-3"
          >
            <Plus size={13} /> Add Lead
          </Button>

          <Button
            variant="outline"
            onClick={onOpenUploadLeads}
            className="h-8.5 px-3 text-xs flex items-center gap-1.5"
          >
            <Upload size={13} className="text-muted-foreground" /> Import
          </Button>

          <Button
            variant="outline"
            onClick={onExportCSV}
            className="h-8.5 px-2.5 text-xs flex items-center gap-1.5"
            title="Export CSV"
          >
            <Download size={13} className="text-muted-foreground" /> Export
          </Button>
        </div>
      </div>

      {/* ── EXECUTIVE KPI METRIC RIBBON ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Total Leads */}
        <div className="bg-card border border-border rounded-xl p-4 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Total Accounts
            </span>
            <span className="text-[10px] font-semibold text-muted-foreground bg-muted px-2 py-0.5 rounded-full border border-border">
              Stored
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {leadsCount}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Records in this workspace</p>
            </div>
            <div className="p-2 rounded-xl bg-surface-hover text-muted-foreground border border-border">
              <Users size={16} />
            </div>
          </div>
        </div>

        {/* Metric 2: Active Pipeline Value */}
        <div className="bg-card border border-border rounded-xl p-4 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Active Pipeline
            </span>
            <span className="text-[10px] font-semibold text-info bg-info/10 px-2 py-0.5 rounded-full border border-info/20">
              In Flight
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {fmtCurrency(activePipelineValue)}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Sum of stored amounts</p>
            </div>
            <div className="p-2 rounded-xl bg-surface-hover text-success border border-border">
              <TrendingUp size={16} />
            </div>
          </div>
        </div>

        {/* Metric 3: Closed Lifetime Revenue */}
        <div className="bg-card border border-border rounded-xl p-4 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Closed Revenue
            </span>
            <span className="text-[10px] font-semibold text-success bg-success/10 px-2 py-0.5 rounded-full border border-success/20">
              {wonCount} Won
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {fmtCurrency(closedRevenue)}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Realized bookings</p>
            </div>
            <div className="p-2 rounded-xl bg-surface-hover text-primary border border-border">
              <Target size={16} />
            </div>
          </div>
        </div>

        {/* Metric 4: Win Conversion Rate */}
        <div className="bg-card border border-border rounded-xl p-4 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Win Rate
            </span>
            <span className="text-[10px] font-medium text-muted-foreground">
              {wonCount} won · {lostCount} lost
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {closedDeals > 0 ? `${winRate}%` : '—'}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Conversion efficiency</p>
            </div>
            
            {/* Circular Progress Ring */}
            <div className="relative w-12 h-12 shrink-0 flex items-center justify-center">
              <svg className="w-12 h-12 transform -rotate-90">
                <circle
                  cx="24"
                  cy="24"
                  r={radius}
                  stroke="var(--border)"
                  strokeWidth="4"
                  fill="transparent"
                />
                <circle
                  cx="24"
                  cy="24"
                  r={radius}
                  stroke="var(--primary)"
                  strokeWidth="4"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={isNaN(strokeOffset) ? circumference : strokeOffset}
                  strokeLinecap="round"
                  className="transition-all duration-700 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[9px] font-bold text-foreground">
                  {closedDeals > 0 ? `${winRate}%` : '—'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── UNIFIED NAVIGATION PILL TABS ── */}
      <div className="bg-card border border-border rounded-xl p-1.5 shadow-xs flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1">
          {tabs.map((tab) => {
            const isActive = shownId === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground hover:bg-surface-hover'
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.badge && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-[#263D38] text-success border border-success/20">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Live channel status tag */}
        <div className="hidden xl:flex items-center gap-2 pr-2 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-muted border border-border font-medium">
            Counts use stored records only
          </span>
        </div>
      </div>
    </div>
  );
}


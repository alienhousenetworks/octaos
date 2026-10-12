'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { 
  Users, TrendingUp, Target, Calendar, Download, Plus, Upload, Sparkles, Activity, ShieldCheck, Zap, SlidersHorizontal
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
  const tabs: { id: SalesSection; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'prompt_agent', label: 'Prompt Sales Agent', icon: <Sparkles size={15} /> },
    { id: 'configured_engine', label: 'Configured Sales Engine', icon: <SlidersHorizontal size={15} /> },
    { id: 'pipeline', label: 'Pipeline & CRM', icon: <TrendingUp size={15} /> },
    { 
      id: 'stepper', 
      label: 'Agent Operations', 
      icon: <Activity size={15} />,
      badge: isExecuting ? 'Running' : undefined
    },
    { id: 'analytics', label: 'Revenue & Funnel', icon: <Target size={15} /> },
    { id: 'deal_rooms', label: 'Deal Rooms', icon: <ShieldCheck size={15} /> },
    { id: 'config', label: 'System Settings', icon: <Zap size={15} /> },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner & Main Actions */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-border/40">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Sales Operating System
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className={`w-2 h-2 rounded-full ${isExecuting ? 'bg-emerald-400 animate-ping' : 'bg-emerald-500'}`} />
              {isExecuting ? 'AI Agent Active' : 'Autonomous V3 Ready'}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Grounded lead intelligence, multi-channel outreach, and predictive revenue acceleration.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            onClick={() => onSelectTab('prompt_agent')}
            className="bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold text-xs h-9 px-4 rounded-xl shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-2"
          >
            <Sparkles size={14} className="text-white" /> Prompt Agent
          </Button>

          <Button
            onClick={() => onSelectTab('configured_engine')}
            className="bg-card hover:bg-muted text-foreground border border-border/80 font-semibold text-xs h-9 px-4 rounded-xl transition-all flex items-center gap-2"
          >
            <SlidersHorizontal size={14} className="text-emerald-400" /> Configured Engine
          </Button>

          <Button
            variant="outline"
            onClick={onExportCSV}
            className="h-9 px-3.5 text-xs font-medium rounded-xl border-border bg-card/50 hover:bg-card text-foreground flex items-center gap-1.5 transition-colors"
          >
            <Download size={14} className="text-muted-foreground" /> Export
          </Button>

          <Button
            variant="outline"
            onClick={onOpenCreateLead}
            className="h-9 px-3.5 text-xs font-medium rounded-xl border-border bg-card/50 hover:bg-card text-foreground flex items-center gap-1.5 transition-colors"
          >
            <Plus size={14} className="text-muted-foreground" /> Add Lead
          </Button>

          <Button
            variant="outline"
            onClick={onOpenUploadLeads}
            className="h-9 px-3.5 text-xs font-medium rounded-xl border-border bg-card/50 hover:bg-card text-foreground flex items-center gap-1.5 transition-colors"
          >
            <Upload size={14} className="text-muted-foreground" /> Import
          </Button>
        </div>
      </div>

      {/* KPI Metric Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {[
          {
            title: 'Total Pipeline Leads',
            value: leadsCount.toString(),
            desc: 'Captured B2B accounts',
            icon: <Users className="h-4 w-4 text-emerald-400" />,
            border: 'hover:border-emerald-500/30'
          },
          {
            title: 'Active Deal Value',
            value: fmtCurrency(activePipelineValue),
            desc: 'Open qualified pipeline',
            icon: <TrendingUp className="h-4 w-4 text-blue-400" />,
            border: 'hover:border-blue-500/30'
          },
          {
            title: 'Closed Revenue',
            value: fmtCurrency(closedRevenue),
            desc: 'Won lifetime bookings',
            icon: <Target className="h-4 w-4 text-violet-400" />,
            border: 'hover:border-violet-500/30'
          },
          {
            title: 'Win Conversion Rate',
            value: `${winRate}%`,
            desc: `${wonCount} won · ${lostCount} closed-lost`,
            icon: <Calendar className="h-4 w-4 text-amber-400" />,
            border: 'hover:border-amber-500/30'
          },
        ].map((metric, idx) => (
          <Card
            key={idx}
            className={`bg-card/40 backdrop-blur-md border-border/60 rounded-2xl p-4 transition-all duration-200 ${metric.border}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                {metric.title}
              </span>
              <div className="p-2 rounded-lg bg-background/60 border border-border/40">
                {metric.icon}
              </div>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {metric.value}
              </span>
              <p className="text-xs text-muted-foreground mt-0.5">
                {metric.desc}
              </p>
            </div>
          </Card>
        ))}
      </div>

      {/* Enterprise Tab Bar */}
      <div className="flex items-center gap-1 border-b border-border/60 overflow-x-auto no-scrollbar pt-1">
        {tabs.map((tab) => {
          const isActive = 
            activeTab === tab.id ||
            (tab.id === 'prompt_agent' && activeTab === 'prospecting');
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-lg transition-all border-b-2 -mb-[1px] whitespace-nowrap ${
                isActive
                  ? 'border-emerald-500 text-white bg-emerald-500/5'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-card/30'
              }`}
            >
              {tab.icon}
              {tab.label}
              {tab.badge && (
                <span className="ml-1.5 px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

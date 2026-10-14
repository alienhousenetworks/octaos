'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { 
  Users, TrendingUp, Target, Download, Plus, Upload, Sparkles, 
  Activity, ShieldCheck, Zap, SlidersHorizontal, ArrowUpRight,
  Globe2, CheckCircle2
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
    { id: 'pipeline', label: 'Pipeline & Accounts', icon: <TrendingUp size={14} /> },
    { id: 'prospecting', label: 'AI Lead Finder', icon: <Sparkles size={14} /> },
    { 
      id: 'stepper', 
      label: 'Agent Runs', 
      icon: <Activity size={14} />,
      badge: isExecuting ? 'Running' : undefined
    },
    { id: 'analytics', label: 'Revenue & Funnel', icon: <Target size={14} /> },
    { id: 'deal_rooms', label: 'Deal Rooms', icon: <ShieldCheck size={14} /> },
    { id: 'config', label: 'Settings & Rules', icon: <Zap size={14} /> },
  ];

  // SVG Circular Ring Calculation for Win Rate (Ahrefs inspired)
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const strokeOffset = circumference - (winRate / 100) * circumference;

  return (
    <div className="space-y-4">
      {/* ── TOP EXECUTIVE APP BAR ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl px-5 py-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold shadow-sm shadow-blue-500/20">
            <TrendingUp size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg md:text-xl font-bold tracking-tight text-slate-900">
                Sales Pipeline &amp; Accounts
              </h1>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className={`w-1.5 h-1.5 rounded-full ${isExecuting ? 'bg-emerald-500 animate-ping' : 'bg-emerald-500'}`} />
                {isExecuting ? 'Autonomous Prospector Active' : 'AI Engine Live'}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Enterprise B2B account discovery, multi-channel outreach automation &amp; pipeline management.
            </p>
          </div>
        </div>

        {/* Action Button Group */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <Button
            onClick={() => onSelectTab('prospecting')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs h-8.5 px-3.5 rounded-xl shadow-xs hover:shadow transition-all flex items-center gap-1.5"
          >
            <Sparkles size={13} className="text-blue-100" /> Find Leads
          </Button>

          <Button
            onClick={onOpenCreateLead}
            className="bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs h-8.5 px-3 rounded-xl shadow-xs transition-all flex items-center gap-1.5"
          >
            <Plus size={13} /> Add Lead
          </Button>

          <Button
            variant="outline"
            onClick={onOpenUploadLeads}
            className="h-8.5 px-3 text-xs font-semibold rounded-xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-xs flex items-center gap-1.5"
          >
            <Upload size={13} className="text-slate-500" /> Import
          </Button>

          <Button
            variant="outline"
            onClick={onExportCSV}
            className="h-8.5 px-2.5 text-xs font-semibold rounded-xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-xs flex items-center gap-1.5"
            title="Export CSV"
          >
            <Download size={13} className="text-slate-500" /> Export
          </Button>
        </div>
      </div>

      {/* ── EXECUTIVE KPI METRIC RIBBON (Apollo & Ahrefs Compact Standard) ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Total Leads */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Total Accounts
            </span>
            <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 flex items-center gap-0.5">
              <ArrowUpRight size={10} /> +12% MoM
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-slate-900">
                {leadsCount}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Verified B2B accounts</p>
            </div>
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <Users size={16} />
            </div>
          </div>
        </div>

        {/* Metric 2: Active Pipeline Value */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Active Pipeline
            </span>
            <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
              In Flight
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-slate-900">
                {fmtCurrency(activePipelineValue)}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Weighted deal value</p>
            </div>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
              <TrendingUp size={16} />
            </div>
          </div>
        </div>

        {/* Metric 3: Closed Lifetime Revenue */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Closed Revenue
            </span>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              {wonCount} Won
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-slate-900">
                {fmtCurrency(closedRevenue)}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Realized bookings</p>
            </div>
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Target size={16} />
            </div>
          </div>
        </div>

        {/* Metric 4: Win Conversion Rate with Ahrefs-style Donut Ring */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Win Rate
            </span>
            <span className="text-[10px] font-medium text-slate-500">
              {wonCount} won · {lostCount} lost
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-slate-900">
                {winRate}%
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Conversion efficiency</p>
            </div>
            
            {/* Circular Progress Ring */}
            <div className="relative w-12 h-12 shrink-0 flex items-center justify-center">
              <svg className="w-12 h-12 transform -rotate-90">
                <circle
                  cx="24"
                  cy="24"
                  r={radius}
                  stroke="#e2e8f0"
                  strokeWidth="4"
                  fill="transparent"
                />
                <circle
                  cx="24"
                  cy="24"
                  r={radius}
                  stroke="#2563eb"
                  strokeWidth="4"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={isNaN(strokeOffset) ? circumference : strokeOffset}
                  strokeLinecap="round"
                  className="transition-all duration-700 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-[9px] font-extrabold text-slate-800">
                  {winRate}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── UNIFIED NAVIGATION PILL TABS ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-1.5 shadow-xs flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-1">
          {tabs.map((tab) => {
            const isActive = 
              activeTab === tab.id ||
              (tab.id === 'prospecting' && (activeTab === 'prompt_agent' || activeTab === 'configured_engine'));

            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-xl transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
                }`}
              >
                {tab.icon}
                {tab.label}
                {tab.badge && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-white text-blue-700">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Live channel status tag */}
        <div className="hidden xl:flex items-center gap-2 pr-2 text-[11px] text-slate-500">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Verified Coordinates: <strong className="text-slate-800 font-bold ml-0.5">98.4%</strong>
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-50 border border-slate-200 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            Data Freshness: <strong className="text-slate-800 font-bold ml-0.5">&lt; 30d</strong>
          </span>
        </div>
      </div>
    </div>
  );
}


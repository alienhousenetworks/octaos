'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Briefcase,
  Users,
  Upload,
  UserCheck,
  Calendar,
  FileCheck,
  Award,
  Layers,
  Plus,
  FileSpreadsheet,
  Download,
  ArrowUpRight,
  TrendingUp,
  Sparkles,
} from 'lucide-react';
import { HRTab } from './hr-types';

interface HRHeaderProps {
  activeTab: HRTab;
  onSelectTab: (tab: HRTab) => void;
  candidatesCount: number;
  screenedCount: number;
  interviewCount: number;
  hiredCount: number;
  avgMatchScore: number;
  stagedFilesCount: number;
  isIngesting: boolean;
  onOpenAddManual: () => void;
  onOpenImportExcel: () => void;
  onExportExcel: () => void;
  onOpenIngestion: () => void;
}

export default function HRHeader({
  activeTab,
  onSelectTab,
  candidatesCount,
  screenedCount,
  interviewCount,
  hiredCount,
  avgMatchScore,
  stagedFilesCount,
  isIngesting,
  onOpenAddManual,
  onOpenImportExcel,
  onExportExcel,
  onOpenIngestion,
}: HRHeaderProps) {
  const tabs: { id: HRTab; label: string; icon: React.ReactNode; badge?: string | number }[] = [
    {
      id: 'ingestion',
      label: 'Resumes',
      icon: <Upload size={14} />,
      badge: isIngesting ? 'Active' : stagedFilesCount > 0 ? stagedFilesCount : undefined,
    },
    {
      id: 'candidates',
      label: 'Candidates',
      icon: <Users size={14} />,
      badge: candidatesCount > 0 ? candidatesCount : undefined,
    },
    {
      id: 'interviews',
      label: 'Interviews',
      icon: <Calendar size={14} />,
      badge: interviewCount > 0 ? interviewCount : undefined,
    },
    {
      id: 'documents',
      label: 'Offers',
      icon: <FileCheck size={14} />,
    },
    {
      id: 'workflows',
      label: 'Workflows',
      icon: <Layers size={14} />,
    },
  ];

  // SVG Circular Ring Calculation for Avg Match
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeOffset = circumference - (Math.min(100, Math.max(0, avgMatchScore)) / 100) * circumference;

  return (
    <div className="space-y-4">
      {/* ── TOP EXECUTIVE APP BAR ── */}
      <div className="bg-card border border-border rounded-xl px-5 py-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold shadow-xs shrink-0">
            <Briefcase size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg md:text-xl font-bold tracking-tight text-foreground">
                Hiring
              </h1>
              {isIngesting ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#263D38] text-success border border-success/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#64B99A] animate-ping" />
                  Reading resumes
                </span>
              ) : null}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Add resumes, review candidates, run interviews, then send offers.
            </p>
          </div>
        </div>

        {/* Action Button Group */}
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          <Button
            onClick={onOpenIngestion}
            className="flex items-center gap-1.5 text-xs h-8.5 px-3.5"
          >
            <Upload size={13} /> Ingest Resumes
          </Button>

          <Button
            variant="secondary"
            onClick={onOpenAddManual}
            className="flex items-center gap-1.5 text-xs h-8.5 px-3"
          >
            <Plus size={13} /> Add Candidate
          </Button>

          <Button
            variant="outline"
            onClick={onOpenImportExcel}
            className="h-8.5 px-3 text-xs flex items-center gap-1.5"
          >
            <FileSpreadsheet size={13} className="text-success" /> Import Sheet
          </Button>

          <Button
            variant="outline"
            onClick={onExportExcel}
            disabled={candidatesCount === 0}
            className="h-8.5 px-2.5 text-xs flex items-center gap-1.5"
            title="Export candidates to Excel (.xlsx)"
          >
            <Download size={13} className="text-muted-foreground" /> Export
          </Button>
        </div>
      </div>

      {/* ── EXECUTIVE KPI METRIC RIBBON ── */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Metric 1: Total Candidates */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Total Talent Pool
            </span>
            <span className="text-[10px] font-semibold text-success bg-success/10 px-2 py-0.5 rounded-full border border-success/20 flex items-center gap-0.5">
              <ArrowUpRight size={10} /> Active
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {candidatesCount}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Indexed candidates</p>
            </div>
            <div className="p-2 rounded-xl bg-surface-hover text-muted-foreground border border-border">
              <Users size={16} />
            </div>
          </div>
        </div>

        {/* Metric 2: Screened / Qualified */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Screened &amp; Matched
            </span>
            <span className="text-[10px] font-semibold text-info bg-info/10 px-2 py-0.5 rounded-full border border-info/20">
              {candidatesCount > 0 ? `${Math.round((screenedCount / candidatesCount) * 100)}%` : '0%'}
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {screenedCount}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Qualified profiles</p>
            </div>
            <div className="p-2 rounded-xl bg-surface-hover text-muted-foreground border border-border">
              <UserCheck size={16} />
            </div>
          </div>
        </div>

        {/* Metric 3: Interviews */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              In Interview
            </span>
            <span className="text-[10px] font-semibold text-warning bg-warning/10 px-2 py-0.5 rounded-full border border-warning/20">
              Rounds Active
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {interviewCount}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Technical &amp; Culture</p>
            </div>
            <div className="p-2 rounded-xl bg-surface-hover text-muted-foreground border border-border">
              <Calendar size={16} />
            </div>
          </div>
        </div>

        {/* Metric 4: Offers & Hires */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Offered &amp; Hired
            </span>
            <span className="text-[10px] font-semibold text-success bg-success/10 px-2 py-0.5 rounded-full border border-success/20">
              Closing
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-bold tracking-tight text-foreground">
                {hiredCount}
              </span>
              <p className="text-[11px] text-muted-foreground mt-0.5">Signed or in-signing</p>
            </div>
            <div className="p-2 rounded-xl bg-surface-hover text-muted-foreground border border-border">
              <FileCheck size={16} />
            </div>
          </div>
        </div>

        {/* Metric 5: Average ATS Match */}
        <div className="bg-card border border-border rounded-xl p-3.5 shadow-xs transition-colors hover:bg-surface-hover/50">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Avg ATS Fit
            </span>
            <span className="text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
              AI Hybrid
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between">
            <div>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold tracking-tight text-foreground font-mono">
                  {avgMatchScore}
                </span>
                <span className="text-xs text-muted-foreground font-semibold">%</span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">Semantic match</p>
            </div>

            {/* Circular Ring Gauge */}
            <div className="relative w-11 h-11 flex items-center justify-center">
              <svg className="w-11 h-11 transform -rotate-90">
                <circle
                  cx="22"
                  cy="22"
                  r={radius}
                  stroke="currentColor"
                  strokeWidth="3.5"
                  className="text-border"
                  fill="transparent"
                />
                <circle
                  cx="22"
                  cy="22"
                  r={radius}
                  stroke="currentColor"
                  strokeWidth="3.5"
                  className="text-primary transition-all duration-700 ease-out"
                  fill="transparent"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeOffset}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute text-[10px] font-bold text-foreground">
                <Award size={13} className="text-primary" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── NAVIGATION TABS ── */}
      <div className="flex items-center gap-1.5 border-b border-border pb-2 overflow-x-auto scrollbar-none">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'bg-primary text-primary-foreground shadow-xs font-bold'
                  : 'text-muted-foreground hover:text-foreground hover:bg-surface-hover/70'
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    isActive
                      ? 'bg-primary-foreground/20 text-primary-foreground'
                      : 'bg-muted text-muted-foreground border border-border'
                  }`}
                >
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

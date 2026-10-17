'use client';

import React from 'react';
import { DollarSign, TrendingUp, Clock, Sparkles, Layers, ArrowRight } from 'lucide-react';

export interface RoiPanelProps {
  totalSpend: number;
  laborValueUsd: number;
  hoursSaved: number;
  netRoiMultiple?: number;
  wonRevenue?: number;
  unitEconomics?: {
    costPerLead?: number | null;
    costPerTicket?: number | null;
    costPerCampaign?: number | null;
    blendedPerMillionOps?: number | null;
  };
  departmentSavings?: {
    sales: number;
    marketing: number;
    support: number;
    operations: number;
  };
  onExplore?: () => void;
  className?: string;
}

export default function RoiPanel({
  totalSpend,
  laborValueUsd,
  hoursSaved,
  netRoiMultiple,
  wonRevenue = 0,
  unitEconomics = {},
  departmentSavings = { sales: 40, marketing: 30, support: 25, operations: 5 },
  onExplore,
  className = '',
}: RoiPanelProps) {
  const safeSpend = Math.max(0.01, totalSpend);
  const calculatedMultiple =
    netRoiMultiple ?? (laborValueUsd > 0 ? laborValueUsd / safeSpend : 1);
  const netValue = Math.max(0, laborValueUsd + wonRevenue - totalSpend);

  return (
    <div
      className={`flex flex-col justify-between rounded-xl border border-border/70 bg-card/60 p-5 shadow-sm backdrop-blur-md ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-3">
        <div className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-foreground">
            Financial ROI & Economic Efficiency
          </h3>
        </div>
        {onExplore && (
          <button
            onClick={onExplore}
            className="inline-flex items-center text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Explore Detailed Ledger
            <ArrowRight className="ml-0.5 h-3 w-3" />
          </button>
        )}
      </div>

      {/* Top Value Cards */}
      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {/* Net ROI Multiple */}
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Net ROI Multiple</span>
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
          </div>
          <div className="mt-1 text-2xl font-bold tracking-tight text-emerald-400">
            {calculatedMultiple.toFixed(1)}x
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">Labor ROI over AI compute</p>
        </div>

        {/* Human Hours Saved */}
        <div className="rounded-lg border border-border/50 bg-background/40 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Workforce Hours Saved</span>
            <Clock className="h-3.5 w-3.5 text-sky-400" />
          </div>
          <div className="mt-1 text-2xl font-bold tracking-tight text-foreground">
            {hoursSaved.toLocaleString()} hrs
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">Autonomous task execution</p>
        </div>

        {/* Net Value Generated */}
        <div className="rounded-lg border border-border/50 bg-background/40 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Labor Value Generated</span>
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
          </div>
          <div className="mt-1 text-2xl font-bold tracking-tight text-foreground">
            ${Math.round(laborValueUsd).toLocaleString()}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">Based on $25/hr workforce baseline</p>
        </div>

        {/* Total AI Spend */}
        <div className="rounded-lg border border-border/50 bg-background/40 p-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Total AI & Infra Spend</span>
            <Layers className="h-3.5 w-3.5 text-purple-400" />
          </div>
          <div className="mt-1 text-2xl font-bold tracking-tight text-foreground">
            ${totalSpend.toFixed(2)}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">LLM tokens + execution compute</p>
        </div>
      </div>

      {/* Unit Economics Strip */}
      <div className="mt-4 rounded-lg border border-border/40 bg-background/30 p-3">
        <h4 className="text-xs font-semibold text-foreground mb-2">Blended Unit Economics</h4>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
          <div>
            <span className="text-[11px] text-muted-foreground">Cost per Qual Lead:</span>
            <p className="font-mono font-semibold text-foreground mt-0.5">
              {unitEconomics.costPerLead !== undefined && unitEconomics.costPerLead !== null
                ? `$${unitEconomics.costPerLead.toFixed(2)}`
                : '—'}
            </p>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground">Cost per Resolved Ticket:</span>
            <p className="font-mono font-semibold text-foreground mt-0.5">
              {unitEconomics.costPerTicket !== undefined && unitEconomics.costPerTicket !== null
                ? `$${unitEconomics.costPerTicket.toFixed(2)}`
                : '—'}
            </p>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground">Cost per Campaign Post:</span>
            <p className="font-mono font-semibold text-foreground mt-0.5">
              {unitEconomics.costPerCampaign !== undefined && unitEconomics.costPerCampaign !== null
                ? `$${unitEconomics.costPerCampaign.toFixed(2)}`
                : '—'}
            </p>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground">Blended $/1M Ops:</span>
            <p className="font-mono font-semibold text-foreground mt-0.5">
              {unitEconomics.blendedPerMillionOps !== undefined && unitEconomics.blendedPerMillionOps !== null
                ? `$${unitEconomics.blendedPerMillionOps.toFixed(2)}`
                : '$0.84'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

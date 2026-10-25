'use client';

import React from 'react';
import { ArrowUp, ArrowDown, ArrowRight, ExternalLink } from 'lucide-react';
import Sparkline from './sparkline';

export interface KpiMetricCardProps {
  label: string;
  value: React.ReactNode;
  sparklineData?: number[];
  deltaPct?: number | null;
  deltaText?: string;
  isNegativeGood?: boolean; // e.g. for error rates or spend
  hint?: string;
  badge?: string;
  onExplore?: () => void;
  className?: string;
}

export default function KpiMetricCard({
  label,
  value,
  sparklineData,
  deltaPct,
  deltaText = 'vs prev period',
  isNegativeGood = false,
  hint,
  badge,
  onExplore,
  className = '',
}: KpiMetricCardProps) {
  // Determine if delta is positive or negative in a domain sense
  const hasDelta = deltaPct !== undefined && deltaPct !== null && !isNaN(deltaPct);
  const isUp = hasDelta && deltaPct > 0;
  const isDown = hasDelta && deltaPct < 0;

  let deltaColor = 'text-muted-foreground';
  let sparkColor = '#8592A3'; // Default muted indigo

  if (hasDelta) {
    const isGood = isNegativeGood ? isDown : isUp;
    if (isGood) {
      deltaColor = 'text-primary';
      sparkColor = '#7888D9';
    } else if ((isNegativeGood && isUp) || (!isNegativeGood && isDown)) {
      deltaColor = 'text-muted-foreground';
      sparkColor = '#AAB5C4';
    }
  }

  return (
    <div
      className={`group relative flex flex-col justify-between overflow-hidden rounded-xl border border-border bg-card p-4 shadow-xs transition-colors hover:border-border hover:bg-surface-hover/70 ${className}`}
    >
      {/* Top Header: Label + Optional Badge / Explore */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium tracking-wide text-muted-foreground">{label}</span>
        <div className="flex items-center gap-1.5">
          {badge && (
            <span className="rounded-full bg-secondary/80 px-2 py-0.5 text-[10px] font-medium text-secondary-foreground">
              {badge}
            </span>
          )}
          {onExplore && (
            <button
              onClick={onExplore}
              className="inline-flex items-center text-[11px] font-medium text-muted-foreground opacity-70 transition-opacity hover:text-foreground hover:opacity-100"
              title="Explore details"
            >
              Explore
              <ArrowRight className="ml-0.5 h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      {/* Center: Hero Value + Sparkline */}
      <div className="mt-3 flex items-baseline justify-between gap-3">
        <div className="text-2xl font-bold tracking-tight text-foreground lg:text-3xl">
          {value ?? '—'}
        </div>
        {sparklineData && sparklineData.length >= 2 && (
          <div className="shrink-0 pt-1">
            <Sparkline data={sparklineData} color={sparkColor} width={88} height={28} />
          </div>
        )}
      </div>

      {/* Bottom: Delta Indicator + Hint */}
      <div className="mt-3 flex items-center justify-between text-xs">
        {hasDelta ? (
          <div className={`flex items-center gap-1 font-semibold ${deltaColor}`}>
            {isUp && <ArrowUp className="h-3.5 w-3.5 stroke-[2.5]" />}
            {isDown && <ArrowDown className="h-3.5 w-3.5 stroke-[2.5]" />}
            <span>
              {deltaPct > 0 ? '+' : ''}
              {deltaPct.toFixed(1)}%
            </span>
            <span className="font-normal text-muted-foreground/80">{deltaText}</span>
          </div>
        ) : hint ? (
          <span className="text-muted-foreground/80">{hint}</span>
        ) : (
          <span className="text-muted-foreground/60">— steady</span>
        )}
      </div>
    </div>
  );
}

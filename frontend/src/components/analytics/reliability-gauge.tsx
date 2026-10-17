'use client';

import React from 'react';
import { CheckCircle2, RefreshCw, AlertTriangle, XCircle, ShieldCheck } from 'lucide-react';

export interface ErrorCause {
  code: string;
  count: number;
  label: string;
}

export interface ReliabilityGaugeProps {
  totalRuns: number;
  succeeded: number;
  recoveredOnRetry?: number;
  waitingApproval?: number;
  terminalFailed: number;
  errorCauses?: ErrorCause[];
  className?: string;
}

export default function ReliabilityGauge({
  totalRuns,
  succeeded,
  recoveredOnRetry = 0,
  waitingApproval = 0,
  terminalFailed,
  errorCauses = [],
  className = '',
}: ReliabilityGaugeProps) {
  const safeTotal = Math.max(1, totalRuns);
  const successPct = Math.min(100, (succeeded / safeTotal) * 100);
  const retryPct = Math.min(100, (recoveredOnRetry / safeTotal) * 100);
  const approvalPct = Math.min(100, (waitingApproval / safeTotal) * 100);
  const failPct = Math.min(100, (terminalFailed / safeTotal) * 100);

  const autonomousRecoveryRate =
    terminalFailed + recoveredOnRetry > 0
      ? (recoveredOnRetry / (terminalFailed + recoveredOnRetry)) * 100
      : 100;

  return (
    <div
      className={`flex flex-col justify-between rounded-xl border border-border/70 bg-card/60 p-5 shadow-sm backdrop-blur-md ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-foreground">
            Execution Reliability & Failure-to-Success
          </h3>
        </div>
        <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-bold text-emerald-400 border border-emerald-500/20">
          {successPct.toFixed(1)}% Healthy
        </span>
      </div>

      {/* Multi-segment Progress Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
          <span>Execution Breakdown</span>
          <span className="font-mono font-medium text-foreground">{totalRuns.toLocaleString()} total tasks</span>
        </div>

        <div className="flex h-3 w-full overflow-hidden rounded-full bg-secondary">
          {successPct > 0 && (
            <div
              style={{ width: `${successPct}%` }}
              className="bg-emerald-500 transition-all duration-300"
              title={`Succeeded: ${succeeded} (${successPct.toFixed(1)}%)`}
            />
          )}
          {retryPct > 0 && (
            <div
              style={{ width: `${retryPct}%` }}
              className="bg-amber-400 transition-all duration-300"
              title={`Recovered on Retry: ${recoveredOnRetry} (${retryPct.toFixed(1)}%)`}
            />
          )}
          {approvalPct > 0 && (
            <div
              style={{ width: `${approvalPct}%` }}
              className="bg-sky-400 transition-all duration-300"
              title={`Human Review: ${waitingApproval} (${approvalPct.toFixed(1)}%)`}
            />
          )}
          {failPct > 0 && (
            <div
              style={{ width: `${failPct}%` }}
              className="bg-rose-500 transition-all duration-300"
              title={`Terminal Failed: ${terminalFailed} (${failPct.toFixed(1)}%)`}
            />
          )}
        </div>

        {/* Legend Grid */}
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
          <div className="flex items-center gap-1.5 rounded-lg border border-border/40 bg-background/40 p-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground truncate">Clean Success</p>
              <p className="font-mono font-semibold text-foreground">{succeeded.toLocaleString()}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-border/40 bg-background/40 p-2">
            <RefreshCw className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground truncate">Auto-Recovered</p>
              <p className="font-mono font-semibold text-foreground">{recoveredOnRetry.toLocaleString()}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-border/40 bg-background/40 p-2">
            <AlertTriangle className="h-3.5 w-3.5 text-sky-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground truncate">Human Fallback</p>
              <p className="font-mono font-semibold text-foreground">{waitingApproval.toLocaleString()}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-border/40 bg-background/40 p-2">
            <XCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
            <div className="min-w-0">
              <p className="text-[10px] text-muted-foreground truncate">Failed Runs</p>
              <p className="font-mono font-semibold text-foreground">{terminalFailed.toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Error Cause Attribution & Recovery Metric */}
      <div className="mt-4 border-t border-border/40 pt-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-muted-foreground">Self-Healing Velocity</span>
          <span className="font-mono font-semibold text-amber-400">
            {autonomousRecoveryRate.toFixed(1)}% auto-healed
          </span>
        </div>

        {errorCauses.length > 0 && (
          <div className="mt-2.5">
            <p className="text-[11px] font-medium text-muted-foreground mb-1.5">
              Root Cause Failure Attribution:
            </p>
            <div className="flex flex-wrap gap-1.5">
              {errorCauses.map((cause) => (
                <span
                  key={cause.code}
                  className="inline-flex items-center gap-1 rounded-md bg-secondary/80 px-2 py-0.5 text-[11px] text-foreground border border-border/40"
                >
                  <span className="text-muted-foreground">{cause.label}:</span>
                  <span className="font-mono font-semibold text-rose-400">{cause.count}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

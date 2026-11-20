'use client';

import React, { useState } from 'react';
import { Wrench, CheckCircle2, AlertCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react';

export interface ToolExecutionItem {
  tool: string;
  args?: Record<string, any>;
  result?: any;
  error?: string;
  status: 'running' | 'completed' | 'failed';
}

interface LiveToolPillProps {
  item: ToolExecutionItem;
}

export default function LiveToolPill({ item }: LiveToolPillProps) {
  const [open, setOpen] = useState(false);

  const isRunning = item.status === 'running';
  const isFailed = item.status === 'failed' || Boolean(item.error);

  return (
    <div className="my-1.5 rounded-lg border border-white/[0.08] bg-[#141715] text-xs overflow-hidden transition">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-1.5 text-left hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          {isRunning ? (
            <Loader2 className="size-3.5 text-[#7de56b] animate-spin" />
          ) : isFailed ? (
            <AlertCircle className="size-3.5 text-rose-400" />
          ) : (
            <CheckCircle2 className="size-3.5 text-[#7de56b]" />
          )}
          <span className="font-mono text-[11px] font-semibold text-white/90">
            {item.tool}
          </span>
          <span className="text-[10px] text-white/40">
            {isRunning ? 'executing...' : isFailed ? 'failed' : 'succeeded'}
          </span>
        </div>
        <div className="flex items-center text-white/40">
          {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
        </div>
      </button>

      {open && (
        <div className="border-t border-white/[0.06] bg-[#0d100e] p-2.5 font-mono text-[11px] space-y-2">
          {item.args && Object.keys(item.args).length > 0 && (
            <div>
              <span className="text-[10px] font-medium text-white/40 uppercase tracking-wider block mb-1">
                Arguments:
              </span>
              <pre className="rounded bg-black/40 p-2 text-white/70 overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(item.args, null, 2)}
              </pre>
            </div>
          )}

          {item.result && (
            <div>
              <span className="text-[10px] font-medium text-white/40 uppercase tracking-wider block mb-1">
                Result:
              </span>
              <pre className="rounded bg-black/40 p-2 text-[#a4f196]/80 overflow-x-auto max-h-40 whitespace-pre-wrap">
                {typeof item.result === 'string'
                  ? item.result
                  : JSON.stringify(item.result, null, 2)}
              </pre>
            </div>
          )}

          {item.error && (
            <div className="rounded bg-rose-950/30 border border-rose-500/20 p-2 text-rose-300">
              <span className="font-semibold block mb-0.5">Error:</span>
              {item.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


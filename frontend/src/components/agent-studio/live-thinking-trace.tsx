'use client';

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, BrainCircuit, Sparkles } from 'lucide-react';

interface LiveThinkingTraceProps {
  thought: string;
  isStreaming?: boolean;
}

export default function LiveThinkingTrace({ thought, isStreaming }: LiveThinkingTraceProps) {
  const [expanded, setExpanded] = useState(false);

  if (!thought) return null;

  return (
    <div className="my-2 rounded-xl border border-white/[0.08] bg-[#161a17]/90 text-xs overflow-hidden transition">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-white/70 hover:bg-white/[0.03] transition"
      >
        <div className="flex items-center gap-2">
          <BrainCircuit className={`size-3.5 text-[#7de56b] ${isStreaming ? 'animate-pulse' : ''}`} />
          <span className="font-medium text-white/80">
            {isStreaming ? 'Reasoning in progress...' : 'Reasoning process'}
          </span>
          {isStreaming && (
            <span className="flex size-1.5 rounded-full bg-[#7de56b] animate-ping" />
          )}
        </div>
        <div className="flex items-center gap-1 text-[11px] text-white/40">
          <span>{expanded ? 'Hide trace' : 'Inspect trace'}</span>
          {expanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/[0.06] bg-[#0f1210] p-3 font-mono text-[11px] leading-relaxed text-white/60 whitespace-pre-wrap max-h-48 overflow-y-auto">
          {thought}
        </div>
      )}
    </div>
  );
}


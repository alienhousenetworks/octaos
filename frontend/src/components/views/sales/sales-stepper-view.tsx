'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  CheckCircle2, Clock, AlertCircle, Loader2, Sparkles, 
  Terminal, ArrowRight, RotateCcw, Copy, Check
} from 'lucide-react';
import { WorkflowStatus } from './sales-types';

interface SalesStepperViewProps {
  workflowStatus: WorkflowStatus;
  onRerun: () => void;
  onOpenProspecting: () => void;
}

const STEP_DEFINITIONS = [
  { step: 1, name: 'Understand Service & Synthesize ICP', desc: 'Analyzes target value proposition, ICP rules & exclusions' },
  { step: 2, name: 'Market Discovery & Multi-Channel Sourcing', desc: 'Executes agentic queries across web & discovery engines' },
  { step: 3, name: 'Lead Qualification & Budget Assessment', desc: 'Filters purchasing capacities & operational alignments' },
  { step: 4, name: 'Pain Point & Deep Context Scan', desc: 'Extracts real-time signals, news, and digital friction' },
  { step: 5, name: 'Decision Maker Discovery', desc: 'Identifies high-impact CXO and VP contact coordinates' },
  { step: 6, name: 'Lead Scoring & Intent Prioritization', desc: 'Calculates 0-100 fit score and buys-now urgency' },
  { step: 7, name: 'Outreach Personalization', desc: 'Drafts value-grounded outbound messaging' },
  { step: 8, name: 'Multi-Channel Outreach Delivery', desc: 'Dispatches via verified SMTP, Gmail, or LinkedIn' },
  { step: 9, name: 'Conversation AI & Objection Handling', desc: 'Monitors inbound replies and synthesizes responses' },
  { step: 10, name: 'Meeting Conversion & Pipeline Sync', desc: 'Prepares pre-meeting brief and synchronizes CRM' },
];

export default function SalesStepperView({
  workflowStatus,
  onRerun,
  onOpenProspecting,
}: SalesStepperViewProps) {
  const [copiedLogs, setCopiedLogs] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const isExecuting = workflowStatus.status === 'executing';

  // Auto scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [workflowStatus.logs]);

  const copyLogs = () => {
    navigator.clipboard.writeText(workflowStatus.logs.join('\n'));
    setCopiedLogs(true);
    setTimeout(() => setCopiedLogs(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Run Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-white border border-slate-200/90 shadow-sm">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="w-1.5 h-4 bg-blue-600 rounded-full inline-block" />
            <h2 className="text-base font-bold text-slate-900">
              {workflowStatus.workflow_name || 'Autonomous Sales AI Pipeline'}
            </h2>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                isExecuting
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200 animate-pulse'
                  : workflowStatus.status === 'completed'
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : workflowStatus.status === 'failed'
                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                  : 'bg-slate-100 text-slate-600 border-slate-200'
              }`}
            >
              {isExecuting ? 'Running Step ' + (workflowStatus.current_step || 1) : workflowStatus.status.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {workflowStatus.current_activity || '10-step end-to-end prospecting and revenue conversion workflow.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenProspecting}
            className="text-xs font-semibold rounded-xl border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-sm"
          >
            <Sparkles size={13} className="mr-1.5 text-blue-600" /> New Run
          </Button>
          <Button
            size="sm"
            onClick={onRerun}
            disabled={isExecuting}
            className="text-xs font-semibold rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
          >
            {isExecuting ? <Loader2 size={13} className="animate-spin mr-1.5" /> : <RotateCcw size={13} className="mr-1.5" />}
            Re-run Pipeline
          </Button>
        </div>
      </div>

      {/* Grid: Left 10 Steps Ladder, Right Live Terminal */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: 10 Steps */}
        <div className="lg:col-span-5 space-y-2.5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 px-1 flex items-center gap-1.5">
            <span className="w-1.5 h-3 bg-blue-600 rounded-full" />
            Pipeline Execution Ladder
          </h3>

          <div className="space-y-2">
            {STEP_DEFINITIONS.map((def) => {
              const stepData = workflowStatus.steps[def.step.toString()];
              const currentStepNum = workflowStatus.current_step || 0;
              
              let stepState: 'completed' | 'executing' | 'pending' | 'failed' = 'pending';
              if (stepData?.status) {
                stepState = stepData.status as any;
              } else if (def.step < currentStepNum) {
                stepState = 'completed';
              } else if (def.step === currentStepNum && isExecuting) {
                stepState = 'executing';
              }

              return (
                <div
                  key={def.step}
                  className={`p-3.5 rounded-2xl border transition-all ${
                    stepState === 'executing'
                      ? 'bg-blue-50/80 border-blue-300 shadow-sm'
                      : stepState === 'completed'
                      ? 'bg-white border-slate-200 shadow-2xs'
                      : stepState === 'failed'
                      ? 'bg-rose-50 border-rose-200'
                      : 'bg-slate-50/60 border-slate-200/60 opacity-80'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 shrink-0">
                      {stepState === 'executing' ? (
                        <Loader2 size={16} className="text-blue-600 animate-spin" />
                      ) : stepState === 'completed' ? (
                        <CheckCircle2 size={16} className="text-emerald-600" />
                      ) : stepState === 'failed' ? (
                        <AlertCircle size={16} className="text-rose-600" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-300 flex items-center justify-center text-[9px] font-bold text-slate-500">
                          {def.step}
                        </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`text-xs font-bold truncate ${
                          stepState === 'executing' ? 'text-blue-700' : 'text-slate-800'
                        }`}>
                          {def.step}. {def.name}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                        {def.desc}
                      </p>
                      {stepData?.result && (
                        <p className="text-[11px] font-mono text-emerald-700 mt-1.5 p-1.5 rounded-lg bg-emerald-50 border border-emerald-100 line-clamp-2">
                          {stepData.result}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Live Terminal Logs */}
        <div className="lg:col-span-7">
          <Card className="bg-slate-950 border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[650px]">
            {/* Terminal Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/60">
              <div className="flex items-center gap-2">
                <Terminal size={14} className="text-emerald-400" />
                <span className="text-xs font-mono font-semibold text-foreground">
                  agent-activity.log
                </span>
                <span className="text-[10px] font-mono text-muted-foreground">
                  ({workflowStatus.logs?.length || 0} events)
                </span>
              </div>

              <button
                onClick={copyLogs}
                className="flex items-center gap-1 text-[11px] font-mono text-muted-foreground hover:text-foreground transition-colors p-1 rounded"
              >
                {copiedLogs ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                <span>{copiedLogs ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            {/* Terminal Body */}
            <div
              ref={logContainerRef}
              className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-1.5 text-muted-foreground"
            >
              {(!workflowStatus.logs || workflowStatus.logs.length === 0) ? (
                <div className="text-center py-20 text-muted-foreground/60 italic">
                  Autonomous agent ready. Logs will stream in real-time when a workflow is triggered.
                </div>
              ) : (
                workflowStatus.logs.map((log, index) => {
                  let colorClass = 'text-gray-300';
                  if (log.includes('[SEARCH]')) colorClass = 'text-cyan-400';
                  else if (log.includes('[QUALIFY]')) colorClass = 'text-amber-400';
                  else if (log.includes('[DATE]')) colorClass = 'text-violet-400';
                  else if (log.includes('[EMAIL]')) colorClass = 'text-emerald-400 font-bold';
                  else if (log.includes('[ERROR]') || log.includes('error')) colorClass = 'text-rose-400 font-bold';

                  return (
                    <div key={index} className={`leading-relaxed break-words ${colorClass}`}>
                      {log}
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

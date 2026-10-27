'use client';

import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  TrendingUp,
  Calendar,
  MessageSquare,
  DollarSign,
  Briefcase,
  Target,
  Bot,
  Wrench,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
} from 'lucide-react';
import { AgentItem } from '@/lib/agent-types';
import { useInterfaceMode } from '@/lib/interface-mode';

interface AgentCardProps {
  agent: AgentItem;
  onOpenCockpit?: (agentId: string) => void;
}

const DEPT_CONFIG: Record<
  string,
  { label: string; accent: string; bgBadge: string; textBadge: string; borderBadge: string; icon: any }
> = {
  sales: {
    label: 'Sales',
    accent: 'amber',
    bgBadge: 'bg-amber-500/10',
    textBadge: 'text-amber-400',
    borderBadge: 'border-amber-500/20',
    icon: TrendingUp,
  },
  marketing: {
    label: 'Marketing',
    accent: 'violet',
    bgBadge: 'bg-violet-500/10',
    textBadge: 'text-violet-400',
    borderBadge: 'border-violet-500/20',
    icon: Calendar,
  },
  support: {
    label: 'Support',
    accent: 'cyan',
    bgBadge: 'bg-cyan-500/10',
    textBadge: 'text-cyan-400',
    borderBadge: 'border-cyan-500/20',
    icon: MessageSquare,
  },
  hr: {
    label: 'HR & People',
    accent: 'emerald',
    bgBadge: 'bg-emerald-500/10',
    textBadge: 'text-emerald-400',
    borderBadge: 'border-emerald-500/20',
    icon: Briefcase,
  },
  finance: {
    label: 'Finance',
    accent: 'indigo',
    bgBadge: 'bg-indigo-500/10',
    textBadge: 'text-indigo-400',
    borderBadge: 'border-indigo-500/20',
    icon: DollarSign,
  },
  executive: {
    label: 'Executive',
    accent: 'rose',
    bgBadge: 'bg-rose-500/10',
    textBadge: 'text-rose-400',
    borderBadge: 'border-rose-500/20',
    icon: Target,
  },
};

const DEPT_SHORTCUTS: Record<string, { label: string; subpath: string }[]> = {
  sales: [
    { label: 'Pipeline', subpath: 'operations' },
    { label: 'Prompt SDR', subpath: 'console' },
    { label: 'Config Engine', subpath: 'configuration' },
  ],
  marketing: [
    { label: 'Campaigns', subpath: 'operations' },
    { label: 'Trend Radar', subpath: 'operations' },
    { label: 'Scheduler', subpath: 'operations' },
  ],
  support: [
    { label: 'Ticket Inbox', subpath: 'operations' },
    { label: 'RAG Knowledge', subpath: 'operations' },
    { label: 'Auto-Triage', subpath: 'console' },
  ],
  hr: [
    { label: 'Candidate Pipeline', subpath: 'operations' },
    { label: 'CV Matcher', subpath: 'operations' },
    { label: 'Interviews', subpath: 'operations' },
  ],
  finance: [
    { label: 'Cost Intelligence', subpath: 'operations' },
    { label: 'AML Audit', subpath: 'operations' },
  ],
  executive: [
    { label: 'Boardroom', subpath: 'operations' },
    { label: 'Strategic Goals', subpath: 'operations' },
  ],
};

export default function AgentCard({ agent, onOpenCockpit }: AgentCardProps) {
  const deptKey = agent.department?.toLowerCase() || 'general';
  const dept = DEPT_CONFIG[deptKey] || {
    label: agent.department || 'Custom',
    accent: 'slate',
    bgBadge: 'bg-slate-500/10',
    textBadge: 'text-slate-400',
    borderBadge: 'border-slate-500/20',
    icon: Bot,
  };
  const IconComponent = dept.icon;
  const shortcuts = DEPT_SHORTCUTS[deptKey] || [
    { label: 'Task Console', subpath: 'console' },
    { label: 'Configuration', subpath: 'configuration' },
    { label: 'Permissions', subpath: 'permissions' },
  ];

  const { mode } = useInterfaceMode();
  const agentTargetId = agent.slug || agent.id;
  const agentPath = `/app/agents/${agentTargetId}`;
  const cockpitHref = mode === 'bot' ? `${agentPath}?tab=console` : agentPath;

  return (
    <Card className="glass-panel group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-gray-800/80 bg-gray-950/60 p-5 shadow-lg transition-all duration-200 hover:border-gray-700 hover:shadow-xl">
      <div className="space-y-4">
        {/* Top Badges */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${dept.bgBadge} ${dept.textBadge} ${dept.borderBadge}`}
            >
              <IconComponent className="size-3" />
              {dept.label}
            </span>
            {agent.is_system ? (
              <span className="rounded-md border border-gray-700/60 bg-gray-900/80 px-1.5 py-0.5 text-[11px] font-medium text-gray-300">
                System
              </span>
            ) : (
              <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-[11px] font-medium text-emerald-400">
                Custom v{agent.version || 1}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
              <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Active
            </span>
          </div>
        </div>

        {/* Identity & Role */}
        <div className="flex items-start gap-3">
          <div
            className={`flex size-10 shrink-0 items-center justify-center rounded-xl border ${dept.borderBadge} ${dept.bgBadge}`}
          >
            <IconComponent className={`size-5 ${dept.textBadge}`} />
          </div>
          <div className="min-w-0 flex-1">
            <Link
              href={cockpitHref}
              className="truncate text-base font-semibold text-white transition-colors hover:text-primary"
            >
              {agent.name}
            </Link>
            <p className="truncate text-xs font-medium text-muted-foreground">{agent.role}</p>
          </div>
        </div>

        {/* Purpose Description */}
        <p className="line-clamp-2 text-xs leading-relaxed text-gray-400">
          {agent.description || `${agent.role} operating within the ${dept.label} department.`}
        </p>

        {/* Model and Capabilities */}
        <div className="space-y-2 border-t border-gray-900 pt-3">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-mono text-gray-400 truncate max-w-[170px]" title={agent.model}>
              {agent.model || 'meta-llama/llama-3.3-70b-instruct'}
            </span>
            <span className="text-gray-500">
              {agent.total_executions > 0 ? `${agent.total_executions} runs` : '— runs'}
            </span>
          </div>

          {/* Capability chips */}
          <div className="flex flex-wrap gap-1">
            {agent.tools && agent.tools.length > 0 ? (
              agent.tools.slice(0, 3).map((tool) => (
                <span
                  key={tool}
                  className="inline-flex items-center gap-1 rounded bg-gray-900 border border-gray-800/80 px-1.5 py-0.5 text-[10px] text-gray-300 font-mono"
                >
                  <Wrench className="size-2.5 text-gray-500" />
                  {tool}
                </span>
              ))
            ) : (
              <span className="text-[11px] text-gray-500 italic">Conversational agent</span>
            )}
            {agent.tools && agent.tools.length > 3 && (
              <span className="rounded bg-gray-900/60 px-1.5 py-0.5 text-[10px] text-gray-500">
                +{agent.tools.length - 3} more
              </span>
            )}
          </div>
        </div>

        {/* Operational Shortcuts */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {shortcuts.map((sc) => (
            <Link
              key={sc.label}
              href={`${agentPath}?tab=${sc.subpath}`}
              className="rounded-md border border-gray-800 bg-gray-900/50 px-2 py-0.5 text-[10px] font-medium text-gray-400 transition-colors hover:border-gray-700 hover:text-white"
            >
              {sc.label}
            </Link>
          ))}
        </div>
      </div>

      {/* CTA Footer */}
      <div className="mt-4 border-t border-gray-900 pt-3">
        <Link href={cockpitHref} className="block w-full">
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-between rounded-xl border-gray-800 bg-gray-900/40 text-xs font-semibold text-gray-200 hover:border-gray-700 hover:bg-gray-800 hover:text-white"
          >
            <span>Open Cockpit</span>
            <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
          </Button>
        </Link>
      </div>
    </Card>
  );
}

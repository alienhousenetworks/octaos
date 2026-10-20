'use client';

import React from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  TrendingUp,
  Building2,
  Zap,
  Settings,
  Activity,
  DollarSign,
  Radar,
  Calendar,
  MessageSquare,
  FileText,
  Briefcase,
  Users,
  Target,
  ExternalLink,
  GitFork,
  ArrowRight,
} from 'lucide-react';
import { AgentItem } from '@/lib/agent-types';

interface AgentOperationsProps {
  agent: AgentItem;
}

interface OperationItem {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: any;
  badge?: string;
}

const DEPARTMENT_OPERATIONS: Record<string, OperationItem[]> = {
  sales: [
    {
      id: 'pipeline',
      title: 'Sales Lead Pipeline',
      description: 'Manage prospect stages, qualification scores, and pipeline flow in Table or Kanban mode.',
      href: '/app/sales',
      icon: TrendingUp,
      badge: 'Core CRM',
    },
    {
      id: 'prompt_sdr',
      title: 'Prompt-Driven SDR Prospector',
      description: 'Execute high-precision search directives, intent extraction, and automated lead enrichment.',
      href: '/app/sales/prompt-agent',
      icon: Zap,
      badge: 'Autonomous',
    },
    {
      id: 'deal_rooms',
      title: 'Enterprise Deal Rooms',
      description: 'Collaborative client closing spaces with automated deal summaries, documents, and stakeholders.',
      href: '/app/sales/deals',
      icon: Building2,
      badge: 'Closing',
    },
    {
      id: 'sales_config',
      title: 'Sales Engine Configuration',
      description: 'Configure target ICP, country exclusions, pricing parameters, and outreach sequencing rules.',
      href: '/app/sales/configuration',
      icon: Settings,
      badge: 'Governance',
    },
    {
      id: 'stepper',
      title: 'Sales Activity Stepper',
      description: 'Live procedural visualization of active prospecting steps, evidence harvesting, and syncs.',
      href: '/app/sales/activity',
      icon: Activity,
    },
    {
      id: 'source_intel',
      title: 'Lead Source Intelligence',
      description: 'Scored evidence sources, ROI attribution, and verification analytics across outbound channels.',
      href: '/app/sales/intelligence',
      icon: Radar,
    },
  ],
  marketing: [
    {
      id: 'campaigns',
      title: 'Multi-Channel Campaigns',
      description: 'Create, stage, and schedule viral social media campaigns across LinkedIn, X, and Instagram.',
      href: '/app/campaigns',
      icon: Calendar,
      badge: 'Operations',
    },
    {
      id: 'trend_radar',
      title: 'Autonomous Marketing Radar',
      description: 'Continuous market signal monitoring, competitor keyword analysis, and viral opportunity detection.',
      href: '/app/campaigns',
      icon: Radar,
      badge: 'Signals',
    },
    {
      id: 'content_knowledge',
      title: 'Brand Knowledge Retrieval',
      description: 'Align social copy with verified corporate documentation, guidelines, and tone-of-voice directives.',
      href: '/app/knowledge',
      icon: FileText,
    },
  ],
  support: [
    {
      id: 'tickets',
      title: 'Customer Ticket Inbox & Triage',
      description: 'Real-time client inquiries with automated technical triage, sentiment analysis, and SLA tracking.',
      href: '/app/support',
      icon: MessageSquare,
      badge: 'Helpdesk',
    },
    {
      id: 'knowledge_rag',
      title: 'Support Knowledge Base (RAG)',
      description: 'Verified enterprise troubleshooting documentation indexed for instant automated resolution.',
      href: '/app/knowledge',
      icon: FileText,
    },
  ],
  hr: [
    {
      id: 'recruiting',
      title: 'Candidate Screening Pipeline',
      description: 'Automated CV parsing, job requirement matching, applicant scorecards, and interview coordination.',
      href: '/app/hiring',
      icon: Briefcase,
      badge: 'Hiring',
    },
  ],
  finance: [
    {
      id: 'costs',
      title: 'AI Cost & Token Intelligence',
      description: 'Track model-level token usage, cache efficiency, blended inference expenses, and cost budgets.',
      href: '/app/costs',
      icon: DollarSign,
      badge: 'Financials',
    },
  ],
  executive: [
    {
      id: 'boardroom',
      title: 'Executive Boardroom',
      description: 'Multi-agent debate, cross-functional consensus building, and executive mandate synthesis.',
      href: '/app/boardroom',
      icon: Users,
      badge: 'Synthesis',
    },
    {
      id: 'ceo_workspace',
      title: 'CEO Strategic Workspace',
      description: 'Top-down strategic objective decomposition and delegation across Sales, Marketing, and Operations.',
      href: '/app/ceo',
      icon: Target,
    },
  ],
};

export default function AgentOperations({ agent }: AgentOperationsProps) {
  const deptKey = agent.department?.toLowerCase() || 'general';
  const operations = DEPARTMENT_OPERATIONS[deptKey] || [
    {
      id: 'automations',
      title: 'Automations & Workflows',
      description: 'Trigger autonomous Activepieces workflows, webhooks, and event-driven recipes with this agent.',
      href: '/app/automations',
      icon: GitFork,
      badge: 'Workflows',
    },
    {
      id: 'teams',
      title: 'Multi-Agent Teams',
      description: 'Collaborate with other enterprise agents inside team clusters for complex cross-agent tasks.',
      href: '/app/teams',
      icon: Users,
      badge: 'Teams',
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold text-white">Department Workspaces & Operations</h3>
        <p className="text-xs text-muted-foreground">
          Dedicated enterprise workspaces and operational interfaces governed by {agent.name}.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {operations.map((op) => {
          const Icon = op.icon;
          return (
            <Card
              key={op.id}
              className="group flex flex-col justify-between rounded-2xl border border-gray-800 bg-gray-950/50 p-5 transition-all duration-200 hover:border-gray-700 hover:bg-gray-900/40"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex size-9 items-center justify-center rounded-xl border border-gray-800 bg-gray-900 text-primary">
                    <Icon className="size-4" />
                  </div>
                  {op.badge && (
                    <span className="rounded-md border border-gray-700/60 bg-gray-900 px-2 py-0.5 text-[10px] font-semibold uppercase text-gray-300">
                      {op.badge}
                    </span>
                  )}
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-white group-hover:text-primary transition-colors">
                    {op.title}
                  </h4>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    {op.description}
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-900">
                <Link href={op.href} className="inline-flex w-full items-center justify-between text-xs font-semibold text-primary hover:underline">
                  <span>Open Operational Workspace</span>
                  <ExternalLink className="size-3.5" />
                </Link>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

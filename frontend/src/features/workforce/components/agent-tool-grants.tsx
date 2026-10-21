'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Wrench,
  Search,
  Mail,
  TrendingUp,
  MessageSquare,
  Shield,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Loader2,
} from 'lucide-react';
import { AgentItem, ToolGrant } from '@/lib/agent-types';
import { notify } from '@/lib/notify';

interface AgentToolGrantsProps {
  agent: AgentItem;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onAgentUpdated?: () => void;
}

const CATALOG_TOOLS: ToolGrant[] = [
  {
    id: 'web_search',
    label: 'Web Research & Signal Intelligence',
    description: 'Allows querying verified search engines and crawling public domains for prospecting intelligence.',
    risk: 'LOW',
    sideEffect: 'READ',
    approval: false,
  },
  {
    id: 'lead.create',
    label: 'Create CRM Leads',
    description: 'Registers newly qualified prospect accounts and contacts into the sales pipeline.',
    risk: 'MEDIUM',
    sideEffect: 'WRITE',
    approval: false,
  },
  {
    id: 'lead.update',
    label: 'Update CRM Records & Intent Scores',
    description: 'Updates lead metadata, ICP match ratings, and advances pipeline stages.',
    risk: 'MEDIUM',
    sideEffect: 'WRITE',
    approval: false,
  },
  {
    id: 'email.send',
    label: 'Outbound Email Dispatch',
    description: 'Dispatches personalized email sequences via approved organizational mailboxes.',
    risk: 'HIGH',
    sideEffect: 'WRITE',
    approval: true,
  },
  {
    id: 'ticket.reply',
    label: 'Customer Ticket Reply & Closure',
    description: 'Transmits verified support answers to client tickets and updates ticket status.',
    risk: 'MEDIUM',
    sideEffect: 'WRITE',
    approval: false,
  },
  {
    id: 'knowledge.search',
    label: 'Company Knowledge Base Retrieval (RAG)',
    description: 'Queries internal truth documents, brand guidelines, and product documentation.',
    risk: 'LOW',
    sideEffect: 'READ',
    approval: false,
  },
  {
    id: 'webhook_post',
    label: 'External Webhook Triggers',
    description: 'Dispatches HTTP webhooks to third-party endpoints or active automations.',
    risk: 'HIGH',
    sideEffect: 'WRITE',
    approval: true,
  },
];

export default function AgentToolGrants({
  agent,
  API_URL,
  fetchWithAuth,
  onAgentUpdated,
}: AgentToolGrantsProps) {
  const [grantedTools, setGrantedTools] = useState<string[]>(agent.tools || []);
  const [saving, setSaving] = useState(false);

  const toggleTool = (toolId: string) => {
    if (grantedTools.includes(toolId)) {
      setGrantedTools(grantedTools.filter((t) => t !== toolId));
    } else {
      setGrantedTools([...grantedTools, toolId]);
    }
  };

  const handleSaveGrants = async () => {
    setSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/agents/${agent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tools: grantedTools,
        }),
      });

      if (res.ok) {
        notify('Tool capabilities and permissions updated successfully.');
        onAgentUpdated?.();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to update tool permissions');
      }
    } catch (e: any) {
      notify(e.message || 'Network error updating permissions');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white">Tool Grants & Governance Policy</h3>
          <p className="text-xs text-muted-foreground">
            Configure authorized tool access, risk classifications, and human approval enforcement.
          </p>
        </div>

        <Button
          type="button"
          onClick={handleSaveGrants}
          disabled={saving}
          className="rounded-xl px-4 text-xs font-semibold"
        >
          {saving ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <Shield className="mr-2 size-3.5" />}
          Save Tool Policy
        </Button>
      </div>

      <div className="space-y-3">
        {CATALOG_TOOLS.map((tool) => {
          const isGranted = grantedTools.includes(tool.id);

          return (
            <Card
              key={tool.id}
              className={`flex flex-col gap-3 rounded-2xl border p-4 transition-all sm:flex-row sm:items-center sm:justify-between ${
                isGranted
                  ? 'border-gray-700 bg-gray-950/70 shadow-sm'
                  : 'border-gray-800/80 bg-gray-950/30 opacity-75'
              }`}
            >
              <div className="space-y-1 sm:max-w-xl">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-white">{tool.label}</h4>
                  <span className="font-mono text-[11px] text-gray-500">({tool.id})</span>

                  {/* Risk Tier Badge */}
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                      tool.risk === 'HIGH'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        : tool.risk === 'MEDIUM'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    }`}
                  >
                    {tool.risk} Risk
                  </span>

                  <span className="rounded bg-gray-900 border border-gray-800 px-1.5 py-0.5 text-[10px] font-mono text-gray-400">
                    {tool.sideEffect}
                  </span>
                </div>

                <p className="text-xs text-muted-foreground leading-relaxed">
                  {tool.description}
                </p>

                {tool.approval && (
                  <div className="flex items-center gap-1.5 pt-0.5 text-[11px] text-amber-400">
                    <Lock className="size-3" />
                    <span>Requires Human-in-the-Loop review before dispatch</span>
                  </div>
                )}
              </div>

              {/* Grant Toggle */}
              <button
                type="button"
                onClick={() => toggleTool(tool.id)}
                className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  isGranted ? 'bg-primary' : 'bg-gray-800'
                }`}
                role="switch"
                aria-checked={isGranted}
              >
                <span
                  className={`pointer-events-none inline-block size-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                    isGranted ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

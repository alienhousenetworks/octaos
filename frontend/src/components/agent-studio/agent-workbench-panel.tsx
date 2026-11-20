'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Wrench,
  Cpu,
  FileText,
  BookOpen,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  Clock,
  Sparkles,
  Layers,
  Download,
  X,
  Activity,
  Bot,
  Plug,
  Globe2,
  KeyRound,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';
import { AgentItem } from '@/lib/agent-types';
import { ToolExecutionItem } from './live-tool-pill';

export interface ArtifactItem {
  id: string;
  title: string;
  type: 'document' | 'table' | 'json' | 'image' | 'code' | 'post';
  content: any;
  createdAt: string;
}

export type WorkbenchTab = 'telemetry' | 'artifacts' | 'integrations' | 'context';

interface AgentWorkbenchPanelProps {
  open: boolean;
  onClose: () => void;
  activeTab: WorkbenchTab;
  onTabChange: (tab: WorkbenchTab) => void;
  agent: AgentItem | null;
  tools: ToolExecutionItem[];
  artifacts: ArtifactItem[];
  environment?: {
    model?: string;
    provider?: string;
    status?: string;
  };
}

const DEFAULT_INTEGRATIONS = [
  { name: 'Anthropic Claude 3.5', category: 'LLM Engine', status: 'connected', dot: 'bg-emerald-400' },
  { name: 'OpenAI GPT-4o', category: 'LLM Engine', status: 'connected', dot: 'bg-emerald-400' },
  { name: 'Meta / Instagram API', category: 'Marketing & Social', status: 'ready', dot: 'bg-sky-400' },
  { name: 'Buffer Social Scheduler', category: 'Marketing & Distribution', status: 'ready', dot: 'bg-sky-400' },
  { name: 'CRM & Lead Database', category: 'Sales Pipeline', status: 'connected', dot: 'bg-emerald-400' },
  { name: 'Model Context Protocol (MCP)', category: 'Tool Gateway', status: 'active', dot: 'bg-purple-400' },
  { name: 'ElevenLabs Voice Engine', category: 'Audio & Speech', status: 'optional', dot: 'bg-amber-400' },
];

export default function AgentWorkbenchPanel({
  open,
  onClose,
  activeTab,
  onTabChange,
  agent,
  tools,
  artifacts,
  environment,
}: AgentWorkbenchPanelProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  if (!open) return null;

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const downloadArtifact = (artifact: ArtifactItem) => {
    const raw = typeof artifact.content === 'string' ? artifact.content : JSON.stringify(artifact.content, null, 2);
    const blob = new Blob([raw], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.title.toLowerCase().replace(/[^a-z0-9]/g, '_')}.${artifact.type === 'json' ? 'json' : 'txt'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <aside
      aria-label="Agent Workbench and Telemetry"
      className="flex h-full w-[380px] max-w-[90vw] shrink-0 flex-col border-l border-white/[0.08] bg-[#0d1116] text-white/90 select-none animate-in slide-in-from-right duration-200"
    >
      {/* Workbench Header */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-white/[0.08] px-4 bg-[#11161c]">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-[#e5a93c]/15 text-[#2dd4bf]">
            <Cpu className="size-4" />
          </div>
          <div>
            <h2 className="text-xs font-semibold tracking-wide uppercase text-white/80">Agent Workbench</h2>
            <p className="text-[10px] text-white/45">
              {environment?.model || agent?.model || 'Claude 3.5 Sonnet'} · Sandboxed
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close Workbench"
          className="rounded-lg p-1 text-white/40 hover:bg-white/[0.06] hover:text-white transition"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* Tabs Switcher: 4 Tabs (Telemetry, Artifacts, Integrations, Context) */}
      <div className="grid grid-cols-4 border-b border-white/[0.08] bg-[#0f1318] p-1 text-xs">
        <button
          type="button"
          onClick={() => onTabChange('telemetry')}
          className={`flex items-center justify-center gap-1 rounded-md py-1.5 font-medium transition ${
            activeTab === 'telemetry'
              ? 'bg-white/[0.1] text-[#2dd4bf] shadow-sm'
              : 'text-white/50 hover:bg-white/[0.04] hover:text-white'
          }`}
          title="Live Tool Execution Telemetry"
        >
          <Activity className="size-3" />
          <span className="text-[11px]">Telemetry</span>
        </button>

        <button
          type="button"
          onClick={() => onTabChange('artifacts')}
          className={`flex items-center justify-center gap-1 rounded-md py-1.5 font-medium transition ${
            activeTab === 'artifacts'
              ? 'bg-white/[0.1] text-[#2dd4bf] shadow-sm'
              : 'text-white/50 hover:bg-white/[0.04] hover:text-white'
          }`}
          title="Generated Files & Artifacts"
        >
          <Layers className="size-3" />
          <span className="text-[11px]">Artifacts</span>
          {artifacts.length > 0 && (
            <span className="rounded-full bg-[#e5a93c]/20 px-1 text-[9px] text-[#2dd4bf]">
              {artifacts.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => onTabChange('integrations')}
          className={`flex items-center justify-center gap-1 rounded-md py-1.5 font-medium transition ${
            activeTab === 'integrations'
              ? 'bg-white/[0.1] text-[#2dd4bf] shadow-sm'
              : 'text-white/50 hover:bg-white/[0.04] hover:text-white'
          }`}
          title="Connected Integrations & Models"
        >
          <Plug className="size-3" />
          <span className="text-[11px]">Integrations</span>
        </button>

        <button
          type="button"
          onClick={() => onTabChange('context')}
          className={`flex items-center justify-center gap-1 rounded-md py-1.5 font-medium transition ${
            activeTab === 'context'
              ? 'bg-white/[0.1] text-[#2dd4bf] shadow-sm'
              : 'text-white/50 hover:bg-white/[0.04] hover:text-white'
          }`}
          title="Agent Specs and System Prompt"
        >
          <BookOpen className="size-3" />
          <span className="text-[11px]">Context</span>
        </button>
      </div>

      {/* Tab Contents */}
      <div className="min-h-0 flex-1 overflow-y-auto p-3.5 select-text">
        {/* TELEMETRY & TOOLS TAB */}
        {activeTab === 'telemetry' && (
          <div className="space-y-3.5">
            {/* Environment Status Card */}
            <div className="rounded-xl border border-white/[0.08] bg-[#171e26] p-3 text-xs">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-white/45">
                  Sandbox State
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#e5a93c]/15 px-2 py-0.5 text-[10px] font-medium text-[#2dd4bf]">
                  <span className="size-1.5 rounded-full bg-[#e5a93c] animate-pulse" />
                  Online
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="block text-white/40">Model</span>
                  <span className="font-mono text-white/80">{environment?.model || agent?.model || 'claude-3-5-sonnet'}</span>
                </div>
                <div>
                  <span className="block text-white/40">Provider</span>
                  <span className="text-white/80">{environment?.provider || agent?.provider || 'Anthropic / In-House'}</span>
                </div>
                <div>
                  <span className="block text-white/40">Tool Calls</span>
                  <span className="font-mono text-white/80">{tools.length} executed</span>
                </div>
                <div>
                  <span className="block text-white/40">Stream Protocol</span>
                  <span className="font-mono text-white/80">SSE / v1.2</span>
                </div>
              </div>
            </div>

            {/* Tool Executions Stream */}
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-white/45">
                  Live Tool Execution Stream
                </span>
                <span className="text-[10px] text-white/40 font-mono">
                  {tools.filter((t) => t.status === 'completed').length} / {tools.length} succeeded
                </span>
              </div>

              {tools.length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 p-6 text-center text-xs text-white/40">
                  <Wrench className="mx-auto mb-2 size-5 text-white/20" />
                  <p>No tools executed yet.</p>
                  <p className="mt-1 text-[11px] text-white/30">
                    When the agent invokes web scrapers, database lookups, or APIs, they stream here live.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {tools.map((t, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-white/[0.08] bg-[#171e26] p-2.5 text-xs font-mono"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <Wrench className="size-3 text-[#2dd4bf]" />
                          <span className="font-semibold text-white/90">{t.tool}</span>
                        </div>
                        <span
                          className={`rounded px-1.5 py-0.2 text-[9px] uppercase font-bold ${
                            t.status === 'completed'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : t.status === 'running'
                              ? 'bg-sky-500/20 text-sky-300 animate-pulse'
                              : 'bg-rose-500/20 text-rose-300'
                          }`}
                        >
                          {t.status}
                        </span>
                      </div>
                      {t.args && Object.keys(t.args).length > 0 && (
                        <div className="mt-1.5 rounded bg-black/40 p-1.5 text-[10px] text-white/60 overflow-x-auto whitespace-pre-wrap max-h-24">
                          {JSON.stringify(t.args, null, 2)}
                        </div>
                      )}
                      {t.error && (
                        <div className="mt-1 text-[10px] text-rose-400">
                          Error: {t.error}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ARTIFACTS TAB */}
        {activeTab === 'artifacts' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-white/45">
                Session Artifacts ({artifacts.length})
              </span>
            </div>

            {artifacts.length === 0 ? (
              <div className="rounded-xl border border-dashed border-white/10 p-6 text-center text-xs text-white/40">
                <FileText className="mx-auto mb-2 size-5 text-white/20" />
                <p>No artifacts generated in this session.</p>
                <p className="mt-1 text-[11px] text-white/30">
                  Documents, extracted spreadsheets, generated leads, and drafts will appear here.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {artifacts.map((art) => {
                  const contentStr =
                    typeof art.content === 'string'
                      ? art.content
                      : JSON.stringify(art.content, null, 2);
                  return (
                    <div
                      key={art.id}
                      className="rounded-xl border border-white/[0.08] bg-[#171e26] p-3 transition hover:border-[#2dd4bf]/30"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <FileText className="size-4 text-[#2dd4bf]" />
                          <div>
                            <h4 className="text-xs font-medium text-white/90">{art.title}</h4>
                            <p className="text-[10px] text-white/40">
                              {art.type.toUpperCase()} · {new Date(art.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => copyToClipboard(contentStr, art.id)}
                            title="Copy contents"
                            className="rounded p-1 text-white/40 hover:bg-white/[0.08] hover:text-white"
                          >
                            {copiedId === art.id ? <Check className="size-3.5 text-[#2dd4bf]" /> : <Copy className="size-3.5" />}
                          </button>
                          <button
                            type="button"
                            onClick={() => downloadArtifact(art)}
                            title="Download artifact"
                            className="rounded p-1 text-white/40 hover:bg-white/[0.08] hover:text-white"
                          >
                            <Download className="size-3.5" />
                          </button>
                        </div>
                      </div>

                      <div className="mt-2 max-h-36 overflow-y-auto rounded-lg bg-black/50 p-2 font-mono text-[10px] text-white/70 whitespace-pre-wrap">
                        {contentStr.slice(0, 500)}
                        {contentStr.length > 500 ? '...' : ''}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* INTEGRATIONS TAB */}
        {activeTab === 'integrations' && (
          <div className="space-y-3.5">
            <div className="flex items-center justify-between pb-1 border-b border-white/[0.06]">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-white/45">
                Connected Integrations & Models
              </span>
              <span className="rounded bg-[#e5a93c]/15 px-2 py-0.5 text-[10px] font-mono text-[#2dd4bf]">
                Active
              </span>
            </div>

            <p className="text-[11px] text-white/55 leading-relaxed">
              These external AI models, database connectors, and tool providers are attached to your current workspace session.
            </p>

            <div className="space-y-2">
              {DEFAULT_INTEGRATIONS.map((integ) => (
                <div
                  key={integ.name}
                  className="flex items-center justify-between rounded-xl border border-white/[0.08] bg-[#171e26] p-2.5 text-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className={`size-2 rounded-full shrink-0 ${integ.dot}`} />
                    <div className="min-w-0">
                      <p className="font-medium text-white/90 truncate text-[11px]">{integ.name}</p>
                      <p className="text-[10px] text-white/40 truncate">{integ.category}</p>
                    </div>
                  </div>
                  <span className="rounded bg-white/[0.05] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-white/60 shrink-0">
                    {integ.status}
                  </span>
                </div>
              ))}
            </div>

            {/* Direct Link to Configure All Integrations */}
            <div className="pt-2">
              <Link
                href="/app/settings/integrations"
                className="flex h-9 w-full items-center justify-center gap-1.5 rounded-xl border border-[#e5a93c]/30 bg-[#e5a93c]/10 text-xs font-medium text-[#2dd4bf] transition hover:bg-[#e5a93c]/20 hover:text-white"
              >
                <KeyRound className="size-3.5" />
                <span>Manage API Keys & Connectors</span>
                <ArrowRight className="size-3" />
              </Link>
            </div>
          </div>
        )}

        {/* CONTEXT & KNOWLEDGE TAB */}
        {activeTab === 'context' && (
          <div className="space-y-3.5">
            <div className="rounded-xl border border-white/[0.08] bg-[#171e26] p-3 text-xs">
              <div className="flex items-center gap-2 pb-2 mb-2 border-b border-white/[0.06]">
                <Bot className="size-4 text-[#2dd4bf]" />
                <span className="font-semibold text-white/90">
                  {agent?.name || 'OctaOS Specialist'}
                </span>
                <span className="ml-auto rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-white/50">
                  {agent?.department || 'Executive'}
                </span>
              </div>
              <p className="text-[11px] leading-relaxed text-white/60">
                {agent?.description || agent?.role || 'Autonomous specialist configured for end-to-end task execution.'}
              </p>
            </div>

            {agent?.system_prompt && (
              <div>
                <span className="block mb-1 text-[11px] font-semibold uppercase tracking-wider text-white/45">
                  System Instructions
                </span>
                <div className="rounded-xl border border-white/[0.08] bg-[#171e26] p-3 font-mono text-[10px] leading-relaxed text-white/60 max-h-48 overflow-y-auto whitespace-pre-wrap">
                  {agent.system_prompt}
                </div>
              </div>
            )}

            <div>
              <span className="block mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/45">
                Authorized Capabilities & Tools
              </span>
              <div className="flex flex-wrap gap-1.5">
                {(agent?.tools && agent.tools.length > 0
                  ? agent.tools
                  : ['web_search', 'knowledge_lookup', 'crm_query', 'campaign_generator', 'approval_broker']
                ).map((toolName: string) => (
                  <span
                    key={toolName}
                    className="inline-flex items-center gap-1 rounded-md border border-white/[0.08] bg-white/[0.03] px-2 py-1 font-mono text-[10px] text-white/70"
                  >
                    <ShieldCheck className="size-2.5 text-[#2dd4bf]" />
                    {toolName}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <span className="block mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/45">
                Company Knowledge Context
              </span>
              <div className="rounded-xl border border-white/[0.08] bg-[#171e26] p-3 text-xs">
                <div className="flex items-center gap-2 text-white/80">
                  <BookOpen className="size-3.5 text-[#2dd4bf]" />
                  <span className="font-medium text-[11px]">Connected Vector Library</span>
                </div>
                <p className="mt-1 text-[10px] text-white/45">
                  Access to tenant policies, brand books, past campaigns, and CRM documents is active.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

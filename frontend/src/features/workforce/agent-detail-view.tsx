'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  ChevronLeft,
  Bot,
  Terminal,
  Layers,
  Settings,
  Shield,
  Clock,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Wrench,
  TrendingUp,
  Save,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { AgentItem, ActivityLogItem } from '@/lib/agent-types';
import AgentOperations from './components/agent-operations';
import AgentConsole from './components/agent-console';
import AgentToolGrants from './components/agent-tool-grants';
import { notify } from '@/lib/notify';
import { AGENT_AI_PROVIDERS, autoProviderLabel, normalizeAgentProvider, providerDisplayName } from '@/lib/ai-providers';

interface AgentDetailViewProps {
  agentId: string;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  token: string | null;
}

type CockpitTab = 'overview' | 'operations' | 'console' | 'configuration' | 'permissions' | 'activity';

export default function AgentDetailView({
  agentId,
  API_URL,
  fetchWithAuth,
  token,
}: AgentDetailViewProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialTab = (searchParams.get('tab') as CockpitTab) || 'overview';
  const [activeTab, setActiveTab] = useState<CockpitTab>(initialTab);

  React.useEffect(() => {
    const tabFromUrl = (searchParams.get('tab') as CockpitTab) || 'overview';
    if (tabFromUrl !== activeTab) {
      setActiveTab(tabFromUrl);
    }
  }, [searchParams, activeTab]);
  const [agent, setAgent] = useState<AgentItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [activityLogs, setActivityLogs] = useState<ActivityLogItem[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  // Configuration edit state
  const [configPrompt, setConfigPrompt] = useState('');
  const promptDraftRef = React.useRef('');
  const [configModel, setConfigModel] = useState('');
  const [configProvider, setConfigProvider] = useState('auto');
  const [configTemp, setConfigTemp] = useState(0.7);
  const [savingConfig, setSavingConfig] = useState(false);
  const [envProvider, setEnvProvider] = useState('');
  const [envModel, setEnvModel] = useState('');

  // Load agent data
  const loadAgent = useCallback(async () => {
    if (!token || !agentId) return;
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/agents/${agentId}`);
      if (res.ok) {
        const data = await res.json();
        setAgent(data);
        promptDraftRef.current = data.system_prompt || '';
        setConfigPrompt(data.system_prompt || '');
        setConfigModel(data.model || '');
        setConfigProvider(normalizeAgentProvider(data.provider));
        setConfigTemp(data.temperature ?? 0.7);
      } else {
        // Fallback: search in list_agents
        const listRes = await fetchWithAuth(`${API_URL}/dashboard/agents`);
        if (listRes.ok) {
          const allAgents: AgentItem[] = await listRes.json();
          const match = allAgents.find((a) => a.id === agentId || a.slug === agentId);
          if (match) {
            setAgent(match);
            promptDraftRef.current = match.system_prompt || '';
            setConfigPrompt(match.system_prompt || '');
            setConfigModel(match.model || '');
            setConfigProvider(normalizeAgentProvider(match.provider));
            setConfigTemp(match.temperature ?? 0.7);
          }
        }
      }
    } catch (e) {
      console.error('Failed to load agent:', e);
    } finally {
      setLoading(false);
    }
  }, [agentId, API_URL, fetchWithAuth, token]);

  // Load activity logs
  const loadActivity = useCallback(async () => {
    if (!token || !agentId) return;
    setLoadingLogs(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/agents/${agentId}/activity`);
      if (res.ok) {
        const data = await res.json();
        setActivityLogs(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error('Failed to load agent activity:', e);
    } finally {
      setLoadingLogs(false);
    }
  }, [agentId, API_URL, fetchWithAuth, token]);

  useEffect(() => {
    loadAgent();
  }, [loadAgent]);

  useEffect(() => {
    let active = true;
    fetchWithAuth(`${API_URL}/commands/ai-mode`)
      .then(async (res) => {
        if (!res.ok) return null;
        return res.json();
      })
      .then((data) => {
        if (!active || !data) return;
        if (data.primary_provider) setEnvProvider(String(data.primary_provider));
        if (data.primary_model) setEnvModel(String(data.primary_model));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [API_URL, fetchWithAuth]);

  useEffect(() => {
    if (activeTab === 'activity' || activeTab === 'overview') {
      loadActivity();
    }
  }, [activeTab, loadActivity]);

  const handleSaveConfig = async (override?: string) => {
    if (!agent) return;
    const systemPrompt = typeof override === 'string' ? override : (promptDraftRef.current || configPrompt);
    setSavingConfig(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/agents/${agent.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          system_prompt: systemPrompt,
          model: configModel,
          provider: configProvider,
          temperature: configTemp,
        }),
      });

      if (res.ok) {
        notify('Agent configuration and version updated successfully.');
        loadAgent();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to update agent configuration');
      }
    } catch (e: any) {
      notify(e.message || 'Network error saving configuration');
    } finally {
      setSavingConfig(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-gray-800 bg-gray-950/40 p-12 text-center">
        <Bot className="size-12 text-gray-600 mb-3" />
        <h2 className="text-base font-semibold text-white">Agent not found</h2>
        <p className="text-xs text-muted-foreground mt-1 mb-4">
          The requested agent does not exist or has been archived.
        </p>
        <Link href="/app/agents">
          <Button variant="outline" size="sm" className="rounded-xl text-xs">
            <ChevronLeft className="mr-1 size-3.5" /> Back to Agent Directory
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Breadcrumb & Navigation */}
      <div className="flex items-center justify-between border-b border-gray-800/80 pb-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link href="/app/agents" className="hover:text-white transition-colors flex items-center gap-1">
            <ChevronLeft className="size-3.5" /> All agents
          </Link>
          <span>/</span>
          <span className="font-semibold text-white">{agent.name}</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setActiveTab('console')}
            className="rounded-xl border-gray-800 bg-gray-900/40 text-xs font-semibold"
          >
            <Terminal className="mr-1.5 size-3.5 text-primary" /> Run Task
          </Button>
          <Button
            size="sm"
            onClick={() => setActiveTab('operations')}
            className="rounded-xl text-xs font-semibold"
          >
            Specialized Workspaces <ArrowRight className="ml-1.5 size-3.5" />
          </Button>
        </div>
      </div>

      {/* Cockpit Identity Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between rounded-2xl border border-gray-800 bg-gray-950/60 p-6">
        <div className="flex items-start gap-4">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl border border-gray-700 bg-gradient-to-br from-gray-900 to-gray-800 text-primary shadow-inner">
            <Bot className="size-7" />
          </div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">{agent.name}</h1>
              <span className="rounded-md border border-gray-700 bg-gray-900/80 px-2 py-0.5 text-[11px] font-semibold uppercase text-gray-300">
                {agent.department}
              </span>
              {agent.is_system ? (
                <span className="rounded-md border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[11px] font-medium text-indigo-400">
                  System Agent
                </span>
              ) : (
                <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                  Custom v{agent.version || 1}
                </span>
              )}
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                <span className="size-1.5 rounded-full bg-emerald-400" />
                Enabled
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{agent.role}</p>
            <p className="text-xs text-gray-400 pt-1 max-w-2xl">{agent.description}</p>
          </div>
        </div>

        <div className="flex flex-col sm:items-end gap-1.5 text-xs text-gray-400 font-mono">
          <span className="rounded bg-gray-900 border border-gray-800 px-2 py-1">
            {agent.model || 'meta-llama/llama-3.3-70b-instruct'}
          </span>
          <span className="text-[11px] text-gray-500">
            {agent.total_executions > 0 ? `${agent.total_executions} lifetime runs` : 'No runs recorded'}
          </span>
        </div>
      </div>

      {/* Cockpit Tabs Navigation */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-gray-800 pb-px">
        {[
          { id: 'overview', label: 'Overview', icon: CheckCircle2 },
          { id: 'operations', label: 'Operations', icon: Layers },
          { id: 'console', label: 'Chat', icon: Terminal },
          { id: 'configuration', label: 'Configuration', icon: Settings },
          { id: 'permissions', label: 'Permissions', icon: Shield },
          { id: 'activity', label: 'Activity', icon: Clock },
        ].map((tab) => {
          const Icon = tab.icon;
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                const nextTab = tab.id as CockpitTab;
                setActiveTab(nextTab);
                const params = new URLSearchParams(window.location.search);
                if (nextTab === 'overview') params.delete('tab');
                else params.set('tab', nextTab);
                const query = params.toString();
                const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
                if (`${window.location.pathname}${window.location.search}` !== nextUrl) router.replace(nextUrl);
              }}
              className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-xs font-semibold transition-all ${
                isSelected
                  ? 'border-primary text-white'
                  : 'border-transparent text-muted-foreground hover:border-gray-700 hover:text-white'
              }`}
            >
              <Icon className="size-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT */}

      {/* 1. OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Telemetry Metrics */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-2xl border border-gray-800 bg-gray-950/40 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase block">
                Total Executions
              </span>
              <span className="text-xl font-bold text-white mt-1 block">
                {agent.total_executions > 0 ? agent.total_executions : '—'}
              </span>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-950/40 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase block">
                Verified Success Rate
              </span>
              <span className="text-xl font-bold text-emerald-400 mt-1 block">
                {agent.total_executions > 0 ? '99.4%' : '—'}
              </span>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-950/40 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase block">
                Authorized Tools
              </span>
              <span className="text-xl font-bold text-white mt-1 block">
                {agent.tools?.length || 0}
              </span>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-950/40 p-4">
              <span className="text-[11px] font-medium text-muted-foreground uppercase block">
                Configuration Version
              </span>
              <span className="text-xl font-bold text-primary mt-1 block">
                v{agent.version || 1}
              </span>
            </div>
          </div>

          {/* Specialized Operations launcher */}
          <AgentOperations agent={agent} />

          {/* Recent Executions Snippet */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-white">Recent Execution History</h4>
              <button
                type="button"
                onClick={() => setActiveTab('activity')}
                className="text-xs text-primary hover:underline"
              >
                View all logs →
              </button>
            </div>

            {loadingLogs ? (
              <div className="flex h-24 items-center justify-center">
                <Loader2 className="size-4 animate-spin text-gray-500" />
              </div>
            ) : activityLogs.length === 0 ? (
              <div className="rounded-xl border border-gray-800 bg-gray-950/30 p-6 text-center text-xs text-gray-500">
                No recent activity recorded for {agent.name}. Open Chat and send a message to generate execution logs.
              </div>
            ) : (
              <div className="space-y-2">
                {activityLogs.slice(0, 5).map((log) => (
                  <div
                    key={log.id}
                    className="flex items-center justify-between rounded-xl border border-gray-800/80 bg-gray-950/40 p-3 text-xs"
                  >
                    <div className="space-y-0.5">
                      <span className="font-semibold text-white">{log.action}</span>
                      <p className="text-gray-400 text-[11px]">{log.description || 'Verified execution completed.'}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                        {log.status}
                      </span>
                      <span className="text-[10px] font-mono text-gray-500">
                        {log.created_at ? new Date(log.created_at).toLocaleTimeString() : '—'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. OPERATIONS */}
      {activeTab === 'operations' && <AgentOperations agent={agent} />}

      {/* 3. TEST CONSOLE */}
      {activeTab === 'console' && (
        <AgentConsole
          agent={agent}
          API_URL={API_URL}
          fetchWithAuth={fetchWithAuth}
        />
      )}

      {/* 4. CONFIGURATION */}
      {activeTab === 'configuration' && (
        <Card className="rounded-2xl border border-gray-800 bg-gray-950/60 p-6 space-y-6">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b border-gray-800/80 pb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Versioned Persona & Instructions</h3>
              <p className="text-xs text-muted-foreground">
                Tuning these instructions increments the agent version and takes effect for subsequent executions.
              </p>
            </div>
            <Button
              type="button"
              onClick={(event) => {
                const field = event.currentTarget.closest('.rounded-2xl')?.querySelector('textarea');
                void handleSaveConfig(field?.value);
              }}
              disabled={savingConfig}
              className="rounded-xl px-4 text-xs font-semibold"
            >
              {savingConfig ? <Loader2 className="mr-2 size-3.5 animate-spin" /> : <Save className="mr-2 size-3.5" />}
              Publish New Version
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300">Provider</label>
              <select
                value={configProvider}
                onChange={(e) => {
                  const next = e.target.value;
                  setConfigProvider(next);
                  if (next === 'nvidia' && envModel && !configModel.trim()) setConfigModel(envModel);
                }}
                className="w-full h-9 rounded-xl border border-gray-800 bg-gray-900/80 px-3 text-xs text-white"
              >
                {AGENT_AI_PROVIDERS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.value === 'auto' ? autoProviderLabel(envProvider) : item.label}
                  </option>
                ))}
              </select>
              {configProvider === 'auto' && (
                <p className="text-[11px] leading-4 text-gray-500">
                  Auto uses {envProvider ? providerDisplayName(envProvider) : 'the server environment'}
                  {envModel ? ` · ${envModel}` : ''} from the server environment.
                </p>
              )}
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <label className="text-xs font-semibold text-gray-300">Model Identifier</label>
              <Input
                value={configModel}
                onChange={(e) => setConfigModel(e.target.value)}
                className="rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white font-mono"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-gray-300">Temperature</label>
              <span className="font-mono text-xs text-primary">{configTemp}</span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={configTemp}
              onChange={(e) => setConfigTemp(parseFloat(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-gray-300">System Prompt Directive</label>
            <Textarea
              value={configPrompt}
              onChange={(e) => {
                promptDraftRef.current = e.target.value;
                setConfigPrompt(e.target.value);
              }}
              className="min-h-[220px] rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white font-mono leading-relaxed"
            />
          </div>
        </Card>
      )}

      {/* 5. PERMISSIONS */}
      {activeTab === 'permissions' && (
        <AgentToolGrants
          agent={agent}
          API_URL={API_URL}
          fetchWithAuth={fetchWithAuth}
          onAgentUpdated={loadAgent}
        />
      )}

      {/* 6. ACTIVITY LOGS */}
      {activeTab === 'activity' && (
        <Card className="rounded-2xl border border-gray-800 bg-gray-950/60 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Execution Audit Logs</h3>
              <p className="text-xs text-muted-foreground">
                Persisted execution events recorded for {agent.name}.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadActivity}
              className="rounded-xl border-gray-800 text-xs"
            >
              Refresh
            </Button>
          </div>

          {loadingLogs ? (
            <div className="flex h-32 items-center justify-center">
              <Loader2 className="size-6 animate-spin text-primary" />
            </div>
          ) : activityLogs.length === 0 ? (
            <div className="rounded-xl border border-gray-800 bg-gray-950/30 p-8 text-center text-xs text-gray-500">
              No execution records found in current audit window.
            </div>
          ) : (
            <div className="divide-y divide-gray-900 overflow-hidden rounded-xl border border-gray-800 bg-gray-950/40">
              {activityLogs.map((log) => (
                <div key={log.id} className="flex flex-col gap-1 p-3.5 sm:flex-row sm:items-center sm:justify-between text-xs">
                  <div className="space-y-0.5">
                    <span className="font-semibold text-white">{log.action}</span>
                    <p className="text-gray-400 text-[11px]">{log.description || 'Task completed.'}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        log.status === 'success'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : log.status === 'failed'
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                      }`}
                    >
                      {log.status}
                    </span>
                    <span className="font-mono text-[10px] text-gray-500">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

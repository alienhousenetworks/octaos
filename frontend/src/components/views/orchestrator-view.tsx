'use client';

import { notify } from '@/lib/notify';
import { createId } from '@/lib/id';
import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Bot,
  Loader2,
  Send,
  Cpu,
  Zap,
  Activity,
  Trash2,
  Sparkles,
  Check,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  BarChart3,
  TrendingUp,
  Layers,
  CheckCircle2,
  PanelRightClose,
  PanelRightOpen,
  Paperclip,
  FolderOpen,
  X,
  FileText,
} from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import PageHeader from '@/components/shell/page-header';
import OrchestratorCharts from './orchestrator-charts';

interface OrchestratorViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  apps: any[];
  configuredProviders: string[];
  timeline: any[];
  queue: { posts: any[]; leads: any[] };
  handleApprovePost: (postId: string) => Promise<void>;
  handleRejectPost: (postId: string) => Promise<void>;
}

export default function OrchestratorView({
  API_URL,
  fetchWithAuth,
  fetchData,
  apps,
  configuredProviders,
  timeline,
  queue,
  handleApprovePost,
  handleRejectPost,
}: OrchestratorViewProps) {
  const [orchMessages, setOrchMessages] = useState<any[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Welcome to the Orchestrator AI Console. I coordinate your Marketing, Sales, Support, and Operations teams to accomplish complex business goals.\n\nTell me what you'd like to achieve, or select a suggested prompt below.",
    },
  ]);
  const [orchInput, setOrchInput] = useState('');
  const [analysisFiles, setAnalysisFiles] = useState<File[]>([]);
  const [analyzingFiles, setAnalyzingFiles] = useState(false);
  const [fileInputError, setFileInputError] = useState('');
  const filePickerRef = useRef<HTMLInputElement>(null);
  const folderPickerRef = useRef<HTMLInputElement>(null);
  const [prompt, setPrompt] = useState(''); // backwards compatibility
  const [orchInlineKeyValue, setOrchInlineKeyValue] = useState('');
  const [orchModel, setOrchModel] = useState('');
  const [orchProvider, setOrchProvider] = useState('auto');
  const [loading, setLoading] = useState(false);
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({});
  const [approvingActionId, setApprovingActionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('orchestrator_sidebar_open');
      if (stored !== null) return stored === '1';
    }
    return true;
  });
  const [activityFeedCollapsed, setActivityFeedCollapsed] = useState(false);
  const [approvalsCollapsed, setApprovalsCollapsed] = useState(false);

  const orchChatEndRef = useRef<HTMLDivElement>(null);

  const toggleSidebar = React.useCallback(() => {
    setSidebarOpen((prev) => {
      const next = !prev;
      if (typeof window !== 'undefined') {
        localStorage.setItem('orchestrator_sidebar_open', next ? '1' : '0');
      }
      return next;
    });
  }, []);

  // Orchestrator chat: load from localStorage on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const saved = localStorage.getItem('orchestrator_chat_messages');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          queueMicrotask(() => setOrchMessages(parsed));
        }
      } catch {
        // ignore parse errors
      }
    }
  }, []);

  // Persist orchestrator chat to localStorage
  useEffect(() => {
    if (orchMessages.length > 0) {
      localStorage.setItem('orchestrator_chat_messages', JSON.stringify(orchMessages));
    }
  }, [orchMessages]);

  // Auto-scroll orchestrator chat to bottom
  useEffect(() => {
    orchChatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [orchMessages]);

  const handleAnalyzeFiles = React.useCallback(async () => {
    if (!analysisFiles.length || analyzingFiles) return;
    setAnalyzingFiles(true);
    setFileInputError('');
    const uploaded = [...analysisFiles];
    setOrchMessages(prev => [...prev, { id: `user-files-${Date.now()}`, role: 'user', content: `Analyze ${uploaded.length} uploaded file(s): ${uploaded.map(f => f.name).join(', ')}`, timestamp: new Date().toISOString() }]);
    try {
      const body = new FormData();
      body.append('title', `Orchestrator data analysis — ${new Date().toLocaleDateString()}`);
      body.append('idempotency_key', createId());
      uploaded.forEach(file => body.append('files', file, (file as File & {webkitRelativePath?: string}).webkitRelativePath || file.name));
      const response = await fetchWithAuth(`${API_URL}/data-intelligence/runs`, { method: 'POST', body });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : `File analysis failed (HTTP ${response.status}).`);
      const run = result.run || {};
      const reportResponse = await fetchWithAuth(`${API_URL}/data-intelligence/runs/${encodeURIComponent(run.id)}`);
      const detail = reportResponse.ok ? await reportResponse.json() : {};
      const findings = Array.isArray(detail.findings) ? detail.findings : [];
      const reportText = [
        `Data analysis ${run.status || 'created'}.`,
        `Run ID: ${run.id || 'unavailable'}`,
        `Files received: ${run.file_count ?? uploaded.length}; extracted: ${detail.profile?.files_parsed ?? 0}; findings: ${findings.length}.`,
        '',
        ...findings.slice(0, 12).map((finding: any, i: number) => `${i + 1}. [${String(finding.severity || 'info').toUpperCase()}] ${finding.title}\nObserved: ${finding.observation}\nWhy it matters: ${finding.why_it_matters}\nRecommended action: ${finding.recommended_action}`),
        '',
        'These are deterministic extraction and profiling findings, not causal business claims. Review extraction coverage and evidence before acting.',
      ].join('\n');
      setOrchMessages(prev => [...prev, { id: `assistant-files-${Date.now()}`, role: 'assistant', content: reportText, mode: 'data_intelligence', dataAnalysis: { runId: run.id, status: run.status, findings, coverage: detail.report?.coverage }, timestamp: new Date().toISOString() }]);
      setAnalysisFiles([]);
      if (filePickerRef.current) filePickerRef.current.value = '';
      if (folderPickerRef.current) folderPickerRef.current.value = '';
      notify('File analysis report created');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'File analysis failed.';
      setFileInputError(message);
      setOrchMessages(prev => [...prev, { id: `assistant-files-error-${Date.now()}`, role: 'assistant', content: `I could not analyze the uploaded files. ${message}`, timestamp: new Date().toISOString() }]);
    } finally { setAnalyzingFiles(false); }
  }, [analysisFiles, analyzingFiles, API_URL, fetchWithAuth]);

  const handleRunCommand = React.useCallback(async (override?: string) => {
    const typed = typeof override === 'string' ? override : orchInput;
    const inputText = typed.trim() || prompt.trim();
    if (!inputText) return;

    const timestamp = new Date().toISOString();
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: inputText,
      timestamp,
    };
    setOrchMessages((prev) => [...prev, userMsg]);
    setOrchInput('');
    setPrompt('');
    setLoading(true);

    try {
      // Build previous conversation turns for multi-turn context (exclude welcome greeting)
      const historyToSend = orchMessages
        .filter((m: any) => m.id !== 'welcome' && typeof m.content === 'string' && m.content.trim())
        .slice(-10)
        .map((m: any) => ({
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.content.trim(),
        }));

      const payload: any = { prompt: inputText };
      if (historyToSend.length > 0) payload.messages = historyToSend;
      if (orchProvider && orchProvider !== 'auto') payload.provider = orchProvider;
      if (orchModel && orchModel.trim()) payload.model = orchModel;

      const res = await fetchWithAuth(`${API_URL}/commands/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof data?.detail === 'string'
          ? data.detail
          : `The request failed (${res.status}). No result was produced.`;
        setOrchMessages((prev) => [...prev, {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: detail,
          timestamp: new Date().toISOString(),
        }]);
        return;
      }

      const answer =
        data.results?.map((r: any) => r.message || r.status).filter(Boolean).join('\n') ||
        data.briefing?.briefing_text ||
        data.plan?.message ||
        '';
      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: answer || 'The model returned no text for that request.',
        plan: data.plan,
        results: data.results,
        briefing: data.briefing,
        mode: data.mode,
        timestamp: new Date().toISOString(),
      };
      setOrchMessages((prev) => [...prev, assistantMsg]);

      if (res.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
      const errorMsg = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setOrchMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }, [orchInput, prompt, orchProvider, orchModel, orchMessages, fetchWithAuth, API_URL, fetchData]);

  const handleExecuteApprovedAction = React.useCallback(async (action: any) => {
    const actId = action.id || action.action_id;
    setApprovingActionId(actId);
    try {
      let commandPrompt = action.title;
      if (action.action_type === 'sales_outreach') {
        commandPrompt = `Send sales outreach to ${action.parameters?.count || 10} leads via ${action.parameters?.channel || 'smtp'}`;
      } else if (action.action_type === 'generate_campaign') {
        commandPrompt = `Create a 7-day marketing campaign about ${action.parameters?.topic || 'AI Automation'}`;
      } else if (action.action_type === 'generate_leads') {
        commandPrompt = `Source ${action.parameters?.count || 20} leads for ${action.parameters?.query || 'tech founders'}`;
      }

      const res = await fetchWithAuth(`${API_URL}/commands/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: commandPrompt, provider: orchProvider, model: orchModel }),
      });
      const data = await res.json();
      notify(`Action approved & dispatched: ${action.title}`);

      const confirmMsg = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: `✅ Approved & Executed: "${action.title}"\n${data.results?.map((r: any) => r.message || r.status).join('\n') || 'Tasks queued for execution.'}`,
        plan: data.plan,
        results: data.results,
        timestamp: new Date().toISOString(),
      };
      setOrchMessages((prev) => [...prev, confirmMsg]);
      fetchData();
    } catch (err) {
      console.error(err);
      notify('Failed to execute approved action');
    } finally {
      setApprovingActionId(null);
    }
  }, [API_URL, fetchWithAuth, fetchData, orchProvider, orchModel]);

  const clearOrchestratorChat = React.useCallback(() => {
    const welcome = [
      {
        id: 'welcome',
        role: 'assistant',
        content:
          "Welcome to the Orchestrator AI Console. I coordinate your Marketing, Sales, Support, and Operations teams to accomplish complex business goals.\n\nTell me what you'd like to achieve, or select a suggested prompt below.",
        timestamp: '2026-01-01T00:00:00.000Z',
      },
    ];
    setOrchMessages(welcome);
    localStorage.setItem('orchestrator_chat_messages', JSON.stringify(welcome));
  }, []);

  const pendingApprovalsCount = (queue?.posts?.length || 0) + (queue?.leads?.length || 0);

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-in fade-in duration-300">
      {/* Standard OctaOS PageHeader */}
      <PageHeader
        title="Orchestrator AI"
        description="Autonomous multi-agent execution console coordinating Marketing, Sales, Support, and Operations fleets."
        actions={
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {configuredProviders.length} Providers Active
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={toggleSidebar}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              title={sidebarOpen ? 'Collapse side panel' : 'Expand side panel'}
            >
              {sidebarOpen ? (
                <>
                  <PanelRightClose className="size-3.5 mr-1.5" />
                  Collapse Sidebar
                </>
              ) : (
                <>
                  <PanelRightOpen className="size-3.5 mr-1.5" />
                  Show Sidebar{pendingApprovalsCount > 0 ? ` (${pendingApprovalsCount})` : ''}
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={clearOrchestratorChat}
              className="text-xs text-muted-foreground hover:text-destructive hover:border-destructive/30 transition-colors"
              title="Reset chat to welcome screen"
            >
              <Trash2 className="size-3.5 mr-1.5" />
              Clear Console
            </Button>
          </div>
        }
      />

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT: Chat Console (8 or 12 columns) */}
        <div className={`${sidebarOpen ? 'lg:col-span-8' : 'lg:col-span-12'} flex flex-col transition-all duration-300`}>
          <Card className="flex flex-col bg-card border-border rounded-xl shadow-xs overflow-hidden h-[760px]">
            {/* Console Control Bar */}
            <div className="px-5 py-3 border-b border-border bg-secondary/20 flex items-center justify-between gap-3 flex-wrap shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                  <Cpu className="size-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-foreground text-sm tracking-tight leading-none">
                      AI Fleet Command Center
                    </h3>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
                      <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Ready
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Cross-departmental DAG execution engine</p>
                </div>
              </div>

              {/* Model & Provider Selectors */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground hidden sm:inline">Provider:</span>
                  <Select
                    value={orchProvider}
                    onValueChange={(val) => {
                      if (val) {
                        setOrchProvider(val);
                        if (val === 'openrouter') setOrchModel('meta-llama/llama-3.3-70b-instruct');
                        else if (val === 'together') setOrchModel('meta-llama/Llama-3.3-70B-Instruct-Turbo');
                        else if (val === 'groq') setOrchModel('openai/gpt-oss-120b');
                        else if (val === 'grok') setOrchModel('grok-2-latest');
                        else if (val === 'anthropic') setOrchModel('claude-sonnet-4-6');
                        else if (val === 'openai') setOrchModel('gpt-4o');
                        else if (val === 'gemini') setOrchModel('gemini-2.5-pro');
                        else if (val === 'nvidia') setOrchModel('meta/llama-3.3-70b-instruct');
                        else if (val === 'auto') setOrchModel('');
                      }
                    }}
                  >
                    <SelectTrigger className="bg-background border-border text-foreground rounded-md h-8 text-xs w-[115px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-popover border-border text-popover-foreground">
                      <SelectItem value="auto">Auto / Default (.env)</SelectItem>
                      <SelectItem value="nvidia">NVIDIA NIM</SelectItem>
                      <SelectItem value="openrouter">OpenRouter</SelectItem>
                      <SelectItem value="together">Together AI</SelectItem>
                      <SelectItem value="groq">Groq</SelectItem>
                      <SelectItem value="anthropic">Claude</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="gemini">Gemini</SelectItem>
                      <SelectItem value="grok">Grok</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-muted-foreground hidden sm:inline">Model:</span>
                  <Select value={orchModel} onValueChange={(val) => val && setOrchModel(val)}>
                    <SelectTrigger className="bg-background border-border text-foreground rounded-md h-8 text-xs w-[145px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-popover border-border text-popover-foreground">
                      {orchProvider === 'openrouter' && (
                        <>
                          <SelectItem value="meta-llama/llama-3.3-70b-instruct">Llama 3.3 70B (Default)</SelectItem>
                          <SelectItem value="google/gemini-2.5-flash">Gemini 2.5 Flash</SelectItem>
                          <SelectItem value="google/gemini-2.5-pro">Gemini 2.5 Pro</SelectItem>
                          <SelectItem value="anthropic/claude-3.5-sonnet">Claude 3.5 Sonnet</SelectItem>
                          <SelectItem value="openai/gpt-4o">GPT-4o</SelectItem>
                          <SelectItem value="openai/gpt-4o-mini">GPT-4o-mini</SelectItem>
                          <SelectItem value="deepseek/deepseek-chat">DeepSeek Chat</SelectItem>
                          <SelectItem value="deepseek/deepseek-r1">DeepSeek R1</SelectItem>
                          <SelectItem value="qwen/qwen-2.5-72b-instruct">Qwen 2.5 72B</SelectItem>
                        </>
                      )}
                      {orchProvider === 'nvidia' && (
                        <>
                          <SelectItem value="meta/llama-3.3-70b-instruct">Llama 3.3 70B (Default)</SelectItem>
                          <SelectItem value="meta/llama-3.1-405b-instruct">Llama 3.1 405B</SelectItem>
                          <SelectItem value="meta/llama-3.1-70b-instruct">Llama 3.1 70B</SelectItem>
                          <SelectItem value="meta/llama-3.1-8b-instruct">Llama 3.1 8B</SelectItem>
                        </>
                      )}
                      {orchProvider === 'together' && (
                        <>
                          <SelectItem value="meta-llama/Llama-3.3-70B-Instruct-Turbo">Llama 3.3 70B Turbo</SelectItem>
                          <SelectItem value="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo">Llama 3.1 8B Turbo</SelectItem>
                          <SelectItem value="deepseek-ai/DeepSeek-V3">DeepSeek V3</SelectItem>
                          <SelectItem value="deepseek-ai/DeepSeek-R1">DeepSeek R1</SelectItem>
                          <SelectItem value="Qwen/Qwen2.5-72B-Instruct-Turbo">Qwen 2.5 72B Turbo</SelectItem>
                        </>
                      )}
                      {orchProvider === 'groq' && (
                        <>
                          <SelectItem value="openai/gpt-oss-120b">GPT OSS 120B</SelectItem>
                          <SelectItem value="llama-3.1-8b-instant">Llama 3.1 8B Instant</SelectItem>
                          <SelectItem value="mixtral-8x7b-32768">Mixtral 8x7B</SelectItem>
                        </>
                      )}
                      {orchProvider === 'anthropic' && (
                        <>
                          <SelectItem value="claude-sonnet-4-6">Sonnet 4.6</SelectItem>
                          <SelectItem value="claude-opus-4-8">Opus 4.8</SelectItem>
                          <SelectItem value="claude-haiku-4-5-20251001">Haiku 4.5</SelectItem>
                        </>
                      )}
                      {orchProvider === 'openai' && (
                        <>
                          <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                          <SelectItem value="gpt-4o-mini">GPT-4o-mini</SelectItem>
                        </>
                      )}
                      {orchProvider === 'gemini' && (
                        <>
                          <SelectItem value="gemini-2.5-pro">2.5 Pro</SelectItem>
                          <SelectItem value="gemini-2.5-flash">2.5 Flash</SelectItem>
                          <SelectItem value="gemini-2.0-flash">2.0 Flash</SelectItem>
                        </>
                      )}
                      {orchProvider === 'grok' && (
                        <>
                          <SelectItem value="grok-2-latest">Grok 2 Latest</SelectItem>
                          <SelectItem value="grok-2-vision-latest">Grok 2 Vision</SelectItem>
                          <SelectItem value="grok-beta">Grok Beta</SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleSidebar}
                  className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground hidden lg:flex items-center justify-center rounded-md"
                  title={sidebarOpen ? 'Collapse side panel' : 'Expand side panel'}
                >
                  {sidebarOpen ? <PanelRightClose className="size-3.5" /> : <PanelRightOpen className="size-3.5" />}
                </Button>
              </div>
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4 min-h-0">
              {orchMessages.map((msg: any) => (
                <div key={msg.id}>
                  {msg.role === 'user' ? (
                    <div className="flex justify-end animate-in fade-in duration-200">
                      <div className="max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-xs px-4 py-2.5 shadow-xs">
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                        <span className="text-[10px] mt-1.5 block text-right text-primary-foreground/75 font-medium">
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start gap-3 justify-start animate-in fade-in duration-200">
                      <div className="h-8 w-8 rounded-lg bg-secondary border border-border flex items-center justify-center text-primary shrink-0 mt-0.5">
                        <Bot className="size-4" />
                      </div>
                      <div className="flex-1 max-w-[90%] bg-card border border-border text-foreground rounded-2xl rounded-tl-xs p-4 shadow-xs space-y-3">
                        <p className="text-sm leading-relaxed whitespace-pre-wrap text-foreground/95">{msg.content}</p>

                        {/* EXECUTIVE BRIEFING DECK */}
                        {msg.briefing && (
                          <div className="mt-3 pt-3 border-t border-border space-y-3.5">
                            {/* Executive Header Banner */}
                            <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-border">
                              <div className="flex items-center gap-2">
                                <Sparkles className="size-3.5 text-primary" />
                                <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
                                  C-Suite Executive Briefing
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                  {msg.briefing.data_freshness || 'Live SQL Grounded'}
                                </span>
                                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md bg-secondary text-muted-foreground border border-border">
                                  10-Agent Swarm
                                </span>
                              </div>
                            </div>

                            {/* 1. Live Grounded KPI Scorecard Grid */}
                            {msg.briefing.metrics?.items && (
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                                {msg.briefing.metrics.items['leads.total'] && (
                                  <div className="bg-secondary/40 border border-border rounded-lg p-2.5 flex flex-col justify-between">
                                    <span className="text-[11px] font-medium text-muted-foreground">Active Leads</span>
                                    <div className="flex items-baseline justify-between mt-1">
                                      <span className="text-base font-semibold text-foreground">
                                        {msg.briefing.metrics.items['leads.total'].formatted}
                                      </span>
                                      {msg.briefing.metrics.items['leads.total'].change_pct_wow !== null && (
                                        <span
                                          className={`text-[10px] font-medium flex items-center ${
                                            (msg.briefing.metrics.items['leads.total'].change_pct_wow || 0) >= 0
                                              ? 'text-emerald-400'
                                              : 'text-rose-400'
                                          }`}
                                        >
                                          {(msg.briefing.metrics.items['leads.total'].change_pct_wow || 0) >= 0 ? '+' : ''}
                                          {msg.briefing.metrics.items['leads.total'].change_pct_wow}% WoW
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {msg.briefing.metrics.items['leads.conversion_rate'] && (
                                  <div className="bg-secondary/40 border border-border rounded-lg p-2.5 flex flex-col justify-between">
                                    <span className="text-[11px] font-medium text-muted-foreground">Conversion Rate</span>
                                    <div className="flex items-baseline justify-between mt-1">
                                      <span className="text-base font-semibold text-foreground">
                                        {msg.briefing.metrics.items['leads.conversion_rate'].formatted}
                                      </span>
                                      <span className="text-[10px] text-muted-foreground">Pipeline</span>
                                    </div>
                                  </div>
                                )}

                                {msg.briefing.metrics.items['deals.pipeline_value'] && (
                                  <div className="bg-secondary/40 border border-border rounded-lg p-2.5 flex flex-col justify-between">
                                    <span className="text-[11px] font-medium text-muted-foreground">Pipeline Capital</span>
                                    <div className="flex items-baseline justify-between mt-1">
                                      <span className="text-base font-semibold text-emerald-400">
                                        {msg.briefing.metrics.items['deals.pipeline_value'].formatted}
                                      </span>
                                      <span className="text-[10px] text-muted-foreground">Active</span>
                                    </div>
                                  </div>
                                )}

                                {msg.briefing.metrics.items['tickets.sla_compliance'] && (
                                  <div className="bg-secondary/40 border border-border rounded-lg p-2.5 flex flex-col justify-between">
                                    <span className="text-[11px] font-medium text-muted-foreground">Support SLA</span>
                                    <div className="flex items-baseline justify-between mt-1">
                                      <span className="text-base font-semibold text-foreground">
                                        {msg.briefing.metrics.items['tickets.sla_compliance'].formatted}
                                      </span>
                                      <span className="text-[10px] text-muted-foreground">Target 95%</span>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* 2. Visual Analytics Deck */}
                            {msg.briefing.charts && msg.briefing.charts.length > 0 && (
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-semibold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                                    <BarChart3 className="size-3.5 text-primary" /> Visual Analytics
                                  </span>
                                  <span className="text-[10px] text-muted-foreground">Interactive Plotly Engine</span>
                                </div>
                                <OrchestratorCharts charts={msg.briefing.charts} />
                              </div>
                            )}

                            {/* 3. Operational Bottlenecks & Vulnerabilities */}
                            {msg.briefing.findings && msg.briefing.findings.length > 0 && (
                              <div className="space-y-2">
                                <span className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                                  <ShieldAlert className="size-3.5 text-rose-400" /> Operational Bottlenecks & Vulnerabilities
                                </span>
                                <div className="space-y-2">
                                  {msg.briefing.findings.map((f: any) => (
                                    <div
                                      key={f.id}
                                      className={`rounded-lg p-3 border text-xs space-y-1.5 transition-colors ${
                                        f.severity === 'CRITICAL'
                                          ? 'bg-rose-500/10 border-rose-500/20 text-rose-200'
                                          : f.severity === 'WARNING'
                                          ? 'bg-amber-500/10 border-amber-500/20 text-amber-200'
                                          : 'bg-secondary/40 border-border text-foreground'
                                      }`}
                                    >
                                      <div className="flex items-center justify-between gap-2">
                                        <span className="font-semibold flex items-center gap-1.5 text-foreground">
                                          <AlertTriangle
                                            className={`size-3.5 ${
                                              f.severity === 'CRITICAL' ? 'text-rose-400' : 'text-amber-400'
                                            }`}
                                          />
                                          {f.title}
                                        </span>
                                        <span
                                          className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-md border ${
                                            f.severity === 'CRITICAL'
                                              ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                                              : f.severity === 'WARNING'
                                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                                              : 'bg-secondary text-muted-foreground border-border'
                                          }`}
                                        >
                                          {f.severity}
                                        </span>
                                      </div>
                                      <p className="text-muted-foreground leading-relaxed font-normal">{f.evidence}</p>
                                      <div className="pt-1 flex items-center gap-2 text-[11px] text-muted-foreground border-t border-border/50">
                                        <span>
                                          <strong className="text-foreground">Root Cause:</strong> {f.root_cause}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* 4. Strategic Improvement Roadmap */}
                            {msg.briefing.improvement_plan && msg.briefing.improvement_plan.length > 0 && (
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                                    <CheckCircle2 className="size-3.5 text-emerald-400" /> Strategic Improvement Roadmap
                                  </span>
                                  <span className="text-[10px] text-muted-foreground">Actionable with Approval Guard</span>
                                </div>
                                <div className="space-y-2">
                                  {msg.briefing.improvement_plan.map((act: any) => (
                                    <div
                                      key={act.id}
                                      className="bg-secondary/40 border border-border rounded-lg p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                                    >
                                      <div className="space-y-1 flex-1">
                                        <div className="flex items-center gap-2">
                                          <span
                                            className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-md border ${
                                              act.phase === '7d'
                                                ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                                                : act.phase === '30d'
                                                ? 'bg-blue-500/10 text-blue-300 border-blue-500/20'
                                                : 'bg-primary/10 text-primary border-primary/20'
                                            }`}
                                          >
                                            {act.phase === '7d' ? '7-Day Quick Win' : act.phase === '30d' ? '30-Day Fix' : '90-Day Scale'}
                                          </span>
                                          <span className="text-xs font-semibold text-foreground">{act.title}</span>
                                        </div>
                                        <p className="text-xs text-muted-foreground">{act.description}</p>
                                        {act.estimated_roi && (
                                          <span className="text-[11px] text-emerald-400 font-medium block">
                                            ★ Expected Impact: {act.estimated_roi}
                                          </span>
                                        )}
                                      </div>

                                      <Button
                                        size="sm"
                                        disabled={approvingActionId === act.id}
                                        onClick={() => handleExecuteApprovedAction(act)}
                                        className="h-7 text-xs font-medium shrink-0"
                                      >
                                        {approvingActionId === act.id ? (
                                          <Loader2 className="size-3 animate-spin mr-1" />
                                        ) : (
                                          <Sparkles className="size-3 mr-1" />
                                        )}
                                        Execute Plan
                                      </Button>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* 5. Swarm Execution Trace Drawer */}
                            {msg.briefing.trace && msg.briefing.trace.length > 0 && (
                              <div className="border border-border rounded-lg overflow-hidden bg-secondary/20">
                                <button
                                  type="button"
                                  onClick={() => setExpandedTraces((prev) => ({ ...prev, [msg.id]: !prev[msg.id] }))}
                                  className="w-full px-3.5 py-2.5 flex items-center justify-between text-xs font-medium text-muted-foreground hover:text-foreground bg-secondary/40 transition-colors"
                                >
                                  <span className="flex items-center gap-1.5">
                                    <Layers className="size-3.5 text-primary" />
                                    10-Agent Swarm Audit Trace ({msg.briefing.trace.length} agents executed)
                                  </span>
                                  {expandedTraces[msg.id] ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
                                </button>

                                {expandedTraces[msg.id] && (
                                  <div className="p-3.5 space-y-2 border-t border-border text-xs divide-y divide-border/40">
                                    {msg.briefing.trace.map((tr: any) => (
                                      <div key={tr.agent_id} className="flex items-start justify-between gap-2 pt-2 first:pt-0">
                                        <div className="flex items-start gap-2">
                                          <span className="h-4 w-4 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                                            {tr.agent_id}
                                          </span>
                                          <div>
                                            <span className="font-semibold text-foreground">{tr.name}</span>
                                            <span className="text-muted-foreground text-[11px] block">{tr.role}</span>
                                            <p className="text-muted-foreground text-[11px] mt-0.5">{tr.summary}</p>
                                          </div>
                                        </div>
                                        <div className="text-right shrink-0">
                                          <span className="text-[10px] text-muted-foreground block font-mono">{tr.latency_ms}ms</span>
                                          <span className="text-[9px] uppercase font-semibold text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                                            {tr.execution_type}
                                          </span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* HYBRID MODE: DRAFT ACTION PLAN */}
                        {msg.mode === 'hybrid' && msg.plan?.actions && msg.plan.actions.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-amber-500/30 bg-amber-500/10 rounded-lg p-3 space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                                <AlertTriangle className="size-3.5 text-amber-400" /> Hybrid Mode: Execution Plan Drafted
                              </span>
                              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                Approval Required
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              The diagnostic swarm formulated the following immediate actions to address your query. Please review before execution:
                            </p>
                            <div className="space-y-1.5">
                              {msg.plan.actions.map((act: any) => (
                                <div key={act.action_id} className="flex items-center justify-between bg-card rounded-md px-3 py-2 border border-border">
                                  <span className="text-xs text-foreground font-medium">{act.title}</span>
                                  <Button
                                    size="sm"
                                    disabled={approvingActionId === act.action_id}
                                    onClick={() => handleExecuteApprovedAction(act)}
                                    className="h-7 text-xs font-medium"
                                  >
                                    Confirm & Run
                                  </Button>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Execution Blueprint */}
                        {msg.plan?.tasks && msg.plan.tasks.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-border space-y-2">
                            <span className="text-xs font-semibold uppercase tracking-wider text-primary flex items-center gap-1.5">
                              <Sparkles className="size-3 text-primary" /> Execution Blueprint
                            </span>
                            {msg.plan.tasks.map((task: any, idx: number) => (
                              <div key={idx} className="flex items-center gap-2.5 bg-secondary/40 rounded-lg px-3 py-2 border border-border">
                                <span
                                  className={`h-2 w-2 rounded-full shrink-0 ${
                                    task.department === 'Marketing'
                                      ? 'bg-indigo-500'
                                      : task.department === 'Sales'
                                      ? 'bg-emerald-500'
                                      : task.department === 'Support'
                                      ? 'bg-blue-500'
                                      : task.department === 'HR'
                                      ? 'bg-amber-500'
                                      : task.department === 'System'
                                      ? 'bg-rose-500'
                                      : 'bg-zinc-500'
                                  }`}
                                />
                                <span className="text-xs font-semibold text-foreground">{task.department}</span>
                                <span className="text-xs text-muted-foreground">→ {task.action}</span>
                                {task.parameters && Object.keys(task.parameters).length > 0 && (
                                  <span className="text-xs text-muted-foreground ml-auto hidden sm:inline truncate max-w-[180px] font-mono">
                                    {JSON.stringify(task.parameters).slice(0, 60)}
                                  </span>
                                )}
                                <Check className="size-3 text-emerald-400 ml-auto shrink-0" />
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Quick Connect for API key requirements */}
                        {msg.results?.some((r: any) => r.status === 'action_required') && (
                          <div className="mt-3 pt-3 border-t border-border">
                            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 space-y-2.5">
                              <span className="text-xs font-semibold uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                                <Zap className="size-3 text-amber-400" /> Quick Connect
                              </span>
                              <div className="flex gap-2">
                                <Input
                                  type="text"
                                  placeholder="Paste your API key here..."
                                  value={orchInlineKeyValue}
                                  onChange={(e) => setOrchInlineKeyValue(e.target.value)}
                                  className="bg-background border-border text-foreground focus:border-amber-500 rounded-md h-8 text-xs flex-1"
                                />
                                <Button
                                  onClick={async () => {
                                    if (!orchInlineKeyValue) return;
                                    let detectedProvider = 'anthropic';
                                    if (orchInlineKeyValue.startsWith('sk-ant')) detectedProvider = 'anthropic';
                                    else if (orchInlineKeyValue.startsWith('sk-or-')) detectedProvider = 'openrouter';
                                    else if (orchInlineKeyValue.startsWith('sk-')) detectedProvider = 'openai';
                                    else if (orchInlineKeyValue.startsWith('AIza')) detectedProvider = 'gemini';
                                    else if (orchInlineKeyValue.startsWith('gsk_')) detectedProvider = 'groq';
                                    else if (orchInlineKeyValue.startsWith('xai-')) detectedProvider = 'grok';
                                    try {
                                      await fetchWithAuth(`${API_URL}/commands/keys`, {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({ provider: detectedProvider, key: orchInlineKeyValue }),
                                      });
                                      setOrchInlineKeyValue('');
                                      fetchData();
                                      const successMsg = {
                                        id: `system-${Date.now()}`,
                                        role: 'assistant' as const,
                                        content: `✅ ${detectedProvider} API key saved successfully. I'm now fully operational — what would you like me to do?`,
                                        timestamp: new Date().toISOString(),
                                      };
                                      setOrchMessages((prev) => [...prev, successMsg]);
                                    } catch (err) {
                                      console.error(err);
                                    }
                                  }}
                                  className="h-8 px-3 text-xs font-medium"
                                >
                                  Save
                                </Button>
                              </div>
                            </div>
                          </div>
                        )}

                        <span className="text-[10px] mt-2 block text-right text-muted-foreground font-medium">
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Typing Indicator */}
              {loading && (
                <div className="flex items-start gap-3 justify-start animate-in fade-in duration-200">
                  <div className="h-8 w-8 rounded-lg bg-secondary border border-border flex items-center justify-center text-primary shrink-0 mt-0.5">
                    <Bot className="size-4" />
                  </div>
                  <div className="bg-card border border-border rounded-2xl rounded-tl-xs px-4 py-3 shadow-xs">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span className="text-xs text-muted-foreground font-medium ml-1">Orchestrating teams & agents...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={orchChatEndRef} />
            </div>

            {/* Quick Prompt Chips */}
            <div className="px-5 py-2.5 border-t border-border bg-secondary/15 shrink-0">
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setOrchInput('Generate a full executive report on our current operations and weaknesses')}
                  className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors flex items-center gap-1.5"
                >
                  <BarChart3 className="size-3 text-primary" />
                  Executive Briefing
                </button>
                <button
                  type="button"
                  onClick={() => setOrchInput('Visual analytics of lead funnel velocity with Plotly charts')}
                  className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors flex items-center gap-1.5"
                >
                  <TrendingUp className="size-3 text-primary" />
                  Visual Analytics
                </button>
                <button
                  type="button"
                  onClick={() => setOrchInput('What are our biggest operational weaknesses and bottlenecks?')}
                  className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors flex items-center gap-1.5"
                >
                  <ShieldAlert className="size-3 text-rose-400" />
                  Weakness Audit
                </button>
                <button
                  type="button"
                  onClick={() => setOrchInput('Why is conversion low, and fix it')}
                  className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors flex items-center gap-1.5"
                >
                  <Zap className="size-3 text-amber-400" />
                  Diagnose & Fix
                </button>
                {apps.some((a: any) => a.app_name === 'Restaurant Growth Pack') && (
                  <button
                    type="button"
                    onClick={() =>
                      setOrchInput(
                        "Trigger the daily special post for Restaurant Pack. Create a draft of today's specials for Instagram."
                      )
                    }
                    className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors"
                  >
                    🍔 Daily specials
                  </button>
                )}
                {apps.some((a: any) => a.app_name === 'SaaS Outreach System') && (
                  <button
                    type="button"
                    onClick={() =>
                      setOrchInput(
                        'Execute the SaaS Outreach System. Source 5 CTOs at early-stage AI startups in New York.'
                      )
                    }
                    className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors"
                  >
                    🚀 Source SaaS leads
                  </button>
                )}
                {apps.some((a: any) => a.app_name === 'Real Estate Lead Engine') && (
                  <button
                    type="button"
                    onClick={() =>
                      setOrchInput(
                        'Generate property descriptions using the Real Estate Lead Engine for 456 Oak Ave. Premium luxury pool description.'
                      )
                    }
                    className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors"
                  >
                    🏡 Generate listings
                  </button>
                )}
                {apps.some((a: any) => a.app_name === 'Creative Content Lab') && (
                  <button
                    type="button"
                    onClick={() =>
                      setOrchInput(
                        "Create an SEO Blog Outline with the Creative Content Lab on 'How AI employees are transforming small businesses'."
                      )
                    }
                    className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors"
                  >
                    ✨ Write blog outline
                  </button>
                )}
                {apps.length === 0 && (
                  <>
                    <button
                      type="button"
                      onClick={() => setOrchInput('Find 5 marketing agencies in San Francisco and email them a partnership proposal.')}
                      className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors"
                    >
                      🔍 Find leads & email
                    </button>
                    <button
                      type="button"
                      onClick={() => setOrchInput('Create a 7-day Instagram content campaign about healthy meal prep tips.')}
                      className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors"
                    >
                      📸 Create content campaign
                    </button>
                    <button
                      type="button"
                      onClick={() => setOrchInput('Source 5 senior React developers with 4+ years experience, salary $130k/year.')}
                      className="text-xs font-medium px-2.5 py-1 rounded-md bg-secondary/70 hover:bg-secondary text-foreground border border-border transition-colors"
                    >
                      👨‍💻 Hire developers
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Input Area */}
            <div className="px-5 py-3.5 border-t border-border bg-secondary/20 shrink-0">
              <input ref={filePickerRef} type="file" multiple accept=".csv,.tsv,.json,.jsonl,.ndjson,.txt,.md,.log,.pdf,.docx,.xlsx,.xlsm,.pptx,.zip" className="hidden" onChange={event => { setAnalysisFiles(prev => [...prev, ...Array.from(event.target.files || [])].slice(0, 100)); setFileInputError(''); }} />
              <input ref={folderPickerRef} type="file" multiple {...({ webkitdirectory: '', directory: '' } as any)} className="hidden" onChange={event => { setAnalysisFiles(prev => [...prev, ...Array.from(event.target.files || [])].slice(0, 100)); setFileInputError(''); }} />
              {analysisFiles.length > 0 && <div className="mb-3 rounded-lg border border-border bg-background p-3">
                <div className="mb-2 flex items-center justify-between gap-2"><span className="text-xs font-semibold">{analysisFiles.length} file(s) ready · {(analysisFiles.reduce((sum, file) => sum + file.size, 0) / (1024 * 1024)).toFixed(2)} MB</span><button type="button" onClick={() => { setAnalysisFiles([]); if (filePickerRef.current) filePickerRef.current.value = ''; if (folderPickerRef.current) folderPickerRef.current.value = ''; }} className="text-xs text-muted-foreground hover:text-foreground">Clear all</button></div>
                <div className="max-h-24 space-y-1 overflow-y-auto">{analysisFiles.map((file, index) => <div key={`${file.name}-${index}`} className="flex items-center gap-2 text-xs text-muted-foreground"><FileText className="size-3.5 shrink-0"/><span className="min-w-0 flex-1 truncate">{(file as File & {webkitRelativePath?: string}).webkitRelativePath || file.name}</span><span className="shrink-0">{(file.size / 1024).toFixed(0)} KB</span><button type="button" aria-label={`Remove ${file.name}`} onClick={() => setAnalysisFiles(prev => prev.filter((_, i) => i !== index))} className="rounded p-0.5 hover:bg-muted"><X className="size-3.5"/></button></div>)}</div>
                {fileInputError && <p role="alert" className="mt-2 text-xs text-destructive">{fileInputError}</p>}
                <Button type="button" onClick={() => void handleAnalyzeFiles()} disabled={analyzingFiles || loading || !analysisFiles.length} size="sm" className="mt-3 w-full">{analyzingFiles ? <><Loader2 className="mr-2 size-4 animate-spin"/>Analyzing uploaded files…</> : <><BarChart3 className="mr-2 size-4"/>Analyze files and generate report</>}</Button>
              </div>}
              {fileInputError && analysisFiles.length === 0 && <p role="alert" className="mb-2 text-xs text-destructive">{fileInputError}</p>}
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Button type="button" variant="outline" size="sm" disabled={loading || analyzingFiles} onClick={() => filePickerRef.current?.click()} className="h-8 gap-1.5 text-xs"><Paperclip className="size-3.5"/> Attach files</Button>
                <Button type="button" variant="outline" size="sm" disabled={loading || analyzingFiles} onClick={() => folderPickerRef.current?.click()} className="h-8 gap-1.5 text-xs"><FolderOpen className="size-3.5"/> Upload folder</Button>
                <span className="text-[11px] text-muted-foreground">File analysis runs separately from command execution.</span>
              </div>
              <div className="flex gap-2.5 items-end">
                <div className="flex-1 relative">
                  <Textarea
                    placeholder="Instruct the orchestrator or describe a business objective..."
                    value={orchInput}
                    onChange={(e) => setOrchInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        void handleRunCommand((e.target as HTMLTextAreaElement).value);
                      }
                    }}
                    className="bg-background border-border text-foreground placeholder:text-muted-foreground focus:border-primary rounded-lg text-sm min-h-[44px] max-h-[120px] resize-none pr-3 py-2.5"
                    rows={1}
                  />
                </div>
                <Button
                  onClick={(event) => {
                    const field = event.currentTarget.parentElement?.querySelector('textarea');
                    void handleRunCommand(field?.value);
                  }}
                  disabled={loading || !orchInput.trim()}
                  className="h-11 px-4 rounded-lg flex items-center justify-center gap-1.5 font-medium shrink-0"
                >
                  {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                  <span className="hidden sm:inline">Send</span>
                </Button>
              </div>
              <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
                <span>Enter to send, Shift + Enter for new line</span>
                <span className="flex items-center gap-1">
                  <Activity className="size-3 text-emerald-400" />
                  Autonomous Execution Connected
                </span>
              </div>
            </div>
          </Card>
        </div>

        {/* RIGHT: Sidebar (4 columns) */}
        {sidebarOpen && (
          <div className="lg:col-span-4 flex flex-col gap-6 animate-in fade-in duration-200">
            {/* Live Activity Feed */}
            <Card
              className={`bg-card border-border rounded-xl shadow-xs overflow-hidden flex flex-col transition-all duration-200 ${
                activityFeedCollapsed
                  ? 'h-auto'
                  : approvalsCollapsed
                  ? 'h-[760px]'
                  : 'h-[400px]'
              }`}
            >
              <CardHeader className="py-2.5 px-4 border-b border-border shrink-0 bg-secondary/20 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <Activity className="size-4 text-primary" />
                  Live Activity Feed
                </CardTitle>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-muted-foreground font-normal">
                    {timeline.length} logs
                  </span>
                  <button
                    type="button"
                    onClick={() => setActivityFeedCollapsed((prev) => !prev)}
                    className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
                    title={activityFeedCollapsed ? 'Expand Activity Feed' : 'Collapse Activity Feed'}
                  >
                    {activityFeedCollapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
                  </button>
                </div>
              </CardHeader>

              {!activityFeedCollapsed && (
                <CardContent className="p-4 space-y-3 overflow-y-auto flex-1 min-h-0">
                  {timeline.length === 0 && (
                    <div className="text-center py-10 text-xs text-muted-foreground">
                      No recent activity logs.
                    </div>
                  )}
                  {timeline.slice(0, 30).map((log: any) => (
                    <div key={log.id} className="relative pl-3.5 border-l border-border space-y-1 text-xs">
                      <span className="absolute -left-1 top-1.5 size-2 rounded-full bg-primary" />
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground text-xs">{log.agent_name}</span>
                        <span className="text-[11px] text-muted-foreground font-mono">
                          {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <span className="text-primary font-medium text-xs block">{log.action}</span>
                      <p className="text-muted-foreground text-xs leading-relaxed line-clamp-2">
                        {log.description}
                      </p>
                    </div>
                  ))}
                </CardContent>
              )}
            </Card>

            {/* Pending Approvals */}
            <Card
              className={`bg-card border-border rounded-xl shadow-xs overflow-hidden flex flex-col transition-all duration-200 ${
                approvalsCollapsed
                  ? 'h-auto'
                  : activityFeedCollapsed
                  ? 'h-[760px]'
                  : 'h-[336px]'
              }`}
            >
              <CardHeader className="py-2.5 px-4 border-b border-border shrink-0 bg-secondary/20 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold text-foreground flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2">
                    <Check className="size-4 text-emerald-400" />
                    Pending Approvals
                  </span>
                  {pendingApprovalsCount > 0 ? (
                    <span className="text-xs bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded-full font-medium">
                      {pendingApprovalsCount} pending
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground font-normal">All clear</span>
                  )}
                </CardTitle>
                <button
                  type="button"
                  onClick={() => setApprovalsCollapsed((prev) => !prev)}
                  className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors ml-2"
                  title={approvalsCollapsed ? 'Expand Pending Approvals' : 'Collapse Pending Approvals'}
                >
                  {approvalsCollapsed ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
                </button>
              </CardHeader>

              {!approvalsCollapsed && (
                <CardContent className="p-3.5 space-y-2.5 overflow-y-auto flex-1 min-h-0">
                  {(!queue?.posts || queue.posts.length === 0) && (!queue?.leads || queue.leads.length === 0) && (
                    <div className="text-center py-8 text-xs text-muted-foreground">
                      No pending items in queue.
                    </div>
                  )}
                  {queue?.posts?.slice(0, 10).map((post: any) => (
                    <div key={post.id} className="bg-secondary/40 border border-border rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold uppercase text-primary tracking-wide">{post.platform}</span>
                        <span className="text-[11px] text-muted-foreground font-medium">Day {post.day}</span>
                      </div>
                      <p className="text-xs text-foreground/90 leading-relaxed line-clamp-2">{post.content}</p>
                      <div className="flex gap-2 pt-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRejectPost(post.id)}
                          className="h-7 text-xs text-muted-foreground hover:text-destructive hover:border-destructive/30 flex-1 rounded-md"
                        >
                          Reject
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleApprovePost(post.id)}
                          className="h-7 text-xs flex-1 rounded-md"
                        >
                          Approve
                        </Button>
                      </div>
                    </div>
                  ))}
                  {queue?.leads?.slice(0, 6).map((lead: any) => (
                    <div key={lead.id} className="bg-secondary/40 border border-border rounded-lg p-3 flex items-center justify-between">
                      <div className="flex flex-col">
                        <span className="text-xs font-semibold text-foreground">{lead.name}</span>
                        <span className="text-[11px] text-muted-foreground">{lead.company}</span>
                      </div>
                      <span className="text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-md uppercase">
                        {lead.source}
                      </span>
                    </div>
                  ))}
                </CardContent>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

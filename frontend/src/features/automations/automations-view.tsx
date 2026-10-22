'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

function Badge({ children, className = '', variant = 'default' }: { children: React.ReactNode; className?: string; variant?: string }) {
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium border ${className}`}>
      {children}
    </span>
  );
}
import {
  Sparkles,
  GitFork,
  Play,
  Pause,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Activity,
  Layers,
  ArrowRight,
  Clock,
  RefreshCw,
  KeyRound,
  BarChart3,
  Sliders,
  ChevronRight,
  Check,
  Bot,
  Zap,
  Plus,
  FileText,
} from 'lucide-react';
import { notify } from '@/lib/notify';
import WorkflowCanvas from './canvas/workflow-canvas';

interface AutomationsViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData?: () => Promise<void>;
  userProfile?: any;
}

export default function AutomationsView({
  token,
  API_URL,
  fetchWithAuth,
  userProfile,
}: AutomationsViewProps) {
  // Permission to build and access the visual canvas
  const userRole = (userProfile?.role || '').toLowerCase();
  const canBuild = !!(
    userProfile?.is_system_admin ||
    userRole === 'admin' ||
    userRole === 'owner' ||
    userRole === 'super_admin' ||
    userRole === 'manager' ||
    userRole === 'automation_manager'
  );

  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'workflows' | 'canvas' | 'connections' | 'usage'>('workflows');

  // Workflows & Usage data
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // AI Prompt & Synthesis
  const [prompt, setPrompt] = useState('');
  const [category, setCategory] = useState('sales');
  const [synthesizing, setSynthesizing] = useState(false);
  const [synthesisResult, setSynthesisResult] = useState<any>(null);

  // Modals & Drawers
  const [activeEditorUrl, setActiveEditorUrl] = useState<string | null>(null);
  const [canvasWorkflowId, setCanvasWorkflowId] = useState<string | null>(null);
  const [viewingStepsWorkflow, setViewingStepsWorkflow] = useState<any | null>(null);
  const [selectedWorkflowForExecutions, setSelectedWorkflowForExecutions] = useState<any | null>(null);
  const [executions, setExecutions] = useState<any[]>([]);
  const [loadingExecutions, setLoadingExecutions] = useState(false);

  // Load initial data
  const loadData = async () => {
    setLoading(true);
    try {
      const [wfRes, connRes, usageRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/automations`),
        fetchWithAuth(`${API_URL}/automations/connections`),
        fetchWithAuth(`${API_URL}/automations/usage`),
      ]);

      if (wfRes.ok) setWorkflows(await wfRes.json());
      if (connRes.ok) setConnections(await connRes.json());
      if (usageRes.ok) setUsage(await usageRes.json());
    } catch (e) {
      console.error('Failed to load automations data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) loadData();
  }, [token]);

  // Handle AI synthesis
  const handleSynthesize = async () => {
    if (!prompt.trim()) return;
    setSynthesizing(true);
    setSynthesisResult(null);

    try {
      const res = await fetchWithAuth(`${API_URL}/automations/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, category }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to synthesize automation');
        return;
      }

      const data = await res.json();
      setSynthesisResult(data);
      notify('Automation blueprint generated and validated by OctaOS Governance.');
    } catch (e: any) {
      notify('Error synthesizing automation: ' + e.message);
    } finally {
      setSynthesizing(false);
    }
  };

  // Deploy or Save synthesized workflow
  const handleDeploySynthesized = async (activateNow: boolean) => {
    if (!synthesisResult) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/automations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: synthesisResult.definition_ir.name,
          slug: synthesisResult.definition_ir.slug,
          description: synthesisResult.definition_ir.description,
          category: synthesisResult.definition_ir.category,
          definition_ir: synthesisResult.definition_ir,
          activate_now: activateNow,
          ai_prompt: prompt,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to save automation');
        return;
      }

      notify(activateNow ? 'Automation deployed and activated successfully!' : 'Automation saved as draft.');
      setSynthesisResult(null);
      setPrompt('');
      loadData();
    } catch (e: any) {
      notify('Error saving workflow: ' + e.message);
    }
  };

  // Toggle active status
  const handleToggleActive = async (workflowId: string, currentStatus: string) => {
    const nextActive = currentStatus !== 'active';
    try {
      const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: nextActive }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to update workflow state');
        return;
      }

      notify(nextActive ? 'Workflow activated!' : 'Workflow paused.');
      loadData();
    } catch (e: any) {
      notify('Error updating state: ' + e.message);
    }
  };

  // Manual test execution
  const handleTestRun = async (workflowId: string) => {
    try {
      notify('Triggering test execution...');
      const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: { test: true, initiator: 'OctaOS Console' } }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Test execution failed');
        return;
      }

      notify('Test execution succeeded! Check logs for details.');
      loadData();
    } catch (e: any) {
      notify('Test run failed: ' + e.message);
    }
  };

  // Open Canvas Editor
  const handleOpenEditor = async (workflowId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/editor-url`);
      if (res.ok) {
        const data = await res.json();
        setActiveEditorUrl(data.editor_url);
      } else {
        notify('Failed to generate visual editor session.');
      }
    } catch (e: any) {
      notify('Error launching editor: ' + e.message);
    }
  };

  // View Execution History
  const handleViewExecutions = async (workflow: any) => {
    setSelectedWorkflowForExecutions(workflow);
    setLoadingExecutions(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/automations/${workflow.id}/executions`);
      if (res.ok) {
        setExecutions(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingExecutions(false);
    }
  };

  // Create blank visual workflow
  const handleCreateNewVisualWorkflow = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/automations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'New Visual Workflow',
          category: 'operations',
          definition_ir: {
            name: 'New Visual Workflow',
            category: 'operations',
            trigger: { type: 'octaos_event', event: 'lead.qualified', display_name: 'OctaOS: Lead Qualified' },
            steps: [],
          },
        }),
      });
      if (res.ok) {
        const data = await res.json();
        notify('Visual workflow created! Opening canvas...');
        setCanvasWorkflowId(data.id);
      } else {
        notify('Failed to create workflow');
      }
    } catch (e: any) {
      notify('Error creating workflow: ' + e.message);
    }
  };

  if (canvasWorkflowId) {
    return (
      <WorkflowCanvas
        workflowId={canvasWorkflowId}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onBack={() => {
          setCanvasWorkflowId(null);
          loadData();
        }}
      />
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      {/* ─── Header & Switcher ────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">Enterprise Automations</h1>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 text-xs py-0.5">
              Powered by Activepieces Engine
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Prompt-to-workflow automation intelligence with native OctaOS triggers, 400+ third-party connectors, and enterprise governance.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              if (workflows.length > 0) {
                setCanvasWorkflowId(workflows[0].id);
              } else {
                handleCreateNewVisualWorkflow();
              }
              setActiveTab('canvas');
            }}
            className="text-xs border-primary/30 text-primary hover:bg-primary/10 font-semibold shadow-xs"
          >
            <Layers className="h-3.5 w-3.5 mr-1" />
            Visual n8n Canvas
          </Button>

          {canBuild && (
            <Button
              size="sm"
              onClick={handleCreateNewVisualWorkflow}
              className="text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-sm"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              New Workflow
            </Button>
          )}

          {/* Tab Switcher */}
          <div className="flex items-center gap-1 bg-muted p-1 rounded-lg">
            <Button
              variant={activeTab === 'workflows' && !canvasWorkflowId ? 'default' : 'ghost'}
              size="sm"
              onClick={() => {
                setCanvasWorkflowId(null);
                setActiveTab('workflows');
              }}
              className="text-xs"
            >
              <GitFork className="h-3.5 w-3.5 mr-1.5" />
              Workflows
            </Button>
            <Button
              variant={activeTab === 'canvas' || !!canvasWorkflowId ? 'default' : 'ghost'}
              size="sm"
              onClick={() => {
                if (workflows.length > 0) {
                  setCanvasWorkflowId(workflows[0].id);
                } else {
                  handleCreateNewVisualWorkflow();
                }
                setActiveTab('canvas');
              }}
              className="text-xs font-semibold"
            >
              <Layers className="h-3.5 w-3.5 mr-1.5 text-primary" />
              Visual n8n Canvas
            </Button>
            <Button
              variant={activeTab === 'connections' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => {
                setCanvasWorkflowId(null);
                setActiveTab('connections');
              }}
              className="text-xs"
            >
              <KeyRound className="h-3.5 w-3.5 mr-1.5" />
              Connection Center
            </Button>
            <Button
              variant={activeTab === 'usage' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => {
                setCanvasWorkflowId(null);
                setActiveTab('usage');
              }}
              className="text-xs"
            >
              <BarChart3 className="h-3.5 w-3.5 mr-1.5" />
              Usage & Limits
            </Button>
          </div>
        </div>
    </div>

      {/* ─── Metric Cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-card/60 backdrop-blur-sm">
          <div className="text-xs font-medium text-muted-foreground">Active Workflows</div>
          <div className="text-2xl font-bold mt-1 text-foreground">
            {usage?.active_workflows ?? 0}
            <span className="text-xs font-normal text-muted-foreground ml-1">/ {usage?.workflow_limit ?? 50}</span>
          </div>
          <div className="text-[11px] text-emerald-500 mt-1 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> Tenant Isolated Environment
          </div>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur-sm">
          <div className="text-xs font-medium text-muted-foreground">Executions This Month</div>
          <div className="text-2xl font-bold mt-1 text-foreground">
            {usage?.executions_this_month ?? 0}
            <span className="text-xs font-normal text-muted-foreground ml-1">/ {usage?.execution_limit_monthly ?? 5000}</span>
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">Automatic retry & DLQ enabled</div>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur-sm">
          <div className="text-xs font-medium text-muted-foreground">Execution Success Rate</div>
          <div className="text-2xl font-bold mt-1 text-emerald-500">
            {usage?.success_rate ?? 100}%
          </div>
          <div className="text-[11px] text-muted-foreground mt-1">{usage?.failed_executions ?? 0} failed runs classified</div>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur-sm">
          <div className="text-xs font-medium text-muted-foreground">Automation Workspace</div>
          <div className="text-sm font-semibold mt-1 truncate text-foreground">
            {usage?.subdomain || 'tenant-isolated.flows.octaos.org'}
          </div>
          <div className="text-[11px] text-primary mt-1 flex items-center gap-1 font-mono">
            <ShieldCheck className="h-3 w-3" /> Zero-Credential Exposure
          </div>
        </Card>
      </div>

      {activeTab === 'workflows' && (
        <>
          {/* ─── Hero: AI Prompt-to-Workflow Synthesizer ───────────────────── */}
          <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-card to-background shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-md bg-primary/10 text-primary">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-base font-semibold">AI Automation Synthesizer</CardTitle>
                    <CardDescription className="text-xs">
                      Type your business objective in plain English. OctaOS AI will plan the steps, validate governance, and compile executable workflows.
                    </CardDescription>
                  </div>
                </div>
                <Select value={category} onValueChange={(val: any) => val && setCategory(val)}>
                  <SelectTrigger className="w-36 h-8 text-xs">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sales">Sales & Leads</SelectItem>
                    <SelectItem value="support">Customer Support</SelectItem>
                    <SelectItem value="marketing">Marketing</SelectItem>
                    <SelectItem value="operations">Operations</SelectItem>
                    <SelectItem value="executive">Executive & HITL</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {!canBuild && (
                <div className="flex items-center gap-2 p-2.5 rounded-md bg-muted/70 text-muted-foreground text-xs border">
                  <ShieldCheck className="h-4 w-4 text-primary shrink-0" />
                  <span>
                    <strong>View-Only Mode:</strong> You can inspect active workflows and execution telemetry. Only users with automation builder permissions (Admins, Managers) can open the visual canvas or synthesize new workflows.
                  </span>
                </div>
              )}
              <div className="flex gap-2">
                <Input
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  disabled={!canBuild || synthesizing}
                  placeholder={canBuild ? "e.g. When a lead is qualified in Sales, notify #sales-pipeline in Slack and create a HubSpot deal..." : "Builder permissions required to synthesize new workflows"}
                  className="flex-1 text-sm bg-background/80"
                  onKeyDown={(e) => e.key === 'Enter' && canBuild && handleSynthesize()}
                />
                <Button
                  onClick={handleSynthesize}
                  disabled={!canBuild || synthesizing || !prompt.trim()}
                  className="shrink-0"
                >
                  {synthesizing ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-1.5 animate-spin" />
                      Synthesizing...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 mr-1.5" />
                      Synthesize Flow
                    </>
                  )}
                </Button>
              </div>

              {/* Instant Template Quick-Picks */}
              <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
                <span className="text-muted-foreground mr-1 text-[11px] font-medium">Quick Templates:</span>
                <button
                  type="button"
                  onClick={() => setPrompt('When a qualified lead arrives, send a slack message and create a deal in hubspot')}
                  className="px-2 py-0.5 rounded-full bg-muted hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors text-[11px]"
                >
                  🎯 Qualified Lead → Slack & HubSpot
                </button>
                <button
                  type="button"
                  onClick={() => setPrompt('When a customer support ticket is marked urgent, alert engineers on Slack and run support agent diagnostic')}
                  className="px-2 py-0.5 rounded-full bg-muted hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors text-[11px]"
                >
                  🚨 P1 Support Escalation → Triage
                </button>
                <button
                  type="button"
                  onClick={() => setPrompt('When a deal is closed won, celebrate in Slack and append client row in Google Sheets')}
                  className="px-2 py-0.5 rounded-full bg-muted hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors text-[11px]"
                >
                  🎉 Deal Won → Celebration & Sheets
                </button>
                <button
                  type="button"
                  onClick={() => setPrompt('When a customer refund exceeds $1000, enforce executive HITL approval before dispatching')}
                  className="px-2 py-0.5 rounded-full bg-muted hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors text-[11px]"
                >
                  🛡️ Financial Refund Governance (HITL)
                </button>
              </div>
            </CardContent>
          </Card>

          {/* ─── Live AI Synthesis & Multi-Gate Governance Card ────────────── */}
          {synthesisResult && (
            <Card className="border-emerald-500/30 bg-emerald-500/5">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    <CardTitle className="text-sm font-semibold">
                      {synthesisResult.is_template_match ? 'Enterprise Blueprint Matched' : 'AI Synthesis Completed'}
                    </CardTitle>
                    <Badge variant="outline" className="text-xs bg-emerald-500/10 text-emerald-600 border-emerald-500/20">
                      {synthesisResult.definition_ir.name}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        synthesisResult.risk_level === 'high'
                          ? 'bg-rose-500/10 text-rose-600 border-rose-500/30'
                          : 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30'
                      }`}
                    >
                      Risk: {synthesisResult.risk_level.toUpperCase()}
                    </Badge>
                    {synthesisResult.requires_approval && (
                      <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/30 text-xs">
                        HITL Approval Required
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-xs text-muted-foreground">{synthesisResult.definition_ir.description}</p>

                {/* Multi-Gate Governance Pipeline Indicators */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  {synthesisResult.validation_gates?.map((gate: any) => (
                    <div key={gate.gate_name} className="flex items-center gap-1.5 p-2 rounded bg-background/60 border text-[11px]">
                      {gate.passed ? (
                        <Check className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-rose-500 shrink-0" />
                      )}
                      <span className="font-medium truncate">{gate.gate_name}</span>
                    </div>
                  ))}
                </div>

                {/* Workflow Step Flow Visualization */}
                <div className="p-3 rounded-lg bg-background border flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-primary/10 text-primary text-xs font-medium">
                    <Zap className="h-3.5 w-3.5" />
                    <span>{synthesisResult.definition_ir.trigger?.display_name || synthesisResult.definition_ir.trigger?.event}</span>
                  </div>

                  {synthesisResult.definition_ir.steps?.map((st: any, idx: number) => (
                    <React.Fragment key={st.id}>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-muted text-foreground text-xs font-medium">
                        <Layers className="h-3.5 w-3.5 text-muted-foreground" />
                        <span>{st.display_name || `${st.piece}: ${st.action}`}</span>
                      </div>
                    </React.Fragment>
                  ))}
                </div>

                {/* Action CTA */}
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="outline" size="sm" onClick={() => setSynthesisResult(null)}>
                    Dismiss
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => handleDeploySynthesized(false)}>
                    Save as Draft
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleDeploySynthesized(true)}
                    disabled={synthesisResult.requires_approval}
                  >
                    Deploy & Activate
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* ─── Active Workflows Table ───────────────────────────────────── */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-semibold">Configured Automations</CardTitle>
                <CardDescription className="text-xs">
                  Active business workflows executing across marketing, sales, support, and finance.
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={loadData} disabled={loading} className="text-xs">
                <RefreshCw className={`h-3.5 w-3.5 mr-1 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </CardHeader>
            <CardContent>
              {workflows.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground space-y-3">
                  <GitFork className="h-10 w-10 mx-auto text-muted-foreground/40 mb-2" />
                  <p className="text-sm font-medium">No automations configured yet</p>
                  <p className="text-xs mt-1">Use the AI Synthesizer above or launch the visual canvas to build your first workflow.</p>
                  <Button
                    size="sm"
                    onClick={handleCreateNewVisualWorkflow}
                    className="text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-sm"
                  >
                    <Layers className="h-3.5 w-3.5 mr-1.5" />
                    Open Visual n8n Canvas
                  </Button>
                </div>
              ) : (
                <div className="divide-y text-sm">
                  {workflows.map((wf) => (
                    <div key={wf.id} className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-foreground">{wf.name}</span>
                          <Badge
                            variant="outline"
                            className={`text-[10px] ${
                              wf.status === 'active'
                                ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                                : wf.status === 'paused'
                                ? 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                                : 'bg-muted text-muted-foreground'
                            }`}
                          >
                            {wf.status.toUpperCase()}
                          </Badge>
                          <Badge variant="outline" className="text-[10px] bg-primary/5 text-primary border-primary/20">
                            {wf.category}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{wf.description || 'No description provided'}</p>
                        <div className="flex items-center gap-3 text-[11px] text-muted-foreground pt-0.5">
                          <span>Trigger: <strong className="text-foreground">{wf.trigger_event || wf.trigger_type}</strong></span>
                          <span>•</span>
                          <span>Steps: <strong className="text-foreground">{wf.steps_count}</strong></span>
                          <span>•</span>
                          <span>Runs: <strong className="text-foreground">{wf.total_runs}</strong></span>
                          {wf.last_run_status && (
                            <>
                              <span>•</span>
                              <span className="flex items-center gap-1">
                                Last run:
                                <span className={wf.last_run_status === 'succeeded' ? 'text-emerald-500 font-medium' : 'text-rose-500 font-medium'}>
                                  {wf.last_run_status}
                                </span>
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-1.5 shrink-0">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setCanvasWorkflowId(wf.id);
                            setActiveTab('canvas');
                          }}
                          className="h-8 text-xs border-primary/30 text-primary hover:bg-primary/5 font-semibold"
                          title="Open Visual n8n Canvas"
                        >
                          <Layers className="h-3.5 w-3.5 mr-1 text-primary" />
                          Visual n8n Canvas
                        </Button>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setViewingStepsWorkflow(wf)}
                          className="h-8 text-xs text-muted-foreground hover:text-foreground"
                          title="View Workflow Step Details (Read-Only)"
                        >
                          <FileText className="h-3.5 w-3.5 mr-1" />
                          Steps
                        </Button>

                        {canBuild && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleTestRun(wf.id)}
                              className="h-8 text-xs"
                              title="Run manual test"
                            >
                              <Play className="h-3.5 w-3.5 text-muted-foreground" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleActive(wf.id, wf.status)}
                              className="h-8 text-xs"
                              title={wf.status === 'active' ? 'Pause workflow' : 'Activate workflow'}
                            >
                              {wf.status === 'active' ? (
                                <Pause className="h-3.5 w-3.5 text-amber-500" />
                              ) : (
                                <Play className="h-3.5 w-3.5 text-emerald-500" />
                              )}
                            </Button>
                          </>
                        )}

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewExecutions(wf)}
                          className="h-8 text-xs text-muted-foreground"
                          title="View Execution History & Diagnostics"
                        >
                          <Activity className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* ─── Connection Center Tab ────────────────────────────────────────── */}
      {activeTab === 'connections' && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Enterprise Connection Center</CardTitle>
            <CardDescription className="text-xs">
              Manage third-party SaaS connections and OAuth integrations safely. AI agents and workflows access connections by reference without seeing raw secrets.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {connections.map((c) => (
                <div key={c.piece_name} className="p-3.5 rounded-lg border bg-card/60 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm">{c.display_name}</span>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          c.status === 'connected'
                            ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {c.status.toUpperCase()}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {c.account_name ? `Linked: ${c.account_name}` : 'Not connected'}
                    </p>
                  </div>
                  <div className="mt-4 pt-2 border-t flex justify-end">
                    <Button variant="outline" size="sm" className="h-7 text-xs">
                      {c.status === 'connected' ? 'Manage' : 'Connect via OAuth'}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ─── Usage & Limits Tab ───────────────────────────────────────────── */}
      {activeTab === 'usage' && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Infrastructure & Usage Metering</CardTitle>
            <CardDescription className="text-xs">
              Real-time resource utilization for tenant-isolated automation runtime.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-muted/40 border space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Execution Engine:</span>
                <span className="font-semibold capitalize text-foreground">{usage?.engine || 'Activepieces'} (v1.0)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Isolated Subdomain:</span>
                <span className="font-mono text-primary">{usage?.subdomain}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Environment Status:</span>
                <span className="text-emerald-500 font-semibold uppercase">{usage?.status || 'Active'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Monthly Quota Consumption:</span>
                <span className="font-medium text-foreground">
                  {usage?.executions_this_month} / {usage?.execution_limit_monthly} executions ({Math.round(((usage?.executions_this_month || 0) / (usage?.execution_limit_monthly || 5000)) * 100)}%)
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ─── Visual Canvas Modal ──────────────────────────────────────────── */}
      <Dialog open={!!activeEditorUrl} onOpenChange={(open) => !open && setActiveEditorUrl(null)}>
        <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-4">
          <DialogHeader className="pb-2 border-b">
            <div className="flex items-center justify-between">
              <DialogTitle className="text-base font-semibold flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" />
                n8n Visual Workflow Canvas
              </DialogTitle>
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-7 mr-6"
                onClick={() => activeEditorUrl && window.open(activeEditorUrl, '_blank')}
              >
                <ExternalLink className="h-3 w-3 mr-1" />
                Open Fullscreen
              </Button>
            </div>
            <DialogDescription className="text-xs">
              Drag, reorder, and configure individual piece steps, triggers, and branches visually.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 w-full h-full rounded-md border overflow-hidden bg-background mt-2">
            {activeEditorUrl ? (
              <iframe
                src={activeEditorUrl}
                className="w-full h-full border-0"
                title="n8n Canvas Editor"
                allow="clipboard-read; clipboard-write"
              />
            ) : null}
          </div>
        </DialogContent>
      </Dialog>

      {/* ─── Execution Observability Drawer / Modal ──────────────────────── */}
      <Dialog
        open={!!selectedWorkflowForExecutions}
        onOpenChange={(open) => !open && setSelectedWorkflowForExecutions(null)}
      >
        <DialogContent className="max-w-3xl max-h-[80vh] flex flex-col p-4">
          <DialogHeader className="pb-2 border-b">
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              Execution Logs: {selectedWorkflowForExecutions?.name}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Observable run telemetry with classified failure root causes and payload tracing.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto space-y-2 mt-2">
            {loadingExecutions ? (
              <div className="text-center py-8 text-xs text-muted-foreground">Loading executions...</div>
            ) : executions.length === 0 ? (
              <div className="text-center py-8 text-xs text-muted-foreground">No execution records found for this workflow.</div>
            ) : (
              executions.map((ex) => (
                <div key={ex.id} className="p-3 rounded-lg border bg-muted/20 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-muted-foreground">{ex.id.slice(0, 8)}</span>
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${
                          ex.status === 'succeeded'
                            ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30'
                            : 'bg-rose-500/10 text-rose-600 border-rose-500/30'
                        }`}
                      >
                        {ex.status.toUpperCase()}
                      </Badge>
                      {ex.failure_classification && (
                        <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-600 border-amber-500/30">
                          {ex.failure_classification}
                        </Badge>
                      )}
                    </div>
                    <span className="text-[11px] text-muted-foreground">{ex.duration_ms}ms</span>
                  </div>

                  {ex.failure_reason && (
                    <div className="p-2 rounded bg-rose-500/10 text-rose-600 text-[11px] font-mono">
                      Error: {ex.failure_reason}
                    </div>
                  )}

                  <div className="text-[11px] text-muted-foreground">
                    Started: {ex.started_at ? new Date(ex.started_at).toLocaleString() : 'N/A'}
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* ─── View Steps Modal (Read-Only for non-builders) ───────────────── */}
      <Dialog
        open={!!viewingStepsWorkflow}
        onOpenChange={(open) => !open && setViewingStepsWorkflow(null)}
      >
        <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col p-4">
          <DialogHeader className="pb-2 border-b">
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              {viewingStepsWorkflow?.name}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Structured step definitions and trigger configuration (Read-Only).
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto space-y-3 mt-2 text-xs">
            <div className="p-3 rounded-lg border bg-primary/5 space-y-1">
              <div className="font-semibold text-primary flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5" />
                Trigger: {viewingStepsWorkflow?.trigger_event || viewingStepsWorkflow?.trigger_type}
              </div>
              <p className="text-muted-foreground text-[11px]">{viewingStepsWorkflow?.description}</p>
            </div>

            <div className="space-y-2">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Configured Actions</span>
              {viewingStepsWorkflow?.definition_ir?.steps?.map((step: any, idx: number) => (
                <div key={step.id || idx} className="p-3 rounded-lg border bg-muted/20 space-y-1">
                  <div className="font-medium text-foreground flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <span className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[10px] text-muted-foreground font-mono">
                        {idx + 1}
                      </span>
                      {step.display_name || `${step.piece}: ${step.action}`}
                    </span>
                    <Badge variant="outline" className="text-[10px] capitalize">
                      {step.piece}
                    </Badge>
                  </div>
                  {step.parameters && Object.keys(step.parameters).length > 0 && (
                    <pre className="p-2 rounded bg-muted/40 font-mono text-[10px] overflow-x-auto text-muted-foreground">
                      {JSON.stringify(step.parameters, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

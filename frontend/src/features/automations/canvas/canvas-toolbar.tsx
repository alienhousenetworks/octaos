'use client';

import React, { useState } from 'react';
import {
  Save,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  RotateCw,
  ArrowLeft,
  Upload,
  RefreshCw,
  GitFork,
  XCircle,
  FileText,
  Bot,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useWorkflowEditorStore } from '../state/workflow-editor-store';
import { notify } from '@/lib/notify';

interface CanvasToolbarProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onBack: () => void;
  workflowId: string;
}

export function WorkflowCanvasToolbar({
  API_URL,
  fetchWithAuth,
  onBack,
  workflowId,
}: CanvasToolbarProps) {
  const graph = useWorkflowEditorStore((s) => s.graph);
  const isDirty = useWorkflowEditorStore((s) => s.isDirty);
  const isSaving = useWorkflowEditorStore((s) => s.isSaving);
  const setIsSaving = useWorkflowEditorStore((s) => s.setIsSaving);
  const exportGraph = useWorkflowEditorStore((s) => s.exportGraph);
  const setValidation = useWorkflowEditorStore((s) => s.setValidation);
  const validation = useWorkflowEditorStore((s) => s.validation);
  const activeMode = useWorkflowEditorStore((s) => s.activeMode);
  const setActiveMode = useWorkflowEditorStore((s) => s.setActiveMode);

  const undo = useWorkflowEditorStore((s) => s.undo);
  const redo = useWorkflowEditorStore((s) => s.redo);
  const canUndo = useWorkflowEditorStore((s) => s.undoStack.length > 0);
  const canRedo = useWorkflowEditorStore((s) => s.redoStack.length > 0);

  const [publishing, setPublishing] = useState(false);
  const [testing, setTesting] = useState(false);

  // Save graph draft
  const handleSaveDraft = async () => {
    const currentGraph = exportGraph();
    if (!currentGraph) return;

    setIsSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/graph`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentGraph),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to save workflow graph draft');
        return;
      }

      const data = await res.json();
      setValidation(data.validation);
      notify('Workflow graph draft saved successfully.');
    } catch (e: any) {
      notify('Error saving draft: ' + e.message);
    } finally {
      setIsSaving(false);
    }
  };

  // Run validation check
  const handleValidate = async () => {
    const currentGraph = exportGraph();
    if (!currentGraph) return;

    try {
      const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentGraph),
      });

      if (res.ok) {
        const data = await res.json();
        setValidation(data);
        if (data.is_valid) {
          notify(`Graph topology valid: ${data.topology_stats.total_nodes} nodes, ${data.topology_stats.total_edges} connections.`);
        } else {
          notify(`Validation warnings: ${data.errors.join('; ')}`);
        }
      }
    } catch (e: any) {
      notify('Validation check failed: ' + e.message);
    }
  };

  // Publish to production
  const handlePublish = async () => {
    setPublishing(true);
    try {
      // Auto-save first
      await handleSaveDraft();

      const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Publishing failed');
        return;
      }

      const data = await res.json();
      notify(`Workflow published to v${data.published_version} (Active in production)`);
    } catch (e: any) {
      notify('Publish error: ' + e.message);
    } finally {
      setPublishing(false);
    }
  };

  // Test Run
  const handleTestRun = async () => {
    setTesting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: { test_run: true, source: 'Visual Canvas Toolbar' } }),
      });

      if (res.ok) {
        notify('Test run initiated! Telemetry recorded.');
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Test execution failed');
      }
    } catch (e: any) {
      notify('Test run failed: ' + e.message);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="h-14 border-b bg-card/80 backdrop-blur-md px-4 flex items-center justify-between gap-4 select-none">
      {/* Left: Back & Title */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack} className="h-8 text-xs text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3.5 w-3.5 mr-1" />
          Workflows
        </Button>

        <div className="h-4 w-px bg-border" />

        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-primary/10 text-primary">
            <GitFork className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-foreground tracking-tight">{graph?.name || 'Workflow Canvas'}</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20">
                Visual n8n Canvas
              </span>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-muted border text-muted-foreground">
                v{graph?.version || 1}
              </span>
              {isDirty && (
                <span className="text-[10px] text-amber-500 font-medium animate-pulse">● Unsaved edits</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Center: Mode Switcher & Validation */}
      <div className="flex items-center gap-3">
        {/* Segmented Mode Control */}
        <div className="flex items-center p-1 bg-muted/60 border rounded-lg gap-0.5 text-xs">
          <button
            onClick={() => setActiveMode('general')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all font-medium ${
              activeMode === 'general'
                ? 'bg-card text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">General Flow</span>
          </button>

          <button
            onClick={() => setActiveMode('document')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all font-medium ${
              activeMode === 'document'
                ? 'bg-card text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <FileText className="h-3.5 w-3.5 text-blue-500" />
            <span className="hidden sm:inline">Document Hub</span>
          </button>

          <button
            onClick={() => setActiveMode('ai_agent')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all font-medium ${
              activeMode === 'ai_agent'
                ? 'bg-card text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Bot className="h-3.5 w-3.5 text-purple-500" />
            <span className="hidden sm:inline">AI Agents</span>
          </button>
        </div>

        {/* Validation Status */}
        <div className="hidden lg:flex items-center gap-2 text-xs">
          {validation ? (
            validation.is_valid ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[11px] border border-emerald-500/30">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Valid ({validation.topology_stats?.total_nodes || 0} nodes)</span>
              </div>
            ) : (
              <div
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-500 text-[11px] border border-rose-500/30 cursor-pointer"
                title={validation.errors.join('; ')}
              >
                <XCircle className="h-3.5 w-3.5" />
                <span>{validation.errors.length} issue(s)</span>
              </div>
            )
          ) : null}
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-1.5">
        <Button
          variant="ghost"
          size="sm"
          onClick={undo}
          disabled={!canUndo}
          className="h-8 w-8 p-0"
          title="Undo (Ctrl+Z)"
        >
          <RotateCcw className="h-3.5 w-3.5 text-muted-foreground" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={redo}
          disabled={!canRedo}
          className="h-8 w-8 p-0"
          title="Redo (Ctrl+Y)"
        >
          <RotateCw className="h-3.5 w-3.5 text-muted-foreground" />
        </Button>

        <div className="h-4 w-px bg-border" />

        <Button
          variant="outline"
          size="sm"
          onClick={handleValidate}
          className="h-8 text-xs text-muted-foreground hover:text-foreground"
        >
          Validate
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={handleSaveDraft}
          disabled={isSaving}
          className="h-8 text-xs"
        >
          {isSaving ? <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Save className="h-3.5 w-3.5 mr-1" />}
          Save Draft
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={handleTestRun}
          disabled={testing}
          className="h-8 text-xs text-primary border-primary/30 hover:bg-primary/5"
        >
          {testing ? <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Play className="h-3.5 w-3.5 mr-1 text-primary" />}
          Test
        </Button>

        <Button
          size="sm"
          onClick={handlePublish}
          disabled={publishing}
          className="h-8 text-xs font-semibold"
        >
          {publishing ? <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Upload className="h-3.5 w-3.5 mr-1" />}
          Publish
        </Button>
      </div>
    </div>
  );
}

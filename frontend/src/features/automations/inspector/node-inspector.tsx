'use client';

import React, { useState } from 'react';
import {
  X,
  Trash2,
  Sliders,
  ShieldAlert,
  Clock,
  Layers,
  Sparkles,
  Plus,
  Play,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useWorkflowEditorStore } from '../state/workflow-editor-store';
import type { AutomationNode } from '../types';

export function WorkflowNodeInspector() {
  const selectedNodeId = useWorkflowEditorStore((s) => s.selectedNodeId);
  const nodes = useWorkflowEditorStore((s) => s.nodes);
  const selectNode = useWorkflowEditorStore((s) => s.selectNode);
  const updateNode = useWorkflowEditorStore((s) => s.updateNode);
  const deleteNode = useWorkflowEditorStore((s) => s.deleteNode);

  const [activeTab, setActiveTab] = useState<'params' | 'execution'>('params');

  if (!selectedNodeId) return null;

  const targetFlowNode = nodes.find((n) => n.id === selectedNodeId);
  if (!targetFlowNode) return null;

  const node = targetFlowNode.data as unknown as AutomationNode;

  const handleNameChange = (val: string) => {
    updateNode(selectedNodeId, { name: val });
  };

  const handleDescChange = (val: string) => {
    updateNode(selectedNodeId, { description: val });
  };

  const handleParamChange = (key: string, val: any) => {
    const updatedConfig = { ...(node.config || {}), [key]: val };
    updateNode(selectedNodeId, { config: updatedConfig });
  };

  const handleAddParam = () => {
    const newKey = `param_${Date.now().toString().slice(-4)}`;
    handleParamChange(newKey, '');
  };

  const handleDeleteParam = (key: string) => {
    const updatedConfig = { ...(node.config || {}) };
    delete updatedConfig[key];
    updateNode(selectedNodeId, { config: updatedConfig });
  };

  const handleTimeoutChange = (seconds: number) => {
    updateNode(selectedNodeId, { timeout_seconds: seconds });
  };

  const handleApprovalToggle = () => {
    updateNode(selectedNodeId, { requires_approval: !node.requires_approval });
  };

  return (
    <div className="w-80 border-l bg-card/70 backdrop-blur-md flex flex-col h-full text-xs select-none">
      {/* Header */}
      <div className="p-3 border-b flex items-center justify-between">
        <div className="flex items-center gap-2 truncate">
          <Sliders className="h-4 w-4 text-primary shrink-0" />
          <div className="truncate">
            <h3 className="font-semibold text-foreground truncate">{node.name}</h3>
            <p className="text-[10px] text-muted-foreground font-mono truncate">{node.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => deleteNode(selectedNodeId)}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-rose-500"
            title="Delete Node"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => selectNode(null)}
            className="h-7 w-7 p-0 text-muted-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b bg-muted/30">
        <button
          onClick={() => setActiveTab('params')}
          className={`flex-1 py-2 text-center text-[11px] font-medium border-b-2 transition-colors ${
            activeTab === 'params'
              ? 'border-primary text-primary bg-background/50'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Parameters
        </button>
        <button
          onClick={() => setActiveTab('execution')}
          className={`flex-1 py-2 text-center text-[11px] font-medium border-b-2 transition-colors ${
            activeTab === 'execution'
              ? 'border-primary text-primary bg-background/50'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Execution & Safety
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {activeTab === 'params' && (
          <>
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground">Node Label</label>
              <Input
                value={node.name}
                onChange={(e) => handleNameChange(e.target.value)}
                className="h-8 text-xs bg-background/80"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground">Description</label>
              <Input
                value={node.description || ''}
                onChange={(e) => handleDescChange(e.target.value)}
                placeholder="What this step does..."
                className="h-8 text-xs bg-background/80"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-medium text-muted-foreground">Tool Identifier</label>
              <div className="p-2 rounded bg-muted/50 border font-mono text-[10px] text-muted-foreground break-all">
                {node.tool_id || node.type}
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-foreground">Config Parameters</span>
                <Button variant="outline" size="sm" onClick={handleAddParam} className="h-6 text-[10px] px-2">
                  <Plus className="h-3 w-3 mr-1" /> Add
                </Button>
              </div>

              {Object.keys(node.config || {}).length === 0 ? (
                <p className="text-[11px] text-muted-foreground italic py-2">No parameters configured.</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(node.config || {}).map(([key, val]) => (
                    <div key={key} className="space-y-1 p-2 rounded border bg-background/60">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] font-medium text-primary">{key}</span>
                        <button
                          onClick={() => handleDeleteParam(key)}
                          className="text-muted-foreground hover:text-rose-500"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </div>
                      <Input
                        value={typeof val === 'object' ? JSON.stringify(val) : String(val ?? '')}
                        onChange={(e) => handleParamChange(key, e.target.value)}
                        className="h-7 text-[11px] bg-background"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'execution' && (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[11px] font-medium text-muted-foreground flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                Execution Timeout (Seconds)
              </label>
              <Input
                type="number"
                value={node.timeout_seconds || 120}
                onChange={(e) => handleTimeoutChange(parseInt(e.target.value) || 60)}
                className="h-8 text-xs bg-background/80"
              />
            </div>

            <div className="p-3 rounded-lg border bg-muted/20 space-y-2">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <span className="font-medium text-foreground flex items-center gap-1.5">
                    <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                    Human-In-The-Loop Approval
                  </span>
                  <p className="text-[10px] text-muted-foreground">
                    Requires executive sign-off in Boardroom before dispatching.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={!!node.requires_approval}
                  onChange={handleApprovalToggle}
                  className="rounded border-muted-foreground h-4 w-4 text-primary focus:ring-primary"
                />
              </div>
            </div>

            <div className="p-2.5 rounded bg-muted/40 border text-[11px] text-muted-foreground">
              <strong>Dependency Reuse:</strong> This step will automatically reuse output from previous runs if upstream inputs and configurations have not changed.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

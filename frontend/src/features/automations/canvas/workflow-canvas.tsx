'use client';

import React, { useEffect, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { CustomWorkflowNode } from './custom-node';
import { WorkflowNodePalette } from './node-palette';
import { WorkflowNodeInspector } from '../inspector/node-inspector';
import { WorkflowCanvasToolbar } from './canvas-toolbar';
import { DocumentIntelligencePanel } from '../documents/document-mode';
import { useWorkflowEditorStore } from '../state/workflow-editor-store';
import { notify } from '@/lib/notify';

interface WorkflowCanvasProps {
  workflowId: string;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onBack: () => void;
}

export default function WorkflowCanvas({
  workflowId,
  API_URL,
  fetchWithAuth,
  onBack,
}: WorkflowCanvasProps) {
  const nodes = useWorkflowEditorStore((s) => s.nodes);
  const edges = useWorkflowEditorStore((s) => s.edges);
  const onNodesChange = useWorkflowEditorStore((s) => s.onNodesChange);
  const onEdgesChange = useWorkflowEditorStore((s) => s.onEdgesChange);
  const onConnect = useWorkflowEditorStore((s) => s.onConnect);
  const setGraph = useWorkflowEditorStore((s) => s.setGraph);
  const selectNode = useWorkflowEditorStore((s) => s.selectNode);
  const selectedNodeId = useWorkflowEditorStore((s) => s.selectedNodeId);
  const setValidation = useWorkflowEditorStore((s) => s.setValidation);
  const activeMode = useWorkflowEditorStore((s) => s.activeMode);

  const nodeTypes = useMemo(() => ({ custom: CustomWorkflowNode }), []);

  // Fetch initial graph
  useEffect(() => {
    let cancelled = false;
    const loadGraph = async () => {
      try {
        const res = await fetchWithAuth(`${API_URL}/automations/${workflowId}/graph`);
        if (!res.ok) {
          notify('Failed to load workflow graph');
          return;
        }
        const data = await res.json();
        if (!cancelled && data.graph) {
          setGraph(data.graph);
          if (data.validation) {
            setValidation(data.validation);
          }
        }
      } catch (e: any) {
        if (!cancelled) notify('Error loading graph: ' + e.message);
      }
    };
    loadGraph();
    return () => {
      cancelled = true;
    };
  }, [workflowId, API_URL, fetchWithAuth, setGraph, setValidation]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
      {/* Top Bar */}
      <WorkflowCanvasToolbar
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onBack={onBack}
        workflowId={workflowId}
      />

      {/* Main Workspace */}
      <div className="flex flex-1 w-full h-full overflow-hidden relative">
        {/* Left Palette */}
        <WorkflowNodePalette API_URL={API_URL} />

        {/* Central React Flow Canvas */}
        <div className="flex-1 h-full w-full relative bg-neutral-950/40">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.2}
            maxZoom={2.0}
            defaultEdgeOptions={{
              type: 'smoothstep',
              style: { strokeWidth: 2, stroke: 'var(--color-primary, #365bd6)' },
            }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={16}
              size={1}
              color="rgba(255, 255, 255, 0.08)"
            />
            <Controls className="!bg-card !border !border-border !rounded-lg !shadow-md !text-foreground" />
            <MiniMap
              className="!bg-card/80 !border !border-border !rounded-lg"
              nodeColor={() => 'var(--color-primary, #365bd6)'}
              maskColor="rgba(0, 0, 0, 0.6)"
            />
          </ReactFlow>
        </div>

        {/* Side-by-side Document Intelligence Panel in Document Mode */}
        {activeMode === 'document' && (
          <DocumentIntelligencePanel
            API_URL={API_URL}
            fetchWithAuth={fetchWithAuth}
          />
        )}

        {/* Right Inspector (shown when a node is selected and not in document mode, or floating) */}
        {selectedNodeId && activeMode !== 'document' && <WorkflowNodeInspector />}
      </div>
    </div>
  );
}

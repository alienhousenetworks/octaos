import { create } from 'zustand';
import {
  applyNodeChanges,
  applyEdgeChanges,
  type Node,
  type Edge,
  type NodeChange,
  type EdgeChange,
  type Connection,
} from '@xyflow/react';
import type {
  AutomationGraph,
  AutomationNode,
  AutomationEdge,
  GraphValidationResult,
  CanvasMode,
  DocumentExtractionResult,
  DocumentValidationResult,
  DocumentLifecycleState,
} from '../types';

interface HistoryState {
  nodes: Node[];
  edges: Edge[];
}

interface WorkflowEditorState {
  graph: AutomationGraph | null;
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  isDirty: boolean;
  isSaving: boolean;
  validation: GraphValidationResult | null;
  undoStack: HistoryState[];
  redoStack: HistoryState[];

  // Mode Switching
  activeMode: CanvasMode;
  setActiveMode: (mode: CanvasMode) => void;

  // Document Intelligence Workspace State
  selectedDocument: DocumentExtractionResult | null;
  extractedFields: Record<string, any>;
  targetSchema: Record<string, any>;
  validationReport: DocumentValidationResult | null;
  lifecycleState: DocumentLifecycleState;
  setSelectedDocument: (doc: DocumentExtractionResult | null) => void;
  setExtractedFields: (fields: Record<string, any>) => void;
  setTargetSchema: (schema: Record<string, any>) => void;
  setValidationReport: (report: DocumentValidationResult | null) => void;
  setLifecycleState: (state: DocumentLifecycleState) => void;

  // Graph synchronization
  setGraph: (graph: AutomationGraph) => void;
  exportGraph: () => AutomationGraph | null;
  setValidation: (val: GraphValidationResult | null) => void;
  setIsSaving: (saving: boolean) => void;

  // Selection
  selectNode: (id: string | null) => void;

  // React Flow Handlers
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;

  // Node operations
  addNode: (nodeData: Partial<AutomationNode>, position?: { x: number; y: number }) => void;
  updateNode: (nodeId: string, updates: Partial<AutomationNode>) => void;
  deleteNode: (nodeId: string) => void;
  deleteEdge: (edgeId: string) => void;

  // History
  undo: () => void;
  redo: () => void;
}

const mapAutomationNodesToFlowNodes = (nodes: AutomationNode[]): Node[] => {
  return nodes.map((n) => ({
    id: n.id,
    type: 'custom',
    position: { x: n.position.x || 0, y: n.position.y || 0 },
    data: { ...n } as unknown as Record<string, unknown>,
  }));
};

const mapAutomationEdgesToFlowEdges = (edges: AutomationEdge[]): Edge[] => {
  return edges.map((e) => ({
    id: e.id,
    source: e.source,
    sourceHandle: e.source_handle || 'output',
    target: e.target,
    targetHandle: e.target_handle || 'input',
    animated: e.kind === 'trigger' || e.kind === 'branch',
    data: { kind: e.kind, condition: e.condition },
  }));
};

export const useWorkflowEditorStore = create<WorkflowEditorState>((set, get) => ({
  graph: null,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  isDirty: false,
  isSaving: false,
  validation: null,
  undoStack: [],
  redoStack: [],

  // Mode
  activeMode: 'general',
  setActiveMode: (activeMode) => set({ activeMode }),

  // Document Intelligence
  selectedDocument: null,
  extractedFields: {},
  targetSchema: {
    type: 'object',
    properties: {
      document_type: { type: 'string', description: 'e.g. invoice, resume, contract, nda' },
      counterparty_name: { type: 'string', description: 'Name of the company or individual' },
      total_amount: { type: 'number', description: 'Numeric total or salary' },
      effective_date: { type: 'string', description: 'YYYY-MM-DD format' },
      expiration_date: { type: 'string', description: 'YYYY-MM-DD format' },
    },
    required: ['document_type', 'counterparty_name'],
  },
  validationReport: null,
  lifecycleState: 'SUBMITTED',
  setSelectedDocument: (selectedDocument) => set({ selectedDocument }),
  setExtractedFields: (extractedFields) => set({ extractedFields, isDirty: true }),
  setTargetSchema: (targetSchema) => set({ targetSchema, isDirty: true }),
  setValidationReport: (validationReport) => set({ validationReport }),
  setLifecycleState: (lifecycleState) => set({ lifecycleState, isDirty: true }),

  setGraph: (graph) => {
    const flowNodes = mapAutomationNodesToFlowNodes(graph.nodes);
    const flowEdges = mapAutomationEdgesToFlowEdges(graph.edges);
    set({
      graph,
      nodes: flowNodes,
      edges: flowEdges,
      selectedNodeId: null,
      isDirty: false,
      undoStack: [],
      redoStack: [],
    });
  },

  exportGraph: () => {
    const { graph, nodes, edges } = get();
    if (!graph) return null;

    const updatedNodes: AutomationNode[] = nodes.map((n) => {
      const existingData = n.data as unknown as AutomationNode;
      return {
        ...existingData,
        id: n.id,
        position: { x: n.position.x, y: n.position.y },
      };
    });

    const updatedEdges: AutomationEdge[] = edges.map((e) => ({
      id: e.id,
      source: e.source,
      source_handle: e.sourceHandle || 'output',
      target: e.target,
      target_handle: e.targetHandle || 'input',
      kind: (e.data?.kind as any) || 'data',
      condition: e.data?.condition as Record<string, any> | undefined,
    }));

    return {
      ...graph,
      nodes: updatedNodes,
      edges: updatedEdges,
    };
  },

  setValidation: (validation) => set({ validation }),
  setIsSaving: (isSaving) => set({ isSaving }),

  selectNode: (selectedNodeId) => set({ selectedNodeId }),

  onNodesChange: (changes) => {
    const currentNodes = get().nodes;
    const nextNodes = applyNodeChanges(changes, currentNodes);
    set({ nodes: nextNodes, isDirty: true });
  },

  onEdgesChange: (changes) => {
    const currentEdges = get().edges;
    const nextEdges = applyEdgeChanges(changes, currentEdges);
    set({ edges: nextEdges, isDirty: true });
  },

  onConnect: (connection) => {
    if (!connection.source || !connection.target) return;
    const { edges, undoStack, nodes } = get();

    // Push to undo stack
    const newUndo = [...undoStack, { nodes, edges }].slice(-25);

    const newEdgeId = `edge_${connection.source}_${connection.sourceHandle || 'output'}_to_${connection.target}`;
    const newEdge: Edge = {
      id: newEdgeId,
      source: connection.source,
      sourceHandle: connection.sourceHandle || 'output',
      target: connection.target,
      targetHandle: connection.targetHandle || 'input',
      animated: true,
      data: {
        kind: connection.sourceHandle === 'true' || connection.sourceHandle === 'false' ? 'branch' : 'data',
      },
    };

    set({
      edges: [...edges, newEdge],
      isDirty: true,
      undoStack: newUndo,
      redoStack: [],
    });
  },

  addNode: (nodeData, position) => {
    const { nodes, edges, undoStack } = get();
    const id = nodeData.id || `node_${Date.now()}`;
    const pos = position || { x: 300 + Math.random() * 50, y: 200 + Math.random() * 50 };

    const completeNode: AutomationNode = {
      id,
      type: nodeData.type || 'action',
      name: nodeData.name || 'New Step',
      version: '1.0.0',
      position: pos,
      tool_id: nodeData.tool_id || 'octaos:custom',
      config: nodeData.config || {},
      input_mappings: nodeData.input_mappings || {},
      credential_refs: nodeData.credential_refs || [],
      timeout_seconds: nodeData.timeout_seconds || 120,
      is_compensable: nodeData.is_compensable || false,
      requires_approval: nodeData.requires_approval || false,
      display_icon: nodeData.display_icon || 'Zap',
      description: nodeData.description || '',
    };

    const newFlowNode: Node = {
      id,
      type: 'custom',
      position: pos,
      data: completeNode as unknown as Record<string, unknown>,
    };

    set({
      nodes: [...nodes, newFlowNode],
      selectedNodeId: id,
      isDirty: true,
      undoStack: [...undoStack, { nodes, edges }].slice(-25),
      redoStack: [],
    });
  },

  updateNode: (nodeId, updates) => {
    const { nodes, edges, undoStack } = get();
    const newUndo = [...undoStack, { nodes, edges }].slice(-25);

    const nextNodes = nodes.map((n) => {
      if (n.id !== nodeId) return n;
      const currentData = n.data as unknown as AutomationNode;
      return {
        ...n,
        data: {
          ...currentData,
          ...updates,
        } as unknown as Record<string, unknown>,
      };
    });

    set({
      nodes: nextNodes,
      isDirty: true,
      undoStack: newUndo,
      redoStack: [],
    });
  },

  deleteNode: (nodeId) => {
    const { nodes, edges, undoStack } = get();
    const newUndo = [...undoStack, { nodes, edges }].slice(-25);

    const nextNodes = nodes.filter((n) => n.id !== nodeId);
    const nextEdges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);

    set({
      nodes: nextNodes,
      edges: nextEdges,
      selectedNodeId: null,
      isDirty: true,
      undoStack: newUndo,
      redoStack: [],
    });
  },

  deleteEdge: (edgeId) => {
    const { nodes, edges, undoStack } = get();
    const newUndo = [...undoStack, { nodes, edges }].slice(-25);
    const nextEdges = edges.filter((e) => e.id !== edgeId);

    set({
      edges: nextEdges,
      isDirty: true,
      undoStack: newUndo,
      redoStack: [],
    });
  },

  undo: () => {
    const { undoStack, redoStack, nodes, edges } = get();
    if (undoStack.length === 0) return;

    const previous = undoStack[undoStack.length - 1];
    const newUndo = undoStack.slice(0, -1);
    const newRedo = [...redoStack, { nodes, edges }];

    set({
      nodes: previous.nodes,
      edges: previous.edges,
      undoStack: newUndo,
      redoStack: newRedo,
      isDirty: true,
    });
  },

  redo: () => {
    const { undoStack, redoStack, nodes, edges } = get();
    if (redoStack.length === 0) return;

    const next = redoStack[redoStack.length - 1];
    const newRedo = redoStack.slice(0, -1);
    const newUndo = [...undoStack, { nodes, edges }];

    set({
      nodes: next.nodes,
      edges: next.edges,
      undoStack: newUndo,
      redoStack: newRedo,
      isDirty: true,
    });
  },
}));

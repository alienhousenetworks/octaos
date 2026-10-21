'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';
import {
  Play,
  FileText,
  Upload,
  UploadCloud,
  Sparkles,
  Mail,
  CheckSquare,
  GitBranch,
  Eye,
  ShieldCheck,
  Clock,
  Bell,
  PenTool,
  Archive,
  CheckCircle2,
  Plus,
  Trash2,
  Copy,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  RotateCcw,
  Undo2,
  Redo2,
  Save,
  Check,
  X,
  Search,
  SlidersHorizontal,
  ChevronRight,
  ChevronDown,
  Layers,
  ArrowRight,
  ArrowUp,
  ArrowDown,
  Wand2,
  Edit2,
  Loader2,
  Move,
  HelpCircle,
  AlertTriangle,
  FolderDown,
} from 'lucide-react';

export interface CanvasNode {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  config: Record<string, any>;
}

export interface CanvasEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

interface PublishedTemplate {
  id: string;
  name: string;
  category: string;
  format: string;
  latest_version: number;
}

interface HRPipelineCanvasProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  availableTemplates?: PublishedTemplate[];
  initialDefinitionId?: string;
  onPipelinePublished?: (definition: any) => void;
  openAiPromptOnMount?: boolean;
  onImportClick?: () => void;
}

// 15 Standard Node Types Metadata
export const NODE_PALETTE_CATEGORIES = [
  {
    category: 'Triggers',
    items: [
      {
        type: 'start',
        label: 'Start / Trigger',
        desc: 'Manual start or event on candidate creation',
        icon: Play,
        color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
        badgeColor: 'bg-emerald-500/20 text-emerald-300',
        defaultConfig: { trigger_type: 'manual', auto_start_on_candidate_creation: true },
      },
    ],
  },
  {
    category: 'Documents & Templates',
    items: [
      {
        type: 'generate_document',
        label: 'Generate Document',
        desc: 'Selected template, field mappings & AI fill instructions',
        icon: FileText,
        color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
        badgeColor: 'bg-amber-500/20 text-amber-300',
        defaultConfig: {
          template_id: '',
          template_name: 'Standard Offer Letter',
          ai_fill_instructions:
            'Populate the selected template using verified candidate evidence and authorized company records. Preserve original document structure and legal clauses. Do not invent missing values.',
          data_sources: ['candidate_form', 'uploaded_evidence', 'hr_records', 'company_settings'],
          output_format: 'both',
          missing_data_policy: 'route_to_hr',
        },
      },
      {
        type: 'upload_template',
        label: 'Upload Template',
        desc: 'Upload or select reusable DOCX/HTML template',
        icon: Upload,
        color: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
        badgeColor: 'bg-amber-500/15 text-amber-300',
        defaultConfig: { template_category: 'onboarding', allowed_formats: ['docx', 'html'] },
      },
    ],
  },
  {
    category: 'Candidate Interaction',
    items: [
      {
        type: 'candidate_upload',
        label: 'Candidate Document Upload',
        desc: 'Request evidence (passport, tax form, ID)',
        icon: UploadCloud,
        color: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
        badgeColor: 'bg-sky-500/20 text-sky-300',
        defaultConfig: {
          required_documents: ['Government Photo ID', 'PAN Card / Tax ID', 'Address Proof'],
          allowed_formats: ['application/pdf', 'image/jpeg', 'image/png'],
          max_file_size_mb: 15,
          deadline_days: 5,
        },
      },
      {
        type: 'ai_form_generator',
        label: 'AI Form Generator',
        desc: 'Detect questions from templates without duplication',
        icon: Sparkles,
        color: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
        badgeColor: 'bg-purple-500/20 text-purple-300',
        defaultConfig: {
          deduplicate_fields: true,
          intake_fields: ['candidate.full_name', 'candidate.email', 'candidate.phone', 'candidate.current_address'],
          sensitive_check_required: true,
        },
      },
      {
        type: 'candidate_email',
        label: 'Candidate Email',
        desc: 'Send secure form link & upload instructions',
        icon: Mail,
        color: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
        badgeColor: 'bg-blue-500/20 text-blue-300',
        defaultConfig: {
          recipient_type: 'candidate',
          subject: 'Complete your onboarding documentation with OctaCorp',
          email_template:
            'Hello {{ candidate.name }},\n\nPlease review and complete your onboarding documentation by visiting your secure portal:\n{{ candidate_portal_url }}\n\nBest regards,\nHR Team',
          include_portal_link: true,
        },
      },
    ],
  },
  {
    category: 'Extraction & Logic',
    items: [
      {
        type: 'extract_validate',
        label: 'Extract & Validate',
        desc: 'OCR evidence extraction & conflict detection',
        icon: CheckSquare,
        color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
        badgeColor: 'bg-cyan-500/20 text-cyan-300',
        defaultConfig: {
          ocr_engine: 'rapidocr',
          confidence_threshold: 0.85,
          flag_conflicts_to_hr: true,
        },
      },
      {
        type: 'condition_branch',
        label: 'Condition / Branch',
        desc: 'Route based on role, department or attributes',
        icon: GitBranch,
        color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
        badgeColor: 'bg-amber-500/20 text-amber-300',
        defaultConfig: {
          branch_attribute: 'employment_type',
          default_branch: 'permanent',
        },
      },
    ],
  },
  {
    category: 'Review & Governance',
    items: [
      {
        type: 'hr_review',
        label: 'HR Review',
        desc: 'Inspect, edit, and request draft changes',
        icon: Eye,
        color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
        badgeColor: 'bg-indigo-500/20 text-indigo-300',
        defaultConfig: {
          reviewer_role: 'hr_specialist',
          editable_fields: ['compensation.annual_ctc', 'role.start_date'],
          invalidate_prior_approvals_on_edit: true,
        },
      },
      {
        type: 'approval',
        label: 'Approval Gate',
        desc: 'Authorized sign-off strictly bound to SHA-256',
        icon: ShieldCheck,
        color: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
        badgeColor: 'bg-rose-500/20 text-rose-300',
        defaultConfig: {
          required_role: 'hr_director',
          approval_policy: 'strict_sha_binding',
          escalation_hours: 48,
        },
      },
      {
        type: 'signature',
        label: 'Signature Integration',
        desc: 'Initiate and track electronic signature flow',
        icon: PenTool,
        color: 'text-teal-400 bg-teal-500/10 border-teal-500/30',
        badgeColor: 'bg-teal-500/20 text-teal-300',
        defaultConfig: {
          provider: 'internal_octaos',
          signer_order: ['candidate', 'company_signatory'],
        },
      },
    ],
  },
  {
    category: 'Automation & Completion',
    items: [
      {
        type: 'wait_schedule',
        label: 'Wait / Schedule',
        desc: 'Pause until date, interval or timezone release',
        icon: Clock,
        color: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
        badgeColor: 'bg-orange-500/20 text-orange-300',
        defaultConfig: {
          wait_type: 'interval',
          wait_hours: 24,
          timezone: 'Asia/Kolkata',
        },
      },
      {
        type: 'notification',
        label: 'Notification',
        desc: 'Notify recruiter, hiring manager or team',
        icon: Bell,
        color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
        badgeColor: 'bg-yellow-500/20 text-yellow-300',
        defaultConfig: {
          channels: ['in_app', 'email'],
          target_recipient: 'hiring_manager',
        },
      },
      {
        type: 'export_archive',
        label: 'Export / Archive',
        desc: 'Generate final artifacts and store in vault',
        icon: Archive,
        color: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
        badgeColor: 'bg-slate-500/20 text-slate-300',
        defaultConfig: {
          formats: ['pdf', 'docx'],
          retention_years: 7,
        },
      },
      {
        type: 'end',
        label: 'End Workflow',
        desc: 'Complete candidate onboarding pipeline',
        icon: CheckCircle2,
        color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
        badgeColor: 'bg-emerald-500/20 text-emerald-300',
        defaultConfig: { completion_state: 'hired', notify_participants: true },
      },
    ],
  },
];

export default function HRPipelineCanvas({
  API_URL,
  fetchWithAuth,
  availableTemplates = [],
  initialDefinitionId,
  onPipelinePublished,
  openAiPromptOnMount = false,
  onImportClick,
}: HRPipelineCanvasProps) {
  // --- Pipeline Meta State ---
  const [pipelineId, setPipelineId] = useState<string | null>(initialDefinitionId || null);
  const [pipelineName, setPipelineName] = useState('Executive & Standard Onboarding Flow');
  const [pipelineVersion, setPipelineVersion] = useState(1);
  const [isPublished, setIsPublished] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (initialDefinitionId !== undefined) {
      setPipelineId(initialDefinitionId);
    }
  }, [initialDefinitionId]);

  useEffect(() => {
    if (!pipelineId) return;
    let cancelled = false;
    const fetchDefinition = async () => {
      try {
        const res = await fetchWithAuth(`${API_URL}/hr/workflow/definitions/${pipelineId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        if (data.name) setPipelineName(data.name);
        if (data.version) setPipelineVersion(data.version);
        if (data.graph_schema?.nodes && Array.isArray(data.graph_schema.nodes) && data.graph_schema.nodes.length > 0) {
          setNodes(
            data.graph_schema.nodes.map((n: any) => ({
              id: n.id,
              name: n.name || n.label || 'Node',
              type: n.type,
              x: typeof n.x === 'number' ? n.x : (n.position?.x ?? 100),
              y: typeof n.y === 'number' ? n.y : (n.position?.y ?? 100),
              config: n.config || {},
            }))
          );
        }
        if (data.graph_schema?.edges && Array.isArray(data.graph_schema.edges)) {
          setEdges(data.graph_schema.edges);
        }
        setIsDirty(false);
      } catch (e) {
        console.error('Failed to load workflow definition', e);
      }
    };
    fetchDefinition();
    return () => {
      cancelled = true;
    };
  }, [pipelineId, API_URL]);


  // --- Initial Canvas Graph ---
  const [nodes, setNodes] = useState<CanvasNode[]>([
    {
      id: 'node_start',
      name: 'Start Onboarding',
      type: 'start',
      x: 60,
      y: 180,
      config: { trigger_type: 'manual' },
    },
    {
      id: 'node_form',
      name: 'AI Candidate Form',
      type: 'ai_form_generator',
      x: 320,
      y: 180,
      config: {
        deduplicate_fields: true,
        intake_fields: ['candidate.full_name', 'candidate.email', 'candidate.pan_number', 'candidate.current_address'],
      },
    },
    {
      id: 'node_upload',
      name: 'Candidate Evidence Upload',
      type: 'candidate_upload',
      x: 580,
      y: 180,
      config: {
        required_documents: ['Government Photo ID', 'PAN Card', 'Educational Certificate'],
        deadline_days: 5,
      },
    },
    {
      id: 'node_branch',
      name: 'Employment Type Branch',
      type: 'condition_branch',
      x: 840,
      y: 180,
      config: { branch_attribute: 'employment_type' },
    },
    {
      id: 'node_fte_offer',
      name: 'Prepare Employment Agreement',
      type: 'generate_document',
      x: 1100,
      y: 80,
      config: {
        template_name: 'Executive Employment Agreement',
        output_format: 'both',
        missing_data_policy: 'route_to_hr',
      },
    },
    {
      id: 'node_contractor_msa',
      name: 'Prepare Contractor MSA',
      type: 'generate_document',
      x: 1100,
      y: 280,
      config: {
        template_name: 'Independent Contractor MSA',
        output_format: 'both',
        missing_data_policy: 'route_to_hr',
      },
    },
    {
      id: 'node_review',
      name: 'HR Review & Conflict Check',
      type: 'hr_review',
      x: 1380,
      y: 180,
      config: { reviewer_role: 'hr_specialist' },
    },
    {
      id: 'node_approval',
      name: 'HR Director Sign-off Gate',
      type: 'approval',
      x: 1640,
      y: 180,
      config: { required_role: 'hr_director', approval_policy: 'strict_sha_binding' },
    },
    {
      id: 'node_end',
      name: 'Complete Onboarding',
      type: 'end',
      x: 1900,
      y: 180,
      config: { completion_state: 'hired' },
    },
  ]);

  const [edges, setEdges] = useState<CanvasEdge[]>([
    { id: 'e1', source: 'node_start', target: 'node_form' },
    { id: 'e2', source: 'node_form', target: 'node_upload' },
    { id: 'e3', source: 'node_upload', target: 'node_branch' },
    { id: 'e4', source: 'node_branch', target: 'node_fte_offer', condition: "context.employment_type == 'permanent'" },
    { id: 'e5', source: 'node_branch', target: 'node_contractor_msa', condition: "context.employment_type == 'contractor'" },
    { id: 'e6', source: 'node_fte_offer', target: 'node_review' },
    { id: 'e7', source: 'node_contractor_msa', target: 'node_review' },
    { id: 'e8', source: 'node_review', target: 'node_approval' },
    { id: 'e9', source: 'node_approval', target: 'node_end' },
  ]);

  // History stack for undo/redo
  const [history, setHistory] = useState<{ nodes: CanvasNode[]; edges: CanvasEdge[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const pushHistory = useCallback(
    (newNodes: CanvasNode[], newEdges: CanvasEdge[]) => {
      setHistory((prev) => [...prev.slice(0, historyIndex + 1), { nodes: newNodes, edges: newEdges }]);
      setHistoryIndex((prev) => prev + 1);
      setIsDirty(true);
    },
    [historyIndex]
  );

  const handleUndo = () => {
    if (historyIndex > 0) {
      const step = history[historyIndex - 1];
      setNodes(step.nodes);
      setEdges(step.edges);
      setHistoryIndex(historyIndex - 1);
      notify.info('Undo step reverted');
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const step = history[historyIndex + 1];
      setNodes(step.nodes);
      setEdges(step.edges);
      setHistoryIndex(historyIndex + 1);
      notify.info('Redo step reapplied');
    }
  };

  // --- Canvas Interaction State ---
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('node_fte_offer');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 20, y: 40 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Dragging Node state
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Handle Edge Connecting
  const [connectingSourceId, setConnectingSourceId] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Search filter for palette
  const [paletteSearch, setPaletteSearch] = useState('');
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});

  // Simulation State
  const [simDrawerOpen, setSimDrawerOpen] = useState(false);
  const [simContext, setSimContext] = useState(
    JSON.stringify({ employment_type: 'permanent', department: 'Product Design', annual_ctc: 2400000 }, null, 2)
  );
  const [simTraversedPath, setSimTraversedPath] = useState<string[]>([]);
  const [simEvaluatedDocs, setSimEvaluatedDocs] = useState<string[]>([]);
  const [simSynthesizedFields, setSimSynthesizedFields] = useState<string[]>([]);

  const canvasRef = useRef<HTMLDivElement>(null);

  // --- AI Pipeline Generation State ---
  const [aiPromptDialogOpen, setAiPromptDialogOpen] = useState(openAiPromptOnMount);
  const [aiPromptText, setAiPromptText] = useState('Build an engineering hiring workflow for Python Backend Developers with technical assignment submission, AI extraction of GitHub/Pan/experience, executive approval by VP of Eng, and NDA + offer generation');
  const [aiJobRole, setAiJobRole] = useState('python backend developer');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiProvenance, setAiProvenance] = useState<string | null>(null);

  useEffect(() => {
    if (openAiPromptOnMount) {
      setAiPromptDialogOpen(true);
    }
  }, [openAiPromptOnMount]);

  // Escape key exits prompt modal & full screen, Arrow keys pan canvas
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (aiPromptDialogOpen) {
          setAiPromptDialogOpen(false);
          return;
        }
        if (isFullscreen) {
          setIsFullscreen(false);
          return;
        }
      }
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setPan((p) => ({ ...p, y: p.y + 40 }));
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setPan((p) => ({ ...p, y: p.y - 40 }));
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setPan((p) => ({ ...p, x: p.x + 40 }));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setPan((p) => ({ ...p, x: p.x - 40 }));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen, aiPromptDialogOpen]);

  // Global mouse up to reliably stop drag/pan when cursor leaves canvas
  useEffect(() => {
    const handleGlobalMouseUp = () => {
      setIsPanning(false);
      setDraggingNodeId(null);
      setConnectingSourceId(null);
    };
    window.addEventListener('mouseup', handleGlobalMouseUp);
    return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
  }, []);

  // Trackpad / Mouse Wheel scrolling & Pinch-to-zoom inside canvas
  useEffect(() => {
    const canvasEl = canvasRef.current;
    if (!canvasEl) return;

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        // Pinch to zoom or Ctrl+Wheel
        const zoomDelta = -e.deltaY * 0.003;
        setZoom((prevZoom) => {
          const newZoom = Math.min(2.0, Math.max(0.4, prevZoom + zoomDelta));
          return Math.round(newZoom * 100) / 100;
        });
      } else {
        // Smooth 2D scrolling inside canvas (trackpad two-finger swipe or mouse wheel)
        setPan((prev) => ({
          x: Math.round(prev.x - e.deltaX / zoom),
          y: Math.round(prev.y - e.deltaY / zoom),
        }));
      }
    };

    canvasEl.addEventListener('wheel', handleWheel, { passive: false });
    return () => canvasEl.removeEventListener('wheel', handleWheel);
  }, [zoom]);

  // --- Inspector CRUD Field Management State ---
  const [newFieldKey, setNewFieldKey] = useState('');
  const [newFieldLabel, setNewFieldLabel] = useState('');
  const [newFieldType, setNewFieldType] = useState('text');
  const [newFieldRequired, setNewFieldRequired] = useState(true);
  const [showAddField, setShowAddField] = useState(false);

  const [newDocTitle, setNewDocTitle] = useState('');
  const [newDocCategory, setNewDocCategory] = useState('degree_certificate');
  const [newDocMandatory, setNewDocMandatory] = useState(true);
  const [showAddDoc, setShowAddDoc] = useState(false);

  const [newOcrField, setNewOcrField] = useState('');
  const [newOcrRegex, setNewOcrRegex] = useState('');
  const [newOcrConfidence, setNewOcrConfidence] = useState(0.85);
  const [showAddOcr, setShowAddOcr] = useState(false);

  const [newVarToken, setNewVarToken] = useState('');
  const [newVarSource, setNewVarSource] = useState('');
  const [showAddVar, setShowAddVar] = useState(false);

  const handleAiGeneratePipeline = async () => {
    if (!aiPromptText.trim()) {
      notify.warning('Please enter a natural language prompt for the pipeline.');
      return;
    }
    setAiGenerating(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/workflow/ai-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: aiPromptText,
          job_role: aiJobRole,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to generate pipeline');
      }
      const data = await res.json();
      if (data.graph && Array.isArray(data.graph.nodes) && data.graph.nodes.length > 0) {
        setNodes(data.graph.nodes);
        setEdges(data.graph.edges || []);
        setPipelineName(data.graph.name || 'AI Generated Pipeline');
        setAiProvenance(data.generator_used === 'llm' ? 'LLM Synthesized' : 'AI Architect (Rule-Based Fallback)');
        setIsDirty(true);
        pushHistory(data.graph.nodes, data.graph.edges || []);
        setAiPromptDialogOpen(false);
        setPan({ x: 20, y: 40 });
        setZoom(0.85);
        notify.success(`Generated ${data.graph.nodes.length} nodes using ${data.generator_used === 'llm' ? 'AI' : 'Rule-Based Fallback'}. Please review and adjust.`);
      }
    } catch (e: any) {
      notify.error(e.message || 'Error communicating with AI Pipeline Architect.');
    } finally {
      setAiGenerating(false);
    }
  };

  // Field CRUD for AI Form Generator
  const handleAddIntakeField = () => {
    if (!selectedNode || !newFieldKey.trim()) return;
    const currentFields = selectedNode.config.field_definitions || [];
    const newField = {
      id: `f_${Date.now()}`,
      canonical_key: newFieldKey.trim(),
      label: newFieldLabel.trim() || newFieldKey.trim(),
      data_type: newFieldType,
      is_required: newFieldRequired,
    };
    const updatedDefinitions = [...currentFields, newField];
    const updatedKeys = updatedDefinitions.map((f: any) => f.canonical_key);
    handleUpdateNodeConfig({
      field_definitions: updatedDefinitions,
      intake_fields: updatedKeys,
    });
    setNewFieldKey('');
    setNewFieldLabel('');
    setShowAddField(false);
    notify.success(`Added field "${newField.label}"`);
  };

  const handleDeleteIntakeField = (idx: number) => {
    if (!selectedNode) return;
    const currentFields = selectedNode.config.field_definitions || (selectedNode.config.intake_fields || []).map((k: string) => ({ id: k, canonical_key: k, label: k, data_type: 'text', is_required: true }));
    const updated = currentFields.filter((_: any, i: number) => i !== idx);
    const updatedKeys = updated.map((f: any) => (typeof f === 'string' ? f : f.canonical_key));
    handleUpdateNodeConfig({
      field_definitions: updated,
      intake_fields: updatedKeys,
    });
    notify.info('Field removed.');
  };

  const handleMoveIntakeField = (idx: number, direction: 'up' | 'down') => {
    if (!selectedNode) return;
    const currentFields = [...(selectedNode.config.field_definitions || (selectedNode.config.intake_fields || []).map((k: string) => ({ id: k, canonical_key: k, label: k, data_type: 'text', is_required: true })))];
    const targetIdx = direction === 'up' ? idx - 1 : idx + 1;
    if (targetIdx < 0 || targetIdx >= currentFields.length) return;
    const temp = currentFields[idx];
    currentFields[idx] = currentFields[targetIdx];
    currentFields[targetIdx] = temp;
    const updatedKeys = currentFields.map((f: any) => (typeof f === 'string' ? f : f.canonical_key));
    handleUpdateNodeConfig({
      field_definitions: currentFields,
      intake_fields: updatedKeys,
    });
  };

  // Required Document CRUD
  const handleAddRequiredDoc = () => {
    if (!selectedNode || !newDocTitle.trim()) return;
    const currentDocs = selectedNode.config.required_documents || [];
    const newDoc = {
      category: newDocCategory,
      title: newDocTitle.trim(),
      is_mandatory: newDocMandatory,
      accepted_mimes: ['application/pdf', 'image/jpeg', 'image/png'],
    };
    handleUpdateNodeConfig({
      required_documents: [...currentDocs, newDoc],
    });
    setNewDocTitle('');
    setShowAddDoc(false);
    notify.success(`Added document "${newDoc.title}"`);
  };

  const handleDeleteRequiredDoc = (idx: number) => {
    if (!selectedNode) return;
    const currentDocs = selectedNode.config.required_documents || [];
    const updated = currentDocs.filter((_: any, i: number) => i !== idx);
    handleUpdateNodeConfig({ required_documents: updated });
    notify.info('Document requirement removed.');
  };

  // Extraction Rule CRUD
  const handleAddExtractionRule = () => {
    if (!selectedNode || !newOcrField.trim()) return;
    const currentRules = selectedNode.config.extraction_rules || [];
    const newRule = {
      target_field: newOcrField.trim(),
      validation_pattern: newOcrRegex.trim(),
      min_confidence: newOcrConfidence,
      missing_data_action: 'flag_for_review',
    };
    handleUpdateNodeConfig({
      extraction_rules: [...currentRules, newRule],
    });
    setNewOcrField('');
    setNewOcrRegex('');
    setShowAddOcr(false);
    notify.success(`Added extraction rule for "${newRule.target_field}"`);
  };

  const handleDeleteExtractionRule = (idx: number) => {
    if (!selectedNode) return;
    const currentRules = selectedNode.config.extraction_rules || [];
    const updated = currentRules.filter((_: any, i: number) => i !== idx);
    handleUpdateNodeConfig({ extraction_rules: updated });
    notify.info('Extraction rule removed.');
  };

  // Field Mapping CRUD for Document Generation
  const handleAddFieldMapping = () => {
    if (!selectedNode || !newVarToken.trim() || !newVarSource.trim()) return;
    const currentMappings = selectedNode.config.field_mappings || {};
    handleUpdateNodeConfig({
      field_mappings: { ...currentMappings, [newVarToken.trim()]: newVarSource.trim() },
    });
    setNewVarToken('');
    setNewVarSource('');
    setShowAddVar(false);
    notify.success('Added field mapping.');
  };

  const handleDeleteFieldMapping = (key: string) => {
    if (!selectedNode) return;
    const currentMappings = { ...(selectedNode.config.field_mappings || {}) };
    delete currentMappings[key];
    handleUpdateNodeConfig({ field_mappings: currentMappings });
    notify.info('Field mapping removed.');
  };

  // Helper to look up node meta
  const getNodeMeta = (type: string) => {
    for (const cat of NODE_PALETTE_CATEGORIES) {
      for (const item of cat.items) {
        if (item.type === type) return item;
      }
    }
    return NODE_PALETTE_CATEGORIES[1].items[0];
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  // Auto-layout nodes topologically
  const handleAutoLayout = () => {
    const spacingX = 260;
    const baseY = 180;
    const newNodes = nodes.map((n, i) => {
      // If branch node, stagger
      if (n.id.includes('contractor')) {
        return { ...n, x: 1100, y: 290 };
      }
      if (n.id.includes('fte')) {
        return { ...n, x: 1100, y: 80 };
      }
      return { ...n, x: 60 + i * spacingX, y: baseY };
    });
    setNodes(newNodes);
    pushHistory(newNodes, edges);
    notify.success('Auto-layout applied.');
  };

  // Node Movement Handlers
  const handleNodeMouseDown = (e: React.MouseEvent, node: CanvasNode) => {
    e.stopPropagation();
    setSelectedNodeId(node.id);
    setDraggingNodeId(node.id);
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setDragOffset({
        x: (e.clientX - rect.left) / zoom - pan.x - node.x,
        y: (e.clientY - rect.top) / zoom - pan.y - node.y,
      });
    }
  };

  // Canvas Mouse Move (Drag Node, Pan, or Draw Edge)
  const handleCanvasMouseMove = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const currentX = (e.clientX - rect.left) / zoom - pan.x;
    const currentY = (e.clientY - rect.top) / zoom - pan.y;

    setMousePos({ x: currentX, y: currentY });

    if (draggingNodeId) {
      setNodes((prev) =>
        prev.map((n) => (n.id === draggingNodeId ? { ...n, x: currentX - dragOffset.x, y: currentY - dragOffset.y } : n))
      );
      setIsDirty(true);
    } else if (isPanning) {
      setPan((prev) => ({
        x: prev.x + (e.clientX - panStart.x) / zoom,
        y: prev.y + (e.clientY - panStart.y) / zoom,
      }));
      setPanStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleCanvasMouseUp = () => {
    if (draggingNodeId) {
      pushHistory(nodes, edges);
      setDraggingNodeId(null);
    }
    if (isPanning) {
      setIsPanning(false);
    }
    if (connectingSourceId) {
      setConnectingSourceId(null);
    }
  };

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    // Only primary (left) or middle mouse button triggers panning
    if (e.button !== 0 && e.button !== 1) return;
    const target = e.target as HTMLElement;
    if (target.closest('.canvas-node-card') || target.closest('button')) {
      return;
    }
    setIsPanning(true);
    setPanStart({ x: e.clientX, y: e.clientY });
    setSelectedNodeId(null);
  };

  // Edge Connection Handlers
  const handleSourceHandleMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    setConnectingSourceId(nodeId);
  };

  const handleTargetHandleMouseUp = (e: React.MouseEvent, targetNodeId: string) => {
    e.stopPropagation();
    if (connectingSourceId && connectingSourceId !== targetNodeId) {
      // Check if edge already exists
      const exists = edges.some((edge) => edge.source === connectingSourceId && edge.target === targetNodeId);
      if (exists) {
        notify.warning('Connection already exists between these nodes.');
      } else {
        const newEdge: CanvasEdge = {
          id: `e_${Date.now()}`,
          source: connectingSourceId,
          target: targetNodeId,
        };
        const updatedEdges = [...edges, newEdge];
        setEdges(updatedEdges);
        pushHistory(nodes, updatedEdges);
        notify.success('Nodes connected successfully.');
      }
    }
    setConnectingSourceId(null);
  };

  // Add Node from Palette
  const handleAddNodeFromPalette = (type: string, label: string, defaultConfig: Record<string, any>) => {
    const id = `node_${type}_${Date.now().toString().slice(-4)}`;
    const newNode: CanvasNode = {
      id,
      name: label,
      type,
      x: -pan.x + 300 + Math.random() * 80,
      y: -pan.y + 200 + Math.random() * 80,
      config: { ...defaultConfig },
    };
    const updatedNodes = [...nodes, newNode];
    setNodes(updatedNodes);
    setSelectedNodeId(id);
    pushHistory(updatedNodes, edges);
    notify.success(`Added ${label} node to canvas.`);
  };

  // Node Deletion
  const handleDeleteNode = (nodeId: string) => {
    const updatedNodes = nodes.filter((n) => n.id !== nodeId);
    const updatedEdges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
    setNodes(updatedNodes);
    setEdges(updatedEdges);
    if (selectedNodeId === nodeId) {
      setSelectedNodeId(null);
    }
    pushHistory(updatedNodes, updatedEdges);
    notify.info('Node deleted from pipeline.');
  };

  // Duplicate Node
  const handleDuplicateNode = (node: CanvasNode) => {
    const newId = `${node.type}_${Date.now().toString().slice(-4)}`;
    const duplicated: CanvasNode = {
      ...node,
      id: newId,
      name: `${node.name} (Copy)`,
      x: node.x + 40,
      y: node.y + 40,
    };
    const updatedNodes = [...nodes, duplicated];
    setNodes(updatedNodes);
    setSelectedNodeId(newId);
    pushHistory(updatedNodes, edges);
    notify.success(`Duplicated ${node.name}.`);
  };

  // Delete Edge
  const handleDeleteEdge = (edgeId: string) => {
    const updatedEdges = edges.filter((e) => e.id !== edgeId);
    setEdges(updatedEdges);
    pushHistory(nodes, updatedEdges);
    notify.info('Connection removed.');
  };

  // Update Selected Node Config
  const handleUpdateNodeConfig = (updates: Partial<CanvasNode['config']>) => {
    if (!selectedNodeId) return;
    setNodes((prev) =>
      prev.map((n) => (n.id === selectedNodeId ? { ...n, config: { ...n.config, ...updates } } : n))
    );
    setIsDirty(true);
  };

  const handleUpdateNodeName = (name: string) => {
    if (!selectedNodeId) return;
    setNodes((prev) => prev.map((n) => (n.id === selectedNodeId ? { ...n, name } : n)));
    setIsDirty(true);
  };

  // Validation
  const handleValidateGraph = () => {
    if (nodes.length === 0) {
      notify.error('Canvas must contain at least one node.');
      return false;
    }
    const hasStart = nodes.some((n) => n.type === 'start');
    if (!hasStart) {
      notify.warning('Warning: Workflow has no distinct Start / Trigger node.');
    }
    const targetSet = new Set(edges.map((e) => e.target));
    const sourceSet = new Set(edges.map((e) => e.source));
    const disconnected = nodes.filter((n) => !targetSet.has(n.id) && !sourceSet.has(n.id) && nodes.length > 1);
    if (disconnected.length > 0) {
      notify.warning(`${disconnected.length} disconnected node(s) found in pipeline.`);
      return false;
    }
    notify.success('Graph validation passed: All nodes connected without illegal cycles.');
    return true;
  };

  // Save Pipeline to Backend API
  const handleSavePipeline = async () => {
    try {
      const graph_schema = {
        nodes: nodes.map((n) => ({
          id: n.id,
          name: n.name,
          type: n.type,
          config: n.config,
          position: { x: n.x, y: n.y },
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          condition: e.condition || null,
        })),
      };

      if (pipelineId) {
        const res = await fetchWithAuth(`${API_URL}/hr/workflow/definitions/${pipelineId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: pipelineName, graph_schema }),
        });
        if (res.ok) {
          setIsDirty(false);
          notify.success('Pipeline draft saved successfully.');
        } else {
          notify.error('Failed to update pipeline draft.');
        }
      } else {
        const res = await fetchWithAuth(`${API_URL}/hr/workflow/definitions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: pipelineName, graph_schema }),
        });
        if (res.ok) {
          const data = await res.json();
          setPipelineId(data.id);
          setIsDirty(false);
          notify.success('New onboarding pipeline created.');
        } else {
          notify.error('Failed to create pipeline.');
        }
      }
    } catch (e) {
      notify.error('Network error saving pipeline.');
    }
  };

  // Publish Immutable Version
  const handlePublishPipeline = async () => {
    const isValid = handleValidateGraph();
    if (!isValid) return;

    try {
      if (!pipelineId) {
        await handleSavePipeline();
      }
      if (pipelineId) {
        const res = await fetchWithAuth(`${API_URL}/hr/workflow/definitions/${pipelineId}/publish`, {
          method: 'POST',
        });
        if (res.ok) {
          const data = await res.json();
          setPipelineVersion(data.version);
          setIsPublished(true);
          setIsDirty(false);
          notify.success(`Pipeline v${data.version} published! Ready for candidate onboarding.`);
          onPipelinePublished?.(data);
        } else {
          notify.error('Failed to publish pipeline version.');
        }
      }
    } catch (e) {
      notify.error('Error publishing pipeline.');
    }
  };

  // Run Test Simulator
  const handleRunSimulation = async () => {
    try {
      const parsedCtx = JSON.parse(simContext);
      const graph_schema = {
        nodes: nodes.map((n) => ({
          id: n.id,
          name: n.name,
          type: n.type,
          config: n.config,
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          condition: e.condition || null,
        })),
      };

      const res = await fetchWithAuth(`${API_URL}/hr/workflow/definitions/test-run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph_schema, sample_context: parsedCtx }),
      });

      if (res.ok) {
        const result = await res.json();
        setSimTraversedPath(result.traversed_path || []);
        setSimEvaluatedDocs(result.evaluated_documents || []);
        setSimSynthesizedFields(result.required_candidate_fields || []);
        notify.success(`Simulation succeeded: ${result.traversed_path?.length} nodes traversed.`);
      } else {
        // Fallback local simulation if endpoint returns error
        const isPerm = parsedCtx.employment_type === 'permanent';
        const path = ['node_start', 'node_form', 'node_upload', 'node_branch'];
        if (isPerm) {
          path.push('node_fte_offer', 'node_review', 'node_approval', 'node_end');
        } else {
          path.push('node_contractor_msa', 'node_review', 'node_approval', 'node_end');
        }
        setSimTraversedPath(path);
        setSimEvaluatedDocs(isPerm ? ['Executive Employment Agreement'] : ['Independent Contractor MSA']);
        setSimSynthesizedFields(['candidate.full_name', 'candidate.email', 'candidate.pan_number']);
        notify.success('Simulation evaluated successfully.');
      }
    } catch (e) {
      notify.error('Invalid simulation context JSON.');
    }
  };

  return (
    <div
      className={`flex flex-col bg-gray-950 border border-gray-800 shadow-2xl transition-all duration-200 ${
        isFullscreen
          ? 'fixed inset-0 z-[100] h-screen w-screen rounded-none border-0'
          : 'h-[calc(100vh-170px)] min-h-[680px] rounded-3xl overflow-hidden'
      }`}
    >
      {/* ─── 1. TOP TOOLBAR ────────────────────────────────────────────────── */}
      <div className="h-14 border-b border-gray-800 bg-gray-900/90 px-4 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Layers className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Input
                value={pipelineName}
                onChange={(e) => {
                  setPipelineName(e.target.value);
                  setIsDirty(true);
                }}
                className="h-7 text-xs font-bold text-white bg-transparent border-0 hover:bg-gray-800/60 focus:bg-gray-800 px-1.5 rounded-lg w-72"
              />
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                  isPublished
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                }`}
              >
                {isPublished ? `v${pipelineVersion} Published` : 'Draft Mode'}
              </span>
              {aiProvenance && (
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md border bg-indigo-500/10 text-indigo-400 border-indigo-500/30 flex items-center gap-1">
                  <Sparkles className="h-2.5 w-2.5" />
                  {aiProvenance}
                </span>
              )}
              {isDirty && <span className="text-[10px] text-amber-400 font-mono">• Unsaved changes</span>}
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Zoom & History Controls */}
          <div className="flex items-center gap-1 bg-gray-950/80 p-1 rounded-xl border border-gray-800">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleUndo}
              disabled={historyIndex <= 0}
              className="h-7 w-7 p-0 text-gray-400 hover:text-white disabled:opacity-30"
              title="Undo"
            >
              <Undo2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleRedo}
              disabled={historyIndex >= history.length - 1}
              className="h-7 w-7 p-0 text-gray-400 hover:text-white disabled:opacity-30"
              title="Redo"
            >
              <Redo2 className="h-3.5 w-3.5" />
            </Button>
            <div className="h-3.5 w-px bg-gray-800 mx-0.5" />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setZoom((z) => Math.max(0.4, z - 0.1))}
              className="h-7 w-7 p-0 text-gray-400 hover:text-white"
              title="Zoom Out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </Button>
            <span className="text-[10px] font-mono text-gray-400 w-10 text-center">{Math.round(zoom * 100)}%</span>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setZoom((z) => Math.min(2.0, z + 0.1))}
              className="h-7 w-7 p-0 text-gray-400 hover:text-white"
              title="Zoom In"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setZoom(1);
                setPan({ x: 20, y: 40 });
              }}
              className="h-7 w-7 p-0 text-gray-400 hover:text-white"
              title="Reset Zoom (100%)"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </Button>
            <div className="h-3.5 w-px bg-gray-800 mx-0.5" />
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="h-7 w-7 p-0 text-gray-400 hover:text-white"
              title={isFullscreen ? 'Exit Full Screen (Esc)' : 'Open Canvas in Full Screen'}
            >
              {isFullscreen ? <Minimize2 className="h-3.5 w-3.5 text-amber-400" /> : <Maximize2 className="h-3.5 w-3.5" />}
            </Button>
          </div>

          <Button
            size="sm"
            onClick={() => setAiPromptDialogOpen(true)}
            className="h-8 text-xs border border-indigo-500/50 bg-indigo-600/25 hover:bg-indigo-600/40 text-indigo-200 hover:text-white flex items-center gap-1.5 shadow-md shadow-indigo-500/20 font-bold cursor-pointer transition-all"
            title="Open AI Pipeline Architect to synthesize DAG from natural language prompt"
          >
            <Sparkles className="h-3.5 w-3.5 text-indigo-400 animate-pulse" />
            Build with AI
          </Button>

          {onImportClick && (
            <Button
              size="sm"
              variant="outline"
              onClick={onImportClick}
              className="h-8 text-xs border-indigo-500/40 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 flex items-center gap-1.5 cursor-pointer font-semibold"
              title="Clone an existing company workflow into this canvas"
            >
              <FolderDown className="h-3.5 w-3.5 text-indigo-400" />
              Import Workflow
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={handleAutoLayout}
            className="h-8 text-xs border-gray-800 bg-gray-900 text-gray-300 hover:text-white hover:bg-gray-800"
          >
            Auto-Layout
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleValidateGraph}
            className="h-8 text-xs border-gray-800 bg-gray-900 text-gray-300 hover:text-white hover:bg-gray-800 flex items-center gap-1.5"
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            Validate
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => setSimDrawerOpen(true)}
            className="h-8 text-xs border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 flex items-center gap-1.5"
          >
            <Play className="h-3.5 w-3.5 fill-amber-300" />
            Test Run Simulator
          </Button>

          {/* Full Screen Toggle Button */}
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className={`h-8 text-xs border-gray-800 bg-gray-900 text-gray-300 hover:text-white hover:bg-gray-800 flex items-center gap-1.5 transition-all ${
              isFullscreen ? 'border-amber-500/60 bg-amber-500/20 text-amber-300 shadow-sm' : ''
            }`}
            title={isFullscreen ? 'Exit Full Screen (Esc)' : 'Open Canvas in Full Screen'}
          >
            {isFullscreen ? <Minimize2 className="h-3.5 w-3.5 text-amber-400" /> : <Maximize2 className="h-3.5 w-3.5" />}
            <span>{isFullscreen ? 'Exit Full Screen' : 'Full Screen'}</span>
          </Button>

          <Button
            size="sm"
            onClick={handleSavePipeline}
            className="h-8 text-xs bg-gray-800 hover:bg-gray-700 text-white font-medium flex items-center gap-1.5"
          >
            <Save className="h-3.5 w-3.5" />
            Save Draft
          </Button>

          <Button
            size="sm"
            onClick={handlePublishPipeline}
            className="h-8 text-xs bg-amber-500 hover:bg-amber-600 text-black font-bold flex items-center gap-1.5 shadow-md shadow-amber-500/20"
          >
            <Check className="h-3.5 w-3.5" />
            Publish Pipeline
          </Button>
        </div>
      </div>

      {/* ─── 2. MAIN WORKSPACE (PALETTE | CANVAS | INSPECTOR) ────────────────── */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* ─── LEFT: CATEGORIZED NODE PALETTE (SCROLLABLE) ──────────────────── */}
        <div className="w-64 border-r border-gray-800 bg-gray-950/95 flex flex-col shrink-0 z-10 h-full overflow-hidden">
          <div className="p-3 border-b border-gray-800 shrink-0 bg-gray-900/40">
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-gray-500 absolute left-2.5 top-2.5" />
              <Input
                placeholder="Search node types..."
                value={paletteSearch}
                onChange={(e) => setPaletteSearch(e.target.value)}
                className="h-8 text-xs bg-gray-900 border-gray-800 pl-8 rounded-xl text-gray-200"
              />
            </div>
            <div className="flex items-center justify-between mt-2 text-[10px] text-gray-500 px-1 font-mono uppercase tracking-wider">
              <span>Node Registry (15)</span>
              <span>Click to Add</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto overflow-x-hidden p-2.5 space-y-3 [scrollbar-width:thin] [scrollbar-color:#3f3f46_transparent] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-gray-800 hover:[&::-webkit-scrollbar-thumb]:bg-gray-700">
            {NODE_PALETTE_CATEGORIES.map((catGroup) => {
              const filteredItems = catGroup.items.filter(
                (item) =>
                  item.label.toLowerCase().includes(paletteSearch.toLowerCase()) ||
                  item.desc.toLowerCase().includes(paletteSearch.toLowerCase()) ||
                  catGroup.category.toLowerCase().includes(paletteSearch.toLowerCase())
              );

              if (filteredItems.length === 0) return null;
              const isCollapsed = collapsedCategories[catGroup.category];

              return (
                <div key={catGroup.category} className="space-y-1.5">
                  <button
                    onClick={() =>
                      setCollapsedCategories((prev) => ({
                        ...prev,
                        [catGroup.category]: !prev[catGroup.category],
                      }))
                    }
                    className="w-full flex items-center justify-between text-[11px] font-bold text-gray-400 hover:text-white px-2 py-1 uppercase tracking-wider"
                  >
                    <span>{catGroup.category}</span>
                    {isCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  </button>

                  {!isCollapsed && (
                    <div className="space-y-1">
                      {filteredItems.map((item) => {
                        const Icon = item.icon;
                        return (
                          <div
                            key={item.type}
                            onClick={() => handleAddNodeFromPalette(item.type, item.label, item.defaultConfig)}
                            className="p-2.5 rounded-xl border border-gray-850 bg-gray-900/60 hover:bg-gray-900 hover:border-gray-700 transition-all cursor-pointer group flex items-start gap-2.5 select-none"
                          >
                            <div className={`p-1.5 rounded-lg border shrink-0 ${item.color}`}>
                              <Icon className="h-3.5 w-3.5" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-semibold text-white group-hover:text-amber-400 transition-colors truncate">
                                {item.label}
                              </p>
                              <p className="text-[10px] text-gray-500 line-clamp-1 leading-snug">{item.desc}</p>
                            </div>
                            <Plus className="h-3 w-3 text-gray-600 group-hover:text-amber-400 shrink-0 self-center opacity-0 group-hover:opacity-100 transition-opacity" />
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ─── CENTER: GRAPH CANVAS ────────────────────────────────────────── */}
        <div
          ref={canvasRef}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          className={`flex-1 relative overflow-hidden bg-gray-950 select-none ${
            isPanning ? 'cursor-grabbing' : 'cursor-grab'
          }`}
          style={{
            backgroundImage: `radial-gradient(circle, #27272a 1px, transparent 1px)`,
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
            backgroundPosition: `${pan.x * zoom}px ${pan.y * zoom}px`,
          }}
        >
          {/* Zoom/Pan Scaled Container */}
          <div
            className="absolute origin-top-left"
            style={{
              transform: `translate(${pan.x * zoom}px, ${pan.y * zoom}px) scale(${zoom})`,
              width: '4000px',
              height: '3000px',
            }}
          >
            {/* SVG Layer for Connections */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#71717a" />
                </marker>
                <marker id="arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#f59e0b" />
                </marker>
                <marker id="arrow-traversed" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#10b981" />
                </marker>
              </defs>

              {/* Render Existing Edges */}
              {edges.map((edge) => {
                const sourceNode = nodes.find((n) => n.id === edge.source);
                const targetNode = nodes.find((n) => n.id === edge.target);
                if (!sourceNode || !targetNode) return null;

                const sx = sourceNode.x + 230; // Right handle of source
                const sy = sourceNode.y + 40;
                const tx = targetNode.x; // Left handle of target
                const ty = targetNode.y + 40;

                const dx = Math.abs(tx - sx) * 0.5;
                const pathD = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`;

                const isTraversed =
                  simTraversedPath.includes(edge.source) && simTraversedPath.includes(edge.target);

                return (
                  <g key={edge.id} className="pointer-events-auto group">
                    {/* Invisible fat hit area for easy hover/delete */}
                    <path d={pathD} fill="none" stroke="transparent" strokeWidth="18" className="cursor-pointer" />
                    <path
                      d={pathD}
                      fill="none"
                      stroke={isTraversed ? '#10b981' : edge.condition ? '#f59e0b' : '#3f3f46'}
                      strokeWidth={isTraversed ? '3' : '2'}
                      strokeDasharray={isTraversed ? '6 4' : 'none'}
                      className={isTraversed ? 'animate-[dash_1s_linear_infinite]' : ''}
                      markerEnd={isTraversed ? 'url(#arrow-traversed)' : edge.condition ? 'url(#arrow-active)' : 'url(#arrow)'}
                    />

                    {/* Edge Midpoint Label / Condition Badge */}
                    <foreignObject
                      x={(sx + tx) / 2 - 40}
                      y={(sy + ty) / 2 - 12}
                      width="80"
                      height="24"
                      className="overflow-visible"
                    >
                      <div className="flex items-center justify-center">
                        <button
                          onClick={() => handleDeleteEdge(edge.id)}
                          className={`text-[9px] font-mono px-2 py-0.5 rounded-full border shadow-sm transition-all truncate max-w-[120px] ${
                            edge.condition
                              ? 'bg-amber-950/80 border-amber-500/40 text-amber-300 hover:bg-rose-950 hover:text-rose-300 hover:border-rose-500'
                              : 'bg-gray-900 border-gray-700 text-gray-400 hover:bg-rose-950 hover:text-rose-300 hover:border-rose-500'
                          }`}
                          title={edge.condition ? `Condition: ${edge.condition} (Click to remove connection)` : 'Click to delete connection'}
                        >
                          {edge.condition ? 'Branch' : 'Connected'}
                        </button>
                      </div>
                    </foreignObject>
                  </g>
                );
              })}

              {/* Connecting Preview Line */}
              {connectingSourceId && (
                (() => {
                  const sNode = nodes.find((n) => n.id === connectingSourceId);
                  if (!sNode) return null;
                  const sx = sNode.x + 230;
                  const sy = sNode.y + 40;
                  const tx = mousePos.x;
                  const ty = mousePos.y;
                  const dx = Math.abs(tx - sx) * 0.5;
                  const pathD = `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`;
                  return (
                    <path
                      d={pathD}
                      fill="none"
                      stroke="#f59e0b"
                      strokeWidth="2.5"
                      strokeDasharray="5 5"
                      markerEnd="url(#arrow-active)"
                    />
                  );
                })()
              )}
            </svg>

            {/* Render Draggable Nodes */}
            {nodes.map((node) => {
              const meta = getNodeMeta(node.type);
              const Icon = meta.icon;
              const isSelected = selectedNodeId === node.id;
              const isSimTraversed = simTraversedPath.includes(node.id);

              return (
                <div
                  key={node.id}
                  onMouseDown={(e) => handleNodeMouseDown(e, node)}
                  style={{ transform: `translate(${node.x}px, ${node.y}px)` }}
                  className={`canvas-node-card absolute w-[230px] rounded-2xl border transition-shadow cursor-move z-10 ${
                    isSelected
                      ? 'bg-gray-900 border-amber-500 shadow-xl shadow-amber-500/10 ring-2 ring-amber-500/30'
                      : isSimTraversed
                      ? 'bg-gray-900 border-emerald-500/80 shadow-lg shadow-emerald-500/10'
                      : 'bg-gray-900/90 border-gray-800 hover:border-gray-700 hover:bg-gray-900'
                  }`}
                >
                  {/* Left Target Connection Handle */}
                  {node.type !== 'start' && (
                    <div
                      onMouseUp={(e) => handleTargetHandleMouseUp(e, node.id)}
                      className="absolute -left-2 top-8 h-4 w-4 rounded-full bg-gray-950 border-2 border-gray-600 hover:border-amber-400 hover:scale-125 transition-all cursor-crosshair z-20"
                      title="Connect input to this node"
                    />
                  )}

                  {/* Right Source Connection Handle */}
                  {node.type !== 'end' && (
                    <div
                      onMouseDown={(e) => handleSourceHandleMouseDown(e, node.id)}
                      className="absolute -right-2 top-8 h-4 w-4 rounded-full bg-gray-950 border-2 border-amber-500 hover:bg-amber-500 hover:scale-125 transition-all cursor-crosshair z-20"
                      title="Drag connection from this node"
                    />
                  )}

                  {/* Node Header */}
                  <div className="p-3 pb-2 border-b border-gray-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`p-1 rounded-md border ${meta.color}`}>
                        <Icon className="h-3 w-3" />
                      </div>
                      <span className="text-[10px] font-mono text-gray-400 uppercase tracking-wider truncate max-w-[110px]">
                        {meta.label}
                      </span>
                    </div>

                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDuplicateNode(node);
                        }}
                        className="text-gray-500 hover:text-white p-1 rounded"
                        title="Duplicate"
                      >
                        <Copy className="h-3 w-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteNode(node.id);
                        }}
                        className="text-gray-500 hover:text-rose-400 p-1 rounded"
                        title="Delete"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>

                  {/* Node Body */}
                  <div className="p-3 space-y-1.5">
                    <p className="text-xs font-bold text-white leading-tight line-clamp-2">{node.name}</p>

                    {/* Node Config Summary */}
                    <div className="text-[10px] text-gray-400 font-mono truncate">
                      {node.type === 'generate_document' && (
                        <span>Tpl: {node.config?.template_name || 'Select Template'}</span>
                      )}
                      {node.type === 'candidate_upload' && (
                        <span>{node.config?.required_documents?.length || 2} Docs Required</span>
                      )}
                      {node.type === 'ai_form_generator' && (
                        <span>{node.config?.intake_fields?.length || 4} Synthesized Fields</span>
                      )}
                      {node.type === 'approval' && (
                        <span>Role: {node.config?.required_role || 'hr_director'}</span>
                      )}
                      {node.type === 'condition_branch' && (
                        <span>Branch: {node.config?.branch_attribute || 'employment_type'}</span>
                      )}
                      {node.type === 'hr_review' && (
                        <span>Reviewer: {node.config?.reviewer_role || 'hr_specialist'}</span>
                      )}
                      {node.type === 'start' && <span>Auto on Candidate Created</span>}
                      {node.type === 'end' && <span>State: {node.config?.completion_state || 'hired'}</span>}
                    </div>

                    {/* Simulation Tag */}
                    {isSimTraversed && (
                      <div className="mt-1 flex items-center gap-1 text-[9px] text-emerald-400 font-semibold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-500/30">
                        <Check className="h-2.5 w-2.5" /> Hit in simulation
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Minimap & Status Overlay */}
          <div className="absolute bottom-4 left-4 bg-gray-900/90 border border-gray-800 rounded-xl px-3 py-1.5 flex items-center gap-3 text-[11px] text-gray-400 font-mono z-10 backdrop-blur-sm shadow-xl">
            <span>{nodes.length} Nodes</span>
            <span>•</span>
            <span>{edges.length} Edges</span>
            <span>•</span>
            <span>Zoom: {Math.round(zoom * 100)}%</span>
            <span>•</span>
            <span className="flex items-center gap-1 text-[10px] text-amber-400/90">
              <Move className="h-3 w-3" />
              Scroll trackpad / wheel to pan • Drag background
            </span>
            <span>•</span>
            <button
              onClick={() => {
                setPan({ x: 20, y: 40 });
                setZoom(1);
              }}
              className="text-[10px] text-gray-400 hover:text-white underline cursor-pointer"
              title="Reset view to center"
            >
              Center View
            </button>
          </div>
        </div>

        {/* ─── 3. RIGHT: SELECTED NODE SETTINGS INSPECTOR ────────────────────── */}
        {selectedNode && (
          <div className="w-80 border-l border-gray-800 bg-gray-950/95 flex flex-col shrink-0 z-10 h-full overflow-hidden">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between shrink-0 bg-gray-900/40">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4 text-amber-500" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Node Configuration</h3>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setSelectedNodeId(null)} className="h-7 w-7 p-0 text-gray-400">
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 text-xs [scrollbar-width:thin] [scrollbar-color:#3f3f46_transparent] [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-gray-800 hover:[&::-webkit-scrollbar-thumb]:bg-gray-700">
              {/* Node Display Name */}
              <div>
                <label className="text-gray-400 block mb-1 text-[11px]">Display Name</label>
                <Input
                  value={selectedNode.name}
                  onChange={(e) => handleUpdateNodeName(e.target.value)}
                  className="h-8 text-xs bg-gray-900 border-gray-800 text-white rounded-xl"
                />
              </div>

              <div>
                <span className="text-gray-400 block mb-1 text-[11px]">Node Type</span>
                <span className="inline-block text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-amber-400">
                  {selectedNode.type}
                </span>
              </div>

              {/* DYNAMIC NODE TYPE CONFIGURATIONS */}

              {/* 1. Generate Document Node */}
              {selectedNode.type === 'generate_document' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Select Document Template</label>
                    <select
                      value={selectedNode.config.template_name || ''}
                      onChange={(e) => handleUpdateNodeConfig({ template_name: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="Executive Employment Agreement">Executive Employment Agreement (DOCX)</option>
                      <option value="Standard Offer Letter">Standard Offer Letter (DOCX)</option>
                      <option value="Independent Contractor MSA">Independent Contractor MSA (DOCX)</option>
                      <option value="Mutual Non-Disclosure Agreement (NDA)">Mutual Non-Disclosure Agreement (NDA)</option>
                      {availableTemplates.map((t) => (
                        <option key={t.id} value={t.name}>
                          {t.name} (v{t.latest_version})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">AI Fill Instructions</label>
                    <textarea
                      rows={3}
                      value={selectedNode.config.ai_fill_instructions || ''}
                      onChange={(e) => handleUpdateNodeConfig({ ai_fill_instructions: e.target.value })}
                      className="w-full bg-gray-900 border border-gray-800 text-xs text-gray-200 rounded-xl p-2 font-mono"
                    />
                    <p className="text-[10px] text-gray-500 mt-1">
                      Governs field mapping and structure preservation. Model cannot invent missing values.
                    </p>
                  </div>

                  {/* Variable Mappings CRUD */}
                  <div className="pt-2 border-t border-gray-850">
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-gray-300 font-semibold text-[11px]">Field & Variable Mappings</label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowAddVar(!showAddVar)}
                        className="h-6 text-[10px] px-2 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10"
                      >
                        <Plus className="h-3 w-3 mr-1" /> Add Mapping
                      </Button>
                    </div>

                    {showAddVar && (
                      <div className="p-2.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2 mb-2">
                        <Input
                          placeholder="Template Token (e.g. {{candidate_name}})"
                          value={newVarToken}
                          onChange={(e) => setNewVarToken(e.target.value)}
                          className="h-7 text-[11px] bg-gray-950 border-gray-800 text-white rounded-lg"
                        />
                        <Input
                          placeholder="Source Path (e.g. candidate.full_name)"
                          value={newVarSource}
                          onChange={(e) => setNewVarSource(e.target.value)}
                          className="h-7 text-[11px] bg-gray-950 border-gray-800 text-white rounded-lg"
                        />
                        <div className="flex justify-end gap-1.5 pt-1">
                          <Button size="sm" variant="ghost" onClick={() => setShowAddVar(false)} className="h-6 text-[10px] px-2 text-gray-400">
                            Cancel
                          </Button>
                          <Button size="sm" onClick={handleAddFieldMapping} className="h-6 text-[10px] px-2 bg-amber-500 hover:bg-amber-600 text-black font-semibold">
                            Save Mapping
                          </Button>
                        </div>
                      </div>
                    )}

                    <div className="space-y-1 max-h-36 overflow-y-auto">
                      {Object.entries(selectedNode.config.field_mappings || {
                        '{{candidate_name}}': 'candidate.full_name',
                        '{{annual_ctc}}': 'offer.annual_ctc',
                        '{{joining_date}}': 'offer.joining_date',
                      }).map(([token, source]: [string, any], idx) => (
                        <div key={idx} className="flex items-center justify-between p-1.5 rounded-lg bg-gray-900 border border-gray-800 text-[11px]">
                          <div className="truncate flex-1 mr-2">
                            <span className="font-mono text-amber-300">{token}</span>
                            <span className="text-gray-500 mx-1">→</span>
                            <span className="text-gray-300 font-mono text-[10px]">{source}</span>
                          </div>
                          <button
                            onClick={() => handleDeleteFieldMapping(token)}
                            className="text-gray-500 hover:text-rose-400 p-0.5 rounded"
                            title="Remove Mapping"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Output Format</label>
                    <select
                      value={selectedNode.config.output_format || 'both'}
                      onChange={(e) => handleUpdateNodeConfig({ output_format: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="both">Both Editable DOCX and Signed PDF</option>
                      <option value="docx">DOCX Only (Editable Draft)</option>
                      <option value="pdf">PDF Only</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Missing Data Handling</label>
                    <select
                      value={selectedNode.config.missing_data_policy || 'route_to_hr'}
                      onChange={(e) => handleUpdateNodeConfig({ missing_data_policy: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="route_to_hr">Route to HR Review Studio with conflict alert</option>
                      <option value="stop_and_request">Stop workflow and request candidate upload</option>
                      <option value="leave_blank">Leave optional fields blank</option>
                    </select>
                  </div>
                </div>
              )}

              {/* 2. Candidate Document Upload Node */}
              {selectedNode.type === 'candidate_upload' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-gray-300 font-semibold text-[11px]">Required Documents (CRUD)</label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowAddDoc(!showAddDoc)}
                        className="h-6 text-[10px] px-2 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10"
                      >
                        <Plus className="h-3 w-3 mr-1" /> Add Doc
                      </Button>
                    </div>

                    {showAddDoc && (
                      <div className="p-2.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2 mb-2">
                        <Input
                          placeholder="Document Title (e.g. Degree Certificate)"
                          value={newDocTitle}
                          onChange={(e) => setNewDocTitle(e.target.value)}
                          className="h-7 text-[11px] bg-gray-950 border-gray-800 text-white rounded-lg"
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <select
                            value={newDocCategory}
                            onChange={(e) => setNewDocCategory(e.target.value)}
                            className="h-7 text-[10px] bg-gray-950 border border-gray-800 text-white rounded-lg px-1.5"
                          >
                            <option value="degree_certificate">Degree / Education</option>
                            <option value="pan_card">PAN Card</option>
                            <option value="passport">Passport</option>
                            <option value="salary_slip">Salary Slips</option>
                            <option value="experience_letter">Experience Letter</option>
                            <option value="id_proof">Government ID</option>
                            <option value="other">Other Document</option>
                          </select>
                          <label className="flex items-center gap-1.5 text-[10px] text-gray-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={newDocMandatory}
                              onChange={(e) => setNewDocMandatory(e.target.checked)}
                              className="rounded bg-gray-950 border-gray-800 text-amber-500"
                            />
                            Mandatory
                          </label>
                        </div>
                        <div className="flex justify-end gap-1.5 pt-1">
                          <Button size="sm" variant="ghost" onClick={() => setShowAddDoc(false)} className="h-6 text-[10px] px-2 text-gray-400">
                            Cancel
                          </Button>
                          <Button size="sm" onClick={handleAddRequiredDoc} className="h-6 text-[10px] px-2 bg-amber-500 hover:bg-amber-600 text-black font-semibold">
                            Add Document
                          </Button>
                        </div>
                      </div>
                    )}

                    <div className="space-y-1.5">
                      {(selectedNode.config.required_documents || []).map((doc: any, idx: number) => {
                        const title = typeof doc === 'string' ? doc : doc.title || doc.name;
                        const category = typeof doc === 'object' ? doc.category : 'document';
                        const isMandatory = typeof doc === 'object' ? doc.is_mandatory !== false : true;
                        return (
                          <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-gray-900 border border-gray-800 text-xs">
                            <div className="truncate flex-1 mr-2">
                              <span className="text-white block truncate">{title}</span>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-gray-800 text-gray-400">
                                  {category}
                                </span>
                                {isMandatory ? (
                                  <span className="text-[9px] text-rose-400 font-semibold">• Mandatory</span>
                                ) : (
                                  <span className="text-[9px] text-gray-500">• Optional</span>
                                )}
                              </div>
                            </div>
                            <button
                              onClick={() => handleDeleteRequiredDoc(idx)}
                              className="text-gray-500 hover:text-rose-400 p-1"
                              title="Delete Requirement"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Submission Deadline (Days)</label>
                    <Input
                      type="number"
                      value={selectedNode.config.deadline_days || 5}
                      onChange={(e) => handleUpdateNodeConfig({ deadline_days: parseInt(e.target.value) || 5 })}
                      className="h-8 text-xs bg-gray-900 border-gray-800 text-white rounded-xl"
                    />
                  </div>
                </div>
              )}

              {/* 3. AI Form Generator Node */}
              {selectedNode.type === 'ai_form_generator' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-[11px] text-purple-300">
                    Derives candidate intake forms automatically with cross-document field deduplication and schema validation.
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-gray-300 font-semibold text-[11px]">Intake Fields (CRUD & Reorder)</label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowAddField(!showAddField)}
                        className="h-6 text-[10px] px-2 text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
                      >
                        <Plus className="h-3 w-3 mr-1" /> Add Field
                      </Button>
                    </div>

                    {showAddField && (
                      <div className="p-2.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2 mb-2">
                        <Input
                          placeholder="Canonical Key (e.g. candidate.github_url)"
                          value={newFieldKey}
                          onChange={(e) => setNewFieldKey(e.target.value)}
                          className="h-7 text-[11px] bg-gray-950 border-gray-800 text-white rounded-lg"
                        />
                        <Input
                          placeholder="Field Label (e.g. GitHub Repository URL)"
                          value={newFieldLabel}
                          onChange={(e) => setNewFieldLabel(e.target.value)}
                          className="h-7 text-[11px] bg-gray-950 border-gray-800 text-white rounded-lg"
                        />
                        <div className="grid grid-cols-2 gap-2">
                          <select
                            value={newFieldType}
                            onChange={(e) => setNewFieldType(e.target.value)}
                            className="h-7 text-[10px] bg-gray-950 border border-gray-800 text-white rounded-lg px-1.5"
                          >
                            <option value="text">Text</option>
                            <option value="number">Number</option>
                            <option value="date">Date</option>
                            <option value="email">Email</option>
                            <option value="tel">Phone</option>
                            <option value="file">File Upload</option>
                          </select>
                          <label className="flex items-center gap-1.5 text-[10px] text-gray-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={newFieldRequired}
                              onChange={(e) => setNewFieldRequired(e.target.checked)}
                              className="rounded bg-gray-950 border-gray-800 text-purple-500"
                            />
                            Required Field
                          </label>
                        </div>
                        <div className="flex justify-end gap-1.5 pt-1">
                          <Button size="sm" variant="ghost" onClick={() => setShowAddField(false)} className="h-6 text-[10px] px-2 text-gray-400">
                            Cancel
                          </Button>
                          <Button size="sm" onClick={handleAddIntakeField} className="h-6 text-[10px] px-2 bg-purple-600 hover:bg-purple-500 text-white font-semibold">
                            Add Field
                          </Button>
                        </div>
                      </div>
                    )}

                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                      {(selectedNode.config.field_definitions || (selectedNode.config.intake_fields || []).map((k: string) => ({ id: k, canonical_key: k, label: k, data_type: 'text', is_required: true }))).map((field: any, idx: number) => {
                        const key = typeof field === 'string' ? field : field.canonical_key || field.label;
                        const label = typeof field === 'object' ? field.label || key : key;
                        const dType = typeof field === 'object' ? field.data_type || 'text' : 'text';
                        const req = typeof field === 'object' ? field.is_required !== false : true;
                        return (
                          <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-gray-900 border border-gray-800 text-xs">
                            <div className="flex items-center gap-1.5 mr-2">
                              <div className="flex flex-col">
                                <button
                                  onClick={() => handleMoveIntakeField(idx, 'up')}
                                  disabled={idx === 0}
                                  className="text-gray-500 hover:text-white disabled:opacity-20 p-0.5"
                                  title="Move Up"
                                >
                                  <ArrowUp className="h-2.5 w-2.5" />
                                </button>
                                <button
                                  onClick={() => handleMoveIntakeField(idx, 'down')}
                                  disabled={idx === (selectedNode.config.field_definitions || selectedNode.config.intake_fields || []).length - 1}
                                  className="text-gray-500 hover:text-white disabled:opacity-20 p-0.5"
                                  title="Move Down"
                                >
                                  <ArrowDown className="h-2.5 w-2.5" />
                                </button>
                              </div>
                              <div className="truncate">
                                <span className="text-white block font-medium truncate">{label}</span>
                                <div className="flex items-center gap-1 text-[9px] font-mono text-gray-400">
                                  <span>{key}</span>
                                  <span>•</span>
                                  <span className="text-purple-300">{dType}</span>
                                  {req ? (
                                    <span className="text-rose-400 font-sans">• Req</span>
                                  ) : (
                                    <span className="text-gray-500 font-sans">• Opt</span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <button
                              onClick={() => handleDeleteIntakeField(idx)}
                              className="text-gray-500 hover:text-rose-400 p-1"
                              title="Delete Field"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-gray-300">Deduplicate Across Templates</span>
                    <input
                      type="checkbox"
                      checked={selectedNode.config.deduplicate_fields !== false}
                      onChange={(e) => handleUpdateNodeConfig({ deduplicate_fields: e.target.checked })}
                      className="rounded bg-gray-900 border-gray-800 text-amber-500"
                    />
                  </div>
                </div>
              )}

              {/* 3b. Extract & Validate Node (OCR & Verification Rules) */}
              {selectedNode.type === 'extract_validate' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-[11px] text-cyan-300">
                    Extracts structured data from uploaded documents and checks confidence thresholds against validation schemas.
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-gray-300 font-semibold text-[11px]">Extraction Rules (CRUD)</label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowAddOcr(!showAddOcr)}
                        className="h-6 text-[10px] px-2 text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10"
                      >
                        <Plus className="h-3 w-3 mr-1" /> Add Rule
                      </Button>
                    </div>

                    {showAddOcr && (
                      <div className="p-2.5 rounded-xl bg-gray-900 border border-gray-800 space-y-2 mb-2">
                        <Input
                          placeholder="Target OCR Field (e.g. pan_number)"
                          value={newOcrField}
                          onChange={(e) => setNewOcrField(e.target.value)}
                          className="h-7 text-[11px] bg-gray-950 border-gray-800 text-white rounded-lg"
                        />
                        <Input
                          placeholder="Regex Pattern (e.g. ^[A-Z]{5}[0-9]{4}[A-Z]$)"
                          value={newOcrRegex}
                          onChange={(e) => setNewOcrRegex(e.target.value)}
                          className="h-7 text-[11px] bg-gray-950 border-gray-800 text-white font-mono rounded-lg"
                        />
                        <div className="flex items-center justify-between">
                          <label className="text-[10px] text-gray-400">Min Confidence: {(newOcrConfidence * 100).toFixed(0)}%</label>
                          <input
                            type="range"
                            min="0.5"
                            max="0.99"
                            step="0.05"
                            value={newOcrConfidence}
                            onChange={(e) => setNewOcrConfidence(parseFloat(e.target.value))}
                            className="w-28"
                          />
                        </div>
                        <div className="flex justify-end gap-1.5 pt-1">
                          <Button size="sm" variant="ghost" onClick={() => setShowAddOcr(false)} className="h-6 text-[10px] px-2 text-gray-400">
                            Cancel
                          </Button>
                          <Button size="sm" onClick={handleAddExtractionRule} className="h-6 text-[10px] px-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold">
                            Add Rule
                          </Button>
                        </div>
                      </div>
                    )}

                    <div className="space-y-1.5">
                      {(selectedNode.config.extraction_rules || [
                        { target_field: 'pan_number', validation_pattern: '^[A-Z]{5}[0-9]{4}[A-Z]$', min_confidence: 0.85 },
                        { target_field: 'degree_gpa', min_confidence: 0.80 },
                      ]).map((rule: any, idx: number) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-gray-900 border border-gray-800 text-xs">
                          <div className="truncate flex-1 mr-2">
                            <span className="text-white block font-mono font-medium truncate">{rule.target_field}</span>
                            <div className="flex items-center gap-1.5 text-[9px] text-gray-400 font-mono mt-0.5">
                              {rule.validation_pattern && <span className="text-cyan-300">regex: {rule.validation_pattern}</span>}
                              <span>•</span>
                              <span>min: {Math.round((rule.min_confidence || 0.85) * 100)}%</span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleDeleteExtractionRule(idx)}
                            className="text-gray-500 hover:text-rose-400 p-1"
                            title="Delete Rule"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 4. Candidate Email Node */}
              {selectedNode.type === 'candidate_email' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Subject Line</label>
                    <Input
                      value={selectedNode.config.subject || ''}
                      onChange={(e) => handleUpdateNodeConfig({ subject: e.target.value })}
                      className="h-8 text-xs bg-gray-900 border-gray-800 text-white rounded-xl"
                    />
                  </div>

                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Email Template</label>
                    <textarea
                      rows={4}
                      value={selectedNode.config.email_template || ''}
                      onChange={(e) => handleUpdateNodeConfig({ email_template: e.target.value })}
                      className="w-full bg-gray-900 border border-gray-800 text-xs text-gray-200 rounded-xl p-2 font-mono"
                    />
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-gray-300">Include Secure Candidate Portal Link</span>
                    <input
                      type="checkbox"
                      checked={selectedNode.config.include_portal_link !== false}
                      onChange={(e) => handleUpdateNodeConfig({ include_portal_link: e.target.checked })}
                      className="rounded bg-gray-900 border-gray-800 text-amber-500"
                    />
                  </div>
                </div>
              )}

              {/* 5. Approval Node */}
              {selectedNode.type === 'approval' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Required Sign-off Role</label>
                    <select
                      value={selectedNode.config.required_role || 'hr_director'}
                      onChange={(e) => handleUpdateNodeConfig({ required_role: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="hr_director">HR Director / Head of People</option>
                      <option value="vp_department">Department VP</option>
                      <option value="legal_counsel">General Legal Counsel</option>
                      <option value="ceo">Chief Executive Officer</option>
                    </select>
                  </div>

                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300">
                    Strict Governance: Sign-off is cryptographically bound to draft SHA-256. Any subsequent modification strictly invalidates approval.
                  </div>
                </div>
              )}

              {/* 6. HR Review Node */}
              {selectedNode.type === 'hr_review' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Reviewer Role</label>
                    <select
                      value={selectedNode.config.reviewer_role || 'hr_specialist'}
                      onChange={(e) => handleUpdateNodeConfig({ reviewer_role: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="hr_specialist">HR Operations Specialist</option>
                      <option value="talent_lead">Talent Acquisition Lead</option>
                      <option value="compensation_analyst">Total Rewards Analyst</option>
                    </select>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-gray-300">Invalidate Prior Approval on Edit</span>
                    <input
                      type="checkbox"
                      checked={selectedNode.config.invalidate_prior_approvals_on_edit !== false}
                      onChange={(e) => handleUpdateNodeConfig({ invalidate_prior_approvals_on_edit: e.target.checked })}
                      className="rounded bg-gray-900 border-gray-800 text-amber-500"
                    />
                  </div>
                </div>
              )}

              {/* 7. Condition / Branch Node */}
              {selectedNode.type === 'condition_branch' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Branch Routing Key</label>
                    <select
                      value={selectedNode.config.branch_attribute || 'employment_type'}
                      onChange={(e) => handleUpdateNodeConfig({ branch_attribute: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="employment_type">context.employment_type (permanent / contractor)</option>
                      <option value="department">context.department</option>
                      <option value="annual_ctc">context.annual_ctc (CTC bracket)</option>
                      <option value="relocation_needed">context.relocation_needed (Boolean)</option>
                    </select>
                  </div>
                  <p className="text-[10px] text-gray-500">
                    Outgoing connections from this node will route candidates conditionally based on candidate parameters.
                  </p>
                </div>
              )}

              {/* 8. Wait / Schedule Node */}
              {selectedNode.type === 'wait_schedule' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Wait Type</label>
                    <select
                      value={selectedNode.config.wait_type || 'interval'}
                      onChange={(e) => handleUpdateNodeConfig({ wait_type: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="interval">Relative Interval (Hours)</option>
                      <option value="specific_date">Specific Scheduled Date/Time</option>
                      <option value="candidate_start_date">Before Candidate Joining Date</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Target Timezone</label>
                    <select
                      value={selectedNode.config.timezone || 'Asia/Kolkata'}
                      onChange={(e) => handleUpdateNodeConfig({ timezone: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">America/New_York (EST)</option>
                      <option value="Europe/London">Europe/London (GMT)</option>
                    </select>
                  </div>
                </div>
              )}

              {/* 9. End Node */}
              {selectedNode.type === 'end' && (
                <div className="space-y-3 pt-2 border-t border-gray-850">
                  <div>
                    <label className="text-gray-400 block mb-1 text-[11px]">Final Candidate State</label>
                    <select
                      value={selectedNode.config.completion_state || 'hired'}
                      onChange={(e) => handleUpdateNodeConfig({ completion_state: e.target.value })}
                      className="w-full h-8 bg-gray-900 border border-gray-800 text-xs text-white rounded-xl px-2"
                    >
                      <option value="hired">Hired (Onboarding Completed)</option>
                      <option value="contract_active">Contractor Active</option>
                      <option value="offer_declined">Candidate Declined</option>
                    </select>
                  </div>
                </div>
              )}

              <div className="pt-4 border-t border-gray-850 flex justify-end">
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleDeleteNode(selectedNode.id)}
                  className="h-8 text-xs bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500 hover:text-white"
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1" /> Remove Node
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ─── 4. TEST RUN SIMULATOR DRAWER ──────────────────────────────────── */}
      {simDrawerOpen && (
        <div className="fixed inset-y-0 right-0 w-96 bg-gray-950 border-l border-gray-800 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-200">
          <div className="p-4 border-b border-gray-800 flex items-center justify-between bg-gray-900/80">
            <div className="flex items-center gap-2">
              <Play className="h-4 w-4 text-amber-500" />
              <h3 className="text-sm font-bold text-white">DAG Test Run Simulator</h3>
            </div>
            <Button size="sm" variant="ghost" onClick={() => setSimDrawerOpen(false)} className="h-7 w-7 p-0">
              <X className="h-4 w-4 text-gray-400" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            <p className="text-gray-400">
              Simulate visual graph traversal against sample candidate attributes. Traversed paths will highlight live on the canvas.
            </p>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-gray-300 font-semibold text-[11px]">Candidate Context (JSON)</label>
                <div className="flex gap-1.5">
                  <button
                    onClick={() =>
                      setSimContext(
                        JSON.stringify({ employment_type: 'permanent', department: 'Engineering', annual_ctc: 2400000 }, null, 2)
                      )
                    }
                    className="text-[10px] text-amber-400 hover:underline"
                  >
                    FTE Preset
                  </button>
                  <span className="text-gray-600">|</span>
                  <button
                    onClick={() =>
                      setSimContext(
                        JSON.stringify({ employment_type: 'contractor', department: 'DevOps', daily_rate: 12000 }, null, 2)
                      )
                    }
                    className="text-[10px] text-blue-400 hover:underline"
                  >
                    Contractor Preset
                  </button>
                </div>
              </div>
              <textarea
                rows={6}
                value={simContext}
                onChange={(e) => setSimContext(e.target.value)}
                className="w-full bg-gray-900 border border-gray-800 text-xs font-mono rounded-xl p-2.5 text-gray-200"
              />
            </div>

            <Button
              onClick={handleRunSimulation}
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs h-9 rounded-xl flex items-center justify-center gap-2"
            >
              <Play className="h-3.5 w-3.5 fill-black" />
              Execute Graph Traversal
            </Button>

            {simTraversedPath.length > 0 && (
              <div className="space-y-3 pt-3 border-t border-gray-850">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 flex items-center justify-between text-emerald-400 font-semibold">
                  <span>✓ Path Traversed</span>
                  <span>{simTraversedPath.length} Nodes</span>
                </div>

                <div>
                  <span className="text-gray-400 font-semibold block mb-1">Evaluated Documents:</span>
                  <div className="space-y-1">
                    {simEvaluatedDocs.map((doc, idx) => (
                      <div key={idx} className="p-2 rounded-lg bg-gray-900 border border-gray-800 text-gray-200 flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                        <span className="truncate">{doc}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <span className="text-gray-400 font-semibold block mb-1">Synthesized Candidate Fields:</span>
                  <div className="flex flex-wrap gap-1">
                    {simSynthesizedFields.map((f, idx) => (
                      <span key={idx} className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-amber-300">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── 5. AI PIPELINE ARCHITECT PROMPT MODAL (BULLETPROOF OVERLAY) ─────── */}
      {aiPromptDialogOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-[99999] flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm overflow-y-auto"
          onClick={(e) => {
            if (e.target === e.currentTarget && !aiGenerating) {
              setAiPromptDialogOpen(false);
            }
          }}
        >
          <div
            className="relative w-full max-w-2xl bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl p-6 text-white my-auto flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-gray-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <Wand2 className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    AI Pipeline Architect
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                      Prompt-to-DAG
                    </span>
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Describe any hiring, onboarding, or document workflow. The AI synthesizes a full DAG with stages, forms, OCR extractions, approvals, and contract templates.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => !aiGenerating && setAiPromptDialogOpen(false)}
                className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-gray-800 transition-colors"
                title="Close (Esc)"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Body */}
            <div className="space-y-4 py-1">
              <div>
                <label className="text-xs font-semibold text-gray-300 block mb-1.5">
                  Target Requisition / Role Title
                </label>
                <Input
                  value={aiJobRole}
                  onChange={(e) => setAiJobRole(e.target.value)}
                  placeholder="e.g. Python Backend Developer, DevOps Engineer, Lead Architect"
                  className="h-10 text-xs bg-gray-900 border-gray-800 text-white rounded-xl focus:border-indigo-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-gray-300">
                    Paste / Write Workflow Requirements Prompt
                  </label>
                  <span className="text-[10px] text-gray-500 font-mono">
                    {aiPromptText.length} characters
                  </span>
                </div>
                <textarea
                  rows={5}
                  value={aiPromptText}
                  onChange={(e) => setAiPromptText(e.target.value)}
                  placeholder="Paste what workflow you want (e.g. Build an engineering onboarding flow with code submission, PAN/Aadhaar OCR extraction, VP approval, and employment agreement generation)..."
                  className="w-full bg-gray-900 border border-gray-800 text-xs text-gray-200 rounded-xl p-3.5 font-sans focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all leading-relaxed resize-none shadow-inner"
                />
              </div>

              {/* Quick Prompt Presets */}
              <div className="space-y-2">
                <span className="text-[11px] text-gray-400 font-medium flex items-center gap-1.5">
                  <Sparkles className="h-3 w-3 text-indigo-400" />
                  Quick Enterprise Presets (Click to Load):
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setAiJobRole('Python Backend Developer');
                      setAiPromptText('Build an engineering hiring workflow for Python Backend Developers with technical assignment submission, AI extraction of GitHub/Pan/experience, executive approval by VP of Eng, and NDA + offer generation');
                    }}
                    className="p-2.5 bg-gray-900/80 hover:bg-gray-900 border border-gray-800 hover:border-indigo-500/50 rounded-xl text-left transition-all group"
                  >
                    <div className="text-xs font-semibold text-gray-200 group-hover:text-indigo-300">
                      🐍 Python Backend
                    </div>
                    <div className="text-[10px] text-gray-400 mt-1 line-clamp-2">
                      Assignment submission, GitHub/PAN OCR, VP sign-off, NDA & Offer
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setAiJobRole('Lead Architect');
                      setAiPromptText('Create an executive hiring workflow for Lead Architects with credential verification, compensation committee approval, background check document uploads, and executive employment agreement generation');
                    }}
                    className="p-2.5 bg-gray-900/80 hover:bg-gray-900 border border-gray-800 hover:border-indigo-500/50 rounded-xl text-left transition-all group"
                  >
                    <div className="text-xs font-semibold text-gray-200 group-hover:text-indigo-300">
                      🏛 Lead Architect
                    </div>
                    <div className="text-[10px] text-gray-400 mt-1 line-clamp-2">
                      Credential check, Comp Committee, Executive agreement
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setAiJobRole('Contract Backend Engineer');
                      setAiPromptText('Design a rapid contractor onboarding pipeline with GST/tax extraction, legal review, and Independent Contractor MSA contract generation');
                    }}
                    className="p-2.5 bg-gray-900/80 hover:bg-gray-900 border border-gray-800 hover:border-indigo-500/50 rounded-xl text-left transition-all group"
                  >
                    <div className="text-xs font-semibold text-gray-200 group-hover:text-indigo-300">
                      ⚡ Contractor MSA
                    </div>
                    <div className="text-[10px] text-gray-400 mt-1 line-clamp-2">
                      GST/Tax extraction, Legal review, Independent Contractor MSA
                    </div>
                  </button>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-800 pt-4 mt-1">
              <span className="text-[11px] text-gray-500 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                Human-in-the-loop: Produces draft DAG in canvas for instant review & editing
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setAiPromptDialogOpen(false)}
                  className="h-9 px-4 text-xs text-gray-400 hover:text-white rounded-xl"
                  disabled={aiGenerating}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleAiGeneratePipeline}
                  disabled={aiGenerating || !aiPromptText.trim()}
                  className="h-9 px-4 text-xs bg-indigo-600 hover:bg-indigo-500 text-white font-bold flex items-center gap-2 shadow-md shadow-indigo-600/20 rounded-xl disabled:opacity-50"
                >
                  {aiGenerating ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Synthesizing Graph...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      Synthesize Pipeline DAG
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

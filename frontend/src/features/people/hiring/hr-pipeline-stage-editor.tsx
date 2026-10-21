'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';
import {
  GitBranch,
  Plus,
  Trash2,
  Save,
  Loader2,
  FileText,
  ShieldCheck,
  CheckCircle2,
  ChevronUp,
  ChevronDown,
  Layers,
  Sparkles,
  UploadCloud,
  Check,
  X,
  AlertCircle,
  HelpCircle,
  Mail,
  Send,
  UserCheck,
  Play,
  RotateCcw,
} from 'lucide-react';

export interface StageNode {
  id: string;
  name: string;
  type: string;
  position?: { x: number; y: number };
  config: Record<string, any>;
}

export interface StageEdge {
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

interface HRPipelineStageEditorProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  workflowId: string | null;
  availableTemplates?: PublishedTemplate[];
  onWorkflowUpdated?: (updatedWf: any) => void;
  onSwitchToCanvas?: () => void;
}

const STAGE_TYPES = [
  {
    type: 'start',
    label: 'Candidate Information Intake',
    kind: 'Intake',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    icon: Play,
    desc: 'Collects candidate profile, legal identification, and intake questions via secure portal.',
    defaultConfig: {
      trigger_type: 'manual',
      auto_start_on_candidate_creation: true,
      intake_fields: [
        { key: 'candidate.full_name', label: 'Full Legal Name', is_required: true },
        { key: 'candidate.email', label: 'Email Address', is_required: true },
        { key: 'candidate.phone', label: 'Phone Number', is_required: true },
        { key: 'candidate.current_address', label: 'Residential Address', is_required: true },
        { key: 'candidate.pan_number', label: 'PAN / Tax ID', is_required: true },
      ],
    },
  },
  {
    type: 'candidate_upload',
    label: 'Required Document Evidence',
    kind: 'Documents',
    badgeColor: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    icon: UploadCloud,
    desc: 'HR decides which proof files (Government ID, Tax Proof, Degree, Relieving letter) are required.',
    defaultConfig: {
      required_documents: [
        { title: 'Government Photo ID', category: 'passport', is_mandatory: true, description: 'Passport, Aadhaar, or National ID' },
        { title: 'Tax Proof / PAN Card', category: 'tax_form', is_mandatory: true, description: 'PAN card or national tax proof' },
        { title: 'Educational Certificate', category: 'degree_certificate', is_mandatory: true, description: 'Highest degree certificate or transcript' },
      ],
      allowed_formats: ['application/pdf', 'image/jpeg', 'image/png'],
      deadline_days: 5,
    },
  },
  {
    type: 'condition_branch',
    label: 'Employment Type Routing',
    kind: 'Routing',
    badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    icon: GitBranch,
    desc: 'Routes permanent hires to FTE Employment Agreement, and contractors to Independent Contractor MSA.',
    defaultConfig: {
      branch_attribute: 'employment_type',
      branches: [
        { label: 'Permanent FTE', condition: "context.employment_type == 'permanent'" },
        { label: 'Independent Contractor', condition: "context.employment_type == 'contractor'" },
      ],
    },
  },
  {
    type: 'generate_document',
    label: 'Offer & Agreement Generation',
    kind: 'Generate',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    icon: FileText,
    desc: 'Fills the official DOCX/HTML legal templates with reconciled candidate & company values.',
    defaultConfig: {
      template_name: 'Executive Employment Agreement',
      output_format: 'both',
      missing_data_policy: 'route_to_hr',
      field_mappings: {
        candidate_name: 'candidate.full_name',
        annual_ctc: 'company_fields.annual_ctc',
        role_title: 'company_fields.role_title',
      },
    },
  },
  {
    type: 'approval',
    label: 'HR Sign-off & Cryptographic Binding',
    kind: 'Review Gate',
    badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    icon: ShieldCheck,
    desc: 'Authorized HR director signs off on the finalized document draft bound to its SHA-256 seal.',
    defaultConfig: {
      required_role: 'hr_director',
      approval_policy: 'strict_sha_binding',
      timeout_hours: 48,
    },
  },
  {
    type: 'candidate_email',
    label: 'Automated Candidate Dispatch',
    kind: 'Dispatch',
    badgeColor: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    icon: Mail,
    desc: 'Dispatches finalized offer packet and secure sign-off link directly to the candidate.',
    defaultConfig: {
      subject: 'Offer of Employment — Formal Acceptance Package',
      email_template: 'Dear {{ candidate.full_name }},\n\nWe are pleased to extend this formal offer of employment. Please review and sign your offer packet via the portal link below.',
      include_portal_link: true,
    },
  },
  {
    type: 'end',
    label: 'Complete Hire & Profile Provisioning',
    kind: 'Complete',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    icon: CheckCircle2,
    desc: 'Candidate receives acceptance package and employee profile is provisioned in core HR systems.',
    defaultConfig: {
      completion_state: 'hired',
      sync_to_payroll: true,
      notify_participants: true,
    },
  },
];

const PRESET_INTAKE_FIELDS = [
  { key: 'candidate.full_name', label: 'Full Legal Name' },
  { key: 'candidate.email', label: 'Email Address' },
  { key: 'candidate.phone', label: 'Phone Number' },
  { key: 'candidate.current_address', label: 'Residential Address' },
  { key: 'candidate.pan_number', label: 'PAN / Tax ID' },
  { key: 'candidate.dob', label: 'Date of Birth' },
  { key: 'candidate.emergency_contact', label: 'Emergency Contact' },
  { key: 'candidate.bank_account', label: 'Bank Account & IFSC' },
];

const PRESET_DOCUMENTS = [
  { title: 'Government Photo ID', category: 'passport', desc: 'Passport, Aadhaar, or Driver’s License' },
  { title: 'Tax / PAN Document', category: 'tax_form', desc: 'PAN Card or National Tax Certificate' },
  { title: 'Educational Certificate', category: 'degree_certificate', desc: 'Highest Degree Certificate or Official Transcript' },
  { title: 'Relieving & Experience Letter', category: 'relieving_letter', desc: 'Relieving letter or service certificate from previous employer' },
  { title: 'Bank Cancelled Cheque', category: 'bank_proof', desc: 'Cancelled cheque or bank account statement for salary setup' },
];

export default function HRPipelineStageEditor({
  API_URL,
  fetchWithAuth,
  workflowId,
  availableTemplates = [],
  onWorkflowUpdated,
  onSwitchToCanvas,
}: HRPipelineStageEditorProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [workflowName, setWorkflowName] = useState('Standard Autonomous Onboarding Flow');
  const [workflowVersion, setWorkflowVersion] = useState(1);
  const [nodes, setNodes] = useState<StageNode[]>([]);
  const [edges, setEdges] = useState<StageEdge[]>([]);
  const [selectedStageId, setSelectedStageId] = useState<string>('');

  // Add Stage Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newStageType, setNewStageType] = useState('candidate_upload');
  const [newStageTitle, setNewStageTitle] = useState('');
  const [newStageDesc, setNewStageDesc] = useState('');
  const [newStagePosition, setNewStagePosition] = useState<'end' | 'after_selected'>('end');

  // New Intake Field Input State
  const [customFieldLabel, setCustomFieldLabel] = useState('');
  const [customFieldKey, setCustomFieldKey] = useState('');
  const [customFieldRequired, setCustomFieldRequired] = useState(true);

  // New Document Input State
  const [customDocTitle, setCustomDocTitle] = useState('');
  const [customDocCategory, setCustomDocCategory] = useState('passport');
  const [customDocDesc, setCustomDocDesc] = useState('');
  const [customDocMandatory, setCustomDocMandatory] = useState(true);

  // Load workflow definition
  const loadWorkflow = useCallback(async () => {
    if (!workflowId) return;
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/workflow/definitions/${workflowId}`);
      if (res.ok) {
        const data = await res.json();
        setWorkflowName(data.name || 'Standard Autonomous Onboarding Flow');
        setWorkflowVersion(data.version || 1);
        const rawNodes = (data.graph_schema?.nodes || []) as any[];
        const rawEdges = (data.graph_schema?.edges || []) as any[];

        if (rawNodes.length > 0) {
          // Sort nodes in topological/sequential order
          const orderedNodes = sortNodesSequentially(rawNodes, rawEdges);
          setNodes(orderedNodes);
          setEdges(rawEdges);
          setSelectedStageId((prev) => (orderedNodes.some((n) => n.id === prev) ? prev : orderedNodes[0]?.id || ''));
        }
        setIsDirty(false);
      }
    } catch {
      notify.error('Could not load workflow stages.');
    } finally {
      setLoading(false);
    }
  }, [API_URL, fetchWithAuth, workflowId]);

  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);

  // Helper: Sort nodes sequentially based on edges
  const sortNodesSequentially = (rawNodes: StageNode[], rawEdges: StageEdge[]): StageNode[] => {
    if (rawNodes.length <= 1) return rawNodes;

    const nodeMap = new Map(rawNodes.map((n) => [n.id, n]));
    const targetSet = new Set(rawEdges.map((e) => e.target));
    const edgesFrom = new Map<string, string[]>();
    rawEdges.forEach((e) => {
      const list = edgesFrom.get(e.source) || [];
      list.push(e.target);
      edgesFrom.set(e.source, list);
    });

    // Find start nodes (nodes not targeted by any edge, or type 'start')
    const startNodes = rawNodes.filter((n) => !targetSet.has(n.id) || n.type === 'start');
    const startId = startNodes[0]?.id || rawNodes[0].id;

    const visited = new Set<string>();
    const ordered: StageNode[] = [];
    const queue: string[] = [startId];

    while (queue.length > 0) {
      const currId = queue.shift()!;
      if (visited.has(currId)) continue;
      visited.add(currId);
      const node = nodeMap.get(currId);
      if (node) ordered.push(node);

      const nextIds = edgesFrom.get(currId) || [];
      nextIds.forEach((tId) => {
        if (!visited.has(tId) && !queue.includes(tId)) {
          queue.push(tId);
        }
      });
    }

    // Append any unvisited nodes
    rawNodes.forEach((n) => {
      if (!visited.has(n.id)) {
        ordered.push(n);
      }
    });

    return ordered;
  };

  // Re-build sequential edges whenever node order or count changes
  const rebuildSequentialEdges = (newNodes: StageNode[]): StageEdge[] => {
    const newEdges: StageEdge[] = [];
    for (let i = 0; i < newNodes.length - 1; i++) {
      const src = newNodes[i].id;
      const tgt = newNodes[i + 1].id;
      newEdges.push({
        id: `e_${src}_${tgt}`,
        source: src,
        target: tgt,
      });
    }
    return newEdges;
  };

  // Currently selected stage
  const selectedStage = useMemo(() => {
    return nodes.find((n) => n.id === selectedStageId) || nodes[0] || null;
  }, [nodes, selectedStageId]);

  // Stage type metadata helper
  const getStageMeta = (type: string) => {
    return STAGE_TYPES.find((t) => t.type === type) || {
      type,
      label: type.replace('_', ' ').toUpperCase(),
      kind: type,
      badgeColor: 'bg-muted text-foreground border-border',
      icon: GitBranch,
      desc: 'Configurable pipeline stage',
      defaultConfig: {},
    };
  };

  // --- ACTIONS: UPDATE STAGE ---
  const handleUpdateStage = (stageId: string, updates: Partial<StageNode>) => {
    setNodes((prev) =>
      prev.map((n) => {
        if (n.id !== stageId) return n;
        return {
          ...n,
          ...updates,
          config: {
            ...n.config,
            ...(updates.config || {}),
          },
        };
      })
    );
    setIsDirty(true);
  };

  // --- ACTIONS: REORDER STAGE ---
  const handleMoveStage = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === nodes.length - 1) return;

    const newIndex = direction === 'up' ? index - 1 : index + 1;
    const newNodes = [...nodes];
    const [moved] = newNodes.splice(index, 1);
    newNodes.splice(newIndex, 0, moved);

    // Update positions x coordinates sequentially
    const repositioned = newNodes.map((n, idx) => ({
      ...n,
      position: { x: idx * 260 + 60, y: 180 },
    }));

    const newEdges = rebuildSequentialEdges(repositioned);
    setNodes(repositioned);
    setEdges(newEdges);
    setIsDirty(true);
    notify.info(`Stage moved ${direction}.`);
  };

  // --- ACTIONS: DELETE STAGE ---
  const handleDeleteStage = (stageId: string) => {
    if (nodes.length <= 1) {
      notify.error('Pipeline must contain at least one stage.');
      return;
    }
    const nodeToDelete = nodes.find((n) => n.id === stageId);
    if (!window.confirm(`Are you sure you want to remove the stage "${nodeToDelete?.name || 'Selected Stage'}"?`)) {
      return;
    }

    const filtered = nodes.filter((n) => n.id !== stageId);
    const repositioned = filtered.map((n, idx) => ({
      ...n,
      position: { x: idx * 260 + 60, y: 180 },
    }));

    const newEdges = rebuildSequentialEdges(repositioned);
    setNodes(repositioned);
    setEdges(newEdges);
    if (selectedStageId === stageId) {
      setSelectedStageId(repositioned[0]?.id || '');
    }
    setIsDirty(true);
    notify.success('Stage removed from pipeline.');
  };

  // --- ACTIONS: ADD NEW STAGE ---
  const handleAddStageSubmit = () => {
    const meta = getStageMeta(newStageType);
    const stageId = `step_${Date.now()}`;
    const stageTitle = newStageTitle.trim() || `${nodes.length + 1}. ${meta.label}`;
    const stageDesc = newStageDesc.trim() || meta.desc;

    const newStage: StageNode = {
      id: stageId,
      name: stageTitle,
      type: newStageType,
      config: JSON.parse(JSON.stringify(meta.defaultConfig || {})),
    };

    let updatedList: StageNode[] = [];
    if (newStagePosition === 'after_selected' && selectedStageId) {
      const idx = nodes.findIndex((n) => n.id === selectedStageId);
      if (idx !== -1) {
        updatedList = [...nodes.slice(0, idx + 1), newStage, ...nodes.slice(idx + 1)];
      } else {
        updatedList = [...nodes, newStage];
      }
    } else {
      updatedList = [...nodes, newStage];
    }

    const repositioned = updatedList.map((n, idx) => ({
      ...n,
      position: { x: idx * 260 + 60, y: 180 },
    }));

    const newEdges = rebuildSequentialEdges(repositioned);
    setNodes(repositioned);
    setEdges(newEdges);
    setSelectedStageId(stageId);
    setIsDirty(true);
    setIsAddModalOpen(false);
    setNewStageTitle('');
    setNewStageDesc('');
    notify.success(`Added new stage: ${stageTitle}`);
  };

  // --- SAVE & SYNC WORKFLOW ---
  const handleSaveAndSync = async () => {
    if (!workflowId) {
      notify.error('No workflow selected to save.');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: workflowName,
        graph_schema: {
          nodes: nodes.map((n, idx) => ({
            id: n.id,
            name: n.name,
            type: n.type,
            position: n.position || { x: idx * 260 + 60, y: 180 },
            config: n.config || {},
          })),
          edges: edges,
        },
      };

      const res = await fetchWithAuth(`${API_URL}/hr/workflow/definitions/${workflowId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const msg = err.detail?.errors?.join('; ') || err.detail || 'Failed to save pipeline.';
        notify.error(msg);
        return;
      }

      const updated = await res.json();
      setIsDirty(false);
      setWorkflowVersion(updated.version || workflowVersion);
      notify.success('Pipeline stages synchronized with workflow definition & visual canvas!');
      if (onWorkflowUpdated) {
        onWorkflowUpdated(updated);
      }
    } catch {
      notify.error('Network error saving pipeline.');
    } finally {
      setSaving(false);
    }
  };

  // --- INTAKE FIELDS EDITING ---
  const intakeFields = (selectedStage?.config?.intake_fields || []) as Array<{
    key: string;
    label: string;
    is_required: boolean;
  }>;

  const handleAddIntakeField = (label: string, key?: string, isRequired = true) => {
    if (!label.trim()) return;
    const finalKey = key || `candidate.${label.toLowerCase().replace(/[^a-z0-9]/g, '_').slice(0, 32)}`;
    const currentFields = [...intakeFields];
    if (currentFields.some((f) => f.key === finalKey)) {
      notify.error('Field key already exists in this intake stage.');
      return;
    }
    const updated = [...currentFields, { key: finalKey, label: label.trim(), is_required: isRequired }];
    handleUpdateStage(selectedStage!.id, {
      config: { ...selectedStage!.config, intake_fields: updated },
    });
    setCustomFieldLabel('');
    setCustomFieldKey('');
  };

  const handleToggleIntakeFieldRequired = (key: string) => {
    const updated = intakeFields.map((f) => (f.key === key ? { ...f, is_required: !f.is_required } : f));
    handleUpdateStage(selectedStage!.id, {
      config: { ...selectedStage!.config, intake_fields: updated },
    });
  };

  const handleDeleteIntakeField = (key: string) => {
    const updated = intakeFields.filter((f) => f.key !== key);
    handleUpdateStage(selectedStage!.id, {
      config: { ...selectedStage!.config, intake_fields: updated },
    });
  };

  // --- DOCUMENT EVIDENCE EDITING ---
  const requiredDocs = (selectedStage?.config?.required_documents || []) as Array<{
    title: string;
    category?: string;
    description?: string;
    is_mandatory: boolean;
  }>;

  const handleAddRequiredDoc = (title: string, category = 'passport', desc = '', isMandatory = true) => {
    if (!title.trim()) return;
    const currentDocs = [...requiredDocs];
    const updated = [
      ...currentDocs,
      {
        title: title.trim(),
        category,
        description: desc.trim() || 'Upload official proof document',
        is_mandatory: isMandatory,
      },
    ];
    handleUpdateStage(selectedStage!.id, {
      config: { ...selectedStage!.config, required_documents: updated },
    });
    setCustomDocTitle('');
    setCustomDocDesc('');
  };

  const handleToggleDocMandatory = (index: number) => {
    const updated = requiredDocs.map((d, i) => (i === index ? { ...d, is_mandatory: !d.is_mandatory } : d));
    handleUpdateStage(selectedStage!.id, {
      config: { ...selectedStage!.config, required_documents: updated },
    });
  };

  const handleDeleteRequiredDoc = (index: number) => {
    const updated = requiredDocs.filter((_, i) => i !== index);
    handleUpdateStage(selectedStage!.id, {
      config: { ...selectedStage!.config, required_documents: updated },
    });
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-2">
        <Loader2 className="size-5 animate-spin text-primary" />
        <span>Loading pipeline stages…</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ── TOP ACTION BAR ── */}
      <div className="rounded-xl border border-border bg-card p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <GitBranch size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">{workflowName}</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-muted text-muted-foreground border border-border">
                v{workflowVersion}
              </span>
              {isDirty ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                  Unsaved Changes
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <Check size={10} /> Synced with Canvas
                </span>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground">
              {nodes.length} Deterministic Stages • Drag-free visual ordering • Reorder &amp; configure in real time
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onSwitchToCanvas && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onSwitchToCanvas}
              className="h-8 text-xs font-semibold flex items-center gap-1.5"
            >
              <Layers size={13} />
              <span>Visual n8n Canvas</span>
            </Button>
          )}

          <Button
            type="button"
            size="sm"
            onClick={() => setIsAddModalOpen(true)}
            className="h-8 text-xs font-bold bg-surface-hover hover:bg-muted text-foreground border border-border flex items-center gap-1"
          >
            <Plus size={13} />
            <span>Add Stage</span>
          </Button>

          <Button
            type="button"
            size="sm"
            onClick={handleSaveAndSync}
            disabled={saving || !isDirty}
            className={`h-8 text-xs font-bold flex items-center gap-1.5 transition-all ${
              isDirty
                ? 'bg-primary text-primary-foreground shadow-sm hover:brightness-110'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            }`}
          >
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            <span>Save &amp; Sync</span>
          </Button>
        </div>
      </div>

      {/* ── MAIN 2-COLUMN LAYOUT ── */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
        {/* Left Column: Stage List */}
        <div className="space-y-3">
          <div className="rounded-xl border border-border bg-card p-4">
            <h3 className="text-sm font-semibold text-foreground">Standard Autonomous Onboarding Flow</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Each stage in this pipeline executes deterministically for every hired candidate. Select a stage to view rules and configurations.
            </p>
          </div>

          <ol className="space-y-2">
            {nodes.map((stage, idx) => {
              const active = stage.id === selectedStage?.id;
              const meta = getStageMeta(stage.type);

              return (
                <li key={stage.id}>
                  <div
                    onClick={() => setSelectedStageId(stage.id)}
                    className={`group flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-all cursor-pointer ${
                      active
                        ? 'border-primary bg-primary/5 shadow-2xs ring-1 ring-primary/20'
                        : 'border-border bg-card hover:bg-surface-hover'
                    }`}
                  >
                    {/* Index Number */}
                    <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border border-border bg-card text-xs font-semibold text-foreground">
                      {idx + 1}
                    </span>

                    {/* Content */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-foreground">{stage.name}</span>
                        <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold border ${meta.badgeColor}`}>
                          {meta.kind}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                        {stage.config?.desc || meta.desc}
                      </p>
                    </div>

                    {/* Reorder and Delete Controls */}
                    <div
                      className="flex items-center gap-1 opacity-80 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        onClick={() => handleMoveStage(idx, 'up')}
                        disabled={idx === 0}
                        title="Move Up"
                        className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground disabled:opacity-20 disabled:hover:bg-transparent"
                      >
                        <ChevronUp size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMoveStage(idx, 'down')}
                        disabled={idx === nodes.length - 1}
                        title="Move Down"
                        className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground disabled:opacity-20 disabled:hover:bg-transparent"
                      >
                        <ChevronDown size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteStage(stage.id)}
                        title="Delete Stage"
                        className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors ml-1"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>

          {/* Quick Add Stage Button at Bottom of List */}
          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="w-full py-2.5 rounded-xl border border-dashed border-border hover:border-primary/50 bg-card/40 hover:bg-primary/5 text-xs font-semibold text-muted-foreground hover:text-primary transition-all flex items-center justify-center gap-2"
          >
            <Plus size={14} />
            <span>Add Pipeline Stage</span>
          </button>
        </div>

        {/* Right Column: Stage Properties Panel */}
        <div className="space-y-4">
          {selectedStage ? (
            <section className="rounded-xl border border-border bg-card p-5 space-y-4 shadow-xs">
              {/* Properties Header */}
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <GitBranch className="size-4 text-primary" />
                  <h3 className="text-sm font-semibold text-foreground">Stage Properties</h3>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground">ID: {selectedStage.id}</span>
              </div>

              {/* Basic Details: Title & Description */}
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] font-bold text-muted-foreground uppercase">Stage Title</label>
                  <Input
                    value={selectedStage.name}
                    onChange={(e) => handleUpdateStage(selectedStage.id, { name: e.target.value })}
                    className="h-8 mt-1 text-xs bg-surface-hover/50 border-border font-semibold text-foreground"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-muted-foreground uppercase">Stage Type / Kind</label>
                  <select
                    value={selectedStage.type}
                    onChange={(e) => {
                      const newType = e.target.value;
                      const newMeta = getStageMeta(newType);
                      handleUpdateStage(selectedStage.id, {
                        type: newType,
                        config: {
                          ...newMeta.defaultConfig,
                          ...selectedStage.config,
                        },
                      });
                    }}
                    className="w-full h-8 mt-1 px-2.5 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {STAGE_TYPES.map((t) => (
                      <option key={t.type} value={t.type}>
                        {t.label} ({t.kind})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* ── TYPE SPECIFIC EDITOR ── */}

              {/* 1. Candidate Information Intake (`start` or `ai_form_generator`) */}
              {(selectedStage.type === 'start' || selectedStage.type === 'ai_form_generator') && (
                <div className="space-y-3 text-xs pt-2 border-t border-border">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-foreground">Intake Fields Synthesized for Candidate:</span>
                    <span className="text-[10px] text-muted-foreground">{intakeFields.length} fields</span>
                  </div>

                  {/* List of Fields */}
                  <div className="space-y-1.5 max-h-[260px] overflow-y-auto pr-0.5">
                    {intakeFields.map((f) => (
                      <div
                        key={f.key}
                        className="p-2 rounded-lg bg-surface-hover/50 border border-border flex items-center justify-between gap-2"
                      >
                        <div className="min-w-0 flex-1">
                          <span className="font-medium text-foreground block truncate">{f.label}</span>
                          <span className="text-[10px] font-mono text-muted-foreground block truncate">{f.key}</span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleToggleIntakeFieldRequired(f.key)}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-colors ${
                              f.is_required
                                ? 'bg-primary/10 text-primary border-primary/30'
                                : 'bg-muted text-muted-foreground border-border'
                            }`}
                          >
                            {f.is_required ? 'Required' : 'Optional'}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteIntakeField(f.key)}
                            className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Add Field Row */}
                  <div className="p-2.5 rounded-lg bg-muted/40 border border-border space-y-2">
                    <span className="text-[11px] font-bold text-foreground flex items-center gap-1">
                      <Plus size={11} /> Add Intake Field
                    </span>
                    <div className="flex items-center gap-1.5">
                      <Input
                        value={customFieldLabel}
                        onChange={(e) => setCustomFieldLabel(e.target.value)}
                        placeholder="Field Label (e.g. Passport Number)"
                        className="h-7 text-xs bg-card border-border flex-1"
                      />
                      <label className="flex items-center gap-1 text-[11px] text-muted-foreground cursor-pointer shrink-0">
                        <input
                          type="checkbox"
                          checked={customFieldRequired}
                          onChange={(e) => setCustomFieldRequired(e.target.checked)}
                          className="rounded border-border text-primary focus:ring-primary size-3.5"
                        />
                        <span>Req</span>
                      </label>
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => handleAddIntakeField(customFieldLabel, customFieldKey, customFieldRequired)}
                        className="h-7 px-2.5 text-xs font-bold"
                      >
                        Add
                      </Button>
                    </div>

                    {/* Quick Preset Chips */}
                    <div className="pt-1">
                      <span className="text-[10px] text-muted-foreground block mb-1">Quick Presets:</span>
                      <div className="flex flex-wrap gap-1">
                        {PRESET_INTAKE_FIELDS.map((preset) => {
                          const exists = intakeFields.some((f) => f.key === preset.key);
                          if (exists) return null;
                          return (
                            <button
                              key={preset.key}
                              type="button"
                              onClick={() => handleAddIntakeField(preset.label, preset.key, true)}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-card hover:bg-primary/10 hover:text-primary border border-border transition-colors text-muted-foreground"
                            >
                              + {preset.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  <p className="text-[11px] text-muted-foreground pt-1 flex items-center gap-1">
                    <CheckCircle2 size={12} className="text-primary shrink-0" />
                    <span>Candidate values are automatically checked against OCR evidence for conflicts.</span>
                  </p>
                </div>
              )}

              {/* 2. Required Document Evidence (`candidate_upload`) */}
              {selectedStage.type === 'candidate_upload' && (
                <div className="space-y-3 text-xs pt-2 border-t border-border">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-foreground">Default Document Verification Checklist:</span>
                    <span className="text-[10px] text-muted-foreground">{requiredDocs.length} items</span>
                  </div>

                  {/* List of Documents */}
                  <div className="space-y-1.5 max-h-[260px] overflow-y-auto pr-0.5">
                    {requiredDocs.map((doc, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded-lg bg-surface-hover/50 border border-border flex items-center justify-between gap-2"
                      >
                        <div className="min-w-0 flex-1">
                          <span className="font-medium text-foreground block truncate">{doc.title}</span>
                          {doc.description && (
                            <span className="text-[10px] text-muted-foreground block truncate">{doc.description}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleToggleDocMandatory(idx)}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border transition-colors ${
                              doc.is_mandatory
                                ? 'bg-[#64B99A]/10 text-[#64B99A] border-[#64B99A]/30'
                                : 'bg-muted text-muted-foreground border-border'
                            }`}
                          >
                            {doc.is_mandatory ? 'Mandatory' : 'Optional'}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteRequiredDoc(idx)}
                            className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Add Document Row */}
                  <div className="p-2.5 rounded-lg bg-muted/40 border border-border space-y-2">
                    <span className="text-[11px] font-bold text-foreground flex items-center gap-1">
                      <Plus size={11} /> Add Document Requirement
                    </span>
                    <div className="space-y-1.5">
                      <Input
                        value={customDocTitle}
                        onChange={(e) => setCustomDocTitle(e.target.value)}
                        placeholder="Document Title (e.g. Experience Certificate)"
                        className="h-7 text-xs bg-card border-border"
                      />
                      <div className="flex items-center gap-1.5">
                        <select
                          value={customDocCategory}
                          onChange={(e) => setCustomDocCategory(e.target.value)}
                          className="h-7 px-2 rounded bg-card border border-border text-[11px] text-foreground flex-1"
                        >
                          <option value="passport">Government ID / Passport</option>
                          <option value="tax_form">Tax Proof / PAN</option>
                          <option value="degree_certificate">Educational Degree</option>
                          <option value="relieving_letter">Relieving / Experience</option>
                          <option value="bank_proof">Bank Proof</option>
                          <option value="other">Other Document</option>
                        </select>
                        <label className="flex items-center gap-1 text-[11px] text-muted-foreground cursor-pointer shrink-0">
                          <input
                            type="checkbox"
                            checked={customDocMandatory}
                            onChange={(e) => setCustomDocMandatory(e.target.checked)}
                            className="rounded border-border text-[#64B99A] focus:ring-[#64B99A] size-3.5"
                          />
                          <span>Mandatory</span>
                        </label>
                        <Button
                          type="button"
                          size="sm"
                          onClick={() => handleAddRequiredDoc(customDocTitle, customDocCategory, customDocDesc, customDocMandatory)}
                          className="h-7 px-2.5 text-xs font-bold"
                        >
                          Add
                        </Button>
                      </div>
                    </div>

                    {/* Quick Presets */}
                    <div className="pt-1">
                      <span className="text-[10px] text-muted-foreground block mb-1">Quick Presets:</span>
                      <div className="flex flex-wrap gap-1">
                        {PRESET_DOCUMENTS.map((preset) => {
                          const exists = requiredDocs.some((d) => d.title.toLowerCase() === preset.title.toLowerCase());
                          if (exists) return null;
                          return (
                            <button
                              key={preset.title}
                              type="button"
                              onClick={() => handleAddRequiredDoc(preset.title, preset.category, preset.desc, true)}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-card hover:bg-sky-500/10 hover:text-sky-400 border border-border transition-colors text-muted-foreground"
                            >
                              + {preset.title}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  <p className="text-[11px] text-muted-foreground pt-1">
                    HR can also customize or add extra requirements per candidate directly in the Onboarding Inspector.
                  </p>
                </div>
              )}

              {/* 3. Employment Type Routing (`condition_branch`) */}
              {selectedStage.type === 'condition_branch' && (
                <div className="space-y-3 text-xs pt-2 border-t border-border">
                  <span className="font-bold text-foreground">Branch Condition Rules:</span>
                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase font-bold">Branch Attribute</label>
                    <select
                      value={selectedStage.config?.branch_attribute || 'employment_type'}
                      onChange={(e) =>
                        handleUpdateStage(selectedStage.id, {
                          config: { ...selectedStage.config, branch_attribute: e.target.value },
                        })
                      }
                      className="w-full h-8 mt-1 px-2.5 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs font-semibold"
                    >
                      <option value="employment_type">employment_type (Permanent vs Contractor)</option>
                      <option value="department">department (Engineering, Sales, Operations)</option>
                      <option value="annual_ctc">annual_ctc (Compensation Tier)</option>
                      <option value="location">location (Domestic vs Remote/International)</option>
                    </select>
                  </div>

                  <div className="space-y-1.5 p-3 rounded-lg bg-muted/40 border border-border">
                    <span className="font-semibold text-foreground">Configured Routes:</span>
                    <div className="space-y-1 text-[11px] text-muted-foreground">
                      <div className="flex items-center justify-between p-1.5 rounded bg-card border border-border">
                        <span className="font-medium text-foreground">Route A: Permanent FTE</span>
                        <code className="text-primary font-mono text-[10px]">employment_type == &apos;permanent&apos;</code>
                      </div>
                      <div className="flex items-center justify-between p-1.5 rounded bg-card border border-border">
                        <span className="font-medium text-foreground">Route B: Contractor</span>
                        <code className="text-primary font-mono text-[10px]">employment_type == &apos;contractor&apos;</code>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 4. Offer & Agreement Generation (`generate_document`) */}
              {selectedStage.type === 'generate_document' && (
                <div className="space-y-3 text-xs pt-2 border-t border-border">
                  <span className="font-bold text-foreground">Legal Contract Template Association:</span>

                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase font-bold">Document Template</label>
                    <select
                      value={selectedStage.config?.template_name || ''}
                      onChange={(e) =>
                        handleUpdateStage(selectedStage.id, {
                          config: { ...selectedStage.config, template_name: e.target.value },
                        })
                      }
                      className="w-full h-8 mt-1 px-2.5 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs font-semibold"
                    >
                      <option value="Executive Employment Agreement">Executive Employment Agreement</option>
                      <option value="Standard Offer Letter">Standard Offer Letter</option>
                      <option value="Independent Contractor MSA">Independent Contractor MSA</option>
                      {availableTemplates.map((tpl) => (
                        <option key={tpl.id} value={tpl.name}>
                          {tpl.name} ({tpl.format.toUpperCase()})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-muted-foreground uppercase font-bold">Output Format</label>
                      <select
                        value={selectedStage.config?.output_format || 'both'}
                        onChange={(e) =>
                          handleUpdateStage(selectedStage.id, {
                            config: { ...selectedStage.config, output_format: e.target.value },
                          })
                        }
                        className="w-full h-8 mt-1 px-2 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs"
                      >
                        <option value="both">Both DOCX &amp; PDF</option>
                        <option value="pdf">PDF Only</option>
                        <option value="docx">DOCX Only</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[10px] text-muted-foreground uppercase font-bold">Missing Data Policy</label>
                      <select
                        value={selectedStage.config?.missing_data_policy || 'route_to_hr'}
                        onChange={(e) =>
                          handleUpdateStage(selectedStage.id, {
                            config: { ...selectedStage.config, missing_data_policy: e.target.value },
                          })
                        }
                        className="w-full h-8 mt-1 px-2 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs"
                      >
                        <option value="route_to_hr">Route to HR</option>
                        <option value="halt">Halt &amp; Alert</option>
                        <option value="placeholder">Fill Fallback</option>
                      </select>
                    </div>
                  </div>
                </div>
              )}

              {/* 5. HR Sign-off & Cryptographic Binding (`approval` / `hr_review`) */}
              {(selectedStage.type === 'approval' || selectedStage.type === 'hr_review') && (
                <div className="space-y-3 text-xs pt-2 border-t border-border">
                  <span className="font-bold text-foreground">Sign-off Authority &amp; Security Policy:</span>

                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase font-bold">Required Signatory Role</label>
                    <select
                      value={selectedStage.config?.required_role || 'hr_director'}
                      onChange={(e) =>
                        handleUpdateStage(selectedStage.id, {
                          config: { ...selectedStage.config, required_role: e.target.value },
                        })
                      }
                      className="w-full h-8 mt-1 px-2.5 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs font-semibold"
                    >
                      <option value="hr_director">Authorized HR Director</option>
                      <option value="vp_hr">VP of People / HR</option>
                      <option value="hiring_manager">Hiring Manager</option>
                      <option value="legal_counsel">General Legal Counsel</option>
                    </select>
                  </div>

                  <div className="p-3 rounded-lg bg-rose-500/5 border border-rose-500/20 space-y-1.5">
                    <div className="flex items-center gap-1.5 text-rose-400 font-semibold">
                      <ShieldCheck size={14} />
                      <span>Cryptographic Binding Enabled</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">
                      Approved document drafts are bound to a calculated SHA-256 digital fingerprint to prevent post-signature alteration.
                    </p>
                  </div>
                </div>
              )}

              {/* 6. Email & Notification (`candidate_email` or `notification`) */}
              {(selectedStage.type === 'candidate_email' || selectedStage.type === 'notification') && (
                <div className="space-y-3 text-xs pt-2 border-t border-border">
                  <span className="font-bold text-foreground">Dispatch &amp; Notification Configuration:</span>

                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase font-bold">Email Subject</label>
                    <Input
                      value={selectedStage.config?.subject || ''}
                      onChange={(e) =>
                        handleUpdateStage(selectedStage.id, {
                          config: { ...selectedStage.config, subject: e.target.value },
                        })
                      }
                      className="h-8 mt-1 text-xs bg-surface-hover/50 border-border"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] text-muted-foreground uppercase font-bold">Message Template</label>
                    <textarea
                      rows={3}
                      value={selectedStage.config?.email_template || ''}
                      onChange={(e) =>
                        handleUpdateStage(selectedStage.id, {
                          config: { ...selectedStage.config, email_template: e.target.value },
                        })
                      }
                      className="w-full p-2 mt-1 rounded-lg bg-surface-hover/50 border border-border text-xs text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
              )}

              {/* 7. Complete Hire (`end`) */}
              {selectedStage.type === 'end' && (
                <div className="space-y-3 text-xs pt-2 border-t border-border">
                  <span className="font-bold text-foreground">Completion &amp; Downstream Provisioning:</span>

                  <div className="space-y-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                    <label className="flex items-center gap-2 cursor-pointer text-foreground">
                      <input
                        type="checkbox"
                        checked={selectedStage.config?.sync_to_payroll ?? true}
                        onChange={(e) =>
                          handleUpdateStage(selectedStage.id, {
                            config: { ...selectedStage.config, sync_to_payroll: e.target.checked },
                          })
                        }
                        className="rounded border-border text-emerald-500 focus:ring-emerald-500 size-4"
                      />
                      <span className="font-medium">Automatically sync hired profile to payroll</span>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer text-foreground">
                      <input
                        type="checkbox"
                        checked={selectedStage.config?.notify_participants ?? true}
                        onChange={(e) =>
                          handleUpdateStage(selectedStage.id, {
                            config: { ...selectedStage.config, notify_participants: e.target.checked },
                          })
                        }
                        className="rounded border-border text-emerald-500 focus:ring-emerald-500 size-4"
                      />
                      <span className="font-medium">Notify hiring manager and candidate via email</span>
                    </label>
                  </div>
                </div>
              )}
            </section>
          ) : (
            <div className="p-8 text-center text-xs text-muted-foreground rounded-xl border border-border bg-card">
              Select a stage from the pipeline flow on the left to edit its rules and properties.
            </div>
          )}
        </div>
      </div>

      {/* ── ADD STAGE MODAL DIALOG ── */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-card shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Plus size={16} className="text-primary" />
                <h3 className="text-sm font-bold text-foreground">Add Pipeline Stage</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                <X size={15} />
              </button>
            </div>

            <div className="p-4 space-y-3.5 text-xs">
              <div>
                <label className="text-[11px] font-bold text-muted-foreground uppercase">Stage Type</label>
                <select
                  value={newStageType}
                  onChange={(e) => {
                    setNewStageType(e.target.value);
                    const meta = getStageMeta(e.target.value);
                    setNewStageTitle(`${nodes.length + 1}. ${meta.label}`);
                    setNewStageDesc(meta.desc);
                  }}
                  className="w-full h-8 mt-1 px-2.5 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {STAGE_TYPES.map((t) => (
                    <option key={t.type} value={t.type}>
                      {t.label} ({t.kind})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[11px] font-bold text-muted-foreground uppercase">Stage Title</label>
                <Input
                  value={newStageTitle}
                  onChange={(e) => setNewStageTitle(e.target.value)}
                  placeholder="e.g. Background & Reference Check"
                  className="h-8 mt-1 text-xs bg-surface-hover/50 border-border"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-muted-foreground uppercase">Description</label>
                <textarea
                  rows={2}
                  value={newStageDesc}
                  onChange={(e) => setNewStageDesc(e.target.value)}
                  placeholder="Describe what occurs at this stage..."
                  className="w-full p-2 mt-1 rounded-lg bg-surface-hover/50 border border-border text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-[11px] font-bold text-muted-foreground uppercase">Placement</label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  <label
                    className={`p-2 rounded-lg border cursor-pointer text-center font-medium transition-all ${
                      newStagePosition === 'end'
                        ? 'border-primary bg-primary/10 text-primary font-bold'
                        : 'border-border bg-surface-hover/40 text-muted-foreground'
                    }`}
                  >
                    <input
                      type="radio"
                      name="placement"
                      value="end"
                      checked={newStagePosition === 'end'}
                      onChange={() => setNewStagePosition('end')}
                      className="sr-only"
                    />
                    <span>At End of Pipeline</span>
                  </label>
                  <label
                    className={`p-2 rounded-lg border cursor-pointer text-center font-medium transition-all ${
                      newStagePosition === 'after_selected'
                        ? 'border-primary bg-primary/10 text-primary font-bold'
                        : 'border-border bg-surface-hover/40 text-muted-foreground'
                    }`}
                  >
                    <input
                      type="radio"
                      name="placement"
                      value="after_selected"
                      checked={newStagePosition === 'after_selected'}
                      onChange={() => setNewStagePosition('after_selected')}
                      className="sr-only"
                    />
                    <span>After Selected Stage</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="p-3 bg-muted/40 border-t border-border flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsAddModalOpen(false)}
                className="h-8 text-xs font-semibold"
              >
                Cancel
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleAddStageSubmit}
                className="h-8 text-xs font-bold bg-primary text-primary-foreground"
              >
                Insert Stage
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

'use client';

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { notify } from '@/lib/notify';
import HROnboardingDrawer, { OnboardingInstanceData } from './hr-onboarding-drawer';
import {
  Building2,
  User,
  Users,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Copy,
  ExternalLink,
  Plus,
  Trash2,
  Save,
  Loader2,
  FileText,
  ShieldCheck,
  Send,
  Sparkles,
  GitBranch,
  Layers,
  ArrowRight,
  Upload,
  Check,
  Play,
  RotateCcw,
  Folder,
  FolderDown,
} from 'lucide-react';
import HRPipelineCanvas from './hr-pipeline-canvas';
import HRPipelineStageEditor from './hr-pipeline-stage-editor';

interface HiringWorkflowViewProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

type TemplateRow = {
  id: string;
  name: string;
  category?: string;
  latest_version?: number;
  status?: string;
  format?: string;
};

type WorkflowRow = {
  id: string;
  name: string;
  description?: string;
  version?: number;
  is_active?: boolean;
  node_count?: number;
  graph_schema?: any;
  folder_path?: string;
  department_id?: string;
  tags?: string[];
};

interface CandidateOption {
  id: string;
  name: string;
  email: string;
  role?: string;
  status?: string;
}

const DEFAULT_STEPS = [
  {
    id: 'step_intake',
    title: '1. Candidate Information Intake',
    kind: 'Intake',
    desc: 'Collects legal name, phone, email, residential address, and PAN/Tax ID via the secure portal.',
    defaultFields: ['candidate.full_name', 'candidate.email', 'candidate.phone', 'candidate.current_address', 'candidate.pan_number'],
  },
  {
    id: 'step_docs',
    title: '2. Required Document Evidence',
    kind: 'Documents',
    desc: 'HR decides which proof files (Government ID, Tax Proof, Degree, Relieving letter) are required.',
    defaultDocs: ['Government Photo ID', 'Tax / PAN Document', 'Educational Certificate'],
  },
  {
    id: 'step_branch',
    title: '3. Employment Type Routing',
    kind: 'Routing',
    desc: 'Routes permanent hires to FTE Employment Agreement, and contractors to Independent Contractor MSA.',
  },
  {
    id: 'step_offer',
    title: '4. Offer & Agreement Generation',
    kind: 'Generate',
    desc: 'Fills the official DOCX/HTML legal templates with reconciled candidate & company values.',
  },
  {
    id: 'step_approval',
    title: '5. HR Sign-off & Cryptographic Binding',
    kind: 'Review Gate',
    desc: 'Authorized HR director signs off on the finalized document draft bound to its SHA-256 seal.',
  },
  {
    id: 'step_complete',
    title: '6. Dispatch & Complete Hire',
    kind: 'Complete',
    desc: 'Candidate receives acceptance package and employee profile is provisioned.',
  },
];

export default function HiringWorkflowView({ API_URL, fetchWithAuth }: HiringWorkflowViewProps) {
  const [activeTab, setActiveTab] = useState<'onboardings' | 'pipeline' | 'templates'>('onboardings');
  const [instances, setInstances] = useState<OnboardingInstanceData[]>([]);
  const [templates, setTemplates] = useState<TemplateRow[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowRow[]>([]);
  const [candidates, setCandidates] = useState<CandidateOption[]>([]);
  const [loading, setLoading] = useState(true);

  // Inspector Drawer State
  const [selectedInstance, setSelectedInstance] = useState<OnboardingInstanceData | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Start Onboarding Modal State
  const [isStartModalOpen, setIsStartModalOpen] = useState(false);
  const [launchingOnboarding, setLaunchingOnboarding] = useState(false);
  const [selectedCandidateId, setSelectedCandidateId] = useState('');
  const [onboardingRole, setOnboardingRole] = useState('');
  const [onboardingDepartment, setOnboardingDepartment] = useState('Engineering');
  const [onboardingCtc, setOnboardingCtc] = useState('');
  const [onboardingStartDate, setOnboardingStartDate] = useState('');
  const [onboardingSignatory, setOnboardingSignatory] = useState('HR Director');

  // Custom document requirements in Start Modal
  const [includePassport, setIncludePassport] = useState(true);
  const [includeTaxId, setIncludeTaxId] = useState(true);
  const [includeDegree, setIncludeDegree] = useState(true);
  const [includeResume, setIncludeResume] = useState(false);
  const [customDocTitle, setCustomDocTitle] = useState('');
  const [customDocDesc, setCustomDocDesc] = useState('');
  const [additionalDocs, setAdditionalDocs] = useState<{ title: string; desc: string; isMandatory: boolean }[]>([]);

  // Template Upload State
  const [uploadName, setUploadName] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  // Active step selected in pipeline view
  const [selectedPipelineStep, setSelectedPipelineStep] = useState(DEFAULT_STEPS[0].id);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [canvasViewMode, setCanvasViewMode] = useState<'canvas' | 'summary'>('canvas');

  // Folder & Workflow Import State
  const [folders, setFolders] = useState<string[]>(['/']);
  const [selectedFolder, setSelectedFolder] = useState<string>('all');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importSourceWfId, setImportSourceWfId] = useState<string>('');
  const [importTargetFolder, setImportTargetFolder] = useState<string>('/Engineering');
  const [importNewName, setImportNewName] = useState<string>('');
  const [importingWorkflow, setImportingWorkflow] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [instRes, tplRes, wfRes, candRes, folderRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/hr/workflow/instances`),
        fetchWithAuth(`${API_URL}/hr/workflow/templates`),
        fetchWithAuth(`${API_URL}/hr/workflow/definitions`),
        fetchWithAuth(`${API_URL}/hr/candidates`),
        fetchWithAuth(`${API_URL}/hr/workflow/folders`),
      ]);

      if (instRes.ok) {
        const data = await instRes.json();
        setInstances(Array.isArray(data) ? data : []);
      }
      if (tplRes.ok) {
        const data = await tplRes.json();
        setTemplates(Array.isArray(data) ? data : []);
      }
      if (wfRes.ok) {
        const data = await wfRes.json();
        const wfList = Array.isArray(data) ? data : [];
        setWorkflows(wfList);
        setSelectedWorkflowId((prev) => prev || (wfList[0]?.id ?? null));
      }
      if (candRes.ok) {
        const data = await candRes.json();
        const candList = Array.isArray(data) ? data : data.candidates || [];
        setCandidates(
          candList.map((c: any) => ({
            id: c.id,
            name: c.name || 'Candidate',
            email: c.email || '',
            role: c.role || '',
            status: c.status || 'sourced',
          }))
        );
      }
      if (folderRes && folderRes.ok) {
        const folderData = await folderRes.json();
        setFolders(Array.isArray(folderData.folders) ? folderData.folders : ['/']);
      }
    } catch {
      notify.error('Could not load hiring workflows.');
    } finally {
      setLoading(false);
    }
  };

  const handleImportWorkflowSubmit = async () => {
    if (!importSourceWfId) {
      notify.error('Please choose a pipeline to import.');
      return;
    }
    setImportingWorkflow(true);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/hr/workflow/definitions/${importSourceWfId}/import-to-folder`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_folder_path: importTargetFolder || '/',
            new_name: importNewName.trim() || undefined,
          }),
        }
      );
      if (res.ok) {
        const cloned = await res.json();
        notify.success(`Imported as draft: "${cloned.name}" in ${cloned.folder_path}`);
        setIsImportModalOpen(false);
        await loadData();
        setSelectedWorkflowId(cloned.id);
        setActiveTab('pipeline');
        setCanvasViewMode('canvas');
      } else {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Failed to import workflow.');
      }
    } catch {
      notify.error('Network error during workflow import.');
    } finally {
      setImportingWorkflow(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [API_URL]);

  const handleOpenDrawer = (inst: OnboardingInstanceData) => {
    setSelectedInstance(inst);
    setIsDrawerOpen(true);
  };

  const handleStartOnboardingSubmit = async () => {
    if (!selectedCandidateId) {
      notify.error('Please select a candidate.');
      return;
    }

    setLaunchingOnboarding(true);
    try {
      // Build dynamic required documents list
      const reqDocs: any[] = [];
      if (includePassport) {
        reqDocs.push({
          document_category: 'passport',
          title: 'Government Photo ID',
          description: 'Upload Passport, Aadhaar, or Driver’s License',
          is_mandatory: true,
        });
      }
      if (includeTaxId) {
        reqDocs.push({
          document_category: 'tax_form',
          title: 'Tax / Social Security Proof',
          description: 'Upload PAN Card or National Tax Proof',
          is_mandatory: true,
        });
      }
      if (includeDegree) {
        reqDocs.push({
          document_category: 'degree_certificate',
          title: 'Highest Educational Certificate',
          description: 'Graduation certificate or degree transcript',
          is_mandatory: true,
        });
      }
      if (includeResume) {
        reqDocs.push({
          document_category: 'resume',
          title: 'Updated Curriculum Vitae (CV)',
          description: 'Latest resume document',
          is_mandatory: false,
        });
      }
      additionalDocs.forEach((d) => {
        const cat = d.title.toLowerCase().replace(/[^a-z0-9]/g, '_').slice(0, 32);
        reqDocs.push({
          document_category: cat,
          title: d.title,
          description: d.desc || 'Upload official proof document',
          is_mandatory: d.isMandatory,
        });
      });

      const body = {
        candidate_id: selectedCandidateId,
        company_fields: {
          role_title: onboardingRole,
          department: onboardingDepartment,
          annual_ctc: onboardingCtc,
          start_date: onboardingStartDate,
          signatory_name: onboardingSignatory,
        },
        required_documents: reqDocs,
      };

      const res = await fetchWithAuth(`${API_URL}/hr/workflow/instances`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Failed to launch onboarding.');
        return;
      }

      const newInst = await res.json();
      notify.success(`Onboarding launched for ${newInst.candidate_name}!`);
      setIsStartModalOpen(false);
      await loadData();

      // Automatically open drawer for the newly launched instance
      setSelectedInstance(newInst);
      setIsDrawerOpen(true);
    } catch {
      notify.error('Network error launching onboarding.');
    } finally {
      setLaunchingOnboarding(false);
    }
  };

  const uploadTemplate = async () => {
    if (!uploadFile || !uploadName.trim()) {
      notify.error('Name the template and choose a DOCX or HTML file.');
      return;
    }
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', uploadFile);
      body.append('name', uploadName.trim());
      body.append('category', 'offer');
      const res = await fetchWithAuth(`${API_URL}/hr/workflow/templates/upload`, {
        method: 'POST',
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Upload failed.');
        return;
      }
      notify.success('Template uploaded.');
      setUploadName('');
      setUploadFile(null);
      await loadData();
    } catch {
      notify.error('Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  // Metrics
  const activeCount = instances.length;
  const awaitingCandidateCount = instances.filter((i) => i.missing_from_candidate.length > 0).length;
  const awaitingCompanyCount = instances.filter((i) => i.missing_from_company.length > 0).length;
  const reviewReadyCount = instances.filter(
    (i) => i.missing_from_candidate.length === 0 && i.missing_from_company.length === 0
  ).length;

  return (
    <div className="space-y-6">
      {/* ── TOP HEADER & TAB BAR ── */}
      <div className="rounded-xl border border-border bg-card px-5 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold tracking-tight text-foreground">
              Autonomous HR Onboarding &amp; Workflows
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-primary/10 text-primary border border-primary/20">
              Smart Triage Active
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground max-w-2xl">
            Intelligently separates missing company requirements from candidate proofs. Configure required documents, automate portal links, and manage legal agreements.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setActiveTab('pipeline');
              setCanvasViewMode('canvas');
            }}
            className="h-9 px-3.5 text-xs font-bold flex items-center gap-1.5 border-primary/30 text-primary hover:bg-primary/5"
            title="Open Visual n8n Canvas"
          >
            <Layers size={14} />
            <span>Visual n8n Canvas</span>
          </Button>

          <Button
            type="button"
            onClick={() => {
              if (candidates.length > 0) {
                setSelectedCandidateId(candidates[0].id);
                setOnboardingRole(candidates[0].role || 'Software Engineer');
              }
              setIsStartModalOpen(true);
            }}
            className="h-9 px-4 text-xs font-bold flex items-center gap-1.5 shadow-xs bg-[#64B99A] hover:bg-[#52a084] text-black"
          >
            <Plus size={14} />
            <span>Start Candidate Onboarding</span>
          </Button>
        </div>
      </div>

      {/* ── 3 WORKFLOW TABS ── */}
      <div className="flex items-center gap-1 border-b border-border pb-1">
        <button
          type="button"
          onClick={() => setActiveTab('onboardings')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${
            activeTab === 'onboardings'
              ? 'bg-primary/10 text-primary font-bold border border-primary/30'
              : 'text-muted-foreground hover:bg-surface-hover'
          }`}
        >
          <Users size={14} />
          <span>Active Onboardings Tracker</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-muted text-foreground">
            {instances.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('pipeline');
            setCanvasViewMode('canvas');
          }}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${
            activeTab === 'pipeline'
              ? 'bg-primary/10 text-primary font-bold border border-primary/30'
              : 'text-muted-foreground hover:bg-surface-hover'
          }`}
        >
          <Layers size={14} className="text-primary" />
          <span>Visual n8n Canvas &amp; Pipelines</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('templates')}
          className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${
            activeTab === 'templates'
              ? 'bg-primary/10 text-primary font-bold border border-primary/30'
              : 'text-muted-foreground hover:bg-surface-hover'
          }`}
        >
          <FileText size={14} />
          <span>Legal Document Templates</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-muted text-foreground">
            {templates.length}
          </span>
        </button>
      </div>

      {/* ── TAB 1: ONBOARDINGS TRACKER ── */}
      {activeTab === 'onboardings' && (
        <div className="space-y-4">
          {/* Metric Ribbon */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl border border-border bg-card/60">
              <span className="text-[11px] font-bold text-muted-foreground uppercase">Active Onboardings</span>
              <div className="text-xl font-bold font-mono text-foreground mt-1">{activeCount}</div>
            </div>
            <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5">
              <span className="text-[11px] font-bold text-amber-500 uppercase flex items-center gap-1">
                <Building2 size={12} /> Awaiting Company Inputs
              </span>
              <div className="text-xl font-bold font-mono text-amber-500 mt-1">{awaitingCompanyCount}</div>
            </div>
            <div className="p-3.5 rounded-xl border border-destructive/20 bg-destructive/5">
              <span className="text-[11px] font-bold text-destructive uppercase flex items-center gap-1">
                <User size={12} /> Awaiting Candidate Proofs
              </span>
              <div className="text-xl font-bold font-mono text-destructive mt-1">{awaitingCandidateCount}</div>
            </div>
            <div className="p-3.5 rounded-xl border border-[#64B99A]/20 bg-[#263D38]/10">
              <span className="text-[11px] font-bold text-[#64B99A] uppercase flex items-center gap-1">
                <CheckCircle2 size={12} /> Ready for HR Sign-Off
              </span>
              <div className="text-xl font-bold font-mono text-[#64B99A] mt-1">{reviewReadyCount}</div>
            </div>
          </div>

          {/* Instances Table */}
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Candidate Onboarding Stream</h3>
                <p className="text-xs text-muted-foreground">
                  Click any candidate to inspect smart missing items, fill company inputs, or adjust document requirements.
                </p>
              </div>
            </div>

            {loading ? (
              <div className="p-8 text-center text-xs text-muted-foreground">Loading onboardings…</div>
            ) : instances.length === 0 ? (
              <div className="p-12 text-center space-y-3">
                <div className="size-10 rounded-full bg-muted flex items-center justify-center mx-auto text-muted-foreground">
                  <Users size={20} />
                </div>
                <h4 className="text-sm font-bold text-foreground">No active candidate onboardings yet</h4>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Click &ldquo;Start Candidate Onboarding&rdquo; above to launch a smart onboarding flow with dynamic document checklist.
                </p>
                <Button
                  size="sm"
                  onClick={() => setIsStartModalOpen(true)}
                  className="h-8 text-xs font-bold"
                >
                  <Plus size={13} className="mr-1" /> Start First Onboarding
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-border text-xs">
                {instances.map((inst) => {
                  const hasCompanyMissing = inst.missing_from_company.length > 0;
                  const hasCandidateMissing = inst.missing_from_candidate.length > 0;
                  const fullUrl = typeof window !== 'undefined'
                    ? `${window.location.origin}${inst.candidate_portal_url}`
                    : inst.candidate_portal_url;

                  return (
                    <div
                      key={inst.id}
                      onClick={() => handleOpenDrawer(inst)}
                      className="p-4 hover:bg-surface-hover/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer"
                    >
                      {/* Candidate Column */}
                      <div className="space-y-1 min-w-[200px]">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-foreground">{inst.candidate_name}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-muted text-muted-foreground border border-border">
                            {inst.current_state.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                          <span>{inst.role_title}</span>
                          {inst.candidate_email && (
                            <>
                              <span>•</span>
                              <span>{inst.candidate_email}</span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Smart Missing Triage Badges */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {hasCompanyMissing ? (
                          <span
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenDrawer(inst);
                            }}
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/30 flex items-center gap-1.5"
                          >
                            <Building2 size={12} />
                            <span>🏢 {inst.missing_from_company.length} Company fields missing</span>
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-[#263D38] text-[#64B99A] border border-[#64B99A]/30 flex items-center gap-1">
                            <CheckCircle2 size={12} />
                            <span>🏢 Company complete</span>
                          </span>
                        )}

                        {hasCandidateMissing ? (
                          <span
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenDrawer(inst);
                            }}
                            className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-destructive/10 text-destructive border border-destructive/30 flex items-center gap-1.5"
                          >
                            <User size={12} />
                            <span>👤 {inst.missing_from_candidate.length} Candidate docs pending</span>
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-[#263D38] text-[#64B99A] border border-[#64B99A]/30 flex items-center gap-1">
                            <CheckCircle2 size={12} />
                            <span>👤 All proofs uploaded</span>
                          </span>
                        )}
                      </div>

                      {/* Progress Bar & Actions */}
                      <div className="flex items-center gap-3 shrink-0" onClick={(e) => e.stopPropagation()}>
                        <div className="w-24 text-right">
                          <div className="text-[11px] font-mono font-bold text-foreground">
                            {inst.progress_percentage}%
                          </div>
                          <div className="w-full h-1.5 rounded-full bg-muted mt-1 overflow-hidden">
                            <div
                              className="h-full bg-primary rounded-full transition-all"
                              style={{ width: `${inst.progress_percentage}%` }}
                            />
                          </div>
                        </div>

                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            navigator.clipboard.writeText(fullUrl);
                            notify.success('Candidate Portal URL copied!');
                          }}
                          className="h-8 text-xs font-semibold flex items-center gap-1"
                        >
                          <Copy size={12} /> Link
                        </Button>

                        <Button
                          size="sm"
                          onClick={() => handleOpenDrawer(inst)}
                          className="h-8 text-xs font-bold flex items-center gap-1"
                        >
                          <span>Inspect</span>
                          <ArrowRight size={12} />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 2: PIPELINE & STAGE BUILDER ── */}
      {activeTab === 'pipeline' && (
        <div className="space-y-4">
          {/* Workflow Header / Switcher Bar */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-card border border-border rounded-xl p-3">
            <div className="flex items-center gap-2.5 flex-wrap">
              {/* Folder Selector */}
              <div className="flex items-center gap-1.5 border-r border-border pr-3">
                <Folder size={14} className="text-primary shrink-0" />
                <span className="text-[11px] font-bold text-muted-foreground">Folder:</span>
                <select
                  value={selectedFolder}
                  onChange={(e) => setSelectedFolder(e.target.value)}
                  className="h-8 px-2 rounded-lg bg-surface-hover/60 border border-border text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="all">All Folders ({folders.length})</option>
                  {folders.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>

              {/* Pipeline Selector filtered by folder */}
              <div className="flex items-center gap-1.5">
                <GitBranch size={15} className="text-primary" />
                <span className="text-xs font-bold text-foreground">Pipeline:</span>
              </div>
              <select
                value={selectedWorkflowId || ''}
                onChange={(e) => setSelectedWorkflowId(e.target.value || null)}
                className="h-8 px-2.5 rounded-lg bg-surface-hover/60 border border-border text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary min-w-[200px]"
              >
                {workflows
                  .filter((wf) => selectedFolder === 'all' || (wf.folder_path || '/') === selectedFolder)
                  .map((wf) => (
                    <option key={wf.id} value={wf.id}>
                      {wf.name} (v{wf.version || 1}) {wf.folder_path ? `[${wf.folder_path}]` : ''}
                    </option>
                  ))}
                <option value="">+ New Blank Canvas</option>
              </select>

              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelectedWorkflowId(null)}
                className="h-8 text-xs font-semibold"
              >
                <Plus size={13} className="mr-1" /> New Blank
              </Button>

              {/* Import from Folder Button */}
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setImportSourceWfId(workflows[0]?.id || '');
                  setImportTargetFolder(selectedFolder !== 'all' ? selectedFolder : '/Engineering');
                  setImportNewName('');
                  setIsImportModalOpen(true);
                }}
                className="h-8 text-xs font-semibold border-indigo-500/40 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 flex items-center gap-1"
                title="Clone and import an existing company workflow into another folder"
              >
                <FolderDown size={13} />
                <span>Import from Folder</span>
              </Button>
            </div>

            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 bg-muted/60 p-1 rounded-lg border border-border">
              <button
                type="button"
                onClick={() => setCanvasViewMode('canvas')}
                className={`px-3 py-1 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                  canvasViewMode === 'canvas'
                    ? 'bg-[#64B99A] text-black shadow-xs font-bold'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Layers size={13} />
                <span>Visual n8n Canvas</span>
              </button>
              <button
                type="button"
                onClick={() => setCanvasViewMode('summary')}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
                  canvasViewMode === 'summary'
                    ? 'bg-card text-foreground shadow-xs border border-border'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <span>Pipeline Stages</span>
              </button>
            </div>
          </div>

          {canvasViewMode === 'canvas' ? (
            <div className="w-full">
              <HRPipelineCanvas
                key={selectedWorkflowId || 'fresh-canvas'}
                API_URL={API_URL}
                fetchWithAuth={fetchWithAuth}
                initialDefinitionId={selectedWorkflowId || undefined}
                availableTemplates={templates.map((t) => ({
                  id: t.id,
                  name: t.name,
                  category: t.category || 'offer',
                  format: t.format || 'docx',
                  latest_version: t.latest_version || 1,
                }))}
                onPipelinePublished={loadData}
                onImportClick={() => {
                  setImportSourceWfId(workflows[0]?.id || '');
                  setImportTargetFolder(selectedFolder !== 'all' ? selectedFolder : '/Engineering');
                  setImportNewName('');
                  setIsImportModalOpen(true);
                }}
              />
            </div>
          ) : (
            <HRPipelineStageEditor
              key={selectedWorkflowId || 'stage-editor-fresh'}
              API_URL={API_URL}
              fetchWithAuth={fetchWithAuth}
              workflowId={selectedWorkflowId}
              availableTemplates={templates.map((t) => ({
                id: t.id,
                name: t.name,
                category: t.category || 'offer',
                format: t.format || 'docx',
                latest_version: t.latest_version || 1,
              }))}
              onWorkflowUpdated={() => loadData()}
              onSwitchToCanvas={() => setCanvasViewMode('canvas')}
            />
          )}
    </div>
  )}

      {/* ── TAB 3: DOCUMENT TEMPLATES ── */}
      {activeTab === 'templates' && (
        <div className="space-y-4">
          <section className="rounded-xl border border-border bg-card p-5 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Upload Legal Document Template</h3>
              <p className="mt-1 text-xs text-muted-foreground">
                Upload DOCX or HTML contracts containing placeholders like <code className="text-primary font-mono">&#123;&#123; candidate.full_name &#125;&#125;</code> and <code className="text-primary font-mono">&#123;&#123; compensation.annual_ctc &#125;&#125;</code>.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center gap-2">
              <Input
                value={uploadName}
                onChange={(e) => setUploadName(e.target.value)}
                placeholder="Template name (e.g. Executive Offer Letter)"
                className="h-9 sm:max-w-xs text-xs bg-surface-hover/50 border-border"
              />
              <Input
                type="file"
                accept=".docx,.html,.htm"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="h-9 sm:max-w-xs text-xs bg-surface-hover/50 border-border"
              />
              <Button type="button" size="sm" onClick={uploadTemplate} disabled={uploading} className="h-9 font-bold text-xs">
                <Upload className="size-3.5 mr-1.5" />
                {uploading ? 'Uploading…' : 'Upload Template'}
              </Button>
            </div>
          </section>

          <section className="rounded-xl border border-border bg-card p-5 space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Active Legal Templates ({templates.length})</h3>
            {templates.length === 0 ? (
              <p className="text-xs text-muted-foreground">No custom templates uploaded yet.</p>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {templates.map((tpl) => (
                  <div key={tpl.id} className="p-3 rounded-lg border border-border bg-card/60 space-y-1 text-xs">
                    <div className="font-bold text-foreground">{tpl.name}</div>
                    <div className="text-[11px] text-muted-foreground">
                      Category: {tpl.category || 'offer'} • Format: {tpl.format || 'docx'} • v{tpl.latest_version || 1}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* ── START ONBOARDING MODAL ── */}
      <Dialog open={isStartModalOpen} onOpenChange={(open) => !open && setIsStartModalOpen(false)}>
        <DialogContent className="max-w-xl bg-card border-border text-foreground p-0 overflow-hidden shadow-2xl rounded-2xl">
          <DialogHeader className="p-6 border-b border-border bg-muted/20">
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <Sparkles size={18} className="text-primary" />
              <span>Launch Candidate Onboarding Flow</span>
            </DialogTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              Initiates the autonomous onboarding pipeline and configures which document proofs are requested from the candidate.
            </p>
          </DialogHeader>

          <div className="p-6 max-h-[500px] overflow-y-auto space-y-4 text-xs">
            {/* Candidate Selector */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-muted-foreground">Select Candidate *</label>
              <select
                value={selectedCandidateId}
                onChange={(e) => {
                  setSelectedCandidateId(e.target.value);
                  const c = candidates.find((item) => item.id === e.target.value);
                  if (c?.role) setOnboardingRole(c.role);
                }}
                className="w-full h-9 px-3 rounded-lg bg-surface-hover/50 border border-border text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {candidates.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.email || 'No email'}) • {c.role || 'Applicant'}
                  </option>
                ))}
              </select>
            </div>

            {/* Company Inputs */}
            <div className="p-3.5 rounded-xl border border-border bg-surface-hover/30 space-y-3">
              <span className="font-bold text-foreground flex items-center gap-1.5">
                <Building2 size={13} className="text-primary" /> Company Parameters
              </span>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Position / Title</label>
                  <Input
                    value={onboardingRole}
                    onChange={(e) => setOnboardingRole(e.target.value)}
                    placeholder="e.g. Lead Architect"
                    className="h-8 text-xs bg-card border-border"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Department</label>
                  <Input
                    value={onboardingDepartment}
                    onChange={(e) => setOnboardingDepartment(e.target.value)}
                    className="h-8 text-xs bg-card border-border"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Annual CTC / Salary</label>
                  <Input
                    value={onboardingCtc}
                    onChange={(e) => setOnboardingCtc(e.target.value)}
                    placeholder="e.g. ₹24,00,000 / yr"
                    className="h-8 text-xs bg-card border-border"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Joining Date</label>
                  <Input
                    type="date"
                    value={onboardingStartDate}
                    onChange={(e) => setOnboardingStartDate(e.target.value)}
                    className="h-8 text-xs bg-card border-border"
                  />
                </div>
              </div>
            </div>

            {/* Document Checklist Config */}
            <div className="p-3.5 rounded-xl border border-border bg-surface-hover/30 space-y-3">
              <span className="font-bold text-foreground flex items-center gap-1.5">
                <FileText size={13} className="text-primary" /> Required Documents (HR Decides)
              </span>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <label className="flex items-center gap-2 p-2 rounded-lg bg-card border border-border cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includePassport}
                    onChange={(e) => setIncludePassport(e.target.checked)}
                    className="rounded border-border text-primary"
                  />
                  <span>Government Photo ID</span>
                </label>

                <label className="flex items-center gap-2 p-2 rounded-lg bg-card border border-border cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeTaxId}
                    onChange={(e) => setIncludeTaxId(e.target.checked)}
                    className="rounded border-border text-primary"
                  />
                  <span>PAN / Tax ID Document</span>
                </label>

                <label className="flex items-center gap-2 p-2 rounded-lg bg-card border border-border cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeDegree}
                    onChange={(e) => setIncludeDegree(e.target.checked)}
                    className="rounded border-border text-primary"
                  />
                  <span>Degree Certificate</span>
                </label>

                <label className="flex items-center gap-2 p-2 rounded-lg bg-card border border-border cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeResume}
                    onChange={(e) => setIncludeResume(e.target.checked)}
                    className="rounded border-border text-primary"
                  />
                  <span>Updated Resume (CV)</span>
                </label>
              </div>

              {/* Additional custom docs */}
              {additionalDocs.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[11px] font-semibold text-muted-foreground">Extra Documents Added:</span>
                  {additionalDocs.map((ad, idx) => (
                    <div key={idx} className="p-2 rounded-lg bg-card border border-border flex items-center justify-between">
                      <span className="font-semibold text-foreground">{ad.title}</span>
                      <button
                        type="button"
                        onClick={() => setAdditionalDocs(additionalDocs.filter((_, i) => i !== idx))}
                        className="text-destructive hover:underline text-[11px]"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add custom document item */}
              <div className="pt-2 border-t border-border flex gap-2">
                <Input
                  placeholder="Add custom doc (e.g. Relieving Letter)"
                  value={customDocTitle}
                  onChange={(e) => setCustomDocTitle(e.target.value)}
                  className="h-8 text-xs bg-card border-border"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (!customDocTitle.trim()) return;
                    setAdditionalDocs([
                      ...additionalDocs,
                      { title: customDocTitle.trim(), desc: customDocDesc.trim(), isMandatory: true },
                    ]);
                    setCustomDocTitle('');
                    setCustomDocDesc('');
                  }}
                  className="h-8 text-xs font-semibold shrink-0"
                >
                  <Plus size={12} className="mr-1" /> Add
                </Button>
              </div>
            </div>
          </div>

          <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsStartModalOpen(false)}
              className="h-8 text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={launchingOnboarding || !selectedCandidateId}
              onClick={handleStartOnboardingSubmit}
              className="h-8.5 px-4 text-xs font-bold bg-[#64B99A] hover:bg-[#52a084] text-black shadow-xs flex items-center gap-1.5"
            >
              {launchingOnboarding ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
              <span>Launch Onboarding Flow</span>
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ── SMART ONBOARDING INSPECTOR DRAWER ── */}
      <HROnboardingDrawer
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedInstance(null);
        }}
        instance={selectedInstance}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onInstanceUpdated={loadData}
      />

      {/* ── IMPORT WORKFLOW MODAL ── */}
      <Dialog open={isImportModalOpen} onOpenChange={setIsImportModalOpen}>
        <DialogContent className="max-w-lg bg-card border-border text-foreground p-0 overflow-hidden shadow-2xl">
          <DialogHeader className="p-5 border-b border-border bg-muted/20">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <FolderDown size={18} />
              </div>
              <div>
                <DialogTitle className="text-sm font-bold text-foreground">
                  Import Workflow &amp; Legal Templates
                </DialogTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Clone an existing workflow from any company folder into a target department as an isolated draft.
                </p>
              </div>
            </div>
          </DialogHeader>

          <div className="p-5 space-y-4 text-xs">
            {/* Source Workflow Picker */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-foreground">Source Pipeline to Clone *</label>
              <select
                value={importSourceWfId}
                onChange={(e) => setImportSourceWfId(e.target.value)}
                className="w-full h-9 px-2.5 rounded-lg bg-surface-hover/60 border border-border text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {workflows.map((wf) => (
                  <option key={wf.id} value={wf.id}>
                    {wf.name} (v{wf.version || 1}) • Folder: {wf.folder_path || '/'} ({wf.node_count || 0} nodes)
                  </option>
                ))}
              </select>
            </div>

            {/* Target Folder Path */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-foreground">Target Destination Folder *</label>
              <Input
                placeholder="e.g. /Engineering or /Sales/EMEA"
                value={importTargetFolder}
                onChange={(e) => setImportTargetFolder(e.target.value)}
                className="h-8.5 text-xs bg-surface-hover/50 border-border"
              />
              <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                <span className="text-[10px] text-muted-foreground">Quick folders:</span>
                {['/Engineering', '/Sales', '/Operations', '/Executive'].map((qf) => (
                  <button
                    key={qf}
                    type="button"
                    onClick={() => setImportTargetFolder(qf)}
                    className="text-[10px] px-2 py-0.5 rounded-md bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground font-mono"
                  >
                    {qf}
                  </button>
                ))}
              </div>
            </div>

            {/* Cloned Pipeline Name */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-foreground">New Draft Pipeline Name (Optional)</label>
              <Input
                placeholder="Leave blank to use default (e.g. Pipeline Name (Imported))"
                value={importNewName}
                onChange={(e) => setImportNewName(e.target.value)}
                className="h-8.5 text-xs bg-surface-hover/50 border-border"
              />
            </div>

            {/* Enterprise Safety Guarantee Banner */}
            <div className="p-3 rounded-xl border border-indigo-500/30 bg-indigo-500/5 space-y-1">
              <div className="flex items-center gap-1.5 text-indigo-400 font-bold text-[11px]">
                <ShieldCheck size={13} />
                <span>Enterprise Draft-Only Protection</span>
              </div>
              <p className="text-[10px] text-muted-foreground leading-relaxed">
                The imported pipeline is generated with cloned internal IDs and its attached document templates are copied to your folder in <strong>Draft Mode</strong>. Live hirings won’t be affected until you review and publish.
              </p>
            </div>
          </div>

          <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsImportModalOpen(false)}
              className="h-8 text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={importingWorkflow || !importSourceWfId}
              onClick={handleImportWorkflowSubmit}
              className="h-8.5 px-4 text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs flex items-center gap-1.5"
            >
              {importingWorkflow ? <Loader2 size={13} className="animate-spin" /> : <FolderDown size={13} />}
              <span>Import as Editable Draft</span>
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

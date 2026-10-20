'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';

function Badge({ children, className = '', variant }: { children: React.ReactNode; className?: string; variant?: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}
import HRPipelineCanvas from './hr-pipeline-canvas';
import {
  FileText,
  Workflow,
  Sparkles,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Send,
  Eye,
  SlidersHorizontal,
  Copy,
  ExternalLink,
  ShieldAlert,
  ShieldCheck,
  FolderTree,
  Play,
  RotateCcw,
  GitBranch,
  Layers,
  Calendar,
  Check,
  X,
  Plus,
} from 'lucide-react';

interface HRWorkflowHubProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

export default function HRWorkflowHub({ API_URL, fetchWithAuth }: HRWorkflowHubProps) {
  const [subTab, setSubTab] = useState<'templates' | 'builder' | 'onboarding' | 'review'>('templates');

  // --- 1. TEMPLATE HUB STATE ---
  const [templates, setTemplates] = useState<any[]>([
    {
      id: 'tpl-1',
      name: 'Executive Employment Agreement',
      category: 'agreement',
      folder_path: '/Executive',
      tags: ['executive', 'c-suite', 'annual-ctc'],
      latest_version: 2,
      status: 'published',
      format: 'docx',
    },
    {
      id: 'tpl-2',
      name: 'Standard Offer Letter',
      category: 'offer',
      folder_path: '/Standard',
      tags: ['offer', 'general'],
      latest_version: 1,
      status: 'published',
      format: 'docx',
    },
    {
      id: 'tpl-3',
      name: 'Independent Contractor MSA',
      category: 'contractor',
      folder_path: '/Contractors',
      tags: ['contractor', 'hourly-rate'],
      latest_version: 1,
      status: 'published',
      format: 'docx',
    },
    {
      id: 'tpl-4',
      name: 'Mutual Non-Disclosure Agreement (NDA)',
      category: 'nda',
      folder_path: '/Compliance',
      tags: ['confidentiality', 'legal'],
      latest_version: 3,
      status: 'published',
      format: 'docx',
    },
  ]);

  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadCategory, setUploadCategory] = useState('agreement');
  const [uploadName, setUploadName] = useState('');
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);

  // --- 2. WORKFLOW BUILDER STATE ---
  const [workflowNodes, setWorkflowNodes] = useState<any[]>([
    { id: 'node_intake', name: 'Candidate Intake & Evidence', type: 'candidate_intake', config: { intake_fields: ['candidate.full_name', 'candidate.email', 'candidate.pan_number'] } },
    { id: 'node_branch', name: 'Employment Type Branch', type: 'condition_branch', config: {} },
    { id: 'node_offer_fte', name: 'Generate FTE Offer Letter', type: 'document_generation', config: { template_name: 'Standard Offer Letter', required_fields: ['compensation.annual_ctc'] } },
    { id: 'node_contract_fte', name: 'Generate Employment Agreement', type: 'document_generation', config: { template_name: 'Executive Employment Agreement', required_fields: ['role.start_date'] } },
    { id: 'node_contractor_msa', name: 'Generate Contractor MSA', type: 'document_generation', config: { template_name: 'Independent Contractor MSA', required_fields: ['contractor.daily_rate'] } },
    { id: 'node_approval_hr', name: 'HR Executive Sign-off Gate', type: 'approval_gate', config: { role: 'hr_director' } },
    { id: 'node_dispatch', name: 'Timezone-Aware Delivery', type: 'delivery_dispatch', config: { channel: 'email' } },
  ]);

  const [workflowEdges, setWorkflowEdges] = useState<any[]>([
    { id: 'e1', source: 'node_intake', target: 'node_branch' },
    { id: 'e2', source: 'node_branch', target: 'node_offer_fte', condition: "context.employment_type == 'permanent'" },
    { id: 'e3', source: 'node_offer_fte', target: 'node_contract_fte' },
    { id: 'e4', source: 'node_branch', target: 'node_contractor_msa', condition: "context.employment_type == 'contractor'" },
    { id: 'e5', source: 'node_contract_fte', target: 'node_approval_hr' },
    { id: 'e6', source: 'node_contractor_msa', target: 'node_approval_hr' },
    { id: 'e7', source: 'node_approval_hr', target: 'node_dispatch' },
  ]);

  const [simContext, setSimContext] = useState<string>(
    JSON.stringify({ employment_type: 'permanent', department: 'Product Design', annual_ctc: 2400000 }, null, 2)
  );
  const [simResult, setSimResult] = useState<any | null>(null);

  // --- 3. ONBOARDING TRACKER STATE ---
  const [instances, setInstances] = useState<any[]>([
    {
      id: 'inst-101',
      candidate_name: 'Priya Sharma',
      role_title: 'Senior Product Designer',
      employment_type: 'permanent',
      current_state: 'review_ready',
      portal_token: 'tok_sec_9942a1f0a82b99',
      expires_in: '6 days remaining',
      has_conflicts: true,
      conflict_details: {
        canonical_key: 'candidate.full_name',
        candidate_value: 'Priya S.',
        extracted_value: 'Priya Sharma',
        source: 'Passport scan (Page 1, 95% confidence)',
      },
    },
    {
      id: 'inst-102',
      candidate_name: 'Alex Rivera',
      role_title: 'DevOps Lead Contractor',
      employment_type: 'contractor',
      current_state: 'scheduled',
      portal_token: 'tok_sec_7721bc89a24d11',
      expires_in: '4 days remaining',
      has_conflicts: false,
      scheduled_for: '2026-10-22 09:00 IST',
    },
  ]);

  // --- 4. REVIEW STUDIO STATE ---
  const [studioDraft, setStudioDraft] = useState<any>({
    id: 'draft-201',
    document_name: 'Appointment Letter — Priya Sharma',
    approval_status: 'draft', // 'draft', 'pending_approval', 'approved'
    candidate_name: 'Priya Sharma',
    role: 'Senior Product Designer',
    department: 'Design Systems',
    compensation: '₹24,00,000 / year',
    start_date: 'November 1, 2026',
    bound_sha256: null,
    prior_approval_invalidated: false,
    paragraphs: [
      'LETTER OF APPOINTMENT',
      'Dear Priya Sharma,',
      'We are pleased to offer you the position of Senior Product Designer at OctaCorp Global. Your employment terms and statutory benefits are set forth below.',
      'Designation: Senior Product Designer. Reporting directly to the VP of Design in the Design Systems organization.',
      'Annual Compensation: ₹24,00,000 per annum, inclusive of statutory allowances, subject to applicable tax deductions.',
      'Confidentiality & Restrictive Covenants: You agree to hold all proprietary trade secrets, designs, and code of OctaCorp in strict confidentiality.',
    ],
    revisions: [
      { user: 'HR System', action: 'Auto-populated reconciled evidence snapshot', time: '10 mins ago' },
    ],
  });

  const [activePage, setActivePage] = useState(1);
  const [editingParagraphIdx, setEditingParagraphIdx] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [scheduledDate, setScheduledDate] = useState('2026-10-23T09:00');
  const [scheduledTimezone, setScheduledTimezone] = useState('Asia/Kolkata');

  // Handlers
  const handleSimulateWorkflow = () => {
    try {
      const parsedCtx = JSON.parse(simContext);
      const isPermanent = parsedCtx.employment_type === 'permanent';

      const traversed = ['node_intake', 'node_branch'];
      const docs = [];
      const fields = ['candidate.full_name', 'candidate.email', 'candidate.pan_number'];

      if (isPermanent) {
        traversed.push('node_offer_fte', 'node_contract_fte', 'node_approval_hr', 'node_dispatch');
        docs.push('Standard Offer Letter', 'Executive Employment Agreement');
        fields.push('compensation.annual_ctc', 'role.start_date');
      } else {
        traversed.push('node_contractor_msa', 'node_approval_hr', 'node_dispatch');
        docs.push('Independent Contractor MSA');
        fields.push('contractor.daily_rate');
      }

      setSimResult({
        is_valid: true,
        traversed_path: traversed,
        evaluated_documents: docs,
        required_candidate_fields: fields,
      });
      notify.success('Simulation executed: Path traversed successfully.');
    } catch (e: any) {
      notify.error('Invalid simulation JSON context.');
    }
  };

  const handleEditParagraph = (idx: number) => {
    setEditingParagraphIdx(idx);
    setEditText(studioDraft.paragraphs[idx]);
  };

  const handleSaveParagraph = () => {
    if (editingParagraphIdx === null) return;
    const newParagraphs = [...studioDraft.paragraphs];
    newParagraphs[editingParagraphIdx] = editText;

    const wasApproved = studioDraft.approval_status === 'approved';
    setStudioDraft((prev: any) => ({
      ...prev,
      paragraphs: newParagraphs,
      approval_status: 'draft',
      bound_sha256: null,
      prior_approval_invalidated: wasApproved || prev.prior_approval_invalidated,
      revisions: [
        {
          user: 'HR Admin',
          action: `Modified paragraph ${editingParagraphIdx + 1}: prior approval invalidated.`,
          time: 'Just now',
        },
        ...prev.revisions,
      ],
    }));
    setEditingParagraphIdx(null);
    if (wasApproved) {
      notify.warning('Document altered: Prior approval has been invalidated.');
    } else {
      notify.success('Paragraph updated in Review Studio.');
    }
  };

  const handleApproveDraft = () => {
    const mockSha = 'a3f892b109c8491823f990184b8d1039849201938b0918392019384918209384';
    setStudioDraft((prev: any) => ({
      ...prev,
      approval_status: 'approved',
      bound_sha256: mockSha,
      prior_approval_invalidated: false,
      revisions: [
        {
          user: 'HR Director',
          action: `Approved & cryptographically bound to SHA-256 (${mockSha.slice(0, 8)}...)`,
          time: 'Just now',
        },
        ...prev.revisions,
      ],
    }));
    notify.success('Document draft approved and cryptographically bound to SHA-256.');
  };

  const handleScheduleDispatch = () => {
    if (studioDraft.approval_status !== 'approved') {
      notify.error('Cannot schedule unapproved document draft.');
      return;
    }
    setScheduleModalOpen(false);
    notify.success(`Delivery scheduled for ${scheduledDate} (${scheduledTimezone}). Pre-flight check will verify SHA-256 before send.`);
  };

  const handleSimulateTemplateUpload = () => {
    if (!uploadName) {
      notify.error('Please enter a template name.');
      return;
    }
    setUploading(true);
    setTimeout(() => {
      setUploading(false);
      setAnalysisResult({
        template_name: uploadName,
        category: uploadCategory,
        placeholders: [
          { expr: '{{ candidate.full_name }}', canonical: 'candidate.full_name', type: 'string', conf: '98%' },
          { expr: '<< role.title >>', canonical: 'role.title', type: 'string', conf: '95%' },
          { expr: '{{ compensation.annual_ctc }}', canonical: 'compensation.annual_ctc', type: 'money', conf: '99%' },
          { expr: '[Role Start Date]', canonical: 'role.start_date', type: 'date', conf: '92%' },
        ],
        detected_clauses: [
          { type: 'Confidentiality', title: 'Non-Disclosure & Trade Secrets', status: 'Standard' },
          { type: 'Non-Compete', title: '12-Month Post-Termination Restraint', status: 'Flagged for Legal Review' },
        ],
      });
      notify.success('Template parsed: AI detected 4 canonical mappings & 2 legal clauses.');
    }, 1200);
  };

  const handlePublishTemplate = () => {
    if (!analysisResult) return;
    setTemplates((prev) => [
      {
        id: `tpl-${Date.now()}`,
        name: analysisResult.template_name,
        category: analysisResult.category,
        folder_path: `/${analysisResult.category.toUpperCase()}`,
        tags: [analysisResult.category, 'published'],
        latest_version: 1,
        status: 'published',
        format: 'docx',
      },
      ...prev,
    ]);
    setUploadModalOpen(false);
    setAnalysisResult(null);
    setUploadName('');
    notify.success('Template version published to Template Hub.');
  };

  return (
    <div className="space-y-6">
      {/* Sub-header navigation */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Layers className="h-6 w-6 text-amber-500" />
            Dynamic HR Document Intelligence & Workflow Builder
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Configurable, graph-driven onboarding workflows — upload arbitrary templates, collect candidate evidence, and govern reviews.
          </p>
        </div>

        <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-800 rounded-xl p-1">
          <Button
            size="sm"
            variant={subTab === 'templates' ? 'default' : 'ghost'}
            onClick={() => setSubTab('templates')}
            className={`rounded-lg text-xs font-semibold h-8 px-3 ${
              subTab === 'templates' ? 'bg-amber-500 hover:bg-amber-600 text-black font-bold' : 'text-gray-300 hover:text-white'
            }`}
          >
            <FileText className="h-3.5 w-3.5 mr-1.5" />
            Templates Workspace ({templates.length})
          </Button>

          <Button
            size="sm"
            variant={subTab === 'builder' ? 'default' : 'ghost'}
            onClick={() => setSubTab('builder')}
            className={`rounded-lg text-xs font-semibold h-8 px-3 ${
              subTab === 'builder' ? 'bg-amber-500 hover:bg-amber-600 text-black font-bold' : 'text-gray-300 hover:text-white'
            }`}
          >
            <Workflow className="h-3.5 w-3.5 mr-1.5" />
            Pipelines Workspace
          </Button>

          <Button
            size="sm"
            variant={subTab === 'onboarding' ? 'default' : 'ghost'}
            onClick={() => setSubTab('onboarding')}
            className={`rounded-lg text-xs font-semibold h-8 px-3 ${
              subTab === 'onboarding' ? 'bg-amber-500 hover:bg-amber-600 text-black font-bold' : 'text-gray-300 hover:text-white'
            }`}
          >
            <GitBranch className="h-3.5 w-3.5 mr-1.5" />
            Candidate Onboarding ({instances.length})
          </Button>

          <Button
            size="sm"
            variant={subTab === 'review' ? 'default' : 'ghost'}
            onClick={() => setSubTab('review')}
            className={`rounded-lg text-xs font-semibold h-8 px-3 ${
              subTab === 'review' ? 'bg-amber-500 hover:bg-amber-600 text-black font-bold' : 'text-gray-300 hover:text-white'
            }`}
          >
            <Eye className="h-3.5 w-3.5 mr-1.5" />
            DOCX Review Studio
          </Button>
        </div>
      </div>

      {/* --- SUBTAB 1: DYNAMIC TEMPLATE HUB --- */}
      {subTab === 'templates' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium text-gray-400">Filter Category:</span>
              <Badge variant="outline" className="border-gray-800 text-gray-300 cursor-pointer hover:border-amber-500">All</Badge>
              <Badge variant="outline" className="border-gray-800 text-gray-300 cursor-pointer hover:border-amber-500">Agreements</Badge>
              <Badge variant="outline" className="border-gray-800 text-gray-300 cursor-pointer hover:border-amber-500">Offer Letters</Badge>
              <Badge variant="outline" className="border-gray-800 text-gray-300 cursor-pointer hover:border-amber-500">Compliance & NDAs</Badge>
              <Badge variant="outline" className="border-gray-800 text-gray-300 cursor-pointer hover:border-amber-500">Contractors</Badge>
            </div>

            <Button
              onClick={() => setUploadModalOpen(true)}
              className="bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs h-9 px-4 rounded-xl flex items-center gap-2"
            >
              <Upload className="h-4 w-4" />
              Upload DOCX / HTML Template
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((tpl) => (
              <Card key={tpl.id} className="bg-gray-950 border border-gray-800 hover:border-gray-700 transition-all rounded-2xl">
                <CardHeader className="p-4 pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className="p-2 rounded-xl bg-amber-500/10 text-amber-500">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div>
                        <CardTitle className="text-sm font-semibold text-white">{tpl.name}</CardTitle>
                        <CardDescription className="text-xs text-gray-400 font-mono mt-0.5">
                          {tpl.folder_path} • v{tpl.latest_version} ({tpl.format.toUpperCase()})
                        </CardDescription>
                      </div>
                    </div>
                    <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">
                      {tpl.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-2 space-y-3">
                  <div className="flex flex-wrap gap-1.5">
                    {tpl.tags.map((tag: string, i: number) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-gray-900 border border-gray-800 text-gray-400">
                        #{tag}
                      </span>
                    ))}
                  </div>
                  <div className="pt-2 border-t border-gray-900 flex items-center justify-between text-xs">
                    <span className="text-gray-500 text-[11px]">Auto-parsed by AI Analyzer</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setSubTab('review')}
                      className="text-amber-500 hover:text-amber-400 hover:bg-gray-900 h-7 text-xs px-2"
                    >
                      Open in Studio →
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Upload & AI Analysis Modal */}
          {uploadModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
              <Card className="bg-gray-950 border border-gray-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
                <CardHeader className="p-6 border-b border-gray-800">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg font-bold text-white flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-amber-500" />
                        AI Template Intelligence Upload
                      </CardTitle>
                      <CardDescription className="text-xs text-gray-400 mt-1">
                        Upload your DOCX template. OctaOS preserves formatting, identifies variables, and maps canonical fields.
                      </CardDescription>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setUploadModalOpen(false)}>
                      <X className="h-4 w-4 text-gray-400" />
                    </Button>
                  </div>
                </CardHeader>

                <CardContent className="p-6 space-y-5">
                  {!analysisResult ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-xs text-gray-400 block mb-1.5">Template Name</label>
                          <Input
                            placeholder="e.g. Senior Leadership Offer Letter"
                            value={uploadName}
                            onChange={(e) => setUploadName(e.target.value)}
                            className="bg-gray-900 border-gray-800 text-xs h-9"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-400 block mb-1.5">Document Purpose / Category</label>
                          <select
                            value={uploadCategory}
                            onChange={(e) => setUploadCategory(e.target.value)}
                            className="w-full bg-gray-900 border border-gray-800 text-xs rounded-md h-9 px-3 text-gray-300"
                          >
                            <option value="offer">Offer Letter</option>
                            <option value="agreement">Employment Agreement</option>
                            <option value="contractor">Contractor Agreement</option>
                            <option value="nda">Non-Disclosure Agreement</option>
                            <option value="compliance">Tax / Statutory Policy</option>
                            <option value="custom">Custom Company Document</option>
                          </select>
                        </div>
                      </div>

                      <div className="border-2 border-dashed border-gray-800 rounded-2xl p-8 text-center bg-gray-900/40 hover:bg-gray-900/60 transition-all cursor-pointer">
                        <Upload className="h-8 w-8 text-amber-500 mx-auto mb-2 opacity-80" />
                        <p className="text-sm font-semibold text-white">Select existing DOCX or HTML template</p>
                        <p className="text-xs text-gray-500 mt-1">Supports tables, content controls, headers, and custom placeholders</p>
                      </div>

                      <div className="flex justify-end gap-2 pt-2">
                        <Button variant="ghost" size="sm" onClick={() => setUploadModalOpen(false)}>Cancel</Button>
                        <Button
                          size="sm"
                          disabled={uploading}
                          onClick={handleSimulateTemplateUpload}
                          className="bg-amber-500 hover:bg-amber-600 text-black font-bold"
                        >
                          {uploading ? (
                            <>Parsing Document Structure...</>
                          ) : (
                            <>Analyze with AI</>
                          )}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3 flex items-center gap-2.5">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                        <span className="text-xs text-emerald-300 font-medium">
                          Analysis Complete: 4 placeholders mapped to canonical schema. 2 clauses detected.
                        </span>
                      </div>

                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Proposed Canonical Field Mappings</h4>
                        <div className="border border-gray-800 rounded-xl divide-y divide-gray-800 overflow-hidden text-xs">
                          {analysisResult.placeholders.map((p: any, i: number) => (
                            <div key={i} className="p-2.5 bg-gray-900/60 flex items-center justify-between">
                              <div>
                                <span className="font-mono text-amber-400 font-semibold">{p.expr}</span>
                                <span className="text-gray-400 mx-2">→</span>
                                <span className="font-mono text-emerald-400">{p.canonical}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="border-gray-700 text-gray-400 text-[10px]">{p.type}</Badge>
                                <span className="text-emerald-400 text-[11px] font-semibold">{p.conf} conf</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-white uppercase tracking-wider">Detected Legal & Sensitive Clauses</h4>
                        <div className="space-y-1.5">
                          {analysisResult.detected_clauses.map((c: any, i: number) => (
                            <div key={i} className="p-2.5 bg-gray-900/40 border border-gray-800 rounded-xl flex items-center justify-between text-xs">
                              <div>
                                <span className="font-semibold text-white">{c.title}</span>
                                <p className="text-[11px] text-gray-400">{c.type} Clause</p>
                              </div>
                              <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px]">
                                {c.status}
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="flex justify-end gap-2 pt-4 border-t border-gray-800">
                        <Button variant="ghost" size="sm" onClick={() => setAnalysisResult(null)}>Re-upload</Button>
                        <Button
                          size="sm"
                          onClick={handlePublishTemplate}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                        >
                          Approve Mappings & Publish Template
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* --- SUBTAB 2: PIPELINES WORKSPACE (VISUAL BUILDER) --- */}
      {subTab === 'builder' && (
        <HRPipelineCanvas
          API_URL={API_URL}
          fetchWithAuth={fetchWithAuth}
          availableTemplates={templates}
          onPipelinePublished={() => {
            notify.success('Pipeline published! Candidate onboarding workflows are now active.');
          }}
        />
      )}

      {/* --- SUBTAB 3: CANDIDATE ONBOARDING TRACKER --- */}
      {subTab === 'onboarding' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {instances.map((inst) => (
              <Card key={inst.id} className="bg-gray-950 border border-gray-800 rounded-2xl p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-base font-bold text-white">{inst.candidate_name}</h3>
                    <p className="text-xs text-gray-400">{inst.role_title} • {inst.employment_type.toUpperCase()}</p>
                  </div>
                  <Badge className={`text-xs ${
                    inst.current_state === 'scheduled'
                      ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    {inst.current_state.replace('_', ' ').toUpperCase()}
                  </Badge>
                </div>

                <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 space-y-2 text-xs">
                  <div className="flex items-center justify-between text-gray-400">
                    <span>Public Portal Access Link:</span>
                    <span className="text-[11px] text-gray-500">{inst.expires_in}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      readOnly
                      value={`https://app.octaos.ai/public/portal/${inst.portal_token}`}
                      className="bg-gray-950 border-gray-800 text-[11px] font-mono h-8"
                    />
                    <Button
                      size="sm"
                      onClick={() => {
                        navigator.clipboard?.writeText(`https://app.octaos.ai/public/portal/${inst.portal_token}`);
                        notify.success('Public candidate portal link copied to clipboard.');
                      }}
                      className="h-8 px-2.5 bg-gray-800 hover:bg-gray-700 text-white"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>

                {inst.has_conflicts && (
                  <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 space-y-1.5">
                    <div className="flex items-center gap-2 text-rose-400 font-bold text-xs">
                      <AlertTriangle className="h-4 w-4" />
                      Evidence Discrepancy Flagged
                    </div>
                    <p className="text-xs text-gray-300">
                      Candidate entered: <span className="text-amber-300 font-semibold">{inst.conflict_details.candidate_value}</span>, but official document OCR extracted: <span className="text-emerald-300 font-semibold">{inst.conflict_details.extracted_value}</span>.
                    </p>
                    <p className="text-[11px] text-gray-400">Source: {inst.conflict_details.source}</p>
                    <div className="flex gap-2 pt-1">
                      <Button
                        size="sm"
                        onClick={() => {
                          notify.success('Document evidence value accepted for full legal name.');
                        }}
                        className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        Accept Document Value
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSubTab('review')}
                        className="h-7 text-xs text-gray-400 hover:text-white"
                      >
                        Inspect in Studio
                      </Button>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-gray-900 text-xs">
                  <span className="text-gray-500">ID: {inst.id}</span>
                  <Button
                    size="sm"
                    onClick={() => setSubTab('review')}
                    className="bg-gray-900 hover:bg-gray-800 text-amber-400 border border-gray-800 text-xs h-8"
                  >
                    Open Review Studio →
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* --- SUBTAB 4: DOCX REVIEW STUDIO --- */}
      {subTab === 'review' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3 space-y-4">
            {/* Review Studio Header Controls */}
            <div className="bg-gray-950 border border-gray-800 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white">{studioDraft.document_name}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <Badge className={`text-xs ${
                    studioDraft.approval_status === 'approved'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  }`}>
                    Status: {studioDraft.approval_status.toUpperCase()}
                  </Badge>

                  {studioDraft.prior_approval_invalidated && (
                    <Badge className="bg-rose-500/10 text-rose-400 border border-rose-500/30 text-xs flex items-center gap-1">
                      <ShieldAlert className="h-3 w-3" />
                      Approval Invalidated By Recent Edit
                    </Badge>
                  )}

                  {studioDraft.bound_sha256 && (
                    <span className="text-[11px] font-mono text-gray-500">
                      SHA: {studioDraft.bound_sha256.slice(0, 12)}...
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {studioDraft.approval_status === 'draft' ? (
                  <Button
                    onClick={handleApproveDraft}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-9 px-4 rounded-xl flex items-center gap-2"
                  >
                    <ShieldCheck className="h-4 w-4" />
                    Approve Version & Lock SHA-256
                  </Button>
                ) : (
                  <Button
                    onClick={() => setScheduleModalOpen(true)}
                    className="bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs h-9 px-4 rounded-xl flex items-center gap-2"
                  >
                    <Calendar className="h-4 w-4" />
                    Schedule Timezone Send
                  </Button>
                )}
              </div>
            </div>

            {/* A4 Paginated Document Canvas */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 flex justify-center">
              <div className="bg-white text-neutral-900 shadow-2xl rounded-sm p-12 max-w-[640px] w-full min-h-[820px] font-serif space-y-5">
                <div className="border-b border-neutral-300 pb-4 text-center">
                  <h1 className="text-xl font-bold tracking-wide uppercase text-neutral-900">OctaCorp Global Technologies</h1>
                  <p className="text-xs text-neutral-500 tracking-wider mt-1">OFFICE OF HUMAN CAPITAL & LEGAL COMPLIANCE</p>
                </div>

                <div className="space-y-4 text-sm leading-relaxed text-neutral-800">
                  {studioDraft.paragraphs.map((pText: string, idx: number) => (
                    <div
                      key={idx}
                      onClick={() => handleEditParagraph(idx)}
                      className="group relative p-2 -mx-2 rounded hover:bg-amber-50 cursor-pointer transition-all border border-transparent hover:border-amber-300"
                    >
                      <p>{pText}</p>
                      <span className="opacity-0 group-hover:opacity-100 absolute right-2 top-2 text-[10px] font-sans font-bold bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded">
                        Click to Edit
                      </span>
                    </div>
                  ))}
                </div>

                <div className="pt-12 border-t border-neutral-200 flex justify-between text-xs font-sans text-neutral-600">
                  <div>
                    <p className="font-bold">Authorized Signatory</p>
                    <p className="mt-1">OctaCorp Global Ltd.</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold">Appointee Acceptance</p>
                    <p className="mt-1">Priya Sharma</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Inspector & Revision Sidebar */}
          <div className="space-y-4">
            <Card className="bg-gray-950 border border-gray-800 rounded-2xl">
              <CardHeader className="p-4 border-b border-gray-800">
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-gray-400">
                  Reconciled Snapshot
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3 text-xs">
                <div>
                  <span className="text-gray-500 block text-[11px]">Candidate Full Name</span>
                  <span className="text-white font-medium">{studioDraft.candidate_name}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Role & Department</span>
                  <span className="text-white font-medium">{studioDraft.role} ({studioDraft.department})</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Total Compensation</span>
                  <span className="text-amber-400 font-mono font-bold">{studioDraft.compensation}</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-[11px]">Commencement Date</span>
                  <span className="text-white font-medium">{studioDraft.start_date}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-950 border border-gray-800 rounded-2xl">
              <CardHeader className="p-4 border-b border-gray-800">
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-gray-400">
                  Audit & Revision History
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                {studioDraft.revisions.map((rev: any, i: number) => (
                  <div key={i} className="text-xs border-l-2 border-amber-500/50 pl-2.5 py-1 space-y-0.5">
                    <div className="flex items-center justify-between text-gray-400">
                      <span className="font-semibold text-gray-300">{rev.user}</span>
                      <span className="text-[10px] text-gray-500">{rev.time}</span>
                    </div>
                    <p className="text-[11px] text-gray-400 leading-snug">{rev.action}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Edit Paragraph Modal */}
          {editingParagraphIdx !== null && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
              <Card className="bg-gray-950 border border-gray-800 rounded-2xl w-full max-w-lg p-5 space-y-4">
                <h3 className="text-sm font-bold text-white">Edit Paragraph {editingParagraphIdx + 1}</h3>
                <textarea
                  rows={4}
                  value={editText}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setEditText(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-800 text-xs text-white rounded-xl p-3 focus:outline-none focus:border-amber-500"
                />
                <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 text-xs">
                  ⚠️ Note: Saving changes to this document will automatically invalidate any prior approval for this version.
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setEditingParagraphIdx(null)}>Cancel</Button>
                  <Button size="sm" onClick={handleSaveParagraph} className="bg-amber-500 hover:bg-amber-600 text-black font-bold">
                    Save Edit
                  </Button>
                </div>
              </Card>
            </div>
          )}

          {/* Schedule Dispatch Modal */}
          {scheduleModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
              <Card className="bg-gray-950 border border-gray-800 rounded-2xl w-full max-w-md p-5 space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-500" />
                  Schedule Document Dispatch
                </h3>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="text-gray-400 block mb-1">Release Date & Time</label>
                    <Input
                      type="datetime-local"
                      value={scheduledDate}
                      onChange={(e) => setScheduledDate(e.target.value)}
                      className="bg-gray-900 border-gray-800 text-xs h-9"
                    />
                  </div>

                  <div>
                    <label className="text-gray-400 block mb-1">Target Timezone</label>
                    <select
                      value={scheduledTimezone}
                      onChange={(e) => setScheduledTimezone(e.target.value)}
                      className="w-full bg-gray-900 border border-gray-800 text-xs rounded-md h-9 px-3 text-gray-300"
                    >
                      <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                      <option value="America/New_York">America/New_York (EST)</option>
                      <option value="Europe/London">Europe/London (GMT)</option>
                      <option value="UTC">UTC</option>
                    </select>
                  </div>

                  <div className="p-3 bg-gray-900 border border-gray-800 rounded-xl space-y-1">
                    <span className="font-semibold text-emerald-400">Pre-Flight Revalidation:</span>
                    <p className="text-gray-400 text-[11px]">
                      Prior to release, the orchestrator will verify that content SHA-256 matches the approval hash.
                    </p>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="ghost" size="sm" onClick={() => setScheduleModalOpen(false)}>Cancel</Button>
                  <Button size="sm" onClick={handleScheduleDispatch} className="bg-amber-500 hover:bg-amber-600 text-black font-bold">
                    Schedule Release
                  </Button>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

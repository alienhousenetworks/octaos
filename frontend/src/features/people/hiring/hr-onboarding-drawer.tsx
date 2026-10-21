'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';
import {
  Building2,
  User,
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
  Award,
  Check,
  FileCheck,
  Fingerprint,
} from 'lucide-react';

export interface OnboardingInstanceData {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email?: string | null;
  role_title: string;
  current_state: string;
  expires_at: string;
  candidate_portal_url: string;
  missing_from_company: string[];
  missing_from_candidate: string[];
  required_documents: {
    document_category: string;
    title: string;
    description: string;
    is_mandatory: boolean;
  }[];
  uploaded_evidence: {
    id: string;
    document_name: string;
    document_category: string;
    file_sha256: string;
    uploaded_at: string;
    extracted_data?: Record<string, any>;
  }[];
  company_fields: Record<string, any>;
  progress_percentage: number;
}

interface HROnboardingDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  instance: OnboardingInstanceData | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onInstanceUpdated: () => void;
}

export default function HROnboardingDrawer({
  isOpen,
  onClose,
  instance,
  API_URL,
  fetchWithAuth,
  onInstanceUpdated,
}: HROnboardingDrawerProps) {
  const [activeTab, setActiveTab] = useState<'company' | 'candidate' | 'verification'>('company');
  const [savingCompany, setSavingCompany] = useState(false);
  const [savingDocs, setSavingDocs] = useState(false);

  // Verification & Provisioning state
  const [verifyingEvidenceId, setVerifyingEvidenceId] = useState<string | null>(null);
  const [signingOffEvidenceId, setSigningOffEvidenceId] = useState<string | null>(null);
  const [provisioning, setProvisioning] = useState(false);
  const [provisionResult, setProvisionResult] = useState<any | null>(null);

  // Editable company fields
  const [companyFields, setCompanyFields] = useState<Record<string, string>>({
    annual_ctc: '',
    start_date: '',
    department: '',
    signatory_name: '',
  });

  // Dynamic document requirements
  const [docsList, setDocsList] = useState<any[]>([]);
  const [newDocTitle, setNewDocTitle] = useState('');
  const [newDocDesc, setNewDocDesc] = useState('');
  const [newDocMandatory, setNewDocMandatory] = useState(true);
  const [showAddDocForm, setShowAddDocForm] = useState(false);

  // Sync state whenever instance changes
  React.useEffect(() => {
    if (instance) {
      const cf = instance.company_fields || {};
      setCompanyFields({
        annual_ctc: cf.annual_ctc || cf['compensation.annual_ctc'] || '',
        start_date: cf.start_date || cf['role.start_date'] || '',
        department: cf.department || cf['organization.department'] || '',
        signatory_name: cf.signatory_name || cf['company.signatory_name'] || '',
      });
      setDocsList(instance.required_documents || []);
    }
  }, [instance]);

  if (!instance) return null;

  const handleVerifySignedDocument = async (evidenceId: string) => {
    setVerifyingEvidenceId(evidenceId);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/hr/workflow/instances/${instance.id}/verify-signed-document?evidence_id=${evidenceId}`,
        { method: 'POST' }
      );
      if (res.ok) {
        const data = await res.json();
        notify.success(`Document Verified: ${data.decision_summary || data.status}`);
        onInstanceUpdated();
      } else {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Failed to verify signed document.');
      }
    } catch {
      notify.error('Network error during document verification.');
    } finally {
      setVerifyingEvidenceId(null);
    }
  };

  const handleHRSignoff = async (evidenceId: string) => {
    setSigningOffEvidenceId(evidenceId);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/hr/workflow/instances/${instance.id}/hr-verify-signature?evidence_id=${evidenceId}`,
        { method: 'POST' }
      );
      if (res.ok) {
        notify.success('Document signature authorized and confirmed by HR.');
        onInstanceUpdated();
      } else {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Sign-off authorization failed.');
      }
    } catch {
      notify.error('Network error during HR sign-off.');
    } finally {
      setSigningOffEvidenceId(null);
    }
  };

  const handleCompleteAndProvision = async () => {
    setProvisioning(true);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/hr/workflow/instances/${instance.id}/complete-onboarding-and-provision`,
        { method: 'POST' }
      );
      if (res.ok) {
        const data = await res.json();
        setProvisionResult(data);
        notify.success(
          `Candidate provisioned as Employee ${data.employee_number} in ${data.department}!`
        );
        onInstanceUpdated();
      } else {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Failed to complete employee provisioning.');
      }
    } catch {
      notify.error('Network error provisioning employee.');
    } finally {
      setProvisioning(false);
    }
  };

  const handleSaveCompanyFields = async () => {
    setSavingCompany(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/workflow/instances/${instance.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_fields: companyFields,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Failed to save company information.');
        return;
      }

      notify.success('Company onboarding information updated.');
      onInstanceUpdated();
    } catch {
      notify.error('Network error saving company fields.');
    } finally {
      setSavingCompany(false);
    }
  };

  const handleAddCustomDocument = async () => {
    if (!newDocTitle.trim()) {
      notify.error('Please enter a document title.');
      return;
    }

    const newCategory = newDocTitle
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '_')
      .slice(0, 32);

    const updated = [
      ...docsList,
      {
        document_category: newCategory,
        title: newDocTitle.trim(),
        description: newDocDesc.trim() || 'Upload official proof document',
        is_mandatory: newDocMandatory,
        accepted_mimes: ['application/pdf', 'image/jpeg', 'image/png'],
      },
    ];

    setDocsList(updated);
    setNewDocTitle('');
    setNewDocDesc('');
    setShowAddDocForm(false);

    // Save to backend
    setSavingDocs(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/workflow/instances/${instance.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          required_documents: updated,
        }),
      });

      if (res.ok) {
        notify.success('New document requirement added and saved to candidate portal.');
        onInstanceUpdated();
      } else {
        notify.error('Failed to update required documents.');
      }
    } catch {
      notify.error('Network error saving document requirement.');
    } finally {
      setSavingDocs(false);
    }
  };

  const handleRemoveDocument = async (category: string) => {
    const updated = docsList.filter((d) => d.document_category !== category);
    setDocsList(updated);

    setSavingDocs(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/workflow/instances/${instance.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          required_documents: updated,
        }),
      });

      if (res.ok) {
        notify.success('Document requirement removed.');
        onInstanceUpdated();
      }
    } catch {
      notify.error('Network error updating documents.');
    } finally {
      setSavingDocs(false);
    }
  };

  const uploadedCategories = new Set(
    (instance.uploaded_evidence || []).map((e) => e.document_category)
  );

  const fullPortalUrl = typeof window !== 'undefined'
    ? `${window.location.origin}${instance.candidate_portal_url}`
    : instance.candidate_portal_url;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-card border-border text-foreground p-0 overflow-hidden shadow-2xl rounded-2xl">
        {/* Header Ribbon */}
        <div className="p-6 border-b border-border bg-muted/20 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <DialogTitle className="text-lg font-bold text-foreground">
                  {instance.candidate_name}
                </DialogTitle>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
                  {instance.role_title}
                </span>
                <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-muted text-muted-foreground border border-border">
                  {instance.progress_percentage}% Onboarded
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Onboarding Instance ID: <span className="font-mono">{instance.id.slice(0, 12)}…</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  navigator.clipboard.writeText(fullPortalUrl);
                  notify.success('Candidate Portal URL copied to clipboard!');
                }}
                className="h-8 text-xs font-semibold flex items-center gap-1.5"
              >
                <Copy size={13} /> Copy Portal Link
              </Button>
              <Button
                size="sm"
                onClick={() => window.open(instance.candidate_portal_url, '_blank')}
                className="h-8 text-xs font-semibold flex items-center gap-1.5"
              >
                <ExternalLink size={13} /> Open Portal
              </Button>
            </div>
          </div>

          {/* Missing Triage Metric Pill Ribbon (3 Tabs) */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs pt-2">
            <button
              type="button"
              onClick={() => setActiveTab('company')}
              className={`p-2.5 rounded-xl border text-left transition-all ${
                activeTab === 'company'
                  ? 'border-primary bg-primary/10 shadow-2xs'
                  : 'border-border bg-card/60 hover:bg-surface-hover'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground flex items-center gap-1.5 truncate">
                  <Building2 size={13} className="text-primary shrink-0" /> Company / HR
                </span>
                {instance.missing_from_company.length > 0 ? (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/20">
                    {instance.missing_from_company.length} Missing
                  </span>
                ) : (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#263D38] text-[#64B99A]">
                    Complete
                  </span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                {instance.missing_from_company.length > 0
                  ? instance.missing_from_company.join(', ')
                  : 'All company inputs resolved'}
              </p>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('candidate')}
              className={`p-2.5 rounded-xl border text-left transition-all ${
                activeTab === 'candidate'
                  ? 'border-primary bg-primary/10 shadow-2xs'
                  : 'border-border bg-card/60 hover:bg-surface-hover'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground flex items-center gap-1.5 truncate">
                  <User size={13} className="text-primary shrink-0" /> Candidate Proofs
                </span>
                {instance.missing_from_candidate.length > 0 ? (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-destructive/10 text-destructive border border-destructive/20">
                    {instance.missing_from_candidate.length} Pending
                  </span>
                ) : (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#263D38] text-[#64B99A]">
                    All Uploaded
                  </span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                {instance.missing_from_candidate.length > 0
                  ? instance.missing_from_candidate.join(', ')
                  : 'All documents submitted'}
              </p>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('verification')}
              className={`p-2.5 rounded-xl border text-left transition-all ${
                activeTab === 'verification'
                  ? 'border-emerald-500/60 bg-emerald-500/10 shadow-2xs'
                  : 'border-border bg-card/60 hover:bg-surface-hover'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground flex items-center gap-1.5 truncate">
                  <ShieldCheck size={13} className="text-emerald-400 shrink-0" /> Sign &amp; Provision
                </span>
                {instance.current_state === 'completed' || provisionResult ? (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                    Hired
                  </span>
                ) : (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    {instance.current_state}
                  </span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                {instance.current_state === 'completed' || provisionResult
                  ? 'Employee active in dept'
                  : 'PKI verification & employee provision'}
              </p>
            </button>
          </div>
        </div>

        {/* Tab Body */}
        <div className="p-6 max-h-[460px] overflow-y-auto space-y-4">
          {/* TAB 1: COMPANY / HR SIDE */}
          {activeTab === 'company' && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-foreground flex items-center gap-2">
                  <Building2 size={14} className="text-primary" />
                  <span>Company-Side Onboarding Parameters</span>
                </h4>
                <p className="text-xs text-muted-foreground">
                  The system detected the following company fields required for official offer &amp; agreement generation. Fill them below to resolve missing status.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Annual CTC / Salary *</label>
                  <Input
                    placeholder="e.g. ₹24,00,000 / year or $130,000"
                    value={companyFields.annual_ctc}
                    onChange={(e) => setCompanyFields({ ...companyFields, annual_ctc: e.target.value })}
                    className="h-8.5 text-xs bg-surface-hover/40 border-border"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Joining / Start Date *</label>
                  <Input
                    type="date"
                    value={companyFields.start_date}
                    onChange={(e) => setCompanyFields({ ...companyFields, start_date: e.target.value })}
                    className="h-8.5 text-xs bg-surface-hover/40 border-border"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Department *</label>
                  <Input
                    placeholder="e.g. Engineering, Product Design"
                    value={companyFields.department}
                    onChange={(e) => setCompanyFields({ ...companyFields, department: e.target.value })}
                    className="h-8.5 text-xs bg-surface-hover/40 border-border"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-muted-foreground">Authorized Signatory Name *</label>
                  <Input
                    placeholder="e.g. Jane Smith, VP HR"
                    value={companyFields.signatory_name}
                    onChange={(e) => setCompanyFields({ ...companyFields, signatory_name: e.target.value })}
                    className="h-8.5 text-xs bg-surface-hover/40 border-border"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-border flex justify-end">
                <Button
                  size="sm"
                  disabled={savingCompany}
                  onClick={handleSaveCompanyFields}
                  className="h-8 text-xs font-bold flex items-center gap-1.5"
                >
                  {savingCompany ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                  <span>Save Company Information</span>
                </Button>
              </div>
            </div>
          )}

          {/* TAB 2: CANDIDATE SIDE & REQUIRED DOCUMENTS */}
          {activeTab === 'candidate' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h4 className="text-xs font-bold text-foreground">
                    Required Candidate Documents ({docsList.length})
                  </h4>
                  <p className="text-xs text-muted-foreground">
                    HR controls which document proofs are requested from this candidate.
                  </p>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowAddDocForm((prev) => !prev)}
                  className="h-7 text-xs font-semibold flex items-center gap-1"
                >
                  <Plus size={12} /> Add Document Requirement
                </Button>
              </div>

              {/* Add Custom Document Sub-Form */}
              {showAddDocForm && (
                <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 space-y-3 text-xs">
                  <span className="font-bold text-foreground">Add Custom Document Request</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-muted-foreground">Document Title *</label>
                      <Input
                        placeholder="e.g. Previous Employer Relieving Letter"
                        value={newDocTitle}
                        onChange={(e) => setNewDocTitle(e.target.value)}
                        className="h-8 text-xs bg-card border-border"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] font-semibold text-muted-foreground">Instructions</label>
                      <Input
                        placeholder="e.g. Signed relieving letter on company letterhead"
                        value={newDocDesc}
                        onChange={(e) => setNewDocDesc(e.target.value)}
                        className="h-8 text-xs bg-card border-border"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-medium">
                      <input
                        type="checkbox"
                        checked={newDocMandatory}
                        onChange={(e) => setNewDocMandatory(e.target.checked)}
                        className="rounded border-border text-primary"
                      />
                      <span>Mark as Mandatory requirement</span>
                    </label>

                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowAddDocForm(false)}
                        className="h-7 text-xs"
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        disabled={savingDocs || !newDocTitle.trim()}
                        onClick={handleAddCustomDocument}
                        className="h-7 text-xs font-bold"
                      >
                        {savingDocs ? <Loader2 size={12} className="animate-spin mr-1" /> : null}
                        Save to Candidate Portal
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* Documents Checklist Stream */}
              <div className="space-y-2">
                {docsList.map((doc) => {
                  const isUploaded = uploadedCategories.has(doc.document_category);
                  const evidence = (instance.uploaded_evidence || []).find(
                    (e) => e.document_category === doc.document_category
                  );

                  return (
                    <div
                      key={doc.document_category}
                      className="p-3 rounded-xl border border-border bg-card/60 flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-foreground">{doc.title}</span>
                          {doc.is_mandatory ? (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-destructive/10 text-destructive border border-destructive/20">
                              Mandatory
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-muted text-muted-foreground">
                              Optional
                            </span>
                          )}
                          {isUploaded ? (
                            <span className="px-2 py-0.2 rounded text-[10px] font-bold bg-[#263D38] text-[#64B99A] border border-[#64B99A]/30 flex items-center gap-1">
                              <CheckCircle2 size={11} /> Uploaded
                            </span>
                          ) : (
                            <span className="px-2 py-0.2 rounded text-[10px] font-bold bg-muted text-muted-foreground flex items-center gap-1">
                              <Clock size={11} /> Pending Candidate Upload
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground truncate">{doc.description}</p>
                        {evidence && (
                          <p className="text-[10px] font-mono text-[#64B99A] truncate">
                            File: {evidence.document_name} • SHA: {evidence.file_sha256.slice(0, 10)}…
                          </p>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => handleRemoveDocument(doc.document_category)}
                        className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                        title="Remove requirement"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: SIGNED CONTRACT VERIFICATION & PROVISIONING */}
          {activeTab === 'verification' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h4 className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    <Fingerprint size={14} className="text-emerald-400" />
                    <span>Signed Document Verification &amp; Employee Creation</span>
                  </h4>
                  <p className="text-xs text-muted-foreground">
                    Verifies cryptographic PKI certificates, electronic ink strokes, and provisions the employee into their department.
                  </p>
                </div>
              </div>

              {/* Provisioned Success Banner */}
              {(instance.current_state === 'completed' || provisionResult) && (
                <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-500/10 space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={16} className="text-emerald-400" />
                    <span className="text-xs font-bold text-emerald-300">
                      Employee Successfully Provisioned &amp; Hired!
                    </span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-1">
                    <div className="bg-background/40 p-2 rounded-lg border border-border">
                      <span className="text-[10px] text-muted-foreground block">Employee Number</span>
                      <span className="font-mono font-bold text-foreground">
                        {provisionResult?.employee_number || 'EMP-Active'}
                      </span>
                    </div>
                    <div className="bg-background/40 p-2 rounded-lg border border-border">
                      <span className="text-[10px] text-muted-foreground block">Department</span>
                      <span className="font-semibold text-foreground">
                        {provisionResult?.department || companyFields.department || 'Engineering'}
                      </span>
                    </div>
                    <div className="bg-background/40 p-2 rounded-lg border border-border">
                      <span className="text-[10px] text-muted-foreground block">Role</span>
                      <span className="font-semibold text-foreground">{instance.role_title}</span>
                    </div>
                    <div className="bg-background/40 p-2 rounded-lg border border-border">
                      <span className="text-[10px] text-muted-foreground block">Status</span>
                      <span className="font-semibold text-emerald-400">Active</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Uploaded Evidence Verification Stream */}
              <div className="space-y-2.5">
                <span className="text-xs font-semibold text-foreground block">
                  Uploaded Documents &amp; Verification Seals ({instance.uploaded_evidence?.length || 0})
                </span>

                {(!instance.uploaded_evidence || instance.uploaded_evidence.length === 0) ? (
                  <div className="p-6 rounded-xl border border-dashed border-border text-center text-xs text-muted-foreground">
                    No documents uploaded yet by the candidate.
                  </div>
                ) : (
                  instance.uploaded_evidence.map((evidence) => {
                    const report = (evidence as any).extracted_data?.verification_report;
                    const isSignedCat =
                      evidence.document_category.includes('sign') ||
                      evidence.document_category === 'signed_contract' ||
                      evidence.document_category === 'signed_nda';

                    return (
                      <div
                        key={evidence.id}
                        className="p-3.5 rounded-xl border border-border bg-card/70 space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-2">
                            <FileCheck size={14} className="text-primary" />
                            <span className="font-bold text-foreground">{evidence.document_name}</span>
                            <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-muted text-muted-foreground">
                              {evidence.document_category}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {report?.status === 'VERIFIED' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                                <Check size={11} /> HR Confirmed
                              </span>
                            )}
                            {report?.status === 'ELIGIBLE_FOR_APPROVAL' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30">
                                Verified (Eligible)
                              </span>
                            )}
                            {report?.status === 'REVIEW_REQUIRED' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                Review Required
                              </span>
                            )}
                            {report?.status === 'BLOCKED' && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-destructive/10 text-destructive border border-destructive/30">
                                Blocked / Tampered
                              </span>
                            )}
                            {!report && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-muted-foreground">
                                Unverified
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Verification Details Badges */}
                        {report && (
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 bg-background/50 p-2.5 rounded-lg border border-border text-[11px]">
                            <div>
                              <span className="text-[10px] text-muted-foreground block">Digital PKI:</span>
                              <span className="font-semibold text-foreground">
                                {report.has_digital_signature
                                  ? `✓ Detected (${report.pki_details?.[0]?.filter || 'PKCS7'})`
                                  : 'None'}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-muted-foreground block">Electronic Ink:</span>
                              <span className="font-semibold text-foreground">
                                {report.has_visual_signature ? '✓ Detected' : 'None'}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-muted-foreground block">SHA-256 Digest:</span>
                              <span className="font-mono text-[10px] text-muted-foreground truncate block">
                                {evidence.file_sha256.slice(0, 16)}…
                              </span>
                            </div>
                          </div>
                        )}

                        {/* Action buttons */}
                        <div className="flex items-center justify-end gap-2 pt-1">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={verifyingEvidenceId === evidence.id}
                            onClick={() => handleVerifySignedDocument(evidence.id)}
                            className="h-7 text-xs font-semibold flex items-center gap-1"
                          >
                            {verifyingEvidenceId === evidence.id ? (
                              <Loader2 size={11} className="animate-spin" />
                            ) : (
                              <Fingerprint size={12} />
                            )}
                            <span>{report ? 'Re-Verify File' : 'Run Verification'}</span>
                          </Button>

                          {report && report.status !== 'VERIFIED' && (
                            <Button
                              size="sm"
                              disabled={signingOffEvidenceId === evidence.id}
                              onClick={() => handleHRSignoff(evidence.id)}
                              className="h-7 text-xs font-bold bg-[#64B99A] text-black hover:bg-[#52a788] flex items-center gap-1"
                            >
                              {signingOffEvidenceId === evidence.id ? (
                                <Loader2 size={11} className="animate-spin" />
                              ) : (
                                <Award size={12} />
                              )}
                              <span>Authorize HR Sign-off</span>
                            </Button>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Complete Onboarding & Provision Button */}
              {instance.current_state !== 'completed' && !provisionResult && (
                <div className="pt-2">
                  <Button
                    onClick={handleCompleteAndProvision}
                    disabled={provisioning}
                    className="w-full h-10 text-xs font-bold bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-md flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {provisioning ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Award size={15} />
                    )}
                    <span>Complete Onboarding &amp; Provision Employee (EMP-XXXX)</span>
                  </Button>
                  <p className="text-[10px] text-muted-foreground text-center mt-1.5">
                    Atomically allocates next sequential employee number and assigns to {companyFields.department || 'the candidate department'}.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between">
          <Button size="sm" variant="ghost" onClick={onClose} className="h-8 text-xs text-muted-foreground hover:text-foreground">
            Close
          </Button>

          <Button
            size="sm"
            onClick={() => {
              navigator.clipboard.writeText(fullPortalUrl);
              notify.success('Candidate Portal Link copied to clipboard!');
            }}
            className="h-8 text-xs font-bold flex items-center gap-1.5"
          >
            <Copy size={13} />
            <span>Copy Candidate Portal Link</span>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

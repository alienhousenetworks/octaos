'use client';

import React, { useState, useEffect, use } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';
import {
  ShieldCheck,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Clock,
  User,
  Building,
  Mail,
  Phone,
  MapPin,
  Lock,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Loader2,
  Check,
  FileCheck,
} from 'lucide-react';

interface CandidatePortalProps {
  params: Promise<{ token: string }>;
}

export default function CandidatePortalPage({ params }: CandidatePortalProps) {
  const resolvedParams = use(params);
  const token = resolvedParams.token;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<any | null>(null);
  const [activeStep, setActiveStep] = useState<number>(1);

  // Intake form data
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [submittingIntake, setSubmittingIntake] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const fetchSession = async () => {
    try {
      const res = await fetch(`${API_URL}/candidate_portal/session/${token}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'Invalid or expired onboarding session link.');
        setLoading(false);
        return;
      }
      const data = await res.json();
      setSession(data);

      // Pre-fill existing form fields
      const initial: Record<string, string> = {};
      if (data.field_values) {
        Object.entries(data.field_values).forEach(([k, v]) => {
          if (v) initial[k] = String(v);
        });
      }
      // Prefill synthesized fields
      if (data.synthesized_fields) {
        data.synthesized_fields.forEach((f: any) => {
          if (!initial[f.canonical_key]) {
            if (f.canonical_key === 'candidate.full_name' && data.candidate_name) {
              initial[f.canonical_key] = data.candidate_name;
            } else {
              initial[f.canonical_key] = '';
            }
          }
        });
      }
      setFormData(initial);
      if (data.status === 'review_ready' || data.status === 'completed') {
        setCompleted(true);
      }
    } catch {
      setError('Unable to connect to onboarding service. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchSession();
  }, [token]);

  // Handle document upload
  const handleFileUpload = async (category: string, file: File) => {
    setUploadingDoc(category);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('category', category);

      const res = await fetch(`${API_URL}/candidate_portal/session/${token}/upload`, {
        method: 'POST',
        body: form,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Upload failed');
        return;
      }

      notify.success('Document uploaded successfully.');
      await fetchSession();
    } catch {
      notify.error('Network error during upload.');
    } finally {
      setUploadingDoc(null);
    }
  };

  // Handle intake submission
  const handleSubmitIntake = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSubmittingIntake(true);
    try {
      const res = await fetch(`${API_URL}/candidate_portal/session/${token}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field_values: formData }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Failed to submit onboarding form.');
        return;
      }

      notify.success('Onboarding information successfully submitted!');
      setCompleted(true);
      setActiveStep(3);
      await fetchSession();
    } catch {
      notify.error('Network error submitting questionnaire.');
    } finally {
      setSubmittingIntake(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
        <Loader2 className="size-8 animate-spin text-primary mb-3" />
        <p className="text-sm text-muted-foreground">Opening secure candidate portal…</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
        <Card className="max-w-md w-full border-border bg-card p-6 text-center space-y-4">
          <div className="size-12 rounded-full bg-destructive/10 text-destructive mx-auto flex items-center justify-center">
            <Lock className="size-6" />
          </div>
          <CardTitle className="text-lg font-bold">Access Link Inactive</CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            {error || 'This onboarding session token is invalid, expired, or has already been fulfilled.'}
          </CardDescription>
          <p className="text-xs text-muted-foreground">
            If you believe this is an error, please reach out to your HR hiring representative to generate a fresh link.
          </p>
        </Card>
      </div>
    );
  }

  const uploadedCategories = new Set(
    (session.uploaded_evidence || []).map((e: any) => e.document_category)
  );

  const totalMandatoryDocs = (session.required_documents || []).filter((d: any) => d.is_mandatory).length;
  const uploadedMandatoryDocs = (session.required_documents || []).filter(
    (d: any) => d.is_mandatory && uploadedCategories.has(d.document_category)
  ).length;

  const allMandatoryUploaded = totalMandatoryDocs === 0 || uploadedMandatoryDocs >= totalMandatoryDocs;

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Navigation Bar */}
      <header className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="size-9 rounded-xl bg-primary/10 border border-primary/20 text-primary flex items-center justify-center font-bold">
              <Building className="size-5" />
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {session.company_name}
              </div>
              <h1 className="text-sm font-bold text-foreground">Candidate Onboarding Portal</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              <ShieldCheck className="size-3.5" /> Secure Session
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-4xl mx-auto w-full px-4 py-8 flex-1 space-y-6">
        {/* Candidate Welcome Banner */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-xs relative overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-xs font-semibold text-primary uppercase tracking-wider">Welcome</span>
              <h2 className="text-2xl font-bold tracking-tight text-foreground mt-0.5">
                {session.candidate_name}
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Role: <strong className="text-foreground">{session.role_title}</strong> at {session.company_name}
              </p>
            </div>
            <div className="flex flex-col items-start sm:items-end text-xs text-muted-foreground">
              <span>Token expires in</span>
              <span className="font-semibold text-foreground flex items-center gap-1 mt-0.5">
                <Clock className="size-3.5 text-primary" />
                {new Date(session.expires_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </span>
            </div>
          </div>

          {/* Stepper Navigation */}
          <div className="mt-6 pt-5 border-t border-border grid grid-cols-3 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setActiveStep(1)}
              className={`flex items-center gap-2 p-2 rounded-lg text-left transition-all ${
                activeStep === 1
                  ? 'bg-primary/10 text-primary font-bold border border-primary/30'
                  : 'text-muted-foreground hover:bg-surface-hover'
              }`}
            >
              <span className="size-6 rounded-full flex items-center justify-center bg-card border border-border text-[11px] font-bold shrink-0">
                1
              </span>
              <span className="truncate">Personal Info</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveStep(2)}
              className={`flex items-center gap-2 p-2 rounded-lg text-left transition-all ${
                activeStep === 2
                  ? 'bg-primary/10 text-primary font-bold border border-primary/30'
                  : 'text-muted-foreground hover:bg-surface-hover'
              }`}
            >
              <span className="size-6 rounded-full flex items-center justify-center bg-card border border-border text-[11px] font-bold shrink-0">
                2
              </span>
              <span className="truncate">Document Proofs ({uploadedMandatoryDocs}/{totalMandatoryDocs})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveStep(3)}
              className={`flex items-center gap-2 p-2 rounded-lg text-left transition-all ${
                activeStep === 3
                  ? 'bg-primary/10 text-primary font-bold border border-primary/30'
                  : 'text-muted-foreground hover:bg-surface-hover'
              }`}
            >
              <span className="size-6 rounded-full flex items-center justify-center bg-card border border-border text-[11px] font-bold shrink-0">
                3
              </span>
              <span className="truncate">Review &amp; Submit</span>
            </button>
          </div>
        </div>

        {/* STEP 1: Personal Intake Information */}
        {activeStep === 1 && (
          <Card className="border-border bg-card">
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <User className="size-4 text-primary" />
                <span>Step 1: Complete Personal Details</span>
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground">
                Please verify your statutory details. These will be automatically filled into your employment contract.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(session.synthesized_fields || []).map((field: any) => (
                  <div key={field.canonical_key} className="space-y-1.5">
                    <label className="text-xs font-semibold text-foreground flex items-center gap-1">
                      {field.label}
                      {field.is_required && <span className="text-destructive">*</span>}
                    </label>
                    <Input
                      type={field.data_type === 'date' ? 'date' : 'text'}
                      value={formData[field.canonical_key] || ''}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, [field.canonical_key]: e.target.value }))
                      }
                      placeholder={field.sample_placeholder || `Enter ${field.label}`}
                      className="h-9 text-xs bg-surface-hover/40 border-border"
                    />
                    {field.description && (
                      <p className="text-[11px] text-muted-foreground">{field.description}</p>
                    )}
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-border flex justify-end">
                <Button
                  type="button"
                  onClick={() => setActiveStep(2)}
                  className="h-8.5 text-xs font-bold flex items-center gap-1.5"
                >
                  <span>Continue to Document Proofs</span>
                  <ArrowRight className="size-3.5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* STEP 2: Document Proofs Checklist */}
        {activeStep === 2 && (
          <Card className="border-border bg-card">
            <CardHeader className="pb-3 border-b border-border">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <FileText className="size-4 text-primary" />
                    <span>Step 2: Upload Required Document Proofs</span>
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground mt-0.5">
                    HR has requested the following documents to verify your profile and generate your legal contract.
                  </CardDescription>
                </div>
                <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-muted text-foreground border border-border shrink-0">
                  {uploadedMandatoryDocs} of {totalMandatoryDocs} uploaded
                </span>
              </div>
            </CardHeader>
            <CardContent className="pt-5 space-y-4">
              <div className="space-y-3">
                {(session.required_documents || []).map((doc: any) => {
                  const isUploaded = uploadedCategories.has(doc.document_category);
                  const evidenceItem = (session.uploaded_evidence || []).find(
                    (e: any) => e.document_category === doc.document_category
                  );
                  const isUploading = uploadingDoc === doc.document_category;

                  return (
                    <div
                      key={doc.document_category}
                      className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                        isUploaded
                          ? 'border-[#64B99A]/40 bg-[#263D38]/10'
                          : 'border-border bg-card/60 hover:bg-surface-hover/40'
                      }`}
                    >
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-sm text-foreground">{doc.title}</span>
                          {doc.is_mandatory ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-destructive/10 text-destructive border border-destructive/20">
                              Mandatory
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-muted-foreground">
                              Optional
                            </span>
                          )}
                          {isUploaded && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#263D38] text-[#64B99A] border border-[#64B99A]/30 flex items-center gap-1">
                              <CheckCircle2 className="size-3" /> Uploaded &amp; Verified
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">{doc.description}</p>
                        {evidenceItem && (
                          <div className="text-[11px] font-mono text-muted-foreground flex items-center gap-2 pt-1">
                            <span className="truncate text-foreground font-medium">{evidenceItem.document_name}</span>
                            <span>•</span>
                            <span className="truncate">SHA: {evidenceItem.file_sha256.slice(0, 8)}…</span>
                          </div>
                        )}
                      </div>

                      <div className="shrink-0 flex items-center gap-2">
                        <label className="cursor-pointer">
                          <input
                            type="file"
                            accept=".pdf,.png,.jpg,.jpeg,.docx"
                            className="hidden"
                            disabled={isUploading}
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleFileUpload(doc.document_category, file);
                            }}
                          />
                          <span
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-xs ${
                              isUploaded
                                ? 'bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border'
                                : 'bg-primary text-primary-foreground hover:bg-primary/90'
                            }`}
                          >
                            {isUploading ? (
                              <>
                                <Loader2 className="size-3.5 animate-spin" />
                                <span>Uploading…</span>
                              </>
                            ) : (
                              <>
                                <Upload className="size-3.5" />
                                <span>{isUploaded ? 'Replace Document' : 'Upload File'}</span>
                              </>
                            )}
                          </span>
                        </label>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="pt-4 border-t border-border flex items-center justify-between">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setActiveStep(1)}
                  className="text-xs font-semibold flex items-center gap-1.5"
                >
                  <ArrowLeft className="size-3.5" />
                  <span>Back to Personal Info</span>
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => setActiveStep(3)}
                  className="text-xs font-bold flex items-center gap-1.5"
                >
                  <span>Review &amp; Finalize</span>
                  <ArrowRight className="size-3.5" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* STEP 3: Review & Finalize Submission */}
        {activeStep === 3 && (
          <Card className="border-border bg-card">
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <FileCheck className="size-4 text-[#64B99A]" />
                <span>Step 3: Review &amp; Submit to HR</span>
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground">
                Review your details before transmitting to {session.company_name}.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-5 space-y-5">
              {completed ? (
                <div className="p-6 rounded-2xl bg-[#263D38]/20 border border-[#64B99A]/40 text-center space-y-3">
                  <div className="size-12 rounded-full bg-[#263D38] text-[#64B99A] mx-auto flex items-center justify-center">
                    <Check className="size-6" />
                  </div>
                  <h3 className="text-lg font-bold text-foreground">Onboarding Submission Received!</h3>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
                    Thank you, {session.candidate_name}. Your personal details and document evidence have been securely transmitted to the HR team at {session.company_name}. You will receive your appointment letter once reviewed.
                  </p>
                </div>
              ) : (
                <>
                  {/* Summary Checks */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
                      <span className="text-[11px] font-bold text-muted-foreground uppercase">
                        Personal Details Provided
                      </span>
                      <div className="text-xs font-medium text-foreground">
                        {Object.values(formData).filter(Boolean).length} fields filled
                      </div>
                    </div>
                    <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
                      <span className="text-[11px] font-bold text-muted-foreground uppercase">
                        Evidence Documents
                      </span>
                      <div className="text-xs font-medium text-foreground flex items-center gap-1.5">
                        {allMandatoryUploaded ? (
                          <span className="text-[#64B99A] flex items-center gap-1">
                            <CheckCircle2 className="size-3.5" /> All mandatory files uploaded
                          </span>
                        ) : (
                          <span className="text-[#D9828B] flex items-center gap-1">
                            <AlertCircle className="size-3.5" /> {totalMandatoryDocs - uploadedMandatoryDocs} mandatory files missing
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Missing items warning if any */}
                  {session.missing_from_candidate && session.missing_from_candidate.length > 0 && (
                    <div className="p-3.5 rounded-xl border border-[#D9828B]/30 bg-[#462F35]/20 text-xs text-[#D9828B] space-y-1">
                      <div className="font-bold flex items-center gap-1.5">
                        <AlertCircle className="size-3.5" /> Pending Items from You:
                      </div>
                      <ul className="list-disc list-inside text-[11px] text-[#D9828B]/90 space-y-0.5">
                        {session.missing_from_candidate.map((item: string, idx: number) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="pt-4 border-t border-border flex items-center justify-between">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setActiveStep(2)}
                      className="text-xs font-semibold flex items-center gap-1.5"
                    >
                      <ArrowLeft className="size-3.5" />
                      <span>Back to Documents</span>
                    </Button>

                    <Button
                      type="button"
                      disabled={submittingIntake}
                      onClick={() => handleSubmitIntake()}
                      className="h-9 px-5 text-xs font-bold flex items-center gap-1.5 bg-[#64B99A] hover:bg-[#52a084] text-black"
                    >
                      {submittingIntake ? (
                        <>
                          <Loader2 className="size-3.5 animate-spin" />
                          <span>Submitting…</span>
                        </>
                      ) : (
                        <>
                          <Check className="size-3.5" />
                          <span>Submit Onboarding Package</span>
                        </>
                      )}
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground bg-card/40">
        <div className="max-w-4xl mx-auto px-4 flex items-center justify-between">
          <span>Powered by OctaOS Autonomous HR Engine</span>
          <span className="flex items-center gap-1 font-mono text-[11px]">
            <ShieldCheck className="size-3 text-[#64B99A]" /> 256-bit Encrypted
          </span>
        </div>
      </footer>
    </div>
  );
}

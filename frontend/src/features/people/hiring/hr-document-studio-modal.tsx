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
import {
  FileCheck,
  ShieldCheck,
  Printer,
  Copy,
  Send,
  Loader2,
  Lock,
  Sparkles,
  FileText,
  UserCheck,
} from 'lucide-react';
import { Candidate, DocumentPacket } from './hr-types';

interface HRDocumentStudioModalProps {
  candidate: Candidate | null;
  isOpen: boolean;
  onClose: () => void;
  contractTemplates: any[];
  offerVariables: Record<string, any>;
  setOfferVariables: React.Dispatch<React.SetStateAction<Record<string, any>>>;
  offerPreviewHtml: string;
  currentPacketData: DocumentPacket | null;
  isArtifactApproved: boolean;
  contractGenerating: boolean;
  approvalSubmitting: boolean;
  offerSending: boolean;
  onRegeneratePreview: () => void;
  onApproveArtifact: () => void;
  onSendOfferEmail: () => void;
  onDispatchAppointment: () => void;
  onExecuteContract: () => void;
}

export default function HRDocumentStudioModal({
  candidate,
  isOpen,
  onClose,
  contractTemplates,
  offerVariables,
  setOfferVariables,
  offerPreviewHtml,
  currentPacketData,
  isArtifactApproved,
  contractGenerating,
  approvalSubmitting,
  offerSending,
  onRegeneratePreview,
  onApproveArtifact,
  onSendOfferEmail,
  onDispatchAppointment,
  onExecuteContract,
}: HRDocumentStudioModalProps) {
  const [activeStudioTab, setActiveStudioTab] = useState<
    'offer_letter' | 'appointment_letter' | 'employment_contract' | 'audit'
  >('offer_letter');

  if (!candidate) return null;

  const currentArtifact = currentPacketData?.artifacts?.find(
    (a) => a.document_type === (activeStudioTab === 'audit' ? 'offer_letter' : activeStudioTab)
  );

  const activeDocumentHtml = currentArtifact?.html || (activeStudioTab === 'offer_letter' ? offerPreviewHtml : '');

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[95vw] sm:max-w-5xl max-w-5xl max-h-[92vh] bg-card border-border text-foreground p-0 overflow-hidden shadow-2xl rounded-2xl flex flex-col">
        {/* Header Ribbon */}
        <div className="px-6 py-4 pr-12 border-b border-border bg-muted/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold">
              <FileCheck size={18} />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-foreground">
                Governed HR Document Studio
              </DialogTitle>
              <p className="text-xs text-muted-foreground">
                Preparing legal offer &amp; onboarding packet for{' '}
                <strong className="text-foreground">{candidate.name || 'Candidate'}</strong>
              </p>
            </div>
          </div>

          {/* Document Sub-tabs */}
          <div className="flex items-center bg-muted/80 border border-border rounded-lg p-0.5 text-xs shrink-0 overflow-x-auto">
            <button
              onClick={() => setActiveStudioTab('offer_letter')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeStudioTab === 'offer_letter'
                  ? 'bg-card text-foreground shadow-2xs font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Offer Letter
            </button>
            <button
              onClick={() => setActiveStudioTab('appointment_letter')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeStudioTab === 'appointment_letter'
                  ? 'bg-card text-foreground shadow-2xs font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Appointment
            </button>
            <button
              onClick={() => setActiveStudioTab('employment_contract')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeStudioTab === 'employment_contract'
                  ? 'bg-card text-foreground shadow-2xs font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Contract
            </button>
            <button
              onClick={() => setActiveStudioTab('audit')}
              className={`px-3 py-1.5 rounded-md font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeStudioTab === 'audit'
                  ? 'bg-card text-foreground shadow-2xs font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              SHA-256 Audit
            </button>
          </div>
        </div>

        {/* Studio Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 overflow-hidden min-h-[480px]">
          {/* Left Column: Variable Configuration Form (5 cols) */}
          <div className="lg:col-span-5 p-5 border-r border-border overflow-y-auto space-y-3.5 bg-card/60">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Dynamic Variables
              </span>
              <Button
                size="sm"
                variant="ghost"
                disabled={contractGenerating}
                onClick={onRegeneratePreview}
                className="h-7 px-2 text-[11px] text-primary hover:text-primary hover:bg-primary/10"
              >
                {contractGenerating ? <Loader2 size={12} className="animate-spin mr-1" /> : <Sparkles size={12} className="mr-1" />}
                Re-generate
              </Button>
            </div>

            <div className="space-y-2.5 text-xs">
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground">Candidate Full Name</label>
                <Input
                  value={offerVariables.candidate_name || ''}
                  onChange={(e) => setOfferVariables((prev) => ({ ...prev, candidate_name: e.target.value }))}
                  className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-semibold text-muted-foreground">Job Title</label>
                  <Input
                    value={offerVariables.job_title || ''}
                    onChange={(e) => setOfferVariables((prev) => ({ ...prev, job_title: e.target.value }))}
                    className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-muted-foreground">Department</label>
                  <Input
                    value={offerVariables.department || 'Engineering'}
                    onChange={(e) => setOfferVariables((prev) => ({ ...prev, department: e.target.value }))}
                    className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-semibold text-muted-foreground">Start Date</label>
                  <Input
                    value={offerVariables.start_date || ''}
                    onChange={(e) => setOfferVariables((prev) => ({ ...prev, start_date: e.target.value }))}
                    className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-muted-foreground">Salary (Annual)</label>
                  <Input
                    value={offerVariables.salary_amount || '130,000'}
                    onChange={(e) => setOfferVariables((prev) => ({ ...prev, salary_amount: e.target.value }))}
                    className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] font-semibold text-muted-foreground">Work Location / Mode</label>
                  <Input
                    value={offerVariables.work_mode || 'Remote (Global)'}
                    onChange={(e) => setOfferVariables((prev) => ({ ...prev, work_mode: e.target.value }))}
                    className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-muted-foreground">Signatory Name</label>
                  <Input
                    value={offerVariables.signatory_name || 'Alex Vance'}
                    onChange={(e) => setOfferVariables((prev) => ({ ...prev, signatory_name: e.target.value }))}
                    className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-muted-foreground">Company Name</label>
                <Input
                  value={offerVariables.company_name || 'OctaOS Technologies Inc.'}
                  onChange={(e) => setOfferVariables((prev) => ({ ...prev, company_name: e.target.value }))}
                  className="bg-surface-hover/60 border-border text-foreground text-xs h-8 rounded-lg mt-0.5"
                />
              </div>
            </div>
          </div>

          {/* Right Column: Live Document Preview (7 cols) */}
          <div className="lg:col-span-7 p-5 bg-card/40 flex flex-col justify-between overflow-hidden">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <FileText size={13} className="text-primary" /> Live Document Preview
              </span>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => window.print()}
                  className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  <Printer size={12} className="mr-1" /> Print
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    navigator.clipboard.writeText(activeDocumentHtml || offerPreviewHtml);
                  }}
                  className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  <Copy size={12} className="mr-1" /> Copy HTML
                </Button>
              </div>
            </div>

            {/* Document Render Area */}
            <div className="flex-1 my-3 overflow-y-auto bg-background/90 border border-border rounded-xl p-6 shadow-inner text-foreground">
              {contractGenerating ? (
                <div className="h-64 flex flex-col items-center justify-center space-y-2 text-muted-foreground">
                  <Loader2 size={24} className="animate-spin text-primary" />
                  <span className="text-xs">Generating packet preview...</span>
                </div>
              ) : activeStudioTab === 'audit' ? (
                <div className="space-y-4 text-xs font-mono">
                  <div className="p-3 rounded-lg bg-surface-hover/50 border border-border space-y-1">
                    <div className="text-[11px] text-muted-foreground font-sans font-bold uppercase">
                      Document Packet ID
                    </div>
                    <div className="text-primary truncate">{currentPacketData?.packet_id || 'pkt-preview-01'}</div>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-hover/50 border border-border space-y-1">
                    <div className="text-[11px] text-muted-foreground font-sans font-bold uppercase">
                      Cryptographic SHA-256 Seal
                    </div>
                    <div className="text-[#64B99A] break-all">
                      {currentArtifact?.artifact_sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-hover/50 border border-border space-y-1">
                    <div className="text-[11px] text-muted-foreground font-sans font-bold uppercase">
                      Status &amp; Verification
                    </div>
                    <div className="text-foreground">
                      {isArtifactApproved ? 'Cryptographically Sealed & Verified' : 'Draft / Awaiting Authorization'}
                    </div>
                  </div>
                </div>
              ) : activeDocumentHtml ? (
                <div
                  className="prose prose-invert prose-xs max-w-none text-xs leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: activeDocumentHtml }}
                />
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-muted-foreground text-xs space-y-2">
                  <FileText size={28} className="text-muted-foreground/60" />
                  <span>Click &quot;Re-generate&quot; to compile preview.</span>
                </div>
              )}
            </div>

            {/* Cryptographic Seal Status Badge */}
            <div className="pt-2 border-t border-border flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <ShieldCheck
                  size={15}
                  className={isArtifactApproved ? 'text-[#64B99A]' : 'text-[#D9AD68]'}
                />
                <span className="text-muted-foreground text-[11px]">
                  {isArtifactApproved
                    ? 'Cryptographically authorized & bound to hash'
                    : 'Artifact draft awaiting approval'}
                </span>
              </div>

              {!isArtifactApproved && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={approvalSubmitting}
                  onClick={onApproveArtifact}
                  className="h-7 text-xs font-semibold flex items-center gap-1.5"
                >
                  {approvalSubmitting ? <Loader2 size={12} className="animate-spin" /> : <Lock size={12} />}
                  <span>Sign &amp; Seal Artifact</span>
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Modal Bottom Dispatch Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
          <Button
            size="sm"
            variant="ghost"
            onClick={onClose}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Cancel
          </Button>

          <div className="flex items-center gap-2 flex-wrap">
            <Button
              size="sm"
              variant="outline"
              onClick={onDispatchAppointment}
              className="h-8.5 text-xs font-semibold flex items-center gap-1.5"
            >
              <UserCheck size={13} />
              <span>Dispatch Appointment</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={onExecuteContract}
              className="h-8.5 text-xs font-semibold flex items-center gap-1.5"
            >
              <ShieldCheck size={13} className="text-[#64B99A]" />
              <span>Execute Contract</span>
            </Button>

            <Button
              size="sm"
              disabled={offerSending}
              onClick={onSendOfferEmail}
              className="h-8.5 text-xs font-bold flex items-center gap-1.5 shadow-xs"
            >
              {offerSending ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Dispatching...</span>
                </>
              ) : (
                <>
                  <Send size={13} />
                  <span>Dispatch Offer Letter Link</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

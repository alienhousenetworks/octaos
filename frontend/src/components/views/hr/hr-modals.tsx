'use client';

import React, { useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  UserPlus,
  FileSpreadsheet,
  Calendar,
  Edit2,
  Loader2,
  Upload,
  Save,
} from 'lucide-react';
import { Candidate, STAGES } from './hr-types';

/* ── 1. MANUAL ADD CANDIDATE MODAL ── */
interface ManualAddModalProps {
  isOpen: boolean;
  onClose: () => void;
  name: string;
  setName: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  role: string;
  setRole: (v: string) => void;
  phone: string;
  setPhone: (v: string) => void;
  skills: string;
  setSkills: (v: string) => void;
  experience: string;
  setExperience: (v: string) => void;
  budget: string;
  setBudget: (v: string) => void;
  extra: string;
  setExtra: (v: string) => void;
  onAdd: () => void;
  adding: boolean;
}

export function ManualAddCandidateModal({
  isOpen,
  onClose,
  name,
  setName,
  email,
  setEmail,
  role,
  setRole,
  phone,
  setPhone,
  skills,
  setSkills,
  experience,
  setExperience,
  budget,
  setBudget,
  extra,
  setExtra,
  onAdd,
  adding,
}: ManualAddModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border text-foreground shadow-2xl rounded-2xl p-6">
        <DialogHeader className="pb-3 border-b border-border">
          <DialogTitle className="text-base font-bold flex items-center gap-2">
            <UserPlus size={18} className="text-primary" />
            <span>Add Candidate Manually</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3.5 pt-3 text-xs">
          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Full Name *</label>
              <Input
                placeholder="Jane Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Email Address *</label>
              <Input
                placeholder="jane@example.com"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Role / Position *</label>
              <Input
                placeholder="Senior Backend Engineer"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Phone Number</label>
              <Input
                placeholder="+1 (555) 019-2834"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">Skills (comma-separated)</label>
            <Input
              placeholder="Python, FastAPI, Docker, PostgreSQL"
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Experience (Years)</label>
              <Input
                placeholder="5"
                value={experience}
                onChange={(e) => setExperience(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Expected Compensation</label>
              <Input
                placeholder="$130,000/yr"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button size="sm" variant="ghost" onClick={onClose} className="h-8 text-xs text-muted-foreground hover:text-foreground">
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={adding || !name || !email || !role}
              onClick={onAdd}
              className="h-8 text-xs font-bold"
            >
              {adding ? <Loader2 size={13} className="animate-spin mr-1.5" /> : null}
              Save Candidate
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ── 2. EDIT CANDIDATE PROFILE MODAL ── */
interface EditCandidateModalProps {
  candidate: Candidate | null;
  isOpen: boolean;
  onClose: () => void;
  name: string;
  setName: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  role: string;
  setRole: (v: string) => void;
  status: string;
  setStatus: (v: string) => void;
  phone: string;
  setPhone: (v: string) => void;
  address: string;
  setAddress: (v: string) => void;
  skills: string;
  setSkills: (v: string) => void;
  projects: string;
  setProjects: (v: string) => void;
  experienceYears: string;
  setExperienceYears: (v: string) => void;
  experienceSummary: string;
  setExperienceSummary: (v: string) => void;
  resumeLink: string;
  setResumeLink: (v: string) => void;
  extraRemarks: string;
  setExtraRemarks: (v: string) => void;
  onSave: () => void;
  saving: boolean;
}

export function EditCandidateModal({
  candidate,
  isOpen,
  onClose,
  name,
  setName,
  email,
  setEmail,
  role,
  setRole,
  status,
  setStatus,
  phone,
  setPhone,
  address,
  setAddress,
  skills,
  setSkills,
  projects,
  setProjects,
  experienceYears,
  setExperienceYears,
  experienceSummary,
  setExperienceSummary,
  resumeLink,
  setResumeLink,
  extraRemarks,
  setExtraRemarks,
  onSave,
  saving,
}: EditCandidateModalProps) {
  if (!candidate) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl bg-card border-border text-foreground shadow-2xl rounded-2xl p-6 max-h-[85vh] overflow-y-auto">
        <DialogHeader className="pb-3 border-b border-border">
          <DialogTitle className="text-base font-bold flex items-center gap-2">
            <Edit2 size={18} className="text-primary" />
            <span>Edit Candidate Profile</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 pt-3 text-xs">
          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Full Name</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Email</label>
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Role</label>
              <Input
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Pipeline Stage</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full bg-surface-hover/60 border border-border text-foreground rounded-lg px-2.5 h-8.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {STAGES.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Phone</label>
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Location</label>
              <Input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">Skills (comma-separated)</label>
            <Input
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
              className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">Experience Highlights</label>
            <Textarea
              value={experienceSummary}
              onChange={(e) => setExperienceSummary(e.target.value)}
              className="bg-surface-hover/60 border-border text-foreground text-xs rounded-lg min-h-[60px] resize-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button size="sm" variant="ghost" onClick={onClose} className="h-8 text-xs text-muted-foreground hover:text-foreground">
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={saving}
              onClick={onSave}
              className="h-8 text-xs font-bold flex items-center gap-1.5"
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              Save Changes
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ── 3. IMPORT EXCEL / CSV SPREADSHEET MODAL ── */
interface ImportExcelModalProps {
  isOpen: boolean;
  onClose: () => void;
  importFile: File | null;
  setImportFile: (file: File | null) => void;
  onImport: () => void;
  importing: boolean;
}

export function ImportExcelModal({
  isOpen,
  onClose,
  importFile,
  setImportFile,
  onImport,
  importing,
}: ImportExcelModalProps) {
  const excelInputRef = useRef<HTMLInputElement>(null);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border text-foreground shadow-2xl rounded-2xl p-6">
        <DialogHeader className="pb-3 border-b border-border">
          <DialogTitle className="text-base font-bold flex items-center gap-2">
            <FileSpreadsheet size={18} className="text-[#64B99A]" />
            <span>Import Candidates (.xlsx / .csv)</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-3 text-xs">
          <p className="text-muted-foreground leading-relaxed">
            Upload an existing spreadsheet containing candidate details (Name, Phone, Email, Address, Skills, Experience, Projects). Columns are automatically mapped into the ATS.
          </p>

          <div
            onClick={() => excelInputRef.current?.click()}
            className="border-2 border-dashed border-border hover:border-[#64B99A]/60 rounded-xl p-6 text-center cursor-pointer transition-colors bg-surface-hover/30 hover:bg-surface-hover/50 space-y-1.5"
          >
            <FileSpreadsheet size={28} className="text-[#64B99A] mx-auto" />
            <p className="font-semibold text-foreground">
              {importFile ? importFile.name : 'Select or drop .xlsx or .csv file'}
            </p>
            <p className="text-[11px] text-muted-foreground">Standard Excel and CSV spreadsheets supported</p>
            <input
              ref={excelInputRef}
              type="file"
              accept=".xlsx,.csv"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setImportFile(e.target.files[0]);
                }
              }}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button size="sm" variant="ghost" onClick={onClose} className="h-8 text-xs text-muted-foreground hover:text-foreground">
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!importFile || importing}
              onClick={onImport}
              className="h-8 text-xs font-bold"
            >
              {importing ? <Loader2 size={13} className="animate-spin mr-1.5" /> : null}
              Import Spreadsheet
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ── 4. SCHEDULE INTERVIEW MODAL ── */
interface ScheduleInterviewModalProps {
  candidate: Candidate | null;
  isOpen: boolean;
  onClose: () => void;
  interviewDate: string;
  setInterviewDate: (v: string) => void;
  interviewTime: string;
  setInterviewTime: (v: string) => void;
  interviewRound: string;
  setInterviewRound: (v: string) => void;
  meetingLink: string;
  setMeetingLink: (v: string) => void;
  interviewerName: string;
  setInterviewerName: (v: string) => void;
  interviewNotes: string;
  setInterviewNotes: (v: string) => void;
  onSendEmail: () => void;
  sending: boolean;
}

export function ScheduleInterviewModal({
  candidate,
  isOpen,
  onClose,
  interviewDate,
  setInterviewDate,
  interviewTime,
  setInterviewTime,
  interviewRound,
  setInterviewRound,
  meetingLink,
  setMeetingLink,
  interviewerName,
  setInterviewerName,
  interviewNotes,
  setInterviewNotes,
  onSendEmail,
  sending,
}: ScheduleInterviewModalProps) {
  if (!candidate) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border-border text-foreground shadow-2xl rounded-2xl p-6">
        <DialogHeader className="pb-3 border-b border-border">
          <DialogTitle className="text-base font-bold flex items-center gap-2">
            <Calendar size={18} className="text-primary" />
            <span>Schedule Interview Round</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 pt-3 text-xs">
          <div className="p-2.5 bg-surface-hover/50 rounded-lg border border-border">
            <span className="text-[11px] text-muted-foreground font-semibold">Candidate:</span>
            <div className="font-bold text-foreground">{candidate.name || 'Candidate'}</div>
            <div className="text-[11px] text-muted-foreground">{candidate.email}</div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">Round Title</label>
            <Input
              value={interviewRound}
              onChange={(e) => setInterviewRound(e.target.value)}
              placeholder="e.g. Round 1: Technical Architecture"
              className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Date</label>
              <Input
                type="date"
                value={interviewDate}
                onChange={(e) => setInterviewDate(e.target.value)}
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-muted-foreground">Time (UTC)</label>
              <Input
                value={interviewTime}
                onChange={(e) => setInterviewTime(e.target.value)}
                placeholder="11:00 AM"
                className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">Meeting Link</label>
            <Input
              value={meetingLink}
              onChange={(e) => setMeetingLink(e.target.value)}
              placeholder="https://meet.google.com/..."
              className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">Interviewer Name</label>
            <Input
              value={interviewerName}
              onChange={(e) => setInterviewerName(e.target.value)}
              placeholder="Engineering Hiring Lead"
              className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-muted-foreground">Notes for Candidate</label>
            <Textarea
              value={interviewNotes}
              onChange={(e) => setInterviewNotes(e.target.value)}
              placeholder="Preparation instructions, links to portfolio..."
              className="bg-surface-hover/60 border-border text-foreground text-xs rounded-lg min-h-[50px] resize-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button size="sm" variant="ghost" onClick={onClose} className="h-8 text-xs text-muted-foreground hover:text-foreground">
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={sending || !interviewDate}
              onClick={onSendEmail}
              className="h-8 text-xs font-bold"
            >
              {sending ? <Loader2 size={13} className="animate-spin mr-1.5" /> : null}
              Send Invitation Email
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

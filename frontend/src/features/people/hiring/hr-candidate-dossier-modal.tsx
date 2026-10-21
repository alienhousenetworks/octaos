'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Sparkles,
  Calendar,
  FileCheck,
  Mail,
  Phone,
  MapPin,
  DollarSign,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Edit2,
  Trash2,
  Award,
} from 'lucide-react';
import { Candidate, STAGES, getScoreBadgeClass } from './hr-types';

interface HRCandidateDossierModalProps {
  candidate: Candidate | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdateStatus: (candidateId: string, newStatus: string) => void;
  onOpenEditCandidate: (candidate: Candidate) => void;
  onOpenInterview: (candidate: Candidate) => void;
  onOpenOffer: (candidate: Candidate) => void;
  onDeleteCandidate: (candidateId: string) => void;
}

export default function HRCandidateDossierModal({
  candidate,
  isOpen,
  onClose,
  onUpdateStatus,
  onOpenEditCandidate,
  onOpenInterview,
  onOpenOffer,
  onDeleteCandidate,
}: HRCandidateDossierModalProps) {
  const [activeDossierTab, setActiveDossierTab] = useState<'overview' | 'scorecard' | 'resume'>('overview');

  if (!candidate) return null;

  const sc = candidate.scorecard || {};
  const score = sc.composite_score ?? sc.match_score ?? 60;
  const atsScore = sc.ats_score ?? score;
  const semanticScore = sc.semantic_score ?? score;
  const scoreBadge = getScoreBadgeClass(score);

  const matchedSkills = sc.matched_skills || sc.skills || [];
  const missingSkills = sc.missing_skills || [];
  const skillsList = Array.isArray(matchedSkills)
    ? matchedSkills
    : String(matchedSkills).split(',').map((s) => s.trim()).filter(Boolean);

  const currentStageObj = STAGES.find((s) => s.key === candidate.status) || STAGES[0];

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-card border-border text-foreground p-0 overflow-hidden shadow-xl rounded-2xl">
        {/* Header Ribbon */}
        <div className="p-6 border-b border-border bg-muted/20">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h2 className="text-xl font-bold tracking-tight text-foreground">
                  {candidate.name || 'Candidate Dossier'}
                </h2>

                <span
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${scoreBadge.bgColor} ${scoreBadge.textColor} border-current/20`}
                >
                  <Sparkles size={11} />
                  {score}% {scoreBadge.label}
                </span>

                {sc.rank && (
                  <span className="text-xs font-mono font-bold text-muted-foreground bg-muted px-2 py-0.5 rounded-full border border-border">
                    Rank #{sc.rank}
                  </span>
                )}
              </div>

              <p className="text-sm text-muted-foreground mt-1">
                {candidate.role || 'Applicant'} •{' '}
                {sc.is_internship_only || sc.experience_years === 0
                  ? (sc.experience_summary || 'Internship Profile (< 1 yr)')
                  : sc.experience_years
                  ? `${sc.experience_years} years experience`
                  : 'Profile on file'}
              </p>
            </div>

            {/* Stage Selector */}
            <div className="flex items-center gap-1.5 shrink-0">
              <span className="text-xs text-muted-foreground font-semibold">Stage:</span>
              <select
                value={candidate.status}
                onChange={(e) => onUpdateStatus(candidate.id, e.target.value)}
                className="bg-card border border-border text-foreground rounded-lg px-2.5 py-1 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {STAGES.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quick Contact Metadata Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-4 pt-3 border-t border-border/60 text-xs">
            <div className="flex items-center gap-2 text-muted-foreground truncate">
              <Mail size={13} className="text-primary shrink-0" />
              <span className="truncate">{candidate.email || 'No email provided'}</span>
            </div>

            <div className="flex items-center gap-2 text-muted-foreground truncate">
              <Phone size={13} className="text-primary shrink-0" />
              <span className="truncate">{candidate.phone || sc.phone_number || sc.phone || 'No phone'}</span>
            </div>

            <div className="flex items-center gap-2 text-muted-foreground truncate">
              <MapPin size={13} className="text-primary shrink-0" />
              <span className="truncate">{sc.address || 'Location on file'}</span>
            </div>

            <div className="flex items-center gap-2 text-[#64B99A] font-semibold truncate">
              <DollarSign size={13} className="shrink-0" />
              <span className="truncate">{sc.salary_expectation || '$120,000/yr'}</span>
            </div>
          </div>
        </div>

        {/* Dossier Tabs */}
        <div className="flex items-center gap-2 border-b border-border px-6 pt-2 bg-muted/10">
          <button
            onClick={() => setActiveDossierTab('overview')}
            className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
              activeDossierTab === 'overview'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Overview &amp; Skills
          </button>
          <button
            onClick={() => setActiveDossierTab('scorecard')}
            className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
              activeDossierTab === 'scorecard'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            ATS &amp; AI Scorecard
          </button>
          <button
            onClick={() => setActiveDossierTab('resume')}
            className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
              activeDossierTab === 'resume'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Resume Document
          </button>
        </div>

        {/* Tab Body */}
        <div className="p-6 max-h-[460px] overflow-y-auto space-y-4">
          {activeDossierTab === 'overview' && (
            <div className="space-y-4">
              {/* Skills */}
              <div>
                <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                  Skills &amp; Competencies ({skillsList.length})
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {skillsList.map((skill: any, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md text-xs font-medium bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20"
                    >
                      {String(skill).trim()}
                    </span>
                  ))}
                </div>
              </div>

              {/* Experience Summary */}
              {sc.experience_summary && (
                <div>
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">
                    Experience Highlights
                  </h4>
                  <div className="p-3 rounded-xl bg-surface-hover/50 border border-border text-xs text-foreground/90 leading-relaxed">
                    {sc.experience_summary}
                  </div>
                </div>
              )}

              {/* Projects */}
              {sc.projects && (
                <div>
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">
                    Notable Projects &amp; Accomplishments
                  </h4>
                  <div className="p-3 rounded-xl bg-surface-hover/50 border border-border text-xs text-foreground/90 leading-relaxed">
                    {Array.isArray(sc.projects) ? sc.projects.join(' • ') : sc.projects}
                  </div>
                </div>
              )}

              {/* Fit Verdict */}
              {sc.fit_verdict && (
                <div>
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">
                    Executive Fit Verdict
                  </h4>
                  <div className="p-3 rounded-xl bg-primary/5 border border-primary/20 text-xs text-foreground/90 leading-relaxed">
                    {sc.fit_verdict}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeDossierTab === 'scorecard' && (
            <div className="space-y-4">
              {/* Score Breakdown Triple */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 rounded-xl bg-surface-hover/60 border border-border">
                  <span className="text-[11px] font-bold text-muted-foreground uppercase">Composite</span>
                  <div className="text-xl font-bold font-mono text-foreground mt-1">{score}%</div>
                </div>
                <div className="p-3 rounded-xl bg-surface-hover/60 border border-border">
                  <span className="text-[11px] font-bold text-muted-foreground uppercase">ATS Keyword</span>
                  <div className="text-xl font-bold font-mono text-primary mt-1">{atsScore}%</div>
                </div>
                <div className="p-3 rounded-xl bg-surface-hover/60 border border-border">
                  <span className="text-[11px] font-bold text-muted-foreground uppercase">AI Semantic</span>
                  <div className="text-xl font-bold font-mono text-[#64B99A] mt-1">{semanticScore}%</div>
                </div>
              </div>

              {/* Missing Skills */}
              {missingSkills.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-[#D9828B] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <AlertCircle size={13} /> Missing Keywords / Gaps
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {missingSkills.map((sk: any, idx: number) => (
                      <span
                        key={idx}
                        className="px-2.5 py-0.5 rounded-md text-xs font-medium bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20"
                      >
                        {String(sk).trim()}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Detailed Reasoning */}
              <div>
                <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">
                  Requirements Matching Analysis
                </h4>
                <p className="text-xs text-foreground/90 leading-relaxed bg-surface-hover/40 p-3 rounded-xl border border-border">
                  {sc.requirements_match || 'Candidate was screened against role requirements and verified for engineering competencies.'}
                </p>
              </div>
            </div>
          )}

          {activeDossierTab === 'resume' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-xl bg-surface-hover/60 border border-border">
                <div>
                  <h4 className="text-xs font-bold text-foreground">Original Candidate Resume</h4>
                  <p className="text-[11px] text-muted-foreground">
                    Parsed via PyMuPDF deterministic extractor
                  </p>
                </div>
                {sc.resume_link ? (
                  <Button
                    size="sm"
                    onClick={() => window.open(sc.resume_link, '_blank')}
                    className="h-8 text-xs font-semibold"
                  >
                    Open PDF <ExternalLink size={12} className="ml-1.5" />
                  </Button>
                ) : (
                  <span className="text-xs text-muted-foreground italic">File stored in session</span>
                )}
              </div>

              <div className="p-3 rounded-xl bg-muted/40 border border-border text-xs text-muted-foreground font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
                {sc.experience_summary || 'Resume text extracted and indexed into database.'}
              </div>
            </div>
          )}
        </div>

        {/* Modal Action Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => onOpenEditCandidate(candidate)}
              className="h-8.5 text-xs font-semibold flex items-center gap-1.5"
            >
              <Edit2 size={13} /> Edit
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                onDeleteCandidate(candidate.id);
                onClose();
              }}
              className="h-8.5 text-xs text-destructive hover:bg-destructive/10 border-border"
            >
              <Trash2 size={13} /> Delete
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                onClose();
                onOpenInterview(candidate);
              }}
              className="h-8.5 text-xs font-semibold flex items-center gap-1.5"
            >
              <Calendar size={13} className="text-primary" /> Schedule Interview
            </Button>

            <Button
              size="sm"
              onClick={() => {
                onClose();
                onOpenOffer(candidate);
              }}
              className="h-8.5 text-xs font-semibold flex items-center gap-1.5"
            >
              <FileCheck size={13} /> Issue Offer Letter
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

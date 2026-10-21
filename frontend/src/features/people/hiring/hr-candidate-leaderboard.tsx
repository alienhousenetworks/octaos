'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Award,
  Sparkles,
  Calendar,
  FileCheck,
  ChevronDown,
  ChevronUp,
  Mail,
  Phone,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  Eye,
  Trash2,
  FileText,
  DollarSign,
  MapPin,
} from 'lucide-react';
import { Candidate, getScoreBadgeClass, STAGES } from './hr-types';

interface HRCandidateLeaderboardProps {
  candidates: Candidate[];
  onSelectCandidate: (candidate: Candidate) => void;
  onOpenInterview: (candidate: Candidate) => void;
  onOpenOffer: (candidate: Candidate) => void;
  onDeleteCandidate: (candidateId: string) => void;
  onUpdateStatus: (candidateId: string, newStatus: string) => void;
}

export default function HRCandidateLeaderboard({
  candidates,
  onSelectCandidate,
  onOpenInterview,
  onOpenOffer,
  onDeleteCandidate,
  onUpdateStatus,
}: HRCandidateLeaderboardProps) {
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  if (candidates.length === 0) {
    return (
      <Card className="bg-card border-dashed border-border p-12 text-center rounded-xl min-h-[300px] flex flex-col items-center justify-center space-y-2">
        <Award size={36} className="text-muted-foreground/60" />
        <h3 className="text-sm font-bold text-foreground">No Ranked Candidates Found</h3>
        <p className="text-xs text-muted-foreground max-w-sm">
          No candidates match the selected filters. Clear your search or upload resumes to run ATS scoring.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {candidates.map((c, index) => {
        const sc = c.scorecard || {};
        const rank = sc.rank || index + 1;
        const compositeScore = sc.composite_score ?? sc.match_score ?? 60;
        const atsScore = sc.ats_score ?? compositeScore;
        const semanticScore = sc.semantic_score ?? compositeScore;
        const scoreBadge = getScoreBadgeClass(compositeScore);
        const isExpanded = !!expandedIds[c.id];

        const matchedSkills = sc.matched_skills || sc.skills || [];
        const missingSkills = sc.missing_skills || [];
        const currentStageObj = STAGES.find((s) => s.key === c.status) || STAGES[0];

        return (
          <Card
            key={c.id}
            className="bg-card border-border hover:border-primary/40 transition-all duration-150 p-4 shadow-2xs group"
          >
            {/* Top Row: Rank, Identity, Scores, Primary Action */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              {/* Left Identity & Rank */}
              <div className="flex items-start gap-3.5 min-w-0">
                {/* Rank Badge */}
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 border ${
                    rank === 1
                      ? 'bg-[#D9AD68]/15 text-[#D9AD68] border-[#D9AD68]/30 shadow-xs'
                      : rank === 2
                      ? 'bg-muted text-foreground border-border'
                      : rank === 3
                      ? 'bg-primary/10 text-primary border-primary/20'
                      : 'bg-muted/50 text-muted-foreground border-border/60'
                  }`}
                >
                  #{rank}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3
                      className="text-sm font-bold text-foreground hover:text-primary transition-colors cursor-pointer"
                      onClick={() => onSelectCandidate(c)}
                    >
                      {c.name || 'Unnamed Candidate'}
                    </h3>

                    {/* Stage Badge */}
                    <span
                      className={`inline-flex items-center px-2 py-0.2 rounded-full text-[10px] font-semibold border ${currentStageObj.color}`}
                    >
                      {currentStageObj.label}
                    </span>

                    {/* Match Tier Badge */}
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.2 rounded-full text-[10px] font-semibold border ${scoreBadge.bgColor} ${scoreBadge.textColor} border-current/20`}
                    >
                      <Sparkles size={10} /> {scoreBadge.label}
                    </span>
                  </div>

                  <p className="text-xs text-muted-foreground mt-0.5 truncate">
                    {c.role || 'Applicant'} • {sc.experience_years ? `${sc.experience_years} years experience` : 'Experience extracted from resume'}
                  </p>

                  <div className="flex items-center gap-3 text-[11px] text-muted-foreground mt-1.5 flex-wrap">
                    {c.email && (
                      <span className="flex items-center gap-1">
                        <Mail size={12} className="text-muted-foreground/80" /> {c.email}
                      </span>
                    )}
                    {sc.phone_number && (
                      <span className="flex items-center gap-1">
                        <Phone size={12} className="text-muted-foreground/80" /> {sc.phone_number}
                      </span>
                    )}
                    {sc.salary_expectation && (
                      <span className="flex items-center gap-1 text-[#64B99A] font-semibold">
                        <DollarSign size={12} /> {sc.salary_expectation}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Middle: Dual-Engine Score Ribbon */}
              <div className="flex items-center gap-3 shrink-0 py-1 px-3 rounded-xl bg-surface-hover/60 border border-border">
                {/* Composite Overall */}
                <div className="text-center px-2">
                  <div className="text-[10px] uppercase font-bold text-muted-foreground">Match Fit</div>
                  <div className="text-lg font-bold text-foreground font-mono">{compositeScore}%</div>
                </div>

                <div className="w-px h-7 bg-border" />

                {/* ATS Deterministic */}
                <div className="text-center px-2">
                  <div className="text-[10px] uppercase font-bold text-muted-foreground">ATS Keywords</div>
                  <div className="text-sm font-semibold text-primary font-mono">{atsScore}%</div>
                </div>

                <div className="w-px h-7 bg-border" />

                {/* AI Semantic */}
                <div className="text-center px-2">
                  <div className="text-[10px] uppercase font-bold text-muted-foreground">AI Semantic</div>
                  <div className="text-sm font-semibold text-[#64B99A] font-mono">{semanticScore}%</div>
                </div>
              </div>

              {/* Right: Quick Action Buttons */}
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onOpenInterview(c)}
                  className="h-8 text-xs font-semibold flex items-center gap-1.5"
                >
                  <Calendar size={13} className="text-primary" />
                  <span>Interview</span>
                </Button>

                <Button
                  size="sm"
                  onClick={() => onOpenOffer(c)}
                  className="h-8 text-xs font-semibold flex items-center gap-1.5"
                >
                  <FileCheck size={13} />
                  <span>Offer Letter</span>
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onSelectCandidate(c)}
                  className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                  title="View Candidate Dossier"
                >
                  <Eye size={14} />
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => toggleExpand(c.id)}
                  className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                  title="Toggle details"
                >
                  {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </Button>
              </div>
            </div>

            {/* Collapsible Evaluation Details */}
            {isExpanded && (
              <div className="mt-3 pt-3 border-t border-border grid grid-cols-1 md:grid-cols-2 gap-4 text-xs animate-in fade-in duration-150">
                {/* Skills Breakdown */}
                <div className="space-y-2">
                  <div>
                    <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                      <CheckCircle2 size={13} className="text-[#64B99A]" /> Matched Requirements &amp; Skills
                    </span>
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {Array.isArray(matchedSkills) && matchedSkills.length > 0 ? (
                        matchedSkills.map((sk: any, i: number) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20"
                          >
                            {String(sk).trim()}
                          </span>
                        ))
                      ) : (
                        <span className="text-muted-foreground text-xs italic">Skills extracted in profile</span>
                      )}
                    </div>
                  </div>

                  {Array.isArray(missingSkills) && missingSkills.length > 0 && (
                    <div className="pt-1">
                      <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                        <AlertCircle size={13} className="text-[#D9828B]" /> Missing Keywords
                      </span>
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {missingSkills.map((sk: any, i: number) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20"
                          >
                            {String(sk).trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* AI Justification & Experience Summary */}
                <div className="space-y-2">
                  <div>
                    <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                      Executive Fit Justification
                    </span>
                    <p className="text-xs text-foreground/90 mt-1 leading-relaxed bg-surface-hover/40 p-2.5 rounded-lg border border-border">
                      {sc.fit_verdict || sc.requirements_match || sc.recommendation || 'Candidate demonstrates relevant competencies aligned with target criteria.'}
                    </p>
                  </div>

                  {sc.experience_summary && (
                    <div>
                      <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                        Experience Highlights
                      </span>
                      <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                        {sc.experience_summary}
                      </p>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-muted-foreground">
                      Status: <strong className="text-foreground capitalize">{c.status}</strong>
                    </span>

                    <button
                      onClick={() => onDeleteCandidate(c.id)}
                      className="text-[11px] text-destructive hover:underline flex items-center gap-1"
                    >
                      <Trash2 size={12} /> Remove Candidate
                    </button>
                  </div>
                </div>
              </div>
            )}
          </Card>
        );
      })}
    </div>
  );
}

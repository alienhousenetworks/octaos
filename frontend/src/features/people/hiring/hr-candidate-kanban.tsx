'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Calendar,
  FileCheck,
  MoreHorizontal,
  ChevronRight,
  ArrowRight,
  Sparkles,
  MapPin,
  Mail,
  Phone,
  Eye,
  Trash2,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Candidate, STAGES, getScoreBadgeClass } from './hr-types';

interface HRCandidateKanbanProps {
  candidates: Candidate[];
  onSelectCandidate: (candidate: Candidate) => void;
  onUpdateStatus: (candidateId: string, newStatus: string) => void;
  onOpenInterview: (candidate: Candidate) => void;
  onOpenOffer: (candidate: Candidate) => void;
  onDeleteCandidate: (candidateId: string) => void;
}

export default function HRCandidateKanban({
  candidates,
  onSelectCandidate,
  onUpdateStatus,
  onOpenInterview,
  onOpenOffer,
  onDeleteCandidate,
}: HRCandidateKanbanProps) {
  const getNextStage = (currentStage: string): string | null => {
    const stageKeys = STAGES.map((s) => s.key);
    const currentIndex = stageKeys.indexOf(currentStage as any);
    if (currentIndex >= 0 && currentIndex < stageKeys.length - 2) {
      // Don't auto-advance to rejected
      return stageKeys[currentIndex + 1];
    }
    return null;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 min-h-[580px] overflow-x-auto pb-4">
      {STAGES.map((stage) => {
        const stageCandidates = candidates.filter((c) => (c.status || 'sourced') === stage.key);
        const nextStageKey = getNextStage(stage.key);
        const nextStageObj = STAGES.find((s) => s.key === nextStageKey);

        return (
          <div
            key={stage.key}
            className="flex flex-col bg-card/60 border border-border rounded-xl p-3 shadow-2xs min-w-[240px]"
          >
            {/* Column Header */}
            <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-border">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${stage.color.split(' ')[2] || 'text-primary'}`} />
                <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                  {stage.label}
                </h3>
              </div>
              <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                {stageCandidates.length}
              </span>
            </div>

            {/* Candidate Card Stream */}
            <div className="space-y-2.5 flex-1 overflow-y-auto max-h-[700px] pr-0.5">
              {stageCandidates.length === 0 ? (
                <div className="h-32 flex flex-col items-center justify-center border border-dashed border-border/60 rounded-lg text-center p-3 text-muted-foreground/60">
                  <p className="text-[11px]">No candidates</p>
                </div>
              ) : (
                stageCandidates.map((c) => {
                  const score = c.scorecard?.composite_score ?? c.scorecard?.match_score ?? 60;
                  const scoreBadge = getScoreBadgeClass(score);
                  const skills = c.scorecard?.skills || c.scorecard?.matched_skills || [];
                  const displayedSkills = Array.isArray(skills)
                    ? skills.slice(0, 3)
                    : String(skills).split(',').slice(0, 3);

                  return (
                    <Card
                      key={c.id}
                      className="bg-card hover:bg-surface-hover/80 border-border transition-all duration-150 p-3 shadow-2xs hover:shadow-xs group cursor-pointer"
                      onClick={() => onSelectCandidate(c)}
                    >
                      <div className="space-y-2">
                        {/* Top: Name & Quick Dropdown */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <h4 className="text-xs font-bold text-foreground truncate group-hover:text-primary transition-colors">
                              {c.name || 'Unnamed Candidate'}
                            </h4>
                            <p className="text-[11px] text-muted-foreground truncate">
                              {c.role || 'Applicant'}
                            </p>
                          </div>

                          <div
                            onClick={(e) => e.stopPropagation()}
                            className="shrink-0"
                          >
                            <DropdownMenu>
                              <DropdownMenuTrigger
                                render={
                                  <button
                                    className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/80"
                                    title="More options"
                                  >
                                    <MoreHorizontal size={14} />
                                  </button>
                                }
                              />
                              <DropdownMenuContent align="end" className="w-44 text-xs">
                                <DropdownMenuItem onClick={() => onSelectCandidate(c)}>
                                  <Eye size={13} className="mr-2" /> View Dossier
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => onOpenInterview(c)}>
                                  <Calendar size={13} className="mr-2" /> Schedule Interview
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => onOpenOffer(c)}>
                                  <FileCheck size={13} className="mr-2" /> Issue Offer Letter
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <div className="px-2 py-1 text-[10px] uppercase font-bold text-muted-foreground">
                                  Move Stage
                                </div>
                                {STAGES.map((s) => (
                                  <DropdownMenuItem
                                    key={s.key}
                                    onClick={() => onUpdateStatus(c.id, s.key)}
                                    className={c.status === s.key ? 'font-bold text-primary' : ''}
                                  >
                                    {s.label}
                                  </DropdownMenuItem>
                                ))}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() => onDeleteCandidate(c.id)}
                                  className="text-destructive focus:text-destructive"
                                >
                                  <Trash2 size={13} className="mr-2" /> Delete Candidate
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </div>

                        {/* Match Score & Rank Pill */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${scoreBadge.bgColor} ${scoreBadge.textColor} border-current/20`}
                          >
                            <Sparkles size={10} />
                            {score}% {scoreBadge.label}
                          </span>

                          {c.scorecard?.rank && (
                            <span className="text-[10px] font-mono text-muted-foreground px-1.5 py-0.5 rounded bg-muted">
                              #{c.scorecard.rank}
                            </span>
                          )}

                          {c.scorecard?.experience_years !== undefined && (
                            <span className="text-[10px] text-muted-foreground">
                              {c.scorecard.experience_years}y exp
                            </span>
                          )}
                        </div>

                        {/* Skills Chips */}
                        {displayedSkills.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-0.5">
                            {displayedSkills.map((sk: any, i: number) => (
                              <span
                                key={i}
                                className="text-[10px] px-1.5 py-0.2 rounded bg-muted/70 text-muted-foreground border border-border/70 truncate max-w-[120px]"
                              >
                                {String(sk).trim()}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Card Footer: Quick Actions */}
                        <div
                          className="pt-2 border-t border-border flex items-center justify-between gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => onOpenInterview(c)}
                              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted text-[11px] flex items-center gap-1"
                              title="Schedule Interview"
                            >
                              <Calendar size={12} />
                            </button>
                            <button
                              onClick={() => onOpenOffer(c)}
                              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted text-[11px] flex items-center gap-1"
                              title="Issue Offer"
                            >
                              <FileCheck size={12} />
                            </button>
                          </div>

                          {nextStageKey && nextStageObj && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => onUpdateStatus(c.id, nextStageKey)}
                              className="h-6 px-2 text-[10px] font-semibold text-primary hover:text-primary hover:bg-primary/10 flex items-center gap-1"
                              title={`Advance to ${nextStageObj.label}`}
                            >
                              <span>{nextStageObj.label}</span>
                              <ChevronRight size={11} />
                            </Button>
                          )}
                        </div>
                      </div>
                    </Card>
                  );
                })
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

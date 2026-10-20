'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Calendar,
  Clock,
  Video,
  User,
  Mail,
  ExternalLink,
  Plus,
  CheckCircle2,
  FileCheck,
  Sparkles,
} from 'lucide-react';
import { Candidate, STAGES } from './hr-types';

interface HRInterviewsViewProps {
  candidates: Candidate[];
  onOpenScheduleInterview: (candidate?: Candidate) => void;
  onOpenOffer: (candidate: Candidate) => void;
  onUpdateStatus: (candidateId: string, newStatus: string) => void;
}

export default function HRInterviewsView({
  candidates,
  onOpenScheduleInterview,
  onOpenOffer,
  onUpdateStatus,
}: HRInterviewsViewProps) {
  // Find candidates that are in interview stage or shortlisted
  const interviewingCandidates = candidates.filter(
    (c) => c.status === 'interviewed' || c.status === 'screened'
  );

  return (
    <div className="space-y-4">
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-card border border-border rounded-xl px-5 py-3 shadow-2xs">
        <div>
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Calendar size={16} className="text-primary" />
            <span>Interview Scheduling &amp; Candidate Rounds</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Automated Google Meet integration, interviewer assignment, and SMTP calendar dispatch.
          </p>
        </div>

        <Button
          size="sm"
          onClick={() => onOpenScheduleInterview()}
          className="h-8.5 text-xs font-semibold flex items-center gap-1.5 shrink-0"
        >
          <Plus size={13} /> Schedule Interview
        </Button>
      </div>

      {/* Interview Cards Grid */}
      {interviewingCandidates.length === 0 ? (
        <Card className="bg-card border-dashed border-border p-12 text-center rounded-xl min-h-[300px] flex flex-col items-center justify-center space-y-2">
          <Calendar size={36} className="text-muted-foreground/60" />
          <h3 className="text-sm font-bold text-foreground">No Active Interviews Scheduled</h3>
          <p className="text-xs text-muted-foreground max-w-sm">
            Select a candidate from the Candidates &amp; Pipeline tab or click below to schedule a new interview round.
          </p>
          <Button
            size="sm"
            onClick={() => onOpenScheduleInterview()}
            className="mt-2 text-xs font-semibold"
          >
            <Plus size={13} className="mr-1.5" /> Schedule First Interview
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {interviewingCandidates.map((c) => {
            const sc = c.scorecard || {};
            const meetingLink = `https://meet.google.com/octa-${c.id.slice(0, 6)}`;

            return (
              <Card
                key={c.id}
                className="bg-card border-border hover:border-primary/40 transition-all p-4 shadow-2xs space-y-3"
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-xs font-bold text-foreground">{c.name || 'Candidate'}</h3>
                    <p className="text-[11px] text-muted-foreground">{c.role || 'Applicant'}</p>
                  </div>

                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                      c.status === 'interviewed'
                        ? 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                        : 'border-purple-500/30 bg-purple-500/10 text-purple-400'
                    }`}
                  >
                    {c.status === 'interviewed' ? 'Interview Active' : 'Ready to Schedule'}
                  </span>
                </div>

                {/* Interview Round Details */}
                <div className="p-3 bg-surface-hover/50 rounded-lg border border-border text-xs space-y-1.5">
                  <div className="flex items-center gap-2 text-foreground font-semibold">
                    <Video size={13} className="text-primary shrink-0" />
                    <span className="truncate">Round 1: Technical &amp; System Architecture</span>
                  </div>

                  <div className="flex items-center gap-2 text-muted-foreground text-[11px]">
                    <Clock size={12} className="shrink-0" />
                    <span>Next Business Day • 11:00 AM UTC</span>
                  </div>

                  <div className="flex items-center gap-2 text-muted-foreground text-[11px]">
                    <User size={12} className="shrink-0" />
                    <span>Lead Technical Interviewer</span>
                  </div>
                </div>

                {/* Meeting Link & Contact */}
                <div className="flex items-center justify-between text-xs pt-1">
                  <a
                    href={meetingLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-primary hover:underline font-semibold"
                  >
                    <Video size={13} />
                    <span>Join Google Meet</span>
                    <ExternalLink size={10} />
                  </a>

                  <span className="text-[11px] text-muted-foreground truncate max-w-[140px]">
                    {c.email || '—'}
                  </span>
                </div>

                {/* Bottom Actions */}
                <div className="pt-2 border-t border-border flex items-center justify-between gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onOpenScheduleInterview(c)}
                    className="h-7 text-[11px] font-semibold"
                  >
                    Reschedule
                  </Button>

                  <Button
                    size="sm"
                    onClick={() => onOpenOffer(c)}
                    className="h-7 text-[11px] font-semibold flex items-center gap-1"
                  >
                    <FileCheck size={12} /> Advance to Offer
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

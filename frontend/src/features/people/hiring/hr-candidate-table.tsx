'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table as TableIcon,
  Download,
  Trash2,
  Edit2,
  Calendar,
  FileCheck,
  Eye,
  ExternalLink,
  MoreHorizontal,
  Loader2,
  FileSpreadsheet,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Candidate, STAGES, getScoreBadgeClass } from './hr-types';

interface HRCandidateTableProps {
  candidates: Candidate[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: (checked: boolean) => void;
  onSelectCandidate: (candidate: Candidate) => void;
  onOpenEditCandidate: (candidate: Candidate) => void;
  onOpenInterview: (candidate: Candidate) => void;
  onOpenOffer: (candidate: Candidate) => void;
  onDeleteCandidate: (candidateId: string) => void;
  onBatchDelete: (deleteAll: boolean) => void;
  isBatchDeleting: boolean;
  onExportExcel: () => void;
  onOpenImportExcel: () => void;
  exportingExcel: boolean;
}

export default function HRCandidateTable({
  candidates,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onSelectCandidate,
  onOpenEditCandidate,
  onOpenInterview,
  onOpenOffer,
  onDeleteCandidate,
  onBatchDelete,
  isBatchDeleting,
  onExportExcel,
  onOpenImportExcel,
  exportingExcel,
}: HRCandidateTableProps) {
  const isAllSelected = candidates.length > 0 && selectedIds.length === candidates.length;

  return (
    <div className="space-y-3">
      {/* Table Toolbar & Bulk Actions Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-card border border-border rounded-xl px-4 py-2.5 shadow-2xs">
        <div className="flex items-center gap-2">
          {selectedIds.length > 0 ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-foreground">
                {selectedIds.length} candidate(s) selected
              </span>

              <Button
                size="sm"
                variant="destructive"
                disabled={isBatchDeleting}
                onClick={() => onBatchDelete(false)}
                className="h-8 text-xs font-semibold flex items-center gap-1.5"
              >
                {isBatchDeleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                <span>Delete Selected</span>
              </Button>

              <Button
                size="sm"
                variant="ghost"
                onClick={() => onToggleSelectAll(false)}
                className="h-8 text-xs text-muted-foreground hover:text-foreground"
              >
                Clear Selection
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <TableIcon size={14} className="text-primary" />
              <span>Structured extraction sheet • {candidates.length} record(s)</span>
            </div>
          )}
        </div>

        {/* Global Table Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {candidates.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              disabled={isBatchDeleting}
              onClick={() => onBatchDelete(true)}
              className="h-8 text-xs text-destructive hover:text-destructive hover:bg-destructive/10 border-border"
            >
              <Trash2 size={13} className="mr-1.5" /> Delete All
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={onOpenImportExcel}
            className="h-8 text-xs flex items-center gap-1.5"
          >
            <FileSpreadsheet size={13} className="text-[#64B99A]" /> Import
          </Button>

          <Button
            size="sm"
            onClick={onExportExcel}
            disabled={exportingExcel || candidates.length === 0}
            className="h-8 text-xs font-semibold flex items-center gap-1.5"
          >
            {exportingExcel ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
            <span>Export .xlsx</span>
          </Button>
        </div>
      </div>

      {/* Structured Table */}
      <Card className="bg-card border-border rounded-xl overflow-hidden shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse min-w-[950px]">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                <th className="py-3 px-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={(e) => onToggleSelectAll(e.target.checked)}
                    className="h-3.5 w-3.5 rounded border-border bg-card text-primary focus:ring-primary/20 cursor-pointer"
                    title="Select All Candidates"
                  />
                </th>
                <th className="py-3 px-3 w-10 text-center font-mono">#</th>
                <th className="py-3 px-4 font-semibold">Candidate</th>
                <th className="py-3 px-3 font-semibold">Match</th>
                <th className="py-3 px-3 font-semibold">Stage</th>
                <th className="py-3 px-4 font-semibold">Contact</th>
                <th className="py-3 px-4 font-semibold">Skills Extracted</th>
                <th className="py-3 px-3 font-semibold">Experience</th>
                <th className="py-3 px-3 text-center font-semibold">Resume</th>
                <th className="py-3 px-3 w-12 text-center">Actions</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-border/60">
              {candidates.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-muted-foreground">
                    No candidates found matching the criteria.
                  </td>
                </tr>
              ) : (
                candidates.map((c, idx) => {
                  const isSelected = selectedIds.includes(c.id);
                  const sc = c.scorecard || {};
                  const score = sc.composite_score ?? sc.match_score ?? 60;
                  const scoreBadge = getScoreBadgeClass(score);
                  const stageObj = STAGES.find((s) => s.key === c.status) || STAGES[0];
                  const skills = sc.skills || sc.matched_skills || [];
                  const skillsList = Array.isArray(skills)
                    ? skills
                    : String(skills).split(',').map((s) => s.trim()).filter(Boolean);

                  return (
                    <tr
                      key={c.id}
                      className={`hover:bg-surface-hover/50 transition-colors ${
                        isSelected ? 'bg-primary/5' : ''
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-2.5 px-3 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => onToggleSelect(c.id)}
                          className="h-3.5 w-3.5 rounded border-border bg-card text-primary focus:ring-primary/20 cursor-pointer"
                        />
                      </td>

                      {/* Index / Rank */}
                      <td className="py-2.5 px-3 text-center font-mono text-[11px] text-muted-foreground">
                        {idx + 1}
                      </td>

                      {/* Name & Role */}
                      <td className="py-2.5 px-4">
                        <div
                          className="font-bold text-foreground hover:text-primary transition-colors cursor-pointer"
                          onClick={() => onSelectCandidate(c)}
                        >
                          {c.name || 'Unnamed Candidate'}
                        </div>
                        <div className="text-[11px] text-muted-foreground truncate max-w-[200px]">
                          {c.role || 'Applicant'}
                        </div>
                      </td>

                      {/* Match Score */}
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold font-mono border ${scoreBadge.bgColor} ${scoreBadge.textColor} border-current/20`}
                        >
                          {score}%
                        </span>
                      </td>

                      {/* Stage */}
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${stageObj.color}`}
                        >
                          {stageObj.label}
                        </span>
                      </td>

                      {/* Contact Info */}
                      <td className="py-2.5 px-4 whitespace-nowrap">
                        <div className="text-foreground truncate max-w-[180px]">{c.email || '—'}</div>
                        <div className="text-[11px] text-muted-foreground">{c.phone || sc.phone_number || sc.phone || '—'}</div>
                      </td>

                      {/* Skills */}
                      <td className="py-2.5 px-4">
                        <div className="flex flex-wrap gap-1 max-w-[280px]">
                          {skillsList.slice(0, 3).map((sk: any, i: number) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.2 rounded bg-muted text-[10px] text-muted-foreground border border-border truncate max-w-[90px]"
                            >
                              {String(sk).trim()}
                            </span>
                          ))}
                          {skillsList.length > 3 && (
                            <span className="text-[10px] text-muted-foreground font-mono">
                              +{skillsList.length - 3}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Experience */}
                      <td className="py-2.5 px-3 whitespace-nowrap text-muted-foreground font-mono">
                        {sc.is_internship_only || sc.experience_years === 0 ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            Intern
                          </span>
                        ) : sc.experience_years !== undefined ? (
                          `${sc.experience_years}y`
                        ) : (
                          '—'
                        )}
                      </td>

                      {/* Resume Link */}
                      <td className="py-2.5 px-3 text-center">
                        {sc.resume_link ? (
                          <a
                            href={sc.resume_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
                          >
                            PDF <ExternalLink size={10} />
                          </a>
                        ) : (
                          <span className="text-[10px] text-muted-foreground font-mono">parsed</span>
                        )}
                      </td>

                      {/* Actions Dropdown */}
                      <td className="py-2.5 px-3 text-center">
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            render={
                              <button
                                className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted"
                                title="Candidate actions"
                              >
                                <MoreHorizontal size={14} />
                              </button>
                            }
                          />
                          <DropdownMenuContent align="end" className="w-44 text-xs">
                            <DropdownMenuItem onClick={() => onSelectCandidate(c)}>
                              <Eye size={13} className="mr-2" /> View Dossier
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onOpenEditCandidate(c)}>
                              <Edit2 size={13} className="mr-2" /> Edit Profile
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onOpenInterview(c)}>
                              <Calendar size={13} className="mr-2" /> Schedule Interview
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onOpenOffer(c)}>
                              <FileCheck size={13} className="mr-2" /> Issue Offer Letter
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              onClick={() => onDeleteCandidate(c.id)}
                              className="text-destructive focus:text-destructive"
                            >
                              <Trash2 size={13} className="mr-2" /> Delete Candidate
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

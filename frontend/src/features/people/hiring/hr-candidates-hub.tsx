'use client';

import React, { useState, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Search,
  Kanban as KanbanIcon,
  Award,
  Table as TableIcon,
  SlidersHorizontal,
  X,
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Candidate, CandidateViewMode, STAGES } from './hr-types';
import HRCandidateKanban from './hr-candidate-kanban';
import HRCandidateLeaderboard from './hr-candidate-leaderboard';
import HRCandidateTable from './hr-candidate-table';
import HRCandidateDossierModal from './hr-candidate-dossier-modal';

interface HRCandidatesHubProps {
  candidates: Candidate[];
  onUpdateStatus: (candidateId: string, newStatus: string) => void;
  onOpenEditCandidate: (candidate: Candidate) => void;
  onOpenInterview: (candidate: Candidate) => void;
  onOpenOffer: (candidate: Candidate) => void;
  onDeleteCandidate: (candidateId: string) => void;
  onBatchDelete: (deleteAll: boolean) => void;
  isBatchDeleting: boolean;
  onExportExcel: () => void;
  onOpenImportExcel: () => void;
  exportingExcel: boolean;
  onOpenIngest?: () => void;
  onAskCopilot?: (message: string, resourceId?: string) => void;
}

export default function HRCandidatesHub({
  candidates,
  onUpdateStatus,
  onOpenEditCandidate,
  onOpenInterview,
  onOpenOffer,
  onDeleteCandidate,
  onBatchDelete,
  isBatchDeleting,
  onExportExcel,
  onOpenImportExcel,
  exportingExcel,
  onOpenIngest,
  onAskCopilot,
}: HRCandidatesHubProps) {
  const [viewMode, setViewMode] = useState<CandidateViewMode>('kanban');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tierFilter, setTierFilter] = useState('all');
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [selectedSheetIds, setSelectedSheetIds] = useState<string[]>([]);

  // Filter candidates based on search, status, and score tier
  const filteredCandidates = useMemo(() => {
    return candidates.filter((c) => {
      const q = searchQuery.toLowerCase().trim();
      const nameMatch = (c.name || '').toLowerCase().includes(q);
      const emailMatch = (c.email || '').toLowerCase().includes(q);
      const roleMatch = (c.role || '').toLowerCase().includes(q);
      const skillsMatch = Array.isArray(c.scorecard?.skills)
        ? c.scorecard?.skills.some((s: string) => s.toLowerCase().includes(q))
        : false;

      const matchesSearch = !q || nameMatch || emailMatch || roleMatch || skillsMatch;
      const matchesStatus = statusFilter === 'all' || (c.status || 'sourced') === statusFilter;

      const score = c.scorecard?.composite_score ?? c.scorecard?.match_score ?? 60;
      let matchesTier = true;
      if (tierFilter === 'top') matchesTier = score >= 85;
      else if (tierFilter === 'strong') matchesTier = score >= 70 && score < 85;
      else if (tierFilter === 'moderate') matchesTier = score < 70;

      return matchesSearch && matchesStatus && matchesTier;
    });
  }, [candidates, searchQuery, statusFilter, tierFilter]);

  // Selection handlers for table view
  const handleToggleSelect = (id: string) => {
    setSelectedSheetIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleToggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedSheetIds(filteredCandidates.map((c) => c.id));
    } else {
      setSelectedSheetIds([]);
    }
  };

  return (
    <div className="space-y-4">
      {/* Search, Filter, and View Mode Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-card border border-border rounded-xl p-3 shadow-2xs">
        {/* Search Input */}
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by candidate name, role, email, or skill..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-surface-hover/60 border-border text-foreground text-xs h-9 rounded-lg"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X size={13} />
            </button>
          )}
        </div>

        {/* Filters and View Mode Switcher */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Status Filter */}
          <Select value={statusFilter} onValueChange={(val) => val && setStatusFilter(val)}>
            <SelectTrigger className="bg-surface-hover/60 border-border text-foreground text-xs h-9 w-32 rounded-lg">
              <SelectValue placeholder="All Stages" />
            </SelectTrigger>
            <SelectContent className="bg-card border-border text-foreground text-xs">
              <SelectItem value="all">All Stages</SelectItem>
              {STAGES.map((s) => (
                <SelectItem key={s.key} value={s.key}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Tier Filter */}
          <Select value={tierFilter} onValueChange={(val) => val && setTierFilter(val)}>
            <SelectTrigger className="bg-surface-hover/60 border-border text-foreground text-xs h-9 w-36 rounded-lg">
              <SelectValue placeholder="All Tiers" />
            </SelectTrigger>
            <SelectContent className="bg-card border-border text-foreground text-xs">
              <SelectItem value="all">All Match Tiers</SelectItem>
              <SelectItem value="top">Top Match (85%+)</SelectItem>
              <SelectItem value="strong">Strong Match (70–84%)</SelectItem>
              <SelectItem value="moderate">Moderate Match (&lt;70%)</SelectItem>
            </SelectContent>
          </Select>

          {/* View Mode Toggle Group */}
          <div className="flex items-center bg-muted/70 border border-border rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('kanban')}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'kanban'
                  ? 'bg-card text-foreground shadow-2xs font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Pipeline Kanban Board"
            >
              <KanbanIcon size={13} />
              <span className="hidden sm:inline">Kanban</span>
            </button>

            <button
              onClick={() => setViewMode('leaderboard')}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'leaderboard'
                  ? 'bg-card text-foreground shadow-2xs font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Ranked Scorecard Leaderboard"
            >
              <Award size={13} />
              <span className="hidden sm:inline">Scorecards</span>
            </button>

            <button
              onClick={() => setViewMode('table')}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-card text-foreground shadow-2xs font-bold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Extraction Spreadsheet Table"
            >
              <TableIcon size={13} />
              <span className="hidden sm:inline">Sheet</span>
            </button>
          </div>
        </div>
      </div>

      {/* Render Active View Mode */}
      {viewMode === 'kanban' && (
        <HRCandidateKanban
          candidates={filteredCandidates}
          onSelectCandidate={setSelectedCandidate}
          onUpdateStatus={onUpdateStatus}
          onOpenInterview={onOpenInterview}
          onOpenOffer={onOpenOffer}
          onDeleteCandidate={onDeleteCandidate}
        />
      )}

      {viewMode === 'leaderboard' && (
        <HRCandidateLeaderboard
          candidates={filteredCandidates}
          onSelectCandidate={setSelectedCandidate}
          onOpenInterview={onOpenInterview}
          onOpenOffer={onOpenOffer}
          onDeleteCandidate={onDeleteCandidate}
          onUpdateStatus={onUpdateStatus}
        />
      )}

      {viewMode === 'table' && (
        <HRCandidateTable
          candidates={filteredCandidates}
          selectedIds={selectedSheetIds}
          onToggleSelect={handleToggleSelect}
          onToggleSelectAll={handleToggleSelectAll}
          onSelectCandidate={setSelectedCandidate}
          onOpenEditCandidate={onOpenEditCandidate}
          onOpenInterview={onOpenInterview}
          onOpenOffer={onOpenOffer}
          onDeleteCandidate={onDeleteCandidate}
          onBatchDelete={onBatchDelete}
          isBatchDeleting={isBatchDeleting}
          onExportExcel={onExportExcel}
          onOpenImportExcel={onOpenImportExcel}
          exportingExcel={exportingExcel}
          onOpenIngest={onOpenIngest}
        />
      )}

      {/* Candidate Profile Dossier Modal */}
      <HRCandidateDossierModal
        candidate={selectedCandidate}
        isOpen={!!selectedCandidate}
        onClose={() => setSelectedCandidate(null)}
        onUpdateStatus={(id, st) => {
          onUpdateStatus(id, st);
          if (selectedCandidate && selectedCandidate.id === id) {
            setSelectedCandidate({ ...selectedCandidate, status: st });
          }
        }}
        onOpenEditCandidate={onOpenEditCandidate}
        onOpenInterview={onOpenInterview}
        onOpenOffer={onOpenOffer}
        onDeleteCandidate={onDeleteCandidate}
        onAskCopilot={onAskCopilot}
      />
    </div>
  );
}

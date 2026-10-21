export type HRTab = 'candidates' | 'ingestion' | 'interviews' | 'documents' | 'workflows';
export type CandidateViewMode = 'kanban' | 'leaderboard' | 'table';

export interface Scorecard {
  rank?: number;
  composite_score?: number;
  ats_score?: number;
  semantic_score?: number;
  match_score?: number;
  skills?: string[];
  matched_skills?: string[];
  missing_skills?: string[];
  is_internship_only?: boolean;
  experience_years?: number;
  experience_summary?: string;
  requirements_match?: string;
  salary_expectation?: string;
  phone_number?: string;
  phone?: string;
  address?: string;
  projects?: string[] | string;
  recommendation?: string;
  fit_verdict?: string;
  extra_remarks?: string;
  resume_link?: string;
  interview_round?: string;
  meeting_time?: string;
  duration_minutes?: number;
  panelists?: string[];
  interviewer_name?: string;
  meeting_link?: string;
}

export interface Candidate {
  id: string;
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  role?: string | null;
  status: string; // 'sourced' | 'screened' | 'interviewed' | 'offered' | 'hired' | 'rejected'
  scorecard?: Scorecard;
  created_at?: string;
  updated_at?: string;
  notes?: string;
  room_id?: string;
  room_slug?: string;
}

export interface StagedFile {
  id: string;
  file: File;
  selected: boolean;
  name: string;
  sizeFormatted: string;
  type: string;
}

export interface IngestionJob {
  job_id?: string;
  role?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_files?: number;
  processed_files?: number;
  progress_percent?: number;
  current_file?: string;
  error_message?: string;
  logs?: string[];
}

export interface DocumentArtifact {
  artifact_id: string;
  document_type: string;
  title: string;
  html: string;
  artifact_sha256: string;
  status?: string;
  approved_by?: string;
  approved_at?: string;
}

export interface DocumentPacket {
  packet_id: string;
  candidate_id: string;
  status: string;
  artifacts: DocumentArtifact[];
  created_at?: string;
}

export interface ScheduledInterview {
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  candidate_role: string;
  interview_date: string;
  interview_time: string;
  round_name: string;
  meeting_link: string;
  interviewer_name: string;
  custom_notes?: string;
}

export interface Requisition {
  id: string;
  title: string;
  status: string;
  headcount_approved: number;
  headcount_filled: number;
  role?: string;
}

export const STAGES = [
  { key: 'sourced', label: 'Sourced', color: 'border-blue-500/30 bg-blue-500/10 text-blue-400', badgeVariant: 'info' as const },
  { key: 'screened', label: 'Screened', color: 'border-purple-500/30 bg-purple-500/10 text-purple-400', badgeVariant: 'secondary' as const },
  { key: 'interviewed', label: 'Interviewed', color: 'border-amber-500/30 bg-amber-500/10 text-amber-400', badgeVariant: 'warning' as const },
  { key: 'offered', label: 'Offered', color: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400', badgeVariant: 'info' as const },
  { key: 'hired', label: 'Hired', color: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400', badgeVariant: 'success' as const },
  { key: 'rejected', label: 'Rejected', color: 'border-rose-500/30 bg-rose-500/10 text-rose-400', badgeVariant: 'destructive' as const },
] as const;

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getScoreBadgeClass(score: number): {
  badge: 'success' | 'warning' | 'destructive' | 'info' | 'secondary';
  textColor: string;
  bgColor: string;
  label: string;
} {
  if (score >= 85) {
    return {
      badge: 'success',
      textColor: 'text-[#64B99A]',
      bgColor: 'bg-[#263D38]',
      label: 'Top Match'
    };
  }
  if (score >= 70) {
    return {
      badge: 'warning',
      textColor: 'text-[#D9AD68]',
      bgColor: 'bg-[#443A2D]',
      label: 'Strong Match'
    };
  }
  if (score >= 50) {
    return {
      badge: 'info',
      textColor: 'text-[#75AFCB]',
      bgColor: 'bg-[#2B3945]',
      label: 'Moderate'
    };
  }
  return {
    badge: 'destructive',
    textColor: 'text-[#D9828B]',
    bgColor: 'bg-[#462F35]',
    label: 'Low Match'
  };
}

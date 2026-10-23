'use client';

import React, { useState, useEffect, useRef } from 'react';
import { notify, confirmAction } from '@/lib/notify';
import RoomFolderExplorer from '@/components/rooms/room-folder-explorer';
import RoomHeader from '@/components/rooms/room-header';
import { SectionRoomData } from '@/components/rooms/room-access-modal';
import HiringWorkflowView from './hiring-workflow-view';

import {
  Candidate,
  HRTab,
  StagedFile,
  IngestionJob,
  DocumentPacket,
  formatFileSize,
} from './hr-types';
import HRHeader from './hr-header';
import HRCandidatesHub from './hr-candidates-hub';
import HRIngestionView from './hr-ingestion-view';
import HRInterviewsView from './hr-interviews-view';
import HRDocumentStudioModal from './hr-document-studio-modal';
import {
  ManualAddCandidateModal,
  EditCandidateModal,
  ImportExcelModal,
  ScheduleInterviewModal,
} from './hr-modals';

interface HRViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  initialRoomSlug?: string;
  dataRevision?: number;
  onAskCopilot?: (message: string, resourceId?: string) => void;
}

export default function HRView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  initialRoomSlug,
  dataRevision = 0,
  onAskCopilot,
}: HRViewProps) {
  // ── Section Room State ──
  const [rooms, setRooms] = useState<SectionRoomData[]>([]);
  const [roomsLoading, setRoomsLoading] = useState(false);
  const DEFAULT_ROOM: SectionRoomData = {
    id: 'default',
    slug: 'default',
    name: 'General Hiring',
    section: 'hr',
    status: 'active',
    visibility: 'internal_public',
    access_list: [],
    created_at: new Date().toISOString(),
    data: {
      role: 'Senior Full Stack Engineer',
      requirements: 'Python, FastAPI, React, TypeScript, PostgreSQL, Docker, 3+ years experience',
      salary: '$130,000/year',
    },
  };

  const [currentRoomSlug, setCurrentRoomSlug] = useState<string | null>(initialRoomSlug || 'default');
  const [currentRoom, setCurrentRoom] = useState<SectionRoomData>(DEFAULT_ROOM);
  const [isDirectoryView, setIsDirectoryView] = useState(false);

  // ── Main Candidates & ATS State ──
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [hrRole, setHrRole] = useState('Senior Full Stack Engineer');
  const [hrRequirements, setHrRequirements] = useState(
    'Python, FastAPI, React, TypeScript, PostgreSQL, Docker, 3+ years experience'
  );
  const [hrSalary, setHrSalary] = useState('$130,000/year');
  const [hrProvider, setHrProvider] = useState('auto');
  const [hrModel, setHrModel] = useState('');

  // ── Navigation ──
  const [activeTab, setActiveTab] = useState<HRTab>('candidates');

  // ── Staged Files & Ingestion ──
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [uploadPercent, setUploadPercent] = useState<number>(0);
  const [currentProcessingFile, setCurrentProcessingFile] = useState<string>('');
  const [ingestionLogs, setIngestionLogs] = useState<string[]>([]);
  const [activeJob, setActiveJob] = useState<IngestionJob | null>(null);
  const [showLogsDrawer, setShowLogsDrawer] = useState(false);

  // ── Excel Export / Import ──
  const [exportingExcel, setExportingExcel] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importingExcel, setImportingExcel] = useState(false);

  // ── Batch Delete State ──
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);

  // ── Manual Add Modal State ──
  const [isManualAddOpen, setIsManualAddOpen] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualEmail, setManualEmail] = useState('');
  const [manualRole, setManualRole] = useState('');
  const [manualPhone, setManualPhone] = useState('');
  const [manualSkills, setManualSkills] = useState('');
  const [manualExperience, setManualExperience] = useState('');
  const [manualBudget, setManualBudget] = useState('');
  const [manualExtra, setManualExtra] = useState('');
  const [manualAdding, setManualAdding] = useState(false);

  // ── Edit Candidate Modal State ──
  const [editingCandidate, setEditingCandidate] = useState<Candidate | null>(null);
  const [editName, setEditName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editRole, setEditRole] = useState('');
  const [editStatus, setEditStatus] = useState('sourced');
  const [editPhone, setEditPhone] = useState('');
  const [editAddress, setEditAddress] = useState('');
  const [editSkills, setEditSkills] = useState('');
  const [editProjects, setEditProjects] = useState('');
  const [editExperienceYears, setEditExperienceYears] = useState('');
  const [editExperienceSummary, setEditExperienceSummary] = useState('');
  const [editResumeLink, setEditResumeLink] = useState('');
  const [editExtraRemarks, setEditExtraRemarks] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  // ── Interview Scheduling Modal State ──
  const [interviewCandidate, setInterviewCandidate] = useState<Candidate | null>(null);
  const [interviewDate, setInterviewDate] = useState<string>('');
  const [interviewTime, setInterviewTime] = useState<string>('11:00 AM');
  const [interviewRound, setInterviewRound] = useState<string>('Technical System Design');
  const [meetingLink, setMeetingLink] = useState<string>('https://meet.google.com/octa-interview');
  const [interviewerName, setInterviewerName] = useState<string>('Engineering Hiring Lead');
  const [interviewTimezone, setInterviewTimezone] = useState<string>(
    typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC' : 'UTC'
  );
  const [interviewDuration, setInterviewDuration] = useState<number>(45);
  const [interviewPanelists, setInterviewPanelists] = useState<any[]>([]);
  const [interviewNotes, setInterviewNotes] = useState<string>('');
  const [interviewSending, setInterviewSending] = useState<boolean>(false);

  // ── Governed Document Studio State ──
  const [offerCandidate, setOfferCandidate] = useState<Candidate | null>(null);
  const [contractTemplates, setContractTemplates] = useState<any[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('full_time_standard');
  const [offerVariables, setOfferVariables] = useState<Record<string, any>>({});
  const [offerPreviewHtml, setOfferPreviewHtml] = useState<string>('');
  const [currentPacketData, setCurrentPacketData] = useState<DocumentPacket | null>(null);
  const [contractGenerating, setContractGenerating] = useState<boolean>(false);
  const [isArtifactApproved, setIsArtifactApproved] = useState<boolean>(false);
  const [approvalSubmitting, setApprovalSubmitting] = useState<boolean>(false);
  const [offerSending, setOfferSending] = useState<boolean>(false);

  // ── Initial Data Loading ──
  useEffect(() => {
    if (token) {
      fetchRooms();
      fetchCandidates();
      fetchContractTemplates();
      checkIngestionJobStatus();
    }
  }, [token, dataRevision]);

  const fetchRooms = async () => {
    if (!token) return;
    setRoomsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/rooms/?section=hr`);
      if (res.ok) {
        const data = await res.json();
        setRooms(data);
        if (currentRoomSlug) {
          const match = data.find((r: any) => r.slug === currentRoomSlug);
          if (match) {
            setCurrentRoom(match);
            if (match.data?.role) setHrRole(match.data.role);
            if (match.data?.requirements) setHrRequirements(match.data.requirements);
            if (match.data?.salary) setHrSalary(match.data.salary);
          }
        } else if (data.length > 0) {
          const defaultRoom = data.find((r: any) => r.slug === 'default') || data[0];
          setCurrentRoom(defaultRoom);
          setCurrentRoomSlug(defaultRoom.slug);
          if (defaultRoom.data?.role) setHrRole(defaultRoom.data.role);
          if (defaultRoom.data?.requirements) setHrRequirements(defaultRoom.data.requirements);
          if (defaultRoom.data?.salary) setHrSalary(defaultRoom.data.salary);
        }
      }
    } catch (err) {
      console.error('Failed to load HR rooms:', err);
    } finally {
      setRoomsLoading(false);
    }
  };

  const handleSelectRoom = (slug: string) => {
    setCurrentRoomSlug(slug);
    const match = rooms.find((r) => r.slug === slug);
    if (match) {
      setCurrentRoom(match);
      if (match.data?.role) setHrRole(match.data.role);
      if (match.data?.requirements) setHrRequirements(match.data.requirements);
      if (match.data?.salary) setHrSalary(match.data.salary);
    }
    setIsDirectoryView(false);
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', `/app/hiring/rooms/${slug}`);
    }
    fetchCandidates(slug);
  };

  const fetchCandidates = async (slugOverride?: string) => {
    if (!token) return;
    try {
      const targetSlug = slugOverride || currentRoomSlug;
      const url = targetSlug ? `${API_URL}/hr/?room_slug=${targetSlug}` : `${API_URL}/hr/`;
      const res = await fetchWithAuth(url);
      if (res.ok) {
        const data = await res.json();
        const sorted = data.sort((a: any, b: any) => {
          const scoreA = a.scorecard?.composite_score ?? a.scorecard?.match_score ?? 0;
          const scoreB = b.scorecard?.composite_score ?? b.scorecard?.match_score ?? 0;
          return scoreB - scoreA;
        });
        setCandidates(sorted);
      }
    } catch (e) {
      console.error('Error fetching candidates:', e);
    }
  };

  const fetchContractTemplates = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/contract-templates`);
      if (res.ok) {
        setContractTemplates(await res.json());
      }
    } catch (e) {
      console.error('Error fetching contract templates:', e);
    }
  };

  const checkIngestionJobStatus = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/resumes/ingestion-status`);
      if (res.ok) {
        const data = await res.json();
        if (data.job) {
          const j = data.job;
          setActiveJob(j);
          setIngestionLogs(j.logs || []);
          if (data.has_active_job || j.status === 'running') {
            setUploadLoading(true);
            setUploadPercent(j.progress_percent || 15);
            setCurrentProcessingFile(j.current_file || `Processing ${j.processed_files}/${j.total_files} resumes...`);
            setTimeout(() => checkIngestionJobStatus(), 1500);
          } else if (j.status === 'completed') {
            setUploadLoading(false);
            setUploadPercent(100);
            setCurrentProcessingFile(`Completed: Processed ${j.processed_files} candidate(s)`);
            fetchCandidates();
          } else if (j.status === 'failed') {
            setUploadLoading(false);
            setCurrentProcessingFile(`Failed: ${j.error_message || 'Resume parsing encountered an error'}`);
          }
        } else {
          setActiveJob(null);
        }
      }
    } catch (e) {
      console.error('Error checking ingestion job status:', e);
    }
  };

  // ── Candidate Actions ──
  const handleUpdateStatus = async (candidateId: string, newStatus: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        fetchCandidates();
        fetchData();
      } else {
        const data = await res.json();
        notify(`Error: ${data.detail || 'Failed to update candidate status'}`);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteCandidate = async (candidateId: string) => {
    if (!(await confirmAction('Are you sure you want to delete this candidate?'))) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchCandidates();
        fetchData();
        notify('Candidate deleted successfully.');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleBatchDelete = async (deleteAll: boolean) => {
    const idsToDelete = deleteAll ? candidates.map((c) => c.id) : [];
    if (deleteAll && idsToDelete.length === 0) return;

    const confirmMsg = deleteAll
      ? `Are you sure you want to delete ALL ${candidates.length} candidates? This cannot be undone.`
      : 'Are you sure you want to delete the selected candidate(s)?';

    if (!(await confirmAction(confirmMsg))) return;

    setIsBatchDeleting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/candidates/batch-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_ids: idsToDelete }),
      });
      const data = await res.json();
      if (res.ok) {
        notify(data.message || `Deleted candidate(s).`);
        fetchCandidates();
        fetchData();
      } else {
        notify(`Error: ${data.detail || 'Failed to delete candidates'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error during candidate batch deletion.');
    } finally {
      setIsBatchDeleting(false);
    }
  };

  // ── Staged Files & Batch Upload ──
  const handleFilesAdded = (filesList: FileList | null) => {
    if (!filesList || filesList.length === 0) return;
    const newItems: StagedFile[] = [];
    const validExtensions = ['.pdf', '.docx', '.txt', '.md'];

    for (let i = 0; i < filesList.length; i++) {
      const file = filesList[i];
      const lower = file.name.toLowerCase();
      const isValid = validExtensions.some((ext) => lower.endsWith(ext));
      if (!isValid) continue;

      newItems.push({
        id: `${file.name}-${file.size}-${Date.now()}-${i}`,
        file,
        selected: true,
        name: file.name,
        sizeFormatted: formatFileSize(file.size),
        type: lower.endsWith('.pdf') ? 'PDF' : lower.endsWith('.docx') ? 'DOCX' : 'TEXT',
      });
    }

    setStagedFiles((prev) => [...prev, ...newItems]);
    setActiveTab('ingestion');
  };

  const handleToggleFileSelection = (id: string) => {
    setStagedFiles((prev) =>
      prev.map((item) => (item.id === id ? { ...item, selected: !item.selected } : item))
    );
  };

  const handleToggleSelectAllFiles = (select: boolean) => {
    setStagedFiles((prev) => prev.map((item) => ({ ...item, selected: select })));
  };

  const handleRemoveStagedFile = (id: string) => {
    setStagedFiles((prev) => prev.filter((item) => item.id !== id));
  };

  const handleProcessBatchUpload = async () => {
    const selected = stagedFiles.filter((item) => item.selected);
    if (selected.length === 0) {
      notify('Please select at least one resume from the staging queue.');
      return;
    }
    if (!hrRole || !hrRequirements) {
      notify('Please specify the target Role Title and Requirements.');
      return;
    }

    setUploadLoading(true);
    setUploadPercent(10);
    setCurrentProcessingFile(`Preparing ${selected.length} resume(s)...`);
    setIngestionLogs([
      `[${new Date().toLocaleTimeString()}] Target Role: "${hrRole}"`,
      `[${new Date().toLocaleTimeString()}] Engine: ${hrProvider.toUpperCase()} (${hrModel || 'default model'})`,
      `[${new Date().toLocaleTimeString()}] Initiating batch processing of ${selected.length} resume(s)...`,
    ]);

    try {
      const progressTimer = setInterval(() => {
        setUploadPercent((prev) => (prev < 85 ? prev + 8 : prev));
      }, 700);

      const formData = new FormData();
      selected.forEach((item) => formData.append('files', item.file));
      formData.append('role', hrRole);
      formData.append('requirements', hrRequirements);
      formData.append('salary', hrSalary);
      formData.append('provider', hrProvider);
      if (hrModel) formData.append('model', hrModel);
      if (currentRoom) {
        formData.append('room_id', currentRoom.id);
        formData.append('room_slug', currentRoom.slug);
      }

      setUploadProgress(`Extracting text & evaluating candidates (${selected.length} resumes)...`);
      setCurrentProcessingFile(`Running ATS matching & ${hrProvider.toUpperCase()} AI analysis...`);

      const res = await fetchWithAuth(`${API_URL}/hr/resumes/upload-batch`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressTimer);
      setUploadPercent(95);

      const data = await res.json();
      if (res.ok) {
        setUploadPercent(100);
        setCurrentProcessingFile(`Complete! Processed ${data.processed_count} candidates.`);
        setIngestionLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] ✓ Successfully parsed and ranked ${data.processed_count} candidate(s)`,
        ]);
        notify(`Success! Ingested and ranked ${data.processed_count} candidate(s).`);
        setStagedFiles((prev) => prev.filter((item) => !item.selected));
        await fetchCandidates();
        await fetchData();

        setTimeout(() => {
          setActiveTab('candidates');
          setUploadLoading(false);
          setUploadPercent(0);
          setCurrentProcessingFile('');
        }, 1000);
      } else {
        notify(`Upload error: ${data.detail || 'Failed to process resumes'}`);
      }
    } catch (e: any) {
      console.error(e);
      notify('Network error during batch resume upload.');
    } finally {
      setUploadLoading(false);
    }
  };

  // ── Excel Export & Import ──
  const handleExportExcel = async () => {
    try {
      setExportingExcel(true);
      const queryParams = new URLSearchParams();
      if (hrRole) queryParams.append('role', hrRole);
      if (currentRoom?.id && currentRoom.id !== 'default') queryParams.append('room_id', currentRoom.id);
      const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
      const res = await fetchWithAuth(`${API_URL}/hr/candidates/export-excel${queryString}`);
      if (!res.ok) {
        notify('Failed to export Excel spreadsheet.');
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `octaos_candidates_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      notify('Candidates Excel spreadsheet exported successfully!');
    } catch (e) {
      console.error(e);
      notify('Error downloading Excel file.');
    } finally {
      setExportingExcel(false);
    }
  };

  const handleImportExcel = async () => {
    if (!importFile) {
      notify('Please select an Excel (.xlsx) or CSV file to import.');
      return;
    }
    setImportingExcel(true);
    try {
      const formData = new FormData();
      formData.append('file', importFile);
      const res = await fetchWithAuth(`${API_URL}/hr/candidates/import-excel`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        notify(data.message || `Imported ${data.imported_count} candidate(s)!`);
        setIsImportModalOpen(false);
        setImportFile(null);
        fetchCandidates();
        fetchData();
        setActiveTab('candidates');
      } else {
        notify(`Import error: ${data.detail || 'Failed to import spreadsheet'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error importing spreadsheet.');
    } finally {
      setImportingExcel(false);
    }
  };

  // ── Manual Add Candidate ──
  const handleAddManualCandidate = async () => {
    if (!manualName || !manualEmail || !manualRole) {
      notify('Please fill in Name, Email, and Role.');
      return;
    }
    setManualAdding(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: manualName,
          email: manualEmail,
          role: manualRole,
          status: 'sourced',
          scorecard: {
            rank: candidates.length + 1,
            composite_score: 90,
            ats_score: 90,
            semantic_score: 90,
            match_score: 90,
            skills: manualSkills ? manualSkills.split(',').map((s) => s.trim()).filter(Boolean) : [],
            matched_skills: manualSkills ? manualSkills.split(',').map((s) => s.trim()).filter(Boolean) : [],
            missing_skills: [],
            experience_years: parseInt(manualExperience) || 3,
            experience_summary: manualExperience ? `${manualExperience} years of experience.` : 'Manually added candidate.',
            requirements_match: manualExtra || 'Manually verified candidate profile.',
            salary_expectation: manualBudget || '$120,000/year',
            phone_number: manualPhone || '',
            recommendation: 'Recommended',
          },
        }),
      });
      if (res.ok) {
        setIsManualAddOpen(false);
        setManualName('');
        setManualEmail('');
        setManualRole('');
        setManualPhone('');
        setManualSkills('');
        setManualExperience('');
        setManualBudget('');
        setManualExtra('');
        fetchCandidates();
        fetchData();
        notify('Candidate added successfully!');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setManualAdding(false);
    }
  };

  // ── Edit Candidate Profile ──
  const openEditCandidateModal = (candidate: Candidate) => {
    setEditingCandidate(candidate);
    const sc = candidate.scorecard || {};
    setEditName(candidate.name || '');
    setEditEmail(candidate.email || '');
    setEditRole(candidate.role || '');
    setEditStatus(candidate.status || 'sourced');
    setEditPhone(sc.phone_number || sc.phone || '');
    setEditAddress(sc.address || '');
    setEditSkills(Array.isArray(sc.skills) ? sc.skills.join(', ') : sc.skills || '');
    setEditProjects(Array.isArray(sc.projects) ? sc.projects.join('; ') : sc.projects || '');
    setEditExperienceYears(sc.experience_years !== undefined ? String(sc.experience_years) : '');
    setEditExperienceSummary(sc.experience_summary || '');
    setEditResumeLink(sc.resume_link || '');
    setEditExtraRemarks(sc.extra_remarks || sc.fit_verdict || sc.recommendation || '');
  };

  const handleSaveEditedCandidate = async () => {
    if (!editingCandidate) return;
    setSavingEdit(true);
    try {
      const skillsArray = editSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const projectsArray = editProjects ? editProjects.split(';').map((p) => p.trim()).filter(Boolean) : [];

      const res = await fetchWithAuth(`${API_URL}/hr/${editingCandidate.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editName,
          email: editEmail,
          role: editRole,
          status: editStatus,
          phone: editPhone,
          address: editAddress,
          skills: skillsArray,
          projects: projectsArray,
          experience_years: editExperienceYears ? parseFloat(editExperienceYears) : 0,
          experience_summary: editExperienceSummary,
          resume_link: editResumeLink,
          extra_remarks: editExtraRemarks,
        }),
      });

      if (res.ok) {
        notify(`Successfully updated ${editName}'s profile!`);
        setEditingCandidate(null);
        fetchCandidates();
      } else {
        const errData = await res.json();
        notify(`Error: ${errData.detail || 'Failed to update candidate'}`);
      }
    } catch (e) {
      console.error('Error updating candidate:', e);
      notify('Network error updating candidate.');
    } finally {
      setSavingEdit(false);
    }
  };

  // ── Interview Scheduling ──
  const openInterviewModal = (candidate?: Candidate) => {
    const target = candidate || candidates[0];
    if (!target) {
      notify('No candidates available to schedule.');
      return;
    }
    setInterviewCandidate(target);
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setInterviewDate(tomorrow.toISOString().split('T')[0]);
    setMeetingLink(`https://meet.google.com/octa-${target.id.slice(0, 6)}`);
    setInterviewRound('Round 1: Technical & System Architecture');
    setInterviewerName('Lead Technical Interviewer');
    setInterviewPanelists([
      { name: 'Lead Technical Interviewer', email: 'interviewer@octaos.ai', role: 'interviewer' }
    ]);
    setInterviewNotes('');
  };

  const handleSendInterviewEmail = async () => {
    if (!interviewCandidate || !interviewDate) {
      notify('Please provide the interview date.');
      return;
    }
    setInterviewSending(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${interviewCandidate.id}/send-interview-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          interview_date: interviewDate,
          interview_time: interviewTime,
          round_name: interviewRound,
          meeting_link: meetingLink,
          interviewer_name: interviewerName,
          interviewers: interviewPanelists,
          timezone: interviewTimezone,
          duration_minutes: interviewDuration,
          custom_notes: interviewNotes,
          channel: 'smtp',
        }),
      });
      const data = await res.json();
      if (res.ok) {
        notify(`Interview invitation successfully dispatched to ${interviewCandidate.name}!`);
        setInterviewCandidate(null);
        fetchCandidates();
        fetchData();
      } else {
        notify(`Error: ${data.detail || 'Failed to send interview invitation'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error sending interview email.');
    } finally {
      setInterviewSending(false);
    }
  };

  // ── Document Studio ──
  const openOfferModal = async (candidate?: Candidate) => {
    const target = candidate || candidates[0];
    if (!target) {
      notify('No candidates available.');
      return;
    }
    setOfferCandidate(target);
    setIsArtifactApproved(false);
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 14);

    const initialVars = {
      candidate_name: target.name,
      candidate_email: target.email,
      candidate_address: 'San Francisco, CA',
      job_title: target.role,
      department: 'Engineering',
      employment_type: 'Full-Time Permanent',
      start_date: tomorrow.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
      salary_amount: target.scorecard?.salary_expectation?.replace(/[^0-9]/g, '') || '130,000',
      salary_currency: 'USD',
      work_mode: 'Remote (Global)',
      reporting_manager: 'VP of Engineering',
      probation_months: '3',
      notice_period_days: '30',
      company_name: 'OctaOS Technologies Inc.',
      company_address: '100 Innovation Way, Suite 400, Tech Park',
      signatory_name: 'Alex Vance',
      signatory_title: 'Head of People & Operations',
    };
    setOfferVariables(initialVars);
    setSelectedTemplateId('full_time_standard');
    await generateContractPreview(target.id, initialVars);
  };

  const generateContractPreview = async (candidateId: string, vars: Record<string, any>) => {
    setContractGenerating(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/document-packets/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: candidateId,
          override_variables: vars,
        }),
      });
      const data = await res.json();
      if (res.ok && data.artifacts) {
        setCurrentPacketData(data);
        const offerArt = data.artifacts.find((a: any) => a.document_type === 'offer_letter');
        if (offerArt) setOfferPreviewHtml(offerArt.html);
      } else {
        notify(`Preview generation failed: ${data.detail || 'Could not compile preview'}`);
      }
    } catch (e) {
      console.error('Failed to generate packet preview:', e);
    } finally {
      setContractGenerating(false);
    }
  };

  const handleApproveArtifact = async () => {
    if (!currentPacketData) return;
    const currentArt = currentPacketData.artifacts?.[0];
    if (!currentArt) return;

    setApprovalSubmitting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/document-packets/${currentPacketData.packet_id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          packet_id: currentPacketData.packet_id,
          artifact_id: currentArt.artifact_id,
          expected_artifact_sha256: currentArt.artifact_sha256,
          decision: 'approved',
          rationale: 'Verified and authorized by HR Admin via Governed Studio.',
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setIsArtifactApproved(true);
        notify('Document artifact cryptographically approved and bound to hash!');
      } else {
        notify(`Approval blocked: ${data.detail || 'Policy violation'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error authorizing artifact.');
    } finally {
      setApprovalSubmitting(false);
    }
  };

  const handleSendOfferEmail = async () => {
    if (!offerCandidate || !currentPacketData) return;
    setOfferSending(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/document-packets/${currentPacketData.packet_id}/dispatch-offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (res.ok) {
        notify(`Offer letter dispatched to ${offerCandidate.name} with secure acceptance link!`);
        setOfferCandidate(null);
        fetchCandidates();
      } else {
        notify(`Dispatch failed: ${data.detail || 'Could not send offer'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error dispatching offer.');
    } finally {
      setOfferSending(false);
    }
  };

  const handleDispatchAppointment = async () => {
    if (!currentPacketData) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/document-packets/${currentPacketData.packet_id}/dispatch-appointment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (res.ok) {
        notify('Official Appointment & Joining Letter successfully dispatched!');
        setOfferCandidate(null);
        fetchCandidates();
      } else {
        notify(`Error: ${data.detail || 'Failed to dispatch appointment letter'}`);
      }
    } catch (e) {
      notify('Network error dispatching appointment letter.');
    }
  };

  const handleExecuteContract = async () => {
    if (!currentPacketData) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/document-packets/${currentPacketData.packet_id}/execute-contract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (res.ok) {
        notify('Employment contract executed & employee onboarding provisioned!');
        setOfferCandidate(null);
        fetchCandidates();
      } else {
        notify(`Error: ${data.detail || 'Failed to execute contract'}`);
      }
    } catch (e) {
      notify('Network error executing contract.');
    }
  };

  // ── Metrics Computation for Header ──
  const screenedCount = candidates.filter((c) =>
    ['screened', 'interviewed', 'offered', 'hired'].includes(c.status)
  ).length;
  const interviewCount = candidates.filter((c) => c.status === 'interviewed').length;
  const hiredCount = candidates.filter((c) => ['offered', 'hired'].includes(c.status)).length;
  const avgMatchScore =
    candidates.length > 0
      ? Math.round(
          candidates.reduce(
            (acc, c) => acc + (c.scorecard?.composite_score ?? c.scorecard?.match_score ?? 60),
            0
          ) / candidates.length
        )
      : 84;

  if (roomsLoading && !currentRoom) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] text-muted-foreground gap-3">
        <p className="text-sm">Opening hiring…</p>
      </div>
    );
  }

  if (isDirectoryView && rooms.length > 0) {
    return (
      <RoomFolderExplorer
        section="hr"
        sectionTitle="HR & Hiring"
        rooms={rooms}
        loading={roomsLoading}
        onSelectRoom={handleSelectRoom}
        onRefresh={fetchRooms}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
      />
    );
  }

  return (
    <div className="space-y-4 animate-in fade-in duration-200 pb-16">
      {/* Room Header with Folder Directory & Access Switcher */}
      <RoomHeader
        sectionTitle="HR & Hiring"
        activeRoom={currentRoom}
        allRooms={rooms}
        onSelectRoom={handleSelectRoom}
        onOpenDirectory={() => setIsDirectoryView(true)}
        onCreateNewRoom={() => setIsDirectoryView(true)}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onRoomUpdated={(updated) => {
          setCurrentRoom(updated);
          setRooms((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
        }}
      />

      <div className="space-y-4 max-w-7xl mx-auto px-4 sm:px-6">
        {/* Executive Header, Metric Ribbon & Tab Navigation */}
        <HRHeader
          activeTab={activeTab}
          onSelectTab={(tab) => {
            if (tab === 'documents') {
              openOfferModal();
            } else {
              setActiveTab(tab);
            }
          }}
          candidatesCount={candidates.length}
          screenedCount={screenedCount}
          interviewCount={interviewCount}
          hiredCount={hiredCount}
          avgMatchScore={avgMatchScore}
          stagedFilesCount={stagedFiles.length}
          isIngesting={uploadLoading || activeJob?.status === 'running'}
          onOpenAddManual={() => setIsManualAddOpen(true)}
          onOpenImportExcel={() => setIsImportModalOpen(true)}
          onExportExcel={handleExportExcel}
          onOpenIngestion={() => setActiveTab('ingestion')}
        />

        {/* ── TAB 1: CANDIDATES & PIPELINE (UNIFIED HUB) ── */}
        {activeTab === 'candidates' && (
          <HRCandidatesHub
            candidates={candidates}
            onUpdateStatus={handleUpdateStatus}
            onOpenEditCandidate={openEditCandidateModal}
            onOpenInterview={openInterviewModal}
            onOpenOffer={openOfferModal}
            onDeleteCandidate={handleDeleteCandidate}
            onBatchDelete={handleBatchDelete}
            isBatchDeleting={isBatchDeleting}
            onExportExcel={handleExportExcel}
            onOpenImportExcel={() => setIsImportModalOpen(true)}
            exportingExcel={exportingExcel}
            onOpenIngest={() => setActiveTab('ingestion')}
            onAskCopilot={onAskCopilot}
          />
        )}

        {/* ── TAB 2: RESUME INGESTION & STAGING ZONE ── */}
        {activeTab === 'ingestion' && (
          <HRIngestionView
            hrRole={hrRole}
            setHrRole={setHrRole}
            hrRequirements={hrRequirements}
            setHrRequirements={setHrRequirements}
            hrSalary={hrSalary}
            setHrSalary={setHrSalary}
            hrProvider={hrProvider}
            setHrProvider={setHrProvider}
            hrModel={hrModel}
            setHrModel={setHrModel}
            stagedFiles={stagedFiles}
            onFilesAdded={handleFilesAdded}
            onToggleFileSelection={handleToggleFileSelection}
            onToggleSelectAll={handleToggleSelectAllFiles}
            onRemoveStagedFile={handleRemoveStagedFile}
            onProcessBatchUpload={handleProcessBatchUpload}
            uploadLoading={uploadLoading}
            uploadProgress={uploadProgress}
            uploadPercent={uploadPercent}
            currentProcessingFile={currentProcessingFile}
            ingestionLogs={ingestionLogs}
            activeJob={activeJob}
            showLogsDrawer={showLogsDrawer}
            setShowLogsDrawer={setShowLogsDrawer}
          />
        )}

        {/* ── TAB 3: INTERVIEW STUDIO & SCHEDULES ── */}
        {activeTab === 'interviews' && (
          <HRInterviewsView
            candidates={candidates}
            onOpenScheduleInterview={openInterviewModal}
            onOpenOffer={openOfferModal}
            onUpdateStatus={handleUpdateStatus}
          />
        )}

        {/* ── TAB 4: WORKFLOWS & TEMPLATES (PIPELINE DAG & REQUISITIONS) ── */}
        {activeTab === 'workflows' && (
          <HiringWorkflowView API_URL={API_URL} fetchWithAuth={fetchWithAuth} />
        )}

        {/* ── GLOBAL MODALS ── */}
        <ManualAddCandidateModal
          isOpen={isManualAddOpen}
          onClose={() => setIsManualAddOpen(false)}
          name={manualName}
          setName={setManualName}
          email={manualEmail}
          setEmail={setManualEmail}
          role={manualRole}
          setRole={setManualRole}
          phone={manualPhone}
          setPhone={setManualPhone}
          skills={manualSkills}
          setSkills={setManualSkills}
          experience={manualExperience}
          setExperience={setManualExperience}
          budget={manualBudget}
          setBudget={setManualBudget}
          extra={manualExtra}
          setExtra={setManualExtra}
          onAdd={handleAddManualCandidate}
          adding={manualAdding}
        />

        <EditCandidateModal
          candidate={editingCandidate}
          isOpen={!!editingCandidate}
          onClose={() => setEditingCandidate(null)}
          name={editName}
          setName={setEditName}
          email={editEmail}
          setEmail={setEditEmail}
          role={editRole}
          setRole={setEditRole}
          status={editStatus}
          setStatus={setEditStatus}
          phone={editPhone}
          setPhone={setEditPhone}
          address={editAddress}
          setAddress={setEditAddress}
          skills={editSkills}
          setSkills={setEditSkills}
          projects={editProjects}
          setProjects={setEditProjects}
          experienceYears={editExperienceYears}
          setExperienceYears={setEditExperienceYears}
          experienceSummary={editExperienceSummary}
          setExperienceSummary={setEditExperienceSummary}
          resumeLink={editResumeLink}
          setResumeLink={setEditResumeLink}
          extraRemarks={editExtraRemarks}
          setExtraRemarks={setEditExtraRemarks}
          onSave={handleSaveEditedCandidate}
          saving={savingEdit}
        />

        <ImportExcelModal
          isOpen={isImportModalOpen}
          onClose={() => {
            setIsImportModalOpen(false);
            setImportFile(null);
          }}
          importFile={importFile}
          setImportFile={setImportFile}
          onImport={handleImportExcel}
          importing={importingExcel}
        />

        <ScheduleInterviewModal
          candidate={interviewCandidate}
          isOpen={!!interviewCandidate}
          onClose={() => setInterviewCandidate(null)}
          interviewDate={interviewDate}
          setInterviewDate={setInterviewDate}
          interviewTime={interviewTime}
          setInterviewTime={setInterviewTime}
          interviewRound={interviewRound}
          setInterviewRound={setInterviewRound}
          interviewTimezone={interviewTimezone}
          setInterviewTimezone={setInterviewTimezone}
          interviewDuration={interviewDuration}
          setInterviewDuration={setInterviewDuration}
          panelists={interviewPanelists}
          setPanelists={setInterviewPanelists}
          meetingLink={meetingLink}
          setMeetingLink={setMeetingLink}
          interviewerName={interviewerName}
          setInterviewerName={setInterviewerName}
          interviewNotes={interviewNotes}
          setInterviewNotes={setInterviewNotes}
          onSendEmail={handleSendInterviewEmail}
          sending={interviewSending}
        />

        <HRDocumentStudioModal
          candidate={offerCandidate}
          isOpen={!!offerCandidate}
          onClose={() => setOfferCandidate(null)}
          contractTemplates={contractTemplates}
          offerVariables={offerVariables}
          setOfferVariables={setOfferVariables}
          offerPreviewHtml={offerPreviewHtml}
          currentPacketData={currentPacketData}
          isArtifactApproved={isArtifactApproved}
          contractGenerating={contractGenerating}
          approvalSubmitting={approvalSubmitting}
          offerSending={offerSending}
          onRegeneratePreview={() => {
            if (offerCandidate) generateContractPreview(offerCandidate.id, offerVariables);
          }}
          onApproveArtifact={handleApproveArtifact}
          onSendOfferEmail={handleSendOfferEmail}
          onDispatchAppointment={handleDispatchAppointment}
          onExecuteContract={handleExecuteContract}
        />
      </div>
    </div>
  );
}

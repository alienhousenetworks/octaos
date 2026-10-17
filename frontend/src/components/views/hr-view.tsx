'use client';

import { notify, confirmAction } from '@/lib/notify';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import {
  Briefcase,
  Search,
  Mail,
  Calendar,
  Loader2,
  Bot,
  Plus,
  Filter,
  Upload,
  FolderUp,
  Check,
  X,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Award,
  Sparkles,
  ExternalLink,
  Printer,
  Send,
  Users,
  Eye,
  SlidersHorizontal,
  ChevronDown,
  Trash2,
  Phone,
  FileCheck,
  Table,
  Download,
  FileSpreadsheet,
  ArrowUpDown,
  Copy,
  MapPin,
  Edit,
  Save
} from 'lucide-react';

interface HRViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
}

interface StagedFile {
  id: string;
  file: File;
  selected: boolean;
  name: string;
  sizeFormatted: string;
  type: string;
}

export default function HRView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
}: HRViewProps) {
  // Main state
  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [hrRole, setHrRole] = useState('Senior Full Stack Engineer');
  const [hrRequirements, setHrRequirements] = useState('Python, FastAPI, React, TypeScript, PostgreSQL, Docker, 3+ years experience');
  const [hrSalary, setHrSalary] = useState('$130,000/year');
  const [hrProvider, setHrProvider] = useState('auto');
  const [hrModel, setHrModel] = useState('');
  
  // UI Tabs & Filters
  const [activeTab, setActiveTab] = useState<'leaderboard' | 'sheet' | 'upload' | 'manual'>('leaderboard');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tierFilter, setTierFilter] = useState('all'); // all, top, strong, moderate

  // Excel Export & Import State
  const [exportingExcel, setExportingExcel] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importingExcel, setImportingExcel] = useState(false);
  const excelFileInputRef = useRef<HTMLInputElement>(null);

  // Row-wise Selection & Batch Delete State for Extraction Sheet
  const [selectedSheetCandidateIds, setSelectedSheetCandidateIds] = useState<string[]>([]);
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);

  // Staged Files for Batch/Folder upload
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [uploadPercent, setUploadPercent] = useState<number>(0);
  const [currentProcessingFile, setCurrentProcessingFile] = useState<string>('');
  const [ingestionLogs, setIngestionLogs] = useState<string[]>([]);
  const [activeJob, setActiveJob] = useState<any | null>(null);
  const [showLogsDrawer, setShowLogsDrawer] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  // Interview modal state
  const [interviewCandidate, setInterviewCandidate] = useState<any | null>(null);
  const [interviewDate, setInterviewDate] = useState<string>('');
  const [interviewTime, setInterviewTime] = useState<string>('11:00 AM');
  const [interviewRound, setInterviewRound] = useState<string>('Technical System Design');
  const [meetingLink, setMeetingLink] = useState<string>('https://meet.google.com/octa-interview');
  const [interviewerName, setInterviewerName] = useState<string>('Engineering Hiring Lead');
  const [interviewNotes, setInterviewNotes] = useState<string>('');
  const [interviewSending, setInterviewSending] = useState<boolean>(false);

  // Offer Letter & Contract Studio modal state
  const [offerCandidate, setOfferCandidate] = useState<any | null>(null);
  const [contractTemplates, setContractTemplates] = useState<any[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('full_time_standard');
  const [offerVariables, setOfferVariables] = useState<Record<string, any>>({});
  const [offerPreviewHtml, setOfferPreviewHtml] = useState<string>('');
  const [contractGenerating, setContractGenerating] = useState<boolean>(false);
  const [offerSending, setOfferSending] = useState<boolean>(false);

  // Manual candidate addition modal
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
  // Candidate edit modal state for Extraction Sheet
  const [editingCandidate, setEditingCandidate] = useState<any | null>(null);
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

  useEffect(() => {
    if (token) {
      fetchCandidates();
      fetchContractTemplates();
      checkIngestionJobStatus();
    }
  }, [token]);

  // Check ongoing or last active ingestion job from database so state persists across page refresh
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
            // Poll until completed
            setTimeout(() => {
              checkIngestionJobStatus();
            }, 1500);
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
      console.error("Error checking ingestion job status:", e);
    }
  };

  // Fetch all candidates
  const fetchCandidates = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/`);
      if (res.ok) {
        const data = await res.json();
        // Sort candidates by rank or composite score descending
        const sorted = data.sort((a: any, b: any) => {
          const scoreA = a.scorecard?.composite_score ?? a.scorecard?.match_score ?? 0;
          const scoreB = b.scorecard?.composite_score ?? b.scorecard?.match_score ?? 0;
          return scoreB - scoreA;
        });
        setCandidates(sorted);
      }
    } catch (e) {
      console.error("Error fetching candidates:", e);
    }
  };

  // Fetch available contract templates
  const fetchContractTemplates = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/contract-templates`);
      if (res.ok) {
        const data = await res.json();
        setContractTemplates(data);
      }
    } catch (e) {
      console.error("Error fetching contract templates:", e);
    }
  };

  // Helper to format file sizes
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Handle file addition to staging
  const handleFilesAdded = (filesList: FileList | null) => {
    if (!filesList || filesList.length === 0) return;
    const newItems: StagedFile[] = [];
    const validExtensions = ['.pdf', '.docx', '.txt', '.md'];

    for (let i = 0; i < filesList.length; i++) {
      const file = filesList[i];
      const lower = file.name.toLowerCase();
      const isValid = validExtensions.some(ext => lower.endsWith(ext));
      if (!isValid) continue;

      newItems.push({
        id: `${file.name}-${file.size}-${Date.now()}-${i}`,
        file,
        selected: true,
        name: file.name,
        sizeFormatted: formatFileSize(file.size),
        type: lower.endsWith('.pdf') ? 'PDF' : lower.endsWith('.docx') ? 'DOCX' : 'TEXT'
      });
    }

    setStagedFiles(prev => [...prev, ...newItems]);
    setActiveTab('upload');
  };

  // Toggle selection for an individual staged file
  const toggleFileSelection = (id: string) => {
    setStagedFiles(prev =>
      prev.map(item => item.id === id ? { ...item, selected: !item.selected } : item)
    );
  };

  // Toggle all files in staging
  const toggleSelectAll = (select: boolean) => {
    setStagedFiles(prev => prev.map(item => ({ ...item, selected: select })));
  };

  // Remove a staged file
  const removeStagedFile = (id: string) => {
    setStagedFiles(prev => prev.filter(item => item.id !== id));
  };

  // Process batch of selected resumes
  const handleProcessBatchUpload = async () => {
    const selected = stagedFiles.filter(item => item.selected);
    if (selected.length === 0) {
      notify("Please select at least one resume from the staging queue.");
      return;
    }
    if (!hrRole || !hrRequirements) {
      notify("Please specify the target Role Title and Requirements.");
      return;
    }

    setUploadLoading(true);
    setUploadPercent(5);
    setCurrentProcessingFile(`Preparing ${selected.length} resume(s)...`);
    setIngestionLogs([
      `[${new Date().toLocaleTimeString()}] Target Role: "${hrRole}"`,
      `[${new Date().toLocaleTimeString()}] Engine: ${hrProvider.toUpperCase()} (${hrModel || 'default model'})`,
      `[${new Date().toLocaleTimeString()}] Initiating batch processing of ${selected.length} resume(s)...`
    ]);

    try {
      // Progress simulation during network upload & backend parsing
      const progressTimer = setInterval(() => {
        setUploadPercent(prev => {
          if (prev < 85) return prev + 8;
          return prev;
        });
      }, 700);

      const formData = new FormData();
      selected.forEach((item) => {
        formData.append("files", item.file);
      });
      formData.append("role", hrRole);
      formData.append("requirements", hrRequirements);
      formData.append("salary", hrSalary);
      formData.append("provider", hrProvider);
      if (hrModel) formData.append("model", hrModel);

      setUploadProgress(`Extracting text & evaluating candidates (${selected.length} resumes)...`);
      setCurrentProcessingFile(`Running ATS matching & ${hrProvider.toUpperCase()} AI analysis...`);
      setIngestionLogs(prev => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] Uploaded ${selected.length} files to server. Extracting text via PyMuPDF/python-docx...`,
        `[${new Date().toLocaleTimeString()}] Running deterministic ATS keyword scoring against requirements...`,
        `[${new Date().toLocaleTimeString()}] Invoking AI semantic evaluation (${hrProvider} / ${hrModel || 'llama-3.3-70b'})...`
      ]);

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
        const candidateNames = (data.candidates || []).map((c: any) => c.name).filter(Boolean);
        const nameListStr = candidateNames.length > 0 ? ` [${candidateNames.slice(0, 4).join(', ')}${candidateNames.length > 4 ? '...' : ''}]` : '';

        setIngestionLogs(prev => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] ✓ Successfully parsed and ranked ${data.processed_count} candidate(s)${nameListStr}`,
          `[${new Date().toLocaleTimeString()}] ✓ Extracted: Name, Mobile No, Email, Address, Skills, Projects, Experience, and OctaOS Resume Links`,
          `[${new Date().toLocaleTimeString()}] ✓ Database updated. Navigating to Extraction Sheet...`
        ]);

        notify(`Success! Ingested and ranked ${data.processed_count} candidate(s).`);
        // Remove processed files from staging
        setStagedFiles(prev => prev.filter(item => !item.selected));
        await fetchCandidates();
        await fetchData();

        // Brief delay so user sees 100% completion before switching
        setTimeout(() => {
          setActiveTab('sheet');
          setUploadLoading(false);
          setUploadPercent(0);
          setCurrentProcessingFile('');
        }, 1200);
        return;
      } else {
        const errorMsg = `[${new Date().toLocaleTimeString()}] ✗ Error: ${data.detail || 'Failed to process resumes'}`;
        setIngestionLogs(prev => [...prev, errorMsg]);
        notify(`Upload error: ${data.detail || 'Failed to process resumes'}`);
      }
    } catch (e: any) {
      console.error(e);
      const networkErrMsg = `[${new Date().toLocaleTimeString()}] ✗ Network error during resume upload: ${e.message || String(e)}`;
      setIngestionLogs(prev => [...prev, networkErrMsg]);
      notify("Network error during batch resume upload.");
    } finally {
      setUploadLoading(false);
      setUploadProgress('');
    }
  };

  // Export candidates to Excel (.xlsx)
  const handleExportExcel = async () => {
    try {
      setExportingExcel(true);
      const res = await fetchWithAuth(`${API_URL}/hr/candidates/export-excel`);
      if (!res.ok) {
        notify("Failed to export Excel spreadsheet.");
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
      notify("Candidates Excel spreadsheet exported successfully!");
    } catch (e) {
      console.error(e);
      notify("Error downloading Excel file.");
    } finally {
      setExportingExcel(false);
    }
  };

  // Import candidates from Excel (.xlsx) or CSV
  const handleImportExcel = async () => {
    if (!importFile) {
      notify("Please select an Excel (.xlsx) or CSV file to import.");
      return;
    }
    setImportingExcel(true);
    try {
      const formData = new FormData();
      formData.append("file", importFile);

      const res = await fetchWithAuth(`${API_URL}/hr/candidates/import-excel`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (res.ok) {
        notify(data.message || `Imported ${data.imported_count} candidate(s)!`);
        setIsImportModalOpen(false);
        setImportFile(null);
        if (excelFileInputRef.current) excelFileInputRef.current.value = '';
        fetchCandidates();
        fetchData();
        setActiveTab('sheet');
      } else {
        notify(`Import error: ${data.detail || 'Failed to import spreadsheet'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error importing spreadsheet.");
    } finally {
      setImportingExcel(false);
    }
  };

  // Update candidate status
  const handleUpdateCandidateStatus = async (candidateId: string, newStatus: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
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

  // Delete candidate
  const handleDeleteCandidate = async (candidateId: string) => {
    if (!(await confirmAction("Are you sure you want to delete this candidate?"))) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchCandidates();
        fetchData();
        setSelectedSheetCandidateIds(prev => prev.filter(id => id !== candidateId));
        if (selectedCandidateId === candidateId) setSelectedCandidateId(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Toggle single candidate selection in Extraction Sheet
  const toggleCandidateSelection = (candidateId: string) => {
    setSelectedSheetCandidateIds(prev =>
      prev.includes(candidateId) ? prev.filter(id => id !== candidateId) : [...prev, candidateId]
    );
  };

  // Select / Deselect all visible candidates in Extraction Sheet
  const toggleSelectAllCandidates = (selectAll: boolean) => {
    if (selectAll) {
      setSelectedSheetCandidateIds(filteredCandidates.map(c => c.id));
    } else {
      setSelectedSheetCandidateIds([]);
    }
  };

  // Delete all selected candidates (or all candidates)
  const handleBatchDeleteCandidates = async (deleteEntireList: boolean = false) => {
    const idsToDelete = deleteEntireList
      ? filteredCandidates.map(c => c.id)
      : selectedSheetCandidateIds;

    if (idsToDelete.length === 0) {
      notify("No candidates selected to delete.");
      return;
    }

    const confirmMsg = deleteEntireList
      ? `Are you sure you want to delete ALL ${idsToDelete.length} candidates from the list? This cannot be undone.`
      : `Are you sure you want to delete ${idsToDelete.length} selected candidate(s)?`;

    if (!(await confirmAction(confirmMsg))) return;

    setIsBatchDeleting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/candidates/batch-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_ids: idsToDelete })
      });
      const data = await res.json();
      if (res.ok) {
        notify(data.message || `Deleted ${idsToDelete.length} candidate(s).`);
        setSelectedSheetCandidateIds([]);
        fetchCandidates();
        fetchData();
      } else {
        notify(`Error: ${data.detail || 'Failed to delete candidates'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error during candidate batch deletion.");
    } finally {
      setIsBatchDeleting(false);
    }
  };

  // Open Interview modal
  const openInterviewModal = (candidate: any) => {
    setInterviewCandidate(candidate);
    // Suggest next weekday at 11 AM
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setInterviewDate(tomorrow.toISOString().split('T')[0]);
    setMeetingLink(`https://meet.google.com/octa-${candidate.id?.slice(0, 6)}`);
    setInterviewRound("Round 1: Technical & System Architecture");
    setInterviewerName("Lead Technical Interviewer");
    setInterviewNotes("");
  };

  // Dispatch Interview invitation email
  const handleSendInterviewEmail = async () => {
    if (!interviewCandidate || !interviewDate) {
      notify("Please provide the interview date.");
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
          custom_notes: interviewNotes,
          channel: "smtp"
        })
      });
      const data = await res.json();
      if (res.ok) {
        notify(`Interview invitation email successfully dispatched to ${interviewCandidate.name}!`);
        setInterviewCandidate(null);
        fetchCandidates();
        fetchData();
      } else {
        notify(`Error: ${data.detail || 'Failed to send interview invitation'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error sending interview email.");
    } finally {
      setInterviewSending(false);
    }
  };

  // Open Offer Letter & Contract Studio modal
  const openOfferModal = async (candidate: any) => {
    setOfferCandidate(candidate);
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 14);

    const initialVars = {
      candidate_name: candidate.name,
      candidate_email: candidate.email,
      candidate_address: "San Francisco, CA",
      job_title: candidate.role,
      department: "Engineering",
      employment_type: "Full-Time Permanent",
      start_date: tomorrow.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }),
      salary_amount: candidate.scorecard?.salary_expectation?.replace(/[^0-9]/g, '') || "130,000",
      salary_currency: "USD",
      work_mode: "Remote (Global)",
      reporting_manager: "VP of Engineering",
      probation_months: "3",
      notice_period_days: "30",
      company_name: "OctaOS Technologies Inc.",
      company_address: "100 Innovation Way, Suite 400, Tech Park",
      signatory_name: "Alex Vance",
      signatory_title: "Head of People & Operations"
    };
    setOfferVariables(initialVars);
    setSelectedTemplateId('full_time_standard');
    await generateContractPreview(candidate.id, 'full_time_standard', initialVars);
  };

  // Generate live contract preview
  const generateContractPreview = async (candidateId: string, templateId: string, vars: Record<string, any>) => {
    setContractGenerating(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}/generate-offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          variables: vars
        })
      });
      const data = await res.json();
      if (res.ok && data.document) {
        setOfferPreviewHtml(data.document.html);
      }
    } catch (e) {
      console.error("Failed to generate contract preview:", e);
    } finally {
      setContractGenerating(false);
    }
  };

  // Dispatch official offer letter & contract email
  const handleSendOfferEmail = async () => {
    if (!offerCandidate) return;
    setOfferSending(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${offerCandidate.id}/send-offer-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: selectedTemplateId,
          variables: offerVariables,
          channel: "smtp"
        })
      });
      const data = await res.json();
      if (res.ok) {
        notify(`Offer letter and employment contract successfully delivered to ${offerCandidate.name}!`);
        setOfferCandidate(null);
        fetchCandidates();
        fetchData();
      } else {
        notify(`Error: ${data.detail || 'Failed to dispatch offer'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error sending offer email.");
    } finally {
      setOfferSending(false);
    }
  };

  // Add Manual Candidate
  const handleAddManualCandidate = async () => {
    if (!manualName || !manualEmail || !manualRole) {
      notify("Please fill in Name, Email, and Role.");
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
            skills: manualSkills ? manualSkills.split(',').map(s => s.trim()).filter(Boolean) : [],
            matched_skills: manualSkills ? manualSkills.split(',').map(s => s.trim()).filter(Boolean) : [],
            missing_skills: [],
            experience_years: parseInt(manualExperience) || 3,
            experience_summary: manualExperience ? `${manualExperience} of professional experience.` : 'Manually added candidate.',
            requirements_match: manualExtra || 'Manually verified candidate profile.',
            salary_expectation: manualBudget || '$120,000/year',
            phone_number: manualPhone || '',
            recommendation: 'Recommended'
          }
        })
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
        notify("Candidate added successfully!");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setManualAdding(false);
    }
  };

  // Open Edit Candidate Modal
  const openEditCandidateModal = (candidate: any) => {
    setEditingCandidate(candidate);
    const sc = candidate.scorecard || {};
    setEditName(candidate.name || '');
    setEditEmail(candidate.email || '');
    setEditRole(candidate.role || '');
    setEditStatus(candidate.status || 'sourced');
    setEditPhone(sc.phone_number || sc.phone || '');
    setEditAddress(sc.address || '');
    setEditSkills(Array.isArray(sc.skills) ? sc.skills.join(', ') : (sc.skills || ''));
    setEditProjects(Array.isArray(sc.projects) ? sc.projects.join('; ') : (sc.projects || ''));
    setEditExperienceYears(sc.experience_years !== undefined ? String(sc.experience_years) : '');
    setEditExperienceSummary(sc.experience_summary || '');
    setEditResumeLink(sc.resume_link || '');
    setEditExtraRemarks(sc.extra_remarks || sc.fit_verdict || sc.recommendation || '');
  };

  // Save Edited Candidate
  const handleSaveEditedCandidate = async () => {
    if (!editingCandidate) return;
    setSavingEdit(true);
    try {
      const skillsArray = editSkills.split(',').map(s => s.trim()).filter(Boolean);
      const projectsArray = editProjects ? editProjects.split(';').map(p => p.trim()).filter(Boolean) : [];

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
          extra_remarks: editExtraRemarks
        })
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
      console.error("Error updating candidate:", e);
      notify("Network error updating candidate.");
    } finally {
      setSavingEdit(false);
    }
  };

  // Filtered Candidates computation
  const filteredCandidates = candidates.filter(c => {
    const matchesSearch =
      (c.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.email || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.role || '').toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;

    const score = c.scorecard?.composite_score ?? c.scorecard?.match_score ?? 0;
    let matchesTier = true;
    if (tierFilter === 'top') matchesTier = score >= 85;
    else if (tierFilter === 'strong') matchesTier = score >= 70 && score < 85;
    else if (tierFilter === 'moderate') matchesTier = score < 70;

    return matchesSearch && matchesStatus && matchesTier;
  });

  const selectedCount = stagedFiles.filter(f => f.selected).length;

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight flex items-center gap-3">
            <span className="p-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Briefcase className="h-7 w-7" />
            </span>
            Enterprise HR & ATS Recruiting Suite
          </h1>
          <p className="text-gray-400 mt-1.5 text-sm">
            Zero-cost local deterministic resume parsing, dual-engine ATS & semantic ranking, automated interview scheduling, and dynamic offer letter generation.
          </p>
        </div>

        {/* Global Controls & Add Candidate */}
        <div className="flex items-center gap-3">
          <Button
            variant={activeTab === 'upload' ? 'default' : 'outline'}
            onClick={() => setActiveTab('upload')}
            className={`rounded-xl h-10 px-4 font-semibold text-xs flex items-center gap-2 ${
 activeTab === 'upload' ? 'bg-amber-500 hover:bg-amber-600 text-black font-bold' : 'border-gray-800 text-gray-300 hover:bg-gray-900'
 }`}
          >
            <Upload className="h-4 w-4" />
            Resume Ingestion ({stagedFiles.length})
          </Button>

          <Button
            variant={activeTab === 'sheet' ? 'default' : 'outline'}
            onClick={() => setActiveTab('sheet')}
            className={`rounded-xl h-10 px-4 font-semibold text-xs flex items-center gap-2 ${
              activeTab === 'sheet' ? 'bg-amber-500 hover:bg-amber-600 text-black font-bold shadow-md shadow-amber-500/20' : 'border-gray-800 text-gray-300 hover:bg-gray-900'
            }`}
          >
            <Table className="h-4 w-4" />
            Extraction Sheet ({candidates.length})
          </Button>

          <Button
            variant={activeTab === 'leaderboard' ? 'default' : 'outline'}
            onClick={() => setActiveTab('leaderboard')}
            className={`rounded-xl h-10 px-4 font-semibold text-xs flex items-center gap-2 ${
              activeTab === 'leaderboard' ? 'bg-amber-500 hover:bg-amber-600 text-black font-bold' : 'border-gray-800 text-gray-300 hover:bg-gray-900'
            }`}
          >
            <Award className="h-4 w-4" />
            Ranked Leaderboard ({candidates.length})
          </Button>

          {/* Import Excel Dialog */}
          <Dialog open={isImportModalOpen} onOpenChange={setIsImportModalOpen}>
            <DialogTrigger
              render={
                <Button className="h-10 bg-gray-900 hover:bg-gray-800 text-white border border-gray-800 rounded-xl px-3 flex items-center gap-1.5 text-xs font-semibold" />
              }
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" /> Import Excel
            </DialogTrigger>
            <DialogContent className="bg-gray-950 border-gray-800 text-white sm:max-w-[480px] rounded-3xl">
              <DialogHeader>
                <DialogTitle className="text-lg font-bold flex items-center gap-2">
                  <FileSpreadsheet className="h-5 w-5 text-emerald-400" />
                  Import Candidates Spreadsheet (.xlsx / .csv)
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-3">
                <p className="text-xs text-gray-400">
                  Upload an existing spreadsheet containing candidate details (Name, Mobile No, Email, Address, Skills, Projects, Experience, Resume Link, Remarks). Columns will be automatically mapped.
                </p>
                <div
                  onClick={() => excelFileInputRef.current?.click()}
                  className="border-2 border-dashed border-gray-800 hover:border-emerald-500/50 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-gray-900/40"
                >
                  <FileSpreadsheet className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                  <p className="text-xs font-semibold text-white">
                    {importFile ? importFile.name : 'Click to select Excel (.xlsx) or CSV file'}
                  </p>
                  <p className="text-[11px] text-gray-500 mt-1">Supports standard .xlsx and .csv spreadsheets</p>
                  <input
                    ref={excelFileInputRef}
                    type="file"
                    accept=".xlsx,.csv"
                    className="hidden"
                    onChange={e => {
                      if (e.target.files && e.target.files[0]) {
                        setImportFile(e.target.files[0]);
                      }
                    }}
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setIsImportModalOpen(false);
                      setImportFile(null);
                    }}
                    className="text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleImportExcel}
                    disabled={!importFile || importingExcel}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl px-4"
                  >
                    {importingExcel ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Importing...
                      </span>
                    ) : (
                      'Upload & Import Sheet'
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          {/* Manual Add Dialog */}
          <Dialog open={isManualAddOpen} onOpenChange={setIsManualAddOpen}>
            <DialogTrigger
              render={
                <Button className="h-10 bg-gray-900 hover:bg-gray-800 text-white border border-gray-800 rounded-xl px-3 flex items-center gap-1.5 text-xs font-semibold" />
              }
            >
              <Plus size={15} /> Add Manual
            </DialogTrigger>
            <DialogContent className="bg-gray-950 border-gray-800 text-white sm:max-w-[500px] max-h-[85vh] overflow-y-auto rounded-3xl">
              <DialogHeader>
                <DialogTitle className="text-lg font-bold">Add Candidate Manually</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Full Name *</label>
                    <Input placeholder="John Doe" value={manualName} onChange={e => setManualName(e.target.value)} className="bg-gray-900 border-gray-800 text-white rounded-xl" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Email Address *</label>
                    <Input placeholder="john@example.com" type="email" value={manualEmail} onChange={e => setManualEmail(e.target.value)} className="bg-gray-900 border-gray-800 text-white rounded-xl" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Role *</label>
                    <Input placeholder="Senior Backend Engineer" value={manualRole} onChange={e => setManualRole(e.target.value)} className="bg-gray-900 border-gray-800 text-white rounded-xl" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Phone</label>
                    <Input placeholder="+1 (555) 123-4567" value={manualPhone} onChange={e => setManualPhone(e.target.value)} className="bg-gray-900 border-gray-800 text-white rounded-xl" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Skills (comma separated)</label>
                  <Input placeholder="Python, FastAPI, Docker, AWS" value={manualSkills} onChange={e => setManualSkills(e.target.value)} className="bg-gray-900 border-gray-800 text-white rounded-xl" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Experience (years)</label>
                    <Input placeholder="5" value={manualExperience} onChange={e => setManualExperience(e.target.value)} className="bg-gray-900 border-gray-800 text-white rounded-xl" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Expected Salary</label>
                    <Input placeholder="$130,000/year" value={manualBudget} onChange={e => setManualBudget(e.target.value)} className="bg-gray-900 border-gray-800 text-white rounded-xl" />
                  </div>
                </div>
                <Button onClick={handleAddManualCandidate} disabled={manualAdding || !manualName || !manualEmail || !manualRole} className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold rounded-xl mt-2">
                  {manualAdding ? 'Saving...' : 'Save Candidate'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* PERSISTENT RUNNING / COMPLETED JOB BANNER (Visible on all tabs) */}
      {(uploadLoading || (activeJob && (activeJob.status === 'running' || activeJob.status === 'completed'))) && (
        <Card className={`glass-panel border rounded-3xl p-4 shadow-2xl transition-all animate-in fade-in slide-in-from-top-2 ${
          activeJob?.status === 'failed' ? 'border-rose-500/40 bg-rose-950/20' :
          uploadLoading || activeJob?.status === 'running' ? 'border-amber-500/40 bg-amber-950/20' :
          'border-emerald-500/30 bg-emerald-950/20'
        }`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className={`p-2.5 rounded-2xl flex-shrink-0 ${
                activeJob?.status === 'failed' ? 'bg-rose-500/20 text-rose-400' :
                uploadLoading || activeJob?.status === 'running' ? 'bg-amber-500/20 text-amber-400 animate-pulse' :
                'bg-emerald-500/20 text-emerald-400'
              }`}>
                {uploadLoading || activeJob?.status === 'running' ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : activeJob?.status === 'failed' ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Sparkles className="h-5 w-5" />
                )}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-white">
                    {uploadLoading || activeJob?.status === 'running'
                      ? `Ongoing Resume Ingestion for "${activeJob?.role || hrRole}"`
                      : `Resume Ingestion Completed for "${activeJob?.role || hrRole}"`}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                    uploadLoading || activeJob?.status === 'running'
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                  }`}>
                    {uploadLoading || activeJob?.status === 'running' ? 'PROCESSING' : 'COMPLETED'}
                  </span>
                </div>
                <p className="text-xs text-gray-400 truncate mt-0.5">
                  {currentProcessingFile || activeJob?.current_file || `${activeJob?.processed_files || 0}/${activeJob?.total_files || 0} files parsed`}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {(uploadLoading || activeJob?.status === 'running') && (
                <div className="w-36 md:w-48 space-y-1">
                  <div className="flex justify-between text-[11px] font-mono text-gray-400">
                    <span>Progress</span>
                    <span className="font-bold text-amber-400">{uploadPercent}%</span>
                  </div>
                  <div className="w-full bg-gray-900 rounded-full h-2 overflow-hidden border border-gray-800">
                    <div
                      className="bg-gradient-to-r from-amber-500 to-emerald-400 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${uploadPercent}%` }}
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowLogsDrawer(!showLogsDrawer)}
                  className="rounded-xl border-gray-800 text-xs text-gray-300 hover:text-white h-9"
                >
                  <Bot className="h-3.5 w-3.5 mr-1.5 text-amber-400" />
                  {showLogsDrawer ? 'Hide Logs' : `Logs (${ingestionLogs.length})`}
                </Button>

                {activeTab !== 'upload' && (
                  <Button
                    size="sm"
                    onClick={() => setActiveTab('upload')}
                    className="rounded-xl bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs h-9"
                  >
                    View Ingestion Tab
                  </Button>
                )}
              </div>
            </div>
          </div>

          {/* Collapsible live log console in banner */}
          {showLogsDrawer && ingestionLogs.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-800/80 animate-in fade-in duration-200">
              <div className="max-h-40 overflow-y-auto space-y-1 font-mono text-[11px] p-2.5 bg-black/60 rounded-2xl border border-gray-900">
                {ingestionLogs.map((log, lIdx) => (
                  <div
                    key={lIdx}
                    className={`${
                      log.includes('✓') ? 'text-emerald-400 font-semibold' :
                      log.includes('✗') ? 'text-rose-400 font-semibold' :
                      'text-gray-300'
                    }`}
                  >
                    {log}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* TAB 1: RESUME INGESTION & STAGING ZONE */}
      {activeTab === 'upload' && (
        <div className="space-y-6 animate-in slide-in-from-top-2 duration-300">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Target Role & Sourcing Criteria */}
            <div className="lg:col-span-1 space-y-4">
              <Card className="glass-panel border-gray-800 rounded-3xl p-5 shadow-2xl space-y-4">
                <div className="flex items-center gap-2 border-b border-gray-800 pb-3">
                  <SlidersHorizontal className="h-5 w-5 text-amber-400" />
                  <h3 className="font-bold text-white text-base">ATS Target Role & Criteria</h3>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Target Role Title</label>
                  <Input
                    value={hrRole}
                    onChange={e => setHrRole(e.target.value)}
                    placeholder="e.g. Senior Software Engineer"
                    className="bg-gray-900/80 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Required Skills & Criteria</label>
                  <Textarea
                    value={hrRequirements}
                    onChange={e => setHrRequirements(e.target.value)}
                    placeholder="e.g. Python, FastAPI, React, TypeScript, Docker, PostgreSQL, 3+ years experience"
                    className="bg-gray-900/80 border-gray-800 text-white rounded-xl text-xs min-h-[110px]"
                  />
                  <p className="text-xs text-gray-500">Skills are parsed with zero token waste via local deterministic keywords.</p>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Annual Salary Budget</label>
                  <Input
                    value={hrSalary}
                    onChange={e => setHrSalary(e.target.value)}
                    placeholder="e.g. $130,000/year"
                    className="bg-gray-900/80 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>

                {/* AI Model provider */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Semantic Evaluation Engine</label>
                  <Select value={hrProvider} onValueChange={(val) => {
                    if (val) {
                      setHrProvider(val);
                      if (val === 'openrouter') setHrModel('meta-llama/llama-3.3-70b-instruct');
                      else if (val === 'groq') setHrModel('llama-3.3-70b-versatile');
                      else if (val === 'gemini') setHrModel('gemini-2.5-flash');
                      else if (val === 'openai') setHrModel('gpt-4o-mini');
                      else if (val === 'auto') setHrModel('');
                    }
                  }}>
                    <SelectTrigger className="bg-gray-900/80 border-gray-800 text-white rounded-xl text-xs h-10">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-800 text-white">
                      <SelectItem value="openrouter">OpenRouter (Meta Llama 3.3 70B Instruct)</SelectItem>
                      <SelectItem value="groq">Groq (Llama 3.3 70B Versatile - Sub-second)</SelectItem>
                      <SelectItem value="gemini">Google Gemini 2.5 Flash ($0.0001)</SelectItem>
                      <SelectItem value="openai">OpenAI GPT-4o-mini</SelectItem>
                      <SelectItem value="auto">Auto (Smart AI Gateway Router)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Process Button */}
                <Button
                  onClick={handleProcessBatchUpload}
                  disabled={uploadLoading || selectedCount === 0}
                  className="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-semibold rounded-xl h-11 shadow-lg shadow-amber-500/20 text-xs transition-all active:scale-95 disabled:opacity-50 disabled:scale-100"
                >
                  {uploadLoading ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" /> {uploadPercent}% - Processing...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4" /> Run ATS & Semantic Ranking ({selectedCount} Resumes)
                    </span>
                  )}
                </Button>

                {/* Live Progress Bar & Status Feed */}
                {uploadLoading && (
                  <div className="space-y-2 pt-2 animate-in fade-in duration-200">
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="text-gray-300 truncate max-w-[190px] font-medium">
                        {currentProcessingFile || uploadProgress}
                      </span>
                      <span className="font-mono font-bold text-amber-400">{uploadPercent}%</span>
                    </div>
                    <div className="w-full bg-gray-900 rounded-full h-2 overflow-hidden border border-gray-800">
                      <div
                        className="bg-gradient-to-r from-amber-500 to-emerald-400 h-2 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${uploadPercent}%` }}
                      />
                    </div>
                  </div>
                )}
              </Card>
            </div>

            {/* Staging Dropzone & Table */}
            <div className="lg:col-span-2 space-y-4">
              {/* Dropzone Actions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Upload Multiple Files */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="p-6 border-2 border-dashed border-gray-800 hover:border-amber-500/60 rounded-3xl bg-gray-950/40 hover:bg-gray-900/40 cursor-pointer transition-all flex flex-col items-center justify-center text-center group"
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    multiple
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={e => handleFilesAdded(e.target.files)}
                  />
                  <div className="p-3 rounded-2xl bg-amber-500/10 text-amber-400 group-hover:scale-110 transition-transform mb-3">
                    <Upload className="h-6 w-6" />
                  </div>
                  <h4 className="font-bold text-white text-sm">Upload Multiple Resumes</h4>
                  <p className="text-gray-500 text-xs mt-1">Select 5, 20, or 100+ PDF / DOCX files at once</p>
                </div>

                {/* Upload Entire Folder */}
                <div
                  onClick={() => folderInputRef.current?.click()}
                  className="p-6 border-2 border-dashed border-gray-800 hover:border-amber-500/60 rounded-3xl bg-gray-950/40 hover:bg-gray-900/40 cursor-pointer transition-all flex flex-col items-center justify-center text-center group"
                >
                  <input
                    type="file"
                    ref={folderInputRef}
                    // @ts-ignore
                    webkitdirectory=""
                    // @ts-ignore
                    directory=""
                    multiple
                    className="hidden"
                    onChange={e => handleFilesAdded(e.target.files)}
                  />
                  <div className="p-3 rounded-2xl bg-amber-500/10 text-amber-400 group-hover:scale-110 transition-transform mb-3">
                    <FolderUp className="h-6 w-6" />
                  </div>
                  <h4 className="font-bold text-white text-sm">Upload Full Resume Folder</h4>
                  <p className="text-gray-500 text-xs mt-1">Pick a folder of resumes and batch ingest all</p>
                </div>
              </div>

              {/* Staging Queue List */}
              <Card className="glass-panel border-gray-800 rounded-3xl overflow-hidden shadow-2xl">
                <div className="p-4 bg-gray-950/60 border-b border-gray-800 flex justify-between items-center flex-wrap gap-2">
                  <div className="flex items-center gap-3">
                    <h3 className="font-bold text-white text-sm flex items-center gap-2">
                      <FileText className="h-4 w-4 text-amber-400" />
                      Staging Queue ({stagedFiles.length} files detected)
                    </h3>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
                      {selectedCount} Selected for Parsing
                    </span>
                  </div>

                  {stagedFiles.length > 0 && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => toggleSelectAll(true)}
                        className="text-xs text-gray-300 hover:text-white h-8"
                      >
                        Select All
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => toggleSelectAll(false)}
                        className="text-xs text-gray-400 hover:text-white h-8"
                      >
                        Deselect All
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setStagedFiles([])}
                        className="text-xs text-rose-400 hover:text-rose-300 h-8"
                      >
                        Clear All
                      </Button>
                    </div>
                  )}
                </div>

                <div className="max-h-[380px] overflow-y-auto divide-y divide-gray-800/60">
                  {stagedFiles.length === 0 ? (
                    <div className="p-12 text-center text-gray-500 text-xs space-y-2">
                      <FileCheck className="h-8 w-8 mx-auto text-gray-600 mb-2" />
                      <p className="font-semibold text-gray-400">No resumes in staging yet</p>
                      <p>Click "Upload Multiple Resumes" or "Upload Full Resume Folder" above to stage resumes.</p>
                    </div>
                  ) : (
                    stagedFiles.map((item) => (
                      <div
                        key={item.id}
                        className={`p-3.5 flex items-center justify-between gap-3 transition-colors ${
 item.selected ? 'bg-gray-900/30' : 'bg-transparent opacity-60'
 }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <input
                            type="checkbox"
                            checked={item.selected}
                            onChange={() => toggleFileSelection(item.id)}
                            className="h-4 w-4 rounded border-gray-700 bg-gray-900 text-amber-500 focus:ring-amber-500/20 cursor-pointer"
                          />
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-lg border ${
 item.type === 'PDF' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
 item.type === 'DOCX' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
 'bg-gray-500/10 text-gray-400 border-gray-500/20'
 }`}>
                            {item.type}
                          </span>
                          <span className="text-xs font-semibold text-white truncate max-w-[280px] sm:max-w-md">
                            {item.name}
                          </span>
                        </div>

                        <div className="flex items-center gap-3">
                          <span className="text-xs text-gray-500 font-mono">{item.sizeFormatted}</span>
                          <button
                            onClick={() => removeStagedFile(item.id)}
                            className="text-gray-500 hover:text-rose-400 transition-colors p-1"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>

              {/* Live Ingestion Processing Console & Progress Logs */}
              {ingestionLogs.length > 0 && (
                <Card className="glass-panel border-gray-800 rounded-3xl p-4 bg-gray-950/70 shadow-xl space-y-2">
                  <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
                    <span className="text-xs font-bold text-amber-400 flex items-center gap-2">
                      <Bot className="h-4 w-4" /> Live Ingestion & Extraction Log
                    </span>
                    <span className="text-[11px] font-mono text-gray-500">
                      {ingestionLogs.length} events logged
                    </span>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-[11px] p-2 bg-black/40 rounded-2xl border border-gray-900">
                    {ingestionLogs.map((log, lIdx) => (
                      <div
                        key={lIdx}
                        className={`${
                          log.includes('✓') ? 'text-emerald-400 font-semibold' :
                          log.includes('✗') ? 'text-rose-400 font-semibold' :
                          'text-gray-300'
                        }`}
                      >
                        {log}
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: EXTRACTION SHEET & ROW-WISE CANDIDATE GRID */}
      {activeTab === 'sheet' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Action Bar: Search, Filters, Excel Export & Import */}
          <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search by name, email, phone, address, or skills..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-10 bg-gray-900/70 border-gray-800 text-white rounded-2xl h-11 text-xs"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Select value={statusFilter} onValueChange={val => val && setStatusFilter(val)}>
                <SelectTrigger className="bg-gray-900/70 border-gray-800 text-white rounded-xl text-xs h-10 w-36">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-800 text-white">
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="sourced">Sourced</SelectItem>
                  <SelectItem value="accepted">Accepted</SelectItem>
                  <SelectItem value="screened">Screened</SelectItem>
                  <SelectItem value="interviewed">Interviewed</SelectItem>
                  <SelectItem value="offered">Offered</SelectItem>
                  <SelectItem value="hired">Hired</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>

              {/* Delete Selected Candidates */}
              {selectedSheetCandidateIds.length > 0 && (
                <Button
                  onClick={() => handleBatchDeleteCandidates(false)}
                  disabled={isBatchDeleting}
                  className="bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-xl h-10 px-3 text-xs flex items-center gap-1.5 shadow-md shadow-rose-600/20 animate-in fade-in"
                >
                  {isBatchDeleting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                  Delete Selected ({selectedSheetCandidateIds.length})
                </Button>
              )}

              {/* Delete All Candidates Button */}
              {candidates.length > 0 && (
                <Button
                  variant="outline"
                  onClick={() => handleBatchDeleteCandidates(true)}
                  disabled={isBatchDeleting}
                  className="border-rose-900/60 hover:bg-rose-950/40 text-rose-400 hover:text-rose-300 rounded-xl h-10 px-3 text-xs font-semibold flex items-center gap-1.5"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete All ({candidates.length})
                </Button>
              )}

              {/* Export to Excel Button */}
              <Button
                onClick={handleExportExcel}
                disabled={exportingExcel || candidates.length === 0}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl h-10 px-4 text-xs flex items-center gap-1.5 shadow-md shadow-emerald-600/20"
              >
                {exportingExcel ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Export to Excel (.xlsx)
              </Button>

              {/* Import Excel Trigger Button */}
              <Button
                variant="outline"
                onClick={() => setIsImportModalOpen(true)}
                className="border-gray-800 text-gray-300 hover:bg-gray-900 hover:text-white rounded-xl h-10 px-3 text-xs font-semibold flex items-center gap-1.5"
              >
                <FileSpreadsheet className="h-4 w-4 text-emerald-400" />
                Import Excel
              </Button>
            </div>
          </div>

          {/* Row-wise Extraction Details Table */}
          <Card className="glass-panel border-gray-800 overflow-hidden rounded-3xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[1100px]">
                <thead>
                  <tr className="border-b border-gray-800 bg-gray-950/70 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
                    <th className="py-3.5 px-3 w-10 text-center">
                      <input
                        type="checkbox"
                        checked={
                          filteredCandidates.length > 0 &&
                          selectedSheetCandidateIds.length === filteredCandidates.length
                        }
                        onChange={e => toggleSelectAllCandidates(e.target.checked)}
                        className="h-4 w-4 rounded border-gray-700 bg-gray-900 text-amber-500 focus:ring-amber-500/20 cursor-pointer"
                        title="Select All"
                      />
                    </th>
                    <th className="py-3.5 px-3 w-12 text-center">#</th>
                    <th className="py-3.5 px-4">Candidate & Status</th>
                    <th className="py-3.5 px-4">Mobile No</th>
                    <th className="py-3.5 px-4">Email</th>
                    <th className="py-3.5 px-4">Address</th>
                    <th className="py-3.5 px-4">Skills</th>
                    <th className="py-3.5 px-4">Projects</th>
                    <th className="py-3.5 px-4">Experience</th>
                    <th className="py-3.5 px-4 text-center">Resume Link</th>
                    <th className="py-3.5 px-4">Extra Remarks</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 text-xs">
                  {filteredCandidates.length === 0 ? (
                    <tr>
                      <td colSpan={12} className="py-16 text-center text-gray-500">
                        <FileCheck className="h-8 w-8 mx-auto text-gray-600 mb-2" />
                        <p className="font-semibold text-gray-400">No candidate records match your query</p>
                        <p className="text-[11px] mt-1">Ingest resumes or click &quot;Import Excel&quot; to load candidate records.</p>
                      </td>
                    </tr>
                  ) : (
                    filteredCandidates.map((cand, idx) => {
                      const sc = cand.scorecard || {};
                      const phone = sc.phone_number || sc.phone || 'N/A';
                      const addr = sc.address || 'Not specified';
                      const skills = sc.skills || [];
                      const projects = sc.projects || [];
                      const expYears = sc.experience_years ?? 0;
                      const expSummary = sc.experience_summary || '';
                      const resumeLink = sc.resume_link || '';
                      const remarks = sc.extra_remarks || sc.fit_verdict || sc.recommendation || 'Verified candidate profile';
                      const matchScore = sc.composite_score ?? sc.match_score ?? 65;
                      const isRowSelected = selectedSheetCandidateIds.includes(cand.id);

                      return (
                        <tr
                          key={cand.id}
                          className={`transition-colors group ${
                            isRowSelected ? 'bg-amber-500/10' : 'hover:bg-gray-900/40'
                          }`}
                        >
                          {/* Checkbox */}
                          <td className="py-3.5 px-3 text-center">
                            <input
                              type="checkbox"
                              checked={isRowSelected}
                              onChange={() => toggleCandidateSelection(cand.id)}
                              className="h-4 w-4 rounded border-gray-700 bg-gray-900 text-amber-500 focus:ring-amber-500/20 cursor-pointer"
                            />
                          </td>

                          {/* Rank */}
                          <td className="py-3.5 px-3 font-mono font-bold text-gray-500 text-center">
                            {sc.rank || idx + 1}
                          </td>

                          {/* Candidate & Status */}
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-white flex items-center gap-2">
                              <span>{cand.name}</span>
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                                cand.status === 'hired' ? 'bg-teal-500/10 text-teal-400 border-teal-500/20' :
                                cand.status === 'offered' ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' :
                                cand.status === 'interviewed' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
                                cand.status === 'accepted' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                cand.status === 'rejected' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                'bg-blue-500/10 text-blue-400 border-blue-500/20'
                              }`}>
                                {cand.status}
                              </span>
                            </div>
                            <div className="text-[11px] text-gray-400 mt-0.5">{cand.role}</div>
                          </td>

                          {/* Mobile No */}
                          <td className="py-3.5 px-4 font-mono text-gray-300">
                            {phone !== 'N/A' ? (
                              <div className="flex items-center gap-1.5">
                                <span className="truncate max-w-[130px]">{phone}</span>
                                <button
                                  title="Copy phone number"
                                  onClick={() => {
                                    navigator.clipboard.writeText(phone);
                                    notify(`Copied ${phone} to clipboard`);
                                  }}
                                  className="text-gray-500 hover:text-white p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                  <Copy className="h-3 w-3" />
                                </button>
                              </div>
                            ) : (
                              <span className="text-gray-600 italic">N/A</span>
                            )}
                          </td>

                          {/* Email */}
                          <td className="py-3.5 px-4 font-mono text-gray-300">
                            {cand.email && cand.email !== 'N/A' && !cand.email.includes('@applicant.internal') ? (
                              <a
                                href={`mailto:${cand.email}`}
                                className="text-amber-400/90 hover:text-amber-300 hover:underline truncate max-w-[160px] block"
                              >
                                {cand.email}
                              </a>
                            ) : (
                              <span className="text-gray-600 italic">N/A</span>
                            )}
                          </td>

                          {/* Address */}
                          <td className="py-3.5 px-4 text-gray-300">
                            <div className="flex items-center gap-1 text-[11px] max-w-[140px] truncate" title={addr}>
                              <MapPin className="h-3 w-3 text-gray-500 shrink-0" />
                              <span className="truncate">{addr}</span>
                            </div>
                          </td>

                          {/* Skills */}
                          <td className="py-3.5 px-4">
                            <div className="flex flex-wrap gap-1 max-w-[190px]">
                              {skills.slice(0, 3).map((s: string) => (
                                <span key={s} className="px-1.5 py-0.5 rounded bg-gray-900 border border-gray-800 text-[10px] text-gray-300 font-medium">
                                  {s}
                                </span>
                              ))}
                              {skills.length > 3 && (
                                <span className="px-1.5 py-0.5 rounded bg-gray-900/50 border border-gray-800 text-[10px] text-gray-500">
                                  +{skills.length - 3}
                                </span>
                              )}
                              {skills.length === 0 && <span className="text-gray-600 italic text-[11px]">N/A</span>}
                            </div>
                          </td>

                          {/* Projects */}
                          <td className="py-3.5 px-4">
                            <div className="max-w-[180px] text-[11px] text-gray-300 line-clamp-2" title={Array.isArray(projects) ? projects.join(', ') : String(projects)}>
                              {Array.isArray(projects) && projects.length > 0 ? (
                                projects.slice(0, 2).map((p: string, i: number) => (
                                  <div key={i} className="truncate">• {p}</div>
                                ))
                              ) : (
                                <span className="text-gray-600 italic">None listed</span>
                              )}
                            </div>
                          </td>

                          {/* Experience */}
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-white text-[11px]">{expYears} yrs exp</div>
                            {expSummary && (
                              <div className="text-[10px] text-gray-400 truncate max-w-[130px]" title={expSummary}>
                                {expSummary}
                              </div>
                            )}
                          </td>

                          {/* Resume Link */}
                          <td className="py-3.5 px-4 text-center">
                            {resumeLink ? (
                              <a
                                href={resumeLink.startsWith('http') ? resumeLink : `${API_URL.replace('/api/v1', '')}${resumeLink}`}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[11px] font-semibold transition-colors"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Resume
                              </a>
                            ) : (
                              <span className="text-gray-600 text-[11px] italic">Not attached</span>
                            )}
                          </td>

                          {/* Extra Remarks */}
                          <td className="py-3.5 px-4">
                            <div className="max-w-[200px]">
                              <div className="text-[11px] text-gray-300 line-clamp-2" title={remarks}>
                                {remarks}
                              </div>
                              <div className="mt-1 flex items-center gap-1.5">
                                <span className="text-[10px] font-bold text-amber-400 font-mono">{matchScore}% match</span>
                              </div>
                            </div>
                          </td>

                          {/* Actions */}
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {cand.status === 'sourced' && (
                                <Button
                                  size="sm"
                                  onClick={() => handleUpdateCandidateStatus(cand.id, 'accepted')}
                                  className="h-7 px-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold"
                                >
                                  Approve
                                </Button>
                              )}
                              {cand.status === 'accepted' && (
                                <Button
                                  size="sm"
                                  onClick={() => openInterviewModal(cand)}
                                  className="h-7 px-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-bold"
                                >
                                  Interview
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openEditCandidateModal(cand)}
                                title="Edit Candidate Details"
                                className="h-7 w-7 p-0 text-gray-400 hover:text-amber-400 rounded-lg hover:bg-amber-500/10"
                              >
                                <Edit className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteCandidate(cand.id)}
                                title="Delete Candidate"
                                className="h-7 w-7 p-0 text-gray-500 hover:text-rose-400 rounded-lg hover:bg-rose-500/10"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
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
      )}

      {/* TAB 2: CANDIDATE LEADERBOARD & PEOPLE RANKING */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Search, Filter & Quick Stats Bar */}
          <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search candidates by name, email, or role..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-10 bg-gray-900/70 border-gray-800 text-white rounded-2xl h-11 text-xs"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Status Filter */}
              <Select value={statusFilter} onValueChange={val => val && setStatusFilter(val)}>
                <SelectTrigger className="bg-gray-900/70 border-gray-800 text-white rounded-xl text-xs h-10 w-36">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-800 text-white">
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="sourced">Sourced</SelectItem>
                  <SelectItem value="accepted">Accepted</SelectItem>
                  <SelectItem value="screened">Screened</SelectItem>
                  <SelectItem value="interviewed">Interviewed</SelectItem>
                  <SelectItem value="offered">Offered</SelectItem>
                  <SelectItem value="hired">Hired</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>

              {/* Score Tier Filter */}
              <Select value={tierFilter} onValueChange={val => val && setTierFilter(val)}>
                <SelectTrigger className="bg-gray-900/70 border-gray-800 text-white rounded-xl text-xs h-10 w-40">
                  <SelectValue placeholder="All Score Tiers" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-800 text-white">
                  <SelectItem value="all">All Score Tiers</SelectItem>
                  <SelectItem value="top">Top Match (85%+)</SelectItem>
                  <SelectItem value="strong">Strong Match (70-84%)</SelectItem>
                  <SelectItem value="moderate">Moderate Match (&lt;70%)</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                onClick={() => setActiveTab('upload')}
                className="border-amber-500/40 text-amber-400 hover:bg-amber-500/10 rounded-xl h-10 px-3 text-xs font-bold flex items-center gap-1.5"
              >
                <Upload className="h-3.5 w-3.5" /> Ingest More Resumes
              </Button>
            </div>
          </div>

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-2xl bg-gray-900/40 border border-gray-800">
              <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">Total Ranked</div>
              <div className="text-xl font-semibold text-white mt-1">{candidates.length}</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-blue-500/5 border border-blue-500/20">
              <div className="text-xs font-bold text-blue-400 uppercase tracking-wider">Sourced (New)</div>
              <div className="text-xl font-semibold text-blue-300 mt-1">{candidates.filter(c => c.status === 'sourced').length}</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-emerald-500/5 border border-emerald-500/20">
              <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Accepted / Screened</div>
              <div className="text-xl font-semibold text-emerald-300 mt-1">
                {candidates.filter(c => ['accepted', 'screened'].includes(c.status)).length}
              </div>
            </div>
            <div className="p-3.5 rounded-2xl bg-purple-500/5 border border-purple-500/20">
              <div className="text-xs font-bold text-purple-400 uppercase tracking-wider">Interviewed</div>
              <div className="text-xl font-semibold text-purple-300 mt-1">{candidates.filter(c => c.status === 'interviewed').length}</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-indigo-500/5 border border-indigo-500/20">
              <div className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Offered</div>
              <div className="text-xl font-semibold text-indigo-300 mt-1">{candidates.filter(c => c.status === 'offered').length}</div>
            </div>
            <div className="p-3.5 rounded-2xl bg-teal-500/5 border border-teal-500/20">
              <div className="text-xs font-bold text-teal-400 uppercase tracking-wider">Hired</div>
              <div className="text-xl font-semibold text-teal-300 mt-1">{candidates.filter(c => c.status === 'hired').length}</div>
            </div>
          </div>

          {/* Candidate Leaderboard List */}
          {filteredCandidates.length === 0 ? (
            <Card className="glass-panel border-dashed border-gray-800 p-12 text-center rounded-3xl min-h-[350px] flex flex-col items-center justify-center space-y-3">
              <div className="text-4xl">👥</div>
              <h3 className="text-base font-bold text-white">No candidates found</h3>
              <p className="text-xs text-gray-500 max-w-sm">
                Try clearing your search or filters, or switch to the Resume Ingestion tab to parse resumes.
              </p>
              <Button
                onClick={() => setActiveTab('upload')}
                className="bg-amber-500 hover:bg-amber-600 text-black font-bold text-xs rounded-xl h-9 px-4 mt-2"
              >
                Upload & Rank Resumes Now
              </Button>
            </Card>
          ) : (
            <div className="space-y-4">
              {filteredCandidates.map((candidate, index) => {
                const scorecard = candidate.scorecard || {};
                const rank = scorecard.rank || index + 1;
                const compositeScore = scorecard.composite_score ?? scorecard.match_score ?? 60;
                const atsScore = scorecard.ats_score ?? compositeScore;
                const semanticScore = scorecard.semantic_score ?? compositeScore;
                const skills = scorecard.skills || [];
                const matchedSkills = scorecard.matched_skills || [];
                const missingSkills = scorecard.missing_skills || [];
                const experienceYears = scorecard.experience_years ?? 0;
                const summary = scorecard.experience_summary || '';
                const recommendation = scorecard.recommendation || (compositeScore >= 80 ? 'Strong Hire' : compositeScore >= 70 ? 'Recommended' : 'Consider');
                const isSelected = selectedCandidateId === candidate.id;

                // Status badges
                let statusBadgeColor = 'bg-gray-500/10 text-gray-400 border-gray-500/20';
                if (candidate.status === 'sourced') statusBadgeColor = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                if (candidate.status === 'accepted') statusBadgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
                if (candidate.status === 'screened') statusBadgeColor = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
                if (candidate.status === 'interviewed') statusBadgeColor = 'bg-purple-500/10 text-purple-400 border-purple-500/20';
                if (candidate.status === 'offered') statusBadgeColor = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
                if (candidate.status === 'hired') statusBadgeColor = 'bg-teal-500/10 text-teal-400 border-teal-500/20';
                if (candidate.status === 'rejected') statusBadgeColor = 'bg-rose-500/10 text-rose-400 border-rose-500/20';

                // Rank badge design
                const isTopThree = rank <= 3;
                const rankBadgeClass =
                  rank === 1 ? 'bg-gradient-to-br from-amber-400 to-yellow-600 text-black shadow-lg shadow-amber-500/30 font-semibold' :
                  rank === 2 ? 'bg-gradient-to-br from-slate-200 to-slate-400 text-black shadow-lg shadow-slate-400/20 font-semibold' :
                  rank === 3 ? 'bg-gradient-to-br from-amber-700 to-amber-900 text-amber-100 shadow-lg shadow-amber-800/20 font-semibold' :
                  'bg-gray-900 text-gray-400 border border-gray-800 font-bold';

                return (
                  <Card
                    key={candidate.id}
                    className={`glass-panel border-gray-800/80 hover:border-amber-500/40 transition-all rounded-3xl overflow-hidden shadow-xl ${
 isSelected ? 'ring-2 ring-amber-500' : ''
 }`}
                  >
                    {/* Header Row */}
                    <div className="p-5 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-gray-950/40 border-b border-gray-800">
                      <div className="flex items-center gap-4">
                        {/* Rank Badge */}
                        <div className={`h-11 w-11 rounded-2xl flex flex-col items-center justify-center flex-shrink-0 text-xs ${rankBadgeClass}`}>
                          <span className="text-xs leading-tight opacity-75">RANK</span>
                          <span className="text-sm font-semibold leading-tight">#{rank}</span>
                        </div>

                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="text-lg font-bold text-white tracking-tight">{candidate.name}</h3>
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase border ${statusBadgeColor}`}>
                              {candidate.status}
                            </span>
                            <span className={`px-2 py-0.5 rounded-md text-xs font-bold border ${
 recommendation === 'Strong Hire' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
 recommendation === 'Recommended' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
 'bg-amber-500/10 text-amber-400 border-amber-500/20'
 }`}>
                              ★ {recommendation}
                            </span>
                          </div>

                          <p className="text-xs text-gray-400 mt-1 flex items-center gap-2 flex-wrap">
                            <span>
                              {candidate.email && candidate.email !== 'N/A' && !candidate.email.includes('@applicant.internal')
                                ? candidate.email
                                : 'Email: N/A'}
                            </span>
                            {scorecard.phone_number && scorecard.phone_number !== 'N/A' && <span>• {scorecard.phone_number}</span>}
                            <span>• Target: <strong className="text-gray-200">{candidate.role}</strong></span>
                            {experienceYears > 0 && <span>• <strong>{experienceYears} yrs exp</strong></span>}
                          </p>
                        </div>
                      </div>

                      {/* Scores & Details Button */}
                      <div className="flex items-center gap-4 w-full lg:w-auto justify-between lg:justify-end">
                        {/* Dual Score Breakdown */}
                        <div className="hidden sm:flex items-center gap-4 text-right pr-2">
                          <div>
                            <div className="text-xs text-gray-500 font-bold uppercase">ATS Keyword</div>
                            <div className="text-xs font-bold text-gray-300">{atsScore}% match</div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500 font-bold uppercase">Semantic Fit</div>
                            <div className="text-xs font-bold text-amber-400">{semanticScore}% align</div>
                          </div>
                        </div>

                        {/* Circular Composite Score indicator */}
                        <div className="relative h-12 w-12 flex items-center justify-center">
                          <svg className="w-full h-full transform -rotate-90">
                            <circle cx="24" cy="24" r="20" stroke="rgba(255,255,255,0.06)" strokeWidth="3.5" fill="transparent" />
                            <circle
                              cx="24"
                              cy="24"
                              r="20"
                              stroke={compositeScore >= 80 ? "#10b981" : compositeScore >= 70 ? "#f59e0b" : "#ef4444"}
                              strokeWidth="3.5"
                              fill="transparent"
                              strokeDasharray={2 * Math.PI * 20}
                              strokeDashoffset={2 * Math.PI * 20 * (1 - compositeScore / 100)}
                              strokeLinecap="round"
                              className="transition-all duration-700"
                            />
                          </svg>
                          <span className="absolute text-xs font-semibold text-white">{compositeScore}%</span>
                        </div>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedCandidateId(isSelected ? null : candidate.id)}
                          className="text-gray-400 hover:text-white text-xs h-9 px-3 rounded-xl border border-gray-800"
                        >
                          {isSelected ? 'Hide Details' : 'Deep Dive'}
                        </Button>
                      </div>
                    </div>

                    {/* Matched vs Missing Skills Preview Row */}
                    <div className="p-4 bg-gray-950/20 border-b border-gray-800/60 flex flex-wrap items-center gap-2 text-xs">
                      <span className="text-xs font-bold uppercase text-gray-500 mr-1">Skills Overlap:</span>
                      {matchedSkills.slice(0, 6).map((skill: string) => (
                        <span key={skill} className="px-2 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium flex items-center gap-1">
                          <Check className="h-3 w-3" /> {skill}
                        </span>
                      ))}
                      {missingSkills.slice(0, 3).map((skill: string) => (
                        <span key={skill} className="px-2 py-0.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-medium flex items-center gap-1">
                          <X className="h-3 w-3" /> {skill}
                        </span>
                      ))}
                      {matchedSkills.length === 0 && missingSkills.length === 0 && skills.slice(0, 5).map((skill: string) => (
                        <span key={skill} className="px-2 py-0.5 rounded-lg bg-gray-900 text-gray-300 border border-gray-800 text-xs">
                          {skill}
                        </span>
                      ))}
                    </div>

                    {/* Deep Dive Expanded Drawer */}
                    {isSelected && (
                      <div className="p-6 bg-gray-950/50 border-b border-gray-800 space-y-5 animate-in slide-in-from-top-2 duration-200">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                          {/* Experience Summary */}
                          <div className="md:col-span-2 space-y-2">
                            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Candidate Executive Summary</h4>
                            <p className="text-xs text-gray-300 leading-relaxed bg-gray-900/60 border border-gray-800/80 p-3.5 rounded-2xl">
                              {summary || scorecard.requirements_match || 'Candidate profile evaluated via dual ATS & semantic analyzer.'}
                            </p>
                          </div>

                          {/* Compensation & Education */}
                          <div className="space-y-3 bg-gray-900/40 border border-gray-800/80 p-4 rounded-2xl">
                            <div>
                              <div className="text-xs font-bold text-gray-500 uppercase">Education</div>
                              <div className="text-xs font-semibold text-white mt-0.5">{scorecard.education || 'Not explicitly specified'}</div>
                            </div>
                            <div>
                              <div className="text-xs font-bold text-gray-500 uppercase">Salary Expectation</div>
                              <div className="text-xs font-semibold text-white mt-0.5">{scorecard.salary_expectation || '$120,000/year'}</div>
                            </div>
                            {scorecard.linkedin && (
                              <div>
                                <div className="text-xs font-bold text-gray-500 uppercase">Social Profile</div>
                                <a href={scorecard.linkedin} target="_blank" rel="noreferrer" className="text-xs text-amber-400 hover:underline flex items-center gap-1 mt-0.5">
                                  LinkedIn Profile <ExternalLink className="h-3 w-3" />
                                </a>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Strengths and Gaps */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="p-3.5 rounded-2xl bg-emerald-950/20 border border-emerald-900/30 space-y-2">
                            <h5 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                              <CheckCircle2 className="h-3.5 w-3.5" /> Key Strengths
                            </h5>
                            <ul className="text-xs text-gray-300 space-y-1 list-disc list-inside">
                              {(scorecard.strengths || ['Strong technical alignment with core requirements']).map((s: string, i: number) => (
                                <li key={i}>{s}</li>
                              ))}
                            </ul>
                          </div>

                          <div className="p-3.5 rounded-2xl bg-rose-950/20 border border-rose-900/30 space-y-2">
                            <h5 className="text-xs font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                              <AlertTriangle className="h-3.5 w-3.5" /> Potential Gaps / Red Flags
                            </h5>
                            <ul className="text-xs text-gray-300 space-y-1 list-disc list-inside">
                              {(scorecard.gaps || ['Requires technical screen on architectural depth']).map((g: string, i: number) => (
                                <li key={i}>{g}</li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        {/* Interview Details if available */}
                        {scorecard.meeting_time && (
                          <div className="p-4 rounded-2xl bg-purple-950/20 border border-purple-900/30 space-y-2">
                            <h5 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                              <Calendar className="h-3.5 w-3.5" /> Scheduled Interview
                            </h5>
                            <div className="text-xs text-gray-300 flex flex-wrap gap-4">
                              <span><strong>Time:</strong> {scorecard.meeting_time}</span>
                              {scorecard.interview_round && <span><strong>Round:</strong> {scorecard.interview_round}</span>}
                              {scorecard.meeting_link && (
                                <span>
                                  <strong>Meet: </strong>
                                  <a href={scorecard.meeting_link} target="_blank" rel="noreferrer" className="text-purple-400 hover:underline">
                                    {scorecard.meeting_link}
                                  </a>
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Offer Details if available */}
                        {scorecard.offer_details && (
                          <div className="p-4 rounded-2xl bg-indigo-950/20 border border-indigo-900/30 space-y-2">
                            <h5 className="text-xs font-bold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                              <FileCheck className="h-3.5 w-3.5" /> Formal Offer Contract
                            </h5>
                            <div className="text-xs text-gray-300">
                              <p>Template: <strong>{scorecard.offer_details.template_name}</strong> • Dispatched: <strong>{scorecard.offer_details.offered_at?.slice(0, 10)}</strong></p>
                              <p className="text-xs text-gray-400 mt-1">{scorecard.offer_details.delivery_note}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Action Bar Footer */}
                    <div className="p-4 bg-gray-950/40 flex justify-between items-center gap-2 flex-wrap">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteCandidate(candidate.id)}
                        className="text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 h-9 px-3 rounded-xl"
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" /> Delete
                      </Button>

                      {/* Primary Recruiting Pipeline Actions */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {candidate.status === 'sourced' && (
                          <>
                            <Button
                              size="sm"
                              onClick={() => handleUpdateCandidateStatus(candidate.id, 'accepted')}
                              className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold h-9 px-4 rounded-xl text-xs shadow-md shadow-emerald-500/20"
                            >
                              Approve Candidate
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleUpdateCandidateStatus(candidate.id, 'rejected')}
                              className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 border border-rose-900/50 font-semibold h-9 px-3 rounded-xl text-xs"
                            >
                              Reject
                            </Button>
                          </>
                        )}

                        {candidate.status === 'accepted' && (
                          <>
                            <Button
                              size="sm"
                              onClick={() => openInterviewModal(candidate)}
                              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold h-9 px-4 rounded-xl text-xs shadow-md shadow-blue-500/20 flex items-center gap-1.5"
                            >
                              <Mail className="h-3.5 w-3.5" /> Send Interview Mail
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleUpdateCandidateStatus(candidate.id, 'rejected')}
                              className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 border border-rose-900/50 font-semibold h-9 px-3 rounded-xl text-xs"
                            >
                              Reject
                            </Button>
                          </>
                        )}

                        {candidate.status === 'interviewed' && (
                          <>
                            <Button
                              size="sm"
                              onClick={() => openOfferModal(candidate)}
                              className="bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-semibold h-9 px-4 rounded-xl text-xs shadow-md shadow-amber-500/20 flex items-center gap-1.5"
                            >
                              <Sparkles className="h-3.5 w-3.5" /> Generate Offer Letter & Contract
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleUpdateCandidateStatus(candidate.id, 'rejected')}
                              className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 border border-rose-900/50 font-semibold h-9 px-3 rounded-xl text-xs"
                            >
                              Reject
                            </Button>
                          </>
                        )}

                        {candidate.status === 'offered' && (
                          <>
                            <Button
                              size="sm"
                              onClick={() => handleUpdateCandidateStatus(candidate.id, 'hired')}
                              className="bg-teal-600 hover:bg-teal-500 text-white font-bold h-9 px-4 rounded-xl text-xs shadow-md shadow-teal-500/20 flex items-center gap-1.5"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" /> Mark as Hired
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => openOfferModal(candidate)}
                              className="bg-gray-800 hover:bg-gray-700 text-gray-200 font-semibold h-9 px-3 rounded-xl text-xs"
                            >
                              View / Edit Contract
                            </Button>
                          </>
                        )}

                        {candidate.status === 'hired' && (
                          <span className="text-xs font-bold text-teal-400 flex items-center gap-1.5 px-3 py-1 bg-teal-500/10 border border-teal-500/20 rounded-xl">
                            ✓ Successfully Hired Employee
                          </span>
                        )}

                        {candidate.status === 'rejected' && (
                          <Button
                            size="sm"
                            onClick={() => handleUpdateCandidateStatus(candidate.id, 'accepted')}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold h-9 px-3 rounded-xl text-xs"
                          >
                            Re-Open
                          </Button>
                        )}
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* --- INTERVIEW INVITATION MODAL --- */}
      {interviewCandidate && (
        <Dialog open={!!interviewCandidate} onOpenChange={open => !open && setInterviewCandidate(null)}>
          <DialogContent className="bg-gray-950 border-gray-800 text-white sm:max-w-[620px] rounded-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold flex items-center gap-2">
                <Mail className="h-5 w-5 text-blue-400" />
                Send Interview Invitation to {interviewCandidate.name}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 pt-3">
              <div className="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
                Candidate applied for <strong>{interviewCandidate.role}</strong> ({interviewCandidate.email}). Email will be sent using your configured SMTP or Google Workspace connection.
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Interview Date *</label>
                  <Input
                    type="date"
                    value={interviewDate}
                    onChange={e => setInterviewDate(e.target.value)}
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Interview Time</label>
                  <Input
                    value={interviewTime}
                    onChange={e => setInterviewTime(e.target.value)}
                    placeholder="e.g. 11:00 AM EST"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Interview Round / Title</label>
                <Input
                  value={interviewRound}
                  onChange={e => setInterviewRound(e.target.value)}
                  placeholder="e.g. Round 1: Technical & System Design"
                  className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Interviewer Name / Lead</label>
                  <Input
                    value={interviewerName}
                    onChange={e => setInterviewerName(e.target.value)}
                    placeholder="e.g. Sarah Connor (VP Eng)"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Meeting Link (Google Meet / Zoom)</label>
                  <Input
                    value={meetingLink}
                    onChange={e => setMeetingLink(e.target.value)}
                    placeholder="https://meet.google.com/..."
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Additional Instructions / Notes</label>
                <Textarea
                  value={interviewNotes}
                  onChange={e => setInterviewNotes(e.target.value)}
                  placeholder="Please have your GitHub profile or favorite project ready to walk through."
                  className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-[70px]"
                />
              </div>

              <Button
                onClick={handleSendInterviewEmail}
                disabled={interviewSending || !interviewDate}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold h-11 rounded-xl shadow-lg shadow-blue-500/20 text-xs mt-2"
              >
                {interviewSending ? (
                  <span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Sending Invitation...</span>
                ) : (
                  <span className="flex items-center gap-2"><Send className="h-4 w-4" /> Send Official Interview Invitation</span>
                )}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* --- OFFER LETTER & CONTRACT GENERATION STUDIO MODAL --- */}
      {offerCandidate && (
        <Dialog open={!!offerCandidate} onOpenChange={open => !open && setOfferCandidate(null)}>
          <DialogContent className="bg-gray-950 border-gray-800 text-white sm:max-w-[950px] max-h-[92vh] overflow-y-auto rounded-3xl p-6">
            <DialogHeader className="border-b border-gray-800 pb-4">
              <DialogTitle className="text-xl font-semibold flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-amber-400" />
                  Offer Letter & Employment Contract Studio
                </span>
                <span className="text-xs font-semibold text-gray-400">Candidate: {offerCandidate.name}</span>
              </DialogTitle>
            </DialogHeader>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-4">
              {/* Left Column: Template & Dynamic Fields Form */}
              <div className="lg:col-span-5 space-y-4 max-h-[68vh] overflow-y-auto pr-1">
                {/* Contract Template Selector */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Contract Agreement Template</label>
                  <Select
                    value={selectedTemplateId}
                    onValueChange={async (val) => {
                      if (val) {
                        setSelectedTemplateId(val);
                        await generateContractPreview(offerCandidate.id, val, offerVariables);
                      }
                    }}
                  >
                    <SelectTrigger className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-800 text-white">
                      {contractTemplates.map(t => (
                        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Candidate Name & Email */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Candidate Name</label>
                    <Input
                      value={offerVariables.candidate_name || ''}
                      onChange={e => {
                        const updated = { ...offerVariables, candidate_name: e.target.value };
                        setOfferVariables(updated);
                        generateContractPreview(offerCandidate.id, selectedTemplateId, updated);
                      }}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Candidate Email</label>
                    <Input
                      value={offerVariables.candidate_email || ''}
                      onChange={e => setOfferVariables({ ...offerVariables, candidate_email: e.target.value })}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                </div>

                {/* Job Title & Department */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Position / Job Title</label>
                    <Input
                      value={offerVariables.job_title || ''}
                      onChange={e => {
                        const updated = { ...offerVariables, job_title: e.target.value };
                        setOfferVariables(updated);
                        generateContractPreview(offerCandidate.id, selectedTemplateId, updated);
                      }}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Department</label>
                    <Input
                      value={offerVariables.department || 'Engineering'}
                      onChange={e => setOfferVariables({ ...offerVariables, department: e.target.value })}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                </div>

                {/* Employment Type & Joining Date */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Employment Type</label>
                    <Select
                      value={offerVariables.employment_type || 'Full-Time Permanent'}
                      onValueChange={val => {
                        if (val) {
                          const updated = { ...offerVariables, employment_type: val };
                          setOfferVariables(updated);
                          generateContractPreview(offerCandidate.id, selectedTemplateId, updated);
                        }
                      }}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-800 text-white">
                        <SelectItem value="Full-Time Permanent">Full-Time Permanent</SelectItem>
                        <SelectItem value="Part-Time">Part-Time</SelectItem>
                        <SelectItem value="Independent Contractor">Independent Contractor</SelectItem>
                        <SelectItem value="Internship">Internship</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Commencement / Start Date</label>
                    <Input
                      value={offerVariables.start_date || ''}
                      onChange={e => {
                        const updated = { ...offerVariables, start_date: e.target.value };
                        setOfferVariables(updated);
                        generateContractPreview(offerCandidate.id, selectedTemplateId, updated);
                      }}
                      placeholder="e.g. November 1, 2026"
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                </div>

                {/* Salary Amount & Currency */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Base Salary / Rate</label>
                    <Input
                      value={offerVariables.salary_amount || '130,000'}
                      onChange={e => {
                        const updated = { ...offerVariables, salary_amount: e.target.value };
                        setOfferVariables(updated);
                        generateContractPreview(offerCandidate.id, selectedTemplateId, updated);
                      }}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Currency</label>
                    <Select
                      value={offerVariables.salary_currency || 'USD'}
                      onValueChange={val => {
                        if (val) {
                          const updated = { ...offerVariables, salary_currency: val };
                          setOfferVariables(updated);
                          generateContractPreview(offerCandidate.id, selectedTemplateId, updated);
                        }
                      }}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-800 text-white">
                        <SelectItem value="USD">USD ($)</SelectItem>
                        <SelectItem value="EUR">EUR (€)</SelectItem>
                        <SelectItem value="GBP">GBP (£)</SelectItem>
                        <SelectItem value="INR">INR (₹)</SelectItem>
                        <SelectItem value="CAD">CAD ($)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Work Mode & Location */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Work Mode</label>
                    <Select
                      value={offerVariables.work_mode || 'Remote (Global)'}
                      onValueChange={val => {
                        if (val) {
                          const updated = { ...offerVariables, work_mode: val };
                          setOfferVariables(updated);
                          generateContractPreview(offerCandidate.id, selectedTemplateId, updated);
                        }
                      }}
                    >
                      <SelectTrigger className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-900 border-gray-800 text-white">
                        <SelectItem value="Remote (Global)">Remote (Global)</SelectItem>
                        <SelectItem value="Hybrid (2 Days Onsite)">Hybrid (2 Days Onsite)</SelectItem>
                        <SelectItem value="Onsite Headquarters">Onsite Headquarters</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Reporting Manager</label>
                    <Input
                      value={offerVariables.reporting_manager || 'VP of Engineering'}
                      onChange={e => setOfferVariables({ ...offerVariables, reporting_manager: e.target.value })}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                </div>

                {/* Signatory Name & Title */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Signatory Full Name</label>
                    <Input
                      value={offerVariables.signatory_name || 'Alex Vance'}
                      onChange={e => setOfferVariables({ ...offerVariables, signatory_name: e.target.value })}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-gray-400">Signatory Title</label>
                    <Input
                      value={offerVariables.signatory_title || 'Head of People Operations'}
                      onChange={e => setOfferVariables({ ...offerVariables, signatory_title: e.target.value })}
                      className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Right Column: Live Formatted Contract Preview */}
              <div className="lg:col-span-7 flex flex-col space-y-3">
                <div className="flex justify-between items-center bg-gray-900/60 p-2.5 rounded-2xl border border-gray-800">
                  <span className="text-xs font-bold text-gray-300 flex items-center gap-1.5">
                    <Eye className="h-4 w-4 text-amber-400" /> Live Document Preview
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const printWindow = window.open('', '_blank');
                        if (printWindow) {
                          printWindow.document.write(offerPreviewHtml);
                          printWindow.document.close();
                          printWindow.focus();
                          printWindow.print();
                        }
                      }}
                      className="text-xs h-8 border-gray-700 text-gray-300 hover:text-white rounded-xl flex items-center gap-1"
                    >
                      <Printer className="h-3.5 w-3.5" /> Print / Save PDF
                    </Button>
                  </div>
                </div>

                {/* Document render frame */}
                <div className="border border-gray-800 rounded-2xl bg-white overflow-hidden h-[54vh] shadow-inner relative">
                  {contractGenerating ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                      <Loader2 className="h-6 w-6 animate-spin text-gray-900" />
                    </div>
                  ) : null}
                  <iframe
                    title="Contract Document Preview"
                    srcDoc={offerPreviewHtml}
                    className="w-full h-full border-none"
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-3 pt-2">
                  <Button
                    onClick={handleSendOfferEmail}
                    disabled={offerSending}
                    className="flex-1 bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-semibold h-11 rounded-xl shadow-lg shadow-amber-500/20 text-xs flex items-center justify-center gap-2"
                  >
                    {offerSending ? (
                      <span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Dispatching Offer...</span>
                    ) : (
                      <span className="flex items-center gap-2"><Send className="h-4 w-4" /> Send Official Offer Letter & Contract via Email</span>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Candidate Edit Dialog (Extraction Sheet Row-Wise Editor) */}
      {editingCandidate && (
        <Dialog open={!!editingCandidate} onOpenChange={open => !open && setEditingCandidate(null)}>
          <DialogContent className="bg-gray-950 border-gray-800 text-white sm:max-w-[650px] max-h-[88vh] overflow-y-auto rounded-3xl p-6 shadow-2xl">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold flex items-center gap-2">
                <Edit className="h-5 w-5 text-amber-400" />
                Edit Candidate Record
              </DialogTitle>
              <p className="text-xs text-gray-400">
                Update candidate extraction details. All edits immediately synchronize with the database and Excel exports.
              </p>
            </DialogHeader>

            <div className="space-y-4 pt-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Full Name *</label>
                  <Input
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    placeholder="Candidate Name"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Email Address *</label>
                  <Input
                    value={editEmail}
                    onChange={e => setEditEmail(e.target.value)}
                    placeholder="candidate@example.com"
                    type="email"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Role / Job Title *</label>
                  <Input
                    value={editRole}
                    onChange={e => setEditRole(e.target.value)}
                    placeholder="e.g. Senior Backend Engineer"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Shortlisting Status</label>
                  <Select value={editStatus} onValueChange={val => val && setEditStatus(val)}>
                    <SelectTrigger className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-800 text-white">
                      <SelectItem value="sourced">Sourced</SelectItem>
                      <SelectItem value="accepted">Accepted</SelectItem>
                      <SelectItem value="screened">Screened</SelectItem>
                      <SelectItem value="interviewed">Interviewed</SelectItem>
                      <SelectItem value="offered">Offered</SelectItem>
                      <SelectItem value="hired">Hired</SelectItem>
                      <SelectItem value="rejected">Rejected</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Mobile / Phone Number</label>
                  <Input
                    value={editPhone}
                    onChange={e => setEditPhone(e.target.value)}
                    placeholder="+1 (555) 123-4567"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Location / Address</label>
                  <Input
                    value={editAddress}
                    onChange={e => setEditAddress(e.target.value)}
                    placeholder="e.g. San Francisco, CA"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Skills (comma separated)</label>
                <Input
                  value={editSkills}
                  onChange={e => setEditSkills(e.target.value)}
                  placeholder="Python, React, TypeScript, Docker, PostgreSQL"
                  className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Projects (semicolon separated)</label>
                <Textarea
                  value={editProjects}
                  onChange={e => setEditProjects(e.target.value)}
                  placeholder="Project 1: Built distributed queue; Project 2: Microservices migration"
                  className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-[60px]"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Experience (Years)</label>
                  <Input
                    value={editExperienceYears}
                    onChange={e => setEditExperienceYears(e.target.value)}
                    placeholder="e.g. 5"
                    type="number"
                    step="0.5"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>
                <div className="col-span-2 space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Experience Summary</label>
                  <Input
                    value={editExperienceSummary}
                    onChange={e => setEditExperienceSummary(e.target.value)}
                    placeholder="e.g. 5+ years building backend systems"
                    className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Resume Link (OctaOS Internal Media Link)</label>
                <Input
                  value={editResumeLink}
                  onChange={e => setEditResumeLink(e.target.value)}
                  placeholder="/media/resumes/tenant_id/resume.pdf"
                  className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10 font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Extra Remarks & Evaluation Notes</label>
                <Textarea
                  value={editExtraRemarks}
                  onChange={e => setEditExtraRemarks(e.target.value)}
                  placeholder="Additional recruiter notes, recommendations, fit analysis..."
                  className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-[70px]"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <Button
                  variant="ghost"
                  onClick={() => setEditingCandidate(null)}
                  className="text-xs text-gray-400 hover:text-white"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveEditedCandidate}
                  disabled={savingEdit || !editName || !editEmail}
                  className="bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black font-bold text-xs rounded-xl h-10 px-5 shadow-lg shadow-amber-500/20"
                >
                  {savingEdit ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving Changes...
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <Save className="h-3.5 w-3.5" /> Save Changes
                    </span>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

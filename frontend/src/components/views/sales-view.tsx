'use client';

import React, { useState, useEffect } from 'react';
import { notify, confirmAction } from '@/lib/notify';
import { Button } from '@/components/ui/button';
import { LayoutGrid, TableProperties } from 'lucide-react';

import DealRoomView from './deal-room-view';
import SalesHeader from './sales/sales-header';
import SalesProspectingPanel from './sales/sales-prospecting-panel';
import SalesTableView from './sales/sales-table-view';
import SalesKanbanView from './sales/sales-kanban-view';
import SalesLeadDossier from './sales/sales-lead-dossier';
import SalesStepperView from './sales/sales-stepper-view';
import SalesAnalyticsView from './sales/sales-analytics-view';
import SalesConfigPanel from './sales/sales-config-panel';
import { CreateLeadModal, UploadLeadsModal } from './sales/sales-modals';
import {
  SalesSection,
  Lead,
  FollowUpStep,
  WorkflowStatus,
  SalesSettings,
  BusinessProfileData,
  parseBudget,
} from './sales/sales-types';

interface SalesViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  timeline: any[];
  section?: SalesSection;
  onSectionChange?: (section: SalesSection) => void;
}

export default function SalesView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  timeline,
  section,
  onSectionChange,
}: SalesViewProps) {
  // Navigation
  const [activeSalesTab, setActiveSalesTab] = useState<SalesSection>(
    section || 'pipeline'
  );
  useEffect(() => {
    if (section) setActiveSalesTab(section);
  }, [section]);

  const selectSalesSection = (next: SalesSection) => {
    setActiveSalesTab(next);
    onSectionChange?.(next);
  };

  // View Mode for Pipeline (Table vs Kanban)
  const [pipelineViewMode, setPipelineViewMode] = useState<'table' | 'kanban'>('table');

  // Leads CRM State
  const [salesLeads, setSalesLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [salesLoading, setSalesLoading] = useState(false);
  const [salesActionLoading, setSalesActionLoading] = useState(false);

  // Modals
  const [isCreateLeadModalOpen, setIsCreateLeadModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [creatingLead, setCreatingLead] = useState(false);
  const [uploadingLeads, setUploadingLeads] = useState(false);

  // Workflow & Agent State
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>({
    status: 'idle',
    current_step: 0,
    steps: {},
    logs: [],
  });

  // Prompt-Based Sales Agent State
  const [promptDirective, setPromptDirective] = useState('');
  const [promptRunning, setPromptRunning] = useState(false);
  const [promptLeadCount, setPromptLeadCount] = useState<number>(50);
  const [promptFreshness, setPromptFreshness] = useState('30_days');
  const [selectedProvider, setSelectedProvider] = useState('auto');
  const [selectedModel, setSelectedModel] = useState('');

  // Business Profile State
  const [profile, setProfile] = useState<BusinessProfileData>({
    company_name: '',
    website: '',
    industry: '',
    service_description: '',
    target_countries: 'India, UAE',
    target_industries: 'Manufacturing, Healthcare, IT Services',
    target_company_size: '10-100',
    target_budget_range: '1L-5L',
    target_decision_makers: 'Founder, CEO, CTO',
    usp: '',
    case_studies: '',
    offer_details: '',
    extra_context: '',
    primary_source: 'auto',
    calendars: 'https://calendly.com/sales',
    communication_channels: ['email', 'whatsapp', 'linkedin'],
    sales_emails: '',
    support_emails: '',
    lead_freshness: '30_days',
  });
  const [profileSaving, setProfileSaving] = useState(false);

  // Sales Governance Settings
  const [salesSettings, setSalesSettings] = useState<SalesSettings>({
    sales_auto_reply: true,
    reply_mode: 'review_first',
    auto_book_meetings: true,
    meeting_duration_minutes: 30,
    buffer_minutes: 15,
    follow_up_cadence_days: 3,
    max_ai_touchpoints: 5,
  });
  const [salesSettingsSaving, setSalesSettingsSaving] = useState(false);

  // Fetch Leads
  const fetchLeads = async () => {
    if (!token) return;
    setSalesLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/?limit=200`);
      if (res.ok) {
        const data = await res.json();
        setSalesLeads(data);
        if (selectedLead) {
          const updated = data.find((l: Lead) => l.id === selectedLead.id);
          if (updated) setSelectedLead(updated);
        }
      }
    } catch (e) {
      console.error('Error fetching leads:', e);
    } finally {
      setSalesLoading(false);
    }
  };

  // Fetch Business Profile
  const fetchBusinessProfile = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/business-profile`);
      if (res.ok) {
        const data = await res.json();
        setProfile({
          company_name: data.company_name || '',
          website: data.website || '',
          industry: data.industry || '',
          service_description: data.service_description || '',
          target_countries: Array.isArray(data.target_countries)
            ? data.target_countries.join(', ')
            : data.target_countries || '',
          target_industries: Array.isArray(data.target_industries)
            ? data.target_industries.join(', ')
            : data.target_industries || '',
          target_company_size: data.target_company_size || '',
          target_budget_range: data.target_budget_range || '1L-5L',
          target_decision_makers: Array.isArray(data.target_decision_makers)
            ? data.target_decision_makers.join(', ')
            : data.target_decision_makers || '',
          usp: data.usp || '',
          case_studies: data.case_studies || '',
          offer_details: data.offer_details || '',
          extra_context: data.extra_context || '',
          calendars: Array.isArray(data.calendars)
            ? data.calendars.filter((c: any) => typeof c === 'string').join(', ')
            : (typeof data.calendars === 'string' ? data.calendars : ''),
          sales_emails: Array.isArray(data.sales_emails) ? data.sales_emails.join(', ') : data.sales_emails || '',
          support_emails: Array.isArray(data.support_emails) ? data.support_emails.join(', ') : data.support_emails || '',
          lead_freshness: data.lead_freshness || '30_days',
          primary_source: data.primary_source || '',
          communication_channels: data.communication_channels || [],
        });
        if (data.v3_workflow_status) {
          setWorkflowStatus(data.v3_workflow_status);
        }
      }
    } catch (e) {
      console.error('Error fetching business profile:', e);
    }
  };

  // Fetch Workflow Status
  const fetchWorkflowStatus = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/v3-workflow-status`);
      if (res.ok) {
        const data = await res.json();
        setWorkflowStatus(data);
      }
    } catch (e) {
      console.error('Error fetching workflow status:', e);
    }
  };

  // Fetch Sales Settings
  const fetchSalesSettings = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/sales-settings`);
      if (res.ok) {
        const data = await res.json();
        setSalesSettings({
          sales_auto_reply: data.sales_auto_reply ?? true,
          reply_mode: data.reply_mode === 'auto_send' ? 'auto_send' : 'review_first',
          auto_book_meetings: data.auto_book_meetings ?? true,
          meeting_duration_minutes: data.meeting_duration_minutes ?? 30,
          buffer_minutes: data.buffer_minutes ?? 15,
          follow_up_cadence_days: data.follow_up_cadence_days ?? 3,
          max_ai_touchpoints: data.max_ai_touchpoints ?? 5,
        });
      }
    } catch (e) {
      console.error('Error fetching sales settings:', e);
    }
  };

  // Save Sales Settings
  const handleSaveSalesSettings = async (next: SalesSettings) => {
    if (!token) return;
    setSalesSettingsSaving(true);
    setSalesSettings(next);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/sales-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(next),
      });
      if (res.ok) {
        notify('Sales automation settings saved.');
      } else {
        notify('Failed to save sales settings.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesSettingsSaving(false);
    }
  };

  // Save Business Profile
  const handleSaveProfile = async () => {
    if (!token) return;
    setProfileSaving(true);
    try {
      const payload = {
        ...profile,
        target_countries: profile.target_countries.split(',').map((s) => s.trim()).filter(Boolean),
        target_industries: profile.target_industries.split(',').map((s) => s.trim()).filter(Boolean),
        target_decision_makers: profile.target_decision_makers.split(',').map((s) => s.trim()).filter(Boolean),
        calendars: profile.calendars.split(',').map((s) => s.trim()).filter(Boolean),
        sales_emails: profile.sales_emails.split(',').map((s) => s.trim()).filter(Boolean),
        support_emails: profile.support_emails.split(',').map((s) => s.trim()).filter(Boolean),
      };
      const res = await fetchWithAuth(`${API_URL}/leads/business-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        notify('Business profile playbook saved successfully.');
      } else {
        notify('Failed to save business profile.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setProfileSaving(false);
    }
  };

  // Polling for Workflow Status while executing
  useEffect(() => {
    let interval: any = null;
    if (token && (workflowStatus.status === 'executing' || activeSalesTab === 'stepper')) {
      interval = setInterval(() => {
        fetchWorkflowStatus();
        fetchLeads();
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [token, workflowStatus.status, activeSalesTab]);

  // Initial load
  useEffect(() => {
    if (token) {
      fetchLeads();
      fetchBusinessProfile();
      fetchWorkflowStatus();
      fetchSalesSettings();
    }
  }, [token]);

  // Run Prompt-Based Sales Agent
  const handleRunPromptAgent = async () => {
    if (!promptDirective.trim()) {
      notify('Please enter a research prompt directive first.');
      return;
    }
    setPromptRunning(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/run-prompt-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptDirective,
          count: promptLeadCount || 50,
          freshness: promptFreshness || '30_days',
          provider: selectedProvider !== 'auto' ? selectedProvider : 'auto',
          model: selectedModel || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setWorkflowStatus((prev) => ({
          ...prev,
          workflow_type: 'prompt_agent',
          workflow_name: 'Prompt-Based Sales Agent',
          status: 'executing',
          current_step: 1,
        }));
        selectSalesSection('stepper');
        notify(data.message || '⚡ Prompt-Based Sales Agent launched! Live logs streaming.');
      } else {
        const data = await res.json();
        notify(`Failed to launch agent: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error('Launch prompt agent error:', e);
      notify('Network error starting prompt agent.');
    } finally {
      setPromptRunning(false);
    }
  };

  // Run Configured V3 Sales Engine
  const handleLaunchV3Workflow = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/run-v3-workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          model: selectedModel || undefined,
          count: 50,
          freshness: profile.lead_freshness,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setWorkflowStatus((prev) => ({
          ...prev,
          status: 'executing',
        }));
        selectSalesSection('stepper');
        notify(data.message || '🚀 Configured Sales Engine launched! Check Live Stepper.');
      } else {
        const data = await res.json();
        notify(`Failed to launch engine: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error('Launch V3 workflow error:', e);
      notify('Network error starting workflow.');
    }
  };

  // Lead Actions
  const handleCreateLead = async (leadData: any) => {
    setCreatingLead(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(leadData),
      });
      if (res.ok) {
        notify('Prospect account created.');
        fetchLeads();
        fetchData();
      } else {
        notify('Failed to create account.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setCreatingLead(false);
    }
  };

  const handleUploadLeads = async (file: File, withAI: boolean) => {
    setUploadingLeads(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('handle_with_ai', String(withAI));

      const res = await fetchWithAuth(`${API_URL}/leads/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setIsUploadModalOpen(false);
        fetchLeads();
        fetchData();
        notify(`✅ Leads imported successfully!\n${data.message}`);
      } else {
        notify(`Error importing leads: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error uploading leads.');
    } finally {
      setUploadingLeads(false);
    }
  };

  const handleUpdateStatus = async (leadId: string, status: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (res.ok) {
        notify(`Account stage updated to ${status}.`);
        fetchLeads();
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveLead = async (leadId: string, updates: Partial<Lead>) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedLead(updated);
        notify('Account details saved.');
        fetchLeads();
        fetchData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleDeleteLead = async (leadId: string, skipConfirm = false) => {
    if (!skipConfirm) {
      const ok = await confirmAction(
        'Permanently delete this prospect lead and remove it from your pipeline? This action cannot be undone.',
        {
          title: 'Delete Lead Account',
          confirmLabel: 'Delete Lead',
          destructive: true,
        }
      );
      if (!ok) return;
    }

    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        notify('Lead deleted successfully.');
        setSalesLeads((prev) => prev.filter((l) => l.id !== leadId));
        if (selectedLead?.id === leadId) {
          setSelectedLead(null);
        }
        fetchLeads();
        fetchData();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to delete lead.');
      }
    } catch (e) {
      console.error('Error deleting lead:', e);
      notify('An error occurred while deleting the lead.');
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleBulkDeleteLeads = async (leadIds: string[]) => {
    if (!leadIds || leadIds.length === 0) return;
    const ok = await confirmAction(
      `Permanently delete ${leadIds.length} selected leads? This action cannot be undone.`,
      {
        title: 'Delete Selected Leads',
        confirmLabel: `Delete ${leadIds.length} Leads`,
        destructive: true,
      }
    );
    if (!ok) return;

    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/bulk-delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_ids: leadIds }),
      });
      if (res.ok) {
        notify(`${leadIds.length} leads deleted successfully.`);
        const idSet = new Set(leadIds);
        setSalesLeads((prev) => prev.filter((l) => !idSet.has(l.id)));
        if (selectedLead && idSet.has(selectedLead.id)) {
          setSelectedLead(null);
        }
        fetchLeads();
        fetchData();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to delete leads.');
      }
    } catch (e) {
      console.error('Error bulk deleting leads:', e);
      notify('An error occurred while deleting leads.');
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleSendSalesOutreach = async (leadId: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/outreach`, {
        method: 'POST',
      });
      if (res.ok) {
        notify('Sales outreach message generated & sent.');
        fetchLeads();
        fetchData();
      } else {
        notify('Failed to generate outreach.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleSendOutreachSmart = async (leadId: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/send-outreach-smart`, {
        method: 'POST',
      });
      if (res.ok) {
        notify('Smart multi-channel outreach dispatched.');
        fetchLeads();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  const mergeSelectedLeadData = (leadId: string, patch: Record<string, any>) =>
    setSelectedLead((prev) =>
      prev && prev.id === leadId ? { ...prev, data: { ...(prev.data || {}), ...patch } } : prev
    );

  const handleGenerateDraft = async (leadId: string, instructions: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/outreach/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instructions }),
      });
      if (res.ok) {
        const d = await res.json();
        mergeSelectedLeadData(leadId, { draft_subject: d.subject, draft_body: d.body });
        return d as { subject: string; body: string };
      }
      notify('Failed to generate draft.');
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
    return null;
  };

  const handleSendDraft = async (leadId: string, subject: string, body: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/send-outreach-smart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, body }),
      });
      if (res.ok) {
        const d = await res.json();
        notify(d.sent ? 'Outreach sent.' : (d.send_message || 'Outreach staged (email not sent).'));
        fetchLeads();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleSaveSchedule = async (leadId: string, schedule: FollowUpStep[]) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/follow-up-schedule`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schedule }),
      });
      if (res.ok) {
        mergeSelectedLeadData(leadId, { outreach_schedule: schedule });
        notify('Follow-up schedule saved.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleBookSalesMeeting = async (leadId: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/schedule_meeting`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        notify(`Sales meeting booked for ${data.meeting_time}! Meet link: ${data.meeting_link}`);
        fetchLeads();
        fetchData();
      } else {
        notify('Failed to book meeting.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleLogHumanUpdate = async (
    leadId: string,
    content: string,
    channel: string,
    direction: string
  ) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/timeline-note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, channel, direction }),
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedLead(updated);
        notify('Internal note logged to timeline.');
        fetchLeads();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  // CSV Exporter
  const exportLeadsToCSV = () => {
    if (salesLeads.length === 0) {
      notify('No leads to export.');
      return;
    }
    const headers = [
      'ID', 'Name', 'Company', 'Email', 'Phone', 'Capacity', 'Need', 'Why',
      'Priority', 'Status', 'Score', 'Source',
    ];
    const rows = salesLeads.map((lead) => [
      lead.id,
      lead.name || '',
      lead.company || '',
      lead.email || lead.company_email || '',
      lead.phone || lead.mobile_no || '',
      lead.how_much || lead.purchasing_capacity || '',
      lead.need_of_what || '',
      lead.why || '',
      lead.priority || 'medium',
      lead.status || 'new',
      lead.score || 50,
      lead.source || 'Manual',
    ]);
    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `octaos_leads_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    notify('Leads exported to CSV.');
  };

  // Financial KPIs
  const activePipelineValue = salesLeads
    .filter((l) => !['closed_won', 'closed_lost', 'won', 'lost'].includes(l.status))
    .reduce((sum, l) => sum + parseBudget(l.how_much || l.purchasing_capacity), 0);

  const closedRevenue = salesLeads
    .filter((l) => ['closed_won', 'won'].includes(l.status))
    .reduce((sum, l) => sum + parseBudget(l.how_much || l.purchasing_capacity), 0);

  const wonCount = salesLeads.filter((l) => ['closed_won', 'won'].includes(l.status)).length;
  const lostCount = salesLeads.filter((l) => ['closed_lost', 'lost'].includes(l.status)).length;
  const totalClosed = wonCount + lostCount;
  const winRate = totalClosed > 0 ? Math.round((wonCount / totalClosed) * 100) : 0;
  const isExecuting = workflowStatus.status === 'executing';

  return (
    <div className="sales-white-theme -m-4 md:-m-6 p-4 md:p-8 min-h-[calc(100vh-3rem)]">
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Top Header & Executive KPI Ribbon */}
        <SalesHeader
          activeTab={activeSalesTab}
          onSelectTab={selectSalesSection}
          leadsCount={salesLeads.length}
          activePipelineValue={activePipelineValue}
          closedRevenue={closedRevenue}
          winRate={winRate}
          wonCount={wonCount}
          lostCount={lostCount}
          isExecuting={isExecuting}
          onOpenCreateLead={() => setIsCreateLeadModalOpen(true)}
          onOpenUploadLeads={() => setIsUploadModalOpen(true)}
          onExportCSV={exportLeadsToCSV}
        />

        {/* ── TAB 1 & 2: PROSPECTING AGENT & CONFIGURED SALES ENGINE ── */}
        {(activeSalesTab === 'prospecting' ||
          activeSalesTab === 'prompt_agent' ||
          activeSalesTab === 'configured_engine') && (
          <SalesProspectingPanel
            workflowStatus={workflowStatus}
            profile={profile}
            setProfile={setProfile}
            onSaveProfile={handleSaveProfile}
            profileSaving={profileSaving}
            promptDirective={promptDirective}
            setPromptDirective={setPromptDirective}
            promptLeadCount={promptLeadCount}
            setPromptLeadCount={setPromptLeadCount}
            promptFreshness={promptFreshness}
            setPromptFreshness={setPromptFreshness}
            promptRunning={promptRunning}
            onRunPromptAgent={handleRunPromptAgent}
            onRunConfiguredEngine={handleLaunchV3Workflow}
            onSwitchToStepper={() => selectSalesSection('stepper')}
            selectedProvider={selectedProvider}
            setSelectedProvider={setSelectedProvider}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            initialMode={activeSalesTab === 'configured_engine' ? 'configured' : 'prompt'}
          />
        )}

        {/* ── TAB 2: PIPELINE & LEADS CRM ── */}
        {activeSalesTab === 'pipeline' && (
          <div className="space-y-4">
            {pipelineViewMode === 'table' ? (
              <SalesTableView
                leads={salesLeads}
                onSelectLead={(l) => setSelectedLead(l)}
                selectedLeadId={selectedLead?.id}
                onDeleteLead={handleDeleteLead}
                onBulkDeleteLeads={handleBulkDeleteLeads}
                onUpdateStatus={handleUpdateStatus}
                onOpenCreateLead={() => setIsCreateLeadModalOpen(true)}
                onOpenProspecting={() => selectSalesSection('prospecting')}
                viewMode={pipelineViewMode}
                onViewModeChange={setPipelineViewMode}
              />
            ) : (
              <SalesKanbanView
                leads={salesLeads}
                onSelectLead={(l) => setSelectedLead(l)}
                onUpdateStatus={handleUpdateStatus}
                onOpenCreateLead={() => setIsCreateLeadModalOpen(true)}
                viewMode={pipelineViewMode}
                onViewModeChange={setPipelineViewMode}
              />
            )}
          </div>
        )}

      {/* ── TAB 3: AGENT OPERATIONS & LIVE STEPPER ── */}
      {activeSalesTab === 'stepper' && (
        <SalesStepperView
          workflowStatus={workflowStatus}
          onRerun={handleLaunchV3Workflow}
          onOpenProspecting={() => selectSalesSection('prospecting')}
        />
      )}

      {/* ── TAB 4: REVENUE & FUNNEL ANALYTICS ── */}
      {activeSalesTab === 'analytics' && (
        <SalesAnalyticsView
          leads={salesLeads}
          onOpenProspecting={() => selectSalesSection('prospecting')}
          onOpenPipeline={() => selectSalesSection('pipeline')}
        />
      )}

      {/* ── TAB 5: DEAL ROOMS ── */}
      {activeSalesTab === 'deal_rooms' && (
        <DealRoomView token={token} API_URL={API_URL} fetchWithAuth={fetchWithAuth} />
      )}

      {/* ── TAB 6: ENGINE SETTINGS ── */}
      {activeSalesTab === 'config' && (
        <SalesConfigPanel
          API_URL={API_URL}
          fetchWithAuth={fetchWithAuth}
          profile={profile}
          setProfile={setProfile}
          salesSettings={salesSettings}
          onSaveSalesSettings={handleSaveSalesSettings}
          salesSettingsSaving={salesSettingsSaving}
          onSaveProfile={handleSaveProfile}
          profileSaving={profileSaving}
          onRunWorkflowSuccess={() => {
            fetchWorkflowStatus();
            selectSalesSection('stepper');
          }}
        />
      )}

      {/* ── SLIDE-OVER LEAD DOSSIER ── */}
      <SalesLeadDossier
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onUpdateStatus={handleUpdateStatus}
        onSendOutreach={handleSendSalesOutreach}
        onSendSmartOutreach={handleSendOutreachSmart}
        onGenerateDraft={handleGenerateDraft}
        onSendDraft={handleSendDraft}
        onSaveSchedule={handleSaveSchedule}
        onBookMeeting={handleBookSalesMeeting}
        onDeleteLead={handleDeleteLead}
        onLogNote={handleLogHumanUpdate}
        onSaveLead={handleSaveLead}
        actionLoading={salesActionLoading}
      />

      {/* ── MODALS ── */}
      <CreateLeadModal
        isOpen={isCreateLeadModalOpen}
        onClose={() => setIsCreateLeadModalOpen(false)}
        onCreateLead={handleCreateLead}
        loading={creatingLead}
      />

      <UploadLeadsModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUpload={handleUploadLeads}
        loading={uploadingLeads}
      />
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  TrendingUp, Search, Upload, Plus, Edit2, MessageSquare, Send, Clock, 
  ChevronRight, Calendar, Loader2, Bot, Check, X, Phone, Mail, Building, Users, LayoutGrid, Target, Cpu, Sparkles, Activity 
} from 'lucide-react';

interface SalesViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  timeline: any[];
}

export default function SalesView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  timeline,
}: SalesViewProps) {
  // Sales CRM states relocated here
  const [salesLeads, setSalesLeads] = useState<any[]>([]);
  const [selectedLead, setSelectedLead] = useState<any | null>(null);
  const [salesSearch, setSalesSearch] = useState('');
  const [salesStatusFilter, setSalesStatusFilter] = useState('all');
  const [salesPriorityFilter, setSalesPriorityFilter] = useState('all');
  const [salesTimeFilter, setSalesTimeFilter] = useState('all');
  const [salesLoading, setSalesLoading] = useState(false);
  const [salesActionLoading, setSalesActionLoading] = useState(false);

  // Edit Lead Fields
  const [isEditingSalesLead, setIsEditingSalesLead] = useState(false);
  const [editPersonalEmail, setEditPersonalEmail] = useState('');
  const [editCompanyEmail, setEditCompanyEmail] = useState('');
  const [editMobileNo, setEditMobileNo] = useState('');
  const [editCompanyContactNo, setEditCompanyContactNo] = useState('');
  const [editNeedOfWhat, setEditNeedOfWhat] = useState('');
  const [editHowMuch, setEditHowMuch] = useState('');
  const [editWhy, setEditWhy] = useState('');
  const [editTargetContext, setEditTargetContext] = useState('');
  const [editName, setEditName] = useState('');
  const [editCompany, setEditCompany] = useState('');
  const [editPriority, setEditPriority] = useState('medium');
  const [editStatus, setEditStatus] = useState('captured');
  const [editScore, setEditScore] = useState(0);

  // Lead Upload & Human updates states
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadWithAI, setUploadWithAI] = useState(false);
  const [uploadingLeads, setUploadingLeads] = useState(false);
  
  const [noteText, setNoteText] = useState('');
  const [noteChannel, setNoteChannel] = useState('note');
  const [noteDirection, setNoteDirection] = useState('internal');

  // Manual Lead Creation and View Mode States (CRM)
  const [salesViewMode, setSalesViewMode] = useState<'pipeline' | 'list'>('pipeline');
  const [isCreateLeadModalOpen, setIsCreateLeadModalOpen] = useState(false);
  const [newLeadName, setNewLeadName] = useState('');
  const [newLeadCompany, setNewLeadCompany] = useState('');
  const [newLeadEmail, setNewLeadEmail] = useState('');
  const [newLeadPhone, setNewLeadPhone] = useState('');
  const [newLeadPersonalEmail, setNewLeadPersonalEmail] = useState('');
  const [newLeadCompanyEmail, setNewLeadCompanyEmail] = useState('');
  const [newLeadMobileNo, setNewLeadMobileNo] = useState('');
  const [newLeadCompanyContactNo, setNewLeadCompanyContactNo] = useState('');
  const [newLeadNeedOfWhat, setNewLeadNeedOfWhat] = useState('');
  const [newLeadHowMuch, setNewLeadHowMuch] = useState('');
  const [newLeadWhy, setNewLeadWhy] = useState('');
  const [newLeadTargetContext, setNewLeadTargetContext] = useState('');
  const [newLeadPriority, setNewLeadPriority] = useState('medium');
  const [newLeadStatus, setNewLeadStatus] = useState('captured');
  const [newLeadScore, setNewLeadScore] = useState(0);
  const [creatingLead, setCreatingLead] = useState(false);

  // Fetch leads when filters change
  useEffect(() => {
    if (token) {
      fetchLeads();
    }
  }, [salesStatusFilter, salesPriorityFilter, salesSearch, salesTimeFilter, token]);

  // Sync edits if a new lead is selected
  useEffect(() => {
    if (selectedLead) {
      setEditPersonalEmail(selectedLead.personal_email || '');
      setEditCompanyEmail(selectedLead.company_email || '');
      setEditMobileNo(selectedLead.mobile_no || '');
      setEditCompanyContactNo(selectedLead.company_contact_no || '');
      setEditNeedOfWhat(selectedLead.need_of_what || '');
      setEditHowMuch(selectedLead.how_much || '');
      setEditWhy(selectedLead.why || '');
      setEditTargetContext(selectedLead.target_context || '');
      setEditName(selectedLead.name || '');
      setEditCompany(selectedLead.company || '');
      setEditPriority(selectedLead.priority || 'medium');
      setEditStatus(selectedLead.status || 'captured');
      setEditScore(selectedLead.score || 0);
    } else {
      setIsEditingSalesLead(false);
    }
  }, [selectedLead]);

  // CRM functions
    const fetchLeads = async () => {
    if (!token) return;
    setSalesLoading(true);
    try {
      const queryParams = new URLSearchParams();
      if (salesStatusFilter && salesStatusFilter !== 'all') queryParams.append('status', salesStatusFilter);
      if (salesPriorityFilter && salesPriorityFilter !== 'all') queryParams.append('priority', salesPriorityFilter);
      if (salesSearch) queryParams.append('search', salesSearch);
      if (salesTimeFilter && salesTimeFilter !== 'all') queryParams.append('time_filter', salesTimeFilter);

      const res = await fetchWithAuth(`${API_URL}/leads/?${queryParams.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setSalesLeads(data);
        if (selectedLead) {
          const updated = data.find((l: any) => l.id === selectedLead.id);
          if (updated) {
            setSelectedLead(updated);
          }
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesLoading(false);
    }
  };

  
  const handleSaveLead = async () => {
    if (!selectedLead) return;
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${selectedLead.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editName,
          company: editCompany,
          personal_email: editPersonalEmail,
          company_email: editCompanyEmail,
          mobile_no: editMobileNo,
          company_contact_no: editCompanyContactNo,
          need_of_what: editNeedOfWhat,
          how_much: editHowMuch,
          why: editWhy,
          target_context: editTargetContext,
          priority: editPriority,
          status: editStatus,
          score: Number(editScore) || 0
        })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedLead(updated);
        setIsEditingSalesLead(false);
        fetchLeads();
        fetchData();
      } else {
        alert('Failed to save lead updates');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };


    const handleSendSalesOutreach = async (leadId: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/outreach`, {
        method: 'POST'
      });
      if (res.ok) {
        alert('Sales outreach email sent and recorded in conversation history!');
        fetchLeads();
        fetchData();
      } else {
        alert('Failed to send sales outreach');
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
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        alert(`Sales meeting successfully scheduled for ${data.meeting_time}! Meet link: ${data.meeting_link}`);
        fetchLeads();
        fetchData();
      } else {
        alert('Failed to book meeting');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };


    const handleLogHumanUpdate = async () => {
    if (!selectedLead || !noteText.trim()) return;
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${selectedLead.id}/timeline-note`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: noteText,
          channel: noteChannel,
          direction: noteDirection
        })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedLead(updated);
        setNoteText('');
        fetchLeads();
        fetchData();
      } else {
        alert('Failed to log human update');
      }
    } catch (e) {
      console.error(e);
      alert('Network error logging human update');
    } finally {
      setSalesActionLoading(false);
    }
  };


    const handleUploadLeads = async () => {
    if (!uploadFile) return;
    setUploadingLeads(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('handle_with_ai', String(uploadWithAI));

      const res = await fetchWithAuth(`${API_URL}/leads/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setIsUploadModalOpen(false);
        setUploadFile(null);
        setUploadWithAI(false);
        fetchLeads();
        fetchData();
        alert(`✅ Leads imported successfully!\n${data.message}`);
      } else {
        alert(`Error uploading leads: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      alert("Network error uploading leads.");
    } finally {
      setUploadingLeads(false);
    }
  };


    const handleCreateLead = async () => {
    if (!newLeadName && !newLeadEmail) {
      alert("Please enter at least a Lead Name or Email.");
      return;
    }
    setCreatingLead(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newLeadName || null,
          company: newLeadCompany || null,
          email: newLeadEmail || null,
          phone: newLeadPhone || null,
          personal_email: newLeadPersonalEmail || null,
          company_email: newLeadCompanyEmail || null,
          mobile_no: newLeadMobileNo || null,
          company_contact_no: newLeadCompanyContactNo || null,
          need_of_what: newLeadNeedOfWhat || null,
          how_much: newLeadHowMuch || null,
          why: newLeadWhy || null,
          target_context: newLeadTargetContext || null,
          priority: newLeadPriority || 'medium',
          status: newLeadStatus || 'captured',
          score: Number(newLeadScore) || 0,
          source: 'Manual Entry'
        })
      });
      if (res.ok) {
        setIsCreateLeadModalOpen(false);
        setNewLeadName('');
        setNewLeadCompany('');
        setNewLeadEmail('');
        setNewLeadPhone('');
        setNewLeadPersonalEmail('');
        setNewLeadCompanyEmail('');
        setNewLeadMobileNo('');
        setNewLeadCompanyContactNo('');
        setNewLeadNeedOfWhat('');
        setNewLeadHowMuch('');
        setNewLeadWhy('');
        setNewLeadTargetContext('');
        setNewLeadPriority('medium');
        setNewLeadStatus('captured');
        setNewLeadScore(0);
        fetchLeads();
        fetchData();
        alert("✅ Lead created successfully!");
      } else {
        const errorData = await res.json();
        alert(`Failed to create lead: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      alert("Network error creating lead.");
    } finally {
      setCreatingLead(false);
    }
  };


  // Trigger outbound sales sourcing sequence
  const handleRunSequence = async (sequenceType: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/run-sequence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sequence_type: sequenceType })
      });
      if (res.ok) {
        alert("Sales AI Outbound outreach sequence launched!");
        fetchLeads();
        fetchData();
      } else {
        alert("Failed to run sequence");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  // Trigger lead generation auto agent search
  const handleRunAutoSalesAgent = async () => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/run-auto-agent`, {
        method: 'POST'
      });
      if (res.ok) {
        alert("Sales AI Prospector launched! It will search local places/Yelp and sync to CRM.");
        fetchLeads();
        fetchData();
      } else {
        alert("Failed to run agent");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  const handleTriggerScoring = async (leadId: string) => {
    setSalesActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/leads/${leadId}/score`, {
        method: 'POST'
      });
      if (res.ok) {
        alert("Scoring triggered successfully!");
        fetchLeads();
        fetchData();
      } else {
        alert("Failed to score lead");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSalesActionLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <TrendingUp className="text-emerald-400 h-8 w-8 animate-pulse" /> Sales CRM Dashboard
                  </h1>
                  <p className="text-gray-400 mt-1">Autonomous B2B prospect sourcing, outreach sequencing, contact enrichment, and conversion tracking.</p>
                </div>
                 <div className="flex items-center gap-3">
                  <Button
                    onClick={() => setIsCreateLeadModalOpen(true)}
                    className="bg-gray-900 hover:bg-gray-800 text-white border border-gray-800 hover:border-gray-700 font-bold rounded-xl transition-all h-11 px-5 flex items-center gap-2 shadow-lg"
                  >
                    <Plus size={16} /> Add Lead Manually
                  </Button>
                  <Button
                    onClick={() => setIsUploadModalOpen(true)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl transition-all h-11 px-5 flex items-center gap-2 shadow-lg shadow-emerald-500/25"
                  >
                    <Upload size={16} /> Upload Leads (CSV/JSON)
                  </Button>
                </div>
              </div>

              {/* Statistics Ribbon */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { title: "Total Leads Sourced", val: salesLeads.length, desc: "Total B2B leads captured", icon: <Users className="h-4 w-4 text-emerald-400" /> },
                  { title: "Outreach Sent", val: salesLeads.filter(l => l.status === 'contacted' || l.status === 'replied' || l.status === 'meeting_scheduled').length, desc: "Outbound campaigns run", icon: <Send className="h-4 w-4 text-blue-400" /> },
                  { title: "Prospect Replies", val: salesLeads.filter(l => l.status === 'replied').length, desc: "Inbound interested responses", icon: <MessageSquare className="h-4 w-4 text-violet-400" /> },
                  { title: "Meetings Scheduled", val: salesLeads.filter(l => l.status === 'meeting_scheduled').length, desc: "Meetings booked in calendar", icon: <Calendar className="h-4 w-4 text-amber-400" /> },
                ].map((stat, i) => (
                  <Card key={i} className="glass-panel border-transparent shadow-lg rounded-2xl relative overflow-hidden p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">{stat.title}</p>
                        <h3 className="text-2xl font-black text-white mt-1">{stat.val}</h3>
                        <p className="text-[10px] text-gray-450 mt-0.5">{stat.desc}</p>
                      </div>
                      <div className="p-2 bg-gray-950/40 rounded-lg border border-gray-800">
                        {stat.icon}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>

              {/* Split Screen Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                
                {/* Left Pane: Leads List */}
                <div className="lg:col-span-2 space-y-4">
                  <Card className="glass-panel border-transparent rounded-3xl p-6 shadow-2xl relative">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
                    
                    {/* Filter Bar */}
                    <div className="flex flex-col md:flex-row gap-3 items-center mb-6">
                      <div className="relative flex-1 w-full">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-gray-505" />
                        <Input
                          placeholder="Search leads by name, company, email..."
                          value={salesSearch}
                          onChange={e => setSalesSearch(e.target.value)}
                          className="pl-9 bg-gray-900/60 border-gray-800 text-white rounded-xl h-10 w-full focus:border-emerald-500 focus:ring-emerald-500/20"
                        />
                      </div>
                      
                      <div className="flex gap-2 w-full md:w-auto">
                        <Select value={salesStatusFilter} onValueChange={val => setSalesStatusFilter(val || 'all')}>
                          <SelectTrigger className="w-[130px] bg-gray-900/60 border-gray-800 text-xs text-gray-305 rounded-xl h-10">
                            <SelectValue placeholder="Status" />
                          </SelectTrigger>
                          <SelectContent className="bg-gray-950 border-gray-800 text-gray-305">
                            <SelectItem value="all">All Statuses</SelectItem>
                            <SelectItem value="captured">Captured</SelectItem>
                            <SelectItem value="enriched">Enriched</SelectItem>
                            <SelectItem value="contacted">Contacted</SelectItem>
                            <SelectItem value="replied">Replied</SelectItem>
                            <SelectItem value="meeting_scheduled">Meetings</SelectItem>
                            <SelectItem value="won">Closed Won</SelectItem>
                            <SelectItem value="lost">Closed Lost</SelectItem>
                          </SelectContent>
                        </Select>

                        <Select value={salesPriorityFilter} onValueChange={val => setSalesPriorityFilter(val || 'all')}>
                          <SelectTrigger className="w-[110px] bg-gray-900/60 border-gray-800 text-xs text-gray-305 rounded-xl h-10">
                            <SelectValue placeholder="Priority" />
                          </SelectTrigger>
                          <SelectContent className="bg-gray-950 border-gray-800 text-gray-350">
                            <SelectItem value="all">All Priorities</SelectItem>
                            <SelectItem value="high">High</SelectItem>
                            <SelectItem value="medium">Medium</SelectItem>
                            <SelectItem value="low">Low</SelectItem>
                          </SelectContent>
                        </Select>

                         <Select value={salesTimeFilter} onValueChange={val => setSalesTimeFilter(val || 'all')}>
                          <SelectTrigger className="w-[110px] bg-gray-900/60 border-gray-800 text-xs text-gray-305 rounded-xl h-10">
                            <SelectValue placeholder="Time" />
                          </SelectTrigger>
                          <SelectContent className="bg-gray-950 border-gray-800 text-gray-350">
                            <SelectItem value="all">All Time</SelectItem>
                            <SelectItem value="day">Past 24h</SelectItem>
                            <SelectItem value="week">Past Week</SelectItem>
                            <SelectItem value="month">Past Month</SelectItem>
                          </SelectContent>
                        </Select>

                        <div className="flex items-center gap-1 bg-gray-950/80 p-1 border border-gray-800 rounded-xl">
                          <button
                            onClick={() => setSalesViewMode('pipeline')}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                              salesViewMode === 'pipeline'
                                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/15'
                                : 'text-gray-400 hover:text-white hover:bg-gray-900/40'
                            }`}
                          >
                            <LayoutGrid size={13} /> Pipeline
                          </button>
                          <button
                            onClick={() => setSalesViewMode('list')}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                              salesViewMode === 'list'
                                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/15'
                                : 'text-gray-400 hover:text-white hover:bg-gray-900/40'
                            }`}
                          >
                            <Users size={13} /> List
                          </button>
                        </div>
                      </div>
                    </div>

                    {salesViewMode === 'pipeline' ? (
                      /* Pipeline View Container */
                      <div className="flex gap-4 overflow-x-auto pb-4 pt-1 max-w-full custom-scrollbar min-h-[500px]">
                        {[
                          { id: 'captured', label: 'Captured', color: 'border-t-gray-500', glow: 'shadow-gray-500/5' },
                          { id: 'enriched', label: 'Enriched', color: 'border-t-teal-500', glow: 'shadow-teal-500/5' },
                          { id: 'contacted', label: 'Contacted', color: 'border-t-blue-500', glow: 'shadow-blue-500/5' },
                          { id: 'replied', label: 'Replied', color: 'border-t-violet-500', glow: 'shadow-violet-500/5' },
                          { id: 'meeting_scheduled', label: 'Meeting Booked', color: 'border-t-amber-500', glow: 'shadow-amber-500/5' },
                          { id: 'won', label: 'Closed Won', color: 'border-t-emerald-500', glow: 'shadow-emerald-500/5' },
                          { id: 'lost', label: 'Closed Lost', color: 'border-t-rose-500', glow: 'shadow-rose-500/5' },
                        ].map(stage => {
                          const stageLeads = salesLeads.filter(l => l.status === stage.id);
                          return (
                            <div
                              key={stage.id}
                              onDragOver={e => e.preventDefault()}
                              onDrop={async e => {
                                const leadId = e.dataTransfer.getData('text/plain');
                                if (!leadId) return;
                                
                                try {
                                  const res = await fetchWithAuth(`${API_URL}/leads/${leadId}`, {
                                    method: 'PATCH',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ status: stage.id })
                                  });
                                  if (res.ok) {
                                    const updated = await res.json();
                                    if (selectedLead && selectedLead.id === leadId) {
                                      setSelectedLead(updated);
                                    }
                                    fetchLeads();
                                    fetchData();
                                  } else {
                                    alert('Failed to update stage');
                                  }
                                } catch (err) {
                                  console.error(err);
                                }
                              }}
                              className="flex-shrink-0 w-64 bg-gray-950/40 border border-gray-800 rounded-2xl p-3 flex flex-col min-h-[460px] max-h-[580px] overflow-hidden"
                            >
                              {/* Column Header */}
                              <div className={`border-t-2 ${stage.color} pt-2 pb-2.5 flex items-center justify-between flex-shrink-0`}>
                                <span className="text-xs font-bold text-white tracking-wide">{stage.label}</span>
                                <span className="text-[10px] bg-gray-900 border border-gray-800 text-gray-400 font-bold px-2 py-0.5 rounded-full">
                                  {stageLeads.length}
                                </span>
                              </div>
                              
                              {/* Column Scrollable Body */}
                              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 custom-scrollbar min-h-0">
                                {stageLeads.map(lead => {
                                  const isSelected = selectedLead?.id === lead.id;
                                  return (
                                    <div
                                      key={lead.id}
                                      draggable={true}
                                      onDragStart={e => {
                                        e.dataTransfer.setData('text/plain', lead.id);
                                      }}
                                      onClick={() => {
                                        setSelectedLead(lead);
                                        setIsEditingSalesLead(false);
                                      }}
                                      className={`bg-gray-900/60 border rounded-xl p-3 cursor-grab active:cursor-grabbing hover:border-emerald-500/40 hover:bg-gray-900 transition-all shadow-md ${stage.glow} ${
                                        isSelected
                                          ? 'border-emerald-500 ring-1 ring-emerald-500/25 bg-emerald-950/5'
                                          : 'border-gray-850'
                                      }`}
                                    >
                                      <div className="font-extrabold text-white text-xs leading-tight mb-1 truncate">{lead.name || 'Unnamed Lead'}</div>
                                      <div className="text-[10px] text-gray-450 truncate mb-2">{lead.company || 'No Company'}</div>
                                      
                                      <div className="flex items-center justify-between gap-1.5 pt-1.5 border-t border-gray-800/60">
                                        <span className={`text-[8px] font-extrabold uppercase px-1.5 py-0.5 rounded tracking-wide border ${
                                          lead.priority === 'high' 
                                            ? 'bg-rose-500/10 text-rose-455 border-rose-500/20' 
                                            : lead.priority === 'medium' 
                                              ? 'bg-amber-500/10 text-amber-450 border-amber-500/20' 
                                              : 'bg-gray-500/10 text-gray-400 border-gray-800'
                                        }`}>
                                          {lead.priority || 'medium'}
                                        </span>
                                        
                                        <span className="text-[9px] font-mono text-gray-400 font-semibold bg-gray-950 px-1.5 py-0.5 rounded border border-gray-800">
                                          ★ {lead.score || 50}
                                        </span>
                                      </div>
                                    </div>
                                  );
                                })}
                                {stageLeads.length === 0 && (
                                  <div className="text-center py-12 text-[10px] text-gray-500 italic border border-dashed border-gray-850 rounded-xl">
                                    Drag leads here
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      /* Table View Container */
                      <div className="border border-gray-800/80 rounded-2xl overflow-hidden bg-[rgba(0,0,0,0.15)] max-h-[600px] overflow-y-auto custom-scrollbar">
                        <Table>
                          <TableHeader className="bg-gray-950/40 border-b border-gray-800 sticky top-0 z-10">
                            <TableRow className="border-gray-800 hover:bg-transparent">
                              <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-[10px] p-4">Lead</TableHead>
                              <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-[10px] p-4">Source</TableHead>
                              <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-[10px] p-4 text-center">Score</TableHead>
                              <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-[10px] p-4">Priority</TableHead>
                              <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-[10px] p-4">Status</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody className="divide-y divide-gray-850">
                            {salesLoading ? (
                              <TableRow className="hover:bg-transparent">
                                <TableCell colSpan={5} className="text-center py-16">
                                  <Loader2 className="h-6 w-6 animate-spin text-emerald-400 mx-auto" />
                                  <p className="text-xs text-gray-450 mt-2">Loading CRM database...</p>
                                </TableCell>
                              </TableRow>
                            ) : salesLeads.length === 0 ? (
                              <TableRow className="hover:bg-transparent">
                                <TableCell colSpan={5} className="text-center py-16 text-xs text-gray-500 font-medium">
                                  No sales leads found matching these filters.
                                </TableCell>
                              </TableRow>
                            ) : (
                              salesLeads.map(lead => {
                                const isSelected = selectedLead?.id === lead.id;
                                return (
                                  <TableRow
                                    key={lead.id}
                                    onClick={() => {
                                      setSelectedLead(lead);
                                      setIsEditingSalesLead(false);
                                    }}
                                    className={`border-gray-800/60 cursor-pointer transition-colors duration-155 ${
                                      isSelected 
                                        ? 'bg-emerald-500/10 hover:bg-emerald-500/15 border-l-2 border-l-emerald-500' 
                                        : 'hover:bg-gray-900/30'
                                    }`}
                                  >
                                    <TableCell className="p-4">
                                      <div className="font-extrabold text-white text-xs">{lead.name || 'Unnamed Lead'}</div>
                                      <div className="text-[10px] text-gray-455 flex items-center gap-1 mt-0.5">
                                        <Building size={10} /> {lead.company || 'No Company'}
                                      </div>
                                    </TableCell>
                                    <TableCell className="p-4">
                                      <span className="text-[9px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded uppercase tracking-wider max-w-[140px] truncate block text-center">
                                        {lead.source?.split(":")[0] || lead.source || 'Unknown'}
                                      </span>
                                    </TableCell>
                                    <TableCell className="p-4 text-center">
                                      <span className={`text-[10px] font-mono font-black ${
                                        lead.score >= 80 ? 'text-emerald-400' : lead.score >= 60 ? 'text-amber-400' : 'text-gray-400'
                                      }`}>
                                        {lead.score || 50}/100
                                      </span>
                                    </TableCell>
                                    <TableCell className="p-4">
                                      <span className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded tracking-wide border ${
                                        lead.priority === 'high' 
                                          ? 'bg-rose-500/10 text-rose-455 border-rose-500/20' 
                                          : lead.priority === 'medium' 
                                            ? 'bg-amber-500/10 text-amber-450 border-amber-500/20' 
                                            : 'bg-gray-500/10 text-gray-400 border-gray-805'
                                      }`}>
                                        {lead.priority || 'medium'}
                                      </span>
                                    </TableCell>
                                    <TableCell className="p-4">
                                      <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                                        lead.status === 'meeting_scheduled'
                                          ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                                          : lead.status === 'replied'
                                            ? 'bg-violet-500/15 text-violet-400 border border-violet-500/20'
                                            : lead.status === 'contacted'
                                              ? 'bg-blue-500/15 text-blue-400 border border-blue-500/20'
                                              : lead.status === 'enriched'
                                                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                                                : lead.status === 'won'
                                                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                                                  : lead.status === 'lost'
                                                    ? 'bg-rose-500/15 text-rose-455 border-rose-500/20'
                                                    : 'bg-gray-800/80 text-gray-450 border border-gray-700/40'
                                      }`}>
                                        {lead.status === 'meeting_scheduled' ? 'meeting' : lead.status}
                                      </span>
                                    </TableCell>
                                  </TableRow>
                                );
                              })
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </Card>
                </div>

                {/* Right Pane: Lead Detail Panel */}
                <div className="lg:col-span-1">
                  {!selectedLead ? (
                    <Card className="glass-panel border-transparent rounded-3xl p-8 text-center flex flex-col items-center justify-center h-[550px] shadow-2xl relative">
                      <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-gray-700 to-transparent" />
                      <div className="text-5xl mb-4">🎯</div>
                      <h3 className="text-base font-bold text-white">No Lead Selected</h3>
                      <p className="text-xs text-gray-455 max-w-[200px] mt-1 leading-relaxed">
                        Select a sales prospect from the list on the left to view enrichment details and actions.
                      </p>
                    </Card>
                  ) : (
                    <Card className="glass-panel border-transparent rounded-3xl p-6 shadow-2xl relative flex flex-col min-h-[600px] overflow-hidden">
                      <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
                      
                      {/* Identity Section */}
                      <div className="flex justify-between items-start mb-6">
                        <div>
                          <h2 className="text-xl font-extrabold text-white leading-tight">{selectedLead.name}</h2>
                          <p className="text-xs text-gray-450 flex items-center gap-1.5 mt-0.5">
                            <Building size={11} className="text-emerald-400" /> {selectedLead.company}
                          </p>
                        </div>
                        <div className="flex flex-col items-end gap-1.5">
                          <span className={`text-[10px] font-mono font-black border px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border-emerald-500/20`}>
                            Score: {selectedLead.score || 50}
                          </span>
                        </div>
                      </div>

                      {/* Detail Body */}
                      <div className="flex-1 space-y-5 overflow-y-auto max-h-[460px] pr-1 custom-scrollbar">
                        
                        {/* Edit Mode Toggle */}
                        <div className="flex justify-between items-center border-b border-gray-800/80 pb-3">
                          <span className="text-[10px] text-gray-400 font-extrabold uppercase tracking-widest">Prospect Details</span>
                          <button
                            onClick={() => {
                              if (isEditingSalesLead) {
                                setIsEditingSalesLead(false);
                              } else {
                                setEditName(selectedLead.name || '');
                                setEditCompany(selectedLead.company || '');
                                setEditPersonalEmail(selectedLead.personal_email || '');
                                setEditCompanyEmail(selectedLead.company_email || '');
                                setEditMobileNo(selectedLead.mobile_no || '');
                                setEditCompanyContactNo(selectedLead.company_contact_no || '');
                                setEditNeedOfWhat(selectedLead.need_of_what || '');
                                setEditHowMuch(selectedLead.how_much || '');
                                setEditWhy(selectedLead.why || '');
                                setEditTargetContext(selectedLead.target_context || '');
                                setEditPriority(selectedLead.priority || 'medium');
                                setEditStatus(selectedLead.status || 'captured');
                                setIsEditingSalesLead(true);
                              }
                            }}
                            className="text-xs text-emerald-400 hover:text-emerald-300 font-bold transition-colors flex items-center gap-1"
                          >
                            {isEditingSalesLead ? <><X size={12} /> Cancel</> : <><Edit2 size={12} /> Edit Details</>}
                          </button>
                        </div>

                        {isEditingSalesLead ? (
                          /* Edit Inline Form */
                          <div className="space-y-4 text-xs">
                            <div className="grid grid-cols-2 gap-2">
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Name</label>
                                <Input value={editName} onChange={e => setEditName(e.target.value)} className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" />
                              </div>
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Company</label>
                                <Input value={editCompany} onChange={e => setEditCompany(e.target.value)} className="bg-gray-955 border-gray-800 h-8 rounded-lg text-white" />
                              </div>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-2">
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Personal Email</label>
                                <Input value={editPersonalEmail} onChange={e => setEditPersonalEmail(e.target.value)} className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" />
                              </div>
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Company Email</label>
                                <Input value={editCompanyEmail} onChange={e => setEditCompanyEmail(e.target.value)} className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" />
                              </div>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Mobile No</label>
                                <Input value={editMobileNo} onChange={e => setEditMobileNo(e.target.value)} className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" />
                              </div>
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Company Contact No</label>
                                <Input value={editCompanyContactNo} onChange={e => setEditCompanyContactNo(e.target.value)} className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" />
                              </div>
                            </div>

                            <div className="space-y-1">
                              <label className="text-[10px] font-bold text-gray-450 uppercase">Need of what</label>
                              <Input value={editNeedOfWhat} onChange={e => setEditNeedOfWhat(e.target.value)} className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" />
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">How Much (Budget)</label>
                                <Input value={editHowMuch} onChange={e => setEditHowMuch(e.target.value)} className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" />
                              </div>
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Priority</label>
                                <Select value={editPriority} onValueChange={val => setEditPriority(val || 'medium')}>
                                  <SelectTrigger className="bg-gray-955 border-gray-800 h-8 text-xs text-gray-300 rounded-lg">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent className="bg-gray-950 border-gray-800 text-gray-300">
                                    <SelectItem value="low">Low</SelectItem>
                                    <SelectItem value="medium">Medium</SelectItem>
                                    <SelectItem value="high">High</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Status Stage</label>
                                <Select value={editStatus} onValueChange={val => setEditStatus(val || 'captured')}>
                                  <SelectTrigger className="bg-gray-950 border-gray-800 h-8 text-xs text-gray-300 rounded-lg">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent className="bg-gray-950 border-gray-800 text-gray-300">
                                    <SelectItem value="captured">Captured</SelectItem>
                                    <SelectItem value="enriched">Enriched</SelectItem>
                                    <SelectItem value="contacted">Contacted</SelectItem>
                                    <SelectItem value="replied">Replied</SelectItem>
                                    <SelectItem value="meeting_scheduled">Meeting Booked</SelectItem>
                                    <SelectItem value="won">Closed Won</SelectItem>
                                    <SelectItem value="lost">Closed Lost</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-450 uppercase">Score (0-100)</label>
                                <Input 
                                  type="number" 
                                  min={0} 
                                  max={100} 
                                  value={editScore} 
                                  onChange={e => setEditScore(Number(e.target.value) || 0)} 
                                  className="bg-gray-950 border-gray-800 h-8 rounded-lg text-white" 
                                />
                              </div>
                            </div>

                            <div className="space-y-1">
                              <label className="text-[10px] font-bold text-gray-450 uppercase">Why (Reason/Pain Point)</label>
                              <Textarea value={editWhy} onChange={e => setEditWhy(e.target.value)} className="bg-gray-950 border-gray-800 text-white rounded-lg text-xs min-h-[60px]" />
                            </div>

                            <div className="space-y-1">
                              <label className="text-[10px] font-bold text-gray-450 uppercase">Target Context</label>
                              <Textarea value={editTargetContext} onChange={e => setEditTargetContext(e.target.value)} className="bg-gray-950 border-gray-800 text-white rounded-lg text-xs min-h-[65px]" />
                            </div>

                            <Button
                              onClick={handleSaveLead}
                              disabled={salesActionLoading}
                              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold h-9 rounded-lg shadow-lg shadow-emerald-500/20"
                            >
                              {salesActionLoading ? 'Saving changes...' : 'Save Prospect Details'}
                            </Button>
                          </div>
                        ) : (
                          /* View Details Mode */
                          <div className="space-y-5">
                            
                            {/* Contact Card */}
                            <div className="space-y-2.5 bg-gray-900/40 p-4 rounded-2xl border border-gray-850">
                              <div className="flex items-center gap-2 text-xs font-bold text-white border-b border-gray-800/60 pb-1.5">
                                <Users size={13} className="text-emerald-400" /> Contact Channels
                              </div>
                              <div className="space-y-1.5 text-xs text-gray-350">
                                <div className="flex justify-between">
                                  <span className="text-[10px] text-gray-450 font-semibold">Personal Email:</span>
                                  <span className="font-mono text-white flex items-center gap-1 select-all">{selectedLead.personal_email || 'Not enriched'}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[10px] text-gray-450 font-semibold">Company Email:</span>
                                  <span className="font-mono text-white flex items-center gap-1 select-all">{selectedLead.company_email || selectedLead.email || 'Not enriched'}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[10px] text-gray-455 font-semibold">Mobile No:</span>
                                  <span className="font-mono text-white select-all">{selectedLead.mobile_no || selectedLead.phone || 'Not enriched'}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-[10px] text-gray-455 font-semibold">Company Contact No:</span>
                                  <span className="font-mono text-white select-all">{selectedLead.company_contact_no || 'Not enriched'}</span>
                                </div>
                              </div>
                            </div>

                            {/* Business Opportunity details */}
                            <div className="space-y-3 bg-gray-900/40 p-4 rounded-2xl border border-gray-850">
                              <div className="flex items-center gap-2 text-xs font-bold text-white border-b border-gray-800/60 pb-1.5">
                                <Target size={13} className="text-emerald-400" /> Business Intent
                              </div>
                              
                              <div className="space-y-3 text-xs">
                                <div>
                                  <span className="text-[10px] text-gray-450 font-bold uppercase block tracking-wide">Need Description</span>
                                  <p className="text-gray-200 mt-1 leading-relaxed">{selectedLead.need_of_what || 'Awaiting sales agent analysis'}</p>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                  <div>
                                    <span className="text-[10px] text-gray-450 font-bold uppercase block tracking-wide">Deal Valuation</span>
                                    <p className="text-emerald-400 font-extrabold mt-0.5">{selectedLead.how_much || 'Under negotiation'}</p>
                                  </div>
                                  <div>
                                    <span className="text-[10px] text-gray-450 font-bold uppercase block tracking-wide">Priority Setting</span>
                                    <span className={`inline-block text-[9px] font-extrabold uppercase px-2 py-0.5 rounded tracking-wide border mt-0.5 ${
                                      selectedLead.priority === 'high' 
                                        ? 'bg-rose-500/10 text-rose-450 border-rose-500/20' 
                                        : selectedLead.priority === 'medium' 
                                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' 
                                          : 'bg-gray-500/10 text-gray-400 border-gray-800'
                                    }`}>
                                      {selectedLead.priority || 'medium'}
                                    </span>
                                  </div>
                                </div>

                                <div>
                                  <span className="text-[10px] text-gray-455 font-bold uppercase block tracking-wide">Pain point context (Why)</span>
                                  <p className="text-gray-300 mt-1 leading-relaxed">{selectedLead.why || 'Awaiting detail enrichment'}</p>
                                </div>

                                <div>
                                  <span className="text-[10px] text-gray-455 font-bold uppercase block tracking-wide">Target Segment Context</span>
                                  <p className="text-gray-300 mt-1 leading-relaxed">{selectedLead.target_context || 'Not enriched yet'}</p>
                                </div>
                              </div>
                            </div>

                            {/* AI Enrichment Insights */}
                            {selectedLead.data?.enrichment?.llm && (
                              <div className="space-y-3 bg-emerald-950/10 p-4 rounded-2xl border border-emerald-500/20 shadow-lg shadow-emerald-500/5 relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-2 text-emerald-400 opacity-20">
                                  <Cpu size={24} />
                                </div>
                                <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 border-b border-emerald-500/20 pb-1.5">
                                  <Sparkles size={13} /> AI Sourcing & Enrichment
                                </div>
                                <div className="space-y-2.5 text-xs">
                                  <div className="grid grid-cols-2 gap-2 text-gray-300">
                                    <div>
                                      <span className="text-[9px] text-gray-450 font-bold uppercase tracking-wider block">Job Title</span>
                                      <span className="font-semibold text-white">{selectedLead.data.enrichment.llm.title || 'N/A'}</span>
                                    </div>
                                    <div>
                                      <span className="text-[9px] text-gray-450 font-bold uppercase tracking-wider block">Industry</span>
                                      <span className="font-semibold text-white">{selectedLead.data.enrichment.llm.industry || 'N/A'}</span>
                                    </div>
                                    <div>
                                      <span className="text-[9px] text-gray-450 font-bold uppercase tracking-wider block">Company Size</span>
                                      <span className="font-semibold text-white">{selectedLead.data.enrichment.llm.company_size || 'N/A'}</span>
                                    </div>
                                    <div>
                                      <span className="text-[9px] text-gray-450 font-bold uppercase tracking-wider block">Confidence Score</span>
                                      <span className="font-mono text-emerald-400 font-bold">★ {selectedLead.score || 50}/100</span>
                                    </div>
                                  </div>

                                  {selectedLead.data.enrichment.llm.pain_points && selectedLead.data.enrichment.llm.pain_points.length > 0 && (
                                    <div>
                                      <span className="text-[9px] text-gray-455 font-bold uppercase tracking-wider block mb-1">Identified Pain Points</span>
                                      <div className="flex flex-wrap gap-1.5">
                                        {selectedLead.data.enrichment.llm.pain_points.map((pt: string, idx: number) => (
                                          <span key={idx} className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded text-[10px] font-medium">
                                            {pt}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {selectedLead.data.enrichment.llm.outreach_angle && (
                                    <div className="bg-emerald-950/20 border border-emerald-500/10 p-2.5 rounded-xl">
                                      <span className="text-[9px] text-emerald-400 font-extrabold uppercase tracking-wider block">Recommended Outreach Angle</span>
                                      <p className="text-gray-300 mt-1 leading-relaxed text-[11px] italic">"{selectedLead.data.enrichment.llm.outreach_angle}"</p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* AI Conversation Analysis */}
                            {selectedLead.data?.reply_classification && (
                              <div className="space-y-3 bg-violet-950/10 p-4 rounded-2xl border border-violet-500/20 shadow-lg shadow-violet-500/5 relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-2 text-violet-400 opacity-20">
                                  <Bot size={24} />
                                </div>
                                <div className="flex items-center gap-2 text-xs font-bold text-violet-400 border-b border-violet-500/20 pb-1.5">
                                  <MessageSquare size={13} /> AI Conversation Analysis
                                </div>
                                <div className="space-y-3.5 text-xs">
                                  <div className="grid grid-cols-2 gap-2 text-gray-300">
                                    <div>
                                      <span className="text-[9px] text-gray-450 font-bold uppercase tracking-wider block">Response Intent</span>
                                      <span className={`inline-block text-[9px] font-extrabold uppercase px-2 py-0.5 rounded tracking-wide border mt-0.5 ${
                                        selectedLead.data.reply_classification.intent === 'interested'
                                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20'
                                          : selectedLead.data.reply_classification.intent === 'decline'
                                            ? 'bg-rose-500/15 text-rose-400 border-rose-500/20'
                                            : 'bg-gray-500/15 text-gray-400 border-gray-800'
                                      }`}>
                                        {selectedLead.data.reply_classification.intent || 'neutral'}
                                      </span>
                                    </div>
                                    {selectedLead.data.reply_classification.suggested_time && (
                                      <div>
                                        <span className="text-[9px] text-gray-455 font-bold uppercase tracking-wider block">Meeting Proposed</span>
                                        <span className="font-semibold text-white flex items-center gap-1 mt-0.5 text-[10px]">
                                          📅 {selectedLead.data.reply_classification.suggested_time}
                                        </span>
                                      </div>
                                    )}
                                  </div>

                                  <div>
                                    <span className="text-[9px] text-gray-450 font-bold uppercase tracking-wider block">Reply Summary</span>
                                    <p className="text-gray-300 mt-1 leading-relaxed">{selectedLead.data.reply_classification.summary || 'N/A'}</p>
                                  </div>

                                  {selectedLead.data.reply_classification.suggested_reply && (
                                    <div className="space-y-2 bg-violet-950/20 border border-violet-500/10 p-3 rounded-xl">
                                      <div className="flex justify-between items-center">
                                        <span className="text-[9px] text-violet-400 font-extrabold uppercase tracking-wider">Suggested AI Auto-Reply</span>
                                        <div className="flex gap-2">
                                          <button
                                            onClick={() => {
                                              navigator.clipboard.writeText(selectedLead.data.reply_classification.suggested_reply);
                                              alert("📋 Suggested reply copied to clipboard!");
                                            }}
                                            className="text-[10px] text-violet-400 hover:text-violet-300 font-bold flex items-center gap-0.5 bg-violet-950/50 px-1.5 py-0.5 rounded border border-violet-800/40"
                                          >
                                            Copy
                                          </button>
                                          <button
                                            onClick={async () => {
                                              if (confirm("Send this suggested AI reply email to the prospect?")) {
                                                setSalesActionLoading(true);
                                                try {
                                                  const res = await fetchWithAuth(`${API_URL}/leads/${selectedLead.id}/timeline-note`, {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({
                                                      content: selectedLead.data.reply_classification.suggested_reply,
                                                      channel: selectedLead.data.outreach_channel || 'email',
                                                      direction: 'outbound'
                                                    })
                                                  });
                                                  if (res.ok) {
                                                    const updated = await res.json();
                                                    setSelectedLead(updated);
                                                    fetchLeads();
                                                    fetchData();
                                                    alert("🚀 Suggested reply sent/logged successfully!");
                                                  } else {
                                                    alert("Failed to send/log reply");
                                                  }
                                                } catch (err) {
                                                  console.error(err);
                                                } finally {
                                                  setSalesActionLoading(false);
                                                }
                                              }
                                            }}
                                            className="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold flex items-center gap-0.5 bg-emerald-950/50 px-1.5 py-0.5 rounded border border-emerald-800/40"
                                          >
                                            Send
                                          </button>
                                        </div>
                                      </div>
                                      <p className="text-gray-250 leading-relaxed text-[11px] whitespace-pre-wrap">{selectedLead.data.reply_classification.suggested_reply}</p>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}

                            {/* Outreach Actions Center */}
                            <div className="space-y-2 bg-gray-900/40 p-4 rounded-2xl border border-gray-850">
                              <div className="flex items-center gap-2 text-xs font-bold text-white border-b border-gray-800/60 pb-1.5">
                                <Activity size={13} className="text-emerald-400" /> Outreach Actions
                              </div>
                              
                              <div className="grid grid-cols-2 gap-2 pt-1">
                                <Button
                                  onClick={() => handleSendSalesOutreach(selectedLead.id)}
                                  disabled={salesActionLoading}
                                  variant="outline"
                                  className="border-gray-800 hover:bg-gray-800 text-white rounded-xl text-xs h-9 bg-transparent shadow"
                                >
                                  {salesActionLoading ? 'Sending...' : '✉️ Send Outreach'}
                                </Button>
                                <Button
                                  onClick={() => handleBookSalesMeeting(selectedLead.id)}
                                  disabled={salesActionLoading}
                                  variant="outline"
                                  className="border-gray-800 hover:bg-gray-800 text-white rounded-xl text-xs h-9 bg-transparent shadow"
                                >
                                  {salesActionLoading ? 'Booking...' : '📅 Book Meeting'}
                                </Button>
                              </div>
                            </div>

                            {/* Log Human Update Form */}
                            <div className="space-y-3 bg-gray-900/40 p-4 rounded-2xl border border-gray-850">
                              <div className="flex items-center gap-2 text-xs font-bold text-white border-b border-gray-800/60 pb-1.5">
                                <MessageSquare size={13} className="text-emerald-400" /> Log Human Update / Note
                              </div>
                              
                              <div className="space-y-2 text-xs">
                                <div className="grid grid-cols-2 gap-2">
                                  <div className="flex flex-col gap-1">
                                    <label className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Channel</label>
                                    <Select value={noteChannel} onValueChange={val => setNoteChannel(val || 'note')}>
                                      <SelectTrigger className="h-8 bg-gray-950 border-gray-800 text-[11px] text-gray-300 rounded-lg">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent className="bg-gray-950 border-gray-850 text-gray-305">
                                        <SelectItem value="note">Internal Note</SelectItem>
                                        <SelectItem value="call">Phone Call</SelectItem>
                                        <SelectItem value="email">Email Interaction</SelectItem>
                                        <SelectItem value="whatsapp">WhatsApp Text</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                  <div className="flex flex-col gap-1">
                                    <label className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Direction</label>
                                    <Select value={noteDirection} onValueChange={val => setNoteDirection(val || 'outbound')}>
                                      <SelectTrigger className="h-8 bg-gray-950 border-gray-800 text-[11px] text-gray-300 rounded-lg">
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent className="bg-gray-950 border-gray-850 text-gray-305">
                                        <SelectItem value="outbound">Outbound Contact</SelectItem>
                                        <SelectItem value="inbound">Inbound Response</SelectItem>
                                        <SelectItem value="internal">Internal Only</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                </div>
                                
                                <div className="space-y-1">
                                  <label className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">Update Details</label>
                                  <Textarea
                                    placeholder="Spoke with prospect, wants demo next week, etc."
                                    value={noteText}
                                    onChange={e => setNoteText(e.target.value)}
                                    className="bg-gray-950 border-gray-800 text-white rounded-lg text-xs min-h-[50px] placeholder:text-gray-600 focus:border-emerald-500 focus:ring-emerald-500/20"
                                  />
                                </div>

                                <Button
                                  onClick={handleLogHumanUpdate}
                                  disabled={salesActionLoading || !noteText.trim()}
                                  className="w-full bg-emerald-650 hover:bg-emerald-600 text-white font-bold h-8 rounded-lg text-xs shadow-md shadow-emerald-500/10"
                                >
                                  {salesActionLoading ? 'Saving...' : 'Log Human Update'}
                                </Button>
                              </div>
                            </div>

                            {/* Conversation timeline history */}
                            <div className="space-y-3">
                              <div className="text-[10px] text-gray-400 font-extrabold uppercase tracking-widest">Outreach History</div>
                              
                              {(!selectedLead.data?.conversation || selectedLead.data.conversation.length === 0) ? (
                                <div className="text-center py-4 bg-gray-900/10 border border-dashed border-gray-800 rounded-2xl text-xs text-gray-500 font-medium">
                                  No outreach sequence started yet.
                                </div>
                              ) : (
                                <div className="space-y-3 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[1px] before:bg-gray-800">
                                  {selectedLead.data.conversation.map((msg: any, index: number) => (
                                    <div key={index} className="flex gap-3 relative z-10 text-xs">
                                      <div className={`h-6.5 w-6.5 rounded-full flex items-center justify-center text-[10px] shadow border ${
                                        msg.direction === 'outbound' 
                                          ? 'bg-blue-600/15 border-blue-500/20 text-blue-400' 
                                          : 'bg-emerald-600/15 border-emerald-500/20 text-emerald-400'
                                      }`}>
                                        ➔
                                      </div>
                                      <div className="flex-1 bg-gray-900/35 border border-gray-850 p-3 rounded-2xl shadow">
                                        <div className="flex justify-between items-center gap-2">
                                          <span className="font-bold text-white capitalize text-[11px] flex items-center gap-1.5">
                                            {msg.direction === 'outbound' ? 'Outbound' : 'Inbound'}
                                            <span className="text-[9px] bg-gray-800 text-gray-455 border border-gray-750 px-1.5 py-0.5 rounded font-mono uppercase">
                                              {msg.channel || 'smtp'}
                                            </span>
                                          </span>
                                          <span className="text-[9px] text-gray-450 font-mono">
                                            {msg.at ? new Date(msg.at).toLocaleDateString() : 'Just now'}
                                          </span>
                                        </div>
                                        {msg.subject && (
                                          <div className="text-[10px] text-emerald-400 font-bold mt-1">Subj: {msg.subject}</div>
                                        )}
                                        <p className="text-[11px] text-gray-300 leading-relaxed mt-1.5 whitespace-pre-wrap">{msg.content}</p>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>

                          </div>
                        )}

                      </div>
                    </Card>
                  )}
                </div>

              </div>
            </div>
  );
}

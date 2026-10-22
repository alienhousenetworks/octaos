'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Building2, Users, Target, ShieldCheck, AlertTriangle, TrendingUp, Sparkles, 
  Send, RefreshCw, Plus, CheckCircle2, XCircle, Search, FileText, DollarSign,
  ChevronRight, ArrowUpRight, Clock, HelpCircle, Layers, Mail, Check, ExternalLink,
  ShieldAlert, ChevronDown
} from 'lucide-react';
import RoomFolderExplorer from '@/components/rooms/room-folder-explorer';
import RoomHeader from '@/components/rooms/room-header';
import { SectionRoomData } from '@/components/rooms/room-access-modal';

interface DealRoomViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  initialRoomSlug?: string;
  activeRoom?: SectionRoomData | null;
}

const DEFAULT_DEAL_ROOM: SectionRoomData = {
  id: 'sales-default',
  name: 'General Sales',
  slug: 'default',
  section: 'sales',
  status: 'active',
  visibility: 'internal_public',
  access_list: [],
  created_at: new Date().toISOString(),
};

export default function DealRoomView({ token, API_URL, fetchWithAuth, initialRoomSlug, activeRoom }: DealRoomViewProps) {
  // Section Room state
  const [rooms, setRooms] = useState<SectionRoomData[]>([]);
  const [roomsLoading, setRoomsLoading] = useState(false);
  const [currentRoomSlug, setCurrentRoomSlug] = useState<string>(activeRoom?.slug || initialRoomSlug || 'default');
  const [currentRoom, setCurrentRoom] = useState<SectionRoomData>(activeRoom || DEFAULT_DEAL_ROOM);
  const [isDirectoryView, setIsDirectoryView] = useState(false);

  useEffect(() => {
    if (activeRoom) {
      setCurrentRoom(activeRoom);
      setCurrentRoomSlug(activeRoom.slug);
      setIsDirectoryView(false);
      fetchDealRooms(activeRoom.slug);
    }
  }, [activeRoom]);

  const [dealRooms, setDealRooms] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [selectedRoom, setSelectedRoom] = useState<any | null>(null);
  const [roomDetailLoading, setRoomDetailLoading] = useState(false);

  // Manager Audit State
  const [managerAudit, setManagerAudit] = useState<any | null>(null);
  const [managerLoading, setManagerLoading] = useState(false);
  const [knowledgeGaps, setKnowledgeGaps] = useState<any[]>([]);

  // Action States
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // New Deal Room Modal State
  const [isNewRoomOpen, setIsNewRoomOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newDomain, setNewDomain] = useState('');
  const [newIndustry, setNewIndustry] = useState('Technology');
  const [newEmployees, setNewEmployees] = useState('250');

  // New Committee Member Modal State
  const [isNewMemberOpen, setIsNewMemberOpen] = useState(false);
  const [newMemberName, setNewMemberName] = useState('');
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberTitle, setNewMemberTitle] = useState('');
  const [newMemberRole, setNewMemberRole] = useState('economic_buyer');

  // Outreach Composer State
  const [composerResult, setComposerResult] = useState<any | null>(null);
  const [isComposerOpen, setIsComposerOpen] = useState(false);

  // Deal Desk Quote State
  const [isQuoteOpen, setIsQuoteOpen] = useState(false);
  const [quoteListPrice, setQuoteListPrice] = useState('25000');
  const [quoteDiscountPct, setQuoteDiscountPct] = useState('10');
  const [quoteResult, setQuoteResult] = useState<any | null>(null);

  const fetchRooms = async () => {
    if (!token) return;
    setRoomsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/rooms/?section=sales`);
      if (res.ok) {
        const data = await res.json();
        setRooms(data);
        if (currentRoomSlug) {
          const match = data.find((r: any) => r.slug === currentRoomSlug);
          if (match) setCurrentRoom(match);
        } else if (data.length > 0 && !isDirectoryView) {
          const defaultRoom = data.find((r: any) => r.slug === 'default') || data[0];
          setCurrentRoom(defaultRoom);
          setCurrentRoomSlug(defaultRoom.slug);
        }
      }
    } catch (err) {
      console.error('Failed to load sales rooms:', err);
    } finally {
      setRoomsLoading(false);
    }
  };

  const handleSelectRoom = (slug: string) => {
    setCurrentRoomSlug(slug);
    const match = rooms.find((r) => r.slug === slug);
    if (match) setCurrentRoom(match);
    setIsDirectoryView(false);
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', `/app/sales/rooms/${slug}`);
    }
    fetchDealRooms(slug);
  };

  const fetchDealRooms = async (slugOverride?: string) => {
    if (!token) return;
    setLoading(true);
    try {
      let url = `${API_URL}/deal-rooms`;
      const queryParams = new URLSearchParams();
      const targetSlug = slugOverride || currentRoomSlug;
      if (targetSlug) queryParams.append('room_slug', targetSlug);
      if (search) queryParams.append('search', search);
      if (stageFilter !== 'all') queryParams.append('stage', stageFilter);
      if (queryParams.toString()) url += `?${queryParams.toString()}`;

      const res = await fetchWithAuth(url);
      if (res.ok) {
        const data = await res.json();
        setDealRooms(data);
      }
    } catch (err) {
      console.error('Failed to fetch deal rooms:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoomDetails = async (roomId: string) => {
    if (!token) return;
    setRoomDetailLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/deal-rooms/${roomId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedRoom(data);
      }
    } catch (err) {
      console.error('Failed to fetch deal room details:', err);
    } finally {
      setRoomDetailLoading(false);
    }
  };

  const runManagerAudit = async () => {
    if (!token) return;
    setManagerLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-manager/daily-audit`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setManagerAudit(data);
      }
      const gapsRes = await fetchWithAuth(`${API_URL}/sales-manager/knowledge-gaps`);
      if (gapsRes.ok) {
        const gapsData = await gapsRes.json();
        setKnowledgeGaps(gapsData.gaps || []);
      }
    } catch (err) {
      console.error('Manager audit failed:', err);
    } finally {
      setManagerLoading(false);
    }
  };

  useEffect(() => {
    fetchRooms();
    fetchDealRooms();
    runManagerAudit();
  }, [stageFilter]);

  const handleCreateDealRoom = async () => {
    if (!newCompanyName || !newDomain) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/deal-rooms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: newCompanyName,
          domain: newDomain,
          industry: newIndustry,
          employee_count: parseInt(newEmployees) || 100,
        }),
      });
      if (res.ok) {
        setIsNewRoomOpen(false);
        setNewCompanyName('');
        setNewDomain('');
        fetchDealRooms();
      }
    } catch (err) {
      console.error('Create deal room error:', err);
    }
  };

  const handleAddCommitteeMember = async () => {
    if (!selectedRoom || !newMemberEmail || !newMemberName) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/deal-rooms/${selectedRoom.id}/committee`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newMemberName,
          email: newMemberEmail,
          title: newMemberTitle,
          role_type: newMemberRole,
        }),
      });
      if (res.ok) {
        setIsNewMemberOpen(false);
        setNewMemberName('');
        setNewMemberEmail('');
        setNewMemberTitle('');
        fetchRoomDetails(selectedRoom.id);
      }
    } catch (err) {
      console.error('Add committee member error:', err);
    }
  };

  const handleQualifyAccount = async (roomId: string) => {
    setActionLoading(true);
    setActionMessage('Running Multi-Factor Qualifier Agent (Fit × Timing × Evidence)...');
    try {
      const res = await fetchWithAuth(`${API_URL}/deal-rooms/${roomId}/qualify`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`Qualification: ${data.decision.toUpperCase()} (Confidence: ${(data.confidence * 100).toFixed(0)}%)`);
        fetchRoomDetails(roomId);
        fetchDealRooms();
      }
    } catch (err) {
      setActionMessage('Failed to qualify account.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResearchAccount = async (roomId: string) => {
    setActionLoading(true);
    setActionMessage('Running Account Researcher Agent (Extracting cited brief)...');
    try {
      const res = await fetchWithAuth(`${API_URL}/deal-rooms/${roomId}/research`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setActionMessage(`Research Complete: ${data.reasoning_summary}`);
        fetchRoomDetails(roomId);
        fetchDealRooms();
      }
    } catch (err) {
      setActionMessage('Failed to research account.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleComposeOutreach = async (roomId: string, memberId?: string) => {
    setActionLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/deal-rooms/${roomId}/compose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          committee_member_id: memberId,
          channel: 'email',
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setComposerResult(data);
        setIsComposerOpen(true);
      }
    } catch (err) {
      console.error('Compose error:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleGenerateQuote = async (roomId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/deal-rooms/${roomId}/quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          list_price: parseFloat(quoteListPrice) || 25000,
          discount_pct: (parseFloat(quoteDiscountPct) || 10) / 100,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setQuoteResult(data);
      }
    } catch (err) {
      console.error('Quote error:', err);
    }
  };

  const getStageBadge = (stage: string) => {
    const s = stage?.toLowerCase() || '';
    if (s.includes('won') || s === 'meeting_booked') {
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
    if (s.includes('cadence') || s.includes('outreach')) {
      return 'bg-indigo-50 text-indigo-700 border-indigo-200';
    }
    if (s.includes('qualified')) {
      return 'bg-blue-50 text-blue-700 border-blue-200';
    }
    if (s.includes('proposal') || s.includes('closing')) {
      return 'bg-purple-50 text-purple-700 border-purple-200';
    }
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  if (!activeRoom && isDirectoryView && rooms.length > 0) {
    return (
      <RoomFolderExplorer
        section="sales"
        sectionTitle="Sales & Deals"
        rooms={rooms}
        loading={roomsLoading}
        onSelectRoom={handleSelectRoom}
        onRefresh={fetchRooms}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onClose={() => setIsDirectoryView(false)}
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300 pb-16">
      {!activeRoom && currentRoom && (
        <RoomHeader
          sectionTitle="Sales & Deals"
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
      )}

      <div className="space-y-5 text-slate-900 px-1">
        {/* ── 1. EXECUTIVE KPI METRIC RIBBON ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Active Deal Rooms */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Active Deal Rooms
            </span>
            <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
              State Machines
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-slate-900">
                {dealRooms.length}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Persistent buyer environments</p>
            </div>
            <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100">
              <Building2 size={16} />
            </div>
          </div>
        </div>

        {/* Metric 2: Calibrated Pipeline Forecast */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Calibrated Forecast
            </span>
            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              Bayesian Weighted
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-emerald-600">
                ${(managerAudit?.data?.total_calibrated_pipeline_usd || 0).toLocaleString()}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Weighted probability ARR</p>
            </div>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100">
              <DollarSign size={16} />
            </div>
          </div>
        </div>

        {/* Metric 3: Multi-Threaded Coverage */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Multi-Threaded Coverage
            </span>
            <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
              &ge; 2 Personas
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-indigo-600">
                {dealRooms.length > 0 
                  ? `${Math.round((dealRooms.filter(r => r.is_multi_threaded).length / dealRooms.length) * 100)}%`
                  : '0%'}
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Stakeholder consensus rate</p>
            </div>
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Users size={16} />
            </div>
          </div>
        </div>

        {/* Metric 4: Risk Inspection & Audit */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Pipeline Risk Inspection
            </span>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={runManagerAudit} 
              disabled={managerLoading} 
              className="h-5 px-1.5 text-[10px] font-bold text-blue-600 hover:text-blue-700 hover:bg-blue-50"
            >
              <RefreshCw className={`w-3 h-3 mr-1 ${managerLoading ? 'animate-spin' : ''}`} /> Run Audit
            </Button>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-extrabold tracking-tight text-amber-600">
                {managerAudit?.data?.stalled_deals_count || 0} At Risk
              </span>
              <p className="text-[11px] text-slate-500 mt-0.5">Stalled &gt; 7 days / single-threaded</p>
            </div>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600 border border-amber-100">
              <AlertTriangle size={16} />
            </div>
          </div>
        </div>
      </div>

      {/* ── ACTION NOTIFICATION BANNER ── */}
      {actionMessage && (
        <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-2xl text-xs font-semibold text-blue-900 flex items-center justify-between shadow-2xs animate-in fade-in">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
            <span>{actionMessage}</span>
          </div>
          <button 
            type="button" 
            onClick={() => setActionMessage(null)} 
            className="text-slate-400 hover:text-slate-700 p-1"
          >
            &times;
          </button>
        </div>
      )}

      {/* ── 2. COMMAND CENTER TOOLBAR & ACTIONS ── */}
      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 w-full sm:w-auto flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
            <Input
              placeholder="Search deal rooms by company name or domain..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchDealRooms()}
              className="pl-9 bg-slate-50 border-slate-200 text-xs h-9 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500 rounded-xl"
            />
          </div>

          <Select value={stageFilter} onValueChange={(val) => val && setStageFilter(val)}>
            <SelectTrigger className="w-[160px] bg-slate-50 border-slate-200 text-slate-800 rounded-xl text-xs h-9">
              <SelectValue placeholder="All Stages" />
            </SelectTrigger>
            <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl rounded-xl">
              <SelectItem value="all">All Stages</SelectItem>
              <SelectItem value="discovered">Discovered</SelectItem>
              <SelectItem value="qualified">Qualified</SelectItem>
              <SelectItem value="outreach_ready">Outreach Ready</SelectItem>
              <SelectItem value="in_cadence">In Cadence</SelectItem>
              <SelectItem value="replied">Replied</SelectItem>
              <SelectItem value="meeting_booked">Meeting Booked</SelectItem>
              <SelectItem value="proposal">Proposal</SelectItem>
              <SelectItem value="closing">Closing</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <Dialog open={isNewRoomOpen} onOpenChange={setIsNewRoomOpen}>
            <DialogTrigger
              render={
                <Button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs h-9 px-3.5 rounded-xl shadow-xs transition-all flex items-center gap-1.5" />
              }
            >
              <Plus size={14} /> New Deal Room
            </DialogTrigger>
            <DialogContent className="bg-white border border-slate-200 text-slate-900 rounded-3xl max-w-lg p-6 shadow-2xl">
              <DialogHeader>
                <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
                  <span className="text-blue-600 font-bold">▎</span>
                  Open Persistent Deal Room
                </DialogTitle>
                <DialogDescription className="text-xs text-slate-500">
                  Initializes a persistent account state machine with buying committee, signals, and deliverability tracking.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3.5 pt-2">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Company Name *</label>
                  <Input 
                    placeholder="e.g. Acme Cloud Corp"
                    value={newCompanyName}
                    onChange={(e) => setNewCompanyName(e.target.value)}
                    className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Domain *</label>
                  <Input 
                    placeholder="e.g. acmecloud.com"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">Industry</label>
                    <Input 
                      value={newIndustry}
                      onChange={(e) => setNewIndustry(e.target.value)}
                      className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-700 block mb-1">Employee Count</label>
                    <Input 
                      value={newEmployees}
                      onChange={(e) => setNewEmployees(e.target.value)}
                      className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                    />
                  </div>
                </div>
                <div className="pt-2 flex justify-end gap-2">
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={() => setIsNewRoomOpen(false)}
                    className="text-xs rounded-xl border-slate-200 text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleCreateDealRoom} 
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl px-5 shadow-xs"
                  >
                    Initialize Deal Room
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* ── 3. MAIN SPLIT VIEW: ROOMS TABLE & 360° INSPECTOR ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Deal Rooms List */}
        <div className={selectedRoom ? 'lg:col-span-5 space-y-3' : 'lg:col-span-12 space-y-3'}>
          <div className="bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-xs">
            <div className="px-4 py-3 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Accounts in Deal Rooms ({dealRooms.length})
              </span>
              <span className="text-[11px] text-slate-500">
                Click any row to inspect buyer consensus
              </span>
            </div>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-slate-50">
                  <TableRow className="border-b border-slate-200 text-slate-600 font-bold">
                    <TableHead className="text-slate-600 font-bold text-[11px] uppercase tracking-wider py-2.5 px-3.5">Account</TableHead>
                    <TableHead className="text-slate-600 font-bold text-[11px] uppercase tracking-wider py-2.5 px-3">Stage</TableHead>
                    <TableHead className="text-slate-600 font-bold text-[11px] uppercase tracking-wider py-2.5 px-3">Threading</TableHead>
                    <TableHead className="text-slate-600 font-bold text-[11px] uppercase tracking-wider py-2.5 px-3">Priority Index</TableHead>
                    <TableHead className="text-slate-600 font-bold text-[11px] uppercase tracking-wider py-2.5 px-3 text-right">Inspect</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-slate-100">
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-12 text-slate-500 text-xs">
                        Loading persistent deal rooms...
                      </TableCell>
                    </TableRow>
                  ) : dealRooms.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-12 text-slate-500 text-xs">
                        No Deal Rooms found. Initialize a room to begin multi-threaded account execution.
                      </TableCell>
                    </TableRow>
                  ) : (
                    dealRooms.map((r) => {
                      const isSelected = selectedRoom?.id === r.id;
                      return (
                        <TableRow 
                          key={r.id} 
                          onClick={() => fetchRoomDetails(r.id)}
                          className={`cursor-pointer transition-colors ${
                            isSelected 
                              ? 'bg-blue-50/70 border-l-4 border-l-blue-600 font-medium' 
                              : 'hover:bg-slate-50/80'
                          }`}
                        >
                          <TableCell className="py-3 px-3.5">
                            <div className="font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                              {r.company_name}
                            </div>
                            <div className="text-[11px] text-slate-500 font-mono mt-0.5">{r.domain}</div>
                          </TableCell>
                          <TableCell className="py-3 px-3">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${getStageBadge(r.stage)}`}>
                              {r.stage?.replace(/_/g, ' ') || 'Discovered'}
                            </span>
                          </TableCell>
                          <TableCell className="py-3 px-3">
                            {r.is_multi_threaded ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full">
                                <ShieldCheck className="w-3 h-3 text-indigo-600" /> Multi-Threaded
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                                <AlertTriangle className="w-3 h-3 text-amber-600" /> Single-Threaded
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="py-3 px-3">
                            <div className="flex items-center gap-2">
                              <div className="w-12 bg-slate-200 h-2 rounded-full overflow-hidden">
                                <div 
                                  className="bg-blue-600 h-full rounded-full" 
                                  style={{ width: `${Math.min(100, Math.round((r.priority_index || 0) * 100))}%` }}
                                />
                              </div>
                              <span className="text-[11px] font-mono font-bold text-slate-700">
                                {((r.priority_index || 0)).toFixed(2)}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="py-3 px-3 text-right">
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              className="h-7 w-7 p-0 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                              onClick={(e) => {
                                e.stopPropagation();
                                fetchRoomDetails(r.id);
                              }}
                            >
                              <ChevronRight className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>

        {/* Selected Deal Room Detail Inspector */}
        {selectedRoom && (
          <div className="lg:col-span-7 space-y-4">
            <Card className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
              <CardHeader className="bg-slate-50/80 p-5 border-b border-slate-200">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <CardTitle className="text-lg font-bold text-slate-900">
                        {selectedRoom.company_name}
                      </CardTitle>
                      {selectedRoom.domain && (
                        <span className="text-[11px] px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700 font-mono font-semibold">
                          {selectedRoom.domain}
                        </span>
                      )}
                    </div>
                    <CardDescription className="text-xs text-slate-500 mt-1">
                      {selectedRoom.industry || 'Technology'} &bull; {selectedRoom.employee_count || '100+'} employees &bull; Calibrated Win Prob: <strong className="text-slate-800">{Math.round((selectedRoom.calibrated_win_prob || 0) * 100)}%</strong>
                    </CardDescription>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleQualifyAccount(selectedRoom.id)}
                      disabled={actionLoading}
                      className="border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold rounded-xl text-slate-700 h-8"
                    >
                      <Target className="w-3.5 h-3.5 mr-1 text-blue-600" /> Qualify
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleResearchAccount(selectedRoom.id)}
                      disabled={actionLoading}
                      className="border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold rounded-xl text-slate-700 h-8"
                    >
                      <Sparkles className="w-3.5 h-3.5 mr-1 text-indigo-600" /> Research
                    </Button>
                    <Button 
                      variant="default" 
                      size="sm" 
                      onClick={() => handleComposeOutreach(selectedRoom.id)}
                      disabled={actionLoading}
                      className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl h-8 shadow-xs"
                    >
                      <Send className="w-3.5 h-3.5 mr-1" /> Outreach
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-5 p-5 text-slate-900">
                {/* Risk Flags & Next Best Action Directive */}
                <div className="p-4 bg-blue-50/60 rounded-xl border border-blue-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="text-[11px] uppercase tracking-wider font-bold text-blue-700 flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5 text-blue-600" /> Next Best Action
                    </div>
                    <div className="text-sm font-extrabold text-slate-900 mt-0.5">
                      {selectedRoom.next_best_action?.action 
                        ? selectedRoom.next_best_action.action.replace(/_/g, ' ').toUpperCase()
                        : 'CONDUCT MULTI-THREADING OUTREACH'}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5">
                      {selectedRoom.next_best_action?.reason || 'Multi-thread to economic buyer and champion personas to build consensus.'}
                    </div>
                  </div>

                  {selectedRoom.risk_flags && selectedRoom.risk_flags.length > 0 && (
                    <div className="flex flex-wrap gap-1 justify-start sm:justify-end max-w-xs shrink-0">
                      {selectedRoom.risk_flags.map((flag: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 border border-amber-200 text-amber-800">
                          {flag.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Buying Committee Map */}
                <div>
                  <div className="flex items-center justify-between mb-2.5">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                      <span className="w-1.5 h-3 bg-indigo-600 rounded-sm" />
                      Buying Committee ({(selectedRoom.committee || []).length} Stakeholders)
                    </h4>
                    
                    <Dialog open={isNewMemberOpen} onOpenChange={setIsNewMemberOpen}>
                      <DialogTrigger
                        render={
                          <Button variant="ghost" size="sm" className="h-6 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50" />
                        }
                      >
                        <Plus className="w-3.5 h-3.5 mr-1" /> Add Stakeholder
                      </DialogTrigger>
                      <DialogContent className="bg-white border border-slate-200 text-slate-900 rounded-3xl max-w-lg p-6 shadow-2xl">
                        <DialogHeader>
                          <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
                            <span className="text-blue-600 font-bold">▎</span>
                            Add Buying Committee Member
                          </DialogTitle>
                          <DialogDescription className="text-xs text-slate-500">
                            Add an executive or influencer to this account's multi-threading consensus map.
                          </DialogDescription>
                        </DialogHeader>

                        <div className="space-y-3.5 pt-2">
                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">Full Name *</label>
                            <Input 
                              value={newMemberName} 
                              onChange={(e) => setNewMemberName(e.target.value)} 
                              placeholder="e.g. Sarah Jenkins"
                              className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                            />
                          </div>
                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">Work Email *</label>
                            <Input 
                              value={newMemberEmail} 
                              onChange={(e) => setNewMemberEmail(e.target.value)} 
                              placeholder="e.g. sjenkins@company.com"
                              className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                            />
                          </div>
                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">Job Title</label>
                            <Input 
                              value={newMemberTitle} 
                              onChange={(e) => setNewMemberTitle(e.target.value)} 
                              placeholder="e.g. Chief Revenue Officer"
                              className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                            />
                          </div>
                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">Role Type</label>
                            <Select value={newMemberRole} onValueChange={(val) => val && setNewMemberRole(val)}>
                              <SelectTrigger className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent className="bg-white border-slate-200 text-slate-900 rounded-xl shadow-xl">
                                <SelectItem value="economic_buyer">Economic Buyer (Budget Owner)</SelectItem>
                                <SelectItem value="champion">Champion (Internal Advocate)</SelectItem>
                                <SelectItem value="influencer">Influencer</SelectItem>
                                <SelectItem value="technical">Technical / Security Evaluator</SelectItem>
                                <SelectItem value="gatekeeper">Gatekeeper</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="pt-2 flex justify-end gap-2">
                            <Button 
                              type="button" 
                              variant="outline" 
                              onClick={() => setIsNewMemberOpen(false)}
                              className="text-xs rounded-xl border-slate-200 text-slate-700 hover:bg-slate-50"
                            >
                              Cancel
                            </Button>
                            <Button 
                              onClick={handleAddCommitteeMember} 
                              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl px-5 shadow-xs"
                            >
                              Add Stakeholder
                            </Button>
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {(selectedRoom.committee || []).length === 0 ? (
                      <div className="col-span-2 p-6 border border-dashed border-slate-200 rounded-xl text-center text-xs text-slate-500 bg-slate-50/50">
                        No committee members mapped yet. Add stakeholders or run Lead Discovery to auto-populate.
                      </div>
                    ) : (
                      selectedRoom.committee.map((m: any) => (
                        <div key={m.id} className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-200 flex items-start justify-between gap-2 shadow-2xs hover:bg-slate-50 transition-all">
                          <div>
                            <div className="font-bold text-xs text-slate-900">{m.name}</div>
                            <div className="text-[11px] text-slate-500 mt-0.5">{m.title}</div>
                            <div className="text-[11px] text-blue-600 font-mono mt-1">{m.email}</div>
                            <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-white border border-slate-200 text-slate-700">
                                {m.role_type?.replace(/_/g, ' ')}
                              </span>
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                m.engagement_state === 'replied' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                                m.engagement_state === 'contacted' ? 'bg-indigo-50 text-indigo-700 border border-indigo-200' :
                                'bg-slate-100 text-slate-600'
                              }`}>
                                {m.engagement_state}
                              </span>
                            </div>
                          </div>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => handleComposeOutreach(selectedRoom.id, m.id)}
                            className="h-7 px-2 text-[11px] font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg shrink-0"
                          >
                            <Send className="w-3 h-3 mr-1" /> Outreach
                          </Button>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Executive Intelligence Brief & Pain Hypotheses */}
                {selectedRoom.account_brief && (
                  <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200 space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                      <span className="w-1.5 h-3 bg-blue-600 rounded-sm" />
                      Executive Intelligence Brief
                    </h4>
                    <p className="text-xs text-slate-700 leading-relaxed">
                      {selectedRoom.account_brief.executive_summary || 'Brief compiled from verified primary sources, search signals, and technographics.'}
                    </p>
                    
                    {selectedRoom.pain_hypotheses && selectedRoom.pain_hypotheses.length > 0 && (
                      <div className="space-y-1.5 pt-2">
                        <div className="text-[11px] uppercase font-bold text-slate-500">Identified Pain Hypotheses</div>
                        {selectedRoom.pain_hypotheses.map((p: any, idx: number) => (
                          <div key={idx} className="p-2.5 bg-white rounded-lg border border-slate-200 text-xs shadow-2xs">
                            <span className="font-bold text-slate-900">{p.signal}:</span> <span className="text-slate-600">{p.inference}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Deal Desk Quoting & Governance */}
                <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                  <div className="text-xs text-slate-500">
                    Deal Desk Governance: Max discount cap enforced by policy
                  </div>
                  <Dialog open={isQuoteOpen} onOpenChange={setIsQuoteOpen}>
                    <DialogTrigger
                      render={
                        <Button variant="outline" size="sm" className="border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold rounded-xl h-8 text-slate-700" />
                      }
                    >
                      <DollarSign className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Generate Quote
                    </DialogTrigger>
                    <DialogContent className="bg-white border border-slate-200 text-slate-900 rounded-3xl max-w-lg p-6 shadow-2xl">
                      <DialogHeader>
                        <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
                          <span className="text-blue-600 font-bold">▎</span>
                          Deal Desk Quote Generator
                        </DialogTitle>
                        <DialogDescription className="text-xs text-slate-500">
                          Enforces discount thresholds, payment terms, and executive approval policy rules.
                        </DialogDescription>
                      </DialogHeader>

                      <div className="space-y-3.5 pt-2">
                        <div>
                          <label className="text-xs font-semibold text-slate-700 block mb-1">Base List Price ($ USD)</label>
                          <Input 
                            value={quoteListPrice} 
                            onChange={(e) => setQuoteListPrice(e.target.value)} 
                            className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="text-xs font-semibold text-slate-700 block mb-1">Requested Discount (%)</label>
                          <Input 
                            value={quoteDiscountPct} 
                            onChange={(e) => setQuoteDiscountPct(e.target.value)} 
                            className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl focus:bg-white focus:border-blue-500"
                          />
                        </div>

                        <Button 
                          onClick={() => handleGenerateQuote(selectedRoom.id)} 
                          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl h-9 shadow-xs"
                        >
                          Calculate Quote &amp; Verify Governance
                        </Button>

                        {quoteResult && (
                          <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2 mt-2">
                            <div className="flex justify-between items-center font-bold">
                              <span className="text-slate-600">Net Contract Amount:</span>
                              <span className="text-emerald-700 text-sm font-extrabold">${quoteResult.net_amount?.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-slate-600">Governance Status:</span>
                              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                quoteResult.status === 'approved' 
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                                  : 'bg-amber-50 text-amber-700 border border-amber-200'
                              }`}>
                                {quoteResult.status?.toUpperCase()}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* ── 4. EVIDENCE-GROUNDED OUTREACH COMPOSER DIALOG ── */}
      <Dialog open={isComposerOpen} onOpenChange={setIsComposerOpen}>
        <DialogContent className="bg-white border border-slate-200 text-slate-900 rounded-3xl max-w-2xl p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
              <span className="text-blue-600 font-bold">▎</span>
              <Sparkles className="w-4 h-4 text-blue-600" />
              Evidence-Grounded Outreach Draft
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500">
              Generated copy grounded strictly in verified primary source evidence and decay-calibrated buying signals.
            </DialogDescription>
          </DialogHeader>

          {composerResult && (
            <div className="space-y-4 pt-2">
              {/* Groundedness Gate Badge */}
              <div className="flex items-center justify-between p-3.5 bg-emerald-50/70 rounded-xl border border-emerald-200">
                <div className="flex items-center gap-2.5">
                  {composerResult.decision === 'ready' ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                  )}
                  <div>
                    <div className="text-xs font-bold text-slate-900">
                      Groundedness Score: {Math.round((composerResult.confidence || 0) * 100)}%
                    </div>
                    <div className="text-[11px] text-slate-600 mt-0.5">
                      {composerResult.decision === 'ready' 
                        ? 'All claims verified against Primary Source evidence. Approved for dispatch.'
                        : 'Ungrounded claims detected. Human review required before sending.'}
                    </div>
                  </div>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                  composerResult.decision === 'ready' 
                    ? 'bg-emerald-600 text-white' 
                    : 'bg-amber-600 text-white'
                }`}>
                  {composerResult.decision.toUpperCase()}
                </span>
              </div>

              {/* Message Draft Fields */}
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Subject Line</label>
                  <Input 
                    value={composerResult.data?.subject || ''} 
                    readOnly 
                    className="bg-slate-50 border-slate-200 text-xs text-slate-900 font-semibold rounded-xl"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">Email Body</label>
                  <Textarea 
                    value={composerResult.data?.body || ''} 
                    readOnly 
                    rows={6}
                    className="bg-slate-50 border-slate-200 text-xs text-slate-900 rounded-xl leading-relaxed"
                  />
                </div>
              </div>

              {/* Citations & Evidence Records */}
              {composerResult.evidence && composerResult.evidence.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] uppercase font-bold text-slate-500">Verified Evidence Citations</div>
                  <div className="space-y-1 max-h-24 overflow-y-auto pr-1">
                    {composerResult.evidence.map((ev: any, idx: number) => (
                      <div key={idx} className="p-2 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-700">
                        <span className="text-blue-600 font-mono font-bold">[{ev.source || 'Verified Source'}]:</span> {ev.claim}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <Button 
                  variant="outline" 
                  onClick={() => setIsComposerOpen(false)} 
                  className="text-xs rounded-xl border-slate-200 text-slate-700 hover:bg-slate-50"
                >
                  Close
                </Button>
                <Button 
                  disabled={composerResult.decision !== 'ready'} 
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl px-4 shadow-xs"
                >
                  <Send className="w-3.5 h-3.5 mr-1" /> Dispatch to Cadence
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      </div>
    </div>
  );
}

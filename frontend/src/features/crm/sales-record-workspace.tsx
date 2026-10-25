'use client';

import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Lock, Send, Sparkles, Building, CheckCircle, FileText, Check, Zap, Calculator } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { notify } from '@/lib/notify';
import { CopilotAdvice, SalesTerminology, SHARED_TERMS, VerticalPack } from './sales-platform';
import { Lead } from './sales-types';

interface SalesRecordWorkspaceProps {
  lead: Lead;
  activePack?: VerticalPack | null;
  terms: SalesTerminology;
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  actionLoading: boolean;
  onBack: () => void;
  onSave: (leadId: string, updates: Partial<Lead>) => Promise<void>;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onGenerateDraft: (leadId: string, instructions: string) => Promise<{ subject: string; body: string } | null>;
  onBookMeeting: (leadId: string, suggestedTime: string) => Promise<void>;
  onOpenDealDesk: () => void;
  onLogNote: (leadId: string, content: string, channel: string, direction: string) => Promise<void>;
  onSendDraft: (leadId: string, subject: string, body: string) => Promise<void>;
  onDelete: (leadId: string) => Promise<void>;
}

type Pane = 'contact' | 'record' | 'copilot';
type Tab = 'overview' | 'property' | 'activity' | 'sales' | 'history';

export default function SalesRecordWorkspace({
  lead,
  activePack,
  terms,
  API_URL,
  fetchWithAuth,
  actionLoading,
  onBack,
  onSave,
  onUpdateStatus,
  onGenerateDraft,
  onBookMeeting,
  onOpenDealDesk,
  onLogNote,
  onSendDraft,
  onDelete,
}: SalesRecordWorkspaceProps) {
  const [pane, setPane] = useState<Pane>('record');
  const [tab, setTab] = useState<Tab>('overview');
  const [advice, setAdvice] = useState<CopilotAdvice | null>(null);
  const [meetingTime, setMeetingTime] = useState('');

  const isRealEstate = (activePack?.id === 'real_estate' || advice?.pack?.id === 'real_estate');

  const availableStages = React.useMemo(() => {
    if (activePack?.pipeline_stages && activePack.pipeline_stages.length > 0) {
      return activePack.pipeline_stages.map((s) => ({ id: s.id, label: s.label }));
    }
    if (activePack?.stages && activePack.stages.length > 0) {
      return activePack.stages.map((st) => ({
        id: st.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, ''),
        label: st,
      }));
    }
    if (isRealEstate) {
      return [
        { id: 'inquiry', label: 'New Inquiry' },
        { id: 'qualified', label: 'Buyer Qualified' },
        { id: 'site_visit', label: 'Site Visit Scheduled' },
        { id: 'hold_requested', label: 'Hold Requested' },
        { id: 'booking', label: 'Confirmed Booking' },
        { id: 'cancelled', label: 'Cancelled / Lost' },
      ];
    }
    return [
      { id: 'new', label: 'New' },
      { id: 'qualified', label: 'Qualified' },
      { id: 'contacted', label: 'Contacted' },
      { id: 'meeting_scheduled', label: 'Meeting Scheduled' },
      { id: 'closed_won', label: 'Closed Won' },
      { id: 'closed_lost', label: 'Closed Lost' },
    ];
  }, [activePack, isRealEstate]);
  const [copilotError, setCopilotError] = useState<string | null>(null);
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [question, setQuestion] = useState('What should we do next with this customer?');
  const [name, setName] = useState(lead.name || '');
  const [company, setCompany] = useState(lead.company || '');
  const [email, setEmail] = useState(lead.email || '');
  const [phone, setPhone] = useState(lead.phone || '');
  const [why, setWhy] = useState(lead.why || '');
  const [note, setNote] = useState('');
  const [confirmMeeting, setConfirmMeeting] = useState(false);
  const [confirmSend, setConfirmSend] = useState(false);
  const [visits, setVisits] = useState<any[]>([]);
  const [broker, setBroker] = useState<any | null>(null);
  const [visitDate, setVisitDate] = useState('');
  const [visitAgent, setVisitAgent] = useState('');
  const [visitScheduling, setVisitScheduling] = useState(false);
  const [autoAssigning, setAutoAssigning] = useState(false);
  const [autoAssignMessage, setAutoAssignMessage] = useState<string | null>(null);
  const [brokerName, setBrokerName] = useState(lead.data?.channel_partner?.brokerage_name || '');
  const [brokerRera, setBrokerRera] = useState(lead.data?.channel_partner?.rera_id || '');
  const [brokerCommission, setBrokerCommission] = useState(String(lead.data?.channel_partner?.commission_pct || '2.0'));
  const [matches, setMatches] = useState<any[]>([]);
  const [matchesLoading, setMatchesLoading] = useState(false);
  const [bookings, setBookings] = useState<any[]>([]);
  const [bookingUnitId, setBookingUnitId] = useState<string | null>(null);
  const [bookingPrice, setBookingPrice] = useState('');
  const [bookingBuyerName, setBookingBuyerName] = useState('');
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [activeCostSheetUnitId, setActiveCostSheetUnitId] = useState<string | null>(null);
  const [costSheetData, setCostSheetData] = useState<any | null>(null);
  const [costSheetLoading, setCostSheetLoading] = useState(false);
  const [costSheetPlanType, setCostSheetPlanType] = useState('construction_linked');
  const [draftPreview, setDraftPreview] = useState<{ subject: string; body: string } | null>(
    lead.data?.draft_subject || lead.data?.draft_body
      ? { subject: lead.data?.draft_subject || '', body: lead.data?.draft_body || '' }
      : null
  );


  useEffect(() => {
    setName(lead.name || '');
    setCompany(lead.company || '');
    setEmail(lead.email || '');
    setPhone(lead.phone || '');
    setWhy(lead.why || '');
    setConfirmMeeting(false);
    setDraftPreview(
      lead.data?.draft_subject || lead.data?.draft_body
        ? { subject: lead.data?.draft_subject || '', body: lead.data?.draft_body || '' }
        : null
    );
  }, [lead.id, lead.name, lead.company, lead.email, lead.phone, lead.why, lead.data?.draft_subject, lead.data?.draft_body]);

  const ask = async (text: string) => {
    setCopilotLoading(true);
    setCopilotError(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/copilot/record`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_id: lead.id, question: text }),
      });
      if (!res.ok) {
        setAdvice(null);
        setCopilotError(res.status === 404 ? 'This record is not in the current workspace.' : 'The copilot is unavailable. No recommendation was invented.');
        return;
      }
      setAdvice(await res.json());
    } catch {
      setAdvice(null);
      setCopilotError('The copilot is unavailable. No recommendation was invented.');
    } finally {
      setCopilotLoading(false);
    }
  };

  const loadRealEstateData = async () => {
    try {
      const [vRes, bRes, bkRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/sales-os/real-estate/leads/${lead.id}/visits`),
        fetchWithAuth(`${API_URL}/sales-os/real-estate/leads/${lead.id}/broker`),
        fetchWithAuth(`${API_URL}/sales-os/real-estate/bookings?lead_id=${lead.id}`),
      ]);
      if (vRes.ok) setVisits(await vRes.json());
      if (bRes.ok) {
        const bData = await bRes.json();
        setBroker(bData);
        if (bData) {
          setBrokerName(bData.brokerage_name || '');
          setBrokerRera(bData.rera_id || '');
          setBrokerCommission(String(bData.commission_pct || '2.0'));
        }
      }
      if (bkRes.ok) {
        setBookings(await bkRes.json());
      }
    } catch {
      // Ignore if endpoints not queried or non-real estate
    }
  };

  useEffect(() => {
    void ask('What should we do next with this customer?');
    void loadRealEstateData();
    // Reload when the open record changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lead.id]);

  const handleScheduleVisit = async () => {
    if (!visitDate) return;
    setVisitScheduling(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/leads/${lead.id}/visits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: lead.company || 'default_project',
          scheduled_at: new Date(visitDate).toISOString(),
          assigned_agent: visitAgent || undefined,
        }),
      });
      if (res.ok) {
        setVisitDate('');
        setVisitAgent('');
        await loadRealEstateData();
      }
    } finally {
      setVisitScheduling(false);
    }
  };

  const handleAutoAssignVisit = async () => {
    setAutoAssigning(true);
    setAutoAssignMessage(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-real-estate/leads/${lead.id}/auto-assign-visit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferred_time: visitDate ? new Date(visitDate).toISOString() : undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const specialist = data.matched_salesperson?.name || 'Assigned Specialist';
        setAutoAssignMessage(`Successfully scheduled showing with ${specialist} (${data.project_name || 'Project'})`);
        setVisitDate('');
        setVisitAgent('');
        await loadRealEstateData();
      } else {
        const err = await res.json().catch(() => ({}));
        setAutoAssignMessage(err.detail || 'Autonomous dispatch could not find an available assigned specialist.');
      }
    } catch {
      setAutoAssignMessage('Autonomous dispatch encountered a network error.');
    } finally {
      setAutoAssigning(false);
    }
  };

  const handleSaveBroker = async () => {
    if (!brokerName.trim()) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/leads/${lead.id}/broker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brokerage_name: brokerName.trim(),
          rera_id: brokerRera.trim() || undefined,
          commission_pct: parseFloat(brokerCommission) || 2.0,
        }),
      });
      if (res.ok) {
        await loadRealEstateData();
      }
    } catch {
      // Ignore
    }
  };

  const handleFindMatches = async () => {
    setMatchesLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/inquiries/${lead.id}/matches?limit=4`);
      if (res.ok) {
        const data = await res.json();
        setMatches(data.top_matches || []);
      }
    } catch {
      // Ignore
    } finally {
      setMatchesLoading(false);
    }
  };

  const handleLoadCostSheet = async (unitId: string, planType: string = costSheetPlanType) => {
    setActiveCostSheetUnitId(unitId);
    setCostSheetLoading(true);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/sales-os/real-estate/cost-sheets/calculate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            unit_id: unitId,
            lead_id: lead.id,
            payment_plan_type: planType,
          }),
        }
      );
      if (res.ok) {
        setCostSheetData(await res.json());
      } else {
        const err = await res.json().catch(() => ({}));
        notify.error(err.detail || 'Failed to calculate cost sheet');
      }
    } catch (err: any) {
      notify.error(err.message || 'Error calculating cost sheet');
    } finally {
      setCostSheetLoading(false);
    }
  };

  const handleApplyCostSheetToBooking = (cs: any) => {
    setBookingUnitId(cs.unit_id);
    setBookingPrice(String(cs.gross_consideration));
    setBookingBuyerName(lead.name || '');
    setActiveCostSheetUnitId(null);
    notify.success(`CPQ Price of ₹${Number(cs.gross_consideration).toLocaleString()} pre-filled for Booking!`);
  };

  const handleQuickHoldUnit = async (unitId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/units/${unitId}/hold`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id: lead.id,
          deposit_amount: 10000,
          notes: 'Standard 48-hour reservation from workspace matching',
        }),
      });
      if (res.ok) {
        await handleFindMatches();
        await onUpdateStatus(lead.id, 'hold_requested');
      }
    } catch {
      // Ignore
    }
  };

  const handleCreateBookingSubmit = async (unitId: string, basePrice: number) => {
    setBookingSubmitting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/real-estate/bookings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id: lead.id,
          unit_id: unitId,
          agreed_price: parseFloat(bookingPrice) || basePrice,
          buyer_legal_name: bookingBuyerName.trim() || lead.name || 'Purchaser',
          deposit_paid: 50000,
        }),
      });
      if (res.ok) {
        setBookingUnitId(null);
        setBookingPrice('');
        setBookingBuyerName('');
        await loadRealEstateData();
        await onUpdateStatus(lead.id, 'booking');
      }
    } catch {
      // Ignore
    } finally {
      setBookingSubmitting(false);
    }
  };


  const labels = advice?.terminology || terms || SHARED_TERMS;
  const conversation = Array.isArray(lead.data?.conversation) ? lead.data.conversation : [];
  const title = `${lead.name || 'Unnamed record'}${lead.company ? ` · ${lead.company}` : ''}`;

  const runAction = async (id: string) => {
    if (id === 'schedule_site_visit' || id === 'request_unit_hold' || id === 'verify_financing') {
      setTab('property');
      setPane('record');
      return;
    }
    if (id === 'review_follow_up') {
      setTab('sales');
      setPane('record');
      if (!draftPreview?.body) {
        const draft = await onGenerateDraft(lead.id, 'Draft a follow-up from stored facts only. Do not invent metrics.');
        if (draft) setDraftPreview(draft);
      }
      return;
    }
    if (id === 'prepare_proposal') {
      onOpenDealDesk();
      return;
    }
    if (id === 'schedule_meeting') {
      setConfirmMeeting(true);
      setPane('copilot');
    }
  };

  return (
    <div className="space-y-3">
      <header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <button type="button" onClick={onBack} className="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft size={14} /> Back to {labels.leads.toLowerCase()}
          </button>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            {[lead.status || 'No status', lead.source || 'No source', lead.priority || 'No priority'].join(' · ')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            onClick={() => onSave(lead.id, { name, company, email, phone, why })}
            disabled={actionLoading}
          >
            {actionLoading ? <Loader2 className="animate-spin" size={14} /> : <Lock size={14} />} Save
          </Button>
          <Button type="button" variant="outline" disabled={actionLoading} onClick={() => void onDelete(lead.id)}>
            Delete
          </Button>
        </div>
      </header>

      <div className="flex gap-2 xl:hidden">
        {(['contact', 'record', 'copilot'] as Pane[]).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setPane(item)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${pane === item ? 'bg-primary text-primary-foreground' : 'border border-border text-muted-foreground'}`}
          >
            {item === 'contact' ? 'Contact' : item === 'record' ? 'Record' : 'Copilot'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
        <aside className={`${pane === 'contact' ? 'block' : 'hidden'} space-y-3 xl:block`}>
          <Panel>
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-border text-lg">
                {(lead.name || '?').slice(0, 1).toUpperCase()}
              </div>
              <h2 className="mt-2 font-semibold">Contact card</h2>
              <p className="text-xs text-muted-foreground">Details and channels</p>
            </div>
            <Field label="Name" value={name} onChange={setName} />
            <Field label="Company" value={company} onChange={setCompany} />
            <Field label="Email" value={email} onChange={setEmail} />
            <Field label="Phone" value={phone} onChange={setPhone} />
          </Panel>
          <Panel>
            <h2 className="font-semibold">Next-best action</h2>
            <p className="text-sm text-muted-foreground">{advice?.recommendation || 'Ask the copilot. Nothing runs until you confirm.'}</p>
          </Panel>
          <Panel>
            <h2 className="font-semibold">Enrichment</h2>
            <p className="text-sm text-muted-foreground">
              {lead.data?.evidence_url || lead.evidence_url
                ? `Source URL stored: ${lead.data?.evidence_url || lead.evidence_url}`
                : 'No enrichment source is stored on this record.'}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {lead.freshness?.freshness_label
                ? `Freshness label stored: ${lead.freshness.freshness_label}`
                : 'No freshness label is stored.'}
            </p>
          </Panel>
        </aside>

        <section className={`${pane === 'record' ? 'block' : 'hidden'} space-y-3 xl:block`}>
          <div className="flex flex-wrap gap-2">
            {(isRealEstate
              ? (['overview', 'property', 'activity', 'sales', 'history'] as Tab[])
              : (['overview', 'activity', 'sales', 'history'] as Tab[])
            ).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setTab(item)}
              className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${tab === item ? 'bg-[#2563eb] text-white' : 'bg-muted text-muted-foreground'}`}
            >
              {item === 'property' ? 'Property & Showings' : item}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Metric
            title={advice?.readiness.label || 'Readiness'}
            value={advice?.readiness.value || '—'}
            note={advice?.readiness.note || 'Waiting for the copilot.'}
          />
          <Metric
            title={advice?.deal_health.label || 'Deal health'}
            value={advice?.deal_health.value || '—'}
            note={advice?.deal_health.note || 'Status comes from the record.'}
          />
        </div>
        {tab === 'overview' ? (
          <Panel>
            <h2 className="font-semibold">{labels.account} / {labels.opportunity} details</h2>
            <label className="mt-3 block text-xs text-muted-foreground">Why this record</label>
            <Textarea value={why} onChange={(event) => setWhy(event.target.value)} className="mt-1" />
            <label className="mt-3 block text-xs text-muted-foreground">Status</label>
            <select
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-2 text-sm"
              value={lead.status || availableStages[0]?.id || 'new'}
              onChange={(event) => void onUpdateStatus(lead.id, event.target.value)}
            >
              {availableStages.map((stage) => (
                <option key={stage.id} value={stage.id}>{stage.label}</option>
              ))}
            </select>
          </Panel>
        ) : null}

          {tab === 'property' ? (
            <Panel>
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <div>
                  <h2 className="font-semibold text-base">Property & Showing Operations</h2>
                  <p className="text-xs text-muted-foreground">Authoritative unit inventory, private tours, and channel partner attribution.</p>
                </div>
                <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                  Real Estate Operating System
                </span>
              </div>

              {/* Preferences & Inquired Unit */}
              <div className="mt-4 p-3 rounded-xl border border-border bg-card/50 space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Inquiry Preferences</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground block">Project</span>
                    <span className="font-medium text-foreground">{lead.company || 'Not selected'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Unit Preference</span>
                    <span className="font-medium text-foreground">{lead.need_of_what || lead.data?.unit_preference || 'Any configuration'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Budget</span>
                    <span className="font-medium text-foreground">{lead.how_much || lead.data?.budget || 'Not specified'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Property Type</span>
                    <span className="font-medium text-foreground">{lead.data?.property_type || 'Residential'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Purchase Purpose</span>
                    <span className="font-medium text-foreground">{lead.data?.purchase_purpose || 'Self-Use'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Timeline</span>
                    <span className="font-medium text-foreground">{lead.data?.purchase_timeline || '30 Days'}</span>
                  </div>
                </div>
              </div>

              {/* AI Property Matching Section */}
              <div className="mt-4 p-3 rounded-xl border border-border bg-card/50 space-y-3">

                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Sparkles size={13} className="text-primary" />
                      AI Inventory Matcher
                    </h3>
                    <p className="text-[11px] text-muted-foreground">Ranks real, available inventory against buyer budget and preferences.</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={matchesLoading}
                    onClick={handleFindMatches}
                    className="text-xs font-semibold h-7 gap-1"
                  >
                    {matchesLoading ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                    {matches.length > 0 ? 'Refresh Matches' : 'Find Matched Units'}
                  </Button>
                </div>

                {matches.length > 0 ? (
                  <div className="space-y-2 mt-2">
                    {matches.map((m: any) => (
                      <div key={m.unit_id} className="rounded-lg border border-border p-3 bg-card text-xs space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-foreground">{m.unit_number}</span>
                            <span className="rounded bg-primary/10 border border-primary/20 px-2 py-0.5 text-[11px] font-semibold text-primary">
                              {m.unit_type}
                            </span>
                            <span className="text-muted-foreground">{m.project_name} · Floor {m.floor || 1}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-bold text-emerald-400">
                              {m.match_score}% Match
                            </span>
                            <span className="font-semibold text-foreground">₹{Number(m.base_price).toLocaleString()}</span>
                          </div>
                        </div>

                        {/* Pros / Cons Tags */}
                        <div className="flex flex-wrap gap-1">
                          {(m.pros || []).map((pro: string, i: number) => (
                            <span key={i} className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-300">
                              ✓ {pro}
                            </span>
                          ))}
                          {(m.cons || []).map((con: string, i: number) => (
                            <span key={i} className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-300">
                              • {con}
                            </span>
                          ))}
                        </div>

                        {/* Booking or Hold Action */}
                        <div className="flex flex-wrap items-center justify-end gap-2 pt-1 border-t border-border/50">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              if (activeCostSheetUnitId === m.unit_id) {
                                setActiveCostSheetUnitId(null);
                              } else {
                                void handleLoadCostSheet(m.unit_id);
                              }
                            }}
                            className="h-7 text-xs font-medium gap-1 border-primary/40 text-primary hover:bg-primary/10"
                          >
                            <Calculator size={12} />
                            {activeCostSheetUnitId === m.unit_id ? 'Hide CPQ Cost Sheet' : 'CPQ Cost Sheet'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleQuickHoldUnit(m.unit_id)}
                            className="h-7 text-xs font-medium"
                          >
                            Reserve 48h Hold
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => {
                              setBookingUnitId(m.unit_id);
                              setBookingPrice(String(m.base_price));
                              setBookingBuyerName(lead.name || '');
                            }}
                            className="h-7 text-xs font-semibold"
                          >
                            Book Unit
                          </Button>
                        </div>

                        {/* CPQ Cost Sheet Drawer / Expanded Panel */}
                        {activeCostSheetUnitId === m.unit_id ? (
                          <div className="mt-3 p-3 rounded-lg border border-primary/30 bg-card text-xs space-y-3">
                            <div className="flex items-center justify-between border-b border-border pb-2">
                              <div className="flex items-center gap-1.5">
                                <Calculator size={14} className="text-primary" />
                                <span className="font-bold text-foreground">Enterprise CPQ Cost Sheet & Tax Breakdown</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <select
                                  value={costSheetPlanType}
                                  onChange={(e) => {
                                    setCostSheetPlanType(e.target.value);
                                    void handleLoadCostSheet(m.unit_id, e.target.value);
                                  }}
                                  className="rounded border border-border bg-background px-2 py-1 text-[11px]"
                                >
                                  <option value="construction_linked">Construction-Linked (CLP)</option>
                                  <option value="down_payment">Down Payment (DPP)</option>
                                  <option value="subvention">Subvention (10:75:15)</option>
                                </select>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => setActiveCostSheetUnitId(null)}
                                  className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                                >
                                  ✕
                                </Button>
                              </div>
                            </div>

                            {costSheetLoading ? (
                              <div className="py-4 flex justify-center items-center gap-2 text-muted-foreground text-xs">
                                <Loader2 size={14} className="animate-spin" />
                                <span>Calculating authoritative pricing & milestone schedule...</span>
                              </div>
                            ) : costSheetData ? (
                              <div className="space-y-2.5">
                                {/* Core Pricing Grid */}
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] bg-muted/30 p-2.5 rounded-lg border border-border/60">
                                  <div>
                                    <span className="text-muted-foreground block">Carpet / Super Area</span>
                                    <span className="font-semibold text-foreground">{costSheetData.carpet_sqft} / {costSheetData.super_builtup_sqft} sqft</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block">Base Rate</span>
                                    <span className="font-semibold text-foreground">₹{Number(costSheetData.base_rate_per_sqft).toLocaleString()} / sqft</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block">Floor Rise (Floor {costSheetData.floor_number})</span>
                                    <span className="font-semibold text-foreground">₹{Number(costSheetData.floor_rise_total).toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block">PLC Premium ({costSheetData.plc_type || 'None'})</span>
                                    <span className="font-semibold text-foreground">₹{Number(costSheetData.plc_total).toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block">Clubhouse & Infra</span>
                                    <span className="font-semibold text-foreground">₹{Number(costSheetData.clubhouse_charges + costSheetData.infrastructure_development_charges).toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block">Car Parking ({costSheetData.car_parking_slots} slot)</span>
                                    <span className="font-semibold text-foreground">₹{Number(costSheetData.car_parking_charges).toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block">GST ({costSheetData.gst_rate_pct}%)</span>
                                    <span className="font-semibold text-amber-400">₹{Number(costSheetData.gst_amount).toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground block">Stamp Duty & Reg.</span>
                                    <span className="font-semibold text-amber-400">₹{Number(costSheetData.stamp_duty_amount + costSheetData.registration_fee_est).toLocaleString()}</span>
                                  </div>
                                </div>

                                {/* Totals Summary */}
                                <div className="flex flex-wrap items-center justify-between p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                                  <div>
                                    <span className="text-[11px] text-muted-foreground block">Gross Consideration (Agreement Value)</span>
                                    <span className="font-bold text-foreground text-sm">₹{Number(costSheetData.gross_consideration).toLocaleString()}</span>
                                  </div>
                                  <div className="text-right">
                                    <span className="text-[11px] text-muted-foreground block">All-Inclusive Total Effective</span>
                                    <span className="font-bold text-emerald-400 text-sm">₹{Number(costSheetData.total_effective_price).toLocaleString()}</span>
                                  </div>
                                </div>

                                {/* Milestone Schedule preview */}
                                <div className="space-y-1">
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Milestone Payment Plan ({costSheetData.payment_plan_type})</span>
                                  <div className="max-h-36 overflow-y-auto space-y-1 pr-1">
                                    {(costSheetData.milestone_schedule || []).map((ms: any, idx: number) => (
                                      <div key={idx} className="flex items-center justify-between text-[11px] py-1 px-2 rounded bg-muted/40 border border-border/40">
                                        <span className="text-foreground">{ms.stage_index}. {ms.milestone_name} ({ms.percentage}%)</span>
                                        <span className="font-semibold text-foreground">₹{Number(ms.amount).toLocaleString()}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {/* Action Button */}
                                <div className="flex justify-end gap-2 pt-1 border-t border-border/50">
                                  <Button
                                    size="sm"
                                    onClick={() => handleApplyCostSheetToBooking(costSheetData)}
                                    className="h-7 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5"
                                  >
                                    <Check size={12} />
                                    Apply to Booking Application
                                  </Button>
                                </div>
                              </div>
                            ) : null}
                          </div>
                        ) : null}

                        {/* Inline Booking Form */}
                        {bookingUnitId === m.unit_id ? (
                          <div className="mt-2 p-2.5 rounded-lg border border-primary/40 bg-primary/5 space-y-2">
                            <h4 className="text-xs font-bold text-foreground">Confirm Booking Application for {m.unit_number}</h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              <div>
                                <label className="text-[10px] text-muted-foreground block">Buyer Legal Name</label>
                                <Input
                                  value={bookingBuyerName}
                                  onChange={(e) => setBookingBuyerName(e.target.value)}
                                  className="h-7 text-xs mt-0.5"
                                  placeholder="Full Legal Name"
                                />
                              </div>
                              <div>
                                <label className="text-[10px] text-muted-foreground block">Agreed Deal Price</label>
                                <Input
                                  value={bookingPrice}
                                  onChange={(e) => setBookingPrice(e.target.value)}
                                  className="h-7 text-xs mt-0.5"
                                  placeholder="Agreed Amount"
                                />
                              </div>
                            </div>
                            <div className="flex justify-end gap-2 pt-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => setBookingUnitId(null)}
                                className="h-7 text-xs"
                              >
                                Cancel
                              </Button>
                              <Button
                                size="sm"
                                disabled={bookingSubmitting}
                                onClick={() => handleCreateBookingSubmit(m.unit_id, m.base_price)}
                                className="h-7 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                              >
                                {bookingSubmitting ? 'Creating...' : 'Lock & Confirm Booking'}
                              </Button>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>

              {/* Active Bookings & Financial Progress */}
              {bookings.length > 0 ? (
                <div className="mt-4 p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                      <CheckCircle size={13} className="text-emerald-400" />
                      Active Booking Contracts ({bookings.length})
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {bookings.map((bk: any) => (
                      <div key={bk.id} className="rounded-lg border border-border p-2.5 bg-card text-xs flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-foreground">{bk.booking_reference}</span>
                            <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400 uppercase">
                              {bk.status.replaceAll('_', ' ')}
                            </span>
                          </div>
                          <span className="text-[11px] text-muted-foreground mt-0.5 block">
                            Buyer: {bk.buyer_legal_name} · Agreed: ₹{Number(bk.agreed_price).toLocaleString()}
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="font-semibold text-emerald-400 block">₹{Number(bk.deposit_paid).toLocaleString()} paid</span>
                          <span className="text-[10px] text-muted-foreground">₹{Number(bk.balance_due).toLocaleString()} balance</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {/* Site Visits Section */}
              <div className="mt-4 p-3 rounded-xl border border-border bg-card/50 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Site Visits & Private Tours</h3>

                  <span className="text-[11px] text-muted-foreground">{visits.length} scheduled</span>
                </div>
                {visits.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">No site visits have been logged for this inquiry yet.</p>
                ) : (
                  <div className="space-y-2">
                    {visits.map((v: any) => (
                      <div key={v.id} className="flex items-center justify-between rounded-lg border border-border p-2.5 text-xs bg-card">
                        <div>
                          <span className="font-semibold block">{new Date(v.scheduled_at).toLocaleString()}</span>
                          <span className="text-muted-foreground">
                            {v.assigned_agent ? `Escort: ${v.assigned_agent}` : 'Unassigned agent'} · Status: <span className="text-primary font-medium">{v.status}</span>
                          </span>
                        </div>
                        {v.buyer_interest_level ? (
                          <span className="rounded px-2 py-0.5 text-[10px] uppercase font-bold border border-primary/30 text-primary">
                            {v.buyer_interest_level} intent
                          </span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
                {/* Schedule Visit Form */}
                <div className="pt-2 border-t border-border flex flex-wrap gap-2 items-center">
                  <input
                    type="datetime-local"
                    className="rounded-md border border-border bg-background px-2.5 py-1.5 text-xs"
                    value={visitDate}
                    onChange={(e) => setVisitDate(e.target.value)}
                  />
                  <input
                    type="text"
                    placeholder="Assigned Agent / Escort"
                    className="rounded-md border border-border bg-background px-2.5 py-1.5 text-xs flex-1 min-w-[140px]"
                    value={visitAgent}
                    onChange={(e) => setVisitAgent(e.target.value)}
                  />
                  <Button
                    size="sm"
                    disabled={!visitDate || visitScheduling}
                    onClick={handleScheduleVisit}
                    className="text-xs font-semibold h-8"
                  >
                    Schedule Showing
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={autoAssigning}
                    onClick={handleAutoAssignVisit}
                    className="text-xs font-semibold h-8 gap-1.5 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                  >
                    {autoAssigning ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} className="text-emerald-400" />}
                    Auto-Dispatch Specialist
                  </Button>
                </div>
                {autoAssignMessage && (
                  <p className="text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded px-2.5 py-1.5 mt-2">
                    {autoAssignMessage}
                  </p>
                )}
              </div>

              {/* Channel Partner / Broker Attribution */}
              <div className="mt-4 p-3 rounded-xl border border-border bg-card/50 space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Channel Partner & Broker Attribution</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <Field label="Brokerage / Partner Firm" value={brokerName} onChange={setBrokerName} />
                  <Field label="RERA / License ID" value={brokerRera} onChange={setBrokerRera} />
                  <Field label="Commission %" value={brokerCommission} onChange={setBrokerCommission} />
                </div>
                <div className="flex justify-end">
                  <Button size="sm" variant="outline" onClick={handleSaveBroker} className="text-xs font-semibold h-7">
                    Save Broker Attribution
                  </Button>
                </div>
              </div>
            </Panel>
          ) : null}
          {tab === 'activity' ? (
            <Panel>
              <h2 className="font-semibold">Engagement timeline</h2>
              <p className="text-xs text-muted-foreground">Calls, emails, meetings, tasks, and notes stored on this record.</p>
              {conversation.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No activity is stored.</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {conversation.map((item: any, index: number) => (
                    <li key={`${item.at || index}`} className="rounded-lg border border-border px-3 py-2 text-sm">
                      <div className="text-xs text-muted-foreground">{[item.channel, item.direction, item.at].filter(Boolean).join(' · ')}</div>
                      <p className="mt-1">{item.content || item.subject || 'Empty note'}</p>
                    </li>
                  ))}
                </ul>
              )}
              <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add an internal note" className="mt-3" />
              <Button
                type="button"
                variant="secondary"
                className="mt-2"
                disabled={!note.trim() || actionLoading}
                onClick={async () => {
                  await onLogNote(lead.id, note, 'note', 'internal');
                  setNote('');
                }}
              >
                Save note
              </Button>
            </Panel>
          ) : null}
          {tab === 'sales' ? (
            <Panel>
              <h2 className="font-semibold">Follow-up draft</h2>
              <p className="text-xs text-muted-foreground">A draft is not a sent message. Sending stays on the existing outreach action.</p>
              {draftPreview ? (
                <div className="mt-3 rounded-lg border border-border p-3 text-sm">
                  <p className="font-medium">{draftPreview.subject || 'No subject stored'}</p>
                  <p className="mt-2 whitespace-pre-wrap text-muted-foreground">{draftPreview.body || 'No body stored'}</p>
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">No draft is stored.</p>
              )}
              {draftPreview?.body ? (
                <div className="mt-3">
                  {confirmSend ? (
                    <Button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => void onSendDraft(lead.id, draftPreview.subject, draftPreview.body)}
                    >
                      Confirm send
                    </Button>
                  ) : (
                    <Button type="button" variant="secondary" onClick={() => setConfirmSend(true)}>
                      Prepare to send
                    </Button>
                  )}
                </div>
              ) : null}
            </Panel>
          ) : null}
          {tab === 'history' ? (
            <Panel>
              <h2 className="font-semibold">History</h2>
              <dl className="mt-2 space-y-1 text-sm">
                <Row label="Record id" value={lead.id} />
                <Row label="Created" value={lead.created_at || 'Not stored'} />
                <Row label="Updated" value={lead.updated_at || 'Not stored'} />
                <Row label="Score source" value={advice?.readiness.source || 'lead.score'} />
              </dl>
            </Panel>
          ) : null}
        </section>

        <aside className={`${pane === 'copilot' ? 'block' : 'hidden'} xl:block`} aria-label="OctaOS Copilot">
          <div className="flex h-full flex-col rounded-2xl border border-border bg-card p-4">
            <h2 className="font-semibold">OctaOS Copilot</h2>
            <p className="text-xs text-muted-foreground">{labels.lead} · {lead.company || 'No company'}</p>
            <div className="mt-3 flex-1 space-y-3">
              {copilotLoading ? <p className="text-sm text-muted-foreground">Reading the stored record…</p> : null}
              {copilotError ? <p className="text-sm text-destructive">{copilotError}</p> : null}
              {advice ? (
                <>
                  <p className="text-sm">{advice.answer}</p>
                  <div className="rounded-xl border border-border p-3">
                    <h3 className="text-sm font-semibold">Recommendation</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{advice.recommendation}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Confidence {advice.confidence}. {advice.confidence_basis}
                    </p>
                  </div>
                  <div className="space-y-2">
                    {advice.actions.map((action) => (
                      <button
                        key={action.id}
                        type="button"
                        onClick={() => void runAction(action.id)}
                        className="block w-full rounded-xl border border-border px-3 py-2 text-left text-sm font-medium hover:border-primary/40"
                      >
                        {action.label}
                        <span className="mt-0.5 block text-xs font-normal text-muted-foreground">{action.preview}</span>
                      </button>
                    ))}
                  </div>
                  {confirmMeeting ? (
                    <div className="rounded-xl border border-border p-3">
                      <p className="text-sm">Enter the exact prospect-agreed meeting time in your local timezone.</p>
                      <Input
                        type="datetime-local"
                        value={meetingTime}
                        onChange={(event) => setMeetingTime(event.target.value)}
                        disabled={actionLoading}
                        className="mt-2"
                      />
                      <Button
                        type="button"
                        className="mt-2"
                        disabled={actionLoading || !meetingTime}
                        onClick={() => void onBookMeeting(lead.id, meetingTime)}
                      >
                        Confirm booking
                      </Button>
                    </div>
                  ) : null}
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence</h3>
                    <ul className="mt-1 space-y-1">
                      {advice.evidence.length === 0 ? <li className="text-xs text-muted-foreground">No stored facts to cite.</li> : null}
                      {advice.evidence.map((item) => (
                        <li key={item.claim} className="text-xs text-muted-foreground">
                          {item.claim} <span className="text-foreground/70">({item.verification_status}, {item.source})</span>
                        </li>
                      ))}
                    </ul>
                    {advice.unknowns.length > 0 ? (
                      <p className="mt-2 text-xs text-muted-foreground">Unknown: {advice.unknowns.slice(0, 6).join(' · ')}</p>
                    ) : null}
                  </div>
                </>
              ) : null}
            </div>
            <form
              className="mt-3 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (question.trim()) void ask(question.trim());
              }}
            >
              <Input
                aria-label="Ask about this record"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about this record…"
              />
              <Button type="submit" size="icon" aria-label="Ask" disabled={copilotLoading}>
                <Send size={14} />
              </Button>
            </form>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Panel({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-border bg-card p-4">{children}</div>;
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="mt-3 block text-xs text-muted-foreground">
      {label}
      <Input className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Metric({ title, value, note }: { title: string; value: string; note: string }) {
  return (
    <div className="rounded-2xl bg-[#2563eb] p-4 text-white">
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      <p className="mt-2 text-xs text-blue-100">{note}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}

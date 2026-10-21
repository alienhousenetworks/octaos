'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Calculator,
  ShieldCheck,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  DollarSign,
  TrendingUp,
  Building2,
  ChevronRight,
  Plus,
  Trash2,
  ArrowRight,
  RefreshCw,
  Copy,
  ExternalLink,
  Lock,
  Unlock,
  AlertTriangle,
  XCircle,
  UserCheck,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { notify } from '@/lib/notify';

interface SalesDealDeskViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

function money(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const STAGE_ORDER = [
  'discovered',
  'qualified',
  'meeting_booked',
  'proposal',
  'closing',
  'won',
];

export default function SalesDealDeskView({
  token,
  API_URL,
  fetchWithAuth,
}: SalesDealDeskViewProps) {
  // Accounts / Deal Rooms
  const [dealRooms, setDealRooms] = useState<any[]>([]);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [loadingRooms, setLoadingRooms] = useState(false);

  // CPQ Catalog
  const [catalog, setCatalog] = useState<any[]>([]);

  // Quote Builder State
  const [lineItems, setLineItems] = useState<any[]>([
    {
      sku: 'OCTA-PLATFORM',
      name: 'OctaOS Core Autonomous Platform',
      description: 'Enterprise multi-agent control plane, canonical data model & audit logging.',
      unit_price: 18000.0,
      quantity: 1,
      discount_pct: 0.0,
    },
    {
      sku: 'OCTA-SALES-SWARM',
      name: 'Dedicated Sales Swarm Capacity',
      description: 'Autonomous prospecting, cadence execution, meeting booking & inbox copilot.',
      unit_price: 12000.0,
      quantity: 1,
      discount_pct: 0.0,
    },
  ]);

  const [contractMonths, setContractMonths] = useState<number>(12);
  const [paymentTerms, setPaymentTerms] = useState<string>('Net 30');
  const [requestedDiscount, setRequestedDiscount] = useState<number>(5.0);

  // Quote Calculation Results
  const [calculatedQuote, setCalculatedQuote] = useState<any | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [savingQuote, setSavingQuote] = useState(false);
  const [approvingQuote, setApprovingQuote] = useState(false);

  // Proposal State
  const [proposalMarkdown, setProposalMarkdown] = useState<string | null>(null);
  const [termsHash, setTermsHash] = useState<string | null>(null);
  const [clientSignatoryName, setClientSignatoryName] = useState('Jane Doe');
  const [clientSignatoryTitle, setClientSignatoryTitle] = useState('Chief Technology Officer');
  const [customProposalNotes, setCustomProposalNotes] = useState('');
  const [generatingProposal, setGeneratingProposal] = useState(false);

  // Stage Gatekeeper State
  const [stageCheck, setStageCheck] = useState<any | null>(null);
  const [advancingStage, setAdvancingStage] = useState(false);
  const [isLossModalOpen, setIsLossModalOpen] = useState(false);
  const [lossReason, setLossReason] = useState('competitor_chosen');
  const [lossNotes, setLossNotes] = useState('');

  // ── Fetch Deal Rooms & Catalog ──
  const loadData = async () => {
    if (!token) return;
    setLoadingRooms(true);
    try {
      const [roomsRes, catRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/deal-rooms/`),
        fetchWithAuth(`${API_URL}/sales-crm/cpq/catalog`),
      ]);
      if (roomsRes.ok) {
        const rooms = await roomsRes.json();
        setDealRooms(rooms);
        if (rooms.length > 0 && !selectedRoomId) {
          setSelectedRoomId(rooms[0].id);
        }
      }
      if (catRes.ok) {
        setCatalog(await catRes.json());
      }
    } catch (err) {
      console.error('Failed to load deal rooms:', err);
    } finally {
      setLoadingRooms(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  const selectedRoom = useMemo(() => {
    return dealRooms.find((r) => r.id === selectedRoomId) || null;
  }, [dealRooms, selectedRoomId]);

  // ── Fetch Active Quote for Selected Room ──
  const fetchRoomQuote = async (roomId: string) => {
    if (!token || !roomId) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/cpq/quotes/${roomId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.latest_quote) {
          setCalculatedQuote(data.latest_quote);
          if (data.latest_quote.line_items) setLineItems(data.latest_quote.line_items);
          if (data.latest_quote.contract_term_months) setContractMonths(data.latest_quote.contract_term_months);
          if (data.latest_quote.payment_terms) setPaymentTerms(data.latest_quote.payment_terms);
          if (data.latest_quote.additional_discount_pct !== undefined) {
            setRequestedDiscount(data.latest_quote.additional_discount_pct);
          }
        }
        if (data.latest_proposal) {
          setProposalMarkdown(data.latest_proposal.markdown);
          setTermsHash(data.latest_proposal.terms_hash);
        } else {
          setProposalMarkdown(null);
          setTermsHash(null);
        }
      }
    } catch (err) {
      console.error('Failed to fetch room quote:', err);
    }
  };

  // ── Stage Readiness Check ──
  const checkStageReadiness = async (roomId: string, currentStage: string) => {
    if (!token || !roomId) return;
    const currentIdx = STAGE_ORDER.indexOf(currentStage);
    const nextStage = currentIdx >= 0 && currentIdx < STAGE_ORDER.length - 1 ? STAGE_ORDER[currentIdx + 1] : 'closing';
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/deal-rooms/${roomId}/stage-check?target_stage=${nextStage}`);
      if (res.ok) {
        setStageCheck(await res.json());
      }
    } catch (err) {
      console.error('Failed to check stage readiness:', err);
    }
  };

  useEffect(() => {
    if (selectedRoomId && selectedRoom) {
      fetchRoomQuote(selectedRoomId);
      checkStageReadiness(selectedRoomId, selectedRoom.stage || 'discovered');
    }
  }, [selectedRoomId, selectedRoom?.stage]);

  // ── Recalculate Quote on Changes ──
  const calculatePricing = async () => {
    if (!token) return;
    setCalculating(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/cpq/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deal_room_id: selectedRoomId,
          line_items: lineItems,
          requested_discount_pct: requestedDiscount,
          contract_term_months: contractMonths,
          payment_terms: paymentTerms,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setCalculatedQuote(data);
      }
    } catch (err) {
      console.error('Failed to calculate pricing:', err);
    } finally {
      setCalculating(false);
    }
  };

  useEffect(() => {
    calculatePricing();
  }, [lineItems, requestedDiscount, contractMonths, paymentTerms]);

  // ── Save Quote to Deal Room ──
  const handleSaveQuote = async () => {
    if (!token || !selectedRoomId) return;
    setSavingQuote(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/cpq/quotes/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deal_room_id: selectedRoomId,
          line_items: lineItems,
          requested_discount_pct: requestedDiscount,
          contract_term_months: contractMonths,
          payment_terms: paymentTerms,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        notify.success('Commercial quote saved to deal room and synced with opportunity size!');
        loadData();
        if (selectedRoom) checkStageReadiness(selectedRoomId, selectedRoom.stage);
      } else {
        notify.error('Failed to save quote');
      }
    } catch (err) {
      notify.error('Network error saving quote');
    } finally {
      setSavingQuote(false);
    }
  };

  // ── Approve Quote Discount ──
  const handleApproveQuote = async () => {
    if (!token || !selectedRoomId) return;
    setApprovingQuote(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/cpq/quotes/${selectedRoomId}/approve`, {
        method: 'POST',
      });
      if (res.ok) {
        notify.success('Quote discount approved by manager!');
        fetchRoomQuote(selectedRoomId);
        if (selectedRoom) checkStageReadiness(selectedRoomId, selectedRoom.stage);
      } else {
        notify.error('Failed to approve quote discount');
      }
    } catch (err) {
      notify.error('Network error approving quote');
    } finally {
      setApprovingQuote(false);
    }
  };

  // ── Generate Formal Commercial Proposal & Contract ──
  const handleGenerateProposal = async () => {
    if (!token || !selectedRoomId) return;
    setGeneratingProposal(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/cpq/proposals/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deal_room_id: selectedRoomId,
          client_signatory_name: clientSignatoryName,
          client_signatory_title: clientSignatoryTitle,
          custom_notes: customProposalNotes,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setProposalMarkdown(data.proposal_markdown);
        setTermsHash(data.terms_hash);
        notify.success('Commercial proposal & contract generated with SHA-256 integrity hash!');
        loadData();
        if (selectedRoom) checkStageReadiness(selectedRoomId, selectedRoom.stage);
      } else {
        notify.error('Failed to generate proposal');
      }
    } catch (err) {
      notify.error('Network error generating proposal');
    } finally {
      setGeneratingProposal(false);
    }
  };

  // ── Advance Deal Stage via Gatekeeper ──
  const handleAdvanceStage = async (nextStage: string) => {
    if (!token || !selectedRoomId) return;
    setAdvancingStage(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/deal-rooms/${selectedRoomId}/stage`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_stage: nextStage }),
      });
      if (res.ok) {
        notify.success(`Deal advanced to '${nextStage}' with synchronized CRM state!`);
        loadData();
      } else {
        const err = await res.json();
        const msg = err.detail?.message || 'Stage transition blocked by gatekeeper criteria';
        notify.error(msg);
      }
    } catch (err) {
      notify.error('Network error advancing stage');
    } finally {
      setAdvancingStage(false);
    }
  };

  // ── Mark as Lost ──
  const handleMarkLost = async () => {
    if (!token || !selectedRoomId) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/deal-rooms/${selectedRoomId}/stage`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_stage: 'lost',
          loss_reason: lossReason,
          notes: lossNotes,
        }),
      });
      if (res.ok) {
        notify.success('Deal marked as closed lost and reason recorded');
        setIsLossModalOpen(false);
        loadData();
      } else {
        notify.error('Failed to update stage');
      }
    } catch (err) {
      notify.error('Network error recording loss');
    }
  };

  // Add line item from catalog
  const addCatalogItem = (skuItem: any) => {
    setLineItems((prev) => [
      ...prev,
      {
        sku: skuItem.sku,
        name: skuItem.name,
        description: skuItem.description,
        unit_price: skuItem.price,
        quantity: 1,
        discount_pct: 0.0,
      },
    ]);
  };

  // Policy Badge Helper
  const policyBadge = (status: string) => {
    switch (status) {
      case 'auto_approved':
        return {
          label: 'Auto-Approved (Level 2)',
          color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
          icon: <CheckCircle2 size={12} />,
        };
      case 'requires_manager_approval':
        return {
          label: 'Manager Approval Required (Level 1)',
          color: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          icon: <AlertTriangle size={12} />,
        };
      case 'requires_vp_approval':
        return {
          label: 'VP Escalation Required (Level 0)',
          color: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
          icon: <AlertCircle size={12} />,
        };
      case 'blocked':
        return {
          label: 'Blocked: Margin Floor Violation',
          color: 'bg-destructive/10 text-destructive border-destructive/20',
          icon: <XCircle size={12} />,
        };
      default:
        return {
          label: 'Policy Evaluation Pending',
          color: 'bg-muted text-muted-foreground border-border',
          icon: <Clock size={12} />,
        };
    }
  };

  const badge = policyBadge(calculatedQuote?.policy_status || 'auto_approved');

  return (
    <div className="space-y-6">
      {/* ── TOP EXECUTIVE CONTROLS BAR ── */}
      <div className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center font-bold shadow-xs">
            <Calculator size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-foreground">
                Deal Desk, CPQ &amp; Dynamic Pricing Floor Gatekeeper
              </h2>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                L0/L1/L2 Autonomy Ladder
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Deterministic Configure-Price-Quote engine enforcing gross margin floors, tiered approval routing, and contract generation.
            </p>
          </div>
        </div>

        {/* Account / Deal Room Switcher */}
        <div className="flex items-center gap-2.5 shrink-0">
          <label className="text-xs font-semibold text-muted-foreground">Active Deal:</label>
          <select
            value={selectedRoomId || ''}
            onChange={(e) => setSelectedRoomId(e.target.value)}
            className="h-8.5 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary min-w-[220px]"
          >
            {dealRooms.map((r) => (
              <option key={r.id} value={r.id}>
                {r.company_name} · {r.stage.replace('_', ' ')} ({money(r.deal_size)})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── MAIN TWO-COLUMN WORKSPACE: LEFT CPQ BUILDER | RIGHT PROPOSAL & STAGE GATEKEEPER ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── LEFT: INTERACTIVE CPQ QUOTE BUILDER ── */}
        <div className="lg:col-span-7 space-y-5">
          {/* Line Items Table */}
          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-xs">
            <div className="px-4 py-3 border-b border-border flex items-center justify-between bg-muted/20">
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-primary" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                  Commercial Solution Scope &amp; Line Items
                </h3>
              </div>
              <span className="text-xs text-muted-foreground">
                Quote #{calculatedQuote?.quote_number || '—'}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/40 text-muted-foreground border-b border-border">
                  <tr>
                    <th className="py-2.5 px-4 font-medium">Component</th>
                    <th className="py-2.5 px-3 font-medium">List Price</th>
                    <th className="py-2.5 px-3 font-medium text-center">Qty</th>
                    <th className="py-2.5 px-3 font-medium">Disc %</th>
                    <th className="py-2.5 px-4 font-medium text-right">Net Price</th>
                    <th className="py-2.5 px-2 text-center"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {lineItems.map((item, idx) => (
                    <tr key={idx} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4">
                        <span className="font-bold text-foreground block">{item.name}</span>
                        <span className="text-[11px] text-muted-foreground block line-clamp-1">
                          {item.description || item.sku}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-muted-foreground">
                        {money(item.unit_price)}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={item.quantity}
                          onChange={(e) => {
                            const val = Math.max(1, parseInt(e.target.value) || 1);
                            const updated = [...lineItems];
                            updated[idx].quantity = val;
                            setLineItems(updated);
                          }}
                          className="w-12 h-7 rounded border border-border bg-background text-center font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                      </td>
                      <td className="py-3 px-3">
                        <input
                          type="number"
                          min={0}
                          max={50}
                          value={item.discount_pct || 0}
                          onChange={(e) => {
                            const val = Math.max(0, Math.min(50, parseFloat(e.target.value) || 0));
                            const updated = [...lineItems];
                            updated[idx].discount_pct = val;
                            setLineItems(updated);
                          }}
                          className="w-14 h-7 rounded border border-border bg-background text-center font-mono text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-foreground">
                        {money(item.unit_price * item.quantity * (1 - (item.discount_pct || 0) / 100))}
                      </td>
                      <td className="py-3 px-2 text-center">
                        {lineItems.length > 1 && (
                          <button
                            onClick={() => setLineItems(lineItems.filter((_, i) => i !== idx))}
                            className="text-muted-foreground hover:text-destructive transition-colors p-1"
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Catalog Adders Bar */}
            <div className="p-3 border-t border-border bg-muted/10 flex items-center justify-between flex-wrap gap-2">
              <span className="text-[11px] text-muted-foreground">Quick Add from Standard Catalog:</span>
              <div className="flex items-center gap-1.5 flex-wrap">
                {catalog.map((cat) => (
                  <Button
                    key={cat.sku}
                    size="sm"
                    variant="outline"
                    onClick={() => addCatalogItem(cat)}
                    className="h-7 text-[11px] gap-1 px-2.5"
                  >
                    <Plus size={11} /> {cat.name.split(' ')[0]} ({money(cat.price)})
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* Commercial Terms & Concessions Box */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-4 shadow-xs">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Commercial Terms &amp; Multi-Year Concessions
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">
                  Contract Duration &amp; Multi-Year Credit
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { months: 12, label: '1 Year', bonus: '0%' },
                    { months: 24, label: '2 Years', bonus: '-5%' },
                    { months: 36, label: '3 Years', bonus: '-10%' },
                  ].map((opt) => (
                    <button
                      key={opt.months}
                      onClick={() => setContractMonths(opt.months)}
                      className={`p-2 rounded-lg text-xs font-semibold border transition-all text-center ${
                        contractMonths === opt.months
                          ? 'border-primary bg-primary/10 text-primary shadow-xs'
                          : 'border-border bg-background hover:bg-muted/40 text-foreground'
                      }`}
                    >
                      <div>{opt.label}</div>
                      <span className="text-[10px] text-emerald-400 font-mono">{opt.bonus}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-muted-foreground block mb-1">
                  Invoicing &amp; Payment Terms
                </label>
                <select
                  value={paymentTerms}
                  onChange={(e) => setPaymentTerms(e.target.value)}
                  className="w-full h-9 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="Net 30">Net 30 (Standard)</option>
                  <option value="Net 60">Net 60 (Extended)</option>
                  <option value="Due on Receipt">Due on Receipt (Immediate)</option>
                  <option value="Annual Upfront">Annual Upfront (Immediate ACH)</option>
                </select>
              </div>
            </div>

            {/* Discretionary Discount Slider */}
            <div className="space-y-2 pt-2 border-t border-border/60">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <span>Additional Discretionary Discount</span>
                  <span className="font-mono text-primary font-bold">({requestedDiscount}%)</span>
                </label>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border flex items-center gap-1 ${badge.color}`}>
                  {badge.icon}
                  {badge.label}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={45}
                step={1}
                value={requestedDiscount}
                onChange={(e) => setRequestedDiscount(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
              />
              <p className="text-[11px] text-muted-foreground">
                Policy Reason: {calculatedQuote?.policy_reason || 'Evaluating policy rules...'}
              </p>
            </div>
          </div>

          {/* Pricing Totals & Financial ROI Strip */}
          {calculatedQuote && (
            <div className="rounded-xl border border-border bg-gradient-to-r from-card via-card to-primary/5 p-4 space-y-4 shadow-xs">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div>
                  <span className="text-muted-foreground block">Gross Catalog</span>
                  <span className="font-mono font-bold text-foreground text-sm">
                    {money(calculatedQuote.gross_total_usd)}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Total Discounts</span>
                  <span className="font-mono font-bold text-amber-400 text-sm">
                    -{money(calculatedQuote.total_discount_amount)} ({calculatedQuote.total_discount_pct}%)
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Net Contract Value</span>
                  <span className="font-mono font-extrabold text-primary text-base">
                    {money(calculatedQuote.net_total_usd)}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Payback Velocity</span>
                  <span className="font-mono font-bold text-emerald-400 text-sm">
                    ~{calculatedQuote.roi_model.payback_period_months} Months
                  </span>
                </div>
              </div>

              {/* Action Buttons Row */}
              <div className="pt-2 border-t border-border flex items-center justify-between flex-wrap gap-2">
                <Button
                  onClick={handleSaveQuote}
                  disabled={savingQuote || calculatedQuote.floor_violation}
                  className="h-8.5 text-xs gap-1.5 bg-primary text-primary-foreground font-semibold"
                >
                  {savingQuote ? <RefreshCw size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                  Save Quote into Deal Room
                </Button>

                {calculatedQuote.policy_status === 'requires_manager_approval' && (
                  <Button
                    variant="outline"
                    onClick={handleApproveQuote}
                    disabled={approvingQuote}
                    className="h-8.5 text-xs gap-1.5 border-amber-500/40 text-amber-400 hover:bg-amber-500/10 font-semibold"
                  >
                    {approvingQuote ? <RefreshCw size={13} className="animate-spin" /> : <UserCheck size={13} />}
                    Approve Manager Sign-off
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT: STAGE GATEKEEPER & PROPOSAL GENERATOR ── */}
        <div className="lg:col-span-5 space-y-5">
          {/* Stage Progression Gatekeeper Panel */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-3.5 shadow-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-primary" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                  Stage Transition Gatekeeper
                </h3>
              </div>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground">
                Current: {selectedRoom?.stage?.replace('_', ' ') || 'discovered'}
              </span>
            </div>

            {/* Progression Criteria Checklist */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-foreground block">
                Target Stage: <span className="text-primary font-bold">{stageCheck?.target_stage || 'Next Stage'}</span>
              </span>

              {stageCheck?.allowed ? (
                <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-2.5 text-xs text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 size={14} className="shrink-0" />
                  <span>All strict entry criteria satisfied. Ready to advance!</span>
                </div>
              ) : (
                <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-2.5 text-xs text-amber-400 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <AlertTriangle size={13} /> Missing Entry Criteria:
                  </div>
                  <ul className="list-disc list-inside text-[11px] text-muted-foreground space-y-0.5">
                    {stageCheck?.missing_criteria?.map((crit: string, cIdx: number) => (
                      <li key={cIdx}>{crit}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Advance Stage Buttons */}
            <div className="flex items-center gap-2 pt-1">
              <Button
                onClick={() => handleAdvanceStage(stageCheck?.target_stage || 'closing')}
                disabled={advancingStage || !stageCheck?.allowed}
                className="flex-1 h-8 text-xs font-bold gap-1.5"
              >
                {advancingStage ? <RefreshCw size={13} className="animate-spin" /> : <ArrowRight size={13} />}
                Advance to {stageCheck?.target_stage || 'Next'}
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsLossModalOpen(true)}
                className="h-8 text-xs text-destructive hover:bg-destructive/10 border-destructive/30"
              >
                Mark Lost
              </Button>
            </div>
          </div>

          {/* Proposal & Contract Generator Card */}
          <div className="rounded-xl border border-border bg-card p-4 space-y-3.5 shadow-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-primary" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">
                  Commercial Proposal &amp; Contract
                </h3>
              </div>
              {termsHash && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                  SHA-256 Verified
                </span>
              )}
            </div>

            {/* Signatory Inputs */}
            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <div>
                <label className="text-[11px] font-medium text-muted-foreground block mb-1">
                  Client Signatory Name
                </label>
                <Input
                  value={clientSignatoryName}
                  onChange={(e) => setClientSignatoryName(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>
              <div>
                <label className="text-[11px] font-medium text-muted-foreground block mb-1">
                  Signatory Title
                </label>
                <Input
                  value={clientSignatoryTitle}
                  onChange={(e) => setClientSignatoryTitle(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] font-medium text-muted-foreground block mb-1">
                Custom Commercial Terms / Special Clauses (Optional)
              </label>
              <Textarea
                value={customProposalNotes}
                onChange={(e) => setCustomProposalNotes(e.target.value)}
                placeholder="e.g. Net 45 upon signoff; includes 2 on-site architecture workshops."
                rows={2}
                className="text-xs"
              />
            </div>

            <Button
              onClick={handleGenerateProposal}
              disabled={generatingProposal || calculatedQuote?.floor_violation}
              className="w-full h-8.5 text-xs gap-1.5 bg-primary text-primary-foreground font-semibold"
            >
              {generatingProposal ? <RefreshCw size={13} className="animate-spin" /> : <Sparkles size={13} />}
              Generate Official Proposal Document
            </Button>

            {/* Rendered Proposal Preview Box */}
            {proposalMarkdown && (
              <div className="rounded-lg border border-border bg-muted/20 p-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-foreground">Generated Document Preview:</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(proposalMarkdown);
                      notify.success('Proposal markdown copied to clipboard');
                    }}
                    className="text-[11px] text-primary hover:underline flex items-center gap-1"
                  >
                    <Copy size={11} /> Copy Markdown
                  </button>
                </div>
                <div className="max-h-[220px] overflow-y-auto rounded bg-background p-3 text-[11px] font-mono leading-relaxed text-muted-foreground border border-border/50 whitespace-pre-wrap">
                  {proposalMarkdown}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── MARK AS LOST MODAL ── */}
      {isLossModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <XCircle size={16} className="text-destructive" />
                Record Deal as Closed Lost
              </h3>
              <button
                onClick={() => setIsLossModalOpen(false)}
                className="text-muted-foreground hover:text-foreground text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-foreground mb-1">
                  Primary Loss Reason *
                </label>
                <select
                  value={lossReason}
                  onChange={(e) => setLossReason(e.target.value)}
                  className="w-full h-8 rounded-md border border-border bg-background px-2.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="competitor_chosen">Lost to Competitor</option>
                  <option value="budget_constraint">Budget Constraint / Freeze</option>
                  <option value="no_decision">No Decision / Status Quo Kept</option>
                  <option value="feature_gap">Product Feature / Compliance Gap</option>
                  <option value="timing_unfavorable">Timing Unfavorable / Deferred</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">
                  Debrief Notes / Feedback
                </label>
                <Textarea
                  value={lossNotes}
                  onChange={(e) => setLossNotes(e.target.value)}
                  placeholder="What specifically led to this outcome? Which competitor was selected?"
                  rows={3}
                  className="text-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsLossModalOpen(false)}
                  className="h-8 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleMarkLost}
                  className="h-8 text-xs font-semibold"
                >
                  Confirm Closed Lost
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

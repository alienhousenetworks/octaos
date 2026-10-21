'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Building2, Users, Target, ShieldCheck, AlertTriangle, TrendingUp, Sparkles, 
  Plus, CheckCircle2, Search, ExternalLink, RefreshCw, Mail, Phone,
  Layers, Clock, ArrowRight, Zap, ShieldAlert, Check
} from 'lucide-react';
import { notify } from '@/lib/notify';

interface SalesAccount360ViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

export default function SalesAccount360View({ token, API_URL, fetchWithAuth }: SalesAccount360ViewProps) {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [account360, setAccount360] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reconciling, setReconciling] = useState(false);

  // Add Member Modal State
  const [isAddMemberOpen, setIsAddMemberOpen] = useState(false);
  const [memberName, setMemberName] = useState('');
  const [memberEmail, setMemberEmail] = useState('');
  const [memberTitle, setMemberTitle] = useState('');
  const [memberRole, setMemberRole] = useState('economic_buyer');
  const [memberPhone, setMemberPhone] = useState('');
  const [memberLinkedin, setMemberLinkedin] = useState('');
  const [submittingMember, setSubmittingMember] = useState(false);

  const fetchAccounts = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const q = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : '';
      const res = await fetchWithAuth(`${API_URL}/sales-crm/accounts${q}`);
      if (res.ok) {
        const data = await res.json();
        setAccounts(data);
        if (data.length > 0 && !selectedAccountId) {
          setSelectedAccountId(data[0].id);
        }
      }
    } catch (err) {
      console.error('Error fetching accounts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [token]);

  const fetchAccountDetail = async (companyId: string) => {
    setDetailLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/accounts/${companyId}/360`);
      if (res.ok) {
        const data = await res.json();
        setAccount360(data);
      }
    } catch (err) {
      console.error('Error fetching Account 360:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAccountId) {
      fetchAccountDetail(selectedAccountId);
    }
  }, [selectedAccountId]);

  const handleReconcile = async () => {
    setReconciling(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/reconcile`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        notify.success(`Reconciled ${data.scanned} leads. Promoted ${data.promoted_to_canonical} to canonical Sales OS.`);
        fetchAccounts();
        if (selectedAccountId) {
          fetchAccountDetail(selectedAccountId);
        }
      } else {
        notify.error('Reconciliation failed. Check server logs.');
      }
    } catch (err) {
      notify.error('Reconciliation failed.');
    } finally {
      setReconciling(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAccountId || !memberEmail || !memberName) {
      notify.error('Name and email are required.');
      return;
    }
    setSubmittingMember(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/accounts/${selectedAccountId}/committee`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: memberName,
          email: memberEmail,
          title: memberTitle || 'Executive',
          role_type: memberRole,
          phone: memberPhone || undefined,
          linkedin_url: memberLinkedin || undefined,
        }),
      });
      if (res.ok) {
        notify.success(`Added ${memberName} to Buying Committee!`);
        setIsAddMemberOpen(false);
        setMemberName('');
        setMemberEmail('');
        setMemberTitle('');
        setMemberPhone('');
        setMemberLinkedin('');
        fetchAccountDetail(selectedAccountId);
        fetchAccounts();
      } else {
        const err = await res.json();
        notify.error(err.detail || 'Failed to add member.');
      }
    } catch (err) {
      notify.error('Network error adding member.');
    } finally {
      setSubmittingMember(false);
    }
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'economic_buyer':
        return <span className="text-[11px] font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-md">Economic Buyer</span>;
      case 'champion':
        return <span className="text-[11px] font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-md">Champion</span>;
      case 'technical_evaluator':
        return <span className="text-[11px] font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-md">Technical Evaluator</span>;
      case 'blocker':
        return <span className="text-[11px] font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30 px-2 py-0.5 rounded-md">Blocker</span>;
      default:
        return <span className="text-[11px] font-semibold bg-sky-500/15 text-sky-300 border border-sky-500/30 px-2 py-0.5 rounded-md">Influencer</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* ── HEADER ACTIONS & RECONCILE ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card/60 border border-border/80 p-4 rounded-xl backdrop-blur-xs">
        <div>
          <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Building2 className="text-primary w-5 h-5" />
            Account 360 & Buying Committee Workspace
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Enterprise ServiceNow-style account intelligence. Canonical account profiles, multi-stakeholder committee mapping, and signal timelines.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReconcile}
            disabled={reconciling}
            className="border-primary/30 text-primary hover:bg-primary/10 gap-1.5 text-xs font-medium"
          >
            <RefreshCw size={13} className={reconciling ? 'animate-spin' : ''} />
            {reconciling ? 'Reconciling...' : 'Reconcile Leads to Canonical Core'}
          </Button>
        </div>
      </div>

      {/* ── TWO-PANE WORKSPACE ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANE: ACCOUNTS LIST */}
        <div className="lg:col-span-4 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search companies or domains..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchAccounts()}
              className="pl-9 h-9 text-xs bg-card/80 border-border/80"
            />
          </div>

          <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
            {loading ? (
              <div className="text-center py-8 text-xs text-muted-foreground">Loading accounts...</div>
            ) : accounts.length === 0 ? (
              <div className="text-center py-8 text-xs text-muted-foreground border border-dashed border-border rounded-lg p-4">
                No canonical accounts found. Click "Reconcile Leads" to promote leads to canonical accounts.
              </div>
            ) : (
              accounts.map((acc) => {
                const isSelected = acc.id === selectedAccountId;
                return (
                  <div
                    key={acc.id}
                    onClick={() => setSelectedAccountId(acc.id)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer text-left ${
                      isSelected
                        ? 'bg-primary/10 border-primary shadow-xs'
                        : 'bg-card/70 hover:bg-card/90 border-border/70'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="font-semibold text-sm text-foreground flex items-center gap-1.5">
                          {acc.display_name}
                          {acc.is_multi_threaded && (
                            <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.2 rounded font-mono">
                              Multi-Threaded
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                          <span>{acc.canonical_domain || 'no domain'}</span>
                          <span>•</span>
                          <span>{acc.industry}</span>
                        </div>
                      </div>
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-secondary text-secondary-foreground border border-border">
                        {acc.stage}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs mt-3 pt-2 border-t border-border/50 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Users size={12} className="text-muted-foreground" />
                        <span>{acc.committee_count} stakeholders</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-primary font-mono font-medium">
                          ICP: {Math.round(acc.icp_score)}%
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT PANE: ACCOUNT 360 DOSSIER */}
        <div className="lg:col-span-8">
          {detailLoading ? (
            <div className="bg-card border border-border rounded-xl p-12 text-center text-xs text-muted-foreground">
              <RefreshCw className="animate-spin w-5 h-5 mx-auto mb-2 text-primary" />
              Loading Account 360 profile...
            </div>
          ) : !account360 ? (
            <div className="bg-card border border-border rounded-xl p-12 text-center text-xs text-muted-foreground">
              Select an account on the left to inspect its complete 360 profile.
            </div>
          ) : (
            <div className="space-y-6">
              {/* ── ACCOUNT IDENTITY BANNER ── */}
              <Card className="bg-card/90 border-border/80 shadow-xs">
                <CardHeader className="pb-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2.5">
                        <CardTitle className="text-xl font-bold text-foreground">
                          {account360.company.display_name}
                        </CardTitle>
                        {account360.deal_room?.is_multi_threaded ? (
                          <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1">
                            <ShieldCheck size={12} />
                            Multi-Threaded Coverage
                          </span>
                        ) : (
                          <span className="text-xs bg-rose-500/20 text-rose-400 border border-rose-500/30 px-2.5 py-0.5 rounded-full font-medium flex items-center gap-1">
                            <AlertTriangle size={12} />
                            Single-Threaded Risk
                          </span>
                        )}
                      </div>
                      <CardDescription className="text-xs text-muted-foreground mt-1 flex flex-wrap items-center gap-2">
                        {account360.company.website && (
                          <a
                            href={account360.company.website}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary hover:underline flex items-center gap-1"
                          >
                            {account360.company.canonical_domain || account360.company.website}
                            <ExternalLink size={11} />
                          </a>
                        )}
                        <span>•</span>
                        <span>{account360.company.industry || 'Technology'}</span>
                        <span>•</span>
                        <span>{account360.company.employee_count ? `${account360.company.employee_count} employees` : account360.company.employee_band}</span>
                        {account360.company.hq_city && (
                          <>
                            <span>•</span>
                            <span>{account360.company.hq_city}, {account360.company.hq_country}</span>
                          </>
                        )}
                      </CardDescription>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        onClick={() => setIsAddMemberOpen(true)}
                        className="bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5 text-xs h-8"
                      >
                        <Plus size={13} />
                        Add Stakeholder
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  {/* Stage Progress Tracker */}
                  <div className="bg-secondary/40 border border-border/60 rounded-lg p-3 mt-1 flex items-center justify-between text-xs font-medium">
                    <span className="text-muted-foreground">Deal Stage:</span>
                    <div className="flex items-center gap-2">
                      {['discovered', 'qualified', 'evaluating', 'closed_won'].map((st, idx) => {
                        const currentStage = account360.deal_room?.stage || 'discovered';
                        const isCurrent = currentStage === st;
                        return (
                          <React.Fragment key={st}>
                            <span
                              className={`px-2 py-0.5 rounded uppercase tracking-wider text-[10px] font-bold ${
                                isCurrent
                                  ? 'bg-primary text-primary-foreground'
                                  : 'bg-muted/50 text-muted-foreground'
                              }`}
                            >
                              {st}
                            </span>
                            {idx < 3 && <ArrowRight size={11} className="text-muted-foreground" />}
                          </React.Fragment>
                        );
                      })}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* ── AGENT COPILOT RECOMMENDATION CARD ── */}
              {account360.agent_recommendation && (
                <div className="bg-gradient-to-r from-primary/10 via-card to-card border border-primary/30 rounded-xl p-4 shadow-xs">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-primary/20 text-primary mt-0.5">
                      <Sparkles size={16} />
                    </div>
                    <div className="space-y-1 text-left flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider text-primary">
                          Autonomous Deal Strategist Agent
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          account360.agent_recommendation.urgency === 'high'
                            ? 'bg-rose-500/20 text-rose-300'
                            : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {account360.agent_recommendation.urgency} Urgency
                        </span>
                      </div>
                      <div className="text-sm font-semibold text-foreground">
                        {account360.agent_recommendation.recommended_action}
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {account360.agent_recommendation.rationale} Target profile: <span className="text-foreground font-medium">{account360.agent_recommendation.target_persona}</span>.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* ── BUYING COMMITTEE MATRIX ── */}
              <Card className="bg-card/90 border-border/80 shadow-xs">
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-base font-bold text-foreground flex items-center gap-2">
                      <Users className="text-primary w-4 h-4" />
                      Buying Committee Matrix ({account360.buying_committee.length})
                    </CardTitle>
                    <CardDescription className="text-xs text-muted-foreground">
                      Multi-stakeholder decision maker coverage mapped to enterprise deal roles.
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsAddMemberOpen(true)}
                    className="h-7 text-xs border-dashed gap-1"
                  >
                    <Plus size={12} />
                    Add Member
                  </Button>
                </CardHeader>
                <CardContent>
                  {account360.buying_committee.length === 0 ? (
                    <div className="text-center py-6 border border-dashed border-border rounded-lg text-xs text-muted-foreground">
                      No buying committee members identified yet. Click "Add Member" or run the Contact Discovery Agent.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {account360.buying_committee.map((member: any) => (
                        <div
                          key={member.id}
                          className="p-3.5 rounded-lg border border-border/70 bg-secondary/20 hover:bg-secondary/40 transition-colors space-y-2 text-left"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="font-semibold text-sm text-foreground">{member.name}</div>
                              <div className="text-xs text-muted-foreground">{member.title}</div>
                            </div>
                            {getRoleBadge(member.role_type)}
                          </div>

                          <div className="text-xs text-muted-foreground flex items-center gap-3 pt-1 border-t border-border/40">
                            <span className="flex items-center gap-1 font-mono">
                              <Mail size={11} className="text-muted-foreground" />
                              {member.email}
                            </span>
                            {member.phone && (
                              <span className="flex items-center gap-1">
                                <Phone size={11} className="text-muted-foreground" />
                                {member.phone}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* ── INTENT SIGNALS & TIMELINE ── */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="bg-card/90 border-border/80">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                      <Zap className="text-amber-400 w-4 h-4" />
                      Active Intent Signals ({account360.signals.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 max-h-64 overflow-y-auto">
                    {account360.signals.length === 0 ? (
                      <div className="text-xs text-muted-foreground py-4 text-center">No signals recorded yet.</div>
                    ) : (
                      account360.signals.map((sig: any) => (
                        <div key={sig.id} className="p-2.5 rounded-md bg-secondary/20 border border-border/50 text-xs text-left">
                          <div className="flex items-center justify-between font-semibold text-foreground">
                            <span>{sig.signal_type}</span>
                            <span className="text-[10px] text-muted-foreground font-mono">{sig.source_key}</span>
                          </div>
                          <p className="text-muted-foreground text-[11px] mt-0.5">{sig.summary || 'Signal event observed'}</p>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-card/90 border-border/80">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
                      <Clock className="text-sky-400 w-4 h-4" />
                      Recent Activity Feed ({account360.activities.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 max-h-64 overflow-y-auto">
                    {account360.activities.length === 0 ? (
                      <div className="text-xs text-muted-foreground py-4 text-center">No activity history recorded yet.</div>
                    ) : (
                      account360.activities.map((act: any) => (
                        <div key={act.id} className="p-2.5 rounded-md bg-secondary/20 border border-border/50 text-xs text-left">
                          <div className="flex items-center justify-between font-semibold text-foreground">
                            <span>{act.subject || act.activity_type}</span>
                            <span className="text-[10px] text-muted-foreground">{act.created_at?.split('T')[0]}</span>
                          </div>
                          <p className="text-muted-foreground text-[11px] line-clamp-1 mt-0.5">{act.content}</p>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── ADD COMMITTEE MEMBER MODAL ── */}
      <Dialog open={isAddMemberOpen} onOpenChange={setIsAddMemberOpen}>
        <DialogContent className="max-w-md bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">Add Buying Committee Stakeholder</DialogTitle>
            <DialogDescription className="text-xs">
              Register a decision-maker and map their strategic role in the enterprise deal.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleAddMember} className="space-y-3.5 mt-2">
            <div>
              <label className="text-xs font-semibold text-foreground">Full Name *</label>
              <Input
                placeholder="Jane Doe"
                value={memberName}
                onChange={(e) => setMemberName(e.target.value)}
                required
                className="h-8 text-xs mt-1"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-foreground">Work Email *</label>
              <Input
                type="email"
                placeholder="jane@company.com"
                value={memberEmail}
                onChange={(e) => setMemberEmail(e.target.value)}
                required
                className="h-8 text-xs mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-foreground">Job Title</label>
                <Input
                  placeholder="Chief Technology Officer"
                  value={memberTitle}
                  onChange={(e) => setMemberTitle(e.target.value)}
                  className="h-8 text-xs mt-1"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">Strategic Role</label>
                <Select value={memberRole} onValueChange={(val) => val && setMemberRole(val)}>
                  <SelectTrigger className="h-8 text-xs mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="economic_buyer">Economic Buyer</SelectItem>
                    <SelectItem value="champion">Champion</SelectItem>
                    <SelectItem value="technical_evaluator">Technical Evaluator</SelectItem>
                    <SelectItem value="legal_procurement">Legal / Procurement</SelectItem>
                    <SelectItem value="influencer">Influencer</SelectItem>
                    <SelectItem value="blocker">Blocker</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-foreground">Phone Number</label>
                <Input
                  placeholder="+1 (555) 019-2831"
                  value={memberPhone}
                  onChange={(e) => setMemberPhone(e.target.value)}
                  className="h-8 text-xs mt-1"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-foreground">LinkedIn URL</label>
                <Input
                  placeholder="https://linkedin.com/in/..."
                  value={memberLinkedin}
                  onChange={(e) => setMemberLinkedin(e.target.value)}
                  className="h-8 text-xs mt-1"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border mt-4">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsAddMemberOpen(false)} className="text-xs h-8">
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={submittingMember} className="bg-primary text-primary-foreground text-xs h-8">
                {submittingMember ? 'Adding...' : 'Save Stakeholder'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

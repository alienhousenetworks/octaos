'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Bot, ShieldCheck, Activity, Terminal, Play, CheckCircle2, 
  AlertCircle, Clock, Zap, Cpu, Search, RefreshCw, Layers
} from 'lucide-react';
import { notify } from '@/lib/notify';

interface SalesAgentCommandCenterProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

const AGENT_TEAMS = [
  {
    name: 'Team 1: Market Intelligence & Discovery',
    agents: ['Market Research Agent', 'ICP Strategist Agent', 'Intent Signal Agent', 'Account Research Agent', 'Territory Planning Agent'],
  },
  {
    name: 'Team 2: Contact Intelligence & Qualification',
    agents: ['Contact Discovery Agent', 'Waterfall Enrichment Agent', 'Identity Resolution Agent', 'Deliverability & Compliance Agent', 'Lead Qualification Agent'],
  },
  {
    name: 'Team 3: Outreach & Engagement',
    agents: ['Sales Personalization Agent', 'Sequence Strategist Agent', 'Outreach Execution Agent', 'Conversation Intelligence Agent', 'Meeting Coordination Agent'],
  },
  {
    name: 'Team 4: Account & Opportunity Management',
    agents: ['Account Intelligence Agent', 'Buying Committee Agent', 'Opportunity Strategy Agent', 'Deal Progression Agent', 'Deal Risk Agent'],
  },
  {
    name: 'Team 5: Deal Desk & Commercial Operations',
    agents: ['CPQ Agent', 'Pricing & Margin Agent', 'Proposal Generation Agent', 'Contract Review Agent', 'Approval Orchestration Agent'],
  },
  {
    name: 'Team 6: Sales Management & Forecasting',
    agents: ['Sales Manager Agent', 'Forecasting Agent', 'Performance Coach Agent', 'Pipeline Hygiene Agent', 'Revenue Operations Agent'],
  },
  {
    name: 'Team 7: Unified Communications',
    agents: ['Inbox Triage Agent', 'Response Drafting Agent', 'Objection Handling Agent', 'Conversation Summarization Agent', 'Escalation Agent'],
  },
  {
    name: 'Team 8: Integrations & Data Reliability',
    agents: ['CRM Synchronization Agent', 'Integration Health Agent', 'Data Quality Agent', 'Source Attribution Agent', 'Workflow Recovery Agent'],
  },
  {
    name: 'Team 9: Revenue Growth & Lifecycle',
    agents: ['Campaign Intelligence Agent', 'Source ROI Agent', 'Expansion Agent', 'Renewal Intelligence Agent', 'Win/Loss Intelligence Agent'],
  },
  {
    name: 'Team 10: Governance & Platform Intelligence',
    agents: ['Sales Orchestrator Agent', 'Policy & Permission Agent', 'Audit & Evidence Agent', 'Agent Evaluation Agent', 'Workflow Optimization Agent'],
  },
];

export default function SalesAgentCommandCenter({ token, API_URL, fetchWithAuth }: SalesAgentCommandCenterProps) {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isDispatchOpen, setIsDispatchOpen] = useState(false);
  const [dispatchGoal, setDispatchGoal] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('sales_orchestrator');
  const [dispatching, setDispatching] = useState(false);

  const fetchRuns = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/agents/runs`);
      if (res.ok) {
        const data = await res.json();
        setRuns(data);
      }
    } catch (err) {
      console.error('Error fetching agent runs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    const interval = setInterval(fetchRuns, 10000);
    return () => clearInterval(interval);
  }, [token]);

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispatchGoal.trim()) {
      notify.error('Please enter an objective or goal for the agent.');
      return;
    }
    setDispatching(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-crm/agents/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: dispatchGoal.trim(),
          agent_id: selectedAgent,
        }),
      });
      if (res.ok) {
        notify.success('Autonomous agent task dispatched successfully!');
        setIsDispatchOpen(false);
        setDispatchGoal('');
        fetchRuns();
      } else {
        notify.error('Failed to dispatch agent.');
      }
    } catch (err) {
      notify.error('Network error dispatching agent.');
    } finally {
      setDispatching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* ── HEADER BANNER ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card/60 border border-border/80 p-4 rounded-xl backdrop-blur-xs">
        <div>
          <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Cpu className="text-primary w-5 h-5" />
            Agent Command Center & 50-Agent Organization
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Durable, governed agent runtime. 10 specialized functional teams orchestrated under strict tenant boundaries.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => setIsDispatchOpen(true)}
            className="bg-primary hover:bg-primary/90 text-primary-foreground gap-1.5 text-xs font-medium"
          >
            <Play size={13} />
            Dispatch Agent Task
          </Button>
        </div>
      </div>

      {/* ── LIVE EXECUTION RUNS ── */}
      <Card className="bg-card/90 border-border/80 shadow-xs">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
              <Activity className="text-emerald-400 w-4 h-4" />
              Live Execution Sessions & Runs ({runs.length})
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Durable execution sessions tracked in real time.
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchRuns} className="h-7 text-xs gap-1">
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <div className="text-center py-8 border border-dashed border-border rounded-lg text-xs text-muted-foreground">
              No active agent runs. Click "Dispatch Agent Task" to trigger an autonomous workflow.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-border/60 text-muted-foreground">
                    <th className="pb-2 font-semibold">Agent ID</th>
                    <th className="pb-2 font-semibold">Status</th>
                    <th className="pb-2 font-semibold">Goal / Directive</th>
                    <th className="pb-2 font-semibold">Tokens</th>
                    <th className="pb-2 font-semibold">Cost (USD)</th>
                    <th className="pb-2 font-semibold">Started At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {runs.map((r) => (
                    <tr key={r.id} className="hover:bg-secondary/20">
                      <td className="py-2.5 font-mono text-primary font-medium">{r.agent_id}</td>
                      <td className="py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          r.status === 'completed'
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : r.status === 'running'
                            ? 'bg-amber-500/20 text-amber-300 animate-pulse'
                            : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="py-2.5 max-w-xs truncate text-foreground">{r.goal}</td>
                      <td className="py-2.5 font-mono">{r.tokens_used}</td>
                      <td className="py-2.5 font-mono">${Number(r.cost_usd || 0).toFixed(4)}</td>
                      <td className="py-2.5 text-muted-foreground font-mono">{r.started_at?.split('T')[1]?.substring(0, 8) || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── 50-AGENT TARGET CATALOG (10 TEAMS) ── */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
          <Layers className="text-primary w-4 h-4" />
          Autonomous 50-Agent Catalog by Functional Team
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {AGENT_TEAMS.map((team, idx) => (
            <Card key={idx} className="bg-card/70 border-border/70 hover:border-border transition-colors">
              <CardHeader className="py-3 px-4 bg-secondary/15 border-b border-border/40">
                <CardTitle className="text-xs font-bold text-foreground flex items-center justify-between">
                  <span>{team.name}</span>
                  <span className="text-[10px] text-primary font-mono font-normal">5 agents</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="py-3 px-4 space-y-1.5">
                {team.agents.map((ag, aIdx) => (
                  <div key={aIdx} className="flex items-center justify-between text-xs py-1">
                    <span className="text-foreground/90 font-medium flex items-center gap-2">
                      <Bot size={13} className="text-muted-foreground" />
                      {ag}
                    </span>
                    <span className="text-[10px] bg-primary/10 text-primary border border-primary/20 px-1.5 py-0.2 rounded font-mono">
                      Active
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* ── DISPATCH AGENT MODAL ── */}
      <Dialog open={isDispatchOpen} onOpenChange={setIsDispatchOpen}>
        <DialogContent className="max-w-md bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">Dispatch Specialist Agent</DialogTitle>
            <DialogDescription className="text-xs">
              Provide an objective. The Sales Orchestrator will plan, delegate, execute typed tools, and verify the outcome.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleDispatch} className="space-y-3 mt-2">
            <div>
              <label className="text-xs font-semibold text-foreground">Select Specialist Agent</label>
              <Select value={selectedAgent} onValueChange={(val) => val && setSelectedAgent(val)}>
                <SelectTrigger className="h-8 text-xs mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sales_orchestrator">Sales Orchestrator Agent (Default)</SelectItem>
                  <SelectItem value="account_researcher">Account Research Agent</SelectItem>
                  <SelectItem value="qualifier">Lead Qualification Agent</SelectItem>
                  <SelectItem value="composer">Sales Personalization Agent</SelectItem>
                  <SelectItem value="deal_strategist">Opportunity Strategy Agent</SelectItem>
                  <SelectItem value="proposal_cpq">CPQ & Proposal Agent</SelectItem>
                  <SelectItem value="sales_manager">Sales Manager Agent</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground">Objective / Goal Directive *</label>
              <Input
                placeholder="e.g. Audit buying committee coverage for Cyberdyne Systems and map CTO"
                value={dispatchGoal}
                onChange={(e) => setDispatchGoal(e.target.value)}
                required
                className="h-8 text-xs mt-1"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-border mt-4">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsDispatchOpen(false)} className="text-xs h-8">
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={dispatching} className="bg-primary text-primary-foreground text-xs h-8">
                {dispatching ? 'Dispatching...' : 'Dispatch Agent'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

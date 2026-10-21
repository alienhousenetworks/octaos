'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import {
  Users,
  Plus,
  Loader2,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Bot,
  Sparkles,
  Layers,
} from 'lucide-react';
import AgentCard from './components/agent-card';
import AgentFilters from './components/agent-filters';
import AgentCreateWizard from './agent-create-view';
import { AgentItem, WorkforceSummary } from '@/lib/agent-types';

interface AgentDirectoryViewProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  token: string | null;
  onSelectAgent?: (agentId: string) => void;
}

export default function AgentDirectoryView({
  API_URL,
  fetchWithAuth,
  token,
  onSelectAgent,
}: AgentDirectoryViewProps) {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [summary, setSummary] = useState<WorkforceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('all');
  const [isWizardOpen, setIsWizardOpen] = useState(false);

  const fetchAgents = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/agents`);
      if (res.ok) {
        const data = await res.json();
        setAgents(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error('Failed to load agents:', e);
    }
  }, [API_URL, fetchWithAuth, token]);

  const fetchSummary = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/workforce/summary`);
      if (res.ok) {
        setSummary(await res.json());
      }
    } catch {
      // Telemetry stays honest with em dashes
      setSummary(null);
    }
  }, [API_URL, fetchWithAuth, token]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    Promise.all([fetchAgents(), fetchSummary()]).finally(() => {
      if (mounted) setLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, [fetchAgents, fetchSummary]);

  // Department counts
  const deptCounts = useMemo(() => {
    const counts: Record<string, number> = { all: agents.length };
    agents.forEach((a) => {
      const d = a.department?.toLowerCase() || 'custom';
      counts[d] = (counts[d] || 0) + 1;
      if (!a.is_system) {
        counts['custom'] = (counts['custom'] || 0) + 1;
      }
    });
    return counts;
  }, [agents]);

  // Filtered agents
  const filteredAgents = useMemo(() => {
    return agents.filter((agent) => {
      // Department filter
      if (selectedDept !== 'all') {
        if (selectedDept === 'custom') {
          if (agent.is_system) return false;
        } else if (agent.department?.toLowerCase() !== selectedDept.toLowerCase()) {
          return false;
        }
      }

      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = agent.name?.toLowerCase().includes(q);
        const matchesRole = agent.role?.toLowerCase().includes(q);
        const matchesDesc = agent.description?.toLowerCase().includes(q);
        const matchesTool = agent.tools?.some((t) => t.toLowerCase().includes(q));
        if (!matchesName && !matchesRole && !matchesDesc && !matchesTool) {
          return false;
        }
      }

      return true;
    });
  }, [agents, selectedDept, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Hero Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Bot className="size-6 text-primary" />
            AI Workforce
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Discover, govern, and operate your autonomous enterprise agents.
          </p>
        </div>

        <Button
          type="button"
          onClick={() => setIsWizardOpen(true)}
          className="rounded-xl px-4 text-xs font-semibold shadow-md shadow-primary/10"
        >
          <Plus className="mr-1.5 size-3.5" />
          Create Custom Agent
        </Button>
      </div>

      {/* Honest Telemetry Summary Grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {/* Metric 1 */}
        <div className="rounded-2xl border border-gray-800 bg-gray-950/50 p-4">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
            Registered Agents
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-white">
              {agents.length.toString().padStart(2, '0')}
            </span>
            <span className="text-[10px] text-gray-500">
              {summary ? `${summary.system_agents} sys · ${summary.custom_agents} cust` : 'System + Custom'}
            </span>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="rounded-2xl border border-gray-800 bg-gray-950/50 p-4">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
            Running Now
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-white">
              {summary?.running_now != null ? summary.running_now : '—'}
            </span>
            <span className="text-[10px] text-gray-500">Live telemetry</span>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="rounded-2xl border border-gray-800 bg-gray-950/50 p-4">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
            Success Rate
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-emerald-400">
              {summary?.success_rate != null ? `${summary.success_rate}%` : '—'}
            </span>
            <span className="text-[10px] text-gray-500">Verified window</span>
          </div>
        </div>

        {/* Metric 4 */}
        <div className="rounded-2xl border border-gray-800 bg-gray-950/50 p-4">
          <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider block">
            Needs Attention
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-amber-400">
              {summary?.needs_attention != null ? summary.needs_attention : '—'}
            </span>
            <span className="text-[10px] text-gray-500">Approvals + failures</span>
          </div>
        </div>
      </div>

      {/* Search and Department Filter Controls */}
      <AgentFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedDept={selectedDept}
        onSelectDept={setSelectedDept}
        deptCounts={deptCounts}
      />

      {/* Agents Grid */}
      {loading ? (
        <div className="flex h-64 items-center justify-center rounded-2xl border border-gray-800 bg-gray-950/30">
          <Loader2 className="size-6 animate-spin text-primary" />
        </div>
      ) : filteredAgents.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-gray-800/80 bg-gray-950/30 p-12 text-center">
          <Bot className="size-10 text-gray-600 mb-2" />
          <h3 className="text-sm font-semibold text-white">No matching agents found</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm">
            Try adjusting your search terms or department filter to see registered workforce agents.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onOpenCockpit={onSelectAgent}
            />
          ))}
        </div>
      )}

      {/* Create Agent Wizard Modal */}
      <AgentCreateWizard
        open={isWizardOpen}
        onOpenChange={setIsWizardOpen}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onAgentCreated={() => {
          fetchAgents();
          fetchSummary();
        }}
      />
    </div>
  );
}

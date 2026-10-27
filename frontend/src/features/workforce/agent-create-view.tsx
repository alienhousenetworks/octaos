'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Bot,
  Shield,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  Check,
  Loader2,
  Wrench,
  Search,
  Mail,
  TrendingUp,
  MessageSquare,
} from 'lucide-react';
import { AutonomyLevel } from '@/lib/agent-types';
import { notify } from '@/lib/notify';
import { AGENT_AI_PROVIDERS, autoProviderLabel, providerDisplayName } from '@/lib/ai-providers';

interface AgentCreateWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onAgentCreated: (agentId?: string) => void;
}

const AUTONOMY_LEVELS: { id: AutonomyLevel; title: string; desc: string }[] = [
  { id: 'L0', title: 'L0 · Recommend only', desc: 'Synthesizes insights and presents recommendations without preparing outbound actions.' },
  { id: 'L1', title: 'L1 · Draft & Review', desc: 'Drafts emails, CRM records, and content, but requires explicit human approval before any commit.' },
  { id: 'L2', title: 'L2 · Low-risk Autonomy', desc: 'Executes verified read/write actions (search, CRM updates); holds high-risk dispatches for review.' },
  { id: 'L3', title: 'L3 · Bounded Policy', desc: 'Autonomous execution within strict ICP, budget, and cadence constraints under automated auditing.' },
];

const AVAILABLE_TOOLS = [
  { id: 'web_search', label: 'Web Research & Signal Intelligence', icon: Search },
  { id: 'lead.create', label: 'Create CRM Leads', icon: TrendingUp },
  { id: 'lead.update', label: 'Update CRM Records & Intent Scores', icon: TrendingUp },
  { id: 'email.send', label: 'Outbound Email Dispatch', icon: Mail },
  { id: 'ticket.reply', label: 'Customer Ticket Reply', icon: MessageSquare },
  { id: 'knowledge.search', label: 'Company Knowledge Retrieval (RAG)', icon: Shield },
];

export default function AgentCreateWizard({
  open,
  onOpenChange,
  API_URL,
  fetchWithAuth,
  onAgentCreated,
}: AgentCreateWizardProps) {
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);

  // Form fields
  const [name, setName] = useState('');
  const [department, setDepartment] = useState('sales');
  const [role, setRole] = useState('');
  const [description, setDescription] = useState('');
  const [autonomyLevel, setAutonomyLevel] = useState<AutonomyLevel>('L1');
  const [provider, setProvider] = useState('auto');
  const [model, setModel] = useState('');
  const [envProvider, setEnvProvider] = useState('');
  const [envModel, setEnvModel] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [selectedTools, setSelectedTools] = useState<string[]>(['web_search']);

  useEffect(() => {
    if (!open) return;
    let active = true;
    fetchWithAuth(`${API_URL}/commands/ai-mode`)
      .then(async (res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!active || !data) return;
        if (data.primary_provider) setEnvProvider(String(data.primary_provider));
        if (data.primary_model) setEnvModel(String(data.primary_model));
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [open, API_URL, fetchWithAuth]);

  const toggleTool = (toolId: string) => {
    if (selectedTools.includes(toolId)) {
      setSelectedTools(selectedTools.filter((t) => t !== toolId));
    } else {
      setSelectedTools([...selectedTools, toolId]);
    }
  };

  const handleCreate = async () => {
    if (!name.trim() || !role.trim() || !systemPrompt.trim()) {
      notify('Please complete the Agent Name, Role, and System Instructions.');
      return;
    }

    setSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          department,
          role: role.trim(),
          description: description.trim() || `${role.trim()} operating in ${department}.`,
          avatar_icon: 'Bot',
          provider,
          model,
          system_prompt: systemPrompt,
          temperature,
          tools: selectedTools,
        }),
      });

      if (res.ok) {
        const created = await res.json().catch(() => ({}));
        notify(`Custom Agent "${name}" created successfully. Opening its chat…`);
        onAgentCreated(typeof created.id === 'string' ? created.id : undefined);
        onOpenChange(false);
        // Reset
        setStep(1);
        setName('');
        setRole('');
        setDescription('');
        setSystemPrompt('');
        setSelectedTools(['web_search']);
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to create agent');
      }
    } catch (e: any) {
      notify(e.message || 'Network error creating agent');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl rounded-3xl border-gray-800 bg-gray-950 p-6 text-white shadow-2xl">
        <DialogHeader className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-primary/20 text-xs font-bold text-primary">
              Step {step} of 4
            </span>
            <DialogTitle className="text-lg font-semibold text-white">Create Custom Agent</DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground">
            Register an operational autonomous agent with governed capabilities and policy constraints.
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <div className="grid grid-cols-4 gap-2 pt-2 pb-4">
          {['Identity', 'Autonomy', 'Intelligence', 'Governance'].map((label, idx) => (
            <div key={label} className="space-y-1">
              <div
                className={`h-1.5 rounded-full transition-all ${
                  step > idx + 1
                    ? 'bg-primary'
                    : step === idx + 1
                    ? 'bg-primary/80'
                    : 'bg-gray-800'
                }`}
              />
              <span className="block text-[10px] font-medium text-gray-400">{label}</span>
            </div>
          ))}
        </div>

        {/* STEP 1: IDENTITY */}
        {step === 1 && (
          <div className="space-y-4 animate-in fade-in duration-200">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300">Agent Name *</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Enterprise SDR Lead Scout"
                className="rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Department</label>
                <select
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full h-9 rounded-xl border border-gray-800 bg-gray-900/80 px-3 text-xs text-white"
                >
                  <option value="sales">Sales</option>
                  <option value="marketing">Marketing</option>
                  <option value="support">Support</option>
                  <option value="hr">HR & Talent</option>
                  <option value="finance">Finance</option>
                  <option value="executive">Executive</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Operational Role *</label>
                <Input
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. Inbound Prospect Qualification Specialist"
                  className="rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300">Bounded Responsibility / Description</label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary of what this agent is authorized to analyze, score, or execute..."
                className="min-h-[70px] rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white"
              />
            </div>
          </div>
        )}

        {/* STEP 2: AUTONOMY LEVEL */}
        {step === 2 && (
          <div className="space-y-3 animate-in fade-in duration-200">
            <label className="text-xs font-semibold text-gray-300 block">
              Select Initial Autonomy Level
            </label>
            <div className="space-y-2">
              {AUTONOMY_LEVELS.map((lvl) => {
                const isSelected = autonomyLevel === lvl.id;
                return (
                  <button
                    key={lvl.id}
                    type="button"
                    onClick={() => setAutonomyLevel(lvl.id)}
                    className={`w-full text-left p-3.5 rounded-2xl border transition-all ${
                      isSelected
                        ? 'border-primary bg-primary/10 shadow-sm'
                        : 'border-gray-800/80 bg-gray-900/40 hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white">{lvl.title}</span>
                      {isSelected && <Check className="size-4 text-primary" />}
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">
                      {lvl.desc}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 3: INTELLIGENCE & PERSONA */}
        {step === 3 && (
          <div className="space-y-4 animate-in fade-in duration-200">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Inference Provider</label>
                <select
                  value={provider}
                  onChange={(e) => {
                    const next = e.target.value;
                    setProvider(next);
                    if (next === 'nvidia' && envModel && !model.trim()) setModel(envModel);
                  }}
                  className="w-full h-9 rounded-xl border border-gray-800 bg-gray-900/80 px-3 text-xs text-white"
                >
                  {AGENT_AI_PROVIDERS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.value === 'auto' ? autoProviderLabel(envProvider) : item.label}
                    </option>
                  ))}
                </select>
                {provider === 'auto' && (
                  <p className="text-[11px] leading-4 text-gray-500">
                    Auto uses {envProvider ? providerDisplayName(envProvider) : 'the server environment'}
                    {envModel ? ` · ${envModel}` : ''} from the server environment.
                  </p>
                )}
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-300">Foundation Model</label>
                <Input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder={envModel || 'Uses the environment model when Auto is selected'}
                  className="rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white font-mono"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/20 bg-primary/5 p-3">
              <div>
                <p className="text-xs font-semibold text-white">Start with a conversational assistant preset</p>
                <p className="mt-1 text-[11px] text-gray-400">Adds a direct, curious, candid persona. You can edit every instruction before saving.</p>
              </div>
              <Button type="button" variant="outline" size="sm" className="border-primary/30 text-xs" onClick={() => {
                setName((current) => current || 'Grok-style Assistant');
                setDepartment('general');
                setRole('Conversational AI Assistant');
                setDescription('A candid, curious, conversational assistant for research, reasoning, brainstorming, and everyday work.');
                setProvider('grok');
                setModel('grok-3');
                setSystemPrompt('You are a sharp, curious, candid AI assistant. Be conversational, useful, and intellectually honest. Answer directly; explain your reasoning at a high level without revealing private internal reasoning. Ask a clarifying question when the request is ambiguous. Separate verified facts from uncertainty, never invent sources or claim actions you did not perform, and use only tools explicitly granted to you. Before any consequential external action, explain what will happen and follow OctaOS approval policies. Match the user’s tone without being rude. Prefer concise answers, with more detail when the task warrants it.');
                setSelectedTools(['web_search', 'knowledge.search']);
              }}>
                <Sparkles className="mr-1.5 size-3.5" /> Use Grok-style preset
              </Button>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-gray-300">System Prompt & Instructions *</label>
                <span className="text-[11px] text-gray-500">Defines identity and operational guardrails</span>
              </div>
              <Textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                placeholder="You are an autonomous agent specialized in..."
                className="min-h-[120px] rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white font-mono leading-relaxed"
              />
            </div>
          </div>
        )}

        {/* STEP 4: TOOL GRANTS */}
        {step === 4 && (
          <div className="space-y-3 animate-in fade-in duration-200">
            <label className="text-xs font-semibold text-gray-300 block">
              Authorized Capability Grants
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              {AVAILABLE_TOOLS.map((t) => {
                const Icon = t.icon;
                const isChecked = selectedTools.includes(t.id);
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => toggleTool(t.id)}
                    className={`flex items-start gap-2.5 p-3 rounded-xl border text-left transition-all ${
                      isChecked
                        ? 'border-primary/60 bg-primary/10 text-white'
                        : 'border-gray-800 bg-gray-900/30 text-gray-400 hover:border-gray-700'
                    }`}
                  >
                    <Icon className={`size-4 shrink-0 mt-0.5 ${isChecked ? 'text-primary' : 'text-gray-500'}`} />
                    <div className="min-w-0 flex-1">
                      <span className="text-xs font-semibold block truncate">{t.label}</span>
                      <span className="font-mono text-[10px] text-gray-500 block truncate">{t.id}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Dialog Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-900">
          {step > 1 ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setStep(step - 1)}
              className="rounded-xl border-gray-800 text-xs font-semibold"
            >
              <ChevronLeft className="mr-1.5 size-3.5" /> Back
            </Button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <Button
              type="button"
              size="sm"
              onClick={() => {
                if (step === 1 && (!name.trim() || !role.trim())) {
                  notify('Please enter an Agent Name and Operational Role.');
                  return;
                }
                setStep(step + 1);
              }}
              className="rounded-xl text-xs font-semibold"
            >
              Next Step <ChevronRight className="ml-1.5 size-3.5" />
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              onClick={handleCreate}
              disabled={saving}
              className="rounded-xl text-xs font-semibold"
            >
              {saving ? (
                <>
                  <Loader2 className="mr-2 size-3.5 animate-spin" />
                  Registering Agent...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 size-3.5" />
                  Publish Agent
                </>
              )}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

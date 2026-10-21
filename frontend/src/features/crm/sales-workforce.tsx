'use client';

import React from 'react';
import { ShieldCheck } from 'lucide-react';

export interface WorkforceAgent {
  agent_id: string;
  present: boolean;
  readiness: string;
  lifecycle_status: string;
  uses_llm: string;
  purpose: string;
}

export interface WorkforceMap {
  orchestrator: {
    agent_id: string;
    tagline: string;
    present: boolean;
    readiness: string;
    lifecycle_status: string;
    purpose: string;
  };
  departments: {
    id: string;
    name: string;
    summary: string;
    agents: WorkforceAgent[];
  }[];
  control_plane: { id: string; name: string; status: string; note: string }[];
  canonical_count: number;
  registered_canonical_count: number;
}

interface SalesWorkforceProps {
  map: WorkforceMap | null;
  loading: boolean;
  error: string | null;
  onOpenRuns: () => void;
}

const readinessLabel: Record<string, string> = {
  implemented_deterministic: 'Code',
  implemented_hybrid: 'Model + code',
  modular_skill: 'Skill contract',
  missing: 'Missing',
};

export default function SalesWorkforce({ map, loading, error, onOpenRuns }: SalesWorkforceProps) {
  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-[#24344d] bg-[#132033] px-5 py-5 text-center text-white">
        <ShieldCheck className="mx-auto text-[#93c5fd]" size={18} />
        <h1 className="mt-2 text-xl font-semibold">Sales Orchestrator</h1>
        <p className="mt-1 text-sm text-[#b7c3d6]">Intent → plan → authorized tasks → verified results</p>
        {map ? (
          <p className="mt-2 text-xs text-[#8ea0b8]">
            {map.registered_canonical_count} of {map.canonical_count} canonical agents are registered.
            Status is the contract registry, not a production badge.
          </p>
        ) : null}
      </section>
      {loading ? <p className="text-sm text-muted-foreground">Loading the agent registry…</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {map ? (
        <>
          <div className="grid gap-3 lg:grid-cols-2">
            {map.departments.map((group) => (
              <section key={group.id} className="rounded-2xl border border-border bg-card p-4">
                <h2 className="font-semibold">{group.name}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{group.summary}</p>
                <ul className="mt-3 space-y-2">
                  {group.agents.map((agent) => (
                    <li key={agent.agent_id} className="rounded-lg border border-border px-3 py-2">
                      <div className="flex items-center justify-between gap-2">
                        <code className="text-xs">{agent.agent_id}</code>
                        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                          {readinessLabel[agent.readiness] || agent.readiness}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{agent.purpose}</p>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
          <section className="rounded-2xl border border-border bg-card p-4">
            <h2 className="font-semibold">Shared control plane</h2>
            <ul className="mt-3 grid gap-2 md:grid-cols-2">
              {map.control_plane.map((item) => (
                <li key={item.id} className="rounded-lg border border-border px-3 py-2 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{item.name}</span>
                    <span className="text-[10px] uppercase text-muted-foreground">{item.status}</span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{item.note}</p>
                </li>
              ))}
            </ul>
            <button type="button" onClick={onOpenRuns} className="mt-4 text-sm font-medium text-primary">
              Open live agent runs
            </button>
          </section>
        </>
      ) : null}
    </div>
  );
}

'use client';

import React, { useState } from 'react';
import { VerticalPack } from './sales-platform';

interface SalesIndustriesProps {
  packs: VerticalPack[];
  activeId: string | null;
  loading: boolean;
  error: string | null;
  savingId: string | null;
  notice: string | null;
  onSelect: (packId: string) => void;
}

export default function SalesIndustries({
  packs,
  activeId,
  loading,
  error,
  savingId,
  notice,
  onSelect,
}: SalesIndustriesProps) {
  const [openId, setOpenId] = useState<string | null>(activeId);
  const open = packs.find((pack) => pack.id === (openId || activeId)) || packs[0];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Industry packs</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Eighteen verticals share one CRM. Switching a pack changes labels, qualification prompts, and AI limits. It does not delete leads or create a second database.
        </p>
      </div>
      {error ? <p className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm">{error}</p> : null}
      {notice ? <p className="rounded-lg border border-border bg-muted px-3 py-2 text-sm">{notice}</p> : null}
      {loading ? <p className="text-sm text-muted-foreground">Loading packs…</p> : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid gap-2 sm:grid-cols-2">
          {packs.map((pack) => {
            const selected = pack.id === activeId;
            return (
              <button
                key={pack.id}
                type="button"
                onClick={() => setOpenId(pack.id)}
                className={`rounded-xl border p-3 text-left ${
                  selected ? 'border-primary bg-primary/5' : 'border-border bg-card hover:border-primary/40'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-semibold">{pack.name}</span>
                  <span className="rounded-full border border-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {pack.representative ? 'Representative' : 'Configuration'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{pack.summary}</p>
                <p className="mt-2 text-[11px] text-muted-foreground">Domain module: {pack.domain_status.replaceAll('_', ' ')}</p>
              </button>
            );
          })}
        </div>

        {open ? (
          <aside className="rounded-2xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Pack {open.version}</p>
            <h2 className="mt-1 text-lg font-semibold">{open.name}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{open.domain_note}</p>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-xs font-medium text-muted-foreground">Terminology</dt>
                <dd>{open.terminology.lead} · {open.terminology.account} · {open.terminology.opportunity}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-muted-foreground">Objects</dt>
                <dd>{open.objects.join(', ')}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-muted-foreground">Pipeline</dt>
                <dd>{open.stages.join(' → ')}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-muted-foreground">Qualification</dt>
                <dd>{open.qualification.join(' · ')}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-muted-foreground">AI will not</dt>
                <dd>{open.ai_guidance.prohibited.join(' ')}</dd>
              </div>
            </dl>
            <button
              type="button"
              disabled={savingId === open.id || open.id === activeId}
              onClick={() => onSelect(open.id)}
              className="mt-4 w-full rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60"
            >
              {open.id === activeId ? 'Active workspace' : savingId === open.id ? 'Switching…' : 'Use this industry'}
            </button>
            <p className="mt-2 text-xs text-muted-foreground">Existing records stay. The domain workflow listed above is not built yet.</p>
          </aside>
        ) : null}
      </div>
    </div>
  );
}

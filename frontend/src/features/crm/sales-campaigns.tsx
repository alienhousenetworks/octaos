'use client';

import React from 'react';

interface SalesCampaignsProps {
  onOpenMarketing: () => void;
  onOpenInbox: () => void;
  onOpenWorkflows: () => void;
  onOpenRuns: () => void;
}

const links = [
  {
    title: 'Marketing campaigns',
    body: 'The campaign calendar and posts already live in the campaigns module.',
    key: 'marketing' as const,
  },
  {
    title: 'Sales inbox and cadence',
    body: 'Replies, pauses, and follow-ups run from the inbox. A send stays on the delivery path.',
    key: 'inbox' as const,
  },
  {
    title: 'Visual flows',
    body: 'The workflow canvas is the automation studio. This page does not add a second builder.',
    key: 'flows' as const,
  },
  {
    title: 'Run history',
    body: 'Agent runs show the current sales workflow status.',
    key: 'runs' as const,
  },
];

export default function SalesCampaigns({
  onOpenMarketing,
  onOpenInbox,
  onOpenWorkflows,
  onOpenRuns,
}: SalesCampaignsProps) {
  const go = {
    marketing: onOpenMarketing,
    inbox: onOpenInbox,
    flows: onOpenWorkflows,
    runs: onOpenRuns,
  };
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Campaigns and execution</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Campaign work stays in the modules that already send, schedule, and record it. Nothing on this page launches a send.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {links.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={go[item.key]}
            className="rounded-2xl border border-border bg-card p-4 text-left hover:border-primary/40"
          >
            <h2 className="font-semibold">{item.title}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{item.body}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

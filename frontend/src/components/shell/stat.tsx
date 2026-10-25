import React from 'react';

export default function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-4 transition-colors hover:border-border-strong">
      <p className="text-xs font-medium tracking-wide text-muted-foreground">{label}</p>
      <div className="mt-2 text-2xl font-semibold tracking-tight tabular-nums text-foreground">{value}</div>
      {hint && <p className="mt-1.5 text-xs leading-5 text-muted-foreground">{hint}</p>}
    </div>
  );
}

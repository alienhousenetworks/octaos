import React from 'react';
import { Button } from '@/components/ui/button';

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 px-6 py-12 text-center">
      <h2 className="text-base font-semibold tracking-tight text-foreground">{title}</h2>
      {description && <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-muted-foreground">{description}</p>}
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}

export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="space-y-4" aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}</span>
      <div className="h-9 w-56 animate-pulse rounded-lg bg-muted" aria-hidden="true" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-hidden="true">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-24 animate-pulse rounded-xl border border-border bg-card" />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-xl border border-border bg-card" aria-hidden="true" />
    </div>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  description,
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-xl border border-destructive/25 bg-destructive/5 px-6 py-9 text-center">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      {description && <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted-foreground">{description}</p>}
      {onRetry && (
        <Button variant="outline" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

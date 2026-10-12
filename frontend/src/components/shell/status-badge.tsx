const STYLES: Record<string, string> = {
  draft: 'bg-zinc-500/15 text-zinc-300',
  review: 'bg-amber-500/15 text-amber-300',
  pending: 'bg-amber-500/15 text-amber-300',
  published: 'bg-emerald-500/15 text-emerald-300',
  won: 'bg-emerald-500/15 text-emerald-300',
  lost: 'bg-red-500/15 text-red-300',
  captured: 'bg-zinc-500/15 text-zinc-300',
  scored: 'bg-cyan-500/15 text-cyan-200',
  enriched: 'bg-teal-500/15 text-teal-200',
  contacted: 'bg-blue-500/15 text-blue-200',
  replied: 'bg-indigo-500/15 text-indigo-200',
  meeting_scheduled: 'bg-amber-500/15 text-amber-200',
  new: 'bg-zinc-500/15 text-zinc-300',
  screening: 'bg-blue-500/15 text-blue-200',
  interview: 'bg-amber-500/15 text-amber-200',
  offer: 'bg-emerald-500/15 text-emerald-300',
  rejected: 'bg-red-500/15 text-red-300',
  hired: 'bg-emerald-500/15 text-emerald-300',
};

export default function StatusBadge({ status }: { status?: string | null }) {
  const key = (status || 'unknown').toLowerCase().replace(/\s+/g, '_');
  const label = (status || 'Unknown').replace(/_/g, ' ');
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize ${STYLES[key] || 'bg-muted text-muted-foreground'}`}>
      {label}
    </span>
  );
}

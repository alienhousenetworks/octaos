// Status badge colour map uses semantic CSS variables from the design system.
// Backgrounds are the raw semantic colour at low opacity, text is the semantic colour.
const STYLES: Record<string, string> = {
  // Success states — phosphor-emerald
  published:          'bg-success/10 text-success border border-success/20',
  won:                'bg-success/10 text-success border border-success/20',
  hired:              'bg-success/10 text-success border border-success/20',
  offer:              'bg-success/10 text-success border border-success/20',
  active:             'bg-success/10 text-success border border-success/20',
  approved:           'bg-success/10 text-success border border-success/20',
  completed:          'bg-success/10 text-success border border-success/20',
  running:            'bg-success/10 text-success border border-success/20',

  // Warning / Attention states — amber
  review:             'bg-warning/10 text-warning border border-warning/20',
  pending:            'bg-warning/10 text-warning border border-warning/20',
  meeting_scheduled:  'bg-warning/10 text-warning border border-warning/20',
  interview:          'bg-warning/10 text-warning border border-warning/20',
  interviewed:        'bg-warning/10 text-warning border border-warning/20',
  attention:          'bg-warning/10 text-warning border border-warning/20',

  // Destructive / Error states — crimson
  lost:               'bg-destructive/10 text-destructive border border-destructive/20',
  rejected:           'bg-destructive/10 text-destructive border border-destructive/20',
  failed:             'bg-destructive/10 text-destructive border border-destructive/20',
  error:              'bg-destructive/10 text-destructive border border-destructive/20',
  canceled:           'bg-destructive/10 text-destructive border border-destructive/20',

  // Active / In progress — signal-cobalt
  executing:          'bg-primary/10 text-primary border border-primary/20',
  replied:            'bg-primary/10 text-primary border border-primary/20',
  selected:           'bg-primary/10 text-primary border border-primary/20',

  // Information states — info blue
  info:               'bg-info/10 text-info border border-info/20',
  queued:             'bg-info/10 text-info border border-info/20',

  // Neutral / Workflow stages — muted
  draft:              'bg-muted text-muted-foreground border border-border',
  captured:           'bg-muted text-muted-foreground border border-border',
  new:                'bg-muted text-muted-foreground border border-border',
  scored:             'bg-muted text-muted-foreground border border-border',
  enriched:           'bg-muted text-muted-foreground border border-border',
  contacted:          'bg-muted text-muted-foreground border border-border',
  screening:          'bg-muted text-muted-foreground border border-border',
};

export default function StatusBadge({ status }: { status?: string | null }) {
  const key = (status || 'unknown').toLowerCase().replace(/\s+/g, '_');
  const label = (status || 'Unknown').replace(/_/g, ' ');
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize ${STYLES[key] || 'bg-muted text-muted-foreground border border-border'}`}>
      {label}
    </span>
  );
}

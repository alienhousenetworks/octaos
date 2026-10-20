const STYLES: Record<string, string> = {
  // Success states
  published: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',
  won: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',
  hired: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',
  offer: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',
  active: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',
  approved: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',
  completed: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',
  running: 'bg-[#263D38] text-[#64B99A] border border-[#64B99A]/20',

  // Warning / Attention states
  review: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',
  pending: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',
  meeting_scheduled: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',
  interview: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',
  interviewed: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',
  attention: 'bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20',

  // Destructive / Error states
  lost: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',
  rejected: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',
  failed: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',
  error: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',
  canceled: 'bg-[#462F35] text-[#D9828B] border border-[#D9828B]/20',

  // Active / Selected / In Progress
  executing: 'bg-[#343D61] text-[#A1AEF0] border border-[#7888D9]/30',
  replied: 'bg-[#343D61] text-[#A1AEF0] border border-[#7888D9]/30',
  selected: 'bg-[#343D61] text-[#A1AEF0] border border-[#7888D9]/30',

  // Information states
  info: 'bg-[#2B3945] text-[#75AFCB] border border-[#75AFCB]/20',
  queued: 'bg-[#2B3945] text-[#75AFCB] border border-[#75AFCB]/20',

  // Neutral / Workflow stages
  draft: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
  captured: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
  new: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
  scored: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
  enriched: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
  contacted: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
  screening: 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]',
};

export default function StatusBadge({ status }: { status?: string | null }) {
  const key = (status || 'unknown').toLowerCase().replace(/\s+/g, '_');
  const label = (status || 'Unknown').replace(/_/g, ' ');
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium capitalize ${STYLES[key] || 'bg-[#333E4C] text-[#C1CAD6] border border-[#414C5A]'}`}>
      {label}
    </span>
  );
}

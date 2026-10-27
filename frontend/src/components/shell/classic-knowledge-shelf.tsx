'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText } from 'lucide-react';

const DEPARTMENTS = [
  { id: 'all', label: 'All' },
  { id: 'General', label: 'General' },
  { id: 'Marketing', label: 'Marketing' },
  { id: 'Sales', label: 'Sales' },
  { id: 'HR', label: 'Hiring' },
  { id: 'Support', label: 'Support' },
];

function kindOf(doc: any): 'file' | 'web' | 'text' | 'directive' {
  if (doc?.doc_type === 'Prompt Directives') return 'directive';
  if (doc?.source_type === 'web' || String(doc?.source_url || '').startsWith('http')) return 'web';
  if (doc?.source_type === 'file' || String(doc?.content || '').startsWith('Source Document:')) return 'file';
  return 'text';
}

function titleOf(doc: any) {
  const kind = kindOf(doc);
  if (kind === 'web') return doc.source_url || 'Web page';
  if (kind === 'file') {
    const named = String(doc.content || '').match(/^Source Document: ([^\n]+)/)?.[1];
    return named || doc.source_url || doc.doc_type || 'File';
  }
  return doc.doc_type || 'Note';
}

function deptLabel(value?: string) {
  if (!value) return 'Unassigned';
  if (value === 'HR') return 'Hiring';
  return value;
}

function kindLabel(kind: ReturnType<typeof kindOf>) {
  if (kind === 'file') return 'File';
  if (kind === 'web') return 'Web';
  if (kind === 'directive') return 'Directive';
  return 'Note';
}

export default function ClassicKnowledgeShelf({
  knowledge,
  department = 'all',
  limit = 6,
}: {
  knowledge: any[];
  department?: string;
  limit?: number;
}) {
  const [filter, setFilter] = useState(department || 'all');

  useEffect(() => {
    setFilter(department || 'all');
  }, [department]);

  const rows = Array.isArray(knowledge) ? knowledge : [];
  const filtered = filter === 'all' ? rows : rows.filter((doc) => (doc?.department || 'General') === filter);
  const visible = filtered.slice(0, limit);

  return (
    <div data-testid="classic-knowledge-shelf" className="rounded-2xl border border-white/[0.09] bg-[#131714] p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold"><FileText className="size-4 text-[#8be977]" /> Company knowledge</div>
          <p className="mt-1 text-xs leading-5 text-white/50">Same documents as the classic Knowledge library. Filters use the same departments.</p>
        </div>
        <Link href="/app/knowledge" className="rounded-lg border border-[#7de56b]/25 px-3 py-2 text-xs text-[#a4f196] hover:bg-[#7de56b]/10">Open classic Knowledge</Link>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label="Knowledge department">
        {DEPARTMENTS.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-pressed={filter === item.id}
            onClick={() => setFilter(item.id)}
            className={'rounded-full px-2.5 py-1 text-[11px] ' + (filter === item.id ? 'bg-[#78e565] text-[#0b1609]' : 'border border-white/10 text-white/60 hover:text-white')}
          >
            {item.label}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="mt-3 text-xs text-white/45">No documents in this department yet. Add files, sites, notes, and directives in classic Knowledge.</p>
      ) : (
        <ul className="mt-3 space-y-1.5">
          {visible.map((doc) => (
            <li key={doc.id || titleOf(doc)} className="flex items-center gap-2 rounded-lg border border-white/[0.06] px-2.5 py-2">
              <FileText className="size-3.5 shrink-0 text-[#8be977]" />
              <span className="min-w-0 flex-1 truncate text-xs text-white/80">{titleOf(doc)}</span>
              <span className="shrink-0 text-[10px] text-white/40">{deptLabel(doc.department)} · {kindLabel(kindOf(doc))}</span>
            </li>
          ))}
        </ul>
      )}
      {filtered.length > visible.length && (
        <p className="mt-2 text-[11px] text-white/40">Showing {visible.length} of {filtered.length}. The classic Knowledge page has the full library.</p>
      )}
    </div>
  );
}

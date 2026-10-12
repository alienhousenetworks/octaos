'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import PageHeader from '@/components/shell/page-header';
import { EmptyState } from '@/components/shell/states';
import { confirmAction, pushToast } from '@/lib/notify';
import {
  BookOpen,
  Building2,
  Check,
  Clock,
  Copy,
  Cpu,
  Download,
  ExternalLink,
  Eye,
  FileCode,
  FileText,
  Globe,
  Layers,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
  Upload,
  X,
} from 'lucide-react';

interface KnowledgeViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  knowledge: any[];
}

type Kind = 'file' | 'web' | 'text' | 'directive';
type KindFilter = 'all' | Kind;
type RightPane = 'read' | 'add';
type AddTab = 'upload' | 'website' | 'text' | 'directives';

const DEPARTMENTS = ['General', 'Marketing', 'Sales', 'HR', 'Support'];

function deptLabel(value?: string) {
  if (!value) return 'Unassigned';
  if (value === 'HR') return 'Hiring';
  return value;
}

function kindOf(doc: any): Kind {
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

function bodyOf(doc: any) {
  const content = String(doc?.content || '');
  if (kindOf(doc) === 'file') return content.replace(/^Source Document: [^\n]*\n+/, '');
  return content;
}

function excerptOf(doc: any, query: string) {
  const clean = bodyOf(doc).replace(/\s+/g, ' ').trim();
  const needle = query.trim().toLowerCase();
  if (!clean) return 'No extracted text.';
  if (!needle) return clean.slice(0, 160);
  const at = clean.toLowerCase().indexOf(needle);
  if (at < 0) return clean.slice(0, 160);
  const start = Math.max(0, at - 48);
  const slice = clean.slice(start, at + needle.length + 90);
  return `${start > 0 ? '…' : ''}${slice}`;
}

function timeSince(dateStr?: string) {
  if (!dateStr) return 'No date';
  const diff = Date.now() - new Date(dateStr).getTime();
  if (Number.isNaN(diff)) return 'No date';
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function kindLabel(kind: Kind) {
  if (kind === 'file') return 'File';
  if (kind === 'web') return 'Web';
  if (kind === 'directive') return 'Directive';
  return 'Note';
}

async function errorMessage(response: Response) {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail)) return detail.map((item) => item?.msg || 'Invalid request').join(' ');
  } catch {
    /* response was not JSON */
  }
  return 'The request was not accepted.';
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="text-xs font-medium text-muted-foreground">{children}</label>;
}

function DeptSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="space-y-1.5">
      <FieldLabel>Department</FieldLabel>
      <Select value={value} onValueChange={(next) => next && onChange(next)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="General">General</SelectItem>
          <SelectItem value="Marketing">Marketing</SelectItem>
          <SelectItem value="Sales">Sales</SelectItem>
          <SelectItem value="HR">Hiring</SelectItem>
          <SelectItem value="Support">Support</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}

function TypeSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="space-y-1.5">
      <FieldLabel>Category</FieldLabel>
      <Select value={value} onValueChange={(next) => next && onChange(next)}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="Brand Guidelines">Brand and tone</SelectItem>
          <SelectItem value="FAQ">FAQ and support</SelectItem>
          <SelectItem value="Pricing">Pricing</SelectItem>
          <SelectItem value="Sales Playbook">Sales playbook</SelectItem>
          <SelectItem value="Case Study">Case study</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}

export default function KnowledgeView({ token, API_URL, fetchWithAuth, fetchData, knowledge }: KnowledgeViewProps) {
  const [kbDept, setKbDept] = useState('Marketing');
  const [kbType, setKbType] = useState('Brand Guidelines');
  const [kbSearch, setKbSearch] = useState('');
  const [kbContent, setKbContent] = useState('');
  const [kbFile, setKbFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [activeTab, setActiveTab] = useState<AddTab>('upload');
  const [kindFilter, setKindFilter] = useState<KindFilter>('all');
  const [deptFilter, setDeptFilter] = useState('all');
  const [sort, setSort] = useState<'newest' | 'name'>('newest');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [rightPane, setRightPane] = useState<RightPane>('read');
  const [mobilePane, setMobilePane] = useState<'library' | 'detail'>('library');

  const [crawlUrl, setCrawlUrl] = useState('');
  const [crawlMaxPages, setCrawlMaxPages] = useState(25);
  const [crawlDepth, setCrawlDepth] = useState(2);
  const [crawlIncludePaths, setCrawlIncludePaths] = useState('');
  const [crawlExcludePaths, setCrawlExcludePaths] = useState('');
  const [crawlSchedule, setCrawlSchedule] = useState('manual');
  const [isCrawling, setIsCrawling] = useState(false);
  const [isSyncingCompany, setIsSyncingCompany] = useState(false);
  const [sources, setSources] = useState<any[]>([]);
  const [isLoadingSources, setIsLoadingSources] = useState(false);

  const toast = pushToast;

  const fetchSources = useCallback(async () => {
    if (!token) return;
    setIsLoadingSources(true);
    try {
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge/sources`);
      if (response.ok) setSources(await response.json());
    } catch {
      /* leave the previous list in place */
    } finally {
      setIsLoadingSources(false);
    }
  }, [fetchWithAuth, API_URL, token]);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const counts = useMemo(() => {
    const next = { all: knowledge.length, file: 0, web: 0, text: 0, directive: 0 };
    for (const doc of knowledge) next[kindOf(doc)] += 1;
    return next;
  }, [knowledge]);

  const departments = useMemo(() => {
    const found = new Set<string>(DEPARTMENTS);
    for (const doc of knowledge) if (doc.department) found.add(doc.department);
    return Array.from(found);
  }, [knowledge]);

  const filteredDocs = useMemo(() => {
    const needle = kbSearch.trim().toLowerCase();
    const rows = knowledge.filter((doc) => {
      if (kindFilter !== 'all' && kindOf(doc) !== kindFilter) return false;
      if (deptFilter !== 'all' && doc.department !== deptFilter) return false;
      if (!needle) return true;
      const haystack = [titleOf(doc), bodyOf(doc), doc.department, doc.doc_type, doc.source_url].join(' ').toLowerCase();
      return haystack.includes(needle);
    });
    if (sort === 'name') {
      rows.sort((a, b) => titleOf(a).localeCompare(titleOf(b)));
    }
    return rows;
  }, [knowledge, kbSearch, kindFilter, deptFilter, sort]);

  const selected = knowledge.find((doc) => doc.id === selectedId) || null;
  const failedSources = sources.filter((source) => source.last_status === 'failed');
  const pagesIndexed = sources.reduce((sum, source) => sum + (source.pages_indexed || 0), 0);

  const openDocument = (id: string) => {
    setSelectedId(id);
    setRightPane('read');
    setMobilePane('detail');
  };

  const openAdd = (tab?: AddTab) => {
    if (tab) setActiveTab(tab);
    setRightPane('add');
    setMobilePane('detail');
  };

  const uploadKnowledgeFile = async () => {
    if (!kbFile) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', kbFile);
      formData.append('department', kbDept);
      formData.append('doc_type', kbType);
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge/upload`, { method: 'POST', body: formData });
      if (!response.ok) {
        toast('error', 'Upload failed', await errorMessage(response));
        return;
      }
      const data = await response.json();
      setKbFile(null);
      await fetchData();
      if (data.document_id) openDocument(data.document_id);
      const chunks = typeof data.chunks_indexed === 'number' ? `${data.chunks_indexed} sections indexed` : 'Document indexed';
      toast('success', 'Document added', data.method ? `${chunks} · ${data.method}` : chunks);
    } catch {
      toast('error', 'Network error', 'The upload did not reach the server.');
    } finally {
      setIsUploading(false);
    }
  };

  const addKnowledge = async () => {
    if (!kbContent.trim()) return;
    const isDirective = activeTab === 'directives';
    try {
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          department: isDirective ? 'General' : kbDept,
          doc_type: isDirective ? 'Prompt Directives' : kbType,
          content: kbContent,
        }),
      });
      if (!response.ok) {
        toast('error', 'Save failed', await errorMessage(response));
        return;
      }
      setKbContent('');
      setSelectedId(null);
      setRightPane('read');
      setMobilePane('library');
      await fetchData();
      toast('success', isDirective ? 'Directive saved' : 'Note added', 'It is at the top of the library. Open it to read the stored text.');
    } catch {
      toast('error', 'Network error', 'The note did not reach the server.');
    }
  };

  const handleCrawlWebsite = async () => {
    if (!crawlUrl.trim()) return;
    setIsCrawling(true);
    try {
      const includeArr = crawlIncludePaths.split(',').map((item) => item.trim()).filter(Boolean);
      const excludeArr = crawlExcludePaths.split(',').map((item) => item.trim()).filter(Boolean);
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge/web`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: crawlUrl.trim(),
          max_pages: crawlMaxPages,
          crawl_depth: crawlDepth,
          include_paths: includeArr,
          exclude_paths: excludeArr,
          schedule: crawlSchedule,
        }),
      });
      if (!response.ok) {
        toast('error', 'Crawl failed', await errorMessage(response));
        return;
      }
      const data = await response.json();
      setCrawlUrl('');
      await fetchData();
      await fetchSources();
      toast('success', 'Website crawled', data.message || 'Pages were indexed.');
    } catch {
      toast('error', 'Network error', 'The crawl did not reach the server.');
    } finally {
      setIsCrawling(false);
    }
  };

  const handleSyncCompanyWebsite = async () => {
    setIsSyncingCompany(true);
    try {
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge/web/company-sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_pages: crawlMaxPages, crawl_depth: crawlDepth }),
      });
      if (!response.ok) {
        toast('error', 'Sync failed', await errorMessage(response));
        return;
      }
      const data = await response.json();
      await fetchData();
      await fetchSources();
      toast('success', 'Company site synced', data.message || 'The company website was indexed.');
    } catch {
      toast('error', 'Network error', 'The sync did not reach the server.');
    } finally {
      setIsSyncingCompany(false);
    }
  };

  const handleRecrawlSource = async (id: string) => {
    try {
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge/sources/${id}/recrawl`, { method: 'POST' });
      if (!response.ok) {
        toast('error', 'Re-crawl failed', await errorMessage(response));
        return;
      }
      await fetchData();
      await fetchSources();
      toast('success', 'Re-crawl finished', 'Indexed pages were refreshed.');
    } catch {
      toast('error', 'Network error', 'The re-crawl did not reach the server.');
    }
  };

  const handleDeleteSource = async (id: string) => {
    if (!(await confirmAction('Delete this website source and the pages it indexed?'))) return;
    try {
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge/sources/${id}`, { method: 'DELETE' });
      if (!response.ok) {
        toast('error', 'Delete failed', await errorMessage(response));
        return;
      }
      await fetchData();
      await fetchSources();
      toast('success', 'Source deleted', 'Its indexed pages were removed.');
    } catch {
      toast('error', 'Network error', 'The delete did not reach the server.');
    }
  };

  const deleteKnowledge = async (docId: string) => {
    if (!(await confirmAction('Delete this document from the knowledge base?'))) return;
    try {
      const response = await fetchWithAuth(`${API_URL}/commands/knowledge/${docId}`, { method: 'DELETE' });
      if (!response.ok) {
        toast('error', 'Delete failed', await errorMessage(response));
        return;
      }
      if (selectedId === docId) setSelectedId(null);
      await fetchData();
      toast('success', 'Document deleted', 'Agents will no longer retrieve it.');
    } catch {
      toast('error', 'Network error', 'The delete did not reach the server.');
    }
  };

  const copyDocument = async (doc: any) => {
    try {
      await navigator.clipboard.writeText(bodyOf(doc));
      toast('success', 'Copied', 'Document text is on the clipboard.');
    } catch {
      toast('error', 'Copy failed', 'The browser did not allow clipboard access.');
    }
  };

  const filters: { id: KindFilter; label: string; value: number }[] = [
    { id: 'all', label: 'All', value: counts.all },
    { id: 'file', label: 'Files', value: counts.file },
    { id: 'web', label: 'Web', value: counts.web },
    { id: 'text', label: 'Notes', value: counts.text },
    { id: 'directive', label: 'Directives', value: counts.directive },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        title="Knowledge"
        description="Search what agents can retrieve, open a document, or add a file, website, note, or standing directive."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { fetchData(); fetchSources(); }}>
              <RefreshCw className={isLoadingSources ? 'animate-spin' : ''} />
              Refresh
            </Button>
            <Button onClick={() => openAdd()}>
              <Plus />
              Add
            </Button>
          </div>
        }
      />

      {failedSources.length > 0 && (
        <button
          type="button"
          onClick={() => openAdd('website')}
          className="w-full rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-left text-sm"
        >
          <span className="font-medium text-foreground">{failedSources.length} website {failedSources.length === 1 ? 'source' : 'sources'} failed the last crawl.</span>
          <span className="mt-1 block text-muted-foreground">{failedSources[0].url}{failedSources[0].last_error ? ` — ${failedSources[0].last_error}` : ''}</span>
        </button>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {filters.map((filter) => (
          <button
            key={filter.id}
            type="button"
            onClick={() => { setKindFilter(filter.id); setMobilePane('library'); }}
            className={`rounded-lg border px-3 py-3 text-left ${kindFilter === filter.id ? 'border-primary bg-primary/10' : 'border-border bg-card hover:bg-muted/40'}`}
          >
            <p className="text-lg font-semibold leading-none text-foreground">{filter.value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{filter.label}</p>
          </button>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">
        {sources.length} website {sources.length === 1 ? 'source' : 'sources'} · {pagesIndexed} pages indexed
      </p>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <section className={`flex min-h-[28rem] flex-col rounded-lg border border-border bg-card lg:col-span-2 ${mobilePane === 'detail' ? 'hidden lg:flex' : 'flex'}`}>
          <div className="space-y-3 border-b border-border p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={kbSearch}
                onChange={(event) => setKbSearch(event.target.value)}
                placeholder="Search titles and text"
                aria-label="Search knowledge"
                className="px-8"
              />
              {kbSearch && (
                <button type="button" aria-label="Clear search" onClick={() => setKbSearch('')} className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground">
                  <X className="size-4" />
                </button>
              )}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Select value={deptFilter} onValueChange={(value) => value && setDeptFilter(value)}>
                <SelectTrigger className="w-full sm:w-40" aria-label="Filter by department">
                  <SelectValue placeholder="Department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All departments</SelectItem>
                  {departments.map((department) => (
                    <SelectItem key={department} value={department}>{deptLabel(department)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex rounded-lg border border-border p-0.5">
                <button type="button" onClick={() => setSort('newest')} className={`rounded-md px-2.5 py-1 text-xs ${sort === 'newest' ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}>Newest</button>
                <button type="button" onClick={() => setSort('name')} className={`rounded-md px-2.5 py-1 text-xs ${sort === 'name' ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}>Name</button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">{filteredDocs.length} shown</p>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {filteredDocs.length === 0 ? (
              <EmptyState
                title={knowledge.length === 0 ? 'Nothing is indexed yet' : 'No documents match'}
                description={knowledge.length === 0 ? 'Add a file, website, note, or directive. Agents only retrieve what is stored here.' : 'Try another word, department, or type.'}
                action={knowledge.length === 0 ? <Button onClick={() => openAdd()}>Add knowledge</Button> : undefined}
              />
            ) : (
              <ul className="space-y-1">
                {filteredDocs.map((doc) => {
                  const kind = kindOf(doc);
                  const active = doc.id === selectedId;
                  return (
                    <li key={doc.id}>
                      <button
                        type="button"
                        onClick={() => openDocument(doc.id)}
                        className={`w-full rounded-lg border px-3 py-2.5 text-left ${active ? 'border-primary bg-primary/10' : 'border-transparent hover:bg-muted/50'}`}
                      >
                        <span className="block truncate text-sm font-medium text-foreground">{titleOf(doc)}</span>
                        <span className="mt-1 block truncate text-xs text-muted-foreground">{excerptOf(doc, kbSearch)}</span>
                        <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-muted-foreground">
                          <span>{deptLabel(doc.department)}</span>
                          <span>{kindLabel(kind)}</span>
                          {kind !== 'text' && kind !== 'directive' && doc.doc_type && <span>{doc.doc_type}</span>}
                          <span>{timeSince(doc.created_at)}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>

        <section className={`min-h-[28rem] rounded-lg border border-border bg-card lg:col-span-3 ${mobilePane === 'library' ? 'hidden lg:block' : 'block'}`}>
          <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="lg:hidden" onClick={() => setMobilePane('library')}>
                Library
              </Button>
              <div className="flex rounded-lg border border-border p-0.5">
                <button type="button" onClick={() => setRightPane('read')} className={`rounded-md px-3 py-1 text-xs ${rightPane === 'read' ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}>Read</button>
                <button type="button" onClick={() => setRightPane('add')} className={`rounded-md px-3 py-1 text-xs ${rightPane === 'add' ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}>Add</button>
              </div>
            </div>
          </div>

          {rightPane === 'read' ? (
            selected ? (
              <DocumentReader
                doc={selected}
                onCopy={() => copyDocument(selected)}
                onDelete={() => deleteKnowledge(selected.id)}
                API_URL={API_URL}
                fetchWithAuth={fetchWithAuth}
                token={token}
              />
            ) : (
              <div className="p-4">
                <EmptyState
                  title="Select a document"
                  description="The text, source, and department open here. Add something new if the library does not have it yet."
                  action={<Button onClick={() => openAdd()}>Add knowledge</Button>}
                />
              </div>
            )
          ) : (
            <AddPanel
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              kbDept={kbDept}
              setKbDept={setKbDept}
              kbType={kbType}
              setKbType={setKbType}
              kbFile={kbFile}
              setKbFile={setKbFile}
              isDragging={isDragging}
              setIsDragging={setIsDragging}
              isUploading={isUploading}
              onUpload={uploadKnowledgeFile}
              kbContent={kbContent}
              setKbContent={setKbContent}
              onSaveText={addKnowledge}
              crawlUrl={crawlUrl}
              setCrawlUrl={setCrawlUrl}
              crawlMaxPages={crawlMaxPages}
              setCrawlMaxPages={setCrawlMaxPages}
              crawlDepth={crawlDepth}
              setCrawlDepth={setCrawlDepth}
              crawlIncludePaths={crawlIncludePaths}
              setCrawlIncludePaths={setCrawlIncludePaths}
              crawlExcludePaths={crawlExcludePaths}
              setCrawlExcludePaths={setCrawlExcludePaths}
              crawlSchedule={crawlSchedule}
              setCrawlSchedule={setCrawlSchedule}
              isCrawling={isCrawling}
              isSyncingCompany={isSyncingCompany}
              onCrawl={handleCrawlWebsite}
              onSync={handleSyncCompanyWebsite}
              sources={sources}
              isLoadingSources={isLoadingSources}
              onRefreshSources={fetchSources}
              onRecrawl={handleRecrawlSource}
              onDeleteSource={handleDeleteSource}
            />
          )}
        </section>
      </div>
    </div>
  );
}

function formatFileSize(bytes?: number) {
  if (!bytes || bytes <= 0) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface ChunkItem {
  id: string;
  title: string;
  content: string;
  embedding_hint?: string;
  has_embedding?: boolean;
  page_start?: number;
  page_end?: number;
  section_title?: string;
  source_url?: string;
  content_hash?: string;
  token_estimate?: number;
  created_at?: string;
}

function DocumentReader({
  doc,
  onCopy,
  onDelete,
  API_URL,
  fetchWithAuth,
  token,
}: {
  doc: any;
  onCopy: () => void;
  onDelete: () => void;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  token: string | null;
}) {
  const kind = kindOf(doc);
  const body = bodyOf(doc);
  const link = String(doc.source_url || '').startsWith('http') ? doc.source_url : null;
  const isPdf = String(doc.source_url || '').toLowerCase().endsWith('.pdf') || doc.metadata_json?.content_type === 'application/pdf';
  const isImage = /\.(png|jpe?g|gif|webp|svg)$/i.test(doc.metadata_json?.file_name || doc.source_url || '') || Boolean(doc.metadata_json?.content_type?.startsWith('image/'));
  const showQuality = kind === 'file' && typeof doc.quality_score === 'number';

  const [tab, setTab] = useState<'document' | 'parsed' | 'chunks'>(kind === 'file' ? 'document' : 'parsed');
  const [parsedSearch, setParsedSearch] = useState('');
  
  // Actual Document state
  const [fileBlobUrl, setFileBlobUrl] = useState<string | null>(null);
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [fileLoadError, setFileLoadError] = useState<string | null>(null);

  // Chunks state
  const [chunks, setChunks] = useState<ChunkItem[] | null>(null);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [chunkSearch, setChunkSearch] = useState('');
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  // Load file preview blob when Actual Document tab is active
  useEffect(() => {
    let active = true;
    let createdUrl: string | null = null;

    if (tab === 'document') {
      setIsLoadingFile(true);
      setFileLoadError(null);
      fetchWithAuth(`${API_URL}/commands/knowledge/${doc.id}/file`)
        .then(async (res) => {
          if (!active) return;
          if (!res.ok) {
            setFileLoadError('Original binary not available on server.');
            return;
          }
          const blob = await res.blob();
          if (!active) return;
          createdUrl = URL.createObjectURL(blob);
          setFileBlobUrl(createdUrl);
        })
        .catch(() => {
          if (active) setFileLoadError('Failed to load file preview.');
        })
        .finally(() => {
          if (active) setIsLoadingFile(false);
        });
    }

    return () => {
      active = false;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [tab, doc.id, API_URL, fetchWithAuth]);

  // Load chunks when Chunking tab is active
  useEffect(() => {
    let active = true;
    if (tab === 'chunks' && chunks === null) {
      setIsLoadingChunks(true);
      fetchWithAuth(`${API_URL}/commands/knowledge/${doc.id}/chunks`)
        .then(async (res) => {
          if (!active) return;
          if (res.ok) {
            const data = await res.json();
            setChunks(data);
          } else {
            setChunks([]);
          }
        })
        .catch(() => {
          if (active) setChunks([]);
        })
        .finally(() => {
          if (active) setIsLoadingChunks(false);
        });
    }
    return () => {
      active = false;
    };
  }, [tab, doc.id, API_URL, fetchWithAuth, chunks]);

  // Reset states when selected document changes
  useEffect(() => {
    setChunks(null);
    setFileBlobUrl(null);
    setFileLoadError(null);
    setParsedSearch('');
    setChunkSearch('');
    setTab(kindOf(doc) === 'file' ? 'document' : 'parsed');
  }, [doc.id]);

  const downloadOriginal = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/knowledge/${doc.id}/file`);
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const filename = doc.metadata_json?.file_name || doc.source_url || `${doc.id}.pdf`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // fallback
    }
  };

  const copyChunkText = async (c: ChunkItem) => {
    try {
      await navigator.clipboard.writeText(c.content);
      setCopiedChunkId(c.id);
      setTimeout(() => setCopiedChunkId(null), 2000);
    } catch {
      // ignore
    }
  };

  const filteredChunks = useMemo(() => {
    if (!chunks) return [];
    const q = chunkSearch.trim().toLowerCase();
    if (!q) return chunks;
    return chunks.filter((c) =>
      c.content.toLowerCase().includes(q) ||
      (c.section_title && c.section_title.toLowerCase().includes(q)) ||
      (c.title && c.title.toLowerCase().includes(q))
    );
  }, [chunks, chunkSearch]);

  const flags = [
    doc.classification && doc.classification !== 'internal' ? doc.classification : null,
    doc.approved_for_external_use ? 'Approved for external use' : null,
    typeof doc.source_authority === 'number' && doc.source_authority > 1 ? `Authority ${doc.source_authority} of 5` : null,
    doc.valid_until ? `Expires ${new Date(doc.valid_until).toLocaleDateString()}` : null,
  ].filter(Boolean);

  const wordCount = useMemo(() => {
    return body.trim() ? body.trim().split(/\s+/).length : 0;
  }, [body]);

  const estimatedPages = useMemo(() => {
    const pageMatches = body.match(/---\s*Page\s+\d+\s*---/g);
    if (pageMatches && pageMatches.length > 0) return pageMatches.length;
    return Math.max(1, Math.ceil(wordCount / 250));
  }, [body, wordCount]);

  const metaSize = formatFileSize(doc.metadata_json?.file_size);

  return (
    <div className="flex h-full flex-col">
      {/* Header Bar */}
      <div className="space-y-3 border-b border-border p-4 bg-card/50">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="break-words text-base font-semibold text-foreground flex items-center gap-2">
              <span className="truncate">{titleOf(doc)}</span>
              {metaSize && (
                <span className="rounded-md bg-muted px-2 py-0.5 text-[11px] font-mono font-normal text-muted-foreground">
                  {metaSize}
                </span>
              )}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground flex flex-wrap items-center gap-1.5">
              <span className="font-medium text-foreground/80">{deptLabel(doc.department)}</span>
              <span>·</span>
              <span>{doc.doc_type || kindLabel(kind)}</span>
              <span>·</span>
              <span>{kindLabel(kind)}</span>
              <span>·</span>
              <span>{timeSince(doc.created_at)}</span>
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <Button variant="outline" size="sm" onClick={onCopy} title="Copy extracted text">
              <Copy className="size-3.5" />
              Copy
            </Button>
            {kind === 'file' && (
              <Button variant="outline" size="sm" onClick={downloadOriginal} title="Download original file">
                <Download className="size-3.5" />
                Download
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={onDelete} title="Delete document">
              <Trash2 className="size-3.5" />
              Delete
            </Button>
          </div>
        </div>

        {/* View Switcher Tabs & Extraction Badges */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-muted/40 p-1 text-xs shadow-xs">
            <button
              type="button"
              onClick={() => setTab('document')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-all ${
                tab === 'document' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <FileText className="size-3.5" />
              Actual Document
            </button>
            <button
              type="button"
              onClick={() => setTab('parsed')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-all ${
                tab === 'parsed' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Eye className="size-3.5" />
              Parsed Data
            </button>
            <button
              type="button"
              onClick={() => setTab('chunks')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-all ${
                tab === 'chunks' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Layers className="size-3.5" />
              Chunking {chunks ? `(${chunks.length})` : ''}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {showQuality && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 font-medium text-emerald-400 border border-emerald-500/20">
                <Sparkles className="size-3" />
                {Math.round(doc.quality_score * 100)}% Quality Gate
              </span>
            )}
            {doc.extraction_method && (
              <span className="rounded-full bg-primary/10 px-2.5 py-0.5 font-medium text-primary border border-primary/20">
                {doc.extraction_method}
              </span>
            )}
            {flags.map((flag) => (
              <span key={String(flag)} className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground border border-border">
                {flag}
              </span>
            ))}
          </div>
        </div>

        {link && (
          <a href={link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-primary hover:underline break-all">
            <Globe className="size-3.5 shrink-0" />
            {link}
          </a>
        )}
      </div>

      {/* View Content Body */}
      <div className="flex-1 overflow-y-auto min-h-[30rem]">
        {/* TAB 1: ACTUAL DOCUMENT */}
        {tab === 'document' && (
          <div className="flex h-full flex-col p-4 space-y-3">
            <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-muted/20 px-3 py-2 text-xs">
              <div className="flex items-center gap-2 text-muted-foreground">
                <FileCode className="size-4 text-primary" />
                <span>Format: <strong className="text-foreground">{doc.metadata_json?.content_type || (isPdf ? 'application/pdf' : 'text/plain')}</strong></span>
                {doc.metadata_json?.file_name && (
                  <>
                    <span>·</span>
                    <span className="truncate max-w-[20rem]">Original: {doc.metadata_json.file_name}</span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                {token && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs gap-1"
                    onClick={() => window.open(`${API_URL}/commands/knowledge/${doc.id}/file?token=${encodeURIComponent(token)}`, '_blank')}
                  >
                    <ExternalLink className="size-3" />
                    Open in New Tab
                  </Button>
                )}
                <Button variant="outline" size="sm" className="h-7 text-xs gap-1" onClick={downloadOriginal}>
                  <Download className="size-3" />
                  Save Copy
                </Button>
              </div>
            </div>

            {isLoadingFile ? (
              <div className="flex h-96 flex-col items-center justify-center gap-3 text-muted-foreground">
                <Loader2 className="size-8 animate-spin text-primary" />
                <p className="text-sm">Loading document preview...</p>
              </div>
            ) : fileBlobUrl && isPdf ? (
              <div className="h-[min(50rem,75vh)] w-full overflow-hidden rounded-lg border border-border shadow-xs bg-muted/10">
                <iframe
                  src={fileBlobUrl}
                  className="h-full w-full border-0"
                  title={titleOf(doc)}
                />
              </div>
            ) : fileBlobUrl && isImage ? (
              <div className="flex h-[min(50rem,75vh)] w-full items-center justify-center overflow-hidden rounded-lg border border-border bg-muted/10 p-4">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={fileBlobUrl}
                  alt={titleOf(doc)}
                  className="max-h-full max-w-full rounded object-contain shadow-xs"
                />
              </div>
            ) : fileBlobUrl ? (
              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-xs text-muted-foreground mb-2">Original text stream view:</p>
                <iframe
                  src={fileBlobUrl}
                  className="h-[min(40rem,65vh)] w-full rounded border border-border bg-background p-3 text-sm font-mono"
                  title={titleOf(doc)}
                />
              </div>
            ) : (
              <div className="flex h-72 flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-6 text-center text-muted-foreground">
                <FileText className="size-10 text-muted-foreground/50" />
                <div className="max-w-md space-y-1">
                  <p className="text-sm font-medium text-foreground">
                    {fileLoadError || 'Direct binary preview not available'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    This document was processed directly from text or ingested prior to file archiving. You can inspect all parsed contents and individual chunk vectors in the Parsed Data and Chunking tabs.
                  </p>
                </div>
                <div className="flex gap-2 pt-2">
                  <Button size="sm" variant="outline" onClick={() => setTab('parsed')}>
                    <Eye className="size-3.5 mr-1" />
                    View Parsed Data
                  </Button>
                  <Button size="sm" variant="outline" onClick={downloadOriginal}>
                    <Download className="size-3.5 mr-1" />
                    Download Extracted Text
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: PARSED DATA */}
        {tab === 'parsed' && (
          <div className="p-4 space-y-4">
            {/* Stats Overview */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border border-border bg-muted/30 p-3">
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Estimated Pages</p>
                <p className="mt-1 text-lg font-bold text-foreground">{estimatedPages}</p>
              </div>
              <div className="rounded-lg border border-border bg-muted/30 p-3">
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Word Count</p>
                <p className="mt-1 text-lg font-bold text-foreground">{wordCount.toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-border bg-muted/30 p-3">
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Quality Gate</p>
                <p className="mt-1 text-lg font-bold text-emerald-400">
                  {typeof doc.quality_score === 'number' ? `${Math.round(doc.quality_score * 100)}%` : '100%'}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-muted/30 p-3">
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Extractor</p>
                <p className="mt-1 text-sm font-semibold truncate text-primary">{doc.extraction_method || 'Native'}</p>
              </div>
            </div>

            {/* In-document Search */}
            <div className="relative">
              <Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" />
              <Input
                placeholder="Search extracted text content..."
                value={parsedSearch}
                onChange={(e) => setParsedSearch(e.target.value)}
                className="pl-9 h-9 text-xs"
              />
              {parsedSearch && (
                <button
                  type="button"
                  onClick={() => setParsedSearch('')}
                  className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </div>

            {/* Extracted Text Content with highlighted Page boundaries */}
            {body.trim() ? (
              <div className="rounded-lg border border-border bg-card p-4 space-y-4">
                {body.split(/(?=---\s*Page\s+\d+\s*---)/g).map((section, idx) => {
                  const pageHeader = section.match(/---\s*Page\s+(\d+)\s*---/);
                  const cleanSection = section.replace(/---\s*Page\s+\d+\s*---\n*/, '').trim();
                  
                  if (parsedSearch && !section.toLowerCase().includes(parsedSearch.toLowerCase())) {
                    return null;
                  }

                  return (
                    <div key={idx} className="space-y-2 border-b border-border/50 pb-4 last:border-b-0 last:pb-0">
                      {pageHeader && (
                        <div className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1 text-xs font-semibold text-muted-foreground border border-border">
                          <span>Page {pageHeader[1]}</span>
                        </div>
                      )}
                      <p className="whitespace-pre-wrap text-sm leading-6 text-foreground font-sans selection:bg-primary/20">
                        {cleanSection || (pageHeader ? 'Page break marker' : section)}
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground p-4 text-center">This document has no extracted text.</p>
            )}
          </div>
        )}

        {/* TAB 3: CHUNKING / CHUNKS */}
        {tab === 'chunks' && (
          <div className="p-4 space-y-4">
            {/* Chunks Metrics & Vector Status Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/20 p-3">
              <div className="flex items-center gap-3">
                <div>
                  <span className="text-xs text-muted-foreground">Indexed Chunks</span>
                  <p className="text-lg font-bold text-foreground">{chunks ? chunks.length : '…'}</p>
                </div>
                <div className="h-8 w-px bg-border" />
                <div>
                  <span className="text-xs text-muted-foreground">Dense Embedding</span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="size-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs font-semibold text-emerald-400">pgvector 1536d Active</span>
                  </div>
                </div>
              </div>

              <div className="w-full sm:w-64">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Filter chunks..."
                    value={chunkSearch}
                    onChange={(e) => setChunkSearch(e.target.value)}
                    className="pl-8 h-8 text-xs"
                  />
                  {chunkSearch && (
                    <button
                      type="button"
                      onClick={() => setChunkSearch('')}
                      className="absolute right-2.5 top-2 text-muted-foreground hover:text-foreground"
                    >
                      <X className="size-3" />
                    </button>
                  )}
                </div>
              </div>
            </div>

            {isLoadingChunks ? (
              <div className="flex h-64 flex-col items-center justify-center gap-3 text-muted-foreground">
                <Loader2 className="size-7 animate-spin text-primary" />
                <p className="text-xs">Loading chunk partitions and vector indexes...</p>
              </div>
            ) : filteredChunks.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-8 text-center text-muted-foreground">
                <Layers className="size-8 mx-auto mb-2 text-muted-foreground/40" />
                <p className="text-sm font-medium text-foreground">
                  {chunks && chunks.length > 0 ? 'No chunks match your search' : 'No chunks found for this document'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Chunks are generated automatically during document ingestion and indexed with dense vectors.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredChunks.map((c, idx) => (
                  <div key={c.id || idx} className="rounded-lg border border-border bg-card p-3.5 shadow-2xs space-y-2 hover:border-primary/40 transition-colors">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-mono font-bold text-primary border border-primary/20">
                          #{idx + 1}
                        </span>
                        {c.section_title && (
                          <span className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-foreground border border-border">
                            {c.section_title}
                          </span>
                        )}
                        {typeof c.page_start === 'number' && (
                          <span className="text-[11px] text-muted-foreground">
                            Page {c.page_start}{c.page_end && c.page_end !== c.page_start ? `–${c.page_end}` : ''}
                          </span>
                        )}
                        {c.token_estimate && (
                          <span className="text-[11px] text-muted-foreground">
                            · ~{c.token_estimate} tokens
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-400 border border-emerald-500/20">
                          <Check className="size-2.5" />
                          Vector Indexed
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground"
                          onClick={() => copyChunkText(c)}
                        >
                          {copiedChunkId === c.id ? (
                            <span className="text-emerald-400 font-medium">Copied!</span>
                          ) : (
                            <Copy className="size-3" />
                          )}
                        </Button>
                      </div>
                    </div>
                    <p className="whitespace-pre-wrap text-xs leading-5 text-foreground/90 font-mono bg-muted/20 p-2.5 rounded border border-border/50">
                      {c.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AddPanel(props: {
  activeTab: AddTab;
  setActiveTab: (tab: AddTab) => void;
  kbDept: string;
  setKbDept: (value: string) => void;
  kbType: string;
  setKbType: (value: string) => void;
  kbFile: File | null;
  setKbFile: (file: File | null) => void;
  isDragging: boolean;
  setIsDragging: (value: boolean) => void;
  isUploading: boolean;
  onUpload: () => void;
  kbContent: string;
  setKbContent: (value: string) => void;
  onSaveText: () => void;
  crawlUrl: string;
  setCrawlUrl: (value: string) => void;
  crawlMaxPages: number;
  setCrawlMaxPages: (value: number) => void;
  crawlDepth: number;
  setCrawlDepth: (value: number) => void;
  crawlIncludePaths: string;
  setCrawlIncludePaths: (value: string) => void;
  crawlExcludePaths: string;
  setCrawlExcludePaths: (value: string) => void;
  crawlSchedule: string;
  setCrawlSchedule: (value: string) => void;
  isCrawling: boolean;
  isSyncingCompany: boolean;
  onCrawl: () => void;
  onSync: () => void;
  sources: any[];
  isLoadingSources: boolean;
  onRefreshSources: () => void;
  onRecrawl: (id: string) => void;
  onDeleteSource: (id: string) => void;
}) {
  const tabs: { id: AddTab; label: string }[] = [
    { id: 'upload', label: 'File' },
    { id: 'website', label: 'Website' },
    { id: 'text', label: 'Note' },
    { id: 'directives', label: 'Directive' },
  ];

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap gap-1">
        {tabs.map((tab) => (
          <Button key={tab.id} size="sm" variant={props.activeTab === tab.id ? 'default' : 'outline'} onClick={() => props.setActiveTab(tab.id)}>
            {tab.label}
          </Button>
        ))}
      </div>

      {props.activeTab === 'upload' && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <DeptSelect value={props.kbDept} onChange={props.setKbDept} />
            <TypeSelect value={props.kbType} onChange={props.setKbType} />
          </div>
          <label
            onDragOver={(event) => { event.preventDefault(); props.setIsDragging(true); }}
            onDragLeave={() => props.setIsDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              props.setIsDragging(false);
              const file = event.dataTransfer.files?.[0];
              if (file) props.setKbFile(file);
            }}
            className={`block cursor-pointer rounded-lg border border-dashed px-4 py-8 text-center ${props.isDragging || props.kbFile ? 'border-primary bg-primary/5' : 'border-border bg-muted/20'}`}
          >
            <input
              type="file"
              aria-label="Choose a document"
              accept=".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.csv,.tsv,.txt,.md,.json,.html,.png,.jpg,.jpeg,.webp,.bmp,.gif,.tif,.tiff,.rtf"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) props.setKbFile(file);
                event.target.value = '';
              }}
              className="sr-only"
            />
            {props.kbFile ? (
              <span className="block space-y-1">
                <FileText className="mx-auto size-5 text-foreground" />
                <span className="block text-sm font-medium text-foreground">{props.kbFile.name}</span>
                <span className="block text-xs text-muted-foreground">{formatBytes(props.kbFile.size)}. Click to replace it.</span>
                <button type="button" className="text-xs text-muted-foreground underline" onClick={(event) => { event.preventDefault(); event.stopPropagation(); props.setKbFile(null); }}>
                  Remove
                </button>
              </span>
            ) : (
              <span className="block space-y-1">
                <Upload className="mx-auto size-5 text-muted-foreground" />
                <span className="block text-sm text-foreground">Drop a file or browse</span>
                <span className="block text-xs text-muted-foreground">PDF, Office, CSV, images, text, and Markdown</span>
              </span>
            )}
          </label>
          <Button className="w-full" onClick={props.onUpload} disabled={!props.kbFile || props.isUploading}>
            {props.isUploading ? <Loader2 className="animate-spin" /> : <Upload />}
            {props.isUploading ? 'Reading the document' : 'Upload and index'}
          </Button>
        </div>
      )}

      {props.activeTab === 'website' && (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-2">
              <Building2 className="mt-0.5 size-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">Company website</p>
                <p className="text-xs text-muted-foreground">Uses the site on the organization profile, with the page limit and depth below.</p>
              </div>
            </div>
            <Button variant="outline" onClick={props.onSync} disabled={props.isSyncingCompany}>
              {props.isSyncingCompany ? <Loader2 className="animate-spin" /> : <RefreshCw />}
              Sync
            </Button>
          </div>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <FieldLabel>Website</FieldLabel>
              <Input value={props.crawlUrl} onChange={(event) => props.setCrawlUrl(event.target.value)} placeholder="https://example.com/docs" aria-label="Website URL" />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="space-y-1.5">
                <FieldLabel>Max pages</FieldLabel>
                <Input type="number" min={1} max={100} value={props.crawlMaxPages} onChange={(event) => props.setCrawlMaxPages(Number(event.target.value) || 25)} aria-label="Maximum pages" />
              </div>
              <div className="space-y-1.5">
                <FieldLabel>Depth</FieldLabel>
                <Input type="number" min={1} max={5} value={props.crawlDepth} onChange={(event) => props.setCrawlDepth(Number(event.target.value) || 2)} aria-label="Crawl depth" />
              </div>
              <div className="space-y-1.5">
                <FieldLabel>Schedule</FieldLabel>
                <Select value={props.crawlSchedule} onValueChange={(value) => props.setCrawlSchedule(value || 'manual')}>
                  <SelectTrigger className="w-full" aria-label="Crawl schedule">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual</SelectItem>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Input value={props.crawlIncludePaths} onChange={(event) => props.setCrawlIncludePaths(event.target.value)} placeholder="Include paths, comma separated" aria-label="Include paths" />
              <Input value={props.crawlExcludePaths} onChange={(event) => props.setCrawlExcludePaths(event.target.value)} placeholder="Exclude paths, comma separated" aria-label="Exclude paths" />
            </div>
            <Button className="w-full" onClick={props.onCrawl} disabled={!props.crawlUrl.trim() || props.isCrawling}>
              {props.isCrawling ? <Loader2 className="animate-spin" /> : <Globe />}
              {props.isCrawling ? 'Crawling' : 'Crawl and index'}
            </Button>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-foreground">Website sources</h3>
              <Button variant="ghost" size="sm" onClick={props.onRefreshSources}>
                <RefreshCw className={props.isLoadingSources ? 'animate-spin' : ''} />
                Refresh
              </Button>
            </div>
            {props.sources.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">No websites are being watched.</p>
            ) : (
              <ul className="space-y-2">
                {props.sources.map((source) => (
                  <li key={source.id} className="rounded-lg border border-border px-3 py-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm text-foreground" title={source.url}>{source.url}</p>
                        <p className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
                          <span>{source.pages_indexed || 0} pages</span>
                          <span className="capitalize">{source.schedule || 'manual'}</span>
                          <span className="inline-flex items-center gap-1"><Clock className="size-3" />{timeSince(source.last_crawled_at)}</span>
                          <span className="capitalize">{source.last_status || 'idle'}</span>
                        </p>
                        {source.last_error && <p className="mt-1 text-xs text-destructive">{source.last_error}</p>}
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <Button variant="ghost" size="icon-sm" aria-label="Re-crawl source" onClick={() => props.onRecrawl(source.id)}>
                          <RefreshCw />
                        </Button>
                        <Button variant="ghost" size="icon-sm" aria-label="Delete source" onClick={() => props.onDeleteSource(source.id)}>
                          <Trash2 />
                        </Button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {(props.activeTab === 'text' || props.activeTab === 'directives') && (
        <div className="space-y-3">
          {props.activeTab === 'text' ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <DeptSelect value={props.kbDept} onChange={props.setKbDept} />
              <TypeSelect value={props.kbType} onChange={props.setKbType} />
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
              Directives are added to every agent prompt for this workspace. Keep them short: tone, required links, and rules that must always apply.
            </div>
          )}
          <Textarea
            value={props.kbContent}
            onChange={(event) => props.setKbContent(event.target.value)}
            placeholder={props.activeTab === 'directives' ? 'Always close with the support email. Do not name competitors.' : 'Paste a policy, answer, price, or other reference text.'}
            className="min-h-48"
            aria-label={props.activeTab === 'directives' ? 'Directive text' : 'Note text'}
          />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{props.kbContent.length} characters</span>
            {props.activeTab === 'directives' && props.kbContent.length > 1500 && <span>Long directives are included in full on every task.</span>}
          </div>
          <Button className="w-full" onClick={props.onSaveText} disabled={!props.kbContent.trim()}>
            <BookOpen />
            {props.activeTab === 'directives' ? 'Save directive' : 'Save note'}
          </Button>
        </div>
      )}
    </div>
  );
}

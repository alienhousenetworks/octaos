'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowUpRight, Bot, CalendarDays, ChevronRight, CircleAlert,
  FileText, Image as ImageIcon, LoaderCircle, Plus, RefreshCw, Search,
  ShieldCheck, Sparkles, Users, Video, Workflow, BarChart3
} from 'lucide-react';

type Props = {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
};

type Post = {
  id: string;
  content?: string;
  platform?: string;
  approval_status?: string;
  status?: string;
  image_url?: string | null;
  video_url?: string | null;
  scheduled_at?: string | null;
  day?: number | null;
};

type Artifact = { id: string; title: string; artifact_type: string; status: string; current_version: number; campaign_id?: string | null };

type Persona = {
  name: string; persona: string; audience: string; voice: string;
  visual_prompt: string; intro_caption: string; content_pillars: string[];
  disclosure: string; approval_required: boolean; status: string;
};

const NAV = [
  { id: 'overview', label: 'Overview', icon: Workflow },
  { id: 'content', label: 'Content studio', icon: ImageIcon },
  { id: 'influencers', label: 'AI influencer studio', icon: Users },
  { id: 'artifacts', label: 'Artifacts', icon: FileText },
  { id: 'calendar', label: 'Calendar', icon: CalendarDays },
  { id: 'performance', label: 'Performance', icon: BarChart3 },
] as const;
type Tab = typeof NAV[number]['id'];

function statusLabel(post: Post) {
  const status = String(post.approval_status || post.status || 'draft').toLowerCase();
  if (status === 'published') return 'Published';
  if (status === 'scheduled' || status === 'approved') return 'Approved';
  if (status === 'pending') return 'Needs review';
  if (status === 'failed') return 'Failed';
  return 'Draft';
}

function Metric({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return <div className="min-w-0 rounded-xl border border-border bg-card p-4">
    <p className="text-sm text-muted-foreground">{label}</p>
    <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
    <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
  </div>;
}

export default function CampaignStudioView({ token, API_URL, fetchWithAuth }: Props) {
  const [tab, setTab] = useState<Tab>('overview');
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [topic, setTopic] = useState('');
  const [days, setDays] = useState('14');
  const [platforms, setPlatforms] = useState(['linkedin', 'instagram']);
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState('');
  const [performance, setPerformance] = useState<any>(null);
  const [personaInput, setPersonaInput] = useState({ company_name: '', industry: '', brand_tone: 'Confident, useful and human', audience: '', platform: 'instagram', creative_direction: '' });
  const [persona, setPersona] = useState<Persona | null>(null);
  const [personaLoading, setPersonaLoading] = useState(false);
  const [buffer, setBuffer] = useState<any>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [artifactLoading, setArtifactLoading] = useState(false);

  const loadPosts = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true); setError('');
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/?limit=100`);
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Could not load campaign posts.');
      const data = await res.json();
      setPosts(Array.isArray(data) ? data : []);
    } catch (e: any) { setError(e?.message || 'Could not load campaign posts.'); }
    finally { setLoading(false); }
  }, [API_URL, fetchWithAuth, token]);

  useEffect(() => { void loadPosts(); }, [loadPosts]);
  useEffect(() => {
    if (!token || tab !== 'performance') return;
    let cancelled = false;
    fetchWithAuth(`${API_URL}/marketing/analytics/dashboard`).then(async r => {
      if (!r.ok) throw new Error('Analytics are unavailable for this workspace.');
      return r.json();
    }).then(data => { if (!cancelled) setPerformance(data); })
      .catch(e => { if (!cancelled) setError(e?.message || 'Analytics are unavailable.'); });
    return () => { cancelled = true; };
  }, [API_URL, fetchWithAuth, tab, token]);
  const loadArtifacts = useCallback(async () => {
    if (!token) return;
    setArtifactLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/artifacts`);
      if (!res.ok) throw new Error('Could not load saved artifacts.');
      const data = await res.json();
      setArtifacts(Array.isArray(data.items) ? data.items : []);
    } catch (e: any) { setError(e?.message || 'Could not load saved artifacts.'); }
    finally { setArtifactLoading(false); }
  }, [API_URL, fetchWithAuth, token]);

  useEffect(() => { if (tab === 'artifacts') void loadArtifacts(); }, [tab, loadArtifacts]);

  useEffect(() => {
    if (!token) return;
    fetchWithAuth(`${API_URL}/marketing/connectors/buffer/status`).then(async r => r.ok ? r.json() : null)
      .then(data => { if (data) setBuffer(data); }).catch(() => {});
  }, [API_URL, fetchWithAuth, token]);

  const counts = useMemo(() => ({
    total: posts.length,
    review: posts.filter(p => String(p.approval_status).toLowerCase() === 'pending').length,
    approved: posts.filter(p => ['approved', 'scheduled'].includes(String(p.approval_status).toLowerCase())).length,
    published: posts.filter(p => String(p.approval_status).toLowerCase() === 'published').length,
  }), [posts]);
  const filtered = useMemo(() => posts.filter(p => `${p.content || ''} ${p.platform || ''} ${p.approval_status || ''}`.toLowerCase().includes(query.toLowerCase())), [posts, query]);

  async function createCampaign() {
    if (!topic.trim()) { setNotice('Add a campaign goal before generating.'); return; }
    setCreating(true); setNotice('');
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/campaign`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic.trim(), days: Number(days), platforms, generate_images: true })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Campaign could not be queued.');
      setNotice(`Campaign job queued: ${data.job_id || 'job ID unavailable'}. Follow its live status in Campaigns.`);
      setTopic('');
    } catch (e: any) { setNotice(e?.message || 'Campaign could not be queued.'); }
    finally { setCreating(false); }
  }

  async function createPersona() {
    if (!personaInput.company_name.trim() || !personaInput.industry.trim()) {
      setNotice('Enter a brand name and industry to create an influencer brief.'); return;
    }
    setPersonaLoading(true); setNotice('');
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/virtual-influencer/brief`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(personaInput)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Virtual influencer generation is unavailable.');
      setPersona(data);
      setNotice('Persona brief generated. It remains a draft and requires human review.');
    } catch (e: any) { setNotice(e?.message || 'Virtual influencer generation is unavailable.'); }
    finally { setPersonaLoading(false); }
  }

  async function savePersonaArtifact() {
    if (!persona) return;
    setNotice('');
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/artifacts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `${persona.name} — Virtual Influencer Brief`,
          artifact_type: 'virtual_influencer_brief',
          content: persona,
          sources: [{ type: 'user_input', label: 'Brief inputs supplied in Campaign Studio' }]
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Could not save artifact.');
      setNotice(`Saved artifact as version ${data.current_version || 1}; it is still a draft.`);
      setTab('artifacts');
      void loadArtifacts();
    } catch (e: any) { setNotice(e?.message || 'Could not save artifact.'); }
  }

  async function exportArtifact(artifact: Artifact) {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/artifacts/${artifact.id}/versions/${artifact.current_version}/export`);
      if (!res.ok) throw new Error('Artifact export failed.');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${artifact.title.replace(/[^a-z0-9_.-]+/gi, '-')}-v${artifact.current_version}.json`;
      a.click(); URL.revokeObjectURL(url);
    } catch (e: any) { setNotice(e?.message || 'Artifact export failed.'); }
  }

  async function connectBuffer() {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/connectors/buffer/connect`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.url) throw new Error(data.detail || 'Buffer connection is not configured.');
      window.location.assign(data.url);
    } catch (e: any) { setNotice(e?.message || 'Could not start Buffer connection.'); }
  }

  function downloadBrief() {
    if (!persona) return;
    const body = [
      `# ${persona.name}`, '', persona.persona, '', `Audience: ${persona.audience}`,
      `Voice: ${persona.voice}`, '', '## Content pillars', ...persona.content_pillars.map(x => `- ${x}`),
      '', '## Visual direction', persona.visual_prompt, '', '## Intro caption', persona.intro_caption,
      '', `Disclosure: ${persona.disclosure}`, '', 'Status: Draft — approval required'
    ].join('\n');
    const blob = new Blob([body], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `virtual-influencer-${persona.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.md`; a.click();
    URL.revokeObjectURL(url);
  }

  return <main className="mx-auto w-full max-w-[1600px] space-y-6 px-4 py-6 md:px-8">
    <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
      <div>
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[.16em] text-muted-foreground"><Sparkles className="size-4" /> OctaOS · Marketing</div>
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Autonomous Campaign Studio</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Plan campaigns, create content, develop virtual influencers and manage delivery from one workspace. Actions reflect connected services and actual backend state.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={() => window.location.assign('/app/campaigns')} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-muted"><Workflow className="size-4" /> Campaign planner</button>
        <button onClick={connectBuffer} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">Connect Buffer <ArrowUpRight className="size-4" /></button>
      </div>
    </header>

    <nav className="flex gap-1 overflow-x-auto border-b border-border pb-px" aria-label="Campaign Studio sections">
      {NAV.map(item => { const Icon = item.icon; return <button key={item.id} onClick={() => { setTab(item.id); setNotice(''); }} className={`inline-flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm ${tab === item.id ? 'border-primary font-semibold text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`} aria-current={tab === item.id ? 'page' : undefined}><Icon className="size-4" />{item.label}</button>; })}
    </nav>

    {notice && <div role="status" className="flex items-start gap-2 rounded-lg border border-border bg-card px-4 py-3 text-sm"><CircleAlert className="mt-0.5 size-4 shrink-0 text-primary" /><span>{notice}</span></div>}
    {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-border bg-card px-4 py-3 text-sm"><CircleAlert className="mt-0.5 size-4 shrink-0" /><span>{error}</span><button className="ml-auto underline" onClick={() => { setError(''); void loadPosts(); }}>Retry</button></div>}

    {tab === 'overview' && <>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Content items" value={loading ? '—' : counts.total} hint="Loaded from the campaign API" />
        <Metric label="Awaiting review" value={loading ? '—' : counts.review} hint="Posts marked pending review" />
        <Metric label="Approved / scheduled" value={loading ? '—' : counts.approved} hint="Stored post approval states" />
        <Metric label="Published" value={loading ? '—' : counts.published} hint="Posts marked published" />
      </section>
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,1fr)]">
        <div className="rounded-xl border border-border bg-card p-5 md:p-6">
          <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Start a campaign</p><h2 className="mt-2 text-xl font-semibold">What outcome do you want?</h2><p className="mt-1 text-sm text-muted-foreground">The existing campaign worker handles generation; final publish actions remain subject to approval and configured integrations.</p></div><Sparkles className="size-5 text-primary" /></div>
          <label className="mt-5 block text-sm font-medium" htmlFor="campaign-goal">Campaign goal</label>
          <textarea id="campaign-goal" value={topic} onChange={e => setTopic(e.target.value)} placeholder="e.g. Launch our new analytics product to operations leaders and drive demo requests…" rows={3} className="mt-2 w-full resize-y rounded-lg border border-border bg-background px-3 py-3 text-sm outline-none focus:border-primary" />
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">Duration<select value={days} onChange={e => setDays(e.target.value)} className="mt-2 block w-full rounded-lg border border-border bg-background px-3 py-2.5"><option value="7">7 days</option><option value="14">14 days</option><option value="30">30 days</option><option value="60">60 days</option></select></label>
            <div><p className="text-sm font-medium">Channels</p><div className="mt-2 flex flex-wrap gap-2">{['linkedin','instagram','facebook','twitter'].map(p => <button type="button" key={p} onClick={() => setPlatforms(old => old.includes(p) ? old.filter(x => x !== p) : [...old,p])} className={`rounded-md border px-3 py-2 text-xs capitalize ${platforms.includes(p) ? 'border-primary bg-primary/10 text-foreground' : 'border-border text-muted-foreground'}`} aria-pressed={platforms.includes(p)}>{p === 'twitter' ? 'X' : p}</button>)}</div></div>
          </div>
          <button onClick={createCampaign} disabled={creating || !topic.trim() || platforms.length === 0} className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-50">{creating ? <LoaderCircle className="size-4 animate-spin" /> : <Plus className="size-4" />} Queue campaign</button>
        </div>
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center justify-between"><h2 className="font-semibold">Publishing connection</h2><span className={`rounded-full border px-2 py-1 text-xs ${buffer?.connected ? 'border-primary/50 text-foreground' : 'border-border text-muted-foreground'}`}>{buffer?.connected ? 'Connected' : 'Not verified'}</span></div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{buffer?.connected ? 'Buffer credentials are present for this workspace. Channel and publishing capability still depend on account access.' : 'Connect Buffer to discover supported channels and use its available scheduling and publishing capabilities.'}</p>
            <button onClick={connectBuffer} className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-primary">Manage connection <ChevronRight className="size-4" /></button>
          </div>
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center gap-2"><ShieldCheck className="size-4 text-primary" /><h2 className="font-semibold">Trust and approvals</h2></div>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground"><li>• Human review for virtual influencer content</li><li>• Publishing depends on explicit approval and provider readiness</li><li>• Unavailable analytics are not presented as zero</li></ul>
          </div>
        </div>
      </section>
      <section className="rounded-xl border border-border bg-card">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4"><div><h2 className="font-semibold">Recent campaign content</h2><p className="mt-1 text-xs text-muted-foreground">Tenant-scoped records returned by the marketing API</p></div><button onClick={() => void loadPosts()} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm"><RefreshCw className="size-4" /> Refresh</button></div>
        <div className="divide-y divide-border">{loading ? <p className="p-5 text-sm text-muted-foreground">Loading campaign content…</p> : filtered.slice(0,5).map(post => <div key={post.id} className="flex items-start gap-3 p-4"><div className="grid size-10 shrink-0 place-items-center rounded-lg border border-border bg-background">{post.video_url ? <Video className="size-4" /> : post.image_url ? <ImageIcon className="size-4" /> : <FileText className="size-4" />}</div><div className="min-w-0 flex-1"><p className="line-clamp-2 text-sm font-medium">{post.content || 'Untitled content'}</p><p className="mt-1 text-xs capitalize text-muted-foreground">{post.platform || 'Unknown channel'} · {statusLabel(post)}{post.scheduled_at ? ` · ${new Date(post.scheduled_at).toLocaleString()}` : ''}</p></div><span className="shrink-0 rounded-full border border-border px-2 py-1 text-xs text-muted-foreground">{statusLabel(post)}</span></div>) : <p className="p-5 text-sm text-muted-foreground">No campaign content found for this workspace yet.</p>}</div>
      </section>
    </>}

    {tab === 'content' && <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><h2 className="text-xl font-semibold">Content library</h2><p className="mt-1 text-sm text-muted-foreground">Search generated and manually created content from the existing marketing API.</p></div><div className="relative w-full sm:max-w-xs"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search content or channel" className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-sm" /></div></div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map(post => <article key={post.id} className="overflow-hidden rounded-xl border border-border bg-card">{post.image_url && !String(post.image_url).startsWith('error:') ? <img src={post.image_url} alt="Campaign creative" className="aspect-[16/9] w-full bg-background object-cover" /> : <div className="grid aspect-[16/9] place-items-center bg-background"><ImageIcon className="size-8 text-muted-foreground" /></div>}<div className="space-y-3 p-4"><div className="flex items-center justify-between gap-2"><span className="text-xs capitalize text-muted-foreground">{post.platform || 'Unknown channel'}</span><span className="rounded-full border border-border px-2 py-1 text-xs">{statusLabel(post)}</span></div><p className="line-clamp-4 whitespace-pre-wrap text-sm">{post.content || 'No caption available.'}</p>{post.video_url && <a className="text-sm text-primary underline" href={post.video_url} target="_blank" rel="noreferrer">Open video asset</a>}</div></article>)}</div>
      {!loading && filtered.length === 0 && <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">No matching content.</div>}
    </section>}

    {tab === 'influencers' && <section className="grid gap-5 xl:grid-cols-[minmax(320px,.85fr)_minmax(0,1.15fr)]">
      <div className="rounded-xl border border-border bg-card p-5 md:p-6"><div className="flex items-center gap-2"><Users className="size-5 text-primary" /><h2 className="text-xl font-semibold">Create a virtual influencer</h2></div><p className="mt-2 text-sm leading-6 text-muted-foreground">Design an original fictional adult persona for your brand. Generated personas must be disclosed as AI and reviewed before use.</p>
      <div className="mt-5 space-y-4">{([{key:'company_name',label:'Brand name',placeholder:'Your company'} ,{key:'industry',label:'Industry',placeholder:'e.g. B2B SaaS, fitness, travel'},{key:'audience',label:'Target audience',placeholder:'Who should this persona speak to?'},{key:'creative_direction',label:'Creative direction',placeholder:'Visual style, interests and differentiators'}] as const).map(f => <label key={f.key} className="block text-sm font-medium">{f.label}<input value={personaInput[f.key]} onChange={e => setPersonaInput(p => ({...p,[f.key]:e.target.value}))} placeholder={f.placeholder} className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm font-normal" /></label>)}
      <label className="block text-sm font-medium">Brand voice<input value={personaInput.brand_tone} onChange={e => setPersonaInput(p => ({...p,brand_tone:e.target.value}))} className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm font-normal" /></label>
      <label className="block text-sm font-medium">Primary platform<select value={personaInput.platform} onChange={e => setPersonaInput(p => ({...p,platform:e.target.value}))} className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm font-normal"><option value="instagram">Instagram</option><option value="linkedin">LinkedIn</option><option value="facebook">Facebook</option><option value="twitter">X</option></select></label>
      <button onClick={createPersona} disabled={personaLoading} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-50">{personaLoading ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />} Generate persona brief</button></div></div>
      <div className="rounded-xl border border-border bg-card p-5 md:p-6">{persona ? <div className="space-y-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs uppercase tracking-wider text-muted-foreground">Draft persona · Review required</p><h2 className="mt-2 text-2xl font-semibold">{persona.name}</h2></div><button onClick={downloadBrief} className="rounded-lg border border-border px-3 py-2 text-sm">Export brief</button><button onClick={savePersonaArtifact} className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">Save as artifact</button></div><p className="text-sm leading-6">{persona.persona}</p><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Audience</p><p className="mt-1 text-sm">{persona.audience}</p></div><div className="rounded-lg border border-border p-3"><p className="text-xs text-muted-foreground">Voice</p><p className="mt-1 text-sm">{persona.voice}</p></div></div><div><h3 className="font-semibold">Content pillars</h3><div className="mt-2 flex flex-wrap gap-2">{persona.content_pillars?.map(p => <span key={p} className="rounded-full border border-border px-3 py-1.5 text-xs">{p}</span>)}</div></div><div><h3 className="font-semibold">Visual direction</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{persona.visual_prompt}</p></div><div className="rounded-lg border border-border bg-background p-4"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Intro caption</p><p className="mt-2 whitespace-pre-wrap text-sm">{persona.intro_caption}</p><p className="mt-3 text-xs text-muted-foreground">{persona.disclosure}</p></div></div> : <div className="flex min-h-[420px] flex-col items-center justify-center text-center"><div className="grid size-14 place-items-center rounded-2xl border border-border"><Bot className="size-6" /></div><h2 className="mt-4 text-lg font-semibold">Your persona brief appears here</h2><p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">Start with a brand and industry. OctaOS will return a fictional persona, audience, voice, visual prompt, content pillars and disclosure.</p></div>}</div>
    </section>}

    {tab === 'artifacts' && <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-semibold">Campaign artifacts</h2><p className="mt-1 text-sm text-muted-foreground">Tenant-owned deliverables with immutable versions, content hashes and explicit review state.</p></div><button onClick={() => void loadArtifacts()} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm"><RefreshCw className="size-4" /> Refresh</button></div>
      <div className="grid gap-3 md:grid-cols-2"><button onClick={() => setTab('influencers')} className="rounded-xl border border-border bg-card p-5 text-left hover:bg-muted"><FileText className="size-5 text-primary" /><h3 className="mt-3 font-semibold">Create virtual influencer brief</h3><p className="mt-1 text-sm text-muted-foreground">Generate a disclosed fictional persona, then save its brief as a versioned artifact.</p><span className="mt-4 inline-flex items-center gap-1 text-sm text-primary">Open Influencer Studio <ChevronRight className="size-4" /></span></button><button onClick={() => window.location.assign('/app/campaigns')} className="rounded-xl border border-border bg-card p-5 text-left hover:bg-muted"><Workflow className="size-5 text-primary" /><h3 className="mt-3 font-semibold">Campaign plan and schedule</h3><p className="mt-1 text-sm text-muted-foreground">Open the existing campaign planner and persisted generation workflow.</p><span className="mt-4 inline-flex items-center gap-1 text-sm text-primary">Open campaign planner <ChevronRight className="size-4" /></span></button></div>
      <div className="overflow-hidden rounded-xl border border-border bg-card"><div className="border-b border-border p-4"><h3 className="font-semibold">Saved artifacts</h3><p className="mt-1 text-xs text-muted-foreground">Export currently downloads the selected immutable version as JSON; PDF/DOCX/PPTX renderers are not claimed here.</p></div>
        {artifactLoading ? <p className="p-5 text-sm text-muted-foreground">Loading saved artifacts…</p> : artifacts.length ? <div className="divide-y divide-border">{artifacts.map(a => <div key={a.id} className="flex flex-wrap items-center gap-3 p-4"><div className="grid size-10 place-items-center rounded-lg border border-border"><FileText className="size-4" /></div><div className="min-w-0 flex-1"><p className="font-medium">{a.title}</p><p className="mt-1 text-xs text-muted-foreground">{a.artifact_type.replaceAll('_',' ')} · Version {a.current_version} · {a.status}</p></div><button onClick={() => void exportArtifact(a)} className="rounded-lg border border-border px-3 py-2 text-sm">Export JSON</button></div>)}</div> : <p className="p-8 text-center text-sm text-muted-foreground">No saved artifacts yet. Generate an influencer brief and choose “Save as artifact”.</p>}
      </div>
    </section>}

    {tab === 'calendar' && <section className="space-y-4"><div><h2 className="text-xl font-semibold">Publishing calendar</h2><p className="mt-1 text-sm text-muted-foreground">A read-only view of scheduled dates stored on campaign posts. Scheduling changes remain in the established campaign planner.</p></div><div className="rounded-xl border border-border bg-card"><div className="divide-y divide-border">{posts.filter(p => p.scheduled_at).sort((a,b) => String(a.scheduled_at).localeCompare(String(b.scheduled_at))).map(post => <div key={post.id} className="flex flex-wrap items-center gap-4 p-4"><div className="min-w-36"><p className="text-sm font-medium">{new Date(post.scheduled_at!).toLocaleDateString()}</p><p className="text-xs text-muted-foreground">{new Date(post.scheduled_at!).toLocaleTimeString()}</p></div><div className="min-w-0 flex-1"><p className="line-clamp-2 text-sm">{post.content || 'Untitled content'}</p><p className="mt-1 text-xs capitalize text-muted-foreground">{post.platform}</p></div><span className="rounded-full border border-border px-2 py-1 text-xs">{statusLabel(post)}</span></div>)}</div>{posts.every(p => !p.scheduled_at) && <p className="p-8 text-center text-sm text-muted-foreground">No scheduled posts are returned by the API.</p>}</div></section>}

    {tab === 'performance' && <section className="space-y-4"><div><h2 className="text-xl font-semibold">Performance and learning</h2><p className="mt-1 text-sm text-muted-foreground">Metrics come from the existing analytics endpoint. Missing measurements remain unavailable instead of being shown as zero.</p></div>{performance ? <pre className="overflow-auto rounded-xl border border-border bg-card p-5 text-xs leading-6">{JSON.stringify(performance, null, 2)}</pre> : <div className="rounded-xl border border-border bg-card p-8 text-center"><BarChart3 className="mx-auto size-7 text-muted-foreground" /><p className="mt-3 text-sm text-muted-foreground">No verified analytics payload loaded yet. Open this section to fetch connected-platform measurements.</p></div>}</section>}

    <footer className="flex flex-col gap-2 border-t border-border pt-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between"><span>OctaOS Campaign Studio · Tenant-scoped API data</span><span>Draft content is not the same as approved or published content.</span></footer>
  </main>;
}

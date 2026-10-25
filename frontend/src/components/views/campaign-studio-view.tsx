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

type SavedPersona = { id: string; name: string; status: string; brief: Persona };

type Artifact = { id: string; title: string; artifact_type: string; status: string; current_version: number; current_version_hash?: string; current_version_review_status?: string; campaign_id?: string | null };

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
  const [savedPersonas, setSavedPersonas] = useState<SavedPersona[]>([]);
  const [buffer, setBuffer] = useState<any>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [artifactLoading, setArtifactLoading] = useState(false);
  const [artifactDetail, setArtifactDetail] = useState<any>(null);
  const [artifactEditorText, setArtifactEditorText] = useState('');
  const [artifactVersionSaving, setArtifactVersionSaving] = useState(false);
  const [creativeBrief, setCreativeBrief] = useState({ company_name: '', industry: '', campaign_goal: '', audience: '', platform: 'instagram', format: 'reel', duration_seconds: 30, product_context: '' });
  const [scriptInput, setScriptInput] = useState('');
  const [creativePlan, setCreativePlan] = useState<any>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [referenceImageUrl, setReferenceImageUrl] = useState('');
  const [referenceUploading, setReferenceUploading] = useState(false);
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [creativeKind, setCreativeKind] = useState<'image' | 'video'>('image');
  const [creativePrompt, setCreativePrompt] = useState('');
  const [creativeGenerating, setCreativeGenerating] = useState(false);
  const [creativeResult, setCreativeResult] = useState<any>(null);
  const [selectedProfileId, setSelectedProfileId] = useState('');

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
  const loadPersonas = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/virtual-influencer/profiles`);
      if (!res.ok) return;
      const data = await res.json();
      setSavedPersonas(Array.isArray(data.items) ? data.items : []);
    } catch { /* existing brief remains usable when profile listing is unavailable */ }
  }, [API_URL, fetchWithAuth, token]);

  useEffect(() => { if (tab === 'influencers') void loadPersonas(); }, [tab, loadPersonas]);

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
      void loadPersonas();
      setNotice('Persona brief saved. It remains a draft and requires human review.');
    } catch (e: any) { setNotice(e?.message || 'Virtual influencer generation is unavailable.'); }
    finally { setPersonaLoading(false); }
  }

  async function reviewPersona(profile: SavedPersona, decision: 'approve' | 'changes_requested' | 'reject') {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/virtual-influencer/profiles/${profile.id}/review`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, comment: '' })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Persona review failed.');
      setNotice(`Virtual influencer review state: ${data.status}.`);
      void loadPersonas();
    } catch (e: any) { setNotice(e?.message || 'Persona review failed.'); }
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

  async function openArtifactEditor(artifact: Artifact) {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/artifacts/${artifact.id}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Could not open artifact.');
      setArtifactDetail(data);
      const current = Array.isArray(data.versions) ? data.versions.find((v: any) => v.version === data.current_version) : null;
      setArtifactEditorText(JSON.stringify(current?.content || {}, null, 2));
    } catch (e: any) { setNotice(e?.message || 'Could not open artifact.'); }
  }

  async function saveArtifactVersion() {
    if (!artifactDetail) return;
    let parsed: any;
    try { parsed = JSON.parse(artifactEditorText); }
    catch { setNotice('Artifact content must be valid JSON before saving.'); return; }
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      setNotice('Artifact content must be a JSON object.'); return;
    }
    setArtifactVersionSaving(true);
    try {
      const current = Array.isArray(artifactDetail.versions) ? artifactDetail.versions.find((v: any) => v.version === artifactDetail.current_version) : null;
      const res = await fetchWithAuth(`${API_URL}/marketing/artifacts/${artifactDetail.id}/versions`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: parsed, sources: current?.sources || [], expected_version: artifactDetail.current_version })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Could not save a new artifact version.');
      setNotice(`Saved immutable version ${data.current_version}; the new version requires review.`);
      setArtifactDetail(null);
      setArtifactEditorText('');
      void loadArtifacts();
    } catch (e: any) { setNotice(e?.message || 'Could not save artifact version.'); }
    finally { setArtifactVersionSaving(false); }
  }

  async function reviewArtifact(artifact: Artifact, decision: 'approve' | 'changes_requested') {
    if (!artifact.current_version_hash) { setNotice('Current version hash is unavailable. Refresh the library before reviewing.'); return; }
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/artifacts/${artifact.id}/review`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: artifact.current_version, content_hash: artifact.current_version_hash, decision })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Artifact review failed.');
      setNotice(`Version ${artifact.current_version} review state: ${data.version?.review_status || decision}.`);
      void loadArtifacts();
    } catch (e: any) { setNotice(e?.message || 'Artifact review failed.'); }
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

  async function createCreativePlan() {
    if (!creativeBrief.company_name.trim() || !creativeBrief.industry.trim() || !creativeBrief.campaign_goal.trim()) {
      setNotice('Enter the brand, industry and campaign goal first.'); return;
    }
    setPlanLoading(true); setNotice('');
    try {
      const body = { ...creativeBrief, script_input: scriptInput, ...(selectedProfileId ? { profile_id: selectedProfileId } : {}) };
      const res = await fetchWithAuth(`${API_URL}/marketing/virtual-influencer/creative-plan`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Creative plan generation failed.');
      setCreativePlan(data);
      const scenes = Array.isArray(data.storyboard) ? data.storyboard.map((s: any) => `Scene ${s.scene}: ${s.asset_prompt || s.shot || ''}`).join('\n') : '';
      setCreativePrompt([data.concept, data.hook, scenes, data.disclosure].filter(Boolean).join('\n\n'));
      setNotice('Script and storyboard generated. Review and edit them before production.');
    } catch (e: any) { setNotice(e?.message || 'Creative plan generation failed.'); }
    finally { setPlanLoading(false); }
  }

  async function uploadReferenceImage(file?: File) {
    if (!file) return;
    if (!rightsConfirmed) { setNotice('Confirm you have permission to use this character image before uploading.'); return; }
    const data = new FormData(); data.append('file', file);
    setReferenceUploading(true); setNotice('');
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/virtual-influencer/reference-image`, { method: 'POST', body: data });
      const result = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(result.detail || 'Reference image upload failed.');
      setReferenceImageUrl(result.url || '');
      setNotice('Reference image uploaded. It will be used as a visual reference; consistency depends on the selected generation provider.');
    } catch (e: any) { setNotice(e?.message || 'Reference image upload failed.'); }
    finally { setReferenceUploading(false); }
  }

  async function generateInfluencerCreative() {
    if (!creativePrompt.trim()) { setNotice('Generate a plan or enter a visual prompt first.'); return; }
    if (referenceImageUrl && !rightsConfirmed) { setNotice('Confirm permission to use the uploaded character reference.'); return; }
    setCreativeGenerating(true); setNotice(''); setCreativeResult(null);
    try {
      const body = {
        prompt: creativePrompt, deliverable: creativeKind, platform: creativeBrief.platform,
        reference_assets: referenceImageUrl ? [referenceImageUrl] : [],
        ...(selectedProfileId ? { profile_id: selectedProfileId } : {}),
        campaign_goal: creativeBrief.campaign_goal, aspect_ratio: creativeBrief.format === 'reel' || creativeBrief.format === 'story' ? '9:16' : '4:5'
      };
      const res = await fetchWithAuth(`${API_URL}/marketing/virtual-influencer/generate-creative`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Creative generation failed.');
      setCreativeResult(data);
      setNotice('Creative result saved as a draft artifact. Review the asset and provider output before publishing.');
      void loadArtifacts();
    } catch (e: any) { setNotice(e?.message || 'Creative generation failed. Check configured provider readiness.'); }
    finally { setCreativeGenerating(false); }
  }

  async function saveCreativePlanArtifact() {
    if (!creativePlan) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/artifacts`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: `Influencer script & storyboard — ${creativeBrief.company_name || 'Campaign'}`,
          artifact_type: 'ai_influencer_script_storyboard',
          content: { ...creativePlan, editable_script: scriptInput, editable_visual_prompt: creativePrompt, brief: creativeBrief },
          sources: [{ type: 'user_input', label: 'Campaign brief and optional supplied script' }]
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Could not save script and storyboard.');
      setNotice(`Script and storyboard saved as draft artifact version ${data.current_version || 1}.`);
      void loadArtifacts();
    } catch (e: any) { setNotice(e?.message || 'Could not save script and storyboard.'); }
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
        <div className="divide-y divide-border">{loading ? <p className="p-5 text-sm text-muted-foreground">Loading campaign content…</p> : filtered.length > 0 ? filtered.slice(0,5).map(post => <div key={post.id} className="flex items-start gap-3 p-4"><div className="grid size-10 shrink-0 place-items-center rounded-lg border border-border bg-background">{post.video_url ? <Video className="size-4" /> : post.image_url ? <ImageIcon className="size-4" /> : <FileText className="size-4" />}</div><div className="min-w-0 flex-1"><p className="line-clamp-2 text-sm font-medium">{post.content || 'Untitled content'}</p><p className="mt-1 text-xs capitalize text-muted-foreground">{post.platform || 'Unknown channel'} · {statusLabel(post)}{post.scheduled_at ? ` · ${new Date(post.scheduled_at).toLocaleString()}` : ''}</p></div><span className="shrink-0 rounded-full border border-border px-2 py-1 text-xs text-muted-foreground">{statusLabel(post)}</span></div>) : <p className="p-5 text-sm text-muted-foreground">No campaign content found for this workspace yet.</p>}</div>
      </section>
    </>}

    {tab === 'content' && <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><h2 className="text-xl font-semibold">Content library</h2><p className="mt-1 text-sm text-muted-foreground">Search generated and manually created content from the existing marketing API.</p></div><div className="relative w-full sm:max-w-xs"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search content or channel" className="w-full rounded-lg border border-border bg-card py-2 pl-9 pr-3 text-sm" /></div></div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map(post => <article key={post.id} className="overflow-hidden rounded-xl border border-border bg-card">{post.image_url && !String(post.image_url).startsWith('error:') ? <img src={post.image_url} alt="Campaign creative" className="aspect-[16/9] w-full bg-background object-cover" /> : <div className="grid aspect-[16/9] place-items-center bg-background"><ImageIcon className="size-8 text-muted-foreground" /></div>}<div className="space-y-3 p-4"><div className="flex items-center justify-between gap-2"><span className="text-xs capitalize text-muted-foreground">{post.platform || 'Unknown channel'}</span><span className="rounded-full border border-border px-2 py-1 text-xs">{statusLabel(post)}</span></div><p className="line-clamp-4 whitespace-pre-wrap text-sm">{post.content || 'No caption available.'}</p>{post.video_url && <a className="text-sm text-primary underline" href={post.video_url} target="_blank" rel="noreferrer">Open video asset</a>}</div></article>)}</div>
      {!loading && filtered.length === 0 && <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">No matching content.</div>}
    </section>}

    {tab === 'influencers' && <section className="space-y-5">
      <div className="rounded-xl border border-border bg-card p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Influencer production workflow</p><h2 className="mt-2 text-xl font-semibold">From business brief to ready-to-review creative</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">Use a free concept starter, create a brand-grounded script and storyboard, upload a character reference you have rights to use, then generate image or video assets through the workspace's configured providers.</p></div><span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">Human review before publishing</span></div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            { name: 'Helpful expert', niche: 'B2B / SaaS', idea: 'A friendly fictional adult expert explains one customer problem and demonstrates the solution.' },
            { name: 'Everyday guide', niche: 'Consumer / lifestyle', idea: 'A relatable fictional adult character shows a real-world use case in a simple three-beat story.' },
            { name: 'Product explorer', niche: 'E-commerce', idea: 'A fictional adult host unboxes or explores the product; only verified product details are stated.' },
            { name: 'Industry educator', niche: 'Professional services', idea: 'A fictional adult educator explains a common misconception, with unsupported claims flagged for review.' },
          ].map(item => <button key={item.name} onClick={() => { setCreativeBrief(b => ({ ...b, creative_goal: undefined as never, campaign_goal: b.campaign_goal || item.idea, industry: b.industry || item.niche })); setPersonaInput(p => ({ ...p, creative_direction: item.idea })); setCreativePrompt(item.idea); setNotice(`${item.name} starter selected. Add your brand and product context before generating.`); }} className="rounded-lg border border-border p-4 text-left transition hover:bg-muted/40"><p className="font-medium">{item.name}</p><p className="mt-1 text-xs text-muted-foreground">{item.niche}</p><p className="mt-3 text-sm leading-5">{item.idea}</p><span className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary"><Sparkles className="size-3" /> Use starter concept</span></button>)}
        </div>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <div className="space-y-4 rounded-xl border border-border bg-card p-5">
          <div><h3 className="font-semibold">1. Understand the business</h3><p className="mt-1 text-sm text-muted-foreground">Recommendations use these inputs and the optional approved persona. Add evidence-backed product facts; unsupported claims are flagged.</p></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm font-medium">Brand name<input value={creativeBrief.company_name} onChange={e => setCreativeBrief(b => ({...b,company_name:e.target.value}))} placeholder="Company or product brand" className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label>
            <label className="text-sm font-medium">Industry<input value={creativeBrief.industry} onChange={e => setCreativeBrief(b => ({...b,industry:e.target.value}))} placeholder="e.g. skincare, B2B SaaS" className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label>
            <label className="text-sm font-medium sm:col-span-2">Campaign goal<textarea value={creativeBrief.campaign_goal} onChange={e => setCreativeBrief(b => ({...b,campaign_goal:e.target.value}))} rows={2} placeholder="What should the viewer understand, feel or do?" className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label>
            <label className="text-sm font-medium sm:col-span-2">Product facts / offer / proof<input value={creativeBrief.product_context} onChange={e => setCreativeBrief(b => ({...b,product_context:e.target.value}))} placeholder="Only verified details; leave blank if not known" className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label>
            <label className="text-sm font-medium">Target audience<input value={creativeBrief.audience} onChange={e => setCreativeBrief(b => ({...b,audience:e.target.value}))} placeholder="Who is this for?" className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label>
            <label className="text-sm font-medium">Platform<select value={creativeBrief.platform} onChange={e => setCreativeBrief(b => ({...b,platform:e.target.value}))} className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal"><option value="instagram">Instagram</option><option value="tiktok">TikTok</option><option value="youtube">YouTube Shorts</option><option value="linkedin">LinkedIn</option><option value="facebook">Facebook</option></select></label>
            <label className="text-sm font-medium">Format<select value={creativeBrief.format} onChange={e => setCreativeBrief(b => ({...b,format:e.target.value}))} className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal"><option value="reel">Reel</option><option value="short_video">Short video</option><option value="story">Story</option><option value="feed_post">Feed post</option><option value="carousel">Carousel</option><option value="linkedin_video">LinkedIn video</option></select></label>
            <label className="text-sm font-medium">Duration<select value={String(creativeBrief.duration_seconds)} onChange={e => setCreativeBrief(b => ({...b,duration_seconds:Number(e.target.value)}))} className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal"><option value="15">15 seconds</option><option value="30">30 seconds</option><option value="45">45 seconds</option><option value="60">60 seconds</option><option value="90">90 seconds</option></select></label>
          </div>
          <label className="block text-sm font-medium">Existing script (optional)<textarea value={scriptInput} onChange={e => setScriptInput(e.target.value)} rows={4} placeholder="Paste a script to adapt, or leave blank to generate a new one." className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label>
          <label className="block text-sm font-medium">Use an approved saved persona (optional)<select value={selectedProfileId} onChange={e => setSelectedProfileId(e.target.value)} className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal"><option value="">No saved persona — use text/image reference</option>{savedPersonas.filter(p => p.status === 'approved_for_content_review').map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select><span className="mt-1 block text-xs font-normal text-muted-foreground">Only approved profiles can be used for production generation.</span></label>
          <button onClick={() => void createCreativePlan()} disabled={planLoading} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-50">{planLoading ? <LoaderCircle className="size-4 animate-spin" /> : <Sparkles className="size-4" />}{planLoading ? 'Creating script & storyboard…' : 'Generate script & storyboard'}</button>
        </div>
        <div className="space-y-4 rounded-xl border border-border bg-card p-5">
          <div><h3 className="font-semibold">2. Character reference and creative production</h3><p className="mt-1 text-sm text-muted-foreground">Upload a JPG, PNG or WebP reference. Do not upload an image unless you have the rights and permission to use it.</p></div>
          <label className="flex items-start gap-2 rounded-lg border border-border p-3 text-sm"><input type="checkbox" checked={rightsConfirmed} onChange={e => setRightsConfirmed(e.target.checked)} className="mt-0.5" /><span>I confirm I have the rights and permission to use this character image for this campaign.</span></label>
          <label className="block text-sm font-medium">Character reference image<input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => void uploadReferenceImage(e.target.files?.[0])} disabled={referenceUploading} className="mt-2 block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-muted file:px-3 file:py-2" /></label>
          {referenceImageUrl && <div className="rounded-lg border border-border p-3"><img src={referenceImageUrl} alt="Uploaded character reference" className="max-h-48 rounded-md object-contain" /><p className="mt-2 break-all text-xs text-muted-foreground">Reference uploaded and ready to use.</p><button onClick={() => setReferenceImageUrl('')} className="mt-2 text-xs underline">Remove reference from this draft</button></div>}
          <label className="block text-sm font-medium">Creative prompt / storyboard direction<textarea value={creativePrompt} onChange={e => setCreativePrompt(e.target.value)} rows={6} placeholder="Generate a plan above or describe the image/video you need." className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label>
          <div className="flex flex-wrap items-center gap-3"><label className="text-sm font-medium">Output<select value={creativeKind} onChange={e => setCreativeKind(e.target.value as 'image'|'video')} className="ml-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal"><option value="image">Image</option><option value="video">Video / Reel</option></select></label><button onClick={() => void generateInfluencerCreative()} disabled={creativeGenerating} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground disabled:opacity-50">{creativeGenerating ? <LoaderCircle className="size-4 animate-spin" /> : <Video className="size-4" />}{creativeGenerating ? 'Generating…' : 'Generate creative'}</button></div>
          {creativePlan && <div className="space-y-3 rounded-lg border border-border p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h4 className="font-semibold">{creativePlan.concept || 'Script and storyboard'}</h4><button onClick={() => void saveCreativePlanArtifact()} className="rounded-md border border-border px-3 py-1.5 text-xs">Save plan to artifacts</button></div>{creativePlan.hook && <p className="text-sm"><span className="font-medium">Hook:</span> {creativePlan.hook}</p>}<label className="block text-sm font-medium">Editable script<textarea value={scriptInput || (Array.isArray(creativePlan.script) ? creativePlan.script.map((s:any) => `[${s.time || ''}] ${s.dialogue || ''}`).join('\n') : '')} onChange={e => setScriptInput(e.target.value)} rows={5} className="mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-normal" /></label><div><p className="text-sm font-medium">Storyboard</p><div className="mt-2 space-y-2">{(creativePlan.storyboard || []).map((s:any,i:number) => <div key={i} className="rounded-md bg-muted/30 p-3"><p className="text-xs text-muted-foreground">Scene {s.scene ?? i+1} · {s.start_seconds ?? '?'}–{s.end_seconds ?? '?'} sec</p><p className="mt-1 text-sm">{s.shot || s.action || s.asset_prompt || 'No scene description returned.'}</p>{s.dialogue && <p className="mt-1 text-sm text-muted-foreground">“{s.dialogue}”</p>}</div>)}</div></div>{Array.isArray(creativePlan.claims_to_verify) && creativePlan.claims_to_verify.length > 0 && <p className="rounded-md border border-border p-3 text-sm">Claims requiring verification: {creativePlan.claims_to_verify.join('; ')}</p>}<p className="text-xs text-muted-foreground">{creativePlan.disclosure || 'AI/synthetic influencer disclosure required.'}</p></div>}
          {creativeResult && <div className="rounded-lg border border-border p-4"><div className="flex items-center justify-between gap-3"><h4 className="font-semibold">Generation result · {creativeResult.status}</h4><span className="text-xs text-muted-foreground">Saved to artifacts as draft</span></div>{creativeResult.asset_url ? (creativeKind === 'video' ? <video controls src={creativeResult.asset_url} className="mt-3 max-h-80 w-full rounded-lg bg-black" /> : <img src={creativeResult.asset_url} alt="Generated influencer creative" className="mt-3 max-h-80 rounded-lg object-contain" />) : <p className="mt-2 text-sm text-muted-foreground">Provider returned no primary asset URL. Inspect generation details before retrying.</p>}{creativeResult.asset_url && <a href={creativeResult.asset_url} target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm underline">Open generated asset</a>}</div>}
        </div>
      </div>
    </section>}

    {tab === 'influencers' && savedPersonas.length > 0 && <section className="rounded-xl border border-border bg-card"><div className="border-b border-border p-4"><h2 className="font-semibold">Saved virtual influencers</h2><p className="mt-1 text-xs text-muted-foreground">Tenant-owned persona briefs; all remain drafts until reviewed.</p></div><div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">{savedPersonas.map(p => <div key={p.id} className="rounded-lg border border-border p-3"><button onClick={() => setPersona(p.brief)} className="w-full text-left"><p className="font-medium">{p.name}</p><p className="mt-1 text-xs text-muted-foreground">{p.status.replaceAll('_',' ')}</p><p className="mt-2 line-clamp-2 text-sm text-muted-foreground">{p.brief?.persona || 'No persona description'}</p></button>{p.status !== 'approved_for_content_review' && p.status !== 'rejected' && <div className="mt-3 flex flex-wrap gap-2"><button onClick={() => void reviewPersona(p, 'approve')} className="rounded-md border border-border px-2 py-1.5 text-xs">Approve persona</button><button onClick={() => void reviewPersona(p, 'changes_requested')} className="rounded-md border border-border px-2 py-1.5 text-xs">Request changes</button></div>}</div>)}</div></section>}

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
        {artifactLoading ? <p className="p-5 text-sm text-muted-foreground">Loading saved artifacts…</p> : artifacts.length ? <div className="divide-y divide-border">{artifacts.map(a => <div key={a.id} className="flex flex-wrap items-center gap-3 p-4"><div className="grid size-10 place-items-center rounded-lg border border-border"><FileText className="size-4" /></div><div className="min-w-0 flex-1"><p className="font-medium">{a.title}</p><p className="mt-1 text-xs text-muted-foreground">{a.artifact_type.replaceAll('_',' ')} · Version {a.current_version} · {a.current_version_review_status || a.status}</p></div><div className="flex flex-wrap gap-2">{a.current_version_review_status !== 'approved' && <button onClick={() => void reviewArtifact(a, 'approve')} className="rounded-lg border border-border px-3 py-2 text-sm">Approve v{a.current_version}</button>}<button onClick={() => void reviewArtifact(a, 'changes_requested')} className="rounded-lg border border-border px-3 py-2 text-sm">Request changes</button><button onClick={() => void openArtifactEditor(a)} className="rounded-lg border border-border px-3 py-2 text-sm">Edit JSON</button><button onClick={() => void exportArtifact(a)} className="rounded-lg border border-border px-3 py-2 text-sm">Export JSON</button></div></div>)}</div> : <p className="p-8 text-center text-sm text-muted-foreground">No saved artifacts yet. Generate an influencer brief and choose “Save as artifact”.</p>}
      </div>
      {artifactDetail && <section className="space-y-3 rounded-xl border border-border bg-card p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">Edit artifact · {artifactDetail.title}</h3><p className="mt-1 text-xs text-muted-foreground">Editing creates a new immutable version and resets approval. This editor changes structured JSON; it does not claim rich document rendering.</p></div><button onClick={() => { setArtifactDetail(null); setArtifactEditorText(''); }} className="rounded-lg border border-border px-3 py-2 text-sm">Close</button></div><textarea value={artifactEditorText} onChange={e => setArtifactEditorText(e.target.value)} rows={14} spellCheck={false} className="w-full rounded-lg border border-border bg-background p-3 font-mono text-xs leading-5" aria-label="Artifact JSON content" /><button onClick={() => void saveArtifactVersion()} disabled={artifactVersionSaving} className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50">{artifactVersionSaving ? 'Saving version…' : 'Save new version'}</button></section>}
    </section>}

    {tab === 'calendar' && <section className="space-y-4"><div><h2 className="text-xl font-semibold">Publishing calendar</h2><p className="mt-1 text-sm text-muted-foreground">A read-only view of scheduled dates stored on campaign posts. Scheduling changes remain in the established campaign planner.</p></div><div className="rounded-xl border border-border bg-card"><div className="divide-y divide-border">{posts.filter(p => p.scheduled_at).sort((a,b) => String(a.scheduled_at).localeCompare(String(b.scheduled_at))).map(post => <div key={post.id} className="flex flex-wrap items-center gap-4 p-4"><div className="min-w-36"><p className="text-sm font-medium">{new Date(post.scheduled_at!).toLocaleDateString()}</p><p className="text-xs text-muted-foreground">{new Date(post.scheduled_at!).toLocaleTimeString()}</p></div><div className="min-w-0 flex-1"><p className="line-clamp-2 text-sm">{post.content || 'Untitled content'}</p><p className="mt-1 text-xs capitalize text-muted-foreground">{post.platform}</p></div><span className="rounded-full border border-border px-2 py-1 text-xs">{statusLabel(post)}</span></div>)}</div>{posts.every(p => !p.scheduled_at) && <p className="p-8 text-center text-sm text-muted-foreground">No scheduled posts are returned by the API.</p>}</div></section>}

    {tab === 'performance' && <section className="space-y-4"><div><h2 className="text-xl font-semibold">Performance and learning</h2><p className="mt-1 text-sm text-muted-foreground">Metrics come from the existing analytics endpoint. Missing measurements remain unavailable instead of being shown as zero.</p></div>{performance ? <pre className="overflow-auto rounded-xl border border-border bg-card p-5 text-xs leading-6">{JSON.stringify(performance, null, 2)}</pre> : <div className="rounded-xl border border-border bg-card p-8 text-center"><BarChart3 className="mx-auto size-7 text-muted-foreground" /><p className="mt-3 text-sm text-muted-foreground">No verified analytics payload loaded yet. Open this section to fetch connected-platform measurements.</p></div>}</section>}

    <footer className="flex flex-col gap-2 border-t border-border pt-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between"><span>OctaOS Campaign Studio · Tenant-scoped API data</span><span>Draft content is not the same as approved or published content.</span></footer>
  </main>;
}

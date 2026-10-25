'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { notify } from '@/lib/notify';
import {
  Calendar as CalendarIcon,
  BarChart3,
  Newspaper,
  BookOpen,
  Loader2,
  CheckCircle2,
  Film,
  Image as ImageIcon,
  Sparkles,
  RefreshCw,
  Zap,
  ChevronLeft,
  ChevronRight,
  X,
  Lightbulb,
} from 'lucide-react';

interface MarketingEvent {
  name: string;
  date: string;
  days_until: number;
  hook: string;
  category: string;
  scope?: 'global' | 'country' | 'state';
  country?: string;
  country_code?: string;
  state?: string;
  state_code?: string;
  region?: string;
  ideas?: string[];
  source?: string;
}

interface NewsSignal {
  topic: string;
  signal: string;
  relevance_score: number;
  category: string;
  keywords: string[];
}

interface RadarData {
  company_name: string;
  industry: string;
  target_regions?: string[];
  target_states?: string[];
  products_count: number;
  upcoming_events: MarketingEvent[];
  news_signals: NewsSignal[];
  brand_voice?: { tone?: string; archetype?: string; vocabulary?: string[] };
  motion_design_tokens?: { pace?: string };
}

interface CalendarPost {
  id: string;
  platform: string;
  content: string;
  status?: string;
  approval_status?: string;
  scheduled_at?: string | null;
}

interface AnalyticsTopPost {
  id: string;
  platform: string;
  content: string;
  impressions?: number;
  engagement?: number;
}

interface AnalyticsDashboard {
  totals?: {
    posts?: number;
    published?: number;
    impressions?: number;
    engagement?: number;
    clicks?: number;
    avg_engagement_rate?: number;
    avg_ctr?: number;
  };
  top_posts?: AnalyticsTopPost[];
}

interface PulseResult {
  message?: string;
  posts_created?: number;
  detail?: string;
}

interface AutonomousMarketingRadarProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  onPulseSuccess?: () => void;
}

type Tab = 'calendar' | 'results' | 'news' | 'brand';
type Mode = 'schedule' | 'draft';

const PLATFORMS = [
  { id: 'linkedin', label: 'LinkedIn', color: '#7888D9' },
  { id: 'instagram', label: 'Instagram', color: '#AAB5C4' },
  { id: 'facebook', label: 'Facebook', color: '#7888D9' },
  { id: 'twitter', label: 'X', color: '#AAB5C4' },
];
const platformMeta = (id: string) =>
  PLATFORMS.find((p) => p.id === id) ?? { id, label: id, color: '#AAB5C4' };

// Scoped OctaOS graphite/indigo theme: matches the workspace design tokens.
const LIGHT_THEME = {
  '--background': '#202630',
  '--foreground': '#E5EAF1',
  '--card': '#29323E',
  '--card-foreground': '#E5EAF1',
  '--popover': '#29323E',
  '--popover-foreground': '#E5EAF1',
  '--primary': '#7888D9',
  '--primary-foreground': '#202630',
  '--secondary': '#333E4C',
  '--secondary-foreground': '#E5EAF1',
  '--muted': '#333E4C',
  '--muted-foreground': '#AAB5C4',
  '--accent': '#333E4C',
  '--accent-foreground': '#E5EAF1',
  '--border': '#414C5A',
  '--input': '#414C5A',
  '--ring': '#A1AEF0',
} as React.CSSProperties;

const pad = (n: number) => String(n).padStart(2, '0');
const dateKey = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const postKey = (iso?: string | null) => (iso ? dateKey(new Date(iso)) : null);
const compact = (n: number) =>
  new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(n);

export default function AutonomousMarketingRadar({
  API_URL,
  fetchWithAuth,
  onPulseSuccess,
}: AutonomousMarketingRadarProps) {
  const [tab, setTab] = useState<Tab>('calendar');
  const [radar, setRadar] = useState<RadarData | null>(null);
  const [posts, setPosts] = useState<CalendarPost[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  // Calendar state
  const today = useMemo(() => new Date(), []);
  const [month, setMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [selected, setSelected] = useState<string | null>(null);

  // Create-post form
  const [content, setContent] = useState('');
  const [platforms, setPlatforms] = useState<string[]>(['linkedin']);
  const [time, setTime] = useState('09:00');
  const [mode, setMode] = useState<Mode>('schedule');
  const [saving, setSaving] = useState(false);
  const [generatingWithAi, setGeneratingWithAi] = useState(false);

  // Autonomous pulse
  const [pulseOpen, setPulseOpen] = useState(false);
  const [pulseMedia, setPulseMedia] = useState<'auto' | 'video' | 'image'>('auto');
  const [pulsing, setPulsing] = useState(false);
  const [pulseResult, setPulseResult] = useState<PulseResult | null>(null);

  const loadPosts = useCallback(async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/?limit=500`);
      if (res.ok) setPosts(await res.json());
    } catch (err) {
      console.error('Failed to load posts:', err);
    }
  }, [API_URL, fetchWithAuth]);

  const loadRadar = useCallback(
    async (refreshRegional = false) => {
      try {
        const res = await fetchWithAuth(
          `${API_URL}/marketing/radar?days_ahead=365&news_limit=6${refreshRegional ? '&refresh_regional=true' : ''}`
        );
        if (res.ok) setRadar(await res.json());
      } catch (err) {
        console.error('Failed to load radar:', err);
      }
    },
    [API_URL, fetchWithAuth]
  );

  const loadAnalytics = useCallback(async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/analytics/dashboard`);
      if (res.ok) setAnalytics(await res.json());
    } catch (err) {
      console.error('Failed to load analytics:', err);
    }
  }, [API_URL, fetchWithAuth]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      await Promise.all([loadRadar(), loadPosts(), loadAnalytics()]);
      if (mounted) setLoading(false);
    })();
    return () => {
      mounted = false;
    };
  }, [loadRadar, loadPosts, loadAnalytics]);

  const refreshAll = async () => {
    setLoading(true);
    await Promise.all([loadRadar(true), loadPosts(), loadAnalytics()]);
    setLoading(false);
  };

  // Scope filter: all | global | country | state
  const [eventScope, setEventScope] = useState<'all' | 'global' | 'country' | 'state'>('all');

  const filteredEvents = useMemo(() => {
    const list = radar?.upcoming_events ?? [];
    if (eventScope === 'all') return list;
    return list.filter((e) => (e.scope || 'country') === eventScope);
  }, [radar, eventScope]);

  // ---- derived calendar data ----
  const eventsByDay = useMemo(() => {
    const map = new Map<string, MarketingEvent[]>();
    filteredEvents.forEach((e) => {
      const k = e.date.slice(0, 10);
      map.set(k, [...(map.get(k) ?? []), e]);
    });
    return map;
  }, [filteredEvents]);

  const postsByDay = useMemo(() => {
    const map = new Map<string, CalendarPost[]>();
    posts.forEach((p) => {
      const k = postKey(p.scheduled_at);
      if (k) map.set(k, [...(map.get(k) ?? []), p]);
    });
    return map;
  }, [posts]);

  const cells = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const start = new Date(first);
    start.setDate(1 - first.getDay());
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [month]);

  const todayKey = dateKey(today);
  const selectedEvents = selected ? eventsByDay.get(selected) ?? [] : [];
  const selectedPosts = selected ? postsByDay.get(selected) ?? [] : [];
  const selectedIsPast = selected ? selected < todayKey : false;

  const openDay = (key: string) => {
    setSelected(key);
    setMode('schedule');
  };

  const togglePlatform = (id: string) =>
    setPlatforms((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));

  const generateAiPost = async (seedTopic?: string) => {
    const topicToUse =
      seedTopic?.trim() ||
      content.trim() ||
      selectedEvents[0]?.hook ||
      selectedEvents[0]?.name ||
      radar?.industry ||
      'company update and industry insights';

    setGeneratingWithAi(true);
    try {
      const primaryPlatform = platforms[0] || 'linkedin';
      const res = await fetchWithAuth(`${API_URL}/marketing/generate-text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topicToUse,
          platform: primaryPlatform,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.content) {
          setContent(data.content);
          notify('Generated post with AI!');
        }
      } else {
        notify('Could not generate post. Please try again.');
      }
    } catch (err) {
      console.error('AI post generation error:', err);
      notify('Network error generating post with AI.');
    } finally {
      setGeneratingWithAi(false);
    }
  };

  const createPost = async () => {
    if (!selected) return;
    if (!content.trim()) return notify('Write the post text first.');
    if (platforms.length === 0) return notify('Choose at least one platform.');
    const when = new Date(`${selected}T${time}:00`);
    setSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/manual-multi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platforms,
          content,
          publish_mode: mode,
          scheduled_at: when.toISOString(),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        notify(
          `${mode === 'schedule' ? 'Scheduled' : 'Saved draft for'} ${data.length} post${data.length === 1 ? '' : 's'} on ${selected} at ${time}.`
        );
        setContent('');
        await loadPosts();
        onPulseSuccess?.();
      } else {
        notify(data.detail || 'Could not create the post.');
      }
    } catch (err) {
      console.error('Create post failed:', err);
      notify('Network error creating the post.');
    } finally {
      setSaving(false);
    }
  };

  const runPulse = async () => {
    setPulsing(true);
    setPulseResult(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/autonomous-pulse?background=false`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platforms,
          media_type: pulseMedia,
          generate_media: true,
          auto_schedule: true,
          confidence_threshold: 0.85,
        }),
      });
      const data: PulseResult = await res.json();
      if (res.ok) {
        setPulseResult(data);
        notify(data.message || `Pulse created ${data.posts_created ?? 0} scheduled posts.`);
        await loadPosts();
        onPulseSuccess?.();
      } else {
        notify(data.detail || 'Autonomous pulse failed.');
      }
    } catch (err) {
      console.error('Pulse failed:', err);
      notify('Network error running the pulse.');
    } finally {
      setPulsing(false);
    }
  };

  // ---- chart data (real, derived from posts + analytics) ----
  const byDayChart = useMemo(() => {
    return Array.from({ length: 14 }, (_, i) => {
      const d = new Date(today);
      d.setDate(today.getDate() + i - 3);
      const list = postsByDay.get(dateKey(d)) ?? [];
      return {
        key: dateKey(d),
        label: `${d.getDate()}`,
        published: list.filter((p) => p.status === 'published').length,
        scheduled: list.filter((p) => p.status !== 'published' && p.approval_status !== 'pending').length,
        draft: list.filter((p) => p.status !== 'published' && p.approval_status === 'pending').length,
      };
    });
  }, [postsByDay, today]);
  const byDayMax = Math.max(1, ...byDayChart.map((d) => d.published + d.scheduled + d.draft));

  const byPlatform = useMemo(() => {
    const counts = new Map<string, number>();
    posts.forEach((p) => counts.set(p.platform, (counts.get(p.platform) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [posts]);
  const platformMax = Math.max(1, ...byPlatform.map(([, n]) => n));

  const topPosts = analytics?.top_posts ?? [];
  const topMax = Math.max(1, ...topPosts.map((p) => p.impressions ?? 0));
  const totals = analytics?.totals;

  const tabs: { id: Tab; label: string; icon: typeof CalendarIcon }[] = [
    { id: 'calendar', label: 'Calendar', icon: CalendarIcon },
    { id: 'results', label: 'Results', icon: BarChart3 },
    { id: 'news', label: 'News signals', icon: Newspaper },
    { id: 'brand', label: 'Brand context', icon: BookOpen },
  ];

  const chip = (active: boolean) =>
    `rounded-md border px-2.5 py-1 text-xs transition-colors ${
      active
        ? 'border-primary bg-accent font-medium text-accent-foreground'
        : 'border-border text-muted-foreground hover:bg-muted'
    }`;

  return (
    <section
      style={LIGHT_THEME}
      className="space-y-4 rounded-xl border border-border bg-background p-5 text-foreground shadow-sm"
    >
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold">Content calendar</h3>
          <p className="text-xs text-muted-foreground">
            Click a date to write a post, pick platforms and a time.
            {radar?.company_name ? ` · ${radar.company_name}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refreshAll} disabled={loading} className="h-8 gap-1.5 text-xs">
            <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setPulseOpen((v) => !v)} className="h-8 gap-1.5 text-xs">
            <Zap className="size-3.5" />
            Auto-generate posts
          </Button>
        </div>
      </div>

      {pulseOpen && (
        <div className="space-y-3 rounded-lg border border-border bg-muted/50 p-3 text-xs">
          <p className="text-muted-foreground">
            The agent reads upcoming dates and news, writes posts for the selected platforms and schedules them.
          </p>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-medium">Platforms</span>
              {PLATFORMS.map((p) => (
                <button key={p.id} type="button" onClick={() => togglePlatform(p.id)} className={chip(platforms.includes(p.id))}>
                  {p.label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-medium">Media</span>
              {[
                { id: 'auto' as const, label: 'Auto', icon: Sparkles },
                { id: 'video' as const, label: 'Video', icon: Film },
                { id: 'image' as const, label: 'Image', icon: ImageIcon },
              ].map((m) => {
                const Icon = m.icon;
                return (
                  <button key={m.id} type="button" onClick={() => setPulseMedia(m.id)} className={`${chip(pulseMedia === m.id)} inline-flex items-center gap-1`}>
                    <Icon className="size-3" />
                    {m.label}
                  </button>
                );
              })}
            </div>
            <Button size="sm" onClick={runPulse} disabled={pulsing || platforms.length === 0} className="ml-auto h-8 gap-1.5 text-xs">
              {pulsing ? <Loader2 className="size-3.5 animate-spin" /> : <Zap className="size-3.5" />}
              {pulsing ? 'Generating…' : 'Generate and schedule'}
            </Button>
          </div>
          {pulseResult && (
            <p className="flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="size-4 text-emerald-600" />
              {pulseResult.posts_created ?? 0} posts created and scheduled
            </p>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-border text-sm">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 font-medium transition-colors ${
                tab === t.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="size-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {loading && !radar ? (
        <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
          <Loader2 className="mr-2 size-4 animate-spin" /> Loading…
        </div>
      ) : (
        <>
          {/* ---------------- CALENDAR ---------------- */}
          {tab === 'calendar' && (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
              <div className="space-y-3">
                {/* Scope Filter Bar */}
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-muted/30 p-2 text-xs">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-medium text-muted-foreground mr-1">Scope:</span>
                    <button
                      type="button"
                      onClick={() => setEventScope('all')}
                      className={`rounded-full px-2.5 py-0.5 font-medium transition-colors ${
                        eventScope === 'all'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      All Events ({radar?.upcoming_events?.length ?? 0})
                    </button>
                    <button
                      type="button"
                      onClick={() => setEventScope('global')}
                      className={`rounded-full px-2.5 py-0.5 font-medium transition-colors ${
                        eventScope === 'global'
                          ? 'bg-blue-600 text-white'
                          : 'bg-muted text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      🌐 Global
                    </button>
                    <button
                      type="button"
                      onClick={() => setEventScope('country')}
                      className={`rounded-full px-2.5 py-0.5 font-medium transition-colors ${
                        eventScope === 'country'
                          ? 'bg-emerald-600 text-white'
                          : 'bg-muted text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      🏛️ Country
                    </button>
                    <button
                      type="button"
                      onClick={() => setEventScope('state')}
                      className={`rounded-full px-2.5 py-0.5 font-medium transition-colors ${
                        eventScope === 'state'
                          ? 'bg-amber-600 text-white'
                          : 'bg-muted text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      📍 State-wise
                    </button>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                    {radar?.target_regions?.length ? (
                      <span className="rounded bg-background px-2 py-0.5 border border-border">
                        Country: {radar.target_regions.join(', ')}
                      </span>
                    ) : null}
                    {radar?.target_states?.length ? (
                      <span className="rounded bg-background px-2 py-0.5 border border-border">
                        State: {radar.target_states.join(', ')}
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold">
                    {month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
                  </h4>
                  <div className="flex items-center gap-1">
                    <Button variant="outline" size="icon" className="size-7" aria-label="Previous month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>
                      <ChevronLeft className="size-4" />
                    </Button>
                    <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setMonth(new Date(today.getFullYear(), today.getMonth(), 1))}>
                      Today
                    </Button>
                    <Button variant="outline" size="icon" className="size-7" aria-label="Next month" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-7 overflow-hidden rounded-lg border border-border text-xs">
                  {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
                    <div key={d} className="border-b border-border bg-muted px-2 py-1.5 text-center font-medium text-muted-foreground">
                      {d}
                    </div>
                  ))}
                  {cells.map((d) => {
                    const key = dateKey(d);
                    const inMonth = d.getMonth() === month.getMonth();
                    const dayEvents = eventsByDay.get(key) ?? [];
                    const dayPosts = postsByDay.get(key) ?? [];
                    const isSelected = selected === key;
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => openDay(key)}
                        className={`flex min-h-20 flex-col items-start gap-1 border-b border-r border-border p-1.5 text-left transition-colors hover:bg-accent ${
                          inMonth ? 'bg-background' : 'bg-muted/50 text-muted-foreground'
                        } ${isSelected ? 'ring-2 ring-inset ring-primary' : ''}`}
                      >
                        <span
                          className={`flex size-5 items-center justify-center rounded-full text-[11px] ${
                            key === todayKey ? 'bg-primary font-semibold text-primary-foreground' : ''
                          }`}
                        >
                          {d.getDate()}
                        </span>
                        {dayEvents.slice(0, 2).map((e) => {
                          const badgeCls =
                            e.scope === 'global'
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300'
                              : e.scope === 'state'
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                              : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300';
                          return (
                            <span
                              key={e.name}
                              className={`w-full truncate rounded px-1 text-[10px] ${badgeCls}`}
                              title={`${e.name} (${e.scope || 'country'})`}
                            >
                              {e.scope === 'global' ? '🌐 ' : e.scope === 'state' ? '📍 ' : '🏛️ '}
                              {e.name}
                            </span>
                          );
                        })}
                        {dayPosts.length > 0 && (
                          <span className="flex flex-wrap gap-0.5">
                            {dayPosts.slice(0, 4).map((p) => (
                              <span key={p.id} className="size-2 rounded-full" style={{ background: platformMeta(p.platform).color }} title={`${platformMeta(p.platform).label} · ${p.status ?? ''}`} />
                            ))}
                            {dayPosts.length > 4 && <span className="text-[10px] text-muted-foreground">+{dayPosts.length - 4}</span>}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
                <p className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
                  <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-blue-500" /> Global</span>
                  <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> Country</span>
                  <span className="inline-flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-amber-500" /> State-wise</span>
                  {PLATFORMS.map((p) => (
                    <span key={p.id} className="inline-flex items-center gap-1">
                      <span className="size-2 rounded-full" style={{ background: p.color }} /> {p.label}
                    </span>
                  ))}
                </p>
              </div>

              {/* Day panel */}
              <aside className="space-y-3 rounded-lg border border-border p-3 text-sm">
                {!selected ? (
                  <div className="flex h-full min-h-40 flex-col items-center justify-center gap-1 text-center text-muted-foreground">
                    <CalendarIcon className="size-6" />
                    <p className="text-xs">Select a date to view events & schedule posts.</p>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold">
                        {new Date(`${selected}T00:00:00`).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
                      </h4>
                      <button type="button" aria-label="Close" onClick={() => setSelected(null)} className="text-muted-foreground hover:text-foreground">
                        <X className="size-4" />
                      </button>
                    </div>

                    {selectedEvents.map((e) => (
                      <div key={e.name} className="space-y-2 rounded-md border border-border bg-card p-3 text-xs shadow-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-semibold text-foreground leading-snug">{e.name}</p>
                            <span className="inline-flex items-center gap-1 mt-0.5 text-[10px] text-muted-foreground font-medium">
                              📅 {e.source === 'google_calendar_api' ? 'Google Calendar (Live Feed)' : e.source === 'connected_google_calendar' ? 'Connected Workspace Calendar' : (e.source || 'Live Calendar')}
                            </span>
                          </div>
                          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${
                            e.scope === 'global' ? 'bg-blue-100 text-blue-800' :
                            e.scope === 'state' ? 'bg-amber-100 text-amber-800' :
                            'bg-emerald-100 text-emerald-800'
                          }`}>
                            {e.scope === 'global' ? '🌐 Global' : e.scope === 'state' ? `📍 ${e.state || 'State'}` : `🏛️ ${e.country || 'Country'}`}
                          </span>
                        </div>

                        {e.hook && (
                          <div className="rounded bg-muted/60 p-2 text-muted-foreground">
                            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground mb-0.5">Strategic Hook</p>
                            <p className="text-foreground italic leading-relaxed">"{e.hook}"</p>
                          </div>
                        )}

                        {e.ideas && e.ideas.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Creative Angles</p>
                            <div className="space-y-1">
                              {e.ideas.map((idea, idx) => (
                                <button
                                  key={idx}
                                  type="button"
                                  onClick={() => setContent(idea)}
                                  className="w-full text-left rounded border border-border/60 bg-background hover:bg-accent/40 p-1.5 text-[11px] text-foreground transition-colors"
                                >
                                  • {idea}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="flex flex-wrap items-center gap-3 pt-1">
                          <button
                            type="button"
                            onClick={() => setContent(e.hook || e.name)}
                            className="inline-flex items-center gap-1 font-medium text-primary underline underline-offset-2 hover:opacity-80"
                          >
                            <Lightbulb className="size-3" /> Use hook
                          </button>
                          <button
                            type="button"
                            onClick={() => generateAiPost(e.hook || e.name)}
                            disabled={generatingWithAi}
                            className="inline-flex items-center gap-1 font-medium text-primary hover:underline disabled:opacity-50"
                          >
                            {generatingWithAi ? <Loader2 className="size-3 animate-spin" /> : <Sparkles className="size-3" />}
                            Generate post with AI
                          </button>
                        </div>
                      </div>
                    ))}

                    {selectedPosts.length > 0 && (
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-muted-foreground">Already on this day</p>
                        {selectedPosts.map((p) => (
                          <div key={p.id} className="flex items-start gap-2 rounded-md bg-muted px-2 py-1.5 text-xs">
                            <span className="mt-1 size-2 shrink-0 rounded-full" style={{ background: platformMeta(p.platform).color }} />
                            <span className="line-clamp-2 flex-1">{p.content}</span>
                            <span className="shrink-0 capitalize text-muted-foreground">{p.status}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {selectedIsPast ? (
                      <p className="text-xs text-muted-foreground">This date has passed. Pick today or a future date to schedule.</p>
                    ) : (
                      <div className="space-y-3">
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <label htmlFor="cal-post-text" className="text-xs font-medium">Post text</label>
                            <button
                              type="button"
                              onClick={() => generateAiPost()}
                              disabled={generatingWithAi}
                              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline disabled:opacity-50"
                            >
                              {generatingWithAi ? <Loader2 className="size-3 animate-spin" /> : <Sparkles className="size-3" />}
                              {content.trim() ? 'Enhance with AI' : 'Generate with AI'}
                            </button>
                          </div>
                          <textarea
                            id="cal-post-text"
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            rows={5}
                            placeholder="What should this post say? Or click 'Generate with AI'"
                            className="w-full rounded-md border border-input bg-background px-2.5 py-2 text-sm outline-none focus:border-primary"
                          />
                        </div>
                        <div className="space-y-1">
                          <span className="text-xs font-medium">Platforms</span>
                          <div className="flex flex-wrap gap-1.5">
                            {PLATFORMS.map((p) => (
                              <button key={p.id} type="button" onClick={() => togglePlatform(p.id)} className={chip(platforms.includes(p.id))}>
                                {p.label}
                              </button>
                            ))}
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="space-y-1">
                            <label htmlFor="cal-post-time" className="text-xs font-medium">Time</label>
                            <input
                              id="cal-post-time"
                              type="time"
                              value={time}
                              onChange={(e) => setTime(e.target.value)}
                              className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm outline-none focus:border-primary"
                            />
                          </div>
                          <div className="space-y-1">
                            <span className="text-xs font-medium">Action</span>
                            <div className="flex rounded-md border border-border p-0.5">
                              {(['schedule', 'draft'] as const).map((m) => (
                                <button key={m} type="button" onClick={() => setMode(m)} className={`flex-1 rounded px-2 py-1 text-xs capitalize ${mode === m ? 'bg-accent font-medium text-accent-foreground' : 'text-muted-foreground'}`}>
                                  {m === 'schedule' ? 'Schedule' : 'Draft'}
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                        <Button onClick={createPost} disabled={saving} className="w-full gap-1.5">
                          {saving && <Loader2 className="size-4 animate-spin" />}
                          {mode === 'schedule' ? `Schedule on ${selected} at ${time}` : 'Save as draft'}
                        </Button>
                      </div>
                    )}
                  </>
                )}
              </aside>
            </div>
          )}

          {/* ---------------- RESULTS (charts) ---------------- */}
          {tab === 'results' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {[
                  ['Posts', totals?.posts ?? posts.length],
                  ['Published', totals?.published ?? 0],
                  ['Impressions', compact(totals?.impressions ?? 0)],
                  ['Engagement rate', `${((totals?.avg_engagement_rate ?? 0) * 100).toFixed(2)}%`],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-border p-3">
                    <p className="text-xl font-semibold leading-none">{value}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{label}</p>
                  </div>
                ))}
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="space-y-3 rounded-lg border border-border p-4">
                  <div>
                    <h4 className="text-sm font-semibold">Posts by day</h4>
                    <p className="text-xs text-muted-foreground">Three days back to ten days ahead.</p>
                  </div>
                  <div className="flex h-36 items-end gap-1.5">
                    {byDayChart.map((d) => {
                      const total = d.published + d.scheduled + d.draft;
                      return (
                        <div key={d.key} className="flex flex-1 flex-col items-center gap-1" title={`${d.key}: ${total} posts`}>
                          <div className="flex w-full flex-1 flex-col justify-end overflow-hidden rounded-t">
                            <div style={{ height: `${(d.draft / byDayMax) * 100}%` }} className="bg-slate-300" />
                            <div style={{ height: `${(d.scheduled / byDayMax) * 100}%` }} className="bg-indigo-400" />
                            <div style={{ height: `${(d.published / byDayMax) * 100}%` }} className="bg-emerald-500" />
                          </div>
                          <span className={`text-[10px] ${d.key === todayKey ? 'font-semibold text-primary' : 'text-muted-foreground'}`}>{d.label}</span>
                        </div>
                      );
                    })}
                  </div>
                  <p className="flex gap-3 text-[11px] text-muted-foreground">
                    <span className="inline-flex items-center gap-1"><span className="size-2 rounded-sm bg-emerald-500" /> Published</span>
                    <span className="inline-flex items-center gap-1"><span className="size-2 rounded-sm bg-indigo-400" /> Scheduled</span>
                    <span className="inline-flex items-center gap-1"><span className="size-2 rounded-sm bg-slate-300" /> Draft</span>
                  </p>
                </div>

                <div className="space-y-3 rounded-lg border border-border p-4">
                  <div>
                    <h4 className="text-sm font-semibold">Posts by platform</h4>
                    <p className="text-xs text-muted-foreground">All posts in your workspace.</p>
                  </div>
                  {byPlatform.length === 0 ? (
                    <p className="py-6 text-sm text-muted-foreground">No posts yet.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {byPlatform.map(([id, count]) => (
                        <div key={id} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="font-medium">{platformMeta(id).label}</span>
                            <span className="text-muted-foreground">{count}</span>
                          </div>
                          <div className="h-2 rounded-full bg-muted">
                            <div className="h-full rounded-full" style={{ width: `${(count / platformMax) * 100}%`, background: platformMeta(id).color }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-3 rounded-lg border border-border p-4">
                <div>
                  <h4 className="text-sm font-semibold">Top posts by impressions</h4>
                  <p className="text-xs text-muted-foreground">Needs published posts with synced platform metrics.</p>
                </div>
                {topPosts.length === 0 ? (
                  <p className="py-4 text-sm text-muted-foreground">No metrics yet. Publish a post, then sync metrics from Campaigns › Results.</p>
                ) : (
                  <div className="space-y-2.5">
                    {topPosts.slice(0, 6).map((p) => (
                      <div key={p.id} className="space-y-1">
                        <div className="flex justify-between gap-3 text-xs">
                          <span className="truncate">{platformMeta(p.platform).label} · {p.content}</span>
                          <span className="shrink-0 text-muted-foreground">{compact(p.impressions ?? 0)}</span>
                        </div>
                        <div className="h-2 rounded-full bg-muted">
                          <div className="h-full rounded-full bg-primary" style={{ width: `${((p.impressions ?? 0) / topMax) * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ---------------- NEWS ---------------- */}
          {tab === 'news' &&
            ((radar?.news_signals ?? []).length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">No news signals for this industry right now.</p>
            ) : (
              <ul className="divide-y divide-border rounded-lg border border-border">
                {radar!.news_signals.map((s, i) => (
                  <li key={`${s.topic}-${i}`} className="space-y-1 p-3 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <span className="font-medium">{s.topic}</span>
                      <span className="shrink-0 text-xs text-muted-foreground">{Math.round(s.relevance_score * 100)}% brand fit</span>
                    </div>
                    <p className="text-xs text-muted-foreground">{s.signal}</p>
                  </li>
                ))}
              </ul>
            ))}

          {/* ---------------- BRAND ---------------- */}
          {tab === 'brand' && radar && (
            <dl className="grid gap-x-6 gap-y-3 rounded-lg border border-border p-4 text-sm sm:grid-cols-2">
              {[
                ['Industry', radar.industry],
                ['Regions', radar.target_regions?.join(', ')],
                ['Tone', radar.brand_voice?.tone],
                ['Archetype', radar.brand_voice?.archetype],
                ['Content pace', radar.motion_design_tokens?.pace],
                ['Products in catalog', String(radar.products_count)],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd>{value || 'Not set'}</dd>
                </div>
              ))}
              {radar.brand_voice?.vocabulary?.length ? (
                <div className="sm:col-span-2">
                  <dt className="text-xs text-muted-foreground">Key vocabulary</dt>
                  <dd className="mt-1 flex flex-wrap gap-1">
                    {radar.brand_voice.vocabulary.map((w) => (
                      <span key={w} className="rounded bg-muted px-1.5 py-0.5 text-xs">{w}</span>
                    ))}
                  </dd>
                </div>
              ) : null}
            </dl>
          )}
        </>
      )}
    </section>
  );
}

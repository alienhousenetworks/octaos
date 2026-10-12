'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { notify } from '@/lib/notify';
import {
  Sparkles,
  Calendar,
  Radio,
  Newspaper,
  BookOpen,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Clock,
  Play,
  Film,
  Image as ImageIcon,
  Layers,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Zap,
} from 'lucide-react';

interface MarketingEvent {
  name: string;
  date: string;
  days_until: number;
  hook: string;
  category: string;
  region?: string;
  source?: string;
  custom?: boolean;
}

interface NewsSignal {
  topic: string;
  signal: string;
  relevance_score: number;
  category: string;
  keywords: string[];
  source?: string;
  url?: string;
}

interface RadarData {
  company_name: string;
  industry: string;
  target_regions?: string[];
  products_count: number;
  upcoming_events: MarketingEvent[];
  news_signals: NewsSignal[];
  brand_voice?: {
    tone?: string;
    archetype?: string;
    vocabulary?: string[];
  };
  motion_design_tokens?: {
    pace?: string;
    aspect_ratios?: Record<string, string>;
  };
}

interface AutonomousMarketingRadarProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onPulseSuccess?: () => void;
}

export default function AutonomousMarketingRadar({
  API_URL,
  fetchWithAuth,
  onPulseSuccess,
}: AutonomousMarketingRadarProps) {
  const [radarData, setRadarData] = useState<RadarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'calendar' | 'news' | 'brand'>('calendar');
  const [isPulseModalOpen, setIsPulseModalOpen] = useState(false);
  const [pulsing, setPulsing] = useState(false);
  const [pulsePlatforms, setPulsePlatforms] = useState<string[]>(['linkedin', 'instagram']);
  const [pulseMediaType, setPulseMediaType] = useState<'auto' | 'video' | 'image'>('auto');
  const [pulseResult, setPulseResult] = useState<any>(null);
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);

  const fetchRadar = async (refreshRegional = false) => {
    setLoading(true);
    try {
      const url = `${API_URL}/marketing/radar?days_ahead=14&news_limit=6${refreshRegional ? '&refresh_regional=true' : ''}`;
      const res = await fetchWithAuth(url);
      if (res.ok) {
        const data = await res.json();
        setRadarData(data);
      }
    } catch (err) {
      console.error('Failed to fetch context radar:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRadar();
  }, []);

  const handleRunPulse = async () => {
    setPulsing(true);
    setPulseResult(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/autonomous-pulse?background=false`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platforms: pulsePlatforms,
          media_type: pulseMediaType,
          generate_media: true,
          auto_schedule: true,
          confidence_threshold: 0.85,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setPulseResult(data);
        notify(data.message || `Autonomous pulse created ${data.posts_created ?? 0} scheduled posts!`);
        if (onPulseSuccess) {
          onPulseSuccess();
        }
      } else {
        notify(data.detail || 'Autonomous marketing pulse failed.');
      }
    } catch (err) {
      console.error('Pulse execution error:', err);
      notify('Network error executing autonomous marketing pulse.');
    } finally {
      setPulsing(false);
    }
  };

  const togglePlatform = (p: string) => {
    setPulsePlatforms((prev) =>
      prev.includes(p) ? prev.filter((item) => item !== p) : [...prev, p]
    );
  };

  return (
    <div className="space-y-4 rounded-xl border border-border/80 bg-card/60 p-5 shadow-sm backdrop-blur-sm">
      {/* Header with Auto Mode status */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <Radio className="size-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground">
                Autonomous Marketing Radar
              </h3>
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                <span className="size-1.5 rounded-full bg-emerald-500 animate-ping" />
                Auto Mode Active
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Real-world calendar & industry news intelligence intersecting with your brand knowledge.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchRadar(true)}
            disabled={loading}
            title="Scan live regional cultural context & news signals"
            className="h-8 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh & Scan Regional
          </Button>
          <Button
            size="sm"
            onClick={() => setIsPulseModalOpen(true)}
            className="h-8 gap-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 text-xs text-white shadow-sm hover:from-emerald-700 hover:to-teal-700"
          >
            <Zap className="size-3.5" />
            Run Autonomous Pulse
          </Button>
        </div>
      </div>

      {/* Intelligence summary bar */}
      {radarData && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5 rounded-lg border border-border/60 bg-muted/20 p-2.5 text-xs">
          <div>
            <span className="text-[11px] text-muted-foreground">Target Brand:</span>
            <p className="font-medium text-foreground truncate">{radarData.company_name || 'Business Profile'}</p>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground">Target Region:</span>
            <p className="font-medium text-foreground truncate capitalize">
              {radarData.target_regions && radarData.target_regions.length > 0
                ? radarData.target_regions.join(', ')
                : 'Global & Regional'}
            </p>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground">Industry Sector:</span>
            <p className="font-medium text-foreground truncate capitalize">{radarData.industry || 'Technology'}</p>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground">Upcoming Calendar Hooks:</span>
            <p className="font-medium text-foreground">{radarData.upcoming_events?.length || 0} Events (Next 14d)</p>
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground">Live News Signals:</span>
            <p className="font-medium text-foreground">{radarData.news_signals?.length || 0} Scored Signals</p>
          </div>
        </div>
      )}

      {/* Tabs Switcher */}
      <div className="flex border-b border-border text-xs">
        <button
          type="button"
          onClick={() => setActiveTab('calendar')}
          className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 font-medium transition-colors ${
            activeTab === 'calendar'
              ? 'border-emerald-500 text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Calendar className="size-3.5" />
          Calendar & Cultural Events ({radarData?.upcoming_events?.length || 0})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('news')}
          className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 font-medium transition-colors ${
            activeTab === 'news'
              ? 'border-emerald-500 text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Newspaper className="size-3.5" />
          News & Innovation Signals ({radarData?.news_signals?.length || 0})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('brand')}
          className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 font-medium transition-colors ${
            activeTab === 'brand'
              ? 'border-emerald-500 text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <BookOpen className="size-3.5" />
          Synthesized Brand Comprehension
        </button>
      </div>

      {/* Tab 1: Calendar & Cultural Events */}
      {activeTab === 'calendar' && (
        <div className="space-y-2.5">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
              <Loader2 className="mr-2 size-4 animate-spin" /> Scanning calendar engines...
            </div>
          ) : !radarData?.upcoming_events?.length ? (
            <p className="py-6 text-center text-xs text-muted-foreground">
              No upcoming calendar events detected in the next 14 days. Custom tenant calendar events can be added in Business Profile.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {radarData.upcoming_events.map((event, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-border/80 bg-background/50 p-3 text-xs transition-colors hover:border-emerald-500/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="font-semibold text-foreground">{event.name}</span>
                      <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                        <Clock className="size-3" />
                        <span>{event.date}</span>
                        <span>·</span>
                        <span className="font-medium text-emerald-600 dark:text-emerald-400">
                          {event.days_until === 0
                            ? 'Today!'
                            : event.days_until === 1
                            ? 'Tomorrow'
                            : `in ${event.days_until} days`}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-wrap justify-end">
                      {event.region && (
                        <span className="rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 px-2 py-0.5 text-[10px] font-semibold uppercase">
                          {event.region}
                        </span>
                      )}
                      {event.source === 'agentic_radar' && (
                        <span className="rounded-full bg-teal-500/10 text-teal-700 dark:text-teal-300 px-2 py-0.5 text-[10px] font-semibold uppercase">
                          AI Live
                        </span>
                      )}
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground uppercase">
                        {event.category}
                      </span>
                    </div>
                  </div>

                  <div className="mt-2 rounded-md bg-muted/40 p-2 text-[11px]">
                    <span className="font-medium text-muted-foreground">Suggested Hook:</span>
                    <p className="mt-0.5 text-foreground italic">"{event.hook}"</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: News & Innovation Signals */}
      {activeTab === 'news' && (
        <div className="space-y-2.5">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
              <Loader2 className="mr-2 size-4 animate-spin" /> Scanning live industry news radar...
            </div>
          ) : !radarData?.news_signals?.length ? (
            <p className="py-6 text-center text-xs text-muted-foreground">
              No news signals currently registered for this industry.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {radarData.news_signals.map((sig, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-border/80 bg-background/50 p-3 text-xs transition-colors hover:border-emerald-500/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-foreground">{sig.topic}</span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                      {Math.round(sig.relevance_score * 100)}% Brand Fit
                    </span>
                  </div>

                  <p className="mt-1.5 text-muted-foreground text-[11px] leading-relaxed">
                    {sig.signal}
                  </p>

                  {sig.keywords && sig.keywords.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {sig.keywords.map((kw, ki) => (
                        <span
                          key={ki}
                          className="rounded bg-muted/60 px-1.5 py-0.5 text-[10px] text-muted-foreground"
                        >
                          #{kw}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Synthesized Brand Comprehension */}
      {activeTab === 'brand' && (
        <div className="space-y-3 text-xs">
          {radarData ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border bg-background/50 p-3 space-y-2">
                <span className="font-semibold text-foreground">Brand Voice & Tone</span>
                <p className="text-muted-foreground text-[11px]">
                  <strong className="text-foreground">Tone:</strong>{' '}
                  {radarData.brand_voice?.tone || 'Authoritative, Innovative, Visionary'}
                </p>
                <p className="text-muted-foreground text-[11px]">
                  <strong className="text-foreground">Archetype:</strong>{' '}
                  {radarData.brand_voice?.archetype || 'The Creator & Visionary'}
                </p>
                {radarData.brand_voice?.vocabulary && (
                  <div>
                    <span className="text-[11px] text-muted-foreground">Key Lexicon:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {radarData.brand_voice.vocabulary.map((w, wi) => (
                        <span key={wi} className="rounded bg-muted px-1.5 py-0.5 text-[10px]">
                          {w}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-border bg-background/50 p-3 space-y-2">
                <span className="font-semibold text-foreground">Visual & Motion Design Tokens</span>
                <p className="text-muted-foreground text-[11px]">
                  <strong className="text-foreground">Pace:</strong>{' '}
                  {radarData.motion_design_tokens?.pace || 'Snappy dynamic cuts (0.8s - 2.5s)'}
                </p>
                <p className="text-muted-foreground text-[11px]">
                  <strong className="text-foreground">Aspect Ratios:</strong> 16:9 (LinkedIn), 9:16 (Instagram Reels/TikTok), 1:1 (Facebook)
                </p>
                <p className="text-muted-foreground text-[11px]">
                  <strong className="text-foreground">AI Video Engine:</strong> External Wan2.1, Kling, MiniMax via AI Gateway (no Remotion in Auto Mode)
                </p>
              </div>
            </div>
          ) : (
            <div className="py-6 text-center text-xs text-muted-foreground">
              Loading brand synthesis...
            </div>
          )}
        </div>
      )}

      {/* Autonomous Pulse Configuration Drawer / Trigger Panel */}
      {isPulseModalOpen && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-3 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="size-4 text-emerald-600 dark:text-emerald-400" />
              <h4 className="text-sm font-semibold text-foreground">
                Trigger Immediate Autonomous Pulse (Auto Mode)
              </h4>
            </div>
            <button
              type="button"
              onClick={() => setIsPulseModalOpen(false)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>

          <p className="text-xs text-muted-foreground">
            The agent will synthesize today's radar context, choose optimal strategic angles, generate platform-specific copy, produce external AI media, and schedule posts.
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
            {/* Platforms selector */}
            <div className="space-y-1.5">
              <label className="font-medium text-foreground">Target Networks:</label>
              <div className="flex flex-wrap gap-1.5">
                {['linkedin', 'instagram', 'facebook', 'twitter'].map((plat) => (
                  <button
                    key={plat}
                    type="button"
                    onClick={() => togglePlatform(plat)}
                    className={`rounded-md border px-2.5 py-1 text-xs capitalize transition-colors ${
                      pulsePlatforms.includes(plat)
                        ? 'border-emerald-500 bg-emerald-500/20 text-foreground font-medium'
                        : 'border-border text-muted-foreground hover:bg-muted/50'
                    }`}
                  >
                    {plat === 'twitter' ? 'X / Twitter' : plat}
                  </button>
                ))}
              </div>
            </div>

            {/* Media choice */}
            <div className="space-y-1.5">
              <label className="font-medium text-foreground">Media Modality:</label>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: 'auto', label: 'Agent Decides', icon: Sparkles },
                  { id: 'video', label: 'AI Video (Wan2.1 / Kling / MiniMax)', icon: Film },
                  { id: 'image', label: 'Commercial Visual (FLUX)', icon: ImageIcon },
                ].map((m) => {
                  const Icon = m.icon;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setPulseMediaType(m.id as any)}
                      className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs transition-colors ${
                        pulseMediaType === m.id
                          ? 'border-emerald-500 bg-emerald-500/20 text-foreground font-medium'
                          : 'border-border text-muted-foreground hover:bg-muted/50'
                      }`}
                    >
                      <Icon className="size-3" />
                      {m.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-emerald-500/20">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPulseModalOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleRunPulse}
              disabled={pulsing || pulsePlatforms.length === 0}
              className="gap-1.5 bg-emerald-600 text-xs text-white hover:bg-emerald-700"
            >
              {pulsing ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  Synthesizing Radar & Generating...
                </>
              ) : (
                <>
                  <Play className="size-3.5" />
                  Execute Pulse Across {pulsePlatforms.length} Networks
                </>
              )}
            </Button>
          </div>

          {/* Pulse Execution Results */}
          {pulseResult && (
            <div className="rounded-lg border border-border bg-background p-3 text-xs space-y-2 mt-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="size-4 text-emerald-500" />
                  Pulse Completed: {pulseResult.posts_created} Posts Created & Scheduled
                </span>
                <span className="text-muted-foreground text-[11px]">
                  Safety Confidence Gate: Passed
                </span>
              </div>

              <div className="space-y-1.5 divide-y divide-border/60">
                {pulseResult.posts?.map((p: any, pi: number) => (
                  <div key={pi} className="pt-1.5 first:pt-0 flex items-center justify-between gap-2">
                    <div className="truncate">
                      <span className="font-medium capitalize text-foreground">{p.platform}:</span>{' '}
                      <span className="text-muted-foreground">{p.hook}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground capitalize">
                        {p.media_type}
                      </span>
                      <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                        {p.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

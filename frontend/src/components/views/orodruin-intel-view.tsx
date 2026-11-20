'use client';

import React, { useEffect, useState } from 'react';
import { Globe2, Loader2, MapPin, Radar, Sparkles, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import PageHeader from '@/components/shell/page-header';
import { EmptyState } from '@/components/shell/states';
import { HanddrawnWorkflowSketch } from '@/components/handdraw/handdraw-illustrations';

interface OrodruinIntelViewProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
}

interface OsintSignal {
  source: string;
  category: string;
  title: string;
  url?: string;
  country?: string;
  lat?: number | null;
  lon?: number | null;
  timestamp?: string;
}

export default function OrodruinIntelView({ API_URL, fetchWithAuth }: OrodruinIntelViewProps) {
  const [topic, setTopic] = useState('cloud security');
  const [region, setRegion] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [signals, setSignals] = useState<OsintSignal[]>([]);
  const [analysis, setAnalysis] = useState<string>('');
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSignals = async () => {
    setLoadingSignals(true);
    setError(null);
    try {
      const qs = new URLSearchParams({ topic: topic || 'technology', limit: '12' });
      if (region.trim()) qs.set('region', region.trim());
      const res = await fetchWithAuth(`${API_URL}/orodruin/signals?${qs.toString()}`);
      if (!res.ok) throw new Error(`Failed to fetch OSINT signals (${res.status})`);
      const data = await res.json();
      setSignals(Array.isArray(data.signals) ? data.signals : []);
    } catch (err: any) {
      setError(err?.message || 'Unable to fetch global OSINT signals.');
    } finally {
      setLoadingSignals(false);
    }
  };

  useEffect(() => {
    void loadSignals();
  }, []);

  const runAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setAnalyzing(true);
    setError(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/orodruin/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          region: region.trim() || undefined,
          company_name: companyName.trim() || undefined,
        }),
      });
      if (!res.ok) throw new Error(`Strategy analysis failed (${res.status})`);
      const data = await res.json();
      if (Array.isArray(data.signals)) setSignals(data.signals);
      setAnalysis(data.strategy_analysis || '');
    } catch (err: any) {
      setError(err?.message || 'Analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Global Intelligence (Orodruin)"
        description="Live OSINT signals (GDELT, USGS, NASA EONET) fused with your AI provider and LearningLoop to uncover leads, market trends, and campaign strategies."
        meta={
          <span className="inline-flex items-center gap-1.5 text-info">
            <Globe2 className="size-3.5" />
            Live OSINT + Strategy Engine
          </span>
        }
        actions={<HanddrawnWorkflowSketch className="hidden lg:block" />}
      />

      {error && (
        <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={runAnalysis} className="grid gap-3 rounded-lg border border-border bg-card p-4 md:grid-cols-[1.2fr_1fr_1fr_auto]">
        <Input
          placeholder="Market topic or industry (e.g. cloud security)"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <Input
          placeholder="Region / Country (optional)"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
        />
        <Input
          placeholder="Target company (optional)"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
        />
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={() => void loadSignals()} disabled={loadingSignals}>
            {loadingSignals ? <Loader2 className="size-4 animate-spin" /> : <Radar className="size-4" />}
            Refresh
          </Button>
          <Button type="submit" disabled={analyzing}>
            {analyzing ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            Analyze &amp; Strategize
          </Button>
        </div>
      </form>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
            <h2 className="font-heading text-sm font-semibold">Live OSINT Signal Stream</h2>
            <span className="font-mono text-xs text-muted-foreground">{signals.length} signals</span>
          </div>
          {signals.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No signals loaded yet"
                description="Enter a topic or region and click Refresh to pull live global OSINT feeds."
              />
            </div>
          ) : (
            <div className="divide-y divide-border max-h-[540px] overflow-y-auto">
              {signals.map((sig, idx) => (
                <div key={`${sig.source}-${idx}`} className="flex items-start justify-between gap-3 px-5 py-3.5 hover:bg-surface-hover">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[11px] text-info">
                        {sig.source}
                      </span>
                      <span>{sig.category}</span>
                      {sig.lat != null && sig.lon != null && (
                        <span className="inline-flex items-center gap-1 font-mono text-[11px]">
                          <MapPin className="size-3 text-primary" />
                          {sig.lat.toFixed(2)}, {sig.lon.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 text-sm font-medium text-foreground">{sig.title}</p>
                  </div>
                  {sig.url && (
                    <a
                      href={sig.url}
                      target="_blank"
                      rel="noreferrer"
                      className="shrink-0 rounded-md border border-border p-1.5 text-muted-foreground hover:text-foreground"
                      title="Open source"
                    >
                      <ExternalLink className="size-3.5" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-border bg-card">
          <div className="border-b border-border px-5 py-3.5">
            <h2 className="font-heading text-sm font-semibold">AI Intelligence &amp; Strategy Brief</h2>
          </div>
          <div className="p-5">
            {analysis ? (
              <div className="whitespace-pre-wrap text-sm leading-6 text-foreground/90">{analysis}</div>
            ) : (
              <EmptyState
                title="Ready to synthesize strategy"
                description="Click Analyze & Strategize to fuse live OSINT signals with your configured AI provider and LearningLoop."
              />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

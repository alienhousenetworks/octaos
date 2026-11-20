'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  ExternalLink,
  Globe2,
  Loader2,
  MapPin,
  Network,
  Radar,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
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

interface GraphNode {
  id: string;
  label: string;
  kind: string;
  weight: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

export default function OrodruinIntelView({ API_URL, fetchWithAuth }: OrodruinIntelViewProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [topic, setTopic] = useState('cloud security');
  const [region, setRegion] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [activeTab, setActiveTab] = useState<'map' | 'intel' | 'graph' | 'feeds'>('map');

  const [signals, setSignals] = useState<OsintSignal[]>([]);
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] });
  const [analysis, setAnalysis] = useState<string>('');
  const [markets, setMarkets] = useState<Record<string, any> | null>(null);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [ransomware, setRansomware] = useState<any[]>([]);

  const [loadingSignals, setLoadingSignals] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSignalsAndGraph = async () => {
    setLoadingSignals(true);
    setError(null);
    try {
      const qs = new URLSearchParams({ topic: topic || 'technology', limit: '15' });
      if (region.trim()) qs.set('region', region.trim());
      const [sigRes, graphRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/orodruin/signals?${qs.toString()}`),
        fetchWithAuth(`${API_URL}/orodruin/graph?${qs.toString()}`),
      ]);
      if (sigRes.ok) {
        const d = await sigRes.json();
        setSignals(Array.isArray(d.signals) ? d.signals : []);
      }
      if (graphRes.ok) {
        const g = await graphRes.json();
        setGraph({ nodes: g.nodes || [], edges: g.edges || [] });
      }
    } catch (err: any) {
      setError(err?.message || 'Unable to fetch global OSINT signals.');
    } finally {
      setLoadingSignals(false);
    }
  };

  const loadSideFeeds = async () => {
    try {
      const [mRes, pRes, rRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/orodruin/markets`),
        fetchWithAuth(`${API_URL}/orodruin/prediction?limit=6`),
        fetchWithAuth(`${API_URL}/orodruin/ransomware?limit=8`),
      ]);
      if (mRes.ok) setMarkets(await mRes.json());
      if (pRes.ok) setPredictions((await pRes.json()).items || []);
      if (rRes.ok) setRansomware((await rRes.json()).items || []);
    } catch {
      // Optional feed errors are non-blocking
    }
  };

  useEffect(() => {
    void loadSignalsAndGraph();
    void loadSideFeeds();
  }, []);

  // Native MapLibre GL 2D/3D Map Initialization & Live GeoJSON Sync
  useEffect(() => {
    if (activeTab !== 'map' || !mapContainerRef.current) return;
    if (mapRef.current) {
      mapRef.current.resize();
      return;
    }

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap · CARTO',
          },
        },
        layers: [{ id: 'osm-dark', type: 'raster', source: 'osm' }],
      },
      center: [10, 22],
      zoom: 1.8,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [activeTab]);

  // Plot geotagged signals on native MapLibre GL map
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const plot = () => {
      const features = signals
        .filter((s) => s.lat != null && s.lon != null)
        .map((s) => ({
          type: 'Feature' as const,
          geometry: { type: 'Point' as const, coordinates: [s.lon as number, s.lat as number] },
          properties: { title: s.title, source: s.source, category: s.category },
        }));

      const data = { type: 'FeatureCollection' as const, features };
      const existing = map.getSource('octaos-signals') as maplibregl.GeoJSONSource | undefined;
      if (existing) {
        existing.setData(data);
      } else {
        map.addSource('octaos-signals', { type: 'geojson', data });
        map.addLayer({
          id: 'octaos-signals-layer',
          type: 'circle',
          source: 'octaos-signals',
          paint: {
            'circle-radius': 6,
            'circle-color': '#e5a93c',
            'circle-stroke-width': 1.5,
            'circle-stroke-color': '#2dd4bf',
          },
        });
      }
    };

    if (map.loaded()) plot();
    else map.once('load', plot);
  }, [signals, activeTab]);

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
      if (data.graph) setGraph(data.graph);
      setAnalysis(data.strategy_analysis || '');

      // Execute AI UI-driving actions natively on MapLibre
      if (Array.isArray(data.ui_actions) && mapRef.current) {
        for (const act of data.ui_actions) {
          if (act.action === 'focus_map' && act.lat != null && act.lon != null) {
            mapRef.current.flyTo({ center: [act.lon, act.lat], zoom: act.zoom || 4 });
          }
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Global Intelligence (Native Orodruin)"
        description="Live OSINT feeds, MapLibre geospatial view, Actor Graph, and AI strategy synthesis integrated natively inside OctaOS."
        meta={
          <span className="inline-flex items-center gap-1.5 text-info">
            <Globe2 className="size-3.5" />
            Native MapLibre + 10 OSINT Tools
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
        <Input placeholder="Market topic (e.g. cloud security)" value={topic} onChange={(e) => setTopic(e.target.value)} />
        <Input placeholder="Region / Country (optional)" value={region} onChange={(e) => setRegion(e.target.value)} />
        <Input placeholder="Target company (optional)" value={companyName} onChange={(e) => setCompanyName(e.target.value)} />
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={() => void loadSignalsAndGraph()} disabled={loadingSignals}>
            {loadingSignals ? <Loader2 className="size-4 animate-spin" /> : <Radar className="size-4" />}
            Refresh
          </Button>
          <Button type="submit" disabled={analyzing}>
            {analyzing ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            Analyze &amp; Strategize
          </Button>
        </div>
      </form>

      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3">
        {[
          { id: 'map', label: 'Global Map', icon: Globe2 },
          { id: 'intel', label: 'Signals & Strategy', icon: Sparkles },
          { id: 'graph', label: 'Actor Graph', icon: Network },
          { id: 'feeds', label: 'Markets & Cyber', icon: TrendingUp },
        ].map((t) => {
          const Icon = t.icon;
          return (
            <Button
              key={t.id}
              type="button"
              size="sm"
              variant={activeTab === t.id ? 'default' : 'outline'}
              onClick={() => setActiveTab(t.id as any)}
            >
              <Icon className="size-4" />
              {t.label}
            </Button>
          );
        })}
      </div>

      {activeTab === 'map' && (
        <div className="grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="overflow-hidden rounded-lg border border-border bg-card">
            <div ref={mapContainerRef} className="h-[520px] w-full" />
          </div>
          <div className="rounded-lg border border-border bg-card flex flex-col max-h-[520px]">
            <div className="border-b border-border px-4 py-3 text-sm font-semibold">
              Geolocated Signals ({signals.filter((s) => s.lat != null).length})
            </div>
            <div className="divide-y divide-border overflow-y-auto flex-1">
              {signals.filter((s) => s.lat != null && s.lon != null).map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => mapRef.current?.flyTo({ center: [s.lon as number, s.lat as number], zoom: 5 })}
                  className="block w-full px-4 py-3 text-left hover:bg-surface-hover"
                >
                  <div className="flex items-center gap-2 text-xs text-info font-mono">
                    <MapPin className="size-3 text-primary" />
                    <span>{s.source}</span>
                    <span>{s.lat?.toFixed(2)}, {s.lon?.toFixed(2)}</span>
                  </div>
                  <p className="mt-1 text-xs font-medium text-foreground">{s.title}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'intel' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-lg border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
              <h2 className="font-heading text-sm font-semibold">Live OSINT Signal Stream</h2>
              <span className="font-mono text-xs text-muted-foreground">{signals.length} signals</span>
            </div>
            {signals.length === 0 ? (
              <div className="p-6"><EmptyState title="No signals loaded" description="Click Refresh to pull live OSINT feeds." /></div>
            ) : (
              <div className="divide-y divide-border max-h-[480px] overflow-y-auto">
                {signals.map((sig, idx) => (
                  <div key={idx} className="flex items-start justify-between gap-3 px-5 py-3 hover:bg-surface-hover">
                    <div className="min-w-0">
                      <span className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[11px] text-info">{sig.source}</span>
                      <p className="mt-1 text-sm font-medium">{sig.title}</p>
                    </div>
                    {sig.url && (
                      <a href={sig.url} target="_blank" rel="noreferrer" className="shrink-0 rounded border border-border p-1.5 text-muted-foreground hover:text-foreground">
                        <ExternalLink className="size-3.5" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
          <section className="rounded-lg border border-border bg-card">
            <div className="border-b border-border px-5 py-3.5"><h2 className="font-heading text-sm font-semibold">AI Intelligence &amp; Strategy Brief</h2></div>
            <div className="p-5">
              {analysis ? (
                <div className="whitespace-pre-wrap text-sm leading-6 text-foreground/90">{analysis}</div>
              ) : (
                <EmptyState title="Ready to synthesize strategy" description="Click Analyze & Strategize to fuse live signals with your AI provider and LearningLoop." />
              )}
            </div>
          </section>
        </div>
      )}

      {activeTab === 'graph' && (
        <section className="rounded-lg border border-border bg-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-heading text-sm font-semibold">Actor &amp; Signal Co-occurrence Graph</h2>
            <span className="font-mono text-xs text-muted-foreground">{graph.nodes.length} nodes · {graph.edges.length} links</span>
          </div>
          {graph.nodes.length === 0 ? (
            <EmptyState title="No graph nodes yet" description="Refresh signals to build the actor co-occurrence network." />
          ) : (
            <svg viewBox="0 0 760 320" className="w-full rounded-md border border-border bg-background">
              {graph.nodes.map((node, idx) => {
                const angle = (idx / Math.max(graph.nodes.length, 1)) * Math.PI * 2;
                const cx = idx === 0 ? 380 : 380 + Math.cos(angle) * 240;
                const cy = idx === 0 ? 160 : 160 + Math.sin(angle) * 115;
                const fill = node.kind === 'topic' ? '#e5a93c' : node.kind === 'source' ? '#2dd4bf' : '#60a5fa';
                return (
                  <g key={node.id}>
                    {idx > 0 && <line x1={380} y1={160} x2={cx} y2={cy} stroke="#222b36" strokeWidth="1.2" />}
                    <circle cx={cx} cy={cy} r={Math.min(18, 7 + node.weight * 2)} fill={fill} opacity="0.9" />
                    <text x={cx} y={cy + 24} textAnchor="middle" fill="#eceff4" fontSize="10">{node.label.slice(0, 22)}</text>
                  </g>
                );
              })}
            </svg>
          )}
        </section>
      )}

      {activeTab === 'feeds' && (
        <div className="grid gap-5 lg:grid-cols-3">
          <section className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 flex items-center gap-2 font-heading text-sm font-semibold"><TrendingUp className="size-4 text-primary" /> Markets</h3>
            {markets ? (
              <div className="space-y-2 text-sm">
                {Object.entries(markets).map(([coin, vals]: [string, any]) => (
                  <div key={coin} className="flex justify-between rounded border border-border bg-background px-3 py-2">
                    <span className="capitalize">{coin}</span>
                    <span className="font-mono">${vals.usd}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-xs text-muted-foreground">Loading markets...</p>}
          </section>
          <section className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 flex items-center gap-2 font-heading text-sm font-semibold"><Globe2 className="size-4 text-info" /> Prediction Markets</h3>
            <div className="space-y-2 text-xs">
              {predictions.map((p, i) => (
                <div key={i} className="rounded border border-border bg-background p-2.5">{p.question}</div>
              ))}
            </div>
          </section>
          <section className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 flex items-center gap-2 font-heading text-sm font-semibold"><ShieldAlert className="size-4 text-destructive" /> Ransomware Disclosures</h3>
            <div className="space-y-2 text-xs">
              {ransomware.map((r, i) => (
                <div key={i} className="rounded border border-border bg-background p-2.5">
                  <span className="font-semibold">{r.victim || r.post_title}</span>
                  <span className="ml-2 font-mono text-muted-foreground">{r.group_name}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

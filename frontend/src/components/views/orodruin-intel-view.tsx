'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import {
  Camera,
  CloudRain,
  ExternalLink,
  Flame,
  Globe2,
  Layers,
  Loader2,
  MapPin,
  Network,
  Plane,
  Radar,
  Search,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  X,
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

interface CameraFeature {
  geometry: { coordinates: [number, number] };
  properties: {
    id: string;
    title: string;
    source: string;
    city?: string;
    country?: string;
    image?: string | null;
    mp4?: string | null;
  };
}

const BASEMAPS: Record<'dark' | 'streets' | 'satellite', { label: string; tiles: string[] }> = {
  dark: {
    label: '2D Dark',
    tiles: ['https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'],
  },
  streets: {
    label: 'Streets',
    tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
  },
  satellite: {
    label: 'Satellite',
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
  },
};

export default function OrodruinIntelView({ API_URL, fetchWithAuth }: OrodruinIntelViewProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const [topic, setTopic] = useState('cloud security');
  const [region, setRegion] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [deepQuery, setDeepQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'map' | 'intel' | 'cameras' | 'sites' | 'graph' | 'feeds'>('map');
  const [tenantSites, setTenantSites] = useState<any[]>([]);
  const [siteName, setSiteName] = useState('');
  const [siteIndustry, setSiteIndustry] = useState('real_estate');
  const [siteCamUrl, setSiteCamUrl] = useState('');
  const [siteLat, setSiteLat] = useState('');
  const [siteLon, setSiteLon] = useState('');
  const [siteReport, setSiteReport] = useState('');
  const [generatingSiteReport, setGeneratingSiteReport] = useState(false);
  const [basemap, setBasemap] = useState<'dark' | 'streets' | 'satellite' | 'globe'>('dark');
  const [placeQuery, setPlaceQuery] = useState('');
  const [areaBrief, setAreaBrief] = useState<any | null>(null);
  const [cables, setCables] = useState<any[]>([]);
  const [newsRss, setNewsRss] = useState<any[]>([]);
  const [breaches, setBreaches] = useState<any[]>([]);

  const [layers, setLayers] = useState({
    signals: true,
    cameras: true,
    flights: false,
    disasters: true,
    radar: false,
    cables: false,
  });

  const [signals, setSignals] = useState<OsintSignal[]>([]);
  const [cameras, setCameras] = useState<CameraFeature[]>([]);
  const [flights, setFlights] = useState<any[]>([]);
  const [disasters, setDisasters] = useState<any[]>([]);
  const [radarTileUrl, setRadarTileUrl] = useState<string | null>(null);
  const [selectedCamera, setSelectedCamera] = useState<CameraFeature['properties'] | null>(null);
  const [graph, setGraph] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] });
  const [analysis, setAnalysis] = useState<string>('');
  const [deepResults, setDeepResults] = useState<any[]>([]);
  const [foundLeads, setFoundLeads] = useState<any[]>([]);
  const [leadSummary, setLeadSummary] = useState<string>('');
  const [saveToCrm, setSaveToCrm] = useState(false);
  const [findingLeads, setFindingLeads] = useState(false);
  const [markets, setMarkets] = useState<Record<string, any> | null>(null);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [ransomware, setRansomware] = useState<any[]>([]);

  const [loadingSignals, setLoadingSignals] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [deepSearching, setDeepSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAllFeeds = async () => {
    setLoadingSignals(true);
    setError(null);
    try {
      const qs = new URLSearchParams({ topic: topic || 'technology', limit: '15' });
      if (region.trim()) qs.set('region', region.trim());
      const [sigRes, graphRes, camRes, disRes, wxRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/orodruin/signals?${qs.toString()}`),
        fetchWithAuth(`${API_URL}/orodruin/graph?${qs.toString()}`),
        fetchWithAuth(`${API_URL}/orodruin/cameras?limit=80`),
        fetchWithAuth(`${API_URL}/orodruin/disasters?limit=40`),
        fetchWithAuth(`${API_URL}/orodruin/weather-radar`),
      ]);
      if (sigRes.ok) setSignals((await sigRes.json()).signals || []);
      if (graphRes.ok) {
        const g = await graphRes.json();
        setGraph({ nodes: g.nodes || [], edges: g.edges || [] });
      }
      if (camRes.ok) setCameras((await camRes.json()).features || []);
      if (disRes.ok) setDisasters((await disRes.json()).features || []);
      if (wxRes.ok) setRadarTileUrl((await wxRes.json()).tile_url || null);
    } catch (err: any) {
      setError(err?.message || 'Unable to fetch global OSINT feeds.');
    } finally {
      setLoadingSignals(false);
    }
  };

  const loadFlights = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/orodruin/flights?limit=200`);
      if (res.ok) setFlights((await res.json()).features || []);
    } catch {
      // non-blocking
    }
  };

  const loadSideFeeds = async () => {
    try {
      const [mRes, pRes, rRes, sRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/orodruin/markets`),
        fetchWithAuth(`${API_URL}/orodruin/prediction?limit=6`),
        fetchWithAuth(`${API_URL}/orodruin/ransomware?limit=8`),
        fetchWithAuth(`${API_URL}/orodruin/sites`),
      ]);
      if (mRes.ok) setMarkets(await mRes.json());
      if (pRes.ok) setPredictions((await pRes.json()).items || []);
      if (rRes.ok) setRansomware((await rRes.json()).items || []);
      if (sRes.ok) setTenantSites((await sRes.json()).items || []);
    } catch {
      // non-blocking
    }
  };

  useEffect(() => {
    void loadAllFeeds();
    void loadSideFeeds();
  }, []);

  useEffect(() => {
    if (layers.flights && flights.length === 0) {
      void loadFlights();
    }
  }, [layers.flights]);

  // Initialize native MapLibre GL map
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
          basemap: {
            type: 'raster',
            tiles: BASEMAPS[basemap === 'globe' ? 'dark' : basemap].tiles,
            tileSize: 256,
          },
        },
        layers: [{ id: 'basemap-layer', type: 'raster', source: 'basemap' }],
      },
      center: [0, 28],
      zoom: 1.8,
    });

    if (basemap === 'globe') {
      map.once('style.load', () => {
        try {
          (map as any).setProjection({ type: 'globe' });
        } catch {
          // fallback to mercator if unsupported
        }
      });
    }

    map.on('click', async (e) => {
      try {
        const res = await fetchWithAuth(`${API_URL}/orodruin/area-intel?lat=${e.lngLat.lat.toFixed(4)}&lon=${e.lngLat.lng.toFixed(4)}`);
        if (res.ok) setAreaBrief(await res.json());
      } catch {
        // non-blocking
      }
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [activeTab, basemap]);

  // Sync all toggleable GeoJSON & Weather Radar layers onto MapLibre GL
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const syncLayers = () => {
      const upsertCircleLayer = (id: string, features: any[], color: string, visible: boolean) => {
        const data = { type: 'FeatureCollection' as const, features: visible ? features : [] };
        const src = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
        if (src) {
          src.setData(data);
        } else {
          map.addSource(id, { type: 'geojson', data });
          map.addLayer({
            id: `${id}-layer`,
            type: 'circle',
            source: id,
            paint: {
              'circle-radius': id === 'octaos-flights' ? 3.5 : 5.5,
              'circle-color': color,
              'circle-stroke-width': 1,
              'circle-stroke-color': '#0a0d10',
            },
          });
        }
      };

      const sigFeatures = signals
        .filter((s) => s.lat != null && s.lon != null)
        .map((s) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [s.lon, s.lat] },
          properties: { title: s.title, source: s.source },
        }));

      upsertCircleLayer('octaos-signals', sigFeatures, '#e5a93c', layers.signals);
      upsertCircleLayer('octaos-cameras', cameras, '#2dd4bf', layers.cameras);
      upsertCircleLayer('octaos-flights', flights, '#60a5fa', layers.flights);
      upsertCircleLayer('octaos-disasters', disasters, '#f87171', layers.disasters);

      // RainViewer radar overlay
      if (layers.radar && radarTileUrl) {
        if (!map.getSource('octaos-radar')) {
          map.addSource('octaos-radar', { type: 'raster', tiles: [radarTileUrl], tileSize: 256 });
          map.addLayer({ id: 'octaos-radar-layer', type: 'raster', source: 'octaos-radar', paint: { 'raster-opacity': 0.55 } });
        }
      } else if (map.getLayer('octaos-radar-layer')) {
        map.removeLayer('octaos-radar-layer');
        map.removeSource('octaos-radar');
      }
    };

    if (map.loaded()) syncLayers();
    else map.once('load', syncLayers);
  }, [signals, cameras, flights, disasters, layers, radarTileUrl, basemap, activeTab]);

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

  const runDeepSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deepQuery.trim()) return;
    setDeepSearching(true);
    setFindingLeads(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/orodruin/find-leads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: deepQuery.trim(),
          geography: region.trim() || undefined,
          save_to_crm: saveToCrm,
          count: 8,
        }),
      });
      if (res.ok) {
        const d = await res.json();
        setFoundLeads(Array.isArray(d.leads) ? d.leads : []);
        setDeepResults(Array.isArray(d.leads) ? d.leads : []);
        setLeadSummary(d.ai_summary || '');
      }
    } finally {
      setDeepSearching(false);
      setFindingLeads(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Global Intelligence (Native Orodruin)"
        description="Live OSINT feeds, MapLibre multi-layer geospatial view, ~80+ live public cameras, ADS-B flights, GDACS disasters, weather radar, Actor Graph, and Deep Search."
        meta={
          <span className="inline-flex items-center gap-1.5 text-info">
            <Globe2 className="size-3.5" />
            14 Native OSINT + UI Tools Active
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
          <Button type="button" variant="outline" onClick={() => void loadAllFeeds()} disabled={loadingSignals}>
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
          { id: 'map', label: 'Global Map & Layers', icon: Globe2 },
          { id: 'sites', label: `My Sites & Telemetry (${tenantSites.length})`, icon: MapPin },
          { id: 'cameras', label: `Live Cameras (${cameras.length})`, icon: Camera },
          { id: 'intel', label: 'Deep Search & Strategy', icon: Sparkles },
          { id: 'graph', label: 'Actor Graph', icon: Network },
          { id: 'feeds', label: 'Markets & Cyber', icon: TrendingUp },
        ].map((t) => {
          const Icon = t.icon;
          return (
            <Button key={t.id} type="button" size="sm" variant={activeTab === t.id ? 'default' : 'outline'} onClick={() => setActiveTab(t.id as any)}>
              <Icon className="size-4" />
              {t.label}
            </Button>
          );
        })}
      </div>

      {activeTab === 'map' && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-2.5 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 font-medium text-muted-foreground"><Layers className="size-3.5" /> Layers:</span>
              {[
                { key: 'signals', label: 'OSINT Signals', icon: Radar },
                { key: 'cameras', label: 'Live Cameras', icon: Camera },
                { key: 'flights', label: 'Live Flights', icon: Plane },
                { key: 'disasters', label: 'Disasters', icon: Flame },
                { key: 'radar', label: 'Weather Radar', icon: CloudRain },
              ].map((l) => {
                const Icon = l.icon;
                const on = layers[l.key as keyof typeof layers];
                return (
                  <button
                    key={l.key}
                    type="button"
                    onClick={() => setLayers((prev) => ({ ...prev, [l.key]: !prev[l.key as keyof typeof layers] }))}
                    className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 transition ${
                      on ? 'border-primary/40 bg-primary/15 text-foreground' : 'border-border bg-background text-muted-foreground'
                    }`}
                  >
                    <Icon className="size-3" />
                    {l.label}
                  </button>
                );
              })}
            </div>
            <div className="flex items-center gap-1">
              {(['dark', 'streets', 'satellite', 'globe'] as const).map((b) => (
                <button
                  key={b}
                  type="button"
                  onClick={() => setBasemap(b)}
                  className={`rounded border px-2 py-1 ${basemap === b ? 'border-info/50 bg-info/15 text-info' : 'border-border text-muted-foreground'}`}
                >
                  {b === 'globe' ? '3D Globe' : BASEMAPS[b].label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  placeholder="Jump to city, country, or address (Nominatim geocoder)..."
                  value={placeQuery}
                  onChange={(e) => setPlaceQuery(e.target.value)}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={async () => {
                    if (placeQuery.trim().length < 2) return;
                    const r = await fetchWithAuth(`${API_URL}/orodruin/geocode?q=${encodeURIComponent(placeQuery.trim())}`);
                    if (r.ok) {
                      const list = (await r.json()).results || [];
                      if (list[0] && mapRef.current) {
                        mapRef.current.flyTo({ center: [list[0].lon, list[0].lat], zoom: 9 });
                      }
                    }
                  }}
                >
                  <MapPin className="size-4" />
                  Locate
                </Button>
              </div>
              <div className="overflow-hidden rounded-lg border border-border bg-card">
                <div ref={mapContainerRef} className="h-[520px] w-full" />
              </div>
              {areaBrief && (
                <div className="rounded-lg border border-border bg-card px-4 py-2.5 text-xs flex flex-wrap items-center gap-4">
                  <span className="font-mono text-info">Area Intel ({areaBrief.lat}, {areaBrief.lon})</span>
                  {areaBrief.weather && <span>Temp: {areaBrief.weather.temperature}°C · Wind: {areaBrief.weather.windspeed} km/h</span>}
                  {areaBrief.air_quality && <span>PM2.5: {areaBrief.air_quality.pm2_5} · NO₂: {areaBrief.air_quality.nitrogen_dioxide}</span>}
                </div>
              )}
            </div>
            <div className="rounded-lg border border-border bg-card flex flex-col max-h-[520px]">
              <div className="border-b border-border px-4 py-3 text-sm font-semibold">
                Geolocated Feed ({signals.filter((s) => s.lat != null).length + cameras.length})
              </div>
              <div className="divide-y divide-border overflow-y-auto flex-1">
                {cameras.slice(0, 15).map((c) => (
                  <button
                    key={c.properties.id}
                    type="button"
                    onClick={() => {
                      mapRef.current?.flyTo({ center: c.geometry.coordinates, zoom: 11 });
                      setSelectedCamera(c.properties);
                    }}
                    className="block w-full px-4 py-2.5 text-left hover:bg-surface-hover"
                  >
                    <div className="flex items-center gap-2 font-mono text-[11px] text-info">
                      <Camera className="size-3" />
                      <span>{c.properties.source}</span>
                    </div>
                    <p className="mt-0.5 text-xs font-medium text-foreground">{c.properties.title}</p>
                  </button>
                ))}
                {signals.filter((s) => s.lat != null && s.lon != null).map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => mapRef.current?.flyTo({ center: [s.lon as number, s.lat as number], zoom: 5 })}
                    className="block w-full px-4 py-2.5 text-left hover:bg-surface-hover"
                  >
                    <div className="flex items-center gap-2 font-mono text-[11px] text-primary">
                      <MapPin className="size-3" />
                      <span>{s.source}</span>
                    </div>
                    <p className="mt-0.5 text-xs font-medium text-foreground">{s.title}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'sites' && (
        <div className="space-y-5">
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!siteName.trim()) return;
              const r = await fetchWithAuth(`${API_URL}/orodruin/sites`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  name: siteName.trim(),
                  industry: siteIndustry,
                  camera_url: siteCamUrl.trim() || undefined,
                  lat: siteLat ? parseFloat(siteLat) : undefined,
                  lon: siteLon ? parseFloat(siteLon) : undefined,
                }),
              });
              if (r.ok) {
                setSiteName('');
                setSiteCamUrl('');
                void loadSideFeeds();
              }
            }}
            className="grid gap-2 rounded-lg border border-border bg-card p-4 md:grid-cols-[1.2fr_0.9fr_1.3fr_0.6fr_0.6fr_auto]"
          >
            <Input placeholder="Site / Plant name (e.g. Austin Tower Site A)" value={siteName} onChange={(e) => setSiteName(e.target.value)} />
            <Input placeholder="Industry (real_estate, manufacturing)" value={siteIndustry} onChange={(e) => setSiteIndustry(e.target.value)} />
            <Input placeholder="Site Camera / Telemetry URL (optional)" value={siteCamUrl} onChange={(e) => setSiteCamUrl(e.target.value)} />
            <Input placeholder="Lat" value={siteLat} onChange={(e) => setSiteLat(e.target.value)} />
            <Input placeholder="Lon" value={siteLon} onChange={(e) => setSiteLon(e.target.value)} />
            <Button type="submit">Add Site</Button>
          </form>

          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-lg border border-border bg-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-heading text-sm font-semibold">Registered Sites &amp; Feeds</h3>
                <Button
                  type="button"
                  size="sm"
                  disabled={generatingSiteReport}
                  onClick={async () => {
                    setGeneratingSiteReport(true);
                    try {
                      const r = await fetchWithAuth(`${API_URL}/orodruin/site-report`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({}),
                      });
                      if (r.ok) setSiteReport((await r.json()).report || '');
                    } finally {
                      setGeneratingSiteReport(false);
                    }
                  }}
                >
                  {generatingSiteReport ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                  Generate AI Site Report
                </Button>
              </div>
              {tenantSites.length === 0 ? (
                <EmptyState title="No sites registered yet" description="Add a real estate site camera, factory floor, or warehouse to monitor and generate AI operational reports." />
              ) : (
                <div className="divide-y divide-border rounded-md border border-border bg-background">
                  {tenantSites.map((s) => (
                    <div key={s.id} className="p-3 text-xs flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-foreground">{s.name}</div>
                        <div className="text-muted-foreground font-mono">{s.industry} {s.lat != null ? `· ${s.lat}, ${s.lon}` : ''}</div>
                      </div>
                      {s.camera_url && (
                        <Button type="button" size="sm" variant="outline" onClick={() => setSelectedCamera({ id: s.id, title: s.name, source: s.industry, image: s.camera_url, mp4: s.camera_url.endsWith('.mp4') ? s.camera_url : null })}>
                          View Feed
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
            <section className="rounded-lg border border-border bg-card p-4">
              <h3 className="mb-3 font-heading text-sm font-semibold">AI Operational &amp; Site Report</h3>
              {siteReport ? (
                <div className="whitespace-pre-wrap text-sm leading-6 text-foreground/90">{siteReport}</div>
              ) : (
                <EmptyState title="No site report generated yet" description="Click Generate AI Site Report to analyze your sites, cameras, local weather, and operational risks." />
              )}
            </section>
          </div>
        </div>
      )}

      {activeTab === 'cameras' && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cameras.length === 0 ? (
            <div className="col-span-full"><EmptyState title="No cameras loaded" description="Click Refresh to load TfL London and LTA Singapore public feeds." /></div>
          ) : (
            cameras.slice(0, 24).map((cam) => (
              <div key={cam.properties.id} className="overflow-hidden rounded-lg border border-border bg-card">
                {cam.properties.mp4 ? (
                  <video src={cam.properties.mp4} controls muted playsInline className="h-44 w-full bg-black object-cover" />
                ) : cam.properties.image ? (
                  <img src={cam.properties.image} alt={cam.properties.title} className="h-44 w-full bg-black object-cover" />
                ) : null}
                <div className="p-3">
                  <div className="font-mono text-[11px] text-info">{cam.properties.source} · {cam.properties.city}</div>
                  <div className="mt-1 text-xs font-semibold text-foreground">{cam.properties.title}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'intel' && (
        <div className="space-y-5">
          <form onSubmit={runDeepSearch} className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card p-3">
            <Input
              className="flex-1 min-w-[240px]"
              placeholder="Deep browser search for company leads (e.g. B2B cybersecurity startups hiring CISO)..."
              value={deepQuery}
              onChange={(e) => setDeepQuery(e.target.value)}
            />
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground px-2">
              <input type="checkbox" checked={saveToCrm} onChange={(e) => setSaveToCrm(e.target.checked)} />
              Save to CRM
            </label>
            <Button type="submit" disabled={deepSearching || findingLeads}>
              {deepSearching ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
              Find Company Leads
            </Button>
          </form>

          {foundLeads.length > 0 && (
            <section className="rounded-lg border border-border bg-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-heading text-sm font-semibold">Discovered Company Leads ({foundLeads.length})</h3>
                {leadSummary && <span className="text-xs text-info">AI Summary Attached</span>}
              </div>
              {leadSummary && <p className="text-xs leading-5 text-muted-foreground whitespace-pre-wrap">{leadSummary}</p>}
              <div className="divide-y divide-border rounded-md border border-border bg-background">
                {foundLeads.map((ld, i) => (
                  <div key={i} className="flex items-start justify-between gap-3 p-3 text-xs">
                    <div>
                      <div className="font-semibold text-foreground">{ld.company_name}</div>
                      <div className="mt-0.5 text-muted-foreground">{ld.opportunity}</div>
                    </div>
                    {ld.source_url && (
                      <a href={ld.source_url} target="_blank" rel="noreferrer" className="shrink-0 text-info hover:underline">
                        Source
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-lg border border-border bg-card">
              <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
                <h2 className="font-heading text-sm font-semibold">OSINT &amp; Deep Search Results</h2>
                <span className="font-mono text-xs text-muted-foreground">{(deepResults.length || signals.length)} items</span>
              </div>
              <div className="divide-y divide-border max-h-[480px] overflow-y-auto">
                {(deepResults.length ? deepResults : signals).map((sig, idx) => (
                  <div key={idx} className="flex items-start justify-between gap-3 px-5 py-3 hover:bg-surface-hover">
                    <div className="min-w-0">
                      <span className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[11px] text-info">{sig.source || 'web'}</span>
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
                    <text x={cx} y={cy + 24} textAnchor="middle" fill="#eceff4" fontSize="10">{String(node.label).slice(0, 22)}</text>
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

      {selectedCamera && (
        <div className="fixed bottom-5 right-5 z-50 w-96 overflow-hidden rounded-lg border border-border bg-card shadow-2xl">
          <div className="flex items-center justify-between border-b border-border px-3 py-2 text-xs">
            <span className="font-semibold truncate">{selectedCamera.title}</span>
            <button type="button" onClick={() => setSelectedCamera(null)} className="text-muted-foreground hover:text-foreground">
              <X className="size-4" />
            </button>
          </div>
          {selectedCamera.mp4 ? (
            <video src={selectedCamera.mp4} controls autoPlay muted playsInline className="h-52 w-full bg-black object-cover" />
          ) : selectedCamera.image ? (
            <img src={selectedCamera.image} alt={selectedCamera.title} className="h-52 w-full bg-black object-cover" />
          ) : null}
        </div>
      )}
    </div>
  );
}

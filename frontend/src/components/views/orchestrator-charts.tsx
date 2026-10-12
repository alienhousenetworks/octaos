'use client';

import React, { useState, useEffect, useRef } from 'react';
import { PlotlyChartSpec } from '@/types/orchestrator';
import { BarChart3, Filter, TrendingUp, Users, Maximize2, Minimize2 } from 'lucide-react';

interface OrchestratorChartsProps {
  charts: PlotlyChartSpec[];
}

declare global {
  interface Window {
    Plotly?: {
      newPlot: (element: HTMLElement, data: unknown[], layout: Record<string, unknown>, config?: Record<string, unknown>) => Promise<void>;
      purge: (element: HTMLElement) => void;
      Plots?: { resize: (element: HTMLElement) => void };
    };
  }
}

export default function OrchestratorCharts({ charts }: OrchestratorChartsProps) {
  const [activeTab, setActiveTab] = useState<string>(charts[0]?.chart_id || 'funnel_chart');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [plotlyLoaded, setPlotlyLoaded] = useState(() => typeof window !== 'undefined' && !!window.Plotly);
  const containerRef = useRef<HTMLDivElement>(null);

  // Dynamic script loader for Plotly.js without bloat
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.Plotly) {
      queueMicrotask(() => setPlotlyLoaded(true));
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdn.plot.ly/plotly-basic-2.35.2.min.js';
    script.async = true;
    script.onload = () => setPlotlyLoaded(true);
    document.body.appendChild(script);

    return () => {
      // Keep script cached
    };
  }, []);

  const activeChart = charts.find((c) => c.chart_id === activeTab) || charts[0];

  // Render chart whenever activeChart, plotlyLoaded, or isFullscreen changes
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !activeChart) return;

    if (plotlyLoaded && window.Plotly) {
      const spec = activeChart.spec;
      const responsiveLayout = {
        ...spec.layout,
        autosize: true,
        margin: { l: 40, r: 20, t: 40, b: 40 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
      };

      window.Plotly.newPlot(
        container,
        spec.data,
        responsiveLayout,
        spec.config || { responsive: true, displayModeBar: false }
      ).catch((err) => {
        console.warn('Plotly render notice:', err);
      });

      return () => {
        if (container && window.Plotly) {
          window.Plotly.purge(container);
        }
      };
    }
  }, [activeChart, plotlyLoaded, isFullscreen]);

  if (!charts || charts.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground bg-secondary/20 rounded-xl border border-border">
        No visual analytics specs generated.
      </div>
    );
  }

  const getTabIcon = (cat: string) => {
    switch (cat) {
      case 'funnel':
        return <Filter size={12} />;
      case 'financial':
        return <TrendingUp size={12} />;
      case 'operations':
        return <Users size={12} />;
      default:
        return <BarChart3 size={12} />;
    }
  };

  return (
    <div className={`flex flex-col bg-card border border-border rounded-xl overflow-hidden transition-all duration-200 ${
      isFullscreen ? 'fixed inset-4 z-50 shadow-2xl bg-card/95 backdrop-blur-md' : 'w-full'
    }`}>
      {/* Chart Nav Tabs */}
      <div className="flex items-center justify-between px-3 py-2 bg-secondary/30 border-b border-border flex-wrap gap-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          {charts.map((c) => (
            <button
              key={c.chart_id}
              onClick={() => setActiveTab(c.chart_id)}
              className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md transition-colors ${
                activeTab === c.chart_id
                  ? 'bg-primary text-primary-foreground shadow-xs'
                  : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
              }`}
            >
              {getTabIcon(c.category)}
              <span>{c.title}</span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[10px] uppercase font-semibold tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            Interactive Plotly
          </span>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
        </div>
      </div>

      {/* Description Header */}
      {activeChart?.description && (
        <div className="px-3.5 py-2 bg-secondary/15 border-b border-border">
          <p className="text-xs text-muted-foreground leading-relaxed">{activeChart.description}</p>
        </div>
      )}

      {/* Canvas / Plotly Container */}
      <div className="relative p-2 flex items-center justify-center min-h-[260px] w-full" style={{ height: isFullscreen ? 'calc(100% - 80px)' : '300px' }}>
        <div ref={containerRef} className="w-full h-full" />

        {/* Fallback loader indicator */}
        {!plotlyLoaded && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-card/80 backdrop-blur-xs gap-2">
            <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-muted-foreground">Rendering visual analytics...</span>
          </div>
        )}
      </div>
    </div>
  );
}

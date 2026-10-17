'use client';

import React, { useState } from 'react';
import { ArrowRight, BarChart2, Table as TableIcon } from 'lucide-react';

export interface CategoryDef {
  key: string;
  label: string;
  color: string;
}

export interface StackedDataPoint {
  date: string;
  [key: string]: any;
}

export interface StackedBarChartProps {
  title: string;
  subtitle?: string;
  categories: CategoryDef[];
  data: StackedDataPoint[];
  yAxisFormatter?: (val: number) => string;
  onExplore?: () => void;
  className?: string;
  height?: number;
}

export default function StackedBarChart({
  title,
  subtitle,
  categories,
  data,
  yAxisFormatter = (v) => `${v}`,
  onExplore,
  className = '',
  height = 240,
}: StackedBarChartProps) {
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className={`rounded-xl border border-border/70 bg-card/60 p-5 backdrop-blur-md ${className}`}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        </div>
        <div className="flex h-48 items-center justify-center text-xs text-muted-foreground">
          No time-series data available for this range
        </div>
      </div>
    );
  }

  // Calculate maximum total across all data points
  const totals = data.map((d) =>
    categories.reduce((acc, cat) => {
      if (activeCategory && activeCategory !== cat.key) return acc;
      const val = Number(d[cat.key]) || 0;
      return acc + val;
    }, 0)
  );
  const maxTotal = Math.max(1, ...totals);

  // Y-axis tick milestones
  const yTicks = [
    maxTotal,
    Math.round(maxTotal * 0.75),
    Math.round(maxTotal * 0.5),
    Math.round(maxTotal * 0.25),
    0,
  ];

  return (
    <div
      className={`relative flex flex-col justify-between rounded-xl border border-border/70 bg-card/60 p-5 shadow-sm backdrop-blur-md ${className}`}
    >
      {/* Header: Title + Explore + View Toggle */}
      <div className="flex items-center justify-between gap-3 border-b border-border/40 pb-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>

        <div className="flex items-center gap-2">
          {onExplore && (
            <button
              onClick={onExplore}
              className="inline-flex items-center text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              Explore
              <ArrowRight className="ml-0.5 h-3 w-3" />
            </button>
          )}

          <div className="flex items-center rounded-md border border-border/70 bg-background/60 p-0.5">
            <button
              onClick={() => setViewMode('chart')}
              className={`rounded p-1 text-xs transition-colors ${
                viewMode === 'chart'
                  ? 'bg-secondary text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Chart View"
            >
              <BarChart2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`rounded p-1 text-xs transition-colors ${
                viewMode === 'table'
                  ? 'bg-secondary text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Table View"
            >
              <TableIcon className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Body */}
      {viewMode === 'table' ? (
        <div className="mt-4 max-h-[260px] overflow-auto text-xs">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border/60 text-muted-foreground">
                <th className="py-1.5 font-medium">Date</th>
                {categories.map((c) => (
                  <th key={c.key} className="py-1.5 text-right font-medium">
                    {c.label}
                  </th>
                ))}
                <th className="py-1.5 text-right font-semibold">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/30">
              {data.map((row, i) => {
                const rowTotal = categories.reduce((sum, c) => sum + (Number(row[c.key]) || 0), 0);
                return (
                  <tr key={i} className="hover:bg-accent/40">
                    <td className="py-1.5 font-medium text-foreground">{row.date}</td>
                    {categories.map((c) => (
                      <td key={c.key} className="py-1.5 text-right text-muted-foreground">
                        {yAxisFormatter(Number(row[c.key]) || 0)}
                      </td>
                    ))}
                    <td className="py-1.5 text-right font-semibold text-foreground">
                      {yAxisFormatter(rowTotal)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative mt-4">
          {/* Chart Grid with Y-Axis */}
          <div className="flex gap-2">
            {/* Y-Axis Labels */}
            <div
              className="flex flex-col justify-between pb-6 text-right font-mono text-[10px] text-muted-foreground/70"
              style={{ height }}
            >
              {yTicks.map((tick, i) => (
                <span key={i}>{yAxisFormatter(tick)}</span>
              ))}
            </div>

            {/* Bars Area */}
            <div className="relative flex-1">
              {/* Horizontal Gridlines */}
              <div
                className="pointer-events-none absolute inset-0 flex flex-col justify-between pb-6"
                style={{ height }}
              >
                {yTicks.map((_, i) => (
                  <div key={i} className="w-full border-b border-border/30" />
                ))}
              </div>

              {/* Stacked Columns */}
              <div
                className="relative flex items-end justify-between gap-1 pb-6"
                style={{ height }}
              >
                {data.map((point, idx) => {
                  const isHovered = hoveredIndex === idx;
                  const dayTotal = categories.reduce(
                    (sum, cat) => sum + (Number(point[cat.key]) || 0),
                    0
                  );

                  return (
                    <div
                      key={idx}
                      className="group relative flex h-full flex-1 flex-col justify-end"
                      onMouseEnter={() => setHoveredIndex(idx)}
                      onMouseLeave={() => setHoveredIndex(null)}
                    >
                      {/* Bar Container */}
                      <div
                        className={`flex w-full flex-col-reverse overflow-hidden rounded-t transition-opacity duration-150 ${
                          hoveredIndex !== null && !isHovered ? 'opacity-40' : 'opacity-100'
                        }`}
                        style={{
                          height: `${Math.max(4, (dayTotal / maxTotal) * 100)}%`,
                        }}
                      >
                        {categories.map((cat) => {
                          const val = Number(point[cat.key]) || 0;
                          if (val <= 0) return null;
                          const segPct = dayTotal > 0 ? (val / dayTotal) * 100 : 0;
                          const isCatDimmed =
                            activeCategory !== null && activeCategory !== cat.key;

                          return (
                            <div
                              key={cat.key}
                              style={{
                                height: `${segPct}%`,
                                backgroundColor: cat.color,
                                opacity: isCatDimmed ? 0.2 : 0.95,
                              }}
                              className="w-full transition-all hover:brightness-110"
                            />
                          );
                        })}
                      </div>

                      {/* Tooltip on Hover */}
                      {isHovered && (
                        <div className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border bg-popover/95 px-3 py-2 text-xs shadow-xl backdrop-blur-md">
                          <p className="font-semibold text-foreground">{point.date}</p>
                          <div className="mt-1 space-y-0.5">
                            {categories.map((cat) => {
                              const val = Number(point[cat.key]) || 0;
                              return (
                                <div
                                  key={cat.key}
                                  className="flex items-center justify-between gap-3 text-[11px]"
                                >
                                  <span className="flex items-center gap-1.5 text-muted-foreground">
                                    <span
                                      className="h-2 w-2 rounded-full"
                                      style={{ backgroundColor: cat.color }}
                                    />
                                    {cat.label}:
                                  </span>
                                  <span className="font-medium text-foreground">
                                    {yAxisFormatter(val)}
                                  </span>
                                </div>
                              );
                            })}
                            <div className="mt-1 border-t border-border/60 pt-1 flex justify-between font-bold text-foreground">
                              <span>Total:</span>
                              <span>{yAxisFormatter(dayTotal)}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Date Label under Bar */}
                      <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 truncate text-[10px] text-muted-foreground/75">
                        {point.date}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Legend Below */}
      <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-border/30 pt-3 text-xs">
        {categories.map((cat) => {
          const isActive = activeCategory === cat.key;
          return (
            <button
              key={cat.key}
              onClick={() => setActiveCategory(isActive ? null : cat.key)}
              className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 transition-all ${
                activeCategory && !isActive
                  ? 'opacity-40'
                  : 'opacity-100 hover:bg-secondary/70'
              }`}
            >
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: cat.color }}
              />
              <span className="font-medium text-foreground">{cat.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

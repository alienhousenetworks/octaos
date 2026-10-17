'use client';

import React from 'react';
import { ArrowRight } from 'lucide-react';

export interface LeaderboardItem {
  id?: string;
  rank: number;
  name: string;
  subtitle?: string;
  metric: string;
  badgeColor?: string;
  icon?: React.ReactNode;
}

export interface LeaderboardCardProps {
  title: string;
  items: LeaderboardItem[];
  metricHeader?: string;
  onExplore?: () => void;
  className?: string;
  emptyText?: string;
}

export default function LeaderboardCard({
  title,
  items,
  metricHeader,
  onExplore,
  className = '',
  emptyText = 'No items recorded yet',
}: LeaderboardCardProps) {
  return (
    <div
      className={`flex flex-col justify-between rounded-xl border border-border/70 bg-card/60 p-5 shadow-sm backdrop-blur-md ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-3">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        {onExplore && (
          <button
            onClick={onExplore}
            className="inline-flex items-center text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Explore
            <ArrowRight className="ml-0.5 h-3 w-3" />
          </button>
        )}
      </div>

      {/* List */}
      <div className="mt-3 flex-1 divide-y divide-border/30">
        {items.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-xs text-muted-foreground">
            {emptyText}
          </div>
        ) : (
          items.map((item, idx) => (
            <div
              key={item.id || idx}
              className="group flex items-center justify-between py-2.5 transition-colors hover:bg-accent/30 rounded-lg px-2"
            >
              <div className="flex items-center gap-3 min-w-0">
                {/* Rank Number */}
                <span className="w-4 text-center font-mono text-xs font-bold text-muted-foreground/80">
                  {item.rank}
                </span>

                {/* Optional Status Dot or Icon */}
                {item.icon ? (
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-secondary text-secondary-foreground">
                    {item.icon}
                  </div>
                ) : (
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: item.badgeColor || '#10B981' }}
                  />
                )}

                {/* Primary & Subtitle */}
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                    {item.name}
                  </p>
                  {item.subtitle && (
                    <p className="truncate font-mono text-[11px] text-muted-foreground">
                      {item.subtitle}
                    </p>
                  )}
                </div>
              </div>

              {/* Formatted Metric Value on the Right */}
              <div className="shrink-0 text-right">
                <span className="font-mono text-xs font-bold text-foreground">
                  {item.metric}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

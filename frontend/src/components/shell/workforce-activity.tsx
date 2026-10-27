'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, Circle, RefreshCw } from 'lucide-react';
import { useWorkspace } from '@/lib/workspace';

type WorkforceEvent = {
  id: string;
  event_type: string;
  source: string;
  run_id?: string | null;
  payload?: Record<string, unknown>;
  created_at?: string | null;
};

function eventSummary(event: WorkforceEvent): string {
  const payload = event.payload || {};
  const title = typeof payload.title === 'string' ? payload.title : '';
  const message = typeof payload.message === 'string' ? payload.message : '';
  const status = typeof payload.status === 'string' ? payload.status : '';
  return [title, message, status ? `Status: ${status}` : ''].filter(Boolean).join(' · ') || event.event_type;
}

export default function WorkforceActivity() {
  const workspace = useWorkspace();
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<WorkforceEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const cursorRef = useRef<string | null>(null);
  const seenRef = useRef<Set<string>>(new Set());

  const poll = useCallback(async (initial = false) => {
    if (!workspace.token) return;
    setLoading((current) => current || initial);
    try {
      let cursor = cursorRef.current;
      let pageCount = 0;
      let received: WorkforceEvent[] = [];
      let hasMore = true;
      while (hasMore && pageCount < 5) {
        const params = new URLSearchParams({ limit: '100' });
        if (cursor) params.set('cursor', cursor);
        else params.set('latest', 'true');
        const response = await workspace.fetchWithAuth(
          `${workspace.apiUrl}/workforce/events?${params.toString()}`,
        );
        if (!response.ok) {
          setConnected(false);
          return;
        }
        const data = await response.json();
        const page = Array.isArray(data.items) ? data.items as WorkforceEvent[] : [];
        received = received.concat(page);
        cursor = typeof data.next_cursor === 'string' ? data.next_cursor : cursor;
        hasMore = Boolean(data.has_more);
        pageCount += 1;
        if (page.length === 0) hasMore = false;
      }
      if (cursor) cursorRef.current = cursor;
      if (received.length) {
        const unique = received.filter((event) => {
          if (seenRef.current.has(event.id)) return false;
          seenRef.current.add(event.id);
          return true;
        });
        if (unique.length) setEvents((current) => [...current, ...unique].slice(-40));
        // Bound memory during long-running workspaces.
        if (seenRef.current.size > 2000) {
          seenRef.current = new Set(received.slice(-200).map((event) => event.id));
        }
      }
      setConnected(true);
    } catch {
      setConnected(false);
    } finally {
      setLoading(false);
    }
  }, [workspace.apiUrl, workspace.fetchWithAuth, workspace.token]);

  useEffect(() => {
    if (!workspace.token) return;
    void poll(true);
    const interval = window.setInterval(() => void poll(false), 5000);
    return () => window.clearInterval(interval);
  }, [workspace.token, poll]);

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Workforce activity"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="relative inline-flex h-9 items-center gap-2 rounded-md border border-border px-2.5 text-sm hover:bg-muted"
      >
        <Activity className="size-4" />
        <span className="hidden md:inline">Activity</span>
        <Circle className={`size-2 fill-current ${connected ? 'text-emerald-500' : 'text-muted-foreground'}`} />
        {events.length > 0 && (
          <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-primary/10 px-1 text-[10px] font-semibold text-primary">
            {events.length}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-50 w-[min(92vw,420px)] overflow-hidden rounded-xl border border-border bg-card shadow-xl">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div>
              <p className="text-sm font-semibold">Workforce activity</p>
              <p className="text-xs text-muted-foreground">
                {connected ? 'Connected · updates every 5 seconds' : 'Reconnecting to event stream'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => void poll(false)}
              disabled={loading}
              className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
              aria-label="Refresh activity"
            >
              <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="max-h-[min(65vh,520px)] overflow-y-auto">
            {events.length === 0 ? (
              <div className="px-4 py-10 text-center">
                <Activity className="mx-auto mb-2 size-6 text-muted-foreground" />
                <p className="text-sm font-medium">No activity yet</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Task and agent lifecycle events will appear here when emitted by the runtime.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {[...events].reverse().map((event) => (
                  <li key={event.id} className="px-4 py-3">
                    <div className="flex items-start gap-3">
                      <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" />
                      <div className="min-w-0 flex-1">
                        <p className="break-words text-xs font-semibold">{event.event_type.replaceAll('.', ' ')}</p>
                        <p className="mt-1 break-words text-xs leading-5 text-muted-foreground">{eventSummary(event)}</p>
                        <div className="mt-1.5 flex flex-wrap gap-x-3 text-[10px] text-muted-foreground">
                          {event.run_id ? <span>Run {event.run_id.slice(0, 12)}</span> : null}
                          {event.created_at ? <time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString()}</time> : null}
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="border-t border-border px-4 py-2 text-[10px] text-muted-foreground">
            Showing the latest {events.length} events available to your organization.
          </div>
        </div>
      )}
    </div>
  );
}

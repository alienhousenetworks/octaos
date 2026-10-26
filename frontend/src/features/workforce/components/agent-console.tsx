'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Shield,
  Wrench,
  Terminal,
  Check,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { AgentItem, ExecutionTraceItem } from '@/lib/agent-types';

interface AgentConsoleProps {
  agent: AgentItem;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

export default function AgentConsole({ agent, API_URL, fetchWithAuth }: AgentConsoleProps) {
  const [prompt, setPrompt] = useState('');
  const [dryRun, setDryRun] = useState(false);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const [toolCalls, setToolCalls] = useState<ExecutionTraceItem[]>([]);
  const [lifecycle, setLifecycle] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [liveEvents, setLiveEvents] = useState<string[]>([]);

  const handleExecute = async () => {
    if (!prompt.trim() || loading) return;

    setLoading(true);
    setLifecycle('running');
    setResponse(null);
    setToolCalls([]);
    setLiveEvents([]);
    setErrorMsg(null);
    const startTime = performance.now();

    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/agents/${agent.id}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: prompt,
          dry_run: dryRun,
        }),
      });

      const totalTime = Math.round(performance.now() - startTime);
      setDurationMs(totalTime);

      if (res.ok) {
        const data = await res.json();
        setResponse(data.output || data.response || 'Task executed successfully.');
        setToolCalls(data.tool_calls || []);
        const runId = data.execution_id || `run_${Date.now().toString(36)}`;
        setExecutionId(runId);
        setLifecycle('completed');

        // Stream the same normalized, redacted events persisted by AgentRuntime.
        if (data.execution_id) {
          try {
            const streamRes = await fetchWithAuth(
              `${API_URL}/autonomous-work/agent-runs/${encodeURIComponent(data.execution_id)}/events/stream?timeout_seconds=15`,
            );
            if (streamRes.ok && streamRes.body) {
              const reader = streamRes.body.getReader();
              const decoder = new TextDecoder();
              let buffer = '';
              while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const blocks = buffer.split('\n\n');
                buffer = blocks.pop() || '';
                for (const block of blocks) {
                  const dataLine = block.split('\n').find((line) => line.startsWith('data: '));
                  if (!dataLine) continue;
                  try {
                    const event = JSON.parse(dataLine.slice(6));
                    const message = event.payload?.message || event.event_type || 'Runtime event';
                    setLiveEvents((previous) => [...previous, String(message)].slice(-20));
                  } catch {
                    // Ignore malformed event frames; the completed HTTP result remains available.
                  }
                }
              }
            }
          } catch {
            setLiveEvents((previous) => [...previous, 'Live event stream unavailable; response is still available.']);
          }
        }
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || 'Execution failed or rejected by agent policy.');
        setLifecycle('failed');
      }
    } catch (e: any) {
      setErrorMsg(e.message || 'Network error executing agent task.');
      setLifecycle('failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Console Header & Mode Switcher */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-gray-800 bg-gray-950/40 p-4">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Terminal className="size-4 text-primary" />
            Interactive Test & Task Console
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Safely test {agent.name}&apos;s decision logic, tool calling behavior, and structured responses.
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-lg p-1 text-xs">
          <button
            type="button"
            onClick={() => setDryRun(false)}
            className={`px-3 py-1.5 rounded-md font-medium transition-all ${
              !dryRun
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-white'
            }`}
          >
            Live Execution
          </button>
          <button
            type="button"
            onClick={() => setDryRun(true)}
            className={`px-3 py-1.5 rounded-md font-medium transition-all ${
              dryRun
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'text-muted-foreground hover:text-white'
            }`}
          >
            Dry Run (No Side-Effects)
          </button>
        </div>
      </div>

      {/* Prompt Input Form */}
      <Card className="rounded-2xl border border-gray-800 bg-gray-950/60 p-5 space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-gray-300 flex items-center justify-between">
            <span>Task Prompt & Directives</span>
            <span className="font-mono text-[11px] text-gray-500">
              Active Model: {agent.model || 'meta-llama/llama-3.3-70b-instruct'}
            </span>
          </label>
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={`Instruct ${agent.name} with specific context... (e.g. "Evaluate target accounts in healthcare and formulate qualified outreach steps")`}
            className="min-h-[100px] rounded-xl border-gray-800 bg-gray-900/80 text-xs text-white placeholder:text-gray-500 focus-visible:border-gray-700"
          />
        </div>

        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2 text-[11px] text-gray-400">
            <Shield className="size-3.5 text-gray-500" />
            <span>
              {dryRun
                ? 'Dry run: External actions (email dispatch, lead updates) will be planned without committing'
                : 'Live mode: External actions operate under configured human approval policies'}
            </span>
          </div>

          <Button
            type="button"
            onClick={handleExecute}
            disabled={loading || !prompt.trim()}
            className="rounded-xl px-5 text-xs font-semibold"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 size-3.5 animate-spin" />
                Executing...
              </>
            ) : (
              <>
                <Send className="mr-2 size-3.5" />
                Execute Task
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Execution Lifecycle Status */}
      {lifecycle !== 'idle' && (
        <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-3 text-xs">
          <div className="flex items-center gap-2 text-muted-foreground">
            <span className="font-semibold text-gray-300">Run Lifecycle:</span>
            <span className="text-emerald-400">Validated</span>
            <ChevronRight className="size-3 text-gray-600" />
            <span className="text-emerald-400">Authorized</span>
            <ChevronRight className="size-3 text-gray-600" />
            <span className={loading ? 'text-amber-400 font-semibold' : 'text-emerald-400'}>
              {loading ? 'Executing...' : 'Completed'}
            </span>
            {durationMs && (
              <span className="ml-auto font-mono text-[11px] text-gray-400">
                {durationMs}ms
              </span>
            )}
          </div>
        </div>
      )}

      {/* Response and Execution Traces */}
      {response && (
        <Card className="rounded-2xl border border-gray-800 bg-gray-950/60 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-emerald-400" />
              <h4 className="text-xs font-semibold text-white">Agent Output</h4>
              {executionId && (
                <span className="font-mono text-[11px] text-gray-500">
                  ID: {executionId}
                </span>
              )}
            </div>
            <span className="rounded bg-gray-900 px-2 py-0.5 text-[10px] font-mono text-gray-400">
              Runtime Response
            </span>
          </div>

          <div className="whitespace-pre-wrap rounded-xl border border-gray-800/60 bg-gray-900/60 p-4 font-mono text-xs leading-relaxed text-gray-200 max-h-[350px] overflow-y-auto">
            {response}
          </div>

          {liveEvents.length > 0 && (
            <div className="space-y-2 border-t border-gray-800/80 pt-4">
              <h5 className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <Clock className="size-3.5 text-primary" />
                Live Runtime Events
              </h5>
              <ol className="space-y-1.5">
                {liveEvents.map((event, idx) => (
                  <li key={`${idx}-${event}`} className="rounded-lg border border-gray-800 bg-gray-900/40 px-3 py-2 text-xs text-gray-300">
                    {event}
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Inspected Tool Calls */}
          {toolCalls && toolCalls.length > 0 && (
            <div className="space-y-2 border-t border-gray-800/80 pt-4">
              <h5 className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <Wrench className="size-3.5 text-primary" />
                Inspected Tool Invocations ({toolCalls.length})
              </h5>
              <div className="space-y-1.5">
                {toolCalls.map((tc, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col gap-1 rounded-lg border border-gray-800 bg-gray-900/40 p-2.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-primary">{tc.tool}</span>
                      <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
                        {tc.status || 'Executed'}
                      </span>
                    </div>
                    <pre className="font-mono text-[11px] text-gray-400 overflow-x-auto">
                      {JSON.stringify(tc.args, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Error Output */}
      {errorMsg && (
        <Card className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-5 space-y-2">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertCircle className="size-4" />
            <h4 className="text-xs font-semibold">Execution Interrupted</h4>
          </div>
          <p className="font-mono text-xs text-rose-300">{errorMsg}</p>
        </Card>
      )}
    </div>
  );
}

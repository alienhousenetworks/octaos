'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useWorkspace } from '@/lib/workspace';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Bot, ArrowUp, Paperclip, ShieldCheck, Network, Database, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { createId } from '@/lib/id';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  result?: unknown;
};

const WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  createdAt: new Date(0).toISOString(),
  content: "I'm OctaOS. Choose a specialist from the sidebar or tell me the outcome you want. I'll check available company context, ask about important gaps, prepare a plan, and report what the connected systems actually do.",
};

function formatResult(value: any): string {
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object') return String(value ?? 'No result details were returned.');
  const direct = value.message || value.summary || value.answer || value.explanation;
  if (typeof direct === 'string' && direct.trim()) return direct;
  const parts: string[] = [];
  if (value.status) parts.push('Status: ' + value.status);
  if (Array.isArray(value.tasks)) {
    parts.push(...value.tasks.map((task: any, index: number) =>
      (index + 1) + '. ' + (task.title || task.name || task.description || 'Task') + (task.status ? ' — ' + task.status : '')
    ));
  }
  if (Array.isArray(value.results)) {
    parts.push(...value.results.map((item: any) =>
      typeof item === 'string' ? item : item.message || item.summary || JSON.stringify(item)
    ));
  }
  if (value.plan && typeof value.plan === 'object') parts.push('Plan:\n' + JSON.stringify(value.plan, null, 2));
  if (parts.length) return parts.join('\n\n');
  return JSON.stringify(value, null, 2);
}

export default function UniversalAssistantView() {
  const workspace = useWorkspace();
  const tenantKey = String(workspace.tenantId || 'default');
  const storageKey = 'octaos-universal-assistant-messages:' + tenantKey;
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [loadedTenant, setLoadedTenant] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const draftRef = useRef('');
  const sendingRef = useRef(false);

  useEffect(() => {
    setLoadedTenant(null);
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        setMessages(Array.isArray(parsed) && parsed.length ? parsed : [WELCOME]);
      } else {
        setMessages([WELCOME]);
      }
    } catch {
      setMessages([WELCOME]);
    }
    setLoadedTenant(tenantKey);
  }, [storageKey, tenantKey]);

  useEffect(() => {
    if (loadedTenant !== tenantKey) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(messages.slice(-100)));
    } catch { /* Storage can be unavailable or full; conversation still works in memory. */ }
  }, [messages, loadedTenant, storageKey, tenantKey]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, busy]);

  const send = async (text?: string) => {
    const goal = (text ?? draftRef.current ?? input).trim();
    if (!goal || busy || sendingRef.current) return;
    sendingRef.current = true;
    draftRef.current = '';
    const userMessage: ChatMessage = {
      id: createId(), role: 'user', content: goal, createdAt: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage]);
    setInput('');
    setError('');
    setBusy(true);
    try {
      const history = messages
        .filter((message) => message.id !== 'welcome' && message.content.trim())
        .slice(-8)
        .map((message) => ({
          role: message.role === 'user' ? 'user' : 'assistant',
          content: message.content.trim(),
        }));
      const response = await workspace.fetchWithAuth(workspace.apiUrl + '/orchestrator/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal,
          risk_level: 'NORMAL',
          ...(history.length ? { messages: history } : {}),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body?.detail === 'string' ? body.detail : 'Request failed (' + response.status + ').';
        throw new Error(detail);
      }
      const resultMessage: ChatMessage = {
        id: createId(),
        role: 'assistant',
        content: formatResult(body),
        createdAt: new Date().toISOString(),
        result: body,
      };
      setMessages((current) => [...current, resultMessage]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'The request could not be completed.';
      setError(message);
      setMessages((current) => [...current, {
        id: createId(),
        role: 'assistant',
        content: "I couldn't complete the orchestration request. No successful execution is being claimed. Please review the connection or try again. Details: " + message,
        createdAt: new Date().toISOString(),
      }]);
    } finally {
      sendingRef.current = false;
      setBusy(false);
    }
  };

  const suggestions = [
    'Find suitable companies for our services and prepare a lead research plan.',
    'Review our company knowledge and tell me which important information is missing or stale.',
    'Plan a marketing campaign using our approved brand and product information.',
  ];

  return (
    <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-[#7de56b]/20 bg-[#7de56b]/10 px-3 py-1 text-xs font-medium text-[#9af18b]">
            <Bot className="size-3.5" /> OctaOS AI Workforce
          </div>
          <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">What would you like to get done?</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-white/50">
            Work with your specialist bots through one conversation. OctaOS can plan work, use available company context and coordinate supported capabilities. External actions remain subject to permissions and approval.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => {
          setMessages([WELCOME]);
          setError('');
          try { localStorage.removeItem(storageKey); } catch { /* optional */ }
        }}>New conversation</Button>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/[0.09] bg-[#131714] p-3">
          <Database className="mb-2 size-4 text-[#8be977]" />
          <p className="text-sm font-medium">Company knowledge</p>
          <p className="mt-1 text-xs leading-5 text-white/50">Use authorized business information and flag missing details.</p>
        </div>
        <div className="rounded-xl border border-white/[0.09] bg-[#131714] p-3">
          <Network className="mb-2 size-4 text-[#8be977]" />
          <p className="text-sm font-medium">Collaborative bots</p>
          <p className="mt-1 text-xs leading-5 text-white/50">Coordinate specialist capabilities when supported by the runtime.</p>
        </div>
        <div className="rounded-xl border border-white/[0.09] bg-[#131714] p-3">
          <ShieldCheck className="mb-2 size-4 text-[#8be977]" />
          <p className="text-sm font-medium">Governed execution</p>
          <p className="mt-1 text-xs leading-5 text-white/50">Review plans and respect the authorization required for each action.</p>
        </div>
      </div>

      <section aria-label="Conversation" className="flex-1 space-y-4 rounded-2xl border border-white/[0.09] bg-[#101311] p-4 md:p-6">
        {messages.map((message) => (
          <div key={message.id} className={'flex ' + (message.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div className={'max-w-[92%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 md:max-w-[82%] ' + (message.role === 'user' ? 'border border-[#7de56b]/15 bg-[#243a25] text-[#f2f7f0]' : 'border border-white/[0.09] bg-[#1a1e1b] text-[#edf1ec]')}>
              {message.role !== 'user' && <div className="mb-1.5 flex items-center gap-2 text-xs font-semibold text-white/50"><Bot className="size-3.5" /> OctaOS</div>}
              {message.content}
              {message.result !== undefined && (
                <details className="mt-3 border-t border-white/10 pt-2">
                  <summary className="cursor-pointer text-xs font-medium text-white/50">Inspect execution response</summary>
                  <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-black/30 p-3 text-xs leading-5">{JSON.stringify(message.result, null, 2)}</pre>
                </details>
              )}
            </div>
          </div>
        ))}
        {busy && <div className="flex items-center gap-2 text-sm text-white/50"><Loader2 className="size-4 animate-spin" /> OctaOS is processing your request…</div>}
        {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm"><AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" /><span>{error}</span></div>}
        {!busy && messages.length <= 1 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {suggestions.map((suggestion) => <button key={suggestion} type="button" onClick={() => void send(suggestion)} className="rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2 text-left text-xs leading-5 text-white/60 transition-colors hover:bg-white/[0.07] hover:text-white">{suggestion}</button>)}
          </div>
        )}
        <div ref={endRef} />
      </section>

      <form className="mt-3 rounded-2xl border border-white/[0.1] bg-[#131714] p-2 shadow-sm" onSubmit={(event) => {
        event.preventDefault();
        const field = event.currentTarget.querySelector('textarea');
        void send(field?.value || draftRef.current);
      }}>
        <Textarea
          ref={inputRef}
          value={input}
          onChange={(event) => {
            draftRef.current = event.target.value;
            setInput(event.target.value);
          }}
          placeholder="Describe the outcome you want. Include the target, constraints, and what a good result looks like…"
          className="min-h-[76px] resize-y border-0 bg-transparent text-[#f2f5f1] shadow-none placeholder:text-white/35 focus-visible:ring-0"
          disabled={busy}
          aria-label="Message OctaOS"
        />
        <div className="flex items-center justify-between gap-2 px-2 pb-1">
          <div className="flex items-center gap-2 text-xs text-white/50"><Paperclip className="size-3.5" /> Attachments and specialist selection remain available in their existing workspaces.</div>
          <Button type="submit" size="sm" disabled={busy || !input.trim()} onClick={(event) => {
            event.preventDefault();
            const field = event.currentTarget.closest('form')?.querySelector('textarea');
            void send(field?.value || draftRef.current);
          }}><ArrowUp className="mr-1 size-4" /> {busy ? 'Working…' : 'Send'}</Button>
        </div>
      </form>
      <p className="mt-2 flex items-center justify-center gap-1.5 text-center text-[11px] text-white/50"><CheckCircle2 className="size-3" /> Results reflect the orchestration response; verify approvals and external outcomes before treating work as complete.</p>
    </div>
  );
}

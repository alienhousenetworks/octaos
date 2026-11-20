'use client';

import React, { useEffect, useRef, useState, useTransition } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useWorkspace } from '@/lib/workspace';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Bot,
  ArrowUp,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Search,
  Sparkles,
  MessageSquare,
  LayoutDashboard,
  ChevronRight,
  RefreshCw,
  Wrench,
  Copy,
  Check,
  Share2,
  Calendar,
  RotateCw,
  ThumbsUp,
  Image as ImageIcon,
  ExternalLink,
  Hash,
  Clock,
  Cpu,
  Layers,
  Activity,
  Maximize2,
  Minimize2,
  Send,
  Zap,
  Trash2,
  Download,
  BookOpen,
  Plug,
} from 'lucide-react';
import { createId } from '@/lib/id';
import { AgentItem } from '@/lib/agent-types';
import { SECTION_AGENT_SLUG, sectionAssistant, useInterfaceMode } from '@/lib/interface-mode';
import LiveThinkingTrace from '@/components/agent-studio/live-thinking-trace';
import LiveToolPill, { ToolExecutionItem } from '@/components/agent-studio/live-tool-pill';
import LiveApprovalCard, { ApprovalRequiredData } from '@/components/agent-studio/live-approval-modal';
import AgentWorkbenchPanel, { ArtifactItem } from '@/components/agent-studio/agent-workbench-panel';
import { HanddrawnLoopDiagram } from '@/components/handdraw/handdraw-illustrations';

function threadIdFor(storageKey: string): string {
  const key = `${storageKey}:thread-id`;
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;
  const created = createId();
  window.localStorage.setItem(key, created);
  return created;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thought?: string;
  tools?: ToolExecutionItem[];
  pendingApproval?: ApprovalRequiredData;
  isStreaming?: boolean;
  createdAt: string;
  result?: unknown;
  agentName?: string;
  actionArtifact?: any;
}

const SUGGESTIONS: Record<string, string[]> = {
  general: [
    'Research high-value B2B SaaS accounts and summarize target buyers.',
    'Review company knowledge and list any missing or stale policies.',
    'Plan a multi-channel campaign with tone and target personas.',
  ],
  sales: [
    'Find 5 qualified SaaS target companies and prepare an outreach draft.',
    'Review the open pipeline and name the highest priority account to work.',
    'Generate customized cold outreach copy tailored to our value proposition.',
  ],
  marketing: [
    'Draft an engaging LinkedIn announcement with image concept and hashtags.',
    'Propose three product-focused Instagram posts matching our brand voice.',
    'Analyze marketing campaign performance and suggest conversion improvements.',
  ],
  support: [
    'Summarize recent unresolved customer inquiries and prioritize urgent items.',
    'Identify common recurring questions missing from our documentation.',
    'Draft an empathetic troubleshooting response for a system outage.',
  ],
  hr: [
    'Draft a job spec for a Senior Fullstack Engineer based on company standards.',
    'Prepare an onboarding checklist for new engineering hires.',
    'Review current hiring pipeline stages and highlight bottlenecks.',
  ],
  people: [
    'Draft an onboarding checklist for incoming engineering hires.',
    'Summarize weekly HR action items and policy review dates.',
    'Review employee leave requests and team coverage balance.',
  ],
  hiring: [
    'Draft candidate screening questions for an AI Systems Architect role.',
    'Summarize shortlisted applicant qualifications against role requirements.',
    'Prepare an interview evaluation scorecard for hiring managers.',
  ],
  ceo: [
    'Turn our quarterly strategic targets into a departmental execution plan.',
    'Synthesize cross-departmental throughput across Sales, Marketing, and Support.',
    'Identify the top resource constraints threatening our delivery timeline.',
  ],
};

const WELCOME_PROMPT =
  "I'm OctaOS AI Workstation. Select a specialist or describe your goal. I'll execute tools, stream reasoning, formulate artifacts, and report real results.";

function visibleAssistantText(text: string): string {
  return (text || '')
    .replace(/```json[\s\S]*?```/g, '')
    .replace(/\{\s*"tool"[\s\S]*?\}/g, '')
    .trim();
}

function extractActionArtifact(result: any, content: string): any {
  if (result?.action_artifact) return result.action_artifact;
  if (Array.isArray(result?.tool_calls)) {
    for (const tc of result.tool_calls) {
      if (tc?.result?.post_id || tc?.result?.image_url) return tc.result;
      if (tc?.result?.lead_id) return tc.result;
      if (tc?.result?.ticket_id) return tc.result;
      if (tc?.result?.connector_required || tc?.result?.connector) return tc.result;
    }
  }
  if (Array.isArray(result?.results)) {
    for (const r of result.results) {
      if (r?.post_id || r?.connector_required || r?.connector) return r;
    }
  }
  if (result?.post_id || result?.connector_required || result?.connector) return result;

  const imgMatch = (content || '').match(/!\[.*?\]\((https?:\/\/[^\s\)]+)\)/);
  const hashtagMatches = (content || '').match(/#[a-zA-Z0-9_]+/g);
  if (imgMatch) {
    const namedPlatform = (content || '').match(/\b(linkedin|instagram|facebook)\b/i);
    return {
      platform: namedPlatform ? namedPlatform[1].toLowerCase() : 'image',
      image_url: imgMatch[1],
      caption: (content || '').split('\n\n')[0].replace(/!\[.*?\]\(.*?\)/g, '').replace(/#.*/g, '').trim(),
      hashtags: hashtagMatches || [],
      status: 'draft',
      approval_status: 'pending',
    };
  }
  return null;
}

function AgentActionCard({
  artifact,
  workspace,
  onQuickPrompt,
}: {
  artifact: any;
  workspace: ReturnType<typeof useWorkspace>;
  onQuickPrompt?: (prompt: string) => void;
}) {
  const [copied, setCopied] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string>(artifact?.status || 'draft');
  const [currentApproval, setCurrentApproval] = useState<string>(artifact?.approval_status || 'pending');
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const platform = String(artifact?.platform || 'general').toLowerCase();
  const caption = String(artifact?.caption || artifact?.content || '').replace(/#[a-zA-Z0-9_]+/g, '').trim();
  const hashtags: string[] = Array.isArray(artifact?.hashtags)
    ? artifact.hashtags
    : typeof artifact?.hashtags === 'string'
      ? artifact.hashtags.split(/\s+/)
      : [];

  const handleCopy = () => {
    const fullText = [caption, hashtags.join(' ')].filter(Boolean).join('\n\n');
    navigator.clipboard.writeText(fullText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handlePublishNow = async () => {
    if (!artifact?.post_id) {
      setFeedback('Draft noted. Open in Campaign Studio to schedule.');
      return;
    }
    setBusyAction('publishing');
    setFeedback(null);
    try {
      const res = await workspace.fetchWithAuth(
        `${workspace.apiUrl}/marketing/posts/${encodeURIComponent(artifact.post_id)}/publish-now`,
        { method: 'POST' }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || `Publish failed (${res.status})`);
      }
      setCurrentStatus('published');
      setCurrentApproval('approved');
      setFeedback(`Successfully published to ${platform.toUpperCase()}!`);
    } catch (err: any) {
      setFeedback(err?.message || 'Failed to publish post.');
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-white/[0.08] bg-[#171e26] p-4 text-xs shadow-md">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <span className="flex size-2 rounded-full bg-[#e5a93c]" />
          <span className="font-semibold uppercase tracking-wider text-white/90">
            {platform} Action Artifact
          </span>
        </div>
        <span className="rounded bg-white/[0.06] px-2 py-0.5 text-[10px] uppercase font-mono text-white/60">
          {currentStatus}
        </span>
      </div>

      {artifact.image_url && (
        <div className="mb-3 overflow-hidden rounded-lg border border-white/10 bg-black/40">
          <img
            src={artifact.image_url}
            alt="Generated preview"
            className="h-44 w-full object-cover"
          />
        </div>
      )}

      {caption && (
        <p className="mb-2 leading-relaxed text-white/80 whitespace-pre-wrap">{caption}</p>
      )}

      {hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {hashtags.map((ht: string, i: number) => (
            <span key={i} className="text-[#2dd4bf] font-mono text-[11px]">
              {ht.startsWith('#') ? ht : `#${ht}`}
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="h-7 gap-1 border-white/10 bg-white/[0.04] text-xs text-white/70 hover:bg-white/[0.08] hover:text-white"
          >
            {copied ? <Check className="size-3 text-[#2dd4bf]" /> : <Copy className="size-3" />}
            {copied ? 'Copied' : 'Copy Text'}
          </Button>

          {artifact.post_id && currentStatus !== 'published' && (
            <Button
              type="button"
              size="sm"
              onClick={handlePublishNow}
              disabled={Boolean(busyAction)}
              className="h-7 gap-1 bg-[#e5a93c] px-3 text-xs font-semibold text-black hover:bg-[#2dd4bf]"
            >
              {busyAction === 'publishing' ? <Loader2 className="size-3 animate-spin" /> : <Send className="size-3" />}
              Publish Now
            </Button>
          )}
        </div>

        {feedback && (
          <span className="text-[11px] text-[#2dd4bf] font-medium animate-fade-in">{feedback}</span>
        )}
      </div>
    </div>
  );
}

export default function UniversalAssistantView({
  scope = 'general',
  title,
}: {
  scope?: string;
  title?: string;
}) {
  const workspace = useWorkspace();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { setMode } = useInterfaceMode();

  const requestedAgent = searchParams.get('agent') || '';
  const tenantKey = String(workspace.tenantId || 'default');

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState('');

  // Workbench Side-Panel State
  const [workbenchOpen, setWorkbenchOpen] = useState(false);
  const [workbenchTab, setWorkbenchTab] = useState<'telemetry' | 'artifacts' | 'integrations' | 'context'>('telemetry');
  const [sessionTools, setSessionTools] = useState<ToolExecutionItem[]>([]);
  const [sessionArtifacts, setSessionArtifacts] = useState<ArtifactItem[]>([]);

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const draftRef = useRef('');
  const abortControllerRef = useRef<AbortController | null>(null);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) || null;
  const currentScope = selectedAgent?.department?.toLowerCase() || scope || 'general';

  // Persistence Key
  const threadKey = requestedAgent === 'orchestrator'
    ? 'orchestrator'
    : (selectedAgent?.slug || SECTION_AGENT_SLUG[scope] || scope || 'general');
  const storageKey = `octaos-assistant-thread:${tenantKey}:${threadKey}`;

  // 1. Fetch Agents Catalogue
  useEffect(() => {
    if (!workspace.token) return;
    let active = true;
    setAgentsLoading(true);
    workspace
      .fetchWithAuth(`${workspace.apiUrl}/dashboard/agents`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Agent catalogue error (${res.status})`);
        const data = await res.json();
        if (!active) return;
        setAgents(Array.isArray(data) ? (data as AgentItem[]) : []);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setAgentsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [workspace.token, workspace.apiUrl, workspace.fetchWithAuth]);

  // 2. Resolve Active Agent from Query or Scope
  useEffect(() => {
    if (!agents.length) return;
    if (requestedAgent === 'orchestrator') {
      setSelectedAgentId('');
      return;
    }
    if (requestedAgent) {
      const match = agents.find((a) => a.id === requestedAgent || a.slug === requestedAgent);
      if (match) {
        setSelectedAgentId(match.id);
        return;
      }
    }
    const slug = SECTION_AGENT_SLUG[scope];
    const scoped = slug ? agents.find((a) => a.slug === slug) : null;
    setSelectedAgentId(scoped?.id || '');
  }, [agents, requestedAgent, scope]);

  // 3. Load Thread Messages
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed.map((m: ChatMessage) => ({ ...m, isStreaming: false })));
          // Restore tools and artifacts from loaded messages
          const restoredTools: ToolExecutionItem[] = [];
          const restoredArtifacts: ArtifactItem[] = [];
          parsed.forEach((m: ChatMessage) => {
            if (m.tools) restoredTools.push(...m.tools);
            if (m.actionArtifact) {
              restoredArtifacts.push({
                id: m.id,
                title: m.actionArtifact.platform || m.actionArtifact.title || 'Generated Output',
                type: 'document',
                content: m.actionArtifact,
                createdAt: m.createdAt,
              });
            }
          });
          setSessionTools(restoredTools);
          setSessionArtifacts(restoredArtifacts);
          return;
        }
      }
    } catch {
      // Fallback
    }

    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: WELCOME_PROMPT,
        createdAt: new Date().toISOString(),
        agentName: selectedAgent?.name || 'OctaOS Specialist',
      },
    ]);
  }, [storageKey]);

  // 4. Save Thread Messages
  useEffect(() => {
    if (!messages.length) return;
    try {
      const persisted = messages.slice(-50).map((m) => ({ ...m, isStreaming: false }));
      localStorage.setItem(storageKey, JSON.stringify(persisted));
    } catch {
      // Ignore storage errors
    }
  }, [messages, storageKey]);

  // Auto-scroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, busy]);

  const selectAgent = (id: string) => {
    setSelectedAgentId(id);
    const agent = agents.find((a) => a.id === id);
    const params = new URLSearchParams(searchParams.toString());
    params.set('agent', agent ? agent.slug || agent.id : 'orchestrator');
    router.replace(`${pathname}?${params.toString()}`);
  };

  const handleClearThread = () => {
    const welcomeMsg: ChatMessage = {
      id: createId(),
      role: 'assistant',
      content: `Session reset. Ready for your next command as ${selectedAgent?.name || 'OctaOS Specialist'}.`,
      createdAt: new Date().toISOString(),
      agentName: selectedAgent?.name || 'OctaOS Specialist',
    };
    setMessages([welcomeMsg]);
    setSessionTools([]);
    setSessionArtifacts([]);
    localStorage.removeItem(storageKey);
    localStorage.removeItem(`${storageKey}:thread-id`);
  };

  const exportConversation = () => {
    const exportText = messages
      .map(
        (m) =>
          `[${m.role.toUpperCase()} - ${m.agentName || 'User'} (${new Date(m.createdAt).toLocaleTimeString()})]\n${
            m.thought ? `Reasoning:\n${m.thought}\n\n` : ''
          }${m.content}\n`
      )
      .join('\n---\n\n');

    const blob = new Blob([exportText], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `octaos_session_${threadKey}_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // SEND PROMPT WITH SSE STREAMING (Fallback to Orchestrator)
  const send = async (explicitText?: string) => {
    const promptText = (explicitText ?? draftRef.current ?? input).trim();
    if (!promptText || busy) return;

    setInput('');
    draftRef.current = '';
    setError('');
    setBusy(true);

    const speaker = selectedAgent?.name || 'OctaOS Workstation';
    const userMsgId = createId();
    const assistantMsgId = createId();

    const userMessage: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: promptText,
      createdAt: new Date().toISOString(),
    };

    const initialAssistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      thought: '',
      tools: [],
      isStreaming: true,
      createdAt: new Date().toISOString(),
      agentName: speaker,
    };

    setMessages((prev) => [...prev, userMessage, initialAssistantMsg]);

    const abortCtrl = new AbortController();
    abortControllerRef.current = abortCtrl;

    const historyPayload = messages
      .filter((m) => m.id !== 'welcome' && m.content.trim())
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      // 1. Try real-time streaming endpoint
      const streamRes = await workspace.fetchWithAuth(`${workspace.apiUrl}/agents/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: promptText,
          agent_id: selectedAgent?.id || SECTION_AGENT_SLUG[scope] || SECTION_AGENT_SLUG[currentScope] || undefined,
          history: historyPayload,
          dry_run: false,
          thread_id: threadIdFor(storageKey),
        }),
        signal: abortCtrl.signal,
      });

      if (!streamRes.ok || !streamRes.body) {
        const failBody = await streamRes.json().catch(() => ({}));
        throw new Error(failBody?.detail || `Stream connection failed (${streamRes.status})`);
      }

      const reader = streamRes.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            const lines = part.trim().split('\n');
            let eventType = '';
            let dataStr = '';

            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith('data:')) {
                dataStr = line.slice(5).trim();
              }
            }

            if (!dataStr || dataStr === '[DONE]') continue;

            try {
              const eventPayload = JSON.parse(dataStr);
              const eventData = eventPayload.data || {};
              const resolvedType = eventType || eventPayload.event || '';

              setMessages((prev) =>
                prev.map((msg) => {
                  if (msg.id !== assistantMsgId) return msg;

                  let newThought = msg.thought || '';
                  let newContent = msg.content || '';
                  let newTools = [...(msg.tools || [])];
                  let pendingApproval = msg.pendingApproval;

                  if (resolvedType === 'thinking_delta' || resolvedType === 'reasoning_delta') {
                    const t = eventData.thought || eventData.delta || '';
                    if (t) newThought += (newThought ? '\n' : '') + t;
                  } else if (resolvedType === 'content_delta' || resolvedType === 'token_delta') {
                    const delta = visibleAssistantText(eventData.delta || eventData.content || '');
                    if (delta) {
                      newContent += (newContent ? '\n\n' : '') + delta;
                    }
                  } else if (resolvedType === 'tool_call_started' || resolvedType === 'tool_called') {
                    const toolItem: ToolExecutionItem = {
                      tool: eventData.tool,
                      args: eventData.args,
                      status: 'running',
                    };
                    newTools.push(toolItem);
                    setSessionTools((st) => [...st, toolItem]);
                  } else if (resolvedType === 'tool_call_completed' || resolvedType === 'tool_result') {
                    newTools = newTools.map((t) =>
                      t.tool === eventData.tool && t.status === 'running'
                        ? { ...t, status: 'completed', result: eventData.result }
                        : t
                    );
                    setSessionTools((st) =>
                      st.map((t) =>
                        t.tool === eventData.tool && t.status === 'running'
                          ? { ...t, status: 'completed', result: eventData.result }
                          : t
                      )
                    );

                    // Add to session artifacts if artifact produced
                    if (eventData.result && typeof eventData.result === 'object') {
                      const art = extractActionArtifact(eventData.result, '');
                      if (art) {
                        const artifactItem: ArtifactItem = {
                          id: createId(),
                          title: `${eventData.tool} Output`,
                          type: 'document',
                          content: eventData.result,
                          createdAt: new Date().toISOString(),
                        };
                        setSessionArtifacts((sa) => [...sa, artifactItem]);
                      }
                    }
                  } else if (resolvedType === 'tool_call_failed') {
                    newTools = newTools.map((t) =>
                      t.tool === eventData.tool && t.status === 'running'
                        ? { ...t, status: 'failed', error: eventData.error }
                        : t
                    );
                    setSessionTools((st) =>
                      st.map((t) =>
                        t.tool === eventData.tool && t.status === 'running'
                          ? { ...t, status: 'failed', error: eventData.error }
                          : t
                      )
                    );
                  } else if (resolvedType === 'approval_required') {
                    pendingApproval = {
                      approval_id: eventData.approval_id,
                      checkpoint_id: eventData.checkpoint_id,
                      tool: eventData.tool,
                      args: eventData.args,
                      policy_reason: eventData.policy_reason,
                    };
                  } else if (resolvedType === 'run_failed') {
                    if (!newContent) {
                      newContent = `Execution issue: ${eventData.error || 'The model provider returned an error.'}`;
                    }
                  } else if (resolvedType === 'run_completed') {
                    const output = visibleAssistantText(
                      typeof eventData.output === 'string' ? eventData.output : ''
                    );
                    if (output && !newContent) {
                      newContent = output;
                    }
                  }

                  const turnFinished = resolvedType === 'run_completed' || resolvedType === 'run_failed' || resolvedType === 'approval_required';

                  return {
                    ...msg,
                    thought: newThought,
                    content: newContent,
                    tools: newTools,
                    pendingApproval,
                    isStreaming: turnFinished ? false : msg.isStreaming,
                  };
                })
              );
            } catch {
              // Parse error
            }
          }
        }

        // Finalize streaming state
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id !== assistantMsgId) return msg;

            let finalContent = msg.content || '';
            // Clean out pure raw json if emitted as content
            const cleaned = finalContent.replace(/```json[\s\S]*?```/g, '').replace(/\{\s*"tool"[\s\S]*?\}/g, '').trim();
            if (cleaned) {
              finalContent = cleaned;
            } else if (!finalContent.trim()) {
              if (msg.tools && msg.tools.length > 0) {
                finalContent = `Executed ${msg.tools.length} research step(s). You can inspect tool inputs and outputs in the Workbench Telemetry panel.`;
              } else {
                finalContent = 'The request was processed. Please state if you would like me to refine the plan.';
              }
            }

            const artifact = extractActionArtifact(null, finalContent);
            if (artifact?.image_url) {
              finalContent = finalContent.replace(/!\[[^\]]*\]\([^)]+\)/g, '').trim();
            }
            if (artifact) {
              setSessionArtifacts((sa) => [
                ...sa,
                {
                  id: createId(),
                  title: `${artifact.platform || 'Generated'} Content`,
                  type: 'post',
                  content: artifact,
                  createdAt: new Date().toISOString(),
                },
              ]);
            }
            return {
              ...msg,
              content: finalContent,
              isStreaming: false,
              actionArtifact: artifact,
            };
          })
        );
    } catch (err: any) {
      if (err.name === 'AbortError') return;
      setError(err?.message || 'Execution error');
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: `Command could not be completed: ${err?.message || 'Unknown network error'}.`,
                isStreaming: false,
              }
            : msg
        )
      );
    } finally {
      setBusy(false);
      abortControllerRef.current = null;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  const suggestions =
    SUGGESTIONS[currentScope] || SUGGESTIONS[scope] || SUGGESTIONS.general;

  return (
    <div className="ai-console flex h-full w-full min-h-0 overflow-hidden bg-[#0a0d10] text-white">
      {/* CENTER STAGE: AI COMMAND CONSOLE */}
      <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
        {/* Top Workstation Console Header */}
        <header className="ai-console-header flex h-14 shrink-0 items-center justify-between border-b border-white/[0.08] bg-[#0d1116] px-4 md:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex size-8 items-center justify-center rounded-lg border border-[#e5a93c]/30 bg-[#e5a93c]/15 text-[#2dd4bf]">
              <Bot className="size-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-xs font-semibold text-white/95">
                  {selectedAgent?.name || 'OctaOS General Orchestrator'}
                </h1>
                <span className="rounded bg-white/[0.06] px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-wider text-white/50">
                  {selectedAgent?.department || 'Executive'}
                </span>
                <span className="hidden sm:inline-flex items-center gap-1 rounded-full bg-[#e5a93c]/15 px-2 py-0.5 text-[10px] text-[#2dd4bf]">
                  <span className="size-1.5 rounded-full bg-[#e5a93c]" />
                  Ready
                </span>
              </div>
              <p className="truncate text-[10px] text-white/40">
                {selectedAgent?.model || 'Claude 3.5 Sonnet'} · Auto-tool dispatch · Enterprise governed
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Mode Switcher Pill */}
            <div
              role="group"
              aria-label="Interface Mode"
              className="inline-flex shrink-0 items-center rounded-lg border border-white/10 bg-white/[0.03] p-0.5"
            >
              <button
                type="button"
                className="h-6 rounded-md bg-[#e5a93c] px-2 text-[11px] font-semibold text-black"
                title="AI Workstation mode active"
              >
                AI
              </button>
              <button
                type="button"
                onClick={() => setMode('classic')}
                className="h-6 rounded-md px-2 text-[11px] text-white/60 hover:text-white transition"
                title="Switch to Classic Mode"
              >
                Classic
              </button>
            </div>

            {/* Clear Session */}
            <button
              type="button"
              onClick={handleClearThread}
              title="Reset conversation"
              className="flex size-7 items-center justify-center rounded-lg border border-white/10 text-white/50 hover:bg-white/[0.05] hover:text-white transition"
            >
              <Trash2 className="size-3.5" />
            </button>

            {/* Export Markdown */}
            <button
              type="button"
              onClick={exportConversation}
              title="Export session to Markdown"
              className="hidden sm:flex size-7 items-center justify-center rounded-lg border border-white/10 text-white/50 hover:bg-white/[0.05] hover:text-white transition"
            >
              <Download className="size-3.5" />
            </button>

            {/* Integrations Section Button */}
            <button
              type="button"
              onClick={() => {
                if (workbenchOpen && workbenchTab === 'integrations') {
                  setWorkbenchOpen(false);
                } else {
                  setWorkbenchTab('integrations');
                  setWorkbenchOpen(true);
                }
              }}
              className={`flex h-7 items-center gap-1.5 rounded-lg border px-2.5 text-xs transition font-medium ${
                workbenchOpen && workbenchTab === 'integrations'
                  ? 'border-[#e5a93c]/50 bg-[#e5a93c]/15 text-[#2dd4bf]'
                  : 'border-white/10 text-white/70 hover:bg-white/[0.05] hover:text-white'
              }`}
              title="View and configure connected integrations, API keys, and models"
            >
              <Plug className="size-3.5 text-[#2dd4bf]" />
              <span className="hidden sm:inline">Integrations</span>
            </button>

            {/* Workbench Side-Panel Toggle (Rakazo & OpenMausBot signature) */}
            <button
              type="button"
              onClick={() => {
                if (workbenchOpen && workbenchTab !== 'integrations') {
                  setWorkbenchOpen(false);
                } else {
                  setWorkbenchTab('telemetry');
                  setWorkbenchOpen(true);
                }
              }}
              className={`flex h-7 items-center gap-1.5 rounded-lg border px-2.5 text-xs transition font-medium ${
                workbenchOpen && workbenchTab !== 'integrations'
                  ? 'border-[#e5a93c]/50 bg-[#e5a93c]/15 text-[#2dd4bf]'
                  : 'border-white/10 text-white/70 hover:bg-white/[0.05] hover:text-white'
              }`}
            >
              <Cpu className="size-3.5" />
              <span className="hidden sm:inline">Workbench</span>
              {sessionTools.length > 0 && (
                <span className="rounded-full bg-[#e5a93c]/30 px-1 text-[9px] text-[#2dd4bf] font-mono">
                  {sessionTools.length}
                </span>
              )}
            </button>
          </div>
        </header>

        {/* Conversation Stream */}
        <div className="ai-conversation flex-1 min-h-0 overflow-y-auto px-4 py-5 md:px-8">
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((message) => {
              const isUser = message.role === 'user';
              return (
                <div
                  key={message.id}
                  className={`flex gap-3 text-xs leading-relaxed ${
                    isUser ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {!isUser && (
                    <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[#171e26] border border-white/10 text-[#2dd4bf]">
                      <Bot className="size-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl p-4 ${
                      isUser
                        ? 'bg-[#1b232c] text-white/95 border border-white/10 font-sans'
                        : 'bg-[#11161c] text-white/90 border border-white/[0.08]'
                    }`}
                  >
                    {!isUser && (
                      <div className="mb-2 flex items-center justify-between text-[10px] text-white/40">
                        <span className="font-semibold text-[#2dd4bf]">
                          {message.agentName || selectedAgent?.name || 'OctaOS'}
                        </span>
                        <span>{new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    )}

                    {/* LIVE THINKING REASONING TRACE */}
                    {message.thought && (
                      <LiveThinkingTrace thought={message.thought} isStreaming={message.isStreaming} />
                    )}

                    {/* LIVE TOOL EXECUTION PILLS */}
                    {message.tools && message.tools.length > 0 && (
                      <div className="my-2 space-y-1">
                        {message.tools.map((t, idx) => (
                          <LiveToolPill key={idx} item={t} />
                        ))}
                      </div>
                    )}

                    {/* HUMAN-IN-THE-LOOP APPROVAL BROKER */}
                    {message.pendingApproval && (
                      <LiveApprovalCard
                        data={message.pendingApproval}
                        apiUrl={workspace.apiUrl}
                        fetchWithAuth={workspace.fetchWithAuth}
                        onResolved={() => {
                          setMessages((prev) =>
                            prev.map((m) =>
                              m.id === message.id ? { ...m, pendingApproval: undefined } : m
                            )
                          );
                        }}
                      />
                    )}

                    {/* MESSAGE TEXT CONTENT */}
                    {message.content && (
                      <div className="prose prose-invert max-w-none text-xs leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </div>
                    )}

                    {/* STREAMING CURSOR */}
                    {message.isStreaming && !message.content && !message.thought && !(message.tools && message.tools.length) && (
                      <div className="flex items-center gap-2 text-[11px] text-[#2dd4bf]">
                        <Loader2 className="size-3.5 animate-spin" />
                        <span>Formulating plan and reasoning...</span>
                      </div>
                    )}

                    {/* ACTION ARTIFACT CARD */}
                    {message.actionArtifact && (
                      <AgentActionCard
                        artifact={message.actionArtifact}
                        workspace={workspace}
                        onQuickPrompt={(p) => void send(p)}
                      />
                    )}
                  </div>
                </div>
              );
            })}

            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-rose-500/20 bg-rose-950/20 p-3 text-xs text-rose-300">
                <AlertCircle className="size-4 shrink-0 mt-0.5 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            {/* EMPTY STATE / SUGGESTIONS */}
            {messages.length <= 1 && (
              <div className="pt-4">
                <div className="rounded-2xl border border-white/[0.08] bg-[#11161c] p-5 text-center">
                  <div className="mx-auto mb-3 flex size-10 items-center justify-center rounded-xl bg-[#e5a93c]/15 text-[#2dd4bf]">
                    <Sparkles className="size-5" />
                  </div>
                  <h3 className="text-sm font-semibold text-white/95">
                    What should {selectedAgent?.name || 'OctaOS'} execute?
                  </h3>
                  <p className="mx-auto mt-1 max-w-md text-xs text-white/45">
                    Autonomous multi-agent execution with tools, memory, live thinking, and enterprise safety gates.
                  </p>

                  <div className="mt-5 grid gap-2 sm:grid-cols-3 text-left">
                    {suggestions.map((s, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => void send(s)}
                        className="flex flex-col justify-between rounded-xl border border-white/[0.08] bg-white/[0.02] p-3 text-xs transition hover:border-[#e5a93c]/40 hover:bg-white/[0.05]"
                      >
                        <span className="text-white/80 leading-snug">{s}</span>
                        <span className="mt-2 text-[10px] text-[#2dd4bf] font-medium flex items-center gap-1">
                          Execute <ArrowUp className="size-3 rotate-45" />
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div ref={endRef} />
          </div>
        </div>

        {/* BOTTOM COMMAND DECK (Rakazo / OpenMausBot style) */}
        <div className="shrink-0 p-4 bg-[#0d1116] border-t border-white/[0.08]">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
            className="mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#171e26] p-2.5 transition focus-within:border-[#e5a93c]/50 shadow-xl"
          >
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                draftRef.current = e.target.value;
                setInput(e.target.value);
              }}
              onKeyDown={handleKeyDown}
              disabled={busy}
              placeholder={
                selectedAgent
                  ? `Message ${selectedAgent.name}... (Press Enter to execute, Shift+Enter for new line)`
                  : 'Instruct OctaOS to research, coordinate agents, write documents, or take actions...'
              }
              className="min-h-[64px] resize-none border-0 bg-transparent text-xs text-white placeholder:text-white/35 focus-visible:ring-0"
            />

            <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/[0.06] px-1">
              <div className="flex items-center gap-2 text-[11px] text-white/40">
                <span className="flex size-1.5 rounded-full bg-[#e5a93c]" />
                <span className="font-mono text-[10px]">
                  {selectedAgent ? `@${selectedAgent.slug || selectedAgent.name}` : '@orchestrator'}
                </span>
                <span className="hidden sm:inline">·</span>
                <span className="hidden sm:inline">Sandboxed Tools Active</span>
              </div>

              <div className="flex items-center gap-2">
                {busy ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => abortControllerRef.current?.abort()}
                    className="h-7 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs hover:bg-rose-500/30"
                  >
                    Stop
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!input.trim()}
                    className="h-7 gap-1.5 rounded-lg bg-[#e5a93c] px-3 text-xs font-semibold text-black hover:bg-[#2dd4bf] disabled:opacity-30 transition"
                  >
                    <span>Execute</span>
                    <ArrowUp className="size-3.5" />
                  </Button>
                )}
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* RIGHT STAGE: AGENT WORKBENCH / TELEMETRY PANEL */}
      <AgentWorkbenchPanel
        open={workbenchOpen}
        onClose={() => setWorkbenchOpen(false)}
        activeTab={workbenchTab}
        onTabChange={setWorkbenchTab}
        agent={selectedAgent}
        tools={sessionTools}
        artifacts={sessionArtifacts}
        environment={{
          model: selectedAgent?.model || 'claude-3-5-sonnet',
          provider: selectedAgent?.provider || 'Anthropic / In-House',
          status: busy ? 'executing' : 'online',
        }}
      />
    </div>
  );
}

'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Key,
  Trash2,
  Plus,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Eye,
  EyeOff,
  AlertTriangle,
  Zap,
  ChevronRight,
  Sparkles,
  Server,
  ShieldCheck,
  Search,
  ExternalLink,
  Bot,
  Share2,
  Mail,
  Radar,
  Briefcase,
  TrendingUp,
  Globe,
  Sliders,
  Check,
  Star,
  Loader2,
} from 'lucide-react';

interface ApiManagementViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  configuredProviders: string[];
  tenantId: string | null;
}

interface ProviderDef {
  id: string;
  label: string;
  category: string;
  hint: string;
  url: string;
  placeholder: string;
  description: string;
}

const PROVIDERS: ProviderDef[] = [
  // AI Models
  { id: 'openrouter', label: 'OpenRouter (Meta-Hub)', category: 'ai', hint: 'sk-or-v1-...', url: 'https://openrouter.ai/keys', placeholder: 'sk-or-v1-...', description: 'Unified gateway routing to Claude, Llama 3, DeepSeek, and Mistral' },
  { id: 'anthropic', label: 'Anthropic Claude', category: 'ai', hint: 'sk-ant-api03-...', url: 'https://console.anthropic.com/', placeholder: 'sk-ant-api03-...', description: 'Claude 3.5 Sonnet & Opus for deep strategic enterprise reasoning' },
  { id: 'openai', label: 'OpenAI (GPT-4o)', category: 'ai', hint: 'sk-proj-...', url: 'https://platform.openai.com/api-keys', placeholder: 'sk-proj-...', description: 'GPT-4o and o1 models for multi-modal agent workflows' },
  { id: 'together', label: 'Together AI', category: 'ai', hint: 'together_api_key...', url: 'https://api.together.ai/settings/api-keys', placeholder: 'together_...', description: 'Ultra-fast open-weights inference engine' },
  { id: 'groq', label: 'Groq LPU Engine', category: 'ai', hint: 'gsk_...', url: 'https://console.groq.com/keys', placeholder: 'gsk_...', description: 'Sub-second real-time inference for interactive agents' },
  { id: 'gemini', label: 'Google Gemini Studio', category: 'ai', hint: 'AIzaSy...', url: 'https://aistudio.google.com/app/apikey', placeholder: 'AIzaSy...', description: 'Gemini 2.5 Flash & Pro models with 1M token context' },
  { id: 'grok', label: 'xAI Grok', category: 'ai', hint: 'xai-...', url: 'https://console.x.ai/', placeholder: 'xai-...', description: 'Grok 2 model for unfiltered real-time web context' },

  // Social & Content
  { id: 'linkedin', label: 'LinkedIn Share API', category: 'social', hint: 'OAuth Access Token', url: 'https://developer.linkedin.com/', placeholder: 'AQXTs...', description: 'Publishing B2B thought leadership updates and company posts' },
  { id: 'meta', label: 'Meta Graph API', category: 'social', hint: 'Page Access Token', url: 'https://developers.facebook.com/', placeholder: 'EAABsbCS...', description: 'Publishing carousel and video reels on Instagram & Facebook' },

  // Communications & Support
  { id: 'whatsapp', label: 'WhatsApp Business API', category: 'comm', hint: 'Bearer Token | Phone ID', url: 'https://developers.facebook.com/', placeholder: 'EAABx... | 1234567890', description: 'Direct customer engagement and multi-agent support channels' },
  { id: 'telegram', label: 'Telegram Bot API', category: 'comm', hint: 'Bot Token', url: 'https://t.me/BotFather', placeholder: '7123456789:AAFtq...', description: 'Automated executive alerts and community concierge' },
  { id: 'gmail', label: 'Gmail OAuth API', category: 'comm', hint: 'OAuth Token', url: 'https://console.cloud.google.com/', placeholder: 'ya29...', description: 'Outbound sales threads and customer inbox synchronization' },
  { id: 'smtp_sales', label: 'SMTP (Sales Outbound)', category: 'comm', hint: 'smtp://user:pass@host:port', url: '', placeholder: 'smtp://sales@company.com:pass@smtp.mail.com:587', description: 'Dedicated mailbox for SDR cold outreach campaigns' },
  { id: 'smtp_marketing', label: 'SMTP (Marketing)', category: 'comm', hint: 'smtp://user:pass@host:port', url: '', placeholder: 'smtp://news@company.com:pass@smtp.mail.com:587', description: 'Newsletter and transactional email delivery server' },

  // Lead Discovery & Enrichment
  { id: 'apollo', label: 'Apollo.io', category: 'enrichment', hint: 'API Key', url: 'https://app.apollo.io/#/settings/integrations/api', placeholder: 'API_KEY...', description: 'Waterfall contact discovery, direct dials, and verified emails' },
  { id: 'hunter', label: 'Hunter.io', category: 'enrichment', hint: 'API Key', url: 'https://hunter.io/api-keys', placeholder: 'abc123...', description: 'Domain search and email pattern verification' },
  { id: 'clearbit', label: 'Clearbit Enrichment', category: 'enrichment', hint: 'sk_...', url: 'https://clearbit.com/', placeholder: 'sk_...', description: 'Company firmographics and executive role mapping' },
  { id: 'zoominfo', label: 'ZoomInfo Enterprise', category: 'enrichment', hint: 'API Key', url: 'https://www.zoominfo.com/', placeholder: 'API_KEY...', description: 'Enterprise org charts and buyer intent signals' },
  { id: 'crunchbase', label: 'Crunchbase Pro', category: 'enrichment', hint: 'API Key', url: 'https://data.crunchbase.com/', placeholder: 'API_KEY...', description: 'Funding rounds, venture investments, and acquisition signals' },
  { id: 'builtwith', label: 'BuiltWith Technographics', category: 'enrichment', hint: 'API Key', url: 'https://builtwith.com/', placeholder: 'API_KEY...', description: 'Live technology stack detection and software migration alerts' },
  { id: 'firecrawl', label: 'Firecrawl Headless', category: 'enrichment', hint: 'API Key', url: 'https://www.firecrawl.dev/app/api-keys', placeholder: 'fc-...', description: 'Deep LLM-ready website crawling and content scraping' },
];

export default function ApiManagementView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
}: ApiManagementViewProps) {
  const [configured, setConfigured] = useState<string[]>([]);
  const [mainProvider, setMainProvider] = useState<string>('openrouter');
  const [aiMode, setAiMode] = useState<'inbuilt' | 'byok'>('inbuilt');
  const [inbuiltAvailable, setInbuiltAvailable] = useState<boolean>(true);
  const [defaultProvider, setDefaultProvider] = useState<string>('openrouter');
  const [refreshing, setRefreshing] = useState(false);
  const [modeLoading, setModeLoading] = useState(false);

  // Filter & Search
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Key Configuration Modal
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogProvider, setDialogProvider] = useState<ProviderDef | null>(null);
  const [keyValue, setKeyValue] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [savingKey, setSavingKey] = useState(false);

  // Delete Confirmation
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Notification Toast
  const [toast, setToast] = useState<{ msg: string; type: 'ok' | 'err' } | null>(null);

  const showToast = (msg: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [keysRes, modeRes] = await Promise.allSettled([
        fetchWithAuth(`${API_URL}/commands/keys`),
        fetchWithAuth(`${API_URL}/commands/ai-mode`),
      ]);

      if (keysRes.status === 'fulfilled' && keysRes.value.ok) {
        const data = await keysRes.value.json();
        const providers = data.configured_providers || [];
        setConfigured(providers.map((p: any) => p.provider));
        const main = providers.find((p: any) => p.is_main);
        if (main) setMainProvider(main.provider);
      }

      if (modeRes.status === 'fulfilled' && modeRes.value.ok) {
        const modeData = await modeRes.value.json();
        const mode = modeData.current_mode || modeData.mode || 'inbuilt';
        setAiMode(mode);
        const inbuiltAvail = modeData.inbuilt_enabled ?? modeData.inbuilt_available ?? true;
        setInbuiltAvailable(inbuiltAvail);
        const defProv = modeData.primary_provider || modeData.default_provider || 'openrouter';
        setDefaultProvider(defProv);
      }
    } finally {
      setRefreshing(false);
    }
  }, [API_URL, fetchWithAuth]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleModeChange = async (newMode: 'inbuilt' | 'byok') => {
    if (newMode === aiMode || modeLoading) return;
    setModeLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/ai-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode }),
      });
      if (res.ok) {
        const data = await res.json();
        const updatedMode = data.current_mode || data.mode || newMode || 'inbuilt';
        setAiMode(updatedMode);
        showToast(
          updatedMode === 'inbuilt'
            ? '✓ Platform AI Hub active (Server multi-vendor failover).'
            : '✓ BYOK Mode active (Agents authenticate using your credentials).'
        );
        fetchData();
        refresh();
      } else {
        showToast('Failed to update execution mode', 'err');
      }
    } catch {
      showToast('Network error updating AI mode', 'err');
    } finally {
      setModeLoading(false);
    }
  };

  const openConfigModal = (p: ProviderDef) => {
    setDialogProvider(p);
    setKeyValue('');
    setShowKey(false);
    setDialogOpen(true);
  };

  const handleSaveKey = async () => {
    if (!dialogProvider || !keyValue.trim()) return;
    setSavingKey(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: dialogProvider.id, key: keyValue.trim() }),
      });
      if (res.ok) {
        setConfigured((prev) => (prev.includes(dialogProvider.id) ? prev : [...prev, dialogProvider.id]));
        setDialogOpen(false);
        fetchData();
        showToast(`✓ ${dialogProvider.label} credential configured.`);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || 'Invalid key format', 'err');
      }
    } catch {
      showToast('Network error saving key', 'err');
    } finally {
      setSavingKey(false);
    }
  };

  const handleDeleteKey = async (providerId: string) => {
    setDeletingId(providerId);
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/keys/${providerId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setConfigured((prev) => prev.filter((p) => p !== providerId));
        fetchData();
        showToast(`Credential removed for ${providerId}`);
      } else {
        showToast('Failed to remove key', 'err');
      }
    } catch {
      showToast('Network error removing key', 'err');
    } finally {
      setDeletingId(null);
    }
  };

  const handleSetMain = async (providerId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/keys/${providerId}/set-main`, {
        method: 'POST',
      });
      if (res.ok) {
        setMainProvider(providerId);
        showToast(`⭐ Primary model provider set to ${providerId}`);
      }
    } catch {
      showToast('Failed to set primary provider', 'err');
    }
  };

  const filteredProviders = useMemo(() => {
    return PROVIDERS.filter((p) => {
      if (activeCategory !== 'all' && p.category !== activeCategory) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          p.label.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.id.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [activeCategory, searchQuery]);

  const categories = [
    { id: 'all', label: 'All Services' },
    { id: 'ai', label: 'AI Brains & Hubs' },
    { id: 'social', label: 'Social & Media' },
    { id: 'comm', label: 'Communications & Mail' },
    { id: 'enrichment', label: 'Data & Enrichment' },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-16">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 px-4 py-2.5 rounded-xl shadow-2xl text-xs font-mono font-semibold border transition-all ${
            toast.type === 'ok'
              ? 'bg-zinc-900 border-emerald-500/30 text-emerald-300'
              : 'bg-zinc-900 border-rose-500/30 text-rose-300'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono mb-1">
            <span>Settings</span>
            <span>/</span>
            <span className="text-zinc-200">APIs & Integrations</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white flex items-center gap-2.5">
            Integrations & Machine Credentials
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700/60 font-mono">
              {configured.length} connected
            </span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Connect LLM gateways, publishing APIs, outbound SMTP mailboxes, and B2B enrichment providers.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={refresh}
            disabled={refreshing}
            variant="outline"
            size="sm"
            className="h-8 border-white/[0.08] bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 text-xs font-medium gap-1.5 rounded-md"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-zinc-400' : ''}`} />
            Refresh Status
          </Button>
        </div>
      </div>

      {/* AI Architecture Selector (Apple Style Segmented Card) */}
      <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-white">AI Execution Architecture</h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
                {aiMode === 'inbuilt' ? 'PLATFORM HUB' : 'BYOK ACTIVE'}
              </span>
            </div>
            <p className="text-xs text-zinc-400 mt-1 max-w-xl">
              Select whether agents route LLM requests through server-managed failover hubs (OpenRouter/Together) or your dedicated private API tokens.
            </p>
          </div>

          <div className="inline-flex p-1 rounded-lg bg-zinc-900 border border-white/[0.08] shrink-0 self-start md:self-center">
            <button
              onClick={() => handleModeChange('inbuilt')}
              disabled={modeLoading}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                aiMode === 'inbuilt'
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Server className="w-3.5 h-3.5" />
              Inbuilt Platform AI
            </button>
            <button
              onClick={() => handleModeChange('byok')}
              disabled={modeLoading}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                aiMode === 'byok'
                  ? 'bg-zinc-800 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              BYOK (Your Keys)
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Connected Services</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{configured.length}</span>
            <span className="text-[11px] text-zinc-500 font-medium">Of {PROVIDERS.length} total</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Primary AI Router</span>
            <Bot className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-sm font-semibold text-white tracking-tight truncate uppercase font-mono">
              {defaultProvider || 'OPENROUTER'}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Hub Redundancy</span>
            <Zap className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-sm font-semibold text-emerald-400 tracking-tight font-mono">
              ONLINE
            </span>
            <span className="text-[11px] text-zinc-500 font-medium">Auto-failover</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Encryption Standard</span>
            <Key className="w-3.5 h-3.5 text-zinc-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-sm font-semibold text-zinc-200 tracking-tight font-mono">
              AES-256
            </span>
            <span className="text-[11px] text-zinc-500 font-medium">Vault-sealed</span>
          </div>
        </div>
      </div>

      {/* Tabs & Search Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs text-zinc-400 scrollbar-none">
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => setActiveCategory(c.id)}
              className={`px-3 py-1.5 rounded-md text-xs transition-colors whitespace-nowrap font-medium ${
                activeCategory === c.id
                  ? 'bg-zinc-800 text-white shadow-sm border border-white/[0.08]'
                  : 'text-zinc-400 hover:text-zinc-200 border border-transparent'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search providers or services…"
            className="h-8 pl-8 text-xs bg-zinc-900/60 border-white/[0.08] focus:border-zinc-500 rounded-md placeholder:text-zinc-500"
          />
        </div>
      </div>

      {/* Service Cards Grid (GCP APIs & Services style) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filteredProviders.map((p) => {
          const isConfigured = configured.includes(p.id);
          const isMain = mainProvider === p.id;
          const isDeleting = deletingId === p.id;

          return (
            <div
              key={p.id}
              className={`rounded-xl border p-4 flex flex-col justify-between transition-all ${
                isConfigured
                  ? 'border-white/[0.12] bg-[#111318] shadow-sm'
                  : 'border-white/[0.06] bg-[#0d0f14]'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="text-sm font-semibold text-white truncate flex items-center gap-1.5">
                      {p.label}
                      {isMain && (
                        <span title="Primary Engine" className="text-amber-400">
                          <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                        </span>
                      )}
                    </h3>
                    <div className="text-[11px] font-mono text-zinc-500 mt-0.5">ID: {p.id}</div>
                  </div>

                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-md font-medium shrink-0 ${
                      isConfigured
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-zinc-800/80 text-zinc-400 border border-zinc-700/60'
                    }`}
                  >
                    {isConfigured ? 'CONNECTED' : 'DISCONNECTED'}
                  </span>
                </div>

                <p className="text-xs text-zinc-400 line-clamp-2 leading-relaxed">
                  {p.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between gap-2">
                {p.url ? (
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 font-mono transition-colors"
                  >
                    Docs <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <div />
                )}

                <div className="flex items-center gap-1.5">
                  {isConfigured ? (
                    <>
                      {p.category === 'ai' && !isMain && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleSetMain(p.id)}
                          className="h-7 text-[11px] text-zinc-400 hover:text-white px-2 rounded-md font-mono"
                          title="Set as Default AI Provider"
                        >
                          Make Primary
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteKey(p.id)}
                        disabled={isDeleting}
                        className="h-7 w-7 p-0 text-zinc-400 hover:text-rose-400 hover:bg-rose-950/20 rounded-md"
                        title="Remove Credential"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => openConfigModal(p)}
                      className="h-7 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs px-2.5 rounded-md font-medium"
                    >
                      Configure
                    </Button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Key Configuration Modal */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md bg-[#12141a] border-white/[0.08] text-white p-6 rounded-2xl shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
              <Key className="w-4 h-4 text-zinc-300" />
              Configure {dialogProvider?.label}
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              API tokens are stored in hardware-encrypted tenant secrets and never exposed in client logs.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-2">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-300">API Secret Key / Token</label>
                {dialogProvider?.url && (
                  <a
                    href={dialogProvider.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1"
                  >
                    Obtain Key <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>

              <div className="relative">
                <Input
                  type={showKey ? 'text' : 'password'}
                  value={keyValue}
                  onChange={(e) => setKeyValue(e.target.value)}
                  placeholder={dialogProvider?.placeholder || 'sk-...'}
                  className="h-9 pr-9 text-xs font-mono bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-200"
                >
                  {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>

              {dialogProvider?.hint && (
                <p className="text-[11px] text-zinc-500 font-mono">Format: {dialogProvider.hint}</p>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.08]">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDialogOpen(false)}
                className="h-8 border-white/[0.08] bg-zinc-900 text-zinc-300 text-xs rounded-md"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveKey}
                disabled={savingKey || !keyValue.trim()}
                className="h-8 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md px-4 shadow-sm"
              >
                {savingKey ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                    Encrypting & Storing…
                  </>
                ) : (
                  'Save Credential'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

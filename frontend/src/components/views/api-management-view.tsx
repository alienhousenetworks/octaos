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
  Copy,
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
import SystemMcpView from '@/components/views/system-mcp-view';

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
  // AI Models & Brains
  { id: 'openrouter', label: 'OpenRouter (Meta-Hub)', category: 'ai', hint: 'sk-or-v1-...', url: 'https://openrouter.ai/keys', placeholder: 'sk-or-v1-...', description: 'Unified gateway routing to Claude, Llama 3, DeepSeek, and Mistral' },
  { id: 'anthropic', label: 'Anthropic Claude', category: 'ai', hint: 'sk-ant-api03-...', url: 'https://console.anthropic.com/', placeholder: 'sk-ant-api03-...', description: 'Claude 3.5 Sonnet & Opus for deep strategic enterprise reasoning' },
  { id: 'openai', label: 'OpenAI (GPT-4o)', category: 'ai', hint: 'sk-proj-...', url: 'https://platform.openai.com/api-keys', placeholder: 'sk-proj-...', description: 'GPT-4o and o1 models for multi-modal agent workflows' },
  { id: 'together', label: 'Together AI', category: 'ai', hint: 'together_api_key...', url: 'https://api.together.ai/settings/api-keys', placeholder: 'together_...', description: 'Ultra-fast open-weights inference engine' },
  { id: 'groq', label: 'Groq LPU Engine', category: 'ai', hint: 'gsk_...', url: 'https://console.groq.com/keys', placeholder: 'gsk_...', description: 'Sub-second real-time inference for interactive agents' },
  { id: 'gemini', label: 'Google Gemini Studio', category: 'ai', hint: 'AIzaSy...', url: 'https://aistudio.google.com/app/apikey', placeholder: 'AIzaSy...', description: 'Gemini 2.5 Flash & Pro models with 1M token context' },
  { id: 'nvidia', label: 'NVIDIA NIM (Integrate API)', category: 'ai', hint: 'nvapi-...', url: 'https://build.nvidia.com/', placeholder: 'nvapi-...', description: 'Enterprise accelerated inference for Llama 3.3 70B and frontier open models' },
  { id: 'grok', label: 'xAI Grok', category: 'ai', hint: 'xai-...', url: 'https://console.x.ai/', placeholder: 'xai-...', description: 'Grok 2 model for unfiltered real-time web context' },

  // Marketing & Ads
  { id: 'sendgrid', label: 'Twilio SendGrid', category: 'marketing', hint: 'SG....', url: 'https://app.sendgrid.com/settings/api_keys', placeholder: 'SG....', description: 'Transactional & marketing email campaigns, dynamic templates, and bounce telemetry' },
  { id: 'landingi', label: 'Landingi Pages & Funnels', category: 'marketing', hint: 'API Key / Webhook Token', url: 'https://landingi.com/', placeholder: 'landingi_token...', description: 'Landing page conversion webhooks, UTM campaign tagging, and lead capture' },
  { id: 'google_ads', label: 'Google Ads', category: 'marketing', hint: 'Developer Token | Customer ID', url: 'https://ads.google.com/', placeholder: 'dev_token | 123-456-7890', description: 'Offline conversion uploads via GCLID and Customer Match audience sync' },
  { id: 'matomo', label: 'Matomo Analytics', category: 'marketing', hint: 'token_auth | Server URL', url: 'https://matomo.org/', placeholder: 'token_auth...', description: 'Privacy-compliant web analytics, goal conversion tracking, and campaign ROI' },
  { id: 'youscan', label: 'YouScan AI Listening', category: 'marketing', hint: 'API Token', url: 'https://youscan.io/', placeholder: 'youscan_token...', description: 'AI brand sentiment monitoring, visual logo detection, and competitor radar' },
  { id: 'sendpulse', label: 'SendPulse Marketing', category: 'marketing', hint: 'Client ID | Secret', url: 'https://sendpulse.com/', placeholder: 'client_id | secret', description: 'Multi-channel email campaigns, web push notifications, and chatbots' },

  // Social & Media
  { id: 'buffer', label: 'Buffer Omnichannel', category: 'social', hint: 'OAuth 2.0 or API Key', url: 'https://buffer.com/', placeholder: 'Buffer API Key...', description: 'Omnichannel social publishing across Instagram, Facebook, X, LinkedIn, TikTok, Threads, and YouTube' },
  { id: 'linkedin', label: 'LinkedIn Share API', category: 'social', hint: 'OAuth Access Token', url: 'https://developer.linkedin.com/', placeholder: 'AQXTs...', description: 'Publishing B2B thought leadership updates and company posts' },
  { id: 'meta', label: 'Meta Graph API & Lead Ads', category: 'social', hint: 'Page Access Token', url: 'https://developers.facebook.com/', placeholder: 'EAABsbCS...', description: 'Publishing carousels, video reels on IG & FB, and Meta Lead Ads sync' },
  { id: 'heygen', label: 'HeyGen Video AI', category: 'social', hint: 'HeyGen API Key', url: 'https://platform.heygen.com/api-keys', placeholder: 'your_heygen_api_key...', description: 'AI avatars, brand spokesperson videos, and automated video-agent generation' },
  { id: 'hootsuite', label: 'Hootsuite Publishing', category: 'social', hint: 'Access Token', url: 'https://developer.hootsuite.com/', placeholder: 'Bearer token...', description: 'Multi-network social post scheduling, queue management, and stream monitoring' },

  // Communications & Support
  { id: 'whatsapp', label: 'WhatsApp Business API', category: 'comm', hint: 'Bearer Token | Phone ID', url: 'https://developers.facebook.com/', placeholder: 'EAABx... | 1234567890', description: 'Direct customer engagement and multi-agent support channels' },
  { id: 'fbmessenger', label: 'Facebook Messenger', category: 'comm', hint: 'Page Access Token', url: 'https://developers.facebook.com/', placeholder: 'EAAB...', description: 'Conversational marketing triage, automated replies, and agent handoff' },
  { id: 'twilio', label: 'Twilio SMS & Voice', category: 'comm', hint: 'Account SID | Auth Token', url: 'https://console.twilio.com/', placeholder: 'AC... | auth_token', description: 'Two-way SMS outreach, voice telephony alerts, and OTP verification' },
  { id: 'telegram', label: 'Telegram Bot API', category: 'comm', hint: 'Bot Token', url: 'https://t.me/BotFather', placeholder: '7123456789:AAFtq...', description: 'Automated executive alerts and community concierge' },
  { id: 'gmail', label: 'Gmail OAuth API', category: 'comm', hint: 'OAuth Token', url: 'https://console.cloud.google.com/', placeholder: 'ya29...', description: 'Outbound sales threads and customer inbox synchronization' },
  { id: 'smtp_sales', label: 'SMTP (Sales Outbound)', category: 'comm', hint: 'smtp://user:pass@host:port', url: '', placeholder: 'smtp://sales@company.com:pass@smtp.mail.com:587', description: 'Dedicated mailbox for SDR cold outreach campaigns' },
  { id: 'smtp_marketing', label: 'SMTP (Marketing)', category: 'comm', hint: 'smtp://user:pass@host:port', url: '', placeholder: 'smtp://news@company.com:pass@smtp.mail.com:587', description: 'Newsletter and transactional email delivery server' },

  // Sales & Scheduling & Enrichment
  { id: 'calendly', label: 'Calendly Scheduling', category: 'enrichment', hint: 'Personal Access Token', url: 'https://calendly.com/integrations/api_webhooks', placeholder: 'eyJhbGciOi...', description: 'Automated meeting scheduling, single-use booking links, and SDR handoff' },
  { id: 'zoominfo', label: 'ZoomInfo Enterprise', category: 'enrichment', hint: 'API Key', url: 'https://www.zoominfo.com/', placeholder: 'API_KEY...', description: 'Enterprise org charts, verified contact waterfall, and buyer intent signals' },
  { id: 'mapsly', label: 'Mapsly Geocoding', category: 'enrichment', hint: 'API Key', url: 'https://mapsly.com/', placeholder: 'mapsly_api_key...', description: 'Sales territory management, lead geocoding, and field rep route optimization' },
  { id: 'apollo', label: 'Apollo.io', category: 'enrichment', hint: 'API Key', url: 'https://app.apollo.io/#/settings/integrations/api', placeholder: 'API_KEY...', description: 'Waterfall contact discovery, direct dials, and verified emails' },
  { id: 'hunter', label: 'Hunter.io', category: 'enrichment', hint: 'API Key', url: 'https://hunter.io/api-keys', placeholder: 'abc123...', description: 'Domain search and email pattern verification' },
  { id: 'clearbit', label: 'Clearbit Enrichment', category: 'enrichment', hint: 'sk_...', url: 'https://clearbit.com/', placeholder: 'sk_...', description: 'Company firmographics and executive role mapping' },
  { id: 'crunchbase', label: 'Crunchbase Pro', category: 'enrichment', hint: 'API Key', url: 'https://data.crunchbase.com/', placeholder: 'API_KEY...', description: 'Funding rounds, venture investments, and acquisition signals' },
  { id: 'builtwith', label: 'BuiltWith Technographics', category: 'enrichment', hint: 'API Key', url: 'https://builtwith.com/', placeholder: 'API_KEY...', description: 'Live technology stack detection and software migration alerts' },
  { id: 'firecrawl', label: 'Firecrawl Headless', category: 'enrichment', hint: 'API Key', url: 'https://www.firecrawl.dev/app/api-keys', placeholder: 'fc-...', description: 'Deep LLM-ready website crawling and content scraping' },

  // iPaaS & Enterprise Automations
  { id: 'zapier', label: 'Zapier Automation Hub', category: 'ipaas', hint: 'Webhook URL / API Key', url: 'https://zapier.com/app/developer', placeholder: 'https://hooks.zapier.com/...', description: 'Universal no-code automation connecting OctaOS to 6,000+ apps' },
  { id: 'workato', label: 'Workato Enterprise iPaaS', category: 'ipaas', hint: 'API Token | Webhook Secret', url: 'https://www.workato.com/', placeholder: 'workato_token...', description: 'Enterprise workflow recipes, bidirectional ERP sync, and event bus' },
  { id: 'google_forms', label: 'Google Forms Ingestion', category: 'ipaas', hint: 'Webhook Token / Secret', url: 'https://forms.google.com/', placeholder: 'google_forms_secret...', description: 'Real-time form submission capture directly syncing into Sales OS Leads' },
  { id: 'formstack', label: 'Formstack Forms & Docs', category: 'ipaas', hint: 'API Token', url: 'https://www.formstack.com/', placeholder: 'formstack_token...', description: 'Enterprise forms, automated document generation, and digital signature workflows' },
  { id: 'powerbi', label: 'Microsoft Power BI', category: 'ipaas', hint: 'Push Dataset URL | Client Secret', url: 'https://powerbi.microsoft.com/', placeholder: 'https://api.powerbi.com/v1.0/myorg/...', description: 'Streaming executive dashboards, conversion KPIs, and revenue pipelines' },
  { id: 'postman', label: 'Postman Workspace', category: 'ipaas', hint: 'Postman API Key', url: 'https://web.postman.co/settings/me/api-keys', placeholder: 'PMAK-...', description: 'Automated webhook collection tests, API health mocks, and spec validation' },
];

export default function ApiManagementView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  tenantId,
}: ApiManagementViewProps) {
  const [mainSection, setMainSection] = useState<'integrations' | 'mcp'>('integrations');
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
  const [providerSettings, setProviderSettings] = useState<Record<string, any>>({});
  const [orgIdValue, setOrgIdValue] = useState('');
  const [clientIdValue, setClientIdValue] = useState('');
  const [clientSecretValue, setClientSecretValue] = useState('');
  const [selectedScope, setSelectedScope] = useState<string>('openid profile w_member_social w_organization_social');

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
        const settingsMap: Record<string, any> = {};
        providers.forEach((p: any) => {
          if (p.settings) settingsMap[p.provider] = p.settings;
        });
        setProviderSettings(settingsMap);
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
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('linkedin') === 'connected') {
        showToast('✓ LinkedIn account authorized and connected!');
        window.history.replaceState({}, '', window.location.pathname);
      } else if (params.get('linkedin_error')) {
        const err = params.get('linkedin_error');
        const desc = params.get('linkedin_error_description');
        if (err === 'unauthorized_scope_error') {
          showToast(
            desc
              ? `LinkedIn rejected a permission: ${desc}`
              : 'LinkedIn rejected a requested permission. Enable Sign In with LinkedIn (OpenID) for personal posts, or the Community Management API for company pages.',
            'err',
          );
        } else {
          showToast(`LinkedIn error: ${err}`, 'err');
        }
        window.history.replaceState({}, '', window.location.pathname);
      }
    }
  }, [refresh]);

  const parsedOrgUrn = useMemo(() => {
    const clean = orgIdValue.trim();
    if (!clean) return null;
    if (clean.startsWith('urn:li:organization:')) return clean;
    const match = clean.match(/company\/(\d+)/) || clean.match(/(\d+)/);
    if (match) return `urn:li:organization:${match[1]}`;
    return `urn:li:organization:${clean}`;
  }, [orgIdValue]);

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
    if (p.id === 'linkedin') {
      const s = providerSettings['linkedin'] || {};
      const org = s.organization_urn || s.organization_id || '';
      setOrgIdValue(org.replace('urn:li:organization:', ''));
      setClientIdValue(s.client_id || '');
      setClientSecretValue(s.client_secret || '');
    } else {
      setOrgIdValue('');
      setClientIdValue('');
      setClientSecretValue('');
    }
    setDialogOpen(true);
  };

  const handleSaveKey = async (options?: { skipClose?: boolean; customKey?: string }): Promise<boolean> => {
    if (!dialogProvider) return false;
    const isLinkedIn = dialogProvider.id === 'linkedin';
    const keyToSave = options?.customKey || keyValue.trim() || (isLinkedIn && configured.includes('linkedin') ? 'configured_token' : '');
    if (!keyToSave && !isLinkedIn && !orgIdValue.trim() && !clientIdValue.trim()) return false;

    setSavingKey(true);
    try {
      const payload: any = {
        provider: dialogProvider.id,
        key: keyToSave || 'oauth_connected',
      };

      if (isLinkedIn) {
        payload.settings = {
          ...(providerSettings['linkedin'] || {}),
          ...(parsedOrgUrn ? { organization_urn: parsedOrgUrn, organization_id: parsedOrgUrn.replace('urn:li:organization:', '') } : {}),
          ...(clientIdValue.trim() ? { client_id: clientIdValue.trim() } : {}),
          ...(clientSecretValue.trim() ? { client_secret: clientSecretValue.trim() } : {}),
        };
      }

      const res = await fetchWithAuth(`${API_URL}/commands/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setConfigured((prev) => (prev.includes(dialogProvider.id) ? prev : [...prev, dialogProvider.id]));
        if (!options?.skipClose) {
          setDialogOpen(false);
        }
        fetchData();
        refresh();
        showToast(`✓ ${dialogProvider.label} settings saved.`);
        return true;
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || 'Invalid key format', 'err');
        return false;
      }
    } catch {
      showToast('Network error saving credentials', 'err');
      return false;
    } finally {
      setSavingKey(false);
    }
  };

  const handleLinkedInOAuthConnect = async () => {
    if (orgIdValue.trim() || clientIdValue.trim() || clientSecretValue.trim()) {
      await handleSaveKey({ skipClose: true });
    }
    const params = new URLSearchParams();
    if (tenantId) params.set('tenant_id', tenantId);
    if (selectedScope) params.set('scope', selectedScope);
    window.location.href = `${API_URL}/linkedin/auth?${params.toString()}`;
  };

  const handleBufferOAuthConnect = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/connectors/buffer/connect`);
      if (res.ok) {
        const data = await res.json();
        if (data.url) {
          window.location.href = data.url;
          return;
        }
      }
      showToast('Could not start Buffer OAuth session', 'err');
    } catch {
      showToast('Network error starting Buffer OAuth', 'err');
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
    { id: 'marketing', label: 'Marketing & Ads' },
    { id: 'social', label: 'Social & Media' },
    { id: 'comm', label: 'Communications & Chat' },
    { id: 'enrichment', label: 'Sales & Scheduling' },
    { id: 'ipaas', label: 'iPaaS & Automation' },
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

      {/* Top Navigation Tabs */}
      <div className="flex border-b border-white/[0.08] gap-6 text-sm font-medium">
        <button
          onClick={() => setMainSection('integrations')}
          className={`pb-3 transition-colors relative flex items-center gap-2 ${
            mainSection === 'integrations'
              ? 'text-white border-b-2 border-indigo-500 font-semibold'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Server className="w-4 h-4 text-indigo-400" />
          Outbound API Integrations
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300">
            {configured.length}
          </span>
        </button>

        <button
          onClick={() => setMainSection('mcp')}
          className={`pb-3 transition-colors relative flex items-center gap-2 ${
            mainSection === 'mcp'
              ? 'text-white border-b-2 border-indigo-500 font-semibold'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Sparkles className="w-4 h-4 text-purple-400" />
          OctaOS System MCP Hub
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            One-Click Connect
          </span>
        </button>
      </div>

      {mainSection === 'mcp' ? (
        <SystemMcpView
          token={token}
          API_URL={API_URL}
          fetchWithAuth={fetchWithAuth}
        />
      ) : (
        <>
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

                {p.id === 'linkedin' && (providerSettings['linkedin']?.organization_urn || providerSettings['linkedin']?.organization_id) && (
                  <div className="mt-2 flex items-center gap-1.5 text-[11px] font-mono text-sky-400 bg-sky-950/40 border border-sky-800/40 px-2 py-0.5 rounded-md w-fit">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                    <span>Page: {String(providerSettings['linkedin'].organization_urn || providerSettings['linkedin'].organization_id).replace('urn:li:organization:', '')}</span>
                  </div>
                )}
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
                        onClick={() => openConfigModal(p)}
                        className="h-7 text-[11px] text-zinc-400 hover:text-white px-2 rounded-md font-mono"
                        title="Edit Settings"
                      >
                        Edit
                      </Button>
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
        <DialogContent className="sm:max-w-lg bg-[#12141a] border-white/[0.08] text-white p-6 rounded-2xl shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
              <Key className="w-4 h-4 text-zinc-300" />
              Configure {dialogProvider?.label}
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Credentials and company page linkages are encrypted per-tenant and stored securely.
            </DialogDescription>
          </DialogHeader>

          {dialogProvider?.id === 'linkedin' ? (
            <div className="space-y-4 mt-2">
              {/* 1-Click OAuth Connect Card */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-[#0a66c2]/15 via-zinc-900 to-[#004182]/10 border border-[#0a66c2]/30 flex flex-col gap-3 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-semibold text-[#70b5f9]">
                      <Zap className="w-3.5 h-3.5" />
                      <span>1-Click LinkedIn OAuth Authorization</span>
                      {configured.includes('linkedin') && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                      Instantly sign in with LinkedIn to authorize social post publishing permissions for your tenant.
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleLinkedInOAuthConnect}
                    disabled={savingKey}
                    className="bg-[#0a66c2] hover:bg-[#004182] text-white text-xs font-medium h-8 shrink-0 shadow-md gap-1.5 self-start sm:self-auto"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    {configured.includes('linkedin') ? 'Re-authorize Account' : 'Authorize LinkedIn'}
                  </Button>
                </div>

                <div className="pt-2.5 border-t border-white/[0.06] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <span className="text-[11px] text-zinc-400 font-mono">Authorization Scope:</span>
                  <div className="inline-flex items-center gap-1 bg-zinc-950/80 p-1 rounded-lg border border-white/[0.08]">
                    <button
                      type="button"
                      onClick={() => setSelectedScope('openid profile w_member_social w_organization_social')}
                      className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                        selectedScope.includes('w_organization_social')
                          ? 'bg-[#0a66c2] text-white shadow-sm'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      Company Page & Profile
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedScope('openid profile w_member_social')}
                      className={`px-2.5 py-1 text-[11px] font-medium rounded-md transition-all ${
                        !selectedScope.includes('w_organization_social')
                          ? 'bg-zinc-800 text-white shadow-sm'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      Personal Profile Only
                    </button>
                  </div>
                </div>
              </div>

              {/* Company Page Note */}
              <div className="text-[11px] text-zinc-400 bg-sky-950/20 border border-sky-800/30 rounded-xl p-3 leading-relaxed flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-sky-300">LinkedIn Company Page Requirement:</strong>
                  <p className="mt-0.5 text-zinc-400">
                    Personal posts need <strong>Sign In with LinkedIn using OpenID Connect</strong> and <strong>Share on LinkedIn</strong>. Company Page posts also need the <strong>Community Management API</strong> product, and the signed-in member must be a <strong>Super Admin</strong> or <strong>Content Admin</strong> of that page. A member-only token publishes to the personal profile.
                  </p>
                </div>
              </div>

              {/* LinkedIn Company Page URL or ID */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-200 flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-sky-400" />
                    LinkedIn Company Page ID or URL
                  </label>
                  <span className="text-[10px] text-sky-400 font-mono">Company Feed Target</span>
                </div>
                <Input
                  type="text"
                  value={orgIdValue}
                  onChange={(e) => setOrgIdValue(e.target.value)}
                  placeholder="e.g. 104858837 or https://www.linkedin.com/company/104858837/admin/dashboard/"
                  className="h-9 text-xs font-mono bg-zinc-950/80 border-white/[0.08] focus:border-sky-500 rounded-md"
                />
                {parsedOrgUrn ? (
                  <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 font-mono mt-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Target Author URN: <strong>{parsedOrgUrn}</strong></span>
                  </div>
                ) : (
                  <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                    Paste your admin URL (e.g. linkedin.com/company/<strong>104858837</strong>/admin) or page ID.
                  </p>
                )}
              </div>

              {/* Direct Access Token (Optional) */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-200 flex items-center gap-1.5">
                    <Key className="w-3.5 h-3.5 text-amber-400" />
                    Direct Access Token
                    {configured.includes('linkedin') && !keyValue && (
                      <span className="text-[10px] text-emerald-400 font-mono">(Connected via OAuth)</span>
                    )}
                  </label>
                  <a
                    href="https://www.linkedin.com/developers/tools/oauth"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1"
                  >
                    Token Generator <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="relative">
                  <Input
                    type={showKey ? 'text' : 'password'}
                    value={keyValue}
                    onChange={(e) => setKeyValue(e.target.value)}
                    placeholder={configured.includes('linkedin') ? '•••••••••••••••• (Leave blank to keep active OAuth token)' : 'AQXTs... (Optional if using 1-Click Authorize)'}
                    className="h-9 pr-9 text-xs font-mono bg-zinc-950/80 border-white/[0.08] focus:border-zinc-500 rounded-md"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-200"
                  >
                    {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              {/* Developer App BYOK (Optional) */}
              <details className="text-xs text-zinc-400 bg-zinc-950/40 border border-white/[0.05] rounded-xl p-3" open={Boolean(clientIdValue || clientSecretValue)}>
                <summary className="cursor-pointer hover:text-zinc-200 font-medium text-xs text-zinc-300 flex items-center justify-between select-none">
                  <span className="flex items-center gap-1.5">
                    <Sliders className="w-3.5 h-3.5 text-purple-400" />
                    Custom Developer App Credentials (BYOK)
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500">
                    {clientIdValue ? 'Custom App Set' : 'Using Default OctaOS App'}
                  </span>
                </summary>
                <div className="space-y-3 mt-3 pt-3 border-t border-white/[0.05]">
                  <p className="text-[11px] text-zinc-500">
                    Optionally provide your own LinkedIn Developer App credentials. If left blank, OctaOS uses the pre-configured default app.
                  </p>
                  <div>
                    <label className="text-[11px] text-zinc-400 font-mono">LinkedIn Client ID</label>
                    <Input
                      type="text"
                      value={clientIdValue}
                      onChange={(e) => setClientIdValue(e.target.value)}
                      placeholder="e.g. 771xk6ipgiz4un"
                      className="h-8 text-xs font-mono bg-zinc-900 border-white/[0.08] mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-zinc-400 font-mono">LinkedIn Primary Client Secret</label>
                    <Input
                      type="password"
                      value={clientSecretValue}
                      onChange={(e) => setClientSecretValue(e.target.value)}
                      placeholder="e.g. WPL_AP1..."
                      className="h-8 text-xs font-mono bg-zinc-900 border-white/[0.08] mt-1"
                    />
                  </div>
                </div>
              </details>

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
                  onClick={() => handleSaveKey()}
                  disabled={savingKey || (!keyValue.trim() && !orgIdValue.trim() && !clientIdValue.trim() && !configured.includes('linkedin'))}
                  className="h-8 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md px-4 shadow-sm"
                >
                  {savingKey ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                      Saving…
                    </>
                  ) : (
                    'Save Settings'
                  )}
                </Button>
              </div>
            </div>
          ) : dialogProvider?.id === 'buffer' ? (
            <div className="space-y-4 mt-2">
              {/* 1-Click OAuth Connect Card */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-blue-600/15 via-zinc-900 to-indigo-600/10 border border-blue-500/30 flex flex-col gap-3 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-semibold text-blue-400">
                      <Zap className="w-3.5 h-3.5" />
                      <span>1-Click Buffer OAuth 2.0 PKCE</span>
                      {configured.includes('buffer') && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                      Connect your Buffer workspace to schedule and publish approved posts across 11 social networks: Instagram, Facebook, X, LinkedIn, TikTok, Threads, YouTube, Pinterest, Bluesky, Mastodon, and Google Business Profile.
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleBufferOAuthConnect}
                    disabled={savingKey}
                    className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium h-8 shrink-0 shadow-md gap-1.5 self-start sm:self-auto"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    {configured.includes('buffer') ? 'Reconnect Buffer' : 'Connect Buffer'}
                  </Button>
                </div>

                <div className="pt-2.5 border-t border-white/[0.06] flex items-center justify-between">
                  <span className="text-[11px] text-zinc-400">Connected social channels & mapping:</span>
                  <a
                    href="/settings/integrations"
                    className="inline-flex items-center gap-1 text-[11px] font-medium text-blue-400 hover:text-blue-300 font-mono"
                  >
                    Open Channel Mapping <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>

              {/* Direct Buffer API Key (Fallback) */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-zinc-900/60 border border-white/[0.06]">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-zinc-200 flex items-center gap-1.5">
                    <Key className="w-3.5 h-3.5 text-amber-400" />
                    Buffer API Key (Optional Fallback)
                  </label>
                  <a
                    href="https://buffer.com/manage/apps"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1"
                  >
                    Buffer API Settings <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <div className="relative">
                  <Input
                    type={showKey ? 'text' : 'password'}
                    value={keyValue}
                    onChange={(e) => setKeyValue(e.target.value)}
                    placeholder={configured.includes('buffer') ? '•••••••••••••••• (Leave blank to keep active token)' : 'Paste Buffer API Key...'}
                    className="h-9 pr-9 text-xs font-mono bg-zinc-950/80 border-white/[0.08] focus:border-zinc-500 rounded-md"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-200"
                  >
                    {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
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
                  onClick={() => handleSaveKey()}
                  disabled={savingKey || (!keyValue.trim() && !configured.includes('buffer'))}
                  className="h-8 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md px-4 shadow-sm"
                >
                  {savingKey ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                      Saving…
                    </>
                  ) : (
                    'Save Key'
                  )}
                </Button>
              </div>
            </div>
          ) : (
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

              {dialogProvider && ['calendly', 'google_forms', 'landingi', 'formstack', 'zapier', 'workato', 'sendgrid', 'twilio'].includes(dialogProvider.id) && (
                <div className="p-3 rounded-lg bg-zinc-950/60 border border-white/[0.08] space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-zinc-300">
                    <span className="font-medium flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 text-indigo-400" />
                      Inbound Webhook Endpoint
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        const url = `${API_URL}/integrations/webhooks/${dialogProvider.id}/${tenantId || 'default'}`;
                        navigator.clipboard.writeText(url);
                        showToast('✓ Webhook URL copied to clipboard');
                      }}
                      className="text-[10px] font-mono text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" /> Copy URL
                    </button>
                  </div>
                  <p className="text-[11px] font-mono text-zinc-400 truncate bg-zinc-900 px-2 py-1 rounded">
                    {`${API_URL}/integrations/webhooks/${dialogProvider.id}/${tenantId || 'default'}`}
                  </p>
                  <p className="text-[10px] text-zinc-500">
                    Paste this endpoint into {dialogProvider.label} to stream real-time events into OctaOS.
                  </p>
                </div>
              )}

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
                  onClick={() => handleSaveKey()}
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
          )}
        </DialogContent>
      </Dialog>
        </>
      )}
    </div>
  );
}

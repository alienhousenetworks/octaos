'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  Copy,
  Check,
  Server,
  Terminal,
  Globe,
  Shield,
  Layers,
  Database,
  Search,
  ExternalLink,
  Code2,
  Cpu,
  ArrowRight,
  ShieldAlert,
  Sliders,
  Sparkles,
} from 'lucide-react';

interface SystemMcpViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

interface MCPCredential {
  id: string;
  name: string;
  client_type: string;
  key_prefix: string;
  role: string;
  rate_limit_rpm: number;
  max_records_per_query: number;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
  grants: any[];
}

interface DiscoveredObject {
  object_name: string;
  display_name: string;
  description: string;
  supported_operations: string[];
  properties: string[];
}

interface ExternalMCPServer {
  id: string;
  name: string;
  slug: string;
  transport: string;
  target: string | null;
  status: string;
  enabled: boolean;
  has_headers: boolean;
  has_environment: boolean;
  last_synced_at: string | null;
  created_at: string | null;
}

export default function SystemMcpView({
  token,
  API_URL,
  fetchWithAuth,
}: SystemMcpViewProps) {
  const [credentials, setCredentials] = useState<MCPCredential[]>([]);
  const [catalog, setCatalog] = useState<{ universal_tools: any[]; domain_wrappers: any[] }>({
    universal_tools: [],
    domain_wrappers: [],
  });
  const [connectors, setConnectors] = useState<any[]>([]);
  const [externalServers, setExternalServers] = useState<ExternalMCPServer[]>([]);
  const [collaborationProviders, setCollaborationProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  // External MCP server registration
  const [serverDialogOpen, setServerDialogOpen] = useState(false);
  const [serverName, setServerName] = useState('');
  const [serverSlug, setServerSlug] = useState('');
  const [serverTransport, setServerTransport] = useState<'streamable_http' | 'sse' | 'stdio'>('streamable_http');
  const [serverEndpoint, setServerEndpoint] = useState('');
  const [serverCommand, setServerCommand] = useState('');
  const [serverArgs, setServerArgs] = useState('');
  const [serverHeaders, setServerHeaders] = useState('');
  const [serverEnv, setServerEnv] = useState('');
  const [serverSaving, setServerSaving] = useState(false);
  const [testingServerId, setTestingServerId] = useState<string | null>(null);

  // One-Click Setup Wizard State
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [selectedClient, setSelectedClient] = useState('claude_desktop');
  const [selectedTransport, setSelectedTransport] = useState<'streamable_http' | 'stdio'>('stdio');
  const [keyName, setKeyName] = useState('');
  const [selectedRole, setSelectedRole] = useState('standard_operator');
  const [approvalRequired, setApprovalRequired] = useState(true);

  // Generated Key Modal State
  const [newKeyData, setNewKeyData] = useState<{ raw_key: string; name: string } | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedConfig, setCopiedConfig] = useState(false);

  // Test Connection
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; msg: string; ok: boolean } | null>(null);

  // Notification Toast
  const [toast, setToast] = useState<{ msg: string; type: 'ok' | 'err' } | null>(null);

  const showToast = (msg: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [credsRes, catRes, connRes, serversRes, collabRes] = await Promise.allSettled([
        fetchWithAuth(`${API_URL}/mcp/credentials`),
        fetchWithAuth(`${API_URL}/mcp/catalog`),
        fetchWithAuth(`${API_URL}/mcp/connectors`),
        fetchWithAuth(`${API_URL}/mcp/servers`),
        fetchWithAuth(`${API_URL}/plugin/collaboration/providers`),
      ]);

      if (credsRes.status === 'fulfilled' && credsRes.value.ok) {
        const d = await credsRes.value.json();
        setCredentials(d.credentials || []);
      }
      if (catRes.status === 'fulfilled' && catRes.value.ok) {
        const d = await catRes.value.json();
        setCatalog(d);
      }
      if (connRes.status === 'fulfilled' && connRes.value.ok) {
        const d = await connRes.value.json();
        setConnectors(d.connectors || []);
      }
      if (serversRes.status === 'fulfilled' && serversRes.value.ok) {
        const d = await serversRes.value.json();
        setExternalServers(d.servers || []);
      }
      if (collabRes.status === 'fulfilled' && collabRes.value.ok) {
        const d = await collabRes.value.json();
        setCollaborationProviders(Array.isArray(d) ? d : []);
      }
    } finally {
      setLoading(false);
    }
  }, [API_URL, fetchWithAuth]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateCredential = async () => {
    if (!keyName.trim()) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/mcp/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: keyName.trim(),
          client_type: selectedClient,
          role: selectedRole,
        }),
      });

      if (res.ok) {
        const d = await res.json();
        setNewKeyData({ raw_key: d.raw_key, name: d.name });
        setWizardOpen(false);
        setKeyName('');
        setWizardStep(1);
        loadData();
        showToast('✓ MCP API Key generated successfully.');
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || 'Failed to create key', 'err');
      }
    } catch {
      showToast('Network error creating credential', 'err');
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm('Are you sure you want to revoke this MCP key? Connected AI clients will lose access immediately.')) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/mcp/credentials/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setCredentials((prev) => prev.filter((c) => c.id !== id));
        showToast('Credential revoked.');
      }
    } catch {
      showToast('Network error revoking credential', 'err');
    }
  };

  const handleTestConnection = async (credentialId: string) => {
    setTestingId(credentialId);
    setTestResult(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/mcp/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential_id: credentialId }),
      });
      const d = await res.json();
      if (res.ok && d.status === 'success') {
        setTestResult({ id: credentialId, msg: d.message, ok: true });
      } else {
        setTestResult({ id: credentialId, msg: d.message || 'Verification failed', ok: false });
      }
    } catch {
      setTestResult({ id: credentialId, msg: 'Network timeout', ok: false });
    } finally {
      setTestingId(null);
    }
  };

  const handleTriggerSync = async () => {
    setSyncing(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/mcp/connectors/sync`, { method: 'POST' });
      if (res.ok) {
        const d = await res.json();
        showToast(`✓ Schema sync complete. Synced ${d.synced_objects_count} objects.`);
        loadData();
      }
    } finally {
      setSyncing(false);
    }
  };

  const parseJsonObject = (value: string, label: string): Record<string, string> => {
    if (!value.trim()) return {};
    const parsed = JSON.parse(value);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(`${label} must be a JSON object.`);
    }
    return Object.fromEntries(Object.entries(parsed).map(([key, item]) => [key, String(item)]));
  };

  const handleAddExternalServer = async () => {
    if (!serverName.trim()) return;
    setServerSaving(true);
    try {
      const body: Record<string, any> = {
        name: serverName.trim(),
        slug: serverSlug.trim() || undefined,
        transport: serverTransport,
        endpoint: serverTransport === 'stdio' ? undefined : serverEndpoint.trim(),
        command: serverTransport === 'stdio' ? serverCommand.trim() : undefined,
        args: serverTransport === 'stdio' ? serverArgs.split(/\s+/).filter(Boolean) : [],
        headers: parseJsonObject(serverHeaders, 'Headers'),
        env: parseJsonObject(serverEnv, 'Environment'),
      };
      const res = await fetchWithAuth(`${API_URL}/mcp/servers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Failed to add MCP server.');
      setExternalServers((current) => [data, ...current]);
      setServerDialogOpen(false);
      setServerName('');
      setServerSlug('');
      setServerEndpoint('');
      setServerCommand('');
      setServerArgs('');
      setServerHeaders('');
      setServerEnv('');
      showToast('✓ External MCP server added.');
    } catch (error: any) {
      showToast(error?.message || 'Failed to add MCP server.', 'err');
    } finally {
      setServerSaving(false);
    }
  };

  const handleTestExternalServer = async (serverId: string) => {
    setTestingServerId(serverId);
    try {
      const res = await fetchWithAuth(`${API_URL}/mcp/servers/${serverId}/test`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'MCP connection failed.');
      setExternalServers((current) => current.map((server) => server.id === serverId ? data.server : server));
      showToast(`✓ Connected. Discovered ${(data.tools || []).length} tools.`);
    } catch (error: any) {
      showToast(error?.message || 'MCP connection failed.', 'err');
    } finally {
      setTestingServerId(null);
    }
  };

  const handleDeleteExternalServer = async (serverId: string) => {
    if (!confirm('Remove this external MCP server? Its stored connection configuration will be deleted.')) return;
    const res = await fetchWithAuth(`${API_URL}/mcp/servers/${serverId}`, { method: 'DELETE' });
    if (res.ok) {
      setExternalServers((current) => current.filter((server) => server.id !== serverId));
      showToast('External MCP server removed.');
    } else {
      showToast('Failed to remove external MCP server.', 'err');
    }
  };

  const copyToClipboard = (text: string, type: 'key' | 'config') => {
    navigator.clipboard.writeText(text);
    if (type === 'key') {
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    } else {
      setCopiedConfig(true);
      setTimeout(() => setCopiedConfig(false), 2000);
    }
  };

  const generateClientConfigSnippet = (clientKey: string, transport: 'streamable_http' | 'stdio' | string) => {
    const keyPlaceholder = newKeyData?.raw_key || 'octa_mcp_YOUR_SECRET_KEY';
    const baseUrl = API_URL.replace('/api/v1', '');

    if (clientKey === 'chatgpt') {
      return JSON.stringify(
        {
          openApiSchemaUrl: `${baseUrl}/api/v1/plugin/openapi.json`,
          manifestUrl: `${baseUrl}/.well-known/ai-plugin.json`,
          authentication: {
            type: 'API Key',
            authType: 'Bearer',
            apiKey: keyPlaceholder,
          },
          supportedCapabilities: [
            'octaos_delegate_ai_employee',
            'octaos_social_publish_post',
            'octaos_upload_media_or_document',
            'octaos_query_ai_workforce',
          ],
        },
        null,
        2
      );
    } else if (clientKey === 'grok_deepseek') {
      return `# Grok / DeepSeek / Kimi Python Tool Calling
import requests

OCTAOS_KEY = "${keyPlaceholder}"
headers = {"Authorization": f"Bearer {OCTAOS_KEY}"}

# Example: Command Marketing AI to post an Instagram launch video
response = requests.post(
    "${baseUrl}/api/v1/plugin/gateway/execute",
    headers=headers,
    json={
        "tool": "octaos_social_publish_post",
        "arguments": {
            "platform": "instagram",
            "media_url": "https://example.com/launch_video.mp4",
            "media_type": "video",
            "content": "Autonomous product launch video! 🚀",
            "auto_optimize_with_marketing_ai": True,
        },
    },
)
print(response.json())`;
    } else if (clientKey === 'inhouse') {
      return `# In-House System: Direct Multipart Media Upload & Publishing
curl -X POST "${baseUrl}/api/v1/plugin/gateway/execute" \\
  -H "Authorization: Bearer ${keyPlaceholder}" \\
  -F "tool=octaos_social_publish_post" \\
  -F "platform=instagram" \\
  -F "content=Direct video upload from internal ERP system" \\
  -F "media_type=video" \\
  -F "auto_optimize_with_marketing_ai=true" \\
  -F "file=@launch_video.mp4"`;
    } else if (transport === 'stdio') {
      return JSON.stringify(
        {
          mcpServers: {
            octaos: {
              command: 'python3',
              args: ['-m', 'app.mcp_server', '--api-key', keyPlaceholder],
              cwd: '/path/to/octaos/OctaOsautomation',
            },
          },
        },
        null,
        2
      );
    } else {
      return JSON.stringify(
        {
          mcpServers: {
            octaos: {
              url: `${baseUrl}/api/v1/mcp/stream`,
              headers: {
                Authorization: `Bearer ${keyPlaceholder}`,
              },
            },
          },
        },
        null,
        2
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 flex items-center gap-2.5 px-4 py-3 rounded-lg text-xs font-medium shadow-2xl transition-all border ${
            toast.type === 'ok'
              ? 'bg-emerald-950/90 text-emerald-200 border-emerald-700/50'
              : 'bg-red-950/90 text-red-200 border-red-700/50'
          }`}
        >
          {toast.type === 'ok' ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
          <span>{toast.msg}</span>
        </div>
      )}

      {/* Banner / Header */}
      <div className="rounded-xl border border-indigo-500/20 bg-gradient-to-r from-indigo-950/30 via-purple-950/20 to-zinc-900 p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Enterprise Protocol Gateway
            </span>
            <span className="text-zinc-500 text-xs">•</span>
            <span className="text-zinc-400 text-xs font-mono">MCP Specification 2024-11-05</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
            OctaOS Governed Dynamic MCP Hub
          </h2>
          <p className="text-xs text-zinc-300 max-w-2xl leading-relaxed">
            Allow external AI assistants (Claude Desktop, Cursor, Windsurf, Zed, LangChain, custom agents) and automation platforms to discover business capabilities, inspect schema metadata, and execute full CRUD operations under strict multi-tenant isolation and field-level permissions.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            onClick={handleTriggerSync}
            disabled={syncing}
            variant="outline"
            size="sm"
            className="h-9 border-white/10 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 text-xs font-medium gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin text-indigo-400' : ''}`} />
            Sync Schemas
          </Button>

          <Button
            onClick={() => {
              setWizardStep(1);
              setWizardOpen(true);
            }}
            size="sm"
            className="h-9 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium gap-2 shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-3.5 h-3.5" />
            Connect New AI / Client
          </Button>
        </div>
      </div>

      {/* External MCP Server Registry */}
      <div className="rounded-xl border border-indigo-500/20 bg-[#111318] overflow-hidden">
        <div className="p-4 border-b border-white/[0.08] flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-white">External MCP Servers</h3>
              <span className="text-xs font-mono text-zinc-400">({externalServers.length})</span>
            </div>
            <p className="text-[11px] text-zinc-400 mt-1">
              Add any compatible MCP server by URL or stdio command. Provider names are not hardcoded.
            </p>
          </div>
          <Button
            onClick={() => setServerDialogOpen(true)}
            size="sm"
            className="h-8 bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> Add MCP Server
          </Button>
        </div>

        {externalServers.length === 0 ? (
          <div className="p-6 text-center text-zinc-500 text-xs">
            No external MCP servers connected yet. Add a remote HTTP/SSE server or a local stdio server.
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {externalServers.map((server) => (
              <div key={server.id} className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${server.status === 'active' ? 'bg-emerald-400' : server.status === 'degraded' ? 'bg-amber-400' : 'bg-zinc-600'}`} />
                    <span className="text-sm font-medium text-white">{server.name}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">{server.transport}</span>
                    <span className="text-[10px] font-mono text-zinc-500">{server.slug}</span>
                  </div>
                  <p className="mt-1 text-[11px] text-zinc-400 truncate max-w-3xl">{server.target || 'Configured stdio server'}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    onClick={() => handleTestExternalServer(server.id)}
                    disabled={testingServerId === server.id}
                    variant="outline"
                    size="sm"
                    className="h-7 text-[11px] border-white/10 hover:bg-zinc-800 text-zinc-300"
                  >
                    {testingServerId === server.id ? 'Testing...' : 'Discover Tools'}
                  </Button>
                  <Button
                    onClick={() => handleDeleteExternalServer(server.id)}
                    variant="ghost"
                    size="sm"
                    className="h-7 text-[11px] text-red-400 hover:text-red-300 hover:bg-red-950/30"
                  >
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Setup Cards for Clients */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          { id: 'claude_desktop', name: 'Claude Desktop & Code', desc: 'Anthropic Claude Desktop via Stdio Pipe / Remote MCP', icon: Cpu },
          { id: 'chatgpt', name: 'ChatGPT Custom GPTs', desc: 'OpenAPI 3.1 Actions & ChatGPT Plugin Manifest', icon: Sparkles },
          { id: 'grok_deepseek', name: 'Grok / DeepSeek / Kimi', desc: 'xAI & OpenAI-compatible Tool Calling & Python SDK', icon: Globe },
          { id: 'cursor', name: 'Cursor & Windsurf', desc: 'AI code editors with native MCP tool calling', icon: Code2 },
          { id: 'inhouse', name: 'In-House Software', desc: 'REST & Multipart Media Ingestion Gateway', icon: Layers },
        ].map((item) => (
          <div
            key={item.id}
            onClick={() => {
              setSelectedClient(item.id);
              setSelectedTransport(item.id === 'claude_desktop' || item.id === 'cursor' ? 'stdio' : 'streamable_http');
              setWizardStep(2);
              setWizardOpen(true);
            }}
            className="cursor-pointer rounded-xl border border-white/[0.08] bg-[#111318] p-4 hover:border-indigo-500/40 hover:bg-zinc-900/60 transition-all flex flex-col justify-between group"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 rounded-lg bg-zinc-800/80 border border-white/5 text-indigo-400 group-hover:text-indigo-300">
                <item.icon className="w-4 h-4" />
              </div>
              <span className="text-[10px] font-mono text-zinc-500 group-hover:text-indigo-400 flex items-center gap-1">
                One-Click <ArrowRight className="w-3 h-3" />
              </span>
            </div>
            <div>
              <div className="text-sm font-semibold text-white">{item.name}</div>
              <div className="text-xs text-zinc-400 mt-0.5">{item.desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Active MCP Credentials Table */}
      <div className="rounded-xl border border-white/[0.08] bg-[#111318] overflow-hidden">
        <div className="p-4 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white">Active MCP Client Credentials</h3>
            <span className="text-xs font-mono text-zinc-400">({credentials.length})</span>
          </div>
          <span className="text-xs text-zinc-400">
            Keys are scoped to your isolated tenant and governed by the Policy Kernel.
          </span>
        </div>

        {credentials.length === 0 ? (
          <div className="p-8 text-center text-zinc-500 text-xs">
            No MCP credentials generated yet. Click &quot;Connect New AI / Client&quot; above to get started.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/50 text-zinc-400 font-mono text-[11px] border-b border-white/5">
                <tr>
                  <th className="py-3 px-4">Credential Name</th>
                  <th className="py-3 px-4">Client Type</th>
                  <th className="py-3 px-4">Key Prefix</th>
                  <th className="py-3 px-4">Role / Scope</th>
                  <th className="py-3 px-4">Last Connected</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-zinc-300">
                {credentials.map((c) => (
                  <tr key={c.id} className="hover:bg-zinc-800/20 transition-colors">
                    <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${c.is_active ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
                      {c.name}
                    </td>
                    <td className="py-3 px-4 font-mono text-zinc-400">{c.client_type}</td>
                    <td className="py-3 px-4 font-mono text-indigo-300">{c.key_prefix}...</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-zinc-800 border border-white/10 text-zinc-300">
                        {c.role}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-zinc-400 font-mono text-[11px]">
                      {c.last_used_at ? new Date(c.last_used_at).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <Button
                        onClick={() => handleTestConnection(c.id)}
                        disabled={testingId === c.id}
                        variant="outline"
                        size="sm"
                        className="h-7 text-[11px] border-white/10 hover:bg-zinc-800 text-zinc-300"
                      >
                        {testingId === c.id ? 'Testing...' : 'Test'}
                      </Button>
                      <Button
                        onClick={() => handleRevoke(c.id)}
                        variant="ghost"
                        size="sm"
                        className="h-7 text-[11px] text-red-400 hover:text-red-300 hover:bg-red-950/30"
                      >
                        Revoke
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {testResult && (
          <div className={`p-3 border-t text-xs font-mono flex items-center gap-2 ${testResult.ok ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300' : 'bg-red-950/30 border-red-800/40 text-red-300'}`}>
            {testResult.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
            <span>{testResult.msg}</span>
          </div>
        )}
      </div>

      {/* Discovered Dynamic Catalog Section */}
      <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white">Discovered Dynamic Capabilities & Objects</h3>
          </div>
          <span className="text-xs font-mono text-zinc-500">
            Runtime JSON Schema Validation • No Hardcoded Pydantic Models
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {connectors.flatMap((c) =>
            (c.objects || []).map((o: DiscoveredObject) => (
              <div key={o.object_name} className="p-3.5 rounded-lg border border-white/5 bg-zinc-900/60 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white capitalize">{o.display_name}</span>
                  <span className="text-[10px] font-mono text-zinc-400 px-1.5 py-0.5 rounded bg-zinc-800">
                    {o.object_name}
                  </span>
                </div>
                <p className="text-[11px] text-zinc-400 line-clamp-2">{o.description}</p>
                <div className="flex flex-wrap gap-1 pt-1">
                  {o.supported_operations.map((op) => (
                    <span key={op} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {op}
                    </span>
                  ))}
                </div>
              </div>
            ))
          )}
      </div>

      {/* Bidirectional Universal AI Collaboration Engine Section */}
      <div className="rounded-xl border border-purple-500/20 bg-[#111318] p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-white">Bidirectional Universal AI Collaboration Engine</h3>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
              Two-Way Gateway
            </span>
          </div>
          <span className="text-xs font-mono text-zinc-500">
            Loop Prevention • Result-to-Execution Bridge • Tenant Isolated
          </span>
        </div>

        <p className="text-xs text-zinc-400 leading-relaxed">
          OctaOS AI Employees (Sales AI, Marketing AI, Support AI, HR AI, CEO AI) can collaborate with connected frontier models (Claude, Grok, ChatGPT, DeepSeek) on deep reasoning and market research, while external models can safely delegate execution tasks to OctaOS with human-in-the-loop policy gates.
        </p>

        {/* Connected AI Providers Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
          {(collaborationProviders.length > 0 ? collaborationProviders : [
            { provider: 'anthropic', display_name: 'Anthropic Claude', default_model: 'claude-3-7-sonnet', status: 'not_configured', is_connected: false, supported_capabilities: ['deep_coding', 'complex_reasoning', 'document_analysis'], cost_ceiling_usd: 50 },
            { provider: 'grok', display_name: 'xAI Grok', default_model: 'grok-2-1212', status: 'not_configured', is_connected: false, supported_capabilities: ['realtime_research', 'market_analysis', 'vision'], cost_ceiling_usd: 30 },
            { provider: 'openai', display_name: 'OpenAI ChatGPT / o1', default_model: 'gpt-4o', status: 'not_configured', is_connected: false, supported_capabilities: ['reasoning', 'coding', 'tools'], cost_ceiling_usd: 50 },
            { provider: 'deepseek', display_name: 'DeepSeek AI', default_model: 'deepseek-chat', status: 'not_configured', is_connected: false, supported_capabilities: ['deep_reasoning', 'mathematical_logic'], cost_ceiling_usd: 20 },
          ]).map((prov: any) => (
            <div key={prov.provider} className="p-3.5 rounded-lg border border-white/5 bg-zinc-900/60 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white">{prov.display_name}</span>
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-medium ${prov.is_connected ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/50' : 'bg-zinc-800 text-zinc-400'}`}>
                  {prov.is_connected ? '● Connected' : '○ Not Configured'}
                </span>
              </div>
              <div className="text-[10px] font-mono text-zinc-400">
                Model: <span className="text-zinc-200">{prov.default_model}</span>
              </div>
              <div className="flex flex-wrap gap-1 pt-1">
                {(prov.supported_capabilities || []).slice(0, 3).map((cap: string) => (
                  <span key={cap} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
                    {cap}
                  </span>
                ))}
              </div>
              <div className="pt-1 flex items-center justify-between text-[10px] font-mono text-zinc-500 border-t border-white/5">
                <span>Ceiling: ${prov.cost_ceiling_usd || 20}/task</span>
                <span>{prov.data_sharing_scope || 'anonymized'}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Collaboration Pipeline Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          <div className="p-3 rounded-lg border border-white/5 bg-zinc-900/40 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-indigo-300">
              <ArrowRight className="w-3.5 h-3.5" /> 1. Outbound Delegation
            </div>
            <p className="text-[11px] text-zinc-400">
              Sales AI & Marketing AI discover active providers, redact sensitive tenant context, and delegate complex research or coding subtasks.
            </p>
          </div>
          <div className="p-3 rounded-lg border border-white/5 bg-zinc-900/40 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-300">
              <Shield className="w-3.5 h-3.5" /> 2. Result-to-Execution Bridge
            </div>
            <p className="text-[11px] text-zinc-400">
              External AI proposals are evaluated by PolicyEngine. High-risk actions require human approval; executed tools log concrete verification evidence.
            </p>
          </div>
          <div className="p-3 rounded-lg border border-white/5 bg-zinc-900/40 space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-amber-300">
              <ShieldAlert className="w-3.5 h-3.5" /> 3. Loop & Cycle Guard
            </div>
            <p className="text-[11px] text-zinc-400">
              Maximum delegation depth of 3, max 5 child tasks per parent, duplicate task fingerprinting, and lineage cycle prevention ensure zero runaway costs.
            </p>
          </div>
        </div>
      </div>

      {/* Add External MCP Server Modal */}
      <Dialog open={serverDialogOpen} onOpenChange={setServerDialogOpen}>
        <DialogContent className="sm:max-w-xl bg-zinc-950 border border-indigo-500/30 text-white">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Globe className="w-4 h-4 text-indigo-400" /> Add External MCP Server
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Connect any MCP-compatible server. HTTP/SSE headers and stdio environment variables are encrypted at rest.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Display Name</label>
                <Input value={serverName} onChange={(event) => setServerName(event.target.value)} placeholder="HeyGen MCP" className="bg-zinc-900 border-white/10 text-xs text-white" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Slug (optional)</label>
                <Input value={serverSlug} onChange={(event) => setServerSlug(event.target.value)} placeholder="heygen" className="bg-zinc-900 border-white/10 text-xs text-white" />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Transport</label>
              <select
                value={serverTransport}
                onChange={(event) => setServerTransport(event.target.value as 'streamable_http' | 'sse' | 'stdio')}
                className="w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 text-xs text-white"
              >
                <option value="streamable_http">Streamable HTTP</option>
                <option value="sse">Legacy SSE</option>
                <option value="stdio">Local stdio</option>
              </select>
            </div>

            {serverTransport === 'stdio' ? (
              <>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-300">Command</label>
                  <Input value={serverCommand} onChange={(event) => setServerCommand(event.target.value)} placeholder="npx -y @provider/mcp-server" className="bg-zinc-900 border-white/10 text-xs text-white font-mono" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-300">Arguments (space separated)</label>
                  <Input value={serverArgs} onChange={(event) => setServerArgs(event.target.value)} placeholder="--api-key $MCP_API_KEY" className="bg-zinc-900 border-white/10 text-xs text-white font-mono" />
                </div>
              </>
            ) : (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Server Endpoint</label>
                <Input value={serverEndpoint} onChange={(event) => setServerEndpoint(event.target.value)} placeholder="https://provider.example.com/mcp" className="bg-zinc-900 border-white/10 text-xs text-white font-mono" />
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Headers JSON (optional)</label>
                <textarea value={serverHeaders} onChange={(event) => setServerHeaders(event.target.value)} placeholder={'{"Authorization":"Bearer ..."}'} className="min-h-20 w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 text-[11px] text-white font-mono" />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Environment JSON (stdio)</label>
                <textarea value={serverEnv} onChange={(event) => setServerEnv(event.target.value)} placeholder={'{"API_KEY":"..."}'} className="min-h-20 w-full rounded-md border border-white/10 bg-zinc-900 px-3 py-2 text-[11px] text-white font-mono" />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
            <Button variant="ghost" size="sm" onClick={() => setServerDialogOpen(false)} className="text-zinc-400 text-xs">Cancel</Button>
            <Button size="sm" disabled={serverSaving || !serverName.trim()} onClick={handleAddExternalServer} className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs">
              {serverSaving ? 'Adding...' : 'Add MCP Server'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* One-Click Connect Wizard Modal */}
      <Dialog open={wizardOpen} onOpenChange={setWizardOpen}>
        <DialogContent className="sm:max-w-xl bg-zinc-950 border border-white/10 text-white">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              Connect AI Assistant / Client via MCP
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Configure access credentials, choose transports, and copy setup commands.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Step 1: Client & Transport */}
            <div>
              <label className="text-xs font-medium text-zinc-300 mb-1.5 block">Client & Environment</label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {[
                  { id: 'claude_desktop', label: 'Claude Desktop', transport: 'stdio' },
                  { id: 'chatgpt', label: 'ChatGPT Custom GPT', transport: 'openapi' },
                  { id: 'grok_deepseek', label: 'Grok / DeepSeek', transport: 'gateway' },
                  { id: 'cursor', label: 'Cursor / Windsurf', transport: 'stdio' },
                  { id: 'inhouse', label: 'In-House Software', transport: 'gateway' },
                  { id: 'remote_mcp', label: 'Remote Agent / API', transport: 'streamable_http' },
                ].map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      setSelectedClient(c.id);
                      setSelectedTransport(c.transport as any);
                    }}
                    className={`p-2.5 rounded-lg border text-xs text-left transition-all ${
                      selectedClient === c.id
                        ? 'border-indigo-500 bg-indigo-950/40 text-white font-medium'
                        : 'border-white/5 bg-zinc-900 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Step 2: Key Details & Scoped Role */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300 block">Credential Name</label>
              <Input
                placeholder="e.g. Claude Desktop - Enterprise Workflows"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                className="bg-zinc-900 border-white/10 text-xs text-white"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300 block">Access & Risk Tier</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'read_only', label: 'Read-Only', desc: 'Query and read data only' },
                  { id: 'standard_operator', label: 'Standard Operator', desc: 'Read + Create/Update records' },
                  { id: 'admin', label: 'Admin (Full CRUD)', desc: 'Unrestricted create, update, delete' },
                ].map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setSelectedRole(r.id)}
                    className={`p-2.5 rounded-lg border text-left transition-all ${
                      selectedRole === r.id
                        ? 'border-indigo-500 bg-indigo-950/40 text-white'
                        : 'border-white/5 bg-zinc-900 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <div className="text-xs font-semibold">{r.label}</div>
                    <div className="text-[10px] text-zinc-400 mt-0.5">{r.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-zinc-900/60 border border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" />
                <div>
                  <div className="text-xs font-medium text-white">Field Masking & Privacy</div>
                  <div className="text-[11px] text-zinc-400">Passwords, OTPs, and private keys automatically redacted.</div>
                </div>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                Active
              </span>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
            <Button variant="ghost" size="sm" onClick={() => setWizardOpen(false)} className="text-zinc-400 text-xs">
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!keyName.trim()}
              onClick={handleCreateCredential}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
            >
              Generate Scoped Key
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Newly Generated Key Reveal Dialog */}
      <Dialog open={!!newKeyData} onOpenChange={() => setNewKeyData(null)}>
        <DialogContent className="sm:max-w-xl bg-zinc-950 border border-indigo-500/30 text-white">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold flex items-center gap-2 text-white">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              One-Click MCP Connection Ready!
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Save this secret key now. For your security, OctaOS hashes this token and will not display it again.
            </DialogDescription>
          </DialogHeader>

          {newKeyData && (
            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-zinc-400">OctaOS MCP API Key</label>
                <div className="flex items-center gap-2">
                  <Input
                    readOnly
                    value={newKeyData.raw_key}
                    className="font-mono text-xs bg-zinc-900 border-white/10 text-emerald-300"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(newKeyData.raw_key, 'key')}
                    className="h-9 px-3 border-white/10 bg-zinc-900 text-zinc-300 text-xs gap-1.5"
                  >
                    {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedKey ? 'Copied!' : 'Copy'}
                  </Button>
                </div>
              </div>

              {/* Client Configuration Snippet */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono text-zinc-400">
                    Configuration File Snippet ({selectedClient === 'claude_desktop' ? 'claude_desktop_config.json' : 'mcpServers config'})
                  </label>
                  <button
                    onClick={() => copyToClipboard(generateClientConfigSnippet(selectedClient, selectedTransport), 'config')}
                    className="text-[11px] font-mono text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    {copiedConfig ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    {copiedConfig ? 'Copied' : 'Copy JSON'}
                  </button>
                </div>
                <pre className="p-3 rounded-lg bg-black border border-white/10 font-mono text-[11px] text-zinc-300 overflow-x-auto">
                  {generateClientConfigSnippet(selectedClient, selectedTransport)}
                </pre>
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2 border-t border-white/10">
            <Button
              size="sm"
              onClick={() => setNewKeyData(null)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
            >
              Done & Save
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

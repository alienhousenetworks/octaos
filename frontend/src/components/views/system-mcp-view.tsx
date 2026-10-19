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
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

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
      const [credsRes, catRes, connRes] = await Promise.allSettled([
        fetchWithAuth(`${API_URL}/mcp/credentials`),
        fetchWithAuth(`${API_URL}/mcp/catalog`),
        fetchWithAuth(`${API_URL}/mcp/connectors`),
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

  const generateClientConfigSnippet = (clientKey: string, transport: 'streamable_http' | 'stdio') => {
    const keyPlaceholder = newKeyData?.raw_key || 'octa_mcp_YOUR_SECRET_KEY';
    const baseUrl = API_URL.replace('/api/v1', '');

    if (transport === 'stdio') {
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

      {/* Quick Setup Cards for Clients */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { id: 'claude_desktop', name: 'Claude Desktop', desc: 'Anthropic Desktop App via local Stdio Pipe', icon: Cpu },
          { id: 'cursor', name: 'Cursor / Windsurf', desc: 'AI code editors with native MCP tool calling', icon: Code2 },
          { id: 'remote_mcp', name: 'Streamable HTTP', desc: 'Remote AI agents & external automation platforms', icon: Globe },
          { id: 'n8n_zapier', name: 'n8n & Webhooks', desc: 'Workflow engines with JSON-RPC tool calling', icon: Layers },
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
      </div>

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
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'claude_desktop', label: 'Claude Desktop', transport: 'stdio' },
                  { id: 'cursor', label: 'Cursor / Windsurf', transport: 'stdio' },
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

'use client';

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

type Connection = {
  id: string;
  name: string;
  endpoint_url: string;
  auth_type: "bearer" | "hmac" | "custom_header";
  has_secret: boolean;
  custom_header_name?: string | null;
  enabled: boolean;
  description?: string | null;
  last_tested_at?: string | null;
  last_test_status?: number | null;
  created_at?: string | null;
  subscriptions: string[];
};

type Delivery = {
  id: string;
  connection_id?: string | null;
  event_type: string;
  correlation_id?: string | null;
  status: string;
  attempt_count: number;
  last_http_status?: number | null;
  last_error?: string | null;
  delivered_at?: string | null;
  created_at?: string | null;
};

const AVAILABLE_EVENTS = [
  { id: "lead.created", label: "lead.created", desc: "Triggered whenever a verified lead is created or ingested" },
  { id: "lead.status_changed", label: "lead.status_changed", desc: "Fired upon CRM lead stage transitions" },
  { id: "command.issued", label: "command.issued", desc: "Direct instructions or task delegations sent to this agent" },
  { id: "activity.recorded", label: "activity.recorded", desc: "Workforce activity updates and status logs" },
  { id: "*", label: "* (All Events)", desc: "Subscribe to all current and future webhook event categories" },
];

function apiBase() {
  let configured = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  while (configured.endsWith("/")) configured = configured.slice(0, -1);
  if (!configured.endsWith("/api/v1")) configured += "/api/v1";
  return configured;
}

function bearerToken() {
  if (typeof window === "undefined") return "";
  return (
    localStorage.getItem("access_token") ||
    localStorage.getItem("accessToken") ||
    localStorage.getItem("octaos_access_token") ||
    localStorage.getItem("token") ||
    ""
  );
}

export default function ExternalAgentsPage() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [authType, setAuthType] = useState<"bearer" | "hmac" | "custom_header">("bearer");
  const [authSecret, setAuthSecret] = useState("");
  const [customHeaderName, setCustomHeaderName] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [description, setDescription] = useState("");
  const [selectedSubs, setSelectedSubs] = useState<string[]>(["lead.created", "command.issued"]);

  // Test status & latency tracking
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, { success: boolean; latency_ms: number; status_code: number; error?: string }>>({});

  // Command modal
  const [commandModalOpen, setCommandModalOpen] = useState(false);
  const [targetConnectionId, setTargetConnectionId] = useState("");
  const [commandText, setCommandText] = useState("");

  const request = useCallback(async (path: string, init: RequestInit = {}) => {
    const token = bearerToken();
    const response = await fetch(`${apiBase()}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers || {}),
      },
      cache: "no-store",
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${response.status})`);
    }
    return response.json();
  }, []);

  const refresh = useCallback(async () => {
    setError("");
    try {
      const conns = await request("/integrations/external-agents/connections");
      setConnections(conns || []);
      const dels = await request("/integrations/external-agents/deliveries?limit=15");
      setDeliveries(dels.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load external agent connections.");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openCreateDrawer = () => {
    setEditingId(null);
    setName("");
    setEndpointUrl("");
    setAuthType("bearer");
    setAuthSecret("");
    setCustomHeaderName("");
    setEnabled(true);
    setDescription("");
    setSelectedSubs(["lead.created", "command.issued"]);
    setDrawerOpen(true);
  };

  const openEditDrawer = (conn: Connection) => {
    setEditingId(conn.id);
    setName(conn.name);
    setEndpointUrl(conn.endpoint_url);
    setAuthType(conn.auth_type);
    setAuthSecret("");
    setCustomHeaderName(conn.custom_header_name || "");
    setEnabled(conn.enabled);
    setDescription(conn.description || "");
    setSelectedSubs(conn.subscriptions || []);
    setDrawerOpen(true);
  };

  const saveConnection = async () => {
    if (!name.trim() || !endpointUrl.trim()) {
      setError("Connection name and endpoint URL are required.");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");

    const payload: any = {
      name: name.trim(),
      endpoint_url: endpointUrl.trim(),
      auth_type: authType,
      custom_header_name: authType === "custom_header" ? customHeaderName.trim() : null,
      enabled,
      description: description.trim(),
      subscriptions: selectedSubs,
    };
    if (authSecret.trim()) {
      payload.auth_secret = authSecret.trim();
    }

    try {
      if (editingId) {
        await request(`/integrations/external-agents/connections/${editingId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        setMessage("Connection updated successfully.");
      } else {
        await request("/integrations/external-agents/connections", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setMessage("New external agent connection registered.");
      }
      setDrawerOpen(false);
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save connection.");
    } finally {
      setBusy(false);
    }
  };

  const deleteConnection = async (id: string, connName: string) => {
    if (!confirm(`Are you sure you want to remove the external agent connection "${connName}"?`)) return;
    setBusy(true);
    try {
      await request(`/integrations/external-agents/connections/${id}`, { method: "DELETE" });
      setMessage(`Deleted connection "${connName}".`);
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete connection.");
    } finally {
      setBusy(false);
    }
  };

  const testPing = async (id: string) => {
    setTestingId(id);
    setError("");
    try {
      const res = await request(`/integrations/external-agents/connections/${id}/test`, { method: "POST" });
      setTestResult((prev) => ({
        ...prev,
        [id]: {
          success: res.success,
          latency_ms: res.latency_ms,
          status_code: res.status_code,
          error: res.error,
        },
      }));
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Test ping failed.");
    } finally {
      setTestingId(null);
    }
  };

  const replayDelivery = async (id: string) => {
    setBusy(true);
    try {
      await request(`/integrations/external-agents/deliveries/${id}/replay`, { method: "POST" });
      setMessage(`Delivery ${id.slice(0, 8)}... replayed.`);
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Replay failed.");
    } finally {
      setBusy(false);
    }
  };

  const sendCommand = async () => {
    if (!commandText.trim()) return;
    setBusy(true);
    setError("");
    try {
      await request("/integrations/external-agents/commands", {
        method: "POST",
        body: JSON.stringify({
          connection_id: targetConnectionId || null,
          command: commandText.trim(),
        }),
      });
      setMessage("Command dispatched to external controller.");
      setCommandModalOpen(false);
      setCommandText("");
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to issue command.");
    } finally {
      setBusy(false);
    }
  };

  const toggleSubscription = (eventId: string) => {
    setSelectedSubs((prev) =>
      prev.includes(eventId) ? prev.filter((id) => id !== eventId) : [...prev, eventId]
    );
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6 pb-24">
      {/* Top Breadcrumb & Title */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <nav className="mb-2 text-xs text-muted-foreground">
            <Link href="/settings/integrations" className="hover:underline">Integrations</Link>
            <span className="mx-2">/</span>
            <span className="text-foreground">External Agents & Webhooks</span>
          </nav>
          <h1 className="text-2xl font-bold tracking-tight">External Agent Controllers & Webhooks</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Connect any AI controller (Grok Bot, Claude/ChatGPT agents, n8n, Zapier, custom bots) with bidirectional event streams, commands, and media transfer.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setTargetConnectionId("");
              setCommandModalOpen(true);
            }}
            className="rounded-xl border border-primary/40 px-4 py-2 text-sm font-medium hover:bg-primary/5"
          >
            Dispatch Command
          </button>
          <button
            type="button"
            onClick={openCreateDrawer}
            className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm hover:opacity-90"
          >
            + Add External Agent
          </button>
        </div>
      </div>

      {error && <div role="alert" className="rounded-xl border border-red-500/40 bg-red-500/5 p-4 text-sm text-red-600">{error}</div>}
      {message && <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 text-sm text-emerald-600">{message}</div>}

      {/* Connections List */}
      <section className="rounded-2xl border p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b">
          <div>
            <h2 className="text-lg font-semibold">Registered Controllers & Webhook Targets</h2>
            <p className="text-xs text-muted-foreground">Signed HMAC-SHA256 deliveries with automatic exponential retry backoff.</p>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={busy}
            className="rounded-lg border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-muted-foreground">Loading connections...</div>
        ) : connections.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm text-muted-foreground">No external agents connected yet.</p>
            <button
              type="button"
              onClick={openCreateDrawer}
              className="mt-4 rounded-xl border border-dashed px-4 py-2 text-xs font-medium hover:bg-muted"
            >
              Configure your first webhook controller
            </button>
          </div>
        ) : (
          <div className="mt-4 divide-y">
            {connections.map((c) => {
              const test = testResult[c.id];
              return (
                <div key={c.id} className="py-4 first:pt-0 last:pb-0 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-base">{c.name}</h3>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${c.enabled ? "bg-emerald-500/10 text-emerald-600" : "bg-muted text-muted-foreground"}`}>
                        {c.enabled ? "Active" : "Disabled"}
                      </span>
                      <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-600 uppercase">
                        {c.auth_type}
                      </span>
                    </div>
                    <p className="font-mono text-xs text-muted-foreground break-all">{c.endpoint_url}</p>
                    {c.description && <p className="text-xs text-muted-foreground">{c.description}</p>}
                    <div className="flex flex-wrap gap-1 pt-1">
                      {c.subscriptions.map((s) => (
                        <span key={s} className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-mono text-muted-foreground">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-center">
                    {test && (
                      <span className={`text-xs px-2 py-1 rounded font-mono ${test.success ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
                        {test.success ? `200 OK (${test.latency_ms}ms)` : `Err ${test.status_code || test.error}`}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={() => void testPing(c.id)}
                      disabled={testingId === c.id}
                      className="rounded-lg border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
                    >
                      {testingId === c.id ? "Pinging..." : "Test ping"}
                    </button>
                    <button
                      type="button"
                      onClick={() => openEditDrawer(c)}
                      className="rounded-lg border px-3 py-1.5 text-xs font-medium hover:bg-muted"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => void deleteConnection(c.id, c.name)}
                      className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-500/5"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Outbound Delivery Log */}
      <section className="rounded-2xl border p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b">
          <div>
            <h2 className="text-lg font-semibold">Live Outbound Delivery Log</h2>
            <p className="text-xs text-muted-foreground">Recent event dispatches, HTTP statuses, and idempotency states.</p>
          </div>
        </div>

        {deliveries.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground">No deliveries recorded yet.</div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b text-muted-foreground">
                <tr>
                  <th className="pb-2 font-medium">Delivery ID</th>
                  <th className="pb-2 font-medium">Event</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Attempts</th>
                  <th className="pb-2 font-medium">HTTP Code</th>
                  <th className="pb-2 font-medium">Timestamp</th>
                  <th className="pb-2 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {deliveries.map((d) => (
                  <tr key={d.id} className="hover:bg-muted/30">
                    <td className="py-2.5 font-mono">{d.id.slice(0, 14)}...</td>
                    <td className="py-2.5 font-mono font-medium">{d.event_type}</td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        d.status === "delivered" ? "bg-emerald-500/10 text-emerald-600" :
                        d.status === "pending" ? "bg-amber-500/10 text-amber-600" : "bg-red-500/10 text-red-600"
                      }`}>
                        {d.status}
                      </span>
                    </td>
                    <td className="py-2.5">{d.attempt_count}</td>
                    <td className="py-2.5 font-mono">{d.last_http_status || "—"}</td>
                    <td className="py-2.5 text-muted-foreground">{d.created_at ? new Date(d.created_at).toLocaleTimeString() : "—"}</td>
                    <td className="py-2.5 text-right">
                      <button
                        type="button"
                        onClick={() => void replayDelivery(d.id)}
                        disabled={busy}
                        className="rounded border px-2 py-1 text-[11px] font-medium hover:bg-muted"
                      >
                        Replay
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Inbound Integration Instructions Guide */}
      <section className="rounded-2xl border p-6 shadow-sm space-y-4">
        <h2 className="text-lg font-semibold">How External Agents Call OctaOS</h2>
        <div className="grid gap-4 md:grid-cols-2 text-xs">
          <div className="rounded-xl border p-4 bg-muted/20 space-y-2">
            <h3 className="font-semibold text-sm">1. Post Inbound Status & Replies</h3>
            <p className="text-muted-foreground">External bots can report execution progress, errors, or final deliverables with attachments.</p>
            <pre className="p-3 rounded-lg bg-zinc-950 text-zinc-100 overflow-x-auto">
{`POST /api/v1/controller/replies
Authorization: Bearer <octa_mcp_key>
Content-Type: application/json

{
  "correlation_id": "cmd_...",
  "kind": "result",
  "title": "Audit Complete",
  "body": "Analysis report generated with recommendations.",
  "attachments": [
    {
      "name": "Audit.pdf",
      "url": "https://storage.octaos.io/...",
      "mime_type": "application/pdf",
      "size_bytes": 1048576
    }
  ]
}`}
            </pre>
          </div>

          <div className="rounded-xl border p-4 bg-muted/20 space-y-2">
            <h3 className="font-semibold text-sm">2. Universal Media & Document Transfer</h3>
            <p className="text-muted-foreground">Transfer any safe file type (CAD, PDF, audio, video, zip, csv) via the MCP tool gateway.</p>
            <pre className="p-3 rounded-lg bg-zinc-950 text-zinc-100 overflow-x-auto">
{`// MCP Tool: octaos_upload_media_or_document
{
  "filename": "quarterly_financials.xlsx",
  "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "content_base64": "<base64_data>",
  "tags": ["finance", "controller_upload"]
}

// MCP Tool: octaos_get_media_or_document
{
  "file_url": "https://...",
  "include_base64": true
}`}
            </pre>
          </div>
        </div>
      </section>

      {/* Sliding Drawer for Create / Edit Connection */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
          <div className="h-full w-full max-w-lg bg-background p-6 shadow-2xl overflow-y-auto space-y-6">
            <div className="flex items-center justify-between border-b pb-4">
              <h2 className="text-lg font-bold">{editingId ? "Edit External Agent" : "Register External Agent"}</h2>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-sm">
              <div>
                <label className="block font-medium mb-1">Controller / Agent Name *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Grok Bot, Claude Ops Agent, n8n Flow"
                  className="w-full rounded-xl border bg-background px-3 py-2"
                />
              </div>

              <div>
                <label className="block font-medium mb-1">Webhook Endpoint URL *</label>
                <input
                  type="url"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  placeholder="https://agent.yourdomain.com/webhook"
                  className="w-full rounded-xl border bg-background px-3 py-2 font-mono text-xs"
                />
                <p className="mt-1 text-[11px] text-muted-foreground">SSRF Guard: Private RFC-1918 IPs and localhost are strictly prohibited.</p>
              </div>

              <div>
                <label className="block font-medium mb-1">Authentication Type</label>
                <select
                  value={authType}
                  onChange={(e) => setAuthType(e.target.value as any)}
                  className="w-full rounded-xl border bg-background px-3 py-2"
                >
                  <option value="bearer">Bearer Token (Authorization: Bearer ...)</option>
                  <option value="hmac">HMAC Signature (X-OctaOS-Signature)</option>
                  <option value="custom_header">Custom Header</option>
                </select>
              </div>

              {authType === "custom_header" && (
                <div>
                  <label className="block font-medium mb-1">Custom Header Name</label>
                  <input
                    type="text"
                    value={customHeaderName}
                    onChange={(e) => setCustomHeaderName(e.target.value)}
                    placeholder="e.g. X-Agent-Token"
                    className="w-full rounded-xl border bg-background px-3 py-2"
                  />
                </div>
              )}

              <div>
                <label className="block font-medium mb-1">Secret / Token</label>
                <input
                  type="password"
                  value={authSecret}
                  onChange={(e) => setAuthSecret(e.target.value)}
                  placeholder={editingId ? "(Leave empty to keep existing encrypted secret)" : "Enter secret key or bearer token"}
                  className="w-full rounded-xl border bg-background px-3 py-2"
                />
                <p className="mt-1 text-[11px] text-muted-foreground">Encrypted at rest using AES-256 Fernet.</p>
              </div>

              <div>
                <label className="block font-medium mb-1">Description (Optional)</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Notes on agent role, maintainer, or capabilities"
                  className="w-full rounded-xl border bg-background px-3 py-2"
                />
              </div>

              <div>
                <label className="block font-medium mb-2">Subscribed Event Types</label>
                <div className="space-y-2 border rounded-xl p-3 bg-muted/20">
                  {AVAILABLE_EVENTS.map((ev) => (
                    <label key={ev.id} className="flex items-start gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedSubs.includes(ev.id)}
                        onChange={() => toggleSubscription(ev.id)}
                        className="mt-1"
                      />
                      <div>
                        <span className="font-mono text-xs font-semibold">{ev.label}</span>
                        <p className="text-[11px] text-muted-foreground">{ev.desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="enabledCheck"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                />
                <label htmlFor="enabledCheck" className="font-medium">Active (dispatch webhooks to this endpoint)</label>
              </div>
            </div>

            <div className="flex justify-end gap-3 border-t pt-4">
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="rounded-xl border px-4 py-2 text-sm font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={saveConnection}
                disabled={busy}
                className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {busy ? "Saving..." : "Save Connection"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Command Dispatch Modal */}
      {commandModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl bg-background p-6 shadow-2xl space-y-4">
            <h2 className="text-lg font-bold">Dispatch Controller Command</h2>
            <p className="text-xs text-muted-foreground">
              Issues a command to external agents via the <code>command.issued</code> webhook event.
            </p>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block font-medium mb-1">Target Controller</label>
                <select
                  value={targetConnectionId}
                  onChange={(e) => setTargetConnectionId(e.target.value)}
                  className="w-full rounded-xl border bg-background px-3 py-2"
                >
                  <option value="">All Subscribed Controllers (*)</option>
                  {connections.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block font-medium mb-1">Directive / Command *</label>
                <textarea
                  rows={4}
                  value={commandText}
                  onChange={(e) => setCommandText(e.target.value)}
                  placeholder="e.g. Audit the latest 5 high-intent leads and return CRO recommendations with report PDF"
                  className="w-full rounded-xl border bg-background px-3 py-2"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setCommandModalOpen(false)}
                className="rounded-xl border px-4 py-2 text-sm font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={sendCommand}
                disabled={busy || !commandText.trim()}
                className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
              >
                {busy ? "Dispatching..." : "Send Command"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

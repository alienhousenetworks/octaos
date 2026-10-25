'use client';

import { useCallback, useEffect, useState } from "react";

type Channel = { id: string; name: string; service: string };
type Organization = { id: string; name: string; channels: Channel[] };
type BufferStatus = { connected: boolean; connection_method?: string | null; connected_at?: string | null; scopes?: string };

function apiBase() {
  const configured = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  while (configured.endsWith("/")) configured = configured.slice(0, -1);
  return configured;
}

function bearerToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("access_token") || localStorage.getItem("token") || "";
}

export default function IntegrationsPage() {
  const [status, setStatus] = useState<BufferStatus | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

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
      const next = await request("/marketing/connectors/buffer/status");
      setStatus(next);
      if (next.connected) {
        const channels = await request("/marketing/connectors/buffer/channels");
        setOrganizations(channels.organizations || []);
      } else {
        setOrganizations([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load Buffer connection.");
    }
  }, [request]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const result = params.get("buffer");
    if (result === "connected") setMessage("Buffer connected. Your channels are being loaded.");
    else if (result) setError(result === "cancelled" ? "Buffer authorization was cancelled." : "Buffer connection failed. Check server OAuth configuration and try again.");
    void refresh();
  }, [refresh]);

  async function connect() {
    setBusy(true);
    setError("");
    try {
      const response = await request("/marketing/connectors/buffer/connect", { method: "GET" });
      if (!response.url) throw new Error("The server did not return the Buffer authorization URL.");
      window.location.assign(response.url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start Buffer OAuth.");
      setBusy(false);
    }
  }

  async function saveApiKey() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await request("/marketing/connectors/buffer/api-key", {
        method: "POST",
        body: JSON.stringify({ api_key: apiKey }),
      });
      setApiKey("");
      setMessage("Buffer API key saved securely. Refreshing connected channels.");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save Buffer API key.");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError("");
    try {
      await request("/marketing/connectors/buffer/disconnect", { method: "DELETE" });
      setStatus({ connected: false });
      setOrganizations([]);
      setMessage("Buffer disconnected from this OctaOS workspace.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not disconnect Buffer.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl space-y-8 px-6 py-10">
      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">OctaOS · Marketing Workforce</p>
        <h1 className="text-3xl font-semibold tracking-tight">Publishing integrations</h1>
        <p className="max-w-2xl text-muted-foreground">Connect Buffer once, choose your connected social channels, and let OctaOS prepare and schedule approved campaign content. Tokens stay on the server.</p>
      </header>

      {error && <div role="alert" className="rounded-xl border border-red-500/40 bg-red-500/5 p-4 text-sm">{error}</div>}
      {message && <div role="status" className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4 text-sm">{message}</div>}

      <section className="rounded-2xl border p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold">Buffer</h2>
            <p className="text-sm text-muted-foreground">OAuth one-click connection is recommended. API-key entry is available as a fallback.</p>
          </div>
          <span className={`inline-flex w-fit items-center rounded-full px-3 py-1 text-xs font-medium ${status?.connected ? "bg-emerald-500/10 text-emerald-700" : "bg-muted text-muted-foreground"}`}>
            {status === null ? "Checking connection…" : status.connected ? "Connected" : "Not connected"}
          </span>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <button type="button" onClick={connect} disabled={busy} className="rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50">
            {busy ? "Please wait…" : status?.connected ? "Reconnect Buffer" : "Connect Buffer"}
          </button>
          <button type="button" onClick={refresh} disabled={busy} className="rounded-xl border px-4 py-2.5 text-sm font-medium disabled:opacity-50">Refresh status</button>
          {status?.connected && <button type="button" onClick={disconnect} disabled={busy} className="rounded-xl border border-red-500/40 px-4 py-2.5 text-sm font-medium text-red-700 disabled:opacity-50">Disconnect</button>}
        </div>

        {status?.connected && (
          <div className="mt-5 grid gap-2 text-sm sm:grid-cols-2">
            <p><span className="text-muted-foreground">Method:</span> {status.connection_method || "OAuth"}</p>
            <p><span className="text-muted-foreground">Granted scopes:</span> {status.scopes || "Not returned"}</p>
          </div>
        )}

        <div className="mt-6 border-t pt-5">
          <details>
            <summary className="cursor-pointer text-sm font-medium">Use an API key instead</summary>
            <p className="mt-2 text-sm text-muted-foreground">Create a key in Buffer Settings → API. The key is sent to OctaOS over HTTPS and encrypted server-side; never paste it into a public issue or chat.</p>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input aria-label="Buffer API key" type="password" autoComplete="off" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Buffer API key" className="min-w-0 flex-1 rounded-xl border bg-background px-3 py-2 text-sm" />
              <button type="button" onClick={saveApiKey} disabled={busy || apiKey.trim().length < 12} className="rounded-xl border px-4 py-2 text-sm font-medium disabled:opacity-50">Save key</button>
            </div>
          </details>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Connected organizations and channels</h2>
          <p className="text-sm text-muted-foreground">These are the accounts Buffer reports for the authorized user. Publishing remains approval-gated.</p>
        </div>
        {!status?.connected ? (
          <div className="rounded-2xl border border-dashed p-8 text-sm text-muted-foreground">Connect Buffer to see the social profiles available to this workspace.</div>
        ) : organizations.length === 0 ? (
          <div className="rounded-2xl border p-8 text-sm text-muted-foreground">No channels were returned. Confirm that social profiles are connected inside Buffer and that the OAuth scopes are granted.</div>
        ) : organizations.map((organization) => (
          <div key={organization.id} className="rounded-2xl border p-5">
            <h3 className="font-semibold">{organization.name}</h3>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {organization.channels.map((channel) => (
                <div key={channel.id} className="rounded-xl bg-muted/50 p-3">
                  <p className="font-medium">{channel.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{channel.service}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}

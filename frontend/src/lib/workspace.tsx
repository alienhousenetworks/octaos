'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { clearSession, fetchWithSession, getAccessToken, saveSession } from '@/lib/auth-session';
import { notify } from '@/lib/notify';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

type Queue = { posts: any[]; leads: any[] };

type WorkspaceValue = {
  ready: boolean;
  token: string | null;
  tenantId: string | null;
  userProfile: any;
  setUserProfile: (profile: any) => void;
  setToken: (token: string | null) => void;
  setTenantId: (tenantId: string | null) => void;
  apiUrl: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  queue: Queue;
  timeline: any[];
  knowledge: any[];
  metrics: any;
  teams: any[];
  setTeams: React.Dispatch<React.SetStateAction<any[]>>;
  apps: any[];
  configuredProviders: string[];
  logoUrl: string | null;
  setLogoUrl: (url: string | null) => void;
  faviconUrl: string | null;
  setFaviconUrl: (url: string | null) => void;
  logout: () => void;
  retainFeed: () => () => void;
  uninstallApp: (appName: string) => Promise<void>;
  handleApprovePost: (postId: string) => Promise<void>;
  handleRejectPost: (postId: string) => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

async function safeJson(res: Response, fallback: any = null) {
  if (!res.ok) return fallback;
  try {
    return await res.json();
  } catch {
    return fallback;
  }
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [token, setTokenState] = useState<string | null>(null);
  const [tenantId, setTenantIdState] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);
  const [queue, setQueue] = useState<Queue>({ posts: [], leads: [] });
  const [timeline, setTimeline] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>({});
  const [teams, setTeams] = useState<any[]>([]);
  const [apps, setApps] = useState<any[]>([]);
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const feedUsers = useRef(0);
  const [feedOn, setFeedOn] = useState(false);
  const profileRef = useRef<any>(null);
  profileRef.current = userProfile;

  const logout = useCallback(() => {
    clearSession();
    setTokenState(null);
    setTenantIdState(null);
    setUserProfile(null);
    router.replace('/');
  }, [router]);

  const fetchWithAuth = useCallback(async (url: string, options: any = {}) => {
    const res = await fetchWithSession(url, options, API_URL);
    const newest = getAccessToken();
    if (newest && newest !== token) setTokenState(newest);
    if (res.status === 401) logout();
    return res;
  }, [logout, token]);

  const fetchData = useCallback(async () => {
    if (!getAccessToken()) return;
    try {
      if (!profileRef.current) {
        try {
          const meRes = await fetchWithAuth(`${API_URL}/auth/me`);
          if (meRes.ok) {
            const meData = await meRes.json();
            setUserProfile(meData);
            if (meData.tenant_id) {
              localStorage.setItem('tenant_id', meData.tenant_id);
              setTenantIdState(meData.tenant_id);
            }
          } else if (meRes.status === 401 || meRes.status === 403) {
            return;
          }
        } catch {
          // Backend temporarily unreachable (starting up or offline)
          return;
        }
      }

      const load = async (path: string, fallback: any) => {
        try {
          const res = await fetchWithAuth(`${API_URL}${path}`);
          return await safeJson(res, fallback);
        } catch {
          return fallback;
        }
      };
      const [queueData, timelineData, knowledgeData, metricsData, teamData, appData, keyStatusData] = await Promise.all([
        load('/commands/queue', { posts: [], leads: [] }),
        load('/commands/timeline', []),
        load('/commands/knowledge', []),
        load('/dashboard/metrics', {}),
        load('/dashboard/teams', []),
        load('/dashboard/marketplace/installed', []),
        load('/commands/keys', {}),
      ]);
      setQueue(queueData && !Array.isArray(queueData) ? queueData : { posts: [], leads: [] });
      setTimeline(Array.isArray(timelineData) ? timelineData : []);
      setKnowledge(Array.isArray(knowledgeData) ? knowledgeData : []);
      setMetrics(metricsData && typeof metricsData === 'object' && !Array.isArray(metricsData) ? metricsData : {});
      setTeams(Array.isArray(teamData) ? teamData : []);
      setApps(Array.isArray(appData) ? appData : []);
      const providers = keyStatusData?.configured_providers || [];
      setConfiguredProviders(providers.map((provider: any) => typeof provider === 'string' ? provider : provider.provider).filter(Boolean));
    } catch (error) {
      console.error(error);
    }
  }, [fetchWithAuth]);

  useEffect(() => {
    const saved = getAccessToken();
    const savedTenant = typeof window !== 'undefined' ? localStorage.getItem('tenant_id') : null;
    if (saved) setTokenState(saved);
    if (savedTenant) setTenantIdState(savedTenant);
    setReady(true);
    fetch(`${API_URL}/auth/settings`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        if (data.logo_url) setLogoUrl(data.logo_url);
        if (data.favicon_url) setFaviconUrl(data.favicon_url);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!faviconUrl) return;
    try {
      const parsed = new URL(faviconUrl);
      if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return;
    } catch {
      return;
    }
    let link: HTMLLinkElement | null = document.querySelector("link[rel~='icon']");
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = faviconUrl;
  }, [faviconUrl]);

  useEffect(() => {
    if (!token) return;
    fetchData();
  }, [token]); // profile + first feed load

  useEffect(() => {
    if (!token || !feedOn) return;
    const interval = window.setInterval(() => { fetchData(); }, 15000);
    return () => window.clearInterval(interval);
  }, [token, feedOn, fetchData]);

  const retainFeed = useCallback(() => {
    feedUsers.current += 1;
    setFeedOn(true);
    return () => {
      feedUsers.current = Math.max(0, feedUsers.current - 1);
      if (feedUsers.current === 0) setFeedOn(false);
    };
  }, []);

  const setToken = useCallback((next: string | null) => {
    setTokenState(next);
    if (next) saveSession({ access_token: next });
  }, []);

  const setTenantId = useCallback((next: string | null) => {
    setTenantIdState(next);
    if (next) localStorage.setItem('tenant_id', next);
  }, []);

  const uninstallApp = useCallback(async (appName: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/marketplace/uninstall`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_name: appName }),
      });
      if (res.ok) {
        await fetchData();
        notify(`${appName} deactivated.`);
      } else {
        notify.error(`Failed to deactivate ${appName}.`);
      }
    } catch (error) {
      console.error(error);
    }
  }, [fetchData, fetchWithAuth]);

  const handleApprovePost = useCallback(async (postId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/approve`, { method: 'POST' });
      if (res.ok) {
        await fetchData();
        notify('Post approved and scheduled. Publish it from Campaigns when the channel keys are connected.');
      }
    } catch (error) {
      console.error(error);
    }
  }, [fetchData, fetchWithAuth]);

  const handleRejectPost = useCallback(async (postId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/reject`, { method: 'POST' });
      if (res.ok) await fetchData();
    } catch (error) {
      console.error(error);
    }
  }, [fetchData, fetchWithAuth]);

  const value = useMemo<WorkspaceValue>(() => ({
    ready,
    token,
    tenantId,
    userProfile,
    setUserProfile,
    setToken,
    setTenantId,
    apiUrl: API_URL,
    fetchWithAuth,
    fetchData,
    queue,
    timeline,
    knowledge,
    metrics,
    teams,
    setTeams,
    apps,
    configuredProviders,
    logoUrl,
    setLogoUrl,
    faviconUrl,
    setFaviconUrl,
    logout,
    retainFeed,
    uninstallApp,
    handleApprovePost,
    handleRejectPost,
  }), [
    ready, token, tenantId, userProfile, setToken, setTenantId, fetchWithAuth, fetchData,
    queue, timeline, knowledge, metrics, teams, apps, configuredProviders, logoUrl, faviconUrl,
    logout, retainFeed, uninstallApp, handleApprovePost, handleRejectPost,
  ]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error('useWorkspace must be used inside WorkspaceProvider');
  return value;
}

export function useWorkspaceFeed(enabled = true) {
  const workspace = useWorkspace();
  useEffect(() => {
    if (!enabled) return;
    return workspace.retainFeed();
  }, [enabled, workspace]);
  return workspace;
}

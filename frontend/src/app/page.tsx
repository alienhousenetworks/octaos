'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { 
  Activity, Users, DollarSign, BarChart3, Briefcase, Zap, BookOpen, 
  LogOut, Calendar, MessageSquare, Clock, TrendingUp, Target, FileText, Key, Video 
} from 'lucide-react';

import KnowledgeView from '@/components/views/knowledge-view';
import DashboardView from '@/components/views/dashboard-view';
import CampaignsView from '@/components/views/campaigns-view';
import SupportView from '@/components/views/support-view';
import OrchestratorView from '@/components/views/orchestrator-view';
import TeamsView from '@/components/views/teams-view';
import MarketplaceView from '@/components/views/marketplace-view';
import InstructionsView from '@/components/views/instructions-view';
import HRView from '@/components/views/hr-view';
import CEOView from '@/components/views/ceo-view';
import CoordinationView from '@/components/views/coordination-view';
import SalesView from '@/components/views/sales-view';
import AIOptimizationView from '@/components/views/ai-optimization-view';
import MembersView from '@/components/views/members-view';
import SystemAdminView from '@/components/views/system-admin-view';
import ApiManagementView from '@/components/views/api-management-view';
import VideoStudioView from '@/components/views/video-studio-view';

import LandingPage from '@/components/landing-page';
import AuthForms from '@/components/auth-forms';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export default function Home() {
  const [appState, setAppState] = useState<'landing' | 'login' | 'signup' | 'app'>('landing');
  const [token, setToken] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);

  const getFilteredNavItems = () => {
    const defaultItems = [
      { id: 'dashboard', name: 'Operating Dashboard', icon: <BarChart3 size={18} />, color: 'hover:text-violet-400 active-glow-violet', section: 'dashboard' },
      { id: 'knowledge', name: 'Knowledge Base', icon: <FileText size={18} />, color: 'hover:text-violet-400 active-glow-violet', section: 'knowledge' },
      { id: 'campaigns', name: 'Campaign Planner', icon: <Calendar size={18} />, color: 'hover:text-indigo-400 active-glow-indigo', section: 'marketing' },
      { id: 'video_studio', name: 'Video Studio AI', icon: <Video size={18} />, color: 'hover:text-rose-400 active-glow-rose', section: 'marketing' },
      { id: 'sales', name: 'Sales CRM', icon: <TrendingUp size={18} />, color: 'hover:text-emerald-400 active-glow-emerald', section: 'sales' },
      { id: 'support', name: 'Customer Support', icon: <MessageSquare size={18} />, color: 'hover:text-blue-400 active-glow-blue', section: 'support' },
      { id: 'coordination', name: 'Agent Boardroom', icon: <Users size={18} />, color: 'hover:text-amber-400 active-glow-amber', section: 'coordination' },
      { id: 'ceo', name: 'CEO Workspace', icon: <Target size={18} />, color: 'hover:text-sky-400 active-glow-sky', section: 'ceo' },
      { id: 'orchestrator', name: 'Orchestrator AI', icon: <Activity size={18} />, color: 'hover:text-purple-400 active-glow-purple', section: 'orchestrator' },
      { id: 'teams', name: 'AI Teams', icon: <Users size={18} />, color: 'hover:text-emerald-400 active-glow-emerald', section: 'teams' },
      { id: 'marketplace', name: 'App Marketplace', icon: <Briefcase size={18} />, color: 'hover:text-pink-400 active-glow-pink', section: 'marketplace' },
      { id: 'hr', name: 'Hiring & HR', icon: <Briefcase size={18} />, color: 'hover:text-amber-400 active-glow-amber', section: 'hr' },
      { id: 'ai_optimization', name: 'AI Cost Control', icon: <DollarSign size={18} />, color: 'hover:text-emerald-400 active-glow-emerald', section: 'ai_optimization' },
    ];

    if (!userProfile) return defaultItems;

    let items = [...defaultItems];

    if (userProfile.role !== 'admin' && !userProfile.is_system_admin) {
      const allowed = userProfile.allowed_sections;
      if (allowed && !allowed.includes('all')) {
        items = items.filter(item => item.id === 'dashboard' || allowed.includes(item.section));
      }
    }

    if (userProfile.role === 'admin' || userProfile.is_system_admin) {
      items.push({
        id: 'members',
        name: 'Members & Access',
        icon: <Users size={18} />,
        color: 'hover:text-rose-450 active-glow-rose',
        section: 'members'
      });
    }

    if (userProfile.is_system_admin) {
      items.push({
        id: 'system_admin',
        name: 'System Admin',
        icon: <Zap size={18} />,
        color: 'hover:text-yellow-400 active-glow-yellow',
        section: 'system_admin'
      });
    }

    return items;
  };

  // Note: Debug alert hooks removed — use browser DevTools console for error diagnostics

  // Key configurations
  const [keyProvider, setKeyProvider] = useState('anthropic');
  const [keyValue, setKeyValue] = useState('');
  const [isKeyDialogOpen, setIsKeyDialogOpen] = useState(false);

  // App Dashboard States
  const [activeView, setActiveView] = useState('dashboard');
  const [queue, setQueue] = useState<{posts: any[], leads: any[]}>({posts: [], leads: []});
  const [timeline, setTimeline] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>({});
  const [teams, setTeams] = useState<any[]>([]);
  const [apps, setApps] = useState<any[]>([]);
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);

  // Fetch branding settings on mount
  useEffect(() => {
    const fetchBranding = async () => {
      try {
        const res = await fetch(`${API_URL}/auth/settings`);
        if (res.ok) {
          const data = await res.json();
          if (data.logo_url) setLogoUrl(data.logo_url);
          if (data.favicon_url) setFaviconUrl(data.favicon_url);
        }
      } catch (e) {
        // Non-critical; ignore branding fetch errors
      }
    };
    fetchBranding();
  }, []);

  // Apply dynamic favicon whenever faviconUrl changes (only for valid absolute URLs)
  useEffect(() => {
    if (typeof document !== 'undefined' && faviconUrl) {
      // Only apply if it's a valid absolute URL — prevents corrupted/relative DB values from causing 404s
      try {
        const parsed = new URL(faviconUrl);
        if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return;
      } catch {
        return; // Not a valid URL — skip override, static /favicon.ico remains active
      }
      let link: HTMLLinkElement | null = document.querySelector("link[rel~='icon']");
      if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.head.appendChild(link);
      }
      link.href = faviconUrl;
    }
  }, [faviconUrl]);

  // Restore session from localStorage on mount & check for invite token
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const tokenParam = params.get('token');
      if (tokenParam) {
        setInviteToken(tokenParam);
        setAppState('signup');
      } else {
        const savedToken = localStorage.getItem('token');
        const savedTenantId = localStorage.getItem('tenant_id');
        if (savedToken) {
          setToken(savedToken);
          if (savedTenantId) {
            setTenantId(savedTenantId);
          }
          setAppState('app');
        }
      }
    }
  }, []);

  const fetchWithAuth = async (url: string, options: any = {}) => {
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      handleLogout();
    }
    return res;
  };

  const fetchData = async () => {
    if (!token) return;
    try {
      if (!userProfile) {
        const meRes = await fetchWithAuth(`${API_URL}/auth/me`);
        if (meRes.ok) {
          const meData = await meRes.json();
          setUserProfile(meData);
          if (meData.tenant_id) {
            localStorage.setItem('tenant_id', meData.tenant_id);
            setTenantId(meData.tenant_id);
          }
        }
      } else if (!tenantId) {
        const meRes = await fetchWithAuth(`${API_URL}/auth/me`);
        if (meRes.ok) {
          const meData = await meRes.json();
          if (meData.tenant_id) {
            localStorage.setItem('tenant_id', meData.tenant_id);
            setTenantId(meData.tenant_id);
          }
        }
      }

      const [qRes, tRes, kRes, mRes, tmRes, aRes, keyStatusRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/commands/queue`),
        fetchWithAuth(`${API_URL}/commands/timeline`),
        fetchWithAuth(`${API_URL}/commands/knowledge`),
        fetchWithAuth(`${API_URL}/dashboard/metrics`),
        fetchWithAuth(`${API_URL}/dashboard/teams`),
        fetchWithAuth(`${API_URL}/dashboard/marketplace/installed`),
        fetchWithAuth(`${API_URL}/commands/keys`)
      ]);
      setQueue(await qRes.json());
      setTimeline(await tRes.json());
      setKnowledge(await kRes.json());
      setMetrics(await mRes.json());
      setTeams(await tmRes.json());
      setApps(await aRes.json());
      
      const keyStatusData = await keyStatusRes.json();
      setConfiguredProviders(keyStatusData.configured_providers || []);
    } catch (e) {
      console.error(e);
    }
  };

  // Poll global data periodically
  useEffect(() => {
    if (appState === 'app') {
      fetchData();
      const interval = setInterval(() => {
        fetchData();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [appState, token]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('tenant_id');
    setToken(null);
    setTenantId(null);
    setUserProfile(null);
    setInviteToken(null);
    setAppState('landing');
  };

  const saveApiKey = async () => {
    if (!keyValue) return;
    try {
      await fetchWithAuth(`${API_URL}/commands/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: keyProvider, key: keyValue })
      });
      setKeyValue('');
      setIsKeyDialogOpen(false);
      alert(`${keyProvider} API key saved successfully!`);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const uninstallApp = async (appName: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/marketplace/uninstall`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_name: appName })
      });
      if (res.ok) {
        fetchData();
        alert(`${appName} deactivated successfully.`);
      } else {
        alert(`Failed to deactivate ${appName}.`);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleApprovePost = async (postId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/approve`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchData();
        alert('✅ Post approved and scheduled!\n\nTo publish immediately to Instagram/Facebook, click the "Publish Now" button on the post card. Make sure your Meta API key is configured in Settings → Integrations.');
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleRejectPost = async (postId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/reject`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Render Landing Page
  if (appState === 'landing') {
    return <LandingPage setAppState={setAppState} logoUrl={logoUrl} />;
  }

  // Render Login or Signup UI Forms
  if (appState === 'login' || appState === 'signup') {
    return (
      <AuthForms
        appState={appState}
        setAppState={setAppState}
        API_URL={API_URL}
        setToken={setToken}
        setTenantId={setTenantId}
        inviteToken={inviteToken}
        setInviteToken={setInviteToken}
        logoUrl={logoUrl}
      />
    );
  }

  // MAIN APP DASHBOARD VIEW
  return (
    <div className="flex h-screen bg-[#030014] text-[#f4f4f7] font-sans relative overflow-hidden">
      {/* Ambient background glows for App Workspace */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[rgba(139,92,246,0.08)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[rgba(59,130,246,0.08)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-[30%] left-[20%] w-[400px] h-[400px] bg-[rgba(16,185,129,0.03)] rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

      {/* Sidebar */}
      <div className="w-66 glass-panel border-r border-[rgba(255,255,255,0.06)] flex flex-col p-5 relative z-20">
        <div className="flex items-center gap-2.5 mb-8 px-2 text-xl font-black text-white">
          {logoUrl ? (
            <img src={logoUrl} alt="OctaOS Logo" className="h-8 w-auto max-w-[140px] object-contain" />
          ) : (
            <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-1.5 rounded-lg shadow-lg shadow-violet-500/20">
              <Zap className="text-white fill-white h-4.5 w-4.5 animate-pulse" />
            </div>
          )}
          <span>Octa<span className="text-violet-400">Os</span></span>
        </div>
        <nav className="flex flex-col gap-1.5 flex-1">
          {getFilteredNavItems().map((item) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border border-transparent ${
                  isActive
                    ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white shadow-lg'
                    : 'text-gray-400 hover:bg-[rgba(255,255,255,0.02)] hover:border-[rgba(255,255,255,0.04)]'
                } ${item.color}`}
              >
                {item.icon}
                <span>{item.name}</span>
              </button>
            );
          })}
          
          <button
            onClick={() => setActiveView('api_management')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border border-transparent ${
              activeView === 'api_management'
                ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white shadow-lg'
                : 'text-gray-400 hover:bg-[rgba(255,255,255,0.02)] hover:border-[rgba(255,255,255,0.04)] hover:text-violet-400'
            }`}
          >
            <Key size={18} />
            <span>API Management</span>
          </button>

          <button
            onClick={() => setActiveView('instructions')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border border-transparent mt-auto ${
              activeView === 'instructions'
                ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white shadow-lg'
                : 'text-gray-400 hover:bg-[rgba(255,255,255,0.02)] hover:border-[rgba(255,255,255,0.04)]'
            }`}
          >
            <BookOpen size={18} />
            <span>Setup & API Guide</span>
          </button>
          
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border border-transparent text-rose-400 hover:bg-rose-950/20 hover:border-rose-900/30 mt-2"
          >
            <LogOut size={18} />
            <span>Log out</span>
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative z-10">
        {/* Header (Settings & KB) */}
        <header className="h-16 bg-transparent border-b border-[rgba(255,255,255,0.06)] flex items-center justify-end px-8 gap-4 relative z-20">
          <Dialog open={isKeyDialogOpen} onOpenChange={setIsKeyDialogOpen}>
            <DialogTrigger render={<Button variant="outline" className="bg-transparent border-gray-700/60 hover:bg-gray-800 text-gray-300" />}>API Settings</DialogTrigger>
            <DialogContent className="glass-panel border-violet-500/20 text-white rounded-3xl">
              <DialogHeader><DialogTitle className="text-white font-extrabold text-xl">Configure API Keys</DialogTitle></DialogHeader>
              <div className="flex flex-col gap-4 py-4">
                <p className="text-xs text-gray-400">Select a provider and enter your API key. You can also just paste keys directly into the Orchestrator chat!</p>
                <Select value={keyProvider} onValueChange={(val) => val && setKeyProvider(val)}>
                  <SelectTrigger className="bg-gray-900/60 border-gray-800 text-white"><SelectValue placeholder="Select Provider" /></SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-800 text-white">
                    <SelectItem value="anthropic">Claude (Anthropic)</SelectItem>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="gemini">Google Gemini</SelectItem>
                    <SelectItem value="grok">Grok</SelectItem>
                    <SelectItem value="meta">Meta Graph (Instagram/FB)</SelectItem>
                    <SelectItem value="linkedin">LinkedIn</SelectItem>
                    <SelectItem value="apollo">Apollo.io</SelectItem>
                    <SelectItem value="hunter">Hunter.io</SelectItem>
                    <SelectItem value="google_places">Google Places API</SelectItem>
                    <SelectItem value="gmail">Gmail API</SelectItem>
                    <SelectItem value="whatsapp">WhatsApp Business</SelectItem>
                    <SelectItem value="google_calendar">Google Calendar API</SelectItem>
                    <SelectItem value="smtp">SMTP Credentials (outgoing mail)</SelectItem>
                  </SelectContent>
                </Select>
                <Input 
                  type="password" 
                  placeholder={keyProvider === 'smtp' ? 'smtp://username:password@smtp.mailtrap.io:2525' : 'Enter API Key / Token'} 
                  value={keyValue} 
                  onChange={e => setKeyValue(e.target.value)} 
                  className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20"
                />
                <Button onClick={saveApiKey} className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold">Save Configuration</Button>
              </div>
            </DialogContent>
          </Dialog>

          <Button 
            variant="secondary" 
            onClick={() => setActiveView('knowledge')}
            className="bg-[rgba(255,255,255,0.04)] border border-gray-700/60 hover:bg-gray-800 text-gray-300"
          >
            🧠 Knowledge Base
          </Button>
        </header>

        {/* Scrollable View Area */}
        <main className="flex-1 overflow-auto p-8 relative z-10">
          
          <div className={activeView === 'dashboard' ? 'block' : 'hidden'}>
            <DashboardView 
              metrics={metrics} 
              timeline={timeline} 
              queue={queue} 
              apps={apps} 
              setActiveView={setActiveView} 
              uninstallApp={uninstallApp} 
              handleApprovePost={handleApprovePost}
              handleRejectPost={handleRejectPost}
            />
          </div>

          <div className={activeView === 'knowledge' ? 'block' : 'hidden'}>
            <KnowledgeView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              knowledge={knowledge} 
            />
          </div>

          <div className={activeView === 'campaigns' ? 'block' : 'hidden'}>
            <CampaignsView 
              token={token} 
              activeView={activeView}
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              configuredProviders={configuredProviders} 
            />
          </div>

          <div className={activeView === 'support' ? 'block' : 'hidden'}>
            <SupportView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
            />
          </div>

          <div className={activeView === 'orchestrator' ? 'block' : 'hidden'}>
            <OrchestratorView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              apps={apps} 
              configuredProviders={configuredProviders} 
              timeline={timeline} 
              queue={queue}
              handleApprovePost={handleApprovePost}
              handleRejectPost={handleRejectPost}
            />
          </div>

          <div className={activeView === 'teams' ? 'block' : 'hidden'}>
            <TeamsView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              teams={teams} 
              setTeams={setTeams} 
            />
          </div>

          <div className={activeView === 'marketplace' ? 'block' : 'hidden'}>
            <MarketplaceView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              apps={apps} 
            />
          </div>

          <div className={activeView === 'instructions' ? 'block' : 'hidden'}>
            <InstructionsView 
              configuredProviders={configuredProviders} 
              setIsKeyDialogOpen={setIsKeyDialogOpen} 
              setKeyProvider={setKeyProvider} 
              API_URL={API_URL}
              tenantId={tenantId}
            />
          </div>

          <div className={activeView === 'hr' ? 'block' : 'hidden'}>
            <HRView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
            />
          </div>

          <div className={activeView === 'ceo' ? 'block' : 'hidden'}>
            <CEOView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              timeline={timeline} 
              setActiveView={setActiveView} 
            />
          </div>

          <div className={activeView === 'coordination' ? 'block' : 'hidden'}>
            <CoordinationView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
            />
          </div>

          <div className={activeView === 'sales' ? 'block' : 'hidden'}>
            <SalesView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              timeline={timeline} 
            />
          </div>

          <div className={activeView === 'video_studio' ? 'block' : 'hidden'}>
            <VideoStudioView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
            />
          </div>

          <div className={activeView === 'ai_optimization' ? 'block' : 'hidden'}>
            <AIOptimizationView 
              token={token} 
              API_URL={API_URL} 
              fetchWithAuth={fetchWithAuth} 
              fetchData={fetchData} 
              metrics={metrics} 
            />
          </div>

          <div className={activeView === 'api_management' ? 'block' : 'hidden'}>
            <ApiManagementView
              token={token}
              API_URL={API_URL}
              fetchWithAuth={fetchWithAuth}
              fetchData={fetchData}
              configuredProviders={configuredProviders}
              tenantId={tenantId}
            />
          </div>

          {(userProfile?.role === 'admin' || userProfile?.is_system_admin) && (
            <div className={activeView === 'members' ? 'block' : 'hidden'}>
              <MembersView 
                token={token} 
                API_URL={API_URL} 
                fetchWithAuth={fetchWithAuth} 
                fetchData={fetchData} 
              />
            </div>
          )}

          {userProfile?.is_system_admin && (
            <div className={activeView === 'system_admin' ? 'block' : 'hidden'}>
              <SystemAdminView 
                token={token} 
                API_URL={API_URL} 
                fetchWithAuth={fetchWithAuth}
                onBrandingUpdate={(newLogoUrl, newFaviconUrl) => {
                  if (newLogoUrl !== undefined) setLogoUrl(newLogoUrl);
                  if (newFaviconUrl !== undefined) setFaviconUrl(newFaviconUrl);
                }}
              />
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

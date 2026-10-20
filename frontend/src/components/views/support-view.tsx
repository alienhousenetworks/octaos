'use client';

import { notify } from '@/lib/notify';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  MessageSquare, 
  Mail, 
  Phone, 
  Bot, 
  Loader2, 
  Send, 
  Clock, 
  Headphones, 
  CheckCircle2, 
  Copy, 
  Code, 
  Sparkles, 
  UserCheck, 
  Radio, 
  Eye, 
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  Sliders,
  History,
  X
} from 'lucide-react';
import SupportWidget from '@/components/support-widget';
import RoomFolderExplorer from '@/components/rooms/room-folder-explorer';
import RoomHeader from '@/components/rooms/room-header';
import { SectionRoomData } from '@/components/rooms/room-access-modal';

interface SupportViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  tenantId?: string | null;
  initialRoomSlug?: string;
}

export default function SupportView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  tenantId,
  initialRoomSlug,
}: SupportViewProps) {
  // Section Room state
  const [rooms, setRooms] = useState<SectionRoomData[]>([]);
  const [roomsLoading, setRoomsLoading] = useState(false);
  const [currentRoomSlug, setCurrentRoomSlug] = useState<string | null>(initialRoomSlug || null);
  const [currentRoom, setCurrentRoom] = useState<SectionRoomData | null>(null);
  const [isDirectoryView, setIsDirectoryView] = useState(!initialRoomSlug);

  const [activeMainTab, setActiveMainTab] = useState<'tickets' | 'widget' | 'studio'>('tickets');
  const [ticketFilter, setTicketFilter] = useState<'all' | 'pending_human' | 'human_handling' | 'resolved'>('all');
  
  // Support states
  const [tickets, setTickets] = useState<any[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [replyText, setReplyText] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Agent Presence States
  const [isAgentOnline, setIsAgentOnline] = useState<boolean>(true);
  const [presenceSaving, setPresenceSaving] = useState(false);

  // Support Agent Studio States
  const [studioConfig, setStudioConfig] = useState({
    agent_name: 'Ava',
    company_name: 'Acme Technologies',
    agent_avatar: 'bot',
    tone: 'professional_friendly',
    support_email: 'support@acme.com',
    email_signature: 'Best regards,\nAva & Support Team',
    whatsapp_welcome: 'Hello! Welcome to Support. How can we help you today?',
    handoff_trigger_message: 'Connecting you with our support team specialist...',
    sla_timeout_seconds: 300,
    sla_escalation_message: 'Our human agents are currently assisting other clients. We have escalated your request to a high-priority ticket (#{ticket_id}). Our team will reach out shortly.',
  });
  const [studioLoading, setStudioLoading] = useState(false);
  const [studioSaving, setStudioSaving] = useState(false);

  // Unified Customer History State
  const [customerHistory, setCustomerHistory] = useState<any | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);

  // Widget & Support Settings
  const [supportSettings, setSupportSettings] = useState({
    whatsapp_auto_reply: true,
    email_auto_reply: true,
    widget_auto_reply: true,
    live_chat_enabled: true,
    widget_title: 'Customer Support',
    widget_welcome: 'Hi there! How can we assist you today?',
    widget_color: '#2563eb',
    reply_mode: 'review_first' as 'review_first' | 'auto_send',
  });
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  useEffect(() => {
    if (token) {
      fetchTickets();
      fetchSupportSettings();
      fetchAgentPresence();
      fetchStudioConfig();
    }
  }, [token]);

  // Heartbeat interval for Agent Presence (every 45s when online)
  useEffect(() => {
    if (!token || !isAgentOnline) return;
    const interval = setInterval(() => {
      fetchWithAuth(`${API_URL}/support/agent/presence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_online: true }),
      }).catch(() => {});
    }, 45000);
    return () => clearInterval(interval);
  }, [token, isAgentOnline, API_URL]);

  // Auto-refresh rooms & tickets
  useEffect(() => {
    if (!token) return;
    fetchRooms();
    fetchTickets();
    const interval = setInterval(() => {
      fetchTickets();
    }, 6000);
    return () => clearInterval(interval);
  }, [token]);

  const fetchRooms = async () => {
    if (!token) return;
    setRoomsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/rooms/?section=support`);
      if (res.ok) {
        const data = await res.json();
        setRooms(data);
        if (currentRoomSlug) {
          const match = data.find((r: any) => r.slug === currentRoomSlug);
          if (match) {
            setCurrentRoom(match);
          }
        } else if (data.length > 0 && !isDirectoryView) {
          const defaultRoom = data.find((r: any) => r.slug === 'default') || data[0];
          setCurrentRoom(defaultRoom);
          setCurrentRoomSlug(defaultRoom.slug);
        }
      }
    } catch (err) {
      console.error('Failed to load support rooms:', err);
    } finally {
      setRoomsLoading(false);
    }
  };

  const handleSelectRoom = (slug: string) => {
    setCurrentRoomSlug(slug);
    const match = rooms.find((r) => r.slug === slug);
    if (match) {
      setCurrentRoom(match);
    }
    setIsDirectoryView(false);
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', `/app/support/rooms/${slug}`);
    }
    fetchTickets(slug);
  };

  const fetchTickets = async (slugOverride?: string) => {
    if (!token) return;
    try {
      const targetSlug = slugOverride || currentRoomSlug;
      const url = targetSlug ? `${API_URL}/support/tickets?room_slug=${targetSlug}` : `${API_URL}/support/tickets`;
      const res = await fetchWithAuth(url);
      if (res.ok) {
        const data = await res.json();
        setTickets(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMessages = async (ticketId: string) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets/${ticketId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSupportSettings = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/settings`);
      if (res.ok) {
        const data = await res.json();
        setSupportSettings({
          whatsapp_auto_reply: data.whatsapp_auto_reply ?? true,
          email_auto_reply: data.email_auto_reply ?? true,
          widget_auto_reply: data.widget_auto_reply ?? true,
          live_chat_enabled: data.live_chat_enabled ?? true,
          widget_title: data.widget_title || 'Customer Support',
          widget_welcome: data.widget_welcome || 'Hi there! How can we assist you today?',
          widget_color: data.widget_color || '#2563eb',
          reply_mode: data.reply_mode === 'auto_send' ? 'auto_send' : 'review_first',
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAgentPresence = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/agent/presence`);
      if (res.ok) {
        const data = await res.json();
        if (data.available !== undefined) {
          setIsAgentOnline(data.available);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const toggleAgentPresence = async () => {
    if (!token) return;
    setPresenceSaving(true);
    const nextState = !isAgentOnline;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/agent/presence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_online: nextState }),
      });
      if (res.ok) {
        setIsAgentOnline(nextState);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setPresenceSaving(false);
    }
  };

  const saveSupportSettings = async (newSettings: typeof supportSettings) => {
    if (!token) return;
    setSettingsSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings),
      });
      if (res.ok) {
        const data = await res.json();
        setSupportSettings(prev => ({
          ...prev,
          ...(data.settings || newSettings),
        }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSettingsSaving(false);
    }
  };

  const fetchStudioConfig = async () => {
    if (!token) return;
    setStudioLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/studio/config`);
      if (res.ok) {
        const data = await res.json();
        setStudioConfig(prev => ({ ...prev, ...data }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setStudioLoading(false);
    }
  };

  const saveStudioConfig = async () => {
    if (!token) return;
    setStudioSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/studio/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(studioConfig),
      });
      if (res.ok) {
        notify('Support Agent Studio configuration saved successfully!');
      } else {
        const err = await res.json();
        notify(`Failed to save: ${err.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Failed to save Studio configuration.');
    } finally {
      setStudioSaving(false);
    }
  };

  const fetchCustomerHistory = async (customerId: string) => {
    if (!token || !customerId) return;
    setLoadingHistory(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/customers/${customerId}/history`);
      if (res.ok) {
        const data = await res.json();
        setCustomerHistory(data);
        setHistoryDrawerOpen(true);
      } else {
        notify('Could not load unified customer history.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleClaimTicket = async (ticketId: string) => {
    if (!token) return;
    setActionInProgress(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets/${ticketId}/claim`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchTickets();
        await fetchMessages(ticketId);
      } else {
        const err = await res.json();
        notify(err.detail || 'Could not claim ticket.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleResolveTicket = async (ticketId: string) => {
    if (!token) return;
    setActionInProgress(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets/${ticketId}/resolve`, {
        method: 'POST',
      });
      if (res.ok) {
        await fetchTickets();
        await fetchMessages(ticketId);
      } else {
        const err = await res.json();
        notify(err.detail || 'Could not resolve ticket.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionInProgress(false);
    }
  };

  const handleSendManualReply = async () => {
    if (!selectedTicketId || !replyText.trim()) return;
    setSendingReply(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets/${selectedTicketId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: replyText })
      });
      if (res.ok) {
        setReplyText('');
        fetchMessages(selectedTicketId);
        fetchTickets();
      } else {
        const data = await res.json();
        notify(`Failed to send reply: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSendingReply(false);
    }
  };

  // Filtered tickets
  const filteredTickets = tickets.filter(t => {
    if (ticketFilter === 'pending_human') return t.status === 'pending_human';
    if (ticketFilter === 'human_handling') return t.status === 'human_handling';
    if (ticketFilter === 'resolved') return t.status === 'resolved' || t.status === 'closed';
    return true;
  });

  const pendingHandoffCount = tickets.filter(t => t.status === 'pending_human').length;
  const activeHumanCount = tickets.filter(t => t.status === 'human_handling').length;
  const selectedTicket = tickets.find(t => t.id === selectedTicketId);

  // Embed script snippet
  const embedCodeSnippet = `<!-- OctaOS Support & AI Live Chat Widget -->
<script
  src="${API_URL}/support/widget/embed.js"
  data-tenant-id="${tenantId || 'YOUR_TENANT_ID'}"
  async>
</script>`;

  const copyEmbedCode = () => {
    navigator.clipboard.writeText(embedCodeSnippet);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  if (isDirectoryView || !currentRoom) {
    return (
      <RoomFolderExplorer
        section="support"
        sectionTitle="Support & Queues"
        rooms={rooms}
        loading={roomsLoading}
        onSelectRoom={handleSelectRoom}
        onRefresh={fetchRooms}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300 pb-16">
      <RoomHeader
        sectionTitle="Support & Queues"
        activeRoom={currentRoom}
        allRooms={rooms}
        onSelectRoom={handleSelectRoom}
        onOpenDirectory={() => setIsDirectoryView(true)}
        onCreateNewRoom={() => setIsDirectoryView(true)}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onRoomUpdated={(updated) => {
          setCurrentRoom(updated);
          setRooms((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
        }}
      />

      <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-12rem)] flex flex-col px-4 sm:px-6">
      
      {/* Header Panel with Live Presence, Mode & Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2.5">
            <MessageSquare className="text-blue-400 h-8 w-8" /> Customer Support Center
            {pendingHandoffCount > 0 && (
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse">
                <Headphones size={13} /> {pendingHandoffCount} Waiting for Human
              </span>
            )}
          </h1>
          <p className="text-gray-400 mt-1 text-xs">
            Omnichannel Support · Knowledge Base RAG · Live Agent Handoff · Embeddable Web Widget
          </p>
        </div>

        {/* Header Right Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Presence Toggle */}
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-2xl bg-gray-900/60 border border-gray-800 shadow-sm">
            <span className={`w-2.5 h-2.5 rounded-full ${isAgentOnline ? 'bg-emerald-400 animate-ping' : 'bg-gray-500'}`} />
            <div className="flex flex-col">
              <span className="text-xs font-bold text-white">
                {isAgentOnline ? 'Online for Live Chat' : 'Away / Offline'}
              </span>
              <span className="text-xs text-gray-400">
                {isAgentOnline ? 'Receiving handoffs' : 'Tickets auto-escalate'}
              </span>
            </div>
            <button
              onClick={toggleAgentPresence}
              disabled={presenceSaving}
              className={`relative ml-1 inline-flex h-5 w-9 items-center rounded-full transition-colors ${
 isAgentOnline ? 'bg-emerald-600' : 'bg-gray-800'
 }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
 isAgentOnline ? 'translate-x-4' : 'translate-x-1'
 }`}
              />
            </button>
          </div>

          {/* Main View Switcher Tabs */}
          <div className="flex rounded-2xl bg-gray-900/90 border border-gray-800 p-1">
            <button
              onClick={() => setActiveMainTab('tickets')}
              className={`px-3.5 py-1.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 ${
 activeMainTab === 'tickets'
 ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
 : 'text-gray-400 hover:text-white'
 }`}
            >
              <MessageSquare size={13} /> Tickets & Queue
            </button>
            <button
              onClick={() => setActiveMainTab('widget')}
              className={`px-3.5 py-1.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 ${
 activeMainTab === 'widget'
 ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
 : 'text-gray-400 hover:text-white'
 }`}
            >
              <Code size={13} /> Embed Widget
            </button>
            <button
              onClick={() => setActiveMainTab('studio')}
              className={`px-3.5 py-1.5 text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 ${
 activeMainTab === 'studio'
 ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
 : 'text-gray-400 hover:text-white'
 }`}
            >
              <Sliders size={13} /> Support Agent Studio
            </button>
          </div>
        </div>
      </div>

      {/* VIEW 1: TICKETS & LIVE CHAT QUEUE */}
      {activeMainTab === 'tickets' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0 overflow-hidden">
          
          {/* 1. Ticket List - 4 Cols */}
          <Card className="lg:col-span-4 flex flex-col h-full overflow-hidden glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-2 shadow-2xl relative">
            {/* Filter Pills */}
            <div className="p-2 border-b border-gray-800/80 flex flex-wrap gap-1.5">
              <button
                onClick={() => setTicketFilter('all')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors ${
 ticketFilter === 'all' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-gray-200'
 }`}
              >
                All ({tickets.length})
              </button>
              <button
                onClick={() => setTicketFilter('pending_human')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1 ${
 ticketFilter === 'pending_human'
 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
 : pendingHandoffCount > 0
 ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse'
 : 'text-gray-400 hover:text-gray-200'
 }`}
              >
                <Headphones size={11} /> Live Requests ({pendingHandoffCount})
              </button>
              <button
                onClick={() => setTicketFilter('human_handling')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors ${
 ticketFilter === 'human_handling' ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40' : 'text-gray-400 hover:text-gray-200'
 }`}
              >
                Claimed ({activeHumanCount})
              </button>
              <button
                onClick={() => setTicketFilter('resolved')}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors ${
 ticketFilter === 'resolved' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'text-gray-400 hover:text-gray-200'
 }`}
              >
                Resolved
              </button>
            </div>

            {/* Ticket Cards Stream */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {filteredTickets.length === 0 && (
                <div className="text-center py-16 text-gray-500 space-y-2">
                  <Bot size={28} className="mx-auto text-gray-600" />
                  <p className="text-xs">No tickets match this filter.</p>
                </div>
              )}
              {filteredTickets.map(t => {
                const isSelected = selectedTicketId === t.id;
                let channelIcon = "💬";
                if (t.channel === "whatsapp") channelIcon = "🟢";
                if (t.channel === "email") channelIcon = "✉️";
                if (t.channel === "widget") channelIcon = "🌐";

                const isPendingHuman = t.status === "pending_human";
                const isHumanHandling = t.status === "human_handling";

                return (
                  <div
                    key={t.id}
                    onClick={() => setSelectedTicketId(t.id)}
                    className={`p-3.5 rounded-2xl border text-left cursor-pointer transition-all ${
 isSelected 
 ? 'bg-blue-600/10 border-blue-500/50 shadow-lg glow-support' 
 : isPendingHuman
 ? 'bg-amber-500/10 hover:bg-amber-500/15 border-amber-500/30'
 : 'bg-gray-900/30 hover:bg-gray-800/40 border-gray-800/80 text-gray-300'
 }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-gray-400 flex items-center gap-1">
                        {channelIcon} {(t.channel || 'widget').toUpperCase()}
                      </span>
                      {isPendingHuman ? (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500 text-black animate-pulse flex items-center gap-1">
                          <Headphones size={9} /> CLAIM WAITING
                        </span>
                      ) : isHumanHandling ? (
                        <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          LIVE CHAT
                        </span>
                      ) : (
                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded uppercase ${
 t.priority === 'high' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-gray-800 text-gray-400'
 }`}>
                          {t.priority}
                        </span>
                      )}
                    </div>

                    <h4 className="font-bold text-xs text-white truncate mb-1">{t.subject}</h4>
                    
                    {/* Customer Info Snippet */}
                    <div className="text-xs text-gray-400 truncate mb-2">
                      {t.customer_name ? `${t.customer_name} · ` : ''}{t.customer_contact || t.customer_email || 'Visitor'}
                    </div>

                    <div className="flex items-center justify-between pt-1 border-t border-white/5">
                      <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${
 t.status === 'open' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
 t.status === 'resolved' ? 'bg-gray-500/20 text-gray-400' :
 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
 }`}>
                        {t.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* 2. Conversation Thread & Claim/Resolve Controls - 8 Cols */}
          <Card className="lg:col-span-8 flex flex-col h-full overflow-hidden glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-0 shadow-2xl relative">
            {selectedTicketId && selectedTicket ? (
              <>
                {/* Thread Header with Claim & Resolve CTA */}
                <div className="px-5 py-3.5 bg-gray-950/60 border-b border-gray-800 flex items-center justify-between gap-4">
                  <div className="truncate flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-white text-sm truncate">
                        {selectedTicket.subject}
                      </h3>
                      <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase">
                        {selectedTicket.channel}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1 flex flex-wrap gap-3 items-center">
                      {selectedTicket.customer_name && (
                        <span>👤 <strong className="text-gray-300">{selectedTicket.customer_name}</strong></span>
                      )}
                      {selectedTicket.customer_email && (
                        <span>✉️ {selectedTicket.customer_email}</span>
                      )}
                      {selectedTicket.customer_phone && (
                        <span>📱 {selectedTicket.customer_phone}</span>
                      )}
                      {selectedTicket.customer_id && (
                        <button
                          onClick={() => fetchCustomerHistory(selectedTicket.customer_id)}
                          className="px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/30 text-xs font-semibold hover:bg-blue-500/25 flex items-center gap-1 transition-colors"
                        >
                          <History size={11} /> Unified History
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="flex items-center gap-2">
                    {selectedTicket.status === 'pending_human' && (
                      <Button
                        size="sm"
                        disabled={actionInProgress}
                        onClick={() => handleClaimTicket(selectedTicket.id)}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs h-8 px-3.5 rounded-xl shadow-lg shadow-emerald-600/20 flex items-center gap-1.5 transition-all"
                      >
                        <UserCheck size={14} /> Claim & Join Live Chat
                      </Button>
                    )}

                    {selectedTicket.status === 'human_handling' && (
                      <Button
                        size="sm"
                        disabled={actionInProgress}
                        onClick={() => handleResolveTicket(selectedTicket.id)}
                        className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs h-8 px-3.5 rounded-xl shadow-lg shadow-blue-600/20 flex items-center gap-1.5 transition-all"
                      >
                        <CheckCircle2 size={14} /> Resolve & Return to AI
                      </Button>
                    )}

                    {selectedTicket.status === 'resolved' && (
                      <span className="text-xs bg-gray-800 text-gray-300 border border-gray-700 px-2.5 py-1 rounded-lg font-semibold flex items-center gap-1">
                        <CheckCircle2 size={13} className="text-emerald-400" /> Resolved
                      </span>
                    )}
                  </div>
                </div>

                {/* Chat Messages Stream */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-gray-950/20">
                  {messages.length === 0 && (
                    <p className="text-xs text-gray-500 text-center py-10">No messages in this ticket.</p>
                  )}
                  {messages.map(m => {
                    const isAgent = m.sender === "agent";
                    const isSys = m.sender === "system";

                    if (isSys) {
                      return (
                        <div key={m.id} className="flex justify-center my-2">
                          <span className="bg-gray-900/90 border border-gray-800 text-gray-400 text-xs px-3.5 py-1 rounded-full text-center max-w-[85%] leading-relaxed">
                            {m.content}
                          </span>
                        </div>
                      );
                    }

                    return (
                      <div
                        key={m.id}
                        className={`flex ${isAgent ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed shadow-sm ${
 isAgent
 ? 'bg-blue-600 text-white rounded-tr-none shadow-lg shadow-blue-500/15'
 : 'bg-gray-900 border border-gray-800 text-gray-100 rounded-tl-none'
 }`}
                        >
                          <p className="whitespace-pre-wrap">{m.content}</p>
                          <div className="flex items-center justify-between gap-3 mt-1.5 pt-1 border-t border-white/10 text-xs">
                            <span className={isAgent ? 'text-blue-200' : 'text-gray-400'}>
                              {m.channel ? `${m.channel.toUpperCase()}` : ''} {m.delivery_status ? `· ${m.delivery_status}` : ''}
                            </span>
                            <span className={isAgent ? 'text-blue-200 font-medium' : 'text-gray-500'}>
                              {m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Reply Input Box */}
                <div className="p-3 border-t border-gray-800 bg-gray-950/40">
                  <div className="flex gap-2">
                    <Textarea
                      placeholder={
                        selectedTicket.status === 'human_handling'
                          ? "Type live reply directly to customer..."
                          : "Type a response to send back to customer..."
                      }
                      value={replyText}
                      onChange={e => setReplyText(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendManualReply();
                        }
                      }}
                      className="bg-gray-900/80 border-gray-800 text-white focus:border-blue-500 rounded-xl min-h-[50px] text-xs resize-none flex-1"
                    />
                    <Button
                      onClick={handleSendManualReply}
                      disabled={sendingReply || !replyText.trim()}
                      className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl h-auto self-stretch px-4 flex flex-col justify-center items-center shadow-lg shadow-blue-500/20 transition-all active:scale-95"
                    >
                      <Send size={15} className="mb-0.5" />
                      <span className="text-xs font-bold">Reply</span>
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-gray-500">
                <div className="text-4xl mb-3 animate-bounce">💬</div>
                <h4 className="font-bold text-white text-sm">Select a ticket from the left</h4>
                <p className="text-xs text-gray-400 max-w-xs mt-1">
                  Claim waiting live chat requests or respond to customer tickets.
                </p>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* VIEW 2: EMBED WIDGET GENERATOR & LIVE PREVIEW */}
      {activeMainTab === 'widget' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0 overflow-y-auto">
          
          {/* Left Panel: Configuration & Code Copy - 7 Cols */}
          <div className="lg:col-span-7 space-y-5">
            <Card className="glass-panel border-white/5 p-6 rounded-3xl space-y-5">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Code size={18} className="text-blue-400" /> Website & App Widget Integration
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Embed this floating AI Support & Live Chat button into any website, web application, WordPress, or Shopify site with a single script tag.
                </p>
              </div>

              {/* Code Snippet Box */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-300 flex items-center gap-1.5">
                    <Sparkles size={12} className="text-amber-400" /> Embed Code Snippet
                  </span>
                  <Button
                    size="sm"
                    onClick={copyEmbedCode}
                    className="h-7 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded-lg flex items-center gap-1.5 shadow-md shadow-blue-500/20"
                  >
                    {copiedCode ? <CheckCircle2 size={13} className="text-emerald-300" /> : <Copy size={13} />}
                    {copiedCode ? 'Copied!' : 'Copy Code'}
                  </Button>
                </div>

                <div className="bg-gray-950 border border-gray-800 rounded-2xl p-4 font-mono text-xs text-blue-300 overflow-x-auto relative">
                  <pre className="whitespace-pre-wrap">{embedCodeSnippet}</pre>
                </div>
              </div>

              {/* Widget Customization Form */}
              <div className="border-t border-gray-800/80 pt-4 space-y-4">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider text-gray-400">
                  Widget Branding & Behavior
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-300 mb-1">Widget Title</label>
                    <Input
                      type="text"
                      value={supportSettings.widget_title}
                      onChange={e => setSupportSettings({ ...supportSettings, widget_title: e.target.value })}
                      className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-300 mb-1">Brand Color (Hex)</label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={supportSettings.widget_color}
                        onChange={e => setSupportSettings({ ...supportSettings, widget_color: e.target.value })}
                        className="w-9 h-9 rounded-xl bg-transparent border-0 cursor-pointer"
                      />
                      <Input
                        type="text"
                        value={supportSettings.widget_color}
                        onChange={e => setSupportSettings({ ...supportSettings, widget_color: e.target.value })}
                        className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl flex-1"
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Welcome Message</label>
                  <Textarea
                    value={supportSettings.widget_welcome}
                    onChange={e => setSupportSettings({ ...supportSettings, widget_welcome: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl min-h-[60px] resize-none"
                  />
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-white">Live Chat Handoff Enabled</span>
                    <button
                      onClick={() => setSupportSettings({ ...supportSettings, live_chat_enabled: !supportSettings.live_chat_enabled })}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
 supportSettings.live_chat_enabled ? 'bg-emerald-600' : 'bg-gray-800'
 }`}
                    >
                      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
 supportSettings.live_chat_enabled ? 'translate-x-4' : 'translate-x-1'
 }`} />
                    </button>
                  </div>

                  <Button
                    onClick={() => saveSupportSettings(supportSettings)}
                    disabled={settingsSaving}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold h-8 px-4 rounded-xl shadow-lg shadow-emerald-600/20"
                  >
                    {settingsSaving ? 'Saving...' : 'Save Settings'}
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Right Panel: Interactive Sandbox Preview - 5 Cols */}
          <div className="lg:col-span-5 flex flex-col">
            <Card className="bg-card border border-border p-6 rounded-xl flex-1 flex flex-col relative overflow-hidden shadow-xs">
              <div className="flex items-center justify-between mb-4 border-b border-border pb-3">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Eye size={14} className="text-primary" /> Interactive Live Preview
                </span>
                <span className="text-xs text-muted-foreground">Click the floating button below</span>
              </div>

              <div className="flex-1 border border-dashed border-gray-800 rounded-2xl relative min-h-[460px] flex items-center justify-center p-6 text-center text-gray-500">
                <div className="space-y-2 max-w-xs">
                  <p className="text-xs text-gray-400 font-semibold">Your Website Preview Area</p>
                  <p className="text-xs text-gray-500">
                    The support button floats in the bottom right corner of this sandbox. You can click to open and test the full AI chat, RAG, and ticket escalation experience!
                  </p>
                </div>

                {/* Mount Interactive Widget inside Preview */}
                <SupportWidget
                  tenantId={tenantId || 'test-tenant'}
                  API_URL={API_URL}
                  defaultOpen={true}
                  brandColor={supportSettings.widget_color}
                  title={supportSettings.widget_title}
                  welcomeMessage={supportSettings.widget_welcome}
                />
              </div>
            </Card>
          </div>

        </div>
      )}

      {/* VIEW 3: SUPPORT AGENT STUDIO */}
      {activeMainTab === 'studio' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0 overflow-y-auto">
          {/* Left Panel: Agent Persona & Brand Customization - 7 Cols */}
          <div className="lg:col-span-7 space-y-5">
            <Card className="glass-panel border-white/5 p-6 rounded-3xl space-y-5">
              <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <Sliders size={18} className="text-blue-400" /> Support Agent Persona & Branding
                  </h3>
                  <p className="text-xs text-gray-400 mt-1">
                    Configure your tenant's dedicated AI support agent persona, communication tone, and channel signatures.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    onClick={saveStudioConfig}
                    disabled={studioSaving}
                    className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold h-8 px-4 rounded-xl shadow-lg shadow-blue-500/20"
                  >
                    {studioSaving ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                    {studioSaving ? 'Saving...' : 'Save Studio Config'}
                  </Button>
                </div>
              </div>

              {/* Form Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Agent Name</label>
                  <Input
                    type="text"
                    value={studioConfig.agent_name}
                    onChange={e => setStudioConfig({ ...studioConfig, agent_name: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl"
                    placeholder="e.g. Ava, Maya, Nova"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Company / Brand Name</label>
                  <Input
                    type="text"
                    value={studioConfig.company_name}
                    onChange={e => setStudioConfig({ ...studioConfig, company_name: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl"
                  />
                </div>
              </div>

              {/* Tone & Avatar Selector */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Communication Tone</label>
                  <select
                    value={studioConfig.tone}
                    onChange={e => setStudioConfig({ ...studioConfig, tone: e.target.value })}
                    className="w-full h-9 bg-gray-900 border border-gray-800 text-white text-xs rounded-xl px-3 focus:outline-none focus:border-blue-500"
                  >
                    <option value="professional_friendly">Professional & Friendly</option>
                    <option value="concise_technical">Concise & Technical</option>
                    <option value="empathetic_support">Empathetic & Caring</option>
                    <option value="formal_enterprise">Formal Enterprise</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Agent Avatar Icon</label>
                  <select
                    value={studioConfig.agent_avatar}
                    onChange={e => setStudioConfig({ ...studioConfig, agent_avatar: e.target.value })}
                    className="w-full h-9 bg-gray-900 border border-gray-800 text-white text-xs rounded-xl px-3 focus:outline-none focus:border-blue-500"
                  >
                    <option value="bot">Bot / Assistant</option>
                    <option value="sparkles">AI Sparkles</option>
                    <option value="headphones">Support Specialist</option>
                    <option value="user">Human Representative</option>
                  </select>
                </div>
              </div>

              {/* Email Support Display & Signature */}
              <div className="space-y-3 border-t border-gray-800 pt-3">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">Email Channel Identity</h4>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Inbound / Reply-to Email</label>
                  <Input
                    type="email"
                    value={studioConfig.support_email}
                    onChange={e => setStudioConfig({ ...studioConfig, support_email: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl"
                    placeholder="support@company.com"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Email Outbound Signature</label>
                  <Textarea
                    value={studioConfig.email_signature}
                    onChange={e => setStudioConfig({ ...studioConfig, email_signature: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl min-h-[70px] resize-none"
                    placeholder="Best regards,\nYour Support Team"
                  />
                </div>
              </div>

              {/* WhatsApp Welcome */}
              <div className="space-y-3 border-t border-gray-800 pt-3">
                <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">WhatsApp Channel Greeting</h4>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Welcome Greeting Message</label>
                  <Textarea
                    value={studioConfig.whatsapp_welcome}
                    onChange={e => setStudioConfig({ ...studioConfig, whatsapp_welcome: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl min-h-[60px] resize-none"
                  />
                </div>
              </div>
            </Card>
          </div>

          {/* Right Panel: Human Handoff & SLA Escalation Policies - 5 Cols */}
          <div className="lg:col-span-5 space-y-5">
            <Card className="glass-panel border-white/5 p-6 rounded-3xl space-y-5">
              <div className="border-b border-gray-800 pb-3">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Headphones size={18} className="text-emerald-400" /> Human Escalation & SLA
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Control how the AI transitions ownership to humans across WhatsApp, Email, and Web Widget.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Handoff Acknowledgment Message</label>
                  <p className="text-xs text-gray-500 mb-1.5">Sent immediately when `/human` is typed or handoff is triggered.</p>
                  <Textarea
                    value={studioConfig.handoff_trigger_message}
                    onChange={e => setStudioConfig({ ...studioConfig, handoff_trigger_message: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl min-h-[60px] resize-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">Escalation SLA Timeout (Seconds)</label>
                  <p className="text-xs text-gray-500 mb-1.5">Default 300s (5 minutes). If no human agent claims the ticket before timeout, it automatically escalates to a priority ticket.</p>
                  <Input
                    type="number"
                    value={studioConfig.sla_timeout_seconds}
                    onChange={e => setStudioConfig({ ...studioConfig, sla_timeout_seconds: parseInt(e.target.value) || 300 })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">SLA Timeout Escalation Notice</label>
                  <p className="text-xs text-gray-500 mb-1.5">Sent to the customer when the 5-minute timer expires and team is alerted.</p>
                  <Textarea
                    value={studioConfig.sla_escalation_message}
                    onChange={e => setStudioConfig({ ...studioConfig, sla_escalation_message: e.target.value })}
                    className="bg-gray-900 border-gray-800 text-white text-xs rounded-xl min-h-[70px] resize-none"
                  />
                </div>

                <div className="p-3.5 rounded-2xl bg-blue-950/20 border border-blue-800/30 text-xs text-blue-300 space-y-1.5">
                  <div className="font-bold flex items-center gap-1.5 text-blue-200">
                    <ShieldAlert size={14} /> Telegram & Priority Ticket Escalation
                  </div>
                  <p className="text-xs leading-relaxed text-blue-300/80">
                    When escalation triggers, OctaOS broadcasts ticket details and conversation transcript to your configured Telegram Operations Group and sets the ticket priority to <span className="text-rose-400 font-bold">HIGH</span>.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Customer Unified Cross-Channel History Modal */}
      {historyDrawerOpen && customerHistory && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-gray-950 border border-gray-800 rounded-3xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History size={18} className="text-blue-400" />
                <h3 className="font-bold text-white text-sm">Unified Customer Profile & Cross-Channel History</h3>
              </div>
              <button
                onClick={() => setHistoryDrawerOpen(false)}
                className="text-gray-400 hover:text-white p-1 rounded-lg"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5">
              {/* Profile Card */}
              <div className="p-4 rounded-2xl bg-gray-900/60 border border-gray-800 space-y-2">
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Canonical Profile</h4>
                <div className="text-sm font-bold text-white">{customerHistory.customer?.name || 'Customer'}</div>
                <div className="flex flex-wrap gap-3 text-xs text-gray-300">
                  {customerHistory.customer?.primary_email && <span>✉️ {customerHistory.customer.primary_email}</span>}
                  {customerHistory.customer?.primary_phone && <span>📱 {customerHistory.customer.primary_phone}</span>}
                </div>
              </div>

              {/* Verified Identities */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Linked Channels & Identities</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {customerHistory.identities?.map((id: any) => (
                    <div key={id.id} className="p-3 rounded-xl bg-gray-900/40 border border-gray-800 text-xs">
                      <div className="font-bold text-white flex items-center gap-1.5 uppercase">
                        {id.channel === 'whatsapp' ? '🟢 WhatsApp' : id.channel === 'email' ? '✉️ Email' : '🌐 Widget'}
                      </div>
                      <div className="text-gray-400 text-xs mt-0.5 truncate">{id.identifier}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Unified Timeline */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Cross-Channel Tickets ({customerHistory.tickets?.length || 0})</h4>
                <div className="space-y-2">
                  {customerHistory.tickets?.map((t: any) => (
                    <div key={t.id} className="p-3.5 rounded-xl bg-gray-900/30 border border-gray-800 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-xs">{t.subject}</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 uppercase font-bold border border-blue-500/20">
                          {t.channel}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-400">
                        <span>Status: <strong className="text-gray-300">{t.status}</strong> · Owner: {t.owner_type || 'ai'}</span>
                        <span>{new Date(t.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      </div>
    </div>
  );
}

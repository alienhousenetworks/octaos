'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { MessageSquare, Mail, Phone, Bot, Loader2, Send, Clock, Plus } from 'lucide-react';

interface SupportViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
}

export default function SupportView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
}: SupportViewProps) {
  // Support states relocated here
  const [tickets, setTickets] = useState<any[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [replyText, setReplyText] = useState('');
  const [supportSettings, setSupportSettings] = useState({ whatsapp_auto_reply: true, email_auto_reply: true });
  const [simChannel, setSimChannel] = useState<'whatsapp' | 'email'>('whatsapp');
  const [simSender, setSimSender] = useState('+15553334444');
  const [simContent, setSimContent] = useState('');
  const [simSubject, setSimSubject] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [simulatingMessage, setSimulatingMessage] = useState(false);

  useEffect(() => {
    if (token) {
      fetchTickets();
      fetchSupportSettings();
    }
  }, [token]);

  // Handle auto-refresh of selected ticket messages
  useEffect(() => {
    if (selectedTicketId && token) {
      fetchMessages(selectedTicketId);
      const interval = setInterval(() => {
        fetchMessages(selectedTicketId);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [selectedTicketId, token]);

  // Support functions
    const fetchTickets = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets`);
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
        setSupportSettings(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

    const saveSupportSettings = async (settings: { whatsapp_auto_reply: boolean, email_auto_reply: boolean }) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        const data = await res.json();
        setSupportSettings(data.settings);
      }
    } catch (e) {
      console.error(e);
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
        alert(`Failed to send reply: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSendingReply(false);
    }
  };

    const handleSimulateMessage = async () => {
    if (!simSender.trim() || !simContent.trim()) {
      alert("Please enter both sender and content.");
      return;
    }
    setSimulatingMessage(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: simChannel,
          sender: simSender,
          content: simContent,
          subject: simChannel === 'email' ? (simSubject || 'Support Request') : undefined
        })
      });
      const data = await res.json();
      if (res.ok) {
        setSimContent('');
        setSimSubject('');
        fetchTickets();
        if (data.ticket_id) {
          setSelectedTicketId(data.ticket_id);
          fetchMessages(data.ticket_id);
        }
      } else {
        alert(`Simulation Error: ${data.detail || 'Failed to simulate'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSimulatingMessage(false);
    }
  };


  return (
    <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-8rem)] flex flex-col animate-in fade-in duration-300">
              {/* Header Panel with Controls & Stats */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <MessageSquare className="text-blue-400 h-8 w-8" /> Customer Support Center
                  </h1>
                  <p className="text-gray-400 mt-1">Manage omnichannel customer conversations and 24/7 AI auto-reply.</p>
                </div>
                
                {/* Auto-Reply Toggles */}
                <Card className="glass-panel border-transparent shadow-lg p-3.5 flex flex-row gap-6 items-center rounded-2xl bg-gray-900/20">
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white">WhatsApp Auto-Reply</span>
                      <span className="text-[10px] text-gray-400">24/7 AI Responder</span>
                    </div>
                    <button
                      onClick={() => {
                        const newSettings = { ...supportSettings, whatsapp_auto_reply: !supportSettings.whatsapp_auto_reply };
                        saveSupportSettings(newSettings);
                      }}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        supportSettings.whatsapp_auto_reply ? 'bg-emerald-600' : 'bg-gray-800'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          supportSettings.whatsapp_auto_reply ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center gap-3 border-l border-gray-800 pl-6">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white">Email Auto-Reply</span>
                      <span className="text-[10px] text-gray-400">24/7 AI Responder</span>
                    </div>
                    <button
                      onClick={() => {
                        const newSettings = { ...supportSettings, email_auto_reply: !supportSettings.email_auto_reply };
                        saveSupportSettings(newSettings);
                      }}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        supportSettings.email_auto_reply ? 'bg-emerald-600' : 'bg-gray-800'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          supportSettings.email_auto_reply ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                </Card>
              </div>

              {/* Split layout */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0 overflow-hidden">
                
                {/* 1. Ticket List - 3 Cols */}
                <Card className="lg:col-span-3 flex flex-col h-full overflow-hidden glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-2 shadow-2xl relative">
                  <div className="px-4 py-3 bg-gray-950/40 border-b border-gray-800 flex justify-between items-center rounded-t-3xl">
                    <h3 className="font-bold text-white text-sm">Tickets</h3>
                    <span className="text-xs bg-gray-900 border border-gray-800 text-gray-400 px-2 py-0.5 rounded-full font-semibold">
                      {tickets.length} total
                    </span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-2 space-y-2">
                    {tickets.length === 0 && (
                      <p className="text-xs text-gray-500 text-center py-10">No support tickets found.</p>
                    )}
                    {tickets.map(t => {
                      const isSelected = selectedTicketId === t.id;
                      let channelIcon = "💬";
                      if (t.channel === "whatsapp") channelIcon = "🟢";
                      if (t.channel === "email") channelIcon = "✉️";

                      let priorityColor = "bg-gray-500/10 text-gray-400 border border-gray-500/20";
                      if (t.priority === "high") priorityColor = "bg-rose-500/10 text-rose-400 border border-rose-500/20";
                      if (t.priority === "medium") priorityColor = "bg-amber-500/10 text-amber-400 border border-amber-500/20";

                      return (
                        <div
                          key={t.id}
                          onClick={() => setSelectedTicketId(t.id)}
                          className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                            isSelected 
                              ? 'bg-blue-600/10 border-blue-500/40 shadow-lg glow-support' 
                              : 'bg-gray-900/20 hover:bg-gray-800/30 border-gray-800/60 text-gray-300'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-[11px] font-bold text-gray-400 flex items-center gap-1">
                              {channelIcon} {t.channel.toUpperCase()}
                            </span>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${priorityColor}`}>
                              {t.priority}
                            </span>
                          </div>
                          <h4 className="font-bold text-xs text-white truncate mb-0.5">{t.subject}</h4>
                          <p className="text-[11px] text-gray-400 truncate mb-2">{t.customer_contact}</p>
                          <div className="flex items-center justify-between">
                            <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded-full ${
                              t.status === 'open' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                            }`}>
                              {t.status.toUpperCase()}
                            </span>
                            <span className="text-[9px] text-gray-500 font-semibold">
                              {new Date(t.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>

                {/* 2. Conversation Thread & Reply - 5 Cols */}
                <Card className="lg:col-span-5 flex flex-col h-full overflow-hidden glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-0 shadow-2xl relative">
                  {selectedTicketId ? (
                    <>
                      {/* Thread Header */}
                      <div className="px-4 py-3 bg-gray-950/40 border-b border-gray-800 flex items-center justify-between">
                        <div className="truncate pr-4">
                          <h3 className="font-bold text-white text-sm truncate">
                            {tickets.find(t => t.id === selectedTicketId)?.subject}
                          </h3>
                          <p className="text-[10px] text-gray-400 truncate mt-0.5">
                            {tickets.find(t => t.id === selectedTicketId)?.customer_contact}
                          </p>
                        </div>
                        <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-semibold capitalize">
                          {tickets.find(t => t.id === selectedTicketId)?.status}
                        </span>
                      </div>

                      {/* Chat Messages Area */}
                      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-950/20">
                        {messages.length === 0 && (
                          <p className="text-xs text-gray-500 text-center py-10">No messages in this ticket.</p>
                        )}
                        {messages.map(m => {
                          const isAgent = m.sender === "agent";
                          return (
                            <div
                              key={m.id}
                              className={`flex ${isAgent ? 'justify-end' : 'justify-start'}`}
                            >
                              <div
                                className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed shadow-sm ${
                                  isAgent
                                    ? 'bg-blue-600 text-white rounded-tr-none shadow-lg shadow-blue-500/15'
                                    : 'bg-gray-900/80 border border-gray-800 text-gray-100 rounded-tl-none'
                                  }`}
                              >
                                <p className="whitespace-pre-wrap">{m.content}</p>
                                <span
                                  className={`text-[8px] mt-1 block text-right font-medium ${
                                    isAgent ? 'text-blue-100' : 'text-gray-500'
                                  }`}
                                >
                                  {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Manual Quick Reply Input */}
                      <div className="p-3 border-t border-gray-800 bg-gray-950/40">
                        <div className="flex gap-2">
                          <Textarea
                            placeholder="Type a manual response to send back to the customer..."
                            value={replyText}
                            onChange={e => setReplyText(e.target.value)}
                            className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl min-h-[50px] text-xs resize-none flex-1"
                          />
                          <Button
                            onClick={handleSendManualReply}
                            disabled={sendingReply || !replyText.trim()}
                            className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl h-auto self-stretch px-3 flex flex-col justify-center items-center shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-95"
                          >
                            <Send size={14} className="mb-0.5" />
                            <span className="text-[10px]">Send</span>
                          </Button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-gray-500">
                      <div className="text-4xl mb-2 animate-bounce">💬</div>
                      <h4 className="font-bold text-white text-sm">Select a ticket</h4>
                      <p className="text-xs text-gray-400 max-w-xs mt-1">
                        Click on a conversation from the list to view its message history and reply manually.
                      </p>
                    </div>
                  )}
                </Card>

                {/* 3. Interactive Channel Simulator - 4 Cols */}
                <Card className="lg:col-span-4 flex flex-col h-full glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl shadow-2xl relative glow-support overflow-hidden">
                  <div className="px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-b border-gray-800/60">
                    <h3 className="font-bold text-sm flex items-center gap-1.5"><Clock size={14} className="animate-spin" /> Channel Simulator</h3>
                    <p className="text-[10px] text-blue-100 mt-0.5">Test incoming customer messages and observe AI replies.</p>
                  </div>
                  <CardContent className="p-4 space-y-4 flex-1 overflow-y-auto">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-gray-300">Simulated Channel</label>
                      <Select 
                        value={simChannel} 
                        onValueChange={(val: any) => {
                          if (val) {
                            setSimChannel(val);
                            if (val === 'whatsapp') setSimSender('+15553334444');
                            else setSimSender('john.doe@example.com');
                          }
                        }}
                      >
                        <SelectTrigger className="h-9 bg-gray-900/60 border-gray-800 text-white rounded-xl"><SelectValue /></SelectTrigger>
                        <SelectContent className="bg-gray-900 border-gray-800 text-white">
                          <SelectItem value="whatsapp">WhatsApp Message</SelectItem>
                          <SelectItem value="email">Email Inbox</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-gray-300">Customer Contact Info</label>
                      <Input
                        type="text"
                        placeholder={simChannel === 'whatsapp' ? '+15553334444' : 'customer@example.com'}
                        value={simSender}
                        onChange={e => setSimSender(e.target.value)}
                        className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl h-9 text-xs"
                      />
                    </div>

                    {simChannel === 'email' && (
                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-bold text-gray-300">Email Subject</label>
                        <Input
                          type="text"
                          placeholder="e.g. Broken links on dashboard"
                          value={simSubject}
                          onChange={e => setSimSubject(e.target.value)}
                          className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl h-9 text-xs"
                        />
                      </div>
                    )}

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-gray-300">Customer Message Body</label>
                      <Textarea
                        placeholder={
                          simChannel === 'whatsapp' 
                            ? "e.g. 'Hey there, do you guys offer international shipping? if yes, what are the shipping rates?'"
                            : "e.g. 'Hello Support Team, I am having issues logging into my account. It says password incorrect but I reset it already. Can you please help?'"
                        }
                        value={simContent}
                        onChange={e => setSimContent(e.target.value)}
                        className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl min-h-[100px] text-xs resize-none"
                      />
                    </div>

                    <div className="pt-2">
                      <Button
                        onClick={handleSimulateMessage}
                        disabled={simulatingMessage || !simSender.trim() || !simContent.trim()}
                        className="w-full h-10 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100"
                      >
                        {simulatingMessage ? 'Sending Mock Message...' : 'Simulate Customer Message'}
                      </Button>
                    </div>

                    <div className="rounded-xl bg-blue-950/20 border border-blue-900/30 p-3.5 text-[11px] text-blue-300 space-y-1.5 leading-relaxed">
                      <p className="font-bold flex items-center gap-1">
                        <Clock size={12} /> Natural Human-Like Delays:
                      </p>
                      <p>• <strong>WhatsApp:</strong> AI replies are delayed by 4-5 minutes.</p>
                      <p>• <strong>Email:</strong> AI replies are delayed by 20 minutes.</p>
                      <p className="text-[10px] text-blue-400 mt-1 italic">
                        *Note: If you send a manual reply during this delay window, the AI will automatically cancel its pending auto-reply.
                      </p>
                    </div>
                  </CardContent>
                </Card>

              </div>
            </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Users, Bot, Loader2, Send, Clock, Plus, Zap, MessageSquare } from 'lucide-react';

interface CoordinationViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
}

export default function CoordinationView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
}: CoordinationViewProps) {
  // Coordination states relocated here
  const [meetings, setMeetings] = useState<any[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [selectedMeeting, setSelectedMeeting] = useState<any | null>(null);
  const [isCreateMeetingOpen, setIsCreateMeetingOpen] = useState(false);
  const [manualMeetingTitle, setManualMeetingTitle] = useState('');
  const [manualMeetingTopic, setManualMeetingTopic] = useState('');
  const [manualMeetingParticipants, setManualMeetingParticipants] = useState<string[]>(['Support AI', 'Sales AI']);
  const [manualMeetingLoading, setManualMeetingLoading] = useState(false);

  useEffect(() => {
    if (token) {
      fetchMeetings();
    }
  }, [token]);

  // Handle auto-refresh of selected meeting details
  useEffect(() => {
    if (selectedMeetingId && token) {
      fetchMeetingDetails(selectedMeetingId);
      
      let interval: NodeJS.Timeout | null = null;
      if (selectedMeeting?.status === 'running' || selectedMeeting?.status === 'scheduled') {
        interval = setInterval(() => {
          fetchMeetingDetails(selectedMeetingId);
        }, 5000);
      }
      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [selectedMeetingId, selectedMeeting?.status, token]);

  // Coordination functions
    const fetchMeetings = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings`);
      if (res.ok) {
        const data = await res.json();
        setMeetings(data);
      }
    } catch (e) {
      console.error(e);
    }
  };


    const fetchMeetingDetails = async (meetingId: string) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedMeeting(data);
      }
    } catch (e) {
      console.error(e);
    }
  };


    const handleCreateManualMeeting = async () => {
    if (!manualMeetingTitle || !manualMeetingTopic) return;
    setManualMeetingLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: manualMeetingTitle,
          topic: manualMeetingTopic,
          participants: manualMeetingParticipants
        })
      });
      const data = await res.json();
      if (res.ok) {
        setManualMeetingTitle('');
        setManualMeetingTopic('');
        setIsCreateMeetingOpen(false);
        fetchMeetings();
        if (data.id) {
          setSelectedMeetingId(data.id);
        }
      } else {
        alert(`Error: ${data.detail || 'Failed to start boardroom meeting'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setManualMeetingLoading(false);
    }
  };



  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <Users className="text-amber-400 h-8 w-8 animate-pulse" /> AI Agent Boardroom
                  </h1>
                  <p className="text-gray-400 mt-1">Cross-agent coordination meetings, autonomous escalations, and executive boardroom alignments.</p>
                </div>
                <div className="flex gap-2">
                  <Dialog open={isCreateMeetingOpen} onOpenChange={setIsCreateMeetingOpen}>
                    <DialogTrigger render={
                      <Button className="bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold h-10 px-5 rounded-xl shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] active:scale-95 text-xs flex items-center gap-1.5" />
                    }>
                      <Users size={16} /> Summon Boardroom Meeting
                    </DialogTrigger>
                    <DialogContent className="glass-panel border border-gray-800 text-white max-w-md rounded-2xl p-6">
                      <DialogHeader>
                        <DialogTitle className="text-xl font-bold text-white">Call AI Boardroom Meeting</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 mt-4">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-gray-400">Meeting Title</label>
                          <Input
                            placeholder="e.g. Q3 Strategic Marketing Alignment"
                            value={manualMeetingTitle}
                            onChange={(e) => setManualMeetingTitle(e.target.value)}
                            className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-gray-400">Meeting Topic / Agenda Context</label>
                          <Textarea
                            placeholder="Detail what the agents need to coordinate on..."
                            value={manualMeetingTopic}
                            onChange={(e) => setManualMeetingTopic(e.target.value)}
                            className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-24"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-gray-400">Invite Department Specialists (CEO AI always coordinates)</label>
                          <div className="grid grid-cols-2 gap-2 mt-1">
                            {['Support AI', 'Sales AI', 'Finance AI', 'HR AI', 'Marketing AI'].map(agentName => {
                              const isChecked = manualMeetingParticipants.includes(agentName);
                              return (
                                <button
                                  key={agentName}
                                  type="button"
                                  onClick={() => {
                                    if (isChecked) {
                                      setManualMeetingParticipants(manualMeetingParticipants.filter(p => p !== agentName));
                                    } else {
                                      setManualMeetingParticipants([...manualMeetingParticipants, agentName]);
                                    }
                                  }}
                                  className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all text-left flex items-center justify-between ${
                                    isChecked
                                      ? 'bg-amber-600/20 border-amber-500 text-white'
                                      : 'bg-gray-900/50 border-gray-800 text-gray-400 hover:border-gray-700'
                                  }`}
                                >
                                  {agentName}
                                  {isChecked && <span className="text-amber-400 font-bold">✓</span>}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                        <Button
                          onClick={handleCreateManualMeeting}
                          disabled={manualMeetingLoading || !manualMeetingTitle || !manualMeetingTopic}
                          className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold h-11 rounded-xl shadow-lg mt-4 shadow-amber-500/20"
                        >
                          {manualMeetingLoading ? 'Summoning Agents...' : 'Summon Boardroom'}
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* 1. Meeting List Side-Panel */}
                <div className="lg:col-span-1 space-y-6">
                  <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                    <CardHeader>
                      <CardTitle className="text-xl text-white font-extrabold tracking-tight">Boardroom Sessions</CardTitle>
                      <CardDescription className="text-gray-400 text-xs mt-1">Select an active or archived courtroom/boardroom simulation.</CardDescription>
                    </CardHeader>
                    <CardContent className="px-2 pb-6">
                      {meetings.length === 0 ? (
                        <p className="text-xs text-gray-500 text-center py-10">No boardroom sessions found. Trigger an escalation from support or call one manually.</p>
                      ) : (
                        <div className="flex flex-col gap-2 max-h-[500px] overflow-y-auto pr-1">
                          {meetings.map((m) => {
                            const isSelected = selectedMeetingId === m.id;
                            const isCompleted = m.status === 'completed';
                            return (
                              <div
                                key={m.id}
                                onClick={() => setSelectedMeetingId(m.id)}
                                className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col gap-2 ${
                                  isSelected
                                    ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.12)] shadow-xl'
                                    : 'bg-transparent border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                                    m.trigger_type === 'support_ticket'
                                      ? 'bg-blue-900/30 text-blue-400 border border-blue-900/40'
                                      : m.trigger_type === 'manual'
                                      ? 'bg-purple-900/30 text-purple-400 border border-purple-900/40'
                                      : 'bg-amber-900/30 text-amber-400 border border-amber-900/40'
                                  }`}>
                                    {m.trigger_type}
                                  </span>
                                  <span className={`flex items-center gap-1 text-[10px] font-bold ${
                                    isCompleted ? 'text-emerald-400' : 'text-amber-400'
                                  }`}>
                                    <span className={`h-1.5 w-1.5 rounded-full ${isCompleted ? 'bg-emerald-400' : 'bg-amber-400 animate-ping'}`} />
                                    {m.status}
                                  </span>
                                </div>
                                <h3 className="font-bold text-white text-sm leading-tight">{m.title}</h3>
                                <p className="text-gray-400 text-xs line-clamp-1">{m.context_summary?.replace(/Custom Topic:|Inquiry:/g, '').trim()}</p>
                                <span className="text-[10px] text-gray-500 text-right mt-1">
                                  {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* 2. Main Visual Boardroom Panel & Action items */}
                <div className="lg:col-span-2 space-y-6">
                  {selectedMeetingId && selectedMeeting ? (
                    <div className="space-y-6">
                      {/* Interactive Boardroom Table visualization */}
                      <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                        <CardTitle className="text-lg text-white font-extrabold mb-4">Boardroom Table Status</CardTitle>
                        
                        {/* Oval Boardroom Table representation */}
                        <div className="relative bg-gray-950/60 rounded-3xl border border-gray-800 p-8 min-h-60 flex items-center justify-center">
                          <div className="absolute inset-8 border-2 border-dashed border-amber-500/20 rounded-full flex items-center justify-center bg-gray-900/45">
                            <span className="text-xs text-amber-500/40 uppercase tracking-widest font-black">AI Executive Board</span>
                          </div>
                          
                          {/* Render participants positioned dynamically around the table */}
                          <div className="w-full grid grid-cols-3 gap-6 relative z-10">
                            {['CEO AI', 'Support AI', 'Sales AI', 'Finance AI', 'HR AI', 'Marketing AI'].map((agentName) => {
                              const isParticipant = selectedMeeting.participants.includes(agentName);
                              if (!isParticipant) return null;
                              
                              // Check if this agent sent the last message in the transcript
                              const lastMsg = selectedMeeting.transcript && selectedMeeting.transcript.length > 0
                                ? selectedMeeting.transcript[selectedMeeting.transcript.length - 1]
                                : null;
                              const isSpeaking = lastMsg && lastMsg.sender === agentName;
                              
                              return (
                                <div
                                  key={agentName}
                                  className={`flex flex-col items-center p-3 rounded-2xl border transition-all duration-300 ${
                                    isSpeaking
                                      ? 'bg-amber-600/10 border-amber-500 scale-105 shadow-lg shadow-amber-500/15'
                                      : 'bg-gray-900/80 border-gray-800/80 opacity-70'
                                  }`}
                                >
                                  <div className={`p-2 rounded-full mb-2 ${
                                    isSpeaking ? 'bg-amber-500 text-gray-950' : 'bg-gray-800 text-gray-400'
                                  }`}>
                                    <Users size={20} />
                                  </div>
                                  <span className="text-xs font-bold text-white">{agentName}</span>
                                  <span className="text-[10px] text-gray-400 text-center mt-1">
                                    {isSpeaking ? (
                                      <span className="text-amber-400 font-bold animate-pulse">● Speaking...</span>
                                    ) : (
                                      <span>Participant</span>
                                    )}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </Card>

                      {/* Live Discussion Transcript */}
                      <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                        <div className="flex justify-between items-center mb-4">
                          <CardTitle className="text-lg text-white font-extrabold flex items-center gap-2">
                            <MessageSquare className="text-amber-500" size={18} /> Discussion Transcript
                          </CardTitle>
                          <span className="text-xs text-gray-400">{selectedMeeting.transcript?.length || 0} messages</span>
                        </div>

                        <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
                          {selectedMeeting.transcript?.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-10 space-y-2">
                              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-amber-500" />
                              <p className="text-xs text-gray-500">Boardroom assembling. Agents are analyzing context and entering boardroom...</p>
                            </div>
                          ) : (
                            selectedMeeting.transcript.map((msg: any, idx: number) => {
                              const isCEO = msg.sender === 'CEO AI';
                              return (
                                <div key={idx} className={`p-4 rounded-2xl border transition-all ${
                                  isCEO
                                    ? 'bg-amber-950/20 border-amber-900/30'
                                    : 'bg-gray-900/50 border-gray-800/80'
                                }`}>
                                  <div className="flex justify-between items-center mb-1">
                                    <span className={`text-xs font-bold ${isCEO ? 'text-amber-400' : 'text-white'}`}>
                                      {msg.sender}
                                    </span>
                                    <span className="text-[9px] text-gray-500">{msg.timestamp}</span>
                                  </div>
                                  <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </Card>

                      {/* Action Items Panel */}
                      <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                        <CardTitle className="text-lg text-white font-extrabold mb-4 flex items-center gap-2">
                          <Zap className="text-amber-500" size={18} /> CEO Board Directives & Action Items
                        </CardTitle>
                        
                        <div className="space-y-3">
                          {selectedMeeting.action_items?.length === 0 ? (
                            <p className="text-xs text-gray-500 py-4 text-center">Waiting for meeting to conclude to establish boardroom directives...</p>
                          ) : (
                            selectedMeeting.action_items.map((action: any) => {
                              const isComp = action.status === 'completed';
                              const isExec = action.status === 'executing';
                              const isFail = action.status === 'failed';
                              
                              return (
                                <div
                                  key={action.id}
                                  className={`p-4 rounded-xl border flex items-center justify-between gap-4 transition-all ${
                                    isComp
                                      ? 'bg-emerald-950/15 border-emerald-900/35 text-emerald-100'
                                      : isExec
                                      ? 'bg-amber-950/15 border-amber-900/35 text-amber-100'
                                      : isFail
                                      ? 'bg-red-950/15 border-red-900/35 text-red-100'
                                      : 'bg-gray-900/50 border-gray-800 text-gray-300'
                                  }`}
                                >
                                  <div className="flex flex-col gap-1">
                                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-400">
                                      {action.assigned_to}
                                    </span>
                                    <p className="text-xs">{action.description}</p>
                                  </div>
                                  <div className="flex items-center">
                                    {isComp && (
                                      <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                                        ✓ Completed
                                      </span>
                                    )}
                                    {isExec && (
                                      <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                                        <span className="animate-spin rounded-full h-3 w-3 border-b-2 border-amber-400" />
                                        Executing...
                                      </span>
                                    )}
                                    {isFail && (
                                      <span className="text-xs font-bold text-red-400 flex items-center gap-1">
                                        ✗ Failed
                                      </span>
                                    )}
                                    {action.status === 'pending' && (
                                      <span className="text-xs font-bold text-gray-500">
                                        Pending
                                      </span>
                                    )}
                                  </div>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </Card>
                    </div>
                  ) : (
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-12 text-center flex flex-col items-center justify-center min-h-[500px]">
                      <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                      <div className="p-4 bg-amber-500/10 text-amber-500 rounded-full mb-4">
                        <Users size={36} />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Welcome to the AI Boardroom</h2>
                      <p className="text-gray-400 text-sm max-w-md mt-2">
                        Escalated ticket events automatically trigger emergency board meetings here. CEO AI and specialized department AI employees gather in real-time, align on context, and formulate auto-executing directives.
                      </p>
                      <Button
                        onClick={() => setIsCreateMeetingOpen(true)}
                        className="mt-6 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold h-10 px-6 rounded-xl shadow-lg shadow-amber-500/20"
                      >
                        Summon Boardroom Meeting
                      </Button>
                    </Card>
                  )}
                </div>
              </div>
            </div>
  );
}

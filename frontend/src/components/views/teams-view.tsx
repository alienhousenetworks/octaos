'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Bot, Loader2, Send, Cpu, Trash2, Edit2, Users, Plus, Check } from 'lucide-react';

interface TeamsViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  teams: any[];
  setTeams: React.Dispatch<React.SetStateAction<any[]>>;
}

export default function TeamsView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  teams,
  setTeams,
}: TeamsViewProps) {
  // Teams states relocated here
  const [isCreateTeamOpen, setIsCreateTeamOpen] = useState(false);
  const [isEditTeamOpen, setIsEditTeamOpen] = useState(false);
  const [teamFormName, setTeamFormName] = useState('');
  const [teamFormAgents, setTeamFormAgents] = useState<string[]>([]);
  const [editingTeamId, setEditingTeamId] = useState<string | null>(null);

  const [testAgentName, setTestAgentName] = useState<string | null>(null);
  const [testAgentTeamId, setTestAgentTeamId] = useState<string | null>(null);
  const [testInput, setTestInput] = useState('');
  const [testResponse, setTestResponse] = useState('');
  const [testAgentLoading, setTestAgentLoading] = useState(false);

  const [configAgentName, setConfigAgentName] = useState<string | null>(null);
  const [configAgentTeamId, setConfigAgentTeamId] = useState<string | null>(null);
  const [configAgentProvider, setConfigAgentProvider] = useState('anthropic');
  const [configAgentModel, setConfigAgentModel] = useState('claude-sonnet-4-6');
  const [configAgentInstructions, setConfigAgentInstructions] = useState('');
  const [savingConfigLoading, setSavingConfigLoading] = useState(false);

  // Teams functions
    const handleCreateTeam = async () => {
    if (!teamFormName.trim() || teamFormAgents.length === 0) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/teams`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: teamFormName,
          agents: teamFormAgents,
          config: {}
        })
      });
      if (res.ok) {
        setIsCreateTeamOpen(false);
        setTeamFormName('');
        setTeamFormAgents([]);
        const tmRes = await fetchWithAuth(`${API_URL}/dashboard/teams`);
        if (tmRes.ok) setTeams(await tmRes.json());
      }
    } catch (err) {
      console.error("Failed to create team:", err);
    }
  };


    const handleUpdateTeam = async () => {
    if (!editingTeamId || !teamFormName.trim() || teamFormAgents.length === 0) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/teams/${editingTeamId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: teamFormName,
          agents: teamFormAgents
        })
      });
      if (res.ok) {
        setIsEditTeamOpen(false);
        setTeamFormName('');
        setTeamFormAgents([]);
        setEditingTeamId(null);
        const tmRes = await fetchWithAuth(`${API_URL}/dashboard/teams`);
        if (tmRes.ok) setTeams(await tmRes.json());
      }
    } catch (err) {
      console.error("Failed to update team:", err);
    }
  };


    const handleDeleteTeam = async (teamId: string) => {
    if (!confirm("Are you sure you want to delete this AI Team?")) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/teams/${teamId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        const tmRes = await fetchWithAuth(`${API_URL}/dashboard/teams`);
        if (tmRes.ok) setTeams(await tmRes.json());
      }
    } catch (err) {
      console.error("Failed to delete team:", err);
    }
  };


    const handleSaveAgentConfig = async () => {
    if (!configAgentTeamId || !configAgentName) return;
    setSavingConfigLoading(true);
    try {
      const team = teams.find(t => t.id === configAgentTeamId);
      if (!team) return;
      
      const newConfig = {
        ...(team.config || {}),
        [configAgentName]: {
          provider: configAgentProvider,
          model: configAgentModel,
          instructions: configAgentInstructions
        }
      };
      
      const res = await fetchWithAuth(`${API_URL}/dashboard/teams/${configAgentTeamId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config: newConfig
        })
      });
      
      if (res.ok) {
        const tmRes = await fetchWithAuth(`${API_URL}/dashboard/teams`);
        if (tmRes.ok) setTeams(await tmRes.json());
        setConfigAgentName(null);
        setConfigAgentTeamId(null);
        setConfigAgentInstructions('');
      }
    } catch (err) {
      console.error("Failed to save agent config:", err);
    } finally {
      setSavingConfigLoading(false);
    }
  };


    const handleTestAgent = async () => {
    if (!testAgentName || !testInput.trim()) return;
    setTestAgentLoading(true);
    setTestResponse('');
    try {
      const team = teams.find(t => t.id === testAgentTeamId);
      const agentConfig = team?.config?.[testAgentName] || {};
      
      const res = await fetchWithAuth(`${API_URL}/dashboard/teams/test-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_name: testAgentName,
          message: testInput,
          provider: agentConfig.provider || 'gemini',
          model: agentConfig.model || 'gemini-2.5-flash',
          custom_instructions: agentConfig.instructions || ''
        })
      });
      if (res.ok) {
        const data = await res.json();
        setTestResponse(data.response);
      } else {
        const errData = await res.json();
        setTestResponse(`Error: ${errData.detail || 'Failed to get response.'}`);
      }
    } catch (err) {
      setTestResponse(`Error: ${err}`);
    } finally {
      setTestAgentLoading(false);
    }
  };



  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-16 animate-in fade-in duration-300">
              {/* Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800/60 pb-6">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
                    <Users className="text-violet-500 h-9 w-9" /> Autonomous AI Teams
                  </h1>
                  <p className="text-gray-400 mt-1">Deploy specialized autonomous AI agents tailored for your business goals.</p>
                </div>
                <Button 
                  onClick={() => {
                    setTeamFormName('');
                    setTeamFormAgents([]);
                    setIsCreateTeamOpen(true);
                  }}
                  className="bg-violet-600 hover:bg-violet-500 text-white font-bold h-10 rounded-xl px-5 shadow-lg shadow-violet-500/20 flex items-center gap-2 hover:scale-[1.02] active:scale-95 transition-all"
                >
                  <Plus size={16} /> Create Custom Team
                </Button>
              </div>

              {/* Teams List */}
              <div className="grid grid-cols-1 gap-8">
                {teams.map(team => {
                  const isDefaultTeam = team.name === "Growth Team" || team.name === "Operations Team";
                  return (
                    <Card key={team.id} className="glass-panel border-transparent hover:border-violet-500/10 transition-all duration-300 rounded-3xl overflow-hidden shadow-2xl relative p-6 md:p-8">
                      <div className="absolute top-0 left-0 w-2 h-full bg-gradient-to-b from-violet-600 to-indigo-600" />
                      
                      {/* Team Header Card */}
                      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-gray-800/60">
                        <div>
                          <div className="flex items-center gap-2.5">
                            <h2 className="text-2xl font-black text-white">{team.name}</h2>
                            {isDefaultTeam ? (
                              <span className="text-[10px] bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full font-bold">
                                Default Team
                              </span>
                            ) : (
                              <span className="text-[10px] bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2 py-0.5 rounded-full font-bold">
                                Custom Team
                              </span>
                            )}
                          </div>
                          <p className="text-gray-400 text-xs mt-1">Created on {new Date(team.created_at || Date.now()).toLocaleDateString()}</p>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingTeamId(team.id);
                              setTeamFormName(team.name);
                              setTeamFormAgents(team.agents);
                              setIsEditTeamOpen(true);
                            }}
                            className="bg-transparent border-gray-800 text-gray-450 hover:text-white hover:bg-gray-900 rounded-xl h-8 text-xs font-bold"
                          >
                            <Edit2 size={12} className="mr-1.5" /> Edit Team
                          </Button>
                          {!isDefaultTeam && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDeleteTeam(team.id)}
                              className="bg-transparent border-rose-950/30 text-rose-400 hover:bg-rose-950/20 hover:border-rose-900/30 rounded-xl h-8 text-xs font-bold"
                            >
                              <Trash2 size={12} className="mr-1.5" /> Delete
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* Team Stats */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-6 border-b border-gray-800/40">
                        {team.name === "Growth Team" ? (
                          <>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Leads Sourced</span>
                              <span className="text-2xl font-black text-white mt-1 block">1,420</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Campaign Posts</span>
                              <span className="text-2xl font-black text-white mt-1 block">124</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Outreach DMs</span>
                              <span className="text-2xl font-black text-white mt-1 block">458</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Est. Revenue</span>
                              <span className="text-2xl font-black text-emerald-400 mt-1 block">$18,450</span>
                            </div>
                          </>
                        ) : team.name === "Operations Team" ? (
                          <>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Tickets Closed</span>
                              <span className="text-2xl font-black text-white mt-1 block">4,812</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Avg Response</span>
                              <span className="text-2xl font-black text-white mt-1 block">4.2m</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Auto-Replies</span>
                              <span className="text-2xl font-black text-white mt-1 block">94.2%</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Invoices Matched</span>
                              <span className="text-2xl font-black text-emerald-400 mt-1 block">98.7%</span>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Active Tasks</span>
                              <span className="text-2xl font-black text-white mt-1 block">8</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Success Rate</span>
                              <span className="text-2xl font-black text-emerald-400 mt-1 block">99.2%</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Uptime</span>
                              <span className="text-2xl font-black text-white mt-1 block">100%</span>
                            </div>
                            <div className="bg-gray-900/40 border border-gray-800/30 rounded-2xl p-4">
                              <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Total Logs</span>
                              <span className="text-2xl font-black text-white mt-1 block">34</span>
                            </div>
                          </>
                        )}
                      </div>

                      {/* Agents Section */}
                      <div className="pt-6">
                        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                          <Bot size={14} className="text-violet-400" /> Active Agents in Team
                        </h3>
                        <div className="space-y-4">
                          {team.agents.map((agent: string) => {
                            const agentConfig = team.config?.[agent] || {};
                            const isConfiguring = configAgentName === agent && configAgentTeamId === team.id;
                            const isTesting = testAgentName === agent && testAgentTeamId === team.id;
                            
                            return (
                              <div key={agent} className="bg-gray-950/40 border border-gray-800/40 rounded-2xl p-4 md:p-5 relative transition-all hover:bg-gray-950/60">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                  <div className="flex items-start gap-3">
                                    <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/10 flex-shrink-0 mt-0.5">
                                      <Bot size={20} className="text-white" />
                                    </div>
                                    <div>
                                      <div className="flex items-center gap-2 flex-wrap">
                                        <h4 className="font-extrabold text-white text-sm">{agent}</h4>
                                        <span className="flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full text-[9px] font-bold">
                                          <span className="h-1 w-1 rounded-full bg-emerald-400 animate-pulse" /> Running / Idle
                                        </span>
                                      </div>
                                      <p className="text-xs text-gray-450 mt-1 leading-relaxed">
                                        {agent === "Sales AI" ? "Prospecting, scraping, lead generation, and outbound sequencing." :
                                         agent === "Marketing AI" ? "Content strategy, social media copy, and image/video production." :
                                         agent === "Support AI" ? "Ticket analysis, customer auto-responses, and sentiment classification." :
                                         agent === "Finance AI" ? "Invoice routing, ledger validation, and expense analysis." :
                                         agent === "HR AI" ? "Candidate screening, spec matching, and outreach planning." :
                                         agent === "CEO AI" ? "Strategic multi-agent planning and cross-team goal orchestration." :
                                         "Autonomous business operations execution."}
                                      </p>
                                      
                                      {/* Saved Provider / Model Badge */}
                                      <div className="flex gap-2 mt-2">
                                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-gray-900 border border-gray-800 text-gray-400 uppercase">
                                          Provider: {agentConfig.provider || "System default"}
                                        </span>
                                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-gray-900 border border-gray-800 text-gray-400">
                                          Model: {agentConfig.model || "Auto-routed"}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                  
                                  {/* Action Buttons */}
                                  <div className="flex items-center gap-2 self-end sm:self-center">
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => {
                                        if (isTesting) {
                                          setTestAgentName(null);
                                          setTestAgentTeamId(null);
                                        } else {
                                          setTestAgentName(agent);
                                          setTestAgentTeamId(team.id);
                                          setTestInput('');
                                          setTestResponse('');
                                          setConfigAgentName(null);
                                          setConfigAgentTeamId(null);
                                        }
                                      }}
                                      className={`h-8 text-[11px] font-bold rounded-xl px-3 flex items-center gap-1.5 transition-all ${
                                        isTesting 
                                          ? 'bg-violet-600 text-white hover:bg-violet-500 border-transparent shadow-lg shadow-violet-500/20'
                                          : 'bg-transparent border-gray-800 text-gray-300 hover:text-white hover:bg-gray-900'
                                      }`}
                                    >
                                      <Send size={11} /> Test Chat
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => {
                                        if (isConfiguring) {
                                          setConfigAgentName(null);
                                          setConfigAgentTeamId(null);
                                        } else {
                                          setConfigAgentName(agent);
                                          setConfigAgentTeamId(team.id);
                                          setConfigAgentProvider(agentConfig.provider || 'anthropic');
                                          setConfigAgentModel(agentConfig.model || 'claude-sonnet-4-6');
                                          setConfigAgentInstructions(agentConfig.instructions || '');
                                          setTestAgentName(null);
                                          setTestAgentTeamId(null);
                                        }
                                      }}
                                      className={`h-8 text-[11px] font-bold rounded-xl px-3 flex items-center gap-1.5 transition-all ${
                                        isConfiguring
                                          ? 'bg-indigo-600 text-white hover:bg-indigo-500 border-transparent shadow-lg shadow-indigo-500/20'
                                          : 'bg-transparent border-gray-800 text-gray-300 hover:text-white hover:bg-gray-900'
                                      }`}
                                    >
                                      <Cpu size={11} /> Configure
                                    </Button>
                                  </div>
                                </div>

                                {/* CONFIGURATION DRAWER */}
                                {isConfiguring && (
                                  <div className="mt-4 pt-4 border-t border-gray-900/60 flex flex-col gap-4 animate-in slide-in-from-top-2 duration-200">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                      <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase block">LLM Provider</label>
                                        <Select 
                                          value={configAgentProvider} 
                                          onValueChange={(val) => {
                                            if (val) {
                                              setConfigAgentProvider(val);
                                              if (val === 'anthropic') setConfigAgentModel('claude-sonnet-4-6');
                                              else if (val === 'openai') setConfigAgentModel('gpt-4o');
                                              else if (val === 'gemini') setConfigAgentModel('gemini-2.5-pro');
                                            }
                                          }}
                                        >
                                          <SelectTrigger className="bg-gray-900 border-gray-800 text-white h-9 text-xs focus:ring-0">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent className="bg-gray-900 border-gray-800 text-white">
                                            <SelectItem value="anthropic">Claude (Anthropic)</SelectItem>
                                            <SelectItem value="openai">OpenAI</SelectItem>
                                            <SelectItem value="gemini">Google Gemini</SelectItem>
                                          </SelectContent>
                                        </Select>
                                      </div>
                                      <div className="space-y-1">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase block">Model</label>
                                        <Select 
                                          value={configAgentModel} 
                                          onValueChange={(val) => val && setConfigAgentModel(val)}
                                        >
                                          <SelectTrigger className="bg-gray-900 border-gray-800 text-white h-9 text-xs focus:ring-0">
                                            <SelectValue />
                                          </SelectTrigger>
                                          <SelectContent className="bg-gray-900 border-gray-800 text-white">
                                            {configAgentProvider === 'anthropic' && (
                                              <>
                                                <SelectItem value="claude-sonnet-4-6">Claude 3.5 Sonnet 4.6</SelectItem>
                                                <SelectItem value="claude-opus-4-8">Claude 3 Opus 4.8</SelectItem>
                                                <SelectItem value="claude-haiku-4-5-20251001">Claude 3.5 Haiku 4.5</SelectItem>
                                              </>
                                            )}
                                            {configAgentProvider === 'openai' && (
                                              <>
                                                <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                                                <SelectItem value="gpt-4o-mini">GPT-4o-mini</SelectItem>
                                              </>
                                            )}
                                            {configAgentProvider === 'gemini' && (
                                              <>
                                                <SelectItem value="gemini-2.5-pro">Gemini 2.5 Pro</SelectItem>
                                                <SelectItem value="gemini-2.5-flash">Gemini 2.5 Flash</SelectItem>
                                                <SelectItem value="gemini-2.0-flash">Gemini 2.0 Flash</SelectItem>
                                              </>
                                            )}
                                          </SelectContent>
                                        </Select>
                                      </div>
                                    </div>
                                    <div className="space-y-1">
                                      <label className="text-[10px] font-bold text-gray-500 uppercase block">Custom System Prompt/Instructions</label>
                                      <Textarea
                                        placeholder={`Enter custom rules or brand guidelines specific to ${agent}...`}
                                        value={configAgentInstructions}
                                        onChange={e => setConfigAgentInstructions(e.target.value)}
                                        className="bg-gray-900 border-gray-800 text-white text-xs min-h-[80px] max-h-[200px] rounded-xl focus:border-violet-500"
                                      />
                                    </div>
                                    <div className="flex gap-2 justify-end">
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => {
                                          setConfigAgentName(null);
                                          setConfigAgentTeamId(null);
                                        }}
                                        className="h-8 border-gray-800 text-gray-400 hover:text-white rounded-xl text-xs"
                                      >
                                        Cancel
                                      </Button>
                                      <Button
                                        size="sm"
                                        onClick={handleSaveAgentConfig}
                                        disabled={savingConfigLoading}
                                        className="h-8 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-xs font-bold"
                                      >
                                        {savingConfigLoading ? <Loader2 size={12} className="animate-spin mr-1.5" /> : null}
                                        Save Configuration
                                      </Button>
                                    </div>
                                  </div>
                                )}

                                {/* TEST CONSOLE DRAWER */}
                                {isTesting && (
                                  <div className="mt-4 pt-4 border-t border-gray-900/60 flex flex-col gap-4 animate-in slide-in-from-top-2 duration-200">
                                    <div className="space-y-1">
                                      <label className="text-[10px] font-bold text-gray-500 uppercase block">Test Prompt Input</label>
                                      <div className="flex gap-2 items-end">
                                        <Textarea
                                          placeholder={`Ask ${agent} to perform a sample task... (e.g. "Create a sales email to Google executives")`}
                                          value={testInput}
                                          onChange={e => setTestInput(e.target.value)}
                                          className="bg-gray-900 border-gray-800 text-white text-xs min-h-[48px] max-h-[120px] rounded-xl flex-1 focus:border-violet-500"
                                        />
                                        <Button
                                          onClick={handleTestAgent}
                                          disabled={testAgentLoading || !testInput.trim()}
                                          className="h-10 bg-violet-600 hover:bg-violet-500 text-white rounded-xl font-bold px-4 flex items-center justify-center"
                                        >
                                          {testAgentLoading ? <Loader2 size={14} className="animate-spin" /> : "Send"}
                                        </Button>
                                      </div>
                                    </div>
                                    {testResponse && (
                                      <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase block">Agent Response</label>
                                        <div className="bg-gray-900/80 border border-gray-800 text-gray-250 p-4 rounded-2xl text-xs font-mono whitespace-pre-wrap leading-relaxed max-h-[300px] overflow-y-auto">
                                          {testResponse}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>

              {/* Dialog for Creating Team */}
              <Dialog open={isCreateTeamOpen} onOpenChange={setIsCreateTeamOpen}>
                <DialogContent className="glass-panel border-violet-500/20 text-white rounded-3xl max-w-md">
                  <DialogHeader>
                    <DialogTitle className="text-white font-extrabold text-xl">Create Custom AI Team</DialogTitle>
                  </DialogHeader>
                  <div className="flex flex-col gap-4 py-4">
                    <div className="space-y-1">
                      <label className="text-xs font-bold text-gray-400 uppercase">Team Name</label>
                      <Input 
                        placeholder="e.g. Operations & Finance Team" 
                        value={teamFormName} 
                        onChange={e => setTeamFormName(e.target.value)}
                        className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 rounded-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-gray-400 uppercase block">Select AI Agents</label>
                      <div className="grid grid-cols-2 gap-2">
                        {['Sales AI', 'Marketing AI', 'Support AI', 'Finance AI', 'HR AI', 'CEO AI'].map(agent => {
                          const isSelected = teamFormAgents.includes(agent);
                          return (
                            <button
                              key={agent}
                              type="button"
                              onClick={() => {
                                if (isSelected) {
                                  setTeamFormAgents(teamFormAgents.filter(a => a !== agent));
                                } else {
                                  setTeamFormAgents([...teamFormAgents, agent]);
                                }
                              }}
                              className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                                isSelected 
                                  ? 'bg-violet-600/20 border-violet-500 text-violet-300 shadow-md shadow-violet-500/5' 
                                  : 'bg-gray-900/40 border-gray-800 text-gray-400 hover:border-gray-700'
                              }`}
                            >
                              <span>{agent}</span>
                              {isSelected && <Check size={12} className="text-violet-400" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    <Button 
                      onClick={handleCreateTeam}
                      disabled={!teamFormName.trim() || teamFormAgents.length === 0}
                      className="bg-violet-600 hover:bg-violet-500 text-white font-bold h-10 rounded-xl mt-2 w-full transition-all hover:scale-[1.02] active:scale-95 shadow-lg shadow-violet-500/20"
                    >
                      Create Team
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Dialog for Editing Team */}
              <Dialog open={isEditTeamOpen} onOpenChange={setIsEditTeamOpen}>
                <DialogContent className="glass-panel border-violet-500/20 text-white rounded-3xl max-w-md">
                  <DialogHeader>
                    <DialogTitle className="text-white font-extrabold text-xl">Modify AI Team</DialogTitle>
                  </DialogHeader>
                  <div className="flex flex-col gap-4 py-4">
                    <div className="space-y-1">
                      <label className="text-xs font-bold text-gray-400 uppercase">Team Name</label>
                      <Input 
                        placeholder="Team Name" 
                        value={teamFormName} 
                        onChange={e => setTeamFormName(e.target.value)}
                        className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 rounded-xl"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-bold text-gray-400 uppercase block">Select AI Agents</label>
                      <div className="grid grid-cols-2 gap-2">
                        {['Sales AI', 'Marketing AI', 'Support AI', 'Finance AI', 'HR AI', 'CEO AI'].map(agent => {
                          const isSelected = teamFormAgents.includes(agent);
                          return (
                            <button
                              key={agent}
                              type="button"
                              onClick={() => {
                                if (isSelected) {
                                  setTeamFormAgents(teamFormAgents.filter(a => a !== agent));
                                } else {
                                  setTeamFormAgents([...teamFormAgents, agent]);
                                }
                              }}
                              className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                                isSelected 
                                  ? 'bg-violet-600/20 border-violet-500 text-violet-300 shadow-md shadow-violet-500/5' 
                                  : 'bg-gray-900/40 border-gray-800 text-gray-400 hover:border-gray-700'
                              }`}
                            >
                              <span>{agent}</span>
                              {isSelected && <Check size={12} className="text-violet-400" />}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    <Button 
                      onClick={handleUpdateTeam}
                      disabled={!teamFormName.trim() || teamFormAgents.length === 0}
                      className="bg-violet-600 hover:bg-violet-500 text-white font-bold h-10 rounded-xl mt-2 w-full transition-all hover:scale-[1.02] active:scale-95 shadow-lg shadow-violet-500/20"
                    >
                      Save Changes
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
  );
}

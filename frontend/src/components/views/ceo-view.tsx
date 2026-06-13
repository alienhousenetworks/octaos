'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Target, Plus, Loader2, Bot, Check, Play, Zap, Sparkles } from 'lucide-react';

interface CEOViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  timeline: any[];
  setActiveView: (view: string) => void;
}

export default function CEOView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  timeline,
  setActiveView,
}: CEOViewProps) {
  // CEO states relocated here
  const [ceoWorkflows, setCeoWorkflows] = useState<any[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any | null>(null);
  const [objectivePrompt, setObjectivePrompt] = useState('');
  const [ceoProvider, setCeoProvider] = useState('gemini');
  const [ceoModel, setCeoModel] = useState<string | null>(null);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [isExecutingPlan, setIsExecutingPlan] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (token) {
      fetchCeoWorkflows();
    }
  }, [token]);

  // Handle active workflow details auto-refresh when executing
  useEffect(() => {
    if (selectedWorkflowId && token) {
      fetchCeoWorkflowDetails(selectedWorkflowId);
      
      let interval: NodeJS.Timeout | null = null;
      if (selectedWorkflow?.status === 'executing') {
        interval = setInterval(() => {
          fetchCeoWorkflowDetails(selectedWorkflowId);
        }, 5000);
      }
      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [selectedWorkflowId, selectedWorkflow?.status, token]);

  // CEO functions
    const fetchCeoWorkflows = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows`);
      if (res.ok) {
        const data = await res.json();
        setCeoWorkflows(data);
      }
    } catch (e) {
      console.error(e);
    }
  };


    const fetchCeoWorkflowDetails = async (wfId: string) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/workflows/${wfId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedWorkflow(data);
      }
    } catch (e) {
      console.error(e);
    }
  };


    const handleGenerateCeoPlan = async () => {
    if (!token || !objectivePrompt.trim()) return;
    setIsGeneratingPlan(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: objectivePrompt, provider: ceoProvider, model: ceoModel })
      });
      if (res.ok) {
        const data = await res.json();
        setCeoWorkflows(prev => [data, ...prev]);
        setSelectedWorkflowId(data.id);
        setSelectedWorkflow(data);
        setObjectivePrompt('');
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Failed to generate plan'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsGeneratingPlan(false);
    }
  };


    const handleExecuteCeoPlan = async (wfId: string) => {
    if (!token) return;
    setIsExecutingPlan(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/ceo/run/${wfId}`, {
        method: 'POST'
      });
      if (res.ok) {
        await fetchCeoWorkflowDetails(wfId);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsExecutingPlan(false);
    }
  };



  // IIFE Logic
              // Helper component to draw curved dependency connectors
            const GraphConnector = ({ fromId, toId, containerRef }: { fromId: string, toId: string, containerRef: { current: HTMLDivElement | null } }) => {
              const [coords, setCoords] = useState<{ x1: number, y1: number, x2: number, y2: number } | null>(null);

              useEffect(() => {
                const updateCoords = () => {
                  if (!containerRef.current) return;
                  const containerRect = containerRef.current.getBoundingClientRect();
                  const fromEl = document.getElementById(`card-${fromId}`);
                  const toEl = document.getElementById(`card-${toId}`);
                  if (fromEl && toEl) {
                    const fromRect = fromEl.getBoundingClientRect();
                    const toRect = toEl.getBoundingClientRect();

                    setCoords({
                      x1: fromRect.right - containerRect.left,
                      y1: fromRect.top + fromRect.height / 2 - containerRect.top,
                      x2: toRect.left - containerRect.left,
                      y2: toRect.top + toRect.height / 2 - containerRect.top
                    });
                  }
                };

                updateCoords();
                window.addEventListener('resize', updateCoords);
                const t = setTimeout(updateCoords, 300);
                return () => {
                  window.removeEventListener('resize', updateCoords);
                  clearTimeout(t);
                };
              }, [fromId, toId, containerRef]);

              if (!coords) return null;

              const dx = Math.abs(coords.x2 - coords.x1) * 0.5;
              const path = `M ${coords.x1} ${coords.y1} C ${coords.x1 + dx} ${coords.y1}, ${coords.x2 - dx} ${coords.y2}, ${coords.x2} ${coords.y2}`;

              return (
                <svg className="absolute inset-0 pointer-events-none w-full h-full z-0 overflow-visible">
                  <defs>
                    <linearGradient id={`grad-${fromId}-${toId}`} x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#0ea5e9" stopOpacity="0.4" />
                    </linearGradient>
                    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                      <path d="M 0 1 L 10 5 L 0 9 z" fill="#0ea5e9" fillOpacity="0.6" />
                    </marker>
                  </defs>
                  <path
                    d={path}
                    fill="none"
                    stroke={`url(#grad-${fromId}-${toId})`}
                    strokeWidth="2"
                    markerEnd="url(#arrow)"
                    className="animate-dash"
                    strokeDasharray="5, 5"
                  />
                </svg>
              );
            };

            // Compute task dependency levels/columns
            const tasks = selectedWorkflow?.tasks || [];
            const levels: Record<string, number> = {};
            const parents: Record<string, string[]> = {};
            tasks.forEach((t: any) => {
              parents[t.id] = t.payload?.depends_on || [];
            });

            const getLevel = (id: string, visited: Record<string, boolean> = {}): number => {
              if (id in levels) return levels[id];
              if (visited[id]) return 0;
              visited[id] = true;
              
              const pars = parents[id] || [];
              if (pars.length === 0) {
                levels[id] = 0;
              } else {
                levels[id] = Math.max(...pars.map(pId => getLevel(pId, visited))) + 1;
              }
              delete visited[id];
              return levels[id];
            };

            tasks.forEach((t: any) => getLevel(t.id));

            // Group tasks by level
            const columns: Record<number, any[]> = {};
            tasks.forEach((t: any) => {
              const lvl = levels[t.id] || 0;
              if (!columns[lvl]) columns[lvl] = [];
              columns[lvl].push(t);
            });

            const colKeys = Object.keys(columns).map(Number).sort((a, b) => a - b);
            const activeTask = tasks.find((t: any) => t.id === selectedTaskId);



  return (
                  <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
                <style dangerouslySetInnerHTML={{ __html: `
                  @keyframes borderPulse {
                    0%, 100% { border-color: rgba(139, 92, 246, 0.2); box-shadow: 0 0 4px rgba(139, 92, 246, 0.1); }
                    50% { border-color: rgba(14, 165, 233, 0.8); box-shadow: 0 0 12px rgba(14, 165, 233, 0.4); }
                  }
                  .animate-neon-pulse {
                    animation: borderPulse 1.8s infinite ease-in-out;
                  }
                  @keyframes lineDash {
                    to { stroke-dashoffset: -20; }
                  }
                  .animate-dash {
                    animation: lineDash 1s infinite linear;
                  }
                `}} />

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
                      <Target className="text-sky-400 h-8 w-8 animate-pulse" /> CEO Workspace
                    </h1>
                    <p className="text-gray-400 mt-1">Autonomous DAG planning, department delegation, task execution and aggregated business reports.</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                  {/* Left Column: Form & History List */}
                  <div className="lg:col-span-4 space-y-6">
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative">
                      <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-sky-500 to-transparent" />
                      <CardHeader>
                        <CardTitle className="text-lg text-white font-bold tracking-tight">Formulate Strategy</CardTitle>
                        <CardDescription className="text-gray-400 text-xs">Enter your business growth objective for the CEO AI to design an execution plan.</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-gray-400">Objective</label>
                          <Textarea
                            placeholder="e.g. Sourcing real leads for my SaaS AI company in New York, pitch them via SMTP, and find 2 SDR recruiters."
                            value={objectivePrompt}
                            onChange={(e) => setObjectivePrompt(e.target.value)}
                            className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-24 focus:border-sky-500 focus:ring-sky-500/20"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-semibold text-gray-400">AI Brain</label>
                            <Select value={ceoProvider} onValueChange={(val) => val && setCeoProvider(val)}>
                              <SelectTrigger className="bg-gray-900 border-gray-800 text-xs text-white">
                                <SelectValue placeholder="Provider" />
                              </SelectTrigger>
                              <SelectContent className="bg-gray-900 border-gray-800 text-white">
                                <SelectItem value="gemini">Google Gemini</SelectItem>
                                <SelectItem value="anthropic">Claude (Anthropic)</SelectItem>
                                <SelectItem value="openai">OpenAI</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="flex flex-col justify-end">
                            <Button
                              onClick={handleGenerateCeoPlan}
                              disabled={isGeneratingPlan || !objectivePrompt.trim()}
                              className="bg-gradient-to-r from-sky-600 to-violet-600 hover:from-sky-500 hover:to-violet-500 text-white font-bold h-10 rounded-xl shadow-lg text-xs"
                            >
                              {isGeneratingPlan ? (
                                <>
                                  <Loader2 className="animate-spin mr-1.5" size={14} />
                                  Designing...
                                </>
                              ) : 'Formulate Strategy'}
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative">
                      <CardHeader>
                        <CardTitle className="text-lg text-white font-bold tracking-tight">Active Pipelines</CardTitle>
                        <CardDescription className="text-gray-400 text-xs">History of formulated growth plans.</CardDescription>
                      </CardHeader>
                      <CardContent className="px-2 pb-6">
                        {ceoWorkflows.length === 0 ? (
                          <p className="text-xs text-gray-500 text-center py-10">No growth strategy plans found. Generate one above to start.</p>
                        ) : (
                          <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
                            {ceoWorkflows.map((w) => {
                              const isSelected = selectedWorkflowId === w.id;
                              const isCompleted = w.status === 'completed';
                              return (
                                <div
                                  key={w.id}
                                  onClick={() => {
                                    setSelectedWorkflowId(w.id);
                                    setSelectedTaskId(null);
                                    fetchCeoWorkflowDetails(w.id);
                                  }}
                                  className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex flex-col gap-2 ${
                                    isSelected
                                      ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.12)] shadow-xl'
                                      : 'bg-transparent border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]'
                                  }`}
                                >
                                  <div className="flex items-center justify-between">
                                    <span className={`flex items-center gap-1 text-[10px] font-bold ${
                                      isCompleted ? 'text-emerald-400' : w.status === 'executing' ? 'text-sky-400' : 'text-amber-400'
                                    }`}>
                                      <span className={`h-1.5 w-1.5 rounded-full ${
                                        isCompleted ? 'bg-emerald-400' : w.status === 'executing' ? 'bg-sky-400 animate-ping' : 'bg-amber-400'
                                      }`} />
                                      {w.status}
                                    </span>
                                    <span className="text-[9px] text-gray-500">
                                      {new Date(w.created_at).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <h4 className="font-bold text-white text-xs leading-snug line-clamp-2">{w.name}</h4>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </div>

                  {/* Right Column: Workflow DAG visualizer & Drawer details */}
                  <div className="lg:col-span-8 space-y-6">
                    {!selectedWorkflow ? (
                      <Card className="glass-panel border-transparent rounded-3xl h-[520px] flex flex-col items-center justify-center text-center p-8">
                        <Target className="text-gray-600 h-16 w-16 mb-4 animate-bounce" />
                        <h3 className="text-lg font-bold text-white mb-2">No Strategy Selected</h3>
                        <p className="text-xs text-gray-400 max-w-sm">Please input a growth objective on the left panel and click 'Formulate Strategy' to generate an active execution pipeline, or select an existing one.</p>
                      </Card>
                    ) : (
                      <div className="space-y-6">
                        {/* Executive Header */}
                        <Card className="glass-panel border-transparent rounded-3xl p-6 relative overflow-hidden">
                          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-sky-500 to-transparent" />
                          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                            <div className="flex-1 min-w-0">
                              <span className="text-[10px] uppercase font-bold tracking-widest text-sky-400">Target Objective</span>
                              <h2 className="text-xl font-extrabold text-white truncate mt-0.5">{selectedWorkflow.name}</h2>
                              {timeline.length > 0 && (
                                <p className="text-[11px] text-gray-400 mt-1 line-clamp-1 italic">
                                  Latest Action: {timeline[0].description}
                                </p>
                              )}
                            </div>
                            <Button
                              onClick={() => handleExecuteCeoPlan(selectedWorkflow.id)}
                              disabled={isExecutingPlan || selectedWorkflow.status === 'executing' || selectedWorkflow.status === 'completed'}
                              className={`font-bold h-11 px-6 rounded-xl shadow-lg transition-all text-xs shrink-0 ${
                                selectedWorkflow.status === 'completed'
                                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 cursor-default'
                                  : selectedWorkflow.status === 'executing'
                                  ? 'bg-sky-600/20 text-sky-400 border border-sky-500/30'
                                  : 'bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white shadow-sky-500/20'
                              }`}
                            >
                              {selectedWorkflow.status === 'completed' ? (
                                'Strategy Fully Executed'
                              ) : selectedWorkflow.status === 'executing' ? (
                                <span className="flex items-center gap-1.5">
                                  <Loader2 className="animate-spin" size={14} />
                                  Executing...
                                </span>
                              ) : 'Execute Growth Plan'}
                            </Button>
                          </div>
                        </Card>

                        {/* DAG Flow Visualizer */}
                        <Card className="glass-panel border-transparent rounded-3xl p-6 relative">
                          <span className="text-[10px] uppercase font-bold tracking-widest text-sky-400 block mb-6">Orchestration Graph (DAG)</span>
                          
                          <div
                            ref={containerRef}
                            className="relative bg-gray-950/40 border border-gray-900/60 rounded-2xl min-h-[380px] p-6 overflow-x-auto flex justify-between gap-12 items-center z-10"
                          >
                            {/* SVG Connectors */}
                            {tasks.map((task: any) => {
                              const deps = task.payload?.depends_on || [];
                              return deps.map((parentId: string) => (
                                <GraphConnector
                                  key={`${parentId}-${task.id}`}
                                  fromId={parentId}
                                  toId={task.id}
                                  containerRef={containerRef}
                                />
                              ));
                            })}

                            {/* Column nodes */}
                            {colKeys.map((lvl) => (
                              <div key={lvl} className="flex flex-col gap-6 items-center z-10 min-w-[150px]">
                                <span className="text-[9px] uppercase font-bold text-gray-500 tracking-wider">Level {lvl}</span>
                                {columns[lvl].map((task: any) => {
                                  const isSelected = selectedTaskId === task.id;
                                  const isCompleted = task.status === 'completed';
                                  const isExecuting = task.status === 'in_progress';
                                  const isFailed = task.status === 'failed';
                                  
                                  // Assign color configurations based on department
                                  const dept = task.payload?.department || 'CEO';
                                  let colorClass = 'border-gray-800 bg-gray-900/50 text-gray-400';
                                  if (isCompleted) {
                                    colorClass = 'border-emerald-500/40 bg-emerald-950/10 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.1)]';
                                  } else if (isFailed) {
                                    colorClass = 'border-rose-500/40 bg-rose-950/10 text-rose-400 shadow-[0_0_10px_rgba(244,63,94,0.1)]';
                                  } else if (isExecuting) {
                                    colorClass = 'animate-neon-pulse text-sky-400';
                                  } else if (isSelected) {
                                    colorClass = 'border-sky-500 bg-sky-950/20 text-white';
                                  }

                                  let badgeColor = 'bg-gray-800 text-gray-400';
                                  if (dept === 'Marketing') badgeColor = 'bg-violet-950/40 text-violet-400 border border-violet-900/35';
                                  else if (dept === 'Sales') badgeColor = 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/35';
                                  else if (dept === 'Finance') badgeColor = 'bg-amber-950/40 text-amber-400 border border-amber-900/35';
                                  else if (dept === 'HR') badgeColor = 'bg-orange-950/40 text-orange-400 border border-orange-900/35';
                                  else if (dept === 'CEO') badgeColor = 'bg-sky-950/40 text-sky-400 border border-sky-900/35';

                                  return (
                                    <div
                                      key={task.id}
                                      id={`card-${task.id}`}
                                      onClick={() => setSelectedTaskId(task.id)}
                                      className={`w-44 p-3.5 rounded-2xl border flex flex-col gap-2 cursor-pointer transition-all hover:scale-[1.03] select-none text-left relative z-20 ${colorClass}`}
                                    >
                                      <div className="flex items-center justify-between">
                                        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded ${badgeColor}`}>{dept}</span>
                                        {isCompleted && <span className="text-emerald-400 text-[10px] font-bold">✓</span>}
                                        {isExecuting && <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-ping" />}
                                        {isFailed && <span className="text-rose-500 text-[10px] font-bold">✗</span>}
                                      </div>
                                      <h5 className="font-bold text-xs text-white line-clamp-2 leading-tight">{task.name}</h5>
                                    </div>
                                  );
                                })}
                              </div>
                            ))}
                          </div>
                        </Card>

                        {/* Detailed Card Report drawer */}
                        {activeTask && (
                          <Card className="glass-panel border-transparent rounded-3xl p-6 relative overflow-hidden transition-all duration-300">
                            <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
                            <div className="flex justify-between items-start">
                              <div>
                                <span className="text-[10px] uppercase font-bold tracking-widest text-violet-400">{activeTask.payload?.department} Agent</span>
                                <h3 className="text-lg font-bold text-white mt-0.5">{activeTask.name}</h3>
                                <p className="text-gray-400 text-xs mt-1">{activeTask.payload?.description}</p>
                              </div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                activeTask.status === 'completed'
                                  ? 'bg-emerald-950/30 border-emerald-900 text-emerald-400'
                                  : activeTask.status === 'in_progress'
                                  ? 'bg-sky-950/30 border-sky-900 text-sky-400'
                                  : 'bg-gray-900/60 border-gray-800 text-gray-500'
                              }`}>
                                {activeTask.status}
                              </span>
                            </div>

                            {/* Agent Results Details */}
                            <div className="mt-6 border-t border-gray-800/80 pt-6 space-y-4">
                              {activeTask.status !== 'completed' ? (
                                <p className="text-xs text-gray-500 italic">This task is currently {activeTask.status}. The report will generate automatically when the preceding workflow tasks finish executing.</p>
                              ) : (
                                <div className="space-y-4 text-xs">
                                  <div className="bg-gray-950/60 border border-gray-900 p-4 rounded-xl text-gray-300 leading-relaxed font-sans overflow-x-auto whitespace-pre-line">
                                    {activeTask.result?.report}
                                  </div>

                                  {/* Render custom output summaries depending on task type */}
                                  {activeTask.task_type === 'sales_leads' && activeTask.result?.leads && (
                                    <div className="space-y-2.5">
                                      <h5 className="font-bold text-white flex items-center gap-1">👥 Sourced Leads ({activeTask.result.leads.length})</h5>
                                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {activeTask.result.leads.map((l: any) => (
                                          <div key={l.id} className="p-3 bg-emerald-950/10 border border-emerald-900/20 rounded-xl flex items-center justify-between">
                                            <div>
                                              <p className="font-bold text-white">{l.name}</p>
                                              <p className="text-[10px] text-gray-400">{l.company} — {l.email}</p>
                                            </div>
                                            <button 
                                              onClick={() => setActiveView('sales')} 
                                              className="text-[9px] font-bold text-emerald-400 hover:underline cursor-pointer"
                                            >
                                              View CRM →
                                            </button>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {activeTask.task_type === 'hr_source' && activeTask.result?.candidates && (
                                    <div className="space-y-2.5">
                                      <h5 className="font-bold text-white flex items-center gap-1">💼 Sourced Candidates ({activeTask.result.candidates.length})</h5>
                                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {activeTask.result.candidates.map((c: any) => (
                                          <div key={c.id} className="p-3 bg-orange-950/10 border border-orange-900/20 rounded-xl flex items-center justify-between">
                                            <div>
                                              <p className="font-bold text-white">{c.name}</p>
                                              <p className="text-[10px] text-gray-400">{c.email} — Match: {c.score}%</p>
                                            </div>
                                            <button 
                                              onClick={() => setActiveView('hr')} 
                                              className="text-[9px] font-bold text-orange-400 hover:underline cursor-pointer"
                                            >
                                              View HR →
                                            </button>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {activeTask.task_type === 'finance_budget' && activeTask.result?.allocated_budget && (
                                    <div className="p-3.5 bg-amber-950/10 border border-amber-900/20 rounded-xl flex items-center gap-3">
                                      <span className="text-xl">💰</span>
                                      <div>
                                        <p className="font-bold text-white">Capital Allocated: ${activeTask.result.allocated_budget.toLocaleString()}</p>
                                        <p className="text-[10px] text-gray-400">Budget lines updated in central finance registry. ROI projections calculated.</p>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </Card>
                        )}

                        {/* Special summary task representation at bottom */}
                        {selectedWorkflow.status === 'completed' && (() => {
                          const summaryTask = tasks.find((t: any) => t.task_type === 'ceo_summary');
                          if (!summaryTask || !summaryTask.result?.report) return null;
                          return (
                            <Card className="glass-panel border border-sky-500/20 shadow-sky-500/5 rounded-3xl p-6 relative overflow-hidden bg-sky-950/5 animate-in slide-in-from-bottom duration-500">
                              <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-sky-500 to-transparent" />
                              <div className="flex items-center gap-2 mb-4">
                                <Sparkles className="text-sky-400 h-5 w-5 animate-pulse" />
                                <h3 className="text-lg font-bold text-white">CEO AI Executive Growth Report</h3>
                              </div>
                              <div className="bg-gray-950/40 p-5 rounded-2xl border border-gray-900 text-gray-300 leading-relaxed font-sans text-xs whitespace-pre-line">
                                {summaryTask.result.report}
                              </div>
                            </Card>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                </div>
              </div>

  );
}

'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DollarSign, Users, Activity, Briefcase, Calendar, BarChart3, Clock } from 'lucide-react';
import { marketplacePacks } from './marketplace-packs';

interface DashboardViewProps {
  metrics: any;
  timeline: any[];
  queue: { posts: any[]; leads: any[] };
  apps: any[];
  setActiveView: (view: string) => void;
  uninstallApp: (appName: string) => Promise<void>;
  handleApprovePost: (postId: string) => Promise<void>;
  handleRejectPost: (postId: string) => Promise<void>;
}

export default function DashboardView({
  metrics,
  timeline,
  queue,
  apps,
  setActiveView,
  uninstallApp,
  handleApprovePost,
  handleRejectPost,
}: DashboardViewProps) {
  const dailyTasksRaw = metrics.daily_tasks || {
    marketing: [2, 4, 1, 5, 6, 3, 5],
    sales: [1, 2, 2, 4, 5, 3, 6],
    support: [2, 2, 1, 3, 4, 3, 3],
  };

  const hasBreakdown = dailyTasksRaw && !Array.isArray(dailyTasksRaw);
  const marketingData = hasBreakdown ? (dailyTasksRaw.marketing || []) : (Array.isArray(dailyTasksRaw) ? dailyTasksRaw : [2, 4, 1, 5, 6, 3, 5]);
  const salesData = hasBreakdown ? (dailyTasksRaw.sales || []) : [];
  const supportData = hasBreakdown ? (dailyTasksRaw.support || []) : [];

  const allVals = [...marketingData, ...salesData, ...supportData];
  const maxVal = allVals.length > 0 ? Math.max(...allVals, 10) : 10;

  const getPoints = (data: number[]) => {
    return data.map((val: number, i: number) => {
      const x = (i * 500) / 6;
      const y = 130 - (val / maxVal) * 100;
      return { x, y, val };
    });
  };

  const marketingPoints = getPoints(marketingData);
  const salesPoints = getPoints(salesData);
  const supportPoints = getPoints(supportData);

  const getPaths = (pts: any[]) => {
    if (pts.length === 0) return { strokePath: '', areaPath: '' };
    const stroke = pts.map((p: any, i: number) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const area = `${stroke} L500,150 L0,150 Z`;
    return { strokePath: stroke, areaPath: area };
  };

  const marketingPaths = getPaths(marketingPoints);
  const salesPaths = getPaths(salesPoints);
  const supportPaths = getPaths(supportPoints);

  const getDayNames = () => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const result = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(today.getDate() - i);
      if (i === 0) {
        result.push('Today');
      } else {
        result.push(days[d.getDay()]);
      }
    }
    return result;
  };
  const dayNames = getDayNames();

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight">AI Operating Dashboard</h1>
                  <p className="text-gray-400 mt-1">Live metrics from your autonomous AI workforce.</p>
                </div>
                <div className="flex items-center gap-2 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.06)] px-4 py-2 rounded-xl text-xs text-gray-400 font-semibold shadow-inner">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>All virtual employees sync'd</span>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
                {[
                  { title: "Revenue Impact", val: `$${(metrics.revenue_impact || 0).toLocaleString()}`, desc: "Direct sales attributed", icon: <DollarSign className="h-4 w-4 text-emerald-400" />, glow: "glow-sales" },
                  { title: "Leads Sourced", val: metrics.leads_generated || 0, desc: "B2B sales prospects found", icon: <Users className="h-4 w-4 text-emerald-400" />, glow: "glow-sales" },
                  { title: "Content Published", val: metrics.posts_published || 0, desc: "Social media posts live", icon: <Activity className="h-4 w-4 text-violet-400" />, glow: "glow-marketing" },
                  { title: "Candidates Sourced", val: metrics.candidates_sourced || 0, desc: "HR applicants indexed", icon: <Briefcase className="h-4 w-4 text-amber-400" />, glow: "glow-hr" },
                  { title: "Interviews Booked", val: metrics.interviews_scheduled || 0, desc: "Google Meet calls scheduled", icon: <Calendar className="h-4 w-4 text-amber-400" />, glow: "glow-hr" },
                  { title: "Success Rate", val: `${metrics.automation_success_rate || 99.5}%`, desc: "Autopilot efficiency rate", icon: <BarChart3 className="h-4 w-4 text-pink-400" />, glow: "glow-support" },
                ].map((m, idx) => (
                  <Card key={idx} className={`glass-panel border-transparent ${m.glow} relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl`}>
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-current opacity-80" />
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{m.title}</CardTitle>
                      {m.icon}
                    </CardHeader>
                    <CardContent className="space-y-1">
                      <div className="text-3xl font-black text-white">{m.val}</div>
                      <p className="text-[10px] text-gray-500 font-medium">{m.desc}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
 
              {/* Advanced SVG Chart & Activity Center */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Visual Chart Card */}
                <Card className="lg:col-span-8 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4 border-b border-gray-800 pb-4">
                    <div>
                      <h3 className="font-extrabold text-lg text-white">Daily Automated Tasks</h3>
                      <p className="text-xs text-gray-400">Total automated agent tasks over the last 7 days</p>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                      <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-violet-500" /> Marketing</span>
                      <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Sales</span>
                      <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> Support</span>
                    </div>
                  </div>
 
                  <div className="relative w-full h-44 mt-2 flex items-end">
                    <svg viewBox="0 0 500 150" className="w-full h-full overflow-visible" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="chartGradientMarketing" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.25" />
                          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.0" />
                        </linearGradient>
                        <linearGradient id="chartGradientSales" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                          <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                        </linearGradient>
                        <linearGradient id="chartGradientSupport" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.25" />
                          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      {/* Grid Lines */}
                      <line x1="0" y1="30" x2="500" y2="30" stroke="rgba(255,255,255,0.03)" strokeDasharray="4 4" />
                      <line x1="0" y1="75" x2="500" y2="75" stroke="rgba(255,255,255,0.03)" strokeDasharray="4 4" />
                      <line x1="0" y1="120" x2="500" y2="120" stroke="rgba(255,255,255,0.03)" strokeDasharray="4 4" />
                      
                      {/* Marketing Area & Stroke */}
                      {marketingPaths.areaPath && (
                        <>
                          <path d={marketingPaths.areaPath} fill="url(#chartGradientMarketing)" />
                          <path d={marketingPaths.strokePath} fill="none" stroke="#8b5cf6" strokeWidth="2.5" />
                        </>
                      )}

                      {/* Sales Area & Stroke */}
                      {salesPaths.areaPath && (
                        <>
                          <path d={salesPaths.areaPath} fill="url(#chartGradientSales)" />
                          <path d={salesPaths.strokePath} fill="none" stroke="#10b981" strokeWidth="2.5" />
                        </>
                      )}

                      {/* Support Area & Stroke */}
                      {supportPaths.areaPath && (
                        <>
                          <path d={supportPaths.areaPath} fill="url(#chartGradientSupport)" />
                          <path d={supportPaths.strokePath} fill="none" stroke="#3b82f6" strokeWidth="2.5" />
                        </>
                      )}
                      
                      {/* Marketing Data Dots & Text */}
                      {marketingPoints.map((p, i) => (
                        <g key={`m-${i}`}>
                          <circle cx={p.x} cy={p.y} r="3.5" fill="#8b5cf6" stroke="#ffffff" strokeWidth="1" />
                          <text x={p.x} y={p.y - 8} textAnchor="middle" fill="#a78bfa" className="text-[9px] font-bold font-mono">
                            {p.val}
                          </text>
                        </g>
                      ))}

                      {/* Sales Data Dots & Text */}
                      {salesPoints.map((p, i) => (
                        <g key={`s-${i}`}>
                          <circle cx={p.x} cy={p.y} r="3.5" fill="#10b981" stroke="#ffffff" strokeWidth="1" />
                          <text x={p.x} y={p.y + 12} textAnchor="middle" fill="#34d399" className="text-[9px] font-bold font-mono">
                            {p.val}
                          </text>
                        </g>
                      ))}

                      {/* Support Data Dots & Text */}
                      {supportPoints.map((p, i) => (
                        <g key={`sup-${i}`}>
                          <circle cx={p.x} cy={p.y} r="3.5" fill="#3b82f6" stroke="#ffffff" strokeWidth="1" />
                          <text x={p.x} y={p.y - 14} textAnchor="middle" fill="#60a5fa" className="text-[9px] font-bold font-mono">
                            {p.val}
                          </text>
                        </g>
                      ))}
                    </svg>
                  </div>
                  
                  <div className="flex justify-between text-[10px] text-gray-500 font-bold tracking-wider uppercase mt-4 pt-3 border-t border-gray-800/60">
                    {dayNames.map((name, i) => (
                      <span key={i}>{name}</span>
                    ))}
                  </div>
                </Card>

                {/* Developer Terminal Activity Log */}
                <Card className="lg:col-span-4 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col h-full min-h-[280px]">
                  <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                    </div>
                    <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider font-mono">Live Developer Console</span>
                  </div>
                  <div className="flex-1 overflow-y-auto space-y-2.5 font-mono text-[11px] leading-relaxed text-gray-300 pr-1 max-h-[180px]">
                    {timeline.slice(0, 8).map((log) => (
                      <div key={log.id} className="text-gray-400">
                        <span className="text-violet-400 font-semibold">[{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>{" "}
                        <span className="text-emerald-400">({log.agent_name})</span>{" "}
                        <span className="text-white font-medium">{log.action}:</span> {log.description}
                      </div>
                    ))}
                    {timeline.length === 0 && (
                      <div className="text-gray-500 italic">Listening for system triggers...</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-gray-800 text-[10px] text-violet-400 font-bold font-mono">
                    <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-ping" />
                    <span>SYSTEM ONLINE. LOGS BINDING OK.</span>
                    <span className="inline-block w-1.5 h-3 bg-violet-400 animate-pulse" />
                  </div>
                </Card>
              </div>

              {/* Approvals Pipeline Widget */}
              <Card className="glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden">
                <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-6">
                  <div>
                    <h3 className="font-extrabold text-xl text-white">Pending Approvals</h3>
                    <p className="text-xs text-gray-400">Verify content and leads generated by your AI workforce before publishing.</p>
                  </div>
                  <div className="flex items-center gap-1.5 bg-amber-500/10 text-amber-400 text-[10px] font-bold px-3 py-1 rounded-full border border-amber-500/20 uppercase tracking-wider">
                    {((queue.posts?.length || 0) + (queue.leads?.length || 0))} Pending Approval
                  </div>
                </div>

                <Tabs defaultValue="marketing" className="w-full">
                  <TabsList className="grid w-full max-w-[400px] grid-cols-2 bg-gray-950/60 p-1 border border-gray-800 rounded-xl mb-6">
                    <TabsTrigger value="marketing" className="rounded-lg text-xs font-semibold text-gray-400 data-[state=active]:bg-violet-600 data-[state=active]:text-white transition-all">Marketing Queue ({queue.posts?.length || 0})</TabsTrigger>
                    <TabsTrigger value="sales" className="rounded-lg text-xs font-semibold text-gray-400 data-[state=active]:bg-emerald-600 data-[state=active]:text-white transition-all">Sales Leads ({queue.leads?.length || 0})</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="marketing">
                    <div className="border border-gray-800 rounded-2xl overflow-hidden bg-[rgba(0,0,0,0.15)] shadow-inner">
                      <Table>
                        <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                          <TableRow className="border-gray-800 hover:bg-transparent">
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Platform & Day</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Content Preview</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4 text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-gray-800">
                          {(!queue.posts || queue.posts.length === 0) && (
                            <TableRow className="hover:bg-transparent">
                              <TableCell colSpan={3} className="text-center py-12 text-sm text-gray-500 font-medium">
                                Perfect! No marketing posts pending approval.
                              </TableCell>
                            </TableRow>
                          )}
                          {queue.posts?.map((post) => (
                            <TableRow key={post.id} className="border-gray-800 hover:bg-gray-900/20">
                              <TableCell className="p-4 whitespace-nowrap">
                                <div className="flex flex-col">
                                  <span className="text-xs font-extrabold uppercase text-violet-400">{post.platform}</span>
                                  <span className="text-[10px] text-gray-500 font-bold mt-0.5">Day {post.day}</span>
                                </div>
                              </TableCell>
                              <TableCell className="p-4">
                                <p className="max-w-xl text-xs text-gray-300 line-clamp-2 leading-relaxed">{post.content}</p>
                              </TableCell>
                              <TableCell className="p-4 text-right">
                                <div className="flex gap-2 justify-end">
                                  <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => handleRejectPost(post.id)}
                                    className="h-8 text-xs font-semibold text-rose-400 border-rose-900/30 hover:bg-rose-950/20"
                                  >
                                    Reject
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    onClick={() => handleApprovePost(post.id)}
                                    className="h-8 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                                  >
                                    Approve
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="sales">
                    <div className="border border-gray-800 rounded-2xl overflow-hidden bg-[rgba(0,0,0,0.15)] shadow-inner">
                      <Table>
                        <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                          <TableRow className="border-gray-800 hover:bg-transparent">
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Lead Name</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Company</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Source Channel</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-gray-800">
                          {(!queue.leads || queue.leads.length === 0) && (
                            <TableRow className="hover:bg-transparent">
                              <TableCell colSpan={3} className="text-center py-12 text-sm text-gray-500 font-medium">
                                No sales leads to display. Run outbound sourcing in Orchestrator.
                              </TableCell>
                            </TableRow>
                          )}
                          {queue.leads?.map((lead) => (
                            <TableRow key={lead.id} className="border-gray-800 hover:bg-gray-900/20">
                              <TableCell className="p-4 font-bold text-white text-xs">{lead.name}</TableCell>
                              <TableCell className="p-4 text-xs text-gray-300">{lead.company}</TableCell>
                              <TableCell className="p-4">
                                <span className="text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded uppercase tracking-wider">
                                  {lead.source}
                                </span>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                </Tabs>
              </Card>

              {/* Installed Workflows & Integrations Panel */}
              <div className="space-y-6 pt-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="font-extrabold text-2xl text-white">Active Workflows & Automations</h3>
                    <p className="text-xs text-gray-400 mt-1">Manage deployed workflow packs operating autonomously.</p>
                  </div>
                  {apps.length > 0 && (
                    <span className="text-[10px] uppercase font-extrabold tracking-widest text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
                      {apps.length} Operational Packs
                    </span>
                  )}
                </div>
                
                {apps.length === 0 ? (
                  <Card className="glass-panel border-dashed border-gray-800 rounded-3xl p-8 text-center space-y-4 shadow-xl">
                    <div className="text-5xl">🔌</div>
                    <div className="max-w-md mx-auto space-y-2">
                      <h4 className="text-sm font-bold text-white">No active industry workflows installed</h4>
                      <p className="text-xs text-gray-450 leading-relaxed">
                        OctaOS can deploy specialized, pre-configured packages for local growth, SaaS outbound sales, e-commerce automation, medical scheduling, and more. Visit the App Marketplace to activate.
                      </p>
                    </div>
                    <Button 
                      onClick={() => setActiveView('marketplace')}
                      className="bg-violet-600 hover:bg-violet-500 text-white font-bold h-9 px-6 rounded-xl shadow-lg shadow-violet-500/20 hover:scale-105 active:scale-95 transition-all text-xs"
                    >
                      Browse App Marketplace
                    </Button>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {apps.map((app) => {
                      const matchedPack = marketplacePacks.find(p => p.name === app.app_name);
                      return (
                        <Card key={app.id} className="glass-panel border-transparent hover:border-violet-500/30 transition-all duration-300 rounded-3xl p-6 shadow-2xl relative flex flex-col justify-between overflow-hidden">
                          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
                          <div className="space-y-4">
                            <div className="flex items-center justify-between">
                              <span className="text-[9px] uppercase font-black tracking-widest text-violet-400 bg-violet-500/10 px-2.5 py-1 rounded-full border border-violet-500/20">
                                {matchedPack?.category || "Integration"}
                              </span>
                              <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-bold uppercase tracking-wider bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 animate-pulse">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-450" />
                                <span>Autopilot</span>
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-3">
                              <div className="text-3xl p-2 bg-violet-500/10 rounded-2xl border border-violet-500/20 flex items-center justify-center h-12 w-12">
                                {matchedPack?.icon || "⚙️"}
                              </div>
                              <div>
                                <h4 className="text-base text-white font-extrabold">{app.app_name}</h4>
                                <span className="text-[10px] text-gray-500 font-bold">{matchedPack?.timeSaved ? `Saves ${matchedPack.timeSaved}` : "Active"}</span>
                              </div>
                            </div>

                            <p className="text-gray-300 text-xs leading-relaxed">{matchedPack?.desc || "Custom integration workflow."}</p>

                            {matchedPack?.features && (
                              <div className="space-y-2 pt-2 border-t border-gray-800/60">
                                <span className="text-[10px] font-bold uppercase text-gray-500 tracking-wider">Automations active:</span>
                                <ul className="space-y-1">
                                  {matchedPack.features.map((feat, idx) => (
                                    <li key={idx} className="text-[11px] text-gray-400 flex items-center gap-1.5 leading-tight">
                                      <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                                      <span>{feat}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>

                          <div className="pt-4 mt-4 border-t border-gray-800/60">
                            <Button 
                              onClick={() => uninstallApp(app.app_name)}
                              variant="outline"
                              className="w-full text-xs font-semibold text-rose-400 border-rose-900/30 hover:bg-rose-950/20 h-9 rounded-xl transition-all"
                            >
                              Deactivate Pack
                            </Button>
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
  );
}

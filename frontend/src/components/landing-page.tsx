'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Zap, Clock, DollarSign, Users, Calendar, Image as ImageIcon } from 'lucide-react';

interface LandingPageProps {
  setAppState: (state: 'landing' | 'login' | 'signup' | 'app') => void;
  logoUrl?: string | null;
}

export default function LandingPage({ setAppState, logoUrl }: LandingPageProps) {
  const [tasksPerDay, setTasksPerDay] = useState(60);
  const [hourlyRate, setHourlyRate] = useState(35);
  const [activePreviewAgent, setActivePreviewAgent] = useState('marketing');

  const hoursSaved = Math.round(tasksPerDay * 0.75 * 30);
  const moneySaved = Math.round(hoursSaved * hourlyRate);

  return (
    <div className="min-h-screen bg-[#030014] text-[#f4f4f7] relative overflow-hidden font-sans">
      {/* Ambient background glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[rgba(139,92,246,0.15)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[rgba(59,130,246,0.15)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-[40%] left-[25%] w-[400px] h-[400px] bg-[rgba(16,185,129,0.06)] rounded-full blur-[150px] pointer-events-none" />

      {/* Global Grid Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

      {/* Header */}
      <header className="sticky top-0 z-50 h-20 glass-panel border-b border-[rgba(167,139,250,0.1)] flex items-center justify-between px-8 md:px-16">
        <div className="flex items-center gap-3 text-2xl font-black tracking-tight text-white">
          {logoUrl ? (
            <img src={logoUrl} alt="OctaOS Logo" className="h-10 w-auto max-w-[180px] object-contain" />
          ) : (
            <>
              <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2 rounded-xl shadow-lg shadow-violet-500/20">
                <Zap className="text-white fill-white h-5 w-5 animate-pulse" />
              </div>
              <span>Octa<span className="text-violet-400">OS</span></span>
            </>
          )}
        </div>
        <div className="flex items-center gap-6">
          <button 
            onClick={() => setAppState('login')} 
            className="text-gray-300 hover:text-white font-medium transition-colors"
          >
            Log in
          </button>
          <button 
            onClick={() => setAppState('signup')} 
            className="bg-white hover:bg-gray-100 text-black font-bold px-5 py-2.5 rounded-xl transition-all hover:scale-105 active:scale-95 text-sm shadow-md"
          >
            Sign Up
          </button>
        </div>
      </header>

      {/* Hero Content */}
      <main className="max-w-7xl mx-auto px-8 md:px-16 pt-20 pb-32 relative z-10">
        <div className="text-center space-y-6 max-w-4xl mx-auto mb-20">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[rgba(139,92,246,0.1)] border border-[rgba(139,92,246,0.2)] text-violet-400 text-xs font-semibold uppercase tracking-wider animate-bounce">
            <Zap size={12} className="fill-violet-400" />
            <span>OctaOS Autopilot v1.2</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight leading-[1.1] animate-in fade-in slide-in-from-bottom-4 duration-500">
            Your Autonomous <br />
            <span className="bg-gradient-to-r from-violet-400 via-indigo-400 to-emerald-400 text-transparent bg-clip-text animate-text-shine">
              AI Agent Workforce.
            </span>
          </h1>

          <p className="text-lg md:text-xl text-gray-400 leading-relaxed max-w-2xl mx-auto">
            Hire specialized AI Agents for Marketing, Sales, Customer Support, and HR. Define high-level goals and let your virtual team execute them autonomously.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
            <button 
              onClick={() => setAppState('signup')} 
              className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-lg font-bold px-8 py-4 rounded-xl shadow-xl shadow-violet-500/30 hover:shadow-violet-500/40 transition-all hover:scale-105 active:scale-95"
            >
              Deploy Your AI Team
            </button>
            <button 
              onClick={() => {
                const el = document.getElementById('previews');
                el?.scrollIntoView({ behavior: 'smooth' });
              }} 
              className="bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.07)] text-white text-lg font-bold px-8 py-4 rounded-xl border border-gray-700/50 hover:border-gray-600 transition-all hover:scale-105 active:scale-95"
            >
              Watch Previews
            </button>
          </div>
        </div>

        {/* Interactive Agent Previews */}
        <div id="previews" className="mb-24 scroll-mt-24">
          <div className="text-center mb-10">
            <h2 className="text-3xl font-extrabold text-white">Meet Your Virtual Employees</h2>
            <p className="text-gray-400 mt-2">Click each department tab to preview live workspace outputs.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
            {/* Left Selector List - 5 cols */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              {[
                {
                  id: 'marketing',
                  name: 'Marketing Copywriter',
                  title: 'Jules - Senior Copywriter',
                  desc: 'Autonomously schedules 30-day visual campaigns across LinkedIn, Facebook, and Instagram.',
                  glow: 'glow-marketing',
                  bullet: 'Outputs high-converting copy, DALLE-3 graphics, and loop videos.',
                  color: 'text-violet-400'
                },
                {
                  id: 'sales',
                  name: 'B2B Sales SDR',
                  title: 'Alex - Outbound SDR',
                  desc: 'Scrapes local leads via Google Maps or B2B platforms, verifies emails, and handles outreach.',
                  glow: 'glow-sales',
                  bullet: 'Tracks lead statuses, sends automated email pitches via SMTP credentials.',
                  color: 'text-emerald-400'
                },
                {
                  id: 'support',
                  name: 'Support Agent',
                  title: 'Sam - Omnichannel Support',
                  desc: 'Answers user inquiries 24/7 via WhatsApp and Email using company brand context.',
                  glow: 'glow-support',
                  bullet: 'Features dynamic simulator for sandbox testing with realistic human delays.',
                  color: 'text-blue-400'
                },
                {
                  id: 'hr',
                  name: 'Hiring Recruiter',
                  title: 'Hunter - Technical Recruiter',
                  desc: 'Sources candidates matching job requirements, drafts outreach letters, and schedules meetings.',
                  glow: 'glow-hr',
                  bullet: 'Integrates calendar sync to book direct Google Meet video calls.',
                  color: 'text-amber-400'
                }
              ].map(agent => (
                <div
                  key={agent.id}
                  onClick={() => setActivePreviewAgent(agent.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      setActivePreviewAgent(agent.id);
                    }
                  }}
                  className={`text-left p-6 rounded-2xl border transition-all duration-300 relative overflow-hidden cursor-pointer ${
                    activePreviewAgent === agent.id 
                      ? `glass-panel ${agent.glow} scale-[1.02] border-violet-500/40` 
                      : 'bg-[rgba(10,8,26,0.3)] hover:bg-[rgba(255,255,255,0.02)] border-gray-800/80'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-lg text-white">{agent.name}</h3>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full bg-[rgba(255,255,255,0.04)] border border-gray-700 ${agent.color}`}>
                      Active
                    </span>
                  </div>
                  <p className="text-sm text-gray-400 mt-2">{agent.desc}</p>
                  {activePreviewAgent === agent.id && (
                    <div className="mt-4 pt-3 border-t border-gray-800 text-xs text-gray-300 flex items-center gap-1.5">
                      <Zap size={12} className="text-violet-400 fill-violet-400" />
                      {agent.bullet}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Right Output Mock - 7 cols */}
            <div className="lg:col-span-7 flex flex-col justify-center">
              <div className="glass-panel border-violet-500/20 rounded-3xl p-6 min-h-[440px] flex flex-col relative overflow-hidden shadow-2xl">
                {/* Subtle purple gradient orb inside mock container */}
                <div className="absolute top-[-50px] right-[-50px] w-48 h-48 bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />

                {/* Window Chrome */}
                <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-4">
                  <div className="flex gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-rose-500/80" />
                    <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                    <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-xs font-semibold text-gray-500 tracking-wide uppercase">Workspace Output Preview</span>
                  <span className="w-3 h-3 opacity-0" />
                </div>

                {/* Output content depending on active tab */}
                {activePreviewAgent === 'marketing' && (
                  <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                    <div>
                      <div className="flex items-center gap-3 mb-3">
                        <div className="bg-violet-600/20 text-violet-400 p-2 rounded-lg text-xs font-bold">LINKEDIN</div>
                        <span className="text-xs text-gray-400 font-medium">Day 4 of 30</span>
                        <span className="ml-auto text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded font-bold uppercase">Pending Approval</span>
                      </div>
                      <div className="bg-[rgba(255,255,255,0.02)] p-4 rounded-xl border border-gray-800 text-sm text-gray-300 whitespace-pre-line leading-relaxed">
                        {"☕️ Work hard, coffee harder! \n\nWe're thrilled to introduce our new Organic Cold Brew at BlueBottle Cafe. Cold-steeped for 18 hours for maximum smoothness and low acidity. Pop in today and grab your jar! \n\n#cafevibes #organicroast #coldbrew"}
                      </div>
                    </div>
                    
                    <div className="relative rounded-xl overflow-hidden border border-gray-800 aspect-[16/9] flex items-center justify-center bg-gradient-to-br from-indigo-950/50 to-violet-950/50 shadow-inner">
                      <div className="text-center p-4">
                        <ImageIcon size={36} className="text-violet-400 mx-auto mb-2 animate-bounce" />
                        <span className="text-xs text-gray-400 font-bold block uppercase tracking-wider">AI Graphic Generated</span>
                        <span className="text-[10px] text-gray-500 italic block mt-0.5">Prompt: \"Vibrant graphic showcasing cold brew coffee on wooden table, cafe vibes, modern illustration\"</span>
                      </div>
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                      <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs px-4 py-2 rounded-lg font-semibold cursor-not-allowed">Reject</span>
                      <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs px-4 py-2 rounded-lg font-semibold cursor-not-allowed">Approve & Publish</span>
                    </div>
                  </div>
                )}

                {activePreviewAgent === 'sales' && (
                  <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                    <div>
                      <div className="flex items-center gap-3 mb-4">
                        <div className="bg-emerald-600/20 text-emerald-400 p-2 rounded-lg text-xs font-bold">APOLLO.IO</div>
                        <span className="text-xs text-gray-400 font-medium">B2B Sourcing Active</span>
                        <span className="ml-auto text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold uppercase">4 Leads Found</span>
                      </div>

                      <div className="border border-gray-800 rounded-xl overflow-hidden bg-[rgba(0,0,0,0.2)]">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-gray-900/60 border-b border-gray-800 text-gray-400 font-bold uppercase tracking-wider">
                            <tr>
                              <th className="p-3">Lead Name</th>
                              <th className="p-3">Company</th>
                              <th className="p-3">Email Address</th>
                              <th className="p-3">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-800 text-gray-300">
                            {[
                              { name: "Sarah Connor", comp: "Cyberdyne Systems", mail: "s.connor@cyberdyne.io", stat: "Sequence Sent" },
                              { name: "Bruce Wayne", comp: "Wayne Enterprises", mail: "bruce@waynecorp.com", stat: "Replied / Booked" },
                              { name: "Tony Stark", comp: "Stark Industries", mail: "tony@stark.com", stat: "Sequence Active" }
                            ].map(l => (
                              <tr key={l.name} className="hover:bg-gray-800/40">
                                <td className="p-3 font-semibold text-white">{l.name}</td>
                                <td className="p-3">{l.comp}</td>
                                <td className="p-3 text-violet-400 font-mono">{l.mail}</td>
                                <td className="p-3">
                                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                                    l.stat === 'Replied / Booked' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'
                                  }`}>
                                    {l.stat}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800/80">
                      <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-emerald-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                        SMTP Live Log:
                      </div>
                      <p className="text-[11px] text-gray-400 leading-relaxed font-mono">
                        [2026-05-21 11:30] Sent email Pitch_Template_V1 to s.connor@cyberdyne.io. Subject: "Automating support workflows for Cyberdyne..."
                      </p>
                    </div>
                  </div>
                )}

                {activePreviewAgent === 'support' && (
                  <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                    <div>
                      <div className="flex items-center gap-3 mb-4">
                        <div className="bg-blue-600/20 text-blue-400 p-2 rounded-lg text-xs font-bold">WHATSAPP</div>
                        <span className="text-xs text-gray-400 font-medium">Customer Support Sandbox</span>
                        <span className="ml-auto text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold uppercase">Solved By AI</span>
                      </div>

                      {/* WhatsApp Bubble Layout */}
                      <div className="space-y-3 p-3 bg-gray-950/60 rounded-2xl border border-gray-800 shadow-inner">
                        {/* Client Message */}
                        <div className="flex justify-start">
                          <div className="bg-gray-800 text-gray-100 rounded-2xl rounded-tl-none px-3.5 py-2 max-w-[80%] text-xs shadow-md">
                            <p className="font-semibold text-gray-400 mb-0.5">Customer (+1 555-0199)</p>
                            Do you guys offer international shipping? If yes, what are the shipping rates?
                          </div>
                        </div>

                        {/* Agent Auto Reply */}
                        <div className="flex justify-end">
                          <div className="bg-blue-600 text-white rounded-2xl rounded-tr-none px-3.5 py-2 max-w-[80%] text-xs shadow-md border border-blue-500">
                            <div className="flex items-center gap-1.5 mb-1 text-[10px] text-blue-200 font-bold">
                              <Zap size={10} className="fill-blue-200" /> AI Auto-Replied
                            </div>
                            Yes, we offer worldwide shipping to over 150 countries! 🌍 Shipping rates depend on your location and order size, which are automatically calculated at checkout. Feel free to enter your address during checkout to view the exact rate. Let me know if you have other questions!
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="text-[11px] text-blue-300/80 bg-blue-500/5 border border-blue-500/10 p-3 rounded-lg flex items-start gap-2">
                      <Clock size={14} className="mt-0.5 flex-shrink-0" />
                      <p>
                        <strong>Contextual Intelligence:</strong> The AI Agent read your uploaded `Pricing & Shipping Guidelines` PDF in the Knowledge Base to craft this accurate response without any manual code.
                      </p>
                    </div>
                  </div>
                )}

                {activePreviewAgent === 'hr' && (
                  <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                    <div>
                      <div className="flex items-center gap-3 mb-4">
                        <div className="bg-amber-600/20 text-amber-400 p-2 rounded-lg text-xs font-bold">RECRUITER</div>
                        <span className="text-xs text-gray-400 font-medium">Job: Sr. Backend Engineer</span>
                        <span className="ml-auto text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded font-bold uppercase">Interview Scheduled</span>
                      </div>

                      {/* Candidate Card */}
                      <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 space-y-3">
                        <div className="flex justify-between items-center">
                          <div>
                            <h4 className="font-extrabold text-sm text-white">Sarah Connor</h4>
                            <p className="text-xs text-gray-400">Experience: 5 years Python, Go, PostgreSQL</p>
                          </div>
                          <div className="text-right">
                            <span className="text-lg font-black text-emerald-400 block">96%</span>
                            <span className="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Match Score</span>
                          </div>
                        </div>

                        <div className="text-xs bg-indigo-950/20 border border-indigo-900/30 p-2.5 rounded text-gray-300">
                          <strong>Agent Sourcing Notes:</strong> Candidate has a strong fit for cybersecurity projects and PostgreSQL indexing. Outbound message delivered successfully. Candidate booked an interview.
                        </div>

                        {/* Meeting Link widget */}
                        <div className="flex items-center justify-between bg-violet-600/10 border border-violet-500/20 p-2.5 rounded-lg text-xs">
                          <div className="flex items-center gap-2 text-white">
                            <Calendar size={14} className="text-violet-400" />
                            <span>Interview Scheduled: May 24, 2:00 PM</span>
                          </div>
                          <span className="text-violet-400 font-semibold cursor-not-allowed">Google Meet Link</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-[11px] text-amber-300/80 bg-amber-500/5 border border-amber-500/10 p-3 rounded-lg flex items-center gap-2">
                      <Users size={14} className="flex-shrink-0" />
                      <p>Hunter scans job boards, scores candidates, conducts initial mail screens, and books directly into your calendar.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Calculator Section */}
        <div className="glass-panel border-violet-500/15 rounded-3xl p-8 shadow-2xl relative overflow-hidden mb-16">
          <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-indigo-600/5 rounded-full blur-[100px] pointer-events-none" />
          
          <div className="max-w-3xl mx-auto text-center mb-8">
            <h2 className="text-3xl font-extrabold text-white tracking-tight">AI Workforce Savings Calculator</h2>
            <p className="text-gray-400 mt-2">Adjust the sliders to estimate the direct hours and capital saved by using OctaOS.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            {/* Sliders Box */}
            <div className="space-y-6">
              <div className="space-y-2">
                <div className="flex justify-between text-sm font-semibold">
                  <label className="text-gray-300">Daily Tasks Automated</label>
                  <span className="text-violet-400 font-bold">{tasksPerDay} tasks/day</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="300"
                  step="5"
                  value={tasksPerDay}
                  onChange={e => setTasksPerDay(parseInt(e.target.value))}
                  className="w-full h-2 rounded-lg bg-gray-800 appearance-none cursor-pointer slider-thumb accent-violet-500"
                />
                <div className="flex justify-between text-[10px] text-gray-500">
                  <span>5 Tasks</span>
                  <span>300 Tasks</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm font-semibold">
                  <label className="text-gray-300">Target Hourly Rate</label>
                  <span className="text-violet-400 font-bold">${hourlyRate}/hour</span>
                </div>
                <input
                  type="range"
                  min="15"
                  max="120"
                  step="5"
                  value={hourlyRate}
                  onChange={e => setHourlyRate(parseInt(e.target.value))}
                  className="w-full h-2 rounded-lg bg-gray-800 appearance-none cursor-pointer slider-thumb accent-violet-500"
                />
                <div className="flex justify-between text-[10px] text-gray-500">
                  <span>$15/hr</span>
                  <span>$120/hr</span>
                </div>
              </div>
            </div>

            {/* Outputs Box */}
            <div className="grid grid-cols-2 gap-4 bg-[rgba(255,255,255,0.01)] border border-gray-800 p-6 rounded-2xl">
              <div className="text-center p-4 border border-gray-800/40 rounded-xl bg-gray-950/20 shadow-inner">
                <Clock size={24} className="text-violet-400 mx-auto mb-2" />
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Hours Saved / Mo</span>
                <div className="text-3xl font-black text-white mt-1">{hoursSaved} hrs</div>
                <span className="text-[9px] text-gray-400 block mt-1">Based on 0.75h/task</span>
              </div>
              <div className="text-center p-4 border border-gray-800/40 rounded-xl bg-gray-950/20 shadow-inner">
                <DollarSign size={24} className="text-emerald-400 mx-auto mb-2" />
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Savings Value / Mo</span>
                <div className="text-3xl font-black text-emerald-400 mt-1">${moneySaved.toLocaleString()}</div>
                <span className="text-[9px] text-emerald-500/80 block mt-1 font-semibold">Net ROI: 99.8%</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

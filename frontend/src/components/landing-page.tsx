'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Zap, Clock, DollarSign, Users, Calendar, Image as ImageIcon } from 'lucide-react';
import { getAccessToken } from '@/lib/auth-session';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export default function LandingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [tasksPerDay, setTasksPerDay] = useState(60);
  const [hourlyRate, setHourlyRate] = useState(35);
  const [activePreviewAgent, setActivePreviewAgent] = useState('marketing');
  const setAppState = (state: 'landing' | 'login' | 'signup' | 'app') => {
    if (state === 'login') router.push('/login');
    else if (state === 'signup') router.push('/signup');
    else if (state === 'app') router.push('/app/home');
    else router.push('/');
  };

  useEffect(() => {
    const invite = searchParams.get('token');
    if (invite) {
      router.replace(`/signup?token=${encodeURIComponent(invite)}`);
      return;
    }
    if (getAccessToken()) router.replace('/app/home');
  }, [router, searchParams]);

  useEffect(() => {
    fetch(`${API_URL}/auth/settings`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data?.logo_url) setLogoUrl(data.logo_url); })
      .catch(() => undefined);
  }, []);

  const hoursSaved = Math.round(tasksPerDay * 0.75 * 30);
  const moneySaved = Math.round(hoursSaved * hourlyRate);

  return (
    <div className="min-h-screen bg-background text-foreground relative font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 h-20 glass-panel border-b border-[rgba(167,139,250,0.1)] flex items-center justify-between px-8 md:px-16">
        <div className="flex items-center gap-3 text-2xl font-semibold tracking-tight text-white">
          {logoUrl ? (
            <img src={logoUrl} alt="OctaOS Logo" className="h-10 w-auto max-w-[180px] object-contain" />
          ) : (
            <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2 rounded-xl shadow-lg shadow-violet-500/20">
              <Zap className="text-white fill-white h-5 w-5 animate-pulse" />
            </div>
          )}
          <span>Octa<span className="text-violet-400">Os</span></span>
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
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium px-4 py-2 rounded-lg text-sm"
          >
            Sign Up
          </button>
        </div>
      </header>

      {/* Hero Content */}
      <main className="max-w-7xl mx-auto px-8 md:px-16 pt-20 pb-32 relative z-10">
        <div className="text-center space-y-6 max-w-4xl mx-auto mb-20">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-medium">
            <Zap size={12} />
            <span>OctaOS Autopilot v1.2</span>
          </div>

          <h1 className="text-5xl md:text-6xl font-semibold text-foreground tracking-tight leading-[1.1] animate-in fade-in slide-in-from-bottom-4 duration-500">
            The autonomous operating system
            <br />
            for enterprise teams.
          </h1>

          <p className="text-lg md:text-xl text-gray-400 leading-relaxed max-w-2xl mx-auto">
            Hire specialized AI Agents for Marketing, Sales, Customer Support, and HR. Define high-level goals and let your virtual team execute them autonomously.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
            <button 
              onClick={() => setAppState('signup')} 
              className="bg-primary hover:bg-primary/90 text-primary-foreground text-base font-medium px-6 py-3 rounded-lg"
            >
              Deploy Your AI Team
            </button>
            <button 
              onClick={() => {
                const el = document.getElementById('previews');
                el?.scrollIntoView({ behavior: 'smooth' });
              }} 
              className="bg-transparent hover:bg-muted text-foreground text-base font-medium px-6 py-3 rounded-lg border border-border"
            >
              Watch Previews
            </button>
          </div>
        </div>

        {/* Interactive Agent Previews */}
        <div id="previews" className="mb-24 scroll-mt-24">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-semibold text-foreground">Meet your virtual workforce</h2>
            <p className="text-muted-foreground mt-2 text-sm">Select a department to preview live workspace output.</p>
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
              <div className="bg-card border border-border rounded-xl p-6 min-h-[440px] flex flex-col relative overflow-hidden">

                {/* Window chrome */}
                <div className="flex items-center justify-between pb-4 border-b border-border mb-4">
                  <div className="flex gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/25" />
                    <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/25" />
                    <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/25" />
                  </div>
                  <span className="text-xs font-medium text-muted-foreground">Workspace output preview</span>
                  <span className="w-3 h-3 opacity-0" />
                </div>

                {/* Output content depending on active tab */}
                {activePreviewAgent === 'marketing' && (
                  <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                    <div>
                      <div className="flex items-center gap-3 mb-3">
                        <div className="bg-violet-600/20 text-violet-400 p-2 rounded-lg text-xs font-bold">LINKEDIN</div>
                        <span className="text-xs text-gray-400 font-medium">Day 4 of 30</span>
                        <span className="ml-auto text-xs bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded font-bold uppercase">Pending Approval</span>
                      </div>
                      <div className="bg-[rgba(255,255,255,0.02)] p-4 rounded-xl border border-gray-800 text-sm text-gray-300 whitespace-pre-line leading-relaxed">
                        {"☕️ Work hard, coffee harder! \n\nWe're thrilled to introduce our new Organic Cold Brew at BlueBottle Cafe. Cold-steeped for 18 hours for maximum smoothness and low acidity. Pop in today and grab your jar! \n\n#cafevibes #organicroast #coldbrew"}
                      </div>
                    </div>
                    
                    <div className="relative rounded-xl overflow-hidden border border-gray-800 aspect-[16/9] flex items-center justify-center bg-gradient-to-br from-indigo-950/50 to-violet-950/50 shadow-inner">
                      <div className="text-center p-4">
                        <ImageIcon size={36} className="text-violet-400 mx-auto mb-2 animate-bounce" />
                        <span className="text-xs text-gray-400 font-bold block uppercase tracking-wider">AI Graphic Generated</span>
                        <span className="text-xs text-gray-500 italic block mt-0.5">Prompt: \"Vibrant graphic showcasing cold brew coffee on wooden table, cafe vibes, modern illustration\"</span>
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
                        <span className="ml-auto text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold uppercase">4 Leads Found</span>
                      </div>

                      <div className="border border-gray-800 rounded-xl overflow-hidden bg-[rgba(0,0,0,0.2)]">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-surface-hover border-b border-border text-muted-foreground">
                            <tr>
                              <th className="p-3 font-medium">Lead name</th>
                              <th className="p-3 font-medium">Company</th>
                              <th className="p-3 font-medium">Email</th>
                              <th className="p-3 font-medium">Status</th>
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
                                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
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
                      <p className="text-xs text-gray-400 leading-relaxed font-mono">
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
                        <span className="ml-auto text-xs bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold uppercase">Solved By AI</span>
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
                            <div className="flex items-center gap-1.5 mb-1 text-xs text-blue-200 font-bold">
                              <Zap size={10} className="fill-blue-200" /> AI Auto-Replied
                            </div>
                            Yes, we offer worldwide shipping to over 150 countries! 🌍 Shipping rates depend on your location and order size, which are automatically calculated at checkout. Feel free to enter your address during checkout to view the exact rate. Let me know if you have other questions!
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="text-xs text-blue-300/80 bg-blue-500/5 border border-blue-500/10 p-3 rounded-lg flex items-start gap-2">
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
                        <span className="ml-auto text-xs bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded font-bold uppercase">Interview Scheduled</span>
                      </div>

                      {/* Candidate Card */}
                      <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 space-y-3">
                        <div className="flex justify-between items-center">
                          <div>
                            <h4 className="font-semibold text-sm text-white">Sarah Connor</h4>
                            <p className="text-xs text-gray-400">Experience: 5 years Python, Go, PostgreSQL</p>
                          </div>
                          <div className="text-right">
                            <span className="text-lg font-semibold text-emerald-400 block">96%</span>
                            <span className="text-xs text-gray-500 font-bold uppercase tracking-wider">Match Score</span>
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

                    <div className="text-xs text-amber-300/80 bg-amber-500/5 border border-amber-500/10 p-3 rounded-lg flex items-center gap-2">
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
        <div className="bg-card border border-border rounded-xl p-8 relative overflow-hidden mb-16">
          
          <div className="max-w-3xl mx-auto text-center mb-8">
            <h2 className="text-2xl font-semibold text-foreground tracking-tight">Workforce savings calculator</h2>
            <p className="text-muted-foreground mt-2 text-sm">Adjust the sliders to estimate the direct hours and capital saved by deploying OctaOS.</p>
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
                <div className="flex justify-between text-xs text-gray-500">
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
                <div className="flex justify-between text-xs text-gray-500">
                  <span>$15/hr</span>
                  <span>$120/hr</span>
                </div>
              </div>
            </div>

            {/* Outputs Box */}
            <div className="grid grid-cols-2 gap-4 bg-[rgba(255,255,255,0.01)] border border-gray-800 p-6 rounded-2xl">
              <div className="text-center p-4 border border-gray-800/40 rounded-xl bg-gray-950/20 shadow-inner">
                <Clock size={24} className="text-violet-400 mx-auto mb-2" />
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Hours Saved / Mo</span>
                <div className="text-3xl font-semibold text-white mt-1">{hoursSaved} hrs</div>
                <span className="text-xs text-gray-400 block mt-1">Based on 0.75h/task</span>
              </div>
              <div className="text-center p-4 border border-gray-800/40 rounded-xl bg-gray-950/20 shadow-inner">
                <DollarSign size={24} className="text-emerald-400 mx-auto mb-2" />
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Savings Value / Mo</span>
                <div className="text-3xl font-semibold text-emerald-400 mt-1">${moneySaved.toLocaleString()}</div>
                <span className="text-xs text-emerald-500/80 block mt-1 font-semibold">Net ROI: 99.8%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Modular AI Workforce Pricing Section */}
        <div className="mb-16">
          <div className="max-w-3xl mx-auto text-center mb-12">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-400 border border-violet-500/20 mb-3">
              <Zap size={12} /> Transparent Modular Pricing
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight">Hire Individually or as a Full Team</h2>
            <p className="text-gray-400 mt-2 text-sm md:text-base">
              Pay only for the autonomous employees you actually deploy. No forced all-in-one locks.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
            {[
              {
                name: 'Campaign Planner AI',
                persona: 'Jules — Senior Copywriter',
                desc: '30-day autonomous marketing calendar, visual prompts, and multi-channel posting.',
                priceUsd: '$49',
                priceInr: '₹3,999',
                quota: '10,000 actions/mo',
                color: 'text-info',
                border: 'border-primary/20',
              },
              {
                name: 'Sales AI SDR',
                persona: 'Alex — Outbound SDR',
                desc: 'Lead scraping from Google Places & Apollo, automated email sequencing, and Deal Rooms.',
                priceUsd: '$79',
                priceInr: '₹5,999',
                quota: '15,000 actions/mo',
                color: 'text-success',
                border: 'border-success/20',
              },
              {
                name: 'HR Recruiter AI',
                persona: 'Hunter — Talent Recruiter',
                desc: 'Resume parsing, job-match scoring, candidate screening tests, and Google Meet scheduling.',
                priceUsd: '$49',
                priceInr: '₹3,999',
                quota: '10,000 actions/mo',
                color: 'text-warning',
                border: 'border-warning/20',
              },
              {
                name: 'Customer Support AI',
                persona: 'Sam — 24/7 Support Agent',
                desc: 'Omnichannel WhatsApp & Email resolution with Knowledge-Base RAG grounding & human takeover.',
                priceUsd: '$49',
                priceInr: '₹3,999',
                quota: '15,000 actions/mo',
                color: 'text-info',
                border: 'border-info/20',
              },
            ].map((plan, idx) => (
              <div
                key={idx}
                className={`p-6 rounded-xl bg-card border ${plan.border} flex flex-col justify-between hover:border-primary/40 transition-colors`}
              >
                <div>
                  <h3 className="font-bold text-lg text-white">{plan.name}</h3>
                  <span className={`text-xs ${plan.color} font-medium block mt-0.5`}>{plan.persona}</span>
                  <p className="text-xs text-gray-400 mt-3 leading-relaxed">{plan.desc}</p>
                </div>

                <div className="pt-6 mt-4 border-t border-gray-800">
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold text-white">{plan.priceInr}</span>
                    <span className="text-xs text-gray-400">/ mo ({plan.priceUsd})</span>
                  </div>
                  <span className="text-[11px] text-zinc-500 block mt-0.5">{plan.quota}</span>

                  <button
                    onClick={() => setAppState('signup')}
                    className="w-full mt-4 bg-white/5 hover:bg-white/10 text-white border border-white/10 font-semibold py-2 px-3 rounded-xl text-xs transition-colors"
                  >
                    Hire Standalone
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Full Access Workforce Banner */}
          <div className="p-8 rounded-xl bg-surface-hover border border-primary/30 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20 mb-2">
                <Zap size={11} /> Best value for scale
              </div>
              <h3 className="text-xl font-semibold text-foreground">All-in-one AI workforce</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
                Deploy Jules (Marketing), Alex (Sales), Hunter (HR), and Sam (Support) simultaneously, coordinated by the CEO Workspace and Boardroom orchestrator.
              </p>
            </div>

            <div className="text-left lg:text-right shrink-0">
              <div className="text-2xl font-bold text-foreground">
                ₹11,999 <span className="text-sm text-muted-foreground font-normal">/ mo ($149 USD)</span>
              </div>
              <span className="text-xs text-success font-medium block mt-0.5">100,000 monthly actions included</span>
              <button
                onClick={() => setAppState('signup')}
                className="mt-3 bg-primary hover:bg-primary-hover text-primary-foreground font-medium px-6 py-2.5 rounded-lg text-sm transition-colors"
              >
                Deploy complete workforce
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

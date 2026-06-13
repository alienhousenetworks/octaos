'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Briefcase, Search, Mail, Calendar, Loader2, Bot, Plus } from 'lucide-react';

interface HRViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
}

export default function HRView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
}: HRViewProps) {
  // HR states relocated here
  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [hrRole, setHrRole] = useState('Software Engineer');
  const [hrRequirements, setHrRequirements] = useState('React, Node.js, Python, 3+ years experience');
  const [hrSalary, setHrSalary] = useState('$120,000/year');
  const [hrCount, setHrCount] = useState(5);
  const [hrLoading, setHrLoading] = useState(false);
  const [outreachLoading, setOutreachLoading] = useState(false);
  const [interviewLoading, setInterviewLoading] = useState(false);

  useEffect(() => {
    if (token) {
      fetchCandidates();
    }
  }, [token]);

  // HR functions
    const fetchCandidates = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/`);
      if (res.ok) {
        const data = await res.json();
        setCandidates(data);
      }
    } catch (e) {
      console.error(e);
    }
  };


    const handleSourceCandidates = async () => {
    if (!hrRole || !hrRequirements) return;
    setHrLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: hrRole,
          requirements: hrRequirements,
          salary: hrSalary,
          count: hrCount
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("HR Agent has started sourcing candidates! Check progress in the Activity Feed.");
        setHrRole('');
        setHrRequirements('');
        fetchCandidates();
        fetchData();
      } else {
        alert(`Error: ${data.detail || 'Failed to source candidates'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setHrLoading(false);
    }
  };


    const handleCandidateOutreach = async (candidateId: string) => {
    setOutreachLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}/outreach`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: "free_outreach"
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("Outreach sent successfully!");
        fetchCandidates();
        fetchData();
      } else {
        alert(`Error: ${data.detail || 'Failed to send outreach'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setOutreachLoading(false);
    }
  };


    const handleScheduleInterview = async (candidateId: string) => {
    setInterviewLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}/interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: "free_scheduling"
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("Interview scheduled successfully!");
        fetchCandidates();
        fetchData();
      } else {
        alert(`Error: ${data.detail || 'Failed to schedule interview'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setInterviewLoading(false);
    }
  };



  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <Briefcase className="text-amber-400 h-8 w-8 animate-pulse" /> Hiring & HR Recruiter Agent
                  </h1>
                  <p className="text-gray-400 mt-1">Autonomous candidate sourcing, outreach sequencing, and interview scheduling.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Sourcing Generator Form */}
                <div className="lg:col-span-1 space-y-6">
                  <Card className="glass-panel border-transparent glow-hr rounded-3xl overflow-hidden shadow-2xl relative">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                    <CardHeader>
                      <CardTitle className="text-xl text-white font-extrabold tracking-tight">Find Candidates</CardTitle>
                      <CardDescription className="text-gray-400 text-xs mt-1">Specify the role requirements and salary budget to trigger autonomous candidate sourcing.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex flex-col gap-2">
                        <label className="text-xs font-semibold text-gray-400">Role Title</label>
                        <Input
                          placeholder="e.g. Senior Backend Engineer"
                          value={hrRole}
                          onChange={e => setHrRole(e.target.value)}
                          className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl h-10"
                        />
                      </div>

                      <div className="flex flex-col gap-2">
                        <label className="text-xs font-semibold text-gray-400">Role Requirements & Qualifications</label>
                        <Textarea
                          placeholder="e.g. 3+ years experience with Python, FastAPI, PostgreSQL. Strong communication and remote work capability."
                          className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl min-h-[120px] text-sm"
                          value={hrRequirements}
                          onChange={e => setHrRequirements(e.target.value)}
                        />
                      </div>

                      <div className="flex gap-4">
                        <div className="flex-1 flex flex-col gap-2">
                          <label className="text-xs font-semibold text-gray-400">Annual Salary / Budget</label>
                          <Input
                            placeholder="e.g. $120,000/year"
                            value={hrSalary}
                            onChange={e => setHrSalary(e.target.value)}
                            className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl h-10"
                          />
                        </div>
                        <div className="w-24 flex flex-col gap-2">
                          <label className="text-xs font-semibold text-gray-400">Count</label>
                          <Input
                            type="number"
                            min={1}
                            max={10}
                            value={hrCount}
                            onChange={e => setHrCount(parseInt(e.target.value) || 5)}
                            className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl h-10"
                          />
                        </div>
                      </div>

                      <Button
                        onClick={handleSourceCandidates}
                        disabled={hrLoading || !hrRole || !hrRequirements}
                        className="w-full h-11 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold rounded-xl shadow-lg shadow-amber-500/20 hover:shadow-amber-500/30 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 disabled:shadow-none"
                      >
                        {hrLoading ? 'HR Agent Sourcing...' : 'Autonomously Source Candidates'}
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Quick Stats card */}
                  <Card className="glass-panel border-transparent p-6 space-y-4 rounded-3xl shadow-2xl relative">
                    <h3 className="font-bold text-sm text-white border-b border-gray-800 pb-2">Hiring Pipeline Progress</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Sourced Candidates:</span>
                        <span className="font-bold text-white">{candidates.length}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Outreach Sent (Screened):</span>
                        <span className="font-bold text-white">{candidates.filter(c => c.status === 'screened').length}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Interviews Scheduled:</span>
                        <span className="font-bold text-white">{candidates.filter(c => c.status === 'interviewed').length}</span>
                      </div>
                    </div>
                  </Card>
                </div>

                {/* Candidate Pipeline Display */}
                <div className="lg:col-span-2 space-y-6">
                  {candidates.length === 0 ? (
                    <Card className="glass-panel border-dashed border-gray-800 p-12 text-center flex flex-col items-center justify-center rounded-3xl min-h-[400px] shadow-2xl">
                      <div className="text-5xl mb-4 animate-bounce">👥</div>
                      <h3 className="text-lg font-bold text-white">No candidates sourced yet</h3>
                      <p className="text-gray-400 max-w-sm mt-2 text-xs leading-relaxed">Submit your job details on the left, and the HR AI agent will populate matches here.</p>
                    </Card>
                  ) : (
                    <div className="space-y-4 max-h-[750px] overflow-y-auto pr-2 pb-6">
                      {candidates.map(candidate => {
                        const scorecard = candidate.scorecard || {};
                        const skills = scorecard.skills || [];
                        const score = scorecard.match_score || 0;
                        const summary = scorecard.experience_summary || '';
                        const matchReason = scorecard.requirements_match || '';
                        const expectedSalary = scorecard.salary_expectation || '';

                        let statusColor = 'bg-gray-500/10 text-gray-400 border-gray-500/20';
                        if (candidate.status === 'sourced') statusColor = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                        if (candidate.status === 'screened') statusColor = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
                        if (candidate.status === 'interviewed') statusColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';

                        let scoreColor = 'text-emerald-400';
                        if (score < 80) scoreColor = 'text-amber-400';
                        if (score < 70) scoreColor = 'text-rose-400';

                        const isSelected = selectedCandidateId === candidate.id;

                        return (
                          <Card key={candidate.id} className={`glass-panel border-gray-800/80 hover:border-amber-500/40 hover:shadow-amber-500/5 transition-all duration-200 overflow-hidden rounded-2xl shadow-xl ${isSelected ? 'ring-2 ring-amber-500' : ''}`}>
                            <div className="p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-gray-800 bg-gray-950/40">
                              <div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <h3 className="text-lg font-bold text-white">{candidate.name}</h3>
                                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${statusColor}`}>
                                    {candidate.status}
                                  </span>
                                </div>
                                <p className="text-xs text-gray-400 mt-1">{candidate.email} • Sourced for <strong>{candidate.role}</strong></p>
                              </div>

                              <div className="flex items-center gap-3">
                                <div className="relative h-12 w-12 flex items-center justify-center">
                                  <svg className="w-full h-full transform -rotate-90">
                                    <circle cx="24" cy="24" r="20" stroke="rgba(255,255,255,0.05)" strokeWidth="3" fill="transparent" />
                                    <circle cx="24" cy="24" r="20" 
                                      stroke={score >= 80 ? "#10b981" : score >= 70 ? "#f59e0b" : "#ef4444"} 
                                      strokeWidth="3.5" 
                                      fill="transparent" 
                                      strokeDasharray={2 * Math.PI * 20}
                                      strokeDashoffset={2 * Math.PI * 20 * (1 - score / 100)}
                                      strokeLinecap="round"
                                      className="transition-all duration-500"
                                    />
                                  </svg>
                                  <span className={`absolute text-[10px] font-black ${scoreColor}`}>{score}%</span>
                                </div>
                                <div className="text-left hidden md:block pr-2">
                                  <div className="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Match Score</div>
                                  <div className="text-[10px] text-gray-400 font-medium">HR AI Assessed</div>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-gray-400 hover:text-white"
                                  onClick={() => setSelectedCandidateId(isSelected ? null : candidate.id)}
                                >
                                  {isSelected ? 'Hide Details' : 'View Details'}
                                </Button>
                              </div>
                            </div>

                            {/* Details Panel */}
                            {isSelected && (
                              <div className="p-5 border-b border-gray-800 bg-gray-950/20 space-y-4 animate-in slide-in-from-top-2 duration-200">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div>
                                    <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Skills</h4>
                                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                                      {skills.map((skill: string) => (
                                        <span key={skill} className="px-2 py-0.5 bg-gray-900 text-gray-300 text-xs rounded-lg border border-gray-800">
                                          {skill}
                                        </span>
                                      ))}
                                      {skills.length === 0 && <span className="text-xs text-gray-500">None listed</span>}
                                    </div>
                                  </div>
                                  <div>
                                    <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Salary Expectations</h4>
                                    <p className="text-sm font-semibold text-white mt-1">{expectedSalary || 'N/A'}</p>
                                  </div>
                                </div>

                                <div>
                                  <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Profile Summary</h4>
                                  <p className="text-xs text-gray-300 mt-1.5 leading-relaxed">{summary}</p>
                                </div>

                                <div>
                                  <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Match Analysis</h4>
                                  <p className="text-xs text-blue-300 mt-1.5 leading-relaxed bg-blue-950/20 border border-blue-900/30 p-3 rounded-xl">{matchReason}</p>
                                </div>

                                {/* Outreach detail */}
                                {scorecard.outbound_subject && (
                                  <div className="bg-amber-950/20 border border-amber-900/30 p-4 rounded-xl space-y-2">
                                    <h4 className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                                      ✉️ Recruiter Outreach Message
                                    </h4>
                                    <p className="text-xs text-gray-400"><strong>Subject:</strong> {scorecard.outbound_subject}</p>
                                    <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed mt-1 border-t border-amber-900/20 pt-2">{scorecard.outbound_body}</p>
                                    {scorecard.sent_actual !== undefined && (
                                      <p className="text-[9px] text-gray-500 italic mt-1">
                                        Status: {scorecard.sent_actual ? "Sent via SMTP" : "Simulated Delivery"}
                                      </p>
                                    )}
                                  </div>
                                )}

                                {/* Candidate Reply detail */}
                                {scorecard.candidate_reply && (
                                  <div className="bg-emerald-950/20 border border-emerald-900/30 p-4 rounded-xl space-y-2">
                                    <h4 className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                                      💬 Candidate Reply
                                    </h4>
                                    <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{scorecard.candidate_reply}</p>
                                  </div>
                                )}

                                {/* Interview Booking details */}
                                {scorecard.meeting_time && (
                                  <div className="bg-purple-950/20 border border-purple-900/30 p-4 rounded-xl space-y-2">
                                    <h4 className="text-[10px] font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                                      📅 Booked Interview
                                    </h4>
                                    <p className="text-xs text-gray-300"><strong>Time:</strong> {scorecard.meeting_time}</p>
                                    <p className="text-xs text-gray-300">
                                      <strong>Google Meet Link: </strong>
                                      <a href={scorecard.meeting_link} target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 underline font-semibold transition-colors">
                                        {scorecard.meeting_link}
                                      </a>
                                    </p>
                                    {scorecard.calendar_booked !== undefined && (
                                      <p className="text-[9px] text-gray-500 italic mt-1">
                                        Status: {scorecard.calendar_booked ? "Created Google Calendar Event" : "Simulated Schedule"}
                                      </p>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Actions footer */}
                            <div className="px-5 py-3 bg-gray-950/30 flex gap-2 justify-end border-t border-gray-800">
                              {candidate.status === 'sourced' && (
                                <Button
                                  size="sm"
                                  onClick={() => handleCandidateOutreach(candidate.id)}
                                  disabled={outreachLoading}
                                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold h-9 px-4 rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all hover:scale-[1.02] active:scale-95 text-xs"
                                >
                                  {outreachLoading ? 'Sending...' : 'Send Outreach Email'}
                                </Button>
                              )}
                              {candidate.status === 'screened' && (
                                <Button
                                  size="sm"
                                  onClick={() => handleScheduleInterview(candidate.id)}
                                  disabled={interviewLoading}
                                  className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white font-bold h-9 px-4 rounded-xl shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all hover:scale-[1.02] active:scale-95 text-xs"
                                >
                                  {interviewLoading ? 'Scheduling...' : 'Simulate Reply & Book Interview'}
                                </Button>
                              )}
                              {candidate.status === 'interviewed' && (
                                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                                  ✓ Interview Scheduled
                                </span>
                              )}
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
  );
}

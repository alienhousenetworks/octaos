'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { PEOPLE_ROUTES, type PeopleScreen } from './routes';
import {
  Users,
  Target,
  Clock,
  Sparkles,
  Search,
  Plus,
  Calendar,
  CheckCircle2,
  AlertTriangle,
  FileText,
  BarChart3,
  Bot,
  Send,
  Shield,
  Layers,
  ChevronRight,
  UserCheck,
  Building,
  Briefcase,
  Zap,
  Flame,
  ArrowRight,
  TrendingUp,
  RefreshCw,
  X,
  MessageSquare
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { notify } from '@/lib/notify';
import HRView from './hiring/hr-view';

interface HREnterpriseSuiteProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  screen?: PeopleScreen;
  initialRoomSlug?: string;
}

export default function HREnterpriseSuite({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  screen = 'people',
  initialRoomSlug,
}: HREnterpriseSuiteProps) {
  const router = useRouter();

  // Copilot Drawer State
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [copilotInput, setCopilotInput] = useState('');
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [copilotMessages, setCopilotMessages] = useState<Array<{
    role: 'user' | 'assistant';
    content: string;
    agent?: string;
    action?: any;
  }>>([
    {
      role: 'assistant',
      content: 'Ask about people, hiring, or time off. I can look up the directory, the pipeline, or leave coverage.',
      agent: 'HR Orchestrator'
    }
  ]);

  // People Data State
  const [employees, setEmployees] = useState<any[]>([]);
  const [employeesLoading, setEmployeesLoading] = useState(false);
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [isAddEmployeeOpen, setIsAddEmployeeOpen] = useState(false);
  const [newFirstName, setNewFirstName] = useState('');
  const [newLastName, setNewLastName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newDept, setNewDept] = useState('Engineering');

  // Workforce & Leave State
  const [leaves, setLeaves] = useState<any[]>([]);
  const [leavesLoading, setLeavesLoading] = useState(false);
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [selectedEmpForLeave, setSelectedEmpForLeave] = useState('');
  const [leaveDays, setLeaveDays] = useState('3');
  const [leaveReason, setLeaveReason] = useState('Personal time off');
  const [submittingLeave, setSubmittingLeave] = useState(false);

  // Analytics State
  const [analytics, setAnalytics] = useState<any>(null);

  // Keyboard shortcut Cmd+J to toggle Copilot
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        setIsCopilotOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch initial data
  useEffect(() => {
    loadEmployees();
    loadLeaves();
    loadAnalytics();
  }, [API_URL]);

  const loadEmployees = async () => {
    setEmployeesLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/people/employees`);
      if (res.ok) {
        const data = await res.json();
        setEmployees(data.items || []);
        if (data.items?.length > 0 && !selectedEmpForLeave) {
          setSelectedEmpForLeave(data.items[0].id);
        }
      }
    } catch {
      // fallback
    } finally {
      setEmployeesLoading(false);
    }
  };

  const loadLeaves = async () => {
    setLeavesLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/workforce/leaves`);
      if (res.ok) {
        const data = await res.json();
        setLeaves(data || []);
      }
    } catch {
      // fallback
    } finally {
      setLeavesLoading(false);
    }
  };

  const loadAnalytics = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/people/analytics/summary`);
      if (res.ok) {
        setAnalytics(await res.json());
      }
    } catch {
      // fallback
    }
  };

  const handleCreateEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFirstName || !newLastName || !newEmail || !newTitle) {
      notify.error('Please complete all required fields.');
      return;
    }
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/people/employees`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: newFirstName,
          last_name: newLastName,
          email: newEmail,
          job_title: newTitle,
          department_name: newDept
        })
      });
      if (res.ok) {
        notify.success('Employee created successfully.');
        setIsAddEmployeeOpen(false);
        setNewFirstName('');
        setNewLastName('');
        setNewEmail('');
        setNewTitle('');
        loadEmployees();
        loadAnalytics();
      } else {
        const err = await res.json();
        notify.error(err.detail || 'Failed to create employee');
      }
    } catch {
      notify.error('Network error creating employee');
    }
  };

  const handleSubmitLeave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEmpForLeave) {
      notify.error('Select an employee.');
      return;
    }
    setSubmittingLeave(true);
    try {
      const today = new Date();
      const start = new Date(today.setDate(today.getDate() + 7)).toISOString().split('T')[0];
      const end = new Date(today.setDate(today.getDate() + parseInt(leaveDays) - 1)).toISOString().split('T')[0];

      const res = await fetchWithAuth(`${API_URL}/hr/workforce/leaves`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: selectedEmpForLeave,
          leave_type_code: 'ANNUAL',
          start_date: start,
          end_date: end,
          days_requested: parseFloat(leaveDays),
          reason: leaveReason
        })
      });
      if (res.ok) {
        const data = await res.json();
        notify.success(`Leave request submitted! Coverage Score: ${Math.round((data.coverage_score || 1) * 100)}%`);
        setIsLeaveModalOpen(false);
        loadLeaves();
      } else {
        const err = await res.json();
        notify.error(err.detail || 'Failed to submit leave request');
      }
    } catch {
      notify.error('Network error submitting leave');
    } finally {
      setSubmittingLeave(false);
    }
  };

  const handleSendCopilot = async () => {
    if (!copilotInput.trim()) return;
    const msg = copilotInput.trim();
    setCopilotInput('');
    setCopilotMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setCopilotLoading(true);

    try {
      const res = await fetchWithAuth(`${API_URL}/hr/copilot/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: msg,
          messages: copilotMessages.slice(-6).map((m) => ({
            role: m.role,
            content: m.content
          })),
          context_pillar: screen === 'hiring' ? 'talent' : screen === 'leave' ? 'compensation' : 'people',
          context_submodule: screen === 'hiring' ? 'recruitment' : screen === 'leave' ? 'leave_management' : 'employee_management',
          resource_id: selectedEmpForLeave || undefined
        })
      });
      if (res.ok) {
        const data = await res.json();
        const action = data.task_result?.proposed_actions?.[0];
        setCopilotMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.reply,
            agent: data.specialist_agent,
            action: action
          }
        ]);
        if (action?.executed) {
          loadEmployees();
          loadLeaves();
        }
      } else {
        setCopilotMessages((prev) => [
          ...prev,
          { role: 'assistant', content: 'Apologies, I encountered an error retrieving that workforce data.' }
        ]);
      }
    } catch {
      setCopilotMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Unable to reach the HR Copilot service.' }
      ]);
    } finally {
      setCopilotLoading(false);
    }
  };

  const filteredEmployees = employees.filter((e) =>
    e.full_name?.toLowerCase().includes(employeeSearch.toLowerCase()) ||
    e.job_title?.toLowerCase().includes(employeeSearch.toLowerCase()) ||
    e.department_name?.toLowerCase().includes(employeeSearch.toLowerCase())
  );

  return (
    <div className="relative flex flex-col gap-4">
      <div className="border border-border bg-card rounded-xl px-5 py-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">People</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Start with who works here, then hire, then handle time off.
            </p>
          </div>

          {/* Quick Metrics & Copilot Trigger */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-4 bg-slate-800/60 border border-slate-700/60 rounded-lg px-4 py-1.5 text-xs">
              <div>
                <span className="text-slate-400">Headcount:</span>{' '}
                <span className="font-semibold text-white">{analytics?.headcount?.total_active ?? employees.length}</span>
              </div>
              <div className="w-px h-4 bg-slate-700" />
              <div>
                <span className="text-slate-400">Pending Leaves:</span>{' '}
                <span className="font-semibold text-amber-400">{leaves.filter((l) => l.status === 'pending').length}</span>
              </div>
            </div>

            <Button
              onClick={() => setIsCopilotOpen(true)}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-lg shadow-indigo-500/20 text-xs gap-2 font-medium"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              Ask HR
              <span className="hidden sm:inline-block px-1.5 py-0.5 bg-indigo-900/60 rounded text-[10px] text-indigo-200 border border-indigo-400/20">
                ⌘J
              </span>
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-1 mt-4 overflow-x-auto">
          {([
            { id: 'people' as const, label: '1. People', count: `${employees.length}` },
            { id: 'hiring' as const, label: '2. Hiring', count: 'ATS' },
            { id: 'leave' as const, label: '3. Time off', count: `${leaves.filter((l) => l.status === 'pending').length} pending` },
          ]).map((step) => {
            const isActive = screen === step.id;
            return (
              <button
                key={step.id}
                onClick={() => router.push(PEOPLE_ROUTES[step.id])}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border whitespace-nowrap ${
                  isActive
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-border text-muted-foreground hover:text-foreground'
                }`}
              >
                <span>{step.label}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${isActive ? 'bg-primary-foreground/15' : 'bg-muted text-muted-foreground'}`}>
                  {step.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── MAIN WORKSPACE CONTENT ── */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6">
        {/* ========================================================================= */}
        {/* CASE 1: TALENT MANAGEMENT -> RECRUITMENT (PRESERVED LIVE ATS ENGINE)      */}
        {/* ========================================================================= */}
        {screen === 'hiring' && (
          <HRView
            token={token}
            API_URL={API_URL}
            fetchWithAuth={fetchWithAuth}
            fetchData={fetchData}
            initialRoomSlug={initialRoomSlug}
          />
        )}

        {/* ========================================================================= */}
        {/* CASE 2: PEOPLE MANAGEMENT -> EMPLOYEE DIRECTORY                           */}
        {/* ========================================================================= */}
        {screen === 'people' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-foreground">People directory</h2>
                <p className="text-xs text-muted-foreground">Everyone who already works here.</p>
              </div>

              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
                  <Input
                    placeholder="Search by name, role, department..."
                    value={employeeSearch}
                    onChange={(e) => setEmployeeSearch(e.target.value)}
                    className="pl-9 bg-slate-900 border-slate-800 text-xs w-64 text-white"
                  />
                </div>
                <Button
                  onClick={() => setIsAddEmployeeOpen(true)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs gap-1.5"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Employee
                </Button>
              </div>
            </div>

            {/* Employee Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredEmployees.map((emp) => (
                <Card key={emp.id} className="bg-slate-900/60 border-slate-800/80 hover:border-slate-700 transition-all">
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-bold text-white text-sm">
                          {emp.first_name?.[0]}{emp.last_name?.[0]}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-white">{emp.full_name}</div>
                          <div className="text-xs text-slate-400">{emp.job_title}</div>
                        </div>
                      </div>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {emp.employee_number}
                      </span>
                    </div>

                    <div className="text-xs text-slate-400 space-y-1">
                      <div className="flex items-center gap-2">
                        <Building className="w-3.5 h-3.5 text-slate-500" />
                        <span>{emp.department_name || 'General Operations'}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Briefcase className="w-3.5 h-3.5 text-slate-500" />
                        <span>{emp.work_location || 'Remote'} · {emp.employment_type}</span>
                      </div>
                    </div>

                    {emp.skills?.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {emp.skills.slice(0, 3).map((s: string) => (
                          <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>

            {filteredEmployees.length === 0 && !employeesLoading && (
              <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
                No employees found matching &quot;{employeeSearch}&quot;.
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* CASE 3: COMPENSATION -> LEAVE MANAGEMENT (VERTICAL SLICE 1)               */}
        {/* ========================================================================= */}
        {screen === 'leave' && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-foreground">Time off</h2>
                <p className="text-xs text-muted-foreground">
                  Requests, balances, and whether the team is covered.
                </p>
              </div>

              <Button
                onClick={() => setIsLeaveModalOpen(true)}
                className="bg-amber-600 hover:bg-amber-500 text-white text-xs gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" /> Submit Leave Request
              </Button>
            </div>

            {/* Leave Requests Table */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                  <tr>
                    <th className="py-3 px-4">Employee</th>
                    <th className="py-3 px-4">Leave Type</th>
                    <th className="py-3 px-4">Dates</th>
                    <th className="py-3 px-4">Days</th>
                    <th className="py-3 px-4">AI Coverage Score</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {leaves.map((l) => (
                    <tr key={l.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-4 font-medium text-white">{l.employee_name}</td>
                      <td className="py-3 px-4">{l.leave_type}</td>
                      <td className="py-3 px-4 text-slate-400">{l.start_date} → {l.end_date}</td>
                      <td className="py-3 px-4 font-semibold">{l.days_requested} d</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full ${
                                (l.coverage_score || 1) >= 0.6 ? 'bg-emerald-500' : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.round((l.coverage_score || 1) * 100)}%` }}
                            />
                          </div>
                          <span className="text-[11px] font-semibold">
                            {Math.round((l.coverage_score || 1) * 100)}%
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            l.status === 'approved'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          }`}
                        >
                          {l.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {l.status === 'pending' && (
                          <Button
                            onClick={async () => {
                              try {
                                const res = await fetchWithAuth(`${API_URL}/hr/workforce/leaves/${l.id}/approve`, {
                                  method: 'POST'
                                });
                                if (res.ok) {
                                  notify.success('Leave approved and deducted from ledger.');
                                  loadLeaves();
                                }
                              } catch {
                                notify.error('Approval failed');
                              }
                            }}
                            className="h-7 px-2.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-[11px]"
                          >
                            Approve
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {leaves.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500">
                        No active leave requests. Click &quot;Submit Leave Request&quot; above to simulate coverage.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>

      {/* ── COPILOT EXPANDABLE DRAWER (CMD+J) ── */}
      {isCopilotOpen && (
        <div className="fixed inset-y-0 right-0 w-full sm:w-[460px] bg-slate-900/95 border-l border-slate-800 shadow-2xl backdrop-blur-xl z-50 flex flex-col">
          {/* Drawer Header */}
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <div>
                <h3 className="text-sm font-semibold text-white">Universal HR Copilot</h3>
                <span className="text-[10px] text-slate-400">Multi-agent orchestrator with HITL approvals</span>
              </div>
            </div>
            <button
              onClick={() => setIsCopilotOpen(false)}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Drawer Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            {copilotMessages.map((m, idx) => (
              <div
                key={idx}
                className={`p-3.5 rounded-lg border ${
                  m.role === 'user'
                    ? 'bg-blue-600/15 border-blue-500/30 text-blue-200 ml-8'
                    : 'bg-slate-800/60 border-slate-700/60 text-slate-200 mr-4'
                }`}
              >
                {m.agent && (
                  <div className="text-[10px] font-semibold text-amber-400 mb-1 flex items-center gap-1">
                    <Bot className="w-3 h-3" /> {m.agent}
                  </div>
                )}
                <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>

                {/* Proposed Action Card */}
                {m.action && (
                  <div className="mt-3 p-2.5 rounded bg-slate-900 border border-slate-700 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-semibold text-white">{m.action.title}</span>
                      {m.action.executed ? (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-medium">
                          ✓ Live Synced
                        </span>
                      ) : (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          {m.action.risk_tier} · Approval Req
                        </span>
                      )}
                    </div>
                    {!m.action.executed && (
                      <Button
                        onClick={async () => {
                          try {
                            const res = await fetchWithAuth(`${API_URL}/hr/copilot/actions/submit-approval`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                action_type: m.action.action_type,
                                title: m.action.title,
                                resource_id: m.action.resource_id,
                                payload: m.action.payload,
                                rationale: 'Approved via HR Copilot drawer',
                                risk_tier: m.action.risk_tier
                              })
                            });
                            if (res.ok) {
                              notify.success('Action sent to Enterprise Approvals queue (/app/approvals)!');
                            }
                          } catch {
                            notify.error('Failed to submit approval');
                          }
                        }}
                        className="w-full h-7 bg-indigo-600 hover:bg-indigo-500 text-white text-[11px]"
                      >
                        Submit for Enterprise Approval
                      </Button>
                    )}
                  </div>
                )}
              </div>
            ))}
            {copilotLoading && (
              <div className="text-xs text-slate-400 flex items-center gap-2 italic">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                Specialist agent analyzing workforce data...
              </div>
            )}
          </div>

          {/* Drawer Input */}
          <div className="p-3 border-t border-slate-800 bg-slate-950/60 flex items-center gap-2">
            <Input
              placeholder="Ask anything across 16 HR submodules..."
              value={copilotInput}
              onChange={(e) => setCopilotInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendCopilot()}
              className="bg-slate-900 border-slate-800 text-xs text-white"
            />
            <Button
              onClick={handleSendCopilot}
              disabled={copilotLoading}
              className="bg-indigo-600 hover:bg-indigo-500 text-white h-9 px-3"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* ── MODAL: ADD EMPLOYEE ── */}
      {isAddEmployeeOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white">Add New Employee Profile</h3>
              <button onClick={() => setIsAddEmployeeOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreateEmployee} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400">First Name</label>
                  <Input value={newFirstName} onChange={(e) => setNewFirstName(e.target.value)} required className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
                </div>
                <div>
                  <label className="text-slate-400">Last Name</label>
                  <Input value={newLastName} onChange={(e) => setNewLastName(e.target.value)} required className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
                </div>
              </div>
              <div>
                <label className="text-slate-400">Work Email</label>
                <Input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} required className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
              </div>
              <div>
                <label className="text-slate-400">Job Title</label>
                <Input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} required placeholder="e.g., Staff Engineer" className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
              </div>
              <div>
                <label className="text-slate-400">Department</label>
                <Input value={newDept} onChange={(e) => setNewDept(e.target.value)} className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsAddEmployeeOpen(false)} className="border-slate-700 text-xs">
                  Cancel
                </Button>
                <Button type="submit" className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs">
                  Create Employee
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: SUBMIT LEAVE REQUEST ── */}
      {isLeaveModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white">Submit Leave Request</h3>
              <button onClick={() => setIsLeaveModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleSubmitLeave} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400">Employee</label>
                <select
                  value={selectedEmpForLeave}
                  onChange={(e) => setSelectedEmpForLeave(e.target.value)}
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-md p-2 text-white text-xs"
                >
                  {employees.map((emp) => (
                    <option key={emp.id} value={emp.id}>{emp.full_name} ({emp.job_title})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-slate-400">Days Requested</label>
                <Input type="number" min="1" max="30" value={leaveDays} onChange={(e) => setLeaveDays(e.target.value)} className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
              </div>
              <div>
                <label className="text-slate-400">Reason</label>
                <Input value={leaveReason} onChange={(e) => setLeaveReason(e.target.value)} className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
              </div>
              <div className="p-2.5 rounded bg-slate-800/60 border border-slate-700 text-[11px] text-amber-300 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400 flex-shrink-0" />
                <span>The Leave Impact Agent will automatically calculate team coverage upon submission.</span>
              </div>
              <div className="pt-2 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setIsLeaveModalOpen(false)} className="border-slate-700 text-xs">
                  Cancel
                </Button>
                <Button type="submit" disabled={submittingLeave} className="bg-amber-600 hover:bg-amber-500 text-white text-xs">
                  {submittingLeave ? 'Simulating...' : 'Submit Request'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

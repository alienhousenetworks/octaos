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
  Activity,
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
import HROperationsView from './hr-operations-view';

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
      content: 'Ask about people, hiring analytics, or time off. Command a task and I will run it in the HR flow: add someone, open a requisition, move a candidate, or complete pending workflow tasks.',
      agent: 'HR Orchestrator'
    }
  ]);

  // People Data State
  const [employees, setEmployees] = useState<any[]>([]);
  const [employeesLoading, setEmployeesLoading] = useState(false);
  const [employeesError, setEmployeesError] = useState<string | null>(null);
  const [employeeSearch, setEmployeeSearch] = useState('');
  const [isAddEmployeeOpen, setIsAddEmployeeOpen] = useState(false);
  const [newFirstName, setNewFirstName] = useState('');
  const [newLastName, setNewLastName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newDept, setNewDept] = useState('');

  // Workforce & Leave State
  const [leaves, setLeaves] = useState<any[]>([]);
  const [leavesLoading, setLeavesLoading] = useState(false);
  const [leavesError, setLeavesError] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState(false);
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [selectedEmpForLeave, setSelectedEmpForLeave] = useState('');
  const [leaveDays, setLeaveDays] = useState('');
  const [leaveReason, setLeaveReason] = useState('');
  const [submittingLeave, setSubmittingLeave] = useState(false);

  // Analytics State
  const [analytics, setAnalytics] = useState<any>(null);
  const [hiringRevision, setHiringRevision] = useState(0);

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
    setEmployeesError(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/people/employees`);
      if (res.ok) {
        const data = await res.json();
        if (!Array.isArray(data.items)) throw new Error('Employee API returned an unexpected response.');
        setEmployees(data.items);
        if (data.items?.length > 0 && !selectedEmpForLeave) {
          setSelectedEmpForLeave(data.items[0].id);
        }
      } else {
        setEmployeesError(`Employee directory unavailable (HTTP ${res.status}).`);
      }
    } catch (error) {
      setEmployeesError(error instanceof Error ? error.message : 'Employee directory unavailable.');
    } finally {
      setEmployeesLoading(false);
    }
  };

  const loadLeaves = async () => {
    setLeavesLoading(true);
    setLeavesError(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/workforce/leaves`);
      if (res.ok) {
        const data = await res.json();
        if (!Array.isArray(data)) throw new Error('Leave API returned an unexpected response.');
        setLeaves(data);
      } else {
        setLeavesError(`Time-off data unavailable (HTTP ${res.status}).`);
      }
    } catch (error) {
      setLeavesError(error instanceof Error ? error.message : 'Time-off data unavailable.');
    } finally {
      setLeavesLoading(false);
    }
  };

  const loadAnalytics = async () => {
    setAnalyticsError(false);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/people/analytics/summary`);
      if (res.ok) {
        setAnalytics(await res.json());
      } else {
        setAnalyticsError(true);
      }
    } catch {
      setAnalyticsError(true);
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
    const requestedDays = Number(leaveDays);
    if (!selectedEmpForLeave) {
      notify.error('Select an employee.');
      return;
    }
    if (!Number.isFinite(requestedDays) || requestedDays < 1 || requestedDays > 30) {
      notify.error('Enter a number of leave days between 1 and 30.');
      return;
    }
    if (!leaveReason.trim()) {
      notify.error('Enter a reason for the leave request.');
      return;
    }
    setSubmittingLeave(true);
    try {
      const startDate = new Date();
      startDate.setDate(startDate.getDate() + 7);
      const endDate = new Date(startDate);
      endDate.setDate(endDate.getDate() + Math.ceil(requestedDays) - 1);
      const start = startDate.toISOString().split('T')[0];
      const end = endDate.toISOString().split('T')[0];

      const res = await fetchWithAuth(`${API_URL}/hr/workforce/leaves`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: selectedEmpForLeave,
          leave_type_code: 'ANNUAL',
          start_date: start,
          end_date: end,
          days_requested: requestedDays,
          reason: leaveReason.trim()
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (typeof data.coverage_score === 'number' && Number.isFinite(data.coverage_score)) {
          notify.success(`Leave request submitted. Coverage assessment: ${Math.round(data.coverage_score * 100)}%.`);
        } else {
          notify.success('Leave request submitted. Coverage assessment was not returned by the API.');
        }
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

  const [activeCandidateId, setActiveCandidateId] = useState<string | null>(null);

  const handleAskCopilot = (message: string, resourceId?: string) => {
    if (resourceId) setActiveCandidateId(resourceId);
    setCopilotInput(message);
    setIsCopilotOpen(true);
    handleSendCopilot(message, resourceId);
  };

  const handleSendCopilot = async (overrideMsg?: string, overrideResourceId?: string) => {
    const rawMsg = overrideMsg !== undefined ? overrideMsg : copilotInput;
    if (!rawMsg.trim()) return;
    const msg = rawMsg.trim();
    if (overrideMsg === undefined) setCopilotInput('');
    setCopilotMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setCopilotLoading(true);

    const resourceIdToSend = overrideResourceId || activeCandidateId || (screen === 'leave' ? selectedEmpForLeave : undefined);

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
          resource_id: resourceIdToSend || undefined
        })
      });
      if (res.ok) {
        const data = await res.json();
        const action = data.task_result?.proposed_actions?.[0];
        setCopilotMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.reply || 'Ask HR returned an empty answer. Try a headcount, analytics, or a direct command.',
            agent: data.specialist_agent,
            action: action
          }
        ]);
        if (action?.executed) {
          loadEmployees();
          loadLeaves();
          loadAnalytics();
          setHiringRevision((revision) => revision + 1);
        }
      } else {
        let detail = 'Apologies, I encountered an error retrieving that workforce data.';
        try {
          const err = await res.json();
          if (typeof err.detail === 'string' && err.detail.trim()) detail = err.detail;
        } catch {
          // Keep the fallback sentence when the body is not JSON.
        }
        setCopilotMessages((prev) => [
          ...prev,
          { role: 'assistant', content: detail }
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
    <div className="min-w-0 space-y-6">
      <header className="overflow-hidden rounded-2xl border border-border bg-card">
        <div className="flex flex-col gap-5 px-5 py-6 sm:px-7 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
              <Users className="h-4 w-4" /> People &amp; HR
              <span className="h-1 w-1 rounded-full bg-border" />
              <span>Workforce workspace</span>
            </div>
            {screen === 'people' ? <>
              <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">Your people, in one place</h1>
              <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">A connected workspace for your employee directory, hiring pipeline, time off and everyday people operations.</p>
            </> : <p className="text-sm text-muted-foreground">Navigate between employee records, talent acquisition, time off and workforce operations.</p>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={() => { void loadEmployees(); void loadLeaves(); void loadAnalytics(); }} className="gap-2">
              <RefreshCw className="h-4 w-4" /> Refresh data
            </Button>
            <Button onClick={() => setIsCopilotOpen(true)} className="gap-2">
              <Sparkles className="h-4 w-4" /> Ask HR
              <span className="hidden rounded border border-primary-foreground/20 px-1.5 py-0.5 text-[10px] sm:inline">⌘J</span>
            </Button>
          </div>
        </div>
        <nav aria-label="People and HR sections" className="flex gap-1 overflow-x-auto border-t border-border px-3 py-2 sm:px-5">
          {([
            { id: 'people' as const, label: 'Directory', icon: Users, meta: employeesLoading ? 'Loading' : employeesError ? 'Unavailable' : String(employees.length) },
            { id: 'hiring' as const, label: 'Hiring', icon: Target, meta: 'ATS' },
            { id: 'leave' as const, label: 'Time off', icon: Calendar, meta: leavesLoading ? 'Loading' : leavesError ? 'Unavailable' : String(leaves.filter((l) => l.status === 'pending').length) },
            { id: 'operations' as const, label: 'Operations', icon: Shield, meta: 'HR' },
          ]).map((step) => {
            const active = screen === step.id;
            const Icon = step.icon;
            return <button key={step.id} aria-current={active ? 'page' : undefined} onClick={() => router.push(PEOPLE_ROUTES[step.id])} className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${active ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}>
              <Icon className="h-4 w-4" />{step.label}
              <span className={`rounded-md px-1.5 py-0.5 text-[11px] ${active ? 'bg-primary-foreground/15' : 'bg-muted'}`}>{step.meta}</span>
            </button>;
          })}
        </nav>
      </header>
      <div className="min-w-0 space-y-6">
        {/* ========================================================================= */}
        {/* CASE 1: TALENT MANAGEMENT -> RECRUITMENT (PRESERVED LIVE ATS ENGINE)      */}
        {/* ========================================================================= */}
        {screen === 'operations' && <HROperationsView API_URL={API_URL} fetchWithAuth={fetchWithAuth} />}

        {screen === 'hiring' && (
          <HRView
            token={token}
            API_URL={API_URL}
            fetchWithAuth={fetchWithAuth}
            fetchData={fetchData}
            initialRoomSlug={initialRoomSlug}
            dataRevision={hiringRevision}
            onAskCopilot={handleAskCopilot}
          />
        )}

        {/* ========================================================================= */}
        {/* CASE 2: PEOPLE MANAGEMENT -> EMPLOYEE DIRECTORY                           */}
        {/* ========================================================================= */}
        {screen === 'people' && (
          <div className="space-y-6">
            {(employeesError || leavesError || analyticsError) && <div role="status" className="flex flex-col gap-2 rounded-xl border border-amber-300/70 bg-amber-50/70 p-4 text-sm text-amber-950 sm:flex-row sm:items-center sm:justify-between dark:bg-amber-950/20 dark:text-amber-100">
              <div className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0"/><div><p className="font-medium">Some HR data could not be loaded</p><p className="mt-1 text-xs opacity-80">{[employeesError, leavesError, analyticsError ? 'Workforce analytics unavailable.' : null].filter(Boolean).join(' ')}</p></div></div>
              <Button size="sm" variant="outline" onClick={() => { void loadEmployees(); void loadLeaves(); void loadAnalytics(); }} className="shrink-0">Retry</Button>
            </div>}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { label: 'Employees in directory', value: employeesError ? '—' : employeesLoading ? '…' : employees.length, note: employeesError ? 'Source unavailable' : 'Records returned by HR', icon: Users },
                { label: 'Pending time off', value: leavesError ? '—' : leavesLoading ? '…' : leaves.filter((l) => l.status === 'pending').length, note: leavesError ? 'Source unavailable' : 'Requests awaiting review', icon: Calendar },
                { label: 'Active headcount', value: analyticsError ? '—' : analytics?.headcount?.total_active ?? '—', note: analyticsError ? 'Analytics unavailable' : 'From workforce analytics', icon: UserCheck },
                { label: 'Departments', value: employeesError ? '—' : new Set(employees.map((e) => e.department_name).filter(Boolean)).size, note: employeesError ? 'Source unavailable' : 'Distinct departments returned', icon: Building },
              ].map((metric) => { const Icon = metric.icon; return <Card key={metric.label} className="rounded-xl border-border shadow-none"><CardContent className="flex items-start justify-between gap-3 p-5"><div className="min-w-0"><p className="text-sm text-muted-foreground">{metric.label}</p><p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{metric.value}</p><p className="mt-1 text-xs text-muted-foreground">{metric.note}</p></div><span className="rounded-lg border border-border bg-muted/60 p-2.5"><Icon className="h-4 w-4 text-muted-foreground"/></span></CardContent></Card>; })}
            </div>
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(260px,0.7fr)]">
              <section className="min-w-0 overflow-hidden rounded-xl border border-border bg-card">
                <div className="flex flex-col gap-4 border-b border-border p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div><h2 className="text-base font-semibold">Employee directory</h2><p className="mt-1 text-sm text-muted-foreground">Search current employee records and open a hiring workflow when you need to grow the team.</p></div>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"/><Input aria-label="Search employees" placeholder="Name, title or department" value={employeeSearch} onChange={(e) => setEmployeeSearch(e.target.value)} className="w-full pl-9 sm:w-64"/></div>
                    <Button onClick={() => setIsAddEmployeeOpen(true)} className="gap-2"><Plus className="h-4 w-4"/>Add employee</Button>
                  </div>
                </div>
                {employeesError ? <div className="m-5 rounded-lg border border-dashed border-border p-8 text-center"><AlertTriangle className="mx-auto h-5 w-5 text-muted-foreground"/><p className="mt-3 text-sm font-medium">Directory unavailable</p><p className="mt-1 text-sm text-muted-foreground">The request failed. No employee count or empty-state claim is inferred.</p><Button className="mt-4" variant="outline" size="sm" onClick={() => void loadEmployees()}>Retry directory</Button></div>
                : employeesLoading ? <div className="space-y-3 p-5">{[1,2,3,4].map((n) => <div key={n} className="h-14 animate-pulse rounded-lg bg-muted/60"/>)}</div>
                : filteredEmployees.length === 0 ? <div className="p-10 text-center"><Users className="mx-auto h-6 w-6 text-muted-foreground"/><p className="mt-3 text-sm font-medium">{employeeSearch ? 'No matching employees' : 'No employee records returned'}</p><p className="mt-1 text-sm text-muted-foreground">{employeeSearch ? 'Try another name, role or department.' : 'Add an employee or verify the HR data source and your access.'}</p>{!employeeSearch && <Button className="mt-4" onClick={() => setIsAddEmployeeOpen(true)}><Plus className="mr-2 h-4 w-4"/>Add employee</Button>}</div>
                : <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-muted/40 text-xs text-muted-foreground"><tr><th className="px-5 py-3 font-medium">Employee</th><th className="px-4 py-3 font-medium">Department</th><th className="px-4 py-3 font-medium">Location</th><th className="px-4 py-3 font-medium">Employment</th><th className="px-5 py-3 text-right font-medium">Status</th></tr></thead><tbody>{filteredEmployees.map((emp) => <tr key={emp.id} className="border-t border-border transition-colors hover:bg-muted/20"><td className="px-5 py-3.5"><div className="flex items-center gap-3"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-semibold text-foreground">{[emp.first_name?.[0],emp.last_name?.[0]].filter(Boolean).join('').toUpperCase() || '—'}</div><div className="min-w-0"><p className="font-medium text-foreground">{emp.full_name || [emp.first_name,emp.last_name].filter(Boolean).join(' ') || 'Name unavailable'}</p><p className="mt-0.5 text-xs text-muted-foreground">{emp.job_title || 'Job title unavailable'}{emp.employee_number ? ` · ${emp.employee_number}` : ''}</p></div></div></td><td className="px-4 py-3.5 text-muted-foreground">{emp.department_name || '—'}</td><td className="px-4 py-3.5 text-muted-foreground">{emp.work_location || '—'}</td><td className="px-4 py-3.5 text-muted-foreground">{emp.employment_type || '—'}</td><td className="px-5 py-3.5 text-right"><span className="inline-flex rounded-full border border-border bg-muted/50 px-2.5 py-1 text-xs text-muted-foreground">{emp.status || 'Status unavailable'}</span></td></tr>)}</tbody></table></div>}
                {!employeesError && !employeesLoading && filteredEmployees.length > 0 && <div className="flex items-center justify-between border-t border-border px-5 py-3 text-xs text-muted-foreground"><span>Showing {filteredEmployees.length} of {employees.length} records</span><span>Live API data</span></div>}
              </section>
              <aside className="space-y-4">
                <section className="rounded-xl border border-border bg-card p-5"><div className="flex items-center gap-2"><Zap className="h-4 w-4 text-muted-foreground"/><h2 className="text-sm font-semibold">Workspaces</h2></div><p className="mt-1 text-sm text-muted-foreground">Go directly to the workflow you need.</p><div className="mt-4 space-y-2">
                  {[{id:'hiring' as const,title:'Talent acquisition',detail:'Candidates, interviews and hiring docs',icon:Target},{id:'leave' as const,title:'Time off & coverage',detail:'Leave requests and team impact',icon:Calendar},{id:'operations' as const,title:'People operations',detail:'Reviews, service desk and lifecycle',icon:Shield}].map((item) => {const Icon=item.icon;return <button key={item.id} onClick={() => router.push(PEOPLE_ROUTES[item.id])} className="flex w-full items-center gap-3 rounded-lg border border-border p-3 text-left transition-colors hover:bg-muted/50"><span className="rounded-md bg-muted p-2"><Icon className="h-4 w-4 text-muted-foreground"/></span><span className="min-w-0 flex-1"><span className="block text-sm font-medium">{item.title}</span><span className="mt-0.5 block text-xs leading-5 text-muted-foreground">{item.detail}</span></span><ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground"/></button>;})}
                </div></section>
                <section className="rounded-xl border border-border bg-card p-5"><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-muted-foreground"/><h2 className="text-sm font-semibold">Data quality</h2></div><p className="mt-1 text-sm text-muted-foreground">This page reports what connected HR endpoints return. Missing fields stay missing.</p><div className="mt-4 space-y-3 text-sm"><div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Employee directory</span><span className={employeesError?'text-amber-600':'text-foreground'}>{employeesError?'Unavailable':employeesLoading?'Loading':'Responding'}</span></div><div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Time-off data</span><span className={leavesError?'text-amber-600':'text-foreground'}>{leavesError?'Unavailable':leavesLoading?'Loading':'Responding'}</span></div><div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">Analytics</span><span className={analyticsError?'text-amber-600':'text-foreground'}>{analyticsError?'Unavailable':analytics?'Responding':'No data returned'}</span></div></div></section>
              </aside>
            </div>
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
                className="bg-primary hover:bg-primary/90 text-primary-foreground text-xs gap-1.5"
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
                        {typeof l.coverage_score === 'number' && Number.isFinite(l.coverage_score) ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-muted rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-full ${l.coverage_score >= 0.6 ? 'bg-emerald-600' : 'bg-rose-600'}`}
                                style={{ width: `${Math.max(0, Math.min(100, Math.round(l.coverage_score * 100)))}%` }}
                              />
                            </div>
                            <span className="text-[11px] font-semibold">{Math.round(l.coverage_score * 100)}%</span>
                          </div>
                        ) : <span className="text-xs text-muted-foreground">Unavailable</span>}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            l.status === 'approved'
                              ? 'bg-muted text-muted-foreground border border-border'
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
                <h3 className="text-sm font-semibold text-foreground">Universal HR Copilot</h3>
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
              <div className="text-xs text-muted-foreground flex items-center gap-2 italic">
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
              onClick={() => handleSendCopilot()}
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
                  <Input value={newFirstName} onChange={(e) => setNewFirstName(e.target.value)} required className="bg-background border-border text-foreground mt-1" />
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
                <label className="text-sm text-muted-foreground">Employee</label>
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
                <label className="text-sm text-muted-foreground">Days requested</label>
                <Input type="number" min="1" max="30" value={leaveDays} onChange={(e) => setLeaveDays(e.target.value)} className="bg-slate-800 border-slate-700 text-white mt-1 text-xs" />
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Reason</label>
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
                <Button type="submit" disabled={submittingLeave} className="text-xs">
                  {submittingLeave ? 'Submitting…' : 'Submit request'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

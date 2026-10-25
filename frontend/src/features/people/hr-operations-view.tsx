'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ArrowRight, BadgeCheck, CalendarClock, CheckCircle2, CircleAlert, ClipboardList, FileText, RefreshCw, ShieldCheck, Users, WalletCards } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';

type Tab = 'overview' | 'service' | 'performance' | 'compensation' | 'lifecycle';
type Employee = { id: string; full_name?: string; first_name?: string; last_name?: string; employee_number?: string; job_title?: string; status?: string };
type Row = Record<string, any>;

interface Props {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

const tabs: { id: Tab; label: string; description: string }[] = [
  { id: 'overview', label: 'Overview', description: 'People operations at a glance' },
  { id: 'service', label: 'Employee service desk', description: 'Requests, ownership and resolution' },
  { id: 'performance', label: 'Performance', description: 'Review cycles, goals and acknowledgement' },
  { id: 'compensation', label: 'Compensation', description: 'Governed proposals and independent approval' },
  { id: 'lifecycle', label: 'Lifecycle', description: 'Verified onboarding and offboarding tasks' },
];

function humanize(value: unknown) {
  return String(value ?? 'unknown').replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function Status({ value }: { value: unknown }) {
  const status = String(value ?? 'unknown').toLowerCase();
  const tone = ['approved', 'resolved', 'completed', 'acknowledged', 'active'].includes(status)
    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
    : ['rejected', 'blocked', 'failed', 'terminated'].includes(status)
      ? 'border-rose-200 bg-rose-50 text-rose-800'
      : 'border-amber-200 bg-amber-50 text-amber-800';
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${tone}`}>{humanize(status)}</span>;
}

function Empty({ title, detail }: { title: string; detail: string }) {
  return <div className="rounded-xl border border-dashed border-border bg-muted/20 px-6 py-12 text-center"><p className="text-sm font-semibold text-foreground">{title}</p><p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{detail}</p></div>;
}

export default function HROperationsView({ API_URL, fetchWithAuth }: Props) {
  const [tab, setTab] = useState<Tab>('overview');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [requests, setRequests] = useState<Row[]>([]);
  const [reviews, setReviews] = useState<Row[]>([]);
  const [proposals, setProposals] = useState<Row[]>([]);
  const [lifecycleEmployee, setLifecycleEmployee] = useState('');
  const [lifecycleType, setLifecycleType] = useState<'onboarding' | 'offboarding'>('onboarding');
  const [tasks, setTasks] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [requestEmployee, setRequestEmployee] = useState('');
  const [requestCategory, setRequestCategory] = useState('general');
  const [requestSubject, setRequestSubject] = useState('');
  const [requestDescription, setRequestDescription] = useState('');
  const [reviewEmployee, setReviewEmployee] = useState('');
  const [reviewCycle, setReviewCycle] = useState('Annual review');
  const [compEmployee, setCompEmployee] = useState('');
  const [compCurrency, setCompCurrency] = useState('INR');
  const [compCurrent, setCompCurrent] = useState('');
  const [compProposed, setCompProposed] = useState('');
  const [compReason, setCompReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [availability, setAvailability] = useState({ employees: false, requests: false, reviews: false, compensation: false });

  const call = useCallback(async (path: string, init?: RequestInit) => {
    const response = await fetchWithAuth(`${API_URL}${path}`, init);
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try { const body = await response.json(); if (typeof body.detail === 'string') message = body.detail; } catch {}
      throw new Error(message);
    }
    if (response.status === 204) return null;
    return response.json();
  }, [API_URL, fetchWithAuth]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const outcomes = await Promise.allSettled([
        call('/hr/people/employees?limit=200'),
        call('/hr/enterprise/service-requests?limit=100'),
        call('/hr/enterprise/performance-reviews'),
        call('/hr/enterprise/compensation/proposals'),
      ]);
      setAvailability({ employees: outcomes[0].status === 'fulfilled', requests: outcomes[1].status === 'fulfilled', reviews: outcomes[2].status === 'fulfilled', compensation: outcomes[3].status === 'fulfilled' });
      if (outcomes[0].status === 'fulfilled') setEmployees(outcomes[0].value?.items ?? []);
      if (outcomes[1].status === 'fulfilled') setRequests(Array.isArray(outcomes[1].value) ? outcomes[1].value : []);
      if (outcomes[2].status === 'fulfilled') setReviews(Array.isArray(outcomes[2].value) ? outcomes[2].value : []);
      if (outcomes[3].status === 'fulfilled') setProposals(Array.isArray(outcomes[3].value) ? outcomes[3].value : []);
      const failures = outcomes.filter((o) => o.status === 'rejected');
      if (failures.length === outcomes.length) setError('People operations data is unavailable. Check your access and API connection, then retry.');
      else if (failures.length) setError('Some panels could not be loaded. Unavailable panels are not represented as zero.');
    } catch {
      setError('People operations data is unavailable. Check your API connection, then retry.');
    } finally {
      setLoading(false);
    }
  }, [call]);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    const first = employees[0]?.id ?? '';
    if (first) {
      setRequestEmployee((current) => current || first);
      setReviewEmployee((current) => current || first);
      setCompEmployee((current) => current || first);
      setLifecycleEmployee((current) => current || first);
    }
  }, [employees]);

  const loadLifecycle = useCallback(async () => {
    if (!lifecycleEmployee) { setTasks([]); return; }
    try {
      const result = await call(`/hr/enterprise/lifecycle/${encodeURIComponent(lifecycleEmployee)}?lifecycle=${lifecycleType}`);
      setTasks(Array.isArray(result) ? result : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load lifecycle tasks.');
    }
  }, [call, lifecycleEmployee, lifecycleType]);

  useEffect(() => { void loadLifecycle(); }, [loadLifecycle]);

  const pendingRequests = useMemo(() => requests.filter((r) => !['resolved', 'closed'].includes(String(r.status))), [requests]);
  const pendingReviews = useMemo(() => reviews.filter((r) => ['draft', 'submitted'].includes(String(r.status))), [reviews]);
  const pendingComp = useMemo(() => proposals.filter((r) => r.status === 'pending_approval'), [proposals]);

  const submit = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true);
    try { await action(); notify.success(success); await refresh(); await loadLifecycle(); }
    catch (e) { notify.error(e instanceof Error ? e.message : 'The operation failed.'); }
    finally { setBusy(false); }
  };

  const createRequest = (e: React.FormEvent) => {
    e.preventDefault();
    void submit(() => call('/hr/enterprise/service-requests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ employee_id: requestEmployee, category: requestCategory, subject: requestSubject, description: requestDescription, priority: 'medium' }) }), 'Employee service request created.').then(() => { setRequestSubject(''); setRequestDescription(''); });
  };

  const createReview = (e: React.FormEvent) => {
    e.preventDefault();
    void submit(() => call('/hr/enterprise/performance-reviews', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ employee_id: reviewEmployee, cycle: reviewCycle, goals: [] }) }), 'Performance review draft created.');
  };

  const createComp = (e: React.FormEvent) => {
    e.preventDefault();
    void submit(() => call('/hr/enterprise/compensation/proposals', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ employee_id: compEmployee, currency: compCurrency, current_amount: compCurrent ? Number(compCurrent) : null, proposed_amount: Number(compProposed), reason: compReason }) }), 'Compensation proposal submitted for independent approval.');
  };

  const startLifecycle = () => void submit(async () => {
    await call('/hr/enterprise/lifecycle/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ employee_id: lifecycleEmployee, lifecycle: lifecycleType }) });
    await loadLifecycle();
  }, `${humanize(lifecycleType)} workflow started.`);

  const employeeLabel = (id: string) => {
    const employee = employees.find((e) => e.id === id);
    return employee?.full_name || [employee?.first_name, employee?.last_name].filter(Boolean).join(' ') || employee?.employee_number || id;
  };

  const stat = (label: string, value: number | string, detail: string, icon: React.ReactNode) => (
    <div className="rounded-xl border border-border bg-card p-5" key={label}>
      <div className="flex items-start justify-between"><div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div><span className="rounded-lg border border-border bg-muted/40 p-2.5 text-muted-foreground">{icon}</span></div>
    </div>
  );

  return <div className="mx-auto w-full max-w-[1440px] space-y-6 px-4 py-5 md:px-7">
    <header className="flex flex-col justify-between gap-4 border-b border-border pb-5 md:flex-row md:items-end">
      <div><div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground"><Users className="h-4 w-4" /> People operations</div><h1 className="text-3xl font-semibold tracking-tight text-foreground">Employee experience &amp; workforce governance</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">One workspace for employee requests, performance cycles, controlled compensation decisions and verified lifecycle work. Every action is sent to the governed API; unavailable data stays visible as unavailable.</p></div>
      <Button variant="outline" onClick={() => void refresh()} disabled={loading} className="gap-2 self-start md:self-auto"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh data</Button>
    </header>
    {error && <div role="status" className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span></div>}
    <nav aria-label="People operations sections" className="flex gap-1 overflow-x-auto rounded-xl border border-border bg-muted/30 p-1">
      {tabs.map((item) => <button key={item.id} onClick={() => setTab(item.id)} className={`shrink-0 rounded-lg px-4 py-2.5 text-left text-sm transition-colors ${tab === item.id ? 'bg-background font-semibold text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}><span className="block">{item.label}</span><span className="mt-0.5 hidden text-xs font-normal opacity-70 md:block">{item.description}</span></button>)}
    </nav>

    {tab === 'overview' && <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {stat('Active service requests', availability.requests ? pendingRequests.length : '—', 'Open, in progress or awaiting employee', <ClipboardList className="h-5 w-5" />)}
        {stat('Reviews in progress', availability.reviews ? pendingReviews.length : '—', 'Drafts awaiting submission or acknowledgement', <BadgeCheck className="h-5 w-5" />)}
        {stat('Compensation approvals', availability.compensation ? pendingComp.length : '—', 'Pending independent decision', <WalletCards className="h-5 w-5" />)}
        {stat('Lifecycle tasks', lifecycleEmployee ? tasks.filter((t) => t.status !== 'completed').length : '—', 'For selected employee and workflow', <Activity className="h-5 w-5" />)}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-xl border border-border bg-card p-5"><div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">Needs attention</h2><span className="text-xs text-muted-foreground">Live API records</span></div>{pendingRequests.slice(0, 4).map((r) => <div key={r.id} className="flex items-center justify-between gap-3 border-t border-border py-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{r.subject}</p><p className="mt-1 text-xs text-muted-foreground">{r.ticket_number} · {employeeLabel(r.employee_id)}</p></div><Status value={r.status} /></div>)}{pendingRequests.length === 0 && <Empty title={availability.requests ? 'No open service requests' : 'Service request data unavailable'} detail="Requests appear here after they are created and returned by the service API."/>}</section>
        <section className="rounded-xl border border-border bg-card p-5"><div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">Governed decisions</h2><ShieldCheck className="h-5 w-5 text-muted-foreground"/></div>{pendingComp.slice(0, 4).map((r) => <div key={r.id} className="flex items-center justify-between gap-3 border-t border-border py-3"><div className="min-w-0"><p className="truncate text-sm font-medium">{employeeLabel(r.employee_id)}</p><p className="mt-1 text-xs text-muted-foreground">{r.currency} {r.proposed_amount} · {r.reason}</p></div><Status value={r.status}/></div>)}{pendingComp.length === 0 && <Empty title={availability.compensation ? 'No pending compensation decisions' : 'Compensation data unavailable'} detail="This panel reflects proposals returned by the backend, not sample records."/>}</section>
      </div>
    </>}

    {tab === 'service' && <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.7fr)]">
      <section className="rounded-xl border border-border bg-card p-5"><h2 className="font-semibold">Employee service desk</h2><p className="mb-4 mt-1 text-sm text-muted-foreground">Track request ownership and status without leaving People &amp; HR.</p>{availability.requests && requests.length ? <div className="space-y-2">{requests.map((r) => <article key={r.id} className="rounded-lg border border-border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium">{r.subject}</p><p className="mt-1 text-xs text-muted-foreground">{r.ticket_number} · {employeeLabel(r.employee_id)} · {humanize(r.category)}</p></div><Status value={r.status}/></div><p className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">{r.description}</p><div className="mt-3 flex flex-wrap items-center justify-between gap-2"><span className="text-xs text-muted-foreground">Priority: {humanize(r.priority)}</span>{!['resolved','closed'].includes(r.status) && <Button size="sm" variant="outline" disabled={busy} onClick={() => void submit(() => call(`/hr/enterprise/service-requests/${r.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'in_progress' }) }), 'Request moved to in progress.')}>Start work</Button>}</div></article>)}</div> : <Empty title="No service requests returned" detail="Create a request or check that your role can view service desk records."/>}</section>
      <form onSubmit={createRequest} className="h-fit space-y-4 rounded-xl border border-border bg-card p-5"><div><h2 className="font-semibold">Create a request</h2><p className="mt-1 text-sm text-muted-foreground">The backend validates employee scope and request permissions.</p></div><label className="block text-sm">Employee<select required value={requestEmployee} onChange={(e) => setRequestEmployee(e.target.value)} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5">{employees.map((e) => <option key={e.id} value={e.id}>{employeeLabel(e.id)}</option>)}</select></label><label className="block text-sm">Category<select value={requestCategory} onChange={(e) => setRequestCategory(e.target.value)} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5">{['general','payroll','benefits','equipment','access','policy','leave'].map((v) => <option key={v} value={v}>{humanize(v)}</option>)}</select></label><label className="block text-sm">Subject<Input required minLength={3} value={requestSubject} onChange={(e) => setRequestSubject(e.target.value)} className="mt-1.5"/></label><label className="block text-sm">Description<textarea required minLength={3} value={requestDescription} onChange={(e) => setRequestDescription(e.target.value)} rows={4} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5"/></label><Button type="submit" disabled={busy || !requestEmployee} className="w-full">Create service request <ArrowRight className="ml-2 h-4 w-4"/></Button></form>
    </div>}

    {tab === 'performance' && <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.65fr)]">
      <section className="rounded-xl border border-border bg-card p-5"><h2 className="font-semibold">Review register</h2><p className="mb-4 mt-1 text-sm text-muted-foreground">Draft, submitted and acknowledged states come from the API.</p>{availability.reviews && reviews.length ? <div className="overflow-x-auto"><table className="w-full min-w-[540px] text-left text-sm"><thead className="text-xs text-muted-foreground"><tr><th className="pb-3 pr-3 font-medium">Employee</th><th className="pb-3 pr-3 font-medium">Cycle</th><th className="pb-3 pr-3 font-medium">Status</th><th className="pb-3 font-medium">Reviewer</th><th className="pb-3 font-medium">Action</th></tr></thead><tbody>{reviews.map((r) => <tr key={r.id} className="border-t border-border"><td className="py-3 pr-3">{employeeLabel(r.employee_id)}</td><td className="py-3 pr-3">{r.cycle}</td><td className="py-3 pr-3"><Status value={r.status}/></td><td className="py-3 pr-3 text-xs text-muted-foreground">{r.reviewer_user_id}</td><td className="py-3">{r.status === 'draft' && <Button size="sm" variant="outline" disabled={busy} onClick={() => { if (!window.confirm('Submit this review? Submitted reviews become immutable.')) return; void submit(() => call(`/hr/enterprise/performance-reviews/${r.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'submitted' }) }), 'Performance review submitted.'); }}>Submit</Button>}{r.status === 'submitted' && <Button size="sm" variant="outline" disabled={busy} onClick={() => { const comments = window.prompt('Employee acknowledgement comments (optional):'); if (comments === null) return; void submit(() => call(`/hr/enterprise/performance-reviews/${r.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ employee_comments: comments }) }), 'Acknowledgement submitted.'); }}>Acknowledge</Button>}</td></tr>)}</tbody></table></div> : <Empty title={availability.reviews ? 'No performance reviews returned' : 'Performance review data unavailable'} detail="Create a review draft when your role has the manage-performance permission."/>}</section>
      <form onSubmit={createReview} className="h-fit space-y-4 rounded-xl border border-border bg-card p-5"><h2 className="font-semibold">Start a review cycle</h2><label className="block text-sm">Employee<select required value={reviewEmployee} onChange={(e) => setReviewEmployee(e.target.value)} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5">{employees.map((e) => <option key={e.id} value={e.id}>{employeeLabel(e.id)}</option>)}</select></label><label className="block text-sm">Cycle name<Input required minLength={2} value={reviewCycle} onChange={(e) => setReviewCycle(e.target.value)} className="mt-1.5"/></label><Button type="submit" disabled={busy || !reviewEmployee} className="w-full">Create review draft</Button><p className="text-xs leading-5 text-muted-foreground">Creating a draft does not submit or acknowledge it. Review edits remain governed by backend permissions.</p></form>
    </div>}

    {tab === 'compensation' && <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.7fr)]">
      <section className="rounded-xl border border-border bg-card p-5"><h2 className="font-semibold">Compensation proposals</h2><p className="mb-4 mt-1 text-sm text-muted-foreground">Approval is a decision record; it does not change payroll.</p>{availability.compensation && proposals.length ? <div className="space-y-2">{proposals.map((p) => <article key={p.id} className="rounded-lg border border-border p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-medium">{employeeLabel(p.employee_id)}</p><p className="mt-1 text-sm text-muted-foreground">{p.currency} {p.current_amount ?? '—'} <ArrowRight className="inline h-3 w-3"/> {p.proposed_amount}</p></div><Status value={p.status}/></div><p className="mt-2 text-sm">{p.reason}</p>{p.status === 'pending_approval' && <div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="outline" disabled={busy} onClick={() => { const reason = window.prompt('Reason for approving this compensation proposal (minimum 5 characters):'); if (!reason || reason.trim().length < 5) return; void submit(() => call(`/hr/enterprise/compensation/proposals/${p.id}/decision`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision: 'approved', reason: reason.trim() }) }), 'Decision recorded. Payroll was not changed.'); }}>Approve proposal</Button><Button size="sm" variant="outline" disabled={busy} onClick={() => { const reason = window.prompt('Reason for rejecting this compensation proposal (minimum 5 characters):'); if (!reason || reason.trim().length < 5) return; void submit(() => call(`/hr/enterprise/compensation/proposals/${p.id}/decision`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision: 'rejected', reason: reason.trim() }) }), 'Decision recorded.'); }}>Reject proposal</Button></div>}</article>)}</div> : <Empty title={availability.compensation ? 'No compensation proposals returned' : 'Compensation data unavailable'} detail="Approval is a decision record; it does not change payroll."/>}</section>
      <form onSubmit={createComp} className="h-fit space-y-4 rounded-xl border border-border bg-card p-5"><h2 className="font-semibold">Propose a change</h2><label className="block text-sm">Employee<select required value={compEmployee} onChange={(e) => setCompEmployee(e.target.value)} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5">{employees.map((e) => <option key={e.id} value={e.id}>{employeeLabel(e.id)}</option>)}</select></label><div className="grid grid-cols-2 gap-3"><label className="block text-sm">Currency<Input required minLength={3} maxLength={3} value={compCurrency} onChange={(e) => setCompCurrency(e.target.value.toUpperCase())} className="mt-1.5"/></label><label className="block text-sm">Current amount<Input type="number" min="0" step="0.01" value={compCurrent} onChange={(e) => setCompCurrent(e.target.value)} className="mt-1.5"/></label></div><label className="block text-sm">Proposed amount<Input required type="number" min="0.01" step="0.01" value={compProposed} onChange={(e) => setCompProposed(e.target.value)} className="mt-1.5"/></label><label className="block text-sm">Business rationale<textarea required minLength={10} value={compReason} onChange={(e) => setCompReason(e.target.value)} rows={4} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5"/></label><Button type="submit" disabled={busy || !compEmployee} className="w-full">Submit for independent approval</Button></form>
    </div>}

    {tab === 'lifecycle' && <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.65fr)]">
      <section className="rounded-xl border border-border bg-card p-5"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">Lifecycle checklist</h2><p className="mt-1 text-sm text-muted-foreground">Completion of verification-required tasks needs a note.</p></div><Status value={lifecycleType}/></div>{tasks.length ? <div className="space-y-2">{tasks.map((task) => <article key={task.id} className="flex flex-col justify-between gap-3 rounded-lg border border-border p-4 sm:flex-row sm:items-center"><div><p className="font-medium">{task.title}</p><p className="mt-1 text-xs text-muted-foreground">{humanize(task.task_key)}{task.verification_required ? ' · Verification required' : ''}</p><div className="mt-2"><Status value={task.status}/></div></div>{task.status !== 'completed' && <Button size="sm" variant="outline" disabled={busy} onClick={() => { const note = task.verification_required ? window.prompt('Enter verification evidence note:') : null; if (task.verification_required && !note?.trim()) return; void submit(() => call(`/hr/enterprise/lifecycle/tasks/${task.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'completed', verification_note: note || undefined }) }), 'Lifecycle task completed with verification.'); }}>Mark completed</Button>}</article>)}</div> : <Empty title="No lifecycle tasks for this employee" detail="Choose a workflow and start it to create the governed checklist."/>}</section>
      <section className="h-fit space-y-4 rounded-xl border border-border bg-card p-5"><h2 className="font-semibold">Start lifecycle workflow</h2><label className="block text-sm">Employee<select required value={lifecycleEmployee} onChange={(e) => setLifecycleEmployee(e.target.value)} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5">{employees.map((e) => <option key={e.id} value={e.id}>{employeeLabel(e.id)}</option>)}</select></label><label className="block text-sm">Workflow<select value={lifecycleType} onChange={(e) => setLifecycleType(e.target.value as 'onboarding' | 'offboarding')} className="mt-1.5 w-full rounded-md border border-input bg-background px-3 py-2.5"><option value="onboarding">Onboarding</option><option value="offboarding">Offboarding</option></select></label><Button onClick={startLifecycle} disabled={busy || !lifecycleEmployee} className="w-full"><CalendarClock className="mr-2 h-4 w-4"/>Start workflow</Button><p className="text-xs leading-5 text-muted-foreground">The backend enforces employee status, tenant scope and lifecycle permissions. Offboarding should be used with the approved separation process.</p></section>
    </div>}
    <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4 text-xs text-muted-foreground"><span className="flex items-center gap-2"><ShieldCheck className="h-4 w-4"/> Governed API actions · tenant-scoped records · permission-checked writes</span><span>{loading ? 'Refreshing records…' : `Loaded employee records: ${employees.length}`}</span></footer>
  </div>;
}

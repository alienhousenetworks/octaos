'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { Activity, AlertTriangle, RefreshCw, Save, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';

type Attendance = {
  id: string; employee_id: string; employee_name: string; department?: string;
  work_date: string; timezone?: string; clock_in?: string | null; clock_out?: string | null;
  total_hours?: number | null; status?: string; anomaly_detected?: boolean; anomaly_type?: string | null;
};

interface Props {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

export default function HRWorkforceOperationsView({ API_URL, fetchWithAuth }: Props) {
  const [attendance, setAttendance] = useState<Attendance[]>([]);
  const [attendanceAvailable, setAttendanceAvailable] = useState(false);
  const [rulesAvailable, setRulesAvailable] = useState(false);
  const [rulesConfigured, setRulesConfigured] = useState(false);
  const [jurisdiction, setJurisdiction] = useState('');
  const [minimumRest, setMinimumRest] = useState('');
  const [maximumShift, setMaximumShift] = useState('');
  const [maximumWeek, setMaximumWeek] = useState('');
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const request = useCallback(async (path: string, init?: RequestInit) => {
    const response = await fetchWithAuth(`${API_URL}${path}`, init);
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
      try { const body = await response.json(); if (typeof body.detail === 'string') message = body.detail; } catch {}
      throw new Error(message);
    }
    return response.json();
  }, [API_URL, fetchWithAuth]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    const suffix = date ? `?date=${encodeURIComponent(date)}` : '';
    const results = await Promise.allSettled([
      request(`/hr/workforce/attendance${suffix}`),
      request('/hr/workforce/labor-rules'),
    ]);
    setAttendanceAvailable(results[0].status === 'fulfilled');
    setRulesAvailable(results[1].status === 'fulfilled');
    if (results[0].status === 'fulfilled') setAttendance(Array.isArray(results[0].value) ? results[0].value : []);
    if (results[1].status === 'fulfilled') {
      const rules = results[1].value;
      setRulesConfigured(Boolean(rules.configured));
      setJurisdiction(rules.jurisdiction ?? '');
      setMinimumRest(rules.minimum_rest_hours == null ? '' : String(rules.minimum_rest_hours));
      setMaximumShift(rules.maximum_shift_hours == null ? '' : String(rules.maximum_shift_hours));
      setMaximumWeek(rules.maximum_weekly_hours == null ? '' : String(rules.maximum_weekly_hours));
    }
    const failures = results.filter((item) => item.status === 'rejected');
    if (failures.length === results.length) setError('Attendance and labor-rule APIs are unavailable or your role lacks workforce-management permission.');
    else if (failures.length) setError('Some workforce data is unavailable. Missing values are not inferred.');
    setLoading(false);
  }, [date, request]);

  useEffect(() => { void refresh(); }, [refresh]);

  const saveRules = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!jurisdiction.trim()) { notify.error('Enter the policy jurisdiction or scope.'); return; }
    if (![minimumRest, maximumShift, maximumWeek].some((value) => value.trim() !== '')) {
      notify.error('Configure at least one labor limit. Empty policies are not saved.');
      return;
    }
    setSaving(true);
    try {
      await request('/hr/workforce/labor-rules', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jurisdiction: jurisdiction.trim(),
          minimum_rest_hours: minimumRest === '' ? null : Number(minimumRest),
          maximum_shift_hours: maximumShift === '' ? null : Number(maximumShift),
          maximum_weekly_hours: maximumWeek === '' ? null : Number(maximumWeek),
        }),
      });
      notify.success('Labor limits saved. Scheduling will enforce configured limits only.');
      await refresh();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : 'Could not save labor limits.');
    } finally {
      setSaving(false);
    }
  };

  const card = 'rounded-xl border border-border bg-card p-5';
  return <div className="space-y-5">
    {error && <div role="status" className="flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950"><AlertTriangle className="h-4 w-4 shrink-0"/>{error}</div>}
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <section className={card}>
        <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><Activity className="h-5 w-5 text-muted-foreground"/><h2 className="font-semibold">Attendance register</h2></div><p className="mt-1 text-sm text-muted-foreground">Clock times are displayed in the recorded employee timezone when available.</p></div><Button variant="outline" size="sm" onClick={() => void refresh()} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`}/>Refresh</Button></div>
        <div className="my-4 flex flex-wrap items-end gap-3"><label className="text-sm">Work date (optional)<Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="mt-1.5 w-48"/></label><Button variant="outline" onClick={() => void refresh()} disabled={loading}>Apply filter</Button>{date && <Button variant="ghost" onClick={() => setDate('')}>Clear</Button>}</div>
        {!attendanceAvailable ? <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">Attendance data unavailable. Check workforce permission and API connectivity.</div> : attendance.length === 0 ? <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No attendance records returned for this filter.</div> : <div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead className="text-xs text-muted-foreground"><tr><th className="pb-3 pr-3 font-medium">Employee</th><th className="pb-3 pr-3 font-medium">Work date</th><th className="pb-3 pr-3 font-medium">Clock in / out</th><th className="pb-3 pr-3 font-medium">Hours</th><th className="pb-3 font-medium">Review</th></tr></thead><tbody>{attendance.map((row) => <tr key={row.id} className="border-t border-border"><td className="py-3 pr-3"><p className="font-medium">{row.employee_name}</p><p className="text-xs text-muted-foreground">{row.department || 'Department unavailable'}</p></td><td className="py-3 pr-3">{row.work_date}<p className="text-xs text-muted-foreground">{row.timezone || 'Timezone unavailable'}</p></td><td className="py-3 pr-3">{row.clock_in || '—'} / {row.clock_out || '—'}</td><td className="py-3 pr-3">{typeof row.total_hours === 'number' ? row.total_hours.toFixed(2) : '—'}</td><td className="py-3">{row.anomaly_detected ? <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">{row.anomaly_type || 'Anomaly flagged'}</span> : <span className="text-xs text-muted-foreground">{row.status || 'No status returned'}</span>}</td></tr>)}</tbody></table></div>}
      </section>
      <form onSubmit={saveRules} className={`${card} space-y-4`}>
        <div><div className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-muted-foreground"/><h2 className="font-semibold">Labor limits &amp; policy scope</h2></div><p className="mt-1 text-sm text-muted-foreground">Limits are tenant-configured. The system does not guess local labor law or certify legal compliance.</p></div>
        {rulesAvailable ? rulesConfigured ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-900">Configured limits are used by the roster optimizer where supported.</p> : <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950">No labor limits configured. Labor compliance is not evaluated.</p> : <p className="text-sm text-muted-foreground">Labor rules unavailable; your role may not have workforce-management access.</p>}
        <label className="block text-sm">Jurisdiction / policy scope<Input required value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} placeholder="e.g. India — West Bengal office" className="mt-1.5"/></label>
        <label className="block text-sm">Minimum rest between shifts (hours)<Input type="number" min="0" max="24" step="0.25" value={minimumRest} onChange={(e) => setMinimumRest(e.target.value)} placeholder="Not configured" className="mt-1.5"/></label>
        <label className="block text-sm">Maximum shift length (hours)<Input type="number" min="0.01" max="24" step="0.25" value={maximumShift} onChange={(e) => setMaximumShift(e.target.value)} placeholder="Not configured" className="mt-1.5"/></label>
        <label className="block text-sm">Maximum weekly hours<Input type="number" min="0.01" max="168" step="0.25" value={maximumWeek} onChange={(e) => setMaximumWeek(e.target.value)} placeholder="Not configured" className="mt-1.5"/></label>
        <Button type="submit" disabled={saving || !rulesAvailable} className="w-full"><Save className="mr-2 h-4 w-4"/>{saving ? 'Saving…' : 'Save labor limits'}</Button>
        <p className="text-xs leading-5 text-muted-foreground">Changing this configuration affects future scheduling checks. Have HR/legal owners validate the values before use.</p>
      </form>
    </div>
  </div>;
}

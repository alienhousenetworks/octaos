'use client';

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type Requisition = { id: string; title: string; status: string; headcount_approved: number; headcount_filled: number };
type ApplicationRow = { id: string; name: string | null; title: string | null; current_stage: string; status: string };

const STAGES = ['sourced', 'screened', 'interviewing', 'offer', 'hired', 'rejected'];

export default function HRPipelinePanel({
  API_URL,
  fetchWithAuth,
}: {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}) {
  const [title, setTitle] = useState('Software Engineer');
  const [requisitions, setRequisitions] = useState<Requisition[]>([]);
  const [applications, setApplications] = useState<ApplicationRow[]>([]);
  const [metric, setMetric] = useState<any>(null);
  const [message, setMessage] = useState('');

  async function reload() {
    const [reqRes, appRes, metricRes] = await Promise.all([
      fetchWithAuth(`${API_URL}/hr/requisitions`),
      fetchWithAuth(`${API_URL}/hr/applications`),
      fetchWithAuth(`${API_URL}/hr/analytics?metric=time_to_fill`),
    ]);
    if (reqRes.ok) setRequisitions(await reqRes.json());
    if (appRes.ok) setApplications(await appRes.json());
    if (metricRes.ok) setMetric(await metricRes.json());
  }

  useEffect(() => {
    reload().catch(() => setMessage('Pipeline data is not available yet.'));
  }, []);

  async function createRequisition() {
    const res = await fetchWithAuth(`${API_URL}/hr/requisitions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) {
      setMessage('Could not create the requisition.');
      return;
    }
    const created = await res.json();
    await fetchWithAuth(`${API_URL}/hr/requisitions/${created.id}/open`, { method: 'POST' });
    setMessage(`Opened ${created.title}.`);
    await reload();
  }

  async function move(id: string, to_stage: string) {
    const res = await fetchWithAuth(`${API_URL}/hr/applications/${id}/transition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ to_stage }),
    });
    if (!res.ok) {
      setMessage('That stage change is not allowed from here.');
      return;
    }
    await reload();
  }

  return (
    <div className="space-y-4">
      <Card className="bg-gray-950 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white text-base">Requisitions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-center">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} className="bg-gray-900 border-gray-800 text-white" />
          <Button onClick={createRequisition} className="bg-amber-500 text-black hover:bg-amber-600">Open requisition</Button>
          {message && <p className="text-xs text-gray-400">{message}</p>}
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-3">
        {requisitions.map((row) => (
          <Card key={row.id} className="bg-gray-950 border-gray-800">
            <CardContent className="pt-4 text-sm text-gray-200">
              <p className="font-medium text-white">{row.title}</p>
              <p className="text-gray-400">{row.status} · {row.headcount_filled}/{row.headcount_approved} filled</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-gray-950 border-gray-800">
        <CardHeader>
          <CardTitle className="text-white text-base">Time to fill</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-gray-300">
          {metric?.status === 'insufficient_data'
            ? 'Insufficient data. Confirm when the requisition actually opened before this number is shown.'
            : metric?.status === 'ok'
              ? `${metric.value} ${metric.unit}`
              : 'No metric yet.'}
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {STAGES.map((stage) => (
          <div key={stage} className="rounded-xl border border-gray-800 bg-gray-950 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">{stage}</p>
            {applications.filter((row) => row.current_stage === stage).map((row) => (
              <div key={row.id} className="mb-2 rounded-lg border border-gray-800 p-2 text-xs text-gray-200">
                <p className="text-white">{row.name || 'Candidate'}</p>
                <p className="text-gray-500">{row.title}</p>
                {stage === 'sourced' && (
                  <Button size="sm" variant="outline" className="mt-2 h-7 text-[11px]" onClick={() => move(row.id, 'screened')}>
                    Move to screened
                  </Button>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

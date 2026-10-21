'use client';

import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Lock, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { CopilotAdvice, SalesTerminology, SHARED_TERMS } from './sales-platform';
import { Lead } from './sales-types';

interface SalesRecordWorkspaceProps {
  lead: Lead;
  terms: SalesTerminology;
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  actionLoading: boolean;
  onBack: () => void;
  onSave: (leadId: string, updates: Partial<Lead>) => Promise<void>;
  onUpdateStatus: (leadId: string, status: string) => Promise<void>;
  onGenerateDraft: (leadId: string, instructions: string) => Promise<{ subject: string; body: string } | null>;
  onBookMeeting: (leadId: string) => Promise<void>;
  onOpenDealDesk: () => void;
  onLogNote: (leadId: string, content: string, channel: string, direction: string) => Promise<void>;
  onSendDraft: (leadId: string, subject: string, body: string) => Promise<void>;
  onDelete: (leadId: string) => Promise<void>;
}

type Pane = 'contact' | 'record' | 'copilot';
type Tab = 'overview' | 'activity' | 'sales' | 'history';

export default function SalesRecordWorkspace({
  lead,
  terms,
  API_URL,
  fetchWithAuth,
  actionLoading,
  onBack,
  onSave,
  onUpdateStatus,
  onGenerateDraft,
  onBookMeeting,
  onOpenDealDesk,
  onLogNote,
  onSendDraft,
  onDelete,
}: SalesRecordWorkspaceProps) {
  const [pane, setPane] = useState<Pane>('record');
  const [tab, setTab] = useState<Tab>('overview');
  const [advice, setAdvice] = useState<CopilotAdvice | null>(null);
  const [copilotError, setCopilotError] = useState<string | null>(null);
  const [copilotLoading, setCopilotLoading] = useState(false);
  const [question, setQuestion] = useState('What should we do next with this customer?');
  const [name, setName] = useState(lead.name || '');
  const [company, setCompany] = useState(lead.company || '');
  const [email, setEmail] = useState(lead.email || '');
  const [phone, setPhone] = useState(lead.phone || '');
  const [why, setWhy] = useState(lead.why || '');
  const [note, setNote] = useState('');
  const [confirmMeeting, setConfirmMeeting] = useState(false);
  const [confirmSend, setConfirmSend] = useState(false);
  const [draftPreview, setDraftPreview] = useState<{ subject: string; body: string } | null>(
    lead.data?.draft_subject || lead.data?.draft_body
      ? { subject: lead.data?.draft_subject || '', body: lead.data?.draft_body || '' }
      : null
  );

  useEffect(() => {
    setName(lead.name || '');
    setCompany(lead.company || '');
    setEmail(lead.email || '');
    setPhone(lead.phone || '');
    setWhy(lead.why || '');
    setConfirmMeeting(false);
    setDraftPreview(
      lead.data?.draft_subject || lead.data?.draft_body
        ? { subject: lead.data?.draft_subject || '', body: lead.data?.draft_body || '' }
        : null
    );
  }, [lead.id, lead.name, lead.company, lead.email, lead.phone, lead.why, lead.data?.draft_subject, lead.data?.draft_body]);

  const ask = async (text: string) => {
    setCopilotLoading(true);
    setCopilotError(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/sales-os/copilot/record`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead_id: lead.id, question: text }),
      });
      if (!res.ok) {
        setAdvice(null);
        setCopilotError(res.status === 404 ? 'This record is not in the current workspace.' : 'The copilot is unavailable. No recommendation was invented.');
        return;
      }
      setAdvice(await res.json());
    } catch {
      setAdvice(null);
      setCopilotError('The copilot is unavailable. No recommendation was invented.');
    } finally {
      setCopilotLoading(false);
    }
  };

  useEffect(() => {
    void ask('What should we do next with this customer?');
    // Reload when the open record changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lead.id]);

  const labels = advice?.terminology || terms || SHARED_TERMS;
  const conversation = Array.isArray(lead.data?.conversation) ? lead.data.conversation : [];
  const title = `${lead.name || 'Unnamed record'}${lead.company ? ` · ${lead.company}` : ''}`;

  const runAction = async (id: string) => {
    if (id === 'review_follow_up') {
      setTab('sales');
      setPane('record');
      if (!draftPreview?.body) {
        const draft = await onGenerateDraft(lead.id, 'Draft a follow-up from stored facts only. Do not invent metrics.');
        if (draft) setDraftPreview(draft);
      }
      return;
    }
    if (id === 'prepare_proposal') {
      onOpenDealDesk();
      return;
    }
    if (id === 'schedule_meeting') {
      setConfirmMeeting(true);
      setPane('copilot');
    }
  };

  return (
    <div className="space-y-3">
      <header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <button type="button" onClick={onBack} className="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft size={14} /> Back to {labels.leads.toLowerCase()}
          </button>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            {[lead.status || 'No status', lead.source || 'No source', lead.priority || 'No priority'].join(' · ')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            onClick={() => onSave(lead.id, { name, company, email, phone, why })}
            disabled={actionLoading}
          >
            {actionLoading ? <Loader2 className="animate-spin" size={14} /> : <Lock size={14} />} Save
          </Button>
          <Button type="button" variant="outline" disabled={actionLoading} onClick={() => void onDelete(lead.id)}>
            Delete
          </Button>
        </div>
      </header>

      <div className="flex gap-2 xl:hidden">
        {(['contact', 'record', 'copilot'] as Pane[]).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setPane(item)}
            className={`rounded-full px-3 py-1 text-xs font-medium ${pane === item ? 'bg-primary text-primary-foreground' : 'border border-border text-muted-foreground'}`}
          >
            {item === 'contact' ? 'Contact' : item === 'record' ? 'Record' : 'Copilot'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
        <aside className={`${pane === 'contact' ? 'block' : 'hidden'} space-y-3 xl:block`}>
          <Panel>
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-border text-lg">
                {(lead.name || '?').slice(0, 1).toUpperCase()}
              </div>
              <h2 className="mt-2 font-semibold">Contact card</h2>
              <p className="text-xs text-muted-foreground">Details and channels</p>
            </div>
            <Field label="Name" value={name} onChange={setName} />
            <Field label="Company" value={company} onChange={setCompany} />
            <Field label="Email" value={email} onChange={setEmail} />
            <Field label="Phone" value={phone} onChange={setPhone} />
          </Panel>
          <Panel>
            <h2 className="font-semibold">Next-best action</h2>
            <p className="text-sm text-muted-foreground">{advice?.recommendation || 'Ask the copilot. Nothing runs until you confirm.'}</p>
          </Panel>
          <Panel>
            <h2 className="font-semibold">Enrichment</h2>
            <p className="text-sm text-muted-foreground">
              {lead.data?.evidence_url || lead.evidence_url
                ? `Source URL stored: ${lead.data?.evidence_url || lead.evidence_url}`
                : 'No enrichment source is stored on this record.'}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {lead.freshness?.freshness_label
                ? `Freshness label stored: ${lead.freshness.freshness_label}`
                : 'No freshness label is stored.'}
            </p>
          </Panel>
        </aside>

        <section className={`${pane === 'record' ? 'block' : 'hidden'} space-y-3 xl:block`}>
          <div className="flex flex-wrap gap-2">
            {(['overview', 'activity', 'sales', 'history'] as Tab[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setTab(item)}
                className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${tab === item ? 'bg-[#2563eb] text-white' : 'bg-muted text-muted-foreground'}`}
              >
                {item}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Metric
              title={advice?.readiness.label || 'Readiness'}
              value={advice?.readiness.value || '—'}
              note={advice?.readiness.note || 'Waiting for the copilot.'}
            />
            <Metric
              title={advice?.deal_health.label || 'Deal health'}
              value={advice?.deal_health.value || '—'}
              note={advice?.deal_health.note || 'Status comes from the record.'}
            />
          </div>
          {tab === 'overview' ? (
            <Panel>
              <h2 className="font-semibold">{labels.account} / {labels.opportunity} details</h2>
              <label className="mt-3 block text-xs text-muted-foreground">Why this record</label>
              <Textarea value={why} onChange={(event) => setWhy(event.target.value)} className="mt-1" />
              <label className="mt-3 block text-xs text-muted-foreground">Status</label>
              <select
                className="mt-1 w-full rounded-md border border-border bg-background px-2 py-2 text-sm"
                value={lead.status || 'new'}
                onChange={(event) => void onUpdateStatus(lead.id, event.target.value)}
              >
                {['new', 'qualified', 'contacted', 'meeting_scheduled', 'closed_won', 'closed_lost'].map((status) => (
                  <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>
                ))}
              </select>
            </Panel>
          ) : null}
          {tab === 'activity' ? (
            <Panel>
              <h2 className="font-semibold">Engagement timeline</h2>
              <p className="text-xs text-muted-foreground">Calls, emails, meetings, tasks, and notes stored on this record.</p>
              {conversation.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No activity is stored.</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {conversation.map((item: any, index: number) => (
                    <li key={`${item.at || index}`} className="rounded-lg border border-border px-3 py-2 text-sm">
                      <div className="text-xs text-muted-foreground">{[item.channel, item.direction, item.at].filter(Boolean).join(' · ')}</div>
                      <p className="mt-1">{item.content || item.subject || 'Empty note'}</p>
                    </li>
                  ))}
                </ul>
              )}
              <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add an internal note" className="mt-3" />
              <Button
                type="button"
                variant="secondary"
                className="mt-2"
                disabled={!note.trim() || actionLoading}
                onClick={async () => {
                  await onLogNote(lead.id, note, 'note', 'internal');
                  setNote('');
                }}
              >
                Save note
              </Button>
            </Panel>
          ) : null}
          {tab === 'sales' ? (
            <Panel>
              <h2 className="font-semibold">Follow-up draft</h2>
              <p className="text-xs text-muted-foreground">A draft is not a sent message. Sending stays on the existing outreach action.</p>
              {draftPreview ? (
                <div className="mt-3 rounded-lg border border-border p-3 text-sm">
                  <p className="font-medium">{draftPreview.subject || 'No subject stored'}</p>
                  <p className="mt-2 whitespace-pre-wrap text-muted-foreground">{draftPreview.body || 'No body stored'}</p>
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">No draft is stored.</p>
              )}
              {draftPreview?.body ? (
                <div className="mt-3">
                  {confirmSend ? (
                    <Button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => void onSendDraft(lead.id, draftPreview.subject, draftPreview.body)}
                    >
                      Confirm send
                    </Button>
                  ) : (
                    <Button type="button" variant="secondary" onClick={() => setConfirmSend(true)}>
                      Prepare to send
                    </Button>
                  )}
                </div>
              ) : null}
            </Panel>
          ) : null}
          {tab === 'history' ? (
            <Panel>
              <h2 className="font-semibold">History</h2>
              <dl className="mt-2 space-y-1 text-sm">
                <Row label="Record id" value={lead.id} />
                <Row label="Created" value={lead.created_at || 'Not stored'} />
                <Row label="Updated" value={lead.updated_at || 'Not stored'} />
                <Row label="Score source" value={advice?.readiness.source || 'lead.score'} />
              </dl>
            </Panel>
          ) : null}
        </section>

        <aside className={`${pane === 'copilot' ? 'block' : 'hidden'} xl:block`} aria-label="OctaOS Copilot">
          <div className="flex h-full flex-col rounded-2xl border border-border bg-card p-4">
            <h2 className="font-semibold">OctaOS Copilot</h2>
            <p className="text-xs text-muted-foreground">{labels.lead} · {lead.company || 'No company'}</p>
            <div className="mt-3 flex-1 space-y-3">
              {copilotLoading ? <p className="text-sm text-muted-foreground">Reading the stored record…</p> : null}
              {copilotError ? <p className="text-sm text-destructive">{copilotError}</p> : null}
              {advice ? (
                <>
                  <p className="text-sm">{advice.answer}</p>
                  <div className="rounded-xl border border-border p-3">
                    <h3 className="text-sm font-semibold">Recommendation</h3>
                    <p className="mt-1 text-sm text-muted-foreground">{advice.recommendation}</p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Confidence {advice.confidence}. {advice.confidence_basis}
                    </p>
                  </div>
                  <div className="space-y-2">
                    {advice.actions.map((action) => (
                      <button
                        key={action.id}
                        type="button"
                        onClick={() => void runAction(action.id)}
                        className="block w-full rounded-xl border border-border px-3 py-2 text-left text-sm font-medium hover:border-primary/40"
                      >
                        {action.label}
                        <span className="mt-0.5 block text-xs font-normal text-muted-foreground">{action.preview}</span>
                      </button>
                    ))}
                  </div>
                  {confirmMeeting ? (
                    <div className="rounded-xl border border-border p-3">
                      <p className="text-sm">Book a meeting through the existing meeting service?</p>
                      <Button type="button" className="mt-2" disabled={actionLoading} onClick={() => void onBookMeeting(lead.id)}>
                        Confirm booking
                      </Button>
                    </div>
                  ) : null}
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence</h3>
                    <ul className="mt-1 space-y-1">
                      {advice.evidence.length === 0 ? <li className="text-xs text-muted-foreground">No stored facts to cite.</li> : null}
                      {advice.evidence.map((item) => (
                        <li key={item.claim} className="text-xs text-muted-foreground">
                          {item.claim} <span className="text-foreground/70">({item.verification_status}, {item.source})</span>
                        </li>
                      ))}
                    </ul>
                    {advice.unknowns.length > 0 ? (
                      <p className="mt-2 text-xs text-muted-foreground">Unknown: {advice.unknowns.slice(0, 6).join(' · ')}</p>
                    ) : null}
                  </div>
                </>
              ) : null}
            </div>
            <form
              className="mt-3 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (question.trim()) void ask(question.trim());
              }}
            >
              <Input
                aria-label="Ask about this record"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about this record…"
              />
              <Button type="submit" size="icon" aria-label="Ask" disabled={copilotLoading}>
                <Send size={14} />
              </Button>
            </form>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Panel({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-border bg-card p-4">{children}</div>;
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="mt-3 block text-xs text-muted-foreground">
      {label}
      <Input className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Metric({ title, value, note }: { title: string; value: string; note: string }) {
  return (
    <div className="rounded-2xl bg-[#2563eb] p-4 text-white">
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
      <p className="mt-2 text-xs text-blue-100">{note}</p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}

'use client';

import React, { useState } from 'react';
import { ShieldAlert, Check, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ApprovalRequiredData {
  approval_id: string;
  checkpoint_id: string;
  tool: string;
  args: Record<string, any>;
  policy_reason?: string;
}

interface LiveApprovalCardProps {
  data: ApprovalRequiredData;
  apiUrl: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onResolved: (result: { status: 'approved' | 'rejected'; details?: any }) => void;
}

export default function LiveApprovalCard({
  data,
  apiUrl,
  fetchWithAuth,
  onResolved,
}: LiveApprovalCardProps) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleAction = async (action: 'approve' | 'reject') => {
    setSubmitting(true);
    setError('');

    try {
      const res = await fetchWithAuth(
        `${apiUrl}/agents/approvals/${encodeURIComponent(data.approval_id)}/resume`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action,
            reason: action === 'reject' ? 'User rejected via AI Studio' : undefined,
          }),
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || `Approval action failed (${res.status})`);
      }

      const body = await res.json();
      onResolved({
        status: action === 'approve' ? 'approved' : 'rejected',
        details: body,
      });
    } catch (err: any) {
      setError(err?.message || 'Failed to submit approval.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="my-3 rounded-xl border border-amber-500/30 bg-[#191610] p-4 text-xs text-white/90 shadow-lg transition">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-amber-500/20 text-amber-400">
            <ShieldAlert className="size-4" />
          </div>
          <div>
            <h4 className="font-semibold text-amber-200">
              Approval Gate: <span className="font-mono text-white">{data.tool}</span>
            </h4>
            <p className="text-[11px] text-white/50">
              {data.policy_reason || 'This action modifies live resources and requires operator sign-off.'}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-2.5 rounded-lg border border-white/[0.06] bg-[#0f0e0b] p-3 font-mono text-[11px]">
        <div className="mb-1.5">
          <span className="text-[10px] uppercase font-semibold text-white/40">Approved parameters</span>
        </div>
        <pre className="overflow-x-auto text-white/70 whitespace-pre-wrap">
          {JSON.stringify(data.args, null, 2)}
        </pre>
      </div>

      {error && (
        <div className="mt-2 text-rose-400 text-[11px]">
          {error}
        </div>
      )}

      <div className="mt-3.5 flex items-center justify-end gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={submitting}
          onClick={() => handleAction('reject')}
          className="border-white/10 text-white/70 hover:bg-white/[0.06] hover:text-white text-xs h-8"
        >
          <X className="size-3.5 mr-1 text-rose-400" />
          Reject
        </Button>
        <Button
          type="button"
          size="sm"
          disabled={submitting}
          onClick={() => handleAction('approve')}
          className="bg-[#7de56b] text-black font-semibold hover:bg-[#68d356] text-xs h-8"
        >
          {submitting ? (
            <>
              <Loader2 className="size-3.5 mr-1 animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <Check className="size-3.5 mr-1" />
              Approve & Execute Now
            </>
          )}
        </Button>
      </div>
    </div>
  );
}


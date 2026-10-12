'use client';

import React, { useEffect, useState } from 'react';
import { CheckCircle2, Info, AlertTriangle, XCircle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  registerConfirm,
  subscribeToasts,
  type ConfirmRequest,
  type ToastItem,
} from '@/lib/notify';

export default function Providers({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [confirm, setConfirm] = useState<ConfirmRequest | null>(null);

  useEffect(() => {
    return subscribeToasts((item) => {
      setToasts((current) => [...current, item].slice(-4));
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== item.id));
      }, 4800);
    });
  }, []);

  useEffect(() => {
    registerConfirm((request) => setConfirm(request));
    return () => registerConfirm(null);
  }, []);

  const closeConfirm = (value: boolean) => {
    confirm?.resolve(value);
    setConfirm(null);
  };

  return (
    <>
      {children}
      <div className="fixed top-4 right-4 z-[80] flex w-[min(100%-2rem,360px)] flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className="flex items-start gap-3 rounded-lg border border-border bg-popover px-3 py-3 text-popover-foreground shadow-lg"
          >
            {toast.variant === 'success' && <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-400" />}
            {toast.variant === 'error' && <XCircle className="mt-0.5 size-4 shrink-0 text-red-400" />}
            {toast.variant === 'warning' && <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-400" />}
            {toast.variant === 'info' && <Info className="mt-0.5 size-4 shrink-0 text-indigo-300" />}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium leading-5">{toast.title}</p>
              {toast.message && <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{toast.message}</p>}
            </div>
            <button
              type="button"
              aria-label="Dismiss notification"
              className="text-muted-foreground hover:text-foreground"
              onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
            >
              <X className="size-3.5" />
            </button>
          </div>
        ))}
      </div>
      <Dialog open={!!confirm} onOpenChange={(open) => { if (!open) closeConfirm(false); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{confirm?.title}</DialogTitle>
          </DialogHeader>
          <p className="text-sm leading-6 text-muted-foreground">{confirm?.message}</p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => closeConfirm(false)}>Cancel</Button>
            <Button
              variant={confirm?.destructive ? 'destructive' : 'default'}
              onClick={() => closeConfirm(true)}
            >
              {confirm?.confirmLabel ?? 'Confirm'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export type ToastVariant = 'info' | 'success' | 'error' | 'warning';

export type ToastItem = {
  id: string;
  title: string;
  message?: string;
  variant: ToastVariant;
};

type ToastListener = (item: ToastItem) => void;

let toastListener: ToastListener | null = null;

export function subscribeToasts(listener: ToastListener) {
  toastListener = listener;
  return () => {
    if (toastListener === listener) toastListener = null;
  };
}

function inferVariant(text: string): ToastVariant {
  const value = text.toLowerCase();
  if (value.startsWith('error') || value.includes('failed') || value.includes('network error')) return 'error';
  if (value.includes('success') || value.startsWith('✅') || value.includes('saved') || value.includes('started') || value.includes('scheduled') || value.includes('copied')) return 'success';
  if (value.includes('please ') || value.includes('maximum') || value.includes('not configured')) return 'warning';
  return 'info';
}

export function pushToast(variant: ToastVariant, title: string, message?: string) {
  toastListener?.({
    id: Math.random().toString(36).slice(2),
    title,
    message,
    variant,
  });
}

export interface NotifyFunction {
  (message: string): void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

export const notify: NotifyFunction = Object.assign(
  (message: string) => {
    const clean = message.replace(/^✅\s*/, '').replace(/^🚀\s*/, '').replace(/^❌\s*/, '');
    pushToast(inferVariant(message), clean);
  },
  {
    success: (message: string) => pushToast('success', message),
    error: (message: string) => pushToast('error', message),
    warning: (message: string) => pushToast('warning', message),
    info: (message: string) => pushToast('info', message),
  }
);

export type ConfirmRequest = {
  title: string;
  message: string;
  confirmLabel: string;
  destructive: boolean;
  resolve: (value: boolean) => void;
};

let confirmOpener: ((request: ConfirmRequest) => void) | null = null;

export function registerConfirm(opener: ((request: ConfirmRequest) => void) | null) {
  confirmOpener = opener;
}

export function confirmAction(
  message: string,
  options?: { title?: string; confirmLabel?: string; destructive?: boolean },
): Promise<boolean> {
  const destructive = options?.destructive ?? /delete|remove|permanently|cancel this/i.test(message);
  if (!confirmOpener) return Promise.resolve(window.confirm(message));
  return new Promise((resolve) => {
    confirmOpener?.({
      title: options?.title ?? (destructive ? 'Confirm deletion' : 'Please confirm'),
      message,
      confirmLabel: options?.confirmLabel ?? (destructive ? 'Delete' : 'Confirm'),
      destructive,
      resolve,
    });
  });
}

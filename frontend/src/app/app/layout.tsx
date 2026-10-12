'use client';

import React from 'react';
import AppShell from '@/components/shell/app-shell';
import { WorkspaceProvider } from '@/lib/workspace';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <AppShell>{children}</AppShell>
    </WorkspaceProvider>
  );
}

'use client';

import React from 'react';
import AppShell from '@/components/shell/app-shell';
import { InterfaceModeProvider } from '@/lib/interface-mode';
import { WorkspaceProvider } from '@/lib/workspace';

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <InterfaceModeProvider>
        <AppShell>{children}</AppShell>
      </InterfaceModeProvider>
    </WorkspaceProvider>
  );
}

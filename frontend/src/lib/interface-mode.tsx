'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

export type InterfaceMode = 'bot' | 'classic';

const STORAGE_KEY = 'octaos-interface-mode';

type InterfaceModeValue = {
  mode: InterfaceMode;
  ready: boolean;
  setMode: (mode: InterfaceMode) => void;
};

const InterfaceModeContext = createContext<InterfaceModeValue>({
  mode: 'bot',
  ready: false,
  setMode: () => {},
});

export function InterfaceModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<InterfaceMode>('bot');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setModeState(localStorage.getItem(STORAGE_KEY) === 'classic' ? 'classic' : 'bot');
    setReady(true);
  }, []);

  const setMode = (next: InterfaceMode) => {
    setModeState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // The choice still applies for this visit if storage is blocked.
    }
  };

  return (
    <InterfaceModeContext.Provider value={{ mode, ready, setMode }}>
      {children}
    </InterfaceModeContext.Provider>
  );
}

export function useInterfaceMode() {
  return useContext(InterfaceModeContext);
}

/** AI-first chat for the current workspace page. Home, assistant, and agent routes handle the toggle themselves. */
export function sectionAssistant(pathname: string): { scope: string; title: string } | null {
  const rules: Array<[string, string, string]> = [
    ['/app/sales', 'sales', 'Sales'],
    ['/app/campaigns', 'marketing', 'Marketing'],
    ['/app/support', 'support', 'Support'],
    ['/app/hiring', 'hiring', 'Hiring'],
    ['/app/hr', 'people', 'People'],
    ['/app/orchestrator', 'activity', 'Activity'],
    ['/app/knowledge', 'knowledge', 'Knowledge'],
    ['/app/ceo', 'objectives', 'Objectives'],
    ['/app/boardroom', 'governance', 'Governance'],
    ['/app/teams', 'teams', 'Teams'],
    ['/app/approvals', 'approvals', 'Approvals'],
    ['/app/costs', 'costs', 'AI usage'],
    ['/app/marketplace', 'marketplace', 'Marketplace'],
    ['/app/automations', 'workflows', 'Workflows'],
  ];
  for (const [prefix, scope, title] of rules) {
    if (pathname === prefix || pathname.startsWith(`${prefix}/`)) {
      return { scope, title };
    }
  }
  return null;
}

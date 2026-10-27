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
    if (next !== mode) {
      try {
        sessionStorage.setItem(
          'octaos-interface-mode-toggle',
          JSON.stringify({ to: next, path: window.location.pathname }),
        );
      } catch {
        // A page that stays mounted still receives the mode from context.
      }
    }
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

/** Section home that becomes an AI chat. Subpages keep their own screens, and Knowledge always stays the classic library. */
const SECTION_CHATS: Array<[string, string, string]> = [
  ['/app/sales', 'sales', 'Sales'],
  ['/app/campaigns', 'marketing', 'Marketing'],
  ['/app/support', 'support', 'Support'],
  ['/app/hiring', 'hiring', 'Hiring'],
  ['/app/hr', 'people', 'People'],
  ['/app/orchestrator', 'activity', 'Activity'],
  ['/app/ceo', 'objectives', 'Objectives'],
  ['/app/boardroom', 'governance', 'Governance'],
  ['/app/teams', 'teams', 'Teams'],
  ['/app/approvals', 'approvals', 'Approvals'],
  ['/app/costs', 'costs', 'AI usage'],
  ['/app/marketplace', 'marketplace', 'Marketplace'],
  ['/app/automations', 'workflows', 'Workflows'],
];

/** Built-in agent slug for a chat scope. Finance has no section home, so it stays on the assistant. */
export const SECTION_AGENT_SLUG: Record<string, string> = {
  sales: 'sales_ai',
  marketing: 'marketing_ai',
  support: 'support_ai',
  hiring: 'hr_ai',
  people: 'hr_ai',
  objectives: 'ceo_ai',
};

const AGENT_SECTION_PATH: Record<string, string> = {
  sales_ai: '/app/sales',
  marketing_ai: '/app/campaigns',
  support_ai: '/app/support',
  hr_ai: '/app/hr',
  ceo_ai: '/app/ceo',
};

export function sectionAssistant(pathname: string): { scope: string; title: string } | null {
  for (const [path, scope, title] of SECTION_CHATS) {
    if (pathname === path) return { scope, title };
  }
  return null;
}

/** Classic Knowledge departments. HR is stored as HR and labeled Hiring, matching the Knowledge page. */
export function knowledgeDepartmentForScope(scope?: string | null): string {
  if (scope === 'sales') return 'Sales';
  if (scope === 'marketing') return 'Marketing';
  if (scope === 'support') return 'Support';
  if (scope === 'hiring' || scope === 'people') return 'HR';
  return 'all';
}

export function pathForAgentSlug(slug?: string | null, id?: string | null): string {
  if (slug && AGENT_SECTION_PATH[slug]) return AGENT_SECTION_PATH[slug];
  const key = slug || id;
  if (!key) return '/app/assistant';
  return `/app/assistant?agent=${encodeURIComponent(key)}`;
}

import type { SalesSection } from './sales-types';

export const SALES_PATHS: Record<SalesSection, string> = {
  home: '/app/sales',
  accounts: '/app/sales/accounts',
  inbox: '/app/sales/inbox',
  prospecting: '/app/sales/find',
  prompt_agent: '/app/sales/find',
  pipeline: '/app/sales/pipeline',
  intelligence: '/app/sales/intelligence',
  deal_desk: '/app/sales/deal-desk',
  stepper: '/app/sales/activity',
  deal_rooms: '/app/sales/deals',
  agent_center: '/app/sales/agents',
  analytics: '/app/sales/revenue',
  config: '/app/sales/configuration',
  configured_engine: '/app/sales/configuration',
  campaigns: '/app/sales/campaigns',
};

export function pathForSalesSection(section: SalesSection) {
  return SALES_PATHS[section] || '/app/sales';
}

export function salesSectionFromPath(pathname: string): SalesSection {
  if (pathname.startsWith('/app/sales/accounts')) return 'accounts';
  if (pathname.startsWith('/app/sales/inbox')) return 'inbox';
  if (pathname.startsWith('/app/sales/deal-desk') || pathname.startsWith('/app/sales/cpq')) return 'deal_desk';
  if (pathname.startsWith('/app/sales/intelligence')) return 'intelligence';
  if (pathname.startsWith('/app/sales/agents') || pathname.startsWith('/app/sales/agent-center')) return 'agent_center';
  if (pathname.startsWith('/app/sales/find') || pathname.startsWith('/app/sales/prompt-agent')) return 'prospecting';
  if (pathname.startsWith('/app/sales/activity')) return 'stepper';
  if (pathname.startsWith('/app/sales/deals')) return 'deal_rooms';
  if (pathname.startsWith('/app/sales/revenue')) return 'analytics';
  if (pathname.startsWith('/app/sales/configured-engine')) return 'configured_engine';
  if (pathname.startsWith('/app/sales/configuration')) return 'config';
  if (pathname.startsWith('/app/sales/pipeline')) return 'pipeline';
  if (pathname.startsWith('/app/sales/campaigns')) return 'campaigns';
  if (pathname.startsWith('/app/sales/rooms/')) return 'pipeline';
  if (pathname === '/app/sales' || pathname === '/app/sales/') return 'home';
  return 'pipeline';
}

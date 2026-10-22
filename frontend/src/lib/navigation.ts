import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  FileText,
  CheckCheck,
  Calendar,
  TrendingUp,
  Building2,
  MessageSquare,
  Briefcase,
  Users,
  Activity,
  Target,
  Radar,
  Store,
  KeyRound,
  DollarSign,
  Shield,
  UserCircle,
  Settings,
  Zap,
  GitFork,
  Bot,
  ShieldCheck,
  Cpu,
  Mail,
  Navigation,
} from 'lucide-react';

export type NavItem = {
  id: string;
  name: string;
  href: string;
  icon: LucideIcon;
  section: string;
  adminOnly?: boolean;
  systemAdminOnly?: boolean;
  keywords?: string;
  /** exact: only this URL. prefix: this URL and paths under it. */
  match?: 'exact' | 'prefix';
  /** Extra paths that should highlight this item. */
  also?: string[];
};

export type NavGroup = {
  label: string;
  items: NavItem[];
};

export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Work',
    items: [
      { id: 'dashboard', name: 'Home', href: '/app/home', icon: BarChart3, section: 'dashboard', keywords: 'dashboard operating' },
      { id: 'approvals', name: 'Approvals', href: '/app/approvals', icon: CheckCheck, section: 'system', keywords: 'hitl review queue' },
      { id: 'knowledge', name: 'Knowledge', href: '/app/knowledge', icon: FileText, section: 'knowledge', keywords: 'documents rag' },
    ],
  },
  {
    label: 'Revenue',
    items: [
      { id: 'campaigns', name: 'Campaigns', href: '/app/campaigns', icon: Calendar, section: 'marketing' },
      { id: 'sales', name: 'Sales', href: '/app/sales', icon: TrendingUp, section: 'sales', keywords: 'crm leads pipeline accounts deals sales inbox cadence industry copilot' },
    ],
  },
  {
    label: 'Service',
    items: [
      { id: 'support', name: 'Support', href: '/app/support', icon: MessageSquare, section: 'support' },
    ],
  },
  {
    label: 'People',
    items: [
      { id: 'hr', name: 'People', href: '/app/hr', icon: Users, section: 'hr', match: 'exact', keywords: 'employees directory headcount hr' },
      { id: 'hr_hiring', name: 'Hiring', href: '/app/hr/hiring', icon: Briefcase, section: 'hr', also: ['/app/hiring'], keywords: 'ats candidates resumes interviews offers recruitment' },
      { id: 'hr_leave', name: 'Time off', href: '/app/hr/leave', icon: Calendar, section: 'hr', keywords: 'leave pto coverage' },
    ],
  },
  {
    label: 'Workforce',
    items: [
      { id: 'agents', name: 'Agents', href: '/app/agents', icon: Bot, section: 'teams', keywords: 'workforce agents directory cockpit' },
      { id: 'orchestrator', name: 'Live runs', href: '/app/orchestrator', icon: Activity, section: 'orchestrator', keywords: 'orchestrator running tasks' },
      { id: 'automations', name: 'Workflows', href: '/app/automations', icon: GitFork, section: 'automations', keywords: 'automations workflows triggers' },
      { id: 'teams', name: 'Teams', href: '/app/teams', icon: Users, section: 'teams' },
      { id: 'marketplace', name: 'Marketplace', href: '/app/marketplace', icon: Store, section: 'marketplace' },
    ],
  },
  {
    label: 'Oversight',
    items: [
      { id: 'ceo', name: 'Business autonomy', href: '/app/ceo', icon: Target, section: 'ceo', keywords: 'business autonomy control plane objectives execution strategy' },
      { id: 'coordination', name: 'Decision assurance', href: '/app/boardroom', icon: ShieldCheck, section: 'coordination', keywords: 'decision assurance boardroom governance risk audit' },
    ],
  },
  {
    label: 'Admin',
    items: [
      { id: 'api_management', name: 'Integrations', href: '/app/settings/integrations', icon: KeyRound, section: 'system', keywords: 'api keys byok' },
      { id: 'profile', name: 'Organization', href: '/app/settings/organization', icon: UserCircle, section: 'profile' },
      { id: 'members', name: 'Members', href: '/app/settings/members', icon: Users, section: 'members', adminOnly: true },
      { id: 'ai_optimization', name: 'AI cost', href: '/app/costs', icon: DollarSign, section: 'ai_optimization' },
      { id: 'enterprise', name: 'Enterprise', href: '/app/settings/enterprise', icon: Shield, section: 'system' },
      { id: 'system_admin', name: 'System admin', href: '/app/admin', icon: Zap, section: 'system_admin', systemAdminOnly: true },
    ],
  },
];

export const EXTRA_ROUTES: NavItem[] = [
  { id: 'instructions', name: 'Setup guide', href: '/app/settings/guide', icon: Settings, section: 'system', keywords: 'api guide instructions' },
  { id: 'sales_prompt_agent', name: 'Prompt sales agent', href: '/app/sales/prompt-agent', icon: Zap, section: 'sales', keywords: 'prompt sales agent find leads' },
  { id: 'sales_find', name: 'Find leads', href: '/app/sales/find', icon: Radar, section: 'sales', keywords: 'prospecting discovery crm search' },
  { id: 'sales_activity', name: 'Agent runs', href: '/app/sales/activity', icon: Activity, section: 'sales', keywords: 'sales workflow stepper' },
  { id: 'deal_rooms', name: 'Deal rooms', href: '/app/sales/deals', icon: Building2, section: 'sales', keywords: 'deals committee quote' },
  { id: 'sales_revenue', name: 'Revenue', href: '/app/sales/revenue', icon: DollarSign, section: 'sales', keywords: 'funnel analytics won' },
  { id: 'sales_config', name: 'Sales rules', href: '/app/sales/configuration', icon: Settings, section: 'sales', keywords: 'cadence auto reply settings' },
  { id: 'sales_intelligence', name: 'Source intelligence', href: '/app/sales/intelligence', icon: Radar, section: 'sales', keywords: 'evidence sources roi scoring' },
  { id: 'sales_accounts', name: 'Accounts 360', href: '/app/sales/accounts', icon: Building2, section: 'sales', keywords: 'accounts buying committee canonical' },
  { id: 'sales_agents', name: 'Agent Center', href: '/app/sales/agents', icon: Cpu, section: 'sales', keywords: '50 agents autonomous execution runs' },
  { id: 'sales_inbox', name: 'Omnichannel Inbox', href: '/app/sales/inbox', icon: Mail, section: 'sales', keywords: 'inbox messages email whatsapp cadence replies' },
  { id: 'sales_deal_desk', name: 'Deal Desk & CPQ', href: '/app/sales/deal-desk', icon: FileText, section: 'sales', keywords: 'deal desk cpq quotes pricing proposal contract' },
  { id: 'sales_pipeline', name: 'Sales CRM', href: '/app/sales/pipeline', icon: TrendingUp, section: 'sales', keywords: 'pipeline leads table kanban' },
  { id: 'sales_industries', name: 'Industry packs', href: '/app/sales/industries', icon: Building2, section: 'sales', keywords: 'vertical industry pack banking saas real estate' },
  { id: 'sales_campaigns', name: 'Sales campaigns', href: '/app/sales/campaigns', icon: Calendar, section: 'sales', keywords: 'campaign execution cadence' },
  { id: 'sales_field_sales', name: 'Field sales & visits', href: '/app/sales/field-sales', icon: Navigation, section: 'sales', keywords: 'field sales visits property smart scheduling gps real estate dispatch' },
];

const VIEW_PATHS: Record<string, string> = {
  dashboard: '/app/home',
  knowledge: '/app/knowledge',
  campaigns: '/app/campaigns',
  sales: '/app/sales',
  sales_field_sales: '/app/sales/field-sales',
  sales_pipeline: '/app/sales/pipeline',
  sales_industries: '/app/sales/industries',
  sales_campaigns: '/app/sales/campaigns',
  sales_inbox: '/app/sales/inbox',
  sales_deal_desk: '/app/sales/deal-desk',
  sales_accounts: '/app/sales/accounts',
  sales_agents: '/app/sales/agents',
  support: '/app/support',
  coordination: '/app/boardroom',
  boardroom: '/app/boardroom',
  ceo: '/app/ceo',
  orchestrator: '/app/orchestrator',
  teams: '/app/teams',
  marketplace: '/app/marketplace',
  hr: '/app/hr',
  hr_hiring: '/app/hr/hiring',
  hr_leave: '/app/hr/leave',
  sales_find: '/app/sales/find',
  sales_activity: '/app/sales/activity',
  sales_revenue: '/app/sales/revenue',
  sales_config: '/app/sales/configuration',
  'deal-rooms': '/app/sales/deals',
  ai_optimization: '/app/costs',
  api_management: '/app/settings/integrations',
  enterprise: '/app/settings/enterprise',
  members: '/app/settings/members',
  profile: '/app/settings/organization',
  system_admin: '/app/admin',
  instructions: '/app/settings/guide',
  approvals: '/app/approvals',
  deal_rooms: '/app/sales/deals',
  sales_intelligence: '/app/sales/intelligence',
  automations: '/app/automations',
  agents: '/app/agents',
};

export function pathForView(viewId: string) {
  return VIEW_PATHS[viewId] || '/app/home';
}

export function allNavItems() {
  return [...NAV_GROUPS.flatMap((group) => group.items), ...EXTRA_ROUTES];
}

export function canSeeItem(item: NavItem, profile: any) {
  // Profile arrives after /auth/me. Hiding the nav until then leaves a blank sidebar.
  if (!profile) return !item.systemAdminOnly && !item.adminOnly;
  if (item.systemAdminOnly) return !!profile.is_system_admin;
  if (item.adminOnly) return profile.role === 'admin' || !!profile.is_system_admin;
  if (profile.role === 'admin' || profile.is_system_admin) return true;
  if (item.id === 'dashboard' || item.id === 'profile' || item.section === 'profile') return true;
  const allowed: string[] | undefined = profile.allowed_sections;
  if (!allowed || allowed.includes('all')) return true;
  return allowed.includes(item.section);
}

export function visibleGroups(profile: any): NavGroup[] {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => canSeeItem(item, profile)),
  })).filter((group) => group.items.length > 0);
}

export function crumbForPath(pathname: string) {
  if (pathname.startsWith('/app/agents/')) {
    return { section: 'AI Workforce', name: 'Agent Cockpit' };
  }
  if (pathname === '/app/agents') {
    return { section: 'AI Workforce', name: 'Agent Directory' };
  }
  if (pathname.startsWith('/app/hiring/rooms/') || pathname.startsWith('/app/hr/hiring/rooms/')) {
    const slug = pathname.split('/rooms/')[1]?.split('/')[0];
    return { section: 'People', name: `Hiring room (#${slug})` };
  }
  if (pathname.startsWith('/app/hr/hiring') || pathname.startsWith('/app/hiring')) {
    return { section: 'People', name: 'Hiring' };
  }
  if (pathname.startsWith('/app/hr/leave')) {
    return { section: 'People', name: 'Time off' };
  }
  if (pathname.startsWith('/app/campaigns/rooms/')) {
    const slug = pathname.replace('/app/campaigns/rooms/', '').split('/')[0];
    return { section: 'Revenue', name: `Campaign Room (#${slug})` };
  }
  if (pathname.startsWith('/app/support/rooms/')) {
    const slug = pathname.replace('/app/support/rooms/', '').split('/')[0];
    return { section: 'Service', name: `Support Room (#${slug})` };
  }
  if (pathname.startsWith('/app/sales/rooms/')) {
    const slug = pathname.replace('/app/sales/rooms/', '').split('/')[0];
    return { section: 'Revenue', name: `Sales Room (#${slug})` };
  }
  const item = allNavItems().find((entry) => entry.href === pathname);
  if (!item) return { section: 'Workspace', name: 'OctaOS' };
  const group = NAV_GROUPS.find((entry) => entry.items.some((nav) => nav.href === pathname));
  return { section: group?.label || 'Workspace', name: item.name };
}

export function isItemActive(item: NavItem, pathname: string) {
  const hrefs = [item.href, ...(item.also || [])];
  if (item.match === 'exact') return hrefs.some((href) => pathname === href);
  return hrefs.some((href) => pathname === href || pathname.startsWith(`${href}/`));
}

export function isAgentAllowed(agentKey: string, profile: any): boolean {
  if (!profile) return true;
  if (profile.is_system_admin) return true;
  const allowed = profile.allowed_agents;
  if (!allowed || allowed.includes('*')) return true;
  return allowed.map((a: string) => String(a).toLowerCase()).includes(agentKey.toLowerCase());
}


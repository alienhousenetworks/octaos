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
      { id: 'sales', name: 'Sales pipeline', href: '/app/sales', icon: TrendingUp, section: 'sales', keywords: 'crm leads' },
      { id: 'deal_rooms', name: 'Deal rooms', href: '/app/sales/deals', icon: Building2, section: 'sales' },
      { id: 'sales_intelligence', name: 'Source intelligence', href: '/app/sales/intelligence', icon: Radar, section: 'sales', keywords: 'evidence sources roi scoring' },
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
      { id: 'hr', name: 'Hiring', href: '/app/hiring', icon: Briefcase, section: 'hr' },
    ],
  },
  {
    label: 'Workforce',
    items: [
      { id: 'teams', name: 'Teams', href: '/app/teams', icon: Users, section: 'teams' },
      { id: 'orchestrator', name: 'Orchestrator', href: '/app/orchestrator', icon: Activity, section: 'orchestrator' },
      { id: 'coordination', name: 'Boardroom', href: '/app/boardroom', icon: Users, section: 'coordination' },
      { id: 'ceo', name: 'CEO workspace', href: '/app/ceo', icon: Target, section: 'ceo' },
      { id: 'marketplace', name: 'Marketplace', href: '/app/marketplace', icon: Store, section: 'marketplace' },
      { id: 'automations', name: 'Automations', href: '/app/automations', icon: GitFork, section: 'automations', keywords: 'workflows activepieces triggers' },
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
  { id: 'sales_prompt_agent', name: 'Prompt Sales Agent', href: '/app/sales/prompt-agent', icon: Zap, section: 'sales' },
  { id: 'sales_config', name: 'Configured Sales Engine', href: '/app/sales/configuration', icon: Settings, section: 'sales' },
  { id: 'sales_activity', name: 'Sales activity', href: '/app/sales/activity', icon: Activity, section: 'sales' },
  { id: 'sales_revenue', name: 'Revenue', href: '/app/sales/revenue', icon: DollarSign, section: 'sales' },
];

const VIEW_PATHS: Record<string, string> = {
  dashboard: '/app/home',
  knowledge: '/app/knowledge',
  campaigns: '/app/campaigns',
  sales: '/app/sales',
  support: '/app/support',
  coordination: '/app/boardroom',
  boardroom: '/app/boardroom',
  ceo: '/app/ceo',
  orchestrator: '/app/orchestrator',
  teams: '/app/teams',
  marketplace: '/app/marketplace',
  hr: '/app/hiring',
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
  const item = allNavItems().find((entry) => entry.href === pathname);
  if (!item) return { section: 'Workspace', name: 'OctaOS' };
  const group = NAV_GROUPS.find((entry) => entry.items.some((nav) => nav.href === pathname));
  return { section: group?.label || 'Workspace', name: item.name };
}

export function isAgentAllowed(agentKey: string, profile: any): boolean {
  if (!profile) return true;
  if (profile.is_system_admin) return true;
  const allowed = profile.allowed_agents;
  if (!allowed || allowed.includes('*')) return true;
  return allowed.map((a: string) => String(a).toLowerCase()).includes(agentKey.toLowerCase());
}


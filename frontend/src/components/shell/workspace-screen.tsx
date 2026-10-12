'use client';

import React, { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import DashboardView from '@/components/views/dashboard-view';
import KnowledgeView from '@/components/views/knowledge-view';
import CampaignsView from '@/components/views/campaigns-view';
import SupportView from '@/components/views/support-view';
import OrchestratorView from '@/components/views/orchestrator-view';
import TeamsView from '@/components/views/teams-view';
import MarketplaceView from '@/components/views/marketplace-view';
import InstructionsView from '@/components/views/instructions-view';
import HRView from '@/components/views/hr-view';
import CEOView from '@/components/views/ceo-view';
import CoordinationView from '@/components/views/coordination-view';
import SalesView from '@/components/views/sales-view';
import SalesIntelligenceView from '@/components/views/sales-intelligence-view';
import AIOptimizationView from '@/components/views/ai-optimization-view';
import MembersView from '@/components/views/members-view';
import SystemAdminView from '@/components/views/system-admin-view';
import ApiManagementView from '@/components/views/api-management-view';
import ProfileView from '@/components/views/profile-view';
import EnterpriseView from '@/components/views/enterprise-view';
import AutomationsView from '@/components/views/automations-view';
import { EmptyState } from '@/components/shell/states';
import { allNavItems, canSeeItem, pathForView } from '@/lib/navigation';
import { useWorkspace, useWorkspaceFeed } from '@/lib/workspace';

const FEED_PATHS = [
  '/app/home',
  '/app/knowledge',
  '/app/campaigns',
  '/app/sales',
  '/app/orchestrator',
  '/app/teams',
  '/app/marketplace',
  '/app/ceo',
  '/app/costs',
  '/app/automations',
  '/app/settings/integrations',
  '/app/settings/guide',
];

const SALES_SECTIONS = {
  '/app/sales': 'pipeline',
  '/app/sales/deals': 'deal_rooms',
  '/app/sales/prompt-agent': 'prompt_agent',
  '/app/sales/configured-engine': 'configured_engine',
  '/app/sales/configuration': 'configured_engine',
  '/app/sales/activity': 'stepper',
  '/app/sales/revenue': 'analytics',
} as const;

export default function WorkspaceScreen() {
  const pathname = usePathname();
  const router = useRouter();
  const workspace = useWorkspace();
  const needsFeed = FEED_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
  useWorkspaceFeed(needsFeed);

  useEffect(() => {
    if (pathname === '/app') {
      router.replace('/app/home');
    }
  }, [pathname, router]);

  if (pathname === '/app') {
    return null;
  }

  const match = allNavItems().find((item) => item.href === pathname);
  if (match && !canSeeItem(match, workspace.userProfile)) {
    return (
      <EmptyState
        title="You do not have access to this screen"
        description="Ask an admin to update your section permissions."
      />
    );
  }

  const setActiveView = (viewId: string) => router.push(pathForView(viewId));
  const shared = {
    token: workspace.token,
    API_URL: workspace.apiUrl,
    fetchWithAuth: workspace.fetchWithAuth,
    fetchData: workspace.fetchData,
  };

  if (pathname === '/app/home') {
    return (
      <DashboardView
        metrics={workspace.metrics}
        timeline={workspace.timeline}
        queue={workspace.queue}
        apps={workspace.apps}
        setActiveView={setActiveView}
        uninstallApp={workspace.uninstallApp}
        handleApprovePost={workspace.handleApprovePost}
        handleRejectPost={workspace.handleRejectPost}
      />
    );
  }
  if (pathname === '/app/knowledge') {
    return <KnowledgeView {...shared} knowledge={workspace.knowledge} />;
  }
  if (pathname === '/app/campaigns') {
    return <CampaignsView {...shared} activeView="campaigns" configuredProviders={workspace.configuredProviders} />;
  }
  if (pathname === '/app/support') {
    return <SupportView {...shared} tenantId={workspace.tenantId} />;
  }
  if (pathname === '/app/orchestrator') {
    return (
      <OrchestratorView
        {...shared}
        apps={workspace.apps}
        configuredProviders={workspace.configuredProviders}
        timeline={workspace.timeline}
        queue={workspace.queue}
        handleApprovePost={workspace.handleApprovePost}
        handleRejectPost={workspace.handleRejectPost}
      />
    );
  }
  if (pathname === '/app/teams') {
    return <TeamsView {...shared} teams={workspace.teams} setTeams={workspace.setTeams} />;
  }
  if (pathname === '/app/marketplace') {
    return <MarketplaceView {...shared} apps={workspace.apps} />;
  }
  if (pathname === '/app/automations') {
    return <AutomationsView {...shared} userProfile={workspace.userProfile} />;
  }
  if (pathname === '/app/hiring') {
    return <HRView {...shared} />;
  }
  if (pathname === '/app/ceo') {
    return <CEOView {...shared} timeline={workspace.timeline} setActiveView={setActiveView} />;
  }
  if (pathname === '/app/boardroom') {
    return <CoordinationView {...shared} />;
  }
  if (pathname === '/app/sales/intelligence') {
    return <SalesIntelligenceView {...shared} />;
  }
  if (pathname in SALES_SECTIONS) {
    const section = SALES_SECTIONS[pathname as keyof typeof SALES_SECTIONS];
    return (
      <SalesView
        {...shared}
        timeline={workspace.timeline}
        section={section}
        onSectionChange={(next) => {
          const href = Object.entries(SALES_SECTIONS).find(([, value]) => value === next)?.[0];
          if (href) router.push(href);
        }}
      />
    );
  }
  if (pathname === '/app/settings/organization') {
    return (
      <ProfileView
        {...shared}
        userProfile={workspace.userProfile}
        setUserProfile={workspace.setUserProfile}
        setToken={workspace.setToken}
        setTenantId={workspace.setTenantId}
      />
    );
  }
  if (pathname === '/app/costs') {
    return <AIOptimizationView {...shared} metrics={workspace.metrics} />;
  }
  if (pathname === '/app/approvals') {
    return workspace.token ? <EnterpriseView token={workspace.token} mode="approvals" /> : null;
  }
  if (pathname === '/app/settings/enterprise') {
    return workspace.token ? <EnterpriseView token={workspace.token} mode="control" /> : null;
  }
  if (pathname === '/app/settings/integrations') {
    return (
      <ApiManagementView
        {...shared}
        configuredProviders={workspace.configuredProviders}
        tenantId={workspace.tenantId}
      />
    );
  }
  if (pathname === '/app/settings/guide') {
    return (
      <InstructionsView
        configuredProviders={workspace.configuredProviders}
        API_URL={workspace.apiUrl}
        tenantId={workspace.tenantId}
      />
    );
  }
  if (pathname === '/app/settings/members') {
    return <MembersView {...shared} />;
  }
  if (pathname === '/app/admin') {
    return (
      <SystemAdminView
        token={workspace.token}
        API_URL={workspace.apiUrl}
        fetchWithAuth={workspace.fetchWithAuth}
        onBrandingUpdate={(logo, favicon) => {
          if (logo !== undefined) workspace.setLogoUrl(logo ?? null);
          if (favicon !== undefined) workspace.setFaviconUrl(favicon ?? null);
        }}
      />
    );
  }

  return (
    <EmptyState
      title="This page does not exist"
      description="Use search or the sidebar to open a workspace screen."
    />
  );
}

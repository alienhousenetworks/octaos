'use client';

import React, { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import DashboardView from '@/components/views/dashboard-view';
import UniversalAssistantView from '@/components/views/universal-assistant-view';
import KnowledgeView from '@/components/views/knowledge-view';
import CampaignsView from '@/components/views/campaigns-view';
import CampaignStudioView from '@/components/views/campaign-studio-view';
import SupportView from '@/components/views/support-view';
import OrchestratorView from '@/components/views/orchestrator-view';
import TeamsView from '@/components/views/teams-view';
import MarketplaceView from '@/components/views/marketplace-view';
import InstructionsView from '@/components/views/instructions-view';
import HREnterpriseSuite from '@/features/people/hr-suite';
import { peopleScreenFromPath } from '@/features/people/routes';
import CEOView from '@/components/views/ceo-view';
import CoordinationView from '@/components/views/coordination-view';
import SalesView from '@/features/crm/sales-view';
import { salesSectionFromPath } from '@/features/crm/routes';
import AIOptimizationView from '@/components/views/ai-optimization-view';
import MembersView from '@/components/views/members-view';
import DjangoAdminRBACView from '@/features/rbac/django-admin-rbac-view';
import SystemAdminView from '@/components/views/system-admin-view';
import ApiManagementView from '@/components/views/api-management-view';
import ProfileView from '@/components/views/profile-view';
import EnterpriseView from '@/components/views/enterprise-view';
import ApprovalsView from '@/components/views/approvals-view';
import AutomationsView from '@/features/automations/automations-view';
import AgentDirectoryView from '@/features/workforce/agent-directory-view';
import AgentDetailView from '@/features/workforce/agent-detail-view';
import AgentLockedScreen from '@/components/shell/agent-locked-screen';
import { EmptyState } from '@/components/shell/states';
import { sectionAssistant, useInterfaceMode } from '@/lib/interface-mode';
import { allNavItems, canSeeItem, pathForView, isAgentAllowed } from '@/lib/navigation';
import { useWorkspace, useWorkspaceFeed } from '@/lib/workspace';

const FEED_PATHS = [
  '/app/home',
  '/app/assistant',
  '/app/agents',
  '/app/knowledge',
  '/app/campaigns',
  '/app/sales',
  '/app/orchestrator',
  '/app/teams',
  '/app/marketplace',
  '/app/ceo',
  '/app/costs',
  '/app/automations',
  '/app/hr',
  '/app/hiring',
  '/app/support',
  '/app/settings/integrations',
  '/app/settings/guide',
];

export default function WorkspaceScreen() {
  const pathname = usePathname();
  const router = useRouter();
  const workspace = useWorkspace();
  const { mode, ready } = useInterfaceMode();
  const needsFeed = FEED_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
  useWorkspaceFeed(needsFeed);

  useEffect(() => {
    if (pathname === '/app') {
      router.replace('/app/assistant');
    }
  }, [pathname, router]);

  if (!ready || pathname === '/app') {
    return null;
  }

  const match = allNavItems().find(
    (item) => item.href === pathname || (item.href !== '/app/home' && pathname.startsWith(`${item.href}/`))
  );
  if (match && !canSeeItem(match, workspace.userProfile)) {
    return (
      <EmptyState
        title="You do not have access to this screen"
        description="Ask an admin to update your section permissions."
      />
    );
  }

  const pageChat = mode === 'bot' ? sectionAssistant(pathname) : null;
  if (pageChat) {
    const lockedAgent = pathname.startsWith('/app/sales')
      ? 'sales'
      : pathname.startsWith('/app/campaigns')
        ? 'marketing'
        : pathname.startsWith('/app/support')
          ? 'support'
          : pathname.startsWith('/app/hr') || pathname.startsWith('/app/hiring')
            ? 'hr'
            : null;
    if (lockedAgent && !isAgentAllowed(lockedAgent, workspace.userProfile)) {
      return (
        <AgentLockedScreen
          agentKey={lockedAgent}
          token={workspace.token}
          API_URL={workspace.apiUrl}
          fetchData={workspace.fetchData}
        />
      );
    }
    return <UniversalAssistantView scope={pageChat.scope} title={pageChat.title} />;
  }

  const setActiveView = (viewId: string) => router.push(pathForView(viewId));
  const shared = {
    token: workspace.token,
    API_URL: workspace.apiUrl,
    fetchWithAuth: workspace.fetchWithAuth,
    fetchData: workspace.fetchData,
  };

  if (pathname === '/app/assistant') {
    if (mode === 'classic') {
      return (
        <DashboardView
          {...shared}
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
    return <UniversalAssistantView />;
  }
  if (pathname === '/app/home') {
    return (
      <DashboardView
        {...shared}
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
  if (pathname === '/app/agents') {
    return (
      <AgentDirectoryView
        API_URL={workspace.apiUrl}
        fetchWithAuth={workspace.fetchWithAuth}
        token={workspace.token}
        onSelectAgent={(agentId) => router.push(`/app/agents/${agentId}`)}
      />
    );
  }
  if (pathname.startsWith('/app/agents/')) {
    const rawId = pathname.replace('/app/agents/', '').split('/')[0];
    if (rawId) {
      return (
        <AgentDetailView
          agentId={rawId}
          API_URL={workspace.apiUrl}
          fetchWithAuth={workspace.fetchWithAuth}
          token={workspace.token}
        />
      );
    }
  }
  if (pathname === '/app/knowledge') {
    return <KnowledgeView {...shared} knowledge={workspace.knowledge} />;
  }
  if (pathname === '/app/campaigns/studio') {
    if (!isAgentAllowed('marketing', workspace.userProfile)) {
      return (
        <AgentLockedScreen
          agentKey="marketing"
          token={workspace.token}
          API_URL={workspace.apiUrl}
          fetchData={workspace.fetchData}
        />
      );
    }
    return <CampaignStudioView token={workspace.token} API_URL={workspace.apiUrl} fetchWithAuth={workspace.fetchWithAuth} />;
  }
  if (pathname === '/app/campaigns' || pathname.startsWith('/app/campaigns/')) {
    if (!isAgentAllowed('marketing', workspace.userProfile)) {
      return (
        <AgentLockedScreen
          agentKey="marketing"
          token={workspace.token}
          API_URL={workspace.apiUrl}
          fetchData={workspace.fetchData}
        />
      );
    }
    const roomSlug = pathname.startsWith('/app/campaigns/rooms/')
      ? pathname.replace('/app/campaigns/rooms/', '').split('/')[0]
      : undefined;
    return (
      <CampaignsView
        {...shared}
        activeView="campaigns"
        configuredProviders={workspace.configuredProviders}
        initialRoomSlug={roomSlug}
      />
    );
  }
  if (pathname === '/app/support' || pathname.startsWith('/app/support/')) {
    if (!isAgentAllowed('support', workspace.userProfile)) {
      return (
        <AgentLockedScreen
          agentKey="support"
          token={workspace.token}
          API_URL={workspace.apiUrl}
          fetchData={workspace.fetchData}
        />
      );
    }
    const roomSlug = pathname.startsWith('/app/support/rooms/')
      ? pathname.replace('/app/support/rooms/', '').split('/')[0]
      : undefined;
    return <SupportView {...shared} tenantId={workspace.tenantId} initialRoomSlug={roomSlug} />;
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
  if (pathname === '/app/hr' || pathname.startsWith('/app/hr/') || pathname === '/app/hiring' || pathname.startsWith('/app/hiring/')) {
    if (!isAgentAllowed('hr', workspace.userProfile)) {
      return (
        <AgentLockedScreen
          agentKey="hr"
          token={workspace.token}
          API_URL={workspace.apiUrl}
          fetchData={workspace.fetchData}
        />
      );
    }
    const roomSlug = pathname.includes('/rooms/')
      ? pathname.split('/rooms/')[1]?.split('/')[0]
      : undefined;
    return (
      <HREnterpriseSuite
        {...shared}
        screen={peopleScreenFromPath(pathname)}
        initialRoomSlug={roomSlug}
      />
    );
  }
  if (pathname === '/app/ceo') {
    return <CEOView {...shared} timeline={workspace.timeline} setActiveView={setActiveView} />;
  }
  if (pathname === '/app/boardroom') {
    return <CoordinationView {...shared} />;
  }
  if (pathname === '/app/sales' || pathname.startsWith('/app/sales/')) {
    if (!isAgentAllowed('sales', workspace.userProfile)) {
      return (
        <AgentLockedScreen
          agentKey="sales"
          token={workspace.token}
          API_URL={workspace.apiUrl}
          fetchData={workspace.fetchData}
        />
      );
    }
    const roomSlug = pathname.startsWith('/app/sales/rooms/')
      ? pathname.replace('/app/sales/rooms/', '').split('/')[0]
      : undefined;
    const section = salesSectionFromPath(pathname);
    return (
      <SalesView
        {...shared}
        timeline={workspace.timeline}
        section={section}
        initialRoomSlug={roomSlug}
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
    return <ApprovalsView {...shared} />;
  }
  if (pathname === '/app/settings/enterprise') {
    return workspace.token ? <EnterpriseView token={workspace.token} mode="control" API_URL={workspace.apiUrl} /> : null;
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
  if (pathname === '/app/admin/rbac' || pathname === '/app/settings/rbac') {
    return (
      <DjangoAdminRBACView
        token={workspace.token}
        API_URL={workspace.apiUrl}
        fetchWithAuth={workspace.fetchWithAuth}
        currentUserEmail={workspace.userProfile?.email}
      />
    );
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

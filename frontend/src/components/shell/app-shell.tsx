'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  ChevronLeft,
  LogOut,
  Menu,
  Search,
  X,
  Sparkles,
  LayoutDashboard,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import CommandPalette from '@/components/shell/command-palette';
import { LoadingState } from '@/components/shell/states';
import { crumbForPath, isItemActive, visibleGroups } from '@/lib/navigation';
import { saveSession } from '@/lib/auth-session';
import { notify } from '@/lib/notify';
import { useWorkspace } from '@/lib/workspace';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const workspace = useWorkspace();
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [approvalCount, setApprovalCount] = useState<number | null>(null);
  const [orgs, setOrgs] = useState<any[]>([]);
  const [switching, setSwitching] = useState<string | null>(null);
  const [interfaceMode, setInterfaceMode] = useState<'bot' | 'classic'>('bot');

  useEffect(() => {
    if (!workspace.ready) return;
    if (!workspace.token) router.replace('/login');
  }, [workspace.ready, workspace.token, router]);

  useEffect(() => {
    const savedMode = localStorage.getItem('octaos-interface-mode');
    const routeMode = pathname === '/app/home' ? 'classic' : pathname === '/app/assistant' || pathname === '/app' ? 'bot' : null;
    const nextMode = routeMode || (savedMode === 'classic' ? 'classic' : 'bot');
    setInterfaceMode(nextMode);
    if (routeMode) localStorage.setItem('octaos-interface-mode', routeMode);
    const stored = localStorage.getItem('octaos-sidebar-collapsed');
    if (stored === '1') setCollapsed(true);
  }, [pathname]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!workspace.token) return;
    let cancelled = false;
    const load = async () => {
      try {
        const res = await workspace.fetchWithAuth(`${workspace.apiUrl}/enterprise/approvals`);
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (!cancelled) setApprovalCount(Array.isArray(data) ? data.length : 0);
      } catch {
        if (!cancelled) setApprovalCount(null);
      }
    };
    load();
    const interval = window.setInterval(load, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [workspace.token, workspace.fetchWithAuth, workspace.apiUrl]);

  const loadOrgs = async () => {
    try {
      const res = await workspace.fetchWithAuth(`${workspace.apiUrl}/auth/my-organizations`);
      if (res.ok) setOrgs(await res.json());
    } catch {
      setOrgs([]);
    }
  };

  const switchOrg = async (tenantId: string) => {
    setSwitching(tenantId);
    try {
      const res = await workspace.fetchWithAuth(`${workspace.apiUrl}/auth/switch-tenant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to switch organization');
        return;
      }
      const data = await res.json();
      saveSession({
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        tenant_id: data.tenant_id,
      });
      window.location.assign('/app/home');
    } finally {
      setSwitching(null);
    }
  };

  if (!workspace.ready || !workspace.token) {
    return (
      <div className="min-h-screen bg-background p-8">
        <LoadingState label="Checking session" />
      </div>
    );
  }

  const groups = visibleGroups(workspace.userProfile);
  const crumb = crumbForPath(pathname);
  const profile = workspace.userProfile;
  const initials = (profile?.name || profile?.email || 'U').slice(0, 1).toUpperCase();

  const nav = (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex h-[68px] items-center gap-3 border-b border-sidebar-border px-5">
        <Link href="/app/home" className="flex min-w-0 items-center gap-2">
          {workspace.logoUrl ? (
            <img src={workspace.logoUrl} alt="OctaOS" className="h-7 w-auto max-w-[132px] object-contain" />
          ) : (
            <span className={`truncate text-sm font-semibold ${collapsed ? 'sr-only' : ''}`}>OctaOS</span>
          )}
        </Link>
      </div>
      <nav className="flex-1 overflow-y-auto px-2.5 py-4" aria-label="Primary">
        {groups.map((group) => (
          <div key={group.label} className="mb-5">
            <p className={`px-2.5 pb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80 ${collapsed ? 'sr-only' : ''}`}>{group.label}</p>
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = isItemActive(item, pathname);
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  id={`nav-${item.id}`}
                  title={item.name}
                  aria-current={isActive ? "page" : undefined}
                  className={`group/nav mb-1 flex h-10 items-center gap-3 rounded-lg border border-transparent px-3 text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70 focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar ${isActive ? 'border-primary/15 bg-sidebar-accent text-sidebar-accent-foreground font-semibold' : 'text-muted-foreground hover:border-border/70 hover:bg-surface-hover hover:text-foreground'}`}
                >
                  <Icon className={`size-[17px] shrink-0 transition-colors ${isActive ? 'text-primary' : 'text-muted-foreground group-hover/nav:text-foreground'}`} />
                  <span className={`truncate ${collapsed ? 'sr-only' : ''}`}>{item.name}</span>
                  {item.id === 'approvals' && approvalCount ? (
                    <span className={`ml-auto rounded-md bg-warning/10 text-warning border border-warning/20 px-1.5 text-xs font-semibold ${collapsed ? 'sr-only' : ''}`}>{approvalCount}</span>
                  ) : null}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="hidden border-t border-sidebar-border p-3 md:block">
        <button
          type="button"
          className="flex h-10 w-full items-center gap-3 rounded-lg border border-transparent px-3 text-[13px] text-muted-foreground transition-colors hover:border-border hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/70"
          onClick={() => {
            const next = !collapsed;
            setCollapsed(next);
            localStorage.setItem('octaos-sidebar-collapsed', next ? '1' : '0');
          }}
        >
          <ChevronLeft className={`size-4 ${collapsed ? 'rotate-180' : ''}`} />
          <span className={collapsed ? 'sr-only' : ''}>Collapse</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <aside
        className="hidden h-full shrink-0 border-r border-sidebar-border md:block"
        style={{ width: collapsed ? 64 : 248 }}
      >
        {nav}
      </aside>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`fixed inset-y-0 left-0 z-50 w-[248px] border-r border-sidebar-border transition-transform md:hidden ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        {nav}
        <button
          type="button"
          aria-label="Close sidebar"
          className="absolute top-3 right-3"
          onClick={() => setMobileOpen(false)}
        >
          <X className="size-4" />
        </button>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[68px] shrink-0 items-center gap-3 border-b border-border bg-card px-4 md:px-7">
          <button
            type="button"
            className="inline-flex size-9 items-center justify-center rounded-md border border-border md:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="size-4" />
          </button>
          <div className="min-w-0 text-[13px]">
            <span className="text-muted-foreground">{crumb.section}</span>
            <span className="px-1.5 text-muted-foreground">/</span>
            <span className="font-medium">{crumb.name}</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div
              role="group"
              aria-label="Interface mode"
              className="inline-flex shrink-0 items-center rounded-lg border border-border bg-muted/50 p-1"
              data-testid="interface-mode-toggle"
            >
              <Button
                type="button"
                size="sm"
                variant={interfaceMode === 'bot' ? 'default' : 'outline'}
                aria-pressed={interfaceMode === 'bot'}
                onClick={() => {
                  setInterfaceMode('bot');
                  localStorage.setItem('octaos-interface-mode', 'bot');
                  window.location.assign('/app/assistant');
                }}
                className="h-8 gap-1.5 px-2.5"
                title="Use the bot-first AI workspace"
              >
                <Sparkles className="size-3.5" />
                <span className="hidden sm:inline">AI Workspace</span>
                <span className="sm:hidden">AI</span>
              </Button>
              <Button
                type="button"
                size="sm"
                variant={interfaceMode === 'classic' ? 'default' : 'ghost'}
                aria-pressed={interfaceMode === 'classic'}
                onClick={() => {
                  setInterfaceMode('classic');
                  localStorage.setItem('octaos-interface-mode', 'classic');
                  window.location.assign('/app/home');
                }}
                className="h-8 gap-1.5 px-2.5"
                title="Use the classic dashboard"
              >
                <LayoutDashboard className="size-3.5" />
                <span className="hidden sm:inline">Classic</span>
              </Button>
            </div>
            <Button variant="outline" size="sm" onClick={() => setPaletteOpen(true)} id="command-palette-btn">
              <Search className="size-3.5" />
              <span className="hidden sm:inline">Search</span>
              <span className="hidden text-xs text-muted-foreground lg:inline">⌘K</span>
            </Button>
            {approvalCount ? (
              <Link href="/app/approvals" className="hidden rounded-md border border-border bg-muted px-2 py-1 text-xs text-muted-foreground sm:inline">
                {approvalCount} to review
              </Link>
            ) : null}
            <DropdownMenu
              onOpenChange={(open) => {
                if (open) loadOrgs();
              }}
            >
              <DropdownMenuTrigger
                render={<button type="button" id="header-profile-btn" className="inline-flex h-9 items-center gap-2 rounded-md border border-border px-2 text-sm" />}
              >
                <span className="inline-flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">{initials}</span>
                <span className="hidden max-w-[140px] truncate sm:inline">{profile?.name || profile?.email || 'Account'}</span>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                <DropdownMenuLabel>
                  <div className="truncate text-sm">{profile?.name || 'Account'}</div>
                  <div className="truncate text-xs font-normal text-muted-foreground">{profile?.email}</div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => router.push('/app/settings/organization')}>
                  Organization settings
                </DropdownMenuItem>
                {orgs.filter((org) => !org.is_current).slice(0, 5).map((org) => (
                  <DropdownMenuItem key={org.tenant_id} disabled={!!switching} onClick={() => switchOrg(org.tenant_id)}>
                    {switching === org.tenant_id ? 'Switching…' : `Switch to ${org.tenant_name}`}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onClick={workspace.logout}>
                  <LogOut className="size-4" /> Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="flex-1 overflow-auto px-4 py-6 md:px-7 md:py-8"><div className="mx-auto w-full max-w-[1600px]">{children}</div></main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} profile={profile} />
    </div>
  );
}

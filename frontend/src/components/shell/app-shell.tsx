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
import { crumbForPath, visibleGroups } from '@/lib/navigation';
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

  useEffect(() => {
    if (!workspace.ready) return;
    if (!workspace.token) router.replace('/login');
  }, [workspace.ready, workspace.token, router]);

  useEffect(() => {
    const stored = localStorage.getItem('octaos-sidebar-collapsed');
    if (stored === '1') setCollapsed(true);
  }, []);

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
      <div className="flex h-12 items-center gap-2 border-b border-sidebar-border px-3">
        <Link href="/app/home" className="flex min-w-0 items-center gap-2">
          {workspace.logoUrl ? (
            <img src={workspace.logoUrl} alt="OctaOS" className="h-6 w-auto max-w-[120px] object-contain" />
          ) : (
            <span className={`truncate text-sm font-semibold ${collapsed ? 'sr-only' : ''}`}>OctaOS</span>
          )}
        </Link>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 py-3" aria-label="Primary">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <p className={`px-2 pb-1 text-xs font-medium text-muted-foreground ${collapsed ? 'sr-only' : ''}`}>{group.label}</p>
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || (item.href !== '/app/sales' && pathname.startsWith(item.href) && item.href !== '/app/home');
              const salesActive = item.href === '/app/sales' && pathname === '/app/sales';
              const isActive = item.href === '/app/sales' ? salesActive : active;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  id={`nav-${item.id}`}
                  title={item.name}
                  className={`mb-0.5 flex h-9 items-center gap-2 rounded-lg px-2.5 text-sm transition-colors ${isActive ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium border-l-2 border-primary' : 'text-muted-foreground hover:bg-surface-hover hover:text-foreground'}`}
                >
                  <Icon className="size-4 shrink-0" />
                  <span className={`truncate ${collapsed ? 'sr-only' : ''}`}>{item.name}</span>
                  {item.id === 'approvals' && approvalCount ? (
                    <span className={`ml-auto rounded-md bg-[#443A2D] text-[#D9AD68] border border-[#D9AD68]/20 px-1.5 text-xs font-semibold ${collapsed ? 'sr-only' : ''}`}>{approvalCount}</span>
                  ) : null}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="hidden border-t border-sidebar-border p-2 md:block">
        <button
          type="button"
          className="flex h-9 w-full items-center gap-2 rounded-lg px-2.5 text-sm text-muted-foreground hover:bg-surface-hover hover:text-foreground transition-colors"
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
        style={{ width: collapsed ? 64 : 240 }}
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
      <aside className={`fixed inset-y-0 left-0 z-50 w-[240px] border-r border-sidebar-border transition-transform md:hidden ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
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
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-3 md:px-4">
          <button
            type="button"
            className="inline-flex size-9 items-center justify-center rounded-md border border-border md:hidden"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="size-4" />
          </button>
          <div className="min-w-0 text-sm">
            <span className="text-muted-foreground">{crumb.section}</span>
            <span className="px-1.5 text-muted-foreground">/</span>
            <span className="font-medium">{crumb.name}</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPaletteOpen(true)} id="command-palette-btn">
              <Search className="size-3.5" />
              <span className="hidden sm:inline">Search</span>
              <span className="hidden text-xs text-muted-foreground lg:inline">⌘K</span>
            </Button>
            {approvalCount ? (
              <Link href="/app/approvals" className="hidden rounded-md border border-amber-500/30 px-2 py-1 text-xs text-amber-300 sm:inline">
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
                <span className="inline-flex size-6 items-center justify-center rounded-md bg-primary text-xs font-medium text-primary-foreground">{initials}</span>
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
        <main className="flex-1 overflow-auto p-4 md:p-6">{children}</main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} profile={profile} />
    </div>
  );
}

'use client';

import React from 'react';
import Link from 'next/link';
import { Shield, Users, Layers, ExternalLink, ArrowLeft } from 'lucide-react';
import './django-admin-theme.css';

interface DjangoAdminShellProps {
  currentTab: 'users' | 'groups' | 'permissions';
  onTabChange: (tab: 'users' | 'groups' | 'permissions') => void;
  usersCount?: number;
  groupsCount?: number;
  currentUserEmail?: string;
  onExitToWorkspace?: () => void;
  children: React.ReactNode;
}

export default function DjangoAdminShell({
  currentTab,
  onTabChange,
  usersCount = 0,
  groupsCount = 0,
  currentUserEmail = 'admin@octaos.ai',
  onExitToWorkspace,
  children,
}: DjangoAdminShellProps) {
  return (
    <div className="django-admin-container">
      {/* Authentic Django Top Header */}
      <header className="django-header">
        <div className="django-header-title">
          <Shield className="h-5 w-5 text-[#79aec8]" />
          <span>OctaOS Administration</span>
          <span className="text-[10px] font-mono tracking-widest px-2 py-0.5 rounded bg-[#1f2f3f] text-[#79aec8] border border-[#2b4156] font-normal uppercase">
            RBAC Auth
          </span>
        </div>

        <div className="django-header-links">
          <span>
            Welcome, <strong className="text-zinc-200">{currentUserEmail}</strong>.
          </span>
          {onExitToWorkspace && (
            <button
              onClick={onExitToWorkspace}
              className="flex items-center gap-1 text-[#79aec8] hover:text-white"
            >
              <ArrowLeft className="h-3 w-3" />
              Return to Workspace
            </button>
          )}
        </div>
      </header>

      {/* Django Breadcrumbs Bar */}
      <div className="django-breadcrumbs">
        <button
          onClick={() => onTabChange('users')}
          className="hover:underline text-[#79aec8]"
        >
          Home
        </button>
        <span className="sep">›</span>
        <span>Authentication and Authorization</span>
        <span className="sep">›</span>
        <span className="current capitalize">{currentTab}</span>
      </div>

      {/* Django Sub-tabs Navigation */}
      <div className="bg-[#151a24] border-b border-[#283344] px-6 flex gap-6">
        <button
          onClick={() => onTabChange('users')}
          className={`py-3 text-xs font-bold uppercase tracking-wider border-b-2 flex items-center gap-2 transition-all ${
            currentTab === 'users'
              ? 'border-[#79aec8] text-[#79aec8]'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Users className="h-3.5 w-3.5" />
          Users
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
            {usersCount}
          </span>
        </button>

        <button
          onClick={() => onTabChange('groups')}
          className={`py-3 text-xs font-bold uppercase tracking-wider border-b-2 flex items-center gap-2 transition-all ${
            currentTab === 'groups'
              ? 'border-[#79aec8] text-[#79aec8]'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Shield className="h-3.5 w-3.5" />
          Groups
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
            {groupsCount}
          </span>
        </button>

        <button
          onClick={() => onTabChange('permissions')}
          className={`py-3 text-xs font-bold uppercase tracking-wider border-b-2 flex items-center gap-2 transition-all ${
            currentTab === 'permissions'
              ? 'border-[#79aec8] text-[#79aec8]'
              : 'border-transparent text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Layers className="h-3.5 w-3.5" />
          Permissions Catalogue
        </button>
      </div>

      {/* Main Django Content Area */}
      <main className="django-main">{children}</main>
    </div>
  );
}

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Users,
  UserPlus,
  Shield,
  ShieldCheck,
  Trash2,
  Check,
  Copy,
  Loader2,
  Search,
  Filter,
  CheckCircle2,
  Lock,
  Layers,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Settings2,
} from 'lucide-react';
import { notify, confirmAction } from '@/lib/notify';

interface MembersViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
}

interface Member {
  id: string;
  name?: string | null;
  email: string;
  role: string;
  allowed_sections?: string[] | null;
  created_at?: string | null;
  last_login?: string | null;
}

const SECTIONS = [
  { id: 'knowledge', name: 'Knowledge Base' },
  { id: 'marketing', name: 'Campaign Planner' },
  { id: 'sales', name: 'Sales CRM' },
  { id: 'support', name: 'Customer Support' },
  { id: 'coordination', name: 'Agent Boardroom' },
  { id: 'ceo', name: 'CEO Workspace' },
  { id: 'orchestrator', name: 'Orchestrator AI' },
  { id: 'teams', name: 'AI Teams' },
  { id: 'marketplace', name: 'App Marketplace' },
  { id: 'hr', name: 'Hiring & HR' },
  { id: 'ai_optimization', name: 'AI Cost Control' },
];

const PERMISSIONS_MATRIX = [
  { resource: 'Campaigns & Marketing AI', admin: 'Full Control', manager: 'Create / Edit / Publish', agent: 'View / Draft', viewer: 'Read-only' },
  { resource: 'Sales CRM & Deals', admin: 'Full Control', manager: 'Create / Edit / Close', agent: 'View / Outreach', viewer: 'Read-only' },
  { resource: 'Customer Support AI', admin: 'Full Control', manager: 'Resolve / Edit Policy', agent: 'Agent Assist', viewer: 'Read-only' },
  { resource: 'Hiring & HR ATS', admin: 'Full Control', manager: 'Post / Screen / Offer', agent: 'Screen Resumes', viewer: 'Read-only' },
  { resource: 'Boardroom & Strategic Council', admin: 'Full Control', manager: 'Participate / Vote', agent: 'View Minutes', viewer: 'Read-only' },
  { resource: 'CEO Autonomous Orchestrator', admin: 'Full Control', manager: 'Trigger / Inspect', agent: 'No Access', viewer: 'No Access' },
  { resource: 'Human-in-the-Loop Approvals', admin: 'Sign-off / Reject / Revert', manager: 'Sign-off / Reject', agent: 'Draft Proposals', viewer: 'Read-only' },
  { resource: 'API Keys & Integrations', admin: 'Full Control', manager: 'View Status', agent: 'No Access', viewer: 'No Access' },
  { resource: 'Billing & Subscriptions', admin: 'Full Control', manager: 'View Invoices', agent: 'No Access', viewer: 'No Access' },
  { resource: 'Organization & Member Roles', admin: 'Full Control', manager: 'Invite Members', agent: 'No Access', viewer: 'No Access' },
];

export default function MembersView({
  token,
  API_URL,
  fetchWithAuth,
}: MembersViewProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'members' | 'matrix'>('members');
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  // Invite dialog
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('member');
  const [inviting, setInviting] = useState(false);
  const [generatedLink, setGeneratedLink] = useState('');
  const [copied, setCopied] = useState(false);

  // Edit Permissions Dialog
  const [editingMember, setEditingMember] = useState<Member | null>(null);

  useEffect(() => {
    if (token) fetchMembers();
  }, [token]);

  const fetchMembers = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members`);
      if (res.ok) {
        const data = await res.json();
        setMembers(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error('Failed to fetch members:', e);
      notify('Failed to load team members');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviting(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: inviteEmail || null, role: inviteRole }),
      });
      if (res.ok) {
        const data = await res.json();
        const absoluteUrl = `${window.location.origin}${data.invite_url}`;
        setGeneratedLink(absoluteUrl);
        notify('✅ Invitation link generated');
      } else {
        notify('Failed to generate invitation');
      }
    } catch (e) {
      console.error(e);
      notify('Network error generating invite');
    } finally {
      setInviting(false);
    }
  };

  const handleCopyInvite = () => {
    navigator.clipboard.writeText(generatedLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    const member = members.find((m) => m.id === userId);
    if (!member) return;

    // Optimistic update
    setMembers((prev) =>
      prev.map((m) => (m.id === userId ? { ...m, role: newRole } : m))
    );

    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members/${userId}/permissions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: newRole,
          allowed_sections: member.allowed_sections,
        }),
      });
      if (res.ok) {
        notify('Role updated successfully');
      } else {
        notify('Failed to update role');
        fetchMembers();
      }
    } catch (e) {
      console.error(e);
      fetchMembers();
    }
  };

  const handleToggleSection = async (sectionId: string) => {
    if (!editingMember) return;
    let allowed = editingMember.allowed_sections ? [...editingMember.allowed_sections] : [];
    if (allowed.includes(sectionId)) {
      allowed = allowed.filter((s) => s !== sectionId);
    } else {
      allowed.push(sectionId);
    }

    const updated = { ...editingMember, allowed_sections: allowed };
    setEditingMember(updated);

    // Save to server
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members/${editingMember.id}/permissions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: editingMember.role,
          allowed_sections: allowed,
        }),
      });
      if (res.ok) {
        setMembers((prev) => prev.map((m) => (m.id === editingMember.id ? updated : m)));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteMember = async (userId: string) => {
    if (!(await confirmAction('Are you sure you want to remove this member? Their access will be immediately revoked.'))) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members/${userId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setMembers((prev) => prev.filter((m) => m.id !== userId));
        notify('Member removed successfully');
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to remove member');
      }
    } catch (e) {
      console.error(e);
      notify('Network error removing member');
    }
  };

  const filteredMembers = useMemo(() => {
    return members.filter((m) => {
      if (roleFilter !== 'all' && m.role !== roleFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          m.name?.toLowerCase().includes(q) ||
          m.email?.toLowerCase().includes(q) ||
          m.role?.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [members, roleFilter, searchQuery]);

  const metrics = useMemo(() => {
    const total = members.length;
    const admins = members.filter((m) => m.role === 'admin' || m.role === 'super_admin').length;
    const standard = total - admins;
    return { total, admins, standard };
  }, [members]);

  const getInitials = (name?: string | null, email?: string) => {
    if (name) {
      const parts = name.trim().split(' ');
      if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
      return name.slice(0, 2).toUpperCase();
    }
    return (email?.slice(0, 2) || 'US').toUpperCase();
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-16">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono mb-1">
            <span>Settings</span>
            <span>/</span>
            <span className="text-zinc-200">IAM & Access Governance</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white flex items-center gap-2.5">
            Team & Access Control
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 border border-zinc-700/60 font-mono">
              {metrics.total} members
            </span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Manage enterprise user roles, single-use invitation tokens, and granular functional permissions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={() => window.location.href = '/app/admin/rbac'}
            className="h-8 bg-[#1f2f3f] hover:bg-[#283e54] text-[#79aec8] border border-[#2b4156] font-medium text-xs rounded-md px-3.5 flex items-center gap-1.5 shadow-sm"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-[#79aec8]" />
            Django Admin RBAC
          </Button>
          <Button
            onClick={() => {
              setInviteEmail('');
              setGeneratedLink('');
              setInviteModalOpen(true);
            }}
            className="h-8 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md px-3.5 flex items-center gap-1.5 shadow-sm"
          >
            <UserPlus className="w-3.5 h-3.5" />
            Invite Member
          </Button>
        </div>
      </div>

      {/* KPI Stats Strip (GCP style) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Total Organization Members</span>
            <Users className="w-3.5 h-3.5 text-zinc-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{metrics.total}</span>
            <span className="text-[11px] text-zinc-500 font-medium">Active seats</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Administrators & Owners</span>
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{metrics.admins}</span>
            <span className="text-[11px] text-indigo-400/80 font-medium">Full governance</span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-medium">Standard Operators</span>
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-white tracking-tight">{metrics.standard}</span>
            <span className="text-[11px] text-zinc-500 font-medium">Scoped permissions</span>
          </div>
        </div>
      </div>

      {/* Segmented View Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="inline-flex p-1 rounded-lg bg-zinc-900/90 border border-white/[0.08]">
          <button
            onClick={() => setActiveTab('members')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'members'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Team Directory
          </button>
          <button
            onClick={() => setActiveTab('matrix')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'matrix'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Role & Permissions Matrix
          </button>
        </div>

        {activeTab === 'members' && (
          <div className="flex items-center gap-2">
            {/* Role Filter */}
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="h-8 text-xs bg-zinc-900/60 border border-white/[0.08] text-zinc-300 rounded-md px-2.5 focus:border-zinc-500 focus:outline-none"
            >
              <option value="all">All Roles</option>
              <option value="admin">Administrators</option>
              <option value="member">Members</option>
              <option value="manager">Managers</option>
            </select>

            {/* Search */}
            <div className="relative w-full sm:w-60">
              <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name or email…"
                className="h-8 pl-8 text-xs bg-zinc-900/60 border-white/[0.08] focus:border-zinc-500 rounded-md placeholder:text-zinc-500"
              />
            </div>
          </div>
        )}
      </div>

      {/* Main Tab Content */}
      {activeTab === 'members' ? (
        <div className="rounded-xl border border-white/[0.08] bg-[#111318] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/80 border-b border-white/[0.08] text-zinc-400 font-mono uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4 font-medium">User Profile</th>
                  <th className="py-3 px-4 font-medium">System Role</th>
                  <th className="py-3 px-4 font-medium">Capability Scopes</th>
                  <th className="py-3 px-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {loading && members.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-12 text-center text-zinc-400">
                      <Loader2 className="w-5 h-5 mx-auto mb-2 animate-spin text-zinc-500" />
                      Loading team directory…
                    </td>
                  </tr>
                ) : filteredMembers.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-12 text-center text-zinc-400">
                      No members found matching your search.
                    </td>
                  </tr>
                ) : (
                  filteredMembers.map((member) => {
                    const isAdmin = member.role === 'admin' || member.role === 'super_admin';
                    const allowedCount = member.allowed_sections ? member.allowed_sections.length : SECTIONS.length;

                    return (
                      <tr key={member.id} className="hover:bg-white/[0.02] transition-colors">
                        {/* User Column */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-zinc-800 border border-white/[0.1] text-zinc-200 font-mono text-xs font-semibold flex items-center justify-center shrink-0">
                              {getInitials(member.name, member.email)}
                            </div>
                            <div className="min-w-0">
                              <div className="text-white font-medium truncate">
                                {member.name || 'Team Member'}
                              </div>
                              <div className="text-zinc-500 font-mono text-[11px] truncate">
                                {member.email}
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Role Column */}
                        <td className="py-3.5 px-4">
                          <select
                            value={member.role}
                            onChange={(e) => handleRoleChange(member.id, e.target.value)}
                            className={`text-xs font-medium rounded-md px-2.5 py-1 border focus:outline-none cursor-pointer transition-colors ${
                              isAdmin
                                ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30'
                                : 'bg-zinc-800 text-zinc-300 border-zinc-700/60'
                            }`}
                          >
                            <option value="admin">Administrator</option>
                            <option value="manager">Manager</option>
                            <option value="member">Member</option>
                            <option value="read_only">Read Only (Viewer)</option>
                          </select>
                        </td>

                        {/* Scopes Column */}
                        <td className="py-3.5 px-4">
                          {isAdmin ? (
                            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-md">
                              <ShieldCheck className="w-3 h-3" />
                              All Modules (Full Root)
                            </span>
                          ) : (
                            <button
                              onClick={() => setEditingMember(member)}
                              className="inline-flex items-center gap-1.5 text-[11px] font-mono text-zinc-300 hover:text-white bg-zinc-800/80 hover:bg-zinc-800 border border-zinc-700/60 px-2.5 py-1 rounded-md transition-colors"
                            >
                              <Settings2 className="w-3 h-3 text-zinc-400" />
                              {allowedCount} of {SECTIONS.length} Modules Authorized
                              <ChevronRight className="w-3 h-3 text-zinc-500" />
                            </button>
                          )}
                        </td>

                        {/* Actions Column */}
                        <td className="py-3.5 px-4 text-right">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeleteMember(member.id)}
                            className="h-8 w-8 p-0 text-zinc-400 hover:text-rose-400 hover:bg-rose-950/20 rounded-md"
                            title="Remove Member Access"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* GCP IAM Role Matrix View */
        <div className="rounded-xl border border-white/[0.08] bg-[#111318] overflow-hidden">
          <div className="p-4 border-b border-white/[0.08] bg-zinc-900/50">
            <h3 className="text-sm font-semibold text-white">Role-Based Access Governance Matrix</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Reference specification of canonical authorization levels across OctaOS subsystems.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-900/80 border-b border-white/[0.08] text-zinc-400 font-mono uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4 font-medium">Resource / Subsystem</th>
                  <th className="py-3 px-4 font-medium text-indigo-400">Administrator</th>
                  <th className="py-3 px-4 font-medium text-emerald-400">Manager</th>
                  <th className="py-3 px-4 font-medium text-zinc-300">Member (Agent)</th>
                  <th className="py-3 px-4 font-medium text-zinc-400">Viewer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {PERMISSIONS_MATRIX.map((row, idx) => (
                  <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-3 px-4 font-medium text-white">{row.resource}</td>
                    <td className="py-3 px-4 font-mono text-[11px] text-indigo-300">{row.admin}</td>
                    <td className="py-3 px-4 font-mono text-[11px] text-emerald-300">{row.manager}</td>
                    <td className="py-3 px-4 font-mono text-[11px] text-zinc-300">{row.agent}</td>
                    <td className="py-3 px-4 font-mono text-[11px] text-zinc-500">{row.viewer}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Invite Member Dialog (Apple/GCP Modal) */}
      <Dialog open={inviteModalOpen} onOpenChange={setInviteModalOpen}>
        <DialogContent className="sm:max-w-md bg-[#12141a] border-white/[0.08] text-white p-6 rounded-2xl shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
              <UserPlus className="w-4 h-4 text-zinc-300" />
              Invite Team Member
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Generate a cryptographically signed invitation link with predetermined role credentials.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleGenerateInvite} className="space-y-4 mt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Recipient Email (Optional)</label>
              <Input
                type="email"
                placeholder="colleague@enterprise.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="h-9 text-xs bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300">Assigned Organization Role</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="w-full h-9 text-xs bg-zinc-900 border border-white/[0.08] rounded-md px-3 text-zinc-200 focus:border-zinc-500 focus:outline-none"
              >
                <option value="member">Member (Operator)</option>
                <option value="admin">Administrator</option>
                <option value="manager">Manager</option>
                <option value="read_only">Read Only (Viewer)</option>
              </select>
            </div>

            {!generatedLink ? (
              <Button
                type="submit"
                disabled={inviting}
                className="w-full h-9 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md shadow-sm transition-all"
              >
                {inviting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                    Generating Token…
                  </>
                ) : (
                  'Create Invitation Link'
                )}
              </Button>
            ) : (
              <div className="p-3.5 bg-black/40 border border-white/[0.08] rounded-xl space-y-2 mt-4">
                <span className="text-[11px] font-mono text-emerald-400 block font-medium">
                  ✓ Token Generated (Valid for 7 days)
                </span>
                <div className="flex items-center gap-2">
                  <Input
                    readOnly
                    value={generatedLink}
                    className="h-8 text-xs font-mono bg-zinc-900 border-white/[0.08] text-zinc-300"
                  />
                  <Button
                    type="button"
                    onClick={handleCopyInvite}
                    size="sm"
                    className="h-8 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 px-3 rounded-md text-xs shrink-0"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </Button>
                </div>
              </div>
            )}
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Granular Scopes Dialog */}
      <Dialog open={!!editingMember} onOpenChange={(open) => !open && setEditingMember(null)}>
        <DialogContent className="sm:max-w-lg bg-[#12141a] border-white/[0.08] text-white p-6 rounded-2xl shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold tracking-tight text-white flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-zinc-300" />
              Authorized Modules for {editingMember?.name || editingMember?.email}
            </DialogTitle>
            <DialogDescription className="text-xs text-zinc-400">
              Enable or restrict access to specific domain agent workspaces for this user.
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4">
            {SECTIONS.map((sec) => {
              const allowed = editingMember?.allowed_sections
                ? editingMember.allowed_sections.includes(sec.id)
                : true;
              return (
                <label
                  key={sec.id}
                  className={`flex items-center gap-2.5 p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                    allowed
                      ? 'bg-zinc-900/80 border-white/[0.12] text-zinc-200 font-medium'
                      : 'bg-zinc-950/40 border-white/[0.04] text-zinc-500'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={allowed}
                    onChange={() => handleToggleSection(sec.id)}
                    className="rounded border-zinc-700 text-indigo-600 focus:ring-0 bg-zinc-900"
                  />
                  <span>{sec.name}</span>
                </label>
              );
            })}
          </div>

          <div className="flex justify-end mt-4 pt-3 border-t border-white/[0.08]">
            <Button
              onClick={() => setEditingMember(null)}
              className="h-8 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md px-4"
            >
              Done
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

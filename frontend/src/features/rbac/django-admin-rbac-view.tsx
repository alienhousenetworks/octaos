'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { notify } from '@/lib/notify';
import DjangoAdminShell from './django-admin-shell';
import DjangoAdminUsersList, { RBACUserItem } from './django-admin-users-list';
import DjangoAdminUserForm, { UserDetailRBAC } from './django-admin-user-form';
import DjangoAdminGroupsList, { RBACGroup } from './django-admin-groups-list';
import DjangoAdminGroupForm from './django-admin-group-form';
import { FilterItem } from './filter-horizontal';

interface DjangoAdminRBACViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  currentUserEmail?: string;
}

export default function DjangoAdminRBACView({
  token,
  API_URL,
  fetchWithAuth,
  currentUserEmail,
}: DjangoAdminRBACViewProps) {
  const router = useRouter();

  // Navigation tab
  const [currentTab, setCurrentTab] = useState<'users' | 'groups' | 'permissions'>('users');

  // Selected item for edit form (null means list view)
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [isAddingGroup, setIsAddingGroup] = useState<boolean>(false);

  // Data states
  const [users, setUsers] = useState<RBACUserItem[]>([]);
  const [groups, setGroups] = useState<RBACGroup[]>([]);
  const [permissions, setPermissions] = useState<FilterItem[]>([]);
  const [groupedPermissions, setGroupedPermissions] = useState<Record<string, any[]>>({});

  // Form detailed data
  const [selectedUserDetail, setSelectedUserDetail] = useState<UserDetailRBAC | null>(null);
  const [selectedGroupDetail, setSelectedGroupDetail] = useState<any | null>(null);

  // Status states
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [djangoMessage, setDjangoMessage] = useState<string | null>(null);

  const showDjangoMessage = (msg: string) => {
    setDjangoMessage(msg);
    setTimeout(() => setDjangoMessage(null), 5000);
  };

  // 1. Fetch initial permissions, groups, and users
  const loadData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [pRes, gRes, uRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/rbac/permissions`),
        fetchWithAuth(`${API_URL}/rbac/groups`),
        fetchWithAuth(`${API_URL}/rbac/users`),
      ]);

      if (pRes.ok) {
        const pData = await pRes.json();
        const formatted: FilterItem[] = (pData.permissions || []).map((p: any) => ({
          id: p.id,
          name: p.name,
          subtitle: p.content_type,
        }));
        setPermissions(formatted);
        setGroupedPermissions(pData.grouped || {});
      }

      if (gRes.ok) {
        const gData = await gRes.json();
        setGroups(Array.isArray(gData) ? gData : []);
      }

      if (uRes.ok) {
        const uData = await uRes.json();
        setUsers(Array.isArray(uData) ? uData : []);
      }
    } catch (err) {
      console.error('Failed to load RBAC data:', err);
    } finally {
      setLoading(false);
    }
  }, [token, API_URL, fetchWithAuth]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load user details when editing
  useEffect(() => {
    if (!editingUserId || !token) return;
    const fetchUser = async () => {
      try {
        const res = await fetchWithAuth(`${API_URL}/rbac/users/${editingUserId}`);
        if (res.ok) {
          const data = await res.json();
          setSelectedUserDetail(data);
        }
      } catch (e) {
        console.error('Failed to fetch user RBAC:', e);
      }
    };
    fetchUser();
  }, [editingUserId, token, API_URL, fetchWithAuth]);

  // Load group details when editing
  useEffect(() => {
    if (!editingGroupId || !token) return;
    const fetchGroup = async () => {
      try {
        const res = await fetchWithAuth(`${API_URL}/rbac/groups/${editingGroupId}`);
        if (res.ok) {
          const data = await res.json();
          setSelectedGroupDetail(data);
        }
      } catch (e) {
        console.error('Failed to fetch group RBAC:', e);
      }
    };
    fetchGroup();
  }, [editingGroupId, token, API_URL, fetchWithAuth]);

  // Available groups for user filter_horizontal
  const availableGroupsFilterItems: FilterItem[] = groups.map((g) => ({
    id: g.id,
    name: g.name,
    subtitle: `${g.permissions_count} perms`,
  }));

  // Handle Save User
  const handleSaveUser = async (updated: Partial<UserDetailRBAC>, exitAfter: boolean) => {
    if (!editingUserId) return;
    setSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/rbac/users/${editingUserId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated),
      });
      if (res.ok) {
        const data = await res.json();
        showDjangoMessage(`The user "${data.email}" was changed successfully.`);
        await loadData();
        if (exitAfter) {
          setEditingUserId(null);
          setSelectedUserDetail(null);
        } else {
          // Refresh current user detail
          const refreshed = await fetchWithAuth(`${API_URL}/rbac/users/${editingUserId}`);
          if (refreshed.ok) setSelectedUserDetail(await refreshed.json());
        }
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to update user.');
      }
    } catch (e) {
      console.error(e);
      notify('Network error updating user.');
    } finally {
      setSaving(false);
    }
  };

  // Handle Save Group
  const handleSaveGroup = async (groupPayload: any, exitAfter: boolean) => {
    setSaving(true);
    const isEdit = !!groupPayload.id;
    const url = isEdit
      ? `${API_URL}/rbac/groups/${groupPayload.id}`
      : `${API_URL}/rbac/groups`;
    const method = isEdit ? 'PUT' : 'POST';

    try {
      const res = await fetchWithAuth(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(groupPayload),
      });

      if (res.ok) {
        const saved = await res.json();
        showDjangoMessage(
          `The group "${saved.name}" was ${isEdit ? 'changed' : 'added'} successfully.`
        );
        await loadData();

        if (exitAfter) {
          setEditingGroupId(null);
          setIsAddingGroup(false);
          setSelectedGroupDetail(null);
        } else {
          if (!isEdit) {
            setEditingGroupId(saved.id);
            setIsAddingGroup(false);
          }
          const refreshed = await fetchWithAuth(`${API_URL}/rbac/groups/${saved.id}`);
          if (refreshed.ok) setSelectedGroupDetail(await refreshed.json());
        }
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to save group.');
      }
    } catch (e) {
      console.error(e);
      notify('Network error saving group.');
    } finally {
      setSaving(false);
    }
  };

  // Handle Delete Group
  const handleDeleteGroup = async (groupId: string, name?: string) => {
    if (!window.confirm(`Are you sure you want to delete the group "${name || 'this group'}"?`)) {
      return;
    }
    try {
      const res = await fetchWithAuth(`${API_URL}/rbac/groups/${groupId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        showDjangoMessage(`The group was deleted successfully.`);
        setEditingGroupId(null);
        setIsAddingGroup(false);
        await loadData();
      } else {
        notify('Failed to delete group.');
      }
    } catch (e) {
      console.error(e);
      notify('Network error deleting group.');
    }
  };

  // Handle Bulk Action on Users
  const handleBulkUserAction = async (action: string, userIds: string[], groupId?: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/rbac/users/bulk-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, user_ids: userIds, group_id: groupId }),
      });
      if (res.ok) {
        const result = await res.json();
        showDjangoMessage(result.message || 'Action executed successfully.');
        await loadData();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to execute bulk action.');
      }
    } catch (e) {
      console.error(e);
      notify('Network error executing bulk action.');
    }
  };

  return (
    <DjangoAdminShell
      currentTab={currentTab}
      onTabChange={(tab) => {
        setCurrentTab(tab);
        setEditingUserId(null);
        setEditingGroupId(null);
        setIsAddingGroup(false);
      }}
      usersCount={users.length}
      groupsCount={groups.length}
      currentUserEmail={currentUserEmail}
      onExitToWorkspace={() => router.push('/app/settings/members')}
    >
      {/* Django Success Alert Message Bar */}
      {djangoMessage && (
        <div className="mb-4 px-4 py-2.5 bg-[#12281a] border border-[#1f582f] text-[#64b99a] rounded text-xs flex items-center gap-2 shadow-sm">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span className="font-medium">{djangoMessage}</span>
        </div>
      )}

      {/* VIEW: Users Tab */}
      {currentTab === 'users' && (
        <>
          {editingUserId && selectedUserDetail ? (
            <DjangoAdminUserForm
              user={selectedUserDetail}
              availableGroups={availableGroupsFilterItems}
              availablePermissions={permissions}
              saving={saving}
              onSave={handleSaveUser}
              onCancel={() => {
                setEditingUserId(null);
                setSelectedUserDetail(null);
              }}
            />
          ) : (
            <DjangoAdminUsersList
              users={users}
              allGroups={groups}
              loading={loading}
              onSelectUser={(uId) => setEditingUserId(uId)}
              onBulkAction={handleBulkUserAction}
            />
          )}
        </>
      )}

      {/* VIEW: Groups Tab */}
      {currentTab === 'groups' && (
        <>
          {editingGroupId || isAddingGroup ? (
            <DjangoAdminGroupForm
              initialGroup={selectedGroupDetail}
              availablePermissions={permissions}
              saving={saving}
              onSave={handleSaveGroup}
              onDelete={handleDeleteGroup}
              onCancel={() => {
                setEditingGroupId(null);
                setIsAddingGroup(false);
                setSelectedGroupDetail(null);
              }}
            />
          ) : (
            <DjangoAdminGroupsList
              groups={groups}
              loading={loading}
              onSelectGroup={(gId) => setEditingGroupId(gId)}
              onAddGroup={() => {
                setSelectedGroupDetail(null);
                setIsAddingGroup(true);
              }}
              onDeleteGroup={handleDeleteGroup}
            />
          )}
        </>
      )}

      {/* VIEW: Permissions Matrix Catalogue */}
      {currentTab === 'permissions' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white uppercase tracking-wider">
              System Permissions Catalogue ({permissions.length} total)
            </h2>
            <span className="text-xs font-mono text-zinc-400">
              Read-only core registry
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(groupedPermissions).map(([domain, domainPerms]) => (
              <div key={domain} className="django-fieldset">
                <div className="django-legend flex items-center justify-between">
                  <span className="capitalize">{domain} Module</span>
                  <span className="text-[11px] font-mono lowercase text-[#79aec8]">
                    {domainPerms.length} perms
                  </span>
                </div>

                <div className="space-y-2">
                  {domainPerms.map((p) => (
                    <div
                      key={p.id}
                      className="p-2.5 rounded bg-[#0f131a] border border-[#1f2735] text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-200">{p.name}</span>
                        <code className="text-[10px] text-[#79aec8] font-mono bg-zinc-900 px-1.5 py-0.5 rounded">
                          {p.codename}
                        </code>
                      </div>
                      <p className="text-[11px] text-zinc-400">{p.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </DjangoAdminShell>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import { ArrowLeft, Save, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import FilterHorizontal, { FilterItem } from './filter-horizontal';

export interface UserDetailRBAC {
  id: string;
  name?: string;
  email: string;
  phone_no?: string;
  department?: string;
  role: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  group_ids: string[];
  user_permission_ids: string[];
  effective_permissions_count?: number;
}

interface DjangoAdminUserFormProps {
  user: UserDetailRBAC;
  availableGroups: FilterItem[];
  availablePermissions: FilterItem[];
  saving: boolean;
  onSave: (updated: Partial<UserDetailRBAC>, exitAfter: boolean) => Promise<void>;
  onCancel: () => void;
}

export default function DjangoAdminUserForm({
  user,
  availableGroups,
  availablePermissions,
  saving,
  onSave,
  onCancel,
}: DjangoAdminUserFormProps) {
  const [name, setName] = useState(user.name || '');
  const [department, setDepartment] = useState(user.department || '');
  const [role, setRole] = useState(user.role || 'member');
  const [isStaff, setIsStaff] = useState(user.is_staff);
  const [isSuperuser, setIsSuperuser] = useState(user.is_superuser);
  const [isActive, setIsActive] = useState(user.is_active);
  const [groupIds, setGroupIds] = useState<string[]>(user.group_ids || []);
  const [userPermissionIds, setUserPermissionIds] = useState<string[]>(
    user.user_permission_ids || []
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setName(user.name || '');
    setDepartment(user.department || '');
    setRole(user.role || 'member');
    setIsStaff(user.is_staff);
    setIsSuperuser(user.is_superuser);
    setIsActive(user.is_active);
    setGroupIds(user.group_ids || []);
    setUserPermissionIds(user.user_permission_ids || []);
  }, [user]);

  const handleSubmit = async (e: React.FormEvent, exitAfter: boolean) => {
    e.preventDefault();
    setError(null);

    await onSave(
      {
        name: name.trim(),
        department: department.trim(),
        role: role.trim(),
        is_staff: isStaff,
        is_superuser: isSuperuser,
        is_active: isActive,
        group_ids: groupIds,
        user_permission_ids: userPermissionIds,
      },
      exitAfter
    );
  };

  return (
    <form onSubmit={(e) => handleSubmit(e, true)} className="space-y-6">
      {/* Top Breadcrumbs / Header */}
      <div className="flex items-center justify-between pb-3 border-b border-zinc-700/60">
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onCancel}
            className="h-8 px-2 text-zinc-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Users
          </Button>
          <h2 className="text-lg font-bold text-white">
            Change user: <span className="text-[#60a5fa]">{user.email}</span>
          </h2>
        </div>

        {user.effective_permissions_count !== undefined && (
          <span className="text-xs font-mono text-zinc-400 px-2.5 py-1 rounded bg-zinc-800 border border-zinc-700">
            {user.effective_permissions_count} active permissions
          </span>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded text-xs flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Fieldset 1: Personal info */}
      <div className="django-fieldset">
        <div className="django-legend">Personal info</div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="django-form-row mb-0">
            <label className="django-label">Name:</label>
            <Input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="First and last name"
              className="h-9 text-xs bg-[#0b0e14] border-zinc-700 text-zinc-100"
            />
          </div>

          <div className="django-form-row mb-0">
            <label className="django-label">Email address:</label>
            <Input
              type="email"
              disabled
              value={user.email}
              className="h-9 text-xs bg-zinc-900 border-zinc-800 text-zinc-400 cursor-not-allowed"
            />
          </div>

          <div className="django-form-row mb-0">
            <label className="django-label">Department:</label>
            <Input
              type="text"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              placeholder="e.g. Sales, HR, Marketing, Engineering"
              className="h-9 text-xs bg-[#0b0e14] border-zinc-700 text-zinc-100"
            />
            <p className="django-help-text">
              Primary organizational placement (e.g. Sales, HR, Marketing, Operations).
            </p>
          </div>

          <div className="django-form-row mb-0">
            <label className="django-label">Base Role:</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full h-9 text-xs bg-[#0b0e14] border border-zinc-700 rounded px-2.5 text-zinc-100"
            >
              <option value="member">member</option>
              <option value="admin">admin</option>
              <option value="sales_agent">sales_agent</option>
              <option value="manager">manager</option>
              <option value="executive">executive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Fieldset 2: Permissions (Django style) */}
      <div className="django-fieldset space-y-6">
        <div className="django-legend">Permissions</div>

        {/* Checkboxes */}
        <div className="space-y-3.5">
          <div className="flex items-start gap-2.5">
            <input
              type="checkbox"
              id="id_is_active"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="mt-0.5 rounded border-zinc-700 bg-zinc-900"
            />
            <div>
              <label htmlFor="id_is_active" className="text-xs font-bold text-zinc-200 cursor-pointer">
                Active
              </label>
              <p className="django-help-text">
                Designates whether this user should be treated as active. Unselect this instead of deleting accounts.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <input
              type="checkbox"
              id="id_is_staff"
              checked={isStaff}
              onChange={(e) => setIsStaff(e.target.checked)}
              className="mt-0.5 rounded border-zinc-700 bg-zinc-900"
            />
            <div>
              <label htmlFor="id_is_staff" className="text-xs font-bold text-zinc-200 cursor-pointer">
                Staff status
              </label>
              <p className="django-help-text">
                Designates whether the user can log into this admin site.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <input
              type="checkbox"
              id="id_is_superuser"
              checked={isSuperuser}
              onChange={(e) => setIsSuperuser(e.target.checked)}
              className="mt-0.5 rounded border-zinc-700 bg-zinc-900"
            />
            <div>
              <label htmlFor="id_is_superuser" className="text-xs font-bold text-zinc-200 cursor-pointer">
                Superuser status
              </label>
              <p className="django-help-text">
                Designates that this user has all permissions without explicitly assigning them.
              </p>
            </div>
          </div>
        </div>

        {/* Groups dual-listbox */}
        <div className="pt-2 border-t border-zinc-800">
          <div className="text-xs font-bold text-zinc-200 mb-2">Groups</div>
          <FilterHorizontal
            title="groups"
            availableItems={availableGroups}
            chosenItemIds={groupIds}
            onChange={setGroupIds}
            helpText="The groups this user belongs to. A user will get all permissions granted to each of their groups."
          />
        </div>

        {/* User permissions dual-listbox */}
        <div className="pt-2 border-t border-zinc-800">
          <div className="text-xs font-bold text-zinc-200 mb-2">User permissions</div>
          <FilterHorizontal
            title="user permissions"
            availableItems={availablePermissions}
            chosenItemIds={userPermissionIds}
            onChange={setUserPermissionIds}
            helpText="Specific individual permissions granted directly to this user, regardless of their groups."
          />
        </div>
      </div>

      {/* Django Sticky Submit Row */}
      <div className="django-submit-row">
        <div />

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={saving}
            onClick={(e) => handleSubmit(e, false)}
            className="h-8 text-xs bg-zinc-800 border-zinc-700 hover:bg-zinc-700 text-zinc-200"
          >
            Save and continue editing
          </Button>

          <Button
            type="submit"
            size="sm"
            disabled={saving}
            className="h-8 px-4 text-xs font-semibold bg-[#417690] hover:bg-[#205067] text-white rounded shadow-sm flex items-center gap-1.5"
          >
            <Save className="h-3.5 w-3.5" />
            Save
          </Button>
        </div>
      </div>
    </form>
  );
}

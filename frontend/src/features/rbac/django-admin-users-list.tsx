'use client';

import React, { useState, useMemo } from 'react';
import { Search, CheckCircle2, XCircle, Shield, Users, Filter, Check, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export interface RBACUserItem {
  id: string;
  name?: string;
  email: string;
  department?: string;
  role: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  groups: { id: string; name: string }[];
  permissions_count: number;
}

interface DjangoAdminUsersListProps {
  users: RBACUserItem[];
  allGroups: { id: string; name: string }[];
  loading: boolean;
  onSelectUser: (userId: string) => void;
  onBulkAction: (action: string, userIds: string[], groupId?: string) => Promise<void>;
}

export default function DjangoAdminUsersList({
  users,
  allGroups,
  loading,
  onSelectUser,
  onBulkAction,
}: DjangoAdminUsersListProps) {
  const [search, setSearch] = useState('');
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(new Set());

  // Filter state (Django list_filter)
  const [filterDepartment, setFilterDepartment] = useState<string>('all');
  const [filterGroup, setFilterGroup] = useState<string>('all');
  const [filterStaff, setFilterStaff] = useState<string>('all'); // all, yes, no
  const [filterSuperuser, setFilterSuperuser] = useState<string>('all'); // all, yes, no
  const [filterActive, setFilterActive] = useState<string>('all'); // all, yes, no

  // Action dropdown state
  const [actionChoice, setActionChoice] = useState<string>('');
  const [targetGroupForAction, setTargetGroupForAction] = useState<string>('');

  // Extract unique departments
  const availableDepartments = useMemo(() => {
    const depts = new Set<string>();
    users.forEach((u) => {
      if (u.department) depts.add(u.department);
    });
    return Array.from(depts).sort();
  }, [users]);

  // Apply filters
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      // 1. Text search
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchesName = u.name?.toLowerCase().includes(q);
        const matchesEmail = u.email.toLowerCase().includes(q);
        const matchesDept = u.department?.toLowerCase().includes(q);
        if (!matchesName && !matchesEmail && !matchesDept) return false;
      }

      // 2. Department filter
      if (filterDepartment !== 'all') {
        if ((u.department || 'General').toLowerCase() !== filterDepartment.toLowerCase()) {
          return false;
        }
      }

      // 3. Group filter
      if (filterGroup !== 'all') {
        const hasGroup = u.groups.some((g) => g.id === filterGroup);
        if (!hasGroup) return false;
      }

      // 4. Staff filter
      if (filterStaff === 'yes' && !u.is_staff) return false;
      if (filterStaff === 'no' && u.is_staff) return false;

      // 5. Superuser filter
      if (filterSuperuser === 'yes' && !u.is_superuser) return false;
      if (filterSuperuser === 'no' && u.is_superuser) return false;

      // 6. Active filter
      if (filterActive === 'yes' && !u.is_active) return false;
      if (filterActive === 'no' && u.is_active) return false;

      return true;
    });
  }, [
    users,
    search,
    filterDepartment,
    filterGroup,
    filterStaff,
    filterSuperuser,
    filterActive,
  ]);

  // Select all / toggle row
  const toggleSelectAll = () => {
    if (selectedUserIds.size === filteredUsers.length) {
      setSelectedUserIds(new Set());
    } else {
      setSelectedUserIds(new Set(filteredUsers.map((u) => u.id)));
    }
  };

  const toggleSelectUser = (id: string) => {
    setSelectedUserIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Run bulk action
  const handleRunAction = async () => {
    if (!actionChoice || selectedUserIds.size === 0) return;
    await onBulkAction(
      actionChoice,
      Array.from(selectedUserIds),
      targetGroupForAction || undefined
    );
    setSelectedUserIds(new Set());
    setActionChoice('');
  };

  return (
    <div className="space-y-4">
      {/* Top Search & Actions Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
          <Input
            type="text"
            placeholder="Search email, name, or department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9 text-xs bg-[#151a24] border-zinc-700/80 text-zinc-200"
          />
        </div>

        {/* Django Actions Bar */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-400 font-medium">Action:</span>
          <select
            value={actionChoice}
            onChange={(e) => setActionChoice(e.target.value)}
            className="h-8 text-xs bg-[#151a24] border border-zinc-700 rounded px-2.5 text-zinc-200"
          >
            <option value="">---------</option>
            <option value="activate">Activate selected users</option>
            <option value="deactivate">Deactivate selected users</option>
            <option value="assign_group">Assign to group...</option>
            <option value="delete">Delete selected users</option>
          </select>

          {actionChoice === 'assign_group' && (
            <select
              value={targetGroupForAction}
              onChange={(e) => setTargetGroupForAction(e.target.value)}
              className="h-8 text-xs bg-[#151a24] border border-zinc-700 rounded px-2 text-zinc-200"
            >
              <option value="">Select target group</option>
              {allGroups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          )}

          <Button
            size="sm"
            onClick={handleRunAction}
            disabled={!actionChoice || selectedUserIds.size === 0}
            className="h-8 px-3 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700"
          >
            Go
          </Button>

          <span className="text-xs text-zinc-400 font-mono ml-1">
            {selectedUserIds.size} of {filteredUsers.length} selected
          </span>
        </div>
      </div>

      {/* Main Grid: Table on Left, Filter Sidebar on Right (classic Django list_filter layout) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left Column: Changelist Table */}
        <div className="lg:col-span-3 space-y-3">
          <div className="django-table-container">
            <table className="django-table">
              <thead>
                <tr>
                  <th className="w-8 text-center">
                    <input
                      type="checkbox"
                      checked={
                        filteredUsers.length > 0 &&
                        selectedUserIds.size === filteredUsers.length
                      }
                      onChange={toggleSelectAll}
                      className="rounded border-zinc-700 bg-zinc-900"
                    />
                  </th>
                  <th>Username / Email</th>
                  <th>Name</th>
                  <th>Department</th>
                  <th className="text-center w-20">Staff</th>
                  <th className="text-center w-20">Superuser</th>
                  <th className="text-center w-20">Active</th>
                  <th>Assigned Groups</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-zinc-400">
                      Loading user accounts...
                    </td>
                  </tr>
                ) : filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-zinc-500 italic">
                      No matching users found.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => {
                    const isSelected = selectedUserIds.has(u.id);
                    return (
                      <tr key={u.id} className={isSelected ? 'bg-zinc-800/40' : ''}>
                        <td className="text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectUser(u.id)}
                            className="rounded border-zinc-700 bg-zinc-900"
                          />
                        </td>
                        <td>
                          <button
                            onClick={() => onSelectUser(u.id)}
                            className="font-bold text-[#60a5fa] hover:underline text-left"
                          >
                            {u.email}
                          </button>
                        </td>
                        <td className="text-zinc-200">{u.name || '—'}</td>
                        <td>
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold border ${
                              u.department?.toLowerCase() === 'sales'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : u.department?.toLowerCase() === 'hr'
                                ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                                : u.department?.toLowerCase() === 'marketing'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                : 'bg-zinc-800 text-zinc-400 border-zinc-700/60'
                            }`}
                          >
                            {u.department || 'General'}
                          </span>
                        </td>
                        <td className="text-center">
                          {u.is_staff ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400 mx-auto" />
                          ) : (
                            <Minus className="h-4 w-4 text-zinc-600 mx-auto" />
                          )}
                        </td>
                        <td className="text-center">
                          {u.is_superuser ? (
                            <CheckCircle2 className="h-4 w-4 text-[#79aec8] mx-auto" />
                          ) : (
                            <Minus className="h-4 w-4 text-zinc-600 mx-auto" />
                          )}
                        </td>
                        <td className="text-center">
                          {u.is_active ? (
                            <Check className="h-4 w-4 text-emerald-400 mx-auto" />
                          ) : (
                            <XCircle className="h-4 w-4 text-rose-400 mx-auto" />
                          )}
                        </td>
                        <td>
                          <div className="flex gap-1 flex-wrap">
                            {u.groups.length > 0 ? (
                              u.groups.map((g) => (
                                <span
                                  key={g.id}
                                  className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono bg-[#1c2734] text-[#79aec8] border border-[#28394b]"
                                >
                                  {g.name}
                                </span>
                              ))
                            ) : (
                              <span className="text-zinc-600 text-xs italic">None</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="text-xs text-zinc-400 font-mono">
            {filteredUsers.length} {filteredUsers.length === 1 ? 'user' : 'users'}
          </div>
        </div>

        {/* Right Column: Django list_filter Sidebar */}
        <div className="django-filter-box">
          <h2>Filter</h2>

          {/* By Department */}
          <div>
            <h3>By department</h3>
            <ul>
              <li className={filterDepartment === 'all' ? 'selected' : ''}>
                <button onClick={() => setFilterDepartment('all')}>All</button>
              </li>
              {availableDepartments.map((dept) => (
                <li
                  key={dept}
                  className={filterDepartment.toLowerCase() === dept.toLowerCase() ? 'selected' : ''}
                >
                  <button onClick={() => setFilterDepartment(dept)}>{dept}</button>
                </li>
              ))}
            </ul>
          </div>

          {/* By Group */}
          <div>
            <h3>By group</h3>
            <ul>
              <li className={filterGroup === 'all' ? 'selected' : ''}>
                <button onClick={() => setFilterGroup('all')}>All</button>
              </li>
              {allGroups.map((g) => (
                <li key={g.id} className={filterGroup === g.id ? 'selected' : ''}>
                  <button onClick={() => setFilterGroup(g.id)}>{g.name}</button>
                </li>
              ))}
            </ul>
          </div>

          {/* By Staff Status */}
          <div>
            <h3>By staff status</h3>
            <ul>
              <li className={filterStaff === 'all' ? 'selected' : ''}>
                <button onClick={() => setFilterStaff('all')}>All</button>
              </li>
              <li className={filterStaff === 'yes' ? 'selected' : ''}>
                <button onClick={() => setFilterStaff('yes')}>Yes</button>
              </li>
              <li className={filterStaff === 'no' ? 'selected' : ''}>
                <button onClick={() => setFilterStaff('no')}>No</button>
              </li>
            </ul>
          </div>

          {/* By Superuser Status */}
          <div>
            <h3>By superuser status</h3>
            <ul>
              <li className={filterSuperuser === 'all' ? 'selected' : ''}>
                <button onClick={() => setFilterSuperuser('all')}>All</button>
              </li>
              <li className={filterSuperuser === 'yes' ? 'selected' : ''}>
                <button onClick={() => setFilterSuperuser('yes')}>Yes</button>
              </li>
              <li className={filterSuperuser === 'no' ? 'selected' : ''}>
                <button onClick={() => setFilterSuperuser('no')}>No</button>
              </li>
            </ul>
          </div>

          {/* By Active Status */}
          <div>
            <h3>By active</h3>
            <ul>
              <li className={filterActive === 'all' ? 'selected' : ''}>
                <button onClick={() => setFilterActive('all')}>All</button>
              </li>
              <li className={filterActive === 'yes' ? 'selected' : ''}>
                <button onClick={() => setFilterActive('yes')}>Yes</button>
              </li>
              <li className={filterActive === 'no' ? 'selected' : ''}>
                <button onClick={() => setFilterActive('no')}>No</button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useMemo } from 'react';
import { Search, Plus, Trash2, Edit2, Shield, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export interface RBACGroup {
  id: string;
  name: string;
  description?: string;
  members_count: number;
  permissions_count: number;
  permission_ids: string[];
  updated_at?: string;
}

interface DjangoAdminGroupsListProps {
  groups: RBACGroup[];
  loading: boolean;
  onSelectGroup: (groupId: string) => void;
  onAddGroup: () => void;
  onDeleteGroup: (groupId: string, name: string) => void;
}

export default function DjangoAdminGroupsList({
  groups,
  loading,
  onSelectGroup,
  onAddGroup,
  onDeleteGroup,
}: DjangoAdminGroupsListProps) {
  const [search, setSearch] = useState('');

  const filteredGroups = useMemo(() => {
    if (!search.trim()) return groups;
    const q = search.toLowerCase();
    return groups.filter(
      (g) =>
        g.name.toLowerCase().includes(q) ||
        (g.description && g.description.toLowerCase().includes(q))
    );
  }, [groups, search]);

  return (
    <div className="space-y-4">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
          <Input
            type="text"
            placeholder="Search groups..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9 text-xs bg-[#151a24] border-zinc-700/80 text-zinc-200"
          />
        </div>

        <Button
          onClick={onAddGroup}
          className="h-9 px-3.5 bg-[#417690] hover:bg-[#205067] text-white text-xs font-semibold rounded flex items-center gap-1.5 shadow-sm"
        >
          <Plus className="h-4 w-4" />
          Add group
        </Button>
      </div>

      {/* Table */}
      <div className="django-table-container">
        <table className="django-table">
          <thead>
            <tr>
              <th className="w-1/3">Group name</th>
              <th>Description</th>
              <th className="text-center w-28">Members</th>
              <th className="text-center w-28">Permissions</th>
              <th className="text-right w-24">Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-zinc-400">
                  Loading groups...
                </td>
              </tr>
            ) : filteredGroups.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-zinc-500 italic">
                  {groups.length === 0 ? 'No groups configured.' : 'No matching groups found.'}
                </td>
              </tr>
            ) : (
              filteredGroups.map((g) => (
                <tr key={g.id}>
                  <td>
                    <button
                      onClick={() => onSelectGroup(g.id)}
                      className="font-bold text-[#60a5fa] hover:underline flex items-center gap-2 text-left"
                    >
                      <Shield className="h-3.5 w-3.5 text-[#79aec8]" />
                      {g.name}
                    </button>
                  </td>
                  <td className="text-zinc-400 text-xs truncate max-w-xs">
                    {g.description || '—'}
                  </td>
                  <td className="text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-800 text-zinc-300 border border-zinc-700/60">
                      <Users className="h-3 w-3" />
                      {g.members_count}
                    </span>
                  </td>
                  <td className="text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-[#1c2734] text-[#79aec8] border border-[#28394b]">
                      {g.permissions_count} perms
                    </span>
                  </td>
                  <td className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onSelectGroup(g.id)}
                        className="text-zinc-400 hover:text-zinc-200"
                        title="Edit group"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => onDeleteGroup(g.id, g.name)}
                        className="text-rose-400/80 hover:text-rose-400"
                        title="Delete group"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-zinc-400 font-mono">
        {filteredGroups.length} {filteredGroups.length === 1 ? 'group' : 'groups'} total
      </div>
    </div>
  );
}

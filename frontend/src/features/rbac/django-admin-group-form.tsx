'use client';

import React, { useState, useEffect } from 'react';
import { ArrowLeft, Save, Trash2, Check, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import FilterHorizontal, { FilterItem } from './filter-horizontal';

interface GroupDetail {
  id?: string;
  name: string;
  description?: string;
  permission_ids: string[];
}

interface DjangoAdminGroupFormProps {
  initialGroup?: GroupDetail | null;
  availablePermissions: FilterItem[];
  saving: boolean;
  onSave: (group: GroupDetail, exitAfter: boolean) => Promise<void>;
  onDelete?: (groupId: string) => Promise<void>;
  onCancel: () => void;
}

export default function DjangoAdminGroupForm({
  initialGroup,
  availablePermissions,
  saving,
  onSave,
  onDelete,
  onCancel,
}: DjangoAdminGroupFormProps) {
  const [name, setName] = useState(initialGroup?.name || '');
  const [description, setDescription] = useState(initialGroup?.description || '');
  const [permissionIds, setPermissionIds] = useState<string[]>(
    initialGroup?.permission_ids || []
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialGroup) {
      setName(initialGroup.name || '');
      setDescription(initialGroup.description || '');
      setPermissionIds(initialGroup.permission_ids || []);
    }
  }, [initialGroup]);

  const handleSubmit = async (e: React.FormEvent, exitAfter: boolean) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Group name is required.');
      return;
    }
    setError(null);

    await onSave(
      {
        id: initialGroup?.id,
        name: name.trim(),
        description: description.trim(),
        permission_ids: permissionIds,
      },
      exitAfter
    );
  };

  return (
    <form onSubmit={(e) => handleSubmit(e, true)} className="space-y-6">
      {/* Top Breadcrumb Header */}
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
            Back to Groups
          </Button>
          <h2 className="text-lg font-bold text-white">
            {initialGroup?.id ? `Change group: ${initialGroup.name}` : 'Add group'}
          </h2>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded text-xs flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Fieldset: Group Information */}
      <div className="django-fieldset">
        <div className="django-legend">Group Information</div>

        <div className="django-form-row">
          <label className="django-label">
            Name: <span className="text-rose-400">*</span>
          </label>
          <Input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Sales Team, HR & Talent Team, Marketing Ops"
            className="max-w-md h-9 text-xs bg-[#0b0e14] border-zinc-700 text-zinc-100"
          />
          <p className="django-help-text">Unique name for this role or functional department.</p>
        </div>

        <div className="django-form-row mb-0">
          <label className="django-label">Description:</label>
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief explanation of roles and responsibilities..."
            className="max-w-xl text-xs bg-[#0b0e14] border-zinc-700 text-zinc-100"
          />
        </div>
      </div>

      {/* Fieldset: Permissions (Dual Listbox) */}
      <div className="django-fieldset">
        <div className="django-legend">Permissions</div>
        <FilterHorizontal
          title="permissions"
          availableItems={availablePermissions}
          chosenItemIds={permissionIds}
          onChange={setPermissionIds}
          helpText="Hold down Cmd/Ctrl to select multiple items, or click the arrows to move between columns. Double-click items to quickly transfer."
        />
      </div>

      {/* Django Sticky Submit Row */}
      <div className="django-submit-row">
        <div>
          {initialGroup?.id && onDelete && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onDelete(initialGroup.id!)}
              className="h-8 text-xs bg-rose-950/40 text-rose-300 border-rose-800/40 hover:bg-rose-900/40 hover:text-rose-200"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Delete
            </Button>
          )}
        </div>

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

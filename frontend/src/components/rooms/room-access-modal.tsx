'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { notify } from '@/lib/notify';
import {
  Shield,
  Users,
  Globe,
  Lock,
  Building2,
  Copy,
  Check,
  UserPlus,
  Trash2,
  Crown,
  Loader2,
  ExternalLink,
} from 'lucide-react';

export interface RoomMember {
  user_id: string;
  name: string;
  email: string;
  role: 'viewer' | 'editor' | 'admin';
  added_at?: string;
}

export interface SectionRoomData {
  id: string;
  section: string;
  name: string;
  slug: string;
  description?: string;
  status: string;
  visibility: 'internal_public' | 'private' | 'public';
  share_token?: string | null;
  access_list: RoomMember[];
  data?: Record<string, any>;
  created_by_user_id?: string;
  creator_name?: string;
  creator_email?: string;
  created_at?: string;
}

interface RoomAccessModalProps {
  isOpen: boolean;
  onClose: () => void;
  room: SectionRoomData | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onRoomUpdated?: (updatedRoom: SectionRoomData) => void;
}

export default function RoomAccessModal({
  isOpen,
  onClose,
  room,
  API_URL,
  fetchWithAuth,
  onRoomUpdated,
}: RoomAccessModalProps) {
  const [visibility, setVisibility] = useState<'internal_public' | 'private' | 'public'>('internal_public');
  const [accessList, setAccessList] = useState<RoomMember[]>([]);
  const [staffList, setStaffList] = useState<any[]>([]);
  const [selectedStaffId, setSelectedStaffId] = useState<string>('');
  const [selectedRole, setSelectedRole] = useState<'viewer' | 'editor'>('editor');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copiedInternal, setCopiedInternal] = useState(false);
  const [copiedPublic, setCopiedPublic] = useState(false);

  useEffect(() => {
    if (room) {
      setVisibility(room.visibility || 'internal_public');
      setAccessList(room.access_list || []);
    }
  }, [room]);

  useEffect(() => {
    if (isOpen) {
      fetchStaff();
    }
  }, [isOpen]);

  const fetchStaff = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/rooms/staff`);
      if (res.ok) {
        const data = await res.json();
        setStaffList(data);
      }
    } catch (err) {
      console.error('Failed to load staff list:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!room) return null;

  const handleAddMember = () => {
    if (!selectedStaffId) return;
    const staff = staffList.find((s) => s.id === selectedStaffId);
    if (!staff) return;

    if (accessList.some((m) => m.user_id === staff.id)) {
      notify('Staff member already has access');
      return;
    }

    const newMember: RoomMember = {
      user_id: staff.id,
      name: staff.name,
      email: staff.email,
      role: selectedRole,
      added_at: new Date().toISOString(),
    };

    setAccessList([...accessList, newMember]);
    setSelectedStaffId('');
    notify(`Added ${staff.name} as ${selectedRole}`);
  };

  const handleRemoveMember = (userId: string) => {
    setAccessList(accessList.filter((m) => m.user_id !== userId));
  };

  const handleRoleChange = (userId: string, nextRole: 'viewer' | 'editor') => {
    setAccessList(accessList.map((m) => (m.user_id === userId ? { ...m, role: nextRole } : m)));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/rooms/${room.id}/access`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          visibility,
          access_list: accessList,
        }),
      });

      if (res.ok) {
        const updated = await res.json();
        notify('Room access permissions updated successfully');
        onRoomUpdated?.(updated);
        onClose();
      } else {
        const err = await res.json();
        notify(err.detail || 'Failed to update access permissions');
      }
    } catch (err) {
      console.error(err);
      notify('Network error updating room permissions');
    } finally {
      setSaving(false);
    }
  };

  const getInternalLink = () => {
    if (typeof window === 'undefined') return '';
    return `${window.location.origin}/app/${room.section}/rooms/${room.slug}`;
  };

  const getPublicLink = () => {
    if (typeof window === 'undefined') return '';
    const tokenPart = room.share_token ? `?token=${room.share_token}` : '';
    return `${window.location.origin}/app/${room.section}/rooms/${room.slug}${tokenPart}`;
  };

  const copyToClipboard = (text: string, isPub = false) => {
    navigator.clipboard.writeText(text);
    if (isPub) {
      setCopiedPublic(true);
      setTimeout(() => setCopiedPublic(false), 2000);
    } else {
      setCopiedInternal(true);
      setTimeout(() => setCopiedInternal(false), 2000);
    }
    notify('Link copied to clipboard');
  };

  const availableStaff = staffList.filter(
    (s) => s.id !== room.created_by_user_id && !accessList.some((m) => m.user_id === s.id)
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-slate-900 border-slate-800 text-slate-100">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold">Room Access & Sharing</DialogTitle>
              <DialogDescription className="text-slate-400 text-xs">
                Manage who can discover, view, and collaborate inside <span className="font-semibold text-slate-200">{room.name}</span> (#{room.slug})
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-3">
          {/* General Access Level */}
          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 space-y-3">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Lock className="w-3.5 h-3.5 text-indigo-400" /> General Visibility
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setVisibility('internal_public')}
                className={`p-3 rounded-lg border text-left transition-all ${
                  visibility === 'internal_public'
                    ? 'border-indigo-500 bg-indigo-500/10 text-slate-100'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 font-medium text-sm text-slate-200 mb-1">
                  <Building2 className="w-4 h-4 text-indigo-400" /> Internal Staff
                </div>
                <div className="text-[11px] text-slate-400 leading-snug">
                  Anyone in your organization with section access can open this room.
                </div>
              </button>

              <button
                type="button"
                onClick={() => setVisibility('private')}
                className={`p-3 rounded-lg border text-left transition-all ${
                  visibility === 'private'
                    ? 'border-amber-500 bg-amber-500/10 text-slate-100'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 font-medium text-sm text-slate-200 mb-1">
                  <Lock className="w-4 h-4 text-amber-400" /> Private Room
                </div>
                <div className="text-[11px] text-slate-400 leading-snug">
                  Only the creator and invited staff members can access.
                </div>
              </button>

              <button
                type="button"
                onClick={() => setVisibility('public')}
                className={`p-3 rounded-lg border text-left transition-all ${
                  visibility === 'public'
                    ? 'border-emerald-500 bg-emerald-500/10 text-slate-100'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 font-medium text-sm text-slate-200 mb-1">
                  <Globe className="w-4 h-4 text-emerald-400" /> Public Link
                </div>
                <div className="text-[11px] text-slate-400 leading-snug">
                  Anyone with the share link can view and participate.
                </div>
              </button>
            </div>
          </div>

          {/* Members List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Users className="w-3.5 h-3.5 text-indigo-400" /> People With Access
              </label>
              <span className="text-xs text-slate-400">
                {1 + accessList.length} member{1 + accessList.length > 1 ? 's' : ''}
              </span>
            </div>

            <div className="divide-y divide-slate-800/80 rounded-xl border border-slate-800 bg-slate-950/60 max-h-56 overflow-y-auto">
              {/* Creator / Owner */}
              <div className="p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center font-bold text-xs">
                    <Crown className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-slate-200 flex items-center gap-2">
                      {room.creator_name || 'Organization Staff'}
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Owner
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">{room.creator_email || 'Workspace Owner'}</div>
                  </div>
                </div>
                <div className="text-xs text-slate-400 font-medium">Full Manager</div>
              </div>

              {/* Explicitly Added Staff */}
              {accessList.map((member) => (
                <div key={member.user_id} className="p-3 flex items-center justify-between hover:bg-slate-900/40">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center justify-center font-semibold text-xs uppercase">
                      {(member.name || member.email || 'U')[0]}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-200">{member.name || member.email}</div>
                      <div className="text-xs text-slate-400">{member.email}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Select
                      value={member.role}
                      onValueChange={(val) => {
                        if (val) handleRoleChange(member.user_id, val as 'viewer' | 'editor');
                      }}
                    >
                      <SelectTrigger className="h-8 w-28 bg-slate-900 border-slate-700 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-slate-800 text-slate-200">
                        <SelectItem value="editor">Editor</SelectItem>
                        <SelectItem value="viewer">Viewer</SelectItem>
                      </SelectContent>
                    </Select>
                    <button
                      type="button"
                      onClick={() => handleRemoveMember(member.user_id)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Remove access"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}

              {accessList.length === 0 && (
                <div className="p-4 text-center text-xs text-slate-500">
                  No additional staff members added yet. Add colleagues below.
                </div>
              )}
            </div>

            {/* Add Member Row */}
            <div className="flex items-center gap-2 pt-1">
              <Select value={selectedStaffId} onValueChange={(val) => setSelectedStaffId(val || '')}>
                <SelectTrigger className="flex-1 bg-slate-950 border-slate-800 text-slate-200 text-xs h-9">
                  <SelectValue placeholder="Add colleague from organization..." />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800 text-slate-200">
                  {availableStaff.length === 0 ? (
                    <div className="p-2 text-xs text-slate-500 text-center">All active staff already added</div>
                  ) : (
                    availableStaff.map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>
                        {staff.name} ({staff.email})
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>

              <Select
                value={selectedRole}
                onValueChange={(val) => {
                  if (val) setSelectedRole(val as 'viewer' | 'editor');
                }}
              >
                <SelectTrigger className="w-28 bg-slate-950 border-slate-800 text-slate-200 text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-slate-800 text-slate-200">
                  <SelectItem value="editor">Editor</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddMember}
                disabled={!selectedStaffId}
                className="h-9 px-3 gap-1.5 bg-indigo-600/20 text-indigo-300 border-indigo-500/30 hover:bg-indigo-600/30"
              >
                <UserPlus className="w-3.5 h-3.5" /> Add
              </Button>
            </div>
          </div>

          {/* Share Links */}
          <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => copyToClipboard(getInternalLink(), false)}
                className="text-xs text-slate-300 hover:text-white gap-1.5 h-8 border border-slate-800"
              >
                {copiedInternal ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
                Copy Internal Link
              </Button>

              {visibility === 'public' && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(getPublicLink(), true)}
                  className="text-xs text-emerald-400 hover:text-emerald-300 gap-1.5 h-8 border border-emerald-500/20 bg-emerald-500/10"
                >
                  {copiedPublic ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />}
                  Copy Public Link
                </Button>
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={saving}
            className="bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
            Save & Update Access
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

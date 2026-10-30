'use client';

import React, { useState } from 'react';
import {
  Folder,
  FolderOpen,
  Calendar,
  User,
  Lock,
  Globe,
  Building2,
  Share2,
  ChevronDown,
  LayoutGrid,
  Check,
  Plus,
  Trash2,
} from 'lucide-react';
import { notify, confirmAction } from '@/lib/notify';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import RoomAccessModal, { SectionRoomData } from '@/components/rooms/room-access-modal';

interface RoomHeaderProps {
  sectionTitle: string;
  activeRoom: SectionRoomData;
  allRooms: SectionRoomData[];
  onSelectRoom: (slug: string) => void;
  onOpenDirectory: () => void;
  onCreateNewRoom: () => void;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onRoomUpdated?: (updated: SectionRoomData) => void;
}

const SECTION_THEMES: Record<string, { badge: string; accent: string; iconBg: string }> = {
  hr: {
    badge: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    accent: 'text-purple-400',
    iconBg: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  },
  marketing: {
    badge: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    accent: 'text-sky-400',
    iconBg: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
  },
  sales: {
    badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    accent: 'text-emerald-400',
    iconBg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  },
  support: {
    badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    accent: 'text-amber-400',
    iconBg: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  },
};

export default function RoomHeader({
  sectionTitle,
  activeRoom,
  allRooms,
  onSelectRoom,
  onOpenDirectory,
  onCreateNewRoom,
  API_URL,
  fetchWithAuth,
  onRoomUpdated,
}: RoomHeaderProps) {
  const [isShareOpen, setIsShareOpen] = useState(false);
  const theme = SECTION_THEMES[activeRoom.section] || SECTION_THEMES.hr;

  const formatDate = (isoString?: string) => {
    if (!isoString) return 'Recent';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <>
      <div className="border-b border-border/70 bg-card/60 px-4 py-2 sm:px-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          {/* Left: Folder Breadcrumb & Info */}
          <div className="flex items-center gap-2.5 min-w-0">
            <div className={`p-1.5 rounded-lg border flex items-center justify-center shrink-0 shadow-xs ${theme.iconBg}`}>
              <FolderOpen className="w-4 h-4" />
            </div>

            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={onOpenDirectory}
                  className="text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                >
                  {sectionTitle} Folders
                </button>
                <span className="text-muted-foreground/60 text-xs">/</span>

                {/* Switcher Dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger className="group flex items-center gap-1.5 text-sm sm:text-base font-semibold text-foreground hover:text-primary transition-colors cursor-pointer outline-none">
                    <span className="truncate">{activeRoom.name}</span>
                    <ChevronDown className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-transform shrink-0" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-64 bg-popover border-border text-foreground shadow-xl">
                    <DropdownMenuLabel className="text-[11px] text-muted-foreground uppercase tracking-wider">
                      Switch {sectionTitle} Room
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator className="bg-border" />
                    {allRooms.map((room) => (
                      <DropdownMenuItem
                        key={room.id}
                        onClick={() => onSelectRoom(room.slug)}
                        className={`flex items-center justify-between cursor-pointer text-xs py-2 ${
                          room.slug === activeRoom.slug ? 'bg-indigo-600/20 text-indigo-300 font-semibold' : 'text-slate-300'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <Folder className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="truncate">{room.name}</span>
                        </div>
                        {room.slug === activeRoom.slug && <Check className="w-3.5 h-3.5 text-indigo-400 shrink-0" />}
                      </DropdownMenuItem>
                    ))}
                    <DropdownMenuSeparator className="bg-slate-800" />
                    <DropdownMenuItem
                      onClick={onCreateNewRoom}
                      className="text-xs text-indigo-400 cursor-pointer font-medium py-2 gap-2"
                    >
                      <Plus className="w-3.5 h-3.5" /> Create New Room
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={onOpenDirectory}
                      className="text-xs text-slate-400 cursor-pointer py-1.5 gap-2"
                    >
                      <LayoutGrid className="w-3.5 h-3.5" /> View Folder Directory
                    </DropdownMenuItem>
                    {activeRoom.slug !== 'default' && (
                      <>
                        <DropdownMenuSeparator className="bg-slate-800" />
                        <DropdownMenuItem
                          onClick={async () => {
                            const confirmed = await confirmAction(
                              `Are you sure you want to delete folder "${activeRoom.name}"? Records will be safely unlinked.`
                            );
                            if (!confirmed) return;
                            try {
                              const res = await fetchWithAuth(`${API_URL}/rooms/${activeRoom.id}?permanent=true`, {
                                method: 'DELETE',
                              });
                              if (res.ok) {
                                notify(`Deleted folder "${activeRoom.name}"`);
                                onOpenDirectory();
                              } else {
                                const err = await res.json().catch(() => ({}));
                                notify(err.detail || 'Failed to delete folder');
                              }
                            } catch {
                              notify('Error deleting folder');
                            }
                          }}
                          className="text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 cursor-pointer py-1.5 gap-2"
                        >
                          <Trash2 className="w-3.5 h-3.5" /> Delete This Folder
                        </DropdownMenuItem>
                      </>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* Slug Badge */}
                <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-medium bg-slate-800/80 text-slate-300 border border-slate-700">
                  #{activeRoom.slug}
                </span>

                {/* Visibility Badge */}
                {activeRoom.visibility === 'private' ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                    <Lock className="w-2.5 h-2.5" /> Private
                  </span>
                ) : activeRoom.visibility === 'public' ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <Globe className="w-2.5 h-2.5" /> Public
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1">
                    <Building2 className="w-2.5 h-2.5" /> Internal
                  </span>
                )}
              </div>

              {/* Sub-meta: Creator & Creation Date */}
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
                <span className="flex items-center gap-1.5">
                  <User className="w-3 h-3 text-slate-500" />
                  <span>
                    Created by{' '}
                    <strong className="text-slate-300 font-medium">
                      {activeRoom.creator_name || 'Staff Member'}
                    </strong>
                  </span>
                </span>
                <span className="text-slate-600">•</span>
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-3 h-3 text-slate-500" />
                  <span>{formatDate(activeRoom.created_at)}</span>
                </span>
                {activeRoom.description && (
                  <>
                    <span className="text-slate-600">•</span>
                    <span className="text-slate-400 truncate max-w-xs">{activeRoom.description}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2 shrink-0 self-end md:self-auto">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsShareOpen(true)}
              className="h-7 px-2.5 text-xs gap-1.5"
            >
              <Share2 className="w-3.5 h-3.5 text-primary" />
              <span>Share & Access</span>
            </Button>

            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onOpenDirectory}
              className="h-7 px-2.5 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>All Folders</span>
            </Button>
          </div>
        </div>
      </div>

      <RoomAccessModal
        isOpen={isShareOpen}
        onClose={() => setIsShareOpen(false)}
        room={activeRoom}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onRoomUpdated={onRoomUpdated}
      />
    </>
  );
}

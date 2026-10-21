'use client';

import React, { useState, useEffect } from 'react';
import {
  Folder,
  FolderPlus,
  Search,
  Lock,
  Globe,
  Building2,
  Calendar,
  User,
  Share2,
  ArrowRight,
  Sparkles,
  Briefcase,
  Megaphone,
  TrendingUp,
  Headphones,
  Check,
  X,
  Loader2,
  Clock,
  Layers,
  Filter,
  Trash2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { notify, confirmAction } from '@/lib/notify';
import RoomAccessModal, { SectionRoomData } from '@/components/rooms/room-access-modal';

interface RoomFolderExplorerProps {
  section: 'hr' | 'marketing' | 'sales' | 'support';
  sectionTitle: string;
  rooms: SectionRoomData[];
  loading: boolean;
  onSelectRoom: (slug: string) => void;
  onRefresh: () => Promise<void>;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

const SECTION_CONFIG = {
  hr: {
    icon: Briefcase,
    accent: 'purple',
    gradient: 'from-purple-600/20 via-slate-900 to-slate-950',
    borderHover: 'hover:border-purple-500/50',
    itemUnit: 'Candidates',
    defaultRole: 'Senior Full Stack Engineer',
    defaultReqs: 'Python, FastAPI, React, TypeScript, PostgreSQL',
  },
  marketing: {
    icon: Megaphone,
    accent: 'sky',
    gradient: 'from-sky-600/20 via-slate-900 to-slate-950',
    borderHover: 'hover:border-sky-500/50',
    itemUnit: 'Posts',
    defaultRole: 'Omnichannel Launch Campaign',
    defaultReqs: 'LinkedIn, Twitter, Product Hunt',
  },
  sales: {
    icon: TrendingUp,
    accent: 'emerald',
    gradient: 'from-emerald-600/20 via-slate-900 to-slate-950',
    borderHover: 'hover:border-emerald-500/50',
    itemUnit: 'Deals',
    defaultRole: 'Enterprise Account Outreach',
    defaultReqs: 'Target B2B SaaS Accounts',
  },
  support: {
    icon: Headphones,
    accent: 'amber',
    gradient: 'from-amber-600/20 via-slate-900 to-slate-950',
    borderHover: 'hover:border-amber-500/50',
    itemUnit: 'Tickets',
    defaultRole: 'Tier-1 Technical Escalation',
    defaultReqs: 'SLA < 1hr, Multi-channel web & email',
  },
};

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export default function RoomFolderExplorer({
  section,
  sectionTitle,
  rooms,
  loading,
  onSelectRoom,
  onRefresh,
  API_URL,
  fetchWithAuth,
}: RoomFolderExplorerProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived'>('all');
  const [shareRoom, setShareRoom] = useState<SectionRoomData | null>(null);

  // New Room Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [isCustomSlug, setIsCustomSlug] = useState(false);
  const [newDescription, setNewDescription] = useState('');
  const [newVisibility, setNewVisibility] = useState<'internal_public' | 'private' | 'public'>('internal_public');
  const [creating, setCreating] = useState(false);

  // Section Specific Fields
  const [field1, setField1] = useState('');
  const [field2, setField2] = useState('');
  const [field3, setField3] = useState('');

  const config = SECTION_CONFIG[section] || SECTION_CONFIG.hr;
  const SectionIcon = config.icon;

  useEffect(() => {
    if (!isCustomSlug && newName) {
      setNewSlug(slugify(newName));
    }
  }, [newName, isCustomSlug]);

  const handleOpenCreateModal = () => {
    setNewName('');
    setNewSlug('');
    setIsCustomSlug(false);
    setNewDescription('');
    setNewVisibility('internal_public');
    if (section === 'hr') {
      setField1('Senior AI / Full Stack Engineer');
      setField2('Python, React, TypeScript, PostgreSQL, LLM APIs');
      setField3('$140,000/year');
    } else if (section === 'marketing') {
      setField1('Product Launch & Brand Awareness');
      setField2('Early Adopter Tech Executives');
      setField3('LinkedIn, Twitter/X, Instagram');
    } else if (section === 'sales') {
      setField1('Mid-Market & Enterprise Accounts');
      setField2('SaaS / Cloud Infrastructure');
      setField3('$50,000 - $150,000 ARR');
    } else {
      setField1('Tier-1 Inbound Queue');
      setField2('Web Widget, Email & Chat');
      setField3('SLA Target: 2 hours');
    }
    setIsCreateOpen(true);
  };

  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) {
      notify('Please enter a room name');
      return;
    }

    setCreating(true);
    try {
      const roomData: Record<string, any> = {};
      if (section === 'hr') {
        roomData.role = field1;
        roomData.requirements = field2;
        roomData.salary = field3;
      } else if (section === 'marketing') {
        roomData.goal = field1;
        roomData.audience = field2;
        roomData.channels = field3;
      } else if (section === 'sales') {
        roomData.target_tier = field1;
        roomData.industry = field2;
        roomData.deal_size = field3;
      } else {
        roomData.queue_name = field1;
        roomData.channels = field2;
        roomData.sla = field3;
      }

      const res = await fetchWithAuth(`${API_URL}/rooms/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section,
          name: newName.trim(),
          slug: newSlug.trim() || undefined,
          description: newDescription.trim() || undefined,
          visibility: newVisibility,
          data: roomData,
        }),
      });

      if (res.ok) {
        const created = await res.json();
        notify(`Created room "${created.name}"`);
        setIsCreateOpen(false);
        await onRefresh();
        onSelectRoom(created.slug);
      } else {
        const err = await res.json();
        notify(err.detail || 'Failed to create room');
      }
    } catch (err) {
      console.error(err);
      notify('Network error creating room');
    } finally {
      setCreating(false);
    }
  };

  const filteredRooms = rooms.filter((r) => {
    if (statusFilter !== 'all' && r.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchName = r.name.toLowerCase().includes(q);
      const matchSlug = r.slug.toLowerCase().includes(q);
      const matchDesc = (r.description || '').toLowerCase().includes(q);
      const matchCreator = (r.creator_name || '').toLowerCase().includes(q);
      if (!matchName && !matchSlug && !matchDesc && !matchCreator) return false;
    }
    return true;
  });

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
    <div className="space-y-6 p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className={`p-6 rounded-2xl border border-slate-800 bg-gradient-to-r ${config.gradient} shadow-lg relative overflow-hidden`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-slate-800/80 text-slate-300 border border-slate-700">
                Department Workspace
              </span>
              <span className="text-xs text-slate-400">
                {rooms.length} {rooms.length === 1 ? 'Room' : 'Rooms'}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100 flex items-center gap-3">
              <SectionIcon className="w-8 h-8 text-indigo-400" />
              {sectionTitle} Folders & Rooms
            </h1>
            <p className="text-sm text-slate-300/80 max-w-2xl">
              Create and manage dedicated rooms for each hiring process, campaign launch, sales deal, or service queue. Every room has its own unique slug, creation history, and folder access controls.
            </p>
          </div>

          <Button
            type="button"
            onClick={handleOpenCreateModal}
            className="self-start md:self-auto bg-indigo-600 hover:bg-indigo-500 text-white shadow-md gap-2 h-10 px-4"
          >
            <FolderPlus className="w-4 h-4" />
            <span>Create New Room</span>
          </Button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search ${sectionTitle} rooms by name, slug, or creator...`}
            className="pl-9 bg-slate-900 border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 h-9"
          />
        </div>

        <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-lg border border-slate-800 self-start sm:self-auto">
          {(['all', 'active', 'archived'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setStatusFilter(tab)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors ${
                statusFilter === tab
                  ? 'bg-slate-800 text-slate-100 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Folders Grid */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-400 gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
          <span className="text-xs">Loading {sectionTitle} rooms...</span>
        </div>
      ) : filteredRooms.length === 0 ? (
        <div className="py-16 text-center border-2 border-dashed border-slate-800/80 rounded-2xl bg-slate-950/40 p-8 space-y-3">
          <div className="w-12 h-12 rounded-xl bg-slate-900 text-slate-400 border border-slate-800 flex items-center justify-center mx-auto">
            <Folder className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-200">No rooms found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {search ? 'Try clearing your search query or filter.' : `Create your first ${sectionTitle} room to get started.`}
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleOpenCreateModal}
            className="gap-1.5 text-xs bg-slate-900 border-slate-700 text-slate-200 hover:bg-slate-800"
          >
            <FolderPlus className="w-3.5 h-3.5" /> Create Room
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredRooms.map((room) => {
            const counts = (room as any).counts || { total: 0, active: 0 };
            return (
              <div
                key={room.id}
                className="group relative rounded-xl border border-slate-800/80 bg-slate-900/70 hover:bg-slate-900 transition-all duration-200 shadow-md flex flex-col justify-between overflow-hidden hover:border-slate-700"
              >
                {/* Folder Tab Top Visual */}
                <div className="h-1.5 w-full bg-gradient-to-r from-indigo-500/40 via-purple-500/40 to-transparent" />

                <div className="p-4 space-y-3">
                  {/* Top Bar: Icon, Slug & Visibility */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center shrink-0">
                        <Folder className="w-5 h-5" />
                      </div>
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-950 text-slate-300 border border-slate-800">
                        #{room.slug}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {room.visibility === 'private' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                          <Lock className="w-2.5 h-2.5" /> Private
                        </span>
                      ) : room.visibility === 'public' ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                          <Globe className="w-2.5 h-2.5" /> Public
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1">
                          <Building2 className="w-2.5 h-2.5" /> Internal
                        </span>
                      )}

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setShareRoom(room);
                        }}
                        className="p-1.5 rounded-md text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                        title="Share & Access Permissions"
                      >
                        <Share2 className="w-3.5 h-3.5" />
                      </button>

                      {room.slug !== 'default' && (
                        <button
                          type="button"
                          onClick={async (e) => {
                            e.stopPropagation();
                            const confirmed = await confirmAction(
                              `Are you sure you want to delete folder "${room.name}"? Any leads, deals, or records inside it will be safely unlinked.`
                            );
                            if (!confirmed) return;
                            try {
                              const res = await fetchWithAuth(`${API_URL}/rooms/${room.id}?permanent=true`, {
                                method: 'DELETE',
                              });
                              if (res.ok) {
                                notify(`Deleted folder "${room.name}"`);
                                await onRefresh();
                              } else {
                                const err = await res.json().catch(() => ({}));
                                notify(err.detail || 'Failed to delete folder');
                              }
                            } catch {
                              notify('Network error deleting folder');
                            }
                          }}
                          className="p-1.5 rounded-md text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                          title="Delete Folder"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Room Name & Description */}
                  <div>
                    <h3 className="text-base font-bold text-slate-100 group-hover:text-indigo-400 transition-colors line-clamp-1">
                      {room.name}
                    </h3>
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1 min-h-[32px]">
                      {room.description || `Dedicated room workspace for ${room.name}.`}
                    </p>
                  </div>

                  {/* Metrics Badge */}
                  <div className="flex items-center gap-2 pt-1">
                    <span className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-slate-950/80 text-slate-300 border border-slate-800/80 flex items-center gap-1.5">
                      <Layers className="w-3 h-3 text-indigo-400" />
                      <span>
                        <strong className="text-slate-100 font-semibold">{counts.total}</strong> {config.itemUnit}
                      </span>
                      {counts.active > 0 && (
                        <span className="text-slate-500">({counts.active} active)</span>
                      )}
                    </span>
                  </div>

                  {/* Meta: Creator & Creation Date */}
                  <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="flex items-center gap-1 truncate max-w-[140px]" title={room.creator_name || 'Staff'}>
                      <User className="w-3 h-3 text-slate-500 shrink-0" />
                      <span className="truncate">{room.creator_name || 'Staff'}</span>
                    </span>

                    <span className="flex items-center gap-1 shrink-0">
                      <Calendar className="w-3 h-3 text-slate-500" />
                      <span>{formatDate(room.created_at)}</span>
                    </span>
                  </div>
                </div>

                {/* Open Room Action Footer */}
                <button
                  type="button"
                  onClick={() => onSelectRoom(room.slug)}
                  className="w-full py-2.5 px-4 bg-slate-950/60 hover:bg-indigo-600/10 border-t border-slate-800 text-xs font-semibold text-slate-300 hover:text-indigo-300 flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>Open Room Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Share Modal */}
      <RoomAccessModal
        isOpen={!!shareRoom}
        onClose={() => setShareRoom(null)}
        room={shareRoom}
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onRoomUpdated={async () => {
          await onRefresh();
        }}
      />

      {/* Create Room Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-xl bg-slate-900 border-slate-800 text-slate-100">
          <form onSubmit={handleCreateRoom}>
            <DialogHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <FolderPlus className="w-5 h-5" />
                </div>
                <div>
                  <DialogTitle className="text-xl font-bold">Create New {sectionTitle} Room</DialogTitle>
                  <DialogDescription className="text-slate-400 text-xs">
                    Create a dedicated workspace folder with a unique slug and scoped data.
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* Room Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Room Name *</label>
                <Input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer Hiring"
                  required
                  className="bg-slate-950 border-slate-800 text-xs text-slate-100 h-9"
                />
              </div>

              {/* Slug Preview / Input */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-slate-300">Unique URL Slug *</label>
                  <button
                    type="button"
                    onClick={() => setIsCustomSlug(!isCustomSlug)}
                    className="text-[11px] text-indigo-400 hover:underline"
                  >
                    {isCustomSlug ? 'Auto-generate from name' : 'Customize slug'}
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-mono">/app/{section}/rooms/</span>
                  <Input
                    value={newSlug}
                    onChange={(e) => {
                      setIsCustomSlug(true);
                      setNewSlug(slugify(e.target.value));
                    }}
                    placeholder="senior-backend-engineer"
                    required
                    className="flex-1 bg-slate-950 border-slate-800 text-xs font-mono text-slate-200 h-9"
                  />
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Description (Optional)</label>
                <Textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Summary of this room workspace, target goals, or team notes..."
                  rows={2}
                  className="bg-slate-950 border-slate-800 text-xs text-slate-100 resize-none"
                />
              </div>

              {/* Visibility */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Initial Access Level</label>
                <Select
                  value={newVisibility}
                  onValueChange={(val) => {
                    if (val) setNewVisibility(val as 'internal_public' | 'private' | 'public');
                  }}
                >
                  <SelectTrigger className="bg-slate-950 border-slate-800 text-xs text-slate-200 h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-800 text-slate-200">
                    <SelectItem value="internal_public">
                      🏢 Internal Staff (Everyone in your organization with section access)
                    </SelectItem>
                    <SelectItem value="private">
                      🔒 Private / Restricted (Only you and invited staff members)
                    </SelectItem>
                    <SelectItem value="public">
                      🌐 Public (Accessible via external share link)
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Section Specific Preset Fields */}
              <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 space-y-3">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Initial {sectionTitle} Parameters
                </div>

                {section === 'hr' && (
                  <>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Job Role Title</label>
                      <Input
                        value={field1}
                        onChange={(e) => setField1(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Key Requirements / Skills</label>
                      <Input
                        value={field2}
                        onChange={(e) => setField2(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Target Salary / Budget</label>
                      <Input
                        value={field3}
                        onChange={(e) => setField3(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                  </>
                )}

                {section === 'marketing' && (
                  <>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Campaign Objective</label>
                      <Input
                        value={field1}
                        onChange={(e) => setField1(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Target Audience</label>
                      <Input
                        value={field2}
                        onChange={(e) => setField2(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Distribution Channels</label>
                      <Input
                        value={field3}
                        onChange={(e) => setField3(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                  </>
                )}

                {section === 'sales' && (
                  <>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Target Account / Tier</label>
                      <Input
                        value={field1}
                        onChange={(e) => setField1(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Industry / Vertical</label>
                      <Input
                        value={field2}
                        onChange={(e) => setField2(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Target Deal Value</label>
                      <Input
                        value={field3}
                        onChange={(e) => setField3(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                  </>
                )}

                {section === 'support' && (
                  <>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Queue Name</label>
                      <Input
                        value={field1}
                        onChange={(e) => setField1(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">Active Channels</label>
                      <Input
                        value={field2}
                        onChange={(e) => setField2(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] text-slate-300">SLA Response Target</label>
                      <Input
                        value={field3}
                        onChange={(e) => setField3(e.target.value)}
                        className="bg-slate-900 border-slate-800 text-xs h-8"
                      />
                    </div>
                  </>
                )}
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button type="button" variant="ghost" size="sm" onClick={() => setIsCreateOpen(false)} disabled={creating}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={creating} className="bg-indigo-600 hover:bg-indigo-500 text-white gap-1.5">
                {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FolderPlus className="w-3.5 h-3.5" />}
                Create & Open Room
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

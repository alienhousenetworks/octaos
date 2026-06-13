'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Users, Plus, Trash2, Shield, Check, Copy, Loader2 } from 'lucide-react';

interface MembersViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
}

export default function MembersView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
}: MembersViewProps) {
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteLink, setInviteLink] = useState('');
  const [inviting, setInviting] = useState(false);
  const [copied, setCopied] = useState(false);

  const sectionsList = [
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

  useEffect(() => {
    if (token) {
      fetchMembers();
    }
  }, [token]);

  const fetchMembers = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members`);
      if (res.ok) {
        const data = await res.json();
        setMembers(data);
      }
    } catch (e) {
      console.error("Failed to fetch members:", e);
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
        body: JSON.stringify({ email: inviteEmail || null })
      });
      if (res.ok) {
        const data = await res.json();
        const absoluteUrl = `${window.location.origin}${data.invite_url}`;
        setInviteLink(absoluteUrl);
        setInviteEmail('');
      } else {
        alert("Failed to generate invitation");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setInviting(false);
    }
  };

  const handleCopyInvite = () => {
    navigator.clipboard.writeText(inviteLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    const member = members.find(m => m.id === userId);
    if (!member) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members/${userId}/permissions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: newRole,
          allowed_sections: member.allowed_sections
        })
      });
      if (res.ok) {
        fetchMembers();
      } else {
        alert("Failed to update role");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSectionToggle = async (userId: string, sectionId: string) => {
    const member = members.find(m => m.id === userId);
    if (!member) return;
    
    let allowed = member.allowed_sections ? [...member.allowed_sections] : [];
    if (allowed.includes(sectionId)) {
      allowed = allowed.filter(s => s !== sectionId);
    } else {
      allowed.push(sectionId);
    }

    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members/${userId}/permissions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: member.role,
          allowed_sections: allowed
        })
      });
      if (res.ok) {
        fetchMembers();
      } else {
        alert("Failed to update permissions");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteMember = async (userId: string) => {
    if (!confirm("Are you sure you want to remove this member?")) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/members/${userId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchMembers();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to remove member");
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Users className="text-rose-450 h-8 w-8" /> Members & Access control
          </h1>
          <p className="text-gray-400 mt-1">Manage team members, generate invitation links, and customize vertical permissions.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Invite Generator */}
        <Card className="glass-panel border-violet-500/20 rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between h-fit">
          <div>
            <h3 className="font-extrabold text-lg text-white mb-2">Invite New Member</h3>
            <p className="text-xs text-gray-400 mb-4">Generate a unique link to invite a team member to join your organization.</p>
            
            <form onSubmit={handleGenerateInvite} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Target Email (Optional)</label>
                <Input
                  placeholder="team@company.com"
                  type="email"
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20"
                />
              </div>
              <Button 
                type="submit" 
                disabled={inviting}
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold h-11 rounded-xl shadow-lg shadow-violet-500/20 transition-all text-xs"
              >
                {inviting ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
                Generate Invitation Link
              </Button>
            </form>

            {inviteLink && (
              <div className="mt-6 p-4 bg-gray-950/60 border border-violet-500/20 rounded-xl space-y-2.5">
                <label className="text-[10px] font-bold text-violet-400 uppercase tracking-wider block">Invite Link Created</label>
                <div className="flex gap-2">
                  <Input 
                    readOnly
                    value={inviteLink}
                    className="bg-gray-900/60 border-gray-800 text-xs text-gray-300 font-mono"
                  />
                  <Button 
                    size="icon" 
                    onClick={handleCopyInvite}
                    className="bg-gray-850 hover:bg-gray-800 text-gray-300 rounded-xl"
                  >
                    {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-[10px] text-gray-500">This link is single-use and will expire in 7 days.</p>
              </div>
            )}
          </div>
        </Card>

        {/* Members List Table */}
        <Card className="lg:col-span-2 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden">
          <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-4">
            <div>
              <h3 className="font-extrabold text-lg text-white">Active Members</h3>
              <p className="text-xs text-gray-400">Configure roles and specific section access per user.</p>
            </div>
            {loading && <Loader2 className="animate-spin h-5 w-5 text-gray-400" />}
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                <TableRow className="border-gray-800 hover:bg-transparent">
                  <TableHead className="text-gray-400 font-bold text-xs p-4">User</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Role</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Section Permissions</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="divide-y divide-gray-800">
                {members.map(member => (
                  <TableRow key={member.id} className="border-gray-800 hover:bg-gray-900/20">
                    <TableCell className="p-4">
                      <div>
                        <div className="text-xs text-white font-bold">{member.name || 'No Name'}</div>
                        <div className="text-[10px] text-gray-500">{member.email}</div>
                      </div>
                    </TableCell>
                    <TableCell className="p-4">
                      <select
                        value={member.role}
                        onChange={e => handleRoleChange(member.id, e.target.value)}
                        className="bg-gray-900 border border-gray-800 text-xs text-white rounded-lg px-2 py-1 focus:ring-violet-500"
                      >
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                      </select>
                    </TableCell>
                    <TableCell className="p-4">
                      {member.role === 'admin' ? (
                        <span className="inline-flex items-center gap-1 bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2 py-0.5 rounded text-[10px] font-bold">
                          <Shield size={10} /> Full Access (Admin)
                        </span>
                      ) : (
                        <div className="grid grid-cols-2 gap-1.5 max-w-xs">
                          {sectionsList.map(sec => {
                            const isAllowed = member.allowed_sections ? member.allowed_sections.includes(sec.id) : true;
                            return (
                              <label key={sec.id} className="flex items-center gap-1.5 text-[10px] text-gray-300 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={isAllowed}
                                  onChange={() => handleSectionToggle(member.id, sec.id)}
                                  className="rounded border-gray-800 text-violet-600 focus:ring-violet-500 bg-gray-950"
                                />
                                <span>{sec.name}</span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="p-4 text-right">
                      <Button 
                        size="icon" 
                        variant="ghost" 
                        onClick={() => handleDeleteMember(member.id)}
                        className="text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 rounded-xl"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>
    </div>
  );
}

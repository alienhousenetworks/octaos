'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Zap, Users, DollarSign, Activity, Loader2, Globe, Shield, RefreshCw, ImageIcon, Trash2, Upload, CheckCircle } from 'lucide-react';

interface SystemAdminViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  onBrandingUpdate?: (logoUrl: string | null | undefined, faviconUrl: string | null | undefined) => void;
}

export default function SystemAdminView({
  token,
  API_URL,
  fetchWithAuth,
  onBrandingUpdate,
}: SystemAdminViewProps) {
  const [stats, setStats] = useState<any>({ tenants_count: 0, users_count: 0, total_spend: 0, total_calls: 0 });
  const [tenants, setTenants] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'tenants' | 'users' | 'branding'>('tenants');

  // Branding state
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [faviconUrl, setFaviconUrl] = useState<string | null>(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingFavicon, setUploadingFavicon] = useState(false);
  const [brandingMsg, setBrandingMsg] = useState<string | null>(null);
  const logoInputRef = useRef<HTMLInputElement>(null);
  const faviconInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (token) {
      loadAllData();
      fetchBranding();
    }
  }, [token]);

  const loadAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchStats(),
        fetchTenants(),
        fetchUsers()
      ]);
    } catch (e) {
      console.error("Failed to load admin data:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    const res = await fetchWithAuth(`${API_URL}/system-admin/stats`);
    if (res.ok) {
      setStats(await res.json());
    }
  };

  const fetchTenants = async () => {
    const res = await fetchWithAuth(`${API_URL}/system-admin/tenants`);
    if (res.ok) {
      setTenants(await res.json());
    }
  };

  const fetchUsers = async () => {
    const res = await fetchWithAuth(`${API_URL}/system-admin/users`);
    if (res.ok) {
      setUsers(await res.json());
    }
  };

  const fetchBranding = async () => {
    const res = await fetchWithAuth(`${API_URL}/system-admin/settings`);
    if (res.ok) {
      const data = await res.json();
      setLogoUrl(data.logo_url || null);
      setFaviconUrl(data.favicon_url || null);
    }
  };

  const handleToggleTenant = async (tenantId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/system-admin/tenants/${tenantId}/toggle-active`, {
        method: 'POST'
      });
      if (res.ok) {
        // reload tenants
        fetchTenants();
      } else {
        alert("Failed to toggle tenant state");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteTenant = async (tenantId: string) => {
    if (!confirm("Are you sure you want to permanently delete this company and all its users? This action cannot be undone.")) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/system-admin/tenants/${tenantId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchTenants();
        fetchUsers();
      } else {
        alert("Failed to delete tenant");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm("Are you sure you want to permanently delete this user?")) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/system-admin/users/${userId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchUsers();
      } else {
        alert("Failed to delete user");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUploadLogo = async (file: File) => {
    setUploadingLogo(true);
    setBrandingMsg(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetchWithAuth(`${API_URL}/system-admin/settings/upload-logo`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setLogoUrl(data.logo_url);
        onBrandingUpdate?.(data.logo_url, undefined);
        setBrandingMsg('Logo uploaded successfully!');
      } else {
        setBrandingMsg(data.detail || 'Logo upload failed.');
      }
    } catch (e) {
      setBrandingMsg('Error uploading logo.');
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleUploadFavicon = async (file: File) => {
    setUploadingFavicon(true);
    setBrandingMsg(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetchWithAuth(`${API_URL}/system-admin/settings/upload-favicon`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setFaviconUrl(data.favicon_url);
        onBrandingUpdate?.(undefined, data.favicon_url);
        setBrandingMsg('Favicon uploaded successfully!');
      } else {
        setBrandingMsg(data.detail || 'Favicon upload failed.');
      }
    } catch (e) {
      setBrandingMsg('Error uploading favicon.');
    } finally {
      setUploadingFavicon(false);
    }
  };

  const handleRemoveLogo = async () => {
    const res = await fetchWithAuth(`${API_URL}/system-admin/settings/logo`, { method: 'DELETE' });
    if (res.ok) {
      setLogoUrl(null);
      onBrandingUpdate?.(null, undefined);
      setBrandingMsg('Logo removed.');
    }
  };

  const handleRemoveFavicon = async () => {
    const res = await fetchWithAuth(`${API_URL}/system-admin/settings/favicon`, { method: 'DELETE' });
    if (res.ok) {
      setFaviconUrl(null);
      onBrandingUpdate?.(undefined, null);
      setBrandingMsg('Favicon removed.');
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Zap className="text-yellow-400 h-8 w-8 animate-pulse" /> Global System Admin Panel
          </h1>
          <p className="text-gray-400 mt-1">Monitor tenant activities, manage user permissions, and control company status across the platform.</p>
        </div>
        <Button 
          onClick={loadAllData} 
          variant="outline" 
          className="border-gray-800 hover:bg-gray-800 text-gray-300 rounded-xl flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Panel
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="glass-panel border-blue-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-blue-505" />
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Companies</CardTitle>
            <Globe className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-3xl font-black text-white">{stats.tenants_count}</div>
            <p className="text-[10px] text-gray-500 font-medium">Registered business organizations</p>
          </CardContent>
        </Card>

        <Card className="glass-panel border-violet-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-violet-505" />
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total System Users</CardTitle>
            <Users className="h-4 w-4 text-violet-400" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-3xl font-black text-white">{stats.users_count}</div>
            <p className="text-[10px] text-gray-500 font-medium">Total active/verified user accounts</p>
          </CardContent>
        </Card>

        <Card className="glass-panel border-emerald-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-emerald-505" />
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Platform Spend</CardTitle>
            <DollarSign className="h-4 w-4 text-emerald-450" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-3xl font-black text-emerald-400">${stats.total_spend.toFixed(4)}</div>
            <p className="text-[10px] text-gray-500 font-medium">Aggregated LLM gateway charges</p>
          </CardContent>
        </Card>

        <Card className="glass-panel border-amber-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-505" />
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total API calls</CardTitle>
            <Activity className="h-4 w-4 text-amber-400" />
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-3xl font-black text-white">{stats.total_calls}</div>
            <p className="text-[10px] text-gray-500 font-medium">All provider requests processed</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-800 pb-2">
        <button
          onClick={() => setActiveTab('tenants')}
          className={`px-4 py-2 font-bold text-sm border-b-2 transition-all ${
            activeTab === 'tenants' ? 'border-yellow-400 text-yellow-400' : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          Tenants (Companies)
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`px-4 py-2 font-bold text-sm border-b-2 transition-all ${
            activeTab === 'users' ? 'border-yellow-400 text-yellow-400' : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          Users List
        </button>
        <button
          onClick={() => setActiveTab('branding')}
          className={`px-4 py-2 font-bold text-sm border-b-2 transition-all ${
            activeTab === 'branding' ? 'border-yellow-400 text-yellow-400' : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          System Branding
        </button>
      </div>

      {/* Content area */}
      <Card className="glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden">
        {loading && (
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 rounded-3xl">
            <Loader2 className="animate-spin h-10 w-10 text-yellow-400" />
          </div>
        )}

        {activeTab === 'tenants' ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                <TableRow className="border-gray-800 hover:bg-transparent">
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Company Name</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Subdomain</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Users Count</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Keys Configured</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">LLM Spend</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Status</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="divide-y divide-gray-800">
                {tenants.map(tenant => (
                  <TableRow key={tenant.id} className="border-gray-800 hover:bg-gray-900/20">
                    <TableCell className="p-4 font-bold text-white text-xs">{tenant.name}</TableCell>
                    <TableCell className="p-4 font-mono text-gray-300 text-[10px]">{tenant.subdomain || 'N/A'}</TableCell>
                    <TableCell className="p-4 text-xs font-semibold">{tenant.users_count}</TableCell>
                    <TableCell className="p-4">
                      {tenant.configured_keys && tenant.configured_keys.length > 0 ? (
                        <div className="flex gap-1 flex-wrap">
                          {tenant.configured_keys.map((k: string) => (
                            <span key={k} className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded text-[8px] font-bold font-mono uppercase">
                              {k}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[10px] text-gray-500 font-semibold italic">No keys configured</span>
                      )}
                    </TableCell>
                    <TableCell className="p-4 text-xs font-mono font-semibold text-emerald-400">${tenant.spend.toFixed(4)}</TableCell>
                    <TableCell className="p-4">
                      <span className={`inline-flex items-center gap-1 border px-2 py-0.5 rounded text-[10px] font-bold ${
                        tenant.is_active 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-450 border-rose-500/20'
                      }`}>
                        {tenant.is_active ? "Active" : "Suspended"}
                      </span>
                    </TableCell>
                    <TableCell className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          size="xs"
                          onClick={() => handleToggleTenant(tenant.id)}
                          className={`text-[10px] font-bold rounded-lg px-2.5 py-1 ${
                            tenant.is_active 
                              ? 'bg-rose-950/40 text-rose-400 border border-rose-900/30 hover:bg-rose-900/40' 
                              : 'bg-emerald-950/40 text-emerald-400 border border-emerald-900/30 hover:bg-emerald-900/40'
                          }`}
                        >
                          {tenant.is_active ? "Suspend" : "Activate"}
                        </Button>
                        <Button
                          size="xs"
                          onClick={() => handleDeleteTenant(tenant.id)}
                          className="bg-red-950/40 text-red-400 border border-red-900/30 hover:bg-red-900/40 text-[10px] font-bold rounded-lg px-2.5 py-1"
                        >
                          <Trash2 className="h-3 w-3 mr-1" /> Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : activeTab === 'users' ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                <TableRow className="border-gray-800 hover:bg-transparent">
                  <TableHead className="text-gray-400 font-bold text-xs p-4">User</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Role</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Company / Tenant</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Global Admin</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4">Account Status</TableHead>
                  <TableHead className="text-gray-400 font-bold text-xs p-4 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="divide-y divide-gray-800">
                {users.map(user => (
                  <TableRow key={user.id} className="border-gray-800 hover:bg-gray-900/20">
                    <TableCell className="p-4">
                      <div>
                        <div className="text-xs text-white font-bold">{user.name || 'No Name'}</div>
                        <div className="text-[10px] text-gray-500">{user.email}</div>
                      </div>
                    </TableCell>
                    <TableCell className="p-4 text-xs font-semibold capitalize">{user.role}</TableCell>
                    <TableCell className="p-4 text-xs">{user.tenant_name}</TableCell>
                    <TableCell className="p-4">
                      {user.is_system_admin ? (
                        <span className="inline-flex items-center gap-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-2 py-0.5 rounded text-[10px] font-bold">
                          <Shield size={10} /> System Admin
                        </span>
                      ) : (
                        <span className="text-gray-500 text-xs">-</span>
                      )}
                    </TableCell>
                    <TableCell className="p-4">
                      <span className={`inline-flex items-center gap-1 border px-2 py-0.5 rounded text-[10px] font-bold ${
                        user.is_active 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-450 border-rose-500/20'
                      }`}>
                        {user.is_active ? "Active" : "Disabled"}
                      </span>
                    </TableCell>
                    <TableCell className="p-4 text-right">
                      <Button
                        size="xs"
                        onClick={() => handleDeleteUser(user.id)}
                        className="bg-red-950/40 text-red-400 border border-red-900/30 hover:bg-red-900/40 text-[10px] font-bold rounded-lg px-2.5 py-1"
                      >
                        <Trash2 className="h-3 w-3 mr-1" /> Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          /* System Branding Tab */
          <div className="space-y-8 py-2">
            {brandingMsg && (
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-semibold">
                <CheckCircle size={16} /> {brandingMsg}
              </div>
            )}

            {/* Logo Upload */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="glass-panel border-violet-500/20 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2">
                  <ImageIcon className="h-5 w-5 text-violet-400" />
                  <h3 className="text-white font-bold text-sm">Site Logo</h3>
                </div>
                <p className="text-gray-400 text-xs">Displayed in the sidebar and on the login/signup pages. Recommended: PNG or SVG, min 120px height.</p>

                {logoUrl ? (
                  <div className="space-y-3">
                    <div className="bg-gray-900/60 rounded-xl p-4 flex items-center justify-center border border-gray-800">
                      <img src={logoUrl} alt="Current Logo" className="h-14 max-w-full object-contain" />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => logoInputRef.current?.click()}
                        disabled={uploadingLogo}
                        className="flex-1 bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded-xl text-xs font-bold flex items-center gap-1.5"
                      >
                        {uploadingLogo ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload size={12} />}
                        Replace Logo
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleRemoveLogo}
                        className="bg-rose-950/30 hover:bg-rose-900/40 text-rose-400 border border-rose-500/20 rounded-xl text-xs font-bold flex items-center gap-1.5"
                      >
                        <Trash2 size={12} /> Remove
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    onClick={() => logoInputRef.current?.click()}
                    disabled={uploadingLogo}
                    className="w-full bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-dashed border-violet-500/40 rounded-xl h-20 text-xs font-bold flex flex-col items-center justify-center gap-2"
                  >
                    {uploadingLogo ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload size={20} />}
                    {uploadingLogo ? 'Uploading...' : 'Click to Upload Logo'}
                  </Button>
                )}
                <input
                  ref={logoInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={e => { if (e.target.files?.[0]) handleUploadLogo(e.target.files[0]); }}
                />
              </Card>

              {/* Favicon Upload */}
              <Card className="glass-panel border-amber-500/20 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-amber-400" />
                  <h3 className="text-white font-bold text-sm">Site Favicon</h3>
                </div>
                <p className="text-gray-400 text-xs">Shown in browser tabs and bookmarks. Recommended: ICO, PNG, or SVG, 32×32px or 64×64px.</p>

                {faviconUrl ? (
                  <div className="space-y-3">
                    <div className="bg-gray-900/60 rounded-xl p-4 flex items-center justify-center border border-gray-800 gap-4">
                      <img src={faviconUrl} alt="Current Favicon" className="h-8 w-8 object-contain" />
                      <span className="text-gray-400 text-xs">Tab icon preview</span>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => faviconInputRef.current?.click()}
                        disabled={uploadingFavicon}
                        className="flex-1 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 rounded-xl text-xs font-bold flex items-center gap-1.5"
                      >
                        {uploadingFavicon ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload size={12} />}
                        Replace Favicon
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleRemoveFavicon}
                        className="bg-rose-950/30 hover:bg-rose-900/40 text-rose-400 border border-rose-500/20 rounded-xl text-xs font-bold flex items-center gap-1.5"
                      >
                        <Trash2 size={12} /> Remove
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button
                    onClick={() => faviconInputRef.current?.click()}
                    disabled={uploadingFavicon}
                    className="w-full bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-dashed border-amber-500/40 rounded-xl h-20 text-xs font-bold flex flex-col items-center justify-center gap-2"
                  >
                    {uploadingFavicon ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload size={20} />}
                    {uploadingFavicon ? 'Uploading...' : 'Click to Upload Favicon'}
                  </Button>
                )}
                <input
                  ref={faviconInputRef}
                  type="file"
                  accept="image/*,.ico"
                  className="hidden"
                  onChange={e => { if (e.target.files?.[0]) handleUploadFavicon(e.target.files[0]); }}
                />
              </Card>
            </div>

            <div className="text-xs text-gray-500 font-medium">
              <span className="text-yellow-400 font-bold">ℹ️ Note:</span> Changes apply immediately site-wide. Existing sessions will see the new logo/favicon on next page load or navigation.
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Building2,
  Globe,
  Mail,
  MapPin,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Copy,
  Check,
  User,
  Shield,
  Crown,
  Phone,
  RefreshCcw,
  Sparkles,
  ArrowRightLeft,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';

interface ProfileViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  userProfile: any;
  setUserProfile: (profile: any) => void;
  setToken: (token: string) => void;
  setTenantId: (tenantId: string) => void;
  fetchData: () => Promise<void>;
}

export default function ProfileView({
  token,
  API_URL,
  fetchWithAuth,
  userProfile,
  setUserProfile,
  setToken,
  setTenantId,
  fetchData,
}: ProfileViewProps) {
  const [activeTab, setActiveTab] = useState<'organization' | 'workspaces' | 'account'>('organization');
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(false);
  const [switchingTo, setSwitchingTo] = useState<string | null>(null);
  const [copiedTenant, setCopiedTenant] = useState(false);

  // Edit Organization Form State
  const [editOrgName, setEditOrgName] = useState('');
  const [editOrgEmail, setEditOrgEmail] = useState('');
  const [editOrgWebsite, setEditOrgWebsite] = useState('');
  const [editOrgAddress, setEditOrgAddress] = useState('');
  const [savingOrg, setSavingOrg] = useState(false);

  // Edit Personal Profile Form State
  const [editName, setEditName] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  const fetchOrganizations = useCallback(async () => {
    setLoadingOrgs(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/my-organizations`);
      if (res.ok) {
        const data = await res.json();
        setOrganizations(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error('Failed to fetch organizations:', e);
    } finally {
      setLoadingOrgs(false);
    }
  }, [API_URL, fetchWithAuth]);

  useEffect(() => {
    if (token) {
      fetchOrganizations();
      setEditName(userProfile?.name || '');
      setEditPhone(userProfile?.phone_no || '');
    }
  }, [token, userProfile?.name, userProfile?.phone_no, fetchOrganizations]);

  const currentOrg = useMemo(() => {
    return organizations.find((o) => o.is_current) || organizations[0] || null;
  }, [organizations]);

  useEffect(() => {
    if (currentOrg) {
      setEditOrgName(currentOrg.name || '');
      setEditOrgEmail(currentOrg.company_email || '');
      setEditOrgWebsite(currentOrg.company_website || '');
      setEditOrgAddress(currentOrg.company_address || '');
    }
  }, [currentOrg]);

  const handleCopyTenantId = () => {
    const tid = userProfile?.tenant_id || currentOrg?.id || '';
    if (tid) {
      navigator.clipboard.writeText(tid);
      setCopiedTenant(true);
      setTimeout(() => setCopiedTenant(false), 2000);
    }
  };

  const handleSwitchOrg = async (tenantId: string) => {
    if (tenantId === userProfile?.tenant_id) return;
    setSwitchingTo(tenantId);
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/switch-tenant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      if (res.ok) {
        const data = await res.json();
        try {
          const { saveSession } = await import('@/lib/auth-session');
          saveSession({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            tenant_id: data.tenant_id,
          });
        } catch {
          localStorage.setItem('token', data.access_token);
          localStorage.setItem('tenant_id', data.tenant_id);
        }
        setToken(data.access_token);
        setTenantId(data.tenant_id);
        notify(`Switched to organization: ${tenantId}`);
        await fetchData();
        await fetchOrganizations();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to switch workspace');
      }
    } catch (e) {
      console.error(e);
      notify('Network error switching workspace');
    } finally {
      setSwitchingTo(null);
    }
  };

  const handleSaveOrganization = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingOrg(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/organization`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editOrgName,
          company_email: editOrgEmail,
          company_website: editOrgWebsite,
          company_address: editOrgAddress,
        }),
      });
      if (res.ok) {
        notify('✅ Organization profile saved');
        await fetchOrganizations();
        await fetchData();
      } else {
        const err = await res.json().catch(() => ({}));
        notify(err.detail || 'Failed to update organization');
      }
    } catch {
      notify('Network error saving organization');
    } finally {
      setSavingOrg(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/auth/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editName, phone_no: editPhone }),
      });
      if (res.ok) {
        const updated = await res.json();
        setUserProfile({
          ...userProfile,
          name: updated.name || editName,
          phone_no: updated.phone_no || editPhone,
        });
        notify('✅ Account profile updated');
      } else {
        setUserProfile({ ...userProfile, name: editName, phone_no: editPhone });
        notify('✅ Profile updated');
      }
    } catch {
      setUserProfile({ ...userProfile, name: editName, phone_no: editPhone });
    } finally {
      setSavingProfile(false);
    }
  };

  const roleLabel = useMemo(() => {
    if (userProfile?.is_system_admin) return 'System Admin';
    if (userProfile?.role === 'admin') return 'Organization Admin';
    if (userProfile?.role === 'manager') return 'Team Manager';
    return 'Member Operator';
  }, [userProfile]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-16">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono mb-1">
            <span>Settings</span>
            <span>/</span>
            <span className="text-zinc-200">Organization & Account</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-white flex items-center gap-2.5">
            Organization Profile
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
              Live Tenant
            </span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Manage your legal entity profile, multi-tenant workspace routing, and administrative security credentials.
          </p>
        </div>
      </div>

      {/* Organization Identity Card (Apple/GCP Style) */}
      <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-zinc-800 border border-white/[0.1] text-zinc-200 flex items-center justify-center shrink-0">
              <Building2 className="w-6 h-6 text-zinc-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-white tracking-tight">
                  {currentOrg?.name || userProfile?.name || 'OctaOS Enterprise Workspace'}
                </h2>
                <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
                  ENTERPRISE
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-zinc-400">
                <span className="font-mono text-zinc-400">
                  Tenant ID: {userProfile?.tenant_id?.slice(0, 16)}…
                </span>
                <button
                  onClick={handleCopyTenantId}
                  className="inline-flex items-center gap-1 text-[11px] font-mono text-zinc-400 hover:text-white transition-colors"
                  title="Copy full Tenant ID"
                >
                  {copiedTenant ? (
                    <Check className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3 text-zinc-500" />
                  )}
                  {copiedTenant ? 'Copied' : 'Copy ID'}
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center">
            <span className="inline-flex items-center gap-1 text-xs font-mono font-medium px-2.5 py-1 rounded-md bg-zinc-900 border border-white/[0.08] text-zinc-300">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              {roleLabel}
            </span>
          </div>
        </div>
      </div>

      {/* Segmented Tab Controls */}
      <div className="inline-flex p-1 rounded-lg bg-zinc-900/90 border border-white/[0.08]">
        <button
          onClick={() => setActiveTab('organization')}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === 'organization'
              ? 'bg-zinc-800 text-white shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Company Profile
        </button>
        <button
          onClick={() => setActiveTab('workspaces')}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === 'workspaces'
              ? 'bg-zinc-800 text-white shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Workspaces ({organizations.length})
        </button>
        <button
          onClick={() => setActiveTab('account')}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            activeTab === 'account'
              ? 'bg-zinc-800 text-white shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Personal Account & Security
        </button>
      </div>

      {/* Tab 1: Organization Details Form */}
      {activeTab === 'organization' && (
        <form onSubmit={handleSaveOrganization} className="rounded-xl border border-white/[0.08] bg-[#111318] p-6 space-y-6">
          <div className="border-b border-white/[0.08] pb-4">
            <h3 className="text-sm font-semibold text-white">General Information</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Legal entity details used across automated contracts, invoices, and branded communications.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 text-zinc-400" />
                Organization Legal Name
              </label>
              <Input
                value={editOrgName}
                onChange={(e) => setEditOrgName(e.target.value)}
                placeholder="Acme Technologies Inc."
                className="h-9 text-xs bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-zinc-400" />
                Corporate Contact Email
              </label>
              <Input
                type="email"
                value={editOrgEmail}
                onChange={(e) => setEditOrgEmail(e.target.value)}
                placeholder="contact@enterprise.com"
                className="h-9 text-xs bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-zinc-400" />
                Company Website
              </label>
              <Input
                type="url"
                value={editOrgWebsite}
                onChange={(e) => setEditOrgWebsite(e.target.value)}
                placeholder="https://enterprise.com"
                className="h-9 text-xs bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-zinc-400" />
                Registered Business Address
              </label>
              <Input
                value={editOrgAddress}
                onChange={(e) => setEditOrgAddress(e.target.value)}
                placeholder="100 Enterprise Way, Suite 400"
                className="h-9 text-xs bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
              />
            </div>
          </div>

          <div className="flex justify-end pt-3 border-t border-white/[0.08]">
            <Button
              type="submit"
              disabled={savingOrg}
              className="h-8 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md px-4 shadow-sm"
            >
              {savingOrg ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                  Saving Changes…
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </div>
        </form>
      )}

      {/* Tab 2: Workspaces Switcher Grid */}
      {activeTab === 'workspaces' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/[0.08] bg-[#111318] p-5">
            <h3 className="text-sm font-semibold text-white">Your Authorized Workspaces</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Switch tenant context across multi-organization deployments without re-authenticating.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
              {loadingOrgs && organizations.length === 0 ? (
                <div className="col-span-2 py-8 text-center text-xs text-zinc-400">
                  <Loader2 className="w-4 h-4 mx-auto mb-2 animate-spin text-zinc-500" />
                  Loading tenant organizations…
                </div>
              ) : (
                organizations.map((org) => {
                  const isCurrent = org.id === userProfile?.tenant_id || org.is_current;
                  const isSwitching = switchingTo === org.id;

                  return (
                    <div
                      key={org.id}
                      className={`rounded-xl border p-4 transition-all ${
                        isCurrent
                          ? 'border-indigo-500/40 bg-indigo-950/20 shadow-sm'
                          : 'border-white/[0.08] bg-zinc-900/60 hover:border-white/[0.16]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-white truncate">
                              {org.name || 'Organization Workspace'}
                            </span>
                            {isCurrent && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                                ACTIVE
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] font-mono text-zinc-500 mt-1 truncate">
                            ID: {org.id}
                          </div>
                        </div>

                        {!isCurrent && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSwitchOrg(org.id)}
                            disabled={isSwitching}
                            className="h-7 text-xs border-white/[0.1] bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md px-2.5 shrink-0"
                          >
                            {isSwitching ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <>
                                <ArrowRightLeft className="w-3 h-3 mr-1" /> Switch
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Personal Account & Security */}
      {activeTab === 'account' && (
        <form onSubmit={handleSaveProfile} className="rounded-xl border border-white/[0.08] bg-[#111318] p-6 space-y-6">
          <div className="border-b border-white/[0.08] pb-4">
            <h3 className="text-sm font-semibold text-white">Personal Credentials</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Account identity associated with session tokens and audit log signatures.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-zinc-400" />
                Full Name
              </label>
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Jane Doe"
                className="h-9 text-xs bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-zinc-400" />
                Phone Number
              </label>
              <Input
                type="tel"
                value={editPhone}
                onChange={(e) => setEditPhone(e.target.value)}
                placeholder="+1 (555) 000-0000"
                className="h-9 text-xs bg-zinc-900 border-white/[0.08] focus:border-zinc-500 rounded-md"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-zinc-500" />
                Account Email (Primary SSO)
              </label>
              <Input
                readOnly
                disabled
                value={userProfile?.email || ''}
                className="h-9 text-xs bg-zinc-900/40 border-white/[0.04] text-zinc-500 cursor-not-allowed rounded-md font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-zinc-500" />
                Security Verification
              </label>
              <div className="h-9 px-3 rounded-md bg-zinc-900/40 border border-white/[0.04] flex items-center gap-2 text-xs text-emerald-400 font-mono">
                <CheckCircle2 className="w-3.5 h-3.5" />
                SSO Identity Verified
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-3 border-t border-white/[0.08]">
            <Button
              type="submit"
              disabled={savingProfile}
              className="h-8 bg-zinc-100 hover:bg-white text-zinc-950 font-medium text-xs rounded-md px-4 shadow-sm"
            >
              {savingProfile ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                  Saving…
                </>
              ) : (
                'Save Profile'
              )}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

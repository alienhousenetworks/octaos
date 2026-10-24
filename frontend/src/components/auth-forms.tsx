'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Zap, Loader2 } from 'lucide-react';
import { saveSession } from '@/lib/auth-session';
import { notify } from '@/lib/notify';

interface AuthFormsProps {
  appState: 'login' | 'signup';
  setAppState?: (state: 'landing' | 'login' | 'signup' | 'app') => void;
  API_URL: string;
  setToken?: (token: string | null) => void;
  setTenantId?: (tenantId: string | null) => void;
  inviteToken?: string | null;
  setInviteToken?: (token: string | null) => void;
  logoUrl?: string | null;
}

export default function AuthForms({
  appState,
  setAppState,
  API_URL,
  setToken,
  setTenantId,
  inviteToken,
  setInviteToken,
  logoUrl,
}: AuthFormsProps) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const setAppStateSafe = (state: 'landing' | 'login' | 'signup' | 'app') => {
    setFormError(null);
    setAppState?.(state);
    if (state === 'app') router.push('/app/home');
    else if (state === 'login') router.push('/login');
    else if (state === 'signup') router.push('/signup');
    else router.push('/');
  };
  // Form input states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [fullName, setFullName] = useState('');
  const [phoneNo, setPhoneNo] = useState('');
  const [companyWebsite, setCompanyWebsite] = useState('');
  const [companyEmail, setCompanyEmail] = useState('');
  const [companyAddress, setCompanyAddress] = useState('');
  
  // OTP flow states
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpTimer, setOtpTimer] = useState(0);
  const [otpMethod, setOtpMethod] = useState<'signup' | 'login'>('signup');
  const [tempEmail, setTempEmail] = useState('');
  const [loginMode, setLoginMode] = useState<'password' | 'otp'>('password');
  const [tenantSelection, setTenantSelection] = useState<{id: string, name: string}[] | null>(null);

  // Invitation verify & accept states
  const [invitationDetails, setInvitationDetails] = useState<{company_name: string, email?: string} | null>(null);
  const [invitationError, setInvitationError] = useState<string | null>(null);
  const [verifyingInvite, setVerifyingInvite] = useState(false);

  useEffect(() => {
    if (inviteToken) {
      const verifyToken = async () => {
        setVerifyingInvite(true);
        setInvitationError(null);
        try {
          const res = await fetch(`${API_URL}/auth/invite/verify?token=${inviteToken}`);
          const data = await res.json();
          if (res.ok) {
            setInvitationDetails(data);
            if (data.email) {
              setEmail(data.email);
            }
          } else {
            setInvitationError(data.detail || "Invalid or expired invitation token");
          }
        } catch (e) {
          console.error(e);
          setInvitationError("Failed to verify invitation token");
        } finally {
          setVerifyingInvite(false);
        }
      };
      verifyToken();
    }
  }, [inviteToken]);

  const handleAcceptInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/auth/invite/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: inviteToken,
          name: fullName,
          email,
          password
        })
      });
      const data = await res.json();
      if (res.ok) {
        saveSession({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          tenant_id: data.tenant_id,
        });
        setToken?.(data.access_token);
        if (data.tenant_id) setTenantId?.(data.tenant_id);
        setInviteToken?.(null);
        setAppStateSafe('app');
      } else {
        setFormError(data.detail || "Failed to accept invitation");
      }
    } catch (e) {
      console.error(e);
      setFormError("Error accepting invitation");
    }
  };

  // Countdown timer for OTP resend
  useEffect(() => {
    if (otpTimer > 0) {
      const timer = setTimeout(() => setOtpTimer(otpTimer - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [otpTimer]);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/auth/signup/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: fullName,
          email,
          phone_no: phoneNo,
          company: companyName || null,
          company_website: companyWebsite || null,
          company_email: companyEmail || null,
          company_address: companyAddress || null,
          password
        })
      });
      const data = await res.json();
      if (res.ok) {
        setTempEmail(email);
        setOtpSent(true);
        setOtpMethod('signup');
        setOtpTimer(60);
        setOtp('');
      } else {
        setFormError(data.detail || "Signup failed");
      }
    } catch (e) {
      console.error(e);
      setFormError("Failed to connect to the backend server. Please verify that the backend is running at " + API_URL);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: any = { email };
      if (loginMode === 'password') {
        if (!password) {
          setFormError("Please enter your password");
          return;
        }
        payload.password = password;
      }
      
      const res = await fetch(`${API_URL}/auth/login/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        if (data.needs_tenant_selection) {
          setTenantSelection(data.tenants);
          setTempEmail(email);
        } else if (data.otp_required === false) {
          saveSession({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            tenant_id: data.tenant_id,
          });
          setToken?.(data.access_token);
          if (data.tenant_id) setTenantId?.(data.tenant_id);
          // Reset states
          setOtpSent(false);
          setOtp('');
          setTempEmail('');
          setEmail('');
          setPassword('');
          setTenantSelection(null);
          setAppStateSafe('app');
        } else {
          setTempEmail(email);
          setOtpSent(true);
          setOtpMethod('login');
          setOtpTimer(60);
          setOtp('');
        }
      } else {
        setFormError(data.detail || "Login failed");
      }
    } catch (e) {
      console.error(e);
      setFormError("Failed to connect to the backend server. Please verify that the backend is running at " + API_URL);
    }
  };

  const handleOtpVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    const endpoint = otpMethod === 'signup' ? 'signup/verify' : 'login/verify';
    try {
      const res = await fetch(`${API_URL}/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: tempEmail, otp })
      });
      const data = await res.json();
      if (res.ok) {
        if (data.needs_tenant_selection) {
           setTenantSelection(data.tenants);
           setOtpSent(false);
        } else {
          saveSession({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            tenant_id: data.tenant_id,
          });
          setToken?.(data.access_token);
          if (data.tenant_id) setTenantId?.(data.tenant_id);
          // Reset states
          setOtpSent(false);
          setOtp('');
          setTempEmail('');
          setFullName('');
          setPhoneNo('');
          setCompanyName('');
          setCompanyWebsite('');
          setCompanyEmail('');
          setCompanyAddress('');
          setEmail('');
          setPassword('');
          setTenantSelection(null);
          setAppStateSafe('app');
        }
      } else {
        setFormError(data.detail || "OTP verification failed");
      }
    } catch (e) {
      console.error(e);
      setFormError("Error during OTP verification");
    }
  };


  const handleSelectCompany = async (tenantId: string) => {
    try {
      const endpoint = otpMethod === 'signup' ? 'signup/verify' : 'login/initiate';
      const payload: any = { email: tempEmail, tenant_id: tenantId };
      if (loginMode === 'password') {
        payload.password = password;
      } else if (otp) {
        payload.otp = otp;
      }
      
      const res = await fetch(`${API_URL}/auth/${loginMode === 'password' ? 'login/initiate' : 'login/verify'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        saveSession({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          tenant_id: data.tenant_id,
        });
        setToken?.(data.access_token);
        if (data.tenant_id) setTenantId?.(data.tenant_id);
        // Reset states
        setOtpSent(false);
        setOtp('');
        setTempEmail('');
        setEmail('');
        setPassword('');
        setTenantSelection(null);
        setAppStateSafe('app');
      } else {
        setFormError(data.detail || "Failed to switch company");
      }
    } catch (e) {
      console.error(e);
      setFormError("Error selecting company");
    }
  };

  const handleResendOtp = async () => {
    if (otpTimer > 0) return;
    const endpoint = otpMethod === 'signup' ? 'signup/resend-otp' : 'login/resend-otp';
    try {
      const res = await fetch(`${API_URL}/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: tempEmail })
      });
      const data = await res.json();
      if (res.ok) {
        notify("A new OTP code has been sent to " + tempEmail);
        setOtpTimer(60);
      } else {
        setFormError(data.detail || "Failed to resend OTP");
      }
    } catch (e) {
      console.error(e);
      setFormError('Network error resending OTP.');
    }
  };

  if (inviteToken) {
    return (
      <div className="min-h-screen bg-background text-foreground relative overflow-hidden font-sans flex flex-col justify-center items-center px-4">
        <Card className="w-full max-w-md bg-card border border-border shadow-lg relative overflow-hidden rounded-xl animate-in fade-in zoom-in-95 duration-200">
          <CardHeader className="space-y-2 pt-8">
            <div className="flex justify-center items-center gap-3 mb-2">
              {logoUrl ? (
                <img src={logoUrl} alt="OctaOS Logo" className="h-12 w-auto max-w-[160px] object-contain" />
              ) : (
                <div className="bg-primary p-2.5 rounded-lg">
                  <Zap className="text-white h-5 w-5" />
                </div>
              )}
              <span className="text-white font-extrabold text-2xl tracking-tight">OctaOs</span>
            </div>
            <CardTitle className="text-2xl text-center text-white font-extrabold tracking-tight">
              {verifyingInvite ? "Verifying invitation..." : `Join ${invitationDetails?.company_name || 'Organization'}`}
            </CardTitle>
            <CardDescription className="text-center text-gray-400 text-xs">
              {invitationError ? (
                <span className="text-rose-400 font-bold">{invitationError}</span>
              ) : (
                "Complete your profile to accept the invitation and join the workspace."
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pb-8">
            {formError && <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-red-300">{formError}</p>}
            {invitationError ? (
              <Button 
                onClick={() => {
                  setInviteToken?.(null);
                  setAppStateSafe('login');
                }}
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium h-11 rounded-xl text-xs"
              >
                Go to Login
              </Button>
            ) : verifyingInvite ? (
              <div className="flex justify-center py-8">
                <Loader2 className="animate-spin h-8 w-8 text-violet-500" />
              </div>
            ) : (
              <form onSubmit={handleAcceptInvite} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Full Name</label>
                  <Input 
                    placeholder="Jane Doe" 
                    required
                    value={fullName} 
                    onChange={e => setFullName(e.target.value)} 
                    className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20 h-11 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Email Address</label>
                  <Input 
                    placeholder="name@company.com" 
                    type="email" 
                    required
                    value={email} 
                    onChange={e => setEmail(e.target.value)} 
                    className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20 h-11 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-400">Password</label>
                  <Input 
                    placeholder="••••••••" 
                    type="password" 
                    required
                    value={password} 
                    onChange={e => setPassword(e.target.value)} 
                    className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20 h-11 text-sm"
                  />
                </div>

                <div className="pt-2">
                  <button 
                    className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-medium py-3.5 rounded-xl cursor-pointer flex justify-center items-center text-sm" 
                    type="submit"
                  >
                    Accept Invite & Sign Up
                  </button>
                </div>

                <div className="text-center text-xs text-gray-400">
                  Already have an account? <span className="text-violet-400 hover:text-violet-300 cursor-pointer font-bold transition-colors" onClick={() => {
                    setInviteToken?.(null);
                    setAppStateSafe('login');
                  }}>Log in</span>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  if (tenantSelection) {
    return (
      <div className="min-h-screen bg-background text-foreground relative overflow-hidden font-sans flex flex-col justify-center items-center px-4">
        <Card className="w-full max-w-md bg-card border border-border shadow-lg relative overflow-hidden rounded-xl animate-in fade-in zoom-in-95 duration-200">
          <CardHeader className="space-y-2 pt-8">
            <div className="flex justify-center items-center gap-3 mb-2">
              {logoUrl ? (
                <img src={logoUrl} alt="OctaOS Logo" className="h-12 w-auto max-w-[160px] object-contain" />
              ) : (
                <div className="bg-primary p-2.5 rounded-md">
                  <Zap className="text-white h-5 w-5" />
                </div>
              )}
              <span className="font-semibold text-xl">OctaOS</span>
            </div>
            <CardTitle className="text-xl text-center font-semibold">Select workspace</CardTitle>
            <CardDescription className="text-center text-muted-foreground text-xs">
              You belong to multiple workspaces. Choose one to continue.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pb-8">
            {formError && <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{formError}</p>}
            <div className="space-y-2">
              {tenantSelection.map((tenant) => (
                <button
                  key={tenant.id}
                  onClick={() => handleSelectCompany(tenant.id)}
                  className="w-full bg-surface-hover border border-border hover:border-primary/50 text-foreground font-medium py-3 rounded-lg transition-colors flex items-center justify-between px-4 text-sm text-left"
                >
                  <span>{tenant.name}</span>
                </button>
              ))}
            </div>
            <div className="text-center text-xs text-muted-foreground pt-2">
              <span className="text-primary hover:text-primary-hover cursor-pointer font-medium transition-colors" onClick={() => setTenantSelection(null)}>Back to login</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (otpSent) {
    return (
      <div className="min-h-screen bg-background text-foreground relative overflow-hidden font-sans flex flex-col justify-center items-center px-4">
        <Card className="w-full max-w-md bg-card border border-border shadow-lg relative overflow-hidden rounded-xl">
          <CardHeader className="space-y-2 pt-8">
            <div className="flex justify-center items-center gap-3 mb-2">
              {logoUrl ? (
                <img src={logoUrl} alt="OctaOS Logo" className="h-12 w-auto max-w-[160px] object-contain" />
              ) : (
                <div className="bg-primary p-2.5 rounded-md">
                  <Zap className="text-white h-5 w-5" />
                </div>
              )}
              <span className="font-semibold text-xl">OctaOS</span>
            </div>
            <CardTitle className="text-xl text-center font-semibold">
              {otpMethod === 'signup' ? "Verify your email" : "Security verification"}
            </CardTitle>
            <CardDescription className="text-center text-muted-foreground text-xs">
              We sent a 6-digit code to <strong className="text-foreground">{tempEmail}</strong>.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pb-8">
            {formError && <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{formError}</p>}
            <form onSubmit={handleOtpVerify} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Verification code</label>
                <Input 
                  placeholder="000000" 
                  maxLength={6}
                  value={otp} 
                  onChange={e => setOtp(e.target.value)} 
                  className="bg-input border-border text-foreground rounded-lg text-center tracking-widest text-lg font-semibold"
                />
              </div>

              <div className="flex gap-3">
                <Button 
                  type="submit" 
                  className="flex-1 bg-primary hover:bg-primary-hover text-primary-foreground font-medium h-10 rounded-lg text-sm transition-colors"
                >
                  {otpMethod === 'signup' ? "Create account" : "Verify"}
                </Button>
                <Button 
                  type="button" 
                  variant="outline"
                  onClick={handleResendOtp}
                  disabled={otpTimer > 0}
                  className="flex-1 h-10 rounded-lg text-sm border-border"
                >
                  {otpTimer > 0 ? `Resend in ${otpTimer}s` : "Resend"}
                </Button>
              </div>

              <div className="text-center text-xs text-muted-foreground pt-1">
                Wrong email? <span className="text-primary hover:text-primary-hover cursor-pointer font-medium transition-colors" onClick={() => setOtpSent(false)}>Go back</span>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (appState === 'login') {
    return (
      <div className="min-h-screen bg-background text-foreground relative overflow-hidden font-sans flex flex-col justify-center items-center px-4">
        <Card className="w-full max-w-md bg-card border border-border shadow-lg relative overflow-hidden rounded-xl animate-in fade-in zoom-in-95 duration-200">
          <CardHeader className="space-y-2 pt-8">
            <div className="flex justify-center items-center gap-3 mb-2">
              {logoUrl ? (
                <img src={logoUrl} alt="OctaOS Logo" className="h-12 w-auto max-w-[160px] object-contain" />
              ) : (
                <div className="bg-primary p-2.5 rounded-lg">
                  <Zap className="text-white h-5 w-5" />
                </div>
              )}
              <span className="text-white font-extrabold text-2xl tracking-tight">OctaOs</span>
            </div>
            <CardTitle className="text-2xl text-center text-white font-extrabold tracking-tight">Access Your Workspace</CardTitle>
            <CardDescription className="text-center text-gray-400 text-xs">
              {loginMode === 'password' 
                ? "Enter your email and password to log in directly." 
                : "Enter your email. A one-time code (OTP) will be sent."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pb-8">
            {formError && <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-red-300">{formError}</p>}
            {/* Tabs Toggle */}
            <div className="flex bg-muted p-1 rounded-lg border border-border">
              <button
                type="button"
                onClick={() => setLoginMode('password')}
                className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                  loginMode === 'password'
                    ? 'bg-surface-hover text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Password
              </button>
              <button
                type="button"
                onClick={() => setLoginMode('otp')}
                className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                  loginMode === 'otp'
                    ? 'bg-surface-hover text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                One-time code
              </button>
            </div>

            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Email address</label>
                <Input 
                  placeholder="name@company.com" 
                  type="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)} 
                  className="bg-input border-border text-foreground rounded-lg h-10 text-sm"
                />
              </div>
              
              {loginMode === 'password' && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Password</label>
                  <Input 
                    placeholder="••••••••" 
                    type="password" 
                    required={loginMode === 'password'}
                    value={password} 
                    onChange={e => setPassword(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg h-10 text-sm"
                  />
                </div>
              )}

              <div className="pt-1">
                <button 
                  className="w-full bg-primary hover:bg-primary-hover text-primary-foreground font-medium py-2.5 rounded-lg cursor-pointer flex justify-center items-center text-sm transition-colors" 
                  type="submit"
                >
                  {loginMode === 'password' ? "Log in" : "Send one-time code"}
                </button>
              </div>

              <div className="text-center text-xs text-muted-foreground">
                No account? <span className="text-primary hover:text-primary-hover cursor-pointer font-medium transition-colors" onClick={() => setAppStateSafe('signup')}>Sign up</span>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // signup
  return (
    <div className="min-h-screen bg-background text-foreground relative overflow-hidden font-sans flex flex-col justify-center items-center px-4 py-12">
      <Card className="w-full max-w-2xl bg-card border border-border shadow-lg relative overflow-hidden rounded-xl animate-in fade-in zoom-in-95 duration-200">
        <CardHeader className="space-y-2 pt-8">
          <div className="flex justify-center items-center gap-3 mb-2">
              {logoUrl ? (
                <img src={logoUrl} alt="OctaOS Logo" className="h-12 w-auto max-w-[160px] object-contain" />
              ) : (
                <div className="bg-primary p-2.5 rounded-md">
                  <Zap className="text-white h-5 w-5" />
                </div>
              )}
              <span className="text-white font-extrabold text-2xl tracking-tight">OctaOs</span>
            </div>
          <CardTitle className="text-2xl text-center text-white font-extrabold tracking-tight">Deploy Your Workspace</CardTitle>
          <CardDescription className="text-center text-gray-400 text-xs">Create your admin profile and company details. Setup takes 30 seconds.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pb-8">
            {formError && <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-red-300">{formError}</p>}
          <form onSubmit={handleSignup} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              
              {/* Left side: Admin details */}
              <div className="space-y-4">
                <h3 className="text-xs font-semibold text-muted-foreground">Admin account</h3>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Full name</label>
                  <Input 
                    placeholder="Jane Doe" 
                    required
                    value={fullName} 
                    onChange={e => setFullName(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Email address</label>
                  <Input 
                    placeholder="jane@company.com" 
                    type="email" 
                    required
                    value={email} 
                    onChange={e => setEmail(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Phone number (WhatsApp AI)</label>
                  <Input 
                    placeholder="+1 (555) 012-3456" 
                    required
                    value={phoneNo} 
                    onChange={e => setPhoneNo(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Password</label>
                  <Input 
                    placeholder="••••••••" 
                    type="password" 
                    required
                    value={password} 
                    onChange={e => setPassword(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
              </div>

              {/* Right side: Company details */}
              <div className="space-y-4">
                <h3 className="text-xs font-semibold text-muted-foreground">Workspace details</h3>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Company name</label>
                  <Input 
                    placeholder="Acme Corp" 
                    required
                    value={companyName} 
                    onChange={e => setCompanyName(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Company website</label>
                  <Input 
                    placeholder="https://acme.com" 
                    type="url"
                    value={companyWebsite} 
                    onChange={e => setCompanyWebsite(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Company email</label>
                  <Input 
                    placeholder="info@acme.com" 
                    type="email"
                    value={companyEmail} 
                    onChange={e => setCompanyEmail(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">Company address</label>
                  <Input 
                    placeholder="123 Business Rd, Suite 100" 
                    value={companyAddress} 
                    onChange={e => setCompanyAddress(e.target.value)} 
                    className="bg-input border-border text-foreground rounded-lg"
                  />
                </div>
              </div>

            </div>

            <div className="pt-1">
              <button 
                className="w-full bg-primary hover:bg-primary-hover text-primary-foreground font-medium py-2.5 rounded-lg cursor-pointer flex justify-center items-center text-sm transition-colors" 
                type="submit"
              >
                Send verification code
              </button>
            </div>

            <div className="text-center text-xs text-muted-foreground">
              Already have an account? <span className="text-primary hover:text-primary-hover cursor-pointer font-medium transition-colors" onClick={() => setAppStateSafe('login')}>Log in</span>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

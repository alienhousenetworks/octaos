import sys
import os

filepath = "/Users/sayantande/Downloads/jules_session_166401146785413967/frontend/src/components/auth-forms.tsx"

with open(filepath, "r") as f:
    content = f.read()

# Add tenant selection state
state_search = """  const [loginMode, setLoginMode] = useState<'password' | 'otp'>('password');"""
state_replace = """  const [loginMode, setLoginMode] = useState<'password' | 'otp'>('password');
  const [tenantSelection, setTenantSelection] = useState<{id: string, name: string}[] | null>(null);"""
content = content.replace(state_search, state_replace)

# Modify handleLogin
handle_login_search = """      const res = await fetch(`${API_URL}/auth/login/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        if (data.otp_required === false) {
          localStorage.setItem('token', data.access_token);
          setToken(data.access_token);
          if (data.tenant_id) {
            localStorage.setItem('tenant_id', data.tenant_id);
            setTenantId(data.tenant_id);
          }
          // Reset states
          setOtpSent(false);
          setOtp('');
          setTempEmail('');
          setEmail('');
          setPassword('');
          setAppState('app');
        } else {
          setTempEmail(email);
          setOtpSent(true);
          setOtpMethod('login');
          setOtpTimer(60);
          setOtp('');
        }
      } else {
        alert(data.detail || "Login failed");
      }"""

handle_login_replace = """      const res = await fetch(`${API_URL}/auth/login/initiate`, {
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
          localStorage.setItem('token', data.access_token);
          setToken(data.access_token);
          if (data.tenant_id) {
            localStorage.setItem('tenant_id', data.tenant_id);
            setTenantId(data.tenant_id);
          }
          // Reset states
          setOtpSent(false);
          setOtp('');
          setTempEmail('');
          setEmail('');
          setPassword('');
          setTenantSelection(null);
          setAppState('app');
        } else {
          setTempEmail(email);
          setOtpSent(true);
          setOtpMethod('login');
          setOtpTimer(60);
          setOtp('');
        }
      } else {
        alert(data.detail || "Login failed");
      }"""
content = content.replace(handle_login_search, handle_login_replace)

# Modify handleOtpVerify
handle_otp_search = """      const res = await fetch(`${API_URL}/auth/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: tempEmail, otp })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        if (data.tenant_id) {
          localStorage.setItem('tenant_id', data.tenant_id);
          setTenantId(data.tenant_id);
        }
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
        setAppState('app');
      } else {
        alert(data.detail || "OTP verification failed");
      }"""

handle_otp_replace = """      const res = await fetch(`${API_URL}/auth/${endpoint}`, {
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
          localStorage.setItem('token', data.access_token);
          setToken(data.access_token);
          if (data.tenant_id) {
            localStorage.setItem('tenant_id', data.tenant_id);
            setTenantId(data.tenant_id);
          }
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
          setAppState('app');
        }
      } else {
        alert(data.detail || "OTP verification failed");
      }"""
content = content.replace(handle_otp_search, handle_otp_replace)

# Add handleSelectCompany function
handle_select_company = """
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
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        if (data.tenant_id) {
          localStorage.setItem('tenant_id', data.tenant_id);
          setTenantId(data.tenant_id);
        }
        // Reset states
        setOtpSent(false);
        setOtp('');
        setTempEmail('');
        setEmail('');
        setPassword('');
        setTenantSelection(null);
        setAppState('app');
      } else {
        alert(data.detail || "Failed to switch company");
      }
    } catch (e) {
      console.error(e);
      alert("Error selecting company");
    }
  };
"""

# Insert handleSelectCompany after handleResendOtp
content = content.replace("  const handleResendOtp", handle_select_company + "\n  const handleResendOtp")

# Add tenant selection UI
ui_search = """  if (otpSent) {"""
ui_replace = """  if (tenantSelection) {
    return (
      <div className="min-h-screen bg-[#030014] text-[#f4f4f7] relative overflow-hidden font-sans flex flex-col justify-center items-center px-4">
        {/* Ambient background glows */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[rgba(139,92,246,0.12)] rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[rgba(59,130,246,0.12)] rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

        <Card className="w-full max-w-md glass-panel border-violet-500/20 shadow-2xl relative overflow-hidden rounded-3xl animate-in fade-in zoom-in-95 duration-300">
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
          <CardHeader className="space-y-2 pt-8">
            <div className="flex justify-center items-center gap-3 mb-2">
              {logoUrl ? (
                <img src={logoUrl} alt="OctaOS Logo" className="h-12 w-auto max-w-[160px] object-contain" />
              ) : (
                <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-violet-500/20">
                  <Zap className="text-white fill-white h-5 w-5 animate-pulse" />
                </div>
              )}
              <span className="text-white font-extrabold text-2xl tracking-tight">OctaOs</span>
            </div>
            <CardTitle className="text-2xl text-center text-white font-extrabold tracking-tight">Select Workspace</CardTitle>
            <CardDescription className="text-center text-gray-400 text-xs">
              You are associated with multiple companies. Select which one to manage.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pb-8">
            <div className="space-y-3">
              {tenantSelection.map((tenant) => (
                <button
                  key={tenant.id}
                  onClick={() => handleSelectCompany(tenant.id)}
                  className="w-full bg-gray-900/60 border border-gray-800 hover:border-violet-500 text-white font-bold py-3.5 rounded-xl shadow-lg hover:shadow-violet-500/20 transition-all hover:scale-[1.01] active:scale-95 flex items-center justify-between px-4 text-sm text-left"
                >
                  <span>{tenant.name}</span>
                  <span className="text-violet-400">&rarr;</span>
                </button>
              ))}
            </div>
            <div className="text-center text-xs text-gray-400 pt-4">
              <span className="text-violet-400 hover:text-violet-300 cursor-pointer font-bold transition-colors" onClick={() => setTenantSelection(null)}>Back to Login</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (otpSent) {"""

content = content.replace(ui_search, ui_replace)

with open(filepath, "w") as f:
    f.write(content)

print("auth-forms.tsx updated successfully.")

'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import AuthForms from '@/components/auth-forms';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

function SignupForm() {
  const searchParams = useSearchParams();
  const inviteToken = searchParams.get('token');
  const [logoUrl, setLogoUrl] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/auth/settings`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data?.logo_url) setLogoUrl(data.logo_url); })
      .catch(() => undefined);
  }, []);

  return <AuthForms appState="signup" API_URL={API_URL} logoUrl={logoUrl} inviteToken={inviteToken} />;
}

export default function SignupPage() {
  return (
    <Suspense fallback={null}>
      <SignupForm />
    </Suspense>
  );
}

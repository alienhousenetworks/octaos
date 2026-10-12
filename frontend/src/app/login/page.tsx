'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AuthForms from '@/components/auth-forms';
import { getAccessToken } from '@/lib/auth-session';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export default function LoginPage() {
  const router = useRouter();
  const [logoUrl, setLogoUrl] = useState<string | null>(null);

  useEffect(() => {
    if (getAccessToken()) router.replace('/app/home');
  }, [router]);

  useEffect(() => {
    fetch(`${API_URL}/auth/settings`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data?.logo_url) setLogoUrl(data.logo_url); })
      .catch(() => undefined);
  }, []);

  return <AuthForms appState="login" API_URL={API_URL} logoUrl={logoUrl} />;
}

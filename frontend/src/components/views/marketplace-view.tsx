'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Briefcase } from 'lucide-react';
import { marketplacePacks } from './marketplace-packs';

interface MarketplaceViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  apps: any[];
}

export default function MarketplaceView({
  token,
  API_URL,
  fetchWithAuth,
  fetchData,
  apps,
}: MarketplaceViewProps) {
  // Handlers copied from page.tsx
    const installApp = async (appName: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/marketplace/install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_name: appName })
      });
      if (res.ok) {
        fetchData();
        alert(`${appName} installed successfully!`);
      } else {
        alert(`Failed to install ${appName}.`);
      }
    } catch (e) {
      console.error(e);
    }
  };


    const uninstallApp = async (appName: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/dashboard/marketplace/uninstall`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_name: appName })
      });
      if (res.ok) {
        fetchData();
        alert(`${appName} deactivated successfully.`);
      } else {
        alert(`Failed to deactivate ${appName}.`);
      }
    } catch (e) {
      console.error(e);
    }
  };



  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
              <div>
                <h1 className="text-4xl font-extrabold text-white tracking-tight">Workflow Marketplace</h1>
                <p className="text-gray-400 mt-1">Install industry-specific AI workflows with one click.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {marketplacePacks.map(pack => {
                  const isInstalled = apps.some(a => a.app_name === pack.name);
                  return (
                    <Card key={pack.name} className="glass-panel border-transparent hover:border-pink-500/30 transition-all duration-300 rounded-3xl overflow-hidden shadow-2xl relative flex flex-col justify-between p-6">
                      <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-pink-500 to-transparent" />
                      <CardHeader className="p-0 pb-4">
                        <div className="flex items-center justify-between mb-4">
                          <span className="text-[9px] uppercase font-black tracking-widest text-pink-400 bg-pink-500/10 px-2.5 py-1 rounded-full border border-pink-500/20">
                            {pack.category}
                          </span>
                          <span className="text-[10px] font-bold text-emerald-450 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
                            {pack.timeSaved} saved
                          </span>
                        </div>
                        <div className="flex items-center gap-3 mb-2">
                          <div className="text-3xl p-2 bg-pink-500/10 rounded-2xl border border-pink-500/20 flex items-center justify-center h-12 w-12">{pack.icon}</div>
                          <CardTitle className="text-lg text-white font-extrabold mt-1">{pack.name}</CardTitle>
                        </div>
                        <CardDescription className="text-gray-300 text-xs mt-2 leading-relaxed">{pack.desc}</CardDescription>
                      </CardHeader>
                      <CardContent className="mt-auto pt-4 border-t border-gray-800/60 p-0 space-y-4">
                        <div className="space-y-2">
                          <span className="text-[10px] font-bold uppercase text-gray-500 tracking-wider">Features included:</span>
                          <ul className="space-y-1.5">
                            {pack.features.map((feat, idx) => (
                              <li key={idx} className="text-[11px] text-gray-400 flex items-center gap-2 leading-tight">
                                <span className="h-1 w-1 rounded-full bg-pink-500" />
                                <span>{feat}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div className="flex items-center justify-between pt-2 border-t border-gray-900 text-[10px] text-gray-500">
                          <span>Complexity: <span className="text-gray-300 font-semibold">{pack.complexity}</span></span>
                        </div>
                        <Button 
                          className={`w-full font-bold h-10 rounded-xl transition-all ${
                            isInstalled 
                              ? 'bg-transparent border border-gray-800 text-gray-500 cursor-not-allowed' 
                              : 'bg-pink-600 hover:bg-pink-500 text-white shadow-lg shadow-pink-500/20 hover:scale-[1.02] active:scale-95'
                          }`}
                          disabled={isInstalled}
                          onClick={() => installApp(pack.name)}
                        >
                          {isInstalled ? 'Installed ✓' : 'Install Pack'}
                        </Button>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
  );
}

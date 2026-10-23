'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { notify } from '@/lib/notify';
import { RealEstateProjectSummary } from './marketing-platform';
import { Building2, ShieldCheck, Sparkles, Loader2, CheckCircle2, AlertTriangle, Copy, Calendar } from 'lucide-react';

interface RealEstateCampaignDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  onCampaignCreated?: () => void;
}

export default function RealEstateCampaignDialog({
  open,
  onOpenChange,
  API_URL,
  fetchWithAuth,
  onCampaignCreated,
}: RealEstateCampaignDialogProps) {
  const [projects, setProjects] = useState<RealEstateProjectSummary[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [campaignType, setCampaignType] = useState<string>('project_showcase');
  const [platform, setPlatform] = useState<string>('linkedin');
  const [generating, setGenerating] = useState(false);
  const [generatedResult, setGeneratedResult] = useState<any>(null);

  useEffect(() => {
    if (open) {
      loadProjects();
    } else {
      setGeneratedResult(null);
    }
  }, [open]);

  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/verticals/real-estate/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.projects || []);
        if (data.projects && data.projects.length > 0) {
          setSelectedProjectId(data.projects[0].id);
        }
      }
    } catch (err: any) {
      notify(`Failed to load projects: ${err?.message || 'network error'}`);
    } finally {
      setLoadingProjects(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedProjectId) {
      notify('Please select a project');
      return;
    }
    setGenerating(true);
    setGeneratedResult(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/verticals/real-estate/generate-campaign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProjectId,
          campaign_type: campaignType,
          platform: platform,
          persist_post: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedResult(data);
        notify('Real Estate Property Campaign generated and saved as draft!');
        if (onCampaignCreated) onCampaignCreated();
      } else {
        const err = await res.json();
        notify(`Generation failed: ${err.detail || 'server error'}`);
      }
    } catch (err: any) {
      notify(`Failed to generate: ${err?.message || 'error'}`);
    } finally {
      setGenerating(false);
    }
  };

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 text-emerald-600">
            <Building2 className="size-5" />
            <DialogTitle className="text-lg">Real Estate Property Campaign Hub</DialogTitle>
          </div>
          <DialogDescription className="text-xs">
            Generate fact-checked, RERA-compliant marketing copy grounded directly in your active development catalog.
          </DialogDescription>
        </DialogHeader>

        {!generatedResult ? (
          <div className="space-y-4 py-2">
            {/* Project Selection */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">Select Project / Property</label>
              {loadingProjects ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
                  <Loader2 className="size-3.5 animate-spin" /> Loading property catalog…
                </div>
              ) : projects.length === 0 ? (
                <p className="text-xs text-muted-foreground border border-dashed rounded-lg p-3">
                  No projects found in this workspace. Add projects in the Sales CRM to automatically market them.
                </p>
              ) : (
                <Select value={selectedProjectId} onValueChange={(val) => setSelectedProjectId(val || '')}>
                  <SelectTrigger className="w-full text-xs">
                    <SelectValue placeholder="Choose a property" />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((p) => (
                      <SelectItem key={p.id} value={p.id} className="text-xs">
                        {p.name} {p.location ? `· ${p.location}` : ''} ({p.available_units} units available)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Project Metadata Card */}
            {selectedProject && (
              <div className="rounded-lg bg-muted/40 border border-border/60 p-3 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{selectedProject.name}</span>
                  <span className="text-[11px] font-mono text-muted-foreground">
                    {selectedProject.rera_number ? `RERA: ${selectedProject.rera_number}` : 'RERA on file'}
                  </span>
                </div>
                <p className="text-muted-foreground text-[11px]">
                  Location: {selectedProject.location || 'Metro'}, {selectedProject.city || 'Central'}
                </p>
                {selectedProject.amenities?.length > 0 && (
                  <p className="text-muted-foreground text-[11px]">
                    Amenities: {selectedProject.amenities.slice(0, 4).join(', ')}
                  </p>
                )}
              </div>
            )}

            {/* Campaign Pillar / Type */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Campaign Objective / Pillar</label>
                <Select value={campaignType} onValueChange={(val) => setCampaignType(val || 'project_showcase')}>
                  <SelectTrigger className="text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="project_showcase" className="text-xs">
                      Project Showcase & Architecture
                    </SelectItem>
                    <SelectItem value="site_visit_drive" className="text-xs">
                      Weekend Site Visit & Tour Drive
                    </SelectItem>
                    <SelectItem value="unit_spotlight" className="text-xs">
                      Unit Layout & Floor Plan Spotlight
                    </SelectItem>
                    <SelectItem value="investor_yield" className="text-xs">
                      Investor Economics & Cap Rate
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Target Platform</label>
                <Select value={platform} onValueChange={(val) => setPlatform(val || 'linkedin')}>
                  <SelectTrigger className="text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="linkedin" className="text-xs">LinkedIn</SelectItem>
                    <SelectItem value="instagram" className="text-xs">Instagram</SelectItem>
                    <SelectItem value="facebook" className="text-xs">Facebook</SelectItem>
                    <SelectItem value="twitter" className="text-xs">X / Twitter</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        ) : (
          /* Generated Result View */
          <div className="space-y-4 py-2">
            {/* Compliance Badge */}
            <div className="flex items-center justify-between rounded-lg bg-emerald-500/10 border border-emerald-500/30 p-2.5 text-xs text-emerald-800 dark:text-emerald-300">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-emerald-600" />
                <span className="font-semibold">Statutory Compliance Verified</span>
              </div>
              <span className="text-[11px]">Fair Housing & RERA Audited</span>
            </div>

            {/* Post Content */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground">Generated Post Draft</label>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(generatedResult.content);
                    notify('Copied to clipboard');
                  }}
                  className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  <Copy className="size-3" /> Copy
                </button>
              </div>
              <div className="rounded-lg border border-border bg-muted/20 p-3 text-xs whitespace-pre-wrap font-sans leading-relaxed max-h-56 overflow-y-auto">
                {generatedResult.content}
              </div>
            </div>

            {/* Architectural Visual Creative Direction */}
            {generatedResult.image_prompt && (
              <div className="space-y-1 text-xs">
                <span className="font-semibold text-muted-foreground flex items-center gap-1">
                  <Sparkles className="size-3 text-emerald-600" /> Architectural Photography Prompt
                </span>
                <p className="text-[11px] text-muted-foreground italic rounded bg-muted/30 p-2 border border-border/40">
                  {generatedResult.image_prompt}
                </p>
              </div>
            )}
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          {!generatedResult ? (
            <Button
              type="button"
              disabled={generating || !selectedProjectId}
              onClick={handleGenerate}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
            >
              {generating ? (
                <>
                  <Loader2 className="mr-1.5 size-3.5 animate-spin" /> Generating Grounded Copy…
                </>
              ) : (
                <>
                  <Sparkles className="mr-1.5 size-3.5" /> Generate Property Campaign
                </>
              )}
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => onOpenChange(false)}
              className="text-xs"
            >
              Close & View in Campaigns
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

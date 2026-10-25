'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { notify } from '@/lib/notify';
import {
  Sparkles,
  Bot,
  Video,
  Image as ImageIcon,
  CheckCircle2,
  ShieldAlert,
  Loader2,
  Film,
  Send,
  Eye,
  RefreshCw,
  UserCheck,
  Radio,
} from 'lucide-react';

interface VirtualInfluencerStudioProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: RequestInit) => Promise<Response>;
  onPostCreated?: () => void;
  activeRoomId?: string | null;
  activeRoomSlug?: string | null;
}

interface PersonaOutput {
  name: string;
  persona: string;
  audience: string;
  voice: string;
  visual_prompt: string;
  intro_caption: string;
  content_pillars: string[];
  disclosure: string;
}

export default function VirtualInfluencerStudio({
  API_URL,
  fetchWithAuth,
  onPostCreated,
  activeRoomId,
  activeRoomSlug,
}: VirtualInfluencerStudioProps) {
  const [name, setName] = useState('');
  const [creativeDirection, setCreativeDirection] = useState('');
  const [audience, setAudience] = useState('');
  const [platform, setPlatform] = useState('instagram');
  const [generateImage, setGenerateImage] = useState(true);
  const [generateVideo, setGenerateVideo] = useState(false);
  const [imageProvider, setImageProvider] = useState('together');
  const [imageModel, setImageModel] = useState('black-forest-labs/FLUX.1-schnell');
  const [videoProvider, setVideoProvider] = useState('together');
  const [videoModel, setVideoModel] = useState('minimax/video-01');

  const [loading, setLoading] = useState(false);
  const [createdResult, setCreatedResult] = useState<{
    persona: PersonaOutput;
    post_id: string;
    image_url?: string;
    video_url?: string;
  } | null>(null);

  const presets = [
    {
      title: 'Tech & Automation Architect',
      name: 'Maya Stone',
      direction: 'Pragmatic enterprise AI builder who breaks down complex automation workflows in casual smartphone vlog style.',
      audience: 'CTOs, Engineering Leads, and Startup Founders',
      platform: 'linkedin',
    },
    {
      title: 'SaaS Growth & CRO Creator',
      name: 'Leo Vance',
      direction: 'High-energy D2C & SaaS growth strategist sharing contrarian marketing audits and teardowns in 9:16 vertical reels.',
      audience: 'Marketing Directors and Growth Hackers',
      platform: 'instagram',
    },
    {
      title: 'PropTech & Real Estate Host',
      name: 'Aria Chen',
      direction: 'Sophisticated architectural curator presenting modern luxury spaces and PropTech market analyses with calm, editorial elegance.',
      audience: 'High Net Worth Investors and Commercial Property Buyers',
      platform: 'instagram',
    },
  ];

  const handleApplyPreset = (p: typeof presets[0]) => {
    setName(p.name);
    setCreativeDirection(p.direction);
    setAudience(p.audience);
    setPlatform(p.platform);
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const payload = {
        name: name.trim() || undefined,
        creative_direction: creativeDirection.trim() || undefined,
        audience: audience.trim() || undefined,
        platform,
        generate_image: generateImage,
        generate_video: generateVideo,
        image_provider: imageProvider,
        image_model: imageModel,
        video_provider: videoProvider,
        video_model: videoModel,
        room_id: activeRoomId || undefined,
        room_slug: activeRoomSlug || undefined,
      };

      const res = await fetchWithAuth(`${API_URL}/marketing/virtual-influencer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server responded with ${res.status}`);
      }

      const data = await res.json();
      setCreatedResult({
        persona: data.persona,
        post_id: data.post_id,
        image_url: data.image_url,
        video_url: data.video_url,
      });

      notify(`Virtual influencer "${data.persona.name}" generated and queued in drafts!`);
      if (onPostCreated) {
        onPostCreated();
      }
    } catch (err: any) {
      console.error(err);
      notify.error(err.message || 'Failed to generate virtual influencer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Studio Header Card */}
      <div className="relative overflow-hidden rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-950/40 via-slate-900 to-slate-950 p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5 max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-300">
              <Bot className="size-3.5 text-purple-400" />
              <span>Autonomous AI Influencer & Creator Studio</span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Synthesize Brand-Safe Virtual Creators & Video Reels
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed">
              Generate original fictional brand ambassadors with consistent visual traits, 9:16 vertical video reel scripts, and built-in regulatory synthetic disclosures. Never hallucinates real human identity.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
              <CheckCircle2 className="size-3.5" />
              <span>FTC Synthetic Disclosure Ready</span>
            </span>
          </div>
        </div>

        {/* Quick Presets Bar */}
        <div className="mt-5 border-t border-purple-500/20 pt-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-purple-300 mb-2">
            One-Click Creator Archetypes
          </p>
          <div className="flex flex-wrap gap-2">
            {presets.map((preset) => (
              <button
                key={preset.title}
                type="button"
                onClick={() => handleApplyPreset(preset)}
                className="flex items-center gap-2 rounded-lg border border-purple-500/20 bg-purple-950/30 px-3 py-1.5 text-xs text-purple-200 hover:border-purple-400/50 hover:bg-purple-900/40 transition shadow-xs"
              >
                <Sparkles className="size-3 text-purple-400" />
                <span className="font-medium">{preset.title}</span>
                <span className="text-[10px] text-purple-400/80 font-mono">({preset.name})</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Studio Two-Column Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left Column: Creator Formulation Controls (6 cols) */}
        <div className="lg:col-span-6 space-y-4 rounded-xl border border-border bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <Sparkles className="size-4 text-purple-500" />
              <span>Persona & Content Directives</span>
            </h3>
            <span className="text-xs text-muted-foreground">Step 1 of 2</span>
          </div>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Persona Name / Creator Handle</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Maya Stone, Alex Vance (Leave blank for AI to invent)"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Vibe, Identity & Role Direction</label>
              <Textarea
                value={creativeDirection}
                onChange={(e) => setCreativeDirection(e.target.value)}
                placeholder="Describe their communication style, filming environment, and personality. (e.g. Energetic startup builder holding smartphone in modern loft studio, casual tech breakdown, authentic lighting)"
                className="min-h-24"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Target Audience</label>
                <Input
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  placeholder="e.g. B2B decision makers, Gen Z shoppers"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">Primary Social Platform</label>
                <Select value={platform} onValueChange={(val) => val && setPlatform(val)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="instagram">Instagram (Reels & Feed)</SelectItem>
                    <SelectItem value="linkedin">LinkedIn (Creator Mode)</SelectItem>
                    <SelectItem value="facebook">Facebook (Stories & Video)</SelectItem>
                    <SelectItem value="twitter">X / Twitter (Social Clip)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Media Generation Switches */}
            <div className="rounded-lg border border-border/80 bg-muted/20 p-3 space-y-3">
              <p className="text-xs font-semibold text-foreground">Media Rendering Assets</p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setGenerateImage((v) => !v)}
                  className={`flex items-center gap-2 rounded-lg border p-2.5 text-xs text-left transition ${
                    generateImage
                      ? 'border-purple-500 bg-purple-500/10 text-foreground font-medium'
                      : 'border-border text-muted-foreground hover:bg-muted/40'
                  }`}
                >
                  <ImageIcon className="size-4 text-purple-400" />
                  <div>
                    <span className="block font-medium">Portrait Avatar</span>
                    <span className="block text-[10px] text-muted-foreground">FLUX.1 Photorealistic</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setGenerateVideo((v) => !v)}
                  className={`flex items-center gap-2 rounded-lg border p-2.5 text-xs text-left transition ${
                    generateVideo
                      ? 'border-purple-500 bg-purple-500/10 text-foreground font-medium'
                      : 'border-border text-muted-foreground hover:bg-muted/40'
                  }`}
                >
                  <Video className="size-4 text-purple-400" />
                  <div>
                    <span className="block font-medium">Video Reel Intro</span>
                    <span className="block text-[10px] text-muted-foreground">Wan2.1 / MiniMax 9:16</span>
                  </div>
                </button>
              </div>

              {/* Optional Advanced Models Accordion */}
              <details className="text-xs pt-1">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground font-medium">
                  Custom Model Routing (Auto Configured)
                </summary>
                <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-border/60">
                  <div>
                    <label className="text-[10px] text-muted-foreground">Image Provider</label>
                    <Select value={imageProvider} onValueChange={(val) => val && setImageProvider(val)}>
                      <SelectTrigger className="h-7 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="together">Together AI</SelectItem>
                        <SelectItem value="openrouter">OpenRouter</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Image Model</label>
                    <Input
                      value={imageModel}
                      onChange={(e) => setImageModel(e.target.value)}
                      className="h-7 text-xs font-mono"
                    />
                  </div>
                </div>
              </details>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-semibold shadow-md gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>Synthesizing Persona & Video Reel...</span>
                </>
              ) : (
                <>
                  <Sparkles className="size-4" />
                  <span>Create Virtual Influencer & Queue Post</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Right Column: Live Creator Preview & Launch Output (6 cols) */}
        <div className="lg:col-span-6 space-y-4 rounded-xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <UserCheck className="size-4 text-emerald-500" />
              <span>Persona Profile & Verification Preview</span>
            </h3>
            {createdResult && (
              <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                Created & Queued
              </span>
            )}
          </div>

          {!createdResult && !loading && (
            <div className="flex flex-col items-center justify-center p-8 text-center text-muted-foreground min-h-80 border border-dashed border-border/80 rounded-lg">
              <Bot className="size-12 mb-3 text-purple-400/60 animate-bounce" />
              <p className="text-sm font-semibold text-foreground">No Virtual Influencer Formulated Yet</p>
              <p className="text-xs text-muted-foreground max-w-sm mt-1">
                Pick a creator preset on the left or enter custom directives. The AI council will synthesize their voice, generate avatar visuals, and compose a launch video reel.
              </p>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center p-12 text-center text-muted-foreground min-h-80 border border-border rounded-lg bg-muted/10 space-y-3">
              <Loader2 className="size-8 animate-spin text-purple-500" />
              <p className="text-sm font-medium text-foreground">Running Virtual Influencer Creative Director...</p>
              <p className="text-xs text-muted-foreground max-w-xs">
                Generating brand-safe persona brief, compiling photographic visual prompt, and rendering media assets.
              </p>
            </div>
          )}

          {createdResult && !loading && (
            <div className="space-y-4">
              {/* Persona Identity Badge */}
              <div className="rounded-lg border border-purple-500/30 bg-purple-500/5 p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-base font-bold text-foreground flex items-center gap-2">
                      <span>{createdResult.persona.name}</span>
                      <span className="rounded bg-purple-500/20 text-purple-300 px-1.5 py-0.5 text-[10px] font-semibold uppercase">
                        AI Persona
                      </span>
                    </h4>
                    <p className="text-xs text-muted-foreground mt-0.5 leading-snug">
                      {createdResult.persona.persona}
                    </p>
                  </div>
                  <span className="text-[11px] font-mono text-muted-foreground shrink-0 uppercase">
                    {platform}
                  </span>
                </div>

                {/* Media Preview (Video or Image) */}
                {createdResult.video_url && (
                  <div className="overflow-hidden rounded-lg border border-border bg-black">
                    <video
                      src={createdResult.video_url}
                      controls
                      loop
                      playsInline
                      className="w-full max-h-80 object-contain mx-auto"
                    />
                    <p className="p-1.5 text-[10px] text-slate-400 font-mono text-center">
                      9:16 Vertical Video Reel
                    </p>
                  </div>
                )}

                {!createdResult.video_url && createdResult.image_url && (
                  <div className="overflow-hidden rounded-lg border border-border bg-muted">
                    <img
                      src={createdResult.image_url}
                      alt={createdResult.persona.name}
                      className="w-full max-h-80 object-cover"
                    />
                    <p className="p-1.5 text-[10px] text-muted-foreground text-center">
                      FLUX.1 Photorealistic Portrait Avatar
                    </p>
                  </div>
                )}

                {/* Content Pillars */}
                {createdResult.persona.content_pillars?.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[10px] font-semibold text-muted-foreground uppercase">
                      Content Pillars:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {createdResult.persona.content_pillars.map((pil, idx) => (
                        <span
                          key={idx}
                          className="rounded bg-muted/60 border border-border/80 px-2 py-0.5 text-[10px] text-foreground"
                        >
                          {pil}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Launch Post Caption */}
                <div className="space-y-1 border-t border-border/60 pt-2">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase">
                    Launch Reel Caption:
                  </span>
                  <div className="max-h-36 overflow-y-auto rounded bg-card p-2.5 text-xs text-foreground leading-relaxed whitespace-pre-wrap border border-border">
                    {createdResult.persona.intro_caption}
                  </div>
                </div>

                {/* Regulatory Disclosure Banner */}
                <div className="flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-300">
                  <ShieldAlert className="size-4 shrink-0 text-amber-400" />
                  <span className="text-[11px] leading-tight font-medium">
                    {createdResult.persona.disclosure} (Saved with post)
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                <span>Post ID: <code className="font-mono">{createdResult.post_id.slice(0, 8)}...</code></span>
                <span className="text-emerald-500 font-medium">Ready in Review Queue</span>
              </div>
            </div>
          )}

          {/* Footer reassurance */}
          <div className="border-t border-border/60 pt-3 flex items-center justify-between text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <Bot className="size-3 text-purple-400" /> OctaOS Autonomy Layer
            </span>
            <span>All virtual influencer posts require human sign-off</span>
          </div>
        </div>
      </div>
    </div>
  );
}

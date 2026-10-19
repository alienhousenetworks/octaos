'use client';

import { notify } from '@/lib/notify';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import PageHeader from '@/components/shell/page-header';
import { EmptyState } from '@/components/shell/states';
import {
  AlertCircle,
  CalendarRange,
  CheckCircle2,
  Clock,
  Cpu,
  Edit2,
  Eye,
  FileText,
  Film,
  Hash,
  Heart,
  HelpCircle,
  Image as ImageIcon,
  LayoutGrid,
  Loader2,
  MessageSquare,
  Plus,
  Repeat,
  Search,
  Send,
  Share2,
  Sparkles,
  ThumbsUp,
  Trash2,
  TrendingUp,
  UploadCloud,
  X,
} from 'lucide-react';
import TriggerScheduleCard from '@/components/ui/trigger-schedule-card';
import AutonomousMarketingRadar from '@/components/views/autonomous-marketing-radar';

interface CuratedModelItem {
  provider: string;
  slug: string;
  display_name: string;
  specialty: string;
  badge: string;
  modality: string;
  status: string;
  has_api_key?: boolean;
  pricing?: { prompt?: string; completion?: string; image?: string; per_second?: string };
}

interface ValidationResult {
  status: 'idle' | 'validating' | 'available' | 'incompatible' | 'not_found' | 'no_key' | 'unverified';
  message?: string;
  suggestions?: string[];
  pricing?: any;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <label className="text-xs font-medium text-muted-foreground">{children}</label>;
}

function platformName(value?: string) {
  if (value === 'linkedin') return 'LinkedIn';
  if (value === 'instagram') return 'Instagram';
  if (value === 'facebook') return 'Facebook';
  if (value === 'twitter' || value === 'x') return 'X / Twitter';
  return value || 'Unknown';
}

function statusName(value?: string) {
  if (value === 'pending') return 'Needs review';
  if (value === 'approved' || value === 'scheduled') return 'Scheduled';
  if (value === 'published') return 'Published';
  if (value === 'rejected') return 'Rejected';
  if (value === 'failed') return 'Generation Failed';
  return value || 'Unknown';
}

function ModelPicks({ models, active, onPick }: { models: CuratedModelItem[]; active: string; onPick: (slug: string) => void }) {
  if (models.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {models.slice(0, 5).map((model) => (
        <button
          key={model.slug}
          type="button"
          onClick={() => onPick(model.slug)}
          className={`rounded-md border px-2 py-0.5 text-xs ${active === model.slug ? 'border-primary bg-primary/10 text-foreground' : 'border-border text-muted-foreground hover:bg-muted/40'}`}
        >
          {model.display_name}
        </button>
      ))}
    </div>
  );
}

function ValidationNote({ result, onUse }: { result: ValidationResult; onUse?: (slug: string) => void }) {
  if (result.status === 'idle') return null;
  if (result.status === 'validating') {
    return <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><Loader2 className="size-3 animate-spin" /> Checking this model</p>;
  }
  if (result.status === 'available') {
    const price = [
      result.pricing?.prompt ? `Input ${result.pricing.prompt}` : '',
      result.pricing?.completion ? `Output ${result.pricing.completion}` : '',
    ].filter(Boolean).join(' · ');
    return (
      <p className="text-xs text-muted-foreground">
        <CheckCircle2 className="mr-1 inline size-3 text-primary" />
        Model is available{price ? ` · ${price}` : ''}
      </p>
    );
  }
  if (result.status === 'incompatible') {
    return <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><AlertCircle className="size-3" /> {result.message || 'This model does not support that output.'}</p>;
  }
  if (result.status === 'not_found' || result.status === 'no_key') {
    return (
      <div className="space-y-1 text-xs text-muted-foreground">
        <p className="flex items-center gap-1.5"><AlertCircle className="size-3" /> {result.message || 'Model was not found for this provider.'}</p>
        {result.suggestions && result.suggestions.length > 0 && onUse && (
          <p className="flex flex-wrap items-center gap-1">
            <span>Try</span>
            {result.suggestions.map((slug) => (
              <button key={slug} type="button" className="font-mono text-primary underline" onClick={() => onUse(slug)}>{slug}</button>
            ))}
          </p>
        )}
      </div>
    );
  }
  return <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><HelpCircle className="size-3" /> {result.message || 'This slug was not verified.'}</p>;
}

interface CampaignStageItem {
  id: string;
  name: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  desc?: string;
}

interface CampaignStageLog {
  stage: string;
  message: string;
  timestamp: string;
}

interface ActiveCampaignJobState {
  jobId: string;
  status: string;
  progressPct: number;
  currentStage?: string;
  stages: CampaignStageItem[];
  logs: CampaignStageLog[];
  topic?: string;
  days?: number;
  error?: string;
}

const DEFAULT_CAMPAIGN_STAGES: CampaignStageItem[] = [
  { id: 'context', name: 'Brand Context Anchor (Agents 1-5)', status: 'pending', desc: 'Ingesting Brand DNA, Product Catalog, Audience ICP, and Proof Points' },
  { id: 'strategy', name: 'Campaign Strategy & Narrative (Agent 6)', status: 'pending', desc: 'Synthesizing master positioning, tone tokens, and narrative arc' },
  { id: 'narrative', name: 'Multi-Slot Cadence Scheduling (Agent 7)', status: 'pending', desc: 'Structuring chronological daily time slots across networks' },
  { id: 'drafting', name: 'Platform Copywriting & Hooks (Agents 8-10)', status: 'pending', desc: 'Crafting platform-native copy, viral opening hooks, and conversion CTAs' },
  { id: 'creative', name: 'Visual Art & Video Scene Direction (Agents 11 & 12)', status: 'pending', desc: 'Compiling photographic image prompts and video shot kinetics' },
  { id: 'compliance', name: 'Dual Fact-Checking & Compliance (Agents 13 & 14)', status: 'pending', desc: 'Verifying grounded claims, brand voice, and safety rules' },
  { id: 'dispatch', name: 'Executive CMO Dispatch & Scheduling (Agent 15)', status: 'pending', desc: 'CMO final authorization and calendar publication dispatch' },
];

interface CampaignsViewProps {
  token: string | null;
  activeView?: string;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  configuredProviders: string[];
}

export default function CampaignsView({
  token,
  activeView,
  API_URL,
  fetchWithAuth,
  fetchData,
  configuredProviders,
}: CampaignsViewProps) {
  // State variables relocated here
  const [campaignTopic, setCampaignTopic] = useState('');
  const [campaignDays, setCampaignDays] = useState(30);
  const [campaignPlatforms, setCampaignPlatforms] = useState<string[]>(['linkedin', 'instagram', 'facebook']);
  const [contentFormat, setContentFormat] = useState<string>('social_posts');
  const [referenceImageUrl, setReferenceImageUrl] = useState<string>('');
  
  // Multimodal model states & live catalogs
  const [curatedModels, setCuratedModels] = useState<CuratedModelItem[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  const [textProvider, setTextProvider] = useState('openrouter');
  const [textModel, setTextModel] = useState<string>('meta-llama/llama-3.3-70b-instruct');
  const [textValidation, setTextValidation] = useState<ValidationResult>({ status: 'idle' });

  const [generateImages, setGenerateImages] = useState(true);
  const [imageProvider, setImageProvider] = useState('together');
  const [imageModel, setImageModel] = useState<string>('black-forest-labs/FLUX.1-schnell');
  const [imageValidation, setImageValidation] = useState<ValidationResult>({ status: 'idle' });

  // In-app video generation enabled via meta-hub provider adapters
  const ENABLE_IN_APP_VIDEO = true;
  const [generateVideos, setGenerateVideos] = useState(false);
  const [videoProvider, setVideoProvider] = useState('together');
  const [videoModel, setVideoModel] = useState<string>('minimax/video-01');
  const [videoValidation, setVideoValidation] = useState<ValidationResult>({ status: 'idle' });

  // Asynchronous video generation tracking
  const [animatingPostJobs, setAnimatingPostJobs] = useState<Record<string, { jobId: string; status: string; progress: number; error?: string }>>({});

  const [generateRemotion, setGenerateRemotion] = useState(false);
  const [campaignPosts, setCampaignPosts] = useState<any[]>([]);
  const [campaignFilterPlatform, setCampaignFilterPlatform] = useState<string>('all');
  const [campaignFilterStatus, setCampaignFilterStatus] = useState<string>('all');
  const [postQuery, setPostQuery] = useState('');
  const [publishNoteFor, setPublishNoteFor] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});
  const [isGeneratorExpanded, setIsGeneratorExpanded] = useState<boolean>(true);
  const [postsPerDay, setPostsPerDay] = useState<number>(1);
  const [activeCampaignJob, setActiveCampaignJob] = useState<ActiveCampaignJobState | null>(null);
  const [showConfigWhileGenerating, setShowConfigWhileGenerating] = useState<boolean>(false);
  const [campaignViewMode, setCampaignViewMode] = useState<'timeline' | 'kanban' | 'analytics' | 'schedule'>('timeline');
  const [loading, setLoading] = useState(false);
  const [analyticsDash, setAnalyticsDash] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsSyncing, setAnalyticsSyncing] = useState(false);

  const [editingPostId, setEditingPostId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const [editingImageUrl, setEditingImageUrl] = useState('');
  const [editingVideoUrl, setEditingVideoUrl] = useState('');
  const [editingImagePrompt, setEditingImagePrompt] = useState('');
  const [editingImagePromptEnabled, setEditingImagePromptEnabled] = useState(false);
  const [editingVideoPrompt, setEditingVideoPrompt] = useState('');
  const [editingVideoPromptEnabled, setEditingVideoPromptEnabled] = useState(false);
  const [editingRemotionPrompt, setEditingRemotionPrompt] = useState('');
  const [editingRemotionPromptEnabled, setEditingRemotionPromptEnabled] = useState(false);
  const [editingIsManualMedia, setEditingIsManualMedia] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [generatingMedia, setGeneratingMedia] = useState(false);
  const [suggestingPrompt, setSuggestingPrompt] = useState(false);
  const [regeneratingPostId, setRegeneratingPostId] = useState<string | null>(null);

  const fetchAnalyticsDashboard = async () => {
    if (!token) return;
    setAnalyticsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/analytics/dashboard`);
      if (res.ok) setAnalyticsDash(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const syncAnalytics = async () => {
    if (!token) return;
    setAnalyticsSyncing(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/analytics/sync?background=false&limit=50`, {
        method: 'POST',
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        notify(`Synced: ${data.synced ?? 0} posts · Patterns updated: ${data.patterns_updated ?? 0}`);
        await fetchAnalyticsDashboard();
        await fetchData();
      } else {
        notify(data.detail || 'Analytics sync failed — ensure Meta/LinkedIn OAuth and published posts have external IDs.');
      }
    } catch (e) {
      console.error(e);
      notify('Analytics sync failed');
    } finally {
      setAnalyticsSyncing(false);
    }
  };

  useEffect(() => {
    if (token && campaignViewMode === 'analytics') {
      fetchAnalyticsDashboard();
    }
  }, [token, campaignViewMode]);

  const [isCreatePostOpen, setIsCreatePostOpen] = useState(false);
  const [createPostPlatforms, setCreatePostPlatforms] = useState<string[]>(['linkedin']);
  const [createPostPlatform, setCreatePostPlatform] = useState('linkedin');
  const [createPostContent, setCreatePostContent] = useState('');
  const [createPostTags, setCreatePostTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [createPostDay, setCreatePostDay] = useState(1);
  const [createPostImageUrl, setCreatePostImageUrl] = useState('');
  const [createPostVideoUrl, setCreatePostVideoUrl] = useState('');
  const [createPostMediaInputMode, setCreatePostMediaInputMode] = useState<'upload' | 'url'>('upload');
  const [createPostImagePrompt, setCreatePostImagePrompt] = useState('');
  const [createPostImagePromptEnabled, setCreatePostImagePromptEnabled] = useState(false);
  const [createPostVideoPrompt, setCreatePostVideoPrompt] = useState('');
  const [createPostVideoPromptEnabled, setCreatePostVideoPromptEnabled] = useState(false);
  const [createPostRemotionPrompt, setCreatePostRemotionPrompt] = useState('');
  const [createPostRemotionPromptEnabled, setCreatePostRemotionPromptEnabled] = useState(false);
  const [createPostIsManualMedia, setCreatePostIsManualMedia] = useState(true);
  const [createPostPublishMode, setCreatePostPublishMode] = useState<'schedule' | 'now' | 'draft'>('schedule');
  const [creatingPost, setCreatingPost] = useState(false);
  const [editingScheduledAt, setEditingScheduledAt] = useState('');
  const [createPostScheduledAt, setCreatePostScheduledAt] = useState('');
  const [activePreviewPlatform, setActivePreviewPlatform] = useState<string>('linkedin');
  const [isDragOver, setIsDragOver] = useState(false);

  const [isBulkScheduleOpen, setIsBulkScheduleOpen] = useState(false);
  const [bulkStartDate, setBulkStartDate] = useState('');
  const [bulkEndDate, setBulkEndDate] = useState('');
  const [bulkPostingTime, setBulkPostingTime] = useState('09:00');
  const [bulkScheduling, setBulkScheduling] = useState(false);

  const [publishingPostId, setPublishingPostId] = useState<string | null>(null);
  const [publishResult, setPublishResult] = useState<{success: boolean; message: string} | null>(null);
  const [isMetaModalOpen, setIsMetaModalOpen] = useState(false);
  const [pendingPublishPostId, setPendingPublishPostId] = useState<string | null>(null);
  const [metaTokenInput, setMetaTokenInput] = useState('');
  const [savingMetaToken, setSavingMetaToken] = useState(false);

  // Fetch available curated and custom models
  const fetchAvailableModels = async () => {
    if (!token) return;
    setModelsLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/models`);
      if (res.ok) {
        const data = await res.json();
        const allModels = [...(data.curated || []), ...(data.custom || [])];
        setCuratedModels(allModels);
      }
    } catch (e) {
      console.error("Error loading marketing models:", e);
    } finally {
      setModelsLoading(false);
    }
  };

  // Debounced model validator helper
  const validateModelSlug = async (
    provider: string,
    modality: 'text' | 'image' | 'video',
    slug: string,
    setValidation: React.Dispatch<React.SetStateAction<ValidationResult>>
  ) => {
    if (!token || !slug || provider === 'auto') {
      setValidation({ status: 'idle' });
      return;
    }
    setValidation({ status: 'validating' });
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/models/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          modality,
          model: slug,
          mode: modality === 'text' ? 'text_to_text' : (modality === 'image' ? 'text_to_image' : 'text_to_video')
        })
      });
      if (res.ok) {
        const data = await res.json();
        setValidation({
          status: data.status,
          message: data.message,
          suggestions: data.suggestions,
          pricing: data.pricing
        });
      } else {
        setValidation({ status: 'unverified', message: 'Unable to verify model slug' });
      }
    } catch (e) {
      setValidation({ status: 'unverified', message: 'Network probe bypassed' });
    }
  };

  // Reactive debounced validation
  useEffect(() => {
    const timer = setTimeout(() => {
      if (textProvider !== 'auto' && textModel) {
        validateModelSlug(textProvider, 'text', textModel, setTextValidation);
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [textProvider, textModel]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (generateImages && imageProvider && imageModel) {
        validateModelSlug(imageProvider, 'image', imageModel, setImageValidation);
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [generateImages, imageProvider, imageModel]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (generateVideos && videoProvider && videoModel) {
        validateModelSlug(videoProvider, 'video', videoModel, setVideoValidation);
      }
    }, 450);
    return () => clearTimeout(timer);
  }, [generateVideos, videoProvider, videoModel]);

  // Polling active campaign generation job stages
  const startPollingCampaignJob = (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetchWithAuth(`${API_URL}/marketing/jobs/${jobId}`);
        if (!res.ok) return;
        const data = await res.json();
        setActiveCampaignJob((prev) => {
          const rawStages = data.stages && data.stages.length > 0 ? data.stages : (prev?.stages || DEFAULT_CAMPAIGN_STAGES);
          return {
            jobId: data.job_id,
            status: data.status,
            progressPct: data.progress_pct ?? prev?.progressPct ?? 10,
            currentStage: data.current_stage || prev?.currentStage,
            stages: rawStages,
            logs: data.stage_logs && data.stage_logs.length > 0 ? data.stage_logs : (prev?.logs || []),
            topic: data.topic || prev?.topic,
            days: data.days || prev?.days,
            error: data.error,
          };
        });

        if (data.status === 'completed') {
          clearInterval(pollInterval);
          notify("🎉 Campaign generation complete! All posts have been added to your timeline.");
          fetchCampaignPosts();
        } else if (data.status === 'failed') {
          clearInterval(pollInterval);
          notify(`Campaign generation failed: ${data.error || 'Unknown error'}`);
        }
      } catch (err) {
        console.error("Error polling campaign job:", err);
      }
    }, 2500);
  };

  const checkActiveCampaignJob = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/campaign/active-job`);
      if (res.ok) {
        const data = await res.json();
        if ((data.has_active || data.recently_finished) && data.job) {
          setActiveCampaignJob({
            jobId: data.job.job_id,
            status: data.job.status,
            progressPct: data.job.progress_pct ?? 10,
            currentStage: data.job.current_stage,
            stages: data.job.stages && data.job.stages.length > 0 ? data.job.stages : DEFAULT_CAMPAIGN_STAGES,
            logs: data.job.stage_logs || [],
            topic: data.job.topic,
            days: data.job.days,
            error: data.job.error,
          });
          setIsGeneratorExpanded(true);
          if (data.has_active) {
            startPollingCampaignJob(data.job.job_id);
          }
        }
      }
    } catch (e) {
      console.error("Error checking active campaign job:", e);
    }
  };

  // Fetch campaign posts periodically when active
  useEffect(() => {
    if (token && activeView === 'campaigns') {
      fetchCampaignPosts(true);
      fetchAvailableModels();
      checkActiveCampaignJob();
      const interval = setInterval(() => {
        fetchCampaignPosts(false);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [token, activeView]);

  // Handler functions
  const fetchCampaignPosts = async (collapseIfHasData = false) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/`);
      if (res.ok) {
        const data = await res.json();
        setCampaignPosts(data);
        if (collapseIfHasData && data && data.length > 0 && !activeCampaignJob) {
          setIsGeneratorExpanded(false);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Animate static post image into high-impact dynamic video loop
  const handleAnimatePostToVideo = async (postId: string) => {
    const post = campaignPosts.find(p => p.id === postId);
    if (!post || !post.image_url) {
      notify("No image available to animate.");
      return;
    }
    try {
      setAnimatingPostJobs(prev => ({
        ...prev,
        [postId]: { jobId: '', status: 'queued', progress: 5 }
      }));
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/animate-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: videoProvider || 'together',
          model: videoModel || 'Wan-AI/Wan2.1-I2V-14B',
          prompt: post.video_prompt || post.content?.slice(0, 100),
          aspect_ratio: '16:9'
        })
      });
      const data = await res.json();
      if (res.ok && data.job_id) {
        const jobId = data.job_id;
        setAnimatingPostJobs(prev => ({
          ...prev,
          [postId]: { jobId, status: 'in_progress', progress: 15 }
        }));
        notify("🎬 Video animation job dispatched! Rendering in progress...");
        
        // Poll job status every 3 seconds
        const pollInterval = setInterval(async () => {
          try {
            const jobRes = await fetchWithAuth(`${API_URL}/marketing/jobs/${jobId}`);
            if (jobRes.ok) {
              const jobData = await jobRes.json();
              if (jobData.status === 'completed') {
                clearInterval(pollInterval);
                setAnimatingPostJobs(prev => {
                  const next = { ...prev };
                  delete next[postId];
                  return next;
                });
                setCampaignPosts(prev => prev.map(p => p.id === postId ? { ...p, video_url: jobData.result_url } : p));
                notify("🎬 Video animation complete! Dynamic loop attached.");
                fetchCampaignPosts();
              } else if (jobData.status === 'failed') {
                clearInterval(pollInterval);
                setAnimatingPostJobs(prev => ({
                  ...prev,
                  [postId]: { jobId, status: 'failed', progress: 0, error: jobData.error || 'Animation failed' }
                }));
                notify(`Video animation failed: ${jobData.error || 'Unknown error'}`);
              } else {
                setAnimatingPostJobs(prev => ({
                  ...prev,
                  [postId]: { jobId, status: 'in_progress', progress: Math.min(95, (prev[postId]?.progress || 15) + 12) }
                }));
              }
            }
          } catch (err) {
            console.error("Error polling video animation job:", err);
          }
        }, 3000);
      } else {
        setAnimatingPostJobs(prev => {
          const next = { ...prev };
          delete next[postId];
          return next;
        });
        notify(`Failed to animate: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error("Error dispatching animate job:", e);
      setAnimatingPostJobs(prev => {
        const next = { ...prev };
        delete next[postId];
        return next;
      });
      notify("Network error starting video animation.");
    }
  };

  const handleLaunchCampaign = async () => {
    if (!campaignTopic) return;
    if (campaignDays < 1 || campaignDays > 30) {
      notify("You can schedule up to 30 days at a time.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/campaign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: campaignTopic,
          days: campaignDays,
          platforms: campaignPlatforms,
          content_format: contentFormat,
          reference_image_url: referenceImageUrl.trim() || undefined,
          text: textProvider === 'auto' ? undefined : { provider: textProvider, model: textModel },
          image: generateImages ? { provider: imageProvider, model: imageModel } : undefined,
          video: (ENABLE_IN_APP_VIDEO && generateVideos) ? { provider: videoProvider, model: videoModel } : undefined,
          text_provider: textProvider === 'auto' ? undefined : textProvider,
          text_model: textProvider === 'auto' ? undefined : textModel,
          image_provider: imageProvider,
          image_model: imageModel,
          video_provider: videoProvider,
          video_model: videoModel,
          generate_images: generateImages,
          generate_videos: ENABLE_IN_APP_VIDEO && generateVideos,
          generate_remotion: ENABLE_IN_APP_VIDEO && generateRemotion,
          posts_per_day: postsPerDay,
        })
      });
      const data = await res.json();
      if (res.ok) {
        notify(`${campaignDays}-Day Marketing Campaign launched! Live stage tracking started.`);
        if (data.job_id) {
          setActiveCampaignJob({
            jobId: data.job_id,
            status: 'queued',
            progressPct: 5,
            currentStage: 'Queued in Pipeline',
            stages: DEFAULT_CAMPAIGN_STAGES.map((s) => ({ ...s })),
            logs: [
              {
                stage: 'Queue',
                message: `Campaign generation requested for "${campaignTopic}" (${campaignDays} days).`,
                timestamp: new Date().toISOString(),
              },
            ],
            topic: campaignTopic,
            days: campaignDays,
          });
          setIsGeneratorExpanded(true);
          startPollingCampaignJob(data.job_id);
        }
        setCampaignTopic('');
      } else {
        notify(`Error: ${data.detail || 'Failed to trigger campaign'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRegeneratePost = async (postId: string) => {
    setRegeneratingPostId(postId);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/regenerate`, {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok) {
        notify('✅ Post regenerated successfully with AI!');
        fetchCampaignPosts();
        fetchData();
      } else {
        notify(`Regeneration failed: ${data.detail || 'Error regenerating post'}`);
        fetchCampaignPosts();
      }
    } catch (e: any) {
      notify(`Network error regenerating post: ${e.message}`);
    } finally {
      setRegeneratingPostId(null);
    }
  };

  const handleApprovePost = async (postId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/approve`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchCampaignPosts();
        fetchData();
        notify('✅ Post approved and scheduled!\n\nTo publish immediately to Instagram/Facebook, click the "Publish Now" button on the post card. Make sure your Meta API key is configured in Settings → Integrations.');
      }
    } catch (e) {
      console.error(e);
    }
  };

    const handlePublishNow = async (postId: string) => {
    const post = campaignPosts.find(p => p.id === postId);
    const platform = (post?.platform || '').toLowerCase();
    const needsMeta = platform === 'instagram' || platform === 'facebook';
    const needsLinkedIn = platform === 'linkedin';

    // Check if the required credential is configured
    if (needsMeta && !configuredProviders.includes('meta')) {
      setPendingPublishPostId(postId);
      setIsMetaModalOpen(true);
      return;
    }
    if (needsLinkedIn && !configuredProviders.includes('linkedin')) {
      notify('LinkedIn API key is not configured.\n\nGo to Settings → Integrations → Social Media and follow the steps to connect your LinkedIn account.');
      return;
    }

    setPublishingPostId(postId);
    setPublishNoteFor(postId);
    setPublishResult(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/publish-now`, {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok) {
        setPublishResult({ success: true, message: `✅ Published successfully to ${platform}!` });
        fetchCampaignPosts();
        fetchData();
      } else {
        setPublishResult({ success: false, message: `❌ Publish failed: ${data.detail || 'Unknown error. Check activity logs.'}` });
      }
    } catch (e) {
      setPublishResult({ success: false, message: '❌ Network error. Could not reach the server.' });
      console.error(e);
    } finally {
      setPublishingPostId(null);
    }
  };

    const handleSaveMetaTokenAndPublish = async () => {
    if (!metaTokenInput.trim()) return;
    setSavingMetaToken(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'meta', key: metaTokenInput.trim() })
      });
      if (res.ok) {
        setMetaTokenInput('');
        setIsMetaModalOpen(false);
        await fetchData(); // refresh configuredProviders
        // Now attempt publish with the newly saved key
        if (pendingPublishPostId) {
          const postId = pendingPublishPostId;
          setPendingPublishPostId(null);
          await handlePublishNow(postId);
        }
      } else {
        const data = await res.json();
        notify(`Failed to save Meta token: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error saving Meta token.');
    } finally {
      setSavingMetaToken(false);
    }
  };

    const handleRejectPost = async (postId: string) => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/reject`, {
        method: 'POST'
      });
      if (res.ok) {
        fetchCampaignPosts();
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

    const handleApproveAll = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/approve-all`, {
        method: 'POST'
      });
      if (res.ok) {
        notify("All pending campaign posts have been approved and scheduled!");
        fetchCampaignPosts();
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

    const handleBulkSchedule = async () => {
    if (!bulkStartDate || !bulkEndDate || !bulkPostingTime) {
      notify("Please fill in all bulk scheduling details.");
      return;
    }
    setBulkScheduling(true);
    try {
      const startDateTimeStr = `${bulkStartDate}T${bulkPostingTime}:00`;
      const endDateTimeStr = `${bulkEndDate}T${bulkPostingTime}:00`;

      const res = await fetchWithAuth(`${API_URL}/marketing/posts/bulk-schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: new Date(startDateTimeStr).toISOString(),
          end_date: new Date(endDateTimeStr).toISOString(),
          posting_time: bulkPostingTime
        })
      });
      const data = await res.json();
      if (res.ok) {
        setIsBulkScheduleOpen(false);
        fetchCampaignPosts();
        fetchData();
        notify(`✅ Campaign scheduled successfully!\n${data.message}`);
      } else {
        notify(`Error: ${data.detail || 'Failed to bulk schedule campaign'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error bulk scheduling campaign posts.");
    } finally {
      setBulkScheduling(false);
    }
  };

    const handleSavePostEdit = async (postId: string) => {
    try {
      const post = campaignPosts.find(p => p.id === postId);
      if (!post) return;
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: post.platform,
          content: editingContent,
          image_url: editingImageUrl || null,
          video_url: editingVideoUrl || null,
          scheduled_at: editingScheduledAt ? new Date(editingScheduledAt).toISOString() : null,
          image_prompt: editingImagePrompt || null,
          image_prompt_enabled: editingImagePromptEnabled,
          video_prompt: editingVideoPrompt || null,
          video_prompt_enabled: editingVideoPromptEnabled,
          remotion_prompt: editingRemotionPrompt || null,
          remotion_prompt_enabled: editingRemotionPromptEnabled,
          is_manual_media: editingIsManualMedia,
        })
      });
      if (res.ok) {
        setEditingPostId(null);
        fetchCampaignPosts();
        fetchData();
      } else {
        const data = await res.json();
        notify(`Error saving post: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error saving post edits.");
    }
  };

    const formatForDatetimeLocal = (dateStr: string | null) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return '';
      const pad = (n: number) => n.toString().padStart(2, '0');
      const yyyy = d.getFullYear();
      const mm = pad(d.getMonth() + 1);
      const dd = pad(d.getDate());
      const hh = pad(d.getHours());
      const min = pad(d.getMinutes());
      return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
    } catch (e) {
      return '';
    }
  };

    const startEditing = (post: any) => {
    setEditingPostId(post.id);
    setEditingContent(post.content);
    setEditingImageUrl(post.image_url || '');
    setEditingVideoUrl(post.video_url || '');
    setEditingImagePrompt(post.image_prompt || '');
    setEditingImagePromptEnabled(post.image_prompt_enabled || false);
    setEditingVideoPrompt(post.video_prompt || '');
    setEditingVideoPromptEnabled(post.video_prompt_enabled || false);
    setEditingRemotionPrompt(post.remotion_prompt || '');
    setEditingRemotionPromptEnabled(post.remotion_prompt_enabled || false);
    setEditingIsManualMedia(post.is_manual_media || false);
    setEditingScheduledAt(formatForDatetimeLocal(post.scheduled_at));
  };

    const handleFileUpload = async (file: File, isEditing: boolean) => {
    setUploadingFile(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetchWithAuth(`${API_URL}/marketing/upload-media`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok && data.url) {
        if (isEditing) {
          if (file.type.startsWith('video/')) {
            setEditingVideoUrl(data.url);
            setEditingImageUrl('');
          } else {
            setEditingImageUrl(data.url);
            setEditingVideoUrl('');
          }
          setEditingIsManualMedia(true);
        } else {
          if (file.type.startsWith('video/')) {
            setCreatePostVideoUrl(data.url);
            setCreatePostImageUrl('');
          } else {
            setCreatePostImageUrl(data.url);
            setCreatePostVideoUrl('');
          }
          setCreatePostIsManualMedia(true);
        }
      } else {
        notify(`Upload failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error uploading file.");
    } finally {
      setUploadingFile(false);
    }
  };

    const handleGenerateMedia = async (postId: string, mediaType: 'image' | 'video' | 'remotion', customPrompt: string) => {
    if (!customPrompt) {
      notify("Please enter a media prompt first.");
      return;
    }
    setGeneratingMedia(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/${postId}/generate-media`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          media_type: mediaType,
          prompt: customPrompt,
          provider: mediaType === 'video' ? videoProvider : imageProvider,
          model: mediaType === 'video' ? videoModel : imageModel
        })
      });
      const data = await res.json();
      if (res.ok) {
        if (mediaType === 'video') {
          setEditingVideoUrl(data.video_url || '');
          setEditingImageUrl('');
          setEditingVideoPrompt(data.video_prompt || '');
          setEditingVideoPromptEnabled(true);
        } else if (mediaType === 'remotion') {
          setEditingVideoUrl(data.video_url || '');
          setEditingImageUrl('');
          setEditingRemotionPrompt(data.remotion_prompt || customPrompt);
          setEditingRemotionPromptEnabled(true);
        } else {
          setEditingImageUrl(data.image_url || '');
          setEditingVideoUrl('');
          setEditingImagePrompt(data.image_prompt || '');
          setEditingImagePromptEnabled(true);
        }
        setEditingIsManualMedia(false);
        fetchCampaignPosts();
        notify("✅ Media successfully generated and updated via AI!");
      } else {
        const errData = await res.json().catch(() => ({}));
        notify(`Media generation failed: ${errData.detail || data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error generating media.");
    } finally {
      setGeneratingMedia(false);
    }
  };

    const handleSuggestPrompt = async (content: string, mediaType: 'image' | 'video', isEditing: boolean) => {
    if (!content) {
      notify("Please enter post content first so AI can suggest a matching prompt.");
      return;
    }
    setSuggestingPrompt(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/suggest-prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, media_type: mediaType })
      });
      const data = await res.json();
      if (res.ok && data.prompt) {
        if (isEditing) {
          if (mediaType === 'image') {
            setEditingImagePrompt(data.prompt);
            setEditingImagePromptEnabled(true);
          } else if (mediaType === 'video') {
            setEditingVideoPrompt(data.prompt);
            setEditingVideoPromptEnabled(true);
          } else {
            setEditingRemotionPrompt(data.prompt);
            setEditingRemotionPromptEnabled(true);
          }
        } else {
          if (mediaType === 'image') {
            setCreatePostImagePrompt(data.prompt);
            setCreatePostImagePromptEnabled(true);
          } else if (mediaType === 'video') {
            setCreatePostVideoPrompt(data.prompt);
            setCreatePostVideoPromptEnabled(true);
          } else {
            setCreatePostRemotionPrompt(data.prompt);
            setCreatePostRemotionPromptEnabled(true);
          }
        }
      } else {
        notify(`Failed to suggest prompt: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error suggesting prompt.");
    } finally {
      setSuggestingPrompt(false);
    }
  };

  const pendingCount = campaignPosts.filter((post) => post.approval_status === 'pending').length;
  const readyCount = campaignPosts.filter((post) => post.approval_status === 'approved' || post.approval_status === 'scheduled').length;
  const publishedCount = campaignPosts.filter((post) => post.approval_status === 'published').length;
  const rejectedCount = campaignPosts.filter((post) => post.approval_status === 'rejected').length;
  const failedCount = campaignPosts.filter((post) => post.approval_status === 'failed' || post.status === 'failed').length;

  const matchesPlatform = (post: any) => campaignFilterPlatform === 'all' || post.platform === campaignFilterPlatform;
  const matchesStatus = (post: any) => {
    if (campaignFilterStatus === 'all') return true;
    if (campaignFilterStatus === 'ready') return post.approval_status === 'approved' || post.approval_status === 'scheduled';
    if (campaignFilterStatus === 'failed') return post.approval_status === 'failed' || post.status === 'failed';
    return post.approval_status === campaignFilterStatus;
  };
  const matchesQuery = (post: any) => {
    const needle = postQuery.trim().toLowerCase();
    if (!needle) return true;
    return [post.content, post.platform, post.image_prompt, post.video_prompt, post.remotion_prompt, post.day, post.approval_status]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(needle);
  };
  const bySchedule = (a: any, b: any) => (Number(a.day) || 0) - (Number(b.day) || 0) || String(a.scheduled_at || '').localeCompare(String(b.scheduled_at || ''));

  const chooseStatus = (status: string) => {
    setCampaignFilterStatus(status);
    if (campaignViewMode === 'analytics') setCampaignViewMode('timeline');
  };

  const handleAddTag = (tagToAdd?: string) => {
    const raw = tagToAdd !== undefined ? tagToAdd : tagInput;
    const cleaned = raw.trim().replace(/^#/, '');
    if (!cleaned) return;
    if (!createPostTags.includes(cleaned)) {
      setCreatePostTags((prev) => [...prev, cleaned]);
    }
    setTagInput('');
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setCreatePostTags((prev) => prev.filter((t) => t !== tagToRemove));
  };

  const handleCreateManualPost = async () => {
    if (!createPostContent.trim()) {
      notify("Please enter post content.");
      return;
    }
    if (createPostPlatforms.length === 0) {
      notify("Please select at least one target network.");
      return;
    }
    setCreatingPost(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/posts/manual-multi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platforms: createPostPlatforms,
          content: createPostContent,
          tags: createPostTags,
          day: createPostDay,
          image_url: createPostImageUrl || null,
          video_url: createPostVideoUrl || null,
          image_prompt: createPostImagePrompt || null,
          image_prompt_enabled: createPostImagePromptEnabled,
          video_prompt: createPostVideoPrompt || null,
          video_prompt_enabled: createPostVideoPromptEnabled,
          remotion_prompt: createPostRemotionPrompt || null,
          remotion_prompt_enabled: createPostRemotionPromptEnabled,
          is_manual_media: true,
          publish_mode: createPostPublishMode,
          scheduled_at: createPostPublishMode === 'schedule' && createPostScheduledAt ? new Date(createPostScheduledAt).toISOString() : null,
        })
      });
      if (res.ok) {
        const data = await res.json();
        setIsCreatePostOpen(false);
        setCreatePostContent('');
        setCreatePostTags([]);
        setTagInput('');
        setCreatePostImageUrl('');
        setCreatePostVideoUrl('');
        setCreatePostImagePrompt('');
        setCreatePostImagePromptEnabled(false);
        setCreatePostVideoPrompt('');
        setCreatePostVideoPromptEnabled(false);
        setCreatePostRemotionPrompt('');
        setCreatePostRemotionPromptEnabled(false);
        setCreatePostScheduledAt('');
        setCreatePostPublishMode('schedule');
        fetchCampaignPosts();
        fetchData();

        const targets = createPostPlatforms.map(platformName).join(', ');
        if (createPostPublishMode === 'now') {
          notify(`🚀 Published ${data.length} post(s) immediately to ${targets}!`);
        } else if (createPostPublishMode === 'schedule') {
          notify(`📅 Scheduled ${data.length} automated post(s) for ${targets}!`);
        } else {
          notify(`📝 Saved ${data.length} draft post(s) for ${targets}!`);
        }
      } else {
        const data = await res.json();
        notify(`Error: ${data.detail || 'Failed to create post'}`);
      }
    } catch (e) {
      console.error(e);
      notify("Network error creating manual post.");
    } finally {
      setCreatingPost(false);
    }
  };

  const renderPostCard = (post: any) => {
    const isEditing = editingPostId === post.id;
    const hasVideo = !!post.video_url;
    const hasImage = !!post.image_url;
    const imageFailed = String(post.image_url || '').startsWith('error:');
    const copy = String(post.content || '');
    const expanded = !!expandedIds[post.id] || copy.length <= 280;
    const shownCopy = expanded ? copy : `${copy.slice(0, 280).trim()}…`;
    const promptMode = editingImagePromptEnabled ? 'image' : editingVideoPromptEnabled ? 'video' : editingRemotionPromptEnabled ? 'remotion' : 'none';

    return (
      <article key={post.id} className="flex flex-col rounded-lg border border-border bg-card">
        <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
          <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{platformName(post.platform)}</span>
            <span>Day {post.day || '—'}</span>
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${post.is_manual_media ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20' : 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20'}`}>
              {post.is_manual_media ? 'Manual' : 'AI Agent'}
            </span>
          </div>
          <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${
            (post.approval_status === 'failed' || post.status === 'failed')
              ? 'bg-destructive/15 text-destructive border border-destructive/30 font-semibold'
              : 'text-muted-foreground'
          }`}>
            {statusName(post.approval_status === 'failed' || post.status === 'failed' ? 'failed' : post.approval_status)}
          </span>
        </div>

        <div className="space-y-3 p-3">
          {isEditing ? (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <FieldLabel>Post text</FieldLabel>
                <Textarea value={editingContent} onChange={(event) => setEditingContent(event.target.value)} className="min-h-28" aria-label="Post text" />
              </div>
              <div className="space-y-1.5">
                <FieldLabel>Publish at</FieldLabel>
                <Input type="datetime-local" value={editingScheduledAt} onChange={(event) => setEditingScheduledAt(event.target.value)} aria-label="Publish at" />
              </div>
              <div className="space-y-2 rounded-lg border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">Media</p>
                  <span className="text-xs text-muted-foreground">{editingIsManualMedia ? 'Uploaded file' : 'Generated or linked'}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <input type="file" accept="image/*" className="sr-only" id={`edit-image-upload-${post.id}`} onChange={(event) => { const file = event.target.files?.[0]; if (file) handleFileUpload(file, true); }} />
                    <Button type="button" variant="outline" className="w-full" disabled={uploadingFile} onClick={() => document.getElementById(`edit-image-upload-${post.id}`)?.click()}>
                      <ImageIcon /> {uploadingFile ? 'Uploading' : 'Upload image'}
                    </Button>
                  </div>
                  <div>
                    <input type="file" accept="video/*" className="sr-only" id={`edit-video-upload-${post.id}`} onChange={(event) => { const file = event.target.files?.[0]; if (file) handleFileUpload(file, true); }} />
                    <Button type="button" variant="outline" className="w-full" disabled={uploadingFile} onClick={() => document.getElementById(`edit-video-upload-${post.id}`)?.click()}>
                      <Film /> {uploadingFile ? 'Uploading' : 'Upload video'}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="space-y-1.5">
                    <FieldLabel>Image URL</FieldLabel>
                    <Input value={editingImageUrl} placeholder="https://" aria-label="Image URL" onChange={(event) => { setEditingImageUrl(event.target.value); if (event.target.value) { setEditingVideoUrl(''); setEditingIsManualMedia(false); } }} />
                  </div>
                  <div className="space-y-1.5">
                    <FieldLabel>Video URL</FieldLabel>
                    <Input value={editingVideoUrl} placeholder="https://" aria-label="Video URL" onChange={(event) => { setEditingVideoUrl(event.target.value); if (event.target.value) { setEditingImageUrl(''); setEditingIsManualMedia(false); } }} />
                  </div>
                </div>
              </div>
              <div className="space-y-2 rounded-lg border border-border p-3">
                <FieldLabel>Generation prompt</FieldLabel>
                <Select value={promptMode} onValueChange={(value) => {
                  setEditingImagePromptEnabled(value === 'image');
                  setEditingVideoPromptEnabled(value === 'video');
                  setEditingRemotionPromptEnabled(value === 'remotion');
                }}>
                  <SelectTrigger className="w-full" aria-label="Generation prompt type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No prompt</SelectItem>
                    <SelectItem value="image">Image</SelectItem>
                    {ENABLE_IN_APP_VIDEO && <SelectItem value="video">Video</SelectItem>}
                    {ENABLE_IN_APP_VIDEO && <SelectItem value="remotion">Remotion</SelectItem>}
                  </SelectContent>
                </Select>
                {editingImagePromptEnabled && (
                  <div className="space-y-2">
                    <Textarea value={editingImagePrompt} onChange={(event) => setEditingImagePrompt(event.target.value)} placeholder="Describe the image" className="min-h-16" aria-label="Image prompt" />
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Button type="button" size="sm" variant="outline" className="flex-1" disabled={suggestingPrompt} onClick={() => handleSuggestPrompt(editingContent || post.content, 'image', true)}>
                        {suggestingPrompt ? 'Suggesting' : 'Suggest prompt'}
                      </Button>
                      <Button type="button" size="sm" className="flex-1" disabled={generatingMedia || !editingImagePrompt} onClick={() => handleGenerateMedia(post.id, 'image', editingImagePrompt)}>
                        {generatingMedia ? 'Generating' : 'Generate image'}
                      </Button>
                    </div>
                  </div>
                )}
                {ENABLE_IN_APP_VIDEO && editingVideoPromptEnabled && (
                  <div className="space-y-2">
                    <Textarea value={editingVideoPrompt} onChange={(event) => setEditingVideoPrompt(event.target.value)} placeholder="Describe the video" className="min-h-16" aria-label="Video prompt" />
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Button type="button" size="sm" variant="outline" className="flex-1" disabled={suggestingPrompt} onClick={() => handleSuggestPrompt(editingContent || post.content, 'video', true)}>
                        {suggestingPrompt ? 'Suggesting' : 'Suggest prompt'}
                      </Button>
                      <Button type="button" size="sm" className="flex-1" disabled={generatingMedia || !editingVideoPrompt} onClick={() => handleGenerateMedia(post.id, 'video', editingVideoPrompt)}>
                        {generatingMedia ? 'Generating' : 'Generate video'}
                      </Button>
                    </div>
                  </div>
                )}
                {ENABLE_IN_APP_VIDEO && editingRemotionPromptEnabled && (
                  <div className="space-y-2">
                    <Textarea value={editingRemotionPrompt} onChange={(event) => setEditingRemotionPrompt(event.target.value)} placeholder="Describe the Remotion clip" className="min-h-16" aria-label="Remotion prompt" />
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Button type="button" size="sm" variant="outline" className="flex-1" disabled={suggestingPrompt} onClick={() => handleSuggestPrompt(editingContent || post.content, 'video', true)}>
                        {suggestingPrompt ? 'Suggesting' : 'Suggest prompt'}
                      </Button>
                      <Button type="button" size="sm" className="flex-1" disabled={generatingMedia || !editingRemotionPrompt} onClick={() => handleGenerateMedia(post.id, 'remotion', editingRemotionPrompt)}>
                        {generatingMedia ? 'Generating' : 'Generate Remotion'}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <>
              {(post.approval_status === 'failed' || post.status === 'failed') && (
                <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm">
                  <div className="flex items-start gap-2.5">
                    <AlertCircle className="size-4 shrink-0 mt-0.5 text-destructive" />
                    <div className="space-y-1">
                      <p className="font-semibold text-destructive">AI Generation Failed</p>
                      <p className="text-xs text-foreground/80 whitespace-pre-wrap leading-relaxed">
                        {post.fallback_reason || 'An error occurred during AI generation. Please check API keys and provider balance.'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {shownCopy ? (
                <p className="whitespace-pre-wrap text-sm leading-6 text-foreground">{shownCopy}</p>
              ) : !(post.approval_status === 'failed' || post.status === 'failed') ? (
                <p className="whitespace-pre-wrap text-sm leading-6 text-muted-foreground italic">No post text generated yet.</p>
              ) : null}
              {copy.length > 280 && (
                <button type="button" className="text-xs text-primary" onClick={() => setExpandedIds((prev) => ({ ...prev, [post.id]: !prev[post.id] }))}>
                  {expandedIds[post.id] ? 'Show less' : 'Show full text'}
                </button>
              )}
              {post.learning_tags && Array.isArray(post.learning_tags) && post.learning_tags.length > 0 && (
                <div className="flex flex-wrap gap-1 pt-0.5">
                  {post.learning_tags.map((tag: string) => (
                    <span key={tag} className="inline-flex items-center rounded bg-muted/60 px-1.5 py-0.5 text-[10px] text-muted-foreground border border-border">
                      #{tag.replace(/^#/, '')}
                    </span>
                  ))}
                </div>
              )}
              {hasVideo && (
                <div className="overflow-hidden rounded-lg border border-border">
                  <video src={post.video_url} controls loop muted className="aspect-video w-full bg-muted object-cover" />
                  <p className="px-2 py-1 text-xs text-muted-foreground">{post.is_manual_media ? 'Uploaded video' : 'Generated video'}</p>
                </div>
              )}
              {!hasVideo && hasImage && imageFailed && (
                <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-foreground">
                  Image generation failed. {String(post.image_url).replace(/^error:/, '')}
                </p>
              )}
              {!hasVideo && hasImage && !imageFailed && (
                <div className="space-y-2">
                  <div className="overflow-hidden rounded-lg border border-border">
                    <img src={post.image_url} alt="" className="aspect-video w-full object-cover" />
                    <p className="px-2 py-1 text-xs text-muted-foreground">{post.is_manual_media ? 'Uploaded image' : 'Generated image'}</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" disabled={!!animatingPostJobs[post.id] && animatingPostJobs[post.id].status !== 'failed'} onClick={() => handleAnimatePostToVideo(post.id)}>
                    {animatingPostJobs[post.id] && animatingPostJobs[post.id].status !== 'failed' ? <Loader2 className="animate-spin" /> : <Film />}
                    {animatingPostJobs[post.id] && animatingPostJobs[post.id].status !== 'failed'
                      ? `Animating ${animatingPostJobs[post.id].progress}%`
                      : 'Animate this still'}
                  </Button>
                  {animatingPostJobs[post.id]?.error && <p className="text-xs text-destructive">{animatingPostJobs[post.id].error}</p>}
                </div>
              )}
              {post.used_model && (
                <p className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                  <span className="inline-flex min-w-0 items-center gap-1"><Cpu className="size-3 shrink-0" /><span className="truncate font-mono">{post.used_model}</span></span>
                  {typeof post.cost_usd === 'number' && post.cost_usd > 0 && <span>${post.cost_usd.toFixed(4)}</span>}
                </p>
              )}
              {post.fallback_reason && <p className="text-xs text-muted-foreground">{post.fallback_reason}</p>}
              {post.image_prompt_enabled && post.image_prompt && <p className="text-xs text-muted-foreground">Image prompt: {post.image_prompt}</p>}
              {post.video_prompt_enabled && post.video_prompt && <p className="text-xs text-muted-foreground">Video prompt: {post.video_prompt}</p>}
              {post.remotion_prompt_enabled && post.remotion_prompt && <p className="text-xs text-muted-foreground">Remotion prompt: {post.remotion_prompt}</p>}
              {post.scheduled_at && <p className="text-xs text-muted-foreground">Scheduled {new Date(post.scheduled_at).toLocaleString()}</p>}
            </>
          )}
        </div>

        <div className="mt-auto flex flex-wrap items-center justify-end gap-2 border-t border-border px-3 py-2">
          {isEditing ? (
            <>
              <Button size="sm" variant="outline" onClick={() => setEditingPostId(null)}>Cancel</Button>
              <Button size="sm" onClick={() => handleSavePostEdit(post.id)}>Save</Button>
            </>
          ) : (
            <>
              {(post.approval_status === 'failed' || post.status === 'failed') && (
                <Button
                  size="sm"
                  className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
                  disabled={regeneratingPostId === post.id}
                  onClick={() => handleRegeneratePost(post.id)}
                >
                  {regeneratingPostId === post.id ? <Loader2 className="size-3.5 animate-spin" /> : <Repeat className="size-3.5" />}
                  {regeneratingPostId === post.id ? 'Regenerating...' : 'Retry with AI'}
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => startEditing(post)}><Edit2 /> Edit</Button>
              {(post.approval_status === 'pending' || post.approval_status === 'approved' || post.approval_status === 'scheduled' || post.approval_status === 'failed' || post.status === 'failed') && (
                <Button size="sm" variant="destructive" onClick={() => handleRejectPost(post.id)}>Delete</Button>
              )}
              {post.approval_status === 'pending' && (
                <Button size="sm" onClick={() => handleApprovePost(post.id)}>Approve</Button>
              )}
              {(post.approval_status === 'approved' || post.approval_status === 'scheduled') && ['instagram', 'facebook', 'linkedin'].includes(post.platform) && (
                <Button size="sm" onClick={() => handlePublishNow(post.id)} disabled={publishingPostId === post.id}>
                  {publishingPostId === post.id ? <Loader2 className="animate-spin" /> : <Send />}
                  {publishingPostId === post.id ? 'Publishing' : 'Publish now'}
                </Button>
              )}
              {publishResult && publishNoteFor === post.id && publishingPostId === null && (
                <span className={`text-xs ${publishResult.success ? 'text-foreground' : 'text-destructive'}`}>{publishResult.message}</span>
              )}
            </>
          )}
        </div>
      </article>
    );
  };

  const timelinePosts = campaignPosts.filter((post) => matchesPlatform(post) && matchesStatus(post) && matchesQuery(post)).sort(bySchedule);
  const dayGroups = new Map<string, any[]>();
  for (const post of timelinePosts) {
    const label = post.day ? `Day ${post.day}` : 'No day set';
    const rows = dayGroups.get(label) || [];
    rows.push(post);
    dayGroups.set(label, rows);
  }
  const statusFilters = [
    { id: 'all', label: 'All', value: campaignPosts.length },
    { id: 'pending', label: 'Needs review', value: pendingCount },
    { id: 'ready', label: 'Scheduled', value: readyCount },
    { id: 'published', label: 'Published', value: publishedCount },
    ...(failedCount > 0 ? [{ id: 'failed', label: 'Failed', value: failedCount }] : []),
    ...(rejectedCount > 0 ? [{ id: 'rejected', label: 'Rejected', value: rejectedCount }] : []),
  ];
  const formats = [
    { id: 'social_posts', label: 'Social posts', detail: 'Short copy for the selected networks' },
    { id: 'blog_articles', label: 'Articles', detail: 'Longer posts for the same schedule' },
    { id: 'video_first', label: 'Video first', detail: 'Scripts and motion ahead of stills' },
    { id: 'omnichannel_mix', label: 'Mix', detail: 'A mix of the formats above' },
  ];

  const openBulkSchedule = () => {
    const start = new Date();
    const end = new Date();
    end.setDate(end.getDate() + 30);
    setBulkStartDate(start.toISOString().split('T')[0]);
    setBulkEndDate(end.toISOString().split('T')[0]);
    setIsBulkScheduleOpen(true);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        title="Campaigns"
        description="Review drafts, set when they go out, and publish to LinkedIn, Instagram, or Facebook."
        actions={
          <>
            <Button variant="outline" onClick={() => setIsGeneratorExpanded((open) => !open)}>
              {activeCampaignJob && (activeCampaignJob.status === 'queued' || activeCampaignJob.status === 'in_progress') ? (
                <span className="flex items-center gap-1.5 font-medium text-blue-600 dark:text-blue-400">
                  <Loader2 className="size-3.5 animate-spin" />
                  Generating ({Math.round(activeCampaignJob.progressPct)}%)
                </span>
              ) : isGeneratorExpanded ? 'Hide planner' : 'New campaign'}
            </Button>
            <Button
              onClick={() => {
                if (!createPostScheduledAt) {
                  const tomorrow = new Date();
                  tomorrow.setDate(tomorrow.getDate() + 1);
                  tomorrow.setHours(9, 0, 0, 0);
                  const pad = (n: number) => n.toString().padStart(2, '0');
                  setCreatePostScheduledAt(`${tomorrow.getFullYear()}-${pad(tomorrow.getMonth() + 1)}-${pad(tomorrow.getDate())}T09:00`);
                }
                setIsCreatePostOpen(true);
              }}
              className="gap-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium shadow-sm"
            >
              <Sparkles className="size-4" /> Compose & Automate
            </Button>
            {campaignPosts.length > 0 && (
              <Button variant="outline" onClick={openBulkSchedule}>
                <CalendarRange /> Schedule range
              </Button>
            )}
            {pendingCount > 0 && (
              <Button onClick={handleApproveAll}>Approve {pendingCount} {pendingCount === 1 ? 'draft' : 'drafts'}</Button>
            )}
          </>
        }
      />

      <AutonomousMarketingRadar
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        onPulseSuccess={() => {
          fetchCampaignPosts();
          fetchData();
        }}
      />

      {activeCampaignJob && (activeCampaignJob.status === 'queued' || activeCampaignJob.status === 'in_progress') && !isGeneratorExpanded && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-blue-500/30 bg-blue-500/10 p-3.5 text-xs shadow-sm">
          <div className="flex items-center gap-2.5">
            <Loader2 className="size-4 animate-spin text-blue-500" />
            <span className="font-medium text-foreground">
              Generating Campaign: <span className="font-semibold">{activeCampaignJob.topic ? `"${activeCampaignJob.topic}"` : 'Active Campaign'}</span>
            </span>
            <span className="text-muted-foreground hidden sm:inline">
              · Stage: <strong className="text-foreground">{activeCampaignJob.currentStage}</strong> ({Math.round(activeCampaignJob.progressPct)}%)
            </span>
          </div>
          <Button size="sm" variant="outline" onClick={() => setIsGeneratorExpanded(true)}>
            View Stages & Logs
          </Button>
        </div>
      )}

      {campaignPosts.length > 0 && (
        <div className={`grid grid-cols-2 gap-3 ${statusFilters.length > 4 ? 'lg:grid-cols-5' : 'lg:grid-cols-4'}`}>
          {statusFilters.map((filter) => (
            <button
              key={filter.id}
              type="button"
              onClick={() => chooseStatus(filter.id)}
              className={`rounded-lg border px-3 py-3 text-left ${campaignFilterStatus === filter.id && campaignViewMode !== 'analytics' ? 'border-primary bg-primary/10' : 'border-border bg-card hover:bg-muted/40'}`}
            >
              <p className="text-lg font-semibold leading-none">{filter.value}</p>
              <p className="mt-1 text-xs text-muted-foreground">{filter.label}</p>
            </button>
          ))}
        </div>
      )}

      {isGeneratorExpanded && activeCampaignJob ? (
        <section className="space-y-4 rounded-xl border border-border/80 bg-card p-5 shadow-sm">
          {/* Header */}
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border/60 pb-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                {activeCampaignJob.status === 'in_progress' && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-medium text-blue-600 dark:text-blue-400 border border-blue-500/20">
                    <Loader2 className="size-3 animate-spin" />
                    Generating Campaign Stages
                  </span>
                )}
                {activeCampaignJob.status === 'queued' && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400 border border-amber-500/20">
                    <Clock className="size-3 animate-pulse" />
                    Queued in AI Pipeline
                  </span>
                )}
                {activeCampaignJob.status === 'completed' && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="size-3" />
                    Campaign Generated Successfully
                  </span>
                )}
                {activeCampaignJob.status === 'failed' && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-500/10 px-2.5 py-0.5 text-xs font-medium text-rose-600 dark:text-rose-400 border border-rose-500/20">
                    <AlertCircle className="size-3" />
                    Generation Halted
                  </span>
                )}
                <span className="text-xs text-muted-foreground font-mono">
                  {Math.round(activeCampaignJob.progressPct)}% Complete
                </span>
              </div>
              <h2 className="text-base font-semibold tracking-tight text-foreground">
                {activeCampaignJob.topic ? `"${activeCampaignJob.topic}"` : 'Multi-Day Campaign Pipeline'}
              </h2>
              <p className="text-xs text-muted-foreground">
                {activeCampaignJob.days ? `${activeCampaignJob.days} Days Timeline` : 'Full Timeline'} · Stage: <strong className="text-foreground">{activeCampaignJob.currentStage || 'Processing'}</strong>
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowConfigWhileGenerating((v) => !v)}
              >
                {showConfigWhileGenerating ? 'Hide Configuration' : 'View Configuration'}
              </Button>
              {activeCampaignJob.status === 'completed' && (
                <Button
                  size="sm"
                  onClick={() => {
                    setActiveCampaignJob(null);
                    setIsGeneratorExpanded(false);
                    fetchCampaignPosts();
                  }}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                >
                  <Eye className="size-3.5" /> View Campaign Drafts
                </Button>
              )}
              {(activeCampaignJob.status === 'completed' || activeCampaignJob.status === 'failed') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setActiveCampaignJob(null)}
                >
                  Plan Another Campaign
                </Button>
              )}
              {campaignPosts.length > 0 && (
                <Button variant="ghost" size="sm" onClick={() => setIsGeneratorExpanded(false)}>
                  Close
                </Button>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-muted-foreground flex items-center gap-1.5">
                <Sparkles className="size-3 text-primary animate-pulse" />
                Current Stage: <span className="text-foreground font-semibold">{activeCampaignJob.currentStage || 'Processing'}</span>
              </span>
              <span className="font-mono font-semibold text-primary">
                {Math.round(activeCampaignJob.progressPct)}%
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted/60">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600 transition-all duration-500 ease-out"
                style={{ width: `${Math.min(100, Math.max(5, activeCampaignJob.progressPct))}%` }}
              />
            </div>
          </div>

          {/* Two-Column Layout: Stages Stepper + Live Milestone Logs Feed */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Left: Stages Stepper (5 cols) */}
            <div className="lg:col-span-5 space-y-2 rounded-lg border border-border/60 bg-muted/20 p-3.5">
              <div className="flex items-center justify-between border-b border-border/40 pb-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Pipeline Stages
                </h3>
                <span className="text-[11px] text-muted-foreground font-mono">
                  {activeCampaignJob.stages.filter(s => s.status === 'completed').length} / {activeCampaignJob.stages.length} Completed
                </span>
              </div>
              <div className="space-y-2 pt-1">
                {activeCampaignJob.stages.map((stage, idx) => {
                  const isCurrent = stage.status === 'in_progress' || (stage.id === activeCampaignJob.currentStage && stage.status !== 'completed');
                  const isDone = stage.status === 'completed';
                  const isFailed = stage.status === 'failed';

                  return (
                    <div
                      key={stage.id}
                      className={`flex items-start gap-2.5 rounded-md p-2 transition-colors ${
                        isCurrent
                          ? 'border border-blue-500/30 bg-blue-500/5 text-foreground'
                          : isDone
                          ? 'text-muted-foreground hover:bg-muted/30'
                          : 'opacity-70 text-muted-foreground'
                      }`}
                    >
                      <div className="mt-0.5 shrink-0">
                        {isDone ? (
                          <div className="flex size-5 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
                            <CheckCircle2 className="size-3.5" />
                          </div>
                        ) : isCurrent ? (
                          <div className="flex size-5 items-center justify-center rounded-full bg-blue-500/20 text-blue-500">
                            <Loader2 className="size-3.5 animate-spin" />
                          </div>
                        ) : isFailed ? (
                          <div className="flex size-5 items-center justify-center rounded-full bg-rose-500/10 text-rose-500">
                            <AlertCircle className="size-3.5" />
                          </div>
                        ) : (
                          <div className="flex size-5 items-center justify-center rounded-full border border-border text-[10px] font-mono font-medium text-muted-foreground">
                            {idx + 1}
                          </div>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-1">
                          <p className={`text-xs font-medium leading-tight ${isCurrent ? 'text-primary font-semibold' : isDone ? 'text-foreground' : ''}`}>
                            {stage.name}
                          </p>
                          {isCurrent && (
                            <span className="shrink-0 rounded bg-blue-500/10 px-1.5 py-0.2 text-[10px] font-medium text-blue-500">
                              Active
                            </span>
                          )}
                          {isDone && (
                            <span className="shrink-0 text-[10px] text-emerald-500 font-medium">
                              Done
                            </span>
                          )}
                        </div>
                        {stage.desc && (
                          <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground line-clamp-1">
                            {stage.desc}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right: Stage Milestone Activity Log Feed (7 cols) */}
            <div className="lg:col-span-7 flex flex-col rounded-lg border border-border/60 bg-slate-950 p-3.5 text-slate-200">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="relative flex size-2">
                    {activeCampaignJob.status === 'in_progress' && (
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    )}
                    <span className={`relative inline-flex size-2 rounded-full ${activeCampaignJob.status === 'in_progress' ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                  </span>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Stage Milestone Feed
                  </h3>
                </div>
                <span className="text-[11px] text-slate-400 font-mono">
                  {activeCampaignJob.logs?.length || 0} Events
                </span>
              </div>

              {/* Feed Content */}
              <div className="flex-1 min-h-60 max-h-80 overflow-y-auto space-y-2 pr-1 font-mono text-xs">
                {(!activeCampaignJob.logs || activeCampaignJob.logs.length === 0) ? (
                  <div className="flex h-40 flex-col items-center justify-center text-center text-slate-500">
                    <Loader2 className="size-5 animate-spin mb-2 opacity-50" />
                    <p className="text-xs">Connecting to Campaign OS multi-agent orchestrator...</p>
                    <p className="text-[11px] text-slate-600 mt-1">Stage milestones will stream here automatically.</p>
                  </div>
                ) : (
                  activeCampaignJob.logs.map((log, index) => {
                    const timeStr = log.timestamp
                      ? new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                      : '--:--:--';

                    return (
                      <div
                        key={index}
                        className="group flex items-start gap-2 rounded border border-slate-800/60 bg-slate-900/60 p-2 hover:bg-slate-900 transition-colors"
                      >
                        <span className="shrink-0 text-[10px] text-slate-500 font-mono mt-0.5">
                          {timeStr}
                        </span>
                        <div className="min-w-0 flex-1">
                          <span className="inline-block mr-1.5 rounded bg-blue-950/80 border border-blue-800/50 px-1.5 py-0.2 text-[10px] font-semibold text-blue-300">
                            {log.stage}
                          </span>
                          <span className="text-xs text-slate-200 break-words leading-relaxed">
                            {log.message}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Configuration drawer if toggled */}
          {showConfigWhileGenerating && (
            <div className="mt-4 rounded-lg border border-border bg-muted/30 p-4 text-xs text-muted-foreground">
              <p className="font-semibold text-foreground mb-2">Campaign Parameters Submitted</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div><span className="font-medium text-foreground">Topic:</span> {activeCampaignJob.topic}</div>
                <div><span className="font-medium text-foreground">Duration:</span> {activeCampaignJob.days} days</div>
                <div><span className="font-medium text-foreground">Networks:</span> {campaignPlatforms.map(platformName).join(', ')}</div>
                <div><span className="font-medium text-foreground">Format:</span> {contentFormat}</div>
              </div>
            </div>
          )}
        </section>
      ) : isGeneratorExpanded ? (
        <section className="space-y-4 rounded-lg border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Plan a campaign</h2>
              <p className="mt-1 text-sm text-muted-foreground">One topic becomes a timeline of posts. Generation continues in the background after you launch.</p>
            </div>
            {campaignPosts.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setIsGeneratorExpanded(false)}>Close</Button>
            )}
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <div className="space-y-1.5">
                <FieldLabel>Topic</FieldLabel>
                <Textarea
                  value={campaignTopic}
                  onChange={(event) => setCampaignTopic(event.target.value)}
                  placeholder="What should this campaign say, and for which brand or offer?"
                  className="min-h-28"
                  aria-label="Campaign topic"
                />
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <FieldLabel>Days & Cadence</FieldLabel>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setCampaignDays(30)}
                        className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${campaignDays === 30 ? 'bg-primary text-primary-foreground border-primary font-medium' : 'border-border text-muted-foreground hover:bg-muted'}`}
                      >
                        30 Days (Daily)
                      </button>
                      <button
                        type="button"
                        onClick={() => setCampaignDays(14)}
                        className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${campaignDays === 14 ? 'bg-primary text-primary-foreground border-primary font-medium' : 'border-border text-muted-foreground hover:bg-muted'}`}
                      >
                        14 Days
                      </button>
                      <button
                        type="button"
                        onClick={() => setCampaignDays(7)}
                        className={`text-[10px] px-2 py-0.5 rounded border transition-colors ${campaignDays === 7 ? 'bg-primary text-primary-foreground border-primary font-medium' : 'border-border text-muted-foreground hover:bg-muted'}`}
                      >
                        7 Days (Weekly)
                      </button>
                    </div>
                  </div>
                  <Input type="number" min={1} max={30} value={campaignDays} onChange={(event) => setCampaignDays(parseInt(event.target.value, 10) || 0)} aria-label="Campaign days" />
                  <p className="text-xs text-muted-foreground">Select up to 30 days of continuous narrative campaign content.</p>
                </div>
                <div className="space-y-1.5">
                  <FieldLabel>Networks</FieldLabel>
                  <div className="flex flex-wrap gap-1">
                    {['linkedin', 'instagram', 'facebook'].map((platform) => {
                      const selected = campaignPlatforms.includes(platform);
                      return (
                        <button
                          key={platform}
                          type="button"
                          onClick={() => setCampaignPlatforms(selected ? campaignPlatforms.filter((item) => item !== platform) : [...campaignPlatforms, platform])}
                          className={`rounded-md border px-2.5 py-1 text-xs ${selected ? 'border-primary bg-primary/10 text-foreground' : 'border-border text-muted-foreground'}`}
                        >
                          {platformName(platform)}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
              <div className="space-y-1.5 rounded-lg border border-border/70 bg-muted/20 p-2.5">
                <div className="flex items-center justify-between">
                  <FieldLabel>Daily Cadence & Time Slots (15-Agent Council)</FieldLabel>
                  <span className="text-[11px] font-mono text-muted-foreground">{postsPerDay} slot{postsPerDay > 1 ? 's' : ''}/day ({campaignDays * postsPerDay} posts total)</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setPostsPerDay(1)}
                    className={`rounded-lg border px-2.5 py-1.5 text-left transition-colors ${postsPerDay === 1 ? 'border-primary bg-primary/10 text-foreground font-medium' : 'border-border text-muted-foreground hover:bg-muted/40'}`}
                  >
                    <span className="block text-xs font-medium">1 Post / Day</span>
                    <span className="block text-[10px] text-muted-foreground">Peak window (09:00 UTC)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPostsPerDay(2)}
                    className={`rounded-lg border px-2.5 py-1.5 text-left transition-colors ${postsPerDay === 2 ? 'border-primary bg-primary/10 text-foreground font-medium' : 'border-border text-muted-foreground hover:bg-muted/40'}`}
                  >
                    <span className="block text-xs font-medium">2 Posts / Day</span>
                    <span className="block text-[10px] text-muted-foreground">Morning (09:00) + Evening (17:00)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPostsPerDay(3)}
                    className={`rounded-lg border px-2.5 py-1.5 text-left transition-colors ${postsPerDay === 3 ? 'border-primary bg-primary/10 text-foreground font-medium' : 'border-border text-muted-foreground hover:bg-muted/40'}`}
                  >
                    <span className="block text-xs font-medium">3 Posts / Day</span>
                    <span className="block text-[10px] text-muted-foreground">Morning + Midday + Evening</span>
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {formats.map((format) => (
                  <button
                    key={format.id}
                    type="button"
                    onClick={() => setContentFormat(format.id)}
                    className={`rounded-lg border px-3 py-2 text-left ${contentFormat === format.id ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted/40'}`}
                  >
                    <span className="block text-sm font-medium">{format.label}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">{format.detail}</span>
                  </button>
                ))}
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <FieldLabel>Style reference</FieldLabel>
                  {referenceImageUrl && <button type="button" className="text-xs text-muted-foreground" onClick={() => setReferenceImageUrl('')}>Clear</button>}
                </div>
                <Input type="url" value={referenceImageUrl} onChange={(event) => setReferenceImageUrl(event.target.value)} placeholder="Optional image URL for a consistent look" aria-label="Style reference URL" />
                {referenceImageUrl && <img src={referenceImageUrl} alt="" className="h-16 w-24 rounded-md border border-border object-cover" onError={(event) => { (event.target as HTMLImageElement).style.display = 'none'; }} />}
              </div>
            </div>

            <div className="space-y-3">
              <div className="space-y-3 rounded-lg border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="inline-flex items-center gap-1.5 text-sm font-medium"><FileText className="size-4 text-muted-foreground" /> Copy model</p>
                  {modelsLoading && <span className="text-xs text-muted-foreground">Loading models</span>}
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <FieldLabel>Provider</FieldLabel>
                    <Select value={textProvider} onValueChange={(value) => {
                      if (!value) return;
                      setTextProvider(value);
                      if (value === 'openrouter') setTextModel('meta-llama/llama-3.3-70b-instruct');
                      else if (value === 'together') setTextModel('meta-llama/Llama-3.3-70B-Instruct-Turbo');
                      else if (value === 'groq') setTextModel('llama-3.3-70b-versatile');
                      else if (value === 'gemini') setTextModel('gemini-2.5-flash');
                      else if (value === 'openai') setTextModel('gpt-4o');
                      else if (value === 'anthropic') setTextModel('claude-sonnet-4-6');
                      else if (value === 'nvidia') setTextModel('meta/llama-3.3-70b-instruct');
                      else if (value === 'grok') setTextModel('grok-2');
                      else if (value === 'auto') setTextModel('');
                    }}>
                      <SelectTrigger className="w-full" aria-label="Copy provider"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">Auto / Default (.env)</SelectItem>
                        <SelectItem value="nvidia">NVIDIA NIM</SelectItem>
                        <SelectItem value="openrouter">OpenRouter</SelectItem>
                        <SelectItem value="together">Together</SelectItem>
                        <SelectItem value="groq">Groq</SelectItem>
                        <SelectItem value="gemini">Gemini</SelectItem>
                        <SelectItem value="openai">OpenAI</SelectItem>
                        <SelectItem value="anthropic">Anthropic</SelectItem>
                        <SelectItem value="grok">Grok</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {textProvider !== 'auto' && (
                    <div className="space-y-1.5">
                      <FieldLabel>Model</FieldLabel>
                      <Input value={textModel} onChange={(event) => setTextModel(event.target.value)} className="font-mono" aria-label="Copy model" />
                    </div>
                  )}
                </div>
                {textProvider !== 'auto' && (
                  <ModelPicks
                    models={curatedModels.filter((model) => model.modality === 'text' && (model.provider === textProvider || textProvider === 'openrouter' && model.provider === 'openrouter'))}
                    active={textModel}
                    onPick={setTextModel}
                  />
                )}
                <ValidationNote result={textValidation} onUse={setTextModel} />
              </div>

              <div className="space-y-3 rounded-lg border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="inline-flex items-center gap-1.5 text-sm font-medium"><ImageIcon className="size-4 text-muted-foreground" /> Images</p>
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input type="checkbox" checked={generateImages} onChange={(event) => setGenerateImages(event.target.checked)} />
                    Generate
                  </label>
                </div>
                {generateImages && (
                  <>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <FieldLabel>Provider</FieldLabel>
                        <Select value={imageProvider} onValueChange={(value) => {
                          if (!value) return;
                          setImageProvider(value);
                          if (value === 'together') setImageModel('black-forest-labs/FLUX.1-schnell');
                          else if (value === 'openrouter') setImageModel('black-forest-labs/flux-1-schnell');
                          else if (value === 'openai') setImageModel('dall-e-3');
                          else if (value === 'gemini') setImageModel('imagen-3.0-generate-002');
                        }}>
                          <SelectTrigger className="w-full" aria-label="Image provider"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="together">Together</SelectItem>
                            <SelectItem value="openrouter">OpenRouter</SelectItem>
                            <SelectItem value="openai">OpenAI</SelectItem>
                            <SelectItem value="gemini">Gemini</SelectItem>
                            <SelectItem value="stability">Stability</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <FieldLabel>Model</FieldLabel>
                        <Input value={imageModel} onChange={(event) => setImageModel(event.target.value)} className="font-mono" aria-label="Image model" />
                      </div>
                    </div>
                    <ModelPicks
                      models={curatedModels.filter((model) => model.modality === 'image' && (model.provider === imageProvider || imageProvider === 'together' && model.provider === 'together'))}
                      active={imageModel}
                      onPick={setImageModel}
                    />
                    <ValidationNote result={imageValidation} />
                  </>
                )}
              </div>

              {ENABLE_IN_APP_VIDEO && (
                <div className="space-y-3 rounded-lg border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="inline-flex items-center gap-1.5 text-sm font-medium"><Film className="size-4 text-muted-foreground" /> Video</p>
                    <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={generateVideos} onChange={(event) => setGenerateVideos(event.target.checked)} />
                        Generate loops
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={generateRemotion} onChange={(event) => setGenerateRemotion(event.target.checked)} />
                        Remotion clips
                      </label>
                    </div>
                  </div>
                  {generateVideos && (
                    <>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div className="space-y-1.5">
                          <FieldLabel>Provider</FieldLabel>
                          <Select value={videoProvider} onValueChange={(value) => {
                            if (!value) return;
                            setVideoProvider(value);
                            if (value === 'together') setVideoModel('minimax/video-01');
                            else if (value === 'openrouter') setVideoModel('runway/gen-3-alpha');
                            else if (value === 'pika') setVideoModel('pika-core');
                          }}>
                            <SelectTrigger className="w-full" aria-label="Video provider"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="together">Together</SelectItem>
                              <SelectItem value="openrouter">OpenRouter</SelectItem>
                              <SelectItem value="pika">Pika</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1.5">
                          <FieldLabel>Model</FieldLabel>
                          <Input value={videoModel} onChange={(event) => setVideoModel(event.target.value)} className="font-mono" aria-label="Video model" />
                        </div>
                      </div>
                      <ModelPicks
                        models={curatedModels.filter((model) => model.modality === 'video' && (model.provider === videoProvider || videoProvider === 'together' && model.provider === 'together'))}
                        active={videoModel}
                        onPick={setVideoModel}
                      />
                      <ValidationNote result={videoValidation} />
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="flex justify-end gap-2 border-t border-border pt-3">
            {campaignPosts.length > 0 && <Button variant="outline" onClick={() => setIsGeneratorExpanded(false)}>Cancel</Button>}
            <Button onClick={handleLaunchCampaign} disabled={loading || !campaignTopic}>
              {loading ? <Loader2 className="animate-spin" /> : null}
              {loading ? 'Starting generation' : `Launch ${campaignDays}-day campaign`}
            </Button>
          </div>
        </section>
      ) : null}

      {campaignPosts.length === 0 && !isGeneratorExpanded && (
        <EmptyState
          title="No campaign posts yet"
          description="Plan a topic and the networks it should cover. Drafts show up here for review before anything is published."
          action={<Button onClick={() => setIsGeneratorExpanded(true)}>Plan a campaign</Button>}
        />
      )}

      {campaignPosts.length > 0 && (
        <section className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex rounded-lg border border-border p-0.5">
              {([
                ['timeline', 'Timeline', CalendarRange],
                ['kanban', 'Board', LayoutGrid],
                ['schedule', 'Cadence & Triggers', Clock],
                ['analytics', 'Results', TrendingUp],
              ] as const).map(([id, label, Icon]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setCampaignViewMode(id)}
                  className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs ${campaignViewMode === id ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}
                >
                  <Icon className="size-3.5" /> {label}
                </button>
              ))}
            </div>
            {campaignViewMode !== 'analytics' && (
              <div className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
                <div className="relative sm:w-64">
                  <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input value={postQuery} onChange={(event) => setPostQuery(event.target.value)} placeholder="Search post text" aria-label="Search posts" className="px-8" />
                  {postQuery && (
                    <button type="button" aria-label="Clear search" className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground" onClick={() => setPostQuery('')}>
                      <X className="size-4" />
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-1">
                  {['all', 'linkedin', 'instagram', 'facebook'].map((platform) => (
                    <button
                      key={platform}
                      type="button"
                      onClick={() => setCampaignFilterPlatform(platform)}
                      className={`rounded-md px-2.5 py-1 text-xs ${campaignFilterPlatform === platform ? 'bg-muted text-foreground' : 'text-muted-foreground'}`}
                    >
                      {platform === 'all' ? 'All networks' : platformName(platform)}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {campaignViewMode === 'timeline' && (
            timelinePosts.length === 0 ? (
              <EmptyState title="No posts match" description="Try another word, network, or status." />
            ) : (
              <div className="space-y-6">
                {Array.from(dayGroups.entries()).map(([day, posts]) => (
                  <div key={day} className="space-y-2">
                    <h3 className="text-sm font-medium">{day}</h3>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {posts.map((post) => renderPostCard(post))}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}

          {campaignViewMode === 'kanban' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                {[
                  { title: 'Needs review', rows: campaignPosts.filter((post) => post.approval_status === 'pending' && matchesPlatform(post) && matchesQuery(post)) },
                  { title: 'Scheduled', rows: campaignPosts.filter((post) => (post.approval_status === 'approved' || post.approval_status === 'scheduled') && matchesPlatform(post) && matchesQuery(post)) },
                  { title: 'Published', rows: campaignPosts.filter((post) => post.approval_status === 'published' && matchesPlatform(post) && matchesQuery(post)) },
                ].map((column) => (
                  <div key={column.title} className="space-y-2 rounded-lg border border-border bg-card p-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium">{column.title}</h3>
                      <span className="text-xs text-muted-foreground">{column.rows.length}</span>
                    </div>
                    {column.rows.length === 0 ? (
                      <p className="py-8 text-center text-sm text-muted-foreground">None</p>
                    ) : (
                      <div className="space-y-3">{column.rows.sort(bySchedule).map((post) => renderPostCard(post))}</div>
                    )}
                  </div>
                ))}
              </div>
              {failedCount > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-destructive flex items-center gap-1.5">
                    <AlertCircle className="size-4" /> Failed Generation ({failedCount})
                  </h3>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {campaignPosts.filter((post) => (post.approval_status === 'failed' || post.status === 'failed') && matchesPlatform(post) && matchesQuery(post)).map((post) => renderPostCard(post))}
                  </div>
                </div>
              )}
              {rejectedCount > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium">Rejected</h3>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {campaignPosts.filter((post) => post.approval_status === 'rejected' && matchesPlatform(post) && matchesQuery(post)).map((post) => renderPostCard(post))}
                  </div>
                </div>
              )}
            </div>
          )}

          {campaignViewMode === 'analytics' && (
            <div className="space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-sm font-semibold">Results</h2>
                  <p className="mt-1 text-sm text-muted-foreground">Sync reads metrics from connected LinkedIn and Meta accounts. Patterns from that sync are used the next time a campaign is generated.</p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" disabled={analyticsLoading} onClick={() => fetchAnalyticsDashboard()}>
                    {analyticsLoading ? <Loader2 className="animate-spin" /> : null}
                    Refresh
                  </Button>
                  <Button size="sm" disabled={analyticsSyncing} onClick={() => syncAnalytics()}>
                    {analyticsSyncing ? <Loader2 className="animate-spin" /> : null}
                    {analyticsSyncing ? 'Syncing' : 'Sync platform metrics'}
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {[
                  ['Engagement rate', analyticsDash ? `${((analyticsDash.totals?.avg_engagement_rate || 0) * 100).toFixed(2)}%` : '—', `${analyticsDash?.totals?.with_metrics ?? 0} posts with metrics`],
                  ['Impressions', analyticsDash ? Math.round(analyticsDash.totals?.impressions || 0).toLocaleString() : '—', `${analyticsDash?.totals?.published ?? 0} published`],
                  ['Engagement', analyticsDash ? Math.round(analyticsDash.totals?.engagement || 0).toLocaleString() : '—', `${Math.round(analyticsDash?.totals?.clicks || 0).toLocaleString()} clicks`],
                  ['Click rate', analyticsDash ? `${((analyticsDash.totals?.avg_ctr || 0) * 100).toFixed(2)}%` : '—', 'Clicks divided by impressions'],
                ].map(([label, value, detail]) => (
                  <div key={label} className="rounded-lg border border-border bg-card px-3 py-3">
                    <p className="text-lg font-semibold leading-none">{value}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{label}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
                <div className="space-y-2 rounded-lg border border-border bg-card p-3 lg:col-span-3">
                  <h3 className="text-sm font-medium">Strongest posts</h3>
                  {(!analyticsDash?.top_posts || analyticsDash.top_posts.length === 0) && (
                    <p className="py-6 text-sm text-muted-foreground">No metrics yet. Publish a post, then sync platform metrics.</p>
                  )}
                  {(analyticsDash?.top_posts || []).map((post: any) => (
                    <div key={post.id} className="rounded-lg border border-border px-3 py-2">
                      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                        <span>{platformName(post.platform)}</span>
                        <span>Score {post.performance_score ?? 0}</span>
                      </div>
                      <p className="mt-1 line-clamp-2 text-sm">{post.content}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {Math.round(post.impressions || 0).toLocaleString()} impressions · {Math.round(post.engagement || 0).toLocaleString()} engagements · {((post.engagement_rate || 0) * 100).toFixed(2)}% rate · {((post.ctr || 0) * 100).toFixed(2)}% clicks
                      </p>
                      {post.learning_tags?.length > 0 && (
                        <p className="mt-1 text-xs text-muted-foreground">{post.learning_tags.join(' · ')}</p>
                      )}
                    </div>
                  ))}
                </div>
                <div className="space-y-2 rounded-lg border border-border bg-card p-3 lg:col-span-2">
                  <h3 className="text-sm font-medium">What the next campaign will prefer</h3>
                  <p className="text-xs text-muted-foreground">These weights come from synced results. They are not a guarantee of the next post.</p>
                  {(!analyticsDash?.learning_patterns || analyticsDash.learning_patterns.length === 0) && (
                    <p className="py-4 text-sm text-muted-foreground">Sync after publishing to build this list.</p>
                  )}
                  {(analyticsDash?.learning_patterns || []).slice(0, 12).map((pattern: any, index: number) => (
                    <div key={`${pattern.pattern_key}-${index}`} className="flex items-start justify-between gap-3 border-b border-border pb-2 text-sm">
                      <div>
                        <p>{pattern.banned ? 'Avoid' : pattern.weight > 0 ? 'Use more' : 'Neutral'} · {pattern.pattern_key}</p>
                        <p className="text-xs text-muted-foreground">
                          {pattern.sample_count} samples · {((pattern.avg_engagement_rate || 0) * 100).toFixed(2)}% engagement · weight {Number(pattern.weight || 0).toFixed(2)}
                        </p>
                      </div>
                      <span className="text-xs text-muted-foreground">{pattern.platform ? platformName(pattern.platform) : 'All'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {campaignViewMode === 'schedule' && (
            <div className="space-y-6 pt-2">
              <TriggerScheduleCard
                title="⚡ Autonomous Campaign Planner Triggers"
                subtitle="Automate recurring multi-day marketing campaign generation (e.g. Daily at 9:00 AM or Weekly on Mondays) with custom creative directions."
                targetType="campaign_planner"
                API_URL={API_URL}
                fetchWithAuth={fetchWithAuth}
                defaultInstructions={
                  `ROLE\n` +
                  `You are Lead Campaign Strategist & Brand Director.\n` +
                  `Generate high-converting, omnichannel campaign assets for the upcoming cycle.\n` +
                  `Focus on authentic founder storytelling, product differentiation, client problem resolution, and concise CTAs.\n` +
                  `Ensure visual prompts and hooks align with brand guidelines.`
                }
                extraConfig={{
                  days: campaignDays,
                  platforms: campaignPlatforms,
                  topic: campaignTopic || 'Ongoing Brand Awareness & Growth',
                }}
                onRunSuccess={() => {
                  fetchCampaignPosts();
                  fetchData();
                }}
              />
            </div>
          )}
        </section>
      )}

      <Dialog open={isMetaModalOpen} onOpenChange={(open) => { if (!open) { setIsMetaModalOpen(false); setPendingPublishPostId(null); setMetaTokenInput(''); } }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Connect Meta before publishing</DialogTitle>
            <DialogDescription>Instagram and Facebook need a Page access token. It is saved as the Meta integration key.</DialogDescription>
          </DialogHeader>
          <ol className="list-decimal space-y-1 pl-4 text-sm text-muted-foreground">
            <li>Open the Meta Graph API Explorer and choose your app.</li>
            <li>Generate a Page access token with instagram_content_publish, pages_show_list, and instagram_basic.</li>
            <li>Extend it in the Access Token Debugger, then paste it here.</li>
          </ol>
          <div className="space-y-1.5">
            <FieldLabel>Page access token</FieldLabel>
            <Input type="password" value={metaTokenInput} onChange={(event) => setMetaTokenInput(event.target.value)} autoComplete="off" placeholder="Paste the token" aria-label="Meta page access token" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsMetaModalOpen(false); setPendingPublishPostId(null); setMetaTokenInput(''); }}>Cancel</Button>
            <Button onClick={handleSaveMetaTokenAndPublish} disabled={!metaTokenInput.trim() || savingMetaToken}>
              {savingMetaToken ? 'Saving' : 'Save and publish'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isBulkScheduleOpen} onOpenChange={setIsBulkScheduleOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Schedule across a range</DialogTitle>
            <DialogDescription>Pending posts are spread between these dates at the same time each day.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">Quick Cadence Presets</span>
            <div className="grid grid-cols-3 gap-1.5">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-[11px] h-7 px-2"
                onClick={() => {
                  const start = new Date();
                  const end = new Date();
                  end.setDate(end.getDate() + 30);
                  setBulkStartDate(start.toISOString().split('T')[0]);
                  setBulkEndDate(end.toISOString().split('T')[0]);
                  setBulkPostingTime('09:00');
                }}
              >
                30 Days (9 AM)
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-[11px] h-7 px-2"
                onClick={() => {
                  const start = new Date();
                  const end = new Date();
                  end.setDate(end.getDate() + 30);
                  setBulkStartDate(start.toISOString().split('T')[0]);
                  setBulkEndDate(end.toISOString().split('T')[0]);
                  setBulkPostingTime('15:00');
                }}
              >
                30 Days (3 PM)
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="text-[11px] h-7 px-2"
                onClick={() => {
                  const start = new Date();
                  const end = new Date();
                  end.setDate(end.getDate() + 28);
                  setBulkStartDate(start.toISOString().split('T')[0]);
                  setBulkEndDate(end.toISOString().split('T')[0]);
                  setBulkPostingTime('10:00');
                }}
              >
                4 Weeks (Weekly)
              </Button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <FieldLabel>Start</FieldLabel>
              <Input type="date" value={bulkStartDate} onChange={(event) => setBulkStartDate(event.target.value)} aria-label="Schedule start" />
            </div>
            <div className="space-y-1.5">
              <FieldLabel>End</FieldLabel>
              <Input type="date" value={bulkEndDate} onChange={(event) => setBulkEndDate(event.target.value)} aria-label="Schedule end" />
            </div>
          </div>
          <div className="space-y-1.5">
            <FieldLabel>Time each day</FieldLabel>
            <Input type="time" value={bulkPostingTime} onChange={(event) => setBulkPostingTime(event.target.value)} aria-label="Daily posting time" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBulkScheduleOpen(false)}>Cancel</Button>
            <Button onClick={handleBulkSchedule} disabled={bulkScheduling || !bulkStartDate || !bulkEndDate || !bulkPostingTime}>
              {bulkScheduling ? 'Scheduling' : 'Schedule posts'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isCreatePostOpen} onOpenChange={setIsCreatePostOpen}>
        <DialogContent className="max-h-[92vh] overflow-hidden p-0 sm:max-w-5xl flex flex-col">
          <DialogHeader className="p-5 pb-4 border-b border-border bg-card">
            <div className="flex items-center gap-2">
              <span className="flex size-7 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
                <Sparkles className="size-4" />
              </span>
              <div>
                <DialogTitle className="text-base font-semibold">Post Composer & Multi-Platform Automation</DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                  Compose custom text, attach tags & rich media, and automate publishing across your connected social channels.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-border">
            {/* Left Column: Form & Composer Controls */}
            <div className="lg:col-span-7 p-5 space-y-4 overflow-y-auto">
              {/* 1. Target Networks */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <FieldLabel>Target Networks (Cross-Posting)</FieldLabel>
                  <span className="text-[11px] text-muted-foreground">
                    {createPostPlatforms.length} selected
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: 'linkedin', label: 'LinkedIn', color: 'text-[#0a66c2]' },
                    { id: 'instagram', label: 'Instagram', color: 'text-[#e4405f]' },
                    { id: 'facebook', label: 'Facebook', color: 'text-[#1877f2]' },
                    { id: 'twitter', label: 'X / Twitter', color: 'text-foreground' },
                  ].map((network) => {
                    const isSelected = createPostPlatforms.includes(network.id);
                    return (
                      <button
                        key={network.id}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            if (createPostPlatforms.length > 1) {
                              setCreatePostPlatforms(createPostPlatforms.filter((p) => p !== network.id));
                            } else {
                              notify('At least one platform must remain selected.');
                            }
                          } else {
                            setCreatePostPlatforms([...createPostPlatforms, network.id]);
                            setActivePreviewPlatform(network.id);
                          }
                        }}
                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                          isSelected
                            ? 'border-primary bg-primary/10 text-foreground ring-1 ring-primary/30 shadow-xs'
                            : 'border-border text-muted-foreground hover:bg-muted/40'
                        }`}
                      >
                        <span className={`size-2 rounded-full ${isSelected ? 'bg-primary' : 'bg-muted-foreground/40'}`} />
                        <span className={network.color}>{network.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 2. Post Caption / Copy */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <FieldLabel>Caption & Story Text</FieldLabel>
                  {(() => {
                    const len = createPostContent.length;
                    const isTwitter = createPostPlatforms.includes('twitter');
                    const limit = isTwitter ? 280 : 3000;
                    const isOver = len > limit;
                    return (
                      <span className={`text-[11px] font-mono ${isOver ? 'text-destructive font-semibold' : 'text-muted-foreground'}`}>
                        {len} / {limit} chars {isOver && '⚠️ Exceeds limit'}
                      </span>
                    );
                  })()}
                </div>
                <Textarea
                  value={createPostContent}
                  onChange={(event) => setCreatePostContent(event.target.value)}
                  placeholder="Share company updates, product highlights, customer wins, or an engaging industry hook..."
                  className="min-h-28 text-sm leading-relaxed"
                  aria-label="Post caption text"
                />
              </div>

              {/* 3. Hashtags & Tags Manager */}
              <div className="space-y-2 rounded-lg border border-border bg-card/60 p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Hash className="size-3.5 text-muted-foreground" />
                    <FieldLabel>Hashtags & Learning Tags</FieldLabel>
                  </div>
                  <span className="text-[11px] text-muted-foreground">Auto-formatted on publish</span>
                </div>

                {createPostTags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {createPostTags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 rounded-md bg-primary/10 border border-primary/20 px-2 py-0.5 text-xs text-primary font-medium"
                      >
                        #{tag}
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(tag)}
                          className="hover:text-destructive"
                          aria-label={`Remove tag ${tag}`}
                        >
                          <X className="size-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <Input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ',') {
                        e.preventDefault();
                        handleAddTag();
                      }
                    }}
                    placeholder="Add tag (e.g. AI, SaaS, Growth) & press Enter"
                    className="h-8 text-xs font-mono"
                    aria-label="New tag input"
                  />
                  <Button type="button" size="sm" variant="outline" className="h-8 text-xs shrink-0" onClick={() => handleAddTag()}>
                    <Plus className="size-3 mr-1" /> Add
                  </Button>
                </div>

                <div className="flex flex-wrap items-center gap-1 pt-1 text-[11px] text-muted-foreground">
                  <span className="mr-0.5">Quick picks:</span>
                  {['AI', 'Automation', 'Tech', 'Growth', 'SaaS', 'Innovation', 'Marketing'].map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => handleAddTag(suggestion)}
                      className="rounded border border-border px-1.5 py-0.5 hover:bg-muted/50 transition-colors"
                    >
                      +{suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* 4. Rich Media Upload & Attachment */}
              <div className="space-y-2 rounded-lg border border-border bg-card/60 p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <UploadCloud className="size-3.5 text-muted-foreground" />
                    <FieldLabel>Media Asset (Image / Video)</FieldLabel>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => setCreatePostMediaInputMode('upload')}
                      className={`px-2 py-0.5 rounded text-[11px] ${createPostMediaInputMode === 'upload' ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground'}`}
                    >
                      Upload File
                    </button>
                    <button
                      type="button"
                      onClick={() => setCreatePostMediaInputMode('url')}
                      className={`px-2 py-0.5 rounded text-[11px] ${createPostMediaInputMode === 'url' ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground'}`}
                    >
                      Paste URL
                    </button>
                  </div>
                </div>

                {createPostImageUrl || createPostVideoUrl ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between rounded-md border border-border bg-muted/40 p-2 text-xs">
                      <div className="flex items-center gap-2 min-w-0">
                        {createPostVideoUrl ? (
                          <Film className="size-4 shrink-0 text-indigo-500" />
                        ) : (
                          <ImageIcon className="size-4 shrink-0 text-blue-500" />
                        )}
                        <span className="truncate font-mono text-[11px]">
                          {createPostVideoUrl ? 'Video attached' : 'Image attached'}: {createPostImageUrl || createPostVideoUrl}
                        </span>
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs text-destructive hover:bg-destructive/10"
                        onClick={() => {
                          setCreatePostImageUrl('');
                          setCreatePostVideoUrl('');
                        }}
                      >
                        <Trash2 className="size-3 mr-1" /> Remove
                      </Button>
                    </div>

                    {createPostImageUrl && (
                      <div className="max-h-40 overflow-hidden rounded-md border border-border">
                        <img src={createPostImageUrl} alt="Preview" className="h-40 w-full object-cover" />
                      </div>
                    )}
                    {createPostVideoUrl && (
                      <div className="max-h-40 overflow-hidden rounded-md border border-border">
                        <video src={createPostVideoUrl} controls className="h-40 w-full bg-black object-cover" />
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    {createPostMediaInputMode === 'upload' ? (
                      <div
                        onDragOver={(e) => {
                          e.preventDefault();
                          setIsDragOver(true);
                        }}
                        onDragLeave={() => setIsDragOver(false)}
                        onDrop={(e) => {
                          e.preventDefault();
                          setIsDragOver(false);
                          const file = e.dataTransfer.files?.[0];
                          if (file) handleFileUpload(file, false);
                        }}
                        className={`rounded-lg border-2 border-dashed p-4 text-center transition-all ${
                          isDragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/50'
                        }`}
                      >
                        <input
                          type="file"
                          accept="image/*"
                          className="sr-only"
                          id="manual-image-file"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleFileUpload(file, false);
                          }}
                        />
                        <input
                          type="file"
                          accept="video/*"
                          className="sr-only"
                          id="manual-video-file"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleFileUpload(file, false);
                          }}
                        />

                        <div className="mx-auto flex size-9 items-center justify-center rounded-full bg-muted">
                          <UploadCloud className="size-4 text-muted-foreground" />
                        </div>
                        <p className="mt-2 text-xs font-medium">Drag & drop image or video here</p>
                        <p className="text-[11px] text-muted-foreground">Supports JPEG, PNG, WEBP, and MP4</p>
                        <div className="mt-3 flex justify-center gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            disabled={uploadingFile}
                            onClick={() => document.getElementById('manual-image-file')?.click()}
                          >
                            <ImageIcon className="size-3 mr-1" /> {uploadingFile ? 'Uploading…' : 'Browse Image'}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            disabled={uploadingFile}
                            onClick={() => document.getElementById('manual-video-file')?.click()}
                          >
                            <Film className="size-3 mr-1" /> {uploadingFile ? 'Uploading…' : 'Browse Video'}
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Input
                          placeholder="Paste public image or video URL (https://...)"
                          value={createPostImageUrl || createPostVideoUrl}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val.match(/\.(mp4|webm|mov)(\?.*)?$/i)) {
                              setCreatePostVideoUrl(val);
                              setCreatePostImageUrl('');
                            } else {
                              setCreatePostImageUrl(val);
                              setCreatePostVideoUrl('');
                            }
                          }}
                          className="h-8 text-xs font-mono"
                          aria-label="Direct media URL"
                        />
                      </div>
                    )}
                  </>
                )}

                {/* Optional AI prompt generator accordion */}
                <div className="pt-1">
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => {
                        if (!createPostImagePromptEnabled && !createPostVideoPromptEnabled) {
                          setCreatePostImagePromptEnabled(true);
                        } else {
                          setCreatePostImagePromptEnabled(false);
                          setCreatePostVideoPromptEnabled(false);
                        }
                      }}
                      className="text-[11px] font-medium text-primary hover:underline inline-flex items-center gap-1"
                    >
                      <Sparkles className="size-3" />
                      {createPostImagePromptEnabled || createPostVideoPromptEnabled
                        ? 'Hide AI Media Prompting'
                        : '+ Or let AI generate visuals from prompt'}
                    </button>
                  </div>

                  {(createPostImagePromptEnabled || createPostVideoPromptEnabled) && (
                    <div className="mt-2 space-y-2 rounded-md border border-border bg-background p-2.5">
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant={createPostImagePromptEnabled ? 'default' : 'outline'}
                          className="h-7 text-xs"
                          onClick={() => {
                            setCreatePostImagePromptEnabled(true);
                            setCreatePostVideoPromptEnabled(false);
                          }}
                        >
                          AI Image
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant={createPostVideoPromptEnabled ? 'default' : 'outline'}
                          className="h-7 text-xs"
                          onClick={() => {
                            setCreatePostImagePromptEnabled(false);
                            setCreatePostVideoPromptEnabled(true);
                          }}
                        >
                          AI Video
                        </Button>
                      </div>
                      <Textarea
                        value={createPostImagePromptEnabled ? createPostImagePrompt : createPostVideoPrompt}
                        onChange={(e) => {
                          if (createPostImagePromptEnabled) setCreatePostImagePrompt(e.target.value);
                          else setCreatePostVideoPrompt(e.target.value);
                        }}
                        placeholder="Describe the aesthetic or scene for AI generation..."
                        className="min-h-14 text-xs"
                      />
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-6 text-[11px]"
                        disabled={suggestingPrompt}
                        onClick={() => handleSuggestPrompt(createPostContent, createPostImagePromptEnabled ? 'image' : 'video', false)}
                      >
                        {suggestingPrompt ? 'Suggesting…' : '✨ Suggest prompt from text'}
                      </Button>
                    </div>
                  )}
                </div>
              </div>

              {/* 5. Execution & Automation Mode */}
              <div className="space-y-2">
                <FieldLabel>Execution & Scheduling Mode</FieldLabel>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    {
                      id: 'schedule',
                      title: 'Schedule & Automate',
                      desc: 'Auto-publish at set time',
                      icon: Clock,
                      color: 'text-blue-500',
                    },
                    {
                      id: 'now',
                      title: 'Publish Now',
                      desc: 'Instant live push',
                      icon: Send,
                      color: 'text-emerald-500',
                    },
                    {
                      id: 'draft',
                      title: 'Save as Draft',
                      desc: 'Review in timeline',
                      icon: FileText,
                      color: 'text-amber-500',
                    },
                  ].map((mode) => {
                    const active = createPostPublishMode === mode.id;
                    const Icon = mode.icon;
                    return (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => setCreatePostPublishMode(mode.id as any)}
                        className={`rounded-lg border p-2.5 text-left transition-all ${
                          active
                            ? 'border-primary bg-primary/10 ring-1 ring-primary/30 shadow-xs'
                            : 'border-border hover:bg-muted/40'
                        }`}
                      >
                        <div className="flex items-center gap-1.5">
                          <Icon className={`size-3.5 ${mode.color}`} />
                          <span className="text-xs font-semibold">{mode.title}</span>
                        </div>
                        <p className="mt-1 text-[10px] text-muted-foreground leading-tight">{mode.desc}</p>
                      </button>
                    );
                  })}
                </div>

                {createPostPublishMode === 'schedule' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                    <div className="space-y-1">
                      <FieldLabel>Publish Date & Time (UTC/Local)</FieldLabel>
                      <Input
                        type="datetime-local"
                        value={createPostScheduledAt}
                        onChange={(e) => setCreatePostScheduledAt(e.target.value)}
                        className="h-8 text-xs"
                        aria-label="Publish scheduled datetime"
                      />
                    </div>
                    <div className="space-y-1">
                      <FieldLabel>Campaign Timeline Day</FieldLabel>
                      <Input
                        type="number"
                        min={1}
                        value={createPostDay}
                        onChange={(e) => setCreatePostDay(parseInt(e.target.value, 10) || 1)}
                        className="h-8 text-xs"
                        aria-label="Timeline day index"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Live Feed Simulation */}
            <div className="lg:col-span-5 p-5 bg-muted/20 flex flex-col space-y-4 overflow-y-auto">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Eye className="size-4 text-muted-foreground" />
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Live Feed Preview</p>
                </div>
                <div className="flex gap-1">
                  {createPostPlatforms.map((plat) => (
                    <button
                      key={plat}
                      type="button"
                      onClick={() => setActivePreviewPlatform(plat)}
                      className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
                        activePreviewPlatform === plat
                          ? 'bg-foreground text-background shadow-xs'
                          : 'text-muted-foreground hover:bg-muted'
                      }`}
                    >
                      {platformName(plat)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Feed Card Mockup */}
              <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden text-card-foreground">
                {/* Platform-Specific Mockup Header */}
                <div className="p-3.5 border-b border-border/60">
                  <div className="flex items-center gap-2.5">
                    <div className="size-9 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xs shrink-0 shadow-xs">
                      O
                    </div>
                    <div className="min-w-0 flex-1 leading-tight">
                      <div className="flex items-center gap-1.5">
                        <p className="text-xs font-semibold truncate">
                          {activePreviewPlatform === 'instagram' ? 'octaos_official' : 'OctaOS Automation'}
                        </p>
                        {activePreviewPlatform === 'twitter' && (
                          <span className="text-[11px] text-muted-foreground">@octaos</span>
                        )}
                      </div>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {activePreviewPlatform === 'linkedin' && 'Enterprise Automation • Just now • 🌐'}
                        {activePreviewPlatform === 'facebook' && 'Business Page • Just now • 🌐'}
                        {activePreviewPlatform === 'instagram' && 'Sponsored • Audio: Original'}
                        {activePreviewPlatform === 'twitter' && 'Just now'}
                      </p>
                    </div>
                    <span className="text-muted-foreground text-xs">•••</span>
                  </div>
                </div>

                {/* Post Content Body */}
                <div className="p-3.5 space-y-2.5">
                  <p className="text-xs leading-relaxed whitespace-pre-wrap">
                    {createPostContent || (
                      <span className="italic text-muted-foreground">
                        Your post caption and message will appear here in real-time...
                      </span>
                    )}
                  </p>

                  {/* Tags formatted in caption */}
                  {createPostTags.length > 0 && (
                    <p className="text-xs font-medium text-blue-600 dark:text-blue-400">
                      {createPostTags.map((t) => `#${t}`).join(' ')}
                    </p>
                  )}
                </div>

                {/* Media Preview Box */}
                {(createPostImageUrl || createPostVideoUrl) && (
                  <div className="border-t border-border/60 bg-muted/40 overflow-hidden">
                    {createPostImageUrl && (
                      <img src={createPostImageUrl} alt="" className="w-full max-h-64 object-cover" />
                    )}
                    {createPostVideoUrl && (
                      <video src={createPostVideoUrl} controls className="w-full max-h-64 bg-black object-cover" />
                    )}
                  </div>
                )}

                {/* Platform-Specific Interactive Footer Bar */}
                <div className="p-3 border-t border-border/60 bg-muted/10 text-muted-foreground">
                  {activePreviewPlatform === 'linkedin' && (
                    <div className="flex items-center justify-between text-[11px] pt-0.5">
                      <span className="flex items-center gap-1 hover:text-foreground">
                        <ThumbsUp className="size-3.5" /> Like
                      </span>
                      <span className="flex items-center gap-1 hover:text-foreground">
                        <MessageSquare className="size-3.5" /> Comment
                      </span>
                      <span className="flex items-center gap-1 hover:text-foreground">
                        <Repeat className="size-3.5" /> Repost
                      </span>
                      <span className="flex items-center gap-1 hover:text-foreground">
                        <Send className="size-3.5" /> Send
                      </span>
                    </div>
                  )}

                  {activePreviewPlatform === 'instagram' && (
                    <div className="flex items-center justify-between text-foreground">
                      <div className="flex items-center gap-3">
                        <Heart className="size-4 hover:text-red-500 cursor-pointer" />
                        <MessageSquare className="size-4" />
                        <Send className="size-4" />
                      </div>
                      <span className="text-[10px] text-muted-foreground">0 likes</span>
                    </div>
                  )}

                  {activePreviewPlatform === 'facebook' && (
                    <div className="flex items-center justify-around text-[11px]">
                      <span className="flex items-center gap-1">
                        <ThumbsUp className="size-3.5" /> Like
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="size-3.5" /> Comment
                      </span>
                      <span className="flex items-center gap-1">
                        <Share2 className="size-3.5" /> Share
                      </span>
                    </div>
                  )}

                  {activePreviewPlatform === 'twitter' && (
                    <div className="flex items-center justify-between text-[11px] px-2">
                      <span className="flex items-center gap-1"><MessageSquare className="size-3.5" /> 0</span>
                      <span className="flex items-center gap-1"><Repeat className="size-3.5" /> 0</span>
                      <span className="flex items-center gap-1"><Heart className="size-3.5" /> 0</span>
                      <span className="flex items-center gap-1"><Share2 className="size-3.5" /></span>
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-lg border border-border/60 bg-card p-3 text-[11px] text-muted-foreground space-y-1">
                <p className="font-semibold text-foreground flex items-center gap-1">
                  <CheckCircle2 className="size-3.5 text-emerald-500" />
                  Hands-Off Automation Enabled
                </p>
                <p>
                  When scheduled, OctaOS’s Celery Beat background scheduler checks every 5 minutes and publishes automatically without requiring manual review.
                </p>
              </div>
            </div>
          </div>

          <DialogFooter className="p-4 border-t border-border bg-card flex items-center justify-between sm:justify-between">
            <Button variant="outline" size="sm" onClick={() => setIsCreatePostOpen(false)}>
              Cancel
            </Button>
            <div className="flex items-center gap-2">
              <Button
                onClick={handleCreateManualPost}
                disabled={creatingPost || !createPostContent.trim() || createPostPlatforms.length === 0}
                className="gap-1.5"
              >
                {creatingPost ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Saving…
                  </>
                ) : createPostPublishMode === 'now' ? (
                  <>
                    <Send className="size-4" /> Publish Now ({createPostPlatforms.length})
                  </>
                ) : createPostPublishMode === 'schedule' ? (
                  <>
                    <Clock className="size-4" /> Schedule & Automate ({createPostPlatforms.length})
                  </>
                ) : (
                  <>
                    <FileText className="size-4" /> Save as Draft ({createPostPlatforms.length})
                  </>
                )}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

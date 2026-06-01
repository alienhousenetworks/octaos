'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Activity, Users, DollarSign, BarChart3, Briefcase, Zap, BookOpen, LogOut, Calendar, Film, Image as ImageIcon, Edit2, MessageSquare, Send, Clock } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

export default function Home() {
  const [appState, setAppState] = useState<'landing' | 'login' | 'signup' | 'app'>('landing');
  const [token, setToken] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const originalConsoleError = console.error;
      console.error = (...args: any[]) => {
        originalConsoleError.apply(console, args);
        const message = args.map(arg => {
          if (arg instanceof Error) return arg.message + "\n" + arg.stack;
          return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
        }).join(' ');
        
        // Alert on any hydration or rendering errors
        if (message.includes('Error') || message.includes('failed') || message.includes('mismatch') || message.includes(' hydration ') || message.includes('hydrating')) {
          alert("React/Console Error Caught:\n" + message);
        }
      };

      const handleError = (event: ErrorEvent) => {
        alert("Global Error Caught:\n" + event.message + "\nAt: " + event.filename + ":" + event.lineno);
      };
      
      const handleRejection = (event: PromiseRejectionEvent) => {
        alert("Promise Rejection Caught:\n" + event.reason);
      };

      window.addEventListener('error', handleError);
      window.addEventListener('unhandledrejection', handleRejection);

      return () => {
        console.error = originalConsoleError;
        window.removeEventListener('error', handleError);
        window.removeEventListener('unhandledrejection', handleRejection);
      };
    }
  }, []);

  // Auth Forms
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [companyName, setCompanyName] = useState('');

  // Dashboard States
  const [activeView, setActiveView] = useState('dashboard');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [queue, setQueue] = useState<{posts: any[], leads: any[]}>({posts: [], leads: []});
  const [timeline, setTimeline] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>({});
  const [teams, setTeams] = useState<any[]>([]);
  const [apps, setApps] = useState<any[]>([]);
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);

  // HR States
  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [hrRole, setHrRole] = useState('Software Engineer');
  const [hrRequirements, setHrRequirements] = useState('React, Node.js, Python, 3+ years experience');
  const [hrSalary, setHrSalary] = useState('$120,000/year');
  const [hrCount, setHrCount] = useState(5);
  const [hrLoading, setHrLoading] = useState(false);
  const [outreachLoading, setOutreachLoading] = useState(false);
  const [interviewLoading, setInterviewLoading] = useState(false);
  
  // Knowledge Form
  const [kbDept, setKbDept] = useState('Marketing');
  const [kbType, setKbType] = useState('Brand Guidelines');
  const [kbContent, setKbContent] = useState('');

  // API Key Form
  const [keyProvider, setKeyProvider] = useState('anthropic');
  const [keyValue, setKeyValue] = useState('');
  const [isKeyDialogOpen, setIsKeyDialogOpen] = useState(false);

  // Campaign State
  const [campaignTopic, setCampaignTopic] = useState('');
  const [campaignDays, setCampaignDays] = useState(30);
  const [campaignPlatforms, setCampaignPlatforms] = useState<string[]>(['linkedin', 'instagram', 'facebook']);
  const [textProvider, setTextProvider] = useState('gemini');
  const [imageProvider, setImageProvider] = useState('openai');
  const [orchProvider, setOrchProvider] = useState('anthropic');
  const [orchModel, setOrchModel] = useState('claude-sonnet-4-6');
  const [videoProvider, setVideoProvider] = useState('pika');
  const [generateImages, setGenerateImages] = useState(true);
  const [generateVideos, setGenerateVideos] = useState(true);
  const [campaignPosts, setCampaignPosts] = useState<any[]>([]);
  
  // Cost Optimization States
  const [optimizationMetrics, setOptimizationMetrics] = useState<any>(null);
  const [optimizationLoading, setOptimizationLoading] = useState(false);
  
  // Interactive Landing page states
  const [tasksPerDay, setTasksPerDay] = useState(60);
  const [hourlyRate, setHourlyRate] = useState(35);
  const [activePreviewAgent, setActivePreviewAgent] = useState('marketing');

  // Inline editing state
  const [editingPostId, setEditingPostId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const [editingImageUrl, setEditingImageUrl] = useState('');
  const [editingVideoUrl, setEditingVideoUrl] = useState('');

  // Publish-Now + Meta credential modal state
  const [publishingPostId, setPublishingPostId] = useState<string | null>(null);
  const [publishResult, setPublishResult] = useState<{success: boolean; message: string} | null>(null);
  const [isMetaModalOpen, setIsMetaModalOpen] = useState(false);
  const [pendingPublishPostId, setPendingPublishPostId] = useState<string | null>(null);
  const [metaTokenInput, setMetaTokenInput] = useState('');
  const [savingMetaToken, setSavingMetaToken] = useState(false);

  // Support States
  const [tickets, setTickets] = useState<any[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [replyText, setReplyText] = useState('');
  const [supportSettings, setSupportSettings] = useState({ whatsapp_auto_reply: true, email_auto_reply: true });
  const [simChannel, setSimChannel] = useState<'whatsapp' | 'email'>('whatsapp');
  const [simSender, setSimSender] = useState('+15553334444');
  const [simContent, setSimContent] = useState('');
  const [simSubject, setSimSubject] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [simulatingMessage, setSimulatingMessage] = useState(false);

  // Boardroom/Coordination States
  const [meetings, setMeetings] = useState<any[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [selectedMeeting, setSelectedMeeting] = useState<any | null>(null);
  const [isCreateMeetingOpen, setIsCreateMeetingOpen] = useState(false);
  const [manualMeetingTitle, setManualMeetingTitle] = useState('');
  const [manualMeetingTopic, setManualMeetingTopic] = useState('');
  const [manualMeetingParticipants, setManualMeetingParticipants] = useState<string[]>(['Support AI', 'Sales AI']);
  const [manualMeetingLoading, setManualMeetingLoading] = useState(false);

  const fetchMeetings = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings`);
      if (res.ok) {
        const data = await res.json();
        setMeetings(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMeetingDetails = async (meetingId: string) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/${meetingId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedMeeting(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchOptimizationMetrics = async () => {
    if (!token) return;
    setOptimizationLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/llm/optimization-metrics`);
      if (res.ok) {
        const data = await res.json();
        setOptimizationMetrics(data);
      }
    } catch (e) {
      console.error("Failed to fetch optimization metrics:", e);
    } finally {
      setOptimizationLoading(false);
    }
  };

  const handleCreateManualMeeting = async () => {
    if (!manualMeetingTitle || !manualMeetingTopic) return;
    setManualMeetingLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/coordination/meetings/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: manualMeetingTitle,
          topic: manualMeetingTopic,
          participants: manualMeetingParticipants
        })
      });
      const data = await res.json();
      if (res.ok) {
        setManualMeetingTitle('');
        setManualMeetingTopic('');
        setIsCreateMeetingOpen(false);
        fetchMeetings();
        if (data.id) {
          setSelectedMeetingId(data.id);
        }
      } else {
        alert(`Error: ${data.detail || 'Failed to start boardroom meeting'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setManualMeetingLoading(false);
    }
  };

  const fetchCampaignPosts = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/`);
      if (res.ok) {
        const data = await res.json();
        setCampaignPosts(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLaunchCampaign = async () => {
    if (!campaignTopic) return;
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/marketing/campaign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: campaignTopic,
          days: campaignDays,
          platforms: campaignPlatforms,
          text_provider: textProvider,
          image_provider: imageProvider,
          video_provider: videoProvider,
          generate_images: generateImages,
          generate_videos: generateVideos
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("30-Day Marketing Campaign has been scheduled for generation! You can monitor progress in the AI Activity Feed.");
        setCampaignTopic('');
        fetchCampaignPosts();
      } else {
        alert(`Error: ${data.detail || 'Failed to trigger campaign'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
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
        alert('✅ Post approved and scheduled!\n\nTo publish immediately to Instagram/Facebook, click the "Publish Now" button on the post card. Make sure your Meta API key is configured in Settings → Integrations.');
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
      alert('LinkedIn API key is not configured.\n\nGo to Settings → Integrations → Social Media and follow the steps to connect your LinkedIn account.');
      return;
    }

    setPublishingPostId(postId);
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
        alert(`Failed to save Meta token: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      alert('Network error saving Meta token.');
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
        alert("All pending campaign posts have been approved and scheduled!");
        fetchCampaignPosts();
        fetchData();
      }
    } catch (e) {
      console.error(e);
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
          scheduled_at: post.scheduled_at
        })
      });
      if (res.ok) {
        setEditingPostId(null);
        fetchCampaignPosts();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const startEditing = (post: any) => {
    setEditingPostId(post.id);
    setEditingContent(post.content);
    setEditingImageUrl(post.image_url || '');
    setEditingVideoUrl(post.video_url || '');
  };

  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedTenantId = localStorage.getItem('tenant_id');
    if (savedToken) {
      setToken(savedToken);
      if (savedTenantId) {
        setTenantId(savedTenantId);
      }
      setAppState('app');
    }
  }, []);

  const fetchWithAuth = async (url: string, options: any = {}) => {
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
      handleLogout();
    }
    return res;
  };

  const fetchTickets = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets`);
      if (res.ok) {
        const data = await res.json();
        setTickets(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMessages = async (ticketId: string) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets/${ticketId}/messages`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSupportSettings = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/settings`);
      if (res.ok) {
        const data = await res.json();
        setSupportSettings(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const saveSupportSettings = async (settings: { whatsapp_auto_reply: boolean, email_auto_reply: boolean }) => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/support/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        const data = await res.json();
        setSupportSettings(data.settings);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendManualReply = async () => {
    if (!selectedTicketId || !replyText.trim()) return;
    setSendingReply(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/tickets/${selectedTicketId}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: replyText })
      });
      if (res.ok) {
        setReplyText('');
        fetchMessages(selectedTicketId);
        fetchTickets();
      } else {
        const data = await res.json();
        alert(`Failed to send reply: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSendingReply(false);
    }
  };

  const handleSimulateMessage = async () => {
    if (!simSender.trim() || !simContent.trim()) {
      alert("Please enter both sender and content.");
      return;
    }
    setSimulatingMessage(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/support/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: simChannel,
          sender: simSender,
          content: simContent,
          subject: simChannel === 'email' ? (simSubject || 'Support Request') : undefined
        })
      });
      const data = await res.json();
      if (res.ok) {
        setSimContent('');
        setSimSubject('');
        fetchTickets();
        if (data.ticket_id) {
          setSelectedTicketId(data.ticket_id);
          fetchMessages(data.ticket_id);
        }
      } else {
        alert(`Simulation Error: ${data.detail || 'Failed to simulate'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSimulatingMessage(false);
    }
  };

  const fetchCandidates = async () => {
    if (!token) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/`);
      if (res.ok) {
        const data = await res.json();
        setCandidates(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSourceCandidates = async () => {
    if (!hrRole || !hrRequirements) return;
    setHrLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: hrRole,
          requirements: hrRequirements,
          salary: hrSalary,
          count: hrCount
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("HR Agent has started sourcing candidates! Check progress in the Activity Feed.");
        setHrRole('');
        setHrRequirements('');
        fetchCandidates();
        fetchData();
      } else {
        alert(`Error: ${data.detail || 'Failed to source candidates'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setHrLoading(false);
    }
  };

  const handleCandidateOutreach = async (candidateId: string) => {
    setOutreachLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}/outreach`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel: "free_outreach"
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("Outreach sent successfully!");
        fetchCandidates();
        fetchData();
      } else {
        alert(`Error: ${data.detail || 'Failed to send outreach'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setOutreachLoading(false);
    }
  };

  const handleScheduleInterview = async (candidateId: string) => {
    setInterviewLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/hr/${candidateId}/interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool: "free_scheduling"
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("Interview scheduled successfully!");
        fetchCandidates();
        fetchData();
      } else {
        alert(`Error: ${data.detail || 'Failed to schedule interview'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setInterviewLoading(false);
    }
  };

  const fetchData = async () => {
    if (!token) return;
    try {
      if (!tenantId) {
        const meRes = await fetchWithAuth(`${API_URL}/auth/me`);
        if (meRes.ok) {
          const meData = await meRes.json();
          if (meData.tenant_id) {
            localStorage.setItem('tenant_id', meData.tenant_id);
            setTenantId(meData.tenant_id);
          }
        }
      }

      const [qRes, tRes, kRes, mRes, tmRes, aRes, keyStatusRes] = await Promise.all([
        fetchWithAuth(`${API_URL}/commands/queue`),
        fetchWithAuth(`${API_URL}/commands/timeline`),
        fetchWithAuth(`${API_URL}/commands/knowledge`),
        fetchWithAuth(`${API_URL}/dashboard/metrics`),
        fetchWithAuth(`${API_URL}/dashboard/teams`),
        fetchWithAuth(`${API_URL}/dashboard/marketplace/installed`),
        fetchWithAuth(`${API_URL}/commands/keys`)
      ]);
      setQueue(await qRes.json());
      setTimeline(await tRes.json());
      setKnowledge(await kRes.json());
      setMetrics(await mRes.json());
      setTeams(await tmRes.json());
      setApps(await aRes.json());
      
      const keyStatusData = await keyStatusRes.json();
      setConfiguredProviders(keyStatusData.configured_providers || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (appState === 'app') {
      fetchData();
      fetchCampaignPosts();
      fetchTickets();
      fetchSupportSettings();
      fetchCandidates();
      fetchMeetings();
      fetchOptimizationMetrics();
      const interval = setInterval(() => {
        fetchData();
        fetchCampaignPosts();
        fetchTickets();
        fetchCandidates();
        fetchMeetings();
        fetchOptimizationMetrics();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [appState, token]);

  useEffect(() => {
    if (!selectedTicketId || !token) return;
    fetchMessages(selectedTicketId);
    const interval = setInterval(() => {
      fetchMessages(selectedTicketId);
    }, 4000);
    return () => clearInterval(interval);
  }, [selectedTicketId, token]);

  useEffect(() => {
    if (!selectedMeetingId || !token) return;
    fetchMeetingDetails(selectedMeetingId);
    const interval = setInterval(() => {
      fetchMeetingDetails(selectedMeetingId);
    }, 2000);
    return () => clearInterval(interval);
  }, [selectedMeetingId, token]);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, company_name: companyName })
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        if (data.tenant_id) {
          localStorage.setItem('tenant_id', data.tenant_id);
          setTenantId(data.tenant_id);
        }
        setAppState('app');
      } else {
        alert(data.detail || "Signup failed");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to connect to the backend server. Please verify that the backend is running at " + API_URL);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
        if (data.tenant_id) {
          localStorage.setItem('tenant_id', data.tenant_id);
          setTenantId(data.tenant_id);
        }
        setAppState('app');
      } else {
        alert(data.detail || "Login failed");
      }
    } catch (e) {
      console.error(e);
      alert("Failed to connect to the backend server. Please verify that the backend is running at " + API_URL);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('tenant_id');
    setToken(null);
    setTenantId(null);
    setAppState('landing');
  };

  const handleRunCommand = async () => {
    if (!prompt) return;
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, provider: orchProvider, model: orchModel })
      });
      const data = await res.json();
      if (res.ok) {
        setPrompt('');
        fetchData();
      } else {
        alert(`Error: ${data.detail || 'Failed to execute command'}`);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const addKnowledge = async () => {
    if (!kbContent) return;
    try {
      await fetchWithAuth(`${API_URL}/commands/knowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ department: kbDept, doc_type: kbType, content: kbContent })
      });
      setKbContent('');
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

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

  const saveApiKey = async () => {
    if (!keyValue) return;
    try {
      await fetchWithAuth(`${API_URL}/commands/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: keyProvider, key: keyValue })
      });
      setKeyValue('');
      setIsKeyDialogOpen(false);
      alert(`${keyProvider} API key saved successfully!`);
      fetchData();
    } catch (e) {
      console.error(e);
    }
  };

  const marketplacePacks = [
    { 
      name: "Restaurant Growth Pack", 
      desc: "Automates Yelp reviews, daily Instagram specials, and local lead gen.", 
      icon: "🍔",
      category: "Local Marketing",
      complexity: "Beginner",
      timeSaved: "12h/week",
      features: ["Yelp Review Auto-Responder", "Instagram Daily Specials Scheduler", "Local Community Lead Scraper"]
    },
    { 
      name: "SaaS Outreach System", 
      desc: "End-to-end cold email sequencing, LinkedIn DMs, and demo booking.", 
      icon: "🚀",
      category: "B2B Outbound",
      complexity: "Advanced",
      timeSaved: "35h/week",
      features: ["Cold Email Sequencing", "LinkedIn DM Personalizer", "Demo Booking Scheduler"]
    },
    { 
      name: "Real Estate Lead Engine", 
      desc: "Property listing auto-generation, Zillow scraping, and client follow-ups.", 
      icon: "🏡",
      category: "Real Estate",
      complexity: "Intermediate",
      timeSaved: "20h/week",
      features: ["Property Description Generator", "Zillow Agent Scraper", "Client Lead Follow-up Agent"]
    },
    { 
      name: "E-Commerce Growth Autopilot", 
      desc: "SEO product desc generator, competitor price monitor, and abandoned cart SMS sequences.", 
      icon: "🛍️",
      category: "E-Commerce",
      complexity: "Intermediate",
      timeSaved: "25h/week",
      features: ["SEO Product Description Writer", "Competitor Price Monitor", "Cart Abandonment SMS Sequence"]
    },
    { 
      name: "Medical Clinic Receptionist", 
      desc: "Automates patient scheduling, SMS check-in reminders, and insurance triage ticketing.", 
      icon: "🏥",
      category: "Healthcare",
      complexity: "Intermediate",
      timeSaved: "18h/week",
      features: ["Patient Calendar Sync", "SMS Confirmation Reminder", "Insurance Eligibility Triage"]
    },
    { 
      name: "Law Firm Document Automator", 
      desc: "Scans contracts for liability clauses, extracts renewal dates, and drafts legal response letters.", 
      icon: "⚖️",
      category: "LegalTech",
      complexity: "Advanced",
      timeSaved: "30h/week",
      features: ["Contract Clause Scanner", "Renewal Date Extractor", "Legal Correspondence Drafter"]
    },
    { 
      name: "FinTech Compliance Suite", 
      desc: "Automates quarterly audits, flags suspicious transactions, and prepares anti-money laundering compliance drafts.", 
      icon: "📊",
      category: "Fintech",
      complexity: "Advanced",
      timeSaved: "40h/week",
      features: ["Quarterly Audit Automator", "AML Pattern Detection", "Transaction Anomaly Flagger"]
    },
    { 
      name: "Creative Content Lab", 
      desc: "Converts raw video transcripts into social media clips, generates blog outlines, and autogenerates Pinterest pins.", 
      icon: "🎨",
      category: "Creative Agency",
      complexity: "Beginner",
      timeSaved: "15h/week",
      features: ["Video-to-Text Snippet Generator", "SEO Blog Outline Writer", "Pinterest Graphic Auto-Pinner"]
    },
    { 
      name: "HR Recruiter & Onboarding System", 
      desc: "Screens resumes against job specs, runs preliminary interactive screening tests, and coordinates onboarding calendars.", 
      icon: "👔",
      category: "Human Resources",
      complexity: "Intermediate",
      timeSaved: "28h/week",
      features: ["CV Parser & Score Matcher", "Interactive Interview Simulator", "Onboarding Schedule Coordinator"]
    }
  ];

  // LANDING PAGE VIEW
  if (appState === 'landing') {
    const hoursSaved = Math.round(tasksPerDay * 0.75 * 30);
    const moneySaved = Math.round(hoursSaved * hourlyRate);

    return (
      <div className="min-h-screen bg-[#030014] text-[#f4f4f7] relative overflow-hidden font-sans">
        {/* Ambient background glows */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[rgba(139,92,246,0.15)] rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[rgba(59,130,246,0.15)] rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-[40%] left-[25%] w-[400px] h-[400px] bg-[rgba(16,185,129,0.06)] rounded-full blur-[150px] pointer-events-none" />

        {/* Global Grid Overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

        {/* Header */}
        <header className="sticky top-0 z-50 h-20 glass-panel border-b border-[rgba(167,139,250,0.1)] flex items-center justify-between px-8 md:px-16">
          <div className="flex items-center gap-3 text-2xl font-black tracking-tight text-white">
            <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2 rounded-xl shadow-lg shadow-violet-500/20">
              <Zap className="text-white fill-white h-5 w-5 animate-pulse" />
            </div>
            <span>Nexus<span className="text-violet-400">OS</span></span>
          </div>
          <div className="flex items-center gap-6">
            <button 
              onClick={() => setAppState('login')} 
              className="text-gray-300 hover:text-white font-medium transition-colors"
            >
              Log in
            </button>
            <button 
              onClick={() => setAppState('signup')} 
              className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold px-6 py-2.5 rounded-xl shadow-lg shadow-violet-500/25 transition-all hover:scale-105 active:scale-95"
            >
              Sign up
            </button>
          </div>
        </header>

        {/* Hero Section */}
        <main className="max-w-7xl mx-auto px-6 md:px-16 pt-16 pb-24 relative z-10">
          <div className="text-center max-w-3xl mx-auto space-y-6 mb-20">
            {/* Tagline Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300 text-xs font-bold tracking-wider uppercase animate-pulse-glow">
              <Zap size={12} className="fill-violet-300" /> NexusOS Autonomous Engine v2.0
            </div>

            <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight leading-[1.1] animate-in fade-in slide-in-from-bottom-4 duration-500">
              Your Autonomous <br />
              <span className="bg-gradient-to-r from-violet-400 via-indigo-400 to-emerald-400 text-transparent bg-clip-text animate-text-shine">
                AI Agent Workforce.
              </span>
            </h1>

            <p className="text-lg md:text-xl text-gray-400 leading-relaxed max-w-2xl mx-auto">
              Hire specialized AI Agents for Marketing, Sales, Customer Support, and HR. Define high-level goals and let your virtual team execute them autonomously.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
              <button 
                onClick={() => setAppState('signup')} 
                className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-lg font-bold px-8 py-4 rounded-xl shadow-xl shadow-violet-500/30 hover:shadow-violet-500/40 transition-all hover:scale-105 active:scale-95"
              >
                Deploy Your AI Team
              </button>
              <button 
                onClick={() => {
                  const el = document.getElementById('previews');
                  el?.scrollIntoView({ behavior: 'smooth' });
                }} 
                className="bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.07)] text-white text-lg font-bold px-8 py-4 rounded-xl border border-gray-700/50 hover:border-gray-600 transition-all hover:scale-105 active:scale-95"
              >
                Watch Previews
              </button>
            </div>
          </div>

          {/* Interactive Agent Previews */}
          <div id="previews" className="mb-24 scroll-mt-24">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-extrabold text-white">Meet Your Virtual Employees</h2>
              <p className="text-gray-400 mt-2">Click each department tab to preview live workspace outputs.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
              {/* Left Selector List - 5 cols */}
              <div className="lg:col-span-5 flex flex-col gap-4">
                {[
                  {
                    id: 'marketing',
                    name: 'Marketing Copywriter',
                    title: 'Jules - Senior Copywriter',
                    desc: 'Autonomously schedules 30-day visual campaigns across LinkedIn, Facebook, and Instagram.',
                    glow: 'glow-marketing',
                    bullet: 'Outputs high-converting copy, DALLE-3 graphics, and loop videos.',
                    color: 'text-violet-400'
                  },
                  {
                    id: 'sales',
                    name: 'B2B Sales SDR',
                    title: 'Alex - Outbound SDR',
                    desc: 'Scrapes local leads via Google Maps or B2B platforms, verifies emails, and handles outreach.',
                    glow: 'glow-sales',
                    bullet: 'Tracks lead statuses, sends automated email pitches via SMTP credentials.',
                    color: 'text-emerald-400'
                  },
                  {
                    id: 'support',
                    name: 'Support Agent',
                    title: 'Sam - Omnichannel Support',
                    desc: 'Answers user inquiries 24/7 via WhatsApp and Email using company brand context.',
                    glow: 'glow-support',
                    bullet: 'Features dynamic simulator for sandbox testing with realistic human delays.',
                    color: 'text-blue-400'
                  },
                  {
                    id: 'hr',
                    name: 'Hiring Recruiter',
                    title: 'Hunter - Technical Recruiter',
                    desc: 'Sources candidates matching job requirements, drafts outreach letters, and schedules meetings.',
                    glow: 'glow-hr',
                    bullet: 'Integrates calendar sync to book direct Google Meet video calls.',
                    color: 'text-amber-400'
                  }
                ].map(agent => (
                  <div
                    key={agent.id}
                    onClick={() => setActivePreviewAgent(agent.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setActivePreviewAgent(agent.id);
                      }
                    }}
                    className={`text-left p-6 rounded-2xl border transition-all duration-300 relative overflow-hidden cursor-pointer ${
                      activePreviewAgent === agent.id 
                        ? `glass-panel ${agent.glow} scale-[1.02] border-violet-500/40` 
                        : 'bg-[rgba(10,8,26,0.3)] hover:bg-[rgba(255,255,255,0.02)] border-gray-800/80'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <h3 className="font-bold text-lg text-white">{agent.name}</h3>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full bg-[rgba(255,255,255,0.04)] border border-gray-700 ${agent.color}`}>
                        Active
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 mt-2">{agent.desc}</p>
                    {activePreviewAgent === agent.id && (
                      <div className="mt-4 pt-3 border-t border-gray-800 text-xs text-gray-300 flex items-center gap-1.5">
                        <Zap size={12} className="text-violet-400 fill-violet-400" />
                        {agent.bullet}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Right Output Mock - 7 cols */}
              <div className="lg:col-span-7 flex flex-col justify-center">
                <div className="glass-panel border-violet-500/20 rounded-3xl p-6 min-h-[440px] flex flex-col relative overflow-hidden shadow-2xl">
                  {/* Subtle purple gradient orb inside mock container */}
                  <div className="absolute top-[-50px] right-[-50px] w-48 h-48 bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />

                  {/* Window Chrome */}
                  <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-4">
                    <div className="flex gap-1.5">
                      <span className="w-3 h-3 rounded-full bg-rose-500/80" />
                      <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                      <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
                    </div>
                    <span className="text-xs font-semibold text-gray-500 tracking-wide uppercase">Workspace Output Preview</span>
                    <span className="w-3 h-3 opacity-0" />
                  </div>

                  {/* Output content depending on active tab */}
                  {activePreviewAgent === 'marketing' && (
                    <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                      <div>
                        <div className="flex items-center gap-3 mb-3">
                          <div className="bg-violet-600/20 text-violet-400 p-2 rounded-lg text-xs font-bold">LINKEDIN</div>
                          <span className="text-xs text-gray-400 font-medium">Day 4 of 30</span>
                          <span className="ml-auto text-[10px] bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded font-bold uppercase">Pending Approval</span>
                        </div>
                        <div className="bg-[rgba(255,255,255,0.02)] p-4 rounded-xl border border-gray-800 text-sm text-gray-300 whitespace-pre-line leading-relaxed">
                          {"☕️ Work hard, coffee harder! \n\nWe're thrilled to introduce our new Organic Cold Brew at BlueBottle Cafe. Cold-steeped for 18 hours for maximum smoothness and low acidity. Pop in today and grab your jar! \n\n#cafevibes #organicroast #coldbrew"}
                        </div>
                      </div>
                      
                      <div className="relative rounded-xl overflow-hidden border border-gray-800 aspect-[16/9] flex items-center justify-center bg-gradient-to-br from-indigo-950/50 to-violet-950/50 shadow-inner">
                        <div className="text-center p-4">
                          <ImageIcon size={36} className="text-violet-400 mx-auto mb-2 animate-bounce" />
                          <span className="text-xs text-gray-400 font-bold block uppercase tracking-wider">AI Graphic Generated</span>
                          <span className="text-[10px] text-gray-500 italic block mt-0.5">Prompt: \"Vibrant graphic showcasing cold brew coffee on wooden table, cafe vibes, modern illustration\"</span>
                        </div>
                      </div>

                      <div className="flex justify-end gap-2 pt-2">
                        <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs px-4 py-2 rounded-lg font-semibold cursor-not-allowed">Reject</span>
                        <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs px-4 py-2 rounded-lg font-semibold cursor-not-allowed">Approve & Publish</span>
                      </div>
                    </div>
                  )}

                  {activePreviewAgent === 'sales' && (
                    <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                      <div>
                        <div className="flex items-center gap-3 mb-4">
                          <div className="bg-emerald-600/20 text-emerald-400 p-2 rounded-lg text-xs font-bold">APOLLO.IO</div>
                          <span className="text-xs text-gray-400 font-medium">B2B Sourcing Active</span>
                          <span className="ml-auto text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold uppercase">4 Leads Found</span>
                        </div>

                        <div className="border border-gray-800 rounded-xl overflow-hidden bg-[rgba(0,0,0,0.2)]">
                          <table className="w-full text-left text-xs">
                            <thead className="bg-gray-900/60 border-b border-gray-800 text-gray-400 font-bold uppercase tracking-wider">
                              <tr>
                                <th className="p-3">Lead Name</th>
                                <th className="p-3">Company</th>
                                <th className="p-3">Email Address</th>
                                <th className="p-3">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800 text-gray-300">
                              {[
                                { name: "Sarah Connor", comp: "Cyberdyne Systems", mail: "s.connor@cyberdyne.io", stat: "Sequence Sent" },
                                { name: "Bruce Wayne", comp: "Wayne Enterprises", mail: "bruce@waynecorp.com", stat: "Replied / Booked" },
                                { name: "Tony Stark", comp: "Stark Industries", mail: "tony@stark.com", stat: "Sequence Active" }
                              ].map(l => (
                                <tr key={l.name} className="hover:bg-gray-800/40">
                                  <td className="p-3 font-semibold text-white">{l.name}</td>
                                  <td className="p-3">{l.comp}</td>
                                  <td className="p-3 text-violet-400 font-mono">{l.mail}</td>
                                  <td className="p-3">
                                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                                      l.stat === 'Replied / Booked' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-blue-500/10 text-blue-400'
                                    }`}>
                                      {l.stat}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800/80">
                        <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-emerald-400">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                          SMTP Live Log:
                        </div>
                        <p className="text-[11px] text-gray-400 leading-relaxed font-mono">
                          [2026-05-21 11:30] Sent email Pitch_Template_V1 to s.connor@cyberdyne.io. Subject: "Automating support workflows for Cyberdyne..."
                        </p>
                      </div>
                    </div>
                  )}

                  {activePreviewAgent === 'support' && (
                    <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                      <div>
                        <div className="flex items-center gap-3 mb-4">
                          <div className="bg-blue-600/20 text-blue-400 p-2 rounded-lg text-xs font-bold">WHATSAPP</div>
                          <span className="text-xs text-gray-400 font-medium">Customer Support Sandbox</span>
                          <span className="ml-auto text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded font-bold uppercase">Solved By AI</span>
                        </div>

                        {/* WhatsApp Bubble Layout */}
                        <div className="space-y-3 p-3 bg-gray-950/60 rounded-2xl border border-gray-800 shadow-inner">
                          {/* Client Message */}
                          <div className="flex justify-start">
                            <div className="bg-gray-800 text-gray-100 rounded-2xl rounded-tl-none px-3.5 py-2 max-w-[80%] text-xs shadow-md">
                              <p className="font-semibold text-gray-400 mb-0.5">Customer (+1 555-0199)</p>
                              Do you guys offer international shipping? If yes, what are the shipping rates?
                            </div>
                          </div>

                          {/* Agent Auto Reply */}
                          <div className="flex justify-end">
                            <div className="bg-blue-600 text-white rounded-2xl rounded-tr-none px-3.5 py-2 max-w-[80%] text-xs shadow-md border border-blue-500">
                              <div className="flex items-center gap-1.5 mb-1 text-[10px] text-blue-200 font-bold">
                                <Zap size={10} className="fill-blue-200" /> AI Auto-Replied
                              </div>
                              Yes, we offer worldwide shipping to over 150 countries! 🌍 Shipping rates depend on your location and order size, which are automatically calculated at checkout. Feel free to enter your address during checkout to view the exact rate. Let me know if you have other questions!
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="text-[11px] text-blue-300/80 bg-blue-500/5 border border-blue-500/10 p-3 rounded-lg flex items-start gap-2">
                        <Clock size={14} className="mt-0.5 flex-shrink-0" />
                        <p>
                          <strong>Contextual Intelligence:</strong> The AI Agent read your uploaded `Pricing & Shipping Guidelines` PDF in the Knowledge Base to craft this accurate response without any manual code.
                        </p>
                      </div>
                    </div>
                  )}

                  {activePreviewAgent === 'hr' && (
                    <div className="flex-1 flex flex-col justify-between space-y-4 animate-in fade-in duration-300">
                      <div>
                        <div className="flex items-center gap-3 mb-4">
                          <div className="bg-amber-600/20 text-amber-400 p-2 rounded-lg text-xs font-bold">RECRUITER</div>
                          <span className="text-xs text-gray-400 font-medium">Job: Sr. Backend Engineer</span>
                          <span className="ml-auto text-[10px] bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded font-bold uppercase">Interview Scheduled</span>
                        </div>

                        {/* Candidate Card */}
                        <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-800 space-y-3">
                          <div className="flex justify-between items-center">
                            <div>
                              <h4 className="font-extrabold text-sm text-white">Sarah Connor</h4>
                              <p className="text-xs text-gray-400">Experience: 5 years Python, Go, PostgreSQL</p>
                            </div>
                            <div className="text-right">
                              <span className="text-lg font-black text-emerald-400 block">96%</span>
                              <span className="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Match Score</span>
                            </div>
                          </div>

                          <div className="text-xs bg-indigo-950/20 border border-indigo-900/30 p-2.5 rounded text-gray-300">
                            <strong>Agent Sourcing Notes:</strong> Candidate has a strong fit for cybersecurity projects and PostgreSQL indexing. Outbound message delivered successfully. Candidate booked an interview.
                          </div>

                          {/* Meeting Link widget */}
                          <div className="flex items-center justify-between bg-violet-600/10 border border-violet-500/20 p-2.5 rounded-lg text-xs">
                            <div className="flex items-center gap-2 text-white">
                              <Calendar size={14} className="text-violet-400" />
                              <span>Interview Scheduled: May 24, 2:00 PM</span>
                            </div>
                            <span className="text-violet-400 font-semibold cursor-not-allowed">Google Meet Link</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-[11px] text-amber-300/80 bg-amber-500/5 border border-amber-500/10 p-3 rounded-lg flex items-center gap-2">
                        <Users size={14} className="flex-shrink-0" />
                        <p>Hunter scans job boards, scores candidates, conducts initial mail screens, and books directly into your calendar.</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Calculator Section */}
          <div className="glass-panel border-violet-500/15 rounded-3xl p-8 shadow-2xl relative overflow-hidden mb-16">
            <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-indigo-600/5 rounded-full blur-[100px] pointer-events-none" />
            
            <div className="max-w-3xl mx-auto text-center mb-8">
              <h2 className="text-3xl font-extrabold text-white tracking-tight">AI Workforce Savings Calculator</h2>
              <p className="text-gray-400 mt-2">Adjust the sliders to estimate the direct hours and capital saved by using NexusOS.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              {/* Sliders Box */}
              <div className="space-y-6">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm font-semibold">
                    <label className="text-gray-300">Daily Tasks Automated</label>
                    <span className="text-violet-400 font-bold">{tasksPerDay} tasks/day</span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="300"
                    step="5"
                    value={tasksPerDay}
                    onChange={e => setTasksPerDay(parseInt(e.target.value))}
                    className="w-full h-2 rounded-lg bg-gray-800 appearance-none cursor-pointer slider-thumb accent-violet-500"
                  />
                  <div className="flex justify-between text-[10px] text-gray-500">
                    <span>5 Tasks</span>
                    <span>300 Tasks</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm font-semibold">
                    <label className="text-gray-300">Target Hourly Rate</label>
                    <span className="text-violet-400 font-bold">${hourlyRate}/hour</span>
                  </div>
                  <input
                    type="range"
                    min="15"
                    max="120"
                    step="5"
                    value={hourlyRate}
                    onChange={e => setHourlyRate(parseInt(e.target.value))}
                    className="w-full h-2 rounded-lg bg-gray-800 appearance-none cursor-pointer slider-thumb accent-violet-500"
                  />
                  <div className="flex justify-between text-[10px] text-gray-500">
                    <span>$15/hr</span>
                    <span>$120/hr</span>
                  </div>
                </div>
              </div>

              {/* Outputs Box */}
              <div className="grid grid-cols-2 gap-4 bg-[rgba(255,255,255,0.01)] border border-gray-800 p-6 rounded-2xl">
                <div className="text-center p-4 border border-gray-800/40 rounded-xl bg-gray-950/20 shadow-inner">
                  <Clock size={24} className="text-violet-400 mx-auto mb-2" />
                  <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Hours Saved / Mo</span>
                  <div className="text-3xl font-black text-white mt-1">{hoursSaved} hrs</div>
                  <span className="text-[9px] text-gray-400 block mt-1">Based on 0.75h/task</span>
                </div>
                <div className="text-center p-4 border border-gray-800/40 rounded-xl bg-gray-950/20 shadow-inner">
                  <DollarSign size={24} className="text-emerald-400 mx-auto mb-2" />
                  <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Savings Value / Mo</span>
                  <div className="text-3xl font-black text-emerald-400 mt-1">${moneySaved.toLocaleString()}</div>
                  <span className="text-[9px] text-emerald-500/80 block mt-1 font-semibold">Net ROI: 99.8%</span>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // LOGIN VIEW
  if (appState === 'login') {
    return (
      <div className="min-h-screen bg-[#030014] text-[#f4f4f7] relative overflow-hidden font-sans flex flex-col justify-center items-center px-4">
        {/* Ambient background glows */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[rgba(139,92,246,0.12)] rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[rgba(59,130,246,0.12)] rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

        <Card className="w-full max-w-md glass-panel border-violet-500/20 shadow-2xl relative overflow-hidden rounded-3xl">
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
          <CardHeader className="space-y-2 pt-8">
            <div className="flex justify-center mb-2">
              <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-violet-500/20">
                <Zap className="text-white fill-white h-5 w-5 animate-pulse" />
              </div>
            </div>
            <CardTitle className="text-2xl text-center text-white font-extrabold tracking-tight">Welcome back</CardTitle>
            <CardDescription className="text-center text-gray-400 text-xs">Enter your credentials to access your autonomous workspace.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pb-8">
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Email Address</label>
                <Input 
                  placeholder="name@company.com" 
                  type="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)} 
                  required 
                  className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Password</label>
                <Input 
                  placeholder="••••••••" 
                  type="password" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  required 
                  className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20"
                />
              </div>
              <button 
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold py-3 rounded-xl shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 transition-all hover:scale-[1.02] active:scale-95 mt-2 cursor-pointer flex justify-center items-center" 
                type="submit"
              >
                Log In
              </button>
              <div className="text-center text-xs mt-4 text-gray-400">
                Don't have an account? <span className="text-violet-400 hover:text-violet-300 cursor-pointer font-bold transition-colors" onClick={() => setAppState('signup')}>Sign up</span>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // SIGNUP VIEW
  if (appState === 'signup') {
    return (
      <div className="min-h-screen bg-[#030014] text-[#f4f4f7] relative overflow-hidden font-sans flex flex-col justify-center items-center px-4">
        {/* Ambient background glows */}
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[rgba(139,92,246,0.12)] rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[rgba(59,130,246,0.12)] rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

        <Card className="w-full max-w-md glass-panel border-violet-500/20 shadow-2xl relative overflow-hidden rounded-3xl">
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
          <CardHeader className="space-y-2 pt-8">
            <div className="flex justify-center mb-2">
              <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-violet-500/20">
                <Zap className="text-white fill-white h-5 w-5 animate-pulse" />
              </div>
            </div>
            <CardTitle className="text-2xl text-center text-white font-extrabold tracking-tight">Create your workspace</CardTitle>
            <CardDescription className="text-center text-gray-400 text-xs">Deploy your autonomous workforce in seconds.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pb-8">
            <form onSubmit={handleSignup} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Company Name</label>
                <Input 
                  placeholder="e.g. Acme Corp" 
                  value={companyName} 
                  onChange={e => setCompanyName(e.target.value)} 
                  required 
                  className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Email Address</label>
                <Input 
                  placeholder="name@company.com" 
                  type="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)} 
                  required 
                  className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-gray-400">Password</label>
                <Input 
                  placeholder="••••••••" 
                  type="password" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  required 
                  className="bg-gray-900/60 border-gray-800 text-white rounded-xl focus:border-violet-500 focus:ring-violet-500/20"
                />
              </div>
              <button 
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold py-3 rounded-xl shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 transition-all hover:scale-[1.02] active:scale-95 mt-2 cursor-pointer flex justify-center items-center" 
                type="submit"
              >
                Sign Up
              </button>
              <div className="text-center text-xs mt-4 text-gray-400">
                Already have an account? <span className="text-violet-400 hover:text-violet-300 cursor-pointer font-bold transition-colors" onClick={() => setAppState('login')}>Log in</span>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // MAIN APP DASHBOARD VIEW
  return (
    <div className="flex h-screen bg-[#030014] text-[#f4f4f7] font-sans relative overflow-hidden">
      {/* Ambient background glows for App Workspace */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[rgba(139,92,246,0.08)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-[rgba(59,130,246,0.08)] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-[30%] left-[20%] w-[400px] h-[400px] bg-[rgba(16,185,129,0.03)] rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:4rem_4rem] pointer-events-none" />

      {/* Sidebar */}
      <div className="w-66 glass-panel border-r border-[rgba(255,255,255,0.06)] flex flex-col p-5 relative z-20">
        <div className="flex items-center gap-2.5 mb-8 px-2 text-xl font-black text-white">
          <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-1.5 rounded-lg shadow-lg shadow-violet-500/20">
            <Zap className="text-white fill-white h-4.5 w-4.5 animate-pulse" />
          </div>
          <span>Nexus<span className="text-violet-400">OS</span></span>
        </div>
        <nav className="flex flex-col gap-1.5 flex-1">
          {[
            { id: 'dashboard', name: 'Operating Dashboard', icon: <BarChart3 size={18} />, color: 'hover:text-violet-400 active-glow-violet' },
            { id: 'campaigns', name: 'Campaign Planner', icon: <Calendar size={18} />, color: 'hover:text-indigo-400 active-glow-indigo' },
            { id: 'support', name: 'Customer Support', icon: <MessageSquare size={18} />, color: 'hover:text-blue-400 active-glow-blue' },
            { id: 'coordination', name: 'Agent Boardroom', icon: <Users size={18} />, color: 'hover:text-amber-400 active-glow-amber' },
            { id: 'orchestrator', name: 'Orchestrator AI', icon: <Activity size={18} />, color: 'hover:text-purple-400 active-glow-purple' },
            { id: 'teams', name: 'AI Teams', icon: <Users size={18} />, color: 'hover:text-emerald-400 active-glow-emerald' },
            { id: 'marketplace', name: 'App Marketplace', icon: <Briefcase size={18} />, color: 'hover:text-pink-400 active-glow-pink' },
            { id: 'hr', name: 'Hiring & HR', icon: <Briefcase size={18} />, color: 'hover:text-amber-400 active-glow-amber' },
            { id: 'ai_optimization', name: 'AI Cost Control', icon: <DollarSign size={18} />, color: 'hover:text-emerald-400 active-glow-emerald' },
          ].map((item) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border border-transparent ${
                  isActive
                    ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white shadow-lg'
                    : 'text-gray-400 hover:bg-[rgba(255,255,255,0.02)] hover:border-[rgba(255,255,255,0.04)]'
                } ${item.color}`}
              >
                {item.icon}
                <span>{item.name}</span>
              </button>
            );
          })}
          
          <button
            onClick={() => setActiveView('instructions')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border border-transparent mt-auto ${
              activeView === 'instructions'
                ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.1)] text-white shadow-lg'
                : 'text-gray-400 hover:bg-[rgba(255,255,255,0.02)] hover:border-[rgba(255,255,255,0.04)]'
            }`}
          >
            <BookOpen size={18} />
            <span>Setup & API Guide</span>
          </button>
          
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 border border-transparent text-rose-400 hover:bg-rose-950/20 hover:border-rose-900/30 mt-2"
          >
            <LogOut size={18} />
            <span>Log out</span>
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative z-10">
        {/* Header (Settings & KB) */}
        <header className="h-16 bg-transparent border-b border-[rgba(255,255,255,0.06)] flex items-center justify-end px-8 gap-4 relative z-20">
          <Dialog open={isKeyDialogOpen} onOpenChange={setIsKeyDialogOpen}>
            <DialogTrigger render={<Button variant="outline" className="bg-transparent border-gray-700/60 hover:bg-gray-800 text-gray-300" />}>API Settings</DialogTrigger>
            <DialogContent className="glass-panel border-violet-500/20 text-white rounded-3xl">
              <DialogHeader><DialogTitle className="text-white font-extrabold text-xl">Configure API Keys</DialogTitle></DialogHeader>
              <div className="flex flex-col gap-4 py-4">
                <p className="text-xs text-gray-400">Select a provider and enter your API key. You can also just paste keys directly into the Orchestrator chat!</p>
                <Select value={keyProvider} onValueChange={(val) => val && setKeyProvider(val)}>
                  <SelectTrigger className="bg-gray-900/60 border-gray-800 text-white"><SelectValue placeholder="Select Provider" /></SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-800 text-white">
                    <SelectItem value="anthropic">Claude (Anthropic)</SelectItem>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="gemini">Google Gemini</SelectItem>
                    <SelectItem value="grok">Grok</SelectItem>
                    <SelectItem value="meta">Meta Graph (Instagram/FB)</SelectItem>
                    <SelectItem value="linkedin">LinkedIn</SelectItem>
                    <SelectItem value="apollo">Apollo.io</SelectItem>
                    <SelectItem value="hunter">Hunter.io</SelectItem>
                    <SelectItem value="google_places">Google Places API</SelectItem>
                    <SelectItem value="gmail">Gmail API</SelectItem>
                    <SelectItem value="whatsapp">WhatsApp Business</SelectItem>
                    <SelectItem value="google_calendar">Google Calendar API</SelectItem>
                    <SelectItem value="smtp">SMTP Credentials (outgoing mail)</SelectItem>
                  </SelectContent>
                </Select>
                <Input 
                  type={keyProvider === 'smtp' ? 'text' : 'password'} 
                  placeholder={keyProvider === 'smtp' ? 'smtp://username:password@smtp.mailtrap.io:2525' : 'Enter API Key / Token'} 
                  value={keyValue} 
                  onChange={e => setKeyValue(e.target.value)} 
                  className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20"
                />
                <Button onClick={saveApiKey} className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold">Save Configuration</Button>
              </div>
            </DialogContent>
          </Dialog>

           <Dialog>
            <DialogTrigger render={<Button variant="secondary" className="bg-[rgba(255,255,255,0.04)] border border-gray-700/60 hover:bg-gray-800 text-gray-300" />}>Knowledge Base</DialogTrigger>
            <DialogContent className="max-w-2xl glass-panel border-violet-500/20 text-white rounded-3xl">
              <DialogHeader><DialogTitle className="text-white font-extrabold text-xl">Company Knowledge Base</DialogTitle></DialogHeader>
              <div className="flex flex-col gap-4 py-4">
                <div className="flex gap-4">
                  <Select value={kbDept} onValueChange={(val) => val && setKbDept(val)}>
                    <SelectTrigger className="w-[180px] bg-gray-900/60 border-gray-800 text-white"><SelectValue placeholder="Department" /></SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-800 text-white">
                      <SelectItem value="General">General</SelectItem>
                      <SelectItem value="Marketing">Marketing</SelectItem>
                      <SelectItem value="Sales">Sales</SelectItem>
                      <SelectItem value="HR">HR</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={kbType} onValueChange={(val) => val && setKbType(val)}>
                    <SelectTrigger className="w-[180px] bg-gray-900/60 border-gray-800 text-white"><SelectValue placeholder="Doc Type" /></SelectTrigger>
                    <SelectContent className="bg-gray-900 border-gray-800 text-white">
                      <SelectItem value="Brand Guidelines">Brand</SelectItem>
                      <SelectItem value="FAQ">FAQ</SelectItem>
                      <SelectItem value="Pricing">Pricing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Textarea 
                  placeholder="Paste context here..." 
                  value={kbContent} 
                  onChange={e => setKbContent(e.target.value)} 
                  className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20 min-h-[120px]"
                />
                <Button onClick={addKnowledge} className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold">Add to Knowledge Base</Button>
                <div className="mt-2 text-xs text-gray-400">{knowledge.length} documents stored.</div>
              </div>
            </DialogContent>
          </Dialog>
        </header>

        {/* Scrollable View Area */}
        <main className="flex-1 overflow-auto p-8 relative z-10">
          
          {/* VIEW: DASHBOARD */}
          {activeView === 'dashboard' && (
            <div className="space-y-8 max-w-7xl mx-auto">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight">AI Operating Dashboard</h1>
                  <p className="text-gray-400 mt-1">Live metrics from your autonomous AI workforce.</p>
                </div>
                <div className="flex items-center gap-2 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.06)] px-4 py-2 rounded-xl text-xs text-gray-400 font-semibold shadow-inner">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>All virtual employees sync'd</span>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
                {[
                  { title: "Revenue Impact", val: `$${(metrics.revenue_impact || 0).toLocaleString()}`, desc: "Direct sales attributed", icon: <DollarSign className="h-4 w-4 text-emerald-400" />, glow: "glow-sales" },
                  { title: "Leads Sourced", val: metrics.leads_generated || 0, desc: "B2B sales prospects found", icon: <Users className="h-4 w-4 text-emerald-400" />, glow: "glow-sales" },
                  { title: "Content Published", val: metrics.posts_published || 0, desc: "Social media posts live", icon: <Activity className="h-4 w-4 text-violet-400" />, glow: "glow-marketing" },
                  { title: "Candidates Sourced", val: metrics.candidates_sourced || 0, desc: "HR applicants indexed", icon: <Briefcase className="h-4 w-4 text-amber-400" />, glow: "glow-hr" },
                  { title: "Interviews Booked", val: metrics.interviews_scheduled || 0, desc: "Google Meet calls scheduled", icon: <Calendar className="h-4 w-4 text-amber-400" />, glow: "glow-hr" },
                  { title: "Success Rate", val: `${metrics.automation_success_rate || 99.5}%`, desc: "Autopilot efficiency rate", icon: <BarChart3 className="h-4 w-4 text-pink-400" />, glow: "glow-support" },
                ].map((m, idx) => (
                  <Card key={idx} className={`glass-panel border-transparent ${m.glow} relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl`}>
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-current opacity-80" />
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{m.title}</CardTitle>
                      {m.icon}
                    </CardHeader>
                    <CardContent className="space-y-1">
                      <div className="text-3xl font-black text-white">{m.val}</div>
                      <p className="text-[10px] text-gray-500 font-medium">{m.desc}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Advanced SVG Chart & Activity Center */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Visual Chart Card */}
                <Card className="lg:col-span-8 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4 border-b border-gray-800 pb-4">
                    <div>
                      <h3 className="font-extrabold text-lg text-white">Daily Automated Tasks</h3>
                      <p className="text-xs text-gray-400">Total automated agent tasks over the last 7 days</p>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                      <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-violet-500" /> Marketing</span>
                      <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Sales</span>
                      <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> Support</span>
                    </div>
                  </div>

                  <div className="relative w-full h-44 mt-2 flex items-end">
                    <svg viewBox="0 0 500 150" className="w-full h-full overflow-visible" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.35" />
                          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>
                      {/* Grid Lines */}
                      <line x1="0" y1="30" x2="500" y2="30" stroke="rgba(255,255,255,0.03)" strokeDasharray="4 4" />
                      <line x1="0" y1="75" x2="500" y2="75" stroke="rgba(255,255,255,0.03)" strokeDasharray="4 4" />
                      <line x1="0" y1="120" x2="500" y2="120" stroke="rgba(255,255,255,0.03)" strokeDasharray="4 4" />
                      
                      {/* Area Path */}
                      <path d="M0,150 L0,120 L80,95 L160,115 L240,70 L320,45 L400,80 L500,30 L500,150 Z" fill="url(#chartGradient)" />
                      {/* Stroke Path */}
                      <path d="M0,120 L80,95 L160,115 L240,70 L320,45 L400,80 L500,30" fill="none" stroke="#8b5cf6" strokeWidth="2.5" />
                      
                      {/* Data Dots */}
                      <circle cx="80" cy="95" r="3.5" fill="#8b5cf6" stroke="#ffffff" strokeWidth="1" />
                      <circle cx="160" cy="115" r="3.5" fill="#8b5cf6" stroke="#ffffff" strokeWidth="1" />
                      <circle cx="240" cy="70" r="3.5" fill="#8b5cf6" stroke="#ffffff" strokeWidth="1" />
                      <circle cx="320" cy="45" r="3.5" fill="#8b5cf6" stroke="#ffffff" strokeWidth="1" />
                      <circle cx="400" cy="80" r="3.5" fill="#8b5cf6" stroke="#ffffff" strokeWidth="1" />
                      <circle cx="500" cy="30" r="3.5" fill="#8b5cf6" stroke="#ffffff" strokeWidth="1" />
                    </svg>
                  </div>
                  
                  <div className="flex justify-between text-[10px] text-gray-500 font-bold tracking-wider uppercase mt-4 pt-3 border-t border-gray-800/60">
                    <span>Mon</span>
                    <span>Tue</span>
                    <span>Wed</span>
                    <span>Thu</span>
                    <span>Fri</span>
                    <span>Sat</span>
                    <span>Today</span>
                  </div>
                </Card>

                {/* Developer Terminal Activity Log */}
                <Card className="lg:col-span-4 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col h-full min-h-[280px]">
                  <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-3">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                    </div>
                    <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider font-mono">Live Developer Console</span>
                  </div>
                  <div className="flex-1 overflow-y-auto space-y-2.5 font-mono text-[11px] leading-relaxed text-gray-300 pr-1 max-h-[180px]">
                    {timeline.slice(0, 8).map((log) => (
                      <div key={log.id} className="text-gray-400">
                        <span className="text-violet-400 font-semibold">[{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>{" "}
                        <span className="text-emerald-400">({log.agent_name})</span>{" "}
                        <span className="text-white font-medium">{log.action}:</span> {log.description}
                      </div>
                    ))}
                    {timeline.length === 0 && (
                      <div className="text-gray-500 italic">Listening for system triggers...</div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-gray-800 text-[10px] text-violet-400 font-bold font-mono">
                    <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-ping" />
                    <span>SYSTEM ONLINE. LOGS BINDING OK.</span>
                    <span className="inline-block w-1.5 h-3 bg-violet-400 animate-pulse" />
                  </div>
                </Card>
              </div>

              {/* Approvals Pipeline Widget */}
              <Card className="glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden">
                <div className="flex items-center justify-between pb-4 border-b border-gray-800 mb-6">
                  <div>
                    <h3 className="font-extrabold text-xl text-white">Pending Approvals</h3>
                    <p className="text-xs text-gray-400">Verify content and leads generated by your AI workforce before publishing.</p>
                  </div>
                  <div className="flex items-center gap-1.5 bg-amber-500/10 text-amber-400 text-[10px] font-bold px-3 py-1 rounded-full border border-amber-500/20 uppercase tracking-wider">
                    {((queue.posts?.length || 0) + (queue.leads?.length || 0))} Pending Approval
                  </div>
                </div>

                <Tabs defaultValue="marketing" className="w-full">
                  <TabsList className="grid w-full max-w-[400px] grid-cols-2 bg-gray-950/60 p-1 border border-gray-800 rounded-xl mb-6">
                    <TabsTrigger value="marketing" className="rounded-lg text-xs font-semibold text-gray-400 data-[state=active]:bg-violet-600 data-[state=active]:text-white transition-all">Marketing Queue ({queue.posts?.length || 0})</TabsTrigger>
                    <TabsTrigger value="sales" className="rounded-lg text-xs font-semibold text-gray-400 data-[state=active]:bg-emerald-600 data-[state=active]:text-white transition-all">Sales Leads ({queue.leads?.length || 0})</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="marketing">
                    <div className="border border-gray-800 rounded-2xl overflow-hidden bg-[rgba(0,0,0,0.15)] shadow-inner">
                      <Table>
                        <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                          <TableRow className="border-gray-800 hover:bg-transparent">
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Platform & Day</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Content Preview</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4 text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-gray-800">
                          {(!queue.posts || queue.posts.length === 0) && (
                            <TableRow className="hover:bg-transparent">
                              <TableCell colSpan={3} className="text-center py-12 text-sm text-gray-500 font-medium">
                                Perfect! No marketing posts pending approval.
                              </TableCell>
                            </TableRow>
                          )}
                          {queue.posts?.map((post) => (
                            <TableRow key={post.id} className="border-gray-800 hover:bg-gray-900/20">
                              <TableCell className="p-4 whitespace-nowrap">
                                <div className="flex flex-col">
                                  <span className="text-xs font-extrabold uppercase text-violet-400">{post.platform}</span>
                                  <span className="text-[10px] text-gray-500 font-bold mt-0.5">Day {post.day}</span>
                                </div>
                              </TableCell>
                              <TableCell className="p-4">
                                <p className="max-w-xl text-xs text-gray-300 line-clamp-2 leading-relaxed">{post.content}</p>
                              </TableCell>
                              <TableCell className="p-4 text-right">
                                <div className="flex gap-2 justify-end">
                                  <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => handleRejectPost(post.id)}
                                    className="h-8 text-xs font-semibold text-rose-400 border-rose-900/30 hover:bg-rose-950/20"
                                  >
                                    Reject
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    onClick={() => handleApprovePost(post.id)}
                                    className="h-8 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                                  >
                                    Approve
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="sales">
                    <div className="border border-gray-800 rounded-2xl overflow-hidden bg-[rgba(0,0,0,0.15)] shadow-inner">
                      <Table>
                        <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                          <TableRow className="border-gray-800 hover:bg-transparent">
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Lead Name</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Company</TableHead>
                            <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Source Channel</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody className="divide-y divide-gray-800">
                          {(!queue.leads || queue.leads.length === 0) && (
                            <TableRow className="hover:bg-transparent">
                              <TableCell colSpan={3} className="text-center py-12 text-sm text-gray-500 font-medium">
                                No sales leads to display. Run outbound sourcing in Orchestrator.
                              </TableCell>
                            </TableRow>
                          )}
                          {queue.leads?.map((lead) => (
                            <TableRow key={lead.id} className="border-gray-800 hover:bg-gray-900/20">
                              <TableCell className="p-4 font-bold text-white text-xs">{lead.name}</TableCell>
                              <TableCell className="p-4 text-xs text-gray-300">{lead.company}</TableCell>
                              <TableCell className="p-4">
                                <span className="text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded uppercase tracking-wider">
                                  {lead.source}
                                </span>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </TabsContent>
                </Tabs>
              </Card>

              {/* Installed Workflows & Integrations Panel */}
              <div className="space-y-6 pt-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h3 className="font-extrabold text-2xl text-white">Active Workflows & Automations</h3>
                    <p className="text-xs text-gray-400 mt-1">Manage deployed workflow packs operating autonomously.</p>
                  </div>
                  {apps.length > 0 && (
                    <span className="text-[10px] uppercase font-extrabold tracking-widest text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
                      {apps.length} Operational Packs
                    </span>
                  )}
                </div>
                
                {apps.length === 0 ? (
                  <Card className="glass-panel border-dashed border-gray-800 rounded-3xl p-8 text-center space-y-4 shadow-xl">
                    <div className="text-5xl">🔌</div>
                    <div className="max-w-md mx-auto space-y-2">
                      <h4 className="text-sm font-bold text-white">No active industry workflows installed</h4>
                      <p className="text-xs text-gray-450 leading-relaxed">
                        NexusOS can deploy specialized, pre-configured packages for local growth, SaaS outbound sales, e-commerce automation, medical scheduling, and more. Visit the App Marketplace to activate.
                      </p>
                    </div>
                    <Button 
                      onClick={() => setActiveView('marketplace')}
                      className="bg-violet-600 hover:bg-violet-500 text-white font-bold h-9 px-6 rounded-xl shadow-lg shadow-violet-500/20 hover:scale-105 active:scale-95 transition-all text-xs"
                    >
                      Browse App Marketplace
                    </Button>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {apps.map((app) => {
                      const matchedPack = marketplacePacks.find(p => p.name === app.app_name);
                      return (
                        <Card key={app.id} className="glass-panel border-transparent hover:border-violet-500/30 transition-all duration-300 rounded-3xl p-6 shadow-2xl relative flex flex-col justify-between overflow-hidden">
                          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
                          <div className="space-y-4">
                            <div className="flex items-center justify-between">
                              <span className="text-[9px] uppercase font-black tracking-widest text-violet-400 bg-violet-500/10 px-2.5 py-1 rounded-full border border-violet-500/20">
                                {matchedPack?.category || "Integration"}
                              </span>
                              <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-bold uppercase tracking-wider bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 animate-pulse">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-450" />
                                <span>Autopilot</span>
                              </div>
                            </div>
                            
                            <div className="flex items-center gap-3">
                              <div className="text-3xl p-2 bg-violet-500/10 rounded-2xl border border-violet-500/20 flex items-center justify-center h-12 w-12">
                                {matchedPack?.icon || "⚙️"}
                              </div>
                              <div>
                                <h4 className="text-base text-white font-extrabold">{app.app_name}</h4>
                                <span className="text-[10px] text-gray-500 font-bold">{matchedPack?.timeSaved ? `Saves ${matchedPack.timeSaved}` : "Active"}</span>
                              </div>
                            </div>

                            <p className="text-gray-300 text-xs leading-relaxed">{matchedPack?.desc || "Custom integration workflow."}</p>

                            {matchedPack?.features && (
                              <div className="space-y-2 pt-2 border-t border-gray-800/60">
                                <span className="text-[10px] font-bold uppercase text-gray-500 tracking-wider">Automations active:</span>
                                <ul className="space-y-1">
                                  {matchedPack.features.map((feat, idx) => (
                                    <li key={idx} className="text-[11px] text-gray-400 flex items-center gap-1.5 leading-tight">
                                      <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
                                      <span>{feat}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>

                          <div className="pt-4 mt-4 border-t border-gray-800/60">
                            <Button 
                              onClick={() => uninstallApp(app.app_name)}
                              variant="outline"
                              className="w-full text-xs font-semibold text-rose-400 border-rose-900/30 hover:bg-rose-950/20 h-9 rounded-xl transition-all"
                            >
                              Deactivate Pack
                            </Button>
                          </div>
                        </Card>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW: CAMPAIGNS (Campaign Planner & Timeline) */}
          {activeView === 'campaigns' && (
            <>
            <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <Calendar className="text-violet-400 h-8 w-8" /> Campaign Planner & Review Board
                  </h1>
                  <p className="text-gray-400 mt-1">Autonomous social media campaigns with high-impact text, images, and videos.</p>
                </div>
                {campaignPosts.length > 0 && (
                  <Button 
                    onClick={handleApproveAll} 
                    className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/20 hover:scale-[1.02] active:scale-95 transition-all"
                  >
                    Approve & Schedule All ({campaignPosts.filter(p => p.approval_status === 'pending').length} pending)
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Campaign Generator Form */}
                <div className="lg:col-span-1 space-y-6">
                  <Card className="glass-panel border-transparent glow-marketing rounded-3xl overflow-hidden shadow-2xl relative">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
                    <CardHeader>
                      <CardTitle className="text-xl text-white font-extrabold tracking-tight">Generate New Campaign</CardTitle>
                      <CardDescription className="text-gray-400 text-xs mt-1">Enter details and AI will generate optimized content and media files for 30 days.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex flex-col gap-2">
                        <label className="text-xs font-semibold text-gray-400">Company Website, Description or Campaign Idea</label>
                        <Textarea
                          placeholder="e.g. 'Generate marketing posts for BlueBottle Cafe. Highlight our organic roast and friendly workspace vibes.'"
                          className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20 rounded-xl min-h-[120px] text-sm"
                          value={campaignTopic}
                          onChange={e => setCampaignTopic(e.target.value)}
                        />
                      </div>

                      <div className="flex gap-4">
                        <div className="flex-1 flex flex-col gap-2">
                          <label className="text-xs font-semibold text-gray-400">Duration (Days)</label>
                          <Input
                            type="number"
                            min={1}
                            max={60}
                            value={campaignDays}
                            onChange={e => setCampaignDays(parseInt(e.target.value) || 30)}
                            className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20 rounded-xl h-10"
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label className="text-xs font-semibold text-gray-400 block">Target Platforms</label>
                        <div className="flex flex-wrap gap-2">
                          {['linkedin', 'instagram', 'facebook'].map(p => {
                            const isSelected = campaignPlatforms.includes(p);
                            return (
                              <button
                                key={p}
                                type="button"
                                onClick={() => {
                                  if (isSelected) {
                                    setCampaignPlatforms(campaignPlatforms.filter(x => x !== p));
                                  } else {
                                    setCampaignPlatforms([...campaignPlatforms, p]);
                                  }
                                }}
                                className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all ${
                                  isSelected 
                                    ? 'bg-violet-600 border-violet-500 text-white shadow-lg shadow-violet-500/25 scale-[1.02]' 
                                    : 'bg-gray-900/40 border-gray-800 text-gray-400 hover:bg-gray-800 hover:text-white'
                                }`}
                              >
                                {p.toUpperCase()}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div className="border-t border-gray-800 pt-4 space-y-3">
                        <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">AI Configuration</h4>
                        
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] font-semibold text-gray-400">Text Copywriter Model</label>
                          <Select value={textProvider} onValueChange={(val) => val && setTextProvider(val)}>
                            <SelectTrigger className="h-9 bg-gray-900/60 border-gray-800 text-white rounded-xl"><SelectValue /></SelectTrigger>
                            <SelectContent className="bg-gray-900 border-gray-800 text-white">
                              <SelectItem value="gemini">Google Gemini 1.5 Flash (Default)</SelectItem>
                              <SelectItem value="openai">OpenAI GPT-4o</SelectItem>
                              <SelectItem value="anthropic">Claude 3.5 Sonnet</SelectItem>
                              <SelectItem value="grok">xAI Grok-2</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="flex items-center justify-between pt-1">
                          <div className="flex flex-col">
                            <span className="text-xs font-semibold text-gray-300">Generate Images</span>
                            <span className="text-[10px] text-gray-500">Create custom contextual image graphics</span>
                          </div>
                          <input 
                            type="checkbox" 
                            checked={generateImages} 
                            onChange={e => setGenerateImages(e.target.checked)}
                            className="h-4 w-4 rounded border-gray-800 bg-gray-950 text-violet-600 focus:ring-violet-500/20 focus:ring-offset-gray-950"
                          />
                        </div>

                        {generateImages && (
                          <div className="flex flex-col gap-1 pl-4 border-l-2 border-violet-500/30">
                            <label className="text-[10px] font-semibold text-gray-400">Image Generation Model</label>
                            <Select value={imageProvider} onValueChange={(val) => val && setImageProvider(val)}>
                              <SelectTrigger className="h-8 bg-gray-900/60 border-gray-800 text-white text-xs rounded-xl"><SelectValue /></SelectTrigger>
                              <SelectContent className="bg-gray-900 border-gray-800 text-white">
                                <SelectItem value="openai">OpenAI DALL-E 3 (Recommended)</SelectItem>
                                <SelectItem value="gemini">Google Imagen 4 (Via Gemini)</SelectItem>
                                <SelectItem value="stability">Stability AI SDXL</SelectItem>
                                <SelectItem value="grok">xAI Grok-2 Image Gen</SelectItem>
                                <SelectItem value="anthropic">Anthropic Claude (via DALL-E 3)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        )}

                        <div className="flex items-center justify-between pt-1">
                          <div className="flex flex-col">
                            <span className="text-xs font-semibold text-gray-300">Generate Videos</span>
                            <span className="text-[10px] text-gray-500">Create dynamic looping videos (every 3 days)</span>
                          </div>
                          <input 
                            type="checkbox" 
                            checked={generateVideos} 
                            onChange={e => setGenerateVideos(e.target.checked)}
                            className="h-4 w-4 rounded border-gray-800 bg-gray-950 text-violet-600 focus:ring-violet-500/20 focus:ring-offset-gray-950"
                          />
                        </div>

                        {generateVideos && (
                          <div className="flex flex-col gap-1 pl-4 border-l-2 border-violet-500/30">
                            <label className="text-[10px] font-semibold text-gray-400">Video Generation Model</label>
                            <Select value={videoProvider} onValueChange={(val) => val && setVideoProvider(val)}>
                              <SelectTrigger className="h-8 bg-gray-900/60 border-gray-800 text-white text-xs rounded-xl"><SelectValue /></SelectTrigger>
                              <SelectContent className="bg-gray-900 border-gray-800 text-white">
                                <SelectItem value="pika">Pika AI (Recommended)</SelectItem>
                                <SelectItem value="stable_diffusion">Stable Diffusion Video</SelectItem>
                                <SelectItem value="gemini">Google Veo (Via Gemini Mock)</SelectItem>
                                <SelectItem value="grok">Grok Video (Mock)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        )}
                      </div>

                      <Button 
                        onClick={handleLaunchCampaign} 
                        disabled={loading || !campaignTopic} 
                        className="w-full h-11 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 transition-all hover:scale-[1.02] active:scale-95 mt-2 disabled:opacity-50 disabled:scale-100 disabled:shadow-none"
                      >
                        {loading ? 'Initializing Pipeline...' : 'Generate 30-Day Campaign'}
                      </Button>
                    </CardContent>
                  </Card>
                </div>

                {/* Interactive 30-Day Board */}
                <div className="lg:col-span-2 space-y-6">
                  {campaignPosts.length === 0 ? (
                    <Card className="glass-panel border-dashed border-gray-800 p-12 text-center flex flex-col items-center justify-center rounded-3xl min-h-[400px] shadow-2xl">
                      <div className="text-5xl mb-4 animate-bounce">🗓️</div>
                      <h3 className="text-lg font-bold text-white">No active marketing campaign</h3>
                      <p className="text-gray-400 max-w-sm mt-2 text-xs leading-relaxed">Configure your brand topic and launch a campaign. The generated timeline will populate here.</p>
                    </Card>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-h-[750px] overflow-y-auto pr-2 pb-6">
                      {campaignPosts.map(post => {
                        const isEditing = editingPostId === post.id;
                        const hasVideo = !!post.video_url;
                        const hasImage = !!post.image_url;

                        let platformColor = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                        if (post.platform === 'instagram') platformColor = 'bg-pink-500/10 text-pink-400 border-pink-500/20';
                        if (post.platform === 'facebook') platformColor = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';

                        let statusColor = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
                        if (post.approval_status === 'approved') statusColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
                        if (post.approval_status === 'published') statusColor = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                        if (post.approval_status === 'rejected') statusColor = 'bg-rose-500/10 text-rose-400 border-rose-500/20';

                        return (
                          <Card key={post.id} className="glass-panel border-gray-800/80 hover:border-violet-500/40 hover:shadow-violet-500/5 transition-all duration-300 flex flex-col justify-between overflow-hidden rounded-2xl shadow-xl">
                            <div>
                              <div className="flex items-center justify-between border-b border-gray-800 px-4 py-3 bg-gray-950/40">
                                <div className="flex items-center gap-2">
                                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase border ${platformColor}`}>
                                    {post.platform}
                                  </span>
                                  <span className="text-xs font-bold text-gray-400">Day {post.day}</span>
                                </div>
                                <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${statusColor}`}>
                                  {post.approval_status}
                                </span>
                              </div>

                              <div className="p-4 space-y-3">
                                {isEditing ? (
                                  <div className="space-y-3">
                                    <Textarea
                                      className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20 rounded-xl text-sm min-h-[120px]"
                                      value={editingContent}
                                      onChange={e => setEditingContent(e.target.value)}
                                    />
                                    <div>
                                      <label className="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Image URL (Optional)</label>
                                      <Input 
                                        type="text" 
                                        className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20 rounded-xl h-8 text-xs mt-1" 
                                        value={editingImageUrl} 
                                        onChange={e => setEditingImageUrl(e.target.value)}
                                      />
                                    </div>
                                    <div>
                                      <label className="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Video URL (Optional)</label>
                                      <Input 
                                        type="text" 
                                        className="bg-gray-900/60 border-gray-800 text-white focus:border-violet-500 focus:ring-violet-500/20 rounded-xl h-8 text-xs mt-1" 
                                        value={editingVideoUrl} 
                                        onChange={e => setEditingVideoUrl(e.target.value)}
                                      />
                                    </div>
                                  </div>
                                ) : (
                                  <>
                                    <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">
                                      {post.content}
                                    </p>

                                    {/* Visual preview */}
                                    {hasVideo ? (
                                      <div className="relative rounded-xl overflow-hidden border border-gray-800/80 shadow-inner group">
                                        <video
                                          src={post.video_url}
                                          controls
                                          loop
                                          muted
                                          className="w-full h-40 object-cover"
                                        />
                                        <div className="absolute top-2 left-2 bg-black/70 text-white rounded-lg px-2 py-0.5 text-[9px] font-bold flex items-center gap-1.5 border border-white/10 backdrop-blur-md">
                                          <Film size={10} className="text-violet-400" /> AI Video Loop
                                        </div>
                                      </div>
                                    ) : hasImage ? (
                                      post.image_url?.startsWith('error:') ? (
                                        <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 px-4 py-3 flex items-start gap-3">
                                          <div className="text-rose-400 mt-0.5 shrink-0">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                                          </div>
                                          <div>
                                            <p className="text-[10px] font-bold text-rose-400 uppercase tracking-wider mb-0.5">Image Generation Error</p>
                                            <p className="text-[11px] text-rose-300 leading-relaxed">{post.image_url.replace(/^error:/, '')}</p>
                                          </div>
                                        </div>
                                      ) : (
                                        <div className="relative rounded-xl overflow-hidden border border-gray-800/80 shadow-inner group">
                                          <img
                                            src={post.image_url}
                                            alt="Generated graphic preview"
                                            className="w-full h-40 object-cover transition-transform duration-500 group-hover:scale-105"
                                          />
                                          <div className="absolute top-2 left-2 bg-black/70 text-white rounded-lg px-2 py-0.5 text-[9px] font-bold flex items-center gap-1.5 border border-white/10 backdrop-blur-md">
                                            <ImageIcon size={10} className="text-violet-400" /> AI Graphic
                                          </div>
                                        </div>
                                      )
                                    ) : null}
                                  </>
                                )}
                              </div>
                            </div>

                            <div className="border-t border-gray-800 px-4 py-3 bg-gray-950/20 flex gap-2 justify-end">
                              {isEditing ? (
                                <>
                                  <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => setEditingPostId(null)}
                                    className="h-8 px-3 rounded-lg text-xs font-semibold text-gray-400 border-gray-800 hover:bg-gray-800 hover:text-white bg-transparent"
                                  >
                                    Cancel
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    onClick={() => handleSavePostEdit(post.id)}
                                    className="h-8 px-3 rounded-lg text-xs font-semibold bg-violet-600 hover:bg-violet-500 text-white"
                                  >
                                    Save
                                  </Button>
                                </>
                              ) : (
                                <>
                                  <Button 
                                    size="sm" 
                                    variant="outline" 
                                    onClick={() => startEditing(post)}
                                    className="h-8 px-3 rounded-lg text-xs font-semibold text-gray-300 hover:bg-gray-800 hover:text-white border-gray-800 bg-transparent flex items-center gap-1"
                                  >
                                    <Edit2 size={12} /> Edit
                                  </Button>
                                  
                                  {post.approval_status === 'pending' && (
                                    <>
                                      <Button 
                                        size="sm" 
                                        variant="outline" 
                                        onClick={() => handleRejectPost(post.id)}
                                        className="h-8 px-3 rounded-lg text-xs font-semibold text-rose-400 hover:bg-rose-950/20 border-rose-950/50 bg-transparent"
                                      >
                                        Reject
                                      </Button>
                                      <Button 
                                        size="sm" 
                                        onClick={() => handleApprovePost(post.id)}
                                        className="h-8 px-3 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                                      >
                                        Approve
                                      </Button>
                                    </>
                                  )}

                                  {(post.approval_status === 'approved' || post.approval_status === 'scheduled') &&
                                    (post.platform === 'instagram' || post.platform === 'facebook' || post.platform === 'linkedin') && (
                                    <Button
                                      size="sm"
                                      onClick={() => handlePublishNow(post.id)}
                                      disabled={publishingPostId === post.id}
                                      className="h-8 px-3 rounded-lg text-xs font-semibold bg-gradient-to-r from-pink-600 to-rose-600 hover:from-pink-500 hover:to-rose-500 text-white shadow-md shadow-pink-500/20 disabled:opacity-50 flex items-center gap-1.5"
                                    >
                                      {publishingPostId === post.id ? (
                                        <>
                                          <span className="animate-spin inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full" />
                                          Publishing...
                                        </>
                                      ) : (
                                        <>
                                          <Send size={11} />
                                          Publish Now
                                        </>
                                      )}
                                    </Button>
                                  )}

                                  {publishResult && publishingPostId === null && post.id === campaignPosts.find(p => p.approval_status === 'published')?.id && (
                                    <span className={`text-[10px] font-semibold ${
                                      publishResult.success ? 'text-emerald-400' : 'text-rose-400'
                                    }`}>
                                      {publishResult.message}
                                    </span>
                                  )}
                                </>
                              )}
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Meta Credential Modal — shown when Publish Now is clicked without Meta key */}
            {isMetaModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
                <div className="bg-gray-950 border border-gray-800 rounded-3xl shadow-2xl shadow-black/50 w-full max-w-lg overflow-hidden">
                  {/* Header */}
                  <div className="relative px-6 pt-6 pb-4 border-b border-gray-800 bg-gradient-to-r from-pink-950/40 to-rose-950/30">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-pink-500 to-transparent" />
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-pink-600 to-rose-600 flex items-center justify-center shadow-lg shadow-pink-500/30">
                        <span className="text-xl">📲</span>
                      </div>
                      <div>
                        <h2 className="text-white font-extrabold text-lg tracking-tight">Connect Meta to Publish</h2>
                        <p className="text-gray-400 text-xs mt-0.5">Required to post on Instagram &amp; Facebook</p>
                      </div>
                    </div>
                  </div>

                  {/* Body */}
                  <div className="px-6 py-5 space-y-5">
                    <div className="bg-blue-950/30 border border-blue-900/40 rounded-xl p-4 text-xs text-blue-200 leading-relaxed space-y-1">
                      <p className="font-bold text-blue-100 text-sm">How to get your Meta Page Access Token:</p>
                      <ol className="list-decimal pl-4 space-y-1 text-blue-300">
                        <li>Go to <a href="https://developers.facebook.com/tools/explorer/" target="_blank" rel="noreferrer" className="text-pink-400 hover:text-pink-300 underline font-medium">Meta Graph API Explorer</a></li>
                        <li>Select your App &amp; generate a <strong>Page Access Token</strong></li>
                        <li>Add permissions: <code className="bg-blue-950/60 px-1 rounded">instagram_content_publish</code>, <code className="bg-blue-950/60 px-1 rounded">pages_show_list</code>, <code className="bg-blue-950/60 px-1 rounded">instagram_basic</code></li>
                        <li>Use the <strong>Access Token Debugger</strong> to extend it to a 60-day long-lived token</li>
                        <li>Paste the token below</li>
                      </ol>
                    </div>

                    <div className="space-y-2">
                      <label className="text-xs font-bold text-gray-300 uppercase tracking-wider">Meta Page Access Token</label>
                      <input
                        type="password"
                        placeholder="EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx..."
                        value={metaTokenInput}
                        onChange={e => setMetaTokenInput(e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 focus:border-pink-500 focus:ring-1 focus:ring-pink-500/20 rounded-xl px-4 py-3 text-white text-sm outline-none transition-all font-mono placeholder:text-gray-600"
                        autoComplete="off"
                      />
                      <p className="text-[10px] text-gray-500">Your token is encrypted and stored securely. It is never logged or shared.</p>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="px-6 pb-6 flex gap-3 justify-end">
                    <button
                      onClick={() => { setIsMetaModalOpen(false); setPendingPublishPostId(null); setMetaTokenInput(''); }}
                      className="px-4 py-2 rounded-xl text-sm font-semibold text-gray-400 hover:text-white hover:bg-gray-800 transition-all"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveMetaTokenAndPublish}
                      disabled={!metaTokenInput.trim() || savingMetaToken}
                      className="px-5 py-2 rounded-xl text-sm font-bold bg-gradient-to-r from-pink-600 to-rose-600 hover:from-pink-500 hover:to-rose-500 text-white shadow-lg shadow-pink-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                    >
                      {savingMetaToken ? (
                        <>
                          <span className="animate-spin inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full" />
                          Saving &amp; Publishing...
                        </>
                      ) : (
                        'Save Token &amp; Publish Now'
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
            </>
          )}

          {/* VIEW: SUPPORT */}
          {activeView === 'support' && (
            <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-8rem)] flex flex-col animate-in fade-in duration-300">
              {/* Header Panel with Controls & Stats */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <MessageSquare className="text-blue-400 h-8 w-8" /> Customer Support Center
                  </h1>
                  <p className="text-gray-400 mt-1">Manage omnichannel customer conversations and 24/7 AI auto-reply.</p>
                </div>
                
                {/* Auto-Reply Toggles */}
                <Card className="glass-panel border-transparent shadow-lg p-3.5 flex flex-row gap-6 items-center rounded-2xl bg-gray-900/20">
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white">WhatsApp Auto-Reply</span>
                      <span className="text-[10px] text-gray-400">24/7 AI Responder</span>
                    </div>
                    <button
                      onClick={() => {
                        const newSettings = { ...supportSettings, whatsapp_auto_reply: !supportSettings.whatsapp_auto_reply };
                        saveSupportSettings(newSettings);
                      }}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        supportSettings.whatsapp_auto_reply ? 'bg-emerald-600' : 'bg-gray-800'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          supportSettings.whatsapp_auto_reply ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center gap-3 border-l border-gray-800 pl-6">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white">Email Auto-Reply</span>
                      <span className="text-[10px] text-gray-400">24/7 AI Responder</span>
                    </div>
                    <button
                      onClick={() => {
                        const newSettings = { ...supportSettings, email_auto_reply: !supportSettings.email_auto_reply };
                        saveSupportSettings(newSettings);
                      }}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        supportSettings.email_auto_reply ? 'bg-emerald-600' : 'bg-gray-800'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          supportSettings.email_auto_reply ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                </Card>
              </div>

              {/* Split layout */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0 overflow-hidden">
                
                {/* 1. Ticket List - 3 Cols */}
                <Card className="lg:col-span-3 flex flex-col h-full overflow-hidden glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-2 shadow-2xl relative">
                  <div className="px-4 py-3 bg-gray-950/40 border-b border-gray-800 flex justify-between items-center rounded-t-3xl">
                    <h3 className="font-bold text-white text-sm">Tickets</h3>
                    <span className="text-xs bg-gray-900 border border-gray-800 text-gray-400 px-2 py-0.5 rounded-full font-semibold">
                      {tickets.length} total
                    </span>
                  </div>
                  <div className="flex-1 overflow-y-auto p-2 space-y-2">
                    {tickets.length === 0 && (
                      <p className="text-xs text-gray-500 text-center py-10">No support tickets found.</p>
                    )}
                    {tickets.map(t => {
                      const isSelected = selectedTicketId === t.id;
                      let channelIcon = "💬";
                      if (t.channel === "whatsapp") channelIcon = "🟢";
                      if (t.channel === "email") channelIcon = "✉️";

                      let priorityColor = "bg-gray-500/10 text-gray-400 border border-gray-500/20";
                      if (t.priority === "high") priorityColor = "bg-rose-500/10 text-rose-400 border border-rose-500/20";
                      if (t.priority === "medium") priorityColor = "bg-amber-500/10 text-amber-400 border border-amber-500/20";

                      return (
                        <div
                          key={t.id}
                          onClick={() => setSelectedTicketId(t.id)}
                          className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                            isSelected 
                              ? 'bg-blue-600/10 border-blue-500/40 shadow-lg glow-support' 
                              : 'bg-gray-900/20 hover:bg-gray-800/30 border-gray-800/60 text-gray-300'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-[11px] font-bold text-gray-400 flex items-center gap-1">
                              {channelIcon} {t.channel.toUpperCase()}
                            </span>
                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${priorityColor}`}>
                              {t.priority}
                            </span>
                          </div>
                          <h4 className="font-bold text-xs text-white truncate mb-0.5">{t.subject}</h4>
                          <p className="text-[11px] text-gray-400 truncate mb-2">{t.customer_contact}</p>
                          <div className="flex items-center justify-between">
                            <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded-full ${
                              t.status === 'open' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                            }`}>
                              {t.status.toUpperCase()}
                            </span>
                            <span className="text-[9px] text-gray-500 font-semibold">
                              {new Date(t.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>

                {/* 2. Conversation Thread & Reply - 5 Cols */}
                <Card className="lg:col-span-5 flex flex-col h-full overflow-hidden glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-0 shadow-2xl relative">
                  {selectedTicketId ? (
                    <>
                      {/* Thread Header */}
                      <div className="px-4 py-3 bg-gray-950/40 border-b border-gray-800 flex items-center justify-between">
                        <div className="truncate pr-4">
                          <h3 className="font-bold text-white text-sm truncate">
                            {tickets.find(t => t.id === selectedTicketId)?.subject}
                          </h3>
                          <p className="text-[10px] text-gray-400 truncate mt-0.5">
                            {tickets.find(t => t.id === selectedTicketId)?.customer_contact}
                          </p>
                        </div>
                        <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-semibold capitalize">
                          {tickets.find(t => t.id === selectedTicketId)?.status}
                        </span>
                      </div>

                      {/* Chat Messages Area */}
                      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-950/20">
                        {messages.length === 0 && (
                          <p className="text-xs text-gray-500 text-center py-10">No messages in this ticket.</p>
                        )}
                        {messages.map(m => {
                          const isAgent = m.sender === "agent";
                          return (
                            <div
                              key={m.id}
                              className={`flex ${isAgent ? 'justify-end' : 'justify-start'}`}
                            >
                              <div
                                className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed shadow-sm ${
                                  isAgent
                                    ? 'bg-blue-600 text-white rounded-tr-none shadow-lg shadow-blue-500/15'
                                    : 'bg-gray-900/80 border border-gray-800 text-gray-100 rounded-tl-none'
                                  }`}
                              >
                                <p className="whitespace-pre-wrap">{m.content}</p>
                                <span
                                  className={`text-[8px] mt-1 block text-right font-medium ${
                                    isAgent ? 'text-blue-100' : 'text-gray-500'
                                  }`}
                                >
                                  {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Manual Quick Reply Input */}
                      <div className="p-3 border-t border-gray-800 bg-gray-950/40">
                        <div className="flex gap-2">
                          <Textarea
                            placeholder="Type a manual response to send back to the customer..."
                            value={replyText}
                            onChange={e => setReplyText(e.target.value)}
                            className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl min-h-[50px] text-xs resize-none flex-1"
                          />
                          <Button
                            onClick={handleSendManualReply}
                            disabled={sendingReply || !replyText.trim()}
                            className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl h-auto self-stretch px-3 flex flex-col justify-center items-center shadow-lg shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-95"
                          >
                            <Send size={14} className="mb-0.5" />
                            <span className="text-[10px]">Send</span>
                          </Button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-gray-500">
                      <div className="text-4xl mb-2 animate-bounce">💬</div>
                      <h4 className="font-bold text-white text-sm">Select a ticket</h4>
                      <p className="text-xs text-gray-400 max-w-xs mt-1">
                        Click on a conversation from the list to view its message history and reply manually.
                      </p>
                    </div>
                  )}
                </Card>

                {/* 3. Interactive Channel Simulator - 4 Cols */}
                <Card className="lg:col-span-4 flex flex-col h-full glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl shadow-2xl relative glow-support overflow-hidden">
                  <div className="px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white border-b border-gray-800/60">
                    <h3 className="font-bold text-sm flex items-center gap-1.5"><Clock size={14} className="animate-spin" /> Channel Simulator</h3>
                    <p className="text-[10px] text-blue-100 mt-0.5">Test incoming customer messages and observe AI replies.</p>
                  </div>
                  <CardContent className="p-4 space-y-4 flex-1 overflow-y-auto">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-gray-300">Simulated Channel</label>
                      <Select 
                        value={simChannel} 
                        onValueChange={(val: any) => {
                          if (val) {
                            setSimChannel(val);
                            if (val === 'whatsapp') setSimSender('+15553334444');
                            else setSimSender('john.doe@example.com');
                          }
                        }}
                      >
                        <SelectTrigger className="h-9 bg-gray-900/60 border-gray-800 text-white rounded-xl"><SelectValue /></SelectTrigger>
                        <SelectContent className="bg-gray-900 border-gray-800 text-white">
                          <SelectItem value="whatsapp">WhatsApp Message</SelectItem>
                          <SelectItem value="email">Email Inbox</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-gray-300">Customer Contact Info</label>
                      <Input
                        type="text"
                        placeholder={simChannel === 'whatsapp' ? '+15553334444' : 'customer@example.com'}
                        value={simSender}
                        onChange={e => setSimSender(e.target.value)}
                        className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl h-9 text-xs"
                      />
                    </div>

                    {simChannel === 'email' && (
                      <div className="flex flex-col gap-1.5">
                        <label className="text-xs font-bold text-gray-300">Email Subject</label>
                        <Input
                          type="text"
                          placeholder="e.g. Broken links on dashboard"
                          value={simSubject}
                          onChange={e => setSimSubject(e.target.value)}
                          className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl h-9 text-xs"
                        />
                      </div>
                    )}

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-bold text-gray-300">Customer Message Body</label>
                      <Textarea
                        placeholder={
                          simChannel === 'whatsapp' 
                            ? "e.g. 'Hey there, do you guys offer international shipping? if yes, what are the shipping rates?'"
                            : "e.g. 'Hello Support Team, I am having issues logging into my account. It says password incorrect but I reset it already. Can you please help?'"
                        }
                        value={simContent}
                        onChange={e => setSimContent(e.target.value)}
                        className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl min-h-[100px] text-xs resize-none"
                      />
                    </div>

                    <div className="pt-2">
                      <Button
                        onClick={handleSimulateMessage}
                        disabled={simulatingMessage || !simSender.trim() || !simContent.trim()}
                        className="w-full h-10 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100"
                      >
                        {simulatingMessage ? 'Sending Mock Message...' : 'Simulate Customer Message'}
                      </Button>
                    </div>

                    <div className="rounded-xl bg-blue-950/20 border border-blue-900/30 p-3.5 text-[11px] text-blue-300 space-y-1.5 leading-relaxed">
                      <p className="font-bold flex items-center gap-1">
                        <Clock size={12} /> Natural Human-Like Delays:
                      </p>
                      <p>• <strong>WhatsApp:</strong> AI replies are delayed by 4-5 minutes.</p>
                      <p>• <strong>Email:</strong> AI replies are delayed by 20 minutes.</p>
                      <p className="text-[10px] text-blue-400 mt-1 italic">
                        *Note: If you send a manual reply during this delay window, the AI will automatically cancel its pending auto-reply.
                      </p>
                    </div>
                  </CardContent>
                </Card>

              </div>
            </div>
          )}

          {/* VIEW: ORCHESTRATOR */}
          {activeView === 'orchestrator' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="lg:col-span-1 flex flex-col gap-6">
                <Card className="glass-panel border-transparent glow-support rounded-3xl overflow-hidden shadow-2xl relative">
                  <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500 to-transparent" />
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg text-white font-bold">Set a Goal</CardTitle>
                    <CardDescription className="text-gray-400 text-xs">e.g. "Get me 50 gym customers this month"</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <Textarea 
                      placeholder="What should the AI team accomplish?"
                      className="bg-gray-900/60 border-gray-800 text-white focus:border-blue-500 focus:ring-blue-500/20 rounded-xl text-base min-h-[100px] resize-none"
                      value={prompt} onChange={e => setPrompt(e.target.value)}
                    />
                    
                    <div className="grid grid-cols-2 gap-3 mt-1">
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">AI Provider</label>
                        <Select value={orchProvider} onValueChange={(val) => {
                          if (val) {
                            setOrchProvider(val);
                            if (val === 'anthropic') setOrchModel('claude-sonnet-4-6');
                            else if (val === 'openai') setOrchModel('gpt-4o');
                            else if (val === 'gemini') setOrchModel('gemini-2.5-pro');
                          }
                        }}>
                          <SelectTrigger className="bg-gray-900/60 border-gray-800 text-white rounded-xl h-10 text-xs focus:border-blue-500 focus:ring-0">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-gray-900 border-gray-800 text-white">
                            <SelectItem value="anthropic">Anthropic Claude</SelectItem>
                            <SelectItem value="openai">OpenAI GPT</SelectItem>
                            <SelectItem value="gemini">Google Gemini</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">AI Model</label>
                        <Select value={orchModel} onValueChange={(val) => val && setOrchModel(val)}>
                          <SelectTrigger className="bg-gray-900/60 border-gray-800 text-white rounded-xl h-10 text-xs focus:border-blue-500 focus:ring-0">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-gray-900 border-gray-800 text-white">
                            {orchProvider === 'anthropic' && (
                              <>
                                <SelectItem value="claude-sonnet-4-6">Claude 4.6 Sonnet</SelectItem>
                                <SelectItem value="claude-opus-4-8">Claude 4.8 Opus</SelectItem>
                                <SelectItem value="claude-haiku-4-5-20251001">Claude 4.5 Haiku</SelectItem>
                              </>
                            )}
                            {orchProvider === 'openai' && (
                              <>
                                <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                                <SelectItem value="gpt-4o-mini">GPT-4o-mini</SelectItem>
                              </>
                            )}
                            {orchProvider === 'gemini' && (
                              <>
                                <SelectItem value="gemini-2.5-pro">Gemini 2.5 Pro</SelectItem>
                                <SelectItem value="gemini-2.5-flash">Gemini 2.5 Flash</SelectItem>
                                <SelectItem value="gemini-2.0-flash">Gemini 2.0 Flash</SelectItem>
                              </>
                            )}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <Button 
                      onClick={handleRunCommand} 
                      disabled={loading} 
                      className="w-full h-11 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100"
                    >
                      {loading ? 'Orchestrating Teams...' : 'Execute Goal'}
                    </Button>
                  </CardContent>
                </Card>

                <Card className="flex-1 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl overflow-hidden shadow-2xl relative h-[450px] flex flex-col">
                  <CardHeader className="pb-3 border-b border-gray-800">
                    <CardTitle className="text-sm font-bold text-white">AI Activity Feed</CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-4 overflow-y-auto flex-1">
                    {timeline.length === 0 && <p className="text-xs text-gray-500 text-center mt-10">No recent activity.</p>}
                    {timeline.map((log) => (
                      <div key={log.id} className="flex gap-3 text-xs border-l-2 border-violet-500/30 pl-3 pb-3 relative">
                        <span className="absolute left-[-5px] top-1.5 h-2.5 w-2.5 rounded-full bg-violet-500 border border-gray-950 shadow-md" />
                        <div className="flex flex-col w-full">
                          <div className="flex justify-between w-full">
                            <span className="font-semibold text-white">{log.agent_name}</span>
                            <span className="text-[10px] text-gray-500">{new Date(log.created_at).toLocaleTimeString()}</span>
                          </div>
                          <span className="text-violet-400 font-medium mt-0.5">{log.action}</span>
                          <span className="text-gray-300 mt-1 leading-relaxed">{log.description}</span>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>

              <div className="lg:col-span-2">
                <Card className="h-full glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl overflow-hidden shadow-2xl relative h-full flex flex-col">
                  <CardHeader className="pb-3 border-b border-gray-800">
                    <CardTitle className="text-xl text-white font-extrabold">Approvals Pipeline</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-6">
                    <Tabs defaultValue="marketing" className="w-full">
                      <TabsList className="grid w-full max-w-[400px] grid-cols-2 bg-gray-950/60 p-1 border border-gray-800 rounded-xl mb-6">
                        <TabsTrigger value="marketing" className="rounded-lg text-xs font-semibold text-gray-400 data-[state=active]:bg-violet-600 data-[state=active]:text-white transition-all">Marketing Queue</TabsTrigger>
                        <TabsTrigger value="sales" className="rounded-lg text-xs font-semibold text-gray-400 data-[state=active]:bg-emerald-600 data-[state=active]:text-white transition-all">Sales Leads</TabsTrigger>
                      </TabsList>
                      <TabsContent value="marketing">
                        <div className="border border-gray-800 rounded-2xl overflow-hidden bg-[rgba(0,0,0,0.15)] shadow-inner">
                          <Table>
                            <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                              <TableRow className="border-gray-800 hover:bg-transparent">
                                <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Day / Platform</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Content Preview</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4 text-right">Action</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody className="divide-y divide-gray-800">
                              {(!queue.posts || queue.posts.length === 0) && (
                                <TableRow className="hover:bg-transparent">
                                  <TableCell colSpan={3} className="text-center py-8 text-gray-500 font-medium">Queue is empty.</TableCell>
                                </TableRow>
                              )}
                              {queue.posts?.map((post) => (
                                <TableRow key={post.id} className="border-gray-800 hover:bg-gray-900/20">
                                  <TableCell className="p-4 whitespace-nowrap">
                                    <div className="flex flex-col">
                                      <span className="text-xs font-extrabold uppercase text-violet-400">{post.platform}</span>
                                      <span className="text-[10px] text-gray-500 font-bold mt-0.5">Day {post.day}</span>
                                    </div>
                                  </TableCell>
                                  <TableCell className="p-4"><div className="max-w-sm truncate text-xs text-gray-300 leading-relaxed">{post.content}</div></TableCell>
                                  <TableCell className="p-4 text-right">
                                    <div className="flex gap-2 justify-end">
                                      <Button 
                                        size="sm" 
                                        variant="outline" 
                                        onClick={() => handleRejectPost(post.id)}
                                        className="h-8 text-xs font-semibold text-rose-400 border-rose-900/30 hover:bg-rose-950/20"
                                      >
                                        Reject
                                      </Button>
                                      <Button 
                                        size="sm" 
                                        onClick={() => handleApprovePost(post.id)}
                                        className="h-8 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white"
                                      >
                                        Approve
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </TabsContent>
                      <TabsContent value="sales">
                        <div className="border border-gray-800 rounded-2xl overflow-hidden bg-[rgba(0,0,0,0.15)] shadow-inner">
                          <Table>
                            <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                              <TableRow className="border-gray-800 hover:bg-transparent">
                                <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Lead Name</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Company</TableHead>
                                <TableHead className="text-gray-400 font-bold uppercase tracking-wider text-xs p-4">Source</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody className="divide-y divide-gray-800">
                              {(!queue.leads || queue.leads.length === 0) && (
                                <TableRow className="hover:bg-transparent">
                                  <TableCell colSpan={3} className="text-center py-8 text-gray-500 font-medium">No leads found.</TableCell>
                                </TableRow>
                              )}
                              {queue.leads?.map((lead) => (
                                <TableRow key={lead.id} className="border-gray-800 hover:bg-gray-900/20">
                                  <TableCell className="p-4 font-bold text-white text-xs">{lead.name}</TableCell>
                                  <TableCell className="p-4 text-xs text-gray-300">{lead.company}</TableCell>
                                  <TableCell className="p-4">
                                    <span className="text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded uppercase tracking-wider">
                                      {lead.source}
                                    </span>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* VIEW: TEAMS */}
          {activeView === 'teams' && (
            <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
              <div>
                <h1 className="text-4xl font-extrabold text-white tracking-tight">Autonomous AI Teams</h1>
                <p className="text-gray-400 mt-1">Deploy specialized autonomous AI agents tailored for your business goals.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {teams.map(team => (
                  <Card key={team.id} className="glass-panel border-transparent hover:border-violet-500/30 transition-all duration-300 rounded-3xl overflow-hidden shadow-2xl relative p-6">
                    <CardHeader className="p-0 pb-4">
                      <CardTitle className="text-white font-extrabold text-xl">{team.name}</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <h4 className="text-[10px] font-bold text-gray-400 mb-3 uppercase tracking-wider">Agents Included</h4>
                      <div className="flex flex-wrap gap-2">
                        {team.agents.map((agent: string) => (
                          <span key={agent} className="bg-violet-500/10 text-violet-400 border border-violet-500/20 rounded-xl text-xs font-bold px-3 py-1.5">
                            {agent}
                          </span>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* VIEW: MARKETPLACE */}
          {activeView === 'marketplace' && (
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
          )}

          {/* VIEW: INSTRUCTIONS */}
          {activeView === 'instructions' && (
            <div className="max-w-5xl mx-auto space-y-8 pb-16 animate-in fade-in duration-300">
              <div>
                <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
                  <BookOpen className="text-violet-500 h-9 w-9" /> Platform Setup & API Connection Guide
                </h1>
                <p className="text-gray-400 mt-1">Get your autonomous AI workspace connected, configured, and running in minutes.</p>
              </div>

              <Tabs defaultValue="marketplace_guide" className="w-full">
                <TabsList className="grid w-full max-w-[650px] grid-cols-3 bg-gray-950/60 p-1 border border-gray-800 rounded-2xl mb-8">
                  <TabsTrigger value="marketplace_guide" className="rounded-xl text-xs font-semibold py-2.5 text-gray-400 data-[state=active]:bg-violet-600 data-[state=active]:text-white transition-all">
                    🛒 Marketplace & Autopilot Guide
                  </TabsTrigger>
                  <TabsTrigger value="api_setup" className="rounded-xl text-xs font-semibold py-2.5 text-gray-400 data-[state=active]:bg-violet-600 data-[state=active]:text-white transition-all">
                    🔑 API Provider Setup
                  </TabsTrigger>
                  <TabsTrigger value="quick_prompts" className="rounded-xl text-xs font-semibold py-2.5 text-gray-400 data-[state=active]:bg-violet-600 data-[state=active]:text-white transition-all">
                    ⚡ Quick-Start Prompts
                  </TabsTrigger>
                </TabsList>

                {/* TAB CONTENT: MARKETPLACE GUIDE */}
                <TabsContent value="marketplace_guide" className="space-y-6 animate-in fade-in duration-200">
                  <Card className="glass-panel border-transparent p-8 rounded-3xl shadow-2xl relative overflow-hidden">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-violet-500 to-transparent" />
                    <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                      <Zap className="text-pink-500 animate-pulse" size={20} />
                      How to Use Marketplace Automations (Non-Tech Friendly)
                    </h3>
                    
                    <div className="space-y-8 relative before:absolute before:left-[17px] before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-violet-500 before:via-pink-500 before:to-gray-800">
                      
                      {/* Step 1 */}
                      <div className="flex gap-6 relative">
                        <div className="h-9 w-9 rounded-full bg-violet-600 border-2 border-gray-950 flex items-center justify-center font-extrabold text-white text-sm shadow-lg z-10">
                          1
                        </div>
                        <div className="flex-1 space-y-1.5 pt-0.5">
                          <h4 className="font-bold text-white text-base">Select & Install Your Autopilot Pack</h4>
                          <p className="text-gray-300 text-xs leading-relaxed">
                            Click the <strong className="text-violet-400">Workflow Marketplace</strong> in the sidebar. Choose the pack that aligns with your industry (e.g., <strong className="text-violet-400">Restaurant Growth Pack</strong> or <strong className="text-violet-400">SaaS Outreach System</strong>). Click <strong className="bg-pink-600/35 border border-pink-500/30 px-2 py-0.5 rounded text-white font-bold">Install Pack</strong>. Once installed, it instantly shows up under "Installed Automations" on your Operating Dashboard.
                          </p>
                        </div>
                      </div>

                      {/* Step 2 */}
                      <div className="flex gap-6 relative">
                        <div className="h-9 w-9 rounded-full bg-violet-600 border-2 border-gray-950 flex items-center justify-center font-extrabold text-white text-sm shadow-lg z-10">
                          2
                        </div>
                        <div className="flex-1 space-y-1.5 pt-0.5">
                          <h4 className="font-bold text-white text-base">Connect Your API Keys</h4>
                          <p className="text-gray-300 text-xs leading-relaxed">
                            Open the <strong className="text-violet-400">API Provider Setup</strong> tab above. Check which services your pack needs (e.g. Meta Graph for Instagram, Apollo.io for B2B sales email). Click <strong className="text-violet-400 font-bold">API Settings</strong> in the top-right header, select the provider, paste your key, and click Save. Check if the status badge on the provider card turns <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-450 border border-emerald-500/20 px-2 py-0.5 rounded text-[10px] font-bold">● Connected</span>.
                          </p>
                        </div>
                      </div>

                      {/* Step 3 */}
                      <div className="flex gap-6 relative">
                        <div className="h-9 w-9 rounded-full bg-pink-600 border-2 border-gray-950 flex items-center justify-center font-extrabold text-white text-sm shadow-lg z-10">
                          3
                        </div>
                        <div className="flex-1 space-y-1.5 pt-0.5">
                          <h4 className="font-bold text-white text-base">Instruct the Orchestrator AI</h4>
                          <p className="text-gray-300 text-xs leading-relaxed">
                            Navigate to <strong className="text-violet-400">Orchestrator AI</strong> from the sidebar. Ask the AI to perform a task utilizing your installed pack. For example: <code className="bg-gray-950 px-2 py-1 rounded text-pink-400 text-[11px] font-mono">"Run the Restaurant Growth Pack to post our specials on Instagram today"</code>. The AI will look at your active integrations, generate the content draft, and process the request!
                          </p>
                        </div>
                      </div>

                      {/* Step 4 */}
                      <div className="flex gap-6 relative">
                        <div className="h-9 w-9 rounded-full bg-pink-600 border-2 border-gray-950 flex items-center justify-center font-extrabold text-white text-sm shadow-lg z-10">
                          4
                        </div>
                        <div className="flex-1 space-y-1.5 pt-0.5">
                          <h4 className="font-bold text-white text-base">Review & Approve in the Operating Dashboard</h4>
                          <p className="text-gray-300 text-xs leading-relaxed">
                            Open your <strong className="text-violet-400">Operating Dashboard</strong>. Scroll down to the <strong className="text-violet-400">Approvals Pipeline</strong>. You'll see the AI's generated output (e.g. daily specials posts, outbound leads) sitting in the queue. Click <strong className="text-emerald-400 font-bold">Approve</strong> to publish or send them, or <strong className="text-rose-400 font-bold">Reject</strong> to request changes. You are always in control!
                          </p>
                        </div>
                      </div>

                    </div>
                  </Card>

                  {/* Operational Details Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="glass-panel border-transparent p-6 rounded-3xl relative overflow-hidden">
                      <h4 className="text-white font-bold text-base mb-3 flex items-center gap-2">🤖 Autonomous Auto-Reply delays</h4>
                      <p className="text-gray-300 text-xs leading-relaxed">
                        To maintain a natural, human-like appearance, when the AI agent handles incoming messages (e.g. WhatsApp, Email Tickets), it uses natural delays:
                      </p>
                      <ul className="text-gray-400 text-xs space-y-2 mt-3 pl-4 list-disc">
                        <li><strong>WhatsApp:</strong> 4-5 minutes wait window before automated response.</li>
                        <li><strong>Email Tickets:</strong> 20 minutes wait window.</li>
                        <li><strong>Human Interception:</strong> If you write a manual reply in the support tab before the delay timer runs out, the AI will step back and cancel its scheduled response automatically.</li>
                      </ul>
                    </Card>

                    <Card className="glass-panel border-transparent p-6 rounded-3xl relative overflow-hidden">
                      <h4 className="text-white font-bold text-base mb-3 flex items-center gap-2">🧠 Knowledge Base Integration</h4>
                      <p className="text-gray-300 text-xs leading-relaxed">
                        Before the AI generates any marketing posts, replies to customer support emails, or scores candidates, it reads files uploaded to your <strong className="text-violet-400">Knowledge Base</strong> (found in the header). 
                      </p>
                      <p className="text-gray-300 text-xs leading-relaxed mt-2">
                        For best results, upload your <strong>Brand Guidelines</strong>, <strong>FAQs & Policies</strong>, <strong>Pricing Tables</strong>, or <strong>Job Descriptions</strong>. This guarantees the AI behaves in complete alignment with your brand rules!
                      </p>
                    </Card>
                  </div>
                </TabsContent>

                {/* TAB CONTENT: API SETUP CARD GRID */}
                <TabsContent value="api_setup" className="space-y-6 animate-in fade-in duration-200">
                  <div className="grid grid-cols-1 gap-6">

                    {/* AI Brains & Generators Card */}
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4 mb-4">
                        <div>
                          <h3 className="text-white font-extrabold text-lg flex items-center gap-2">1. AI Brains & Generators</h3>
                          <p className="text-gray-400 text-xs mt-1">Powers the core thinking, writing, image creation, and video generation for your AI employees.</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                            configuredProviders.includes('anthropic') || configuredProviders.includes('openai') || configuredProviders.includes('gemini')
                              ? 'bg-emerald-500/10 text-emerald-455 border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-455 border-rose-500/20 animate-pulse'
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              configuredProviders.includes('anthropic') || configuredProviders.includes('openai') || configuredProviders.includes('gemini') ? 'bg-emerald-450' : 'bg-rose-450'
                            }`} />
                            {configuredProviders.includes('anthropic') || configuredProviders.includes('openai') || configuredProviders.includes('gemini') ? 'Active' : 'Missing Primary Key'}
                          </span>
                          <Button 
                            onClick={() => { setKeyProvider('anthropic'); setIsKeyDialogOpen(true); }}
                            className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold h-8 rounded-xl px-4"
                          >
                            Configure
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-300 text-xs">
                        {/* Claude */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-violet-400" /> Claude (Anthropic API) - Recommended
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Go to <a href="https://console.anthropic.com/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">console.anthropic.com</a> and sign in.</li>
                            <li>Navigate to <strong>API Keys</strong> in the left dashboard menu.</li>
                            <li>Click the <strong>Create Key</strong> button.</li>
                            <li>Name it (e.g. "NexusOS") and copy the new key starting with <code>sk-ant-</code>.</li>
                            <li>Click the <strong>Configure</strong> button above and paste this key to activate.</li>
                          </ol>
                        </div>

                        {/* OpenAI */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-emerald-400" /> OpenAI (ChatGPT API)
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Go to <a href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">platform.openai.com/api-keys</a> and sign in.</li>
                            <li>Click the <strong>Create new secret key</strong> button.</li>
                            <li>Provide a name (e.g., "NexusOS Default") and create the key.</li>
                            <li>Copy the generated key (it usually starts with <code>sk-proj-</code>).</li>
                            <li>Save it in NexusOS to give your agents access to GPT-4o.</li>
                          </ol>
                        </div>

                        {/* Gemini */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-blue-400" /> Google Gemini API
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Go to <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Google AI Studio</a> and sign in with your Google account.</li>
                            <li>Click <strong>Get API Key</strong> on the left sidebar.</li>
                            <li>Click the blue <strong>Create API Key in new project</strong> button.</li>
                            <li>Once generated, copy the long alphanumeric string.</li>
                            <li>Paste the key into the NexusOS configuration panel to enable Google's models.</li>
                          </ol>
                        </div>

                        {/* Stable Diffusion */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-fuchsia-400" /> Stable Diffusion (Stability AI)
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Go to <a href="https://platform.stability.ai/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">platform.stability.ai</a> and log in.</li>
                            <li>Click on your profile avatar in the top right, then select <strong>API Keys</strong>.</li>
                            <li>Click the copy icon next to your default API key (starting with <code>sk-</code>).</li>
                            <li>Provide this key to NexusOS to enable high-quality AI image generation for Marketing.</li>
                          </ol>
                        </div>

                        {/* Pika AI */}
                        <div className="space-y-2 md:col-span-2 lg:col-span-1">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-amber-400" /> Pika AI (Video Generation)
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Visit <a href="https://pika.art/login" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">pika.art</a> and create an account or sign in.</li>
                            <li>Navigate to the API section or developer settings (if you have API access enabled).</li>
                            <li>Generate a new API token.</li>
                            <li>Enter this token into NexusOS so your Marketing AI can generate and publish video content directly.</li>
                          </ol>
                        </div>
                      </div>
                      
                      <div className="bg-violet-950/25 border border-violet-900/30 p-4 rounded-xl text-xs text-violet-300 mt-6 leading-relaxed font-mono flex items-start gap-3 shadow-inner">
                        <span className="text-lg">💡</span> 
                        <div>
                          <strong className="text-white block mb-1">Pro-Tip for Non-Tech Users:</strong> 
                          You can bypass the manual "Configure" button entirely! Just type or paste your key directly into the Orchestrator AI Chat window on the left. For example: <code>"Here is my Gemini key: AIzaSyB..."</code> and the AI will securely save and configure it for you automatically!
                        </div>
                      </div>
                    </Card>

                    {/* Social Media Card */}
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4 mb-4">
                        <div>
                          <h3 className="text-white font-extrabold text-lg flex items-center gap-2">2. Social Media (Meta & LinkedIn)</h3>
                          <p className="text-gray-400 text-xs mt-1">Allows the Marketing AI to draft and automatically publish campaigns on your profiles.</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                            configuredProviders.includes('meta') || configuredProviders.includes('linkedin')
                              ? 'bg-emerald-500/10 text-emerald-455 border-emerald-500/20'
                              : 'bg-gray-800 text-gray-400 border-gray-700/60'
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              configuredProviders.includes('meta') || configuredProviders.includes('linkedin') ? 'bg-emerald-450' : 'bg-gray-500'
                            }`} />
                            {configuredProviders.includes('meta') || configuredProviders.includes('linkedin') ? 'Configured' : 'Not Connected'}
                          </span>
                          <Button 
                            onClick={() => { setKeyProvider('linkedin'); setIsKeyDialogOpen(true); }}
                            className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold h-8 rounded-xl px-4"
                          >
                            Configure
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-300 text-xs">
                        {/* Meta Graph API */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-blue-500" /> Meta Graph API (Instagram & Facebook)
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Log into <a href="https://developers.facebook.com/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Meta for Developers</a> and click <strong>Create App</strong>.</li>
                            <li>Select <strong>Other</strong> then <strong>Business</strong> as the app type.</li>
                            <li>Scroll down to add the <strong>Instagram Graph API</strong> product to your newly created app.</li>
                            <li>Navigate to the <strong>Tools &gt; Graph API Explorer</strong> in the top menu.</li>
                            <li>Select your app and generate a <strong>Page Access Token</strong>, ensuring you add the <code>instagram_content_publish</code>, <code>pages_show_list</code>, and <code>instagram_basic</code> permissions.</li>
                            <li>Click "Generate Access Token". Use the <strong>Access Token Tool</strong> to extend it into a long-lived (60-day) token, then paste it into NexusOS. <em className="text-gray-500 text-[10px] block mt-1">(Make sure your Instagram Business Account is properly linked to your Facebook Page!)</em></li>
                          </ol>
                        </div>
                        
                        {/* LinkedIn */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-sky-500" /> LinkedIn Share API
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Sign in to the <a href="https://developer.linkedin.com/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">LinkedIn Developer Portal</a> and click <strong>Create App</strong>.</li>
                            <li>Fill in the required details (Name, LinkedIn Page URL, Privacy Policy URL) and verify your app.</li>
                            <li>Under the <strong>Products</strong> tab, request access to <strong>"Share on LinkedIn"</strong> and <strong>"Sign In with LinkedIn v2"</strong>. Wait for approval.</li>
                            <li>Navigate to the <strong>Auth</strong> tab and use the <strong>OAuth 2.0 Token Generator</strong> tool.</li>
                            <li>Select the products you requested and generate a <strong>Personal Access Token</strong> (usually valid for 2 months).</li>
                            <li>Copy the generated token and paste it here to authorize NexusOS to post on your behalf.</li>
                          </ol>
                        </div>
                      </div>
                    </Card>

                    {/* Messaging Card */}
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4 mb-4">
                        <div>
                          <h3 className="text-white font-extrabold text-lg flex items-center gap-2">3. Chat Messaging (WhatsApp & Telegram)</h3>
                          <p className="text-gray-400 text-xs mt-1">Connects customer chat channels so the Support & Lead Gen AI can respond automatically.</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                            configuredProviders.includes('whatsapp') || configuredProviders.includes('telegram')
                              ? 'bg-emerald-500/10 text-emerald-455 border-emerald-500/20'
                              : 'bg-gray-800 text-gray-400 border-gray-700/60'
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              configuredProviders.includes('whatsapp') || configuredProviders.includes('telegram') ? 'bg-emerald-450' : 'bg-gray-500'
                            }`} />
                            {configuredProviders.includes('whatsapp') || configuredProviders.includes('telegram') ? 'Configured' : 'Not Connected'}
                          </span>
                          <Button 
                            onClick={() => { setKeyProvider('whatsapp'); setIsKeyDialogOpen(true); }}
                            className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold h-8 rounded-xl px-4"
                          >
                            Configure
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-300 text-xs">
                        {/* WhatsApp */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-emerald-500" /> WhatsApp Cloud Business API
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Inside your <a href="https://developers.facebook.com/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Meta Developer Console</a>, open your existing app or create a new Business App.</li>
                            <li>Scroll down to add the <strong>WhatsApp</strong> product to your app.</li>
                            <li>Navigate to <strong>WhatsApp &gt; API Setup</strong> in the left sidebar.</li>
                            <li>Copy your <strong>Phone Number ID</strong> and your temporary <strong>Access Token</strong> (or generate a permanent System User token in Business Settings).</li>
                            <li>Paste the Token and Phone ID in the NexusOS settings.</li>
                            <li>Finally, configure the <strong>Webhook URL</strong> in Meta to point to your NexusOS backend (usually <code>/api/v1/webhooks/whatsapp</code>) with a verify token so your AI can receive incoming customer messages.</li>
                          </ol>
                        </div>
                        
                        {/* Telegram */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-blue-400" /> Telegram Bot API
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Open your Telegram app on your phone or desktop.</li>
                            <li>Search for <code>@BotFather</code> in the global search bar and press <strong>Start</strong>.</li>
                            <li>Send the command <code>/newbot</code> to initiate the creation process.</li>
                            <li>Choose a display name for your AI Assistant, and then a unique username that must end in "bot" (e.g. <code>SupportAgentBot</code>).</li>
                            <li>BotFather will reply with a success message containing your <strong>HTTP API Token</strong> (looks like <code>123456789:ABCDEF...</code>).</li>
                            <li>Copy this exact token and save it in NexusOS. The system will automatically register a webhook to receive messages.</li>
                          </ol>
                        </div>
                      </div>
                    </Card>

                    {/* Google Workspace Card */}
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4 mb-4">
                        <div>
                          <h3 className="text-white font-extrabold text-lg flex items-center gap-2">4. Email & Bookings (Google Workspace / Gmail / Calendar)</h3>
                          <p className="text-gray-400 text-xs mt-1">Allows agents to coordinate and send cold email campaigns or book meetings on your calendar.</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                            configuredProviders.includes('gmail') || configuredProviders.includes('google_calendar') || configuredProviders.includes('smtp')
                              ? 'bg-emerald-500/10 text-emerald-455 border-emerald-500/20'
                              : 'bg-gray-800 text-gray-400 border-gray-700/60'
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              configuredProviders.includes('gmail') || configuredProviders.includes('google_calendar') || configuredProviders.includes('smtp') ? 'bg-emerald-450' : 'bg-gray-500'
                            }`} />
                            {configuredProviders.includes('gmail') || configuredProviders.includes('google_calendar') || configuredProviders.includes('smtp') ? 'Configured' : 'Not Connected'}
                          </span>
                          <Button 
                            onClick={() => { window.location.href = `${API_URL}/api/v1/google/auth?tenant_id=${tenantId}`; }}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold h-8 rounded-xl px-4"
                          >
                            Connect Google Account
                          </Button>
                          <Button 
                            onClick={() => { setKeyProvider('smtp'); setIsKeyDialogOpen(true); }}
                            className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold h-8 rounded-xl px-4"
                          >
                            Configure SMTP
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-300 text-xs">
                        {/* Google Cloud */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-red-500" /> Google Cloud OAuth Setup (Gmail & Calendar)
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Go to the <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Google Cloud Console</a> and create a new Project (e.g., "NexusOS Workspace").</li>
                            <li>Navigate to <strong>APIs &amp; Services &gt; Library</strong> using the left menu.</li>
                            <li>Search for and enable both the <strong>Gmail API</strong> and <strong>Google Calendar API</strong>.</li>
                            <li>Go to the <strong>OAuth consent screen</strong> tab and configure it (Internal for organizations, or External for general use). Add the necessary scopes for Mail and Calendar.</li>
                            <li>Navigate to <strong>Credentials</strong>, click <strong>Create Credentials &gt; OAuth client ID</strong>. Choose "Web application" or "Desktop app".</li>
                            <li>Download the resulting JSON secret file and upload or connect it in NexusOS to grant your AI full calendar and email drafting capabilities.</li>
                          </ol>
                        </div>
                        
                        {/* SMTP */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-orange-400" /> Standard Outgoing Mail (SMTP Alternative)
                          </p>
                          <p className="text-gray-400 leading-relaxed mb-3">
                            If you do not want to set up a full Google Cloud OAuth project, you can allow the AI to send emails via a standard SMTP connection using an App Password.
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Go to your Google Account's <a href="https://myaccount.google.com/security" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Security settings</a>.</li>
                            <li>Ensure <strong>2-Step Verification</strong> is enabled.</li>
                            <li>Search for <strong>App Passwords</strong> in the security search bar.</li>
                            <li>Create a new app password named "NexusOS AI". Copy the generated 16-character password.</li>
                            <li>Provide your SMTP string in the NexusOS settings formatted like this: <br/><code className="bg-gray-900 px-1.5 py-0.5 rounded text-gray-300 mt-1 inline-block border border-gray-800">smtp://your.email@gmail.com:app-password@smtp.gmail.com:587</code></li>
                          </ol>
                        </div>
                      </div>
                    </Card>

                    {/* Lead Gen Card */}
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-800 pb-4 mb-4">
                        <div>
                          <h3 className="text-white font-extrabold text-lg flex items-center gap-2">5. Sales Lead Generation (Apollo / Hunter / Google Maps)</h3>
                          <p className="text-gray-400 text-xs mt-1">Powers the Sales AI to extract and identify high-value contacts or local businesses.</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                            configuredProviders.includes('apollo') || configuredProviders.includes('hunter') || configuredProviders.includes('google_places')
                              ? 'bg-emerald-500/10 text-emerald-455 border-emerald-500/20'
                              : 'bg-gray-800 text-gray-400 border-gray-700/60'
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              configuredProviders.includes('apollo') || configuredProviders.includes('hunter') || configuredProviders.includes('google_places') ? 'bg-emerald-450' : 'bg-gray-500'
                            }`} />
                            {configuredProviders.includes('apollo') || configuredProviders.includes('hunter') || configuredProviders.includes('google_places') ? 'Configured' : 'Not Connected'}
                          </span>
                          <Button 
                            onClick={() => { setKeyProvider('apollo'); setIsKeyDialogOpen(true); }}
                            className="bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold h-8 rounded-xl px-4"
                          >
                            Configure
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-300 text-xs">
                        {/* Apollo / Hunter */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-indigo-500" /> Apollo.io / Hunter.io (B2B Enrichment)
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Create a free or paid account at <a href="https://www.apollo.io/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Apollo.io</a> or <a href="https://hunter.io/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Hunter.io</a>.</li>
                            <li>For Apollo: Go to <strong>Settings &gt; Integrations &gt; API</strong> and click <strong>Generate New API Key</strong>.</li>
                            <li>For Hunter: Go to <strong>Account &gt; API</strong> and copy your API key.</li>
                            <li>Paste the respective API key into the NexusOS configuration panel.</li>
                            <li>Your Sales AI Agent is now instantly capable of enriching company names into verified employee contact lists, emails, and phone numbers!</li>
                          </ol>
                        </div>
                        
                        {/* Google Places */}
                        <div className="space-y-2">
                          <p className="font-bold text-white flex items-center gap-1.5 text-sm pb-1 border-b border-gray-800">
                            <span className="h-2 w-2 rounded-full bg-teal-500" /> Google Places API (Local Business Scraper)
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-gray-400">
                            <li>Log into the <a href="https://console.cloud.google.com/" target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 transition-colors hover:underline font-medium">Google Cloud Console</a> and select your project.</li>
                            <li>In the search bar, type <strong>Places API (New)</strong> and click Enable.</li>
                            <li>Make sure you have an active billing account linked to your Google Cloud project (Google provides $200 free credit monthly).</li>
                            <li>Go to <strong>APIs &amp; Services &gt; Credentials</strong>, click <strong>Create Credentials</strong>, and select <strong>API Key</strong>.</li>
                            <li>(Strongly Recommended) Edit the API Key to restrict it specifically to the "Places API" to prevent unauthorized usage.</li>
                            <li>Copy the generated key and save it in NexusOS to allow your AI to map local business targets.</li>
                          </ol>
                        </div>
                      </div>
                    </Card>

                  </div>
                </TabsContent>

                {/* TAB CONTENT: QUICK PROMPTS */}
                <TabsContent value="quick_prompts" className="space-y-6 animate-in fade-in duration-200">
                  <Card className="glass-panel border-transparent p-6 rounded-3xl shadow-2xl relative">
                    <h3 className="text-white font-extrabold text-lg mb-4 flex items-center gap-2">⚡ Autopilot Launch Commands</h3>
                    <p className="text-gray-300 text-xs leading-relaxed mb-6">
                      Once you have installed a Marketplace Pack and configured its API keys, you can trigger its operation. Go to the <strong className="text-violet-400">Orchestrator AI</strong> chat tab and copy-paste any of the ready-to-run prompts below:
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Prompt 1 */}
                      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 flex flex-col justify-between space-y-4 hover:border-pink-500/30 transition-all">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-pink-400 font-bold uppercase tracking-wider bg-pink-500/10 border border-pink-500/20 px-2 py-0.5 rounded-md">Restaurant Pack</span>
                            <span className="text-[10px] text-gray-500">Local Marketing</span>
                          </div>
                          <p className="text-white text-xs font-semibold">"Trigger the daily special post for Restaurant Pack. Create a draft of today's specials (Steak & Potatoes with red wine) for Instagram."</p>
                        </div>
                        <Button 
                          onClick={() => {
                            navigator.clipboard.writeText("Trigger the daily special post for Restaurant Pack. Create a draft of today's specials (Steak & Potatoes with red wine) for Instagram.");
                            alert("Copied to clipboard! Go to Orchestrator AI to paste.");
                          }}
                          className="bg-gray-850 hover:bg-gray-800 text-gray-300 text-xs font-bold w-full h-8 rounded-xl"
                        >
                          Copy Prompt
                        </Button>
                      </div>

                      {/* Prompt 2 */}
                      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 flex flex-col justify-between space-y-4 hover:border-pink-500/30 transition-all">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-pink-400 font-bold uppercase tracking-wider bg-pink-500/10 border border-pink-500/20 px-2 py-0.5 rounded-md">SaaS Outreach</span>
                            <span className="text-[10px] text-gray-500">B2B Outbound</span>
                          </div>
                          <p className="text-white text-xs font-semibold">"Execute the SaaS Outreach System. Sourcing 5 CTOs at early-stage AI startups in New York, and write personalized outbound LinkedIn DMs."</p>
                        </div>
                        <Button 
                          onClick={() => {
                            navigator.clipboard.writeText("Execute the SaaS Outreach System. Sourcing 5 CTOs at early-stage AI startups in New York, and write personalized outbound LinkedIn DMs.");
                            alert("Copied to clipboard! Go to Orchestrator AI to paste.");
                          }}
                          className="bg-gray-850 hover:bg-gray-800 text-gray-300 text-xs font-bold w-full h-8 rounded-xl"
                        >
                          Copy Prompt
                        </Button>
                      </div>

                      {/* Prompt 3 */}
                      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 flex flex-col justify-between space-y-4 hover:border-pink-500/30 transition-all">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-pink-400 font-bold uppercase tracking-wider bg-pink-500/10 border border-pink-500/20 px-2 py-0.5 rounded-md">Real Estate Pack</span>
                            <span className="text-[10px] text-gray-500">Real Estate</span>
                          </div>
                          <p className="text-white text-xs font-semibold">"Generate property descriptions using the Real Estate Lead Engine for 456 Oak Ave. Make it sound premium with a luxury pool description."</p>
                        </div>
                        <Button 
                          onClick={() => {
                            navigator.clipboard.writeText("Generate property descriptions using the Real Estate Lead Engine for 456 Oak Ave. Make it sound premium with a luxury pool description.");
                            alert("Copied to clipboard! Go to Orchestrator AI to paste.");
                          }}
                          className="bg-gray-850 hover:bg-gray-800 text-gray-300 text-xs font-bold w-full h-8 rounded-xl"
                        >
                          Copy Prompt
                        </Button>
                      </div>

                      {/* Prompt 4 */}
                      <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-4 flex flex-col justify-between space-y-4 hover:border-pink-500/30 transition-all">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] text-pink-400 font-bold uppercase tracking-wider bg-pink-500/10 border border-pink-500/20 px-2 py-0.5 rounded-md">Creative Content</span>
                            <span className="text-[10px] text-gray-500">Creative Agency</span>
                          </div>
                          <p className="text-white text-xs font-semibold">"Create an SEO Blog Outline Writer task with the Creative Content Lab. Write a outline on 'How AI employees are transforming small businesses'."</p>
                        </div>
                        <Button 
                          onClick={() => {
                            navigator.clipboard.writeText("Create an SEO Blog Outline Writer task with the Creative Content Lab. Write a outline on 'How AI employees are transforming small businesses'.");
                            alert("Copied to clipboard! Go to Orchestrator AI to paste.");
                          }}
                          className="bg-gray-850 hover:bg-gray-800 text-gray-300 text-xs font-bold w-full h-8 rounded-xl"
                        >
                          Copy Prompt
                        </Button>
                      </div>
                    </div>
                  </Card>
                </TabsContent>
              </Tabs>
            </div>
          )}

          {/* VIEW: HR */}
          {activeView === 'hr' && (
            <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <Briefcase className="text-amber-400 h-8 w-8 animate-pulse" /> Hiring & HR Recruiter Agent
                  </h1>
                  <p className="text-gray-400 mt-1">Autonomous candidate sourcing, outreach sequencing, and interview scheduling.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Sourcing Generator Form */}
                <div className="lg:col-span-1 space-y-6">
                  <Card className="glass-panel border-transparent glow-hr rounded-3xl overflow-hidden shadow-2xl relative">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                    <CardHeader>
                      <CardTitle className="text-xl text-white font-extrabold tracking-tight">Find Candidates</CardTitle>
                      <CardDescription className="text-gray-400 text-xs mt-1">Specify the role requirements and salary budget to trigger autonomous candidate sourcing.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex flex-col gap-2">
                        <label className="text-xs font-semibold text-gray-400">Role Title</label>
                        <Input
                          placeholder="e.g. Senior Backend Engineer"
                          value={hrRole}
                          onChange={e => setHrRole(e.target.value)}
                          className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl h-10"
                        />
                      </div>

                      <div className="flex flex-col gap-2">
                        <label className="text-xs font-semibold text-gray-400">Role Requirements & Qualifications</label>
                        <Textarea
                          placeholder="e.g. 3+ years experience with Python, FastAPI, PostgreSQL. Strong communication and remote work capability."
                          className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl min-h-[120px] text-sm"
                          value={hrRequirements}
                          onChange={e => setHrRequirements(e.target.value)}
                        />
                      </div>

                      <div className="flex gap-4">
                        <div className="flex-1 flex flex-col gap-2">
                          <label className="text-xs font-semibold text-gray-400">Annual Salary / Budget</label>
                          <Input
                            placeholder="e.g. $120,000/year"
                            value={hrSalary}
                            onChange={e => setHrSalary(e.target.value)}
                            className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl h-10"
                          />
                        </div>
                        <div className="w-24 flex flex-col gap-2">
                          <label className="text-xs font-semibold text-gray-400">Count</label>
                          <Input
                            type="number"
                            min={1}
                            max={10}
                            value={hrCount}
                            onChange={e => setHrCount(parseInt(e.target.value) || 5)}
                            className="bg-gray-900/60 border-gray-800 text-white focus:border-amber-500 focus:ring-amber-500/20 rounded-xl h-10"
                          />
                        </div>
                      </div>

                      <Button
                        onClick={handleSourceCandidates}
                        disabled={hrLoading || !hrRole || !hrRequirements}
                        className="w-full h-11 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold rounded-xl shadow-lg shadow-amber-500/20 hover:shadow-amber-500/30 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:scale-100 disabled:shadow-none"
                      >
                        {hrLoading ? 'HR Agent Sourcing...' : 'Autonomously Source Candidates'}
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Quick Stats card */}
                  <Card className="glass-panel border-transparent p-6 space-y-4 rounded-3xl shadow-2xl relative">
                    <h3 className="font-bold text-sm text-white border-b border-gray-800 pb-2">Hiring Pipeline Progress</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Sourced Candidates:</span>
                        <span className="font-bold text-white">{candidates.length}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Outreach Sent (Screened):</span>
                        <span className="font-bold text-white">{candidates.filter(c => c.status === 'screened').length}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Interviews Scheduled:</span>
                        <span className="font-bold text-white">{candidates.filter(c => c.status === 'interviewed').length}</span>
                      </div>
                    </div>
                  </Card>
                </div>

                {/* Candidate Pipeline Display */}
                <div className="lg:col-span-2 space-y-6">
                  {candidates.length === 0 ? (
                    <Card className="glass-panel border-dashed border-gray-800 p-12 text-center flex flex-col items-center justify-center rounded-3xl min-h-[400px] shadow-2xl">
                      <div className="text-5xl mb-4 animate-bounce">👥</div>
                      <h3 className="text-lg font-bold text-white">No candidates sourced yet</h3>
                      <p className="text-gray-400 max-w-sm mt-2 text-xs leading-relaxed">Submit your job details on the left, and the HR AI agent will populate matches here.</p>
                    </Card>
                  ) : (
                    <div className="space-y-4 max-h-[750px] overflow-y-auto pr-2 pb-6">
                      {candidates.map(candidate => {
                        const scorecard = candidate.scorecard || {};
                        const skills = scorecard.skills || [];
                        const score = scorecard.match_score || 0;
                        const summary = scorecard.experience_summary || '';
                        const matchReason = scorecard.requirements_match || '';
                        const expectedSalary = scorecard.salary_expectation || '';

                        let statusColor = 'bg-gray-500/10 text-gray-400 border-gray-500/20';
                        if (candidate.status === 'sourced') statusColor = 'bg-blue-500/10 text-blue-400 border-blue-500/20';
                        if (candidate.status === 'screened') statusColor = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
                        if (candidate.status === 'interviewed') statusColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';

                        let scoreColor = 'text-emerald-400';
                        if (score < 80) scoreColor = 'text-amber-400';
                        if (score < 70) scoreColor = 'text-rose-400';

                        const isSelected = selectedCandidateId === candidate.id;

                        return (
                          <Card key={candidate.id} className={`glass-panel border-gray-800/80 hover:border-amber-500/40 hover:shadow-amber-500/5 transition-all duration-200 overflow-hidden rounded-2xl shadow-xl ${isSelected ? 'ring-2 ring-amber-500' : ''}`}>
                            <div className="p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-gray-800 bg-gray-950/40">
                              <div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <h3 className="text-lg font-bold text-white">{candidate.name}</h3>
                                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${statusColor}`}>
                                    {candidate.status}
                                  </span>
                                </div>
                                <p className="text-xs text-gray-400 mt-1">{candidate.email} • Sourced for <strong>{candidate.role}</strong></p>
                              </div>

                              <div className="flex items-center gap-3">
                                <div className="relative h-12 w-12 flex items-center justify-center">
                                  <svg className="w-full h-full transform -rotate-90">
                                    <circle cx="24" cy="24" r="20" stroke="rgba(255,255,255,0.05)" strokeWidth="3" fill="transparent" />
                                    <circle cx="24" cy="24" r="20" 
                                      stroke={score >= 80 ? "#10b981" : score >= 70 ? "#f59e0b" : "#ef4444"} 
                                      strokeWidth="3.5" 
                                      fill="transparent" 
                                      strokeDasharray={2 * Math.PI * 20}
                                      strokeDashoffset={2 * Math.PI * 20 * (1 - score / 100)}
                                      strokeLinecap="round"
                                      className="transition-all duration-500"
                                    />
                                  </svg>
                                  <span className={`absolute text-[10px] font-black ${scoreColor}`}>{score}%</span>
                                </div>
                                <div className="text-left hidden md:block pr-2">
                                  <div className="text-[9px] text-gray-500 font-bold uppercase tracking-wider">Match Score</div>
                                  <div className="text-[10px] text-gray-400 font-medium">HR AI Assessed</div>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-gray-400 hover:text-white"
                                  onClick={() => setSelectedCandidateId(isSelected ? null : candidate.id)}
                                >
                                  {isSelected ? 'Hide Details' : 'View Details'}
                                </Button>
                              </div>
                            </div>

                            {/* Details Panel */}
                            {isSelected && (
                              <div className="p-5 border-b border-gray-800 bg-gray-950/20 space-y-4 animate-in slide-in-from-top-2 duration-200">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div>
                                    <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Skills</h4>
                                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                                      {skills.map((skill: string) => (
                                        <span key={skill} className="px-2 py-0.5 bg-gray-900 text-gray-300 text-xs rounded-lg border border-gray-800">
                                          {skill}
                                        </span>
                                      ))}
                                      {skills.length === 0 && <span className="text-xs text-gray-500">None listed</span>}
                                    </div>
                                  </div>
                                  <div>
                                    <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Salary Expectations</h4>
                                    <p className="text-sm font-semibold text-white mt-1">{expectedSalary || 'N/A'}</p>
                                  </div>
                                </div>

                                <div>
                                  <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Profile Summary</h4>
                                  <p className="text-xs text-gray-300 mt-1.5 leading-relaxed">{summary}</p>
                                </div>

                                <div>
                                  <h4 className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Match Analysis</h4>
                                  <p className="text-xs text-blue-300 mt-1.5 leading-relaxed bg-blue-950/20 border border-blue-900/30 p-3 rounded-xl">{matchReason}</p>
                                </div>

                                {/* Outreach detail */}
                                {scorecard.outbound_subject && (
                                  <div className="bg-amber-950/20 border border-amber-900/30 p-4 rounded-xl space-y-2">
                                    <h4 className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                                      ✉️ Recruiter Outreach Message
                                    </h4>
                                    <p className="text-xs text-gray-400"><strong>Subject:</strong> {scorecard.outbound_subject}</p>
                                    <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed mt-1 border-t border-amber-900/20 pt-2">{scorecard.outbound_body}</p>
                                    {scorecard.sent_actual !== undefined && (
                                      <p className="text-[9px] text-gray-500 italic mt-1">
                                        Status: {scorecard.sent_actual ? "Sent via SMTP" : "Simulated Delivery"}
                                      </p>
                                    )}
                                  </div>
                                )}

                                {/* Candidate Reply detail */}
                                {scorecard.candidate_reply && (
                                  <div className="bg-emerald-950/20 border border-emerald-900/30 p-4 rounded-xl space-y-2">
                                    <h4 className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                                      💬 Candidate Reply
                                    </h4>
                                    <p className="text-xs text-gray-300 whitespace-pre-wrap leading-relaxed">{scorecard.candidate_reply}</p>
                                  </div>
                                )}

                                {/* Interview Booking details */}
                                {scorecard.meeting_time && (
                                  <div className="bg-purple-950/20 border border-purple-900/30 p-4 rounded-xl space-y-2">
                                    <h4 className="text-[10px] font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                                      📅 Booked Interview
                                    </h4>
                                    <p className="text-xs text-gray-300"><strong>Time:</strong> {scorecard.meeting_time}</p>
                                    <p className="text-xs text-gray-300">
                                      <strong>Google Meet Link: </strong>
                                      <a href={scorecard.meeting_link} target="_blank" rel="noreferrer" className="text-violet-400 hover:text-violet-300 underline font-semibold transition-colors">
                                        {scorecard.meeting_link}
                                      </a>
                                    </p>
                                    {scorecard.calendar_booked !== undefined && (
                                      <p className="text-[9px] text-gray-500 italic mt-1">
                                        Status: {scorecard.calendar_booked ? "Created Google Calendar Event" : "Simulated Schedule"}
                                      </p>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Actions footer */}
                            <div className="px-5 py-3 bg-gray-950/30 flex gap-2 justify-end border-t border-gray-800">
                              {candidate.status === 'sourced' && (
                                <Button
                                  size="sm"
                                  onClick={() => handleCandidateOutreach(candidate.id)}
                                  disabled={outreachLoading}
                                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold h-9 px-4 rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all hover:scale-[1.02] active:scale-95 text-xs"
                                >
                                  {outreachLoading ? 'Sending...' : 'Send Outreach Email'}
                                </Button>
                              )}
                              {candidate.status === 'screened' && (
                                <Button
                                  size="sm"
                                  onClick={() => handleScheduleInterview(candidate.id)}
                                  disabled={interviewLoading}
                                  className="bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white font-bold h-9 px-4 rounded-xl shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all hover:scale-[1.02] active:scale-95 text-xs"
                                >
                                  {interviewLoading ? 'Scheduling...' : 'Simulate Reply & Book Interview'}
                                </Button>
                              )}
                              {candidate.status === 'interviewed' && (
                                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                                  ✓ Interview Scheduled
                                </span>
                              )}
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* VIEW: AGENT BOARDROOM */}
          {activeView === 'coordination' && (
            <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <Users className="text-amber-400 h-8 w-8 animate-pulse" /> AI Agent Boardroom
                  </h1>
                  <p className="text-gray-400 mt-1">Cross-agent coordination meetings, autonomous escalations, and executive boardroom alignments.</p>
                </div>
                <div className="flex gap-2">
                  <Dialog open={isCreateMeetingOpen} onOpenChange={setIsCreateMeetingOpen}>
                    <DialogTrigger render={
                      <Button className="bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold h-10 px-5 rounded-xl shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] active:scale-95 text-xs flex items-center gap-1.5" />
                    }>
                      <Users size={16} /> Summon Boardroom Meeting
                    </DialogTrigger>
                    <DialogContent className="glass-panel border border-gray-800 text-white max-w-md rounded-2xl p-6">
                      <DialogHeader>
                        <DialogTitle className="text-xl font-bold text-white">Call AI Boardroom Meeting</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 mt-4">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-gray-400">Meeting Title</label>
                          <Input
                            placeholder="e.g. Q3 Strategic Marketing Alignment"
                            value={manualMeetingTitle}
                            onChange={(e) => setManualMeetingTitle(e.target.value)}
                            className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs h-10"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-gray-400">Meeting Topic / Agenda Context</label>
                          <Textarea
                            placeholder="Detail what the agents need to coordinate on..."
                            value={manualMeetingTopic}
                            onChange={(e) => setManualMeetingTopic(e.target.value)}
                            className="bg-gray-900 border-gray-800 text-white rounded-xl text-xs min-h-24"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-xs font-semibold text-gray-400">Invite Department Specialists (CEO AI always coordinates)</label>
                          <div className="grid grid-cols-2 gap-2 mt-1">
                            {['Support AI', 'Sales AI', 'Finance AI', 'HR AI', 'Marketing AI'].map(agentName => {
                              const isChecked = manualMeetingParticipants.includes(agentName);
                              return (
                                <button
                                  key={agentName}
                                  type="button"
                                  onClick={() => {
                                    if (isChecked) {
                                      setManualMeetingParticipants(manualMeetingParticipants.filter(p => p !== agentName));
                                    } else {
                                      setManualMeetingParticipants([...manualMeetingParticipants, agentName]);
                                    }
                                  }}
                                  className={`px-3 py-2 rounded-xl text-xs font-semibold border transition-all text-left flex items-center justify-between ${
                                    isChecked
                                      ? 'bg-amber-600/20 border-amber-500 text-white'
                                      : 'bg-gray-900/50 border-gray-800 text-gray-400 hover:border-gray-700'
                                  }`}
                                >
                                  {agentName}
                                  {isChecked && <span className="text-amber-400 font-bold">✓</span>}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                        <Button
                          onClick={handleCreateManualMeeting}
                          disabled={manualMeetingLoading || !manualMeetingTitle || !manualMeetingTopic}
                          className="w-full bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold h-11 rounded-xl shadow-lg mt-4 shadow-amber-500/20"
                        >
                          {manualMeetingLoading ? 'Summoning Agents...' : 'Summon Boardroom'}
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* 1. Meeting List Side-Panel */}
                <div className="lg:col-span-1 space-y-6">
                  <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative">
                    <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                    <CardHeader>
                      <CardTitle className="text-xl text-white font-extrabold tracking-tight">Boardroom Sessions</CardTitle>
                      <CardDescription className="text-gray-400 text-xs mt-1">Select an active or archived courtroom/boardroom simulation.</CardDescription>
                    </CardHeader>
                    <CardContent className="px-2 pb-6">
                      {meetings.length === 0 ? (
                        <p className="text-xs text-gray-500 text-center py-10">No boardroom sessions found. Trigger an escalation from support or call one manually.</p>
                      ) : (
                        <div className="flex flex-col gap-2 max-h-[500px] overflow-y-auto pr-1">
                          {meetings.map((m) => {
                            const isSelected = selectedMeetingId === m.id;
                            const isCompleted = m.status === 'completed';
                            return (
                              <div
                                key={m.id}
                                onClick={() => setSelectedMeetingId(m.id)}
                                className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col gap-2 ${
                                  isSelected
                                    ? 'bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.12)] shadow-xl'
                                    : 'bg-transparent border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.02)]'
                                }`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                                    m.trigger_type === 'support_ticket'
                                      ? 'bg-blue-900/30 text-blue-400 border border-blue-900/40'
                                      : m.trigger_type === 'manual'
                                      ? 'bg-purple-900/30 text-purple-400 border border-purple-900/40'
                                      : 'bg-amber-900/30 text-amber-400 border border-amber-900/40'
                                  }`}>
                                    {m.trigger_type}
                                  </span>
                                  <span className={`flex items-center gap-1 text-[10px] font-bold ${
                                    isCompleted ? 'text-emerald-400' : 'text-amber-400'
                                  }`}>
                                    <span className={`h-1.5 w-1.5 rounded-full ${isCompleted ? 'bg-emerald-400' : 'bg-amber-400 animate-ping'}`} />
                                    {m.status}
                                  </span>
                                </div>
                                <h3 className="font-bold text-white text-sm leading-tight">{m.title}</h3>
                                <p className="text-gray-400 text-xs line-clamp-1">{m.context_summary?.replace(/Custom Topic:|Inquiry:/g, '').trim()}</p>
                                <span className="text-[10px] text-gray-500 text-right mt-1">
                                  {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* 2. Main Visual Boardroom Panel & Action items */}
                <div className="lg:col-span-2 space-y-6">
                  {selectedMeetingId && selectedMeeting ? (
                    <div className="space-y-6">
                      {/* Interactive Boardroom Table visualization */}
                      <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                        <CardTitle className="text-lg text-white font-extrabold mb-4">Boardroom Table Status</CardTitle>
                        
                        {/* Oval Boardroom Table representation */}
                        <div className="relative bg-gray-950/60 rounded-3xl border border-gray-800 p-8 min-h-60 flex items-center justify-center">
                          <div className="absolute inset-8 border-2 border-dashed border-amber-500/20 rounded-full flex items-center justify-center bg-gray-900/45">
                            <span className="text-xs text-amber-500/40 uppercase tracking-widest font-black">AI Executive Board</span>
                          </div>
                          
                          {/* Render participants positioned dynamically around the table */}
                          <div className="w-full grid grid-cols-3 gap-6 relative z-10">
                            {['CEO AI', 'Support AI', 'Sales AI', 'Finance AI', 'HR AI', 'Marketing AI'].map((agentName) => {
                              const isParticipant = selectedMeeting.participants.includes(agentName);
                              if (!isParticipant) return null;
                              
                              // Check if this agent sent the last message in the transcript
                              const lastMsg = selectedMeeting.transcript && selectedMeeting.transcript.length > 0
                                ? selectedMeeting.transcript[selectedMeeting.transcript.length - 1]
                                : null;
                              const isSpeaking = lastMsg && lastMsg.sender === agentName;
                              
                              return (
                                <div
                                  key={agentName}
                                  className={`flex flex-col items-center p-3 rounded-2xl border transition-all duration-300 ${
                                    isSpeaking
                                      ? 'bg-amber-600/10 border-amber-500 scale-105 shadow-lg shadow-amber-500/15'
                                      : 'bg-gray-900/80 border-gray-800/80 opacity-70'
                                  }`}
                                >
                                  <div className={`p-2 rounded-full mb-2 ${
                                    isSpeaking ? 'bg-amber-500 text-gray-950' : 'bg-gray-800 text-gray-400'
                                  }`}>
                                    <Users size={20} />
                                  </div>
                                  <span className="text-xs font-bold text-white">{agentName}</span>
                                  <span className="text-[10px] text-gray-400 text-center mt-1">
                                    {isSpeaking ? (
                                      <span className="text-amber-400 font-bold animate-pulse">● Speaking...</span>
                                    ) : (
                                      <span>Participant</span>
                                    )}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </Card>

                      {/* Live Discussion Transcript */}
                      <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                        <div className="flex justify-between items-center mb-4">
                          <CardTitle className="text-lg text-white font-extrabold flex items-center gap-2">
                            <MessageSquare className="text-amber-500" size={18} /> Discussion Transcript
                          </CardTitle>
                          <span className="text-xs text-gray-400">{selectedMeeting.transcript?.length || 0} messages</span>
                        </div>

                        <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
                          {selectedMeeting.transcript?.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-10 space-y-2">
                              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-amber-500" />
                              <p className="text-xs text-gray-500">Boardroom assembling. Agents are analyzing context and entering boardroom...</p>
                            </div>
                          ) : (
                            selectedMeeting.transcript.map((msg: any, idx: number) => {
                              const isCEO = msg.sender === 'CEO AI';
                              return (
                                <div key={idx} className={`p-4 rounded-2xl border transition-all ${
                                  isCEO
                                    ? 'bg-amber-950/20 border-amber-900/30'
                                    : 'bg-gray-900/50 border-gray-800/80'
                                }`}>
                                  <div className="flex justify-between items-center mb-1">
                                    <span className={`text-xs font-bold ${isCEO ? 'text-amber-400' : 'text-white'}`}>
                                      {msg.sender}
                                    </span>
                                    <span className="text-[9px] text-gray-500">{msg.timestamp}</span>
                                  </div>
                                  <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </Card>

                      {/* Action Items Panel */}
                      <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-6">
                        <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                        <CardTitle className="text-lg text-white font-extrabold mb-4 flex items-center gap-2">
                          <Zap className="text-amber-500" size={18} /> CEO Board Directives & Action Items
                        </CardTitle>
                        
                        <div className="space-y-3">
                          {selectedMeeting.action_items?.length === 0 ? (
                            <p className="text-xs text-gray-500 py-4 text-center">Waiting for meeting to conclude to establish boardroom directives...</p>
                          ) : (
                            selectedMeeting.action_items.map((action: any) => {
                              const isComp = action.status === 'completed';
                              const isExec = action.status === 'executing';
                              const isFail = action.status === 'failed';
                              
                              return (
                                <div
                                  key={action.id}
                                  className={`p-4 rounded-xl border flex items-center justify-between gap-4 transition-all ${
                                    isComp
                                      ? 'bg-emerald-950/15 border-emerald-900/35 text-emerald-100'
                                      : isExec
                                      ? 'bg-amber-950/15 border-amber-900/35 text-amber-100'
                                      : isFail
                                      ? 'bg-red-950/15 border-red-900/35 text-red-100'
                                      : 'bg-gray-900/50 border-gray-800 text-gray-300'
                                  }`}
                                >
                                  <div className="flex flex-col gap-1">
                                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-400">
                                      {action.assigned_to}
                                    </span>
                                    <p className="text-xs">{action.description}</p>
                                  </div>
                                  <div className="flex items-center">
                                    {isComp && (
                                      <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                                        ✓ Completed
                                      </span>
                                    )}
                                    {isExec && (
                                      <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                                        <span className="animate-spin rounded-full h-3 w-3 border-b-2 border-amber-400" />
                                        Executing...
                                      </span>
                                    )}
                                    {isFail && (
                                      <span className="text-xs font-bold text-red-400 flex items-center gap-1">
                                        ✗ Failed
                                      </span>
                                    )}
                                    {action.status === 'pending' && (
                                      <span className="text-xs font-bold text-gray-500">
                                        Pending
                                      </span>
                                    )}
                                  </div>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </Card>
                    </div>
                  ) : (
                    <Card className="glass-panel border-transparent rounded-3xl overflow-hidden shadow-2xl relative p-12 text-center flex flex-col items-center justify-center min-h-[500px]">
                      <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500 to-transparent" />
                      <div className="p-4 bg-amber-500/10 text-amber-500 rounded-full mb-4">
                        <Users size={36} />
                      </div>
                      <h2 className="text-2xl font-bold text-white">Welcome to the AI Boardroom</h2>
                      <p className="text-gray-400 text-sm max-w-md mt-2">
                        Escalated ticket events automatically trigger emergency board meetings here. CEO AI and specialized department AI employees gather in real-time, align on context, and formulate auto-executing directives.
                      </p>
                      <Button
                        onClick={() => setIsCreateMeetingOpen(true)}
                        className="mt-6 bg-gradient-to-r from-amber-600 to-yellow-600 hover:from-amber-500 hover:to-yellow-500 text-white font-bold h-10 px-6 rounded-xl shadow-lg shadow-amber-500/20"
                      >
                        Summon Boardroom Meeting
                      </Button>
                    </Card>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* VIEW: AI COST CONTROL */}
          {activeView === 'ai_optimization' && (
            <div className="space-y-8 max-w-7xl mx-auto animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                    <DollarSign className="text-emerald-400 h-8 w-8 animate-pulse" /> AI Cost Control Center
                  </h1>
                  <p className="text-gray-400 mt-1">Standardise provider APIs, optimize token usage, route workloads dynamically, and track latency savings.</p>
                </div>
                <div className="flex items-center gap-2 bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.06)] px-4 py-2 rounded-xl text-xs text-gray-400 font-semibold shadow-inner">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>AI Cost Optimization Layer Active</span>
                </div>
              </div>

              {/* Top stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card className="glass-panel border-emerald-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-emerald-500" />
                  <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Total Optimised Spend</CardTitle>
                    <DollarSign className="h-4 w-4 text-emerald-450" />
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <div className="text-3xl font-black text-white">${optimizationMetrics?.total_spend?.toFixed(4) || "0.0000"}</div>
                    <p className="text-[10px] text-gray-500 font-medium">{optimizationMetrics?.active_providers?.length || 0} active providers connected</p>
                  </CardContent>
                </Card>

                <Card className="glass-panel border-violet-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-violet-500" />
                  <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Universal Cache Hit Rate</CardTitle>
                    <Zap className="h-4 w-4 text-violet-400" />
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <div className="text-3xl font-black text-white">{optimizationMetrics?.cache_metrics?.hit_rate || 0}%</div>
                    <p className="text-[10px] text-gray-500 font-medium">{optimizationMetrics?.cache_metrics?.hits || 0} hits out of {optimizationMetrics?.cache_metrics?.total_calls || 0} requests</p>
                  </CardContent>
                </Card>

                <Card className="glass-panel border-blue-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-blue-500" />
                  <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Latency Saved</CardTitle>
                    <Clock className="h-4 w-4 text-blue-400" />
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <div className="text-3xl font-black text-white">{optimizationMetrics?.cache_metrics?.latency_saved || 0}s</div>
                    <p className="text-[10px] text-gray-500 font-medium">Bypassed LLM processing delays</p>
                  </CardContent>
                </Card>

                <Card className="glass-panel border-amber-500/20 relative overflow-hidden transition-all duration-300 hover:scale-[1.03] rounded-2xl shadow-lg">
                  <div className="absolute top-0 left-0 w-1.5 h-full bg-amber-500" />
                  <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Estimated Cost Savings</CardTitle>
                    <BarChart3 className="h-4 w-4 text-amber-400" />
                  </CardHeader>
                  <CardContent className="space-y-1">
                    <div className="text-3xl font-black text-emerald-400">+${((optimizationMetrics?.cache_metrics?.savings || 0) + (optimizationMetrics?.batch_metrics?.async_savings || 0)).toFixed(4)}</div>
                    <p className="text-[10px] text-gray-500 font-medium">From cache hits and batch runs</p>
                  </CardContent>
                </Card>
              </div>

              {/* Providers Status & Telemetry */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <Card className="lg:col-span-8 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-4 border-b border-gray-800 pb-4">
                    <div>
                      <h3 className="font-extrabold text-lg text-white">Universal AI Providers Gateway</h3>
                      <p className="text-xs text-gray-400">Standardised provider telemetry, average latency, and configuration state.</p>
                    </div>
                    <span className="text-[10px] text-violet-400 font-bold uppercase tracking-wider font-mono">Dynamic Fallback Active</span>
                  </div>

                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader className="bg-gray-950/40 border-b border-gray-800">
                        <TableRow className="border-gray-800 hover:bg-transparent">
                          <TableHead className="text-gray-400 font-bold text-xs p-4">Provider</TableHead>
                          <TableHead className="text-gray-400 font-bold text-xs p-4">Status</TableHead>
                          <TableHead className="text-gray-400 font-bold text-xs p-4">Avg Latency</TableHead>
                          <TableHead className="text-gray-400 font-bold text-xs p-4">Uptime / Health</TableHead>
                          <TableHead className="text-gray-400 font-bold text-xs p-4 text-right">Failover Count</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody className="divide-y divide-gray-800">
                        {Object.entries(optimizationMetrics?.provider_metrics || {}).map(([p, metrics]: [string, any]) => {
                          const isConfigured = optimizationMetrics?.active_providers?.includes(p.toLowerCase()) || p === "mock";
                          return (
                            <TableRow key={p} className="border-gray-800 hover:bg-gray-900/20">
                              <TableCell className="p-4 whitespace-nowrap">
                                <div className="flex items-center gap-2">
                                  <div className="bg-gradient-to-tr from-violet-600 to-indigo-600 p-1 rounded text-white text-[10px] font-bold uppercase w-16 text-center">
                                    {p}
                                  </div>
                                  <span className="text-xs text-white capitalize font-semibold">{p}</span>
                                </div>
                              </TableCell>
                              <TableCell className="p-4">
                                <span className={`inline-flex items-center gap-1 border px-2 py-0.5 rounded text-[10px] font-bold ${
                                  isConfigured 
                                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                    : 'bg-gray-800/60 text-gray-500 border-gray-700/60'
                                }`}>
                                  {isConfigured ? "● Connected" : "○ Not Configured"}
                                </span>
                              </TableCell>
                              <TableCell className="p-4 text-xs font-mono text-gray-300">
                                {isConfigured ? `${metrics.avg_latency || "0.0"}s` : "N/A"}
                              </TableCell>
                              <TableCell className="p-4 text-xs font-semibold text-gray-300">
                                {metrics.uptime}%
                              </TableCell>
                              <TableCell className="p-4 text-right text-xs font-mono text-rose-400">
                                {metrics.failed_calls + metrics.failover_calls}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </Card>

                {/* Cache Metrics */}
                <Card className="lg:col-span-4 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-4">
                      <h3 className="font-extrabold text-lg text-white">Universal Cache</h3>
                      <Zap className="text-violet-400 h-5 w-5" />
                    </div>

                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between text-xs font-semibold text-gray-400 mb-1.5">
                          <span>Prompt Hit Rate</span>
                          <span className="text-violet-400 font-bold">{optimizationMetrics?.cache_metrics?.hit_rate || 0}%</span>
                        </div>
                        <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                          <div 
                            className="bg-gradient-to-r from-violet-600 to-indigo-600 h-full rounded-full transition-all duration-500"
                            style={{ width: `${optimizationMetrics?.cache_metrics?.hit_rate || 0}%` }}
                          />
                        </div>
                      </div>

                      <div className="bg-[rgba(0,0,0,0.15)] border border-gray-800 p-4 rounded-xl space-y-3 shadow-inner">
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-400">Cache Hits Count:</span>
                          <span className="font-mono text-white font-bold">{optimizationMetrics?.cache_metrics?.hits || 0}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-400">Token Reuse (Saved):</span>
                          <span className="font-mono text-emerald-400 font-bold">{(optimizationMetrics?.cache_metrics?.token_reuse || 0).toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-400">Cache Caching Layer:</span>
                          <span className="text-violet-400 font-bold font-mono">Redis DB 1</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="text-[11px] text-violet-300/80 bg-violet-500/5 border border-violet-500/10 p-3 rounded-lg flex items-start gap-2 mt-4">
                    <Zap size={14} className="mt-0.5 flex-shrink-0" />
                    <p>
                      <strong>Optimize logic:</strong> Prompts matching Global, Department or Workflow templates bypass LLM endpoints. Saves 100% tokens and execution lag.
                    </p>
                  </div>
                </Card>
              </div>

              {/* Workload Routing & Batching */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Routing Distribution */}
                <Card className="lg:col-span-6 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden">
                  <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-4">
                    <h3 className="font-extrabold text-lg text-white">Dynamic Department Workload Routing</h3>
                    <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider font-mono">Routing Analytics</span>
                  </div>

                  <div className="space-y-4">
                    {Object.entries(optimizationMetrics?.routing_analytics || {}).map(([dept, providers]: [string, any]) => {
                      const totalDeptCalls = Object.values(providers).reduce((a: any, b: any) => a + b, 0) as number;
                      return (
                        <div key={dept} className="space-y-1.5">
                          <div className="flex justify-between text-xs">
                            <span className="font-bold text-white capitalize">{dept} tasks</span>
                            <span className="text-gray-400 text-[10px]">{totalDeptCalls} requests</span>
                          </div>
                          
                          {totalDeptCalls > 0 ? (
                            <div className="w-full bg-gray-800 h-3 rounded-md overflow-hidden flex">
                              {Object.entries(providers).map(([provider, count]: [string, any]) => {
                                const pct = (count / totalDeptCalls) * 100;
                                const colors: any = {
                                  openai: "bg-emerald-500",
                                  anthropic: "bg-violet-600",
                                  gemini: "bg-blue-500",
                                  groq: "bg-orange-500",
                                  grok: "bg-purple-600",
                                  local: "bg-teal-500",
                                  mock: "bg-gray-600"
                                };
                                const bgClass = colors[provider.toLowerCase()] || "bg-indigo-600";
                                return (
                                  <div 
                                    key={provider} 
                                    className={`${bgClass} h-full transition-all`}
                                    style={{ width: `${pct}%` }}
                                    title={`${provider}: ${pct.toFixed(0)}%`}
                                  />
                                );
                              })}
                            </div>
                          ) : (
                            <div className="w-full bg-gray-800 h-3 rounded-md text-[9px] text-center text-gray-500 font-bold flex items-center justify-center">
                              No calls routed yet
                            </div>
                          )}

                          {/* Percentages row */}
                          <div className="flex gap-2.5 flex-wrap text-[9px] font-semibold text-gray-400 mt-1">
                            {Object.entries(providers).map(([provider, count]: [string, any]) => {
                              const pct = ((count / totalDeptCalls) * 100).toFixed(0);
                              return (
                                <span key={provider} className="flex items-center gap-1">
                                  <span className={`h-1.5 w-1.5 rounded-full ${
                                    provider === 'openai' ? 'bg-emerald-500' :
                                    provider === 'anthropic' ? 'bg-violet-600' :
                                    provider === 'gemini' ? 'bg-blue-500' : 'bg-gray-450'
                                  }`} />
                                  <span className="capitalize text-[10px]">{provider}</span> ({pct}%)
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>

                {/* Batch Jobs */}
                <Card className="lg:col-span-6 glass-panel border-[rgba(255,255,255,0.06)] rounded-3xl p-6 shadow-2xl relative overflow-hidden flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-4">
                      <h3 className="font-extrabold text-lg text-white">Batch Orchestration System</h3>
                      <span className="text-[10px] text-amber-400 font-bold uppercase tracking-wider font-mono">Async Batch Telemetry</span>
                    </div>

                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div className="p-3 border border-gray-800 rounded-xl bg-gray-950/20 text-center shadow-inner">
                        <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider block">Jobs Processed</span>
                        <div className="text-xl font-black text-white mt-1">{optimizationMetrics?.batch_metrics?.total_jobs || 0}</div>
                      </div>
                      <div className="p-3 border border-gray-800 rounded-xl bg-gray-950/20 text-center shadow-inner">
                        <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider block">Tasks Completed</span>
                        <div className="text-xl font-black text-white mt-1">{optimizationMetrics?.batch_metrics?.total_tasks_processed || 0}</div>
                      </div>
                      <div className="p-3 border border-gray-800 rounded-xl bg-gray-950/20 text-center shadow-inner bg-emerald-500/5 border-emerald-500/10">
                        <span className="text-[9px] font-bold text-emerald-450 uppercase tracking-wider block">Batch Savings</span>
                        <div className="text-xl font-black text-emerald-400 mt-1">${optimizationMetrics?.batch_metrics?.async_savings?.toFixed(2) || "0.00"}</div>
                      </div>
                    </div>

                    <div className="bg-[rgba(0,0,0,0.15)] border border-gray-800 p-4 rounded-xl space-y-3 shadow-inner">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Processing Jobs:</span>
                        <span className="font-mono text-white font-bold flex items-center gap-1.5">
                          {optimizationMetrics?.batch_metrics?.processing_jobs || 0}
                          {optimizationMetrics?.batch_metrics?.processing_jobs > 0 && (
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Completed Jobs:</span>
                        <span className="font-mono text-white font-bold">{optimizationMetrics?.batch_metrics?.completed_jobs || 0}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">Failed Jobs:</span>
                        <span className="font-mono text-rose-450 font-bold">{optimizationMetrics?.batch_metrics?.failed_jobs || 0}</span>
                      </div>
                    </div>
                  </div>

                  <div className="text-[11px] text-amber-300/80 bg-amber-500/5 border border-amber-500/10 p-3 rounded-lg flex items-start gap-2 mt-4">
                    <Clock size={14} className="mt-0.5 flex-shrink-0" />
                    <p>
                      <strong>Batch API integration:</strong> Supports native API batch submission (e.g. OpenAI/Anthropic 50% discount) or fallbacks to Celery queue simulation.
                    </p>
                  </div>
                </Card>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

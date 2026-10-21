'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Save, SlidersHorizontal, ShieldCheck, Mail, Bot, 
  Sparkles, CheckCircle2, Loader2, Globe, Clock
} from 'lucide-react';
import TriggerScheduleCard from '@/components/ui/trigger-schedule-card';
import { BusinessProfileData, SalesSettings } from './sales-types';

interface SalesConfigPanelProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  profile: BusinessProfileData;
  setProfile: (updater: (prev: BusinessProfileData) => BusinessProfileData) => void;
  salesSettings: SalesSettings;
  onSaveSalesSettings: (next: SalesSettings) => Promise<void>;
  salesSettingsSaving: boolean;
  onSaveProfile: () => Promise<void>;
  profileSaving: boolean;
  onRunWorkflowSuccess: () => void;
}

export default function SalesConfigPanel({
  API_URL,
  fetchWithAuth,
  profile,
  setProfile,
  salesSettings,
  onSaveSalesSettings,
  salesSettingsSaving,
  onSaveProfile,
  profileSaving,
  onRunWorkflowSuccess,
}: SalesConfigPanelProps) {
  const updateField = (field: keyof BusinessProfileData, val: any) => {
    setProfile((prev) => ({ ...prev, [field]: val }));
  };

  return (
    <div className="space-y-6">
      {/* Autonomous Scheduled Lead Generation Trigger */}
      <TriggerScheduleCard
        title="⚡ Autonomous Lead Generation Triggers"
        subtitle="Schedule automated high-intent prospect sourcing and qualification runs (e.g. Daily at 3:00 PM)."
        targetType="lead_generation"
        API_URL={API_URL}
        fetchWithAuth={fetchWithAuth}
        defaultInstructions={profile.extra_context}
        onRunSuccess={onRunWorkflowSuccess}
      />

      {/* Prospect Reply & Automation Governance */}
      <Card className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <span className="w-1.5 h-4 bg-blue-600 rounded-full inline-block" />
            <ShieldCheck size={16} className="text-blue-600" />
            Prospect Reply &amp; Autonomous Meeting Governance
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure how your AI agent handles prospect responses and meeting invitations.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Reply Mode */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2.5">
            <span className="text-xs font-bold text-slate-800 block">
              Inbound Reply Mode {salesSettingsSaving ? '· saving…' : ''}
            </span>
            <p className="text-xs text-slate-500 leading-relaxed">
              {salesSettings.reply_mode === 'review_first'
                ? 'AI drafts replies to prospect emails → requires human approval in the Approvals queue before dispatch.'
                : 'AI autonomously crafts and dispatches grounded responses after a brief review delay.'}
            </p>
            <div className="flex rounded-xl overflow-hidden border border-slate-200 bg-white">
              <button
                type="button"
                onClick={() =>
                  onSaveSalesSettings({
                    ...salesSettings,
                    reply_mode: 'review_first',
                    sales_auto_reply: true,
                  })
                }
                className={`flex-1 py-2 text-xs font-bold transition-colors ${
                  salesSettings.reply_mode === 'review_first'
                    ? 'bg-amber-100 text-amber-900 border-r border-amber-200'
                    : 'bg-white text-slate-600 hover:text-slate-900'
                }`}
              >
                Review First (HITL)
              </button>
              <button
                type="button"
                onClick={() =>
                  onSaveSalesSettings({
                    ...salesSettings,
                    reply_mode: 'auto_send',
                    sales_auto_reply: true,
                  })
                }
                className={`flex-1 py-2 text-xs font-bold transition-colors border-l border-slate-200 ${
                  salesSettings.reply_mode === 'auto_send'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-slate-600 hover:text-slate-900'
                }`}
              >
                Autonomous Auto-Send
              </button>
            </div>
          </div>

          {/* Auto Book Meetings */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2.5">
            <span className="text-xs font-bold text-slate-800 block">
              Auto-Booking Meetings
            </span>
            <p className="text-xs text-slate-500 leading-relaxed">
              When an interested prospect agrees to a call, automatically generate Google Meet link and send pre-meeting brief.
            </p>
            <label className="flex items-center gap-2.5 text-xs text-slate-800 cursor-pointer pt-2 font-medium">
              <input
                type="checkbox"
                checked={salesSettings.auto_book_meetings}
                onChange={(e) =>
                  onSaveSalesSettings({
                    ...salesSettings,
                    auto_book_meetings: e.target.checked,
                  })
                }
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span>Enable Instant Autonomous Meeting Scheduling</span>
            </label>
          </div>
        </div>

        {/* Follow-up Cadence & Sequence Settings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2">
            <span className="text-xs font-bold text-slate-800 block">
              Follow-Up Cadence Interval (Days)
            </span>
            <p className="text-[11px] text-slate-500">
              Spacing between automated outbound follow-up touches across channels.
            </p>
            <Input
              type="number"
              min={1}
              max={30}
              value={salesSettings.follow_up_cadence_days || 3}
              onChange={(e) =>
                onSaveSalesSettings({
                  ...salesSettings,
                  follow_up_cadence_days: Math.max(1, parseInt(e.target.value) || 3),
                })
              }
              className="text-xs bg-white border-slate-200 text-slate-900 w-32"
            />
          </div>

          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-2">
            <span className="text-xs font-bold text-slate-800 block">
              Max Sequence Touchpoints
            </span>
            <p className="text-[11px] text-slate-500">
              Maximum total outreach touches per qualified prospect before marking as unresponsive.
            </p>
            <Input
              type="number"
              min={1}
              max={15}
              value={salesSettings.max_ai_touchpoints || 5}
              onChange={(e) =>
                onSaveSalesSettings({
                  ...salesSettings,
                  max_ai_touchpoints: Math.max(1, parseInt(e.target.value) || 5),
                })
              }
              className="text-xs bg-white border-slate-200 text-slate-900 w-32"
            />
          </div>
        </div>
      </Card>

      {/* Business Profile & ICP Editor */}
      <Card className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm space-y-5">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-blue-600 rounded-full inline-block" />
              <SlidersHorizontal size={16} className="text-blue-600" />
              Organization Business Profile &amp; Playbook Parameters
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              These parameters guide autonomous domain archetype classification, target ICP scoring, and negative exclusions.
            </p>
          </div>
          <Button
            onClick={onSaveProfile}
            disabled={profileSaving}
            className="text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 h-9 shadow-sm"
          >
            {profileSaving ? (
              <>
                <Loader2 size={13} className="animate-spin mr-1.5" /> Saving...
              </>
            ) : (
              <>
                <Save size={13} className="mr-1.5" /> Save Playbook
              </>
            )}
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-bold text-slate-600 block mb-1">Company / Product Name</label>
            <Input
              value={profile.company_name}
              onChange={(e) => updateField('company_name', e.target.value)}
              placeholder="e.g. Acme Cloud"
              className="text-xs bg-slate-50 border-slate-200 text-slate-900"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-slate-600 block mb-1">Website URL</label>
            <Input
              value={profile.website}
              onChange={(e) => updateField('website', e.target.value)}
              placeholder="https://acme.com"
              className="text-xs bg-slate-50 border-slate-200 text-slate-900"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-slate-600 block mb-1">Industry Sector</label>
            <Input
              value={profile.industry}
              onChange={(e) => updateField('industry', e.target.value)}
              placeholder="B2B SaaS, Manufacturing, Healthcare..."
              className="text-xs bg-slate-50 border-slate-200 text-slate-900"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-slate-600 block mb-1">Target Decision Makers</label>
            <Input
              value={profile.target_decision_makers}
              onChange={(e) => updateField('target_decision_makers', e.target.value)}
              placeholder="Founder, CEO, VP of Sales, CTO..."
              className="text-xs bg-slate-50 border-slate-200 text-slate-900"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-slate-600 block mb-1">Target Geographies / Countries</label>
            <Input
              value={profile.target_countries}
              onChange={(e) => updateField('target_countries', e.target.value)}
              placeholder="United States, United Kingdom, UAE..."
              className="text-xs bg-slate-50 border-slate-200 text-slate-900"
            />
          </div>
          <div>
            <label className="text-xs font-bold text-slate-600 block mb-1">Target Budget Range</label>
            <Input
              value={profile.target_budget_range}
              onChange={(e) => updateField('target_budget_range', e.target.value)}
              placeholder="e.g. $1,000 - $10,000"
              className="text-xs bg-slate-50 border-slate-200 text-slate-900"
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-bold text-slate-600 block mb-1">
            Product / Service Offering Description
          </label>
          <Textarea
            rows={3}
            value={profile.service_description}
            onChange={(e) => updateField('service_description', e.target.value)}
            placeholder="Describe what your product does, core features, and the primary pain it solves..."
            className="text-xs bg-slate-50 border-slate-200 text-slate-900"
          />
        </div>

        <div>
          <label className="text-xs font-bold text-slate-600 block mb-1">
            Unique Selling Proposition (USP) &amp; Differentiators
          </label>
          <Textarea
            rows={2}
            value={profile.usp}
            onChange={(e) => updateField('usp', e.target.value)}
            placeholder="Why should customers choose you over competitors? Key ROI drivers..."
            className="text-xs bg-slate-50 border-slate-200 text-slate-900"
          />
        </div>

        <div>
          <label className="text-xs font-bold text-slate-600 block mb-1">
            Extra Research Directives &amp; Negative ICP Exclusions
          </label>
          <Textarea
            rows={2}
            value={profile.extra_context}
            onChange={(e) => updateField('extra_context', e.target.value)}
            placeholder="Do not target agencies, only look for businesses with verifiable email domains..."
            className="text-xs bg-slate-50 border-slate-200 text-slate-900"
          />
        </div>

        <div className="flex justify-end pt-2">
          <Button
            onClick={onSaveProfile}
            disabled={profileSaving}
            className="text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-6 h-10 shadow-sm"
          >
            {profileSaving ? (
              <>
                <Loader2 size={14} className="animate-spin mr-1.5" /> Saving Changes...
              </>
            ) : (
              <>
                <Save size={14} className="mr-1.5" /> Save Business Profile
              </>
            )}
          </Button>
        </div>
      </Card>
    </div>
  );
}

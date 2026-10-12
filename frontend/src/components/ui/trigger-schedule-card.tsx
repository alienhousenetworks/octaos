'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Bell,
  Clock,
  Trash2,
  Play,
  Save,
  CheckCircle2,
  Calendar,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Zap,
  RotateCw,
} from 'lucide-react';
import { notify } from '@/lib/notify';

export interface TriggerScheduleData {
  id?: string | null;
  target_type: string;
  frequency: string; // 'once' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly'
  time_of_day: string; // 'HH:MM' (24-hr)
  day_of_week?: number; // 0=Mon .. 6=Sun
  day_of_month?: number;
  interval_hours?: number;
  instructions: string;
  config?: Record<string, any>;
  is_active: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
  last_status?: string;
}

interface TriggerScheduleCardProps {
  title?: string;
  subtitle?: string;
  targetType: 'lead_generation' | 'campaign_planner';
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  defaultInstructions?: string;
  extraConfig?: Record<string, any>;
  onRunSuccess?: () => void;
  className?: string;
}

const FREQUENCIES = [
  { id: 'once', label: 'Once' },
  { id: 'hourly', label: 'Hourly' },
  { id: 'daily', label: 'Daily' },
  { id: 'weekly', label: 'Weekly' },
  { id: 'monthly', label: 'Monthly' },
  { id: 'yearly', label: 'Yearly' },
];

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function TriggerScheduleCard({
  title = 'Autonomous Agent Triggers',
  subtitle = 'Configure scheduled routines and specific agent prompt instructions.',
  targetType,
  API_URL,
  fetchWithAuth,
  defaultInstructions = '',
  extraConfig = {},
  onRunSuccess,
  className = '',
}: TriggerScheduleCardProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  // Trigger state
  const [frequency, setFrequency] = useState('daily');
  const [hour12, setHour12] = useState('3');
  const [minute, setMinute] = useState('00');
  const [ampm, setAmpm] = useState<'AM' | 'PM'>('PM');
  const [dayOfWeek, setDayOfWeek] = useState(0); // 0=Mon
  const [dayOfMonth, setDayOfMonth] = useState(1);
  const [intervalHours, setIntervalHours] = useState(1);
  const [instructions, setInstructions] = useState(defaultInstructions);
  const [isActive, setIsActive] = useState(true);
  const [nextRunAt, setNextRunAt] = useState<string | null>(null);
  const [lastRunAt, setLastRunAt] = useState<string | null>(null);
  const [lastStatus, setLastStatus] = useState<string>('idle');

  // UI state for dropdowns
  const [isFreqOpen, setIsFreqOpen] = useState(false);
  const [isTimePickerOpen, setIsTimePickerOpen] = useState(false);

  const freqRef = useRef<HTMLDivElement>(null);
  const timePickerRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (freqRef.current && !freqRef.current.contains(event.target as Node)) {
        setIsFreqOpen(false);
      }
      if (timePickerRef.current && !timePickerRef.current.contains(event.target as Node)) {
        setIsTimePickerOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch initial schedule
  const fetchSchedule = async () => {
    setLoading(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/schedules/${targetType}`);
      if (res.ok) {
        const data = await res.json();
        setFrequency(data.frequency || 'daily');
        setIsActive(data.is_active !== undefined ? data.is_active : true);
        if (data.instructions) setInstructions(data.instructions);
        else if (defaultInstructions && !data.instructions) setInstructions(defaultInstructions);

        if (data.day_of_week !== undefined) setDayOfWeek(data.day_of_week);
        if (data.day_of_month !== undefined) setDayOfMonth(data.day_of_month);
        if (data.interval_hours !== undefined) setIntervalHours(data.interval_hours);

        setNextRunAt(data.next_run_at || null);
        setLastRunAt(data.last_run_at || null);
        setLastStatus(data.last_status || 'idle');

        // Convert 24h to 12h
        if (data.time_of_day) {
          const [hStr, mStr] = data.time_of_day.split(':');
          let h = parseInt(hStr, 10);
          const m = mStr || '00';
          const period: 'AM' | 'PM' = h >= 12 ? 'PM' : 'AM';
          if (h === 0) h = 12;
          else if (h > 12) h -= 12;
          setHour12(String(h));
          setMinute(m.padStart(2, '0'));
          setAmpm(period);
        }
      }
    } catch (e) {
      console.error('Failed to load schedule:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, [targetType]);

  const getTimeOfDay24 = (): string => {
    let h = parseInt(hour12, 10) || 12;
    if (ampm === 'PM' && h < 12) h += 12;
    if (ampm === 'AM' && h === 12) h = 0;
    return `${String(h).padStart(2, '0')}:${minute.padStart(2, '0')}`;
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        frequency,
        time_of_day: getTimeOfDay24(),
        day_of_week: dayOfWeek,
        day_of_month: dayOfMonth,
        interval_hours: intervalHours,
        instructions,
        config: extraConfig,
        is_active: isActive,
      };

      const res = await fetchWithAuth(`${API_URL}/schedules/${targetType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        setNextRunAt(data.next_run_at);
        notify(`✅ ${data.message || 'Trigger schedule saved successfully!'}`);
      } else {
        const err = await res.json();
        notify(`Failed to save schedule: ${err.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error saving schedule');
    } finally {
      setSaving(false);
    }
  };

  const handleRunNow = async () => {
    setRunning(true);
    try {
      // Save before running
      await handleSave();

      const res = await fetchWithAuth(`${API_URL}/schedules/${targetType}/run-now`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setLastStatus('running');
        notify(`🚀 ${data.message || 'Workflow executed!'}`);
        if (onRunSuccess) onRunSuccess();
      } else {
        const err = await res.json();
        notify(`Failed to execute: ${err.detail || 'Error'}`);
      }
    } catch (e) {
      console.error(e);
      notify('Network error triggering run');
    } finally {
      setRunning(false);
    }
  };

  const handleResetTrigger = () => {
    setFrequency('daily');
    setHour12('3');
    setMinute('00');
    setAmpm('PM');
    setDayOfWeek(0);
    setIsActive(false);
    notify('Trigger reset to default (inactive)');
  };

  const formatNextRun = (isoStr: string | null) => {
    if (!isoStr) return 'Not scheduled';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return isoStr;
    }
  };

  const currentFreqLabel = FREQUENCIES.find((f) => f.id === frequency)?.label || 'Daily';

  return (
    <Card className={`bg-[#121316] border border-gray-800/80 rounded-2xl p-6 text-white shadow-xl ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-gray-800/60">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-white tracking-wide">{title}</h3>
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-gray-800/60 text-gray-400 border-gray-700/40'
              }`}
            >
              <span className={`size-1.5 rounded-full ${isActive ? 'bg-emerald-400 animate-pulse' : 'bg-gray-400'}`} />
              {isActive ? 'Active' : 'Paused'}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setIsActive(!isActive)}
            className="h-8 text-xs border-gray-800 bg-gray-900/60 hover:bg-gray-800 text-gray-300"
          >
            {isActive ? 'Pause Schedule' : 'Enable Schedule'}
          </Button>

          <Button
            type="button"
            size="sm"
            disabled={running}
            onClick={handleRunNow}
            className="h-8 text-xs bg-gradient-to-r from-blue-600 to-sky-600 hover:from-blue-500 hover:to-sky-500 text-white font-medium shadow-md shadow-blue-500/20 gap-1.5"
          >
            <Play className={`size-3.5 ${running ? 'animate-spin' : ''}`} />
            {running ? 'Running...' : 'Run Now'}
          </Button>
        </div>
      </div>

      {/* Triggers Section */}
      <div className="space-y-4 mb-6">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-gray-300 uppercase tracking-wider">Triggers</label>
          {nextRunAt && isActive && (
            <span className="text-xs text-sky-400 flex items-center gap-1 font-mono">
              <Clock className="size-3" /> Next run: {formatNextRun(nextRunAt)}
            </span>
          )}
        </div>

        {/* Trigger Pill Row - matches screenshot */}
        <div className="relative bg-[#1a1b1f] border border-gray-800 rounded-xl p-2.5 flex flex-wrap items-center gap-3 transition-colors hover:border-gray-700/80">
          {/* Blue Alarm Icon */}
          <div className="flex items-center justify-center size-9 rounded-full bg-[#0084ff] text-white shadow-md shadow-blue-500/30 flex-shrink-0">
            <Bell className="size-4 fill-white" />
          </div>

          {/* Frequency Dropdown */}
          <div className="relative" ref={freqRef}>
            <button
              type="button"
              onClick={() => {
                setIsFreqOpen(!isFreqOpen);
                setIsTimePickerOpen(false);
              }}
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#25262b] hover:bg-[#2c2d33] border border-gray-700/60 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <span>{currentFreqLabel}</span>
              {isFreqOpen ? <ChevronUp className="size-3.5 text-gray-400" /> : <ChevronDown className="size-3.5 text-gray-400" />}
            </button>

            {isFreqOpen && (
              <div className="absolute top-full left-0 mt-1.5 w-36 bg-[#202126] border border-gray-800 rounded-xl shadow-2xl py-1 z-30 overflow-hidden">
                {FREQUENCIES.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => {
                      setFrequency(f.id);
                      setIsFreqOpen(false);
                    }}
                    className={`w-full text-left px-3.5 py-2 text-sm transition-colors flex items-center justify-between ${
                      frequency === f.id
                        ? 'bg-blue-600/20 text-blue-400 font-medium'
                        : 'text-gray-300 hover:bg-[#2a2b32] hover:text-white'
                    }`}
                  >
                    <span>{f.label}</span>
                    {frequency === f.id && <span className="size-1.5 rounded-full bg-blue-400" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Time Picker separator */}
          {frequency !== 'hourly' && (
            <>
              <span className="text-sm font-medium text-gray-400">at</span>

              {/* Time display button */}
              <div className="relative" ref={timePickerRef}>
                <button
                  type="button"
                  onClick={() => {
                    setIsTimePickerOpen(!isTimePickerOpen);
                    setIsFreqOpen(false);
                  }}
                  className="px-3.5 py-1.5 bg-[#25262b] hover:bg-[#2c2d33] border border-gray-700/60 text-white text-sm font-medium rounded-lg transition-colors font-mono tracking-wide"
                >
                  {hour12}:{minute} {ampm}
                </button>

                {/* Interactive Time Picker Popover */}
                {isTimePickerOpen && (
                  <div className="absolute top-full left-0 mt-1.5 bg-[#202126] border border-gray-800 rounded-xl p-3 shadow-2xl z-30 flex items-center gap-2">
                    {/* Hour Input */}
                    <input
                      type="number"
                      min={1}
                      max={12}
                      value={hour12}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        if (!isNaN(val) && val >= 1 && val <= 12) setHour12(String(val));
                        else if (e.target.value === '') setHour12('');
                      }}
                      className="w-12 h-9 text-center bg-[#151619] border border-gray-700/80 rounded-lg text-white font-mono text-base focus:border-blue-500 focus:outline-none"
                    />

                    <span className="text-gray-400 font-bold font-mono text-lg">:</span>

                    {/* Minute Input */}
                    <input
                      type="number"
                      min={0}
                      max={59}
                      value={minute}
                      onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        if (!isNaN(val) && val >= 0 && val <= 59) {
                          setMinute(String(val).padStart(2, '0'));
                        } else if (e.target.value === '') {
                          setMinute('');
                        }
                      }}
                      className="w-12 h-9 text-center bg-[#151619] border border-gray-700/80 rounded-lg text-white font-mono text-base focus:border-blue-500 focus:outline-none"
                    />

                    {/* AM / PM Segmented Control */}
                    <div className="flex bg-[#151619] p-0.5 rounded-lg border border-gray-700/80 ml-1">
                      <button
                        type="button"
                        onClick={() => setAmpm('AM')}
                        className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                          ampm === 'AM' ? 'bg-white text-black shadow-sm' : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        AM
                      </button>
                      <button
                        type="button"
                        onClick={() => setAmpm('PM')}
                        className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                          ampm === 'PM' ? 'bg-white text-black shadow-sm' : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        PM
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Weekly day-of-week selection */}
          {frequency === 'weekly' && (
            <div className="flex items-center gap-1 ml-auto">
              {DAYS_OF_WEEK.map((day, idx) => (
                <button
                  key={day}
                  type="button"
                  onClick={() => setDayOfWeek(idx)}
                  className={`size-7 rounded-md text-xs font-medium transition-colors ${
                    dayOfWeek === idx
                      ? 'bg-blue-600 text-white font-bold'
                      : 'bg-[#25262b] text-gray-400 hover:text-white hover:bg-gray-700'
                  }`}
                >
                  {day[0]}
                </button>
              ))}
            </div>
          )}

          {/* Monthly day selection */}
          {frequency === 'monthly' && (
            <div className="flex items-center gap-1.5 ml-auto text-xs text-gray-400">
              <span>Day</span>
              <input
                type="number"
                min={1}
                max={28}
                value={dayOfMonth}
                onChange={(e) => setDayOfMonth(Math.max(1, Math.min(28, parseInt(e.target.value, 10) || 1)))}
                className="w-12 h-8 text-center bg-[#25262b] border border-gray-700/60 rounded-md text-white font-mono text-xs"
              />
            </div>
          )}

          {/* Hourly interval selection */}
          {frequency === 'hourly' && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">every</span>
              <input
                type="number"
                min={1}
                max={24}
                value={intervalHours}
                onChange={(e) => setIntervalHours(Math.max(1, parseInt(e.target.value, 10) || 1))}
                className="w-14 h-8 text-center bg-[#25262b] border border-gray-700/60 rounded-md text-white font-mono text-sm"
              />
              <span className="text-sm text-gray-400">hour(s)</span>
            </div>
          )}

          {/* Trash button */}
          <button
            type="button"
            onClick={handleResetTrigger}
            title="Reset Trigger"
            className="ml-auto p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
          >
            <Trash2 className="size-4" />
          </button>
        </div>
      </div>

      {/* Instructions / Prompt Directives */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-gray-300 uppercase tracking-wider">Instructions</label>
          <span className="text-[11px] text-gray-500">Autonomous role & execution guidelines</span>
        </div>

        <Textarea
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder="ROLE&#10;You are Sales Intelligence Analyst...&#10;Find observable digital marketing weaknesses or decision-makers...&#10;WHAT WE SELL (only these)..."
          className="bg-[#18191d] border border-gray-800 text-gray-200 rounded-xl p-4 text-xs font-mono leading-relaxed focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 resize-y min-h-[160px] shadow-inner"
        />
      </div>

      {/* Footer Save & Sync Bar */}
      <div className="mt-4 pt-4 border-t border-gray-800/60 flex items-center justify-between">
        <div className="text-xs text-gray-500">
          {lastRunAt ? (
            <span>
              Last executed: <strong className="text-gray-400">{formatNextRun(lastRunAt)}</strong>
            </span>
          ) : (
            <span>No previous automated run recorded.</span>
          )}
        </div>

        <Button
          type="button"
          onClick={handleSave}
          disabled={saving}
          size="sm"
          className="bg-gray-800 hover:bg-gray-700 text-white font-medium text-xs h-8 px-4 rounded-lg gap-1.5"
        >
          <Save className="size-3.5" />
          {saving ? 'Saving...' : 'Save Schedule'}
        </Button>
      </div>
    </Card>
  );
}

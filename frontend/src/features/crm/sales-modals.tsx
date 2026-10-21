'use client';

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { 
  Plus, Upload, Loader2, Sparkles, FileText, CheckCircle2, AlertCircle
} from 'lucide-react';

interface CreateLeadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateLead: (leadData: any) => Promise<void>;
  loading: boolean;
}

export function CreateLeadModal({
  isOpen,
  onClose,
  onCreateLead,
  loading,
}: CreateLeadModalProps) {
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [capacity, setCapacity] = useState('');
  const [need, setNeed] = useState('');
  const [why, setWhy] = useState('');
  const [priority, setPriority] = useState('medium');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!company.trim() || !name.trim()) return;

    await onCreateLead({
      name,
      company,
      email,
      personal_email: email,
      company_email: email,
      phone,
      mobile_no: phone,
      how_much: capacity,
      need_of_what: need,
      why,
      priority,
      status: 'new',
      score: 50,
      assigned_to: 'Sales AI Agent',
      source: 'Manual Entry',
    });

    // Reset
    setName('');
    setCompany('');
    setEmail('');
    setPhone('');
    setCapacity('');
    setNeed('');
    setWhy('');
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-white border border-slate-200 text-slate-900 rounded-3xl max-w-lg p-6 shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
            <span className="text-blue-600 font-bold">▎</span>
            <Plus size={18} className="text-blue-600" /> Add Prospect Manually
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Company Name *</label>
              <Input
                required
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Target Corp"
                className="text-xs bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Contact Name *</label>
              <Input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Jane Doe"
                className="text-xs bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Email Address</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="jane@company.com"
                className="text-xs bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Phone Number</label>
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 555-0199"
                className="text-xs bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Deal Capacity / Value</label>
              <Input
                value={capacity}
                onChange={(e) => setCapacity(e.target.value)}
                placeholder="e.g. $5,000"
                className="text-xs bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">Priority Tier</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full h-9 text-xs bg-slate-50 border border-slate-200 rounded-md px-2.5 text-slate-900 focus:bg-white focus:border-blue-500 outline-none"
              >
                <option value="high">High Priority</option>
                <option value="medium">Medium Priority</option>
                <option value="low">Low Priority</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 block mb-1">Commercial Need</label>
            <Input
              value={need}
              onChange={(e) => setNeed(e.target.value)}
              placeholder="What product or services do they need?"
              className="text-xs bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 block mb-1">Why Now / Buying Signal</label>
            <Textarea
              rows={2}
              value={why}
              onChange={(e) => setWhy(e.target.value)}
              placeholder="Key trigger, recent hiring, expansion, or pain point..."
              className="text-xs bg-slate-50 border-slate-200 text-slate-900 placeholder:text-slate-400 focus:bg-white focus:border-blue-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="text-xs rounded-xl border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading}
              className="text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 shadow-sm"
            >
              {loading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : null}
              Create Account
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface UploadLeadsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File, withAI: boolean) => Promise<void>;
  loading: boolean;
}

export function UploadLeadsModal({
  isOpen,
  onClose,
  onUpload,
  loading,
}: UploadLeadsModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [withAI, setWithAI] = useState(true);

  const handleUploadSubmit = async () => {
    if (!file) return;
    await onUpload(file, withAI);
    setFile(null);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-white border border-slate-200 text-slate-900 rounded-3xl max-w-lg p-6 shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-base font-bold flex items-center gap-2 text-slate-900">
            <span className="text-blue-600 font-bold">▎</span>
            <Upload size={18} className="text-blue-600" /> Import Leads (CSV / JSON)
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          <p className="text-xs text-slate-600 leading-relaxed">
            Upload a structured <strong className="text-slate-900">.csv</strong> or <strong className="text-slate-900">.json</strong> file.
            Headers supported: <code className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-[11px] font-mono">name, email, company, phone, capacity</code>.
          </p>

          {/* Drag & Drop File Target */}
          <div
            onClick={() => document.getElementById('sales-import-file')?.click()}
            className="border-2 border-dashed border-slate-200 hover:border-blue-400 rounded-2xl p-8 text-center cursor-pointer transition-all bg-slate-50/60 hover:bg-blue-50/40 group"
          >
            <Upload size={28} className="mx-auto mb-2 text-slate-400 group-hover:text-blue-600 transition-colors" />
            <p className="text-sm font-bold text-slate-800">
              {file ? file.name : 'Click or drop CSV / JSON file'}
            </p>
            <p className="text-xs text-slate-500 mt-1">Up to 10MB per batch</p>
            <input
              id="sales-import-file"
              type="file"
              accept=".csv,.json"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>

          {/* AI Auto-Enrichment Toggle */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/70">
            <div>
              <p className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <Sparkles size={13} className="text-blue-600" /> AI Scoring & Signal Enrichment
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Auto-score each imported account and synthesize purchasing capacity.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setWithAI(!withAI)}
              className={`relative w-10 h-5 rounded-full transition-colors ${withAI ? 'bg-blue-600' : 'bg-slate-300'}`}
            >
              <span className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${withAI ? 'translate-x-5' : 'translate-x-0'}`} />
            </button>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
            <Button
              variant="outline"
              onClick={onClose}
              className="text-xs rounded-xl border-slate-200 text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </Button>
            <Button
              onClick={handleUploadSubmit}
              disabled={loading || !file}
              className="text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 shadow-sm"
            >
              {loading ? (
                <>
                  <Loader2 size={14} className="animate-spin mr-1.5" /> Importing...
                </>
              ) : (
                'Import Leads'
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

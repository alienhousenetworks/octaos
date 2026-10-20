'use client';

import React, { useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Upload,
  FolderUp,
  SlidersHorizontal,
  Bot,
  Sparkles,
  Loader2,
  CheckCircle2,
  X,
  FileText,
  Trash2,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { StagedFile, IngestionJob } from './hr-types';

interface HRIngestionViewProps {
  hrRole: string;
  setHrRole: (val: string) => void;
  hrRequirements: string;
  setHrRequirements: (val: string) => void;
  hrSalary: string;
  setHrSalary: (val: string) => void;
  hrProvider: string;
  setHrProvider: (val: string) => void;
  hrModel: string;
  setHrModel: (val: string) => void;
  stagedFiles: StagedFile[];
  onFilesAdded: (filesList: FileList | null) => void;
  onToggleFileSelection: (id: string) => void;
  onToggleSelectAll: (select: boolean) => void;
  onRemoveStagedFile: (id: string) => void;
  onProcessBatchUpload: () => void;
  uploadLoading: boolean;
  uploadProgress: string;
  uploadPercent: number;
  currentProcessingFile: string;
  ingestionLogs: string[];
  activeJob: IngestionJob | null;
  showLogsDrawer: boolean;
  setShowLogsDrawer: (show: boolean) => void;
}

export default function HRIngestionView({
  hrRole,
  setHrRole,
  hrRequirements,
  setHrRequirements,
  hrSalary,
  setHrSalary,
  hrProvider,
  setHrProvider,
  hrModel,
  setHrModel,
  stagedFiles,
  onFilesAdded,
  onToggleFileSelection,
  onToggleSelectAll,
  onRemoveStagedFile,
  onProcessBatchUpload,
  uploadLoading,
  uploadProgress,
  uploadPercent,
  currentProcessingFile,
  ingestionLogs,
  activeJob,
  showLogsDrawer,
  setShowLogsDrawer,
}: HRIngestionViewProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const selectedCount = stagedFiles.filter((f) => f.selected).length;
  const isAllSelected = stagedFiles.length > 0 && selectedCount === stagedFiles.length;

  return (
    <div className="space-y-4">
      {/* Active Processing Banner if job is running */}
      {(uploadLoading || activeJob?.status === 'running') && (
        <Card className="bg-card border-border rounded-xl p-4 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20 shrink-0">
                <Loader2 size={18} className="animate-spin" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold text-foreground">
                    Parsing &amp; Scoring Resumes for &quot;{hrRole}&quot;
                  </h4>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/25">
                    PROCESSING
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                  {currentProcessingFile || uploadProgress || 'Extracting candidate profiles...'}
                </p>
              </div>
            </div>

            {/* Progress Meter */}
            <div className="w-48 space-y-1">
              <div className="flex justify-between text-[11px] font-mono text-muted-foreground">
                <span>Progress</span>
                <span className="font-semibold text-primary">{uploadPercent}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-primary h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${uploadPercent}%` }}
                />
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column: Sourcing Criteria & Target Role */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="bg-card border-border rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-border">
              <SlidersHorizontal size={16} className="text-primary" />
              <h3 className="text-sm font-bold text-foreground">ATS Target Criteria</h3>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Target Role Title</label>
              <Input
                value={hrRole}
                onChange={(e) => setHrRole(e.target.value)}
                placeholder="e.g. Senior Full Stack Engineer"
                className="bg-surface-hover/60 border-border text-foreground text-xs h-9 rounded-lg"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Required Skills &amp; Qualifications</label>
              <Textarea
                value={hrRequirements}
                onChange={(e) => setHrRequirements(e.target.value)}
                placeholder="e.g. Python, FastAPI, React, TypeScript, PostgreSQL, 3+ years experience"
                className="bg-surface-hover/60 border-border text-foreground text-xs rounded-lg min-h-[90px] resize-none"
              />
              <p className="text-[10px] text-muted-foreground">
                Used for deterministic keyword extraction and dual-engine semantic scoring.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground">Target Annual Compensation</label>
              <Input
                value={hrSalary}
                onChange={(e) => setHrSalary(e.target.value)}
                placeholder="e.g. $130,000/year"
                className="bg-surface-hover/60 border-border text-foreground text-xs h-9 rounded-lg"
              />
            </div>

            {/* AI Provider & Engine selection */}
            <div className="pt-2 border-t border-border space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                <Bot size={13} className="text-primary" />
                <span>AI Scoring Model</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={hrProvider}
                  onChange={(e) => setHrProvider(e.target.value)}
                  className="bg-surface-hover/60 border border-border text-foreground rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="auto">Auto (Best Available)</option>
                  <option value="groq">Groq (Ultra-Fast)</option>
                  <option value="anthropic">Anthropic Claude</option>
                  <option value="openai">OpenAI GPT-4o</option>
                </select>

                <Input
                  value={hrModel}
                  onChange={(e) => setHrModel(e.target.value)}
                  placeholder="Model override (optional)"
                  className="bg-surface-hover/60 border-border text-foreground text-xs h-8.5 rounded-lg"
                />
              </div>
            </div>
          </Card>
        </div>

        {/* Right Column: Upload Zone & Staged Resumes */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="bg-card border-border rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Upload size={16} className="text-primary" />
                <h3 className="text-sm font-bold text-foreground">Resume Staging Dropzone</h3>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  className="h-8 text-xs font-semibold flex items-center gap-1.5"
                >
                  <Upload size={12} /> Select Files
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => folderInputRef.current?.click()}
                  className="h-8 text-xs font-semibold flex items-center gap-1.5"
                >
                  <FolderUp size={12} /> Select Folder
                </Button>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.md"
                  className="hidden"
                  onChange={(e) => onFilesAdded(e.target.files)}
                />
                <input
                  ref={folderInputRef}
                  type="file"
                  multiple
                  {...({ webkitdirectory: '', directory: '' } as any)}
                  className="hidden"
                  onChange={(e) => onFilesAdded(e.target.files)}
                />
              </div>
            </div>

            {/* Drag & Drop Visual Area */}
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                onFilesAdded(e.dataTransfer.files);
              }}
              className="border-2 border-dashed border-border hover:border-primary/60 transition-colors rounded-xl p-8 text-center cursor-pointer bg-surface-hover/30 hover:bg-surface-hover/50 space-y-2"
            >
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary mx-auto flex items-center justify-center">
                <Upload size={20} />
              </div>
              <p className="text-xs font-semibold text-foreground">
                Drop PDF, DOCX, or text resumes here, or click to browse
              </p>
              <p className="text-[11px] text-muted-foreground">
                Zero-cost local parsing with PyMuPDF text extraction &amp; AI semantic scoring
              </p>
            </div>

            {/* Staged Resumes Table */}
            {stagedFiles.length > 0 && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={isAllSelected}
                      onChange={(e) => onToggleSelectAll(e.target.checked)}
                      className="h-3.5 w-3.5 rounded border-border bg-card text-primary focus:ring-primary/20 cursor-pointer"
                    />
                    <span>
                      Staged Queue ({selectedCount}/{stagedFiles.length} selected)
                    </span>
                  </div>

                  <Button
                    size="sm"
                    disabled={selectedCount === 0 || uploadLoading}
                    onClick={onProcessBatchUpload}
                    className="h-8 text-xs font-bold flex items-center gap-1.5 shadow-xs"
                  >
                    {uploadLoading ? (
                      <>
                        <Loader2 size={13} className="animate-spin" />
                        <span>Parsing Resumes...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={13} />
                        <span>Parse &amp; Rank {selectedCount} Resume(s)</span>
                      </>
                    )}
                  </Button>
                </div>

                <div className="border border-border rounded-xl overflow-hidden max-h-56 overflow-y-auto divide-y divide-border/60">
                  {stagedFiles.map((f) => (
                    <div
                      key={f.id}
                      className="flex items-center justify-between px-3 py-2 text-xs hover:bg-surface-hover/50 transition-colors"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <input
                          type="checkbox"
                          checked={f.selected}
                          onChange={() => onToggleFileSelection(f.id)}
                          className="h-3.5 w-3.5 rounded border-border bg-card text-primary focus:ring-primary/20 cursor-pointer"
                        />
                        <FileText size={14} className="text-muted-foreground shrink-0" />
                        <span className="font-medium text-foreground truncate max-w-[280px]">
                          {f.name}
                        </span>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {f.sizeFormatted}
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-muted text-muted-foreground">
                          {f.type}
                        </span>
                      </div>

                      <button
                        onClick={() => onRemoveStagedFile(f.id)}
                        className="text-muted-foreground hover:text-destructive p-1"
                        title="Remove file"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          {/* Ingestion Console / Activity Stream */}
          {ingestionLogs.length > 0 && (
            <Card className="bg-card border-border rounded-xl p-4 shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                  <Bot size={14} className="text-primary" />
                  <span>Ingestion Engine Activity Stream</span>
                </div>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowLogsDrawer(!showLogsDrawer)}
                  className="h-7 px-2 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  {showLogsDrawer ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  <span className="ml-1">{showLogsDrawer ? 'Collapse' : `Logs (${ingestionLogs.length})`}</span>
                </Button>
              </div>

              {showLogsDrawer && (
                <div className="p-3 bg-background/80 rounded-lg border border-border/70 max-h-48 overflow-y-auto space-y-1 font-mono text-[11px]">
                  {ingestionLogs.map((log, lIdx) => (
                    <div
                      key={lIdx}
                      className={
                        log.includes('✓')
                          ? 'text-[#64B99A] font-semibold'
                          : log.includes('✗')
                          ? 'text-[#D9828B] font-semibold'
                          : 'text-muted-foreground'
                      }
                    >
                      {log}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

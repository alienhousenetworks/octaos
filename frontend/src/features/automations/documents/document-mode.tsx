'use client';

import React, { useState, useRef } from 'react';
import {
  FileText,
  Upload,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Table,
  Eye,
  Check,
  X,
  FileCode,
  ArrowRight,
  Send,
  Sliders,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { notify } from '@/lib/notify';
import { useWorkflowEditorStore } from '../state/workflow-editor-store';
import type { DocumentLifecycleState } from '../types';

interface DocumentModeProps {
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
}

const LIFECYCLE_STEPS: DocumentLifecycleState[] = [
  'SUBMITTED',
  'EXTRACTED',
  'VALIDATED',
  'APPROVED',
  'DELIVERED',
];

export function DocumentIntelligencePanel({ API_URL, fetchWithAuth }: DocumentModeProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isMapping, setIsMapping] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [activeTab, setActiveTab] = useState<'text' | 'tables' | 'schema'>('text');

  const selectedDocument = useWorkflowEditorStore((s) => s.selectedDocument);
  const setSelectedDocument = useWorkflowEditorStore((s) => s.setSelectedDocument);
  const extractedFields = useWorkflowEditorStore((s) => s.extractedFields);
  const setExtractedFields = useWorkflowEditorStore((s) => s.setExtractedFields);
  const targetSchema = useWorkflowEditorStore((s) => s.targetSchema);
  const setTargetSchema = useWorkflowEditorStore((s) => s.setTargetSchema);
  const validationReport = useWorkflowEditorStore((s) => s.validationReport);
  const setValidationReport = useWorkflowEditorStore((s) => s.setValidationReport);
  const lifecycleState = useWorkflowEditorStore((s) => s.lifecycleState);
  const setLifecycleState = useWorkflowEditorStore((s) => s.setLifecycleState);
  const selectedNodeId = useWorkflowEditorStore((s) => s.selectedNodeId);
  const updateNode = useWorkflowEditorStore((s) => s.updateNode);

  // File Upload Handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('department', 'Legal & Ops');

    try {
      const res = await fetchWithAuth(`${API_URL}/automation-documents/extract`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Document extraction failed');
      }

      const data = await res.json();
      setSelectedDocument(data);
      setLifecycleState('EXTRACTED');
      notify(`Extracted ${file.name} successfully (${data.extraction_stage})`);
    } catch (err: any) {
      notify(`Extraction error: ${err.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Run AI Field Mapper
  const handleMapFields = async () => {
    if (!selectedDocument?.text_content) {
      notify('Please upload or extract a document first');
      return;
    }

    setIsMapping(true);
    try {
      const res = await fetchWithAuth(`${API_URL}/automation-documents/map-fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: selectedDocument.text_content,
          schema_definition: targetSchema,
        }),
      });

      if (!res.ok) {
        throw new Error('Field mapping failed');
      }

      const data = await res.json();
      setExtractedFields(data.mapped_fields || {});
      notify('Fields mapped successfully');

      // Auto-validate
      handleValidate(data.mapped_fields || {});
    } catch (err: any) {
      notify(`Mapping error: ${err.message}`);
    } finally {
      setIsMapping(false);
    }
  };

  // Validate Extracted Fields
  const handleValidate = async (fieldsToValidate?: Record<string, any>) => {
    const fields = fieldsToValidate || extractedFields;
    setIsValidating(true);
    try {
      const requiredFields = targetSchema?.required || ['document_type', 'counterparty_name'];
      const res = await fetchWithAuth(`${API_URL}/automation-documents/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fields,
          required_fields: requiredFields,
          min_confidence: 0.75,
          current_confidence: selectedDocument?.confidence_score || 0.9,
        }),
      });

      if (!res.ok) throw new Error('Validation check failed');

      const data = await res.json();
      setValidationReport(data);
      if (data.is_valid && !data.requires_human_review) {
        setLifecycleState('VALIDATED');
        notify('Validation passed. Ready for approval.');
      } else {
        notify('Validation flagged items requiring human review.');
      }
    } catch (err: any) {
      notify(`Validation error: ${err.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  // Advance Lifecycle
  const advanceState = (next: DocumentLifecycleState) => {
    setLifecycleState(next);
    notify(`Document lifecycle transitioned to: ${next}`);
  };

  // Sync to Selected Node
  const handleSyncToNode = () => {
    if (!selectedNodeId) {
      notify('Select a canvas node first to bind document configuration');
      return;
    }

    updateNode(selectedNodeId, {
      config: {
        document_type: extractedFields.document_type || selectedDocument?.doc_type,
        schema: targetSchema,
        mapped_data: extractedFields,
        tokens: selectedDocument?.tokens_detected || [],
      },
    });
    notify(`Bound document configuration to node ${selectedNodeId}`);
  };

  return (
    <div className="w-[460px] border-l bg-card/90 backdrop-blur-md flex flex-col h-full overflow-hidden select-none z-10 shadow-xl">
      {/* Top Banner / Lifecycle Tracker */}
      <div className="p-3 border-b bg-muted/40 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            <span className="text-xs font-bold tracking-wider uppercase text-foreground">
              Document Intelligence Hub
            </span>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-medium bg-primary/10 text-primary border border-primary/20">
            {lifecycleState}
          </span>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-between pt-1">
          {LIFECYCLE_STEPS.map((step, idx) => {
            const currentIdx = LIFECYCLE_STEPS.indexOf(lifecycleState);
            const isCompleted = idx < currentIdx;
            const isCurrent = idx === currentIdx;

            return (
              <div key={step} className="flex items-center gap-1">
                <div
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold transition-all ${
                    isCompleted
                      ? 'bg-emerald-500 text-white'
                      : isCurrent
                      ? 'bg-primary text-primary-foreground ring-2 ring-primary/30'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {isCompleted ? <Check className="h-2.5 w-2.5" /> : idx + 1}
                </div>
                <span
                  className={`text-[9px] hidden sm:inline ${
                    isCurrent ? 'font-bold text-foreground' : 'text-muted-foreground'
                  }`}
                >
                  {step.slice(0, 4)}
                </span>
                {idx < LIFECYCLE_STEPS.length - 1 && (
                  <div className="w-3 h-0.5 bg-border mx-0.5" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Upload Bar & Meta */}
      <div className="p-3 border-b space-y-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.xlsx,.csv,.png,.jpg"
          className="hidden"
          onChange={handleFileUpload}
        />

        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="flex-1 h-8 text-xs gap-1.5"
          >
            {isUploading ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Upload className="h-3.5 w-3.5" />
            )}
            {selectedDocument ? 'Upload Another Doc' : 'Upload & Extract Document'}
          </Button>

          {selectedDocument && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleMapFields}
              disabled={isMapping}
              className="h-8 text-xs gap-1.5"
            >
              {isMapping ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5 text-amber-500" />
              )}
              AI Map
            </Button>
          )}
        </div>

        {/* Selected Document Info */}
        {selectedDocument ? (
          <div className="p-2 rounded bg-muted/60 border text-[11px] space-y-1">
            <div className="flex justify-between items-center font-medium">
              <span className="truncate max-w-[240px] text-foreground font-semibold">
                {selectedDocument.filename}
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-600 font-mono">
                {Math.round((selectedDocument.confidence_score || 0.95) * 100)}% Conf
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground">
              <span>Stage: {selectedDocument.extraction_stage}</span>
              <span>{selectedDocument.page_count} pages • {Math.round(selectedDocument.file_size_bytes / 1024)} KB</span>
            </div>
            {selectedDocument.tokens_detected && selectedDocument.tokens_detected.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {selectedDocument.tokens_detected.slice(0, 4).map((tok) => (
                  <span
                    key={tok}
                    className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 font-mono"
                  >
                    {tok}
                  </span>
                ))}
                {selectedDocument.tokens_detected.length > 4 && (
                  <span className="text-[9px] text-muted-foreground">
                    +{selectedDocument.tokens_detected.length - 4} more
                  </span>
                )}
              </div>
            )}
          </div>
        ) : (
          <p className="text-[11px] text-muted-foreground text-center py-2 italic">
            No document loaded. Upload a PDF, Contract, Invoice, or Resume to initiate cascading extraction.
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b bg-muted/20 px-3 text-xs font-medium">
        <button
          onClick={() => setActiveTab('text')}
          className={`py-2 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'text'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Eye className="h-3.5 w-3.5" /> Text Extracted
        </button>
        <button
          onClick={() => setActiveTab('tables')}
          className={`py-2 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'tables'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Table className="h-3.5 w-3.5" /> Tables ({selectedDocument?.tables?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('schema')}
          className={`py-2 px-3 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'schema'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <FileCode className="h-3.5 w-3.5" /> Field Mapping
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-3 text-xs space-y-3">
        {activeTab === 'text' && (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-muted-foreground">Sanitized Document Text</span>
              <span className="text-[10px] text-muted-foreground">
                {selectedDocument?.text_content ? `${selectedDocument.text_content.length} chars` : 'Empty'}
              </span>
            </div>
            <div className="p-3 bg-muted/30 rounded border font-mono text-[11px] leading-relaxed whitespace-pre-wrap max-h-[340px] overflow-y-auto">
              {selectedDocument?.text_content || 'No text extracted yet.'}
            </div>
          </div>
        )}

        {activeTab === 'tables' && (
          <div className="space-y-2">
            <span className="font-semibold text-muted-foreground">Extracted Tables & Sheets</span>
            {selectedDocument?.tables && selectedDocument.tables.length > 0 ? (
              selectedDocument.tables.map((t, idx) => (
                <div key={idx} className="border rounded p-2 bg-muted/20 space-y-1">
                  <div className="flex justify-between text-[11px] font-medium text-foreground">
                    <span>Sheet/Page: {t.sheet_or_page}</span>
                    <span>{t.row_count} rows</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px] border-collapse">
                      <thead>
                        <tr className="border-b bg-muted/60">
                          {t.headers?.map((h, hIdx) => (
                            <th key={hIdx} className="p-1 text-left font-semibold">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {t.rows?.slice(0, 5).map((r, rIdx) => (
                          <tr key={rIdx} className="border-b border-border/50">
                            {r.map((cell, cIdx) => (
                              <td key={cIdx} className="p-1 text-muted-foreground truncate max-w-[100px]">
                                {String(cell)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-[11px] text-muted-foreground py-4 text-center italic">
                No structured tables detected in this file.
              </p>
            )}
          </div>
        )}

        {activeTab === 'schema' && (
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-muted-foreground">Mapped Fields</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleValidate()}
                disabled={isValidating}
                className="h-6 text-[10px] gap-1"
              >
                <ShieldCheck className="h-3 w-3 text-emerald-500" /> Re-validate
              </Button>
            </div>

            {/* Validation Banner */}
            {validationReport && (
              <div
                className={`p-2 rounded border text-[11px] flex items-start gap-2 ${
                  validationReport.is_valid && !validationReport.requires_human_review
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400'
                }`}
              >
                {validationReport.is_valid && !validationReport.requires_human_review ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                )}
                <div>
                  <p className="font-semibold">
                    {validationReport.is_valid && !validationReport.requires_human_review
                      ? 'All validation constraints met'
                      : 'Human review required before approval'}
                  </p>
                  {validationReport.missing_required_fields?.length > 0 && (
                    <p className="text-[10px] mt-0.5">
                      Missing: {validationReport.missing_required_fields.join(', ')}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Field Inputs */}
            <div className="space-y-2">
              {Object.keys(targetSchema?.properties || {}).map((fieldKey) => {
                const propDef = targetSchema.properties[fieldKey];
                const value = extractedFields[fieldKey] ?? '';

                return (
                  <div key={fieldKey} className="space-y-1">
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="font-medium text-foreground">
                        {fieldKey}
                        {targetSchema.required?.includes(fieldKey) && (
                          <span className="text-red-500 ml-0.5">*</span>
                        )}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {propDef.type}
                      </span>
                    </div>
                    <Input
                      value={value}
                      onChange={(e) =>
                        setExtractedFields({
                          ...extractedFields,
                          [fieldKey]: e.target.value,
                        })
                      }
                      placeholder={propDef.description || `Enter ${fieldKey}`}
                      className="h-7 text-xs bg-background/80"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Footer / Governance & Actions */}
      <div className="p-3 border-t bg-muted/40 space-y-2">
        {/* State Transitions */}
        <div className="flex items-center justify-between gap-2">
          {lifecycleState === 'EXTRACTED' && (
            <Button
              size="sm"
              onClick={() => handleValidate()}
              disabled={isValidating}
              className="flex-1 h-8 text-xs bg-blue-600 hover:bg-blue-700 text-white"
            >
              <ShieldCheck className="h-3.5 w-3.5 mr-1" /> Validate Document
            </Button>
          )}

          {lifecycleState === 'VALIDATED' && (
            <div className="flex gap-2 w-full">
              <Button
                size="sm"
                onClick={() => advanceState('APPROVED')}
                className="flex-1 h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                <Check className="h-3.5 w-3.5 mr-1" /> Approve Document
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => advanceState('EXTRACTED')}
                className="h-8 text-xs text-red-500 hover:text-red-600"
              >
                <X className="h-3.5 w-3.5 mr-1" /> Reject
              </Button>
            </div>
          )}

          {lifecycleState === 'APPROVED' && (
            <Button
              size="sm"
              onClick={() => advanceState('DELIVERED')}
              className="flex-1 h-8 text-xs bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              <Send className="h-3.5 w-3.5 mr-1" /> Deliver Downstream
            </Button>
          )}

          {lifecycleState === 'DELIVERED' && (
            <div className="flex items-center justify-center w-full py-1 text-emerald-600 font-semibold text-xs gap-1.5">
              <CheckCircle2 className="h-4 w-4" /> Document Delivered to Workflow
            </div>
          )}
        </div>

        {/* Sync to Canvas Node */}
        {selectedNodeId && (
          <Button
            size="sm"
            variant="secondary"
            onClick={handleSyncToNode}
            className="w-full h-7 text-[11px] gap-1"
          >
            <Sliders className="h-3 w-3" /> Sync Document Config to Selected Node
          </Button>
        )}
      </div>
    </div>
  );
}

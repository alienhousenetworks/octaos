'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { FileText, Search, Trash2, Upload, Loader2, Bot, Plus, Cpu } from 'lucide-react';

interface KnowledgeViewProps {
  token: string | null;
  API_URL: string;
  fetchWithAuth: (url: string, options?: any) => Promise<Response>;
  fetchData: () => Promise<void>;
  knowledge: any[];
}

export default function KnowledgeView({ token, API_URL, fetchWithAuth, fetchData, knowledge }: KnowledgeViewProps) {
  const [kbDept, setKbDept] = useState('Marketing');
  const [kbType, setKbType] = useState('Brand Guidelines');
  const [kbSearch, setKbSearch] = useState('');
  const [kbContent, setKbContent] = useState('');
  const [kbFile, setKbFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [kbTab, setKbTab] = useState<'text' | 'file' | 'upload' | 'directives'>('text');

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

  const uploadKnowledgeFile = async () => {
    if (!kbFile) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', kbFile);
      formData.append('department', kbDept);
      formData.append('doc_type', kbType);

      const res = await fetchWithAuth(`${API_URL}/commands/knowledge/upload`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        setKbFile(null);
        fetchData();
      } else {
        const errorData = await res.json();
        alert(errorData.detail || "Failed to upload document");
      }
    } catch (e) {
      console.error(e);
      alert("Error uploading document");
    } finally {
      setIsUploading(false);
    }
  };

  const deleteKnowledge = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document from the knowledge base?")) return;
    try {
      const res = await fetchWithAuth(`${API_URL}/commands/knowledge/${docId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchData();
      } else {
        alert("Failed to delete document");
      }
    } catch (e) {
      console.error(e);
      alert("Error deleting document");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto h-[calc(100vh-140px)] flex flex-col">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 flex-shrink-0">
        <div>
          <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
            Company Knowledge Base
          </h1>
          <p className="text-gray-400 mt-1">
            Upload files or paste raw text context. Deployed AI agents read these resources to formulate answers, target marketing posts, and score candidates.
          </p>
        </div>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-12 gap-8 items-stretch bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.05)] rounded-3xl p-6 md:p-8 shadow-2xl glass-panel relative overflow-hidden">
        {/* Left Column: Stored Contexts list */}
        <div className="md:col-span-5 flex flex-col space-y-4 border-r border-gray-800/80 pr-6 min-h-0 h-full">
          <div className="flex items-center justify-between flex-shrink-0">
            <h3 className="text-sm font-bold text-gray-300">Stored Contexts ({knowledge.length})</h3>
          </div>

          {/* Search bar */}
          <div className="relative flex-shrink-0">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" />
            <Input
              placeholder="Search files..."
              value={kbSearch}
              onChange={e => setKbSearch(e.target.value)}
              className="pl-9 bg-gray-950/60 border-gray-800 text-xs text-white rounded-xl placeholder-gray-500 focus:border-violet-500 focus:ring-violet-500/20"
            />
          </div>

          {/* Document list */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar min-h-0">
            {knowledge
              .filter(doc => {
                const title = doc.content.startsWith("Source Document: ")
                  ? doc.content.match(/^Source Document: ([^\n]+)/)?.[1] || doc.doc_type
                  : doc.doc_type;
                const matchSearch = (title + ' ' + doc.content + ' ' + doc.department).toLowerCase().includes(kbSearch.toLowerCase());
                return matchSearch;
              })
              .map(doc => {
                const isFile = doc.content.startsWith("Source Document: ");
                const fileName = isFile
                  ? doc.content.match(/^Source Document: ([^\n]+)/)?.[1] || "Uploaded File"
                  : null;
                return (
                  <div
                    key={doc.id}
                    className="group flex items-start justify-between gap-3 p-3 bg-gray-900/40 hover:bg-gray-900/80 border border-gray-800/50 hover:border-gray-800 rounded-xl transition-all duration-200"
                  >
                    <div className="flex items-start gap-2.5 min-w-0">
                      <div className={`mt-0.5 p-1.5 rounded-lg ${doc.doc_type === 'Prompt Directives'
                          ? 'bg-amber-500/10 text-amber-400'
                          : 'bg-violet-500/10 text-violet-400'
                        }`}>
                        {doc.doc_type === 'Prompt Directives' ? <Cpu size={14} /> : <FileText size={14} />}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-white truncate max-w-[160px]" title={fileName || doc.doc_type}>
                          {fileName || doc.doc_type}
                        </p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-gray-950 border border-gray-800/60 text-gray-400">
                            {doc.department}
                          </span>
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${doc.doc_type === "Prompt Directives"
                              ? "bg-amber-950/25 border border-amber-900/35 text-amber-400"
                              : isFile
                                ? "bg-violet-950/20 border border-violet-900/30 text-violet-400"
                                : "bg-blue-950/20 border border-blue-900/30 text-blue-400"
                            }`}>
                            {doc.doc_type === "Prompt Directives" ? "AI Directive" : isFile ? "File Upload" : "Raw Text"}
                          </span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => deleteKnowledge(doc.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-gray-500 hover:text-rose-400 hover:bg-rose-950/20 rounded transition-all"
                      title="Delete context"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })}

            {knowledge.length === 0 && (
              <div className="text-center py-12 border border-dashed border-gray-800 rounded-xl text-gray-500 text-xs">
                No guidelines stored yet.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Add Knowledge Form */}
        <div className="md:col-span-7 flex flex-col space-y-4 min-h-0 h-full">
          <div className="flex items-center justify-between border-b border-gray-800/80 pb-2 flex-shrink-0">
            <h3 className="text-sm font-bold text-white">Add Knowledge Source</h3>

            {/* Tab controls */}
            <div className="flex bg-gray-950/60 p-0.5 border border-gray-800 rounded-lg">
              <button
                onClick={() => {
                  setKbTab('upload');
                  if (kbType === 'Prompt Directives') {
                    setKbType('Brand Guidelines');
                  }
                }}
                className={`px-3 py-1 rounded-md text-[11px] font-bold transition-all ${kbTab === 'upload'
                    ? 'bg-violet-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                  }`}
              >
                File Upload
              </button>
              <button
                onClick={() => {
                  setKbTab('text');
                  if (kbType === 'Prompt Directives') {
                    setKbType('Brand Guidelines');
                  }
                }}
                className={`px-3 py-1 rounded-md text-[11px] font-bold transition-all ${kbTab === 'text'
                    ? 'bg-violet-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                  }`}
              >
                Manual Text
              </button>
              <button
                onClick={() => {
                  setKbTab('directives');
                  setKbType('Prompt Directives');
                }}
                className={`px-3 py-1 rounded-md text-[11px] font-bold transition-all ${kbTab === 'directives'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                  }`}
              >
                AI Directives
              </button>
            </div>
          </div>

          {/* Department & Doc Type selectors */}
          <div className="grid grid-cols-2 gap-4 flex-shrink-0">
            <div className={`space-y-1 ${kbTab === 'directives' ? 'col-span-2' : ''}`}>
              <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Target Department</label>
              <Select value={kbDept} onValueChange={(val) => val && setKbDept(val)}>
                <SelectTrigger className="w-full bg-gray-900/60 border-gray-800 text-xs text-white">
                  <SelectValue placeholder="Department" />
                </SelectTrigger>
                <SelectContent className="bg-gray-900 border-gray-800 text-white">
                  <SelectItem value="General">General / All Teams</SelectItem>
                  <SelectItem value="Marketing">Marketing AI</SelectItem>
                  <SelectItem value="Sales">Sales CRM</SelectItem>
                  <SelectItem value="HR">Hiring & HR</SelectItem>
                  <SelectItem value="Support">Customer Support</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {kbTab !== 'directives' && (
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Context Category</label>
                <Select value={kbType} onValueChange={(val) => val && setKbType(val)}>
                  <SelectTrigger className="w-full bg-gray-900/60 border-gray-800 text-xs text-white">
                    <SelectValue placeholder="Doc Type" />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-900 border-gray-800 text-white">
                    <SelectItem value="Brand Guidelines">Brand & Tone</SelectItem>
                    <SelectItem value="FAQ">FAQ & Support Runbook</SelectItem>
                    <SelectItem value="Pricing">Pricing & Sourcing Rules</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          {kbTab === 'upload' && (
            /* Tab A: Document Upload Zone */
            <div className="space-y-4 flex-1 flex flex-col justify-between min-h-0">
              <div className="flex-1 min-h-0 border border-dashed border-gray-800 hover:border-violet-500/50 bg-gray-900/20 hover:bg-violet-950/5 rounded-2xl flex flex-col items-center justify-center p-6 text-center transition-all group relative cursor-pointer">
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.md,.csv,.json"
                  onChange={e => {
                    if (e.target.files && e.target.files[0]) {
                      setKbFile(e.target.files[0]);
                    }
                  }}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="p-3 bg-violet-600/10 text-violet-400 rounded-2xl mb-3 shadow-inner group-hover:scale-110 transition-transform">
                  <Upload size={20} />
                </div>
                {kbFile ? (
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-white max-w-[240px] truncate">{kbFile.name}</p>
                    <p className="text-[10px] text-gray-400">{(kbFile.size / 1024).toFixed(1)} KB — Click to change</p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-gray-300">Drag & drop or click to choose file</p>
                    <p className="text-[10px] text-gray-500">Supports PDF, DOCX, TXT, MD, CSV, JSON</p>
                  </div>
                )}
              </div>

              <Button
                onClick={uploadKnowledgeFile}
                disabled={!kbFile || isUploading}
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold py-2.5 rounded-xl shadow-lg shadow-violet-500/20 transition-all flex items-center justify-center gap-2 cursor-pointer flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isUploading ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Parsing and uploading document...
                  </>
                ) : (
                  'Upload & Extract Document'
                )}
              </Button>
            </div>
          )}

          {kbTab === 'text' && (
            /* Tab B: Paste Raw Text Area */
            <div className="space-y-4 flex-1 flex flex-col justify-between min-h-0">
              <Textarea
                placeholder="Paste guidelines, raw details, or FAQ text context here..."
                value={kbContent}
                onChange={e => setKbContent(e.target.value)}
                className="flex-1 bg-gray-900/60 border-gray-800 text-xs text-white focus:border-violet-500 focus:ring-violet-500/20 min-h-0 placeholder-gray-500 resize-none overflow-y-auto"
              />
              <Button
                onClick={addKnowledge}
                disabled={!kbContent}
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold py-2.5 rounded-xl shadow-lg shadow-violet-500/20 transition-all cursor-pointer flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add Text Content
              </Button>
            </div>
          )}

          {kbTab === 'directives' && (
            /* Tab C: AI Directives & Instructions */
            <div className="space-y-4 flex-1 flex flex-col justify-between min-h-0">
              <div className="text-[11px] bg-amber-950/20 border border-amber-900/30 text-amber-300/90 p-3.5 rounded-2xl flex flex-col gap-1.5 flex-shrink-0">
                <span className="font-bold flex items-center gap-1">💡 Custom Brand Directives & Instructions</span>
                <span>Use this to specify strict global instructions (e.g., website link, email, standard tagline, tone rules, or formatting steps) that agents must follow in all outputs.</span>
              </div>
              <Textarea
                placeholder="e.g., 'Always append our contact email: sales@mybrand.com and website link: www.mybrand.com to the end of every marketing campaign post. Make sure to sound bold and write in an authoritative tone.'"
                value={kbContent}
                onChange={e => setKbContent(e.target.value)}
                className="flex-1 bg-gray-900/60 border-gray-800 text-xs text-white focus:border-amber-500 focus:ring-amber-500/20 min-h-0 placeholder-gray-600 resize-none overflow-y-auto"
              />
              <Button
                onClick={addKnowledge}
                disabled={!kbContent}
                className="w-full bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-bold py-2.5 rounded-xl shadow-lg shadow-amber-600/20 transition-all cursor-pointer flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Save AI Directive
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

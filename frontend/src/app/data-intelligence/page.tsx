"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, ArrowDownToLine, CheckCircle2, Clock3, FileArchive, FileText, LoaderCircle, RefreshCw, UploadCloud, XCircle } from "lucide-react";

type Run = { id: string; title: string; status: string; file_count: number; total_bytes: number; created_at?: string | null; completed_at?: string | null; finding_count: number };
type Finding = { id: string; severity: string; title: string; observation: string; why_it_matters: string; recommended_action: string; evidence: Array<{ file?: string; field?: string; metric?: string; value?: unknown }> };
type RunDetail = { run: Run; profile: { artifacts?: Array<Record<string, unknown>> }; findings: Finding[]; report: Record<string, unknown> };

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token") || localStorage.getItem("token") || localStorage.getItem("octaos_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}
function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
function statusLabel(s: string) { return s.replaceAll("_", " ").replace(/^./, x => x.toUpperCase()); }

export default function DataIntelligencePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("Business data analysis");
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadRuns = useCallback(async () => {
    setLoadingRuns(true);
    try {
      const res = await fetch(`${API}/data-intelligence/runs`, { headers: authHeaders(), cache: "no-store" });
      if (!res.ok) throw new Error(res.status === 401 ? "Please sign in again to view your analysis runs." : `Could not load runs (${res.status}).`);
      const data = await res.json();
      setRuns(data.items || []);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load analysis runs."); }
    finally { setLoadingRuns(false); }
  }, []);

  useEffect(() => { void loadRuns(); }, [loadRuns]);

  const openRun = async (run: Run) => {
    setError(""); setNotice("");
    try {
      const res = await fetch(`${API}/data-intelligence/runs/${encodeURIComponent(run.id)}`, { headers: authHeaders(), cache: "no-store" });
      if (!res.ok) throw new Error(`Could not open report (${res.status}).`);
      setSelected(await res.json());
    } catch (e) { setError(e instanceof Error ? e.message : "Could not open report."); }
  };

  const submit = async () => {
    if (!files.length) { setError("Choose at least one file or a ZIP archive first."); return; }
    setLoading(true); setError(""); setNotice(""); setSelected(null);
    const body = new FormData();
    body.append("title", title);
    body.append("idempotency_key", crypto.randomUUID());
    files.forEach(file => body.append("files", file, file.name));
    try {
      const res = await fetch(`${API}/data-intelligence/runs`, { method: "POST", headers: authHeaders(), body });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Analysis failed (${res.status}).`);
      setNotice("Analysis report created. Review the evidence and extraction limitations before acting on findings.");
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      await loadRuns();
      await openRun(data.run);
    } catch (e) { setError(e instanceof Error ? e.message : "Analysis could not be completed."); }
    finally { setLoading(false); }
  };

  const download = async (format: "md" | "json") => {
    if (!selected) return;
    setError("");
    try {
      const res = await fetch(`${API}/data-intelligence/runs/${encodeURIComponent(selected.run.id)}/report.${format}`, { headers: authHeaders() });
      if (!res.ok) throw new Error(`Export failed (${res.status}).`);
      const blob = format === "json" ? new Blob([JSON.stringify(await res.json(), null, 2)], { type: "application/json" }) : await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = `octaos-analysis-${selected.run.id}.${format}`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError(e instanceof Error ? e.message : "Export failed."); }
  };

  return <main className="min-h-screen bg-[#f7f8f7] text-[#171a17]">
    <div className="mx-auto max-w-[1440px] px-5 py-8 md:px-10">
      <header className="mb-8 flex flex-col justify-between gap-4 border-b border-[#e0e4df] pb-6 md:flex-row md:items-end">
        <div>
          <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[#647064]"><Activity size={15}/> Orchestra / Data Intelligence</div>
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Business data workspace</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#626a62]">Upload files, inspect what was actually extracted, review evidence-linked findings, and export a report. Unsupported content is marked—not guessed.</p>
        </div>
        <button onClick={() => void loadRuns()} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-[#d8ded7] bg-white px-4 text-sm font-medium hover:bg-[#f0f2ef]"><RefreshCw size={15}/> Refresh runs</button>
      </header>

      {error && <div role="alert" className="mb-5 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"><XCircle className="mt-0.5 shrink-0" size={17}/>{error}</div>}
      {notice && <div role="status" className="mb-5 flex items-start gap-2 rounded-lg border border-[#d9e6d2] bg-[#f1f7ed] p-3 text-sm text-[#31522a]"><CheckCircle2 className="mt-0.5 shrink-0" size={17}/>{notice}</div>}

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(360px,0.8fr)_minmax(0,1.2fr)]">
        <section className="rounded-2xl border border-[#e0e4df] bg-white p-5 shadow-sm md:p-6">
          <div className="mb-5 flex items-center gap-3"><div className="grid size-10 place-items-center rounded-xl bg-[#eff7e9] text-[#4c742e]"><UploadCloud size={20}/></div><div><h2 className="font-semibold">Start an analysis</h2><p className="text-sm text-[#687068]">Multiple files or one ZIP folder</p></div></div>
          <label className="mb-1 block text-sm font-medium" htmlFor="report-title">Report name</label>
          <input id="report-title" value={title} onChange={e => setTitle(e.target.value)} maxLength={255} className="mb-4 h-11 w-full rounded-lg border border-[#d8ded7] px-3 text-sm outline-none focus:border-[#7ba85a] focus:ring-2 focus:ring-[#dcebd1]"/>
          <input ref={inputRef} type="file" multiple accept=".csv,.tsv,.json,.jsonl,.ndjson,.txt,.md,.log,.pdf,.docx,.xlsx,.xlsm,.pptx,.zip" onChange={e => { setFiles(Array.from(e.target.files || [])); setError(""); }} className="sr-only" id="data-files"/>
          <label htmlFor="data-files" className="flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-[#b9c7b4] bg-[#fafcf9] px-5 text-center transition hover:border-[#789e5c] hover:bg-[#f5f9f1]">
            <UploadCloud size={27} className="mb-3 text-[#567a3e]"/>
            <span className="text-sm font-semibold">Choose files to analyze</span>
            <span className="mt-1 text-xs text-[#687068]">CSV, TSV, JSON, PDF, DOCX, XLSX, PPTX, text, ZIP</span>
            <span className="mt-3 rounded-md border border-[#dce3d8] bg-white px-3 py-1.5 text-xs font-medium">Browse files</span>
          </label>
          {files.length > 0 && <div className="mt-4 rounded-xl border border-[#e0e4df]">
            <div className="flex items-center justify-between border-b border-[#e0e4df] px-3 py-2 text-xs font-semibold"><span>{files.length} selected</span><span>{formatBytes(files.reduce((n, f) => n + f.size, 0))}</span></div>
            <ul className="max-h-48 divide-y divide-[#edf0ec] overflow-auto">{files.map((file, i) => <li key={`${file.name}-${i}`} className="flex items-center gap-2 px-3 py-2 text-xs"><FileText size={14} className="shrink-0 text-[#687068]"/><span className="min-w-0 flex-1 truncate">{file.name}</span><span className="shrink-0 text-[#687068]">{formatBytes(file.size)}</span></li>)}</ul>
            <button onClick={() => { setFiles([]); if (inputRef.current) inputRef.current.value = ""; }} className="m-3 text-xs font-medium text-[#646d64] underline">Clear selection</button>
          </div>}
          <button onClick={() => void submit()} disabled={loading || !files.length} className="mt-5 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#202820] px-4 text-sm font-semibold text-white transition hover:bg-[#344334] disabled:cursor-not-allowed disabled:opacity-50">
            {loading ? <><LoaderCircle className="animate-spin" size={17}/> Analyzing files…</> : <><Activity size={16}/> Analyze and generate report</>}
          </button>
          <div className="mt-4 space-y-2 text-xs leading-5 text-[#697169]"><p>Limits are enforced server-side: per-file, total size, archive expansion, file count and row count.</p><p>Raw uploads are processed in memory and are not retained by this endpoint. Only hashes, extraction metadata, profiles and reports are stored.</p></div>
        </section>

        <section className="rounded-2xl border border-[#e0e4df] bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-[#e0e4df] px-5 py-4 md:px-6"><div><h2 className="font-semibold">Recent analysis runs</h2><p className="mt-1 text-xs text-[#687068]">Tenant-scoped history</p></div><span className="rounded-md bg-[#f0f2ef] px-2.5 py-1 text-xs font-medium">{runs.length} runs</span></div>
          {loadingRuns ? <div className="flex items-center gap-2 p-6 text-sm text-[#687068]"><LoaderCircle size={16} className="animate-spin"/> Loading runs…</div> : runs.length === 0 ? <div className="p-8 text-center"><FileArchive size={26} className="mx-auto mb-3 text-[#7b857b]"/><p className="text-sm font-medium">No analysis runs yet</p><p className="mt-1 text-xs text-[#687068]">Upload a dataset or ZIP archive to create your first report.</p></div> :
            <div className="divide-y divide-[#edf0ec]">{runs.map(run => <button key={run.id} onClick={() => void openRun(run)} className={`block w-full px-5 py-4 text-left transition hover:bg-[#f8faf7] md:px-6 ${selected?.run.id === run.id ? "bg-[#f5f9f1]" : ""}`}>
              <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-semibold">{run.title}</span><span className="rounded-full border border-[#dce3d8] px-2 py-0.5 text-[11px] text-[#586358]">{statusLabel(run.status)}</span></div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#687068]"><span>{run.file_count} files</span><span>{formatBytes(run.total_bytes)}</span><span>{run.finding_count} findings</span><span>{run.created_at ? new Date(run.created_at).toLocaleString() : "Date unavailable"}</span></div>
            </button>)}</div>}
        </section>
      </div>

      {selected && <section className="mt-6 rounded-2xl border border-[#e0e4df] bg-white shadow-sm">
        <div className="flex flex-col justify-between gap-4 border-b border-[#e0e4df] p-5 md:flex-row md:items-center md:px-6"><div><div className="text-xs font-semibold uppercase tracking-[0.15em] text-[#657065]">Report detail</div><h2 className="mt-1 text-xl font-semibold">{selected.run.title}</h2><p className="mt-1 text-xs text-[#687068]">Run ID: {selected.run.id}</p></div><div className="flex flex-wrap gap-2"><button onClick={() => void download("md")} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#d8ded7] px-3 text-sm font-medium hover:bg-[#f5f7f4]"><ArrowDownToLine size={15}/> Markdown</button><button onClick={() => void download("json")} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#d8ded7] px-3 text-sm font-medium hover:bg-[#f5f7f4]"><ArrowDownToLine size={15}/> JSON</button></div></div>
        <div className="grid gap-4 p-5 sm:grid-cols-3 md:px-6">{[
          ["Files processed", String((selected.report.coverage as Record<string, unknown> | undefined)?.files_parsed ?? "—")],
          ["Total findings", String(selected.findings?.length ?? 0)],
          ["Status", statusLabel(selected.run.status)],
        ].map(([label, value]) => <div key={label} className="rounded-xl border border-[#e6eae4] bg-[#fafbf9] p-4"><div className="text-xs text-[#687068]">{label}</div><div className="mt-2 text-2xl font-semibold">{value}</div></div>)}</div>
        <div className="px-5 pb-6 md:px-6">
          <h3 className="mb-3 font-semibold">Evidence-linked findings</h3>
          {!selected.findings?.length ? <p className="rounded-lg bg-[#f7f8f7] p-4 text-sm text-[#687068]">No deterministic findings were produced from the available content. Check extraction coverage before interpreting this as a clean bill of health.</p> : <div className="space-y-3">{selected.findings.map(f => <article key={f.id} className="rounded-xl border border-[#e0e4df] p-4"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${f.severity === "high" ? "bg-[#fbe9e7] text-[#963e32]" : f.severity === "medium" ? "bg-[#fff2d8] text-[#805c16]" : "bg-[#edf1eb] text-[#53634f]"}`}>{f.severity}</span><h4 className="text-sm font-semibold">{f.title}</h4></div><p className="mt-3 text-sm leading-6"><strong>Observed:</strong> {f.observation}</p><p className="mt-2 text-sm leading-6 text-[#596359]"><strong>Why it matters:</strong> {f.why_it_matters}</p><p className="mt-2 text-sm leading-6 text-[#596359]"><strong>Recommended action:</strong> {f.recommended_action}</p>{f.evidence?.length > 0 && <div className="mt-3 rounded-lg bg-[#f7f8f6] p-3"><div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[#687068]">Source evidence</div>{f.evidence.map((e, i) => <div key={i} className="text-xs leading-5 text-[#596359]">{e.file}{e.field ? ` · ${e.field}` : ""} · {e.metric}: {String(e.value)}</div>)}</div>}</article>)}</div>}
          <div className="mt-6 rounded-xl border border-[#e0e4df] p-4"><h3 className="text-sm font-semibold">Method and limitations</h3><p className="mt-2 text-xs leading-5 text-[#687068]">{String((selected.report as Record<string, unknown>).methodology || "Methodology not provided.")}</p><ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-[#687068]">{(((selected.report as Record<string, unknown>).limitations as string[]) || []).map((item, i) => <li key={i}>{item}</li>)}</ul></div>
        </div>
      </section>}
    </div>
  </main>;
}

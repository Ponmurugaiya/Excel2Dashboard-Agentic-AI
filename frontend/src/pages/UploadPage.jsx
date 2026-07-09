import React, { useCallback, useState } from "react";
import {
  UploadCloud, FileSpreadsheet, AlertCircle, Loader2,
  CheckCircle2, X, BarChart3, TrendingUp, ShoppingCart,
  Users, Activity,
} from "lucide-react";
import { uploadAPI } from "../lib/api";
import ModeSelector from "../components/ModeSelector";
import { useToast } from "../components/Toast";

const ACCEPTED = [".xlsx", ".xls", ".xlsm", ".csv"];

/* ── Sample datasets ─────────────────────────────────────────────────────── */
const SAMPLES = [
  {
    id: "sales",
    icon: TrendingUp,
    title: "Sales Report",
    desc:  "Revenue, orders, and product performance",
    color: "emerald",
  },
  {
    id: "ecommerce",
    icon: ShoppingCart,
    title: "E-Commerce",
    desc:  "Customer behaviour and conversion funnel",
    color: "blue",
  },
  {
    id: "hr",
    icon: Users,
    title: "HR Analytics",
    desc:  "Headcount, attrition, and performance",
    color: "violet",
  },
  {
    id: "marketing",
    icon: Activity,
    title: "Marketing",
    desc:  "Campaign ROI and channel attribution",
    color: "amber",
  },
];

const COLOR_MAP = {
  emerald: { bg: "bg-emerald-50", border: "border-emerald-200", icon: "bg-emerald-100 text-emerald-600", title: "text-emerald-700" },
  blue:    { bg: "bg-blue-50",       border: "border-blue-200",       icon: "bg-blue-100 text-blue-600",       title: "text-blue-700" },
  violet:  { bg: "bg-violet-50",   border: "border-violet-200",   icon: "bg-violet-100 text-violet-600", title: "text-violet-700" },
  amber:   { bg: "bg-amber-50",     border: "border-amber-200",     icon: "bg-amber-100 text-amber-600",   title: "text-amber-700" },
};

export default function UploadPage({ onReady, error: externalError }) {
  const [dragging, setDragging]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [localError, setLocalError] = useState(null);
  const [file, setFile]           = useState(null);
  const [progress, setProgress]   = useState(0);
  const [mode, setMode]           = useState("collaborative");
  const toast = useToast();

  const error = localError || externalError;

  const handleFile = useCallback(
    async (f) => {
      if (!f) return;
      const ext = "." + f.name.split(".").pop().toLowerCase();
      if (!ACCEPTED.includes(ext)) {
        setLocalError(`Unsupported file type "${ext}". Please use ${ACCEPTED.join(", ")}.`);
        return;
      }
      if (f.size > 50 * 1024 * 1024) {
        setLocalError("File exceeds the 50 MB limit.");
        return;
      }

      setLocalError(null);
      setFile(f);
      setLoading(true);
      setProgress(0);

      // Fake progress for UX while waiting for server
      const interval = setInterval(() => {
        setProgress((p) => Math.min(p + Math.random() * 15, 85));
      }, 300);

      try {
        const res = await uploadAPI.upload(f);
        setProgress(100);
        clearInterval(interval);
        toast.success("File uploaded", `${f.name} is ready for analysis.`);
        setTimeout(() => onReady(res.data.file_path, mode), 400);
      } catch (err) {
        clearInterval(interval);
        const msg = err.response?.data?.detail || err.message || "Upload failed.";
        setLocalError(msg);
        setFile(null);
        setProgress(0);
        toast.error("Upload failed", msg);
      } finally {
        setLoading(false);
      }
    },
    [mode, onReady, toast]
  );

  const onDragOver  = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = ()  => setDragging(false);
  const onDrop      = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };
  const onInputChange = (e) => handleFile(e.target.files[0]);
  const clearFile = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setFile(null);
    setLocalError(null);
    setProgress(0);
  };

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 space-y-10 animate-fade-in">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-3xl font-extrabold text-slate-900 mb-2">
          New Analysis
        </h1>
        <p className="text-slate-500 text-base">
          Upload your data file and our AI agents will build a full dashboard for you.
        </p>
      </div>

      {/* ── Drop zone ──────────────────────────────────────────────────────── */}
      <div className="card p-1">
        <label
          htmlFor="file-input"
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          className={`
            relative flex flex-col items-center justify-center
            w-full rounded-xl border-2 border-dashed cursor-pointer
            transition-all duration-200 select-none
            min-h-[220px]
            ${loading  ? "pointer-events-none" : ""}
            ${dragging
              ? "border-brand-500 bg-brand-50 scale-[1.01]"
              : file && !loading
                ? "border-emerald-400 bg-emerald-50"
                : "border-slate-200 bg-slate-50 hover:border-brand-400 hover:bg-brand-50:bg-brand-950/10"}
          `}
        >
          {/* Progress overlay */}
          {loading && (
            <div className="absolute inset-0 rounded-xl overflow-hidden">
              <div
                className="absolute bottom-0 left-0 h-1 bg-brand-500 transition-all duration-300 rounded-b-xl"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center gap-4 text-brand-600 py-8">
              <div className="relative">
                <Loader2 className="w-12 h-12 animate-spin" />
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">
                  {Math.round(progress)}%
                </span>
              </div>
              <div className="text-center">
                <p className="font-semibold text-base">Uploading {file?.name}</p>
                <p className="text-sm text-slate-400 mt-1">Please wait…</p>
              </div>
            </div>
          ) : file ? (
            <div className="flex flex-col items-center gap-3 py-8">
              <div className="w-14 h-14 rounded-2xl bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-7 h-7 text-emerald-600" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-slate-800">{file.name}</p>
                <p className="text-sm text-slate-400">
                  {(file.size / 1024).toFixed(0)} KB — ready to analyse
                </p>
              </div>
              <button
                onClick={clearFile}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-red-500
                           transition-colors mt-1"
              >
                <X className="w-3.5 h-3.5" />
                Remove file
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4 py-10 px-6 text-center">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors
                ${dragging ? "bg-brand-100" : "bg-slate-100"}`}
              >
                <UploadCloud className={`w-8 h-8 transition-colors
                  ${dragging ? "text-brand-600" : "text-slate-400"}`}
                />
              </div>
              <div>
                <p className="font-semibold text-slate-700 text-base">
                  {dragging ? "Drop your file here" : "Drag & drop your data file"}
                </p>
                <p className="text-sm text-slate-400 mt-1">
                  or{" "}
                  <span className="text-brand-600 font-medium underline underline-offset-2">
                    click to browse
                  </span>
                </p>
              </div>
              <div className="flex items-center gap-2 flex-wrap justify-center">
                {ACCEPTED.map((ext) => (
                  <span key={ext} className="badge bg-slate-100 text-slate-500">
                    {ext}
                  </span>
                ))}
                <span className="badge bg-slate-100 text-slate-500">
                  max 50 MB
                </span>
              </div>
            </div>
          )}
        </label>
        <input
          id="file-input"
          type="file"
          accept={ACCEPTED.join(",")}
          className="hidden"
          onChange={onInputChange}
          disabled={loading}
        />
      </div>

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {error && (
        <div className="flex items-start gap-3 bg-red-50
                        border border-red-200 rounded-2xl px-5 py-4 animate-fade-in">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-red-700">Upload error</p>
            <p className="text-sm text-red-600 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* ── Sample templates ───────────────────────────────────────────────── */}
      <div>
        <p className="section-heading mb-4">Or try a sample dataset</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {SAMPLES.map(({ id, icon: Icon, title, desc, color }) => {
            const c = COLOR_MAP[color];
            return (
              <button
                key={id}
                disabled={loading}
                className={`
                  flex flex-col items-start gap-3 p-4 rounded-2xl border text-left
                  transition-all duration-150 hover:scale-[1.02] hover:shadow-card-md
                  disabled:opacity-40 disabled:cursor-not-allowed
                  ${c.bg} ${c.border}
                `}
                onClick={() =>
                  toast.info("Coming soon", `Sample dataset "${title}" will be available soon.`)
                }
              >
                <div className={`p-2 rounded-xl ${c.icon}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <p className={`text-xs font-semibold ${c.title}`}>{title}</p>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                    {desc}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Mode selector ──────────────────────────────────────────────────── */}
      <div>
        <p className="section-heading mb-4">Analysis mode</p>
        <ModeSelector mode={mode} onChange={setMode} />
      </div>

    </div>
  );
}

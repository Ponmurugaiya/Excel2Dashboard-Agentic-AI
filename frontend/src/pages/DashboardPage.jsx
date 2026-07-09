import React, { useState } from "react";
import {
  RotateCcw, Save, FolderOpen, Loader2,
  CheckCircle, Terminal, Share2, Download,
  BarChart3, Zap,
} from "lucide-react";
import SpecRenderer       from "../components/SpecRenderer";
import AutoDecisionsPanel from "../components/AutoDecisionsPanel";
import SavedDashboardsDrawer from "../components/SavedDashboardsDrawer";
import AgentLogsModal     from "../components/AgentLogsModal";
import DashboardChat      from "../components/DashboardChat";
import { authAPI }        from "../lib/api";
import { isLoggedIn }     from "../lib/auth";
import { useToast }       from "../components/Toast";

export default function DashboardPage({
  sessionId,
  spec: initialSpec,
  downloads,
  mode,
  events = [],
  onReset,
  onLoadSaved,
}) {
  const [spec, setSpec]             = useState(initialSpec);
  const [saving, setSaving]         = useState(false);
  const [saved, setSaved]           = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [logsOpen, setLogsOpen]     = useState(false);
  const toast = useToast();

  const autoCount = events.filter((e) => e.type === "auto_decision").length;

  const handleSave = async () => {
    if (!isLoggedIn()) {
      toast.warning("Sign in required", "Create an account to save dashboards.");
      return;
    }
    setSaving(true);
    try {
      await authAPI.saveDashboard({
        title:      spec?.title || "Dashboard",
        file_name:  spec?.title || "data",
        session_id: sessionId || "",
        spec_json:  spec,
      });
      setSaved(true);
      toast.success("Dashboard saved", "Find it under 'My Dashboards'.");
      setTimeout(() => setSaved(false), 4000);
    } catch (err) {
      toast.error("Save failed", err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    toast.info("Link copied", "Dashboard link copied to clipboard.");
  };

  return (
    <div className="flex flex-col h-full bg-surface-50">

      {/* ── Toolbar ──────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between gap-4">

        {/* Left — title + mode badge */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-brand-50 flex items-center justify-center flex-shrink-0">
            <BarChart3 className="w-4 h-4 text-brand-600" />
          </div>
          <div className="min-w-0">
            <h1 className="font-bold text-slate-900 text-sm truncate">
              {spec?.title || "Dashboard"}
            </h1>
            {spec?.subtitle && (
              <p className="text-xs text-slate-400 truncate">{spec.subtitle}</p>
            )}
          </div>
          {mode === "autonomous" && (
            <span className="badge bg-amber-100 text-amber-700 flex-shrink-0">
              <Zap className="w-3 h-3" />
              Autonomous
            </span>
          )}
        </div>

        {/* Right — actions */}
        <div className="flex items-center gap-2 flex-shrink-0">

          {/* Agent logs */}
          <button
            onClick={() => setLogsOpen(true)}
            className="btn-ghost text-xs"
            title="View agent run log"
          >
            <Terminal className="w-4 h-4" />
            <span className="hidden sm:inline">Agent Logs</span>
            {autoCount > 0 && (
              <span className="badge bg-amber-100 text-amber-700">
                {autoCount}
              </span>
            )}
          </button>

          {/* Share */}
          <button onClick={handleShare} className="btn-ghost text-xs" title="Copy share link">
            <Share2 className="w-4 h-4" />
            <span className="hidden sm:inline">Share</span>
          </button>

          {isLoggedIn() && (
            <>
              <button
                onClick={() => setDrawerOpen(true)}
                className="btn-secondary text-xs"
              >
                <FolderOpen className="w-4 h-4" />
                <span className="hidden sm:inline">My Dashboards</span>
              </button>

              <button
                onClick={handleSave}
                disabled={saving || saved}
                className="btn-primary text-xs"
              >
                {saving  ? <Loader2     className="w-4 h-4 animate-spin" />
                : saved  ? <CheckCircle className="w-4 h-4" />
                :           <Save       className="w-4 h-4" />}
                {saved ? "Saved" : "Save"}
              </button>
            </>
          )}

          <button
            onClick={onReset}
            className="btn-ghost text-xs"
            title="Start new analysis"
          >
            <RotateCcw className="w-4 h-4" />
            <span className="hidden sm:inline">New Analysis</span>
          </button>
        </div>
      </div>

      {/* ── Autonomous decisions banner ───────────────────────────────────── */}
      {mode === "autonomous" && spec?.auto_decisions?.length > 0 && (
        <div className="flex-shrink-0 px-6 pt-4">
          <AutoDecisionsPanel decisions={spec.auto_decisions} />
        </div>
      )}

      {/* ── Dashboard content ─────────────────────────────────────────────── */}
      <div className="flex-1 overflow-auto">
        <SpecRenderer spec={spec} sessionId={sessionId} downloads={downloads} />
      </div>

      {/* ── Modals & drawers ─────────────────────────────────────────────── */}
      <AgentLogsModal
        events={events}
        open={logsOpen}
        onClose={() => setLogsOpen(false)}
      />

      <SavedDashboardsDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onLoad={(saved) => {
          onLoadSaved(saved.spec_json);
          setDrawerOpen(false);
        }}
      />

      {/* ── Floating chat ─────────────────────────────────────────────────── */}
      {sessionId && (
        <DashboardChat sessionId={sessionId} onSpecUpdate={setSpec} />
      )}
    </div>
  );
}

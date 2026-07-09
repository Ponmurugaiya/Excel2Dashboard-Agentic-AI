import React, { useState } from "react";
import { RotateCcw, FileSpreadsheet, Save, FolderOpen, Loader2, CheckCircle, Terminal } from "lucide-react";
import SpecRenderer from "../components/SpecRenderer";
import AutoDecisionsPanel from "../components/AutoDecisionsPanel";
import SavedDashboardsDrawer from "../components/SavedDashboardsDrawer";
import AgentLogsModal from "../components/AgentLogsModal";
import DashboardChat from "../components/DashboardChat";
import { authAPI } from "../lib/api";
import { isLoggedIn } from "../lib/auth";

/**
 * Dashboard screen.
 * - Renders the agent-designed dashboard spec (live-updated by chat)
 * - Toolbar: Save, My Dashboards, Agent Logs, New Analysis
 * - Floating chat button for Q&A and spec modifications
 */
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

  const handleSave = async () => {
    if (!isLoggedIn()) return;
    setSaving(true);
    try {
      await authAPI.saveDashboard({
        title: spec?.title || "Dashboard",
        file_name: spec?.title || "data",
        session_id: sessionId || "",
        spec_json: spec,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Save failed:", err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <header className="bg-white border-b border-gray-200 px-6 py-3.5
                         flex items-center justify-between sticky top-0 z-20">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-blue-600" />
          <span className="font-semibold text-gray-800">{spec?.title || "Dashboard"}</span>
          {mode === "autonomous" && (
            <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
              ⚡ Autonomous
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Agent logs button — always visible */}
          <button
            onClick={() => setLogsOpen(true)}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600
                       border border-gray-200 hover:border-blue-300 rounded-lg px-3 py-1.5 transition-colors"
            title="View agent run log"
          >
            <Terminal className="w-4 h-4" />
            Agent Logs
            {events.filter(e => e.type === "auto_decision").length > 0 && (
              <span className="text-xs bg-amber-100 text-amber-700 rounded-full px-1.5">
                {events.filter(e => e.type === "auto_decision").length}⚡
              </span>
            )}
          </button>

          {isLoggedIn() && (
            <>
              <button
                onClick={() => setDrawerOpen(true)}
                className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600
                           border border-gray-200 hover:border-blue-300 rounded-lg px-3 py-1.5 transition-colors"
              >
                <FolderOpen className="w-4 h-4" />
                My Dashboards
              </button>

              <button
                onClick={handleSave}
                disabled={saving || saved}
                className="flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-700
                           text-white rounded-lg px-3 py-1.5 font-medium transition-colors disabled:opacity-70"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" />
                 : saved ? <CheckCircle className="w-4 h-4" />
                 : <Save className="w-4 h-4" />}
                {saved ? "Saved" : "Save"}
              </button>
            </>
          )}

          <button
            onClick={onReset}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-blue-600 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            New analysis
          </button>
        </div>
      </header>

      {/* Autonomous decisions panel */}
      {mode === "autonomous" && spec?.auto_decisions?.length > 0 && (
        <div className="max-w-7xl mx-auto px-6 pt-5">
          <AutoDecisionsPanel decisions={spec.auto_decisions} />
        </div>
      )}

      {/* Dashboard spec renderer */}
      <SpecRenderer spec={spec} sessionId={sessionId} downloads={downloads} />

      {/* Agent logs modal */}
      <AgentLogsModal
        events={events}
        open={logsOpen}
        onClose={() => setLogsOpen(false)}
      />

      {/* Saved dashboards drawer */}
      <SavedDashboardsDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onLoad={(saved) => {
          onLoadSaved(saved.spec_json);
          setDrawerOpen(false);
        }}
      />

      {/* Floating chat — only when we have a live session */}
      {sessionId && (
        <DashboardChat
          sessionId={sessionId}
          onSpecUpdate={setSpec}
        />
      )}
    </div>
  );
}

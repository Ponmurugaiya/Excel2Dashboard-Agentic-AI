import React, { useEffect, useState } from "react";
import { FolderOpen, Trash2, X, Loader2, BarChart3, Calendar, ExternalLink } from "lucide-react";
import { authAPI } from "../lib/api";

/**
 * Slide-out drawer listing the user's saved dashboards.
 */
export default function SavedDashboardsDrawer({ open, onClose, onLoad }) {
  const [dashboards, setDashboards] = useState([]);
  const [loading, setLoading]       = useState(false);
  const [deleting, setDeleting]     = useState(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    authAPI.listDashboards()
      .then((r) => setDashboards(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [open]);

  const handleLoad = async (id) => {
    try {
      const res = await authAPI.loadDashboard(id);
      onLoad(res.data);
      onClose();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    setDeleting(id);
    try {
      await authAPI.deleteDashboard(id);
      setDashboards((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      console.error(err);
    } finally {
      setDeleting(null);
    }
  };

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-40 animate-fade-in"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="
        fixed right-0 top-0 h-full w-80
        bg-white
        border-l border-slate-200
        shadow-card-lg z-50 flex flex-col
        animate-slide-in-right
      ">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4
                        border-b border-slate-100">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-brand-600" />
            <h2 className="font-bold text-slate-900 text-sm">Saved Dashboards</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600:text-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-slate-400">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : dashboards.length === 0 ? (
            <div className="text-center py-16 text-slate-400">
              <div className="w-14 h-14 rounded-2xl bg-slate-100
                              flex items-center justify-center mx-auto mb-3">
                <BarChart3 className="w-6 h-6 opacity-50" />
              </div>
              <p className="text-sm font-medium">No saved dashboards yet</p>
              <p className="text-xs mt-1">Run an analysis and save it to see it here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {dashboards.map((d) => (
                <div
                  key={d.id}
                  className="
                    card
                    p-4 hover:border-brand-300:border-brand-700
                    transition-all hover:shadow-card-md
                  "
                >
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-slate-800 truncate">
                        {d.title}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5 truncate">
                        {d.file_name}
                      </p>
                      <div className="flex items-center gap-1 mt-1 text-xs text-slate-400">
                        <Calendar className="w-3 h-3" />
                        {new Date(d.created_at * 1000).toLocaleDateString(undefined, {
                          month: "short", day: "numeric", year: "numeric",
                        })}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDelete(d.id)}
                      disabled={deleting === d.id}
                      className="text-slate-300 hover:text-red-500:text-red-400
                                 transition-colors p-1.5 rounded-lg hover:bg-red-50:bg-red-950/30"
                    >
                      {deleting === d.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Trash2  className="w-3.5 h-3.5" />
                      }
                    </button>
                  </div>
                  <button
                    onClick={() => handleLoad(d.id)}
                    className="btn-primary w-full justify-center text-xs py-2"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Load Dashboard
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

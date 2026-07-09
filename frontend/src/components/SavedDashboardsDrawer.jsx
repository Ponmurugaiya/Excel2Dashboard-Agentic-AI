import React, { useEffect, useState } from "react";
import { FolderOpen, Trash2, X, Loader2, BarChart2 } from "lucide-react";
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
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-80 bg-white shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-blue-600" />
            <h2 className="font-semibold text-gray-800 text-sm">Saved Dashboards</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-gray-400">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          ) : dashboards.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <BarChart2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No saved dashboards yet.</p>
              <p className="text-xs mt-1">Run an analysis and save it to see it here.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {dashboards.map((d) => (
                <div
                  key={d.id}
                  className="bg-gray-50 border border-gray-200 rounded-xl p-3 hover:border-blue-300 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{d.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{d.file_name}</p>
                      <p className="text-xs text-gray-400">
                        {new Date(d.created_at * 1000).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDelete(d.id)}
                      disabled={deleting === d.id}
                      className="text-gray-300 hover:text-red-500 transition-colors p-1"
                    >
                      {deleting === d.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <Trash2 className="w-3.5 h-3.5" />
                      }
                    </button>
                  </div>
                  <button
                    onClick={() => handleLoad(d.id)}
                    className="mt-2 w-full text-xs bg-blue-600 hover:bg-blue-700 text-white
                               py-1.5 rounded-lg font-medium transition-colors"
                  >
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

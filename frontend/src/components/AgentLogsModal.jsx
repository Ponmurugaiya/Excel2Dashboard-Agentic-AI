import React, { useState } from "react";
import { X, Terminal, Zap, CheckCircle, XCircle, ChevronDown, ChevronUp } from "lucide-react";

/**
 * Modal showing the full agent run log after dashboard is done.
 * Grouped by agent, with auto-decisions highlighted.
 */
export default function AgentLogsModal({ events, open, onClose }) {
  const [filter, setFilter] = useState("all"); // "all" | "auto" | "errors"

  if (!open) return null;

  const filtered = events.filter((e) => {
    if (filter === "auto")   return e.type === "auto_decision";
    if (filter === "errors") return e.type === "error";
    return ["log", "auto_decision", "error"].includes(e.type);
  });

  const counts = {
    all:    events.filter(e => ["log","auto_decision","error"].includes(e.type)).length,
    auto:   events.filter(e => e.type === "auto_decision").length,
    errors: events.filter(e => e.type === "error").length,
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        {/* Modal */}
        <div
          className="bg-gray-950 rounded-2xl border border-gray-700 w-full max-w-3xl
                     max-h-[80vh] flex flex-col shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-blue-400" />
              <h2 className="font-semibold text-white text-sm">Agent Run Log</h2>
              <span className="text-xs text-gray-500">{counts.all} events</span>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1 px-5 py-2 border-b border-gray-800">
            {[
              { id: "all",    label: "All",          count: counts.all },
              { id: "auto",   label: "⚡ Auto",      count: counts.auto },
              { id: "errors", label: "Errors",       count: counts.errors },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`text-xs px-3 py-1 rounded-lg transition-colors
                  ${filter === f.id
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"}`}
              >
                {f.label}
                <span className="ml-1 opacity-60">({f.count})</span>
              </button>
            ))}
          </div>

          {/* Log entries */}
          <div className="flex-1 overflow-y-auto p-5 font-mono text-xs space-y-1">
            {filtered.length === 0 && (
              <p className="text-gray-600">No events match this filter.</p>
            )}
            {filtered.map((ev, i) => (
              <LogEntry key={ev.id || i} event={ev} />
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

function LogEntry({ event }) {
  const { type, from, payload, timestamp } = event;
  const time = new Date(timestamp * 1000).toLocaleTimeString();

  if (type === "auto_decision") {
    return (
      <div className="flex items-start gap-2 text-amber-400 py-0.5">
        <Zap className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <span className="text-gray-500 w-16 flex-shrink-0">{time}</span>
        <span>
          <span className="text-amber-300 font-bold">[Auto] </span>
          <span className="text-amber-200">{payload.context}</span>
          <span className="text-amber-400"> → {payload.decision}</span>
          <span className="text-amber-600 ml-1">({payload.reason})</span>
        </span>
      </div>
    );
  }

  if (type === "error") {
    return (
      <div className="flex items-start gap-2 text-red-400 py-0.5">
        <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <span className="text-gray-500 w-16 flex-shrink-0">{time}</span>
        <span>
          <span className="text-red-300 font-bold">[{from}] </span>
          {payload.text}
        </span>
      </div>
    );
  }

  const text = payload.text || "";
  const isSuccess = text.startsWith("✓");
  const isSystem  = from === "system";

  return (
    <div className={`flex items-start gap-2 py-0.5 ${
      isSuccess ? "text-green-400" : isSystem ? "text-gray-500" : "text-gray-300"
    }`}>
      {isSuccess
        ? <CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
        : <span className="w-3 text-center text-gray-600">›</span>
      }
      <span className="text-gray-600 w-16 flex-shrink-0">{time}</span>
      <span>
        {!isSystem && (
          <span className="text-blue-400 font-bold">[{from}] </span>
        )}
        {text}
      </span>
    </div>
  );
}

import React, { useState } from "react";
import { X, Terminal, Zap, CheckCircle, XCircle, User, ChevronDown, ChevronUp } from "lucide-react";

/**
 * Full agent run log modal.
 * Tabs: All | Decisions | ⚡ Auto | Errors
 * Decision entries are fully expandable — show question, all options, chosen answer, reason.
 */
export default function AgentLogsModal({ events, open, onClose }) {
  const [filter, setFilter] = useState("all");

  if (!open) return null;

  const isDecision  = (e) => e.type === "log" && e.payload?.log_type === "decision";
  const isAutoShort = (e) => e.type === "auto_decision";
  const isError     = (e) => e.type === "error";
  const isLog       = (e) => e.type === "log";

  const allVisible   = events.filter((e) => isLog(e) || isAutoShort(e) || isError(e));
  const decisions    = events.filter(isDecision);
  const autoDecisions = events.filter(isAutoShort);
  const errors       = events.filter(isError);

  const counts = {
    all:       allVisible.length,
    decisions: decisions.length,
    auto:      autoDecisions.length,
    errors:    errors.length,
  };

  const filtered =
    filter === "decisions" ? decisions :
    filter === "auto"      ? autoDecisions :
    filter === "errors"    ? errors :
    allVisible;

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-slate-950 rounded-2xl border border-slate-800 w-full max-w-3xl
                   max-h-[85vh] flex flex-col shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-blue-400" />
            <h2 className="font-semibold text-white text-sm">Agent Run Log</h2>
            <span className="text-xs text-gray-500">{counts.all} events</span>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 px-5 py-2 border-b border-gray-800">
          {[
            { id: "all",       label: "All",        count: counts.all },
            { id: "decisions", label: "Decisions",  count: counts.decisions },
            { id: "auto",      label: "⚡ Auto",    count: counts.auto },
            { id: "errors",    label: "Errors",     count: counts.errors },
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
        <div className="flex-1 overflow-y-auto p-5 space-y-1 font-mono text-xs">
          {filtered.length === 0 && (
            <p className="text-gray-600 text-center py-8">No events in this category.</p>
          )}
          {filtered.map((ev, i) => (
            <LogEntry key={ev.id || i} event={ev} />
          ))}
        </div>
      </div>
    </div>
  );
}

function LogEntry({ event }) {
  const { type, from, payload, timestamp } = event;
  const time = new Date(timestamp * 1000).toLocaleTimeString();

  // ── Auto-decision (compact) ───────────────────────────────────────────────
  if (type === "auto_decision") {
    return (
      <div className="flex items-start gap-2 text-amber-400 py-0.5">
        <Zap className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <span className="text-gray-600 w-16 flex-shrink-0">{time}</span>
        <span>
          <span className="text-amber-300 font-bold">[Auto] </span>
          <span className="text-amber-200">{payload.context}</span>
          <span className="text-amber-400"> → {payload.decision}</span>
          <span className="text-amber-600 ml-1">({payload.reason})</span>
        </span>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (type === "error") {
    return (
      <div className="flex items-start gap-2 text-red-400 py-0.5">
        <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <span className="text-gray-600 w-16 flex-shrink-0">{time}</span>
        <span>
          <span className="text-red-300 font-bold">[{from}] </span>
          {payload.text}
        </span>
      </div>
    );
  }

  // ── Rich decision log ─────────────────────────────────────────────────────
  if (payload?.log_type === "decision" && payload.decision_point) {
    return (
      <ExpandableDecisionEntry
        dp={payload.decision_point}
        text={payload.text}
        time={time}
      />
    );
  }

  // ── Standard log ──────────────────────────────────────────────────────────
  const text = payload?.text || "";
  const isSuccess = text.startsWith("✓");
  const isSystem  = from === "system";

  if (text.includes("\n")) {
    return (
      <div className={`py-0.5 ${isSystem ? "text-gray-500" : "text-gray-300"}`}>
        <span className="text-gray-600 w-16 inline-block">{time}</span>
        {!isSystem && <span className="text-blue-400 font-bold">[{from}] </span>}
        {text.split("\n").map((line, i) => (
          <div key={i} className={i === 0 ? "inline" : "block pl-20 text-gray-400"}>
            {line}
          </div>
        ))}
      </div>
    );
  }

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
        {!isSystem && <span className="text-blue-400 font-bold">[{from}] </span>}
        {text}
      </span>
    </div>
  );
}

function ExpandableDecisionEntry({ dp, text, time }) {
  const [open, setOpen] = useState(false);
  const isAuto = dp.mode === "autonomous";

  return (
    <div className={`rounded-lg border my-1 ${
      isAuto ? "border-amber-800 bg-amber-950" : "border-blue-800 bg-blue-950"
    }`}>
      {/* Header row */}
      <button
        className="w-full flex items-start gap-2 px-3 py-2 text-left"
        onClick={() => setOpen(!open)}
      >
        {isAuto
          ? <Zap  className="w-3 h-3 mt-0.5 flex-shrink-0 text-amber-400" />
          : <User className="w-3 h-3 mt-0.5 flex-shrink-0 text-blue-400" />
        }
        <span className="text-gray-600 w-16 flex-shrink-0">{time}</span>
        <span className={`flex-1 ${isAuto ? "text-amber-300" : "text-blue-300"}`}>
          {text}
        </span>
        {open
          ? <ChevronUp   className="w-3 h-3 text-gray-500 mt-0.5" />
          : <ChevronDown className="w-3 h-3 text-gray-500 mt-0.5" />
        }
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="px-4 pb-3 space-y-2 text-xs border-t border-gray-800 pt-2">
          {/* Agent + context */}
          <div className="flex items-center gap-2">
            <span className={`font-semibold ${isAuto ? "text-amber-400" : "text-blue-400"}`}>
              {dp.icon} {dp.agent}
            </span>
            <span className="text-gray-500">·</span>
            <span className="text-gray-400">{dp.context}</span>
          </div>

          {/* Question */}
          {dp.question && (
            <p className="text-gray-200 font-medium border-l-2 border-gray-700 pl-2">
              {dp.question}
            </p>
          )}

          {/* Options */}
          {dp.options?.length > 0 && (
            <div className="space-y-1">
              <p className="text-gray-600 uppercase tracking-wider text-xs">Options</p>
              {dp.options.map((opt) => {
                const isSuggested = opt.id === dp.suggested_answer;
                const isChosen    = opt.id === dp.chosen_answer;
                return (
                  <div
                    key={opt.id}
                    className={`flex items-start gap-2 px-2 py-1 rounded ${
                      isChosen    ? "bg-green-900/60 text-green-300" :
                      isSuggested ? "bg-gray-800 text-gray-400"      :
                                    "text-gray-600"
                    }`}
                  >
                    <span className="w-4 text-center flex-shrink-0">
                      {isChosen ? "✓" : isSuggested ? "→" : "·"}
                    </span>
                    <div>
                      <span className="font-medium">{opt.label}</span>
                      {opt.description && (
                        <span className="text-gray-500 ml-1">— {opt.description}</span>
                      )}
                    </div>
                    <div className="ml-auto flex-shrink-0 flex gap-1">
                      {isChosen    && <span className="text-green-500 text-xs">chosen</span>}
                      {isSuggested && !isChosen && <span className="text-gray-600 text-xs">suggested</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Reason + Impact */}
          <div className="space-y-0.5">
            {dp.reason && (
              <p className="text-gray-500">
                <span className="text-gray-600">Reason: </span>{dp.reason}
              </p>
            )}
            {dp.impact && (
              <p className="text-gray-600">
                <span className="text-gray-700">Impact: </span>{dp.impact}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

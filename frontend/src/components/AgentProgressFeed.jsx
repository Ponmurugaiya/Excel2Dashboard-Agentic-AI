import React, { useEffect, useRef, useState } from "react";
import { CheckCircle, XCircle, Zap, User, ChevronDown, ChevronUp } from "lucide-react";

const STATUS_LABELS = {
  created:   "Initialising...",
  parsing:   "Parsing file...",
  cleaning:  "Cleaning data...",
  planning:  "Planning analysis...",
  analysing: "Running analyses...",
  insight:   "Generating insights...",
  designing: "Designing dashboard...",
  done:      "Done",
  error:     "Error",
};

/**
 * Live feed of agent messages during pipeline execution.
 * Shows all log types including decision logs (auto + collaborative).
 */
export default function AgentProgressFeed({ events, status }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const displayEvents = events.filter((e) =>
    ["log", "auto_decision", "error"].includes(e.type)
  );

  return (
    <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          status === "done"  ? "bg-emerald-400" :
          status === "error" ? "bg-red-400"     :
          "bg-brand-400 animate-pulse"
        }`} />
        <span className="text-xs font-mono text-slate-400">
          {STATUS_LABELS[status] || status}
        </span>
        <span className="ml-auto text-xs font-mono text-slate-600">
          {displayEvents.length} events
        </span>
      </div>

      {/* Events */}
      <div className="p-4 space-y-1 max-h-72 overflow-y-auto font-mono text-xs">
        {displayEvents.length === 0 && (
          <p className="text-slate-600">Waiting for agents to start…</p>
        )}
        {displayEvents.map((ev, i) => (
          <EventRow key={ev.id || i} event={ev} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function EventRow({ event }) {
  const { type, from, payload } = event;

  // ── Auto-decision (compact ⚡ line) ────────────────────────────────────────
  if (type === "auto_decision") {
    return (
      <div className="flex items-start gap-2 text-amber-400">
        <Zap className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <span>
          <span className="text-amber-300 font-semibold">[Auto] </span>
          {payload.context}
          <span className="text-amber-400"> → {payload.decision}</span>
          <span className="text-amber-600 ml-1">({payload.reason})</span>
        </span>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (type === "error") {
    return (
      <div className="flex items-start gap-2 text-red-400">
        <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <span>
          <span className="text-red-300 font-semibold">[{from}] </span>
          {payload.text}
        </span>
      </div>
    );
  }

  // ── Decision log (rich expandable) ────────────────────────────────────────
  if (payload.log_type === "decision" && payload.decision_point) {
    return <DecisionRow dp={payload.decision_point} text={payload.text} />;
  }

  // ── Standard log ──────────────────────────────────────────────────────────
  const text = payload.text || "";
  const isSuccess = text.startsWith("✓");
  const isSystem  = from === "system";

  // Multi-line log (e.g. analysis plan)
  if (text.includes("\n")) {
    return (
      <div className={`${isSystem ? "text-gray-500" : "text-gray-300"}`}>
        {!isSystem && (
          <span className="text-blue-400 font-semibold">[{from}] </span>
        )}
        {text.split("\n").map((line, i) => (
          <div key={i} className={i === 0 ? "" : "pl-4 text-gray-400"}>
            {line}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`flex items-start gap-2 ${
      isSuccess ? "text-green-400" : isSystem ? "text-gray-500" : "text-gray-300"
    }`}>
      {isSuccess
        ? <CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
        : <span className="w-3 text-center text-gray-600">›</span>
      }
      <span>
        {!isSystem && (
          <span className="text-blue-400 font-semibold">[{from}] </span>
        )}
        {text}
      </span>
    </div>
  );
}

function DecisionRow({ dp, text }) {
  const [expanded, setExpanded] = useState(false);
  const isAuto = dp.mode === "autonomous";

  return (
    <div className={`rounded-lg border my-1 ${
      isAuto
        ? "border-amber-800 bg-amber-950"
        : "border-blue-800 bg-blue-950"
    }`}>
      {/* Summary line — always visible */}
      <button
        className="w-full flex items-start gap-2 px-3 py-2 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {isAuto
          ? <Zap className="w-3 h-3 mt-0.5 flex-shrink-0 text-amber-400" />
          : <User className="w-3 h-3 mt-0.5 flex-shrink-0 text-blue-400" />
        }
        <span className={`flex-1 ${isAuto ? "text-amber-300" : "text-blue-300"}`}>
          {text}
        </span>
        {expanded
          ? <ChevronUp className="w-3 h-3 text-gray-500 flex-shrink-0" />
          : <ChevronDown className="w-3 h-3 text-gray-500 flex-shrink-0" />
        }
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-3 pb-3 space-y-1.5 text-xs">
          {dp.context && (
            <p className="text-gray-400"><span className="text-gray-500">Context: </span>{dp.context}</p>
          )}
          {dp.question && (
            <p className="text-gray-300 font-medium">{dp.question}</p>
          )}

          {/* Options list */}
          {dp.options?.length > 0 && (
            <div className="space-y-0.5">
              {dp.options.map((opt) => {
                const isSuggested = opt.id === dp.suggested_answer;
                const isChosen    = opt.id === dp.chosen_answer;
                return (
                  <div
                    key={opt.id}
                    className={`flex items-center gap-2 px-2 py-1 rounded ${
                      isChosen
                        ? "bg-green-900 text-green-300"
                        : isSuggested
                          ? "bg-gray-800 text-gray-400"
                          : "text-gray-600"
                    }`}
                  >
                    <span className="w-4 text-center">
                      {isChosen ? "✓" : isSuggested ? "→" : " "}
                    </span>
                    <span className="font-medium">{opt.label}</span>
                    {opt.description && (
                      <span className="text-gray-500 text-xs">— {opt.description}</span>
                    )}
                    {isSuggested && !isChosen && (
                      <span className="ml-auto text-xs text-gray-600">suggested</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

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
      )}
    </div>
  );
}

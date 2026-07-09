import React, { useEffect, useRef } from "react";
import { CheckCircle, XCircle, Zap, Info } from "lucide-react";

const STATUS_LABELS = {
  created:    "Initialising...",
  parsing:    "Parsing file...",
  cleaning:   "Cleaning data...",
  planning:   "Planning analysis...",
  analysing:  "Running analyses...",
  insight:    "Generating insights...",
  designing:  "Designing dashboard...",
  done:       "Done",
  error:      "Error",
};

/**
 * Live feed of agent messages during pipeline execution.
 */
export default function AgentProgressFeed({ events, status }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const displayEvents = events.filter(
    (e) => ["log", "auto_decision", "error"].includes(e.type)
  );

  return (
    <div className="bg-gray-950 rounded-2xl border border-gray-800 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          status === "done" ? "bg-green-400" :
          status === "error" ? "bg-red-400" :
          "bg-blue-400 animate-pulse"
        }`} />
        <span className="text-xs font-mono text-gray-400">
          {STATUS_LABELS[status] || status}
        </span>
      </div>

      {/* Event list */}
      <div className="p-4 space-y-1.5 max-h-64 overflow-y-auto font-mono text-xs">
        {displayEvents.length === 0 && (
          <p className="text-gray-600">Waiting for agents to start...</p>
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

  if (type === "auto_decision") {
    return (
      <div className="flex items-start gap-2 text-amber-400">
        <Zap className="w-3 h-3 mt-0.5 flex-shrink-0" />
        <span>
          <span className="text-amber-300 font-semibold">[Auto] </span>
          {payload.context} → {payload.decision}
          <span className="text-amber-600 ml-1">({payload.reason})</span>
        </span>
      </div>
    );
  }

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

  // log
  const text = payload.text || "";
  const isSuccess = text.startsWith("✓");
  const isSystem = from === "system";

  return (
    <div className={`flex items-start gap-2 ${
      isSuccess ? "text-green-400" : isSystem ? "text-gray-500" : "text-gray-300"
    }`}>
      {isSuccess
        ? <CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0 text-green-400" />
        : <span className="w-3 h-3 mt-0.5 flex-shrink-0 text-center text-gray-600">›</span>
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

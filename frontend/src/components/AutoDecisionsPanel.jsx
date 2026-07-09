import React, { useState } from "react";
import { Zap, ChevronDown, ChevronUp } from "lucide-react";

/**
 * After an autonomous run, shows all auto-decisions so the user can review them.
 */
export default function AutoDecisionsPanel({ decisions }) {
  const [open, setOpen] = useState(false);

  if (!decisions || decisions.length === 0) return null;

  return (
    <div className="rounded-2xl border border-amber-200 overflow-hidden
                    bg-amber-50">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5
                   hover:bg-amber-100:bg-amber-950/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-100">
            <Zap className="w-3.5 h-3.5 text-amber-600" />
          </div>
          <span className="text-sm font-bold text-amber-800">
            {decisions.length} Autonomous Decision{decisions.length !== 1 ? "s" : ""} Made
          </span>
          <span className="badge bg-amber-100 text-amber-700 text-xs">
            Click to review
          </span>
        </div>
        {open
          ? <ChevronUp   className="w-4 h-4 text-amber-500" />
          : <ChevronDown className="w-4 h-4 text-amber-500" />
        }
      </button>

      {open && (
        <div className="border-t border-amber-200 divide-y
                        divide-amber-100">
          {decisions.map((d, i) => (
            <div key={i} className="px-5 py-3.5">
              <p className="text-xs font-bold text-amber-600 uppercase tracking-wider mb-1">
                {d.context}
              </p>
              <p className="text-sm text-amber-900">
                <span className="font-semibold">Decision: </span>{d.decision}
              </p>
              <p className="text-xs text-amber-600 mt-1">
                <span className="font-semibold">Reason: </span>{d.reason}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import React, { useState } from "react";
import { Zap, ChevronDown, ChevronUp } from "lucide-react";

/**
 * After an autonomous run, shows all auto-decisions so the user can review them.
 */
export default function AutoDecisionsPanel({ decisions }) {
  const [open, setOpen] = useState(false);

  if (!decisions || decisions.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-amber-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-600" />
          <span className="text-sm font-semibold text-amber-800">
            {decisions.length} Autonomous Decision{decisions.length !== 1 ? "s" : ""} Made
          </span>
          <span className="text-xs text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">
            Click to review
          </span>
        </div>
        {open ? (
          <ChevronUp className="w-4 h-4 text-amber-600" />
        ) : (
          <ChevronDown className="w-4 h-4 text-amber-600" />
        )}
      </button>

      {open && (
        <div className="border-t border-amber-200 divide-y divide-amber-100">
          {decisions.map((d, i) => (
            <div key={i} className="px-5 py-3">
              <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-0.5">
                {d.context}
              </p>
              <p className="text-sm text-amber-900">
                <span className="font-medium">Decision: </span>{d.decision}
              </p>
              <p className="text-xs text-amber-600 mt-0.5">
                <span className="font-medium">Reason: </span>{d.reason}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

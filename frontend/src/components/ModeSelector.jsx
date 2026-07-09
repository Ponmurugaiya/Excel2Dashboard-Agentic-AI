import React from "react";
import { Users, Zap } from "lucide-react";

/**
 * Mode selector shown before starting analysis.
 * Collaborative (default) vs Autonomous.
 */
export default function ModeSelector({ mode, onChange }) {
  return (
    <div className="w-full max-w-lg">
      <p className="text-sm font-medium text-gray-700 mb-3">How should the agents run?</p>
      <div className="grid grid-cols-2 gap-3">
        {/* Collaborative */}
        <button
          onClick={() => onChange("collaborative")}
          className={`
            flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition-all
            ${mode === "collaborative"
              ? "border-blue-500 bg-blue-50"
              : "border-gray-200 bg-white hover:border-gray-300"}
          `}
        >
          <div className={`p-2 rounded-lg ${mode === "collaborative" ? "bg-blue-100" : "bg-gray-100"}`}>
            <Users className={`w-4 h-4 ${mode === "collaborative" ? "text-blue-600" : "text-gray-500"}`} />
          </div>
          <div>
            <p className={`text-sm font-semibold ${mode === "collaborative" ? "text-blue-700" : "text-gray-800"}`}>
              Collaborative
            </p>
            <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
              Agents pause and ask you at key decision points. You guide the analysis.
            </p>
          </div>
          {mode === "collaborative" && (
            <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
              Selected
            </span>
          )}
        </button>

        {/* Autonomous */}
        <button
          onClick={() => onChange("autonomous")}
          className={`
            flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition-all
            ${mode === "autonomous"
              ? "border-amber-500 bg-amber-50"
              : "border-gray-200 bg-white hover:border-gray-300"}
          `}
        >
          <div className={`p-2 rounded-lg ${mode === "autonomous" ? "bg-amber-100" : "bg-gray-100"}`}>
            <Zap className={`w-4 h-4 ${mode === "autonomous" ? "text-amber-600" : "text-gray-500"}`} />
          </div>
          <div>
            <p className={`text-sm font-semibold ${mode === "autonomous" ? "text-amber-700" : "text-gray-800"}`}>
              Fully Autonomous
            </p>
            <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
              Agents make all decisions automatically. No interruptions. Review decisions after.
            </p>
          </div>
          {mode === "autonomous" && (
            <span className="text-xs font-medium text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">
              Selected
            </span>
          )}
        </button>
      </div>
    </div>
  );
}

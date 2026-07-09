import React, { useState } from "react";
import { Loader2 } from "lucide-react";

/**
 * Renders a decision point card when an agent pauses for user input.
 * Shows: context, question, suggested answer + reason, option buttons.
 */
export default function AgentQuestionCard({ question, onAnswer, loading }) {
  const [selected, setSelected] = useState(null);

  if (!question) return null;

  const dp = question.payload?.decision_point || question;

  const handleSelect = (optionId) => {
    setSelected(optionId);
    onAnswer(dp.id, optionId);
  };

  const isSuggested = (optionId) => optionId === dp.suggested_answer;

  return (
    <div className="bg-white border-2 border-blue-200 rounded-2xl p-5 shadow-sm animate-fade-in">
      {/* Agent header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{dp.icon || "🤔"}</span>
        <div>
          <p className="text-sm font-semibold text-gray-800">{dp.agent}</p>
          <p className="text-xs text-gray-400">is asking for your input</p>
        </div>
      </div>

      {/* Context */}
      {dp.context && (
        <p className="text-sm text-gray-600 mb-2">{dp.context}</p>
      )}

      {/* Question */}
      <p className="text-sm font-medium text-gray-800 mb-1">{dp.question}</p>

      {/* Impact */}
      {dp.impact && (
        <p className="text-xs text-gray-400 mb-3">
          <span className="inline-block bg-gray-100 px-2 py-0.5 rounded-full">{dp.impact}</span>
        </p>
      )}

      {/* Suggestion highlight */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 mb-4">
        <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">
          Suggested
        </p>
        <p className="text-sm text-blue-800 font-medium">
          {dp.options?.find(o => o.id === dp.suggested_answer)?.label}
        </p>
        <p className="text-xs text-blue-600 mt-1">{dp.reason}</p>
      </div>

      {/* Options */}
      <div className="flex flex-wrap gap-2">
        {(dp.options || []).map((opt) => (
          <button
            key={opt.id}
            disabled={loading || selected !== null}
            onClick={() => handleSelect(opt.id)}
            className={`
              flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all
              ${selected === opt.id
                ? "bg-blue-600 text-white"
                : isSuggested(opt.id)
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"}
              disabled:opacity-60
            `}
          >
            {loading && selected === opt.id && (
              <Loader2 className="w-3 h-3 animate-spin" />
            )}
            {opt.label}
          </button>
        ))}
      </div>

      {dp.options?.find(o => o.id === selected)?.description && (
        <p className="text-xs text-gray-400 mt-2">{dp.options?.find(o => o.id === selected)?.description}</p>
      )}
    </div>
  );
}

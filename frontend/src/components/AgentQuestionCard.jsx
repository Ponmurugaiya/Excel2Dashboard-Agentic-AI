import React, { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

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

  const suggestedOption = dp.options?.find((o) => o.id === dp.suggested_answer);
  const selectedOption  = dp.options?.find((o) => o.id === selected);

  return (
    <div className="card p-6 border-brand-200 border-2 animate-slide-up shadow-card-md">
      {/* Agent header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-2xl bg-brand-100 flex items-center justify-center text-xl">
          {dp.icon || "🤔"}
        </div>
        <div>
          <p className="text-sm font-bold text-slate-900">{dp.agent}</p>
          <p className="text-xs text-slate-400">is asking for your input</p>
        </div>
        <span className="ml-auto badge bg-brand-100 text-brand-700">
          Action required
        </span>
      </div>

      {/* Context */}
      {dp.context && (
        <p className="text-sm text-slate-600 mb-3">{dp.context}</p>
      )}

      {/* Question */}
      <p className="text-sm font-bold text-slate-800 mb-2 leading-relaxed">
        {dp.question}
      </p>

      {/* Impact */}
      {dp.impact && (
        <p className="text-xs text-slate-400 mb-4">
          <span className="badge bg-slate-100 text-slate-500">
            {dp.impact}
          </span>
        </p>
      )}

      {/* Suggestion highlight */}
      {suggestedOption && (
        <div className="bg-brand-50 border border-brand-200
                        rounded-xl p-4 mb-5">
          <div className="flex items-center gap-2 mb-1.5">
            <Sparkles className="w-3.5 h-3.5 text-brand-600" />
            <p className="text-xs font-bold text-brand-700 uppercase tracking-wider">
              AI Suggestion
            </p>
          </div>
          <p className="text-sm font-bold text-brand-900">{suggestedOption.label}</p>
          {dp.reason && (
            <p className="text-xs text-brand-600 mt-1.5 leading-relaxed">{dp.reason}</p>
          )}
        </div>
      )}

      {/* Options */}
      <div className="flex flex-wrap gap-2">
        {(dp.options || []).map((opt) => {
          const isSelected  = selected === opt.id;
          const isSuggested = opt.id === dp.suggested_answer;
          return (
            <button
              key={opt.id}
              disabled={loading || selected !== null}
              onClick={() => handleSelect(opt.id)}
              className={`
                flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold
                transition-all duration-150 disabled:opacity-60
                focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2
                ${isSelected
                  ? "bg-brand-600 text-white shadow-sm"
                  : isSuggested
                    ? "bg-brand-600 text-white hover:bg-brand-700"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200:bg-dark-muted"
                }
              `}
            >
              {loading && isSelected && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {opt.label}
              {isSuggested && !isSelected && (
                <span className="text-xs opacity-70 font-normal">(suggested)</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Selected option description */}
      {selectedOption?.description && (
        <p className="text-xs text-slate-400 mt-3 animate-fade-in">
          {selectedOption.description}
        </p>
      )}
    </div>
  );
}

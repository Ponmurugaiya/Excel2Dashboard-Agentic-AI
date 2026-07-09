import React from "react";
import { AlertTriangle, Info, CheckCircle, Lightbulb } from "lucide-react";

const VARIANTS = {
  high: {
    wrap:  "bg-red-50 border-red-200",
    icon:  "bg-red-100 text-red-600",
    title: "text-red-800",
    body:  "text-red-700",
    rec:   "bg-red-100/60 text-red-700",
    Icon:  AlertTriangle,
  },
  medium: {
    wrap:  "bg-blue-50 border-blue-200",
    icon:  "bg-blue-100 text-blue-600",
    title: "text-blue-800",
    body:  "text-blue-700",
    rec:   "bg-blue-100/60 text-blue-700",
    Icon:  Info,
  },
  low: {
    wrap:  "bg-emerald-50 border-emerald-200",
    icon:  "bg-emerald-100 text-emerald-600",
    title: "text-emerald-800",
    body:  "text-emerald-700",
    rec:   "bg-emerald-100/60 text-emerald-700",
    Icon:  CheckCircle,
  },
  info: {
    wrap:  "bg-violet-50 border-violet-200",
    icon:  "bg-violet-100 text-violet-600",
    title: "text-violet-800",
    body:  "text-violet-700",
    rec:   "bg-violet-100/60 text-violet-700",
    Icon:  Lightbulb,
  },
};

export default function InsightCard({ text, recommendation, severity = "medium" }) {
  const v = VARIANTS[severity] || VARIANTS.medium;
  const { Icon } = v;

  return (
    <div className={`rounded-2xl border p-4 space-y-2.5 ${v.wrap}`}>
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-xl flex-shrink-0 ${v.icon}`}>
          <Icon className="w-4 h-4" />
        </div>
        <p className={`text-sm font-semibold leading-relaxed pt-1 ${v.title}`}>{text}</p>
      </div>

      {recommendation && (
        <div className={`ml-11 rounded-xl px-3 py-2.5 text-xs leading-relaxed ${v.rec}`}>
          <span className="font-bold">Recommendation: </span>
          {recommendation}
        </div>
      )}
    </div>
  );
}

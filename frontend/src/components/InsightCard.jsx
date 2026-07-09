import React from "react";
import { AlertTriangle, Info, CheckCircle } from "lucide-react";

const SEVERITY = {
  high:   { bg: "bg-red-50",    border: "border-red-200",   text: "text-red-800",   icon: AlertTriangle, iconColor: "text-red-500"  },
  medium: { bg: "bg-blue-50",   border: "border-blue-200",  text: "text-blue-800",  icon: Info,          iconColor: "text-blue-500" },
  low:    { bg: "bg-green-50",  border: "border-green-200", text: "text-green-800", icon: CheckCircle,   iconColor: "text-green-500"},
};

export default function InsightCard({ text, recommendation, severity = "medium" }) {
  const s = SEVERITY[severity] || SEVERITY.medium;
  const Icon = s.icon;

  return (
    <div className={`${s.bg} ${s.border} border rounded-xl p-4`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${s.iconColor}`} />
        <div className="space-y-1.5">
          <p className={`text-sm font-medium ${s.text}`}>{text}</p>
          {recommendation && (
            <p className={`text-xs ${s.text} opacity-80`}>
              <span className="font-semibold">Recommendation: </span>
              {recommendation}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

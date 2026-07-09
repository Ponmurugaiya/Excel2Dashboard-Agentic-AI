import React from "react";
import { Users, Zap, CheckCircle2 } from "lucide-react";

const OPTIONS = [
  {
    id:    "collaborative",
    label: "Collaborative",
    desc:  "Agents pause and ask you at key decision points. You guide the analysis.",
    icon:  Users,
    active:  "border-brand-500 bg-brand-50",
    inactive: "border-slate-200 bg-white hover:border-brand-300",
    iconActive:   "bg-brand-100 text-brand-600",
    iconInactive: "bg-slate-100 text-slate-500",
    badge: "badge bg-brand-100 text-brand-700",
    title: "text-brand-700",
  },
  {
    id:    "autonomous",
    label: "Fully Autonomous",
    desc:  "Agents make all decisions automatically. No interruptions. Review decisions after.",
    icon:  Zap,
    active:   "border-amber-500 bg-amber-50",
    inactive: "border-slate-200 bg-white hover:border-amber-300",
    iconActive:   "bg-amber-100 text-amber-600",
    iconInactive: "bg-slate-100 text-slate-500",
    badge: "badge bg-amber-100 text-amber-700",
    title: "text-amber-700",
  },
];

export default function ModeSelector({ mode, onChange }) {
  return (
    <div className="w-full">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {OPTIONS.map((opt) => {
          const isActive = mode === opt.id;
          const Icon = opt.icon;
          return (
            <button
              key={opt.id}
              onClick={() => onChange(opt.id)}
              className={`
                flex flex-col items-start gap-3 p-5 rounded-2xl border-2 text-left
                transition-all duration-150 focus:outline-none focus:ring-2
                focus:ring-brand-400 focus:ring-offset-2
                ${isActive ? opt.active : opt.inactive}
              `}
            >
              <div className={`p-2.5 rounded-xl transition-colors ${isActive ? opt.iconActive : opt.iconInactive}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <p className={`text-sm font-bold transition-colors
                  ${isActive ? opt.title : "text-slate-800"}`}>
                  {opt.label}
                </p>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  {opt.desc}
                </p>
              </div>
              {isActive && (
                <span className={`${opt.badge} flex items-center gap-1`}>
                  <CheckCircle2 className="w-3 h-3" />
                  Selected
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

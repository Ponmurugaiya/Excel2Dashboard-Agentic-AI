import React, { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle, XCircle, AlertTriangle, Info, X } from "lucide-react";

/* ── Context ──────────────────────────────────────────────────────────────── */

const ToastContext = createContext(null);

export function useToast() {
  return useContext(ToastContext);
}

/* ── Provider ─────────────────────────────────────────────────────────────── */

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    ({ title, description, type = "info", duration = 4000 }) => {
      const id = Date.now() + Math.random();
      setToasts((prev) => [...prev.slice(-4), { id, title, description, type }]);
      if (duration > 0) setTimeout(() => dismiss(id), duration);
    },
    [dismiss]
  );

  /* Convenience shortcuts */
  toast.success = (title, description) => toast({ title, description, type: "success" });
  toast.error   = (title, description) => toast({ title, description, type: "error", duration: 6000 });
  toast.warning = (title, description) => toast({ title, description, type: "warning" });
  toast.info    = (title, description) => toast({ title, description, type: "info" });

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastList toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

/* ── UI ───────────────────────────────────────────────────────────────────── */

const ICONS = {
  success: { Icon: CheckCircle,   cls: "text-emerald-500" },
  error:   { Icon: XCircle,       cls: "text-red-500"     },
  warning: { Icon: AlertTriangle, cls: "text-amber-500"   },
  info:    { Icon: Info,          cls: "text-brand-500"   },
};

const BG = {
  success: "border-emerald-200 bg-emerald-50",
  error:   "border-red-200   bg-red-50",
  warning: "border-amber-200 bg-amber-50",
  info:    "border-brand-200 bg-brand-50",
};

function ToastList({ toasts, onDismiss }) {
  if (!toasts.length) return null;
  return (
    <div className="fixed bottom-6 right-6 z-[200] flex flex-col gap-3 items-end pointer-events-none">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }) {
  const { id, title, description, type } = toast;
  const { Icon, cls } = ICONS[type] || ICONS.info;

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 px-4 py-3.5 rounded-2xl border
                  shadow-card-lg min-w-[280px] max-w-sm animate-slide-up
                  ${BG[type] || BG.info}`}
    >
      <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${cls}`} />
      <div className="flex-1 min-w-0">
        {title && <p className="text-sm font-semibold text-slate-800">{title}</p>}
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <button
        onClick={() => onDismiss(id)}
        className="text-slate-400 hover:text-slate-600 transition-colors flex-shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

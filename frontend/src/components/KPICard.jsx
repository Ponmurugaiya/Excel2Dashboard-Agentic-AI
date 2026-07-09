import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

/**
 * Production KPI card.
 * Supports: label, value, format, delta (%), trend direction, sparkline data
 */
export default function KPICard({ label, value, format, delta, trend, sparkline, icon: IconProp }) {
  const formatted = formatValue(value, format);
  const hasChange = delta !== null && delta !== undefined;

  const trendDir =
    trend        ? trend :
    hasChange && delta > 0  ? "up"   :
    hasChange && delta < 0  ? "down" :
    hasChange               ? "flat" : null;

  return (
    <div className="
      group relative bg-white rounded-2xl border border-slate-200 p-5 flex flex-col gap-3 shadow-card
      hover:shadow-card-md hover:-translate-y-0.5 transition-all duration-200
      overflow-hidden
    ">
      {/* Subtle gradient accent top */}
      <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-brand opacity-0 group-hover:opacity-100 transition-opacity" />

      {/* Label row */}
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 truncate">
          {label}
        </p>
        {trendDir && <TrendBadge dir={trendDir} delta={delta} />}
      </div>

      {/* Value */}
      <p className="text-2xl font-extrabold text-slate-900 leading-none tabular-nums truncate">
        {formatted}
      </p>

      {/* Sparkline */}
      {sparkline?.length > 1 && (
        <MiniSparkline data={sparkline} trend={trendDir} />
      )}
    </div>
  );
}

/* ── Trend badge ─────────────────────────────────────────────────────────── */

function TrendBadge({ dir, delta }) {
  if (dir === "up") {
    return (
      <span className="flex items-center gap-1 badge bg-emerald-50
                       text-emerald-700">
        <TrendingUp className="w-3 h-3" />
        {delta != null ? `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%` : "↑"}
      </span>
    );
  }
  if (dir === "down") {
    return (
      <span className="flex items-center gap-1 badge bg-red-50
                       text-red-600">
        <TrendingDown className="w-3 h-3" />
        {delta != null ? `${delta.toFixed(1)}%` : "↓"}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 badge bg-slate-100
                     text-slate-500">
      <Minus className="w-3 h-3" />
    </span>
  );
}

/* ── Mini sparkline (pure SVG) ───────────────────────────────────────────── */

function MiniSparkline({ data, trend }) {
  const nums = data.map(Number).filter((n) => !isNaN(n));
  if (nums.length < 2) return null;

  const W = 100, H = 28;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const range = max - min || 1;

  const points = nums.map((v, i) => [
    (i / (nums.length - 1)) * W,
    H - ((v - min) / range) * (H - 4) - 2,
  ]);

  const d = points
    .map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const fillD = `${d} L ${W} ${H} L 0 ${H} Z`;

  const stroke =
    trend === "up"   ? "#10b981" :
    trend === "down" ? "#ef4444" :
                       "#94a3b8";
  const fill =
    trend === "up"   ? "rgba(16,185,129,0.12)" :
    trend === "down" ? "rgba(239,68,68,0.12)"  :
                       "rgba(148,163,184,0.12)";

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ height: H }}
      preserveAspectRatio="none"
    >
      <path d={fillD}   fill={fill}   />
      <path d={d}       fill="none"   stroke={stroke} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ── Value formatter ─────────────────────────────────────────────────────── */

function formatValue(value, format) {
  if (value === null || value === undefined) return "—";
  const num = Number(value);
  if (isNaN(num)) return String(value);

  switch (format) {
    case "currency":
      if (Math.abs(num) >= 1_000_000)
        return `$${(num / 1_000_000).toFixed(1)}M`;
      if (Math.abs(num) >= 1_000)
        return `$${(num / 1_000).toFixed(1)}K`;
      return new Intl.NumberFormat("en-US", {
        style: "currency", currency: "USD", maximumFractionDigits: 0,
      }).format(num);

    case "percentage":
      return `${num.toFixed(1)}%`;

    default:
      if (Math.abs(num) >= 1_000_000)
        return `${(num / 1_000_000).toFixed(1)}M`;
      if (Math.abs(num) >= 1_000)
        return `${(num / 1_000).toFixed(1)}K`;
      return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(num);
  }
}

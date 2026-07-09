import React from "react";

/**
 * Displays a single KPI metric.
 * format: "number" | "currency" | "percentage"
 */
export default function KPICard({ label, value, format }) {
  const formatted = formatValue(value, format);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-1 shadow-sm hover:shadow-md transition-shadow">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide truncate">
        {label}
      </p>
      <p className="text-2xl font-bold text-gray-900 truncate">
        {formatted}
      </p>
    </div>
  );
}

function formatValue(value, format) {
  if (value === null || value === undefined) return "—";

  const num = Number(value);
  if (isNaN(num)) return String(value);

  switch (format) {
    case "currency":
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(num);

    case "percentage":
      return `${num.toFixed(1)}%`;

    default:
      // Plain number — add thousand separators
      return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 2,
      }).format(num);
  }
}

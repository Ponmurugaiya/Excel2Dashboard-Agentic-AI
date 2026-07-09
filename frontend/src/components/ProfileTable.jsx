import React from "react";

/**
 * Displays a tabular data profile for one sheet.
 */
export default function ProfileTable({ sheetName, profile }) {
  const { row_count, column_count, columns } = profile;

  const TYPE_BADGE = {
    number:   "bg-blue-100 text-blue-700",
    string:   "bg-gray-100 text-gray-600",
    datetime: "bg-purple-100 text-purple-700",
    boolean:  "bg-green-100 text-green-700",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      {/* Sheet header */}
      <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">{sheetName}</h3>
        <span className="text-xs text-gray-400">
          {row_count.toLocaleString()} rows · {column_count} columns
        </span>
      </div>

      {/* Column table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
              <th className="text-left px-5 py-2 font-medium">Column</th>
              <th className="text-left px-4 py-2 font-medium">Type</th>
              <th className="text-right px-4 py-2 font-medium">Missing</th>
              <th className="text-right px-4 py-2 font-medium">Unique</th>
              <th className="text-right px-4 py-2 font-medium">Min</th>
              <th className="text-right px-4 py-2 font-medium">Max</th>
              <th className="text-right px-4 py-2 font-medium">Mean</th>
              <th className="text-left px-4 py-2 font-medium">Sample</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {Object.entries(columns).map(([col, stats]) => (
              <tr key={col} className="hover:bg-gray-50 transition-colors">
                <td className="px-5 py-2.5 font-medium text-gray-800 whitespace-nowrap">
                  {col}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      TYPE_BADGE[stats.type] ?? "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {stats.type}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500">
                  {stats.missing_pct > 0 ? (
                    <span className="text-amber-600">{stats.missing_pct}%</span>
                  ) : (
                    <span className="text-green-500">0%</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500">
                  {stats.unique?.toLocaleString() ?? "—"}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500">
                  {stats.min ?? stats.min_date ?? "—"}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500">
                  {stats.max ?? stats.max_date ?? "—"}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500">
                  {stats.mean != null ? stats.mean.toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2.5 text-gray-400 text-xs truncate max-w-[160px]">
                  {stats.sample_values?.join(", ") ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

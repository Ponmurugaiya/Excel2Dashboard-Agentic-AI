import React, { Suspense, lazy, useState } from "react";
import InsightCard   from "./InsightCard";
import KPICard       from "./KPICard";
import DownloadButton from "./DownloadButton";

const Plot = lazy(() => import("react-plotly.js"));

const PlotFallback = (
  <div className="h-72 flex items-center justify-center text-slate-400 text-sm">
    <div className="flex flex-col items-center gap-2">
      <div className="w-6 h-6 border-2 border-slate-200 border-t-brand-500 rounded-full animate-spin" />
      <span>Loading chart…</span>
    </div>
  </div>
);

/**
 * Renders any dashboard spec JSON.
 * Data-driven: handles kpi_row, chart, chart_row, table, heatmap, insight_card.
 */
export default function SpecRenderer({ spec, sessionId, downloads = [] }) {
  if (!spec || !spec.tabs?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
          <span className="text-3xl">📊</span>
        </div>
        <p className="font-medium">No dashboard data available.</p>
        <p className="text-sm mt-1">Run an analysis to generate your dashboard.</p>
      </div>
    );
  }

  const [activeTab, setActiveTab] = useState(spec.tabs[0]?.id);
  const currentTab = spec.tabs.find((t) => t.id === activeTab);

  return (
    <div className="flex flex-col min-h-full">

      {/* ── Tab bar ──────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-200 bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-0 overflow-x-auto no-scrollbar">
            {spec.tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab-item flex-shrink-0 ${
                  activeTab === tab.id ? "tab-item-active" : "tab-item-inactive"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Tab content ──────────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto w-full px-6 py-8 space-y-6 animate-fade-in">
        {currentTab?.sections?.map((section, i) => (
          <SectionRenderer
            key={`${activeTab}-${i}`}
            section={section}
            sessionId={sessionId}
            downloads={downloads}
          />
        ))}

        {/* Downloads row */}
        {downloads.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-4 border-t border-slate-100">
            <span className="text-xs text-slate-400 self-center mr-2">Export data:</span>
            {downloads.map((d) => (
              <DownloadButton
                key={d.name}
                sessionId={sessionId}
                name={d.name}
                label={d.filename}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Section dispatcher ──────────────────────────────────────────────────── */

function SectionRenderer({ section, sessionId, downloads }) {
  const t = section.section_type;

  if (t === "insight_card") {
    return (
      <InsightCard
        text={section.text}
        recommendation={section.recommendation}
        severity={section.severity}
      />
    );
  }
  if (t === "kpi_row") {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {(section.items || []).map((kpi, i) => (
          <KPICard key={i} {...kpi} />
        ))}
      </div>
    );
  }
  if (t === "chart_row") {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {(section.items || []).map((item, i) => (
          <ChartSection key={i} section={item} />
        ))}
      </div>
    );
  }
  if (t === "chart" || t === "heatmap") {
    return <ChartSection section={section} />;
  }
  if (t === "table") {
    return <TableSection section={section} />;
  }
  return null;
}

/* ── Chart section ───────────────────────────────────────────────────────── */

function ChartSection({ section }) {
  const { title, chart_spec, insight, caveat, section_type, row_count } = section;

  if (!chart_spec?.data) {
    return (
      <div className="card p-6 text-sm text-slate-400">
        No chart data for &ldquo;{title}&rdquo;
      </div>
    );
  }

  const isHeatmap   = section_type === "heatmap";
  const chartHeight = isHeatmap
    ? `${Math.max(300, Math.min((row_count || 8) * 48 + 120, 600))}px`
    : "320px";

  return (
    <div className="card overflow-hidden">
      {title && (
        <div className="px-5 pt-5 pb-0">
          <h3 className="text-sm font-bold text-slate-700">{title}</h3>
        </div>
      )}
      <Suspense fallback={PlotFallback}>
        <Plot
          data={chart_spec.data}
          layout={{
            ...chart_spec.layout,
            title:      undefined,
            autosize:   true,
            margin:     isHeatmap ? { l: 80, r: 40, t: 20, b: 60 } : { l: 50, r: 20, t: 20, b: 50 },
            paper_bgcolor: "transparent",
            plot_bgcolor:  "transparent",
            font: { family: "Inter, sans-serif", size: 12, color: "#64748b" },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: chartHeight }}
          useResizeHandler
        />
      </Suspense>
      {(insight || caveat) && (
        <div className="px-5 pb-5 space-y-2 mt-1">
          {insight && (
            <p className="text-xs text-slate-500 leading-relaxed">{insight}</p>
          )}
          {caveat && (
            <p className="text-xs text-amber-700 bg-amber-50
                          border border-amber-200 px-3 py-1.5 rounded-xl">
              ⚠ {caveat}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Table section ───────────────────────────────────────────────────────── */

function TableSection({ section }) {
  const { title, segment_summary, records, chart_spec, insight } = section;
  const [showTable, setShowTable] = useState(false);
  const [search, setSearch]       = useState("");

  const filteredRecords = records?.filter((row) =>
    !search || Object.values(row).some((v) =>
      String(v ?? "").toLowerCase().includes(search.toLowerCase())
    )
  );

  return (
    <div className="space-y-4">
      {/* Segment summary chart */}
      {chart_spec?.data && (
        <div className="card overflow-hidden">
          {title && (
            <div className="px-5 pt-5 pb-0">
              <h3 className="text-sm font-bold text-slate-700">
                {title} — Distribution
              </h3>
            </div>
          )}
          <Suspense fallback={PlotFallback}>
            <Plot
              data={chart_spec.data}
              layout={{
                ...chart_spec.layout,
                title:         undefined,
                autosize:      true,
                margin:        { l: 40, r: 40, t: 20, b: 40 },
                paper_bgcolor: "transparent",
                plot_bgcolor:  "transparent",
                font: { family: "Inter, sans-serif", size: 12, color: "#64748b" },
              }}
              config={{ responsive: true, displayModeBar: false }}
              style={{ width: "100%", height: "320px" }}
              useResizeHandler
            />
          </Suspense>
        </div>
      )}

      {/* Segment summary table */}
      {segment_summary?.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-bold text-slate-800 text-sm">{title}</h3>
            {records?.length > 0 && (
              <button
                onClick={() => setShowTable(!showTable)}
                className="text-xs text-brand-600 font-medium hover:underline"
              >
                {showTable ? "Hide full table" : `Show all ${records.length} records`}
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-xs text-slate-500
                               uppercase tracking-wider">
                  <th className="text-left px-5 py-3">Segment</th>
                  <th className="text-right px-4 py-3">Customers</th>
                  <th className="text-right px-4 py-3">Avg Revenue</th>
                  <th className="text-right px-4 py-3">Avg Recency (d)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {segment_summary.map((seg, i) => (
                  <tr key={i} className="hover:bg-slate-50:bg-dark-surface transition-colors">
                    <td className="px-5 py-3 font-medium text-slate-800">
                      <SegmentBadge name={seg.segment} />
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600 tabular-nums">
                      {seg.count?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600 tabular-nums">
                      {seg.avg_monetary != null
                        ? new Intl.NumberFormat("en-US", {
                            style: "currency", currency: "USD", maximumFractionDigits: 0
                          }).format(seg.avg_monetary)
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600 tabular-nums">
                      {seg.avg_recency != null ? Math.round(seg.avg_recency) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Full records table (expandable) */}
      {showTable && filteredRecords?.length > 0 && (
        <div className="card overflow-hidden animate-slide-up">
          {/* Search bar */}
          <div className="px-5 py-3 border-b border-slate-100">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search records…"
              className="input text-xs py-2"
            />
          </div>
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-slate-50 z-10">
                <tr className="text-slate-500 uppercase tracking-wider">
                  {Object.keys(filteredRecords[0] || {}).map((col) => (
                    <th key={col} className="text-left px-4 py-2.5 font-semibold whitespace-nowrap border-b
                                             border-slate-100">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filteredRecords.slice(0, 200).map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50:bg-dark-surface transition-colors">
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-4 py-2 text-slate-600 whitespace-nowrap">
                        {val != null ? String(val) : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {records.length > 200 && (
            <p className="text-xs text-slate-400 px-5 py-3 border-t
                          border-slate-100">
              Showing first 200 of {records.length.toLocaleString()} records.
              Download CSV for the full dataset.
            </p>
          )}
        </div>
      )}

      {insight && (
        <p className="text-xs text-slate-500">{insight}</p>
      )}
    </div>
  );
}

/* ── Segment badge ───────────────────────────────────────────────────────── */

function SegmentBadge({ name }) {
  const lower = (name || "").toLowerCase();
  const cls =
    lower.includes("champion") ? "bg-purple-100 text-purple-700" :
    lower.includes("loyal")    ? "bg-blue-100 text-blue-700"         :
    lower.includes("risk")     ? "bg-amber-100 text-amber-700"     :
    lower.includes("lost")     ? "bg-red-100 text-red-700"             :
                                  "bg-slate-100 text-slate-700";
  return (
    <span className={`badge ${cls}`}>{name}</span>
  );
}

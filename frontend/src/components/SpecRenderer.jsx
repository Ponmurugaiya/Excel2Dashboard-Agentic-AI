import React, { Suspense, lazy } from "react";
import InsightCard from "./InsightCard";
import KPICard from "./KPICard";
import DownloadButton from "./DownloadButton";

const Plot = lazy(() => import("react-plotly.js"));

const PlotFallback = (
  <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
    Loading chart…
  </div>
);

/**
 * Renders any dashboard spec JSON.
 * Handles all section types: kpi_row, chart, chart_row, table, heatmap, insight_card.
 * The layout is 100% data-driven — no hardcoded structure.
 */
export default function SpecRenderer({ spec, sessionId, downloads = [] }) {
  if (!spec || !spec.tabs?.length) {
    return (
      <div className="text-center py-20 text-gray-400">
        No dashboard data available.
      </div>
    );
  }

  const [activeTab, setActiveTab] = React.useState(spec.tabs[0]?.id);
  const currentTab = spec.tabs.find((t) => t.id === activeTab);

  return (
    <div className="space-y-0">
      {/* Tab nav */}
      <div className="border-b border-gray-200 bg-white sticky top-[57px] z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-0">
            {spec.tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  px-5 py-3.5 text-sm font-medium border-b-2 transition-colors
                  ${activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"}
                `}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab content */}
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {currentTab?.sections?.map((section, i) => (
          <SectionRenderer
            key={i}
            section={section}
            sessionId={sessionId}
            downloads={downloads}
          />
        ))}

        {/* Downloads row */}
        {downloads.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-4 border-t border-gray-100">
            <span className="text-xs text-gray-400 self-center">Download data:</span>
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

// ── Section dispatcher ────────────────────────────────────────────────────────

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

// ── Chart / Heatmap section ───────────────────────────────────────────────────

function ChartSection({ section }) {
  const { title, chart_spec, insight, caveat } = section;

  if (!chart_spec?.data) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 text-sm text-gray-400">
        No chart data for "{title}"
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <Suspense fallback={PlotFallback}>
        <Plot
          data={chart_spec.data}
          layout={{
            ...chart_spec.layout,
            autosize: true,
            margin: { l: 50, r: 20, t: 50, b: 50 },
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            font: { family: "Inter, sans-serif", size: 12 },
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "320px" }}
          useResizeHandler
        />
      </Suspense>
      {(insight || caveat) && (
        <div className="px-4 pb-4 space-y-1">
          {insight && <p className="text-xs text-gray-500 leading-relaxed">{insight}</p>}
          {caveat && (
            <p className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-lg">
              ⚠ {caveat}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Table section (RFM segments etc.) ────────────────────────────────────────

function TableSection({ section }) {
  const { title, segment_summary, records, chart_spec, insight } = section;
  const [showTable, setShowTable] = React.useState(false);

  return (
    <div className="space-y-4">
      {/* Segment summary chart */}
      {chart_spec?.data && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <Suspense fallback={PlotFallback}>
            <Plot
              data={chart_spec.data}
              layout={{
                ...chart_spec.layout,
                autosize: true,
                margin: { l: 40, r: 40, t: 50, b: 40 },
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
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
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
            {records?.length > 0 && (
              <button
                onClick={() => setShowTable(!showTable)}
                className="text-xs text-blue-600 hover:underline"
              >
                {showTable ? "Hide full table" : `Show all ${records.length} records`}
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="text-left px-5 py-2">Segment</th>
                  <th className="text-right px-4 py-2">Customers</th>
                  <th className="text-right px-4 py-2">Avg Revenue</th>
                  <th className="text-right px-4 py-2">Avg Recency (days)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {segment_summary.map((seg, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-5 py-2.5 font-medium text-gray-800">
                      <SegmentBadge name={seg.segment} />
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-600">
                      {seg.count?.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-600">
                      {seg.avg_monetary != null
                        ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(seg.avg_monetary)
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-600">
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
      {showTable && records?.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50">
                <tr className="text-gray-500 uppercase tracking-wide">
                  {Object.keys(records[0] || {}).map((col) => (
                    <th key={col} className="text-left px-4 py-2 font-medium whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {records.slice(0, 200).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-4 py-2 text-gray-600 whitespace-nowrap">
                        {val != null ? String(val) : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {records.length > 200 && (
            <p className="text-xs text-gray-400 px-4 py-2 border-t border-gray-100">
              Showing first 200 of {records.length} records. Download CSV for full data.
            </p>
          )}
        </div>
      )}

      {insight && <p className="text-xs text-gray-500">{insight}</p>}
    </div>
  );
}

// ── Segment badge ─────────────────────────────────────────────────────────────

function SegmentBadge({ name }) {
  const lower = (name || "").toLowerCase();
  const colors =
    lower.includes("champion") ? "bg-purple-100 text-purple-700" :
    lower.includes("loyal")    ? "bg-blue-100 text-blue-700" :
    lower.includes("risk")     ? "bg-amber-100 text-amber-700" :
    lower.includes("lost")     ? "bg-red-100 text-red-700" :
                                  "bg-gray-100 text-gray-700";

  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colors}`}>
      {name}
    </span>
  );
}

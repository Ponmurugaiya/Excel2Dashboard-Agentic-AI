import React, { Suspense, lazy } from "react";

// react-plotly.js is large — lazy load it so the upload screen stays fast
const Plot = lazy(() => import("react-plotly.js"));

/**
 * Renders a single Plotly chart inside a card.
 * chart: { id, title, type, figure: { data, layout } }
 */
export default function ChartCard({ chart }) {
  const { title, figure } = chart;

  if (!figure?.data) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 text-sm text-gray-400">
        No data for "{title}"
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <Suspense
        fallback={
          <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
            Loading chart…
          </div>
        }
      >
        <Plot
          data={figure.data}
          layout={{
            ...figure.layout,
            autosize: true,
            margin: { l: 40, r: 20, t: 50, b: 40 },
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
          }}
          config={{ responsive: true, displayModeBar: false }}
          style={{ width: "100%", height: "320px" }}
          useResizeHandler
        />
      </Suspense>
    </div>
  );
}

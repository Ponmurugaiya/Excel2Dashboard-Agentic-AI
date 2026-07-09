import React from "react";
import { RotateCcw, FileSpreadsheet } from "lucide-react";
import KPICard from "../components/KPICard";
import ChartCard from "../components/ChartCard";
import ProfileTable from "../components/ProfileTable";

/**
 * Dashboard screen.
 * Renders KPI cards, charts, and a data profile summary.
 */
export default function DashboardPage({ data, onReset }) {
  const { file, kpis, charts, profile, plan } = data;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-brand-600" />
          <span className="font-semibold text-gray-800">{file}</span>
        </div>
        <button
          onClick={onReset}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-brand-600 transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          Upload new file
        </button>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-10">

        {/* LLM Reasoning (collapsible) */}
        {plan?.reasoning && (
          <details className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <summary className="cursor-pointer font-medium text-blue-700 select-none">
              AI Analysis
            </summary>
            <p className="mt-2 text-sm text-blue-600 leading-relaxed">
              {plan.reasoning}
            </p>
          </details>
        )}

        {/* KPIs */}
        {kpis?.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              Key Metrics
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {kpis.map((kpi, i) => (
                <KPICard key={i} {...kpi} />
              ))}
            </div>
          </section>
        )}

        {/* Charts */}
        {charts?.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              Charts
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {charts.map((chart) => (
                <ChartCard key={chart.id} chart={chart} />
              ))}
            </div>
          </section>
        )}

        {/* Data Profile */}
        {profile && (
          <section>
            <h2 className="text-lg font-semibold text-gray-700 mb-4">
              Data Profile
            </h2>
            <div className="space-y-6">
              {Object.entries(profile).map(([sheetName, sheetProfile]) => (
                <ProfileTable
                  key={sheetName}
                  sheetName={sheetName}
                  profile={sheetProfile}
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

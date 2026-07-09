"""
Insight Agent
Goal: Extract and communicate the most actionable findings for a business audience.

Real agent properties:
  - Memory: all results, insights already written, cross-result patterns
  - Tools: read_result, cross_reference, write_insight, rank_by_actionability, identify_anomaly
  - Goal loop: observe all results → cross-reference → write → rank → done
  - Communication: sends final insights to Dashboard Architect
"""

from __future__ import annotations

import json
from typing import Any

from backend.agents.base import BaseAgent
from backend.agents.message_bus import MessageBus
from backend.agents.models import (
    AgentName,
    AnalysisResult,
    RunMode,
)


class InsightAgent(BaseAgent):
    name = AgentName.INSIGHT.value
    icon = "💡"

    def __init__(self, bus: MessageBus, mode: RunMode):
        super().__init__(bus, mode)
        self._insights: list[dict] = []

    # ── Main entry point ──────────────────────────────────────────────────────

    async def generate(
        self, accepted_results: list[AnalysisResult]
    ) -> list[dict]:
        """
        Observe all accepted results, cross-reference patterns,
        write actionable insights, rank by business impact.
        """
        if not accepted_results:
            self.log("No accepted results to generate insights from")
            self.mark_done()
            return []

        self.log(f"Analysing {len(accepted_results)} results for insights...")

        # ── Tool: read and index all results ──────────────────────────────────
        self.memory.set("results_index", {r.task_id: r for r in accepted_results})

        # ── Tool: LLM-powered insight generation ─────────────────────────────
        raw_insights = self._generate_insights_llm(accepted_results)
        self.memory.remember("raw_insights", {"count": len(raw_insights)})

        # ── Tool: cross-reference for compound insights ───────────────────────
        compound = self._cross_reference(accepted_results, raw_insights)
        all_insights = raw_insights + compound

        # ── Tool: rank by actionability ───────────────────────────────────────
        ranked = self._rank_by_actionability(all_insights)

        # Keep top 5
        top = ranked[:5]
        self.log(f"Generated {len(all_insights)} insights, surfacing top {len(top)}")
        self.memory.remember("final_insights", {"insights": [i["text"] for i in top]})

        self._insights = top
        self.mark_done()
        return top

    # ── Tool: LLM insight generation ─────────────────────────────────────────

    def _generate_insights_llm(self, results: list[AnalysisResult]) -> list[dict]:
        """Call LLM with all results to generate data-grounded insights."""

        results_summary = []
        for r in results:
            summary = {
                "task_id": r.task_id,
                "title": r.title,
                "pattern": r.data.get("result_type", ""),
                "insight": r.data.get("insight", ""),
            }
            # Add key numbers for grounding
            data = r.data
            if data.get("result_type") == "kpi_row":
                summary["kpis"] = data.get("kpis", [])
            elif data.get("result_type") == "chart" and data.get("pattern") == "time_series":
                x = data.get("x", [])
                y = data.get("y", [])
                if x and y:
                    summary["first_period"] = f"{x[0]}={y[0]}"
                    summary["last_period"] = f"{x[-1]}={y[-1]}"
            elif data.get("result_type") == "table":
                seg_summary = data.get("segment_summary", [])
                summary["segment_summary"] = seg_summary[:4]
            elif data.get("result_type") == "heatmap":
                matrix = data.get("matrix", [[]])
                if matrix and matrix[0]:
                    month1 = matrix[0][1] if len(matrix[0]) > 1 else None
                    summary["month0_retention"] = 1.0
                    summary["month1_retention"] = round(month1, 3) if month1 else None

            results_summary.append(summary)

        prompt = f"""You are a senior business analyst writing executive insights.

ANALYSIS RESULTS:
{json.dumps(results_summary, indent=2)}

Write 3-5 actionable business insights based ONLY on the numbers above.

Each insight must:
1. Reference a specific number from the results
2. Explain what it means for the business
3. Include a recommendation when possible

Format: JSON array of objects:
[
  {{
    "text": "Champions (X% of customers) generate Y% of revenue — ...",
    "recommendation": "...",
    "severity": "high|medium|low",
    "source_task_id": "..."
  }}
]

Rules:
- Be specific — cite actual numbers
- Write for a business executive, not a data scientist
- severity=high means immediate action needed
- Return ONLY the JSON array
"""
        try:
            raw = self._llm_json(prompt)
            if isinstance(raw, list):
                return raw
            return raw.get("insights", [])
        except Exception as e:
            self.log_error(f"Insight LLM call failed: {e}")
            # Fallback: use the per-task insights
            return [
                {
                    "text": r.data.get("insight", f"{r.title} analysis completed."),
                    "recommendation": "",
                    "severity": "medium",
                    "source_task_id": r.task_id,
                }
                for r in results
                if r.data.get("insight")
            ]

    # ── Tool: cross-reference results for compound insights ───────────────────

    def _cross_reference(
        self,
        results: list[AnalysisResult],
        existing_insights: list[dict],
    ) -> list[dict]:
        """Look for patterns that only emerge when comparing multiple results."""
        compound = []
        result_types = {r.task_id: r.data.get("result_type") for r in results}

        # Pattern: RFM + retention both present → combine
        has_rfm = any("rfm" in r.task_id for r in results)
        has_cohort = any("cohort" in r.task_id for r in results)

        if has_rfm and has_cohort:
            rfm_result = next((r for r in results if "rfm" in r.task_id), None)
            cohort_result = next((r for r in results if "cohort" in r.task_id), None)

            if rfm_result and cohort_result:
                matrix = cohort_result.data.get("matrix", [[]])
                month1_retention = None
                if matrix and len(matrix[0]) > 1:
                    month1_retention = matrix[0][1]

                seg_summary = rfm_result.data.get("segment_summary", [])
                at_risk = next(
                    (s for s in seg_summary if "risk" in s.get("segment", "").lower()), None
                )

                if month1_retention and at_risk:
                    compound.append({
                        "text": (
                            f"Only {month1_retention*100:.0f}% of customers return after month 1, "
                            f"and {at_risk['count']} customers are in the At-Risk segment. "
                            f"These two signals together suggest a critical onboarding gap."
                        ),
                        "recommendation": (
                            "Implement a month-1 retention campaign targeting new customers "
                            "with personalized follow-up offers."
                        ),
                        "severity": "high",
                        "source_task_id": "cross:rfm+cohort",
                    })

        return compound

    # ── Tool: rank by actionability ───────────────────────────────────────────

    def _rank_by_actionability(self, insights: list[dict]) -> list[dict]:
        """Sort insights: high severity first, then those with recommendations."""
        severity_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            insights,
            key=lambda i: (
                severity_order.get(i.get("severity", "medium"), 1),
                0 if i.get("recommendation") else 1,
            ),
        )

    @property
    def insights(self) -> list[dict]:
        return self._insights

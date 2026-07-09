"""
Dashboard Architect Agent
Goal: Design a dashboard that tells a coherent, compelling data story.

Real agent properties:
  - Memory: all accepted results ranked, narrative flow decisions, self-critique log
  - Tools: rank_results, design_narrative, assign_visual, compose_layout, self_review, revise
  - Goal loop: observe results → rank → compose → self-critique → revise → approve
  - Communication: receives insights from Insight Agent, produces dashboard spec
"""

from __future__ import annotations

import json
from typing import Any

import plotly.express as px
import plotly.graph_objects as go

from backend.agents.base import BaseAgent
from backend.agents.message_bus import MessageBus
from backend.agents.models import (
    AgentName,
    AnalysisResult,
    DashboardSpec,
    RunMode,
)

_COLORS = px.colors.qualitative.Plotly


class ArchitectAgent(BaseAgent):
    name = AgentName.ARCHITECT.value
    icon = "🎨"

    def __init__(self, bus: MessageBus, mode: RunMode):
        super().__init__(bus, mode)
        self._spec: dict = {}

    # ── Main entry point ──────────────────────────────────────────────────────

    async def design(
        self,
        accepted_results: list[AnalysisResult],
        insights: list[dict],
        dataset_title: str = "Data Analysis",
    ) -> dict:
        """
        Compose the full dashboard spec.
        Returns a dict that the frontend spec-renderer can consume directly.
        """
        if not accepted_results:
            self.log("No results to design dashboard from")
            return {"title": dataset_title, "tabs": [], "auto_decisions": []}

        self.log(f"Designing dashboard for {len(accepted_results)} accepted analyses...")

        # ── Tool: rank results by importance ──────────────────────────────────
        ranked = self._rank_results(accepted_results, insights)
        self.memory.remember("ranked_results", {"order": [r.task_id for r in ranked]})

        # ── Tool: assign chart specs ──────────────────────────────────────────
        for result in ranked:
            result.chart_spec = self._build_chart_spec(result)

        # ── Tool: design narrative flow (LLM) ─────────────────────────────────
        tab_plan = self._plan_tabs_llm(ranked, insights, dataset_title)
        self.memory.remember("tab_plan", {"tabs": [t["label"] for t in tab_plan]})
        self.log(f"Planned {len(tab_plan)} dashboard tabs: {[t['label'] for t in tab_plan]}")

        # ── Tool: compose layout ──────────────────────────────────────────────
        spec = self._compose_spec(ranked, insights, tab_plan, dataset_title)

        # ── Tool: self-review ─────────────────────────────────────────────────
        critique = self._self_review(spec)
        if critique:
            self.log(f"Self-critique: {critique}")
            spec = self._apply_critique(spec, critique)
            self.memory.remember("self_critique_applied", {"notes": critique})

        self.log("Dashboard design complete")
        self._spec = spec
        self.mark_done()
        return spec

    # ── Tool: rank results ────────────────────────────────────────────────────

    def _rank_results(
        self, results: list[AnalysisResult], insights: list[dict]
    ) -> list[AnalysisResult]:
        """Order results by importance for dashboard placement."""
        pattern_priority = {
            "kpi_row": 10,
            "time_series": 9,
            "rfm": 8,
            "cohort": 7,
            "ranking": 6,
            "geo": 5,
            "distribution": 4,
        }

        def score(r: AnalysisResult) -> int:
            pattern = r.data.get("result_type", "")
            if r.data.get("result_type") == "kpi_row":
                pattern = "kpi_row"
            base = pattern_priority.get(pattern, 3)
            # Boost if referenced in high-severity insight
            for ins in insights:
                if ins.get("source_task_id") == r.task_id and ins.get("severity") == "high":
                    base += 2
            return base

        return sorted(results, key=score, reverse=True)

    # ── Tool: plan tabs via LLM ───────────────────────────────────────────────

    def _plan_tabs_llm(
        self,
        results: list[AnalysisResult],
        insights: list[dict],
        dataset_title: str,
    ) -> list[dict]:
        """Ask LLM to decide tab structure and which results go on which tab."""

        results_summary = [
            {
                "task_id": r.task_id,
                "title": r.title,
                "result_type": r.data.get("result_type"),
                "quality_score": r.quality_score,
                "has_caveat": bool(r.caveat),
            }
            for r in results
        ]

        top_insights = [i.get("text", "")[:120] for i in insights[:3]]

        prompt = f"""You are designing a BI dashboard layout.

DATASET TITLE: {dataset_title}

AVAILABLE ANALYSES:
{json.dumps(results_summary, indent=2)}

TOP INSIGHTS:
{json.dumps(top_insights, indent=2)}

Design the tab structure for this dashboard.

Rules:
- 2-4 tabs maximum
- Tab 1 should always be an "Overview" with KPIs and top charts
- Group related analyses together
- Tab names should be business-friendly (not technical)
- Every analysis must be assigned to exactly one tab

Return a JSON array:
[
  {{
    "id": "overview",
    "label": "Overview",
    "task_ids": ["kpi_overview", "revenue_over_time", "top_categories"],
    "description": "High-level business performance"
  }},
  ...
]

Return ONLY the JSON array.
"""
        try:
            raw = self._llm_json(prompt, task="planning")
            if isinstance(raw, list) and raw:
                return raw
        except Exception as e:
            self.log_error(f"Tab planning LLM failed: {e}. Using fallback.")

        return self._fallback_tab_plan(results)

    def _fallback_tab_plan(self, results: list[AnalysisResult]) -> list[dict]:
        """Simple fallback: Overview + optional specialist tabs."""
        overview_ids = []
        segment_ids = []
        retention_ids = []
        other_ids = []

        for r in results:
            tid = r.task_id
            if "kpi" in tid or "time_series" in tid or "revenue_over_time" in tid:
                overview_ids.append(tid)
            elif "rfm" in tid or "segment" in tid:
                segment_ids.append(tid)
            elif "cohort" in tid or "retention" in tid:
                retention_ids.append(tid)
            else:
                overview_ids.append(tid)

        tabs = [{"id": "overview", "label": "Overview", "task_ids": overview_ids}]
        if segment_ids:
            tabs.append({"id": "segments", "label": "Customer Segments", "task_ids": segment_ids})
        if retention_ids:
            tabs.append({"id": "retention", "label": "Retention", "task_ids": retention_ids})
        if other_ids:
            tabs[0]["task_ids"].extend(other_ids)

        return tabs

    # ── Tool: compose dashboard spec ──────────────────────────────────────────

    def _compose_spec(
        self,
        results: list[AnalysisResult],
        insights: list[dict],
        tab_plan: list[dict],
        dataset_title: str,
    ) -> dict:
        results_by_id = {r.task_id: r for r in results}

        tabs = []
        for tab_def in tab_plan:
            sections = []

            # Find top insight for this tab (if any)
            tab_tasks = set(tab_def.get("task_ids", []))
            tab_insights = [
                i for i in insights
                if i.get("source_task_id") in tab_tasks
                or i.get("source_task_id", "").startswith("cross:")
            ]

            # Add top insight card at top of tab
            if tab_insights:
                top_ins = tab_insights[0]
                sections.append({
                    "section_type": "insight_card",
                    "severity": top_ins.get("severity", "medium"),
                    "text": top_ins.get("text", ""),
                    "recommendation": top_ins.get("recommendation", ""),
                })

            # Group items by layout preference
            kpi_items = []
            full_width_items = []
            half_width_pairs = []
            pending_half = None

            for task_id in tab_def.get("task_ids", []):
                result = results_by_id.get(task_id)
                if not result:
                    continue

                rt = result.data.get("result_type")

                if rt == "kpi_row":
                    kpi_items.extend(result.data.get("kpis", []))
                elif rt in ("heatmap",) or task_id.startswith("rfm"):
                    full_width_items.append(result)
                elif rt == "table":
                    full_width_items.append(result)
                else:
                    # Try to pair charts side by side
                    if pending_half is None:
                        pending_half = result
                    else:
                        half_width_pairs.append((pending_half, result))
                        pending_half = None

            # Flush unpaired item to full width
            if pending_half:
                full_width_items.append(pending_half)

            # Add KPI row
            if kpi_items:
                sections.append({"section_type": "kpi_row", "items": kpi_items})

            # Add paired charts
            for left, right in half_width_pairs:
                sections.append({
                    "section_type": "chart_row",
                    "items": [
                        self._result_to_section_item(left, "half"),
                        self._result_to_section_item(right, "half"),
                    ],
                })

            # Add full-width items
            for r in full_width_items:
                sections.append(self._result_to_section_item(r, "full"))

            tabs.append({
                "id": tab_def["id"],
                "label": tab_def["label"],
                "sections": sections,
            })

        return {
            "title": dataset_title,
            "tabs": tabs,
            "all_insights": [
                {
                    "text": i.get("text", ""),
                    "recommendation": i.get("recommendation", ""),
                    "severity": i.get("severity", "medium"),
                }
                for i in insights
            ],
            "auto_decisions": self.bus.get_auto_decisions(),
        }

    # ── Tool: build chart spec (Plotly) ───────────────────────────────────────

    def _build_chart_spec(self, result: AnalysisResult) -> dict | None:
        data = result.data
        rt = data.get("result_type")

        try:
            if rt == "chart":
                ct = data.get("chart_type", "bar")
                if ct == "line":
                    fig = px.line(
                        x=data.get("x", []),
                        y=data.get("y", []),
                        title=data.get("title", result.title),
                        labels={"x": data.get("x_label", ""), "y": data.get("y_label", "")},
                        color_discrete_sequence=_COLORS,
                    )
                elif ct == "bar":
                    fig = px.bar(
                        x=data.get("labels", data.get("x", [])),
                        y=data.get("values", data.get("y", [])),
                        title=data.get("title", result.title),
                        labels={"x": data.get("x_label", ""), "y": data.get("y_label", "")},
                        color_discrete_sequence=_COLORS,
                    )
                elif ct == "pie":
                    labels = data.get("labels", [])
                    values = data.get("values", [])
                    fig = px.pie(
                        names=labels,
                        values=values,
                        title=data.get("title", result.title),
                        color_discrete_sequence=_COLORS,
                    )
                elif ct == "histogram":
                    fig = px.histogram(
                        x=data.get("values", []),
                        title=data.get("title", result.title),
                        labels={"x": data.get("x_label", "")},
                        color_discrete_sequence=_COLORS,
                    )
                else:
                    fig = px.bar(
                        x=data.get("labels", []),
                        y=data.get("values", []),
                        title=data.get("title", result.title),
                        color_discrete_sequence=_COLORS,
                    )

            elif rt == "heatmap":
                matrix   = data.get("matrix", [])
                x_labels = data.get("x_labels", [])
                y_labels = data.get("y_labels", [])

                # Keep None as None — Plotly renders missing cells as blank/grey,
                # which is correct for cohort periods that haven't happened yet.
                # Do NOT replace None with 0 — 0% retention and "no data" are different.
                z = [[v for v in row] for row in matrix]

                # Annotation text: show percentage for real values, blank for None
                text = [
                    [f"{v*100:.0f}%" if v is not None else "" for v in row]
                    for row in matrix
                ]

                # Dynamic x-axis title based on content
                x_title = data.get("x_axis_label", "Months Since First Purchase")

                fig = go.Figure(data=go.Heatmap(
                    z=z,
                    x=x_labels,
                    y=y_labels,
                    colorscale="Blues",
                    text=text,
                    texttemplate="%{text}",
                    showscale=True,
                    zmin=0,
                    zmax=1,
                ))
                fig.update_layout(
                    title=data.get("title", result.title),
                    xaxis_title=x_title,
                    yaxis_title="Cohort",
                    # Auto-expand height based on number of cohort rows
                    height=max(300, min(80 * len(y_labels) + 100, 700)),
                )

            elif rt == "table":
                # Segment summary chart
                seg_summary = data.get("segment_summary", [])
                if seg_summary:
                    segments = [s.get("segment", "") for s in seg_summary]
                    counts = [s.get("count", 0) for s in seg_summary]
                    fig = px.pie(
                        names=segments,
                        values=counts,
                        title=data.get("title", "Segment Distribution"),
                        color_discrete_sequence=_COLORS,
                    )
                else:
                    return None

            else:
                return None

            fig.update_layout(
                template="plotly_white",
                margin=dict(l=40, r=40, t=50, b=40),
                font=dict(family="Inter, sans-serif", size=13),
            )
            import json as _json
            return _json.loads(fig.to_json())

        except Exception as e:
            self.log_error(f"Chart spec build failed for {result.task_id}: {e}")
            return None

    # ── Tool: result → section item dict ─────────────────────────────────────

    def _result_to_section_item(self, result: AnalysisResult, size: str) -> dict:
        item: dict[str, Any] = {
            "section_type": result.data.get("result_type", "chart"),
            "task_id": result.task_id,
            "title": result.title,
            "size": size,
            "insight": result.data.get("insight", ""),
            "caveat": result.caveat,
        }

        if result.data.get("result_type") == "table":
            item["section_type"] = "table"
            item["records"] = result.data.get("records", [])
            item["segment_summary"] = result.data.get("segment_summary", [])
            if result.chart_spec:
                item["chart_spec"] = result.chart_spec

        elif result.data.get("result_type") == "heatmap":
            item["section_type"] = "heatmap"
            # chart_spec may be None if build failed — frontend null-guards this
            item["chart_spec"] = result.chart_spec
            # row_count drives dynamic height in the frontend
            item["row_count"] = len(result.data.get("y_labels", []))

        else:
            item["chart_spec"] = result.chart_spec

        return item

    # ── Tool: self-review ─────────────────────────────────────────────────────

    def _self_review(self, spec: dict) -> str:
        """
        Read the spec and critique it. Returns improvement note or empty string.
        Simple rule-based critique — no LLM needed.
        """
        issues = []

        tabs = spec.get("tabs", [])
        if not tabs:
            return "No tabs were generated."

        # Check first tab has KPIs
        first_tab = tabs[0]
        has_kpi = any(s.get("section_type") == "kpi_row" for s in first_tab.get("sections", []))
        if not has_kpi:
            issues.append("first_tab_missing_kpis")

        # Check no tab is empty
        for tab in tabs:
            if not tab.get("sections"):
                issues.append(f"empty_tab:{tab['id']}")

        # Check insight cards have content
        for tab in tabs:
            for section in tab.get("sections", []):
                if section.get("section_type") == "insight_card" and not section.get("text"):
                    issues.append("empty_insight_card")

        return ", ".join(issues) if issues else ""

    # ── Tool: apply critique ──────────────────────────────────────────────────

    def _apply_critique(self, spec: dict, critique: str) -> dict:
        """Apply fixes based on self-critique notes."""
        if "empty_insight_card" in critique:
            for tab in spec.get("tabs", []):
                tab["sections"] = [
                    s for s in tab.get("sections", [])
                    if not (s.get("section_type") == "insight_card" and not s.get("text"))
                ]
        return spec

    @property
    def spec(self) -> dict:
        return self._spec

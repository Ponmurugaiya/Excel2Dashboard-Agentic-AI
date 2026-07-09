"""
Strategist Agent
Goal: Decide what analyses are worth running on THIS specific dataset.

Real agent properties:
  - Memory: dataset context, tasks proposed, reprioritisation decisions
  - Tools: detect_patterns, propose_tasks, reprioritise (based on results)
  - Goal loop: observe profile → detect patterns → propose tasks → refine based on feedback
  - Communication: receives Quality feedback, can revise task list
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from backend.agents.base import BaseAgent
from backend.agents.message_bus import MessageBus
from backend.agents.models import (
    AgentName,
    AnalysisTask,
    DecisionPoint,
    Option,
    RunMode,
)


class StrategistAgent(BaseAgent):
    name = AgentName.DATA_SCIENTIST.value  # reports under Data Scientist in logs
    icon = "🧠"
    name = "Strategist"

    def __init__(self, bus: MessageBus, mode: RunMode):
        super().__init__(bus, mode)

    # ── Main entry point ──────────────────────────────────────────────────────

    async def plan(
        self,
        profile: dict,
        cleaning_report: dict,
    ) -> list[AnalysisTask]:
        """
        Observe the dataset profile and produce an ordered list of analysis tasks.
        Uses LLM to reason about what patterns are present.
        """
        self.log("Analysing dataset structure to identify analysis opportunities...")

        # ── Tool: detect structural patterns ─────────────────────────────────
        context = self._build_dataset_context(profile, cleaning_report)
        self.memory.set("dataset_context", context)

        # ── Tool: LLM-powered task proposal ──────────────────────────────────
        tasks = self._propose_tasks(context, profile)
        self.log(
            f"Identified {len(tasks)} analysis opportunities",
            {"tasks": [t.name for t in tasks]},
        )
        self.memory.remember("initial_tasks", {"tasks": [t.id for t in tasks]})

        # ── Present task plan to user ─────────────────────────────────────────
        task_list_str = "\n".join(
            f"  • {t.name} — {t.reason}" for t in tasks
        )
        chosen = await self.ask_user(DecisionPoint(
            agent=AgentName.DATA_SCIENTIST,
            icon=self.icon,
            context="Based on the dataset structure, these analyses have been identified.",
            question=f"Proceed with the following analysis plan?\n{task_list_str}",
            suggested_answer="proceed",
            reason="These analyses cover the key patterns detected in the data.",
            options=[
                Option("proceed", "Proceed with all", "Run all identified analyses"),
                Option("proceed_priority", "Priority analyses only",
                       "Run only high-priority analyses (faster)"),
            ],
            impact=f"{len(tasks)} analyses planned",
        ))

        if chosen == "proceed_priority":
            tasks = [t for t in tasks if t.priority >= 2]
            self.log(f"⟳ Reduced to {len(tasks)} priority analyses")

        self.mark_done()
        return tasks

    # ── Tool: build dataset context ───────────────────────────────────────────

    def _build_dataset_context(self, profile: dict, cleaning_report: dict) -> dict:
        """Extract semantic context from the profile — column roles, patterns present."""
        ctx: dict[str, Any] = {
            "total_rows": 0,
            "columns": [],
            "has_datetime": False,
            "has_entity_id": False,
            "has_transaction_id": False,
            "has_revenue": False,
            "has_quantity": False,
            "has_geography": False,
            "has_category": False,
            "entity_col": None,
            "time_col": None,
            "value_col": None,
            "transaction_col": None,
            "geo_col": None,
            "category_col": None,
            "derived_columns": cleaning_report.get("derived_columns", []),
        }

        for sheet_name, sheet_profile in profile.items():
            ctx["total_rows"] = sheet_profile["row_count"]

            for col, stats in sheet_profile["columns"].items():
                col_lower = col.lower()
                ctx["columns"].append({"name": col, "type": stats["type"]})

                if stats["type"] == "datetime":
                    ctx["has_datetime"] = True
                    if not ctx["time_col"]:
                        ctx["time_col"] = col

                if stats["type"] in ("number", "integer"):
                    for kw in ["price", "revenue", "amount", "total", "sales", "cost", "value"]:
                        if kw in col_lower:
                            ctx["has_revenue"] = True
                            if not ctx["value_col"]:
                                ctx["value_col"] = col
                    for kw in ["quantity", "qty", "units", "count"]:
                        if kw in col_lower:
                            ctx["has_quantity"] = True

                if stats["type"] == "string":
                    for kw in ["customerid", "customer_id", "userid", "user_id", "patientid", "employeeid"]:
                        if kw in col_lower:
                            ctx["has_entity_id"] = True
                            ctx["entity_col"] = col
                    for kw in ["invoiceno", "invoice_no", "order_id", "orderid", "transactionid"]:
                        if kw in col_lower:
                            ctx["has_transaction_id"] = True
                            ctx["transaction_col"] = col
                    for kw in ["country", "region", "state", "city", "location", "territory"]:
                        if kw in col_lower:
                            if stats.get("unique", 999) < 200:
                                ctx["has_geography"] = True
                                ctx["geo_col"] = col
                    for kw in ["description", "product", "category", "item", "sku", "name", "type"]:
                        if kw in col_lower:
                            if stats.get("unique", 0) > 1:
                                ctx["has_category"] = True
                                ctx["category_col"] = col

                # Also check if derived TotalPrice is available
                if col in cleaning_report.get("derived_columns", []):
                    if col.lower() in ("totalprice", "total_price"):
                        ctx["has_revenue"] = True
                        ctx["value_col"] = col

        return ctx

    # ── Tool: LLM task proposal ───────────────────────────────────────────────

    def _propose_tasks(self, context: dict, profile: dict) -> list[AnalysisTask]:
        """Use LLM to propose analysis tasks based on detected context."""

        profile_summary = self._format_profile_summary(profile)

        prompt = f"""You are a senior data analyst planning a BI dashboard.

DATASET CONTEXT:
{json.dumps(context, indent=2)}

COLUMN DETAILS:
{profile_summary}

Based on this dataset, propose the most valuable analysis tasks.

For each task, identify:
- id: unique snake_case identifier
- name: human-readable name
- pattern: one of [time_series, ranking, rfm, cohort, distribution, geo, kpi]
- columns: dict mapping roles to actual column names, e.g. {{"time_col": "InvoiceDate", "value_col": "TotalPrice"}}
- reason: why this analysis is valuable for THIS dataset (1 sentence)
- priority: 1 (nice to have) or 2 (important) or 3 (essential)

RULES:
- Only propose tasks where the required columns actually exist
- Always include a "kpi" task for headline numbers
- Always include "time_series" if a datetime + numeric value column exist
- Include "rfm" ONLY if entity_id + datetime + transaction_id + value all exist
- Include "cohort" ONLY if entity_id + datetime exist AND total_rows > 1000
- Include "ranking" for any high-cardinality string + numeric value combination
- Include "geo" only if a geography column exists
- Maximum 6 tasks total
- Prioritise tasks that answer "how is the business performing?" first

Return a JSON array of task objects. Nothing else.
"""
        try:
            raw = self._llm_json(prompt, task="planning")
            tasks = []
            for item in (raw if isinstance(raw, list) else raw.get("tasks", [])):
                tasks.append(AnalysisTask(
                    id=item.get("id", f"task_{len(tasks)}"),
                    name=item.get("name", "Analysis"),
                    pattern=item.get("pattern", "ranking"),
                    columns=item.get("columns", {}),
                    reason=item.get("reason", ""),
                    priority=int(item.get("priority", 1)),
                ))
            # Sort by priority descending
            tasks.sort(key=lambda t: t.priority, reverse=True)
            return tasks

        except Exception as e:
            self.log_error(f"LLM task planning failed: {e}. Falling back to rule-based.")
            return self._fallback_tasks(context)

    # ── Fallback task generation (no LLM) ────────────────────────────────────

    def _fallback_tasks(self, ctx: dict) -> list[AnalysisTask]:
        tasks = []

        tasks.append(AnalysisTask(
            id="kpi_overview",
            name="Key Metrics Overview",
            pattern="kpi",
            columns={
                "value_col": ctx.get("value_col", ""),
                "entity_col": ctx.get("entity_col", ""),
                "transaction_col": ctx.get("transaction_col", ""),
            },
            reason="Headline KPIs give immediate business context",
            priority=3,
        ))

        if ctx["has_datetime"] and ctx["has_revenue"]:
            tasks.append(AnalysisTask(
                id="revenue_over_time",
                name="Revenue Over Time",
                pattern="time_series",
                columns={"time_col": ctx["time_col"], "value_col": ctx["value_col"]},
                reason="Time series reveals growth trends and seasonality",
                priority=3,
            ))

        if ctx["has_category"] and ctx["has_revenue"]:
            tasks.append(AnalysisTask(
                id="top_categories",
                name=f"Top {ctx.get('category_col', 'Categories')} by Revenue",
                pattern="ranking",
                columns={"group_col": ctx["category_col"], "value_col": ctx["value_col"]},
                reason="Ranking shows which products/categories drive most revenue",
                priority=2,
            ))

        if ctx["has_entity_id"] and ctx["has_datetime"] and ctx["has_transaction_id"] and ctx["has_revenue"]:
            tasks.append(AnalysisTask(
                id="rfm_segmentation",
                name="Customer Segmentation (RFM)",
                pattern="rfm",
                columns={
                    "entity_col": ctx["entity_col"],
                    "time_col": ctx["time_col"],
                    "transaction_col": ctx["transaction_col"],
                    "value_col": ctx["value_col"],
                },
                reason="RFM scoring identifies high-value vs at-risk customers",
                priority=2,
            ))

        if ctx["has_entity_id"] and ctx["has_datetime"] and ctx["total_rows"] > 1000:
            tasks.append(AnalysisTask(
                id="cohort_retention",
                name="Customer Cohort Retention",
                pattern="cohort",
                columns={
                    "entity_col": ctx["entity_col"],
                    "time_col": ctx["time_col"],
                },
                reason="Cohort analysis reveals how well customers are retained over time",
                priority=2,
            ))

        if ctx["has_geography"] and ctx["has_revenue"]:
            tasks.append(AnalysisTask(
                id="revenue_by_geo",
                name=f"Revenue by {ctx.get('geo_col', 'Geography')}",
                pattern="geo",
                columns={"geo_col": ctx["geo_col"], "value_col": ctx["value_col"]},
                reason="Geographic breakdown highlights key markets",
                priority=1,
            ))

        return tasks

    # ── Helper ────────────────────────────────────────────────────────────────

    def _format_profile_summary(self, profile: dict) -> str:
        lines = []
        for sheet_name, sheet_profile in profile.items():
            lines.append(f"Sheet: {sheet_name} ({sheet_profile['row_count']:,} rows)")
            for col, stats in sheet_profile["columns"].items():
                t = stats["type"]
                extra = ""
                if t == "number":
                    extra = f" | min={stats.get('min')}, max={stats.get('max')}, mean={stats.get('mean')}"
                elif t == "datetime":
                    extra = f" | {stats.get('min_date')} to {stats.get('max_date')}"
                lines.append(
                    f"  {col}: {t}{extra} | unique={stats.get('unique')} | missing={stats['missing_pct']}%"
                )
        return "\n".join(lines)

"""
Quality Agent
Goal: Ensure every result that reaches the dashboard is statistically sound and interpretable.

Real agent properties:
  - Memory: all results reviewed, failure patterns for this dataset
  - Tools: inspect_distribution, check_interpretability, approve, reject, flag_for_user
  - Goal loop: receive result → inspect → test → approve/reject/flag → communicate back
  - Communication: approvals to Architect+Insight, rejections to Data Scientist
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.agents.base import BaseAgent
from backend.agents.message_bus import MessageBus
from backend.agents.models import (
    AgentName,
    AnalysisResult,
    DecisionPoint,
    Message,
    MessageType,
    Option,
    RunMode,
)


class QualityAgent(BaseAgent):
    name = AgentName.QUALITY.value
    icon = "🔍"

    def __init__(self, bus: MessageBus, mode: RunMode):
        super().__init__(bus, mode)
        self._accepted: list[AnalysisResult] = []
        self._failure_patterns: list[str] = []

    # ── Main entry point ──────────────────────────────────────────────────────

    async def review_all(self, raw_results: list[dict]) -> list[AnalysisResult]:
        """
        Review every result produced by the Data Scientist.
        Returns only the accepted results.
        """
        for raw in raw_results:
            result = await self._review_one(raw)
            if result and result.accepted:
                self._accepted.append(result)

        self.log(
            f"Quality review complete — {len(self._accepted)}/{len(raw_results)} results accepted"
        )
        self.mark_done()
        return self._accepted

    # ── Review loop for one result ────────────────────────────────────────────

    async def _review_one(self, raw: dict) -> AnalysisResult | None:
        task_id   = raw.get("task_id", "")
        task_name = raw.get("task_name", "")
        pattern   = raw.get("pattern", "")
        data      = raw.get("result", {})

        self.log(f"Reviewing: {task_name}")

        if not data:
            self.log(f"✗ Empty result for '{task_name}' — rejecting")
            self.memory.remember(f"rejected:{task_id}", {"reason": "empty result"})
            return None

        result = AnalysisResult(
            task_id=task_id,
            result_type=data.get("result_type", "chart"),
            title=data.get("title", task_name),
            data=data,
        )

        # ── Tool: inspect based on pattern ────────────────────────────────────
        verdict, quality_score, caveat, suggestion = self._inspect(data, pattern, task_name)

        result.quality_score = quality_score
        result.caveat = caveat

        if verdict == "accept":
            result.accepted = True
            self.log(f"✓ Accepted: {task_name} (score={quality_score:.2f})")
            self.memory.remember(f"accepted:{task_id}", {"score": quality_score})

        elif verdict == "flag":
            # Ask user
            chosen = await self.ask_user(DecisionPoint(
                agent=AgentName.QUALITY,
                icon=self.icon,
                context=f"'{task_name}' produced a result but quality is uncertain. {caveat}",
                question=f"Should we include '{task_name}' in the dashboard?",
                suggested_answer="include_caveat",
                reason=f"The result is directionally valid but has limitations: {caveat}",
                options=[
                    Option("include_caveat", "Include with a note", "Show it with a caveat label"),
                    Option("exclude", "Exclude it", "Leave this analysis out"),
                ],
                impact=f"Quality score: {quality_score:.2f}/1.0",
            ))
            if chosen == "exclude":
                self.log(f"⟳ Excluded by decision: {task_name}")
                result.accepted = False
            else:
                result.accepted = True
                result.caveat = caveat
                self.log(f"✓ Accepted with caveat: {task_name}")

        elif verdict == "reject":
            self.log(f"✗ Rejected: {task_name} — {caveat}")
            self.memory.remember(
                f"rejected:{task_id}",
                {"reason": caveat, "suggestion": suggestion},
            )
            self._failure_patterns.append(f"{pattern}:{caveat[:60]}")
            result.accepted = False

        return result

    # ── Tool: inspect a result ────────────────────────────────────────────────

    def _inspect(
        self, data: dict, pattern: str, task_name: str
    ) -> tuple[str, float, str, str]:
        """
        Returns: (verdict, quality_score, caveat, suggestion)
        verdict: "accept" | "flag" | "reject"
        """

        # ── KPI row — always accept if has items ──────────────────────────────
        if data.get("result_type") == "kpi_row":
            kpis = data.get("kpis", [])
            if not kpis:
                return "reject", 0.0, "No KPI values computed", ""
            return "accept", 1.0, "", ""

        # ── Time series ───────────────────────────────────────────────────────
        if pattern == "time_series":
            x = data.get("x", [])
            y = data.get("y", [])
            if len(x) < 2:
                return "reject", 0.0, "Less than 2 time periods — not a meaningful trend", ""
            # Flag for very short series, but don't reject — sample data is still useful
            if len(x) < 3:
                return "flag", 0.5, f"Only {len(x)} time periods — trend is very limited", ""
            non_zero = sum(1 for v in y if v and v != 0)
            if non_zero < len(y) * 0.5:
                return "flag", 0.6, "More than 50% of periods have zero values", ""
            return "accept", 0.9, "", ""

        # ── Ranking ───────────────────────────────────────────────────────────
        if pattern == "ranking":
            labels = data.get("labels", [])
            values = data.get("values", [])
            if len(labels) < 2:
                return "reject", 0.0, "Less than 2 categories to rank", ""
            # Check if one category dominates (>85%)
            if values and max(values) / (sum(values) or 1) > 0.85:
                return (
                    "flag",
                    0.7,
                    "One category accounts for >85% — chart may not be informative",
                    "Consider filtering to show only that category's breakdown",
                )
            return "accept", 0.9, "", ""

        # ── RFM ───────────────────────────────────────────────────────────────
        if pattern == "rfm":
            records = data.get("records", [])
            score_dist = data.get("score_distribution", {})
            if not records:
                return "reject", 0.0, "No customer records in RFM result", ""
            # Flag (not reject) for small customer counts — still useful as sample data
            if len(records) < 5:
                return "reject", 0.0, f"Only {len(records)} customers — too few for segmentation", ""
            if len(records) < 20:
                return "flag", 0.6, f"Only {len(records)} customers — segmentation is indicative only on sample data", ""
            std = score_dist.get("std", 1)
            rng = (score_dist.get("max", 12) - score_dist.get("min", 3)) or 1
            if std < rng * 0.1:
                return (
                    "flag",
                    0.6,
                    "RFM scores are tightly clustered — segment separation may be weak",
                    "Consider adjusting scoring thresholds",
                )
            return "accept", 0.85, "", ""

        # ── Cohort ────────────────────────────────────────────────────────────
        if pattern == "cohort":
            matrix = data.get("matrix", [])
            if not matrix:
                return "reject", 0.0, "Empty cohort matrix", ""
            total  = sum(len(row) for row in matrix)
            filled = sum(1 for row in matrix for v in row if v is not None)
            fill_rate = filled / total if total else 0
            # For small datasets the matrix will naturally be sparse — lower threshold
            if fill_rate < 0.05:
                return (
                    "flag",
                    0.5,
                    f"Cohort matrix is {100-fill_rate*100:.0f}% empty — very low repeat purchase rate",
                    "Include with caveat that retention data is sparse",
                )
            if fill_rate < 0.3:
                return (
                    "flag",
                    0.65,
                    f"Cohort matrix is sparse ({fill_rate*100:.0f}% filled) — typical for small or sample datasets",
                    "",
                )
            return "accept", 0.8, "", ""

        # ── Distribution ──────────────────────────────────────────────────────
        if pattern == "distribution":
            values = data.get("values", [])
            if len(values) < 10:
                return "reject", 0.0, "Too few values for a meaningful distribution", ""
            return "accept", 0.85, "", ""

        # ── Geo ───────────────────────────────────────────────────────────────
        if pattern == "geo":
            labels = data.get("labels", [])
            values = data.get("values", [])
            if len(labels) < 2:
                return "reject", 0.0, "Less than 2 geographic regions", ""
            return "accept", 0.85, "", ""

        # ── Default ───────────────────────────────────────────────────────────
        return "accept", 0.7, "", ""

    @property
    def accepted_results(self) -> list[AnalysisResult]:
        return self._accepted

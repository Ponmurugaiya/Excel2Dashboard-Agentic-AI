"""
Data Scientist Agent
Goal: Produce statistically valid, meaningful analysis of the dataset.

Real agent properties:
  - Memory: what analyses attempted, what succeeded/failed, statistical properties discovered
  - Tools: explore_data, form_hypothesis, write_code, request_review, store_result
  - Goal loop: observe → hypothesise → explore → code → execute → review → iterate
  - Communication: sends results to Quality Agent, receives approvals/rejections
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

import pandas as pd

from backend.agents.base import BaseAgent
from backend.agents.message_bus import MessageBus
from backend.agents.models import (
    AgentName,
    AnalysisTask,
    DecisionPoint,
    Message,
    MessageType,
    Option,
    RunMode,
)
from backend.agents.sandbox import execute as sandbox_execute


class DataScientistAgent(BaseAgent):
    name = AgentName.DATA_SCIENTIST.value
    icon = "🔬"

    MAX_RETRIES_PER_TASK = 2

    def __init__(self, bus: MessageBus, mode: RunMode):
        super().__init__(bus, mode)
        self._tasks: list[AnalysisTask] = []
        self._results: list[dict] = []

    # ── Main entry point ──────────────────────────────────────────────────────

    async def run(
        self,
        df: pd.DataFrame,
        profile: dict,
        tasks: list[AnalysisTask],
    ) -> list[dict]:
        """
        Execute each analysis task.
        For each task: write code → execute → handle errors → send to Quality Agent.
        Returns list of raw result dicts (accepted/rejected decided by Quality Agent).
        """
        self._tasks = tasks
        self.memory.set("profile", profile)
        self.memory.set("columns", list(df.columns))

        for task in tasks:
            if task.status == "skipped":
                continue

            self.log(f"Starting analysis: {task.name}")
            await self._run_task(df, task, profile)

        self.mark_done()
        return self._results

    # ── Task loop ─────────────────────────────────────────────────────────────

    async def _run_task(
        self,
        df: pd.DataFrame,
        task: AnalysisTask,
        profile: dict,
    ):
        task.status = "running"
        last_error = None

        for attempt in range(1, self.MAX_RETRIES_PER_TASK + 1):
            task.attempts = attempt

            # ── Tool: write code ──────────────────────────────────────────────
            self.log(f"Writing code for '{task.name}' (attempt {attempt})...")
            code = self._write_code(task, profile, last_error)
            self.memory.remember(
                f"code_attempt:{task.id}:{attempt}",
                {"code_preview": code[:200]},
            )

            # ── Tool: execute code ────────────────────────────────────────────
            result = sandbox_execute(code, df)

            if result.success:
                self.log(f"✓ Code executed successfully for '{task.name}'")
                task.result = result.data
                task.status = "done"

                # ── Post result to Quality Agent ──────────────────────────────
                self.bus.post(Message(
                    type=MessageType.RESULT,
                    from_agent=self.name,
                    to_agent=AgentName.QUALITY.value,
                    payload={
                        "task_id": task.id,
                        "task_name": task.name,
                        "pattern": task.pattern,
                        "result": result.data,
                        "code": code,
                    },
                ))
                self._results.append({
                    "task_id": task.id,
                    "task_name": task.name,
                    "pattern": task.pattern,
                    "columns": task.columns,
                    "result": result.data,
                    "code": code,
                })
                return

            else:
                last_error = result.error
                self.log(
                    f"✗ Attempt {attempt} failed: {result.error[:120]}",
                    {"error": result.error, "line": result.error_line},
                )
                self.memory.remember(
                    f"error:{task.id}:{attempt}",
                    {"error": result.error, "line": result.error_line},
                )

                # On final failure, ask user if they want to skip
                if attempt == self.MAX_RETRIES_PER_TASK:
                    chosen = await self.ask_user(DecisionPoint(
                        agent=AgentName.DATA_SCIENTIST,
                        icon=self.icon,
                        context=f"'{task.name}' failed after {attempt} attempts.",
                        question=f"Analysis '{task.name}' could not be completed. What should we do?",
                        suggested_answer="skip",
                        reason="After multiple failures, skipping prevents blocking the rest of the dashboard.",
                        options=[
                            Option("skip", "Skip this analysis", "Continue without this chart"),
                            Option("retry", "Try one more time", "One additional attempt"),
                        ],
                        impact="This chart will be missing from the dashboard if skipped.",
                    ))

                    if chosen == "skip":
                        task.status = "failed"
                        self.log(f"⟳ Skipping '{task.name}'")
                        return
                    else:
                        # one more attempt allowed
                        continue

        task.status = "failed"

    # ── Tool: write analysis code (LLM) ───────────────────────────────────────

    def _write_code(
        self,
        task: AnalysisTask,
        profile: dict,
        previous_error: str | None = None,
    ) -> str:
        """Ask LLM to write a self-contained `run(df)` function for the task."""

        columns_desc = self._format_columns(profile)
        error_section = ""
        if previous_error:
            error_section = f"""
PREVIOUS ATTEMPT FAILED WITH THIS ERROR — fix it:
{previous_error}
"""

        prompt = f"""You are writing a Python analysis function.

DATASET COLUMNS:
{columns_desc}

TASK: {task.name}
PATTERN: {task.pattern}
COLUMN ROLES: {json.dumps(task.columns)}
REASON: {task.reason}

{error_section}

Write a Python function named `run(df)` that:
1. Takes a pandas DataFrame `df` as input
2. Performs the analysis described above
3. Returns a dict with this exact structure:

For pattern "time_series":
{{
  "result_type": "chart",
  "title": "...",
  "chart_type": "line",
  "x": [...],         // list of period/date strings
  "y": [...],         // list of numeric values
  "x_label": "...",
  "y_label": "...",
  "insight": "..."    // 1-sentence finding
}}

For pattern "ranking":
{{
  "result_type": "chart",
  "title": "...",
  "chart_type": "bar",
  "labels": [...],    // category names
  "values": [...],    // numeric values
  "x_label": "...",
  "y_label": "...",
  "insight": "..."
}}

For pattern "rfm":
{{
  "result_type": "table",
  "title": "Customer Segments",
  "records": [...],   // list of dicts, max 500 rows
  "segment_summary": [  // one dict per segment
    {{"segment": "...", "count": N, "avg_monetary": N, "avg_recency": N}}
  ],
  "score_distribution": {{"min": N, "max": N, "mean": N, "std": N}},
  "insight": "..."
}}

For pattern "cohort":
{{
  "result_type": "heatmap",
  "title": "Cohort Retention",
  "matrix": [[...]],  // 2D list of retention rates (0-1), None for missing
  "x_labels": [...],  // cohort index labels e.g. ["Month 0", "Month 1", ...]
  "y_labels": [...],  // cohort period labels e.g. ["2011-01", ...]
  "insight": "..."
}}

For pattern "distribution":
{{
  "result_type": "chart",
  "chart_type": "histogram",
  "title": "...",
  "values": [...],
  "x_label": "...",
  "insight": "..."
}}

For pattern "geo":
{{
  "result_type": "chart",
  "chart_type": "bar",
  "title": "...",
  "labels": [...],
  "values": [...],
  "x_label": "Country",
  "y_label": "...",
  "insight": "..."
}}

For pattern "kpi":
{{
  "result_type": "kpi_row",
  "title": "Key Metrics",
  "kpis": [
    {{"label": "...", "value": N, "format": "currency|number|percentage"}}
  ],
  "insight": ""
}}

RULES:
- Use only the available columns listed above
- Handle missing values with .dropna() or .fillna()
- Convert Period objects to strings before returning
- Keep records lists to max 500 items
- All returned values must be JSON-serialisable (no numpy types, no pd.Timestamp)
- Import nothing — pd and np are already available
- Do NOT use file system, network, or subprocess
- Return ONLY the function definition, no other code

Return ONLY the Python function code, nothing else.
"""

        try:
            import google.generativeai as genai
            import os

            api_key = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                system_instruction="You are a Python data analysis expert. Return only valid Python code.",
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            raw = model.generate_content(prompt).text.strip()

            # Strip markdown code fences if present
            import re
            raw = re.sub(r"```python\s*", "", raw)
            raw = re.sub(r"```\s*", "", raw)
            return raw.strip()

        except Exception as e:
            # Fallback: return a minimal safe function
            return textwrap.dedent(f"""
def run(df):
    return {{
        "result_type": "chart",
        "chart_type": "bar",
        "title": "{task.name}",
        "labels": [],
        "values": [],
        "x_label": "",
        "y_label": "",
        "insight": "Could not generate analysis: {str(e)[:100]}"
    }}
""")

    # ── Helper ────────────────────────────────────────────────────────────────

    def _format_columns(self, profile: dict) -> str:
        lines = []
        for sheet_name, sheet_profile in profile.items():
            for col, stats in sheet_profile["columns"].items():
                t = stats["type"]
                extra = ""
                if t == "number":
                    extra = f", min={stats.get('min')}, max={stats.get('max')}, mean={stats.get('mean')}"
                elif t == "datetime":
                    extra = f", {stats.get('min_date')} to {stats.get('max_date')}"
                missing = f", {stats['missing_pct']}% missing" if stats["missing_pct"] > 0 else ""
                lines.append(f"  {col} ({t}{missing}{extra})")
        return "\n".join(lines)

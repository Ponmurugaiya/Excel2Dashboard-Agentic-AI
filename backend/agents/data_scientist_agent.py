"""
Data Scientist Agent
Goal: Produce statistically valid, meaningful analysis of the dataset.

Real agent loop:
  observe task → write code → execute in sandbox → on error: diagnose + rewrite → repeat
  Never asks the user about internal code failures — it handles them autonomously.
  Only escalates to the user for genuine dataset-level decisions.
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
    Message,
    MessageType,
    RunMode,
)
from backend.agents.sandbox import execute as sandbox_execute


class DataScientistAgent(BaseAgent):
    name = AgentName.DATA_SCIENTIST.value
    icon = "🔬"

    MAX_RETRIES_PER_TASK = 3   # 3 attempts before giving up silently

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
        self._tasks = tasks
        self.memory.set("profile", profile)
        self.memory.set("columns", list(df.columns))
        self.memory.set("shape", {"rows": len(df), "cols": len(df.columns)})

        for task in tasks:
            if task.status == "skipped":
                continue
            self.log(f"Starting analysis: {task.name}")
            await self._run_task(df, task, profile)

        self.mark_done()
        return self._results

    # ── Task execution loop ───────────────────────────────────────────────────

    async def _run_task(
        self,
        df: pd.DataFrame,
        task: AnalysisTask,
        profile: dict,
    ):
        task.status = "running"
        last_error: str | None = None
        last_code:  str | None = None

        for attempt in range(1, self.MAX_RETRIES_PER_TASK + 1):
            task.attempts = attempt

            # Write code — on retry, include previous code + error for diagnosis
            self.log(f"Writing code for '{task.name}' (attempt {attempt})...")
            code = self._write_code(task, profile, last_error, last_code)
            last_code = code

            self.memory.remember(
                f"code:{task.id}:attempt{attempt}",
                {"preview": code[:200]},
            )

            # Execute in sandbox
            result = sandbox_execute(code, df)

            if result.success:
                self.log(f"✓ Executed: {task.name}")
                task.result = result.data
                task.status = "done"

                self.bus.post(Message(
                    type=MessageType.RESULT,
                    from_agent=self.name,
                    to_agent=AgentName.QUALITY.value,
                    payload={
                        "task_id":   task.id,
                        "task_name": task.name,
                        "pattern":   task.pattern,
                        "result":    result.data,
                        "code":      code,
                    },
                ))
                self._results.append({
                    "task_id":   task.id,
                    "task_name": task.name,
                    "pattern":   task.pattern,
                    "columns":   task.columns,
                    "result":    result.data,
                    "code":      code,
                })
                return

            # Failure — log and loop (no user escalation)
            last_error = result.error
            self.log(
                f"✗ Attempt {attempt}/{self.MAX_RETRIES_PER_TASK} failed — diagnosing...",
                {"error": result.error[:200], "line": result.error_line},
            )
            self.memory.remember(
                f"error:{task.id}:attempt{attempt}",
                {"error": result.error, "line": result.error_line},
            )

        # All attempts exhausted — log and move on silently
        # The dashboard will simply not include this chart
        task.status = "failed"
        self.log(
            f"✗ '{task.name}' could not be completed after {self.MAX_RETRIES_PER_TASK} attempts — skipping",
            {"last_error": last_error},
        )
        self.memory.remember(
            f"failed:{task.id}",
            {"error": last_error, "attempts": self.MAX_RETRIES_PER_TASK},
        )

    # ── Code writer ───────────────────────────────────────────────────────────

    def _write_code(
        self,
        task: AnalysisTask,
        profile: dict,
        previous_error: str | None = None,
        previous_code:  str | None = None,
    ) -> str:
        columns_desc = self._format_columns(profile)

        # Build the error context with the actual failing code so the LLM can see exactly what went wrong
        error_section = ""
        if previous_error and previous_code:
            error_section = f"""
PREVIOUS CODE (failed — do NOT repeat it):
```python
{previous_code[:1500]}
```

ERROR:
{previous_error}

DIAGNOSIS REQUIRED: Read the error carefully.
- KeyError: '__import__' → you used `import` inside run() — DON'T. pd, np, datetime, re, math are pre-available.
- NoneType returned → your run() function is missing a return statement or has an early exit path
- run() not defined → you wrapped the function in a class, if-block, or named it differently
- Period/Timestamp not serialisable → convert with str() before returning
Fix ONLY the specific error above. Rewrite the entire run() function.
"""
        elif previous_error:
            error_section = f"""
PREVIOUS ATTEMPT FAILED:
{previous_error}

Fix this error in your rewrite.
"""

        prompt = f"""Write a Python function for data analysis.

AVAILABLE COLUMNS (use exact names):
{columns_desc}

TASK: {task.name}
PATTERN: {task.pattern}
COLUMN ROLES: {json.dumps(task.columns)}
{error_section}

CRITICAL RULES — violations cause failures:
1. Function MUST be named exactly `run` with signature `def run(df):`
2. DO NOT use any import statements — these are pre-available: pd, np, datetime, re, math
3. Function MUST always return a dict (no code paths that return None)
4. Convert ALL Period/Timestamp objects to str() before returning
5. Convert ALL numpy types (int64, float64, etc.) using .item() or int()/float()
6. Use df.copy() at the start to avoid mutating the input
7. Handle errors with try/except and return a valid dict even on failure

RETURN FORMAT for pattern "{task.pattern}":
{self._get_return_template(task.pattern)}

Return ONLY the Python function — no imports, no prose, no markdown fences, no other code.
The function must start with `def run(df):` on the first line.
"""

        try:
            from backend.llm.client import llm_code
            raw = llm_code(prompt)

            # Verify it contains a run function — if not, wrap it
            import re as re_module
            if not re_module.search(r"^def run\s*\(", raw, re_module.MULTILINE):
                # LLM returned code without a run() — wrap it
                raw = self._wrap_as_run_function(raw, task)

            return raw

        except Exception as e:
            return self._fallback_code(task, str(e))

    def _get_return_template(self, pattern: str) -> str:
        templates = {
            "time_series": """{
  "result_type": "chart", "chart_type": "line",
  "title": "...", "x": [...], "y": [...],
  "x_label": "...", "y_label": "...", "insight": "..."
}""",
            "ranking": """{
  "result_type": "chart", "chart_type": "bar",
  "title": "...", "labels": [...], "values": [...],
  "x_label": "...", "y_label": "...", "insight": "..."
}""",
            "rfm": """{
  "result_type": "table", "title": "Customer Segments",
  "records": [{...}],
  "segment_summary": [{"segment": "...", "count": N, "avg_monetary": N, "avg_recency": N}],
  "score_distribution": {"min": N, "max": N, "mean": N, "std": N},
  "insight": "..."
}""",
            "cohort": """{
  "result_type": "heatmap", "title": "Cohort Retention",
  "matrix": [[...]], "x_labels": [...], "y_labels": [...], "insight": "..."
}""",
            "geo": """{
  "result_type": "chart", "chart_type": "bar",
  "title": "...", "labels": [...], "values": [...],
  "x_label": "Country", "y_label": "...", "insight": "..."
}""",
            "kpi": """{
  "result_type": "kpi_row", "title": "Key Metrics",
  "kpis": [{"label": "...", "value": N, "format": "currency|number|percentage"}],
  "insight": ""
}""",
            "distribution": """{
  "result_type": "chart", "chart_type": "histogram",
  "title": "...", "values": [...], "x_label": "...", "insight": "..."
}""",
        }
        return templates.get(pattern, '{"result_type": "chart", "chart_type": "bar", "title": "...", "labels": [], "values": [], "x_label": "", "y_label": "", "insight": ""}')

    def _wrap_as_run_function(self, code: str, task: AnalysisTask) -> str:
        """Wrap bare code (no run() function) inside a run() function."""
        indented = textwrap.indent(code.strip(), "    ")
        return f"""def run(df):
    df = df.copy()
    try:
{indented}
    except Exception as e:
        return {{
            "result_type": "chart", "chart_type": "bar",
            "title": "{task.name}", "labels": [], "values": [],
            "x_label": "", "y_label": "", "insight": str(e)[:100]
        }}
"""

    def _fallback_code(self, task: AnalysisTask, error_msg: str) -> str:
        """Return safe fallback code when LLM call itself fails."""
        safe_name = task.name.replace('"', "'")
        safe_err  = error_msg[:100].replace('"', "'")
        return textwrap.dedent(f"""\
def run(df):
    return {{
        "result_type": "chart",
        "chart_type": "bar",
        "title": "{safe_name}",
        "labels": [],
        "values": [],
        "x_label": "",
        "y_label": "",
        "insight": "Analysis unavailable: {safe_err}"
    }}
""")

    # ── Helpers ───────────────────────────────────────────────────────────────

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
                is_id = " [ID column]" if stats.get("is_id") else ""
                missing = f", {stats['missing_pct']}% missing" if stats["missing_pct"] > 0 else ""
                lines.append(f"  {col} ({t}{missing}{extra}){is_id}")
        return "\n".join(lines)

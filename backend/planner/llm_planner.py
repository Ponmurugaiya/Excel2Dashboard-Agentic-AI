"""
Dashboard Planner — Phase 1 (legacy, kept for backward compatibility)
Single LLM call that takes the dataset profile and returns KPI + chart recommendations.
Now routes through the unified LLM client (Gemini → Groq fallback).
"""

import json
import re
from typing import Any, Dict

from backend.llm.client import llm_json as _llm_json_base

def _client_llm_json(prompt: str, task: str = "planning") -> dict:
    return _llm_json_base(prompt, task=task)


# ── Public API ────────────────────────────────────────────────────────────────

def plan_dashboard(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a dataset profile, ask the LLM to recommend KPIs and charts.
    """
    prompt = _build_prompt(profile)
    try:
        return _client_llm_json(prompt, task="planning")
    except Exception as e:
        preview = str(e)[:200]
        return {
            "kpis": [],
            "charts": [],
            "reasoning": f"LLM planning failed: {preview}",
        }


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(profile: Dict[str, Any]) -> str:
    sheet_summaries = []
    for sheet_name, sheet_profile in profile.items():
        col_lines = []
        for col, stats in sheet_profile["columns"].items():
            col_type = stats["type"]
            extra = ""
            if col_type == "number":
                extra = f"min={stats.get('min')}, max={stats.get('max')}, mean={stats.get('mean')}"
            elif col_type == "datetime":
                extra = f"{stats.get('min_date')} to {stats.get('max_date')}"
            missing_note = f", {stats['missing_pct']}% missing" if stats["missing_pct"] > 0 else ""
            col_lines.append(f"  - {col} ({col_type}{missing_note}){': ' + extra if extra else ''}")

        sheet_summaries.append(
            f"Sheet: {sheet_name} | Rows: {sheet_profile['row_count']}\n"
            + "\n".join(col_lines)
        )

    dataset_description = "\n\n".join(sheet_summaries)

    return f"""You are a BI dashboard expert. Analyse this dataset profile and return a JSON dashboard plan.

{dataset_description}

Rules:
- Only use columns listed above.
- KPI aggregations: sum | mean | count | max | min | distinct_count
- Chart types: line | bar | pie | scatter | area | histogram
- Return exactly 3-5 KPIs and 3-5 charts. No more.
- Prefer a time-series line chart when a date column exists.
- Keep "reasoning" under 30 words.

Return ONLY this JSON structure, nothing else:
{{
  "kpis": [{{"label":"...","column":"...","aggregation":"...","format":"number|currency|percentage"}}],
  "charts": [{{"type":"...","title":"...","x":"...","y":"...","color":null,"sheet":"..."}}],
  "reasoning": "..."
}}"""

"""
Dashboard Planner — Phase 1
Single LLM call that takes the dataset profile and returns KPI + chart recommendations.
Uses Google Gemini via the official google-generativeai SDK.
"""

import json
import os
import re
from typing import Any, Dict

import google.generativeai as genai


# ── Public API ────────────────────────────────────────────────────────────────

def plan_dashboard(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a dataset profile (from profiler.profile_sheets), ask the LLM to
    recommend KPIs and charts.

    Returns:
    {
        "kpis":    [ {"label": ..., "column": ..., "aggregation": ..., "format": ...} ],
        "charts":  [ {"type": ..., "title": ..., "x": ..., "y": ..., "sheet": ...} ],
        "reasoning": "..."
    }
    """
    prompt = _build_prompt(profile)
    raw_response = _call_llm(prompt)
    plan = _parse_response(raw_response)
    return plan


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(profile: Dict[str, Any]) -> str:
    """
    Convert the data profile into a compact prompt.
    Keeping the prompt short directly reduces the output size needed.
    """
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

    # Strict rules keep the response short and parseable
    prompt = f"""You are a BI dashboard expert. Analyse this dataset profile and return a JSON dashboard plan.

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
    return prompt


# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_llm(prompt: str) -> str:
    """
    Call Google Gemini. Raises EnvironmentError if the API key is missing.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )

    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=(
            "You are a senior data analyst. "
            "Respond with valid JSON only — no markdown, no code fences, no extra text."
        ),
        generation_config=genai.GenerationConfig(
            temperature=0.1,          # as deterministic as possible
            max_output_tokens=8192,   # ample room — never truncate mid-JSON
            response_mime_type="application/json",
        ),
    )

    response = model.generate_content(prompt)
    return response.text.strip()


# ── Response parser ───────────────────────────────────────────────────────────

def _parse_response(raw: str) -> Dict[str, Any]:
    """
    Parse the LLM JSON response with multiple fallback strategies:
    1. Direct parse
    2. Strip markdown fences and retry
    3. Extract the first {...} block with regex and retry
    4. Return a safe empty structure so the pipeline never crashes
    """
    # ── Strategy 1: direct parse ──────────────────────────────────────────────
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # ── Strategy 2: strip markdown fences ────────────────────────────────────
    clean = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # ── Strategy 3: extract first { ... } block ───────────────────────────────
    # Handles cases where the model prefixes text before the JSON
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # ── Strategy 4: safe fallback ─────────────────────────────────────────────
    # Log enough context to diagnose without crashing the pipeline
    preview = raw[:400].replace("\n", " ")
    return {
        "kpis": [],
        "charts": [],
        "reasoning": f"Could not parse LLM response. Raw preview: {preview}",
    }

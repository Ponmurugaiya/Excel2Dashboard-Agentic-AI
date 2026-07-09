"""
Dashboard Builder — Phase 1
Orchestrates the full pipeline: parse → profile → plan → charts → JSON.
This is the single entry point the API layer calls.
Supports Excel and CSV files.
"""

import json
from pathlib import Path
from typing import Any, Dict

from backend.parser.file_parser import parse_file
from backend.profiler.profile import profile_sheets
from backend.planner.llm_planner import plan_dashboard
from backend.charts.chart_generator import generate_charts, compute_kpis


def build_dashboard(file_path: str) -> Dict[str, Any]:
    """
    Full Phase-1 pipeline.

    Args:
        file_path: Path to the uploaded Excel file.

    Returns:
        A dashboard JSON dict:
        {
            "file": "sales.xlsx",
            "sheets": ["Sheet1", ...],
            "profile": { ... },
            "plan": { "kpis": [...], "charts": [...], "reasoning": "..." },
            "kpis": [ {"label": ..., "value": ..., "format": ...}, ... ],
            "charts": [ {"id": ..., "title": ..., "figure": {...}}, ... ],
        }
    """
    path = Path(file_path)

    # ── Step 1: Parse ─────────────────────────────────────────────────────────
    sheets = parse_file(file_path)

    # ── Step 2: Profile ───────────────────────────────────────────────────────
    profile = profile_sheets(sheets)

    # ── Step 3: Plan (one LLM call) ───────────────────────────────────────────
    plan = plan_dashboard(profile)

    # ── Step 4: Charts + KPIs ─────────────────────────────────────────────────
    charts = generate_charts(plan, sheets)
    kpis = compute_kpis(plan, sheets)

    # ── Assemble dashboard JSON ───────────────────────────────────────────────
    dashboard = {
        "file": path.name,
        "sheets": list(sheets.keys()),
        "profile": profile,
        "plan": plan,
        "kpis": kpis,
        "charts": charts,
    }

    return dashboard


def save_dashboard(dashboard: Dict[str, Any], output_path: str) -> None:
    """Persist the dashboard JSON to disk (for caching / debugging)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, default=str)

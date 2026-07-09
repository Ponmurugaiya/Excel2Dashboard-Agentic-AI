"""
Orchestrator
Drives the full multi-agent pipeline. Event-driven, not a fixed pipeline.

Flow:
  Cleaner → Strategist → Data Scientist + Quality (concurrent per task) → Insight → Architect

Supports both collaborative (pause on user questions) and autonomous modes.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from backend.agents.cleaner_agent import CleanerAgent
from backend.agents.data_scientist_agent import DataScientistAgent
from backend.agents.insight_agent import InsightAgent
from backend.agents.architect_agent import ArchitectAgent
from backend.agents.quality_agent import QualityAgent
from backend.agents.strategist_agent import StrategistAgent
from backend.agents.message_bus import MessageBus
from backend.agents.models import RunMode
from backend.parser.file_parser import parse_file
from backend.profiler.profile import profile_sheets


SESSION_DIR = Path("storage/sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class AnalysisSession:
    """
    Holds all state for one analysis run.
    Lives in memory + persisted to storage/sessions/{id}.
    """
    def __init__(self, session_id: str, file_path: str, mode: RunMode):
        self.session_id = session_id
        self.file_path = file_path
        self.mode = mode
        self.status = "created"   # created | cleaning | planning | analysing | designing | done | error
        self.bus = MessageBus()
        self.dashboard_spec: dict | None = None
        self.error: str | None = None
        self._task: asyncio.Task | None = None

        # Agents
        self.cleaner    = CleanerAgent(self.bus, mode)
        self.strategist = StrategistAgent(self.bus, mode)
        self.scientist  = DataScientistAgent(self.bus, mode)
        self.quality    = QualityAgent(self.bus, mode)
        self.insight    = InsightAgent(self.bus, mode)
        self.architect  = ArchitectAgent(self.bus, mode)

    # ── State helpers ─────────────────────────────────────────────────────────

    def get_events(self, since: float = 0) -> list[dict]:
        return self.bus.messages_as_dicts(since)

    def is_waiting_for_user(self) -> bool:
        return self.bus.is_waiting_for_user()

    def get_pending_question(self) -> dict | None:
        q = self.bus.get_pending_question()
        if q:
            return q.to_dict()
        return None

    def resolve_user_answer(self, answer: str):
        self.bus.resolve_user_question(answer)

    # ── Session directory ─────────────────────────────────────────────────────

    @property
    def session_dir(self) -> Path:
        d = SESSION_DIR / self.session_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_csv(self, name: str, df: pd.DataFrame):
        df.to_csv(self.session_dir / f"{name}.csv", index=False)

    def save_spec(self):
        if self.dashboard_spec:
            with open(self.session_dir / "dashboard_spec.json", "w") as f:
                json.dump(self.dashboard_spec, f, indent=2, default=str)


# ── Singleton session store ────────────────────────────────────────────────────

_sessions: dict[str, AnalysisSession] = {}


def create_session(file_path: str, mode: RunMode) -> AnalysisSession:
    session_id = uuid.uuid4().hex
    session = AnalysisSession(session_id, file_path, mode)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> AnalysisSession | None:
    return _sessions.get(session_id)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_pipeline(session: AnalysisSession):
    """
    Full multi-agent pipeline. Runs as an async task.
    All agents communicate through session.bus.
    """
    bus = session.bus

    try:
        # ── Step 1: Parse + Profile ───────────────────────────────────────────
        session.status = "parsing"
        bus.post_log("system", f"Parsing file: {Path(session.file_path).name}")

        sheets = parse_file(session.file_path)
        profile = profile_sheets(sheets)
        df = next(iter(sheets.values()))  # primary sheet

        bus.post_log("system", f"File parsed — {len(df):,} rows, {len(df.columns)} columns")

        # ── Step 2: Cleaner Agent ─────────────────────────────────────────────
        session.status = "cleaning"
        cleaned_df, cleaning_report = await session.cleaner.run(df)
        session.save_csv("cleaned_transactions", cleaned_df)

        # Re-profile after cleaning
        cleaned_sheets = {"data": cleaned_df}
        clean_profile = profile_sheets(cleaned_sheets)

        # ── Step 3: Strategist Agent ──────────────────────────────────────────
        session.status = "planning"
        tasks = await session.strategist.plan(clean_profile, cleaning_report)

        # ── Step 4: Data Scientist + Quality (per task) ───────────────────────
        session.status = "analysing"
        raw_results = await session.scientist.run(cleaned_df, clean_profile, tasks)
        accepted_results = await session.quality.review_all(raw_results)

        # Save per-task CSVs
        for raw in raw_results:
            data = raw.get("result", {})
            if data.get("result_type") == "table":
                records = data.get("records", [])
                if records:
                    pd.DataFrame(records).to_csv(
                        session.session_dir / f"{raw['task_id']}.csv", index=False
                    )
            elif data.get("result_type") == "heatmap":
                matrix = data.get("matrix", [])
                y_labels = data.get("y_labels", [])
                if matrix:
                    pd.DataFrame(matrix, index=y_labels or None).to_csv(
                        session.session_dir / f"{raw['task_id']}.csv"
                    )

        # ── Step 5: Insight Agent ─────────────────────────────────────────────
        session.status = "insight"
        insights = await session.insight.generate(accepted_results)

        # ── Step 6: Dashboard Architect ───────────────────────────────────────
        session.status = "designing"
        file_title = Path(session.file_path).stem.replace("_", " ").title()
        spec = await session.architect.design(accepted_results, insights, file_title)

        # Attach auto-decisions log to spec
        spec["auto_decisions"] = bus.get_auto_decisions()

        session.dashboard_spec = spec
        session.save_spec()
        session.status = "done"
        bus.post_log("system", "✓ Dashboard ready")

    except Exception as exc:
        import traceback
        session.status = "error"
        session.error = str(exc)
        bus.post_log("system", f"Pipeline error: {exc}")
        traceback.print_exc()

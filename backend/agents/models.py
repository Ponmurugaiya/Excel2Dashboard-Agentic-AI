"""
Shared data models used across all agents.
Every agent speaks this language.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


# ── Enums ─────────────────────────────────────────────────────────────────────

class AgentName(str, Enum):
    CLEANER     = "Cleaner"
    DATA_SCIENTIST = "Data Scientist"
    QUALITY     = "Quality"
    ARCHITECT   = "Dashboard Architect"
    INSIGHT     = "Insight"


class MessageType(str, Enum):
    # Agent → Agent
    TASK        = "task"
    RESULT      = "result"
    APPROVAL    = "approval"
    REJECTION   = "rejection"
    QUESTION    = "question"       # collaborative mode: pause + show user
    AUTO_DECISION = "auto_decision"  # autonomous mode: log + continue
    DONE        = "done"

    # Agent → User
    USER_QUESTION = "user_question"

    # User → Agent
    USER_RESPONSE = "user_response"

    # System
    LOG         = "log"
    ERROR       = "error"


class RunMode(str, Enum):
    COLLABORATIVE = "collaborative"
    AUTONOMOUS    = "autonomous"


# ── Option ───────────────────────────────────────────────────────────────────

@dataclass
class Option:
    id: str
    label: str
    description: str = ""


# ── DecisionPoint ─────────────────────────────────────────────────────────────

@dataclass
class DecisionPoint:
    """
    Structured representation of every agent decision point.
    In collaborative mode → shown to user as a question card.
    In autonomous mode   → suggestion is taken, reason is logged.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    agent: AgentName = AgentName.DATA_SCIENTIST
    icon: str = "🤔"
    context: str = ""          # what situation triggered this
    question: str = ""         # the actual question
    suggested_answer: str = "" # which option id is the autonomous choice
    reason: str = ""           # why that's suggested
    options: list[Option] = field(default_factory=list)
    impact: str = ""           # e.g. "affects 135,000 rows"


# ── Message ──────────────────────────────────────────────────────────────────

@dataclass
class Message:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type: MessageType = MessageType.LOG
    from_agent: str = "system"
    to_agent: str = "all"
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "from": self.from_agent,
            "to": self.to_agent,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


# ── AgentMemory ───────────────────────────────────────────────────────────────

@dataclass
class MemoryEntry:
    timestamp: float = field(default_factory=time.time)
    event: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMemory:
    """Per-agent memory — short-term (current task) + long-term (session history)."""
    short_term: dict[str, Any] = field(default_factory=dict)
    long_term: list[MemoryEntry] = field(default_factory=list)

    def remember(self, event: str, data: dict[str, Any] = None):
        self.long_term.append(MemoryEntry(event=event, data=data or {}))

    def recall(self, keyword: str) -> list[MemoryEntry]:
        return [e for e in self.long_term if keyword.lower() in e.event.lower()]

    def set(self, key: str, value: Any):
        self.short_term[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.short_term.get(key, default)


# ── AnalysisTask ──────────────────────────────────────────────────────────────

@dataclass
class AnalysisTask:
    id: str
    name: str
    pattern: str                       # "time_series" | "rfm" | "cohort" | "distribution" | "ranking" | "geo"
    columns: dict[str, str]            # role → column name, e.g. {"entity_id": "CustomerID"}
    reason: str
    priority: int = 1                  # higher = more important
    status: Literal["pending", "running", "done", "failed", "skipped"] = "pending"
    attempts: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None


# ── AnalysisResult ────────────────────────────────────────────────────────────

@dataclass
class AnalysisResult:
    task_id: str
    result_type: Literal["chart", "table", "heatmap", "kpi_row"]
    title: str
    data: Any                          # raw computed data
    chart_spec: dict[str, Any] | None = None   # plotly figure JSON
    insight: str = ""
    quality_score: float = 0.0         # 0-1, set by Quality Agent
    accepted: bool = False
    caveat: str = ""                   # quality agent note if borderline


# ── DashboardSpec ─────────────────────────────────────────────────────────────

@dataclass
class DashboardSection:
    section_type: str    # "kpi_row" | "chart" | "chart_row" | "table" | "heatmap" | "insight_card"
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DashboardTab:
    id: str
    label: str
    sections: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DashboardSpec:
    title: str
    tabs: list[dict[str, Any]] = field(default_factory=list)
    auto_decisions: list[dict[str, Any]] = field(default_factory=list)  # autonomous mode log

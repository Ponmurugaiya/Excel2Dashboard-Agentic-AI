"""
Chat Memory System
Three-layer memory that keeps context window usage flat regardless of conversation length.

Layers:
  1. short_term  — last N raw exchanges (verbatim, for immediate coherence)
  2. summary     — rolling paragraph updated every SUMMARY_INTERVAL turns
  3. entities    — key facts extracted and updated incrementally

Stored per session_id on disk so it survives server restarts.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.agents.orchestrator import SESSION_DIR
from backend.llm.client import llm_call, llm_json

SHORT_TERM_WINDOW  = 4    # how many recent exchanges to keep verbatim
SUMMARY_INTERVAL   = 4    # summarise every N turns
MAX_ENTITIES       = 20   # cap on tracked entity facts


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class Turn:
    role: str        # "user" | "assistant"
    text: str
    timestamp: float = field(default_factory=time.time)
    action: str = "none"   # "answered_question" | "updated_dashboard"

    def to_dict(self) -> dict:
        return {"role": self.role, "text": self.text,
                "timestamp": self.timestamp, "action": self.action}

    @classmethod
    def from_dict(cls, d: dict) -> "Turn":
        return cls(role=d["role"], text=d["text"],
                   timestamp=d.get("timestamp", 0),
                   action=d.get("action", "none"))


@dataclass
class ChatMemory:
    session_id: str
    all_turns:   list[Turn]   = field(default_factory=list)  # full history (for summary)
    summary:     str          = ""                            # rolling synthesis
    entities:    list[str]    = field(default_factory=list)  # extracted key facts
    turn_count:  int          = 0
    last_summarised_at: int   = 0                            # turn index of last summary

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def short_term(self) -> list[Turn]:
        """Most recent turns — kept verbatim in every prompt."""
        return self.all_turns[-SHORT_TERM_WINDOW:]

    def short_term_text(self) -> str:
        """Format recent turns as a compact dialogue block."""
        lines = []
        for t in self.short_term:
            prefix = "User" if t.role == "user" else "Assistant"
            suffix = f" [{t.action}]" if t.action != "none" else ""
            lines.append(f"{prefix}{suffix}: {t.text[:300]}")
        return "\n".join(lines)

    def context_block(self) -> str:
        """
        Assemble the full memory context for injection into an LLM prompt.
        Structure:
          [Key facts]
          [Summary]
          [Recent conversation]
        """
        parts = []

        if self.entities:
            parts.append("Key facts about this conversation:\n"
                         + "\n".join(f"  • {e}" for e in self.entities[-MAX_ENTITIES:]))

        if self.summary:
            parts.append(f"Conversation summary so far:\n{self.summary}")

        recent = self.short_term_text()
        if recent:
            parts.append(f"Recent exchanges:\n{recent}")

        return "\n\n".join(parts) if parts else ""

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_turn(self, role: str, text: str, action: str = "none"):
        turn = Turn(role=role, text=text, action=action)
        self.all_turns.append(turn)
        self.turn_count += 1

    def should_summarise(self) -> bool:
        unsummarised = self.turn_count - self.last_summarised_at
        return (unsummarised >= SUMMARY_INTERVAL
                and self.turn_count > SHORT_TERM_WINDOW)

    def update_summary_and_entities(self, new_summary: str, new_entities: list[str]):
        self.summary = new_summary
        # Merge new entities, avoid duplicates (case-insensitive)
        existing_lower = {e.lower() for e in self.entities}
        for e in new_entities:
            if e.lower() not in existing_lower and e.strip():
                self.entities.append(e.strip())
                existing_lower.add(e.lower())
        # Cap
        if len(self.entities) > MAX_ENTITIES:
            self.entities = self.entities[-MAX_ENTITIES:]
        self.last_summarised_at = self.turn_count

    # ── Persistence ───────────────────────────────────────────────────────────

    def _path(self) -> Path:
        p = SESSION_DIR / self.session_id / "chat_memory.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def save(self):
        data = {
            "session_id":          self.session_id,
            "all_turns":           [t.to_dict() for t in self.all_turns],
            "summary":             self.summary,
            "entities":            self.entities,
            "turn_count":          self.turn_count,
            "last_summarised_at":  self.last_summarised_at,
        }
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, session_id: str) -> "ChatMemory":
        path = SESSION_DIR / session_id / "chat_memory.json"
        if not path.exists():
            return cls(session_id=session_id)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        m = cls(session_id=session_id)
        m.all_turns           = [Turn.from_dict(t) for t in data.get("all_turns", [])]
        m.summary             = data.get("summary", "")
        m.entities            = data.get("entities", [])
        m.turn_count          = data.get("turn_count", 0)
        m.last_summarised_at  = data.get("last_summarised_at", 0)
        return m


# ── Memory manager ────────────────────────────────────────────────────────────

_memory_cache: dict[str, ChatMemory] = {}


def get_memory(session_id: str) -> ChatMemory:
    """Load from cache or disk."""
    if session_id not in _memory_cache:
        _memory_cache[session_id] = ChatMemory.load(session_id)
    return _memory_cache[session_id]


def update_memory_after_turn(
    memory: ChatMemory,
    user_msg: str,
    assistant_reply: str,
    action: str,
    spec_summary: str,
) -> None:
    """
    Add the new turn to memory and conditionally run the summarisation LLM call.
    Persists to disk.
    """
    memory.add_turn("user",      user_msg)
    memory.add_turn("assistant", assistant_reply, action=action)

    if memory.should_summarise():
        _run_summarisation(memory, spec_summary)

    memory.save()


def _run_summarisation(memory: ChatMemory, spec_summary: str) -> None:
    """
    Call LLM to:
    1. Update the rolling summary
    2. Extract/update key entity facts
    Uses the 'classify' task chain (fast, cheap — llama-3.1-8b).
    """
    # Build a transcript of all turns not yet in the current summary
    start_idx = max(0, memory.last_summarised_at - SHORT_TERM_WINDOW)
    recent_turns = memory.all_turns[start_idx:]
    transcript = "\n".join(
        f"{'User' if t.role == 'user' else 'Assistant'}: {t.text[:200]}"
        for t in recent_turns
    )

    prompt = f"""You are maintaining a memory summary for a BI dashboard chat assistant.

CURRENT SUMMARY (may be empty if this is the first summary):
{memory.summary or '(none yet)'}

DASHBOARD CONTEXT:
{spec_summary[:600]}

RECENT CONVERSATION:
{transcript}

Update the memory. Return JSON with exactly these fields:
{{
  "summary": "A concise paragraph (max 120 words) synthesising everything discussed so far. Focus on: what analyses were discussed, what changes were made to the dashboard, what the user seems to care about most.",
  "new_entities": [
    "Fact 1 about user interests or decisions (max 15 words each)",
    "Fact 2 ...",
    "..."
  ]
}}

Rules for new_entities:
- Only include genuinely useful facts (user preferences, key questions asked, dashboard changes made)
- Max 5 new facts per update
- Do not repeat facts already in the summary
- Return ONLY the JSON, nothing else
"""

    try:
        result = llm_json(
            prompt,
            task="classify",   # fast model — this runs in the background
            system="You are a memory manager. Return only valid JSON.",
            temperature=0.1,
            max_tokens=512,
        )
        new_summary  = result.get("summary", memory.summary)
        new_entities = result.get("new_entities", [])
        if isinstance(new_entities, list):
            memory.update_summary_and_entities(new_summary, new_entities)
    except Exception as e:
        # Summarisation failure is non-fatal — just keep existing memory
        print(f"[Memory] Summarisation failed (non-fatal): {e}")

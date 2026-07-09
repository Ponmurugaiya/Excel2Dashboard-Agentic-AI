"""
Base Agent — every agent inherits from this.
Provides: memory, mode-aware ask_user, logging, LLM helpers (Gemini→Groq fallback).
"""

from __future__ import annotations

from typing import Any

from backend.agents.message_bus import MessageBus
from backend.agents.models import (
    AgentMemory,
    DecisionPoint,
    Message,
    MessageType,
    RunMode,
)


class BaseAgent:
    name: str = "base"
    icon: str = "🤖"

    def __init__(self, bus: MessageBus, mode: RunMode):
        self.bus = bus
        self.mode = mode
        self.memory = AgentMemory()
        self._done = False

    # ── Core loop interface ───────────────────────────────────────────────────

    def is_done(self) -> bool:
        return self._done

    def mark_done(self):
        self._done = True

    # ── Mode-aware user interaction ───────────────────────────────────────────

    async def ask_user(self, dp: DecisionPoint) -> str:
        """
        The single method every agent calls when it needs a human decision.

        Collaborative: posts USER_QUESTION to bus, suspends until response.
        Autonomous:    logs the auto-decision, immediately returns suggestion.

        Returns the chosen option id.
        """
        if self.mode == RunMode.AUTONOMOUS:
            self.bus.post_auto_decision(
                from_agent=self.name,
                context=dp.context,
                decision=dp.suggested_answer,
                reason=dp.reason,
                decision_point_id=dp.id,
            )
            self.memory.remember(
                f"auto_decision:{dp.id}",
                {
                    "context": dp.context,
                    "decision": dp.suggested_answer,
                    "reason": dp.reason,
                },
            )
            return dp.suggested_answer

        else:
            # Collaborative — post question, suspend
            question_msg = Message(
                type=MessageType.USER_QUESTION,
                from_agent=self.name,
                to_agent="user",
                payload={
                    "decision_point": {
                        "id": dp.id,
                        "agent": self.name,
                        "icon": dp.icon,
                        "context": dp.context,
                        "question": dp.question,
                        "suggested_answer": dp.suggested_answer,
                        "reason": dp.reason,
                        "options": [
                            {"id": o.id, "label": o.label, "description": o.description}
                            for o in dp.options
                        ],
                        "impact": dp.impact,
                    }
                },
            )
            response = await self.bus.ask_user_async(question_msg)
            self.memory.remember(
                f"user_decision:{dp.id}",
                {"question": dp.question, "response": response},
            )
            return response

    # ── Logging helpers ───────────────────────────────────────────────────────

    def log(self, text: str, data: dict = None):
        self.bus.post_log(from_agent=self.name, text=text, data=data)
        self.memory.remember(text, data or {})

    def log_error(self, text: str, data: dict = None):
        self.bus.post(Message(
            type=MessageType.ERROR,
            from_agent=self.name,
            to_agent="all",
            payload={"text": text, **(data or {})},
        ))
        self.memory.remember(f"ERROR: {text}", data or {})

    # ── LLM helpers — task-routed, per-model quota fallback ─────────────────

    def _llm_json(self, prompt: str, task: str = "json") -> dict | list:
        """Call LLM and return parsed JSON. Routes by task type."""
        from backend.llm.client import llm_json
        return llm_json(prompt, task=task)

    def _llm_text(self, prompt: str, system: str = None, task: str = "chat") -> str:
        """Call LLM and return raw text. Routes by task type."""
        from backend.llm.client import llm_call
        kwargs = {"task": task}
        if system:
            kwargs["system"] = system
        return llm_call(prompt, **kwargs)

    def _llm_code(self, prompt: str) -> str:
        """Call LLM for code generation. Uses the 'code' task chain."""
        from backend.llm.client import llm_code
        return llm_code(prompt)

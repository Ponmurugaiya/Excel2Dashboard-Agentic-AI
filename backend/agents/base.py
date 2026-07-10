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

        In BOTH modes: posts a rich DECISION_LOG message so the full
        decision (context, options, chosen answer, reason) appears in the logs.

        Returns the chosen option id.
        """
        if self.mode == RunMode.AUTONOMOUS:
            chosen = dp.suggested_answer

            # Post auto-decision (compact, for the ⚡ filter)
            self.bus.post_auto_decision(
                from_agent=self.name,
                context=dp.context,
                decision=chosen,
                reason=dp.reason,
                decision_point_id=dp.id,
            )

            # Post rich decision log (for the Decisions tab)
            self.bus.post(Message(
                type=MessageType.LOG,
                from_agent=self.name,
                to_agent="all",
                payload={
                    "text": f"⚡ Auto-decided: {dp.question}",
                    "log_type": "decision",
                    "decision_point": {
                        "id":               dp.id,
                        "agent":            self.name,
                        "icon":             dp.icon,
                        "mode":             "autonomous",
                        "context":          dp.context,
                        "question":         dp.question,
                        "options":          [{"id": o.id, "label": o.label, "description": o.description} for o in dp.options],
                        "suggested_answer": dp.suggested_answer,
                        "chosen_answer":    chosen,
                        "chosen_label":     next((o.label for o in dp.options if o.id == chosen), chosen),
                        "reason":           dp.reason,
                        "impact":           dp.impact,
                    },
                },
            ))

            self.memory.remember(
                f"auto_decision:{dp.id}",
                {"context": dp.context, "decision": chosen, "reason": dp.reason},
            )
            return chosen

        else:
            # Collaborative — post question, suspend
            question_msg = Message(
                type=MessageType.USER_QUESTION,
                from_agent=self.name,
                to_agent="user",
                payload={
                    "decision_point": {
                        "id":               dp.id,
                        "agent":            self.name,
                        "icon":             dp.icon,
                        "mode":             "collaborative",
                        "context":          dp.context,
                        "question":         dp.question,
                        "suggested_answer": dp.suggested_answer,
                        "reason":           dp.reason,
                        "options": [
                            {"id": o.id, "label": o.label, "description": o.description}
                            for o in dp.options
                        ],
                        "impact": dp.impact,
                    }
                },
            )
            response = await self.bus.ask_user_async(question_msg)

            # Post the resolved decision to the log
            chosen_label = next(
                (o.label for o in dp.options if o.id == response), response
            )
            self.bus.post(Message(
                type=MessageType.LOG,
                from_agent=self.name,
                to_agent="all",
                payload={
                    "text": f"👤 User chose: {chosen_label} — {dp.question[:80]}",
                    "log_type": "decision",
                    "decision_point": {
                        "id":               dp.id,
                        "agent":            self.name,
                        "icon":             dp.icon,
                        "mode":             "collaborative",
                        "context":          dp.context,
                        "question":         dp.question,
                        "options":          [{"id": o.id, "label": o.label, "description": o.description} for o in dp.options],
                        "suggested_answer": dp.suggested_answer,
                        "chosen_answer":    response,
                        "chosen_label":     chosen_label,
                        "reason":           dp.reason,
                        "impact":           dp.impact,
                    },
                },
            ))

            self.memory.remember(
                f"user_decision:{dp.id}",
                {"question": dp.question, "response": response, "chosen_label": chosen_label},
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

    # ── LLM helpers — task-routed, per-model quota fallback ──────────────────
    # Sync versions for simple one-off calls.
    # Async versions run the blocking HTTP call in a thread pool so concurrent
    # agent tasks don't stall the event loop waiting for each other.

    def _llm_json(self, prompt: str, task: str = "json") -> dict | list:
        from backend.llm.client import llm_json
        return llm_json(prompt, task=task)

    async def _llm_json_async(self, prompt: str, task: str = "json") -> dict | list:
        import asyncio as _aio
        from backend.llm.client import llm_json
        return await _aio.to_thread(llm_json, prompt, task=task)

    def _llm_text(self, prompt: str, system: str = None, task: str = "chat") -> str:
        from backend.llm.client import llm_call
        kw: dict = {"task": task}
        if system:
            kw["system"] = system
        return llm_call(prompt, **kw)

    async def _llm_text_async(self, prompt: str, system: str = None, task: str = "chat") -> str:
        import asyncio as _aio
        from backend.llm.client import llm_call
        kw: dict = {"task": task}
        if system:
            kw["system"] = system
        return await _aio.to_thread(llm_call, prompt, **kw)

    def _llm_code(self, prompt: str) -> str:
        from backend.llm.client import llm_code
        return llm_code(prompt)

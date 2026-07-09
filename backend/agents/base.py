"""
Base Agent — every agent inherits from this.
Provides: memory, mode-aware ask_user, logging, message bus access.
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

    # ── LLM helper (shared config) ────────────────────────────────────────────

    def _get_llm(self):
        import os
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not set")

        genai.configure(api_key=api_key)

        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=(
                "You are a senior data scientist. "
                "Respond with valid JSON only — no markdown, no code fences, no extra text."
            ),
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )

    def _llm_json(self, prompt: str) -> dict | list:
        """Call LLM and parse JSON response with fallback strategies."""
        import json
        import re

        model = self._get_llm()
        raw = model.generate_content(prompt).text.strip()

        # Strategy 1: direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Strategy 2: strip markdown fences
        clean = re.sub(r"```(?:json)?", "", raw).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        # Strategy 3: extract first {...} or [...] block
        match = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse LLM JSON response. Preview: {raw[:300]}")

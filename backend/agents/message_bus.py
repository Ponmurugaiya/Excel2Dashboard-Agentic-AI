"""
Message Bus — shared communication channel for all agents.
Agents post messages here. The orchestrator reads and routes them.
Supports pause/resume for collaborative mode user questions.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any, Callable

from backend.agents.models import Message, MessageType


class MessageBus:
    def __init__(self):
        self._messages: list[Message] = []
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._pending_user_question: Message | None = None
        self._user_response_event: asyncio.Event = asyncio.Event()
        self._user_response_value: str | None = None
        # ── User hints — isolated from agent memory ───────────────────────────
        # Plain strings written by the user during the analysis run.
        # Only read at explicit injection points (Strategist, Architect).
        # Never written into any AgentMemory or MessageBus._messages.
        self._user_hints: list[str] = []

    # ── Post ─────────────────────────────────────────────────────────────────

    def post(self, message: Message) -> None:
        self._messages.append(message)
        # Notify subscribers
        for cb in self._subscribers.get(message.to_agent, []):
            cb(message)
        for cb in self._subscribers.get("all", []):
            cb(message)

    def post_log(self, from_agent: str, text: str, data: dict = None) -> None:
        self.post(Message(
            type=MessageType.LOG,
            from_agent=from_agent,
            to_agent="all",
            payload={"text": text, **(data or {})},
        ))

    def post_auto_decision(
        self,
        from_agent: str,
        context: str,
        decision: str,
        reason: str,
        decision_point_id: str = "",
    ) -> None:
        self.post(Message(
            type=MessageType.AUTO_DECISION,
            from_agent=from_agent,
            to_agent="all",
            payload={
                "context": context,
                "decision": decision,
                "reason": reason,
                "decision_point_id": decision_point_id,
            },
        ))

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_all(self) -> list[Message]:
        return list(self._messages)

    def get_since(self, since_timestamp: float) -> list[Message]:
        return [m for m in self._messages if m.timestamp > since_timestamp]

    def get_for_agent(self, agent_name: str) -> list[Message]:
        return [
            m for m in self._messages
            if m.to_agent in (agent_name, "all")
        ]

    def get_by_type(self, msg_type: MessageType) -> list[Message]:
        return [m for m in self._messages if m.type == msg_type]

    def get_auto_decisions(self) -> list[dict]:
        return [
            m.payload for m in self._messages
            if m.type == MessageType.AUTO_DECISION
        ]

    # ── Collaborative mode — pause/resume ────────────────────────────────────

    async def ask_user_async(self, question_message: Message) -> str:
        """
        Post a USER_QUESTION message and suspend until the user responds.
        Returns the user's chosen option id.
        """
        self._pending_user_question = question_message
        self._user_response_event.clear()
        self.post(question_message)

        # Wait for user response (set by resolve_user_question)
        await self._user_response_event.wait()
        return self._user_response_value

    def resolve_user_question(self, response: str) -> None:
        """Called by the API layer when the user submits their answer."""
        self._user_response_value = response
        self._pending_user_question = None
        self._user_response_event.set()

    def get_pending_question(self) -> Message | None:
        return self._pending_user_question

    def is_waiting_for_user(self) -> bool:
        return self._pending_user_question is not None

    # ── User hints ────────────────────────────────────────────────────────────
    # Hints are intentionally NOT posted to _messages so they never appear in
    # agent decision logs or SSE streams as agent messages.  They are only
    # surfaced at the two injection points: Strategist.plan() and
    # ArchitectAgent.design().  The API layer also broadcasts a system log so
    # the hint is visible in the agent feed as a user action, not an agent action.

    def add_hint(self, text: str) -> None:
        """Store a user hint. Thread-safe for concurrent async tasks."""
        stripped = text.strip()
        if stripped:
            self._user_hints.append(stripped)

    def get_hints(self) -> list[str]:
        """Return a snapshot of all hints received so far."""
        return list(self._user_hints)

    def has_hints(self) -> bool:
        return bool(self._user_hints)

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def subscribe(self, agent_name: str, callback: Callable) -> None:
        self._subscribers[agent_name].append(callback)

    # ── Serialise for SSE streaming ───────────────────────────────────────────

    def messages_as_dicts(self, since: float = 0) -> list[dict]:
        return [m.to_dict() for m in self.get_since(since)]

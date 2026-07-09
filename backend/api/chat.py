"""
Dashboard Chat API
POST /chat/{session_id}  — send a message, get a response that may modify the dashboard spec

Memory system:
  - Short-term: last 4 exchanges verbatim (immediate coherence)
  - Rolling summary: updated every 4 turns via LLM (llama-3.1-8b, fast)
  - Entity memory: key facts extracted and accumulated

Single LLM call per user message — classify + act in one shot.
Gemini → Groq multi-model fallback via unified client.
Falls back to disk when session not in memory (handles server restarts).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.orchestrator import SESSION_DIR, get_session
from backend.chat.memory import get_memory, update_memory_after_turn
from backend.llm.client import llm_json

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    updated_spec: dict | None = None
    action: str = "none"
    memory_snapshot: dict | None = None   # optional debug info


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/chat/{session_id}")
async def chat(session_id: str, req: ChatRequest) -> ChatResponse:
    spec, session = _load_spec(session_id)
    if spec is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Dashboard not found. The server may have restarted — "
                "please re-upload your file to start a new analysis."
            ),
        )

    memory       = get_memory(session_id)
    spec_summary = _summarise_spec(spec)

    try:
        reply, updated_spec, action = _process_chat(
            req.message, spec_summary, spec, memory
        )
    except Exception as e:
        err = str(e)
        if "quota" in err.lower() or "exhausted" in err.lower() or "rate" in err.lower():
            raise HTTPException(
                status_code=429,
                detail="LLM rate limit reached. Please wait a moment and try again.",
            )
        raise HTTPException(status_code=500, detail=f"LLM error: {err[:200]}")

    # Update memory (persists to disk, may trigger background summarisation)
    update_memory_after_turn(memory, req.message, reply, action, spec_summary)

    # Persist updated spec if dashboard was modified
    if updated_spec:
        if session:
            session.dashboard_spec = updated_spec
            session.save_spec()
        else:
            spec_path = SESSION_DIR / session_id / "dashboard_spec.json"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            with open(spec_path, "w", encoding="utf-8") as f:
                json.dump(updated_spec, f, indent=2, default=str)

        return ChatResponse(
            reply=reply,
            updated_spec=updated_spec,
            action="updated_dashboard",
        )

    return ChatResponse(reply=reply, action=action)


# ── GET memory snapshot (debug / frontend display) ────────────────────────────

@router.get("/chat/{session_id}/memory")
async def get_memory_snapshot(session_id: str):
    memory = get_memory(session_id)
    return {
        "turn_count":  memory.turn_count,
        "summary":     memory.summary,
        "entities":    memory.entities,
        "recent_turns": [t.to_dict() for t in memory.short_term],
    }


# ── Core LLM processing ───────────────────────────────────────────────────────

def _process_chat(
    message: str,
    spec_summary: str,
    full_spec: dict,
    memory,
) -> tuple[str, dict | None, str]:
    """
    Single LLM call that classifies intent + acts.
    Memory context is injected into the prompt.
    Returns: (reply, updated_spec_or_None, action_str)
    """

    memory_context = memory.context_block()

    prompt = f"""You are a BI dashboard assistant with memory of this conversation.

{f'CONVERSATION MEMORY:{chr(10)}{memory_context}{chr(10)}' if memory_context else ''}
CURRENT DASHBOARD:
{spec_summary}

USER MESSAGE: "{message}"

Decide what to do and respond with a JSON object.

If the user is asking a QUESTION (wants to understand data, follow up on something, etc.):
{{
  "intent": "question",
  "reply": "<answer under 120 words — reference specific numbers, and acknowledge prior context if relevant>"
}}

If the user wants to MODIFY the dashboard (add/remove/change/rename):
{{
  "intent": "modify",
  "action": "add_insight_card" | "rename_tab" | "remove_section" | "reorder_tabs" | "unsupported",
  "target_tab_id": "<tab id or null>",
  "params": {{
    // add_insight_card: "text" (use real numbers from dashboard), "recommendation", "severity"
    // rename_tab: "old_label", "new_label"
    // remove_section: "title" (partial match), "section_type"
    // reorder_tabs: "order" (list of tab ids)
  }},
  "reply": "<one sentence confirming the change>"
}}

Rules:
- Use memory context to give continuity (e.g. if user previously asked about UK, acknowledge it)
- For add_insight_card: write specific text using ACTUAL numbers from the dashboard
- If unsure of intent, classify as "question"
- Return ONLY the JSON object
"""

    result = llm_json(
        prompt,
        task="json",
        system="You are a BI dashboard assistant with persistent memory. Return only valid JSON.",
        temperature=0.1,
        max_tokens=1024,
    )

    intent = result.get("intent", "question")
    reply  = result.get("reply", "")

    if intent == "modify":
        action_type = result.get("action", "unsupported")
        if action_type == "unsupported":
            return (
                result.get("reply",
                    "I can't make that change automatically. "
                    "Supported: add insight card, rename tab, remove section, reorder tabs."),
                None,
                "answered_question",
            )

        updated_spec, err = _apply_patch(full_spec, result)
        if err:
            return err, None, "answered_question"

        return reply or "Dashboard updated.", updated_spec, "updated_dashboard"

    return reply or "I couldn't generate an answer. Please try rephrasing.", None, "answered_question"


# ── Spec helpers ──────────────────────────────────────────────────────────────

def _load_spec(session_id: str) -> tuple[dict | None, object | None]:
    session = get_session(session_id)
    if session and session.dashboard_spec:
        return session.dashboard_spec, session

    spec_path = SESSION_DIR / session_id / "dashboard_spec.json"
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            return json.load(f), None

    return None, None


def _summarise_spec(spec: dict) -> str:
    lines = [f"Dashboard: {spec.get('title', 'Unknown')}"]
    for tab in spec.get("tabs", []):
        lines.append(f"\nTab [{tab.get('id')}]: {tab['label']}")
        for section in tab.get("sections", []):
            _summarise_section(section, lines, indent=2)

    insights = spec.get("all_insights", [])
    if insights:
        lines.append("\nKey insights:")
        for ins in insights[:4]:
            lines.append(f"  [{ins.get('severity','?')}] {ins.get('text','')[:150]}")
            if ins.get("recommendation"):
                lines.append(f"    Recommendation: {ins['recommendation'][:100]}")

    return "\n".join(lines)


def _summarise_section(section: dict, lines: list, indent: int):
    pad = " " * indent
    st = section.get("section_type", "")

    if st == "insight_card":
        lines.append(f"{pad}- insight_card [{section.get('severity','?')}]: {section.get('text','')[:120]}")
    elif st == "kpi_row":
        kpis = [f"{k.get('label')}={k.get('value')}" for k in section.get("items", [])]
        lines.append(f"{pad}- kpi_row: {', '.join(kpis)}")
    elif st == "chart":
        cs = section.get("chart_spec", {}) or {}
        chart_type = cs.get("data", [{}])[0].get("type", "") if cs.get("data") else ""
        lines.append(f"{pad}- chart ({chart_type}): {section.get('title', '')}")
        if section.get("insight"):
            lines.append(f"{pad}  insight: {section['insight'][:100]}")
    elif st == "heatmap":
        lines.append(f"{pad}- heatmap: {section.get('title', '')}")
    elif st == "chart_row":
        lines.append(f"{pad}- chart_row:")
        for item in section.get("items", []):
            _summarise_section(item, lines, indent + 2)
    elif st == "table":
        segs = [s.get("segment", "") for s in section.get("segment_summary", [])]
        lines.append(f"{pad}- table: {section.get('title', '')} (segments: {segs})")


# ── Patch applicator ──────────────────────────────────────────────────────────

def _apply_patch(spec: dict, patch: dict) -> tuple[dict, str | None]:
    spec           = copy.deepcopy(spec)
    action         = patch.get("action", "unsupported")
    params         = patch.get("params", {}) or {}
    target_tab_id  = patch.get("target_tab_id")

    def get_tab(tab_id):
        if tab_id:
            for t in spec.get("tabs", []):
                if t.get("id") == tab_id or t.get("label", "").lower() == str(tab_id).lower():
                    return t
        return spec["tabs"][0] if spec.get("tabs") else None

    if action == "add_insight_card":
        text = params.get("text", "")
        if not text:
            return spec, "The insight text is empty — please try again with more detail."
        tab = get_tab(target_tab_id)
        if not tab:
            return spec, "No tab found to add the insight card to."
        card = {
            "section_type":  "insight_card",
            "severity":      params.get("severity", "medium"),
            "text":          text,
            "recommendation": params.get("recommendation", ""),
        }
        tab["sections"].insert(0, card)
        spec.setdefault("all_insights", []).insert(0, {
            "text":           text,
            "recommendation": params.get("recommendation", ""),
            "severity":       params.get("severity", "medium"),
        })
        return spec, None

    elif action == "rename_tab":
        old_label = params.get("old_label", "")
        new_label = params.get("new_label", "")
        if not new_label:
            return spec, "Please provide the new tab name."
        for tab in spec.get("tabs", []):
            if (tab.get("label", "").lower() == old_label.lower()
                    or tab.get("id") == target_tab_id):
                tab["label"] = new_label
                return spec, None
        return spec, f"Couldn't find a tab named '{old_label}'."

    elif action == "remove_section":
        section_title = params.get("title", "").lower()
        section_type  = params.get("section_type", "").lower()
        removed = False
        for tab in spec.get("tabs", []):
            new_sections = []
            for s in tab.get("sections", []):
                t_match = section_type and s.get("section_type", "").lower() == section_type
                n_match = section_title and section_title in s.get("title", "").lower()
                if t_match or n_match:
                    removed = True
                else:
                    new_sections.append(s)
            tab["sections"] = new_sections
        if not removed:
            return spec, "Couldn't find the section to remove. Try being more specific."
        return spec, None

    elif action == "reorder_tabs":
        order = params.get("order", [])
        if order:
            tab_map = {t.get("id"): t for t in spec.get("tabs", [])}
            reordered = [tab_map[tid] for tid in order if tid in tab_map]
            mentioned = set(order)
            for t in spec.get("tabs", []):
                if t.get("id") not in mentioned:
                    reordered.append(t)
            spec["tabs"] = reordered
        return spec, None

    return spec, (
        "I understood your request but can't apply that change automatically. "
        "Try: add insight card, rename tab, remove section, reorder tabs."
    )

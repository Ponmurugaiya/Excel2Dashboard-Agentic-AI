"""
Analyse API
POST /analyse        — start a new analysis session
GET  /analyse/{id}/events  — SSE stream of agent messages
POST /analyse/{id}/answer  — send user's answer to a waiting agent
GET  /analyse/{id}/status  — poll session status + dashboard spec
GET  /download/{id}/{name} — download a generated CSV
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from backend.agents.models import RunMode
from backend.agents.orchestrator import create_session, get_session, run_pipeline


router = APIRouter()


# ── Request/Response models ────────────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    file_path: str     # absolute path saved by /upload
    mode: str = "collaborative"   # "collaborative" | "autonomous"


class AnswerRequest(BaseModel):
    decision_point_id: str
    answer: str        # the chosen option id


class HintRequest(BaseModel):
    text: str          # free-text user suggestion/preference


# ── POST /analyse ─────────────────────────────────────────────────────────────

@router.post("/analyse")
async def start_analysis(req: AnalyseRequest, background_tasks: BackgroundTasks):
    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")

    try:
        run_mode = RunMode(req.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode '{req.mode}'. Use 'collaborative' or 'autonomous'.")

    session = create_session(str(path), run_mode)

    # Run pipeline in background so we can return immediately
    background_tasks.add_task(_run_pipeline_bg, session)

    return {
        "session_id": session.session_id,
        "mode": run_mode.value,
        "status": "started",
        "events_url": f"/analyse/{session.session_id}/events",
        "status_url": f"/analyse/{session.session_id}/status",
    }


async def _run_pipeline_bg(session):
    """Wrapper to run pipeline and log any unhandled exceptions."""
    try:
        await run_pipeline(session)
    except Exception as e:
        session.status = "error"
        session.error = str(e)


# ── GET /analyse/{id}/events — SSE stream ─────────────────────────────────────

@router.get("/analyse/{session_id}/events")
async def stream_events(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        last_ts = 0.0
        while True:
            new_events = session.get_events(since=last_ts)
            for event in new_events:
                last_ts = max(last_ts, event["timestamp"])
                data = json.dumps(event)
                yield f"data: {data}\n\n"

            # If pipeline done or errored, send final status and close
            if session.status in ("done", "error"):
                final = json.dumps({
                    "type": "session_status",
                    "status": session.status,
                    "error": session.error,
                })
                yield f"data: {final}\n\n"
                break

            # If waiting for user, send question prompt
            if session.is_waiting_for_user():
                q = session.get_pending_question()
                if q:
                    pending = json.dumps({"type": "pending_question", "question": q})
                    yield f"data: {pending}\n\n"

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── GET /analyse/{id}/status ──────────────────────────────────────────────────

@router.get("/analyse/{session_id}/status")
async def get_status(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response = {
        "session_id": session_id,
        "status": session.status,
        "mode": session.mode.value,
        "waiting_for_user": session.is_waiting_for_user(),
        "pending_question": session.get_pending_question(),
        "error": session.error,
    }

    if session.status == "done" and session.dashboard_spec:
        response["dashboard"] = session.dashboard_spec
        response["downloads"] = _list_downloads(session_id)

    return response


# ── POST /analyse/{id}/answer ─────────────────────────────────────────────────

@router.post("/analyse/{session_id}/answer")
async def submit_answer(session_id: str, req: AnswerRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.is_waiting_for_user():
        raise HTTPException(status_code=409, detail="Session is not waiting for a user answer")

    session.resolve_user_answer(req.answer)
    return {"status": "ok", "answer_received": req.answer}


# ── POST /analyse/{id}/hint ───────────────────────────────────────────────────

@router.post("/analyse/{session_id}/hint")
async def submit_hint(session_id: str, req: HintRequest):
    """
    Accept a free-text user hint during (or before) pipeline execution.

    The hint is stored on the MessageBus in an isolated _user_hints list —
    completely separate from agent memory and the SSE message stream.
    Agents read it only at two safe injection points:
      1. Strategist.plan()  — shapes which analyses are prioritised
      2. ArchitectAgent.design() — shapes tab naming and layout narrative

    A system log is also posted so the hint appears visibly in the agent
    progress feed as a "💬 User hint" entry.
    """
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Hint text cannot be empty")

    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Hint too long (max 500 characters)")

    # Store on bus — isolated from agent memory
    session.bus.add_hint(text)

    # Post a visible system log so it appears in the agent feed
    session.bus.post_log(
        "system",
        f"💬 User hint: {text}",
        {"hint_type": "user_suggestion"},
    )

    return {
        "status": "ok",
        "hint_received": text,
        "hint_count": len(session.bus.get_hints()),
        "pipeline_status": session.status,
    }


# ── GET /download/{session_id}/{name} ─────────────────────────────────────────

@router.get("/download/{session_id}/{name}")
async def download_csv(session_id: str, name: str):
    from backend.agents.orchestrator import SESSION_DIR

    csv_path = SESSION_DIR / session_id / f"{name}.csv"
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File '{name}.csv' not found for session {session_id}",
        )

    return FileResponse(
        path=str(csv_path),
        filename=f"{name}.csv",
        media_type="text/csv",
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _list_downloads(session_id: str) -> list[dict]:
    from backend.agents.orchestrator import SESSION_DIR

    session_path = SESSION_DIR / session_id
    if not session_path.exists():
        return []

    files = []
    for f in session_path.glob("*.csv"):
        files.append({
            "name": f.stem,
            "url": f"/download/{session_id}/{f.stem}",
            "filename": f.name,
        })
    return files

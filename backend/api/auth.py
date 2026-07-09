"""
Auth API — JWT-based login/register + saved dashboards.
Uses SQLite (no external ORM — just sqlite3).
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

DB_PATH   = Path("storage/users.db")
SECRET    = os.getenv("JWT_SECRET", "change-me-in-production-please")
ALGORITHM = "HS256"
TOKEN_TTL = 60 * 60 * 24 * 30  # 30 days

router   = APIRouter(prefix="/auth")
security = HTTPBearer(auto_error=False)


# ── DB init ───────────────────────────────────────────────────────────────────

def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_dashboards (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            file_name TEXT NOT NULL,
            session_id TEXT NOT NULL,
            spec_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    return conn


# ── Models ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class SaveDashboardRequest(BaseModel):
    title: str
    file_name: str
    session_id: str
    spec_json: dict


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": int(time.time()) + TOKEN_TTL},
        SECRET,
        algorithm=ALGORITHM,
    )

def _decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    if not creds:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _decode_token(creds.credentials)

def get_optional_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> str | None:
    if not creds:
        return None
    try:
        return _decode_token(creds.credentials)
    except HTTPException:
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    user_id = uuid.uuid4().hex

    conn = _db()
    try:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?,?,?,?)",
            (user_id, req.email.lower(), hashed, time.time()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    finally:
        conn.close()

    return {"token": _create_token(user_id), "user_id": user_id}


@router.post("/login")
def login(req: LoginRequest):
    conn = _db()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (req.email.lower(),)
    ).fetchone()
    conn.close()

    if not row or not bcrypt.checkpw(req.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"token": _create_token(row["id"]), "user_id": row["id"]}


@router.post("/dashboards", status_code=201)
def save_dashboard(req: SaveDashboardRequest, user_id: str = Depends(get_current_user)):
    dash_id = uuid.uuid4().hex
    conn = _db()
    conn.execute(
        """INSERT INTO saved_dashboards
           (id, user_id, title, file_name, session_id, spec_json, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (dash_id, user_id, req.title, req.file_name,
         req.session_id, json.dumps(req.spec_json), time.time()),
    )
    conn.commit()
    conn.close()
    return {"id": dash_id, "title": req.title}


@router.get("/dashboards")
def list_dashboards(user_id: str = Depends(get_current_user)):
    conn = _db()
    rows = conn.execute(
        "SELECT id, title, file_name, session_id, created_at FROM saved_dashboards "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/dashboards/{dash_id}")
def load_dashboard(dash_id: str, user_id: str = Depends(get_current_user)):
    conn = _db()
    row = conn.execute(
        "SELECT * FROM saved_dashboards WHERE id = ? AND user_id = ?",
        (dash_id, user_id),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    d = dict(row)
    d["spec_json"] = json.loads(d["spec_json"])
    return d


@router.delete("/dashboards/{dash_id}", status_code=204)
def delete_dashboard(dash_id: str, user_id: str = Depends(get_current_user)):
    conn = _db()
    conn.execute(
        "DELETE FROM saved_dashboards WHERE id = ? AND user_id = ?",
        (dash_id, user_id),
    )
    conn.commit()
    conn.close()

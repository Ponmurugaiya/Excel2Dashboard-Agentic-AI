"""
Upload API
FastAPI app entry point.
POST /upload  → saves file, returns file_path for use with /analyse
Supports Excel (.xlsx, .xls, .xlsm) and CSV (.csv).
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.parser.file_parser import SUPPORTED_EXTENSIONS
from backend.api.analyse import router as analyse_router
from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI BI Dashboard Builder",
    description="Upload a data file and get an AI-powered, agent-designed dashboard.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(analyse_router)
app.include_router(auth_router)
app.include_router(chat_router)

UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = SUPPORTED_EXTENSIONS
MAX_FILE_SIZE_MB = 50


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/health/llm")
def llm_health():
    """Check which LLM models are configured and which is active per task."""
    from backend.llm.client import provider_status, task_chain_status
    return {
        "models":  provider_status(),
        "routing": task_chain_status(),
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accept a file upload, save it, return the file_path.
    Client then calls POST /analyse with this path to start the agent pipeline.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        readable = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted: {readable}.",
        )

    content = await file.read()

    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.",
        )

    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    upload_path = UPLOAD_DIR / unique_name
    upload_path.write_bytes(content)

    return JSONResponse(content={
        "file_name": file.filename,
        "file_path": str(upload_path),
        "size_mb": round(size_mb, 2),
    })

"""
Upload API — Phase 1
FastAPI endpoint: POST /upload → returns dashboard JSON.
Supports Excel (.xlsx, .xls, .xlsm) and CSV (.csv).
"""

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.dashboard.dashboard_builder import build_dashboard, save_dashboard
from backend.parser.file_parser import SUPPORTED_EXTENSIONS

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI BI Dashboard Builder",
    description="Upload an Excel or CSV file and receive an auto-generated dashboard.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("storage/uploads")
OUTPUT_DIR = Path("storage/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = SUPPORTED_EXTENSIONS   # kept in one place: file_parser.py
MAX_FILE_SIZE_MB = 50


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accept an Excel or CSV upload, run the full pipeline, return dashboard JSON.
    """
    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        readable = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted formats: {readable}.",
        )

    # Save upload to disk
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    upload_path = UPLOAD_DIR / unique_name

    content = await file.read()

    # Validate size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.",
        )

    upload_path.write_bytes(content)

    # Run pipeline
    try:
        dashboard = build_dashboard(str(upload_path))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {str(e)}",
        )

    # Persist output JSON
    output_path = OUTPUT_DIR / f"{upload_path.stem}_dashboard.json"
    save_dashboard(dashboard, str(output_path))

    return JSONResponse(content=dashboard)

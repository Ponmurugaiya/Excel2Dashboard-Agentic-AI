"""
Entry point — run with:
    uvicorn main:app --reload --port 8000
"""

from dotenv import load_dotenv

load_dotenv()  # load .env before any module reads os.getenv()

from backend.api.upload import app  # noqa: F401 — re-exported for uvicorn

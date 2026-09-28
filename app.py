"""
app.py — Hugging Face Spaces entry point.

Hugging Face Spaces auto-detects this file and launches it with uvicorn on
port 7860. We simply re-export the FastAPI `app` object from api/main.py so
all existing routers, lifespan, and middleware are preserved exactly as-is.

The Space must be configured as:
  SDK: Docker   (see README.md for the HF Space card metadata)

Or alternatively as a FastAPI app, which HF will serve on port 7860.
"""

import sys
from pathlib import Path

# Ensure the project's src/ package is importable (for ddi_scorer)
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Re-export the FastAPI app — Hugging Face Spaces will serve this
from api.main import app  # noqa: F401, E402

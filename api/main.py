"""
api/main.py
FastAPI application entry point for the Dental DDI Risk Scorer.

Loads scores.parquet and dental_drugs.csv once on startup and makes them
available to all routers via app.state.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import check, drugs

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SCORES_PATH = ROOT / "data" / "processed" / "scores.parquet"
DENTAL_PATH = ROOT / "data" / "reference" / "dental_drugs.csv"

log = logging.getLogger(__name__)


# ── Lifespan — load data once at startup ─────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    log.info("Loading scores from %s …", SCORES_PATH)
    if not SCORES_PATH.exists():
        log.warning(
            "scores.parquet not found — run `make score` to generate it. "
            "POST /check will return 503 until it exists."
        )
        app.state.scores = None
    else:
        app.state.scores = pd.read_parquet(SCORES_PATH)
        log.info("Scores loaded: %s pairs", f"{len(app.state.scores):,}")

    log.info("Loading dental drug list from %s …", DENTAL_PATH)
    app.state.dental_drugs = pd.read_csv(DENTAL_PATH)
    log.info("Dental drugs loaded: %d drugs", len(app.state.dental_drugs))

    yield  # app is running

    # ── Shutdown ──────────────────────────────────────────────────────────────
    log.info("Shutting down — releasing data.")
    app.state.scores = None
    app.state.dental_drugs = None


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Dental DDI Risk Scorer",
    description=(
        "Drug-drug interaction risk scoring tool for dental prescribers. "
        "Input a patient's current medication list and receive ranked interaction "
        "risks for the drugs a dentist would prescribe, powered by TWOSIDES "
        "pharmacovigilance data.\n\n"
        "> **Disclaimer:** For educational purposes only. "
        "Not for clinical decision support."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow all origins for now (tighten before production) ──────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(check.router, tags=["Interactions"])
app.include_router(drugs.router, tags=["Reference data"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Meta"])
async def health():
    return {
        "status": "ok",
        "scores_loaded": app.state.scores is not None,
        "n_pairs": len(app.state.scores) if app.state.scores is not None else 0,
        "n_dental_drugs": len(app.state.dental_drugs),
    }

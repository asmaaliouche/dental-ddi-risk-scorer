"""
scripts/smoke_test.py
---------------------
Quick integration smoke test for the Dental DDI Risk Scorer API.
Exercises all three endpoints (/health, /dental-drugs, /patient-drugs, /check)
and logs a structured pass/fail report to stdout.

Intended for local development validation — NOT a replacement for pytest.

Usage:
    # With the API server running on port 8000:
    poetry run python scripts/smoke_test.py

    # Against a deployed environment:
    API_BASE_URL=https://your-api.railway.app poetry run python scripts/smoke_test.py
"""

from __future__ import annotations

import logging
import os
import sys

import httpx

# ── Configuration ─────────────────────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")

# Test payload: two common chronic medications against our dental drug list
TEST_PATIENT_DRUGS = ["warfarin", "atorvastatin"]

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Test helpers ──────────────────────────────────────────────────────────────


def _assert(condition: bool, label: str, detail: str = "") -> bool:
    """Log a PASS/FAIL line. Returns True on pass."""
    if condition:
        log.info("  ✅  PASS  %s  %s", label, detail)
    else:
        log.error("  ❌  FAIL  %s  %s", label, detail)
    return condition


# ── Test cases ────────────────────────────────────────────────────────────────


def test_health(client: httpx.Client) -> bool:
    """GET /health — server is up and data is loaded."""
    log.info("── /health ──────────────────────────────────────────────────")
    r = client.get("/health")
    ok = True
    ok &= _assert(r.status_code == 200, "HTTP 200", f"(got {r.status_code})")
    body = r.json()
    ok &= _assert(body.get("status") == "ok", "status == ok")
    ok &= _assert(body.get("scores_loaded") is True, "scores_loaded is True")
    ok &= _assert(body.get("n_pairs", 0) > 0, "n_pairs > 0", f"({body.get('n_pairs')} pairs)")
    ok &= _assert(
        body.get("n_dental_drugs", 0) > 0,
        "n_dental_drugs > 0",
        f"({body.get('n_dental_drugs')} drugs)",
    )
    return ok


def test_dental_drugs(client: httpx.Client) -> bool:
    """GET /dental-drugs — returns curated dental drug list."""
    log.info("── /dental-drugs ────────────────────────────────────────────")
    r = client.get("/dental-drugs")
    ok = True
    ok &= _assert(r.status_code == 200, "HTTP 200", f"(got {r.status_code})")
    body = r.json()
    ok &= _assert(
        body.get("total", 0) >= 20, "at least 20 dental drugs", f"(got {body.get('total')})"
    )

    if body.get("drugs"):
        first = body["drugs"][0]
        ok &= _assert("name" in first, "drug has 'name' field")
        ok &= _assert("category" in first, "drug has 'category' field")
        log.info("  Sample: %s | %s", first.get("name"), first.get("category"))

    return ok


def test_patient_drugs(client: httpx.Client) -> bool:
    """GET /patient-drugs — returns autocomplete index."""
    log.info("── /patient-drugs ───────────────────────────────────────────")
    r = client.get("/patient-drugs")
    ok = True
    ok &= _assert(r.status_code == 200, "HTTP 200", f"(got {r.status_code})")
    body = r.json()
    ok &= _assert(
        body.get("total", 0) > 1000, "more than 1,000 patient drugs", f"(got {body.get('total')})"
    )
    ok &= _assert("warfarin" in body.get("drugs", []), "'warfarin' is in the index")
    return ok


def test_check(client: httpx.Client) -> bool:
    """POST /check — interaction results for a known high-risk combination."""
    log.info(
        "── POST /check (%s) ─────────────────────────────────────────",
        ", ".join(TEST_PATIENT_DRUGS),
    )
    r = client.post("/check", json={"patient_drugs": TEST_PATIENT_DRUGS})
    ok = True
    ok &= _assert(r.status_code == 200, "HTTP 200", f"(got {r.status_code})")
    body = r.json()
    total = body.get("total_interactions", 0)
    ok &= _assert(total > 0, "at least 1 interaction found", f"({total} found)")
    ok &= _assert(len(body.get("interactions", [])) == total, "interaction count matches")

    if body.get("interactions"):
        top = body["interactions"][0]
        ok &= _assert("risk_score" in top, "risk_score present")
        ok &= _assert("severity_bin" in top, "severity_bin present")
        ok &= _assert(
            top.get("severity_bin") in {"major", "moderate", "minor"}, "valid severity_bin"
        )
        log.info(
            "  Top interaction: [%s] score=%.1f  %s ↔ %s",
            top.get("severity_bin"),
            top.get("risk_score", 0),
            top.get("dental_drug_display"),
            top.get("patient_drug"),
        )

    return ok


def test_check_unknown_drug(client: httpx.Client) -> bool:
    """POST /check — unknown drug returns empty interactions and not_found list."""
    log.info("── POST /check (unknown drug) ───────────────────────────────")
    r = client.post("/check", json={"patient_drugs": ["zxcvbnm_totally_fake_drug"]})
    ok = True
    ok &= _assert(r.status_code == 200, "HTTP 200", f"(got {r.status_code})")
    body = r.json()
    ok &= _assert(body.get("total_interactions", -1) == 0, "0 interactions for unknown drug")
    ok &= _assert(
        "zxcvbnm_totally_fake_drug" in body.get("patient_drugs_not_found", []),
        "drug appears in not_found list",
    )
    return ok


# ── Runner ────────────────────────────────────────────────────────────────────


def main() -> None:
    log.info("Dental DDI Risk Scorer — API Smoke Test")
    log.info("Target: %s", API_BASE)
    log.info("=" * 60)

    passed = 0
    failed = 0

    tests = [
        test_health,
        test_dental_drugs,
        test_patient_drugs,
        test_check,
        test_check_unknown_drug,
    ]

    try:
        with httpx.Client(base_url=API_BASE, timeout=30.0) as client:
            for test_fn in tests:
                result = test_fn(client)
                if result:
                    passed += 1
                else:
                    failed += 1
    except httpx.ConnectError:
        log.error(
            "Cannot reach API at %s. "
            "Start the server with: poetry run uvicorn api.main:app --reload --port 8000",
            API_BASE,
        )
        sys.exit(1)

    log.info("=" * 60)
    log.info("Results: %d passed, %d failed", passed, failed)

    if failed > 0:
        log.error("Smoke test FAILED — %d test(s) did not pass.", failed)
        sys.exit(1)
    else:
        log.info("All smoke tests passed ✅")


if __name__ == "__main__":
    main()

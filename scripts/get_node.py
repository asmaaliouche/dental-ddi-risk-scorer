"""
scripts/get_node.py
-------------------
Downloads and extracts a portable (standalone) Node.js binary for Windows
into the project's `.node/` directory — one level above this project root.

This avoids requiring a system-wide Node.js installation for frontend
development. The downloaded binaries are excluded from version control
via .gitignore.

Usage:
    poetry run python scripts/get_node.py

Node.js version can be overridden via the NODE_VERSION env variable:
    NODE_VERSION=v22.2.0 poetry run python scripts/get_node.py
"""

from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path

import httpx

# ── Configuration ─────────────────────────────────────────────────────────────

# Override by setting NODE_VERSION env var, e.g. NODE_VERSION=v22.2.0
NODE_VERSION = os.environ.get("NODE_VERSION", "v20.12.2")
NODE_DIR_NAME = f"node-{NODE_VERSION}-win-x64"
ZIP_URL = f"https://nodejs.org/dist/{NODE_VERSION}/{NODE_DIR_NAME}.zip"

# Target: <workspace_root>/.node/  (parent of the dental-ddi-risk-scorer project)
ROOT_DIR = Path(__file__).resolve().parents[1]
TARGET_DIR = ROOT_DIR.parent / ".node"
ZIP_PATH = TARGET_DIR / "node.zip"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _node_exe() -> Path:
    """Return the expected path to node.exe after extraction."""
    return TARGET_DIR / NODE_DIR_NAME / "node.exe"


def _download_zip() -> None:
    """Download the Node.js zip archive with a progress indicator."""
    log.info("Downloading Node.js %s from %s …", NODE_VERSION, ZIP_URL)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with httpx.Client(follow_redirects=True, timeout=120.0) as client:
            with client.stream("GET", ZIP_URL) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(ZIP_PATH, "wb") as fp:
                    for chunk in response.iter_bytes(chunk_size=256 * 1024):
                        fp.write(chunk)
                        downloaded += len(chunk)

                        # Log progress every ~5 MB
                        if total and downloaded % (5 * 1024 * 1024) < (256 * 1024):
                            pct = 100 * downloaded / total
                            log.info(
                                "  %.0f%%  (%s / %s bytes)", pct, f"{downloaded:,}", f"{total:,}"
                            )

        log.info("Download complete — %s bytes written to %s", f"{downloaded:,}", ZIP_PATH)

    except httpx.HTTPStatusError as exc:
        log.error("HTTP error downloading Node.js: %s", exc)
        raise
    except httpx.RequestError as exc:
        log.error("Network error: %s", exc)
        raise


def _extract_zip() -> None:
    """Extract the downloaded zip and remove the archive afterwards."""
    log.info("Extracting archive to %s …", TARGET_DIR)
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(TARGET_DIR)

    # Clean up the zip file to save space
    ZIP_PATH.unlink()
    log.info("Archive extracted and zip file removed.")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point — idempotent: skips download if node.exe already exists."""
    node_exe = _node_exe()

    if node_exe.exists():
        log.info("Node.js already available at: %s — nothing to do.", node_exe)
        return

    _download_zip()
    _extract_zip()

    log.info("Node.js %s ready at: %s", NODE_VERSION, node_exe)
    log.info(
        "To use it without a system PATH change, call it explicitly:\n" "  %s --version", node_exe
    )


if __name__ == "__main__":
    main()

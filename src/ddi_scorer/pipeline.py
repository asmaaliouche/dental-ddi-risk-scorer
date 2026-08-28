"""
pipeline.py
-----------
Reads the raw TWOSIDES CSV, filters interaction rows where at least one drug
is in the curated dental drug list, and writes a clean Parquet file to
data/processed/.

Usage:
    poetry run python -m ddi_scorer.pipeline
    # or directly:
    poetry run python src/ddi_scorer/pipeline.py
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]  # project root
TWOSIDES_PATH = ROOT / "data" / "raw" / "TWOSIDES.csv"
DENTAL_REF_PATH = ROOT / "data" / "reference" / "dental_drugs.csv"
OUT_PATH = ROOT / "data" / "processed" / "interactions.parquet"

CHUNK_SIZE = 500_000

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


def load_dental_drug_set(ref_path: Path) -> set[str]:
    """Return the set of lowercase drug names that act as join keys to TWOSIDES."""
    df = pd.read_csv(ref_path)
    names = set(df["drug_name"].str.lower().str.strip())
    log.info("Dental drug set loaded: %d drugs", len(names))
    return names


def load_dental_drug_lookup(ref_path: Path) -> dict[str, dict]:
    """Return a dict keyed by drug_name with category/display_name metadata."""
    df = pd.read_csv(ref_path)
    df["drug_name"] = df["drug_name"].str.lower().str.strip()
    return df.set_index("drug_name").to_dict(orient="index")


def filter_twosides(
    twosides_path: Path,
    dental_drugs: set[str],
    chunk_size: int = CHUNK_SIZE,
) -> pd.DataFrame:
    """
    Stream TWOSIDES in chunks, keeping only rows where at least one drug
    is in the dental drug set.

    Returns a concatenated DataFrame of all matching rows.
    """
    kept_chunks: list[pd.DataFrame] = []
    total_rows = 0
    kept_rows = 0

    log.info("Streaming TWOSIDES from %s …", twosides_path)
    t0 = time.time()

    for i, chunk in enumerate(pd.read_csv(twosides_path, chunksize=chunk_size, low_memory=False)):
        total_rows += len(chunk)

        # Normalise names to lowercase for matching
        d1 = chunk["drug_1_concept_name"].str.lower().str.strip()
        d2 = chunk["drug_2_concept_name"].str.lower().str.strip()

        mask = d1.isin(dental_drugs) | d2.isin(dental_drugs)
        matched = chunk[mask].copy()

        if not matched.empty:
            kept_chunks.append(matched)
            kept_rows += len(matched)

        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            log.info(
                "  chunk %3d | rows processed: %9s | kept: %7s | %.1fs elapsed",
                i + 1,
                f"{total_rows:,}",
                f"{kept_rows:,}",
                elapsed,
            )

    elapsed = time.time() - t0
    log.info(
        "Done. Total rows: %s | Kept: %s (%.2f%%) | %.1fs",
        f"{total_rows:,}",
        f"{kept_rows:,}",
        100 * kept_rows / max(total_rows, 1),
        elapsed,
    )

    return pd.concat(kept_chunks, ignore_index=True) if kept_chunks else pd.DataFrame()


def enrich(df: pd.DataFrame, lookup: dict[str, dict]) -> pd.DataFrame:
    """
    Add dental-side metadata columns so downstream scoring knows which drug
    in the pair is the dental drug and what category it belongs to.

    A pair can have:
      - dental_drug = drug_1   (dentist prescribes drug_1, patient on drug_2)
      - dental_drug = drug_2   (patient on drug_1, dentist prescribes drug_2)
      - both                   (both drugs are dental — flag as well)
    """
    d1 = df["drug_1_concept_name"].str.lower().str.strip()
    d2 = df["drug_2_concept_name"].str.lower().str.strip()

    dental_set = set(lookup.keys())

    df = df.copy()
    df["drug_1_is_dental"] = d1.isin(dental_set)
    df["drug_2_is_dental"] = d2.isin(dental_set)

    # Identify which drug is the dental drug (for single-dental pairs)
    df["dental_drug_name"] = None
    df["patient_drug_name"] = None
    df["dental_drug_category"] = None

    # Case 1: drug_1 is dental, drug_2 is the patient's drug
    mask1 = df["drug_1_is_dental"] & ~df["drug_2_is_dental"]
    df.loc[mask1, "dental_drug_name"] = df.loc[mask1, "drug_1_concept_name"]
    df.loc[mask1, "patient_drug_name"] = df.loc[mask1, "drug_2_concept_name"]
    df.loc[mask1, "dental_drug_category"] = d1[mask1].map(
        lambda x: lookup.get(x, {}).get("category", "Unknown")
    )

    # Case 2: drug_2 is dental, drug_1 is the patient's drug
    mask2 = df["drug_2_is_dental"] & ~df["drug_1_is_dental"]
    df.loc[mask2, "dental_drug_name"] = df.loc[mask2, "drug_2_concept_name"]
    df.loc[mask2, "patient_drug_name"] = df.loc[mask2, "drug_1_concept_name"]
    df.loc[mask2, "dental_drug_category"] = d2[mask2].map(
        lambda x: lookup.get(x, {}).get("category", "Unknown")
    )

    # Case 3: both are dental drugs (drug-drug within dental list)
    mask3 = df["drug_1_is_dental"] & df["drug_2_is_dental"]
    df.loc[mask3, "dental_drug_name"] = df.loc[mask3, "drug_1_concept_name"]
    df.loc[mask3, "patient_drug_name"] = df.loc[mask3, "drug_2_concept_name"]
    df.loc[mask3, "dental_drug_category"] = "Both dental"

    return df


def save(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # pyarrow requires homogeneous column types; TWOSIDES has mixed int/str in
    # ID columns — cast all object columns to str to avoid ArrowTypeError.
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str)
    df.to_parquet(out_path, index=False, engine="pyarrow")
    size_mb = out_path.stat().st_size / 1_048_576
    log.info("Saved → %s  (%.1f MB, %s rows)", out_path, size_mb, f"{len(df):,}")


# ── Main ──────────────────────────────────────────────────────────────────────


def run() -> pd.DataFrame:
    dental_drugs = load_dental_drug_set(DENTAL_REF_PATH)
    lookup = load_dental_drug_lookup(DENTAL_REF_PATH)

    df = filter_twosides(TWOSIDES_PATH, dental_drugs)

    if df.empty:
        log.warning("No interactions found — check drug names match TWOSIDES exactly.")
        return df

    df = enrich(df, lookup)
    save(df, OUT_PATH)

    # Quick summary
    log.info("--- Summary ---")
    log.info("Unique dental drugs with interactions: %d", df["dental_drug_name"].nunique())
    log.info("Unique patient drugs involved:         %d", df["patient_drug_name"].nunique())
    log.info("Unique adverse effects:                %d", df["condition_concept_name"].nunique())
    log.info(
        "Unique drug pairs:                     %d",
        df[["drug_1_concept_name", "drug_2_concept_name"]].drop_duplicates().shape[0],
    )

    return df


if __name__ == "__main__":
    run()

"""
scorer.py
---------
Aggregates the 7M-row interactions.parquet (one row per drug-pair × adverse effect)
into ONE composite risk score per unique (dental_drug, patient_drug) pair.

Scoring axes (total = 100 points, all percentile-rank normalised):
  1. PRR signal strength   (40 pts) — percentile rank of max PRR across all pairs
  2. Adverse effect breadth (30 pts) — percentile rank of distinct adverse effects
  3. Mean severity weight   (30 pts) — mean clinical severity of reported effects,
                                        normalised within the distribution

Note on percentile-rank scoring: because FAERS captures predominantly serious
events (deaths, hospitalisations), max_severity_weight is 1.0 for ~95% of pairs
— effectively useless. Mean severity weight (0.05–0.83) actually discriminates.
Similarly, absolute PRR thresholds are replaced by rank-based scoring so that
the score reflects *relative* risk within this dental drug population.

Output: data/processed/scores.parquet  (one row per drug pair)

Usage:
    poetry run python -m ddi_scorer.scorer
    make score
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
INTERACTIONS = ROOT / "data" / "processed" / "interactions.parquet"
DENTAL_REF = ROOT / "data" / "reference" / "dental_drugs.csv"
SCORES_OUT = ROOT / "data" / "processed" / "scores.parquet"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Severity dictionary ───────────────────────────────────────────────────────
# Maps adverse effect keyword fragments → severity weight (0.0–1.0).
# Clinical judgement: these are the adverse effects that matter most in a
# dental prescribing context.  Any condition_concept_name containing one of
# these substrings (case-insensitive) gets the corresponding weight.
# Everything not matched defaults to LOW (0.1).

SEVERITY_RULES: list[tuple[float, list[str]]] = [
    # ── HIGH (1.0) — life-threatening / serious harm ──────────────────────────
    (
        1.0,
        [
            "death",
            "cardiac arrest",
            "ventricular fibrill",
            "ventricular tachycard",
            "qt prolongation",
            "torsade",
            "torsades",
            "rhabdomyolysis",
            "anaphyla",  # anaphylaxis / anaphylactic shock
            "stevens-johnson",
            "toxic epidermal necrolysis",
            "serotonin syndrome",
            "haemorrhage",
            "hemorrhage",
            "respiratory failure",
            "respiratory arrest",
            "hepatic failure",
            "liver failure",
            "hepatic necrosis",
            "renal failure",
            "acute kidney",
            "agranulocytosis",
            "seizure",
            "status epilepticus",
            "stroke",
            "cerebral infarct",
            "pulmonary embolism",
            "angio-oedema",
            "angioedema",
            "sudden death",
        ],
    ),
    # ── MEDIUM (0.5) — significant but manageable ─────────────────────────────
    (
        0.5,
        [
            "hepatitis",
            "jaundice",
            "cholestasis",
            "thrombocytopenia",
            "neutropenia",
            "leucopenia",
            "leukopenia",
            "myopathy",
            "myalgia",
            "neuropathy",
            "peripheral neuropathy",
            "arrhythmia",
            "atrial fibrill",
            "bradycardia",
            "tachycardia",
            "syncope",
            "loss of consciousness",
            "hypoglycaemia",
            "hypoglycemia",
            "hyponatraemia",
            "hyponatremia",
            "hallucination",
            "psychosis",
            "confusion",
            "renal impairment",
            "creatinine increased",
            "hypotension",
            "pancreatitis",
            "colitis",
            "pseudomembranous",
        ],
    ),
    # ── LOW (0.2) — uncomfortable but not dangerous ───────────────────────────
    (
        0.2,
        [
            "nausea",
            "vomiting",
            "diarrhoea",
            "diarrhea",
            "headache",
            "dizziness",
            "somnolence",
            "sedation",
            "rash",
            "urticaria",
            "pruritus",
            "constipation",
            "abdominal pain",
            "insomnia",
            "anxiety",
            "dry mouth",
            "fatigue",
            "asthenia",
            "oedema",
            "edema",
            "dyspepsia",
            "flatulence",
        ],
    ),
]

# Default weight for any condition not matched above
DEFAULT_SEVERITY_WEIGHT = 0.05


# ── Helpers ───────────────────────────────────────────────────────────────────


def severity_weight(condition_name: str) -> float:
    """Return the severity weight for a given adverse effect name."""
    cn = condition_name.lower()
    for weight, keywords in SEVERITY_RULES:
        if any(kw in cn for kw in keywords):
            return weight
    return DEFAULT_SEVERITY_WEIGHT


def load_interactions(path: Path) -> pd.DataFrame:
    log.info("Loading interactions from %s …", path)
    df = pd.read_parquet(path)

    # Columns were stored as strings — cast numeric ones back
    for col in ["PRR", "PRR_error", "mean_reporting_frequency", "A", "B", "C", "D"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    log.info("Loaded %s rows, %s columns", f"{len(df):,}", len(df.columns))
    return df


def load_dental_ref(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["drug_name"] = df["drug_name"].str.lower().str.strip()
    return df.set_index("drug_name")


def add_severity_weights(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorised severity weighting using the SEVERITY_RULES lookup."""
    log.info("Computing severity weights …")
    cn_lower = df["condition_concept_name"].str.lower().fillna("")

    weights = pd.Series(DEFAULT_SEVERITY_WEIGHT, index=df.index, dtype=float)
    # Apply rules from lowest to highest priority so HIGH overwrites LOW
    for weight, keywords in reversed(SEVERITY_RULES):
        pattern = "|".join(keywords)
        mask = cn_lower.str.contains(pattern, regex=True, na=False)
        weights[mask] = weight

    df = df.copy()
    df["severity_weight"] = weights
    return df


def aggregate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse one row per (dental_drug, patient_drug, adverse_effect) into
    one row per (dental_drug, patient_drug) with a composite risk score.

    Scoring uses percentile-rank normalisation so that scores reflect
    *relative* risk within this dental-drug population rather than
    arbitrary absolute thresholds.
    """
    log.info("Aggregating scores per drug pair …")

    # Drop rows where dental or patient drug is null / 'None'
    df = df[
        df["dental_drug_name"].notna()
        & (df["dental_drug_name"] != "None")
        & df["patient_drug_name"].notna()
        & (df["patient_drug_name"] != "None")
    ].copy()

    grp = df.groupby(["dental_drug_name", "patient_drug_name", "dental_drug_category"])

    agg = grp.agg(
        prr_max=("PRR", "max"),
        prr_mean=("PRR", "mean"),
        n_adverse_effects=("condition_concept_name", "nunique"),
        max_severity_weight=("severity_weight", "max"),
        mean_severity_weight=("severity_weight", "mean"),
        mean_reporting_freq=("mean_reporting_frequency", "mean"),
    ).reset_index()

    n = len(agg)

    # ── Component scores (percentile-rank normalised, each 0–1) ───────────
    #
    # PRR component: rank all pairs by their max PRR; a pair at the 90th
    # percentile gets 0.90, at the 50th gets 0.50, etc.
    agg["prr_component"] = rankdata(agg["prr_max"].fillna(0), method="average") / n

    # Breadth component: rank by number of distinct adverse effects.
    agg["breadth_component"] = rankdata(agg["n_adverse_effects"], method="average") / n

    # Severity component: use MEAN severity weight (max is 1.0 for ~95% of
    # pairs due to FAERS bias — it adds no information). Normalise mean
    # weight linearly from its observed min to max → 0–1.
    sw_min = agg["mean_severity_weight"].min()
    sw_max = agg["mean_severity_weight"].max()
    agg["severity_component"] = ((agg["mean_severity_weight"] - sw_min) / (sw_max - sw_min)).fillna(
        0
    )

    # ── Composite score (0–100) ─────────────────────────────────────────────
    agg["risk_score"] = (
        agg["prr_component"] * 40  # 40 pts — signal strength
        + agg["breadth_component"] * 30  # 30 pts — breadth of evidence
        + agg["severity_component"] * 30  # 30 pts — clinical severity
    ).round(1)

    # ── Severity bin ────────────────────────────────────────────────────────
    # Thresholds chosen to yield roughly: major ~15%, moderate ~35%, minor ~50%
    # based on percentile-rank score distribution.
    agg["severity_bin"] = pd.cut(
        agg["risk_score"],
        bins=[-0.1, 45, 70, 100],
        labels=["minor", "moderate", "major"],
    )

    return agg


def add_top_adverse_effects(df_agg: pd.DataFrame, df_full: pd.DataFrame) -> pd.DataFrame:
    """
    For each drug pair, attach the top 5 adverse effects ranked by severity
    weight then PRR, as a pipe-separated string (API-friendly).
    """
    log.info("Attaching top adverse effects per pair …")

    df_full = df_full[
        df_full["dental_drug_name"].notna()
        & (df_full["dental_drug_name"] != "None")
        & df_full["patient_drug_name"].notna()
        & (df_full["patient_drug_name"] != "None")
    ].copy()

    top = (
        df_full.sort_values(["severity_weight", "PRR"], ascending=[False, False])
        .groupby(["dental_drug_name", "patient_drug_name"])["condition_concept_name"]
        .apply(lambda s: "|".join(s.drop_duplicates().head(5)))
        .reset_index()
        .rename(columns={"condition_concept_name": "top_adverse_effects"})
    )

    return df_agg.merge(top, on=["dental_drug_name", "patient_drug_name"], how="left")


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, engine="pyarrow")
    size_mb = path.stat().st_size / 1_048_576
    log.info("Saved → %s  (%.1f MB, %s rows)", path, size_mb, f"{len(df):,}")


def print_summary(df: pd.DataFrame) -> None:
    log.info("─── Scoring Summary ───────────────────────────────────────────")
    log.info("Total scored pairs:  %s", f"{len(df):,}")
    log.info("Severity breakdown:")
    counts = df["severity_bin"].value_counts().reindex(["major", "moderate", "minor"])
    for label, count in counts.items():
        pct = 100 * count / len(df)
        log.info("  %-10s %5s  (%.1f%%)", label, f"{count:,}", pct)

    log.info("Top 10 highest-risk pairs:")
    top10 = df.nlargest(10, "risk_score")[
        [
            "dental_drug_name",
            "patient_drug_name",
            "risk_score",
            "severity_bin",
            "n_adverse_effects",
            "prr_max",
        ]
    ]
    for _, row in top10.iterrows():
        log.info(
            "  %-20s ↔ %-20s  score=%-5.1f  bin=%-8s  n_ae=%-5d  prr_max=%.1f",
            row["dental_drug_name"],
            row["patient_drug_name"],
            row["risk_score"],
            row["severity_bin"],
            row["n_adverse_effects"],
            row["prr_max"] if not np.isnan(row["prr_max"]) else 0,
        )


# ── Main ──────────────────────────────────────────────────────────────────────


def run() -> pd.DataFrame:
    df_full = load_interactions(INTERACTIONS)
    df_full = add_severity_weights(df_full)
    df_agg = aggregate_scores(df_full)
    df_agg = add_top_adverse_effects(df_agg, df_full)

    # Load dental ref to attach display_name and notes
    ref = load_dental_ref(DENTAL_REF)
    df_agg["dental_drug_display"] = df_agg["dental_drug_name"].map(
        lambda x: ref.loc[x, "display_name"] if x in ref.index else x
    )
    df_agg["dental_drug_notes"] = df_agg["dental_drug_name"].map(
        lambda x: ref.loc[x, "notes"] if x in ref.index else ""
    )

    save(df_agg, SCORES_OUT)
    print_summary(df_agg)
    return df_agg


if __name__ == "__main__":
    run()

"""
tests/test_scorer.py
Tests for the scoring engine.
Uses small synthetic DataFrames — no real data files required.
"""

import pandas as pd
import pytest

from ddi_scorer.scorer import add_severity_weights, aggregate_scores, severity_weight

# ── Tests: severity_weight ────────────────────────────────────────────────────


def test_severity_weight_high_for_death():
    assert severity_weight("Death") == 1.0


def test_severity_weight_high_for_qt_prolongation():
    assert severity_weight("QT prolongation") == 1.0


def test_severity_weight_high_for_rhabdomyolysis():
    assert severity_weight("Rhabdomyolysis") == 1.0


def test_severity_weight_high_for_anaphylaxis():
    assert severity_weight("Anaphylactic shock") == 1.0


def test_severity_weight_medium_for_hepatitis():
    assert severity_weight("Drug-induced hepatitis") == 0.5


def test_severity_weight_medium_for_arrhythmia():
    assert severity_weight("Cardiac arrhythmia") == 0.5


def test_severity_weight_low_for_nausea():
    assert severity_weight("Nausea and vomiting") == 0.2


def test_severity_weight_low_for_rash():
    assert severity_weight("Skin rash") == 0.2


def test_severity_weight_default_for_unknown():
    """Conditions not matching any keyword should return the default."""
    assert severity_weight("Some obscure condition") == 0.05


def test_severity_weight_case_insensitive():
    """Matching should be case-insensitive."""
    assert severity_weight("DEATH") == severity_weight("death") == 1.0


# ── Tests: add_severity_weights ───────────────────────────────────────────────


def test_add_severity_weights_adds_column():
    df = pd.DataFrame({"condition_concept_name": ["Death", "Nausea", "Unknown condition"]})
    result = add_severity_weights(df)
    assert "severity_weight" in result.columns
    assert len(result) == 3


def test_add_severity_weights_correct_values():
    df = pd.DataFrame({"condition_concept_name": ["Death", "Nausea", "Unknown condition"]})
    result = add_severity_weights(df)
    assert result.loc[0, "severity_weight"] == 1.0  # Death → HIGH
    assert result.loc[1, "severity_weight"] == 0.2  # Nausea → LOW
    assert result.loc[2, "severity_weight"] == 0.05  # Unknown → DEFAULT


def test_add_severity_weights_does_not_mutate_input():
    df = pd.DataFrame({"condition_concept_name": ["Death"]})
    _ = add_severity_weights(df)
    assert "severity_weight" not in df.columns


# ── Tests: aggregate_scores ───────────────────────────────────────────────────


@pytest.fixture
def sample_interactions():
    """Synthetic interaction rows for two drug pairs."""
    return pd.DataFrame(
        {
            "dental_drug_name": ["fluconazole"] * 3 + ["ibuprofen"] * 2,
            "patient_drug_name": ["simvastatin"] * 3 + ["warfarin"] * 2,
            "dental_drug_category": ["Antifungal"] * 3 + ["NSAID Analgesic"] * 2,
            "condition_concept_name": [
                "Rhabdomyolysis",
                "Death",
                "Nausea",
                "Haemorrhage",
                "Death",
            ],
            "PRR": [12.7, 8.3, 3.1, 5.5, 4.0],
            "PRR_error": [0.3, 0.2, 0.1, 0.4, 0.3],
            "mean_reporting_frequency": [0.08, 0.05, 0.02, 0.04, 0.03],
            "severity_weight": [1.0, 1.0, 0.2, 1.0, 1.0],
        }
    )


def test_aggregate_scores_one_row_per_pair(sample_interactions):
    """Output should have exactly one row per unique (dental, patient) pair."""
    result = aggregate_scores(sample_interactions)
    assert len(result) == 2


def test_aggregate_scores_has_required_columns(sample_interactions):
    result = aggregate_scores(sample_interactions)
    for col in [
        "risk_score",
        "severity_bin",
        "prr_max",
        "n_adverse_effects",
        "mean_severity_weight",
        "prr_component",
        "breadth_component",
        "severity_component",
    ]:
        assert col in result.columns, f"Missing column: {col}"


def test_aggregate_scores_risk_score_in_range(sample_interactions):
    """All risk scores should be between 0 and 100."""
    result = aggregate_scores(sample_interactions)
    assert (result["risk_score"] >= 0).all()
    assert (result["risk_score"] <= 100).all()


def test_aggregate_scores_severity_bin_valid(sample_interactions):
    """All severity bins should be one of the three valid labels."""
    result = aggregate_scores(sample_interactions)
    valid = {"major", "moderate", "minor"}
    bins = set(result["severity_bin"].astype(str).unique())
    assert bins.issubset(valid | {"nan"}), f"Unexpected bin values: {bins}"


def test_aggregate_scores_prr_max_is_max(sample_interactions):
    """prr_max for fluconazole↔simvastatin should be 12.7."""
    result = aggregate_scores(sample_interactions)
    fc_row = result[result["dental_drug_name"] == "fluconazole"]
    assert fc_row["prr_max"].iloc[0] == pytest.approx(12.7)


def test_aggregate_scores_drops_none_rows():
    """Rows where dental_drug_name is None or 'None' should be excluded."""
    df = pd.DataFrame(
        {
            "dental_drug_name": [None, "None", "ibuprofen"],
            "patient_drug_name": ["warfarin", "warfarin", "warfarin"],
            "dental_drug_category": ["X", "X", "NSAID Analgesic"],
            "condition_concept_name": ["Death", "Death", "Haemorrhage"],
            "PRR": [5.0, 5.0, 3.0],
            "PRR_error": [0.2, 0.2, 0.1],
            "mean_reporting_frequency": [0.03, 0.03, 0.02],
            "severity_weight": [1.0, 1.0, 1.0],
        }
    )
    result = aggregate_scores(df)
    assert len(result) == 1
    assert result.iloc[0]["dental_drug_name"] == "ibuprofen"

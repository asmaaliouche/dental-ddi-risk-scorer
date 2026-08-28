"""
tests/test_pipeline.py
Tests for the dental drug filter pipeline.
Uses small synthetic DataFrames — no real data files required.
"""

from pathlib import Path

import pandas as pd
import pytest

from ddi_scorer.pipeline import enrich, filter_twosides, load_dental_drug_set

# ── Fixtures ──────────────────────────────────────────────────────────────────

DENTAL_REF = Path(__file__).resolve().parents[1] / "data" / "reference" / "dental_drugs.csv"


@pytest.fixture
def dental_set():
    return {"amoxicillin", "ibuprofen", "fluconazole"}


@pytest.fixture
def sample_twosides(dental_set):
    """A tiny synthetic TWOSIDES-like DataFrame for testing."""
    return pd.DataFrame(
        {
            "drug_1_concept_name": ["amoxicillin", "warfarin", "metformin"],
            "drug_2_concept_name": ["warfarin", "metformin", "atorvastatin"],
            "condition_concept_name": ["Haemorrhage", "Nausea", "Myopathy"],
            "PRR": [4.2, 1.1, 2.3],
            "PRR_error": [0.3, 0.2, 0.4],
            "mean_reporting_frequency": [0.03, 0.01, 0.02],
            "A": [10, 5, 7],
            "B": [100, 200, 150],
            "C": [20, 10, 15],
            "D": [1000, 2000, 1500],
            "drug_1_rxnorn_id": ["12345", "67890", "11111"],
            "drug_2_rxnorm_id": ["99999", "11111", "22222"],
            "condition_meddra_id": ["10019222", "10028813", "10028607"],
        }
    )


# ── Tests: load_dental_drug_set ───────────────────────────────────────────────


def test_load_dental_drug_set_returns_set():
    """Should return a set of lowercase drug name strings."""
    result = load_dental_drug_set(DENTAL_REF)
    assert isinstance(result, set)
    assert len(result) > 0


def test_load_dental_drug_set_lowercase():
    """All names in the set should be lowercase."""
    result = load_dental_drug_set(DENTAL_REF)
    for name in result:
        assert name == name.lower(), f"Name not lowercase: {name}"


def test_load_dental_drug_set_contains_key_drugs():
    """Known dental drugs must be present."""
    result = load_dental_drug_set(DENTAL_REF)
    for drug in ["amoxicillin", "fluconazole", "ibuprofen", "metronidazole", "lidocaine"]:
        assert drug in result, f"Expected dental drug missing: {drug}"


# ── Tests: filter_twosides ────────────────────────────────────────────────────


def test_filter_keeps_dental_rows(sample_twosides, dental_set, tmp_path):
    """Only rows involving a dental drug should be kept."""
    # Write synthetic data to a temp CSV
    csv_path = tmp_path / "TWOSIDES.csv"
    sample_twosides.to_csv(csv_path, index=False)

    result = filter_twosides(csv_path, dental_set, chunk_size=10)

    assert len(result) == 1  # Only amoxicillin↔warfarin row
    assert "amoxicillin" in result["drug_1_concept_name"].values


def test_filter_discards_non_dental_rows(sample_twosides, dental_set, tmp_path):
    """Rows with no dental drug on either side must be dropped."""
    csv_path = tmp_path / "TWOSIDES.csv"
    sample_twosides.to_csv(csv_path, index=False)

    result = filter_twosides(csv_path, dental_set, chunk_size=10)

    # metformin↔atorvastatin should not appear
    all_drugs = set(result["drug_1_concept_name"]) | set(result["drug_2_concept_name"])
    assert "atorvastatin" not in all_drugs


def test_filter_empty_result_when_no_dental_match(tmp_path):
    """If no dental drug appears in the data, return an empty DataFrame."""
    df = pd.DataFrame(
        {
            "drug_1_concept_name": ["metformin"],
            "drug_2_concept_name": ["atorvastatin"],
            "condition_concept_name": ["Nausea"],
            "PRR": [1.1],
            "PRR_error": [0.2],
            "mean_reporting_frequency": [0.01],
            "A": [5],
            "B": [200],
            "C": [10],
            "D": [2000],
            "drug_1_rxnorn_id": ["1"],
            "drug_2_rxnorm_id": ["2"],
            "condition_meddra_id": ["123"],
        }
    )
    csv_path = tmp_path / "TWOSIDES.csv"
    df.to_csv(csv_path, index=False)

    result = filter_twosides(csv_path, {"amoxicillin"}, chunk_size=10)
    assert result.empty


# ── Tests: enrich ─────────────────────────────────────────────────────────────


@pytest.fixture
def dental_lookup():
    return {
        "amoxicillin": {
            "category": "Antibiotic",
            "display_name": "Amoxicillin",
            "atc_code": "J01CA04",
            "notes": "",
        },
        "ibuprofen": {
            "category": "NSAID Analgesic",
            "display_name": "Ibuprofen",
            "atc_code": "M01AE01",
            "notes": "",
        },
    }


def test_enrich_labels_dental_drug_correctly(dental_lookup):
    """When drug_1 is dental and drug_2 is patient, labels should reflect that."""
    df = pd.DataFrame(
        {
            "drug_1_concept_name": ["amoxicillin"],
            "drug_2_concept_name": ["warfarin"],
            "drug_1_is_dental": [True],
            "drug_2_is_dental": [False],
        }
    )
    result = enrich(df, dental_lookup)

    assert result.loc[0, "dental_drug_name"] == "amoxicillin"
    assert result.loc[0, "patient_drug_name"] == "warfarin"
    assert result.loc[0, "dental_drug_category"] == "Antibiotic"


def test_enrich_both_dental_flagged(dental_lookup):
    """When both drugs are dental, dental_drug_category should be 'Both dental'."""
    df = pd.DataFrame(
        {
            "drug_1_concept_name": ["amoxicillin"],
            "drug_2_concept_name": ["ibuprofen"],
            "drug_1_is_dental": [True],
            "drug_2_is_dental": [True],
        }
    )
    result = enrich(df, dental_lookup)
    assert result.loc[0, "dental_drug_category"] == "Both dental"


def test_enrich_reverse_pair(dental_lookup):
    """When drug_2 is dental and drug_1 is patient, assignment should be reversed."""
    df = pd.DataFrame(
        {
            "drug_1_concept_name": ["warfarin"],
            "drug_2_concept_name": ["ibuprofen"],
            "drug_1_is_dental": [False],
            "drug_2_is_dental": [True],
        }
    )
    result = enrich(df, dental_lookup)

    assert result.loc[0, "dental_drug_name"] == "ibuprofen"
    assert result.loc[0, "patient_drug_name"] == "warfarin"

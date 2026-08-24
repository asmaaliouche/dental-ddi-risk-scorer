"""
api/schemas.py
Pydantic request and response models for the DDI Risk Scorer API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── /check ────────────────────────────────────────────────────────────────────

class CheckRequest(BaseModel):
    patient_drugs: list[str] = Field(
        ...,
        min_length=1,
        description="List of drugs the patient is currently taking (any case).",
        examples=[["warfarin", "atorvastatin", "metformin"]],
    )


class InteractionResult(BaseModel):
    dental_drug: str = Field(description="Canonical dental drug name (lowercase).")
    dental_drug_display: str = Field(description="Human-readable dental drug name.")
    dental_drug_category: str = Field(description="Clinical category (e.g. Antibiotic).")
    dental_drug_notes: str = Field(description="Key clinical notes for this drug.")
    patient_drug: str = Field(description="Patient's existing drug that interacts.")
    risk_score: float = Field(description="Composite risk score 0–100.")
    severity_bin: str = Field(description="major | moderate | minor")
    top_adverse_effects: list[str] = Field(
        description="Up to 5 most clinically significant adverse effects reported."
    )
    prr_max: float = Field(description="Maximum Proportional Reporting Ratio for this pair.")
    n_adverse_effects: int = Field(description="Number of distinct adverse effects reported.")


class CheckResponse(BaseModel):
    interactions: list[InteractionResult]
    patient_drugs_checked: list[str] = Field(
        description="Normalised list of patient drugs that were searched."
    )
    patient_drugs_not_found: list[str] = Field(
        description="Patient drugs that had no interactions with dental drugs in the database."
    )
    total_interactions: int


# ── /dental-drugs ─────────────────────────────────────────────────────────────

class DentalDrug(BaseModel):
    name: str = Field(description="Canonical lowercase name (used for matching).")
    display_name: str
    category: str
    atc_code: str
    notes: str


class DentalDrugsResponse(BaseModel):
    drugs: list[DentalDrug]
    total: int


# ── /patient-drugs ────────────────────────────────────────────────────────────

class PatientDrugsResponse(BaseModel):
    drugs: list[str] = Field(
        description="All patient-side drug names available in the interaction database."
    )
    total: int

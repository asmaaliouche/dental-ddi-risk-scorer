"""
api/routers/drugs.py
--------------------
Reference data endpoints:

  GET /dental-drugs   — returns the curated list of 27 dental prescribing drugs
                        with category, ATC code, and clinical notes. Used to
                        populate frontend drug pickers and documentation.

  GET /patient-drugs  — returns all patient-side drug names indexed in the
                        interaction database (~1,739 unique names). Used to
                        power frontend autocomplete on the patient input.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from api.schemas import DentalDrug, DentalDrugsResponse, PatientDrugsResponse

log = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/dental-drugs",
    response_model=DentalDrugsResponse,
    summary="List dental drugs",
    description=(
        "Returns the curated list of drugs a dentist commonly prescribes. "
        "Each entry includes the canonical name, display name, clinical category, "
        "ATC code, and pharmacological notes."
    ),
)
async def get_dental_drugs(request: Request) -> DentalDrugsResponse:
    """
    Serialise the dental_drugs DataFrame (loaded from dental_drugs.csv at
    startup) into a list of DentalDrug response models.
    """
    dental_df = request.app.state.dental_drugs

    drugs = [
        DentalDrug(
            name=str(row["drug_name"]),
            display_name=str(row["display_name"]),
            category=str(row["category"]),
            atc_code=str(row["atc_class"]),
            notes=str(row["notes"]),
        )
        for _, row in dental_df.iterrows()
    ]

    log.debug("GET /dental-drugs — returning %d drugs", len(drugs))
    return DentalDrugsResponse(drugs=drugs, total=len(drugs))


@router.get(
    "/patient-drugs",
    response_model=PatientDrugsResponse,
    summary="List patient-side drugs",
    description=(
        "Returns all unique patient drug names available in the scored interaction "
        "database. Use this list to power autocomplete on the patient medication "
        "input field. Returns an empty list if scores.parquet is not yet loaded."
    ),
)
async def get_patient_drugs(request: Request) -> PatientDrugsResponse:
    """
    Extract unique patient_drug_name values from the pre-computed scores
    DataFrame and return them sorted alphabetically.
    """
    scores_df = request.app.state.scores

    # Return an empty response if data is not yet loaded rather than raising
    if scores_df is None:
        log.warning("GET /patient-drugs called but scores DataFrame is not loaded.")
        return PatientDrugsResponse(drugs=[], total=0)

    # Drop nulls, deduplicate, and sort for consistent autocomplete ordering
    drugs = sorted(scores_df["patient_drug_name"].dropna().unique().tolist())

    log.debug("GET /patient-drugs — returning %d drug names", len(drugs))
    return PatientDrugsResponse(drugs=drugs, total=len(drugs))

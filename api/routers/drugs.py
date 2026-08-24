"""
api/routers/drugs.py
GET /dental-drugs  — returns the curated dental drug list (for autocomplete).
GET /patient-drugs — returns all patient-side drugs available in the database.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas import DentalDrug, DentalDrugsResponse, PatientDrugsResponse

router = APIRouter()


@router.get(
    "/dental-drugs",
    response_model=DentalDrugsResponse,
    summary="List dental drugs",
    description="Returns the curated list of drugs a dentist would prescribe. Use this for frontend autocomplete on the dental drug selector.",
)
async def get_dental_drugs(request: Request) -> DentalDrugsResponse:
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

    return DentalDrugsResponse(drugs=drugs, total=len(drugs))


@router.get(
    "/patient-drugs",
    response_model=PatientDrugsResponse,
    summary="List patient-side drugs",
    description=(
        "Returns all patient drug names available in the interaction database. "
        "Use this to power autocomplete on the patient medication input."
    ),
)
async def get_patient_drugs(request: Request) -> PatientDrugsResponse:
    scores_df = request.app.state.scores
    
    if scores_df is None:
        return PatientDrugsResponse(drugs=[], total=0)

    drugs = sorted(scores_df["patient_drug_name"].dropna().unique().tolist())

    return PatientDrugsResponse(drugs=drugs, total=len(drugs))

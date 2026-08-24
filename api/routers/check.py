"""
api/routers/check.py
POST /check — takes a patient drug list, returns ranked DDI interactions.
"""

from __future__ import annotations

import math
from fastapi import APIRouter, HTTPException, Request

from api.schemas import CheckRequest, CheckResponse, InteractionResult

router = APIRouter()


@router.post(
    "/check",
    response_model=CheckResponse,
    summary="Check drug interactions",
    description=(
        "Given a list of drugs the patient is currently taking, returns all "
        "known drug-drug interactions with dental prescribing drugs, ranked by "
        "risk score (highest first)."
    ),
)
async def check_interactions(body: CheckRequest, request: Request) -> CheckResponse:
    scores_df = request.app.state.scores
    if scores_df is None:
        raise HTTPException(
            status_code=503,
            detail="Interaction database not loaded. Run `make score` first.",
        )

    # Normalise input to lowercase stripped strings
    patient_drugs_input = [d.lower().strip() for d in body.patient_drugs]

    # Filter scores where patient_drug_name matches any of the input drugs
    mask = scores_df["patient_drug_name"].str.lower().isin(patient_drugs_input)
    matched = scores_df[mask].copy()

    # Track which patient drugs had matches vs not
    matched_patient_drugs = set(matched["patient_drug_name"].str.lower().unique())
    not_found = [d for d in patient_drugs_input if d not in matched_patient_drugs]

    if matched.empty:
        return CheckResponse(
            interactions=[],
            patient_drugs_checked=patient_drugs_input,
            patient_drugs_not_found=not_found,
            total_interactions=0,
        )

    # Sort by risk score descending
    matched = matched.sort_values("risk_score", ascending=False)

    interactions: list[InteractionResult] = []
    for _, row in matched.iterrows():
        # Parse top_adverse_effects from pipe-separated string
        top_ae_raw = row.get("top_adverse_effects", "") or ""
        top_ae = [ae.strip() for ae in str(top_ae_raw).split("|") if ae.strip()]

        prr_max = row["prr_max"]
        if isinstance(prr_max, float) and math.isnan(prr_max):
            prr_max = 0.0

        interactions.append(
            InteractionResult(
                dental_drug=str(row["dental_drug_name"]),
                dental_drug_display=str(row.get("dental_drug_display") or row["dental_drug_name"]),
                dental_drug_category=str(row["dental_drug_category"]),
                dental_drug_notes=str(row.get("dental_drug_notes") or ""),
                patient_drug=str(row["patient_drug_name"]),
                risk_score=round(float(row["risk_score"]), 1),
                severity_bin=str(row["severity_bin"]),
                top_adverse_effects=top_ae,
                prr_max=round(float(prr_max), 1),
                n_adverse_effects=int(row["n_adverse_effects"]),
            )
        )

    return CheckResponse(
        interactions=interactions,
        patient_drugs_checked=patient_drugs_input,
        patient_drugs_not_found=not_found,
        total_interactions=len(interactions),
    )
